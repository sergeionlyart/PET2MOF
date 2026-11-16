import math

import jsonschema
import pytest

from pet2mof.extraction.digitize import AxisCalibration, digitize_markers, read_project, write_project
from pet2mof.provenance.extraction import require_measurement, validate_extraction, write_extraction, read_extraction
from pet2mof.units import convert_capacity, convert_pressure, normalize_capacity, parse_number

pytestmark = pytest.mark.ocr


@pytest.mark.parametrize("text,expected", [("1.2×10−3", .0012), ("1.2e-3", .0012), ("10^-3", .001),
    ("−1.2E−3", -.0012), ("1.2×10⁻³", .0012), ("10**-3", .001)])
def test_exponents(text, expected):
    assert parse_number(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["unknown", "nan", "inf", "1e999", "2+3", "__import__('os')"])
def test_reject_non_numbers(text):
    with pytest.raises(ValueError):
        parse_number(text)


def test_capacity_pressure_normalization():
    assert convert_capacity(44.0095, "mg/g", "mmol/g") == pytest.approx(1)
    assert convert_capacity(22.414, "cm3(STP)/g", "mol/kg") == pytest.approx(1)
    assert convert_capacity(4.40095, "wt%", "mmol/g") == pytest.approx(1)
    assert convert_pressure(1, "bar", "kPa") == pytest.approx(100)
    assert convert_pressure(760, "Torr", "atm") == pytest.approx(1)
    for unit in ("bar", "kPa", "Pa", "mbar", "Torr", "atm"):
        assert convert_pressure(convert_pressure(1.2, "bar", unit), unit, "bar") == pytest.approx(1.2)
    for unit in ("mmol/g", "mol/kg", "mg/g", "cm3(STP)/g", "wt%"):
        assert convert_capacity(convert_capacity(1.2, "mmol/g", unit), unit, "mmol/g") == pytest.approx(1.2)
    assert normalize_capacity(2, "mof", "composite", pei_mass_fraction=.25) == 1.5
    assert normalize_capacity(1.5, "composite", "mof", pei_mass_fraction=.25) == 2
    with pytest.raises(ValueError):
        convert_pressure(1, "psi", "bar")
    with pytest.raises(ValueError):
        convert_capacity(1, "unknown", "mg/g")
    with pytest.raises(ValueError):
        normalize_capacity(1, "mof", "composite", pei_mass_fraction=1)


def test_log_axis_uncertainty_project_roundtrip(tmp_path):
    x = AxisCalibration(0, 1, 100, 100, "log")
    y = AxisCalibration(100, 0, 0, 10)
    point = digitize_markers([[50, 50]], x, y, sigma_pixel=1)[0]
    assert point["x"] == pytest.approx(10)
    assert point["y"] == pytest.approx(5)
    assert point["sigma_x"] == pytest.approx(10 * math.log(100) / 100)
    assert point["sigma_y"] == pytest.approx(.1)
    path = tmp_path / "test.digitization.yaml"
    project = write_project(path, image_sha256="a" * 64, x_axis=x, y_axis=y,
        series=[dict(name="markers", data_kind="digitized_markers", pixels=[[50, 50]], sigma_pixel=1)], code_version="abc123")
    assert read_project(path) == project
    with pytest.raises(FileExistsError):
        write_project(path, **{k: v for k, v in dict(image_sha256="a"*64, x_axis=x, y_axis=y, series=project["series"], code_version="abc123").items()})
    with pytest.raises(ValueError):
        AxisCalibration(0, 0, 10, 100, "log")


def record():
    return dict(extraction_id="E-test", source_id="S-test", doi="10.example/test", url=None,
        input_sha256="a" * 64, pdf_page=1, api_page_map={"1": 1}, figure_or_table="Table 1", region=None,
        tool="manual", tool_version="1", params={}, date="2026-11-16T00:00:00Z", raw_response_ref="private/ocr_cache/raw/example.json",
        unit_conversions=[], derived_sha256="b" * 64, status="verified", reviewer="independent-reviewer",
        corrections=[], error_estimate="unknown", data_kind="measured_table")


def test_extraction_schema_and_roundtrip(tmp_path):
    valid = record()
    assert validate_extraction(valid) is valid
    path = tmp_path / "E-test.yaml"
    write_extraction(path, valid)
    assert read_extraction(path) == valid
    for change in ({"status": "trusted"}, {"input_sha256": "bad"}, {"pdf_page": 0}, {"reviewer": None},
                   {"date": "tomorrow"}, {"doi": None, "url": None}):
        with pytest.raises(jsonschema.ValidationError):
            validate_extraction(valid | change)


def test_measurement_guard():
    assert require_measurement(record())
    for kind in ("author_fit", "simulation", "unknown"):
        with pytest.raises(ValueError):
            require_measurement(record() | {"data_kind": kind}, allow_provisional=True)
    for status in ("provisional", "excluded", None):
        with pytest.raises(ValueError):
            require_measurement(record() | {"status": status})
    with pytest.raises(ValueError):
        require_measurement(record() | {"status": "provisional"}, allow_provisional=True)
    assert require_measurement(record() | {"status": "provisional", "sensitivity_only": True}, allow_provisional=True)
    with pytest.raises(ValueError):
        require_measurement(record() | {"status": "excluded", "sensitivity_only": True}, allow_provisional=True)
