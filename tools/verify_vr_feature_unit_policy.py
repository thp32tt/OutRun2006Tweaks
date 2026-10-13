#!/usr/bin/env python3
"""DX9Ex whole-function guard: one visible defect through root cause, code, regression and CI.

Historical <=00771 task records are grandfathered. New 00772+ visual tasks must
name exactly one symptom from the canonical feature catalog. This verifier
proves the *record contract*, not live HMD correctness or Docker deployment.
"""
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
SHA = re.compile(r"[0-9a-f]{40}")
POSITIVE = {"PASS", "PASS_BUILD", "PASS_EXACT_SHA", "SUCCESS_EXACT_SHA"}
TERMINAL = ("COMPLETE", "DONE", "PASS")


def _substantive(value: object, length: int = 12) -> bool:
    return isinstance(value, str) and len(value.strip()) >= length


def validate(record: dict, policy: dict) -> list[str]:
    task_id = record.get("task_id", "")
    match = re.fullmatch(r"CONVERSION-DX9EX-(\d{5})", str(task_id))
    if not match:
        return ["invalid DX9Ex TASK_ID"]
    if int(match.group(1)) < policy["effective_from_task_number"]:
        return []  # Never retroactively invalidate completed/active historical jobs.
    errors: list[str] = []
    fid = record.get("feature_id")
    contract = record.get("feature_contract")
    if not _substantive(fid, 8):
        errors.append("stable per-function feature_id required")
    if not isinstance(contract, dict):
        return errors + ["feature_contract required for one whole function"]
    if contract.get("feature_id") != fid:
        errors.append("feature_contract.feature_id mismatch")
    if not _substantive(contract.get("goal"), 32):
        errors.append("goal must describe full user-visible behavior")
    if not _substantive(contract.get("scope_boundary"), 16):
        errors.append("scope_boundary must exclude adjacent unrelated features")
    listed = {f["feature_id"]: f for f in policy.get("feature_catalog", [])}
    definition = listed.get(fid)
    if definition is None:
        if record.get("feature_class") not in {"MEASURED_PERFORMANCE", "CRITICAL_BLOCKER"}:
            errors.append("visual feature must be one registered symptom (umbrella banned)")
        if not _substantive(contract.get("special_work_evidence"), 24):
            errors.append("nonvisual feature requires measured blocker/performance evidence")
    else:
        if record.get("symptom_id") != definition["symptom_id"]:
            errors.append("symptom_id must match canonical one-defect catalog")
        if contract.get("symptom_id") != definition["symptom_id"]:
            errors.append("feature_contract.symptom_id must match one defect")
        if record.get("feature_class") not in (None, "USER_VISIBLE_VISUAL_DEFECT"):
            errors.append("registered visual feature class changed")
    stages = contract.get("trace_stages")
    if not isinstance(stages, list) or len(stages) < 3 or any(not _substantive(x, 10) for x in stages):
        errors.append("trace plan must cover at least three original→Draw→eye stages")
    parts = contract.get("subcomponents")
    if not isinstance(parts, list) or len(parts) < 2 or any(not _substantive(x, 8) for x in parts):
        errors.append("one offset/slider is not a full feature; need two real subcomponents")
    items = contract.get("acceptance_items")
    if not isinstance(items, list) or len(items) < policy["minimum_acceptance_items"]:
        return errors + ["at least three feature acceptance items required"]
    ids, categories, areas = [], set(), set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("acceptance item must be a dict")
            continue
        key = item.get("id")
        if not _substantive(key, 1):
            errors.append("acceptance item id missing")
        else:
            ids.append(key)
        categories.add(item.get("category"))
        area = item.get("behavior_area")
        if _substantive(area, 2):
            areas.add(area)
        if not _substantive(item.get("expected_behavior"), 12):
            errors.append("acceptance item lacks verifiable expected behavior")
    if len(ids) != len(items) or len(set(ids)) != len(ids):
        errors.append("duplicate/missing acceptance IDs")
    if not set(policy["required_categories"]).issubset(categories):
        errors.append("whole-feature acceptance requires end-to-end, fallback and integration")
    if len(areas) < policy["minimum_behavior_areas"]:
        errors.append("single-technical-layer microtask rejected")
    status = str(record.get("status") or "").upper()
    terminal = status.startswith(TERMINAL)
    if terminal:
        results = record.get("acceptance_results")
        if not isinstance(results, dict) or any(results.get(i) not in POSITIVE for i in ids):
            errors.append("terminal completion requires all feature acceptance items PASS")
        if record.get("automation_validation") not in {"PASS", "PASS_EXACT_SHA"}:
            errors.append("terminal completion requires exact-SHA CI PASS")
        validated = record.get("validation_bearing_result_sha")
        if not isinstance(validated, str) or SHA.fullmatch(validated) is None:
            errors.append("terminal completion requires a validation-bearing full SHA")
        material = record.get("material_result_sha")
        if not isinstance(material, str) or SHA.fullmatch(material) is None:
            errors.append("terminal completion requires original material source SHA")
        changed = record.get("changed_files") or []
        if not isinstance(changed, list) or not any(
            isinstance(x, str) and (x.startswith("src/") or x.startswith("vrhost/"))
            and x.endswith((".cpp", ".hpp", ".h", ".c")) for x in changed
        ):
            errors.append("terminal visual feature needs real C/C++ source material, not bookkeeping")
        diagnosis = record.get("diagnosis")
        if not isinstance(diagnosis, dict):
            errors.append("deep root cause evidence required before terminal DONE")
        else:
            fields = policy["diagnosis_required_for_terminal"]["required_fields"]
            for field in fields:
                v = diagnosis.get(field)
                if field in {"source_trace", "alternatives_rejected"}:
                    count = 3 if field == "source_trace" else 1
                    if not isinstance(v, list) or len(v) < count or any(not _substantive(x, 16) for x in v):
                        errors.append("deep diagnosis missing evidence: " + field)
                elif not _substantive(v, 24):
                    errors.append("deep diagnosis missing evidence: " + field)
            if definition and _substantive(diagnosis.get("original_evidence"), 24):
                if not _substantive(diagnosis.get("eye_ownership"), 16):
                    errors.append("visual symptom must explain per-eye ownership")
        if not isinstance(record.get("ci_evidence"), (dict, list)):
            errors.append("terminal feature needs exact-SHA CI evidence")
    if record.get("runtime_validation") == "PASS" and not record.get("runtime_evidence"):
        errors.append("Quest3/VDXR visual PASS needs matching hardware evidence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-head", action="store_true")
    parser.add_argument("--check-run", type=Path)
    args = parser.parse_args()
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema_version") != 2 or len(policy.get("feature_catalog", [])) < 6:
        print("DX9Ex feature catalog FAIL: missing per-function granular policy")
        return 1
    if args.check_head:
        message = subprocess.check_output(
            ["git", "log", "-1", "--format=%B"], cwd=ROOT, text=True
        )
        found = PATTERN.search(message)
        if not found or int(found.group(1)) < policy["effective_from_task_number"]:
            print("DX9Ex function policy: historical/metadata-only HEAD exempt")
            return 0
        run_path = RUNS / (found.group(0) + ".json")
        if not run_path.is_file():
            print("DX9Ex function policy FAIL: run record missing", run_path)
            return 1
    elif args.check_run:
        run_path = args.check_run
    else:
        print("DX9Ex whole-function policy schema PASS (no selected run)")
        return 0
    errors = validate(json.loads(run_path.read_text(encoding="utf-8")), policy)
    if errors:
        print("DX9Ex whole-function policy FAIL:", "; ".join(errors))
        return 1
    print("DX9Ex whole-function policy PASS:", run_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
