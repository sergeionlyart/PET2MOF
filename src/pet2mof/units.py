"""CO2 units with explicit STP convention and PEI composite mass fraction."""

import math
import re

CO2_MOLAR_MASS_G_MOL = 44.0095
STP_MOLAR_VOLUME_CM3_MOL = 22414.0  # RT/P at 273.15 K, 101.325 kPa, rounded
_SUPER = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


def parse_number(value):
    text = str(value).strip().replace("−", "-").replace("–", "-")
    text = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)", lambda m: "10^" + m[1].translate(_SUPER), text)
    text = text.replace(" ", "").replace("**", "^").replace("×", "*").replace("·", "*")
    text = re.sub(r"(?<=10)([+-]\d+)$", r"^\1", text) if "*10" in text else text
    match = re.fullmatch(r"(?:(?P<m>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\*)?10\^(?P<e>[+-]?\d+)", text)
    try:
        result = float(match["m"] or 1) * 10.0 ** int(match["e"]) if match else float(text)
    except (ValueError, OverflowError):
        raise ValueError("invalid scientific number") from None
    if not math.isfinite(result):
        raise ValueError("number must be finite")
    return result


def _capacity_factor(unit, molar_mass, stp_volume):
    factors = {"mmol/g": 1.0, "mol/kg": 1.0, "mol/g": 1000.0,
               "mmol/kg": 0.001, "mg/g": 1 / molar_mass,
               "cm3(STP)/g": 1000 / stp_volume, "wt%": 10 / molar_mass}
    if unit not in factors:
        raise ValueError("unknown capacity unit")
    return factors[unit]


def convert_capacity(value, from_unit, to_unit, *, molar_mass=CO2_MOLAR_MASS_G_MOL,
                     stp_molar_volume=STP_MOLAR_VOLUME_CM3_MOL):
    """Return scalar; wt% is grams CO2 per 100 grams dry adsorbent.

    Default STP volume is the ideal-gas RT/P at 273.15 K and 101.325 kPa,
    rounded to 22414 cm3/mol (22.414 cm3/mmol), independent of sample T.
    """
    if not math.isfinite(molar_mass) or molar_mass <= 0 or not math.isfinite(stp_molar_volume) or stp_molar_volume <= 0:
        raise ValueError("positive molecular mass and STP volume required")
    return parse_number(value) * _capacity_factor(from_unit, molar_mass, stp_molar_volume) / _capacity_factor(to_unit, molar_mass, stp_molar_volume)


def convert_pressure(value, from_unit, to_unit):
    factors = {"bar": 100000.0, "kPa": 1000.0, "MPa": 1e6, "Pa": 1.0,
               "mbar": 100.0, "Torr": 101325 / 760, "mmHg": 101325 / 760,
               "atm": 101325.0}
    if from_unit not in factors or to_unit not in factors:
        raise ValueError("unknown pressure unit")
    return parse_number(value) * factors[from_unit] / factors[to_unit]


def normalize_capacity(value, from_basis, to_basis, *, pei_mass_fraction):
    """PEI fraction is m_PEI / m_composite, NOT m_PEI / m_MOF."""
    fraction = parse_number(pei_mass_fraction)
    if not 0 <= fraction < 1 or from_basis not in {"mof", "composite"} or to_basis not in {"mof", "composite"}:
        raise ValueError("unknown basis or invalid PEI composite mass fraction")
    value = parse_number(value)
    if from_basis == to_basis:
        return value
    return value * (1 - fraction) if from_basis == "mof" else value / (1 - fraction)
