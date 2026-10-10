#!/usr/bin/env python3
"""DX11 autonomous-work acceptance: real integration progress, never guard-only churn.

The controller must evaluate the selected new task before committing work.
CI rechecks the highest-numbered DX11 run record at the exact validation SHA.
Tasks through 00530 are grandfathered; existing owners and material SHAs are not rewritten.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "docs/automation/DX11_AUTODEV_EXECUTION_POLICY.json"
RUN_DIR = ROOT / "docs/automation/runs"
NAME = re.compile(r"^CONVERSION-DX11-(\d{5})\.json$")


def validate_policy(policy: dict) -> list[str]:
    errors: list[str] = []
    if policy.get("lane") != "DX11" or policy.get("target_branch") != "vr-dx11-native-r71":
        errors.append("lane/branch mismatch")
    if policy.get("effective_from_task_number") != 531:
        errors.append("unreviewed activation threshold")
    if policy.get("allowed_full_gate_plan") != "one_validation_bearing_sha":
        errors.append("final exact-SHA Gate must stay mandatory")
    ids = [x.get("id") for x in policy.get("milestones", [])]
    if not ids or len(ids) != len(set(ids)):
        errors.append("missing or duplicate milestone IDs")
    if "mono_native_draw" not in ids or "shader_parity_r175" not in ids:
        errors.append("missing end-to-end native Draw or known R175 dependency")
    if "first_live_game_draw" not in ids:
        errors.append("missing actual game Draw milestone")
    if policy.get("gameplay_direction_effective_from_task_number") != 537:
        errors.append("gameplay-first threshold missing or changed")
    if not policy.get("gameplay_delivery_targets") or "FIRST_GAME_DRAW_FRAME" not in policy["gameplay_delivery_targets"]:
        errors.append("no real game frame delivery goal")
    rules = policy.get("selection_rules", {})
    for key in (
        "forbid_guard_only_new_task", "prefer_complete_vertical_slice",
        "skip_conflicting_active_owner", "maintain_full_exact_sha_gate",
        "no_score_on_full_gate_failure", "preserve_runtime_validation_untested",
        "no_ci_skip_on_validation_bearing_commit", "no_implicit_draw_activation",
        "prohibit_new_dormant_warp_only_tasks",
        "require_game_created_draw_for_native_feature",
        "require_explicit_gameplay_outcome_since_00537",
        "prioritize_r175_and_game_frame_before_more_readiness_guards",
        "never_bypass_r175_or_visual_fail_closed_gate",
    ):
        if rules.get(key) is not True:
            errors.append("safety/progress rule disabled: " + key)
    if not policy.get("required_task_strategy_fields"):
        errors.append("task strategy contract missing")
    return errors


def validate_task(task: dict, policy: dict) -> list[str]:
    identity = task.get("task_id", "")
    found = re.fullmatch(r"CONVERSION-DX11-(\d{5})", identity)
    if not found:
        return ["invalid DX11 task_id"]
    if int(found.group(1)) < policy["effective_from_task_number"]:
        return []
    errors: list[str] = []
    if task.get("target_branch", policy["target_branch"]) != policy["target_branch"]:
        errors.append("cross-branch task")
    strategy = task.get("development_strategy")
    if not isinstance(strategy, dict):
        return ["development_strategy missing after structural policy effective date"]
    for key in policy["required_task_strategy_fields"]:
        if key not in strategy:
            errors.append("missing strategy field: " + key)
    kind = strategy.get("work_class")
    if kind not in policy["allowed_work_classes"]:
        errors.append("unknown or guard-only work class")
    milestones = {x["id"]: x for x in policy["milestones"]}
    milestone = strategy.get("milestone_id")
    if milestone not in milestones:
        errors.append("unknown end-to-end milestone")
    if not isinstance(strategy.get("integration_path"), list) or len(strategy["integration_path"]) < policy["minimum_integration_path_stages"]:
        errors.append("integration_path must cover at least two real connected stages")
    if not isinstance(strategy.get("batch_components"), list) or len(set(strategy["batch_components"])) < policy["minimum_batch_components"]:
        errors.append("one-guard/one-component microtask rejected")
    proof = strategy.get("acceptance_proof")
    if not isinstance(proof, dict):
        errors.append("acceptance_proof missing")
    else:
        for field in policy["mandatory_acceptance_proof_fields"]:
            if not isinstance(proof.get(field), str) or not proof[field].strip():
                errors.append("acceptance_proof missing: " + field)
    if strategy.get("full_gate_plan") != policy["allowed_full_gate_plan"]:
        errors.append("full exact-SHA Gate cannot be omitted or repeated per micro-edit")
    if not isinstance(strategy.get("conflict_keys"), list) or not strategy["conflict_keys"]:
        errors.append("conflict_keys missing")
    if kind in {"blocker_resolution", "safety_regression", "ci_acceleration"}:
        if not isinstance(strategy.get("blocking_evidence"), str) or not strategy["blocking_evidence"].strip():
            errors.append("blocker/regression/CI work requires measurable evidence")
    if kind == "vertical_slice" and milestone not in {
        "mono_native_draw", "programmable_shader_path", "first_live_game_draw",
    }:
        errors.append("vertical slice does not lead toward an actual native draw")
    # From 00537 onwards, a tiny dormant WARP probe is not a feature.
    # Older in-flight 00531..00536 records remain grandfathered unchanged.
    if int(found.group(1)) >= policy.get("gameplay_direction_effective_from_task_number", 537):
        delivery = strategy.get("gameplay_delivery_target")
        if delivery not in policy["gameplay_delivery_targets"]:
            errors.append("gameplay_delivery_target must close a real game-frame milestone")
        if milestone == "mono_native_draw":
            errors.append("dormant mono WARP fixture is no longer a new task milestone")
        if delivery == "R175_CI_UNBLOCK":
            if milestone != "shader_parity_r175" or kind != "blocker_resolution":
                errors.append("R175 repair must resolve the shader parity blocker")
            if not isinstance(strategy.get("r175_owner_handoff_evidence"), str) or not strategy["r175_owner_handoff_evidence"].strip():
                errors.append("R175 owner must be released or handed off explicitly before edits")
        elif delivery in {"FIRST_GAME_DRAW_FRAME", "MENU_TO_RACE_NATIVE_FRAME", "NATIVE_STEREO_EYE_OUTPUT"}:
            stages = strategy.get("live_game_draw_path")
            expected = ["LIVE_D3D9_CALLSITE", "D3D11_NATIVE_DRAW", "VISIBLE_FRAME_OUTPUT"]
            if not isinstance(stages, list) or any(stage not in stages for stage in expected) or [stages.index(stage) for stage in expected] != sorted(stages.index(stage) for stage in expected):
                errors.append("gameplay path must connect real D3D9 callsite through native Draw to visible frame output")
            for field in ("visible_frame_acceptance", "activation_guard_and_fallback"):
                if not isinstance(strategy.get(field), str) or not strategy[field].strip():
                    errors.append("missing game-frame acceptance or safe DX9Ex fallback: " + field)
            terminal = str(task.get("status") or "").upper().startswith(("COMPLETE", "PASS"))
            changes = task.get("changed_files") or []
            if terminal and not any(str(p).startswith(("src/", "vrhost/")) for p in changes):
                errors.append("completed game-frame work requires real renderer or hook source change")
    if task.get("runtime_validation") == "PASS" and not task.get("runtime_evidence"):
        errors.append("runtime PASS without actual HMD/game evidence")
    if task.get("automation_validation") == "PASS" and task.get("evidence", {}).get("backend_gate_conclusion") == "failure":
        errors.append("full Gate FAIL cannot become automation PASS")
    return errors


def latest_dx11_run() -> Path | None:
    numbered = []
    for p in RUN_DIR.glob("CONVERSION-DX11-*.json"):
        match = NAME.fullmatch(p.name)
        if match:
            numbered.append((int(match.group(1)), p))
    return max(numbered)[1] if numbered else None


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-latest", action="store_true")
    group.add_argument("--check-run", type=Path)
    group.add_argument("--recommend", action="store_true")
    args = parser.parse_args()
    policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    errors = validate_policy(policy)
    if errors:
        print("DX11 policy FAIL:", "; ".join(errors))
        return 1
    if args.recommend:
        print(json.dumps({"milestones": policy["milestones"], "selection_rules": policy["selection_rules"]}, indent=2))
        return 0
    run = latest_dx11_run() if args.check_latest else args.check_run
    if run:
        errors = validate_task(json.loads(run.read_text(encoding="utf-8")), policy)
        if errors:
            print(f"DX11 task acceptance FAIL {run}: " + "; ".join(errors))
            return 1
        print("DX11 integration-first acceptance PASS:", run.name)
    else:
        print("DX11 integration-first policy PASS (no new run to check)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
