"""Frozen pure-gas observation operators. Inputs contain no measured responses."""
import math
import numpy as np
from pet2mof.model.gas import R

MODEL_LABELS = tuple(f'{m}/{v}/{r}' for m in ('M1', 'B1')
                     for v in ('v1', 'v1.1-mof', 'v1.1-connectivity') for r in ('composite', 'ratio'))


def _number(row, key, *, required=True, default=None):
    v = row.get(key, '')
    if v is None or str(v).strip() == '':
        if required:
            raise ValueError('unknown '+key)
        return default
    v = float(v)
    if not math.isfinite(v):
        raise ValueError('nonfinite '+key)
    return v


def evaluate(row, sample, label):
    """Return capacity/ratio in the explicitly requested physical mass basis.

    The S100 observation operator is used ONLY in calibration. Its fitted
    parameters now predict dry-composite states; dry_MOF divides once by 1-w.
    Unknown wet chemistry and single-temperature extrapolation are untestable.
    """
    model, version, reading = label.split('/')
    fit = next(f for f in sample['fits'] if f['model_version'] == version and f['interpretation'] == reading)
    material, gas, obs = (row[k] for k in ('material', 'gas', 'observable'))
    if material not in ('UiO-66', 'UiO-66-NH2', 'PEI@UiO-66-NH2'):
        raise ValueError('unsupported material')
    if row['basis'] not in ('dry_sorbent', 'dry_MOF'):
        raise ValueError('unknown mass basis')
    expected_unit = '1' if obs in ('q_CO2_ratio_to_w0', 'Vp_ratio_to_w0') else 'mmol/g'
    if row['unit'] != expected_unit:
        raise ValueError('observable unit mismatch')
    w = _number(row, 'w_PEI', required=material.startswith('PEI'), default=0.)
    if not 0 <= w < 1 or (not material.startswith('PEI') and w != 0):
        raise ValueError('invalid PEI fraction/material')
    if w > 0:
        if row.get('w_reading') not in ('label', 'retained'):
            raise ValueError('unknown loading reading')
        if row['w_reading'] == 'label' and reading == 'ratio':
            w = w/(1+w)
        if row.get('source_id') == 'S2':
            if row['w_reading'] != 'retained' or _number(row, 'Mw_PEI') != 600.:
                raise ValueError('D-11 requires retained loading and Mw=600')
    if obs == 'Vp_ratio_to_w0':
        # Mass-normalized pore volume uses no gas isotherm or temperature
        # transfer. A supplied porosimetry temperature must still be physical.
        T = _number(row, 'T_K', required=False)
        if T is not None and T <= 0:
            raise ValueError('nonpositive temperature')
        m = fit['models'][model]['parameters']
        if model == 'B1':
            scale = 1-w
        elif version == 'v1.1-connectivity':
            scale = (1-w)*math.exp(-(m['kappa']*w/(1-w))**m['power'])
        else:
            scale = 1-w-m['kappa']*w
        if scale < 0:
            raise ValueError('loading outside feasible dry-pore domain')
        return scale/(1-w) if row['basis'] == 'dry_MOF' else scale
    T = _number(row, 'T_K')
    if T <= 0:
        raise ValueError('nonpositive temperature')
    a = _number(row, 'RH_fraction')
    if not 0 <= a <= 1:
        raise ValueError('invalid water activity')
    if a != 0 or gas == 'CO2+H2O' or obs == 'q_H2O':
        raise ValueError('wet operator/defect identity/temperature transfer not identified for this material')
    host_material = 'UiO-66-NH2' if 'NH2' in material else 'UiO-66'
    carrier_gas = 'CO2' if obs in ('q_CO2_ratio_to_w0', 'Vp_ratio_to_w0') else gas
    if carrier_gas not in ('CO2', 'N2') or (obs in ('q_CO2', 'q_CO2_ratio_to_w0') and gas != 'CO2') or (obs == 'q_N2' and gas != 'N2'):
        raise ValueError('unsupported gas/observable combination')
    carrier = next((c for c in sample['c_fits']['carriers'] if c['material'] == host_material and c['gas'] == carrier_gas), None)
    if carrier is None:
        raise ValueError('verified carrier calibration missing')
    if carrier['Q'] is None and abs(T-carrier['T_ref']) > 1e-8:
        raise ValueError('carrier temperature coefficient unknown')
    if w > 0 and carrier_gas == 'CO2' and abs(T-fit['T_fit']) > 1e-8:
        raise ValueError('PEI temperature coefficient unknown')
    p = _number(row, 'p_partial_bar')
    if p < 0:
        raise ValueError('negative partial pressure')
    if obs not in ('q_CO2', 'q_N2', 'q_CO2_ratio_to_w0', 'Vp_ratio_to_w0'):
        raise ValueError('unsupported observable')
    b = carrier['b']*math.exp((carrier['Q'] or 0.)/R*(1/T-1/carrier['T_ref']))
    host_q = carrier['q_sat']*b*p/(1+b*p)
    m = fit['models'][model]['parameters']
    if model == 'B1':
        scale = 1-w
    elif version == 'v1.1-connectivity':
        scale = (1-w)*math.exp(-(m['kappa']*w/(1-w))**m['power'])
    else:
        scale = 1-w-m['kappa']*w
    if scale < 0:
        raise ValueError('loading outside feasible dry-pore domain')
    q = scale*host_q
    if gas == 'CO2':
        eta = m['eta0'] if model == 'B1' else .5*m['A0']*math.exp(-m['lam']*w/(1-w))
        q += w*fit['n_N']*eta*m['K_d']*p/(1+m['K_d']*p)
    if row['basis'] == 'dry_MOF':
        q /= 1-w
    if obs == 'q_CO2_ratio_to_w0':
        if host_q <= 0:
            raise ValueError('zero reference capacity')
        q /= host_q
    return q


def derivatives(row, sample, label, *, ensemble=None):
    """Richardson finite differences; no inferred humidity response in dry fit."""
    result = {}
    def predict(r):
        return evaluate(r, sample, label) if ensemble is None else float(np.median([evaluate(r, s, label) for s in ensemble]))
    for key, name, step in (('p_partial_bar', 'dq_dp', 1e-4), ('T_K', 'dq_dT', .01)):
        x = _number(row, key)
        if key == 'p_partial_bar':
            step = 1e-5*max(x, 1e-3)
        forward = x < step
        # For the PEI isotherm T is fixed by design: derivative needs unknown Q.
        if key == 'T_K' and _number(row, 'w_PEI', required=False, default=0.) > 0:
            result[name] = None
            continue
        def slope(h):
            left, right = dict(row), dict(row)
            if forward:
                left[key], right[key] = x+h, x+2*h
                return (-3*predict(row)+4*predict(left)-predict(right))/(2*h)
            left[key], right[key] = x-h, x+h
            return (predict(right)-predict(left))/(right[key]-left[key])
        try:
            result[name] = (4*slope(step/2)-slope(step))/3
        except ValueError:
            result[name] = None
    result['dq_da'] = None  # unknown wet chemistry; only u_a=0 permits a dry test
    return result


def applicability(row, sample, label):
    """D-18 declarations from conditions/C only, never observation errors.

    A matching temperature permits *excluding* unknown u_T conditionally;
    it does not identify a missing temperature derivative or set u_T to zero.
    evaluate() still refuses transfer of a single-temperature component.
    """
    evaluate(row, sample, label)
    _, version, reading = label.split('/')
    fit = next(f for f in sample['fits'] if f['model_version'] == version and f['interpretation'] == reading)
    host = 'UiO-66-NH2' if 'NH2' in row['material'] else 'UiO-66'
    gas = 'CO2' if row['observable'] in ('q_CO2_ratio_to_w0', 'Vp_ratio_to_w0') else row['gas']
    carrier = next(c for c in sample['c_fits']['carriers'] if c['material'] == host and c['gas'] == gas)
    temperatures = carrier.get('calibration_temperatures_K', [carrier['T_ref']] if carrier['Q'] is None else [])
    T = _number(row, 'T_K')
    matches = any(abs(T-t) <= 1. for t in temperatures)
    if _number(row, 'w_PEI', required=False, default=0.) > 0 and gas == 'CO2':
        matches = matches and abs(T-fit['T_fit']) <= 1.
    return dict(dry_series=_number(row, 'RH_fraction') == 0.,
                temperature_matches_calibration=matches)
