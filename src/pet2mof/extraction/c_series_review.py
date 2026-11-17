"""Per-series review authority tied to exact coordinate bytes."""
import hashlib
import json


T011V2_REF = "reviews/T011v2_reverification.md"
T011V2_SHA256 = "1dbdb8098253de4f7d3c66d337b349bd2d3689af11ef4e7a5f12b60e0d798fd4"
T011V2_COORDINATES = {
    "S105-Fig8A|UiO-66": (46, "0a0d07d471ad618bb281b93ddbbfc49d45390ba997d945837c82ab0c124ccb78"),
    "S105-Fig8A|UiO-66/GO": (39, "9e1e995e4b2195b8d2374301e917a82018f47612426c10f55980b00678370634"),
    "S105-Fig8C|UiO-66/GO": (39, "433ea951054167d8cdbd2a31a6a14d1347fe8f20c3fae14e9333071525ce100d"),
    "S105-Fig9|UiO-66": (46, "1b732b68eadb25b85baf4cb31c6e45e47a151c270d5b48f016742862a2b023d2"),
    "S105-Fig9|UiO-66-NH2": (50, "edfc654e903a846539209274aadd34eced59051ff959d67c4506fded5e3e727b"),
    "S105-Fig9|UiO-66/GO": (47, "f24f7f7f3e2d4a64de5698df90d5271af3383efd7d1168c00eebcb2df9e44cef"),
    "S106-Fig4|UiO-66_160": (35, "2aa8968c1ae89c1f7a678148b05ce83772e6d7d891c0dd647bdd15856b3df420"),
}


def coordinate_bytes(rows, fields):
    return "".join(",".join(str(row[k]) for k in fields) + "\n" for row in rows).encode()


def review_status(root, figure, material, rows):
    baseline = json.loads((root / "data/extraction/digitization/T011b/baseline.json").read_text())
    review = root / baseline["review_ref"]
    if hashlib.sha256(review.read_bytes()).hexdigest() != baseline["review_sha256"]:
        raise ValueError("T011v review changed; re-establish review authority")
    verdicts = {}
    for line in review.read_text().splitlines():
        cells = [v.strip() for v in line.strip("|").split("|")]
        if len(cells) == 10 and cells[0].startswith("T011-"):
            verdicts[cells[0].removeprefix("T011-") + "|" + cells[1]] = cells[8]
    key = figure + "|" + material
    prior = baseline["series"][key]
    digest = hashlib.sha256(coordinate_bytes(rows, baseline["coordinate_fields"])).hexdigest()
    unchanged = digest == prior["coordinate_bytes_sha256"] and len(rows) == prior["rows"]
    accepted = verdicts[key] == prior["T011v_verdict"] == "verified" and unchanged
    accepted_v2 = False
    if key in T011V2_COORDINATES:
        if hashlib.sha256((root / T011V2_REF).read_bytes()).hexdigest() != T011V2_SHA256:
            raise ValueError("T011v2 review changed; re-establish review authority")
        count, reviewed_digest = T011V2_COORDINATES[key]
        accepted_v2 = len(rows) == count and digest == reviewed_digest
    reviewer = "T011v2" if accepted_v2 else "T011v" if accepted else None
    return dict(status="verified" if reviewer else "provisional",
                reviewer=reviewer,
                review_ref=T011V2_REF if accepted_v2 else baseline["review_ref"] if accepted else None,
                pending_review=None if reviewer else "T011v2",
                baseline_coordinate_bytes_sha256=prior["coordinate_bytes_sha256"],
                coordinate_bytes_sha256=digest, coordinates_byte_identical=unchanged)
