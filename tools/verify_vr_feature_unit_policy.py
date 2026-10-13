#!/usr/bin/env python3
"""Enforce functional feature units for DX9Ex new production tasks without touching legacy records."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/automation/DX9EX_FEATURE_UNIT_POLICY.json"
RUNS = ROOT / "docs/automation/runs"
PATTERN = re.compile(r"CONVERSION-DX9EX-(\d{5})")


def validate(record: dict, policy: dict) -> list[str]:
    task_id = record.get("task_id", "")
    match = re.fullmatch(r"CONVERSION-DX9EX-(\d{5})", task_id)
    if not match:
        return ["invalid DX9Ex TASK_ID"]
    if int(match.group(1)) < policy["effective_from_task_number"]:
        return []
    errors: list[str] = []
    fid = record.get("feature_id")
    contract = record.get("feature_contract")
    if not isinstance(fid, str) or not fid.strip():
        errors.append("new task must have a stable feature_id")
    if not isinstance(contract, dict):
        return errors + ["new task must provide feature_contract"]
    if contract.get("feature_id") != fid:
        errors.append("feature_contract.feature_id must equal feature_id")
    goal = contract.get("goal")
    if not isinstance(goal, str) or len(goal.strip()) < 24:
        errors.append("integrated functional goal is required")
    items = contract.get("acceptance_items")
    if not isinstance(items, list) or len(items) < policy["minimum_acceptance_items"]:
        return errors + ["at least three functional acceptance items are required"]
    ids, cats, areas = [], set(), set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("acceptance items must be objects")
            continue
        key = item.get("id")
        if not isinstance(key, str) or not key.strip():
            errors.append("each acceptance item must have an id")
        else:
            ids.append(key)
        cats.add(item.get("category"))
        area = item.get("behavior_area")
        if isinstance(area, str) and area.strip():
            areas.add(area.strip())
        expected = item.get("expected_behavior")
        if not isinstance(expected, str) or len(expected.strip()) < 12:
            errors.append("each item needs measurable expected_behavior")
    if len(ids) != len(items) or len(set(ids)) != len(ids):
        errors.append("duplicate or missing acceptance item ids")
    if not set(policy["required_categories"]).issubset(cats):
        errors.append("end-to-end, fallback/negative and integrated validation items required")
    if len(areas) < policy["minimum_behavior_areas"]:
        errors.append("one widget/one helper is not a feature; need multiple behavior areas")
    status = str(record.get("status") or "").upper()
    terminal = status.startswith(("COMPLETE", "DONE", "PASS"))
    if terminal:
        results = record.get("acceptance_results")
        if not isinstance(results, dict) or any(results.get(i) not in ("PASS", "PASS_BUILD", "PASS_EXACT_SHA") for i in ids):
            errors.append("cannot complete feature with pending acceptance items")
        if record.get("automation_validation") not in ("PASS", "PASS_EXACT_SHA"):
            errors.append("cannot complete feature without exact-SHA automation PASS")
        sha = record.get("validation_bearing_result_sha")
        if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            errors.append("terminal feature missing verified 40-char SHA")
    if record.get("runtime_validation") == "PASS" and not record.get("runtime_evidence"):
        errors.append("Quest3/VDXR PASS requires real runtime_evidence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-head", action="store_true")
    args = parser.parse_args()
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if args.check_head:
        message = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=ROOT, text=True)
        found = PATTERN.search(message)
        if not found or int(found.group(1)) < policy["effective_from_task_number"]:
            print("DX9Ex feature policy: legacy/metadata-only HEAD exempt")
            return 0
        task_id = found.group(0)
        path = RUNS / (task_id + ".json")
        if not path.is_file():
            print(f"DX9Ex feature policy FAIL: missing {path}")
            return 1
        errors = validate(json.loads(path.read_text(encoding="utf-8")), policy)
        if errors:
            print("DX9Ex feature policy FAIL: " + "; ".join(errors))
            return 1
        print("DX9Ex feature policy PASS:", task_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
