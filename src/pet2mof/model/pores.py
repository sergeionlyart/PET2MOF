"""Equations (6),(8)-(10); incompatible volumes raise Inadmissible."""
from dataclasses import dataclass
import math
from . import Inadmissible


@dataclass(frozen=True)
class Pores:
    V_p0: float
    rho_pei: float
    f_in: float = 0.
    c_conn: float = 1.
    alpha_in: float = 0.
    W_max: float = 0.
    K_WP: float = 1.
    rho_water: float = 1.  # explicit liquid-density approximation, not IAPWS density
    M_water: float = 18.01528
    connectivity_kappa: float = 0.
    connectivity_power: float = 1.

    def __post_init__(self):
        if not all(math.isfinite(v) for v in vars(self).values()):
            raise ValueError('finite pore parameters required')
        if min(self.V_p0, self.rho_pei, self.rho_water, self.M_water, self.K_WP) <= 0 or self.W_max < 0:
            raise ValueError('positive volume,densities,K_WP; W_max >= 0 required')
        if any(not 0 <= v <= 1 for v in (self.f_in, self.c_conn, self.alpha_in)):
            raise ValueError('pore fractions outside [0,1]')
        if self.f_in == 0 and self.alpha_in != 0:
            if self.connectivity_kappa == 0:
                raise Inadmissible('internal PEI water requires internal PEI or pore-mouth film')
        if self.connectivity_kappa < 0 or self.connectivity_power < 1:
            raise ValueError('invalid connectivity branch')

    @property
    def v_water(self):
        return .001 * self.M_water / self.rho_water

    def state(self, w, a, F):
        if not 0 <= w <= 1 or not 0 <= a <= 1 or not 0 <= F <= 1:
            raise ValueError('w,a,F must lie in [0,1]')
        host = (1 - w) * self.V_p0
        pei = self.f_in * w / self.rho_pei
        if pei > host:
            raise Inadmissible('PEI volume exceeds host pores')
        if w == 0 and self.c_conn != 1:
            raise Inadmissible('own bare-host basis requires c_conn=1')
        dry = self.c_conn * (host - pei)
        if self.connectivity_kappa:
            from .revision import connectivity
            dry *= float(connectivity(w, self.connectivity_kappa, self.connectivity_power)) if w < 1 else 0.
        water_pei = w * self.W_max * a / (self.K_WP + a)
        remaining = dry - self.alpha_in * self.v_water * water_pei
        if remaining < 0:
            raise Inadmissible('PEI-associated water exceeds remaining pore volume')
        water_mof = remaining / self.v_water * F
        gas = remaining * (1 - F)
        return dict(V_host=host, V_pei=pei, V_dry=dry, V_R=remaining, V_g=gas,
                    W_P=water_pei, W_M=water_mof,
                    phys_scale=0. if host == 0 else gas / host * (1 - w))
