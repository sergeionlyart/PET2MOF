"""Langmuir/DSL; IAST uses analytical spreading integrals, scalar numerical roots.

There is no general closed-form DSL mixture solution. The independent reference
solver integrates q/p by quadrature and solves in adsorbed mole fraction.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import expit
from .gas import R, p_sat


def affinity(b, Q, T, T_ref=298.):
    if not all(math.isfinite(x) for x in (b, Q, T, T_ref)) or b <= 0 or Q < 0 or min(T, T_ref) <= 0:
        raise ValueError('positive b,T,T_ref and nonnegative Q required')
    return b * math.exp(Q / R * (1 / T - 1 / T_ref))


@dataclass(frozen=True)
class Site:
    q: float
    b: float
    Q: float = 0.

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.q, self.b, self.Q)) or min(self.q, self.b) <= 0 or self.Q < 0:
            raise ValueError('finite q,b > 0 and Q >= 0 required')


@dataclass(frozen=True)
class Isotherm:
    sites: tuple[Site, ...]
    T_ref: float = 298.

    def __post_init__(self):
        if len(self.sites) not in (1, 2) or not math.isfinite(self.T_ref) or self.T_ref <= 0:
            raise ValueError('one or two sites and positive T_ref required')

    def uptake(self, p, T):
        if not math.isfinite(p) or p < 0:
            raise ValueError('finite absolute p >= 0 required')
        if p == 0:
            return 0.
        return sum(s.q * expit(math.log(affinity(s.b, s.Q, T, self.T_ref)) + math.log(p)) for s in self.sites)

    def spreading_logp(self, logp, T):
        return sum(s.q * np.logaddexp(0., math.log(affinity(s.b, s.Q, T, self.T_ref)) + logp) for s in self.sites)

    def spreading(self, p, T):
        if p < 0 or not math.isfinite(p):
            raise ValueError('finite p >= 0 required')
        return 0. if p == 0 else float(self.spreading_logp(math.log(p), T))

    def inverse_logp(self, pi, T):
        if pi <= 0:
            raise ValueError('positive spreading pressure required')
        if len(self.sites) == 1:
            s = self.sites[0]
            x = pi / s.q
            logexpm1 = math.log(math.expm1(x)) if x < 50 else x + math.log1p(-math.exp(-x))
            return logexpm1 - math.log(affinity(s.b, s.Q, T, self.T_ref))
        lo, hi = -700., 700.
        return brentq(lambda u: self.spreading_logp(u, T) - pi, lo, hi, xtol=1e-12)


@lru_cache(maxsize=4096)
def iast(p_C, p_N, T, co2, n2, *, tolerance=1e-9):
    """Return CO2,N2 mmol/g MOF. Check closure of sum(p_i/p_i^0)."""
    p = np.array([p_C, p_N], dtype=float)
    if np.any(~np.isfinite(p)) or np.any(p < 0):
        raise ValueError('nonnegative finite partial pressures required')
    models = (co2, n2)
    active = np.flatnonzero(p > 0)
    if len(active) < 2:
        return tuple(m.uptake(float(v), T) for m, v in zip(models, p))
    logp = np.log(p)
    def fractions(pi):
        return np.exp([lp - m.inverse_logp(pi, T) for lp, m in zip(logp, models)])
    lo = max(m.spreading(float(v), T) for m, v in zip(models, p))
    hi = max(2 * lo, 1.)
    while fractions(hi).sum() > 1:
        hi *= 2
    pi = brentq(lambda v: fractions(v).sum() - 1, lo, hi, xtol=1e-13, rtol=1e-13)
    x = fractions(pi)
    if abs(x.sum() - 1) > tolerance:
        raise RuntimeError('IAST closure failed')
    pure = [m.uptake(math.exp(m.inverse_logp(pi, T)), T) for m in models]
    total = 1 / sum(xi / qi for xi, qi in zip(x, pure))
    return tuple(float(v) for v in x * total)


def iast_numerical(p_C, p_N, T, co2, n2):
    """Independent quadrature + logit-composition root, for verification."""
    if p_C <= 0 or p_N <= 0:
        return iast(p_C, p_N, T, co2, n2)
    def integral(model, p):
        return quad(lambda v: model.uptake(v, T) / v, 0, p, epsabs=1e-11, epsrel=1e-11)[0]
    def residual(u):
        x = expit(u)
        return integral(co2, p_C / x) - integral(n2, p_N / (1 - x))
    u = brentq(residual, -25, 25, xtol=1e-12)
    x = expit(u)
    q = 1 / (x / co2.uptake(p_C / x, T) + (1 - x) / n2.uptake(p_N / (1 - x), T))
    return (x * q, (1 - x) * q)


def hill(a, T, *, p_s_ref, m, Q=0., T_ref=298.):
    if not 0 <= a <= 1 or m < 1 or p_s_ref <= 0 or Q < 0:
        raise ValueError('invalid water step')
    if a == 0:
        return 0.
    # Sign follows specification (7), intentionally opposite to gas affinity.
    p_s = p_s_ref * math.exp(-Q / R * (1 / T - 1 / T_ref))
    return float(expit(m * (math.log(a) - math.log(p_s / p_sat(T)))))
