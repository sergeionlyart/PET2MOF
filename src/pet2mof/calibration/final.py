"""C-only deterministic joint calibration, with correlated extraction-error refits.

No holdout paths are enumerated. Parametric draws perturb entire isotherms with
their fixed covariance (including shared offsets); they are not a point bootstrap.
Experimental errors and between-article variability remain unidentified.
"""
import copy
import hashlib
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares

from pet2mof.data.c_series import load_series
from pet2mof.model.config import load_config
from pet2mof.model.gas import p_sat, R
from pet2mof.model.revision import VERSIONS, dry_prediction
from .fit import loading
from .revision import covariance_csv, complete_metrics


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen_inputs(root, frozen):
    root = Path(root).resolve()
    for item in frozen['inputs']:
        path = (root/item['input_path']).resolve()
        path.relative_to(root/'data/processed/c_series')
        if sha256(path) != item['input_sha256']:
            raise ValueError('C calibration input changed')
    for field in ('config_hashes', 'document_hashes'):
        for name, digest in frozen.get(field, {}).items():
            path = (root/name).resolve(); path.relative_to(root)
            if sha256(path) != digest:
                raise ValueError('frozen configuration/document changed: '+name)


def selected_c(root, include_provisional=False):
    """Candidates may be verified; never promote a CSV's status by its role."""
    f = load_series(root, sources=('S100', 'S105', 'S106'), debug=True)
    selected = f.status.eq('verified')
    if include_provisional:
        # NIST-only S100 additions have unknown extraction bounds. Including
        # provisional never licenses inventing their error bars or using zero.
        errors_known = np.isfinite(f.q_err_mmol_g) & np.isfinite(f.p_err_bar) & (f.q_err_mmol_g > 0) & (f.p_err_bar >= 0)
        selected |= f.status.eq('provisional') & errors_known
    omitted = f.loc[~selected, ['series_id', 'status']].value_counts().reset_index(name='rows')
    f = f.loc[selected].reset_index(drop=True)
    return f, omitted.to_dict('records')


def _problem(frame, predict, starts, bounds, shared):
    frame = frame.reset_index(drop=True)
    C = covariance_csv(frame, shared)
    L = cholesky(C, lower=True)
    return dict(frame=frame, predict=predict, starts=starts, bounds=bounds, C=C, L=L)


def _fit(problem, rng=None, start=None):
    f, L = problem['frame'], problem['L']
    q = f.q_mmol_g.to_numpy().copy()
    if rng is not None:
        q += L @ rng.standard_normal(len(q))
    fun = lambda x: solve_triangular(L, problem['predict'](x)-q, lower=True)
    starts = problem['starts'] if start is None else [start]
    fits = [least_squares(fun, s, bounds=problem['bounds'], max_nfev=2000,
                         xtol=1e-9, ftol=1e-9, gtol=1e-9) for s in starts]
    good = [v for v in fits if v.success and np.isfinite(v.fun).all()]
    if not good:
        raise RuntimeError('calibration optimizer failed; no draw silently removed')
    v = min(good, key=lambda x: x.fun @ x.fun)
    return v.x, dict(chi2=float(v.fun @ v.fun), optimizer_success=True,
                    metrics=complete_metrics(f, problem['predict'](v.x), problem['C'],
                        inputs_note='experimental uncertainty unknown; C fit is not independent validation; PEI loading/basis unresolved where applicable'))


def calibrate(root, *, include_provisional=False, draws=64, seed=18018):
    if draws < 8:
        raise ValueError('at least 8 calibration draws required (64 default)')
    root = Path(root)
    frame, omitted = selected_c(root, include_provisional)
    settings = load_config(root/'configs/calibration.yaml')['calibration']
    revision = load_config(root/'configs/revision.yaml')
    shared = revision['covariance_shared_fraction']
    inputs = frame[['input_path', 'input_sha256', 'source_id', 'extraction_id', 'status']].drop_duplicates().to_dict('records')
    problems = {}
    for (source, material, gas), f in frame.groupby(['source_id', 'material', 'gas'], sort=True):
        if source == 'S100':
            continue
        p, T = f.p_bar.to_numpy(), f.T_K.to_numpy()
        if source == 'S105':
            multi = len(np.unique(T)) > 1
            def predict(x, p=p, T=T, multi=multi):
                b = x[1]*np.exp((x[2] if multi else 0.)/R*(1/T-1/298.))
                return x[0]*b*p/(1+b*p)
            bounds = ([.001, .00001, 0.], [100., 1000., 100000.]) if multi else ([.001, .00001], [100., 1000.])
            starts = [[5., .5, 20000.], [20., .05, 10000.]] if multi else [[1., .1], [5., .01]]
        else:
            a = p/p_sat(float(T[0]))
            def predict(x, a=a):
                return x[0]*a**x[2]/(x[1]**x[2]+a**x[2])
            bounds, starts = ([.001, .001, 1.], [100., 2., 30.]), [[20., .3, 4.], [25., .5, 8.]]
        problems[(source, material, gas)] = _problem(f, predict, starts, bounds, shared)
    host = frame[(frame.source_id == 'S100') & (frame.material == 'UiO-66')]
    hp = host.p_bar.to_numpy()
    host_predict = lambda x: x[0]*x[1]*hp/(1+x[1]*hp)
    host_problem = _problem(host, host_predict, settings['host_starts'], tuple(np.array(settings['host_bounds']).T), shared)
    host_best, host_diag = _fit(host_problem)
    best = {k: _fit(v) for k, v in problems.items()}

    def carrier_record(key, x):
        source, material, gas = key
        if source == 'S105':
            return dict(source_id=source, material=material, gas=gas, q_sat=float(x[0]), b=float(x[1]),
                        Q=float(x[2]) if len(x) == 3 else None, T_ref=298.)
        return dict(source_id=source, material=material, gas=gas, q_max=float(x[0]), a_s=float(x[1]), m=float(x[2]),
                    T_ref=float(problems[key]['frame'].T_K.iloc[0]), Q=None, equivalent_volume_cm3_g=float(x[0])*.01801528)

    def c_records(values):
        records = {}
        for k, v in values.items():
            records[k] = carrier_record(k, v)
            records[k]['extraction_ids'] = sorted(problems[k]['frame'].extraction_id.unique().tolist())
            records[k]['calibration_temperatures_K'] = sorted(problems[k]['frame'].T_K.unique().tolist())
        return dict(carriers=[r for k, r in records.items() if k[0] == 'S105'],
                    water=[r for k, r in records.items() if k[0] == 'S106'])

    pei_problems, fits = {}, []
    for version in VERSIONS:
        for interpretation in ('composite', 'ratio'):
            f = frame[(frame.source_id == 'S100') & (frame.material != 'UiO-66')].copy().reset_index(drop=True)
            f['w'] = [loading(v, interpretation) for v in f.material]
            p, w = f.p_bar.to_numpy(), f.w.to_numpy()
            record = dict(model_version=version, interpretation=interpretation, n_N=settings['n_N'], T_fit=298.,
                          source_id='S100', extraction_id='T006-S100-FigS5',
                          host=dict(q_sat=float(host_best[0]), b=float(host_best[1])), models={})
            for model in ('M1', 'B1'):
                baseline = model == 'B1'
                columns = ['eta0', 'K_d'] if baseline else ['A0', 'lam', 'K_d', 'kappa']
                bounds, starts = np.array(settings[model+'_bounds']).T.copy(), np.array(settings[model+'_starts']).copy()
                if not baseline:
                    if version == 'v1.1-connectivity':
                        bs = revision['branches'][version]
                        bounds[:, 3] = bs['kappa_bounds']
                        bounds = np.column_stack([bounds, bs['power_bounds']])
                        starts[:, 3] = [2., 3., 4.]
                        starts = np.column_stack([starts, [2., 4., 8.]])
                        columns += ['power']
                    else:
                        bounds[1, 3] = min(bounds[1, 3], float(np.min((1-w)/w)))
                def predictor(h, version=version, baseline=baseline, p=p, w=w):
                    return lambda x: dry_prediction(p, w, h[0]*h[1]*p/(1+h[1]*p), settings['n_N'], x, version, baseline)
                pr = _problem(f, predictor(host_best), starts, tuple(bounds), shared)
                x, diag = _fit(pr)
                record['models'][model] = dict(parameters=dict(zip(columns, x.tolist())), **diag)
                pei_problems[(version, interpretation, model)] = (pr, predictor, x, columns)
            fits.append(record)

    # Common perturbation of each entire C input across all structural/readout
    # alternatives; one joint draw includes host, PEI, carrier and water refits.
    rng = np.random.default_rng(seed)
    joint = []
    for _ in range(draws):
        h, _ = _fit(host_problem, rng, host_best)
        c = c_records({k: _fit(pr, rng, best[k][0])[0] for k, pr in problems.items()})
        sample_fits = copy.deepcopy(fits)
        state = copy.deepcopy(rng.bit_generator.state)
        next_state = None
        for rec in sample_fits:
            rec['host'] = dict(q_sat=float(h[0]), b=float(h[1]))
            # Same error realization for PEI in every structural/readout fit.
            for model in ('M1', 'B1'):
                rng.bit_generator.state = copy.deepcopy(state)
                pr, predictor, x, columns = pei_problems[(rec['model_version'], rec['interpretation'], model)]
                pr = dict(pr, predict=predictor(h))
                y, _ = _fit(pr, rng, x)
                next_state = copy.deepcopy(rng.bit_generator.state)
                rec['models'][model] = dict(parameters=dict(zip(columns, y.tolist())))
        rng.bit_generator.state = next_state
        joint.append(dict(fits=sample_fits, c_fits=c))
    c_fits = c_records({k: v[0] for k, v in best.items()})
    for section in ('carriers', 'water'):
        for rec in c_fits[section]:
            rec.update(best[(rec['source_id'], rec['material'], rec['gas'])][1])
    missing = []
    for material in ('UiO-66', 'UiO-66-NH2'):
        for gas in ('CO2', 'N2'):
            if not any(r['material'] == material and r['gas'] == gas for r in c_fits['carriers']):
                missing.append(f'S105/{material}/{gas}')
    for material in ('UiO-66_100', 'UiO-66_160', 'UiO-66_220'):
        if not any(r['material'] == material for r in c_fits['water']):
            missing.append(f'S106/{material}')
    return dict(schema_version='T018-v1', status='provisional_sensitivity' if include_provisional else 'freeze_candidate',
                include_provisional=include_provisional, seed=seed, calibration_draws=draws,
                parameter_units=dict(q_sat='mmol/g dry carrier', q_max='mmol H2O/g dry carrier', b='bar^-1', Q='J/mol',
                                     a_s='1', m='1', n_N='mmol N/g PEI', A0='1', lam='1', K_d='bar^-1',
                                     kappa='1', power='1', eta0='1', equivalent_volume_cm3_g='cm3/g dry carrier'),
                inputs=inputs, omitted=omitted, missing=missing,
                config_hashes={s: sha256(root/s) for s in ('configs/calibration.yaml', 'configs/revision.yaml', 'configs/scenarios.yaml', 'configs/sourced_ranges.yaml')},
                document_hashes={s: sha256(root/s) for s in ('docs/validation_protocol.md', 'docs/hypotheses.md', 'docs/decisions.md')},
                uncertainty_method='joint parametric correlated extraction-error refits; equal-weight draws; 2.5/97.5 percentiles; covariance fixed from C CSV bounds/sqrt(3), half variance shared by whole isotherm',
                limitations=['not a bootstrap of adjacent points; no inter-article uncertainty inferred from one article',
                             'experimental errors unknown; intervals conditional on extraction errors and model structure',
                             'S100 nominal loading/basis unresolved; no structure passed all C criteria (D-17)',
                             'N2 Q, water Q, chemical Q and kinetics unknown; no single-temperature Q fit',
                             'freeze_candidate is not a prereg-v1 tag or independent verification'],
                host_diagnostics=host_diag, fits=fits, c_fits=c_fits, joint_draws=joint)
