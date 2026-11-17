"""Independent branch ensembles. Uniform measures are design sensitivity, not priors.

Replicates share no random streams. Branches are never averaged. Within one
branch, iid calibration/unknown draws permit MC standard errors (not MCMC ESS).
"""
import copy
from itertools import combinations, product
import json
from pathlib import Path
import time

import numpy as np
import yaml

from pet2mof.model.config import load_config
from .final import sha256, verify_frozen_inputs
from .revision_screening import draws, feasible_parameters, screen_cell, nominal_controls
from .screening import BRANCHES

CONDITIONS = tuple(f'{r}_RH{rh}' for r in ('R1', 'R2') for rh in (0, 40, 70))
CANDIDATES = np.array([0., .1, .2, .3])


def parameter_draws(scenario, settings, sourced, count, seed, mechanism, fit, measure):
    p = draws(scenario, count, seed, mechanism, fit['n_N']*fit['models']['M1']['parameters']['A0'], settings,
              controls='nominal')
    if measure == 'analog':
        rng = np.random.default_rng(np.random.SeedSequence([int(seed), 14014]))
        literature = sourced['literature_ranges']
        # Directly matching Q and nitrogen fractions. Not gamma from a wet/dry
        # capacity ratio, nor effective Q_W from a zero-coverage simulation heat.
        p['Q_phys'] = rng.uniform(*literature['Q_phys']['range'], count)
        p['f3'] = rng.uniform(*literature['f3']['range'], count)
        split = rng.uniform(0., 1., count)
        p['f1'], p['f2'] = (1-p['f3'])*split, (1-p['f3'])*(1-split)
        # Explicit proxy sensitivity: reactor CO2 exponential equivalent used as
        # common tau under D-17, not an identification of H2O or target kinetics.
        p['tau_over_t'] = rng.uniform(*literature['tau_CO2_des']['range'], count)/1800.
        p['analog_V_p0'] = rng.uniform(*literature['V_p0_proxy']['range'], count)
    elif measure != 'stress':
        raise ValueError('unknown uncertainty measure')
    return p


def sampled_calibration(frozen, fit_index, material, count, seed):
    """One same joint calibration index for all coupled model components."""
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), 18018]))
    indices = rng.integers(len(frozen['joint_draws']), size=count)
    joint = [frozen['joint_draws'][i] for i in indices]
    fit = copy.deepcopy(frozen['fits'][fit_index])
    for key in ('q_sat', 'b'):
        fit['host'][key] = np.array([d['fits'][fit_index]['host'][key] for d in joint])
    for model in ('M1', 'B1'):
        for key in fit['models'][model]['parameters']:
            fit['models'][model]['parameters'][key] = np.array([d['fits'][fit_index]['models'][model]['parameters'][key] for d in joint])
    carriers = {}
    for gas in ('CO2', 'N2'):
        records = [next(c for c in d['c_fits']['carriers'] if c['material'] == 'UiO-66' and c['gas'] == gas) for d in joint]
        carriers[gas] = {k: np.array([r[k] for r in records]) for k in ('q_sat', 'b')}
    records = [next(w for w in d['c_fits']['water'] if w['material'] == material) for d in joint]
    water = dict(material=material, T_ref=records[0]['T_ref'])
    water.update({k: np.array([r[k] for r in records]) for k in ('a_s', 'm', 'equivalent_volume_cm3_g')})
    return fit, carriers, water, indices


def _probabilities(candidate):
    ties = np.isclose(candidate, candidate.max(axis=1)[:, None], atol=1e-9, rtol=0)
    unique = ties.sum(axis=1) == 1
    p = np.mean(ties & unique[:, None], axis=0)
    return p


def summarize(raw):
    """Apply HYP to four candidates; ties remain sets on the dense grid."""
    out = {}
    dry = raw['dry']
    # Max-standardized-error simultaneous family for all six pairs, both humid
    # RH and both regenerations (and corresponding dry contrasts). Protocol §6.
    pairs = list(combinations(range(4), 2))
    vectors = [dry[:, i]-dry[:, j] for i, j in pairs]
    for key in CONDITIONS:
        if key.endswith('RH0'):
            continue
        vectors += [raw[key][:, i]-raw[key][:, j] for i, j in pairs]
    z = np.column_stack(vectors)
    means, sd = z.mean(axis=0), z.std(axis=0, ddof=1)
    standardized = np.divide(abs(z-means), sd, out=np.zeros_like(z), where=sd>1e-15)
    critical = np.quantile(standardized.max(axis=1), .95)
    simultaneous = np.column_stack([means-critical*sd, means+critical*sd])
    for key in CONDITIONS:
        values = raw[key]; q = values[:, :4]
        p = _probabilities(q); n = len(q)
        se = np.sqrt(p*(1-p)/n)
        # Wilson lower bound is nondegenerate even for p=1, unlike Wald.
        lower_mc = (p+1.96**2/(2*n)-1.96*np.sqrt(p*(1-p)/n+1.96**2/(4*n*n)))/(1+1.96**2/n)
        winner = int(np.argmax(p))
        contrast = q[:, winner, None]-np.delete(q, winner, axis=1)
        # Simultaneously protect all three possible nearest competitors.
        lower = np.quantile(contrast, .025/6, axis=0)
        wci = [float(np.quantile(values[:, 4], .05)), float(np.quantile(values[:, 5], .95))]
        delta = np.quantile(values[:, 6], [.025, .975])
        resolved = bool(lower_mc[winner] >= .8 and np.min(lower) > 0)
        h1a = []
        for k, (i, j) in enumerate(pairs):
            dd, wd = dry[:, i]-dry[:, j], q[:, i]-q[:, j]
            if key.endswith('RH0'):
                wet_ci = [None, None]; supported = False
            else:
                humid_keys = [c for c in CONDITIONS if not c.endswith('RH0')]
                wet_ci = simultaneous[6+humid_keys.index(key)*6+k].tolist()
                dry_ci = simultaneous[k]
                supported = bool(np.mean(dd*wd < 0) >= .95 and dry_ci[0]*dry_ci[1] > 0 and
                                 wet_ci[0]*wet_ci[1] > 0 and dry_ci[0]*wet_ci[0] < 0)
            h1a.append(dict(pair=CANDIDATES[[i, j]].tolist(), probability=float(np.mean(dd*wd < 0)),
                            dry_simultaneous_95=simultaneous[k].tolist(), wet_simultaneous_95=wet_ci, supported=supported))
        grid_values = raw[key+'/grid']
        diffs = np.diff(grid_values, axis=1)
        bq = raw[key+'/B1']
        bp = _probabilities(bq); bse = np.sqrt(bp*(1-bp)/n); bwinner = int(np.argmax(bp))
        blower_mc = (bp+1.96**2/(2*n)-1.96*np.sqrt(bp*(1-bp)/n+1.96**2/(4*n*n)))/(1+1.96**2/n)
        bcontrast = np.quantile(bq[:, bwinner, None]-np.delete(bq, bwinner, axis=1), .025/6, axis=0)
        bties = np.isclose(bq, bq.max(axis=1)[:, None], rtol=0, atol=1e-9)
        blo = np.min(np.where(bties, CANDIDATES, np.inf), axis=1)
        bhi = np.max(np.where(bties, CANDIDATES, -np.inf), axis=1)
        out[key] = dict(rank1_probabilities=p.tolist(), SE_MC=se.tolist(), rank1_lower95_MC=lower_mc.tolist(),
                        candidate=float(CANDIDATES[winner]), winner_contrast_lower95_simultaneous=lower.tolist(),
                        winner_resolved=resolved, w_star_90=wci, delta_95=delta.tolist(),
                        interior=bool(delta[0] > 0 and wci[0] > 0 and wci[1] < .3),
                        q_work_quantiles=np.quantile(q, [.025, .5, .975], axis=0).tolist(),
                        monotone_up_probability=float(np.mean((diffs >= -1e-9).all(axis=1))),
                        monotone_down_probability=float(np.mean((diffs <= 1e-9).all(axis=1))),
                        adjacent_contrast_95=np.quantile(diffs, [.025, .975], axis=0).tolist(),
                        B1_rank1_probabilities=bp.tolist(), H1a_pairs=h1a,
                        B1=dict(rank1_probabilities=bp.tolist(), SE_MC=bse.tolist(), rank1_lower95_MC=blower_mc.tolist(),
                                candidate=float(CANDIDATES[bwinner]), winner_contrast_lower95_simultaneous=bcontrast.tolist(),
                                winner_resolved=bool(blower_mc[bwinner] >= .8 and min(bcontrast) > 0),
                                w_star_90=[float(np.quantile(blo, .05)), float(np.quantile(bhi, .95))], delta_95=[0., 0.],
                                q_work_quantiles=np.quantile(bq, [.025, .5, .975], axis=0).tolist(),
                                interior=False, reason='B1 is linear in w; continuous maxima are endpoint(s) or whole interval'))
    for regeneration in ('R1', 'R2'):
        dry_ci = out[regeneration+'_RH0']['w_star_90']
        wet_ci = out[regeneration+'_RH70']['w_star_90']
        shift = dry_ci[1] < wet_ci[0] or wet_ci[1] < dry_ci[0]
        delta_difference = np.quantile(raw[regeneration+'_RH70'][:, 6]-raw[regeneration+'_RH0'][:, 6], [.025, .975])
        out[regeneration] = dict(w_star_shift_resolved=bool(shift), delta_RH70_minus_dry_95=delta_difference.tolist(),
                               conditional_H1=bool(out[regeneration+'_RH70']['interior'] and out[regeneration+'_RH70']['winner_resolved'] and
                                                   shift and delta_difference[0]*delta_difference[1] > 0))
    return out


def convergence(repetitions, pooled, fine_checks):
    full = summarize(pooled)
    per_repeat = [summarize(r) for r in repetitions]
    half = summarize({k: np.concatenate([r[k][:max(2, len(r[k])//2)] for r in repetitions]) for k in pooled})
    p_spread = max(float(np.ptp([s[k]['rank1_probabilities'] for s in per_repeat], axis=0).max()) for k in CONDITIONS)
    doubling_p = max(float(np.max(abs(np.array(full[k]['rank1_probabilities'])-half[k]['rank1_probabilities']))) for k in CONDITIONS)
    q_spread = max(float(np.ptp([s[k]['q_work_quantiles'] for s in per_repeat], axis=0).max()) for k in CONDITIONS)
    doubling_q = max(float(np.max(abs(np.array(full[k]['q_work_quantiles'])-half[k]['q_work_quantiles']))) for k in CONDITIONS)
    return dict(probability_repeat_spread=p_spread, probability_N_doubling_change=doubling_p,
                probability_checks_pass=bool(p_spread < .02 and doubling_p < .02),
                q_quantiles_repeat_spread=q_spread, q_quantiles_N_doubling_change=doubling_q,
                grid_w_star_max_change=max(c['w_star_max_change'] for c in fine_checks),
                grid_delta_max_change=max(c['delta_max_change'] for c in fine_checks),
                grid_location_pass=all(c['w_star_max_change'] <= .01+1e-12 for c in fine_checks),
                target_observational_U=None, status='not_established',
                reason='target observational U unknown: q/Delta 0.1 U thresholds cannot be certified; no decisive H1 claim')


def run_ensemble(root, *, frozen_path='configs/frozen_parameters.yaml', output='reports/ensemble', count=4096,
                 repeats=4, seed=12001, debug=False, run_id='unregistered', branch_limit=None, plots=True):
    root = Path(root)
    frozen_file = (root/frozen_path).resolve(); frozen_file.relative_to(root.resolve())
    frozen = yaml.safe_load(frozen_file.read_text())
    verify_frozen_inputs(root, frozen)
    if frozen['missing']:
        raise ValueError('ensemble requires calibrated N2 and three water samples; missing '+str(frozen['missing']))
    if not debug and (frozen['include_provisional'] or repeats != 4 or count != 4096 or branch_limit is not None or seed != 12001):
        raise ValueError('production requires verified calibration, all branches, four repeats, seeds 12001..12004 and exactly 4096 draws (D-18)')
    if count < 4 or repeats < 2:
        raise ValueError('at least two repeats of four draws required')
    scenario = load_config(root/'configs/scenarios.yaml')['scenario']
    settings = load_config(root/'configs/revision.yaml')
    sourced = yaml.safe_load((root/'configs/sourced_ranges.yaml').read_text())
    folder = (root/output).resolve(); folder.relative_to(root.resolve()); folder.mkdir(parents=True, exist_ok=True)
    grid = np.round(np.arange(0., .300001, .01), 8)
    fine = np.round(np.arange(0., .300001, .005), 8)
    cases = list(product(('stress', 'analog'), range(len(frozen['fits'])), BRANCHES,
                         settings['transfer_branches'], settings['water_branches']))
    if branch_limit is not None:
        # Spread a small debug run across the factorial; production always all.
        cases = [cases[i] for i in np.unique(np.linspace(0, len(cases)-1, branch_limit, dtype=int))]
    result = dict(status='debug' if debug else 'conditional_forecast', run_id=run_id, seed=seed,
                  analysis_role='nominal_H1_H1a', fixed_controls=nominal_controls(scenario),
                  RH_percent=[0, 40, 70],
                  control_sensitivity=dict(status='separate_analysis', decisive=False,
                                           implementation='pet2mof.calibration.revision_screening.screen_revision',
                                           output='reports/T015/screen.json'),
                  repeat_seeds=list(range(seed, seed+repeats)),
                  samples_per_repeat=count, repeats=repeats, branches={}, elapsed_seconds=None,
                  parameter_sha256=sha256(frozen_file), rng='numpy.PCG64', numpy_version=np.__version__,
                  calibration_uncertainty=frozen['uncertainty_method'],
                  measure_note='uniform stress/design measures; analog branch is conditional proxy sensitivity, not target prior; no averaging branches',
                  analog_mappings={'Q_phys': 'Q_phys', 'f3': 'f3', 'V_p0_proxy': 'V_p0 before water-volume-transfer',
                                   'tau_CO2_des': 'tau_over_t = tau_CO2_des/1800; common relaxation is D-17 conditional assumption'},
                  analog_not_mapped=['wet/dry capacity ratios are not gamma', 'initial Q_d heat is not effective chemical Q_d',
                                     'simulation zero-coverage Q_water is not water-step Q_W', 'heat-signal log-base-unknown tau is not e-fold relaxation'],
                  unknowns_keep_stress=['Q_W', 'gamma', 'kappa', 'alpha_in', 'W_max', 'h_max', 'Q_d', 'water_volume_transfer'],
                  scientific_status='проверяемый прогноз; данных недостаточно')
    checksums = []
    result['artifact_hashes'] = {}
    result['branch_compute_seconds'] = {}
    start = time.monotonic()
    for case_index, (measure, fi, mechanism, transfer, defect) in enumerate(cases):
        branch_start = time.monotonic()
        nominal = frozen['fits'][fi]
        label = '/'.join((measure, nominal['model_version'], nominal['interpretation'], mechanism, transfer, defect))
        reps, fine_checks, evidence = [], [], {}
        for repeat in range(repeats):
            # Stable factorial identity: selecting debug branches never changes seeds.
            identity = [seed+repeat, 0 if measure == 'stress' else 1, fi, BRANCHES.index(mechanism),
                        settings['transfer_branches'].index(transfer), settings['water_branches'].index(defect)]
            ss = int(np.random.SeedSequence(identity).generate_state(1)[0])
            p = parameter_draws(scenario, settings, sourced, count, ss, mechanism, nominal, measure)
            fit, carrier, water, indices = sampled_calibration(frozen, fi, defect, count, ss)
            if measure == 'analog':
                water['equivalent_volume_cm3_g'] = p['analog_V_p0']
            p['n_N'] = np.maximum(p['n_N'], fit['n_N']*fit['models']['M1']['parameters']['A0'])
            p = feasible_parameters(p, water, nominal['model_version'])
            _, _, values = screen_cell(fit, carrier, water, p, nominal['model_version'], transfer, mechanism, grid,
                                       include_grid=True, include_correlations=False)
            reps.append(values)
            subset = min(64, count)
            def cut(node):
                if isinstance(node, dict): return {k: cut(v) for k, v in node.items()}
                if isinstance(node, np.ndarray): return node[:subset]
                return node
            _, _, refined = screen_cell(cut(fit), cut(carrier), cut(water), cut(p), nominal['model_version'], transfer, mechanism, fine,
                                        include_grid=True, include_correlations=False)
            fine_checks.append(dict(w_star_max_change=max(float(np.max(abs(values[k][:subset, 4:6]-refined[k][:, 4:6]))) for k in CONDITIONS),
                                    delta_max_change=max(float(np.max(abs(values[k][:subset, 6]-refined[k][:, 6]))) for k in CONDITIONS)))
            evidence[f'{repeat}/calibration_indices'] = indices
            evidence[f'{repeat}/parameter_names'] = np.array(sorted(p))
            evidence[f'{repeat}/parameters'] = np.column_stack([p[k] for k in sorted(p)])
            for k, v in values.items(): evidence[f'{repeat}/{k}'] = v
        pooled = {k: np.concatenate([r[k] for r in reps]) for k in reps[0]}
        summary = summarize(pooled)
        result['branches'][label] = dict(summary=summary, convergence=convergence(reps, pooled, fine_checks),
                                         analysis_role='nominal_H1_H1a', fixed_controls=result['fixed_controls'],
                                         attempted=count*repeats, accepted=count*repeats, rejected=0,
                                         verdict='данных недостаточно', provisional_inputs=bool(frozen['include_provisional']))
        result['branch_compute_seconds'][label] = time.monotonic()-branch_start
        destination = folder/label; destination.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(destination/'samples.npz', grid=grid, **evidence)
        relative = (destination/'samples.npz').relative_to(root).as_posix()
        checksums.append(f'{sha256(destination/"samples.npz")}  {relative}')
        (destination/'summary.json').write_text(json.dumps(dict(run_id=run_id, branch=label, **result['branches'][label]), indent=2, allow_nan=False)+'\n')
        if plots:
            plot_maps(pooled, grid, destination/'map.png', label, run_id,
                      status=result['status'], provisional=frozen['include_provisional'])
        for artifact in (destination/'summary.json', destination/'map.png'):
            if artifact.is_file():
                result['artifact_hashes'][artifact.relative_to(root).as_posix()] = sha256(artifact)
        print(f'ensemble {case_index+1}/{len(cases)} {label}', flush=True)
    result['elapsed_seconds'] = time.monotonic()-start
    result['branch_count'] = len(cases)
    result['full_estimate_seconds_linear'] = result['elapsed_seconds']*360/len(cases)*4096/count*4/repeats
    result['raw_bytes'] = sum(p.stat().st_size for p in folder.rglob('samples.npz'))
    (folder/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (folder/'SHA256SUMS.large').write_text('\n'.join(checksums)+'\n')
    return result


def plot_maps(raw, grid, path, label, run_id, *, status, provisional):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for model, row in zip(('M1', 'B1'), axes):
        for ax, reg in zip(row, ('R1', 'R2')):
            curves = []
            for rh in (0, 40, 70):
                key = f'{reg}_RH{rh}'
                if model == 'M1':
                    values = raw[key+'/grid']
                else:
                    b = raw[key+'/B1']
                    values = b[:, 0, None]*(1-grid[None, :]/.3)+b[:, -1, None]*(grid[None, :]/.3)
                curves.append(np.median(values, axis=0))
            mesh = ax.pcolormesh(grid, [0, 40, 70], curves, shading='nearest', cmap='viridis')
            fig.colorbar(mesh, ax=ax, label='median q_work, mmol/g dry composite')
            ax.set(xlabel='PEI mass fraction', ylabel='RH (%)', title=model+' '+reg)
            ax.set(xlim=(0, .3), ylim=(0, 70), xticks=[0, .1, .2, .3], yticks=[0, 40, 70])
    input_status = 'provisional sensitivity' if provisional else 'verified C calibration'
    fig.suptitle(f'{label}\n{run_id}; {status.upper()} / {input_status}; C: S100/S105/S106; RH grid 0/40/70 only', fontsize=8)
    fig.savefig(path, dpi=130); plt.close(fig)
