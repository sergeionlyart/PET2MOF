"""B1 (19); B0 is the literal, nonregenerable constant nitrogen increment."""
from dataclasses import dataclass
from .isotherms import affinity


@dataclass(frozen=True)
class Baseline:
    n_N: float
    eta0: float
    K_d: float
    Q_d: float = 0.
    T_ref: float = 298.

    def __post_init__(self):
        import math
        if not all(math.isfinite(v) for v in vars(self).values()) or not 0 <= self.eta0 <= .5 or self.n_N <= 0:
            raise ValueError('invalid baseline nitrogen/efficiency')
        affinity(self.K_d, self.Q_d, self.T_ref, self.T_ref)

    def chemistry(self, w, p_C, T, *, B0=False):
        if not 0 <= w <= 1 or p_C < 0:
            raise ValueError('invalid baseline state')
        theta = 1. if B0 else (lambda x: x / (1 + x))(affinity(self.K_d, self.Q_d, T, self.T_ref) * p_C)
        return w * self.n_N * self.eta0 * theta
