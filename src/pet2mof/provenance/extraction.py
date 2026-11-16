import json
import re
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import jsonschema
import yaml


def schema():
    bundled = files("pet2mof.provenance").joinpath("extraction.schema.json")
    if bundled.is_file():
        return json.loads(bundled.read_text(encoding="utf-8"))
    # Editable source checkout; the wheel includes the same canonical file.
    path = Path(__file__).resolve().parents[3] / "data/extraction/schema/extraction.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_extraction(record):
    checker = jsonschema.FormatChecker()

    @checker.checks("date-time", raises=ValueError)
    def date_time(value):
        if not isinstance(value, str):
            return True
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
            return False
        return datetime.fromisoformat(value.upper()).utcoffset() is not None

    jsonschema.Draft202012Validator(schema(), format_checker=checker).validate(record)
    return record


def write_extraction(path, record):
    validate_extraction(record)
    with Path(path).open("x", encoding="utf-8") as stream:
        yaml.safe_dump(record, stream, sort_keys=False)


def read_extraction(path):
    with Path(path).open(encoding="utf-8") as stream:
        return validate_extraction(yaml.safe_load(stream))


def require_measurement(record, *, allow_provisional=False):
    if record.get("data_kind") not in {"measured_table", "digitized_markers", "text_value"}:
        raise ValueError("author fits, simulations and unknown kinds are not measurements")
    if record.get("status") == "verified":
        return record
    if allow_provisional and record.get("status") == "provisional" and record.get("sensitivity_only") is True:
        return record
    raise ValueError("unverified record; provisional use requires sensitivity_only")
