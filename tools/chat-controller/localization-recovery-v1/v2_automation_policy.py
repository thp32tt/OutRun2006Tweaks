#!/usr/bin/env python3
"""OutRun KR v2 Docker fail-closed policy. No Chrome/Docker/ChatGPT side effects.

The v2 imagegen-sheet worker, native DDS edit/mip contract and C1/C3 migration
are NOT implemented in this controller. Accordingly no AUTO_SEND is accepted.
Stages are review gates, not task-completion attestations or deployment permission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

STAGES = ("PAUSED", "F0", "F1", "F2", "F3", "F4")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FLAGS = ("OUTRUN_A_TILE_BATCH_QUEUE", "OUTRUN_AB_BATCH_QUEUE",
         "OUTRUN_AB_TEXT_ROI_QUEUE", "OUTRUN_KR_V2_AUTO_GENERATE",
         "OUTRUN_KR_V2_AUTO_COMPOSE", "OUTRUN_KR_V2_AUTO_DEPLOY")
SCHEMA = "outrun-kr-v2-docker-policy-20261016"
EVIDENCE_SCHEMA = "outrun-kr-v2-stage-evidence-v1"


def _enabled(val):
    return str(val).strip().lower() in ("true", "1", "yes", "on")


def _json_file(path, max_bytes=262144):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        raise ValueError("POLICY_OR_EVIDENCE_MISSING_UNSAFE_OR_OVERSIZE:" + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def gate(env=None, policy_path=None, evidence_root=None):
    """Return (allowed, reason, phase); never mutate sources or queue state."""
    env = os.environ if env is None else env
    phase = str(env.get("OUTRUN_KR_V2_PHASE", "PAUSED")).strip()
    if phase not in STAGES:
        return False, "INVALID_V2_PHASE", phase
    if any(_enabled(env.get(key, "false")) for key in FLAGS):
        return False, "LEGACY_OR_UNQUALIFIED_BATCH_QUEUE_ENABLED", phase
    if str(env.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "")).strip():
        return False, "LEGACY_SMOKE_SEND_BLOCKED", phase
    if _enabled(env.get("AUTO_SEND", "false")):
        return False, "V2_BATCH_SHEET_DISPATCH_NOT_IMPLEMENTED_AUTOSEND_FORBIDDEN", phase
    if not _enabled(env.get("OUTRUN_KR_V2_NO_SEND", "true")):
        return False, "V2_NO_SEND_INTERLOCK_REQUIRED", phase
    if policy_path:
        try:
            policy = _json_file(policy_path)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            return False, "POLICY_UNREADABLE:" + str(exc)[:80], phase
        if (policy.get("schema") != SCHEMA
                or policy.get("deployment_mode") != "PAUSED_MANUAL"
                or policy.get("native_source_only") is not True
                or policy.get("legacy_986_tiles_forbidden") is not True
                or policy.get("c_role") != "ORIGINAL_HD_NATIVE_CROP_ONLY"
                or policy.get("v2_batch_sheet_dispatch_implemented") is not False
                or policy.get("runtime_activation_approved") is not False):
            return False, "POLICY_CONTRACT_MISMATCH", phase
    if phase == "PAUSED":
        return True, "PAUSED_NO_SEND_NO_QUEUE", phase

    # A phase request is not an authorization. Earlier real evidence must exist.
    if evidence_root is None:
        return False, "EVIDENCE_ROOT_REQUIRED", phase
    for required_stage in STAGES[1:STAGES.index(phase)]:
        try:
            evidence = _json_file(Path(evidence_root) / (required_stage + ".json"))
        except (ValueError, OSError, json.JSONDecodeError):
            return False, "PRIOR_STAGE_EVIDENCE_MISSING_OR_INVALID:" + required_stage, phase
        if not isinstance(evidence, dict):
            return False, "PRIOR_STAGE_EVIDENCE_INVALID:" + required_stage, phase
        if (evidence.get("schema") != EVIDENCE_SCHEMA or
                evidence.get("stage") != required_stage or
                evidence.get("decision") != "PASS" or
                evidence.get("RUNTIME_VALIDATION") != "PASS" or
                not isinstance(evidence.get("reviewer"), str) or
                not evidence["reviewer"].strip()):
            return False, "PRIOR_STAGE_NOT_ACTUALLY_APPROVED:" + required_stage, phase
        hashes = evidence.get("artifact_sha256", {})
        if (not isinstance(hashes, dict) or not hashes or
                any(not isinstance(v, str) or not HEX64.fullmatch(v) for v in hashes.values())):
            return False, "PRIOR_STAGE_SHA_EVIDENCE_MISSING:" + required_stage, phase
        # Evidence cannot pass from hashes typed into JSON alone: verify real files.
        base = Path(evidence_root).resolve()
        for rel, digest in hashes.items():
            if (not isinstance(rel, str) or not rel
                    or Path(rel).is_absolute() or ".." in Path(rel).parts):
                return False, "PRIOR_STAGE_ARTIFACT_PATH_UNSAFE:" + required_stage, phase
            target = base / rel
            if (not target.is_file() or target.is_symlink()
                    or not target.resolve().is_relative_to(base)):
                return False, "PRIOR_STAGE_ARTIFACT_NOT_FOUND:" + required_stage, phase
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                return False, "PRIOR_STAGE_ARTIFACT_HASH_MISMATCH:" + required_stage, phase
    return True, "MANUAL_REVIEW_PHASE_NO_SEND:" + phase, phase


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
    print(json.dumps({"ok": ok, "reason": reason, "phase": phase,
                      "AUTO_SEND": False, "C": "NATIVE_CROP_ONLY",
                      "RUNTIME_VALIDATION": "UNTESTED"},
                     ensure_ascii=False, sort_keys=True))
    return 0 if ok else 64


if __name__ == "__main__":
    sys.exit(main())