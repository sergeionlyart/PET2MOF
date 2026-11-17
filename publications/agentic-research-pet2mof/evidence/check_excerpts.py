#!/usr/bin/env python3
"""Read-only checks of T050 evidence; run with python3 -I, stdlib only.

No scientific code is imported or executed. Git reads are confined to explicit
public paths. Cleaning records contain byte ranges in the ORIGINAL Git blob;
only deletion is supported, with a hash of each deleted range.
"""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[2]
PROMPTS = EVIDENCE.parent / "prompts"
FAILURES = []


def check(ok, message):
    if not ok:
        FAILURES.append(message)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def blob(commit, path):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("expected full commit SHA")
    parts = Path(path).parts
    if Path(path).is_absolute() or ".." in parts or any(
        x == "private" or x.startswith(".env") for x in parts
    ):
        raise ValueError("non-public source path")
    return git("show", f"{commit}:{path}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def table(name):
    with (EVIDENCE / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def timestamp(value):
    if "-" not in value:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def commit_time(commit):
    return timestamp(git("show", "-s", "--format=%aI", commit).decode().strip())


def references(value):
    if value == "unknown":
        return []
    return [item.split(":", 1) for item in value.split(" | ")]


def main():
    manifests = table("prompts_manifest.csv")
    check(6 <= len(manifests) <= 8, "prompt count outside 6–8")
    check(len({r['prompt_id'] for r in manifests}) == len(manifests), "duplicate prompt ID")
    excerpt_count = 0
    for row in manifests:
        label = row["prompt_id"]
        raw = blob(row["commit"], row["source_path"])
        check(digest(raw) == row["blob_sha256"], f"{label}: source hash")
        check(timestamp(row["date_utc"]) == commit_time(row["commit"]), f"{label}: date")
        exact = True
        for key in ("excerpt_1", "excerpt_2"):
            excerpt = row[key]
            if not excerpt:
                continue
            excerpt_count += 1
            matched = excerpt.encode("utf-8") in raw
            exact &= matched
            check(matched, f"{label}: {key} not an exact byte substring")
            check(len(excerpt.split()) <= 120, f"{label}: {key} over 120 words")
        check(bool(row["excerpt_1"]), f"{label}: missing excerpt")
        check(row["excerpt_exact"] == str(exact).lower(), f"{label}: excerpt_exact flag")
        cleaning = row["cleaning_edits"]
        edits = [] if cleaning == "без правок" else json.loads(cleaning)
        last_end = 0
        for edit in edits:
            start, end = edit["start_byte"], edit["end_byte"]
            if not (last_end <= start < end <= len(raw)):
                raise ValueError(f"{label}: overlapping or invalid cleaning ranges")
            check(bool(edit["reason"]), f"{label}: unexplained cleaning")
            check(digest(raw[start:end]) == edit["removed_sha256"], f"{label}: removed hash")
            last_end = end
        cleaned = raw
        for edit in reversed(edits):
            cleaned = cleaned[:edit["start_byte"]] + cleaned[edit["end_byte"]:]
        header = (
            "<!-- PET2MOF historical prompt\n"
            f"source_path: {row['source_path']}\n"
            f"commit: {row['commit']}\n"
            f"blob_sha256: {row['blob_sha256']}\n"
            f"cleaning_edits: {cleaning}\n-->\n"
        ).encode("utf-8")
        copies = list(PROMPTS.glob(f"{label}-*.md"))
        check(len(copies) == 1, f"{label}: expected exactly one copy")
        if len(copies) == 1:
            check(copies[0].read_bytes() == header + cleaned, f"{label}: copy mismatch")
        for commit, path in references(row["follow_refs"]):
            blob(commit, path)

    chronology = table("chronology.csv")
    roles = {"owner", "owner_with_chatgpt_prep", "lead_claude_code", "executor_codex", "reviewer_codex", "ready_input"}
    check(40 <= len(chronology) <= 80, "chronology count outside 40–80")
    check(len({r['event_id'] for r in chronology}) == len(chronology), "duplicate event ID")
    for row in chronology:
        blob(row["commit"], row["source_path"])
        for key in ("input_ref", "artifact_ref"):
            for commit, path in references(row[key]):
                blob(commit, path)
        check(row["actor_role"] in roles, f"{row['event_id']}: role")
        if row["time_utc"]:
            check(row["time_utc"].endswith("Z"), f"{row['event_id']}: not UTC")
            timestamp(row["time_utc"])
        else:
            check("unknown" in row["problem_found"], f"{row['event_id']}: unexplained unknown time")

    runs = table("agent_runs.csv")
    stats = table("stage_stats.csv")
    check({r['stage'] for r in stats} == {"setup", "TASK-001", "TASK-002", "TASK-003"}, "stage coverage")
    for row in stats:
        stage = row["stage"]
        selected = [r for r in runs if r["stage"] == stage]
        source = blob(row["agent_runs_commit"], "publications/agentic-research-pet2mof/evidence/agent_runs.csv")
        check(digest(source) == row["agent_runs_sha256"], f"{stage}: run-source hash")
        check(source == (EVIDENCE / "agent_runs.csv").read_bytes(), f"{stage}: run-source changed")
        check(int(row["agent_runs"]) == len(selected), f"{stage}: run count")
        total = sum(int(r["duration_s"]) for r in selected)
        check(int(row["agent_duration_sum_s"]) == total, f"{stage}: duration sum")
        intervals = []
        for run in selected:
            start, end = timestamp(run["started_utc"]), timestamp(run["finished_utc"])
            check((end - start).total_seconds() == int(run["duration_s"]), f"{run['run']}: duration")
            intervals.extend([(start, 1), (end, -1)])
        active = peak = 0
        for _, change in sorted(intervals):  # finish (-1) before start (+1): [start,end)
            active += change
            peak = max(peak, active)
        check(int(row["max_concurrent_runs"]) == peak, f"{stage}: concurrency")
        for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
            value = str(sum(int(r[key]) for r in selected)) if all(r[key] for r in selected) else "unknown"
            check(row[key] == value, f"{stage}: {key}")
        fresh = str(sum(int(r['input_tokens']) - int(r['cached_input_tokens']) for r in selected)) if all(r['input_tokens'] and r['cached_input_tokens'] for r in selected) else "unknown"
        check(row["new_input_tokens"] == fresh, f"{stage}: new tokens")
        check(int(row["tokens_recorded_runs"]) == sum(bool(r['input_tokens']) for r in selected), f"{stage}: token coverage")
        start, end = timestamp(row["calendar_start_utc"]), timestamp(row["calendar_end_utc"])
        check((end - start).total_seconds() == int(row["calendar_duration_s"]), f"{stage}: calendar duration")
        check(start <= min(t for t, d in intervals if d == 1), f"{stage}: start excludes run")
        check(end >= max(t for t, d in intervals if d == -1), f"{stage}: end excludes run")
        for key in ("boundary_start_ref", "boundary_end_ref"):
            for commit, path in references(row[key]):
                blob(commit, path)
        passport_refs = references(row["passport_refs"])
        check(len(passport_refs) == int(row["counted_passports"]), f"{stage}: passport count")
        wall = 0.0
        for commit, path in passport_refs:
            passport = json.loads(blob(commit, path))
            check(passport["status"] == "completed" and passport["exit_code"] == 0, f"{path}: not counted")
            wall += passport["resources"]["elapsed_seconds"]
        if passport_refs:
            check(abs(wall - float(row["counted_process_wall_s"])) < 0.000001, f"{stage}: passport elapsed sum")
        check(row["pure_numerical_compute_s"] == "unknown", f"{stage}: undocumented kernel timing")
        check(row["environment_preparation_s"] == "unknown", f"{stage}: undocumented setup time")
        check(row["lead_usage"] == "unknown", f"{stage}: undocumented lead usage")

    print(f"Prompts: {len(manifests)}; exact excerpts checked: {excerpt_count}; copies checked: {len(manifests)}")
    print(f"Chronology: {len(chronology)} events; direct source/input/artifact references checked")
    print(f"Stage statistics: {len(stats)} stages; {len(runs)} agent runs; intervals/tokens/passport sums checked")
    print(f"Mismatches: {len(FAILURES)}")
    for failure in FAILURES:
        print("FAIL:", failure)
    return bool(FAILURES)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
