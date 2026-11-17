"""Read-only audit excerpt of PET2MOF prediction.py at commit 66bae26.
_number and evaluate copied from GitHub; no scientific parameters are fitted here.
Only the import of R is replaced by its SI value: pore-volume output does not use R.
Source Git blob: 51f78ef7f50769b8c1f61ed6a37d7ebe7b692e9d.
"""
import math
R = 8.31446261815324

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
    if obs == 'Vp_ratio_to_w0':
        # Accessible volume per reported mass. B1 has simple dilution only.
        return scale/(1-w) if row['basis'] == 'dry_MOF' else scale
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
