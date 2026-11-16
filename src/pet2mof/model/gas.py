"""Ideal wet gas and IAPWS SR1-86(1992), equation (1).

Correlation source: https://iapws.org/public/documents/6dGkr/Supp-sat.pdf
Section 1: Tc=647.096 K, pc=22.064 MPa; powers 1,1.5,3,3.5,4,7.5.
Reference checks (pressure in MPa): 273.16 K -> 0.000611657,
373.15 K -> 0.101417994, critical point -> 22.064.
The official PDF is not present in the blind T013 checkout and source network
access is forbidden. Coefficient transcription/reference checks are provisional
pending independent comparison with that document (T016); no claim of source QA.
"""
from dataclasses import dataclass
import math

R = 8.31446261815324  # exact SI: N_A * k_B, J/(mol K)


def p_sat(T):
    """Saturation pressure, bar; liquid-vapour domain 273.16..647.096 K."""
    if not math.isfinite(T) or not 273.16 <= T <= 647.096:
        raise ValueError('IAPWS liquid saturation requires 273.16 <= T <= 647.096 K')
    theta = 1 - T / 647.096
    coefficients = (-7.85951783, 1.84408259, -11.7866497, 22.6807411, -15.9618719, 1.80122502)
    powers = (1, 1.5, 3, 3.5, 4, 7.5)
    return 220.64 * math.exp(647.096 / T * sum(c * theta**k for c, k in zip(coefficients, powers)))


@dataclass(frozen=True)
class Gas:
    T: float
    P: float
    p_C: float
    p_N: float
    p_W: float

    def __post_init__(self):
        values = (self.T, self.P, self.p_C, self.p_N, self.p_W)
        if not all(math.isfinite(x) for x in values) or self.T <= 0 or self.P <= 0:
            raise ValueError('finite T,P > 0 required')
        if min(values[2:]) < 0 or not math.isclose(sum(values[2:]), self.P, rel_tol=1e-10):
            raise ValueError('partial pressures must be nonnegative and sum to P')
        if self.p_W >= self.P or self.p_W > p_sat(self.T) * (1 + 1e-10):
            raise ValueError('supersaturated or all-water gas is outside M1')

    @property
    def a(self):
        return self.p_W / p_sat(self.T)

    @property
    def y(self):
        return tuple(p / self.P for p in (self.p_C, self.p_N, self.p_W))


def wet_gas(T, P, RH, z_C=0.05):
    if not all(math.isfinite(x) for x in (RH, z_C)) or not 0 <= RH <= 100 or not 0 <= z_C <= 1:
        raise ValueError('RH in percent and dry CO2 mole fraction required')
    water = RH / 100 * p_sat(T)
    return Gas(T, P, z_C * (P - water), (1 - z_C) * (P - water), water)


def regeneration(kind='R1', *, T=None, P=None, y_C=None, y_W=None):
    if kind not in ('R1', 'R2'):
        raise ValueError('regeneration must be R1 or R2')
    defaults = (383.15, 1., .001, .001) if kind == 'R1' else (363.15, .1, .01, .01)
    T, P, y_C, y_W = tuple(d if v is None else v for v, d in zip((T, P, y_C, y_W), defaults))
    return Gas(T, P, P * y_C, P * (1 - y_C - y_W), P * y_W)
