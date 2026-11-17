"""Disjoint N pools, equations (11)-(13). No silent water-capacity clipping."""
from dataclasses import dataclass
import math
from . import Inadmissible
from .isotherms import affinity


@dataclass(frozen=True)
class Amines:
    n_N: float
    A0: float
    lam: float
    K_d: float
    Q_d: float = 0.
    f1: float = .25
    f2: float = .5
    f3: float = .25
    gamma: float = 0.
    h_max: float = 0.
    K_h: float = .1
    K_b: float = 1.
    Q_b: float = 0.
    T_ref: float = 298.
    water_limited: bool = False

    def __post_init__(self):
        if not all(math.isfinite(v) for v in vars(self).values()):
            raise ValueError('finite amine parameters required')
        if min(self.n_N, self.K_d, self.K_b, self.K_h, self.T_ref) <= 0 or min(self.lam, self.Q_d, self.Q_b) < 0:
            raise ValueError('invalid amine constants')
        if not 0 <= self.A0 <= 1 or not 0 <= self.h_max <= 1 or self.gamma < -1:
            raise ValueError('invalid availability or wet chemistry')
        if min(self.f1, self.f2, self.f3) < 0 or not math.isclose(self.f1 + self.f2 + self.f3, 1., abs_tol=1e-12):
            raise ValueError('N fractions must form a simplex')

    @property
    def nu_d(self):
        return min(.5, self.f1 + self.f2)

    def equilibrium(self, w, a, p_C, T, water_pei):
        if not 0 <= w <= 1 or not 0 <= a <= 1 or min(p_C, water_pei) < 0:
            raise ValueError('invalid chemical state')
        attenuation = math.exp(-self.lam * w / (1 - w)) if w < 1 else (1. if self.lam == 0 else 0.)
        A = min(1., max(0., self.A0 * attenuation * (1 + self.gamma * a)))  # specified clip in (11)
        N = w * self.n_N * A
        h = self.h_max * a / (self.K_h + a)
        if self.water_limited:
            # Joint allocation before occupancy: h*N <= W. No rejected or clipped
            # CO2 target and no second independent water pool for bicarbonate.
            h *= water_pei/(water_pei+h*N) if water_pei+h*N > 0 else 0.
        kd, kb = affinity(self.K_d, self.Q_d, T, self.T_ref), affinity(self.K_b, self.Q_b, T, self.T_ref)
        d = (1 - h) * N * self.nu_d * kd * p_C / (1 + kd * p_C)
        b = h * N * kb * p_C / (1 + kb * p_C)
        if b > water_pei + 1e-12:
            raise Inadmissible('bicarbonate target exceeds PEI-associated water')
        return dict(d=d, b=b, N_acc=N, N_d=(1-h)*N, N_b=h*N, A=A, h=h)

    def check_state(self, w, d, b, water_pei, *, tolerance=1e-10):
        used = d / self.nu_d if self.nu_d else (0. if d <= tolerance else math.inf)
        if min(d, b, water_pei) < -tolerance or b > water_pei + tolerance or used + b > w * self.n_N + tolerance:
            raise Inadmissible('retained chemical pools violate nitrogen/water balance; coupled kinetics needed')
