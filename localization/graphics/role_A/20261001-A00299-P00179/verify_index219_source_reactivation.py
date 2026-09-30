#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index219 / D263B3F1.

This tool never reacquires source bytes. It verifies the current GitHub-SSOT
fingerprints that keep index219 SOURCE_ACQUISITION_EXHAUSTED. If any dependency
changes, it requests a fresh rescan; otherwise it forbids Drive/direct/Release
re-probing and forbids substituting the verified-but-noncanonical pinned Release
member for the canonical inventory object.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

INDEX = 219
ASSET = "D263B3F1"
QUEUE_PATH = "textures/load/spr_sprani_sumo_fe_cvt_Exst/D263B3F1_512x512.dds"
LOCKED_CANONICAL = {
    "sha256": "489fec388b636cd681e3d691ef9b5026a9036e1fbfd2948845d327a184050084",
    "width": 512,
    "height": 512,
    "mode": "RGBA",
}
LOCKED_A00196_RESULT = "86a5583fd9ae02f7c23744ae709da2da82ae501e"
LOCKED_C142_RESULT = "b697463f9714bb2c00d86cc89bd5d9dc96f0a915"
LOCKED_RELEASE_SHA256 = "6cb45f18647bb20965d89c9e6e48b427241ea08edccf7b09be3aa53af213555d"
PINNED_TAG = "v0.25.10a"
PINNED_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
DRIVE_FOLDER_ID = "1TpFYOgf0ulxmj6lJozHjAS-69asQajXr"

def load_json(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))

def csv_row(root: Path, rel: str, key: str, value: str):
    with (root / rel).open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get(key) == value:
                return row
    return None

def asset_by_index(payload, index):
    for row in payload.get("assets", []):
        if row.get("index") == index:
            return row
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    root = Path(args.repo_root)

    inv = csv_row(root, "localization/graphics/inventory.csv", "path", QUEUE_PATH)
    queue = csv_row(root, "localization/graphics/asset_queue.csv", "index", str(INDEX))
    a00196 = load_json(
        root,
        "localization/graphics/role_A/20260930-A00196-P00101/"
        "A00196_P00101_MOD3_RELEASE_FALLBACK_MANIFEST.json",
    )
    c142 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00201.json")
    c142_report = load_json(
        root,
        "localization/graphics/role_C/20260930-0345-C142/"
        "C142_Q00040_INDEPENDENT_QA_BATCH.json",
    )
    c164 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00293.json")
    a289 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00289.json")
    a296 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00296.json")
    a297 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00297.json")
    roles = load_json(root, "localization/controller_roles.json")
    contract = (root / "docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(
        encoding="utf-8"
    )

    canonical = None if inv is None else {
        "sha256": inv["sha256"],
        "width": int(inv["width"]),
        "height": int(inv["height"]),
        "mode": inv["mode"],
    }
    qnote = "" if queue is None else queue.get("notes", "")
    a_asset = asset_by_index(a00196, INDEX)
    c_asset = asset_by_index(c142_report, INDEX)
    rr = c164.get("readiness_reconciliation", {})
    a00196_input = next(
        (
            row for row in c142.get("qa_batch_inputs", [])
            if row.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00196"
        ),
        None,
    )
    a00196_disposition = next(
        (
            row for row in c142.get("qa_dispositions", [])
            if row.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00196"
        ),
        None,
    )

    checks = {
        "queue_identity": bool(
            queue
            and queue["path"] == QUEUE_PATH
            and queue["action"] == "localize_text"
            and INDEX % 3 == 0
        ),
        "queue_retains_c142_source_exhaustion": (
            "Q00040 C142 A00196 PASS PREFLIGHT_ONLY/SOURCE_ACQUISITION_EXHAUSTED"
            in qnote
            and "do not repeat unchanged source probes" in qnote
        ),
        "canonical_inventory_identity": canonical == LOCKED_CANONICAL,
        "a00196_asset_identity": bool(
            a_asset
            and a_asset.get("index") == INDEX
            and a_asset.get("asset") == ASSET
            and a_asset.get("queue_path") == QUEUE_PATH
            and a_asset.get("canonical_sha256") == LOCKED_CANONICAL["sha256"]
        ),
        "a00196_drive_miss": bool(
            a_asset and a_asset.get("drive") == "SOURCE_TRANSPORT_MISS_EXACT_PARENT"
        ),
        "a00196_direct_miss": bool(
            a_asset and a_asset.get("pinned_direct") == "SOURCE_TRANSPORT_MISS_404"
        ),
        "c142_consumed_exact_a00196_result": bool(
            a00196_input
            and a00196_input.get("result_sha") == LOCKED_A00196_RESULT
            and a00196_disposition
            and a00196_disposition.get("status") == "PASS"
        ),
        "c142_source_exhausted": bool(
            INDEX in c142.get("readiness_reconciliation", {}).get(
                "source_acquisition_exhausted_indices", []
            )
            and c_asset
            and c_asset.get("source_outcome") == "SOURCE_ACQUISITION_EXHAUSTED"
        ),
        "c142_release_mismatch": bool(
            c_asset
            and c_asset.get("release_sha256") == LOCKED_RELEASE_SHA256
            and c_asset.get("canonical_sha256") == LOCKED_CANONICAL["sha256"]
            and (
                c_asset.get("release_width") != LOCKED_CANONICAL["width"]
                or c_asset.get("release_height") != LOCKED_CANONICAL["height"]
                or c_asset.get("release_sha256") != LOCKED_CANONICAL["sha256"]
            )
        ),
        "c142_validation_result_identity": (
            c142.get("validation_bearing_result_sha") == LOCKED_C142_RESULT
            and c142.get("automation_validation") == "PASS"
        ),
        "c164_no_a_render_ready": all(
            i % 3 != 0 for i in rr.get("render_ready_indices", [])
        ),
        "c164_no_a_one_stage": all(
            i % 3 != 0 for i in rr.get("one_stage_to_render_indices", [])
        ),
        "c164_no_a_candidate_rework": all(
            i % 3 != 0 for i in rr.get("candidate_rework_indices", [])
        ),
        "c164_a_candidate_qa_pending": all(
            i in rr.get("candidate_qa_pending_indices", [])
            for i in (159, 198, 201)
        ),
        "newer_a_inputs_not_repeated": (
            a289.get("automation_validation") == "PENDING"
            and a289.get("selection", {}).get("selected_index") == 111
            and a296.get("automation_validation") == "PENDING"
            and a296.get("selection", {}).get("selected_index") == 51
            and a297.get("automation_validation") == "PENDING"
            and a297.get("selection", {}).get("selected_index") == 24
        ),
        "controller_schema15_mod3": (
            roles.get("schema_version") == 15
            and roles.get("lanes", {}).get("A", {}).get("primary_index_modulo_3") == 0
        ),
        "pinned_source_policy_unchanged": all(
            token in contract
            for token in (PINNED_TAG, PINNED_COMMIT, PINNED_ZIP_SHA256, DRIVE_FOLDER_ID)
        ),
    }

    unchanged = all(checks.values())
    out = {
        "schema_version": 1,
        "task_id": "LOCALIZATION-LOCALIZATION_A-00299",
        "wave_id": "P00179",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "checks": checks,
        "current_canonical": canonical,
        "locked_canonical": LOCKED_CANONICAL,
        "locked_a00196_result_sha": LOCKED_A00196_RESULT,
        "locked_c142_validation_bearing_result_sha": LOCKED_C142_RESULT,
        "locked_release_sha256": LOCKED_RELEASE_SHA256,
        "source_reprobe_authorized": False,
        "release_member_substitution_authorized": False,
        "candidate_rebuild_authorized": False,
        "reactivation_triggers": [
            "canonical inventory identity for index219 changes",
            "asset_queue no longer retains C142 SOURCE_ACQUISITION_EXHAUSTED for index219",
            "C142/A00196 source-exhaustion evidence is superseded by authoritative later C evidence",
            "pinned source tag/commit/bundle or approved Drive transport policy changes",
            "an exact canonical 512x512 D263B3F1 source transport is newly recorded by authoritative evidence",
        ],
        "fresh_rescan_required": not unchanged,
        "result": (
            "BLOCKED_UNCHANGED_SOURCE_ACQUISITION_EXHAUSTED_FINGERPRINT"
            if unchanged
            else "FRESH_RESCAN_REQUIRED"
        ),
        "runtime_validation": "UNTESTED",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if unchanged else 2)

if __name__ == "__main__":
    main()
