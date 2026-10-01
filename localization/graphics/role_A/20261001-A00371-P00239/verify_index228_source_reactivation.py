#!/usr/bin/env python3
"""Fail-closed canonical-source reactivation guard for A-owned index228/E7F6E9B7.

This tool performs no network/source acquisition. It replays current GitHub-SSOT
metadata against the C136-accepted B00180 source-exhaustion fingerprint. When the
fingerprint is unchanged it forbids duplicate Drive/direct/Release probing and
forbids substituting the pinned-but-noncanonical release member. Any dependency
change makes the tool exit non-zero and requests a fresh producer rescan.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

INDEX = 228
ASSET = "E7F6E9B7"
QUEUE_PATH = "textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
LOCKED_CANONICAL = {
    "sha256": "bbbc44543042527a1c4f80156ddbf4f0f26b9130d8eca0a78012fb79ee3f38b2",
    "width": 512,
    "height": 512,
    "mode": "RGBA",
}
LOCKED_B00180_RESULT = "2af61fc8fd41e5ee6d8e4524914107682c591149"
LOCKED_C136_RESULT = "5417599fe8ce1951be9b36edf63b058f6f68c19d"
LOCKED_DIRECT_BLOB = "87ff6635b287982d1dd2089f9bf9183df8a1e3ea"
LOCKED_RELEASE_SHA256 = "3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
LOCKED_RELEASE_DIMS = [2048, 2048]
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
    b180 = load_json(
        root,
        "localization/graphics/role_B/20260930-B00180-P00091/"
        "B00180_P00091_FOUR_EVEN_SOURCE_TIER_EXHAUSTION.json",
    )
    c136 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00184.json")
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
    b_asset = asset_by_index(b180, INDEX)
    b_input = next(
        (row for row in c136.get("qa_batch_inputs", [])
         if row.get("task_id") == "LOCALIZATION-LOCALIZATION_B-00180"),
        None,
    )
    b_disp = next(
        (row for row in c136.get("qa_dispositions", [])
         if row.get("task_id") == "LOCALIZATION-LOCALIZATION_B-00180"),
        None,
    )
    direct = {} if b_asset is None else b_asset.get("pinned_direct_tier", {})
    release = {} if b_asset is None else b_asset.get("pinned_release_tier", {})
    drive = {} if b_asset is None else b_asset.get("drive_tier", {})
    source_transport = roles.get("source_transport", {})
    drive_policy = source_transport.get("canonical_hd_source", {})

    checks = {
        "queue_identity_current_a_shard": bool(
            queue
            and queue.get("path") == QUEUE_PATH
            and queue.get("action") == "localize_text"
            and INDEX % 3 == 0
        ),
        "queue_retains_c136_source_exhaustion": (
            "Q00034 C136 consumed B00180@2af61fc8 PASS source-acquisition exhaustion"
            in qnote
            and "do not repeat source probes" in qnote
        ),
        "canonical_inventory_identity": canonical == LOCKED_CANONICAL,
        "b00180_asset_identity": bool(
            b_asset
            and b_asset.get("index") == INDEX
            and b_asset.get("asset") == ASSET
            and b_asset.get("queue_path") == QUEUE_PATH
            and b_asset.get("canonical_sha256") == LOCKED_CANONICAL["sha256"]
        ),
        "b00180_drive_exact_name_miss": bool(
            drive.get("exact_filename_matches") == 0
            and drive.get("result") == "SOURCE_TRANSPORT_MISS"
        ),
        "b00180_direct_release_byte_identity": bool(
            direct.get("git_blob_sha") == LOCKED_DIRECT_BLOB
            and direct.get("release_bundle_member_git_blob_sha") == LOCKED_DIRECT_BLOB
            and direct.get("exact_byte_identity_with_pinned_release_member") is True
        ),
        "b00180_release_is_noncanonical": bool(
            release.get("member_sha256") == LOCKED_RELEASE_SHA256
            and release.get("member_dimensions") == LOCKED_RELEASE_DIMS
            and release.get("canonical_sha256_match") is False
            and LOCKED_RELEASE_SHA256 != LOCKED_CANONICAL["sha256"]
        ),
        "b00180_source_exhausted": bool(
            b_asset
            and b_asset.get("final_source_status")
            == "SOURCE_ACQUISITION_EXHAUSTED_NO_EXACT_CANONICAL_BYTES"
        ),
        "c136_consumed_exact_b00180_result": bool(
            b_input
            and b_input.get("result_sha") == LOCKED_B00180_RESULT
            and b_disp
            and b_disp.get("status") == "PASS"
        ),
        "c136_validation_identity": (
            c136.get("validation_bearing_result_sha") == LOCKED_C136_RESULT
            and c136.get("automation_validation") == "PASS"
        ),
        "controller_schema30_current_a_ownership": (
            roles.get("schema_version") == 30
            and roles.get("lanes", {}).get("A", {}).get("primary_index_modulo_3") == 0
            and roles.get("concurrency_safety", {}).get("stable_shard_rule")
            == "asset_queue.index % 3: A=0, B=1, E=2"
        ),
        "source_transport_policy_current": (
            source_transport.get("acquisition_order")
            == [
                "GOOGLE_DRIVE_EXACT_RELATIVE_PATH",
                "PINNED_UPSTREAM_DIRECT_FILE",
                "PINNED_V0.25.10A_RELEASE",
            ]
            and drive_policy.get("folder_id") == DRIVE_FOLDER_ID
            and drive_policy.get("read_only") is True
            and drive_policy.get("historical_localized_outputs_allowed") is False
        ),
        "pinned_source_policy_unchanged": all(
            token in contract
            for token in (PINNED_TAG, PINNED_COMMIT, PINNED_ZIP_SHA256, DRIVE_FOLDER_ID)
        ),
        "sticky_source_guard_policy_enabled": (
            roles.get("production_strategy", {})
            .get("source_exhaustion_reselection", {})
            .get("skip_unchanged_source_acquisition_exhausted") is True
        ),
    }

    unchanged = all(checks.values())
    out = {
        "schema_version": 30,
        "task_id": "LOCALIZATION-LOCALIZATION_A-00371",
        "wave_id": "P00239",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "checks": checks,
        "current_canonical": canonical,
        "locked_canonical": LOCKED_CANONICAL,
        "locked_b00180_result_sha": LOCKED_B00180_RESULT,
        "locked_c136_validation_bearing_result_sha": LOCKED_C136_RESULT,
        "locked_direct_blob_sha": LOCKED_DIRECT_BLOB,
        "locked_release_sha256": LOCKED_RELEASE_SHA256,
        "locked_release_dimensions": LOCKED_RELEASE_DIMS,
        "source_reprobe_authorized": False,
        "release_member_substitution_authorized": False,
        "candidate_rebuild_authorized": False,
        "reactivation_triggers": [
            "index228 canonical inventory identity changes",
            "asset_queue no longer retains C136/B00180 source-acquisition exhaustion",
            "C136/B00180 source-exhaustion evidence is superseded by authoritative C evidence",
            "pinned source tag/commit/bundle or approved Drive transport policy changes",
            "an exact canonical E7F6E9B7 source transport is newly recorded by authoritative evidence",
        ],
        "fresh_rescan_required": not unchanged,
        "result": (
            "BLOCKED_UNCHANGED_SOURCE_ACQUISITION_EXHAUSTED_FINGERPRINT"
            if unchanged else "FRESH_RESCAN_REQUIRED"
        ),
        "runtime_validation": "UNTESTED",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if unchanged else 2)

if __name__ == "__main__":
    main()
