"""Pure dry-composite balances (mmol CO2/g, mmol N/g PEI, g/g fractions).

No fitted phi/eta, pore-area proxy, IO or calibration-module dependency.
The effective eta is an additional contribution per mole of *PEI* nitrogen.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

M_N_G_MOL = 14.007
M_BDC_ACID_G_MOL = 166.13
M_PET_REPEAT_G_MOL = 192.17
M_BDC_LINKER_G_MOL = 164.116
M_NH2_BDC_LINKER_G_MOL = 179.131
M_NODE_G_MOL = 6 * 91.224 + 8 * 15.999 + 4 * 1.008
N_PEI_MASS_FRACTION = .3074
N_NOMINAL_MMOL_G_PEI = N_PEI_MASS_FRACTION * 1000 / M_N_G_MOL
N_UPPER_MMOL_G_PEI = 1000 / 43.069
ETA_LIT = .3747
ETA_CEILING = .5
# P3-02 explicitly rounds the lower ceiling to 0.195.
ETA_CEILING_LOW = .195
GA_FEED_G_G_MOF = .6007 * .5 / .78


def finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def fraction(value: float, name: str) -> float:
    if not 0 <= finite(value, name) <= 1:
        raise ValueError(f"{name} must lie in [0, 1]")
    return value


def positive(value: float, name: str) -> float:
    if finite(value, name) <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Composition:
    h_g_mof_g_composite: float
    w_g_pei_g_composite: float
    s_g_residue_g_composite: float = 0.

    def __post_init__(self):
        for name, value in vars(self).items():
            fraction(value, name)
        if abs(self.h + self.w + self.s - 1) > 1e-12:
            raise ValueError("h + w + s must equal 1 within 1e-12")

    @property
    def h(self):
        return self.h_g_mof_g_composite

    @property
    def w(self):
        return self.w_g_pei_g_composite

    @property
    def s(self):
        return self.s_g_residue_g_composite


def s2_pei_mass_fraction(mass_gain_g_g_mof: float, nitrogen_g_g_composite: float,
                         host_nitrogen_g_g_mof: float,
                         pei_nitrogen_g_g_pei: float = N_PEI_MASS_FRACTION) -> float:
    """S2 authors' equation; subtract linker N once, before dividing by PEI N."""
    if finite(mass_gain_g_g_mof, "W") < 0:
        raise ValueError("negative mass gain")
    fraction(nitrogen_g_g_composite, "N")
    fraction(host_nitrogen_g_g_mof, "N_host")
    positive(pei_nitrogen_g_g_pei, "N_PEI")
    fraction(pei_nitrogen_g_g_pei, "N_PEI")
    return (nitrogen_g_g_composite - host_nitrogen_g_g_mof / (1 + mass_gain_g_g_mof)) / pei_nitrogen_g_g_pei


def s2_composition(mass_gain_g_g_mof: float, pei_g_g_as_prepared: float,
                   branch: str) -> Composition:
    if finite(mass_gain_g_g_mof, "W") < 0:
        raise ValueError("negative mass gain")
    fraction(pei_g_g_as_prepared, "PEI_exp")
    h = 1 / (1 + mass_gain_g_g_mof)
    # Also validate the initial composition when taking the volatile branch.
    original = Composition(h, pei_g_g_as_prepared, 1 - h - pei_g_g_as_prepared)
    if branch == "s-I":
        return original
    if branch == "s-V":
        return Composition(h / (h + original.w), original.w / (h + original.w))
    raise ValueError("expected s-I or s-V")


def s100_composition(loading_label_pct: float, branch: str) -> Composition:
    if not 0 <= finite(loading_label_pct, "loading_pct") <= 100:
        raise ValueError("invalid loading percent")
    if branch == "w-C":
        w = loading_label_pct / 100
    elif branch == "w-F":
        w = loading_label_pct / (100 + loading_label_pct)
    else:
        raise ValueError("expected w-C or w-F")
    return Composition(1 - w, w)


def s100_q_composite(q_reported_mmol_g: float, composition: Composition, basis: str) -> float:
    positive(q_reported_mmol_g, "q_reported_mmol_g")
    if basis == "b-C":
        return q_reported_mmol_g
    if basis == "b-M":
        return q_reported_mmol_g * composition.h
    raise ValueError("expected b-C or b-M")


def capacity_mmol_g(composition: Composition, phi: float, q_host_mmol_g_mof: float,
                    n_n_mmol_g_pei: float, eta_mol_co2_mol_n: float) -> float:
    fraction(phi, "phi")
    positive(q_host_mmol_g_mof, "q_host_mmol_g_mof")
    positive(n_n_mmol_g_pei, "n_n_mmol_g_pei")
    if finite(eta_mol_co2_mol_n, "eta") < 0:
        raise ValueError("negative eta")
    return composition.h * phi * q_host_mmol_g_mof + composition.w * n_n_mmol_g_pei * eta_mol_co2_mol_n


def eta_min(composition: Composition, phi: float, q_host_mmol_g_mof: float,
            n_n_mmol_g_pei: float, q_target_mmol_g_composite: float) -> float | None:
    """None for w=0: the host-only inequality must be checked separately."""
    fraction(phi, "phi")
    positive(q_host_mmol_g_mof, "q_host_mmol_g_mof")
    positive(n_n_mmol_g_pei, "n_n_mmol_g_pei")
    positive(q_target_mmol_g_composite, "q_target_mmol_g_composite")
    if composition.w == 0:
        return None
    return (q_target_mmol_g_composite - composition.h * phi * q_host_mmol_g_mof) / (composition.w * n_n_mmol_g_pei)


def phi_crit(composition: Composition, gain_target: float, q_host_mmol_g_mof: float,
             n_n_mmol_g_pei: float, eta_mol_co2_mol_n: float) -> float | None:
    """Unclipped phi threshold; None when h=0 (test PEI-only inequality)."""
    positive(gain_target, "g")
    positive(q_host_mmol_g_mof, "q_host_mmol_g_mof")
    positive(n_n_mmol_g_pei, "n_n_mmol_g_pei")
    if finite(eta_mol_co2_mol_n, "eta") < 0:
        raise ValueError("negative eta")
    if composition.h == 0:
        return None
    return (gain_target - composition.w * n_n_mmol_g_pei * eta_mol_co2_mol_n / q_host_mmol_g_mof) / composition.h


def classify_eta(eta: float | None, ceiling: float = ETA_CEILING) -> str:
    positive(ceiling, "ceiling")
    if eta is None:
        return "host_only"
    finite(eta, "eta")
    if eta <= 0:
        return "A"
    # A lower stoichiometric ceiling takes precedence over the literature anchor.
    if eta > ceiling:
        return "D"
    return "B" if eta <= ETA_LIT else "C"


@dataclass(frozen=True)
class LineInterval:
    phi_low: float | None
    phi_high: float | None
    eta_at_phi0: float | None
    eta_at_phi1: float | None
    status: str


def analog_interval(composition: Composition, q_comp_mmol_g: float, q_host_mmol_g_mof: float,
                    n_n_mmol_g_pei: float, ceiling: float = ETA_CEILING) -> LineInterval:
    positive(ceiling, "ceiling")
    a = eta_min(composition, 0, q_host_mmol_g_mof, n_n_mmol_g_pei, q_comp_mmol_g)
    b = eta_min(composition, 1, q_host_mmol_g_mof, n_n_mmol_g_pei, q_comp_mmol_g)
    if a is None:
        phi = q_comp_mmol_g / (composition.h * q_host_mmol_g_mof) if composition.h else math.inf
        return LineInterval(phi if phi <= 1 else None, phi if phi <= 1 else None,
                            None, None, "host_only" if phi <= 1 else "host_only_incompatible")
    slope = a - b
    if slope == 0:
        return LineInterval(0 if 0 <= a <= ceiling else None, 1 if 0 <= a <= ceiling else None,
                            a, b, "admissible" if 0 <= a <= ceiling else "entirely_above_ceiling")
    low, high = max(0., (a - ceiling) / slope), min(1., a / slope)
    if low > high:
        return LineInterval(None, None, a, b,
                            "entirely_above_ceiling" if b > ceiling else "entirely_below_zero")
    return LineInterval(low, high, a, b, "admissible")


def gain_pet(composition: Composition, phi: float, k: float, gain_analog: float) -> float:
    fraction(phi, "phi")
    positive(k, "k")
    positive(gain_analog, "G_analog")
    a = composition.h * phi
    return a * (1 - 1 / k) + gain_analog / k


def k_crit(composition: Composition, phi: float, gain_analog: float, gain_target: float) -> float:
    """Largest positive k satisfying G_PET>=g, for g>=h*phi.

    0 denotes an empty positive-k set; inf denotes no upper bound. No
    restriction to the plotting range [0.8, 1.5] is imposed.
    """
    fraction(phi, "phi")
    positive(gain_analog, "G_analog")
    positive(gain_target, "g")
    a = composition.h * phi
    if gain_target < a:
        raise ValueError("upper-threshold definition requires g >= h*phi")
    if gain_target == a:
        return math.inf if gain_analog >= a else 0.
    return max(0., (gain_analog - a) / (gain_target - a))


def kstar_all(composition: Composition, gain_analog: float, gain_target: float) -> float:
    """All phi in [0,1], including k<1. For G>=g>=1 this is exactly G/g.

    For G<g the minimum is at phi=1 instead: G/g alone would be an
    incorrect guarantee below k=1. There is then no feasible k>=1.
    """
    return min(k_crit(composition, phi, gain_analog, gain_target) for phi in (0., 1.))


def kstar_admissible(composition: Composition, gain_analog: float, gain_target: float,
                     interval: LineInterval) -> float | None:
    if interval.phi_low is None:
        return None
    return min(k_crit(composition, phi, gain_analog, gain_target)
               for phi in (interval.phi_low, interval.phi_high))


def linker_inventory(composition: Composition, nh2_linker_mole_fraction: float,
                     linkers_per_zr6: float = 6., cap_mass_g_mol_zr6: float = 0.) -> dict:
    """Stoichiometric inventory per kg composite. Missing caps must be explicit.

    For defective counts, cap_mass=0 is only a skeleton upper bound on
    linker content, never an experimentally established dry composition.
    """
    f = fraction(nh2_linker_mole_fraction, "NH2 linker mole fraction")
    if not 0 < finite(linkers_per_zr6, "linkers_per_zr6") <= 6:
        raise ValueError("expected 0 < linkers_per_zr6 <= 6")
    if finite(cap_mass_g_mol_zr6, "cap_mass") < 0:
        raise ValueError("negative capping mass")
    linker_molar_mass = (1 - f) * M_BDC_LINKER_G_MOL + f * M_NH2_BDC_LINKER_G_MOL
    formula_mass = M_NODE_G_MOL + linkers_per_zr6 * linker_molar_mass + cap_mass_g_mol_zr6
    mol_linker_per_kg = 1000 * composition.h / formula_mass * linkers_per_zr6
    bdc_mol = mol_linker_per_kg * (1 - f)
    return dict(formula_mass_g_mol_zr6=formula_mass,
                linker_mol_kg_composite=mol_linker_per_kg,
                linker_bound_g_kg_composite=mol_linker_per_kg * linker_molar_mass,
                bdc_acid_equivalent_g_kg_composite=bdc_mol * M_BDC_ACID_G_MOL,
                nh2_bdc_acid_equivalent_g_kg_composite=mol_linker_per_kg * f * (M_NH2_BDC_LINKER_G_MOL + 2.016),
                pet_theoretical_g_kg_composite=bdc_mol * M_PET_REPEAT_G_MOL,
                pet_linker_mole_fraction=1 - f,
                pet_fragment_mass_fraction=bdc_mol * M_BDC_LINKER_G_MOL / 1000,
                nitrogen_linker_mmol_g_composite=mol_linker_per_kg * f)
