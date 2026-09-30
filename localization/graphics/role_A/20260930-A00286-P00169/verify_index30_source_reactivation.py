#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index30 / 8215FD25.

This tool never acquires source bytes and never authorizes a DDS candidate.
It evaluates the exact GitHub-SSOT evidence that currently makes index30 a
sticky SOURCE_ACQUISITION_EXHAUSTED PREFLIGHT_ONLY item. If any dependency
changes, it returns FRESH_RESCAN_REQUIRED so the producer can re-enter normal
candidate-first selection without blindly repeating the old source probes.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

INDEX = 30
ASSET = "8215FD25"
QUEUE_PATH = "textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds"
LOCKED_CANONICAL = {
    "sha256": "0cd71138fd6811f5466a9c6674a243324d88ecc8dd82ad36df05234d759abc56",
    "width": 1024,
    "height": 512,
    "mode": "RGBA",
}
LOCKED_A00179_RESULT = "7548b44b7364504c248341cce0771969f0793160"
PINNED_TAG = "v0.25.10a"
PINNED_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"


def load_json(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def inventory_row(root: Path):
    with (root / "localization/graphics/inventory.csv").open(
        "r", encoding="utf-8", newline=""
    ) as fh:
        for row in csv.DictReader(fh):
            if row["path"] == QUEUE_PATH:
                return {
                    "sha256": row["sha256"],
                    "width": int(row["width"]),
                    "height": int(row["height"]),
                    "mode": row["mode"],
                }
    return None


def queue_row(root: Path):
    with (root / "localization/graphics/asset_queue.csv").open(
        "r", encoding="utf-8", newline=""
    ) as fh:
        for row in csv.DictReader(fh):
            if int(row["index"]) == INDEX:
                return row
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    root = Path(args.repo_root)

    inv = inventory_row(root)
    queue = queue_row(root)
    a00179 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00179.json")
    a00179_evidence = load_json(
        root,
        "localization/graphics/role_A/20260930-0138-A00179-P00090/"
        "A00179_P00090_MOD3_SOURCE_ACQUISITION_EXHAUSTION.json",
    )
    c136 = load_json(
        root,
        "localization/graphics/role_C/20260930-0208-C136/"
        "C136_Q00034_INDEPENDENT_QA_BATCH.json",
    )
    a285 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00285.json")
    contract = (root / "docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(
        encoding="utf-8"
    )

    evidence30 = next(
        (x for x in a00179_evidence.get("source_results", []) if x.get("index") == INDEX),
        None,
    )
    cdisp = next(
        (
            x
            for x in c136.get("qa_dispositions", [])
            if x.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00179"
            and x.get("result_sha") == LOCKED_A00179_RESULT
        ),
        None,
    )

    checks = {
        "queue_identity": bool(
            queue
            and int(queue["index"]) == INDEX
            and queue["path"] == QUEUE_PATH
            and queue["action"] == "localize_text"
            and INDEX % 3 == 0
        ),
        "canonical_inventory_identity": inv == LOCKED_CANONICAL,
        "a00179_result_identity": (
            a00179.get("result_sha") == LOCKED_A00179_RESULT
            or a00179.get("authoritative_result_sha") == LOCKED_A00179_RESULT
        ),
        "a00179_index30_still_exhausted": bool(
            evidence30
            and evidence30.get("final") == "SOURCE_ACQUISITION_EXHAUSTED"
            and evidence30.get("canonical") == LOCKED_CANONICAL
            and evidence30.get("pinned_direct", {}).get("outcome")
            == "SOURCE_IDENTITY_MISMATCH"
            and evidence30.get("pinned_release", {}).get("outcome")
            == "SOURCE_IDENTITY_MISMATCH"
        ),
        "c136_accepts_exhaustion_only": bool(
            cdisp
            and cdisp.get("status") == "PASS"
            and c136.get("production_readiness", {}).get(str(INDEX)) == "PREFLIGHT_ONLY"
            and INDEX in c136.get("source_acquisition_exhausted", [])
        ),
        "a285_sticky_guard_still_tracks_index30": (
            INDEX in a285.get("selection", {}).get("sticky_source_acquisition_not_repeated", [])
            and not a285.get("selection", {}).get("direct_rework_required_runnable", [])
            and not a285.get("selection", {}).get("render_ready", [])
            and not a285.get("selection", {}).get("one_stage_to_render", [])
        ),
        "pinned_source_policy_unchanged": (
            PINNED_TAG in contract
            and PINNED_COMMIT in contract
            and PINNED_ZIP_SHA256 in contract
        ),
    }

    unchanged = all(checks.values())
    result = {
        "schema_version": 1,
        "task_id": "LOCALIZATION-LOCALIZATION_A-00286",
        "wave_id": "P00169",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "checks": checks,
        "current_canonical": inv,
        "locked_canonical": LOCKED_CANONICAL,
        "reactivation_triggers": [
            "canonical inventory identity changes",
            "C disposition/source-acquisition state changes",
            "A00179 accepted result identity is superseded",
            "pinned canonical source policy/tag/commit/bundle digest changes",
            "A-shard candidate-completion scan no longer classifies index30 as sticky",
        ],
        "source_reprobe_authorized": False,
        "candidate_rebuild_authorized": False,
        "fresh_rescan_required": not unchanged,
        "result": (
            "BLOCKED_UNCHANGED_DEPENDENCY_FINGERPRINT"
            if unchanged
            else "FRESH_RESCAN_REQUIRED"
        ),
        "runtime_validation": "UNTESTED",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
