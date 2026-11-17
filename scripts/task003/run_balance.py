#!/usr/bin/env python3
"""TASK-003 tables and figures. Local inputs only; no model fitting."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from pet2mof.task003 import balance as b
from pet2mof.task003.interpolation import interpolate, coordinate_corner_envelope

ROOT = Path(__file__).resolve().parents[2]
PACK = Path('data/task002/PET2MOF_Task002_DataPack_v1.0')
OUT = Path('reports/task003')
S2_MATERIALS = PACK / 'data/primary/S2_materials.csv'
S2_DRY = PACK / 'data/primary/S2_dry_CO2.csv'
S100 = PACK / 'data/benchmark/S100_dry_isotherms.csv'
PLAN = Path('docs/task003/analysis_plan.md')
P_BAR = .896
CEILINGS = (b.ETA_CEILING, b.ETA_CEILING_LOW)


def load(path):
    with (ROOT / path).open(newline='', encoding='utf-8') as file:
        return list(csv.DictReader(file))


def save(path, rows):
    rows = iter(rows)
    first = next(rows)
    with (ROOT / path).open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(first), lineterminator='\n')
        writer.writeheader()
        for row in itertools.chain((first,), rows):
            writer.writerow({key: ('' if value is None else value) for key, value in row.items()})


def dump(path, obj):
    (ROOT / path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def scalar(value):
    return value if value is not None and math.isfinite(value) else None


def get(rows, sample, quantity, locator):
    found = [r for r in rows if r['sample_label'] == sample and r['quantity'] == quantity and r['locator'] == locator]
    if len(found) != 1:
        raise ValueError(f'expected unique cell: {sample}, {quantity}, {locator}')
    return float(found[0]['value'])


def check_bounds():
    rows = {r['bound_id']: r for r in load('data/task003/eta_bounds.csv')}
    for key, value in [('T041-ETA-01', .5), ('T041-HP-etaapp', .3747), ('T041-N-03', 30.74)]:
        if float(rows[key]['value_or_range']) != value:
            raise ValueError('registered T041 bounds changed')


def ga_source():
    # Lead edit (T042 acceptance): the GA recipe (S2 §4.1 GA 50 %; §4.3 0.6007 g solution per 0.78 g MOF; §4.4 I96
    # without GA) was checked by T041 and by T042 against the open JATS on 2026-11-17. The JATS is not redistributed,
    # so the pipeline no longer reads it: outputs must not depend on an ignored local file.
    return 'S2 §§4.1,4.3 (I96: §4.4 no GA); checked against open JATS by T041/T042 on 2026-11-17', None


def records():
    material = load(S2_MATERIALS)
    dry = {r['sample_id']: float(r['q_CO2_dry_mmol_g']) for r in load(S2_DRY)}
    q0 = dry['S2-BASE']
    result = []
    for r in material:
        for branch in ('s-I', 's-V'):
            c = b.s2_composition(float(r['mass_gain_pct_of_initial_MOF']) / 100,
                                 float(r['PEI_content_author_calculated_wt_pct']) / 100, branch)
            result.append(dict(sample=r['sample_id'], series='S2', branch=branch, basis='composite_after_outgassing',
                c=c, q=dry[r['sample_id']], q0=q0, raw=r, extraction_id='T041-BAL;T041-S2;TASK002-S2-Tables1-2',
                source_locator='S2 Tables 1–2; §§2.1,4.6', q_basis_note='q unchanged between s-I/s-V; dry composite per plan'))
    points = load(S100)
    if any(float(r['q_digitization_halfwidth']) != .105 or float(r['p_digitization_halfwidth_bar']) != .042
           or float(r['T_K']) != 298 or r['gas'] != 'CO2' for r in points):
        raise ValueError('S100 conditions or registered coordinate halfwidths changed')
    curves, envelopes = {}, []
    for sample in sorted({r['sample_label'] for r in points}):
        rr = sorted((r for r in points if r['sample_label'] == sample), key=lambda r: float(r['p_bar']))
        p = [float(r['p_bar']) for r in rr]
        q = [float(r['q_mmol_per_g_reported']) for r in rr]
        curves[sample] = interpolate(p, q, P_BAR)
        envelope = coordinate_corner_envelope(p, q, P_BAR)
        envelopes.append(dict(sample=sample, p_bar=P_BAR, nominal_q_reported_mmol_g=curves[sample],
            **envelope, full_envelope_reason='endpoint pressure corners lack support; extrapolation forbidden' if envelope['outside_support_vertices'] else '',
            unordered_vertex_note='nonmonotone pressure tuples excluded from the ordered-curve domain' if envelope['unordered_vertices'] else '',
            extraction_id='T006-S100-FigS5', source_locator='S100 SI Fig. S5; TASK002 coordinate halfwidths'))
    for sample, q in curves.items():
        loading = 0 if sample == 'UiO-66' else float(sample.split('PEI')[0])
        for branch, basis in itertools.product(('w-C', 'w-F'), ('b-C', 'b-M')):
            c = b.s100_composition(loading, branch)
            result.append(dict(sample=sample, series='S100', branch=branch, basis=basis, c=c,
                q=b.s100_q_composite(q, c, basis), q0=curves['UiO-66'], raw={'loading': loading},
                extraction_id='T006-S100-FigS5;T040-S100-methods', source_locator='S100 SI Fig. S5; T040 methods unknown basis',
                q_basis_note='conditional basis reading; PEI retention assumed equal to loading label'))
    return result, envelopes


def identity(r, run_id):
    ga_ok = None
    if r['series']=='S2':
        raw=r['raw']
        original=b.s2_composition(float(raw['mass_gain_pct_of_initial_MOF'])/100,
                                  float(raw['PEI_content_author_calculated_wt_pct'])/100,'s-I')
        ga=0. if r['sample'] in ('S2-BASE','S2-I96') else b.GA_FEED_G_G_MOF
        ga_ok=original.s/original.h <= ga+1e-12
    return dict(run_id=run_id, sample_id=r['sample'], series=r['series'], composition_branch=r['branch'],
                mass_basis_branch=r['basis'], original_sI_GA_consistent=ga_ok)


def s2_formula_rows(recs, run_id):
    rows = []
    for r in recs:
        if r['series'] != 'S2' or r['branch'] != 's-I':
            continue
        raw = r['raw']
        W, N = float(raw['mass_gain_pct_of_initial_MOF']) / 100, float(raw['N_elemental_wt_pct']) / 100
        tab = float(raw['PEI_content_author_calculated_wt_pct']) / 100
        calc = b.s2_pei_mass_fraction(W, N, .05)
        vertices = [b.s2_pei_mass_fraction(W+dW, N+dN, .05+dN0)
                    for dW,dN,dN0 in itertools.product((-.005,.005),(-.0005,.0005),(-.0005,.0005))
                    if W+dW >= 0]
        if r['sample']=='S2-BASE':
            # The blank N and N0 are the same measurement, not two errors.
            vertices=[0.]
        rows.append(dict(**identity(r, run_id), W_g_g_mof=W, N_mass_fraction=N, N_base_mass_fraction=.05,
            pei_table_mass_fraction=tab, pei_reconstructed_mass_fraction=calc, delta_percentage_points=100*(calc-tab),
            reconstruction_rounding_low=min(vertices), reconstruction_rounding_high=max(vertices),
            table_interval_intersects_reconstruction=max(tab-.0005,min(vertices)) <= min(tab+.0005,max(vertices)),
            reconstructed_N_from_table_mass_fraction=r['c'].h * .05 + r['c'].w * .3074,
            evidence_class='derived', extraction_id=r['extraction_id'], source_locator='S2 Table 1; unnumbered PEI_exp equation §2.1'))
    return rows


def structure_scenarios(r, src6, src3):
    # Actual analog is not PET-derived. Formula is an ideal inventory proxy.
    yield dict(name='actual_analog_ideal_proxy', route='analog', f=1. if r['series'] == 'S2' else 0., L=6.,
               pet=False, conversion=None, kind='derived', loc='plan §3A ideal Zr6O4(OH)4L6', eid='TASK003-plan-3A', defect=False)
    for label in ('PET-UiO-66', 'PET-UiO-66-NH2-25%', 'PET-UiO-66-NH2-50%', 'PET-UiO-66-NH2-75%', 'PET-UiO-66-NH2-100%'):
        f = get(src6, label, 'BDC-NH2 fraction by NMR', 'Table S3') / 100
        x = get(src6, label, 'x', 'Table 4')
        conversion = get(src6, label, 'MOF conversion', 'Table S2') / 100
        for defect in (False, True):
            yield dict(name=label + ('_defect_skeleton_upper_bound' if defect else '_ideal'),
                route='R1' if f == 0 else 'R2' if f < 1 else 'NH2_control_zero_PET',
                f=f, L=6-x if defect else 6., pet=True, conversion=conversion, kind='scenario',
                loc='SRC06 Tables S1–S3, Table 4; missing caps unknown', eid='T040-SRC06-tables', defect=defect)
    # S4 describes coordination 8.8 versus 12, not unique linkers. Use only as conditional ratio.
    coord = get(src3, 'PET-derived UiO-66', 'BDC/Zr6 coordination reported', 'S4')
    reference = get(src3, 'PET-derived UiO-66', 'comparison coordination', 'S4')
    yield dict(name='SRC03_defect_skeleton_upper_bound', route='R1', f=0., L=6*coord/reference,
        pet=True, conversion=None, kind='scenario', loc='SRC03 S4 coordination ratio; caps and sample identity unknown',
        eid='T040-SRC03-tables;T040L-SRC03-S4', defect=True)


def material_rows(recs, run_id, ga_note):
    src6, src3 = load('data/task003/extracted/SRC06_tables.csv'), load('data/task003/extracted/SRC03_tables.csv')
    src03_s4 = load('data/task003/extracted/SRC03_S4_lead_supplement.csv')
    tga_bdc_fraction = get(src03_s4, 'PET-derived UiO-66 (sample not named in S4)',
        'weight loss of coordinated BDC2-', 'SI section S4 (formula line)') / 100
    recovery_ratios = [get(src6, label, 'BDC yield', 'Table S1') / get(src6, label, 'PET mass', 'Table S1') for label in ('#1', '#2', '#3')]
    for r in recs:
        # S100 capacity-basis branches share one composition.
        if r['series'] == 'S100' and r['basis'] != 'b-C':
            continue
        c, raw = r['c'], r['raw']
        if r['series'] == 'S2':
            feed = float(raw['PEI_feed_pct_of_initial_MOF']) / 100 * 1000 * c.h
            ga = 0. if r['sample'] in ('S2-BASE', 'S2-I96') else b.GA_FEED_G_G_MOF * 1000 * c.h
            original = b.s2_composition(float(raw['mass_gain_pct_of_initial_MOF']) / 100,
                                       float(raw['PEI_content_author_calculated_wt_pct']) / 100, 's-I')
            residue_per_mof = original.s / original.h
            compatible = residue_per_mof <= ga / (1000*c.h) + 1e-12
            feed_note = 'Table 1 nominal feed; I96 method 0.716/0.78 differs from nominal 0.96' if r['sample'] == 'S2-I96' else 'S2 Table 1 nominal feed'
        else:
            # Neither actual feed nor independently measured retention is known for S100.
            feed, ga, residue_per_mof, compatible = None, 0., 0., True
            feed_note = 'actual PEI feed/retention unknown; loading label interpreted by w-C/w-F'
        for st in structure_scenarios(r, src6, src3):
            inv = b.linker_inventory(c, st['f'], st['L'])
            if not st['pet']:
                inv['pet_linker_mole_fraction'] = 0.
                inv['pet_fragment_mass_fraction'] = 0.
                inv['pet_theoretical_g_kg_composite'] = 0.
            acid = inv['bdc_acid_equivalent_g_kg_composite'] if st['pet'] else 0.
            conv = st['conversion']
            # Recovery is g BDC / g PET, not a molar yield: do not apply 166.13/192.17 twice.
            low = acid / max(recovery_ratios) / conv if conv else None
            high = acid / min(recovery_ratios) / conv if conv else None
            actual_N_host = c.h * .05 * 1000/b.M_N_G_MOL if r['series'] == 'S2' else 0.
            yield dict(**identity(r, run_id), structure_scenario=st['name'], route=st['route'], evidence_class=st['kind'],
                h_g_mof_g_composite=c.h, w_g_pei_g_composite=c.w, s_g_residue_g_composite=c.s, fraction_sum=c.h+c.w+c.s,
                mof_g_kg_composite=1000*c.h, pei_feed_g_kg_composite=feed, pei_retained_g_kg_composite=1000*c.w,
                pei_feed_note=feed_note, ga_feed_pure_g_kg_composite=ga, ga_recipe_source=ga_note,
                residue_g_kg_composite=1000*c.s, original_residue_g_g_mof=residue_per_mof,
                sI_ga_feed_consistent=compatible, sI_ga_check_applies=r['branch']=='s-I',
                n_pei_mmol_g_composite=c.w*b.N_NOMINAL_MMOL_G_PEI,
                n_actual_analog_host_mmol_g_composite=actual_N_host,
                nitrogen_note='PEI N excludes all linker N; proxy linker N separate from actual elemental N',
                nh2_linker_mole_fraction=st['f'], unique_linkers_per_zr6=st['L'], **inv,
                cap_mass_status='unknown; positive cap mass lowers all skeleton inventories' if st['defect'] else 'ideal formula assumption',
                src06_mof_conversion=conv, pet_src06_scenario_low_g_kg_composite=low, pet_src06_scenario_high_g_kg_composite=high,
                pet_scenario_note='transfer of gram recovery and reported MOF conversion; no proof of linker-specific yield' if conv else 'unknown MOF conversion; no yield-adjusted PET estimate',
                src03_tga_bdc_mass_g_kg_composite=1000*c.h*tga_bdc_fraction if st['name'].startswith('SRC03') else None,
                src03_tga_note='conditional: S4 39.75% loss attributed to BDC; dry reference and caps unknown; not equated to skeleton' if st['name'].startswith('SRC03') else '',
                extraction_id=r['extraction_id']+';'+st['eid'], source_locator=r['source_locator']+';'+st['loc'], input_status='provisional')


def analog_rows(recs, run_id):
    for r in recs:
        for ceiling in CEILINGS:
            c = r['c']
            interval = b.analog_interval(c, r['q'], r['q0'], b.N_NOMINAL_MMOL_G_PEI, ceiling)
            yield dict(**identity(r, run_id), eta_ceiling=ceiling, h=c.h, w=c.w, s=c.s,
                q_composite_mmol_g=r['q'], q_host_mmol_g_mof=r['q0'], gain_analog=r['q']/r['q0'],
                n_n_mmol_g_pei=b.N_NOMINAL_MMOL_G_PEI, eta_phi0=interval.eta_at_phi0, eta_phi1=interval.eta_at_phi1,
                eta_per_primary_secondary_N=None,
                primary_secondary_normalization_reason='unknown secondary/tertiary N split; T041-N-06',
                admissible_phi_low=interval.phi_low, admissible_phi_high=interval.phi_high,
                line_status=interval.status, entirely_above_ceiling=interval.status=='entirely_above_ceiling',
                q_basis_note=r['q_basis_note'], evidence_class='derived', extraction_id=r['extraction_id'], source_locator=r['source_locator'])


def design_rows(recs, run_id):
    s_c72 = next(r['c'].s for r in recs if r['sample']=='S2-C72' and r['branch']=='s-I')
    hosts = [('S2_BASE', next(r['q0'] for r in recs if r['series']=='S2'), 'measured_analog', 'T041-S2;TASK002-S2-Table2'),
             ('S100_UiO66', next(r['q0'] for r in recs if r['series']=='S100'), 'measured_analog', 'T006-S100-FigS5'),
             ('PET_R0_or_M', None, 'unknown_PET', 'TASK003-plan-2.4')]
    for (host,q0,origin,eid), s, g, wi, pi in itertools.product(hosts, (0.,s_c72), (1.,1.1), range(51), range(101)):
        w, phi = wi/100, pi/100
        c = b.Composition(1-w-s, w, s)
        normalized = (g-c.h*phi)/w if w else None
        eta = b.eta_min(c, phi, q0, b.N_NOMINAL_MMOL_G_PEI, g*q0) if q0 else None
        host_only_meets = c.h*phi >= g if not w else None
        yield dict(run_id=run_id, host=host, q_host_origin=origin, q_host_mmol_g_mof=q0, q_host_status='known_analog' if q0 else 'unknown',
            g=g, h=c.h, w=w, s=s, phi=phi, eta_min_normalized=normalized,
            eta_min_mol_co2_mol_n=eta, n_n_mmol_g_pei=b.N_NOMINAL_MMOL_G_PEI,
            class_nominal=b.classify_eta(eta) if q0 else ('host_only' if not w else 'unknown'),
            class_low_ceiling=b.classify_eta(eta,b.ETA_CEILING_LOW) if q0 else ('host_only' if not w else 'unknown'),
            eta_lit=b.ETA_LIT, eta_ceiling=b.ETA_CEILING, eta_ceiling_low=b.ETA_CEILING_LOW,
            phi_crit_lit=b.phi_crit(c,g,q0,b.N_NOMINAL_MMOL_G_PEI,b.ETA_LIT) if q0 else None,
            phi_crit_ceiling=b.phi_crit(c,g,q0,b.N_NOMINAL_MMOL_G_PEI,b.ETA_CEILING) if q0 else None,
            phi_crit_low_ceiling=b.phi_crit(c,g,q0,b.N_NOMINAL_MMOL_G_PEI,b.ETA_CEILING_LOW) if q0 else None,
            host_only_gain=c.h*phi if not w else None, host_only_meets_target=host_only_meets,
            absolute_missing_reason='PET host capacity unknown; no analog capacity substituted' if not q0 else 'w=0: no PEI denominator' if not w else '',
            evidence_class='scenario', extraction_id=eid+';T041-HP-etaapp;T041-ETA-01;T041-N-05', source_locator='analysis_plan §§1,3B; P3-02')


def transfer_rows(recs, run_id):
    rows, summary = [], []
    for r, ceiling, g in itertools.product(recs, CEILINGS, (1.,1.1)):
        c, gain = r['c'], r['q']/r['q0']
        interval = b.analog_interval(c,r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI,ceiling)
        adm = b.kstar_admissible(c,gain,g,interval)
        all_phi = b.kstar_all(c,gain,g)
        common = dict(**identity(r,run_id), eta_ceiling=ceiling, g=g, gain_analog=gain,
            registered_kstar_G_over_g=gain/g, registered_domain_k_ge_1_feasible=gain>=g,
            kstar_all_phi_positive_k=scalar(all_phi), kstar_admissible=scalar(adm),
            kstar_admissible_unbounded=adm is not None and math.isinf(adm),
            admissible_phi_low=interval.phi_low, admissible_phi_high=interval.phi_high,
            line_status=interval.status,
            threshold_note='registered G/g guarantees all phi for k>=1 only if G>=g; full positive-k bound is separate',
            r_R2_min_at_k1_vs_R0=g/gain if r['series']=='S2' else None,
            evidence_class='scenario', extraction_id=r['extraction_id']+';TASK003-P3-01', source_locator='analysis_plan §3B, P3-01')
        points = [] if interval.phi_low is None else sorted(set([interval.phi_low,interval.phi_high]))
        for phi in points:
            eta = b.eta_min(c,phi,r['q0'],b.N_NOMINAL_MMOL_G_PEI,r['q'])
            kcrit = b.k_crit(c,phi,gain,g)
            rows.append(dict(**common, point_kind='ceiling_intersection' if eta is not None and abs(eta-ceiling)<1e-12 else 'zero_intersection' if eta is not None and abs(eta)<1e-12 else 'line_endpoint',
                phi=phi, eta_mol_co2_mol_n=eta, class_nominal=b.classify_eta(eta,ceiling), k_crit_phi=scalar(kcrit),
                k_crit_unbounded=math.isinf(kcrit),
                gain_pet_k08=b.gain_pet(c,phi,.8,gain), gain_pet_k15=b.gain_pet(c,phi,1.5,gain)))
        if not points:
            rows.append(dict(**common,point_kind='no_admissible_segment',phi=None,eta_mol_co2_mol_n=None,
                class_nominal=None,k_crit_phi=None,k_crit_unbounded=False,gain_pet_k08=None,gain_pet_k15=None))
        summary.append(common)
    return rows, summary


def branch_summary(summary, run_id):
    groups = {}
    for row in summary:
        key = tuple(row[k] for k in ('series','composition_branch','mass_basis_branch','eta_ceiling','g'))
        groups.setdefault(key,[]).append(row)
    result = []
    for key, rr in groups.items():
        # Controls have no PEI and do not establish a modification route window.
        modified = [r for r in rr if r['sample_id'] not in ('S2-BASE','UiO-66')]
        admissible = [r for r in modified if r['admissible_phi_low'] is not None]
        feasible = [r for r in admissible if r['registered_domain_k_ge_1_feasible']]
        values = [r['registered_kstar_G_over_g'] for r in admissible]
        adm_values = [r['kstar_admissible'] for r in admissible if r['kstar_admissible'] is not None]
        feasible_values = [r['registered_kstar_G_over_g'] for r in feasible]
        result.append(dict(run_id=run_id, **dict(zip(('series','composition_branch','mass_basis_branch','eta_ceiling','g'),key)),
            modified_count=len(modified), admissible_count=len(admissible), feasible_k_ge1_count=len(feasible),
            GA_inconsistent_sI_count=sum(r['original_sI_GA_consistent'] is False for r in modified) if key[1]=='s-I' else 0,
            kstar_registered_min=min(values) if values else None,kstar_registered_max=max(values) if values else None,
            kstar_registered_feasible_ge1_min=min(feasible_values) if feasible_values else None,
            kstar_registered_feasible_ge1_max=max(feasible_values) if feasible_values else None,
            kstar_admissible_min=min(adm_values) if adm_values else None,kstar_admissible_max=max(adm_values) if adm_values else None,
            evidence_class='scenario',extraction_id='TASK003-P3-01',source_locator='transfer_kstar.csv; controls excluded'))
    return result


def stress_metrics(c,q,q0,n,g):
    gain=q/q0
    interval=b.analog_interval(c,q,q0,n)
    return dict(eta_required_phi1=b.eta_min(c,1,q0,n,g*q0),
        eta_analog_phi0=b.eta_min(c,0,q0,n,q),eta_analog_phi1=b.eta_min(c,1,q0,n,q),
        registered_kstar=gain/g,kstar_all_positive=b.kstar_all(c,gain,g),
        kstar_admissible=scalar(b.kstar_admissible(c,gain,g,interval)))


def uncertainty_rows(recs,envelopes,run_id):
    env={r['sample']:r for r in envelopes}
    rows=[]
    for r,g in itertools.product(recs,(1.,1.1)):
        if not r['c'].w:
            continue
        c,n=r['c'],b.N_NOMINAL_MMOL_G_PEI
        # Systematic n_N range, individual per-series bounds, then joint vertices.
        if r['series']=='S2':
            raw=r['raw']
            W=float(raw['mass_gain_pct_of_initial_MOF'])/100
            wp=float(raw['PEI_content_author_calculated_wt_pct'])/100
            N=float(raw['N_elemental_wt_pct'])/100
            families={}
            families['individual_table_rounding']=[(b.s2_composition(W+dw,wp+dwp,r['branch']),r['q']+dq,r['q0'],n)
                for dw,dwp,dq in itertools.product((-.005,.005),(-.0005,.0005),(-.005,.005))]
            families['individual_N_balance_rounding']=[(b.s2_composition(W+dw,b.s2_pei_mass_fraction(W+dw,N+dn,.05),r['branch']),r['q']+dq,r['q0'],n)
                for dw,dn,dq in itertools.product((-.005,.005),(-.0005,.0005),(-.005,.005))]
            families['common_blank_q_rounding']=[(c,r['q'],r['q0']+d,n) for d in (-.005,.005)]
            families['common_blank_N_rounding']=[(b.s2_composition(W,b.s2_pei_mass_fraction(W,N,.05+d),r['branch']),r['q'],r['q0'],n)
                for d in (-.0005,.0005)]
            families['systematic_nN_fixed_table_w']=[(c,r['q'],r['q0'],nn) for nn in (n,b.N_UPPER_MMOL_G_PEI)]
            families['combined_table_rounding_nN']=[(cc,q,q0+dq0,nn) for cc,q,q0,_ in families['individual_table_rounding']
                for nn,dq0 in itertools.product((n,b.N_UPPER_MMOL_G_PEI),(-.005,.005))]
            # N(PEI) controls both inferred w and n_N: not independent.
            families['coupled_N_balance_and_nN']=[(b.s2_composition(W+dw,b.s2_pei_mass_fraction(W+dw,N+dn,.05+dn0,nn*b.M_N_G_MOL/1000),r['branch']),r['q']+dq,r['q0']+dq0,nn)
                for dw,dn,dn0,dq,dq0,nn in itertools.product((-.005,.005),(-.0005,.0005),(-.0005,.0005),(-.005,.005),(-.005,.005),(n,b.N_UPPER_MMOL_G_PEI))]
            one_factor={
                'q_composite_rounding':[(c,r['q']+d,r['q0'],n) for d in (-.005,.005)],
                'q_host_rounding':[(c,r['q'],r['q0']+d,n) for d in (-.005,.005)],
                'W_rounding':[(b.s2_composition(W+d,wp,r['branch']),r['q'],r['q0'],n) for d in (-.005,.005)],
                'PEI_table_rounding':[(b.s2_composition(W,wp+d,r['branch']),r['q'],r['q0'],n) for d in (-.0005,.0005)],
                'N_composite_rounding':[(b.s2_composition(W,b.s2_pei_mass_fraction(W,N+d,.05),r['branch']),r['q'],r['q0'],n) for d in (-.0005,.0005)],
                'N_base_rounding':[(b.s2_composition(W,b.s2_pei_mass_fraction(W,N,.05+d),r['branch']),r['q'],r['q0'],n) for d in (-.0005,.0005)],
                'nN_convention':families['systematic_nN_fixed_table_w']}
            support_known=True
        else:
            e,e0=env[r['sample']],env['UiO-66']
            scale=c.h if r['basis']=='b-M' else 1.
            q_range=[e['q_low_supported_mmol_g']*scale,e['q_high_supported_mmol_g']*scale]
            q0_range=[e0['q_low_supported_mmol_g'],e0['q_high_supported_mmol_g']]
            families={
                'individual_coordinate_vertices_supported':[(c,q,r['q0'],n) for q in q_range],
                'common_blank_coordinate_vertices_supported':[(c,r['q'],q0,n) for q0 in q0_range],
                'systematic_nN':[(c,r['q'],r['q0'],nn) for nn in (n,b.N_UPPER_MMOL_G_PEI)],
                'combined_coordinates_nN_supported':[(c,q,q0,nn) for q,q0,nn in itertools.product(q_range,q0_range,(n,b.N_UPPER_MMOL_G_PEI))]}
            one_factor={
                'q_digitization_only':[(c,r['q']+d*scale,r['q0'],n) for d in (-.105,.105)],
                'host_q_digitization_only':[(c,r['q'],r['q0']+d,n) for d in (-.105,.105)],
                'p_sample_only_supported':[(c,q*scale,r['q0'],n) for q in
                    [e['q_low_supported_mmol_g']+.105,e['q_high_supported_mmol_g']-.105]],
                'p_host_only_supported':[(c,r['q'],q0,n) for q0 in
                    [e0['q_low_supported_mmol_g']+.105,e0['q_high_supported_mmol_g']-.105]],
                'nN_convention':families['systematic_nN']}
            support_known=e['full_envelope_known'] and e0['full_envelope_known']
        for family,vertices in itertools.chain(families.items(),(('one_factor:'+key,val) for key,val in one_factor.items())):
            metrics=[stress_metrics(*v,g) for v in vertices]
            for metric in metrics[0]:
                values=[m[metric] for m in metrics if m[metric] is not None]
                rows.append(dict(**identity(r,run_id),g=g,family=family,metric=metric,vertices=len(vertices),
                    low=min(values) if values else None,high=max(values) if values else None,
                    span=max(values)-min(values) if values else None,compatible_vertices=len(values),
                    full_envelope_known=support_known,
                    error_scope='one_factor' if family.startswith('one_factor:') else 'shared_blank' if family.startswith('common_blank') else 'individual_series' if family.startswith('individual') else 'shared_systematic' if family.startswith('systematic') else 'combined_with_shared_blank',
                    interval_note='deterministic bounds; S100 unsupported endpoint corners not extrapolated; branch alternatives separate',
                    evidence_class='scenario',extraction_id=r['extraction_id']+';T041-N-03;T041-N-07',source_locator='analysis_plan §3C'))
    # Discrete systematic branch choices reported as envelopes, not merged errors.
    for series in ('S2','S100'):
        samples=sorted({r['sample'] for r in recs if r['series']==series and r['c'].w})
        for sample,g in itertools.product(samples,(1.,1.1)):
            rr=[r for r in recs if r['series']==series and r['sample']==sample]
            metrics=[stress_metrics(r['c'],r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI,g) for r in rr]
            for metric in metrics[0]:
                vals=[m[metric] for m in metrics if m[metric] is not None]
                rows.append(dict(run_id=run_id,sample_id=sample,series=series,composition_branch='all_discrete',mass_basis_branch='all_discrete',g=g,
                    family='systematic_discrete_branches',metric=metric,vertices=len(rr),low=min(vals) if vals else None,high=max(vals) if vals else None,
                    span=max(vals)-min(vals) if vals else None,compatible_vertices=len(vals),full_envelope_known=True,error_scope='shared_systematic',
                    interval_note='discrete assumptions only; individual errors not included',evidence_class='scenario',extraction_id=rr[0]['extraction_id'],source_locator='analysis_plan §3C'))
    return rows


def route_windows(recs,run_id):
    rows=[]
    for r in recs:
        if not r['c'].w:
            continue
        c,gain=r['c'],r['q']/r['q0']
        for ceiling in CEILINGS:
            # Class B on a measured-q line additionally requires G>=1.10 at k=1.
            interval=b.analog_interval(c,r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI,min(b.ETA_LIT,ceiling))
            rows.append(dict(**identity(r,run_id),eta_ceiling=ceiling,g=1.1,gain_analog=gain,
                B_phi_low=interval.phi_low,B_phi_high=interval.phi_high,
                B_window_at_k1_g110=gain>=1.1 and interval.phi_low is not None,
                kstar_registered=gain/1.1, r_R2_min_vs_R0_at_k1=1.1/gain if r['series']=='S2' else None,
                chemical_condition='R2 only: own mixed-linker control and accessible NH2 required; C recipe not R1' if r['series']=='S2' and r['sample']!='S2-I96' else 'PEI impregnation scenario; S2 I96 host is NH2, not R1 measurement',
                evidence_class='scenario',extraction_id=r['extraction_id']+';T041-HP-etaapp',source_locator='analysis_plan §4; T041 route compatibility'))
    return rows


def transfer_envelope_rows(recs,run_id):
    for r,ceiling,ki in itertools.product(recs,CEILINGS,range(80,151)):
        c,gain,k=r['c'],r['q']/r['q0'],ki/100
        interval=b.analog_interval(c,r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI,ceiling)
        full=[b.gain_pet(c,p,k,gain) for p in (0.,1.)]
        adm=[] if interval.phi_low is None else [b.gain_pet(c,p,k,gain) for p in (interval.phi_low,interval.phi_high)]
        yield dict(**identity(r,run_id),eta_ceiling=ceiling,k=k,
            gain_all_phi_min=min(full),gain_all_phi_max=max(full),
            gain_admissible_phi_min=min(adm) if adm else None,gain_admissible_phi_max=max(adm) if adm else None,
            r_R2_min_g110_all_phi=1.1/min(full) if r['series']=='S2' and min(full)>0 else None,
            r_R2_min_g110_admissible=1.1/min(adm) if r['series']=='S2' and adm and min(adm)>0 else None,
            evidence_class='scenario',extraction_id=r['extraction_id']+';TASK003-P3-01',source_locator='analysis_plan §3B transfer equation; r*G_M>=g_R0')


def sensitivity_ranks(stress):
    groups={}
    for row in stress:
        if row['family'].startswith('one_factor:') and row['span'] is not None:
            key=tuple(row[k] for k in ('sample_id','composition_branch','mass_basis_branch','g','metric'))
            groups.setdefault(key,[]).append(row)
    for rr in groups.values():
        for rank,row in enumerate(sorted(rr,key=lambda r:(-r['span'],r['family'])),1):
            yield dict(**row,sensitivity_rank=rank)


def figures(recs,run_id):
    os.environ['MPLCONFIGDIR']=str(ROOT/'.uv-cache/task003-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    plt.rcParams.update({'font.size':8})
    s_c72=next(r['c'].s for r in recs if r['sample']=='S2-C72' and r['branch']=='s-I')
    colors=['#f7f7f7','#73c6a2','#f4d06f','#e78686']
    fig,axes=plt.subplots(2,2,figsize=(11,8),sharex=True,sharey=True)
    ww,pp=np.meshgrid(np.arange(1,51)/100,np.arange(101)/100)
    for ai,series in enumerate(('S2','S100')):
        q0=next(r['q0'] for r in recs if r['series']==series)
        for si,s in enumerate((0.,s_c72)):
            ax=axes[ai,si]
            eta=(1.1-(1-ww-s)*pp)*q0/(ww*b.N_NOMINAL_MMOL_G_PEI)
            classes=np.where(eta<=0,0,np.where(eta<=b.ETA_LIT,1,np.where(eta<=.5,2,3)))
            im=ax.pcolormesh(ww,pp,classes,cmap=ListedColormap(colors),norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5],4),shading='auto')
            for threshold,style in ((b.ETA_LIT,'-'),(.5,'--'),(.195,':')):
                w=np.arange(1,51)/100
                pc=(1.1-w*b.N_NOMINAL_MMOL_G_PEI*threshold/q0)/(1-w-s)
                ax.plot(w,pc,color='#333333',linestyle=style,lw=.8)
            for r in recs:
                if r['series']!=series or not r['c'].w:
                    continue
                iv=b.analog_interval(r['c'],r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI)
                if iv.phi_low is not None:
                    # w/phi projection; analog s differs from the background slice.
                    ax.plot([r['c'].w]*2,[iv.phi_low,iv.phi_high],lw=1,alpha=.7)
            ax.set(xlim=(0,.5),ylim=(0,1),title=f'{series} analog q_host={q0:.4f}; s={s:.6f}',xlabel='w, g PEI/g composite',ylabel='phi')
    fig.colorbar(im,ax=axes.ravel().tolist(),ticks=range(4),label='A / B / C / D (0 / 1 / 2 / 3)',fraction=.025,pad=.025)
    fig.suptitle('Conditional design window: g=1.10; n_N=21.946 mmol/g PEI')
    fig.text(.06,.015,f'{run_id}\nS2 Tables 1–2; S100 Fig. S5. Lines: eta_lit / ceiling / lower ceiling. Analog segments are w/phi projections.',fontsize=6)
    fig.savefig(ROOT/OUT/'design_window.png',dpi=140,metadata={'Software':'PET2MOF TASK003'})
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    k=np.linspace(.8,1.5,141)
    for ax,series in zip(axes,('S100','S2')):
        for r in recs:
            if r['series']!=series or not r['c'].w:
                continue
            iv=b.analog_interval(r['c'],r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI)
            if iv.phi_low is None:
                continue
            gain=r['q']/r['q0']
            lo=np.minimum([b.gain_pet(r['c'],0,x,gain) for x in k],[b.gain_pet(r['c'],1,x,gain) for x in k])
            hi=np.maximum([b.gain_pet(r['c'],0,x,gain) for x in k],[b.gain_pet(r['c'],1,x,gain) for x in k])
            line,=ax.plot(k,lo,lw=.8,label=f"{r['sample']} {r['branch']} {r['basis']}")
            ax.fill_between(k,lo,hi,color=line.get_color(),alpha=.04)
        ax.axhline(1.,color='black',lw=.8)
        ax.axhline(1.1,color='black',ls='--',lw=.8)
        ax.set(title=f'{series}: full phi [0,1] envelope',xlabel='k = q_host,PET / q_host,analog',ylabel='G_PET')
        ax.legend(fontsize=4.5,ncol=2)
    fig.suptitle('Transfer scenario; no measured PET CO2 capacity')
    fig.text(.06,.01,f'{run_id}\nS2 Tables 1–2; S100 Fig. S5; full-phi envelope includes algebraic extensions outside admissible segments.',fontsize=6)
    fig.tight_layout(rect=(0,.07,1,.95))
    fig.savefig(ROOT/OUT/'transfer_window.png',dpi=140,metadata={'Software':'PET2MOF TASK003'})
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,6.2),sharey=True)
    phi=np.linspace(0,1,101)
    for ax,series in zip(axes,('S2','S100')):
        for r in recs:
            if r['series']!=series or not r['c'].w:
                continue
            eta=[b.eta_min(r['c'],p,r['q0'],b.N_NOMINAL_MMOL_G_PEI,r['q']) for p in phi]
            ga_flag=' GA?' if r['branch']=='s-I' and identity(r,run_id)['original_sI_GA_consistent'] is False else ''
            line,=ax.plot(phi,eta,lw=.6,alpha=.7,label=f"{r['sample']} {r['branch']} {r['basis']}{ga_flag}")
            iv=b.analog_interval(r['c'],r['q'],r['q0'],b.N_NOMINAL_MMOL_G_PEI)
            if iv.phi_low is not None:
                endpoints=[iv.phi_low,iv.phi_high]
                ax.plot(endpoints,[b.eta_min(r['c'],p,r['q0'],b.N_NOMINAL_MMOL_G_PEI,r['q']) for p in endpoints],
                        color=line.get_color(),lw=2)
        for value,style in ((.5,'--'),(.3747,'-'),(.195,':')):
            ax.axhline(value,color='black',ls=style,lw=.8)
        ax.set(title=series,xlabel='phi',ylabel='eta, mol CO2 / mol PEI N',xlim=(0,1),ylim=(0,1.25))
        ax.legend(fontsize=5,ncol=2,loc='upper right')
    fig.suptitle('Algebraic analog lines; bold segment: 0 <= eta <= 0.5')
    fig.text(.06,.015,f'{run_id}\nS2 Tables 1–2; S100 Fig. S5. GA? = s-I residue exceeds pure GA feed. Host-only controls have no eta line.',fontsize=6)
    fig.tight_layout(rect=(0,.08,1,.95))
    fig.savefig(ROOT/OUT/'analog_lines.png',dpi=140,metadata={'Software':'PET2MOF TASK003'})
    plt.close(fig)


def material_notes(rows,run_id):
    special={
        'structure_scenario':'Формула/маршрут; actual_analog — без PET. Остальные строки — сценарный перенос состава, не образцы S2/S100 из PET.',
        'evidence_class':'Класс вычисленной строки: derived или scenario. Классы исходных ячеек сохранены в extracted CSV и input_evidence.csv.',
        'mass_basis_branch':'Для S100 материальный состав общий b-C/b-M; в этой таблице показан один раз как b-C.',
        'pei_feed_g_kg_composite':'Номинальная подача Table 1 S2 на 1 кг конечного состава; S100 unknown, пусто.',
        'pei_retained_g_kg_composite':'Удержание: S2 авторский PEI_exp; S100 условная трактовка метки загрузки, не измерение.',
        'n_actual_analog_host_mmol_g_composite':'N исходного носителя S2 из элементных 5%; не N PEI. S100 носитель без NH2.',
        'nitrogen_linker_mmol_g_composite':'N только NH2-линкера формульного сценария; не прибавляется к n_pei.',
        'original_residue_g_g_mof':'s/h исходной ветви s-I; остаётся для проверки GA даже у строки s-V.',
        'sI_ga_feed_consistent':'Остаток s-I на г MOF <= чистая подача GA. Не устанавливает химический состав остатка.',
        'cap_mass_status':'У дефектного состава известны число линкеров и неизвестны массы концевых групп/гостей. Остов без этих групп даёт верхнюю границу, не точный состав.',
        'pet_theoretical_g_kg_composite':'Теоретический PET: n_BDC*192.17; кислота BDC 166.13 г/моль. Не применяется к actual_analog.',
        'pet_src06_scenario_low_g_kg_composite':'BDC-эквивалент / max(m_BDC/m_PET) / MOF conversion; recovery — граммовое отношение, без второго множителя 192.17/166.13.',
        'pet_src06_scenario_high_g_kg_composite':'BDC-эквивалент / min(m_BDC/m_PET) / MOF conversion. Конверсия MOF не измеренный выход каждого типа линкера.',
        'pet_linker_mole_fraction':'R1=1; R2=1-f_NH2,NMR; actual_analog=0, PET-происхождение для него не заявляется.',
        'pet_fragment_mass_fraction':'Масса связанного BDC2- PET-происхождения / масса композита. Не весь PET-повтор и не этиленгликоль.',
        'src03_tga_bdc_mass_g_kg_composite':'Отдельная условная оценка 0.3975*масса MOF из S4. База сухой массы не восстановлена; не приравнивается к остову.'}
    lines=['# Материальный баланс TASK-003','',f'run_id: `{run_id}`. Входы: S2 Tables 1–2; S100 Fig. S5; SRC03/SRC06 SI; T041.','',
        'h+w+s=1. Подача GA и удержанный остаток раздельны. s-V удаляет s, сохраняет PEI:MOF; q остаётся на заявленной сухой основе. '
        'Никакой доли PET в фактических аналогах S2/S100 не назначено. Сценарии R2 100% NH2 имеют нулевую PET-долю и служат контролем.','',
        f'Для идеального каркаса M={b.M_NODE_G_MOL:.3f}+6[(1-f)164.116+f179.131] г/моль Zr6. Дефектный остов использует 6-x линкеров SRC06; '
        'SRC03: условно 6*(8.8/12)=4.4 по отношению координаций. Положительная неизвестная масса caps уменьшает инвентарь линкеров. '
        'Неизвестная дегидратация узла/база TGA остаётся отдельным ограничением. '
        'Дефектные оценки — верхние границы при фиксированном узле, не восстановленные экспериментальные формулы.','',
        'N PEI = w*30.74%/M(N); N исходного NH2-MOF вычитается в авторской формуле. '
        'Табличные w не заменены реконструкцией; её отклонения и интервалы округления — s2_pei_formula.csv. '
        'Номинальные PEI feed I96 96% и текст §4.4 (0.716/0.78=91.8%) различаются, обе конвенции отмечены.','',
        '| Столбец | Смысл |','|---|---|']
    for key in rows[0]:
        description=special.get(key)
        if description is None:
            if key.endswith('_g_kg_composite'): description='г соответствующего компонента на 1 кг композита (название компонента в имени).'
            elif key.endswith('_mmol_g_composite'): description='ммоль соответствующего N на г композита; численно равно моль/кг.'
            elif key.endswith('_g_composite'): description='Массовая доля соответствующего компонента, г/г.'
            else: description={'run_id':'Паспорт запуска.','sample_id':'Идентификатор аналога.','series':'Источник S2/S100.',
                'composition_branch':'Ветвь s-I/s-V или w-C/w-F.','route':'Маршрут сценария или аналог.',
                'fraction_sum':'Контроль суммы h+w+s.','nh2_linker_mole_fraction':'f в каркасе по NMR; у actual S2 идеальный NH2-контроль.',
                'unique_linkers_per_zr6':'Число уникальных линкеров на узел Zr6.',
                'linker_mol_kg_composite':'Моль всех линкеров на кг композита.',
                'formula_mass_g_mol_zr6':'Масса идеальной формулы/остова на моль узлов Zr6.',
                'src06_mof_conversion':'Авторская конверсия S2 SRC06, доля от 1; переносится только сценарно.',
                'sI_ga_check_applies':'Флаг применения ограничения GA к ветви s-I.',
                'input_status':'Статус принятых входов provisional.',
                'extraction_id':'Паспорта/идентификаторы извлечения и производных операций.',
                'source_locator':'Локаторы исходных таблиц и формул.'}.get(key,'Текстовая оговорка/источник соответствующей величины; см. имя столбца.')
        lines.append(f'| `{key}` | {description} |')
    (ROOT/OUT/'material_balance.md').write_text('\n'.join(lines)+'\n')


def input_evidence(run_id):
    rows=[]
    for path in sorted((ROOT/'data/task003/extracted').glob('*.csv')):
        for r in load(path):
            rows.append(dict(run_id=run_id,input_path=str(path.relative_to(ROOT)),extraction_id=r.get('extraction_id',''),
                source_locator=r.get('locator',''),sample_label=r.get('sample_label',''),quantity=r.get('quantity',r.get('file','')),
                value=r.get('value',''),unit=r.get('unit',''),evidence_class=r.get('value_kind','unknown'),input_status='provisional'))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if not args.run_id or '/' in args.run_id or '\n' in args.run_id:
        raise ValueError('invalid run_id')
    (ROOT/OUT).mkdir(parents=True,exist_ok=True)
    # Tree state is taken before any output is written (T045): outputs of this run must not mark their own run dirty.
    tree_clean_at_start=not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    check_bounds()
    ga_note,raw_path=ga_source()
    recs,envelopes=records()
    for r in envelopes: r['run_id']=args.run_id
    material=list(material_rows(recs,args.run_id,ga_note))
    analog=list(analog_rows(recs,args.run_id))
    transfer,summary=transfer_rows(recs,args.run_id)
    stress=uncertainty_rows(recs,envelopes,args.run_id)
    windows=route_windows(recs,args.run_id)
    save(OUT/'material_balance.csv',material)
    material_notes(material,args.run_id)
    save(OUT/'s2_pei_formula.csv',s2_formula_rows(recs,args.run_id))
    save(OUT/'analog_lines.csv',analog)
    save(OUT/'design_window.csv',design_rows(recs,args.run_id))
    save(OUT/'transfer_kstar.csv',transfer)
    save(OUT/'transfer_kstar_summary.csv',branch_summary(summary,args.run_id))
    save(OUT/'transfer_envelope.csv',transfer_envelope_rows(recs,args.run_id))
    save(OUT/'uncertainty_vertices.csv',stress)
    save(OUT/'sensitivity_rank.csv',sensitivity_ranks(stress))
    save(OUT/'s100_coordinate_envelopes.csv',envelopes)
    save(OUT/'route_windows.csv',windows)
    save(OUT/'input_evidence.csv',input_evidence(args.run_id))
    obs=[r['eta_phi0'] for r in analog if r['eta_phi0'] is not None and r['eta_ceiling']==.5]
    clipped=[min(.5,r['eta_phi0']) for r in analog if r['eta_phi0'] is not None and r['admissible_phi_low'] is not None and r['eta_ceiling']==.5]
    metrics=dict(run_id=args.run_id,conditional_design_only=True,n_n_nominal_mmol_g_pei=b.N_NOMINAL_MMOL_G_PEI,
        n_n_upper_mmol_g_pei=b.N_UPPER_MMOL_G_PEI,eta_lit=b.ETA_LIT,eta_ceiling=.5,eta_ceiling_low=.195,
        eta_obs_max_unclipped=max(obs),eta_obs_max_ceiling_admissible=max(clipped),
        eta_obs_note='unclipped endpoint maximum includes incompatible extensions; not measured eta, not class B anchor',
        q_s100_host_mmol_g=next(r['q0'] for r in recs if r['series']=='S100'),s100_pressure_bar=P_BAR,
        material_rows=len(material),analog_rows=len(analog),transfer_rows=len(transfer),design_rows=3*2*2*51*101,
        branch_summary=branch_summary(summary,args.run_id))
    dump(OUT/'summary.json',metrics)
    figures(recs,args.run_id)
    inputs=[PLAN,Path('docs/work_order_task003_RU.md'),S2_MATERIALS,S2_DRY,PACK/'data/primary/S2_secondary_properties.csv',S100,
        Path('data/task003/eta_bounds.csv'),Path('reviews/T040_report.md'),Path('reviews/T041_report.md'),
        Path('reports/task003/drafts/route_compatibility_T041.md')]
    inputs+=sorted(p.relative_to(ROOT) for p in (ROOT/'data/task003/extracted').glob('*.csv'))
    if raw_path: inputs.append(raw_path)
    code=[Path('Makefile')]+sorted(p.relative_to(ROOT) for folder in ('src/pet2mof/task003','scripts/task003') for p in (ROOT/folder).glob('*.py'))
    code += [Path('scripts/run.py'),Path('src/pet2mof/runs.py')]
    code+=sorted(p.relative_to(ROOT) for p in (ROOT/'tests').glob('test_task003_*.py'))
    def hashed(paths):
        return [dict(path=str(p),sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in paths]
    outputs=[OUT/name for name in ('material_balance.csv','material_balance.md','s2_pei_formula.csv','analog_lines.csv',
        'design_window.csv','transfer_kstar.csv','transfer_kstar_summary.csv','uncertainty_vertices.csv',
        's100_coordinate_envelopes.csv','route_windows.csv','input_evidence.csv','summary.json','design_window.png','transfer_window.png',
        'transfer_envelope.csv','sensitivity_rank.csv','analog_lines.png')]
    dump(OUT/'provenance.json',dict(run_id=args.run_id,
        commit_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        status='committed_tree' if tree_clean_at_start else 'debug_uncommitted_implementation',
        status_basis='git status --porcelain before outputs were written',
        inputs=hashed(inputs),implementation=hashed(code),outputs=hashed(outputs),
        assumptions=['q_s=0','dry pure CO2','no fitting of phi or eta','PET q_host unknown',
                     'defective skeleton masses are conditional upper bounds; caps and exact dry basis unknown'],
        operation_ids=['TASK003-plan-3A','TASK003-plan-2.4','TASK003-P3-01','TASK003-P3-02'],
        runtime=dict(python=sys.version.split()[0],numpy=np.__version__)))
    print(json.dumps({key:metrics[key] for key in ('run_id','material_rows','analog_rows','transfer_rows','design_rows','q_s100_host_mmol_g')}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
