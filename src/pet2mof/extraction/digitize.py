"""Two-point, axis-aligned calibration, including inverted pixel y axes."""

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AxisCalibration:
    pixel_1: float
    value_1: float
    pixel_2: float
    value_2: float
    scale: str = "linear"

    def __post_init__(self):
        if self.scale not in {"linear", "log"}:
            raise ValueError("axis must be linear or log10")
        if not all(math.isfinite(v) for v in (self.pixel_1, self.pixel_2, self.value_1, self.value_2)):
            raise ValueError("finite calibration required")
        if self.pixel_1 == self.pixel_2 or self.value_1 == self.value_2:
            raise ValueError("distinct calibration points required")
        if self.scale == "log" and min(self.value_1, self.value_2) <= 0:
            raise ValueError("log axis requires positive values")

    def transform(self, pixel):
        if not math.isfinite(pixel):
            raise ValueError("finite pixel coordinate required")
        a, b = self.value_1, self.value_2
        if self.scale == "log":
            a, b = math.log10(a), math.log10(b)
        coordinate = a + (pixel - self.pixel_1) * (b - a) / (self.pixel_2 - self.pixel_1)
        return 10 ** coordinate if self.scale == "log" else coordinate

    def uncertainty(self, pixel, sigma_pixel):
        """First-order independent readout error; calibration-point errors excluded."""
        if not math.isfinite(sigma_pixel) or sigma_pixel < 0:
            raise ValueError("nonnegative finite pixel error required")
        if self.scale == "linear":
            slope = (self.value_2 - self.value_1) / (self.pixel_2 - self.pixel_1)
        else:
            slope = self.transform(pixel) * math.log(self.value_2 / self.value_1) / (self.pixel_2 - self.pixel_1)
        return abs(slope) * sigma_pixel


def digitize_markers(pixels, x_axis, y_axis, *, sigma_pixel):
    return [{"x": x_axis.transform(x), "y": y_axis.transform(y),
             "sigma_x": x_axis.uncertainty(x, sigma_pixel), "sigma_y": y_axis.uncertainty(y, sigma_pixel)} for x, y in pixels]


def validate_project(project):
    if not re.fullmatch(r"[0-9a-f]{64}", project["image_sha256"]) or not project["code_version"]:
        raise ValueError("image hash and code version required")
    for axis in ("x_axis", "y_axis"):
        AxisCalibration(**project[axis])
    if not isinstance(project["series"], list) or not project["series"]:
        raise ValueError("marker series required")
    for series in project["series"]:
        if not series["name"] or series["data_kind"] not in {"digitized_markers", "author_fit"}:
            raise ValueError("identify each series and its data kind")
        sigma = series["sigma_pixel"]
        if not math.isfinite(sigma) or sigma < 0:
            raise ValueError("pixel uncertainty required")
        for marker in series["pixels"]:
            if len(marker) != 2 or not all(math.isfinite(v) for v in marker):
                raise ValueError("finite x/y marker pixels required")
    return project


def write_project(path, *, image_sha256, x_axis, y_axis, series, code_version):
    path = Path(path)
    if not path.name.endswith(".digitization.yaml"):
        raise ValueError("use .digitization.yaml extension")
    project = validate_project({"image_sha256": image_sha256, "x_axis": asdict(x_axis),
                                "y_axis": asdict(y_axis), "series": series, "code_version": code_version})
    with path.open("x", encoding="utf-8") as stream:
        yaml.safe_dump(project, stream, sort_keys=False)
    return project


def read_project(path):
    with Path(path).open(encoding="utf-8") as stream:
        return validate_project(yaml.safe_load(stream))
