#!/usr/bin/env python3
"""Fail-closed activation policy for controlled OutRun Korean ImageGen automation.

Authorized automatic scope:
  verified unsplit/native HD English crop -> exact reviewed translation ->
  A/B ChatGPT ImageGen attachment/generation -> project Library SHA proof ->
  C1 lightweight independent QA.

Explicitly NOT authorized here:
  legacy 986 split tiles, automatic DDS promotion/write, game PASS, game deploy,
  VR work, or automatic C2/C3 approval.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

SCHEMA = "outrun-kr-v2-docker-policy-20261016"
STAGES = ("PAUSED", "F0", "F1", "F2", "F3", "F4")


def _enabled(val):
    return str(val).strip().lower() in ("true", "1", "yes", "on")


def _json_file(path, max_bytes=262144):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        raise ValueError("POLICY_MISSING_UNSAFE_OR_OVERSIZE:" + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def gate(env=None, policy_path=None, evidence_root=None):
    """Return (allowed, reason, phase). This gate never changes queue state."""
    env = os.environ if env is None else env
    phase = str(env.get("OUTRUN_KR_V2_PHASE", "PAUSED")).strip()
    if phase not in STAGES:
        return False, "INVALID_V2_PHASE", phase

    try:
        policy = _json_file(policy_path) if policy_path else {}
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return False, "POLICY_UNREADABLE:" + str(exc)[:100], phase

    if policy:
        if (
            policy.get("schema") != SCHEMA
            or policy.get("native_source_only") is not True
            or policy.get("legacy_986_tiles_forbidden") is not True
            or policy.get("c_role") != "ORIGINAL_HD_NATIVE_CROP_ONLY"
            or policy.get("auto_dds_write") is not False
            or policy.get("auto_game_pass") is not False
            or policy.get("auto_deploy") is not False
        ):
            return False, "POLICY_CONTRACT_MISMATCH", phase

    auto_send = _enabled(env.get("AUTO_SEND", "false"))
    roi_queue = _enabled(env.get("OUTRUN_AB_TEXT_ROI_QUEUE", "false"))
    roi_bridge = _enabled(env.get("OUTRUN_ROI_BRIDGE_ENABLED", "false"))
    auto_generate = _enabled(env.get("OUTRUN_KR_V2_AUTO_GENERATE", "false"))
    no_send = _enabled(env.get("OUTRUN_KR_V2_NO_SEND", "true"))

    # Retired/unqualified paths are never allowed during controlled activation.
    if _enabled(env.get("OUTRUN_A_TILE_BATCH_QUEUE", "false")):
        return False, "LEGACY_TILE_QUEUE_FORBIDDEN", phase
    if _enabled(env.get("OUTRUN_AB_BATCH_QUEUE", "false")):
        return False, "LEGACY_AB_BATCH_QUEUE_FORBIDDEN", phase
    if str(env.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "")).strip():
        return False, "LEGACY_SMOKE_SEND_BLOCKED", phase
    if _enabled(env.get("OUTRUN_KR_V2_AUTO_COMPOSE", "false")):
        return False, "AUTO_DDS_COMPOSE_FORBIDDEN", phase
    if _enabled(env.get("OUTRUN_KR_V2_AUTO_DEPLOY", "false")):
        return False, "AUTO_GAME_DEPLOY_FORBIDDEN", phase

    if not auto_send:
        # Manual/paused browser operation remains allowed only with no generators.
        if auto_generate or roi_queue:
            return False, "AUTO_GENERATE_OR_QUEUE_REQUIRES_AUTOSEND", phase
        return True, "MANUAL_NO_SEND", phase

    # AUTO_SEND is accepted only for the newly authorized native ROI pipeline.
    if no_send:
        return False, "NO_SEND_INTERLOCK_CONFLICTS_WITH_AUTOSEND", phase
    if phase not in ("F2", "F3", "F4"):
        return False, "AUTOSEND_REQUIRES_CONTROLLED_PRODUCTION_PHASE", phase
    if not (roi_queue and roi_bridge and auto_generate):
        return False, "CONTROLLED_ROI_PIPELINE_NOT_FULLY_ENABLED", phase

    if policy:
        if (
            policy.get("deployment_mode") != "ACTIVE_CONTROLLED_ROI_IMAGEGEN"
            or policy.get("runtime_activation_approved") is not True
            or policy.get("controller_auto_send") is not True
            or policy.get("native_roi_dispatch_implemented") is not True
            or policy.get("browser_slots") != ["A", "B", "C1"]
        ):
            return False, "ACTIVE_POLICY_NOT_APPROVED", phase

    # F-stage here is a work-scope label, not a false runtime/game PASS.
    # DDS/game promotion remains outside this controller and keeps its own evidence gates.
    return True, "CONTROLLED_NATIVE_ROI_IMAGEGEN_ACTIVE", phase


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="/opt/outrun/v2_docker_policy.json")
    parser.add_argument("--evidence-root", default="/data/imagegen/korean_v2/stage_evidence")
    parser.add_argument("--phase", choices=STAGES)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    if args.phase:
        env["OUTRUN_KR_V2_PHASE"] = args.phase
    ok, reason, phase = gate(env, args.policy, args.evidence_root)
    print(json.dumps({
        "ok": ok,
        "reason": reason,
        "phase": phase,
        "AUTO_SEND": _enabled(env.get("AUTO_SEND", "false")),
        "A_B": "NATIVE_ROI_IMAGEGEN" if ok and _enabled(env.get("AUTO_SEND", "false")) else "NO_SEND",
        "C1": "LIGHT_QA_ONLY",
        "C": "NATIVE_CROP_BACKGROUND_WORKER",
        "AUTO_DDS_WRITE": False,
        "AUTO_GAME_PASS": False,
        "RUNTIME_VALIDATION": "UNTESTED",
    }, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 64


if __name__ == "__main__":
    sys.exit(main())
