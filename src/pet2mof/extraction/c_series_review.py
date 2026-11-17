"""Per-series T011v authority, tied to the exact pre-fix coordinate bytes."""
import hashlib
import json


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
    return dict(status="verified" if accepted else "provisional",
                reviewer="T011v" if accepted else None,
                review_ref=baseline["review_ref"] if accepted else None,
                pending_review=None if accepted else "T011v2",
                baseline_coordinate_bytes_sha256=prior["coordinate_bytes_sha256"],
                coordinate_bytes_sha256=digest, coordinates_byte_identical=unchanged)
