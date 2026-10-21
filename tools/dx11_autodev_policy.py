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
    if "full_resolution_native_game_frame" not in ids:
        errors.append("2026-10-14 override requires full-resolution game output milestone")
    override = policy.get("user_override_20261014") or {}
    if (override.get("status") != "ACTIVE" or
        override.get("immediate_delivery") != "FULL_RESOLUTION_GAME_FRAME" or
        not override.get("no_inset_only_completion") or
        not override.get("source_first_validation")):
        errors.append("missing active DX11 source-first full-frame user override")
    if "FULL_RESOLUTION_GAME_FRAME" not in policy.get("gameplay_delivery_targets", []):
        errors.append("missing full-resolution game output delivery target")
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
        "batch_source_and_regressions_before_full_gate",
        "avoid_full_build_after_each_individual_edit",
        "prefer_one_material_commit_per_coherent_batch_when_possible",
        "only_one_final_full_gate_per_coherent_batch_when_possible",
    ):
        if rules.get(key) is not True:
            errors.append("safety/progress rule disabled: " + key)
    unit = policy.get("feature_unit", {})
    if unit.get("effective_from_task_number") != 672:
        errors.append("feature-sized task threshold missing")
    if unit.get("minimum_acceptance_items", 0) < 3 or unit.get("minimum_behavior_areas", 0) < 2:
        errors.append("feature-sized acceptance minimum weakened")
    if set(unit.get("required_categories", [])) != {"end_to_end_behavior", "fallback_regression", "integrated_validation"}:
        errors.append("feature-sized acceptance categories incomplete")
    for key in ("forbid_per_format_microtask_completion", "require_feature_level_acceptance_contract", "resume_unfinished_feature_same_task_id"):
        if rules.get(key) is not True:
            errors.append("feature-sized dispatch rule disabled: " + key)
    if not policy.get("required_task_strategy_fields"):
        errors.append("task strategy contract missing")
    # 2026-10-18: Verify that recommendation/dispatch has a live-game delivery
    # target, not only an ever-growing inventory of CI/probe milestones.
    latest = policy.get("user_override_20261018") or {}
    if (latest.get("status") != "ACTIVE" or
        latest.get("execution_mode") != "PLAYABLE_NATIVE_DX11_VERTICAL_SLICE_FIRST" or
        latest.get("max_consecutive_validation_only_dispatches_when_implementable") != 0 or
        not latest.get("implementation_required_per_cycle") or
        not latest.get("prohibit_standalone_probe_guard_ci_only_delivery") or
        not latest.get("continue_same_unfinished_feature_task_id") or
        not latest.get("forbid_unreviewed_external_code_import")):
        errors.append("2026-10-18 playable-native-DX11 source-first dispatch override missing")
    for rule in ("require_material_native_game_draw_progress_before_new_independent_task",
                 "refuse_guard_only_terminal_playability",
                 "prohibit_rechecking_unchanged_exact_sha",
                 "prioritize_live_shader_bound_draw_at_native_draw_zero",
                 "enable_early_real_game_frame_test_candidate",
                 "import_external_source_only_after_license_review"):
        if rules.get(rule) is not True:
            errors.append("playable-DX11 execution rule disabled: " + rule)
    return errors


def verified_build_acceptance(value: object) -> bool:
    """Require auditable source/CI evidence for structured acceptance entries.

    The persisted 00966 feature result uses an object with status and evidence,
    unlike older string-valued results. Reject missing evidence/status instead
    of treating every structured result as UNTESTED (or blindly trusting it).
    The separate exact-SHA and source gates remain mandatory in validate_task.
    """
    if isinstance(value, dict):
        paths = value.get("evidence_paths")
        command = value.get("validation_command")
        if (not isinstance(paths, list) or not paths
                or any(not isinstance(path, str) or not path.strip() for path in paths)
                or not isinstance(command, str) or not command.strip()):
            return False
        value = value.get("status")
    if value in ("PASS", "PASS_BUILD", "PASS_EXACT_SHA"):
        return True
    if not isinstance(value, str) or not re.fullmatch(
        r"PASS_[A-Z0-9]+(?:_[A-Z0-9]+)+", value
    ):
        return False
    return not any(
        negative in value.split("_")
        for negative in ("UNTESTED", "UNKNOWN", "PENDING", "FAIL", "FAILED", "SKIP", "BLOCKED")
    )


def source_stage_build_verified(task: dict) -> bool:
    """Successful bounded DX11 source stages are not full gameplay completion."""
    return (
        task.get("status") == "COMPLETE_BUILD_VERIFIED"
        and task.get("full_dx11_renderer_complete") is False
        and task.get("automation_validation") == "PASS_EXACT_SHA"
        and task.get("runtime_validation") == "UNTESTED"
        and task.get("score_change", 0) == 0
        and isinstance(task.get("validation_bearing_result_sha"), str)
        and re.fullmatch(r"[0-9a-f]{40}", task["validation_bearing_result_sha"]) is not None
    )


def source_stage_native_desktop_gpu_build_verified(task: dict) -> bool:
    """A verified game-owned desktop GPU output bracket is a SOURCE stage.

    Copy/Resolve MRT/DSV/UAV restoration is real integration progress, but
    it does not demonstrate the missing D3D9->native Draw->visible frame or
    Quest3 runtime. Admit only this bounded, exact-SHA tested stage, never a
    complete renderer or a score-bearing new milestone.
    """
    strategy = task.get("development_strategy") or {}
    changed = task.get("changed_files") or []
    return (
        source_stage_build_verified(task)
        and strategy.get("milestone_id") == "full_resolution_native_game_frame"
        and strategy.get("gameplay_delivery_target")
            == "NATIVE_FULL_FRAME_GPU_DESKTOP_OUTPUT_STATE_PRESERVATION"
        and strategy.get("live_game_draw_path")
            == ["D3D11_NATIVE_DRAW", "NATIVE_FULL_FRAME_GPU_DESKTOP_OUTPUT"]
        and isinstance(strategy.get("visible_frame_acceptance"), str)
        and "SOURCE_STAGE_NOT_GAMEPLAY_VERIFIED" in strategy["visible_frame_acceptance"]
        and any(isinstance(path, str) and path.startswith("src/vr/d3d11/")
                for path in changed)
        and any(isinstance(path, str) and "gpu_output" in path.lower()
                for path in changed)
    )


def source_stage_ci_pending(task: dict) -> bool:
    """Allow only an actual DX11 native-eye SOURCE checkpoint to await CI.

    The source/transport change is real, but neither the exact SHA gates nor
    an R30 game callback have been proven. Terminal acceptance remains sealed
    by source_stage_build_verified and the independent feature checks.
    """
    changed = task.get("changed_files")
    return (
        task.get("status") == "SOURCE_IMPLEMENTED_CI_PENDING"
        and task.get("full_dx11_renderer_complete") is False
        and task.get("automation_validation") == "PENDING_EXACT_SHA"
        and task.get("runtime_validation") == "UNTESTED"
        and task.get("score_change", 0) == 0
        and not task.get("validation_bearing_result_sha")
        and isinstance(changed, list)
        and any(isinstance(path, str) and path.startswith("src/vr/d3d11/")
                for path in changed)
    )


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
        "full_resolution_native_game_frame",
    }:
        errors.append("vertical slice does not lead toward an actual native draw")
    # From 00537 onwards, a tiny dormant WARP probe is not a feature.
    # Older in-flight 00531..00536 records remain grandfathered unchanged.
    if int(found.group(1)) >= policy.get("gameplay_direction_effective_from_task_number", 537):
        delivery = strategy.get("gameplay_delivery_target")
        if (delivery not in policy["gameplay_delivery_targets"]
                and not source_stage_native_desktop_gpu_build_verified(task)):
            errors.append("gameplay_delivery_target must close a real game-frame milestone")
        if milestone == "mono_native_draw":
            errors.append("dormant mono WARP fixture is no longer a new task milestone")
        if delivery == "R175_CI_UNBLOCK":
            if milestone != "shader_parity_r175" or kind != "blocker_resolution":
                errors.append("R175 repair must resolve the shader parity blocker")
            if not isinstance(strategy.get("r175_owner_handoff_evidence"), str) or not strategy["r175_owner_handoff_evidence"].strip():
                errors.append("R175 owner must be released or handed off explicitly before edits")
        elif (delivery in {"FIRST_GAME_DRAW_FRAME", "FULL_RESOLUTION_GAME_FRAME",
                            "MENU_TO_RACE_NATIVE_FRAME", "NATIVE_STEREO_EYE_OUTPUT"}
              or source_stage_native_desktop_gpu_build_verified(task)):
            stages = strategy.get("live_game_draw_path")
            expected = ["LIVE_D3D9_CALLSITE", "D3D11_NATIVE_DRAW", "VISIBLE_FRAME_OUTPUT"]
            has_full_path = (
                isinstance(stages, list)
                and all(stage in stages for stage in expected)
                and [stages.index(stage) for stage in expected] ==
                    sorted(stages.index(stage) for stage in expected)
            )
            # An exact-SHA built but explicitly UNFINISHED source stage can
            # terminate at a native stereo GPU eye. Do not pretend that the
            # missing R30 camera game-draw callsite reached visible OpenXR.
            # Full renderer completion still requires the full ordered path.
            partial_eye_stage = (
                (source_stage_build_verified(task) or source_stage_ci_pending(task))
                and milestone == "native_stereo_eye_transport"
                # Do not invent an R30 live game callsite for an isolated
                # source-ordered GPU-eye stage. Older verified run records
                # used the legacy prefix; keep their exact-SHA record valid.
                and stages in (
                    ["D3D11_NATIVE_DRAW", "NATIVE_STEREO_EYE_OUTPUT"],
                    ["LIVE_D3D9_CALLSITE", "D3D11_NATIVE_DRAW",
                     "NATIVE_STEREO_EYE_OUTPUT"],
                )
            )
            if (not has_full_path and not partial_eye_stage
                    and not source_stage_native_desktop_gpu_build_verified(task)):
                errors.append("gameplay path must connect real D3D9 callsite through native Draw to visible frame output")
            for field in ("visible_frame_acceptance", "activation_guard_and_fallback"):
                if not isinstance(strategy.get(field), str) or not strategy[field].strip():
                    errors.append("missing game-frame acceptance or safe DX9Ex fallback: " + field)
            terminal = str(task.get("status") or "").upper().startswith(("COMPLETE", "PASS"))
            changes = task.get("changed_files") or []
            if terminal and not any(str(p).startswith(("src/", "vrhost/")) for p in changes):
                errors.append("completed game-frame work requires real renderer or hook source change")
    # From 00672, source-format and one-guard edits are subtasks, not terminal features.
    unit = policy.get("feature_unit", {})
    if int(found.group(1)) >= unit.get("effective_from_task_number", 10**9):
        feature_id = task.get("feature_id")
        contract = task.get("feature_contract")
        if not isinstance(feature_id, str) or not feature_id.strip():
            errors.append("feature_id required for feature-sized task")
        if not isinstance(contract, dict):
            errors.append("feature_contract required for feature-sized task")
        else:
            goal = contract.get("goal")
            if not isinstance(goal, str) or len(goal.strip()) < 24:
                errors.append("feature goal must describe integrated behavior")
            if contract.get("feature_id") != feature_id:
                errors.append("feature_contract feature_id mismatch")
            items = contract.get("acceptance_items")
            if not isinstance(items, list) or len(items) < unit["minimum_acceptance_items"]:
                errors.append("at least three feature acceptance items required")
                items = []
            ids = [item.get("id") for item in items if isinstance(item, dict)]
            if len(ids) != len(items) or len(set(ids)) != len(items) or any(not isinstance(i, str) or not i for i in ids):
                errors.append("feature acceptance IDs must be unique/nonempty")
            categories = set()
            areas = set()
            for item in items:
                if not isinstance(item, dict):
                    continue
                categories.add(item.get("category"))
                area = item.get("behavior_area")
                if isinstance(area, str) and area.strip():
                    areas.add(area.strip())
                expected = item.get("expected_behavior")
                if not isinstance(expected, str) or len(expected.strip()) < 12:
                    errors.append("feature acceptance item missing expected behavior")
            if not set(unit["required_categories"]).issubset(categories):
                errors.append("feature acceptance must cover end-to-end, fallback and integration")
            if len(areas) < unit["minimum_behavior_areas"]:
                errors.append("feature must span at least two behavior areas")
            terminal = str(task.get("status") or "").upper().startswith(("COMPLETE", "DONE", "PASS"))
            if terminal:
                results = task.get("acceptance_results")
                if not isinstance(results, dict) or any(not verified_build_acceptance(results.get(i)) for i in ids):
                    errors.append("terminal feature requires all acceptance items PASS")
                if task.get("automation_validation") not in ("PASS", "PASS_EXACT_SHA"):
                    errors.append("terminal feature requires exact-SHA automation PASS")
                sha = task.get("validation_bearing_result_sha")
                if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
                    errors.append("terminal feature missing validated source SHA")
    # 00672+: material result is one functional renderer capability, not a
    # succession of one-format or one-guard tasks. The feature contract is
    # distinct from runtime/HMD proof and must survive task retries.
    feature_unit = policy.get("feature_unit", {})
    if int(found.group(1)) >= feature_unit.get("effective_from_task_number", 672):
        contract = task.get("feature_contract")
        if not isinstance(contract, dict):
            errors.append("feature-sized task missing feature_contract")
        else:
            if not isinstance(task.get("feature_id"), str) or not task["feature_id"] or (
                contract.get("feature_id") != task["feature_id"]
            ):
                errors.append("feature contract identity mismatch")
            if not isinstance(contract.get("goal"), str) or not contract["goal"].strip():
                errors.append("feature contract goal missing")
            items = contract.get("acceptance_items")
            if not isinstance(items, list) or len(items) < feature_unit.get("minimum_acceptance_items", 3):
                errors.append("feature acceptance list incomplete")
            else:
                ids = [item.get("id") if isinstance(item, dict) else None for item in items]
                categories = {item.get("category") for item in items if isinstance(item, dict)}
                areas = {item.get("behavior_area") for item in items if isinstance(item, dict)
                         and isinstance(item.get("behavior_area"), str) and item["behavior_area"].strip()}
                if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
                    errors.append("feature acceptance IDs missing or duplicated")
                if not set(feature_unit.get("required_categories", [])).issubset(categories):
                    errors.append("feature acceptance categories incomplete")
                if len(areas) < feature_unit.get("minimum_behavior_areas", 2):
                    errors.append("feature capability limited to one behavior area")
                if any(not isinstance(item, dict) or
                       not isinstance(item.get("expected_behavior"), str) or
                       not item["expected_behavior"].strip() for item in items):
                    errors.append("feature acceptance expected behavior missing")
                status = str(task.get("status") or "").upper()
                if status.startswith(("COMPLETE", "PASS")):
                    results = task.get("acceptance_results") or {}
                    if not isinstance(results, dict) or any(
                        not verified_build_acceptance(results.get(item_id)) for item_id in ids
                    ):
                        errors.append("complete feature has unverified acceptance items")
                    sha = task.get("validation_bearing_result_sha")
                    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
                        errors.append("complete feature missing exact validation SHA")
                    if task.get("automation_validation") != "PASS_EXACT_SHA":
                        errors.append("complete feature missing exact-SHA Gate PASS")
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
        print(json.dumps({
            "active_priority": "REAL_LIVE_PROGRAMMABLE_GAME_DRAW_TO_NATIVE_D3D11",
            "game_draw_status": "OBSERVED_15548388_D3D9__ZERO_ELIGIBLE__ZERO_NATIVE__ZERO_PUBLICATION",
            "next_source_paths": [
                "src/vr/d3d11/live_game_frame_bridge.cpp",
                "src/vr/d3d11/native_backend.cpp",
                "src/vr/d3d11/runtime_census.cpp",
                "src/vr/d3d9/stereo_renderer_r30.cpp",
            ],
            "delivery_override": policy["user_override_20261018"],
            "milestones": policy["milestones"],
            "selection_rules": policy["selection_rules"],
        }, indent=2))
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
