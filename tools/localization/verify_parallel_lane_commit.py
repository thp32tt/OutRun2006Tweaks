#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
head = os.environ.get("VERIFY_HEAD", "").strip() or "HEAD"
message = subprocess.check_output(["git", "log", "-1", "--pretty=%B", head], cwd=ROOT, text=True)
m = re.search(r"\[AUTO:(LOCALIZATION-LOCALIZATION_([ABCE])-\d+)\]", message)
if not m:
    print("parallel-lane-gate: commit is not a controller localization task; no lane restriction applied")
    raise SystemExit(0)

task_id, lane = m.group(1), m.group(2)
before = os.environ.get("VERIFY_BEFORE", "").strip() or subprocess.check_output(["git", "rev-parse", f"{head}^"], cwd=ROOT, text=True).strip()
changed = subprocess.check_output(["git", "diff", "--name-only", before, head], cwd=ROOT, text=True).splitlines()

shared = {
    "localization/resume_state.json",
    "localization/WORKLOG.md",
    "localization/progress.json",
    "localization/progress/progress.json",
    "localization/progress/STATUS.md",
    "localization/graphics/asset_queue.csv",
}

if lane in {"A", "B", "E"}:
    bad_shared = sorted(set(changed) & shared)
    if bad_shared:
        print(f"{task_id}: A/B parallel production may not modify shared state:")
        for p in bad_shared:
            print(" -", p)
        raise SystemExit(1)

    allowed_role = f"localization/graphics/role_{lane}/"
    wrong_role = [
        p for p in changed
        if p.startswith("localization/graphics/role_")
        and not p.startswith(allowed_role)
    ]
    if wrong_role:
        print(f"{task_id}: lane {lane} wrote another lane's role directory:")
        for p in wrong_role:
            print(" -", p)
        raise SystemExit(1)

    queue_csv = subprocess.check_output(
        ["git", "show", f"{head}:localization/graphics/asset_queue.csv"],
        cwd=ROOT,
        text=True,
    )
    by_basename: dict[str, list[int]] = {}
    with io.StringIO(queue_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                idx = int(row["index"])
            except (KeyError, TypeError, ValueError):
                continue
            name = pathlib.PurePosixPath(row.get("path", "")).name.lower()
            if name:
                by_basename.setdefault(name, []).append(idx)

    expected_remainder = {"A": 0, "B": 1, "E": 2}[lane]
    shard_errors = []
    for p in changed:
        if not p.lower().endswith(".dds"):
            continue
        name = pathlib.PurePosixPath(p).name.lower()
        indices = by_basename.get(name, [])
        if len(indices) == 1 and indices[0] % 3 != expected_remainder:
            shard_errors.append((p, indices[0]))
    if shard_errors:
        print(f"{task_id}: DDS changed outside lane {lane} modulo-3 shard:")
        for p, idx in shard_errors:
            print(f" - index={idx} {p}")
        raise SystemExit(1)

    # Post-reset graphics candidates are fail-closed: a DDS change must carry
    # clean-generation QA evidence from the same lane. Historical candidates
    # cannot be promoted by a controller task without these records.
    dds_changes = [p for p in changed if p.lower().endswith(".dds")]
    if dds_changes:
        evidence_prefix = f"localization/graphics/role_{lane}/"
        evidence = [p for p in changed if p.startswith(evidence_prefix) and (p.endswith(".json") or p.endswith(".png") or p.endswith(".jpg"))]
        required_tokens = ("CLEAN", "SOURCE", "CANDIDATE", "COMPARE", "QA", "MASK")
        if not any(any(t in pathlib.PurePosixPath(p).name.upper() for t in required_tokens) for p in evidence):
            print(f"{task_id}: DDS change blocked: missing post-reset clean-generation QA evidence")
            raise SystemExit(1)

    run_prefix = "docs/automation/runs/"
    run_records = [p for p in changed if p.startswith(run_prefix) and task_id in p]
    if not run_records:
        print(f"{task_id}: missing unique durable task record under docs/automation/runs/")
        raise SystemExit(1)

elif lane == "C":
    # C is the independent batch QA consumer and may reconcile shared state.
    pass

print(f"PARALLEL_LANE_COMMIT_OK task={task_id} lane={lane} changed={len(changed)}")
