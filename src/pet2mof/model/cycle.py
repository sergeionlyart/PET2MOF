"""Quasi-equilibrium cycle, NOT a coupled kinetic/column model (D-08).

Water and physical pools equilibrate at each endpoint; chemical residuals relax
from the preceding endpoint. Reject incompatible residual N/water states. A wet
bicarbonate-to-dry transition generally needs the deferred coupled integrator.
"""
from dataclasses import dataclass, replace
import math
import numpy as np
from .isotherms import Isotherm, iast, hill

POOL_NAMES = ('C_phys', 'N_phys', 'd', 'b', 'W_M', 'W_P')


@dataclass(frozen=True)
class Model:
    co2: Isotherm
    n2: Isotherm
    pores: object
    amines: object
    water_step: dict
    xi: float = 0.
    baseline: object = None
    B0: bool = False

    def equilibrium(self, w, gas):
        physical = iast(gas.p_C, gas.p_N, gas.T, self.co2, self.n2)
        if self.baseline is not None:
            return np.array([(1-w)*physical[0], (1-w)*physical[1],
                             self.baseline.chemistry(w, gas.p_C, gas.T, B0=self.B0), 0., 0., 0.])
        F = hill(gas.a, gas.T, **self.water_step)
        volume = self.pores.state(w, gas.a, F)
        if self.xi:
            shifted = replace(self.co2, sites=tuple(replace(s, b=s.b * math.exp(self.xi * F)) for s in self.co2.sites))
            physical = iast(gas.p_C, gas.p_N, gas.T, shifted, self.n2)
        chem = self.amines.equilibrium(w, gas.a, gas.p_C, gas.T, volume['W_P'])
        return np.array([volume['phys_scale']*physical[0], volume['phys_scale']*physical[1],
                         chem['d'], chem['b'], volume['W_M'], volume['W_P']])


def finite_fraction(tau_over_t):
    if not math.isfinite(tau_over_t) or tau_over_t < 0:
        raise ValueError('finite tau/t >= 0 required')
    return 1. if tau_over_t == 0 else -math.expm1(-1 / tau_over_t)


def co2_total(state):
    return float(state[0] + state[2] + state[3])


def selectivity(state, gas, tolerance=1e-12):
    if state[1] <= tolerance or gas.p_C <= 0 or gas.p_N <= 0:
        return None
    return co2_total(state) / state[1] / (gas.p_C / gas.p_N)


def periodic_cycle(model, w, ads, des, *, tau_over_t=0., tau_des_over_t=None,
                   tolerance=1e-9, max_cycles=1000, t_ads=1800., t_des=1800.):
    """Fixed-point cycling; require all endpoint pools stable three cycles in a row.

    tolerance is an explicit numerical debug tolerance, not an experimental U.
    Ratios refer separately to each specified dwell; no diffusion fit is implied.
    """
    if tolerance <= 0 or max_cycles < 3 or min(t_ads, t_des) <= 0:
        raise ValueError('positive tolerances/times and >=3 cycles required')
    eq_a, eq_d = model.equilibrium(w, ads), model.equilibrium(w, des)
    fa = finite_fraction(tau_over_t)
    fd = finite_fraction(tau_over_t if tau_des_over_t is None else tau_des_over_t)
    start = np.zeros(6)
    previous_ads = np.zeros(6)
    stable = 0
    for iteration in range(1, max_cycles + 1):
        a, d = eq_a.copy(), eq_d.copy()
        a[2:4] = start[2:4] + fa * (eq_a[2:4] - start[2:4])
        d[2:4] = a[2:4] + fd * (eq_d[2:4] - a[2:4])
        if model.baseline is None:
            model.amines.check_state(w, a[2], a[3], a[5])
            model.amines.check_state(w, d[2], d[3], d[5])
        residual = max(float(np.max(abs(d - start))), float(np.max(abs(a - previous_ads))))
        stable = stable + 1 if residual <= tolerance else 0
        if stable == 3:
            return dict(q_work=co2_total(a)-co2_total(d), delta_water=float(sum(a[4:])-sum(d[4:])),
                        ads=a.tolist(), des=d.tolist(), equilibrium_ads=eq_a.tolist(), equilibrium_des=eq_d.tolist(),
                        cycles=iteration, residual=residual, tolerance=tolerance,
                        selectivity_ads=selectivity(a, ads), selectivity_kind='quasi_equilibrium_endpoint',
                        t_ads=t_ads, t_des=t_des, tau_over_t=tau_over_t,
                        tau_des_over_t=tau_over_t if tau_des_over_t is None else tau_des_over_t,
                        baseline_water_available=model.baseline is None, status='debug_quasi_equilibrium')
        start, previous_ads = d, a
    raise RuntimeError(f'periodic cycle did not converge in {max_cycles} cycles; residual={residual}')


def heat(cycle, w, T_ads, T_des, *, cp_mof=None, cp_pei=None, cp_water=None,
         Q_phys=None, Q_d=None, Q_b=None, Q_water=None, Q_n2=None, epsilon_s=0., epsilon_d=0.,
         chemical_reference='sorbed_water', M_water=18.01528, M_co2=44.0095):
    """Endpoint heat with water sensible lower/upper bounds, J/g dry composite.

    Q_d/Q_b must be the SAME thermodynamic scenario used in equilibrium; Q_b is
    relative to sorbed water. No extra vaporisation term. Plant energy unknown.
    """
    symbolic = '(1-eps_s)*integral(cp_dry+1e-3*M_W*q_W(T)*cp_W)dT + (1-eps_d)*1e-3*sum(Q_j*delta_q_j)'
    args = (cp_mof, cp_pei, cp_water, Q_phys, Q_d, Q_b, Q_water, Q_n2)
    if not cycle['baseline_water_available'] or any(x is None for x in args):
        return dict(status='unknown', expression=symbolic, plant_energy='unknown')
    if not all(math.isfinite(x) and x >= 0 for x in args) or not 0 <= epsilon_s <= 1 or not 0 <= epsilon_d <= 1:
        raise ValueError('finite nonnegative heat parameters and recovery fractions in [0,1] required')
    if chemical_reference != 'sorbed_water' or T_des < T_ads:
        raise ValueError('heat requires sorbed-water reaction reference and heating regeneration')
    a, d = np.array(cycle['ads']), np.array(cycle['des'])
    changes = np.array([a[0]-d[0], a[2]-d[2], a[3]-d[3], sum(a[4:])-sum(d[4:]), a[1]-d[1]])
    if min(changes) < -1e-12:
        return dict(status='unknown', expression=symbolic, reason='opposing endpoint changes require signed path heat', plant_energy='unknown')
    des_heat = .001 * float(np.dot(changes, [Q_phys, Q_d, Q_b, Q_water, Q_n2]))
    dry_cp = (1-w)*cp_mof + w*cp_pei
    sensible = [(T_des-T_ads)*(dry_cp + .001*M_water*q*cp_water) for q in (0., sum(a[4:]))]
    total = [(1-epsilon_s)*s + (1-epsilon_d)*des_heat for s in sensible]
    return dict(status='conditional', heat_J_g=total, sensible_J_g=sensible, desorption_J_g=des_heat,
                specific_J_g_co2=None if cycle['q_work'] <= 0 else [e/(.001*M_co2*cycle['q_work']) for e in total],
                water_path='leaves_before_heating / retained_during_heating', plant_energy='unknown')
