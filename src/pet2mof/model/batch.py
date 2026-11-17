"""Vectorized single-site endpoint equations; scalar Model is the reference.

Only the analytical periodic limit is accelerated. No new equilibrium model and
no kinetic fitting are introduced here.
"""
import numpy as np
from scipy.special import expit
from .gas import R, p_sat


def iast_batch(p_c, p_n, T, q_c, b_c, Q_c, q_n, b_n, Q_n, T_ref=298.):
    p_c, p_n, T, q_c, b_c, Q_c, q_n, b_n, Q_n = np.broadcast_arrays(
        *[np.asarray(x, float) for x in (p_c, p_n, T, q_c, b_c, Q_c, q_n, b_n, Q_n)])
    bc = b_c*np.exp(Q_c/R*(1/T-1/T_ref)); bn = b_n*np.exp(Q_n/R*(1/T-1/T_ref))
    lo = np.maximum(q_c*np.log1p(bc*p_c), q_n*np.log1p(bn*p_n))
    hi = np.maximum(2*lo, 1.)
    def fractions(pi):
        return bc*p_c/np.expm1(np.minimum(pi/q_c, 700)), bn*p_n/np.expm1(np.minimum(pi/q_n, 700))
    for _ in range(100):
        x, y = fractions(hi); mask = x+y > 1
        if not mask.any():
            break
        hi = np.where(mask, 2*hi, hi)
    else:
        raise RuntimeError('batch IAST bracket failed')
    for _ in range(60):
        mid = (lo+hi)/2
        x, y = fractions(mid)
        mask = x+y > 1
        lo, hi = np.where(mask, mid, lo), np.where(mask, hi, mid)
    pi = (lo+hi)/2
    x, y = fractions(pi)
    pure_c, pure_n = q_c*(-np.expm1(-pi/q_c)), q_n*(-np.expm1(-pi/q_n))
    total = 1/(x/pure_c+y/pure_n)
    return x*total, y*total


def endpoint_grid(fit, carrier, water, params, w, gas, *, version, transfer):
    """Arrays [sample,w,pool]; dry composite basis even for MOF observations."""
    w = np.asarray(w)[None, :]
    r = w/(1-w)
    v = lambda key: np.asarray(params[key])[:, None]
    T, P, pc, pn, a = [np.asarray(gas[k]) for k in ('T', 'P', 'p_C', 'p_N', 'a')]
    size = len(params['Q_phys'])
    T, pc, pn, a = [np.broadcast_to(x, (size,)) for x in (T, pc, pn, a)]
    step_ps = water['a_s']*p_sat(water['T_ref'])*np.exp(-params['Q_W']/R*(1/T-1/water['T_ref']))
    psat = np.array([p_sat(float(t)) for t in T])
    F = expit(water['m']*(np.log(np.maximum(a, 1e-300))-np.log(step_ps/psat)))
    F = np.where(a == 0, 0., F)[:, None]
    if version == 'v1.1-connectivity':
        dry = (1-w)*v('V_p0')*np.exp(-(v('kappa')*r)**v('power'))
    else:
        dry = (1-w-v('kappa')*w)*v('V_p0')
    WP = w*v('W_max')*a[:, None]/(v('K_WP')+a[:, None])
    vw = .01801528/v('rho_water')
    remaining = dry-v('alpha_in')*vw*WP
    WM = remaining/vw*F
    phys_scale = remaining*(1-F)/v('V_p0')
    host = fit['host'] if transfer == 'S100-own-temperature-ratio-S105' else carrier['CO2']
    hq, hb = host['q_sat'], host['b']
    bc = hb*np.exp(params['xi']*F[:, 0])
    cc, nn = iast_batch(pc, pn, T, hq, bc, params['Q_phys'], carrier['N2']['q_sat'], carrier['N2']['b'], params['Q_n2'])
    m = fit['models']['M1']['parameters']
    A0 = fit['n_N']*m['A0']/params['n_N']
    A = np.clip(A0[:, None]*np.exp(-m['lam']*r)*(1+v('gamma')*a[:, None]), 0., 1.)
    N = w*v('n_N')*A
    h = v('h_max')*a[:, None]/(v('K_h')+a[:, None])
    h = h*np.divide(WP, WP+h*N, out=np.zeros_like(WP), where=(WP+h*N)>0)
    kd = m['K_d']*np.exp(params['Q_d']/R*(1/T-1/fit['T_fit']))
    kb = params['K_b']*np.exp(params['Q_b']/R*(1/T-1/fit['T_fit']))
    nu = np.minimum(.5, params['f1']+params['f2'])[:, None]
    d = (1-h)*N*nu*(kd*pc/(1+kd*pc))[:, None]
    b = h*N*(kb*pc/(1+kb*pc))[:, None]
    out = np.stack([phys_scale*cc[:, None], phys_scale*nn[:, None], d, b, WM, WP], axis=-1)
    if np.any(remaining < -1e-12) or np.any(b-WP > 1e-12) or not np.isfinite(out).all():
        raise ValueError('joint endpoint violates volume/water constraints')
    return out


def periodic_endpoints(eq_a, eq_d, tau, t_ads, t_des, *, coupled):
    """Exact fixed point of the affine endpoint map (no iteration cutoff)."""
    tau, ta, td = np.broadcast_arrays(tau, t_ads, t_des)
    ra = np.exp(-np.divide(ta, tau, out=np.full_like(ta, np.inf), where=tau>0))
    rd = np.exp(-np.divide(td, tau, out=np.full_like(td, np.inf), where=tau>0))
    ra, rd = ra[:, None, None], rd[:, None, None]
    a = ((1-ra)*eq_a + ra*(1-rd)*eq_d)/(1-ra*rd)
    d = (1-rd)*eq_d+rd*a
    if not coupled:
        a[..., [0,1,4,5]] = eq_a[..., [0,1,4,5]]
        d[..., [0,1,4,5]] = eq_d[..., [0,1,4,5]]
    return a, d
