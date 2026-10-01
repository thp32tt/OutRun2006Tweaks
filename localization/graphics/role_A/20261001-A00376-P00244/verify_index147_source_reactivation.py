#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index147 / 39BCA907.

No source bytes are acquired here. This replays the GitHub-SSOT dependency
fingerprint accepted by C176/Q00074. Exit 0 means the blocker is unchanged, so
duplicate source probing, noncanonical substitution, and candidate construction
remain forbidden. Exit 2 means a dependency changed and a fresh producer scan is
required.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

INDEX = 147
ASSET = "39BCA907"
QUEUE_PATH = "textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds"
LOCKED_CANONICAL = {
    "sha256": "c52f48b1d08781c70e9637b9c95103dc3ae8cc637ca0ed951f74cf1d69e40b72",
    "width": 2048,
    "height": 1024,
    "mode": "RGBA",
}
LOCKED_A00344_RESULT = "bea28331bbdbe605dea3f6c8fb4e27892b48f56d"
LOCKED_C176_RESULT = "507a781c4ac309fc7435c9f7064faa238b2278c5"
LOCKED_RELEASE_SHA256 = "b913c9670288f7b67be514ddb4bc7eaba97fe70e0e640ba744429bbb4e5625a5"
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    root = Path(args.repo_root)

    inv = csv_row(root, "localization/graphics/inventory.csv", "path", QUEUE_PATH)
    queue = csv_row(root, "localization/graphics/asset_queue.csv", "index", str(INDEX))
    a344 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00344.json")
    a344e = load_json(
        root,
        "localization/graphics/role_A/20261001-A00344-P00215/"
        "A00344_P00215_INDEX147_SOURCE_IDENTITY_MISMATCH.json",
    )
    c176 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00356.json")
    roles = load_json(root, "localization/controller_roles.json")
    contract = (root / "docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")

    canonical = None if inv is None else {
        "sha256": inv["sha256"],
        "width": int(inv["width"]),
        "height": int(inv["height"]),
        "mode": inv["mode"],
    }
    qnote = "" if queue is None else queue.get("notes", "")
    disp = next(
        (row for row in c176.get("qa_dispositions", [])
         if row.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00344"),
        None,
    )
    acq = a344e.get("acquisition", [])
    drive = next((x for x in acq if x.get("tier") == 1), {})
    direct = next((x for x in acq if x.get("tier") == 2), {})
    release = next((x for x in acq if x.get("tier") == 3), {})
    st = roles.get("source_transport", {})
    hd = st.get("canonical_hd_source", {})

    checks = {
        "queue_identity_current_a_shard": bool(
            queue and queue.get("path") == QUEUE_PATH
            and queue.get("action") == "localize_text" and INDEX % 3 == 0
        ),
        "queue_retains_c176_source_identity_mismatch": (
            "Q00074 C176 A00344@bea28331 PASS PREFLIGHT_ONLY SOURCE_IDENTITY_MISMATCH" in qnote
        ),
        "canonical_inventory_identity": canonical == LOCKED_CANONICAL,
        "a00344_result_identity": (
            a344.get("result_sha") == LOCKED_A00344_RESULT
            and a344.get("candidate_dds_modified") is False
        ),
        "a00344_terminal_evidence": (
            a344e.get("asset_index") == INDEX
            and a344e.get("asset_path") == QUEUE_PATH
            and a344e.get("canonical_inventory", {}).get("expected_sha256") == LOCKED_CANONICAL["sha256"]
            and a344e.get("identity_comparison", {}).get("terminal_typed_outcome") == "SOURCE_IDENTITY_MISMATCH"
            and a344e.get("production_readiness") == "PREFLIGHT_ONLY"
            and a344e.get("candidate_authorized") is False
        ),
        "approved_drive_exact_miss": drive.get("outcome") == "SOURCE_TRANSPORT_MISS",
        "pinned_direct_exact_miss": (
            direct.get("outcome") == "SOURCE_TRANSPORT_MISS"
            and direct.get("http_semantics") == "404_NOT_FOUND"
        ),
        "pinned_release_noncanonical": (
            release.get("archive_sha256") == PINNED_ZIP_SHA256
            and release.get("member_sha256") == LOCKED_RELEASE_SHA256
            and release.get("outcome") == "SOURCE_IDENTITY_MISMATCH"
            and LOCKED_RELEASE_SHA256 != LOCKED_CANONICAL["sha256"]
        ),
        "c176_consumed_exact_a00344": bool(
            disp and disp.get("result_sha") == LOCKED_A00344_RESULT
            and disp.get("status") == "PASS"
            and disp.get("production_readiness") == "PREFLIGHT_ONLY_SOURCE_IDENTITY_MISMATCH"
            and c176.get("validation_bearing_result_sha") == LOCKED_C176_RESULT
            and c176.get("automation_validation") == "PASS"
        ),
        "controller_schema30_current_a_ownership": (
            roles.get("schema_version") == 30
            and roles.get("lanes", {}).get("A", {}).get("primary_index_modulo_3") == 0
            and roles.get("concurrency_safety", {}).get("stable_shard_rule")
                == "asset_queue.index % 3: A=0, B=1, E=2"
        ),
        "source_transport_policy_current": (
            st.get("acquisition_order") == [
                "GOOGLE_DRIVE_EXACT_RELATIVE_PATH",
                "PINNED_UPSTREAM_DIRECT_FILE",
                "PINNED_V0.25.10A_RELEASE",
            ]
            and hd.get("folder_id") == DRIVE_FOLDER_ID
            and hd.get("read_only") is True
            and hd.get("historical_localized_outputs_allowed") is False
        ),
        "pinned_source_policy_unchanged": all(
            token in contract
            for token in (PINNED_TAG, PINNED_COMMIT, PINNED_ZIP_SHA256, DRIVE_FOLDER_ID)
        ),
        "sticky_source_guard_policy_enabled": (
            roles.get("production_strategy", {})
                 .get("source_exhaustion_reselection", {})
                 .get("skip_unchanged_source_acquisition_exhausted") is True
            and roles.get("production_strategy", {})
                    .get("preflight_suppression", {})
                    .get("source_guard_retry_requires_dependency_fingerprint_change") is True
        ),
    }
    unchanged = all(checks.values())
    out = {
        "schema_version": 30,
        "task_id": "LOCALIZATION-LOCALIZATION_A-00376",
        "wave_id": "P00244",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "checks": checks,
        "current_canonical": canonical,
        "locked_canonical": LOCKED_CANONICAL,
        "locked_a00344_result_sha": LOCKED_A00344_RESULT,
        "locked_c176_validation_bearing_result_sha": LOCKED_C176_RESULT,
        "locked_release_sha256": LOCKED_RELEASE_SHA256,
        "source_reprobe_authorized": False,
        "release_member_substitution_authorized": False,
        "candidate_rebuild_authorized": False,
        "reactivation_triggers": [
            "index147 canonical inventory identity changes",
            "asset_queue no longer retains C176/A00344 source-identity mismatch",
            "C176/A00344 evidence is superseded by authoritative C evidence",
            "pinned source tag/commit/bundle or approved Drive transport policy changes",
            "an exact canonical 39BCA907 source transport is newly recorded",
            "explicit user instruction changes dependency policy",
        ],
        "fresh_rescan_required": not unchanged,
        "result": (
            "BLOCKED_UNCHANGED_SOURCE_IDENTITY_MISMATCH_FINGERPRINT"
            if unchanged else "FRESH_RESCAN_REQUIRED"
        ),
        "runtime_validation": "UNTESTED",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if unchanged else 2)

if __name__ == "__main__":
    main()
