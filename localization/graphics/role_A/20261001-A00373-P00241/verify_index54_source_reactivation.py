#!/usr/bin/env python3
"""Fail-closed source-identity reactivation guard for A-owned index54/FA7BBB13.

This tool performs no source acquisition. It replays the GitHub-SSOT evidence
accepted by C172/Q00070 and exits 0 only while the current canonical inventory
still disagrees with the exact pinned v0.25.10a / approved-Drive source bytes.
When any dependency fingerprint changes, it exits 2 and requires a fresh
producer rescan before source probing, candidate reuse, or rendering.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

INDEX = 54
ASSET = "FA7BBB13"
QUEUE_PATH = "textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds"

LOCKED_CANONICAL = {
    "sha256": "f7695f10b8761ab00ff988c443fd864340d5569a7047cc7342c3e1e3e96db7b6",
    "width": 4096,
    "height": 2048,
    "mode": "RGBA",
}
LOCKED_ACQUIRED_SHA256 = "61c82072fcc44e9e5f4c6f127d2a29b17abecf5cdb536a5609512246d1ab8d15"
LOCKED_A00323_RESULT = "d40716564a256cf6425b62dcf01038550769269f"
LOCKED_C172_RESULT = "b0388771ec0f8835898c4300c061b16a0fca8af7"
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    root = Path(args.repo_root)

    inv = csv_row(root, "localization/graphics/inventory.csv", "path", QUEUE_PATH)
    queue = csv_row(root, "localization/graphics/asset_queue.csv", "index", str(INDEX))
    a323 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00323.json")
    c172 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00333.json")
    gate = load_json(
        root,
        "localization/graphics/role_A/20261001-A00323-P00198/"
        "A00323_P00198_INDEX54_SOURCE_REACTIVATION_GATE.json",
    )
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
    c_input = next(
        (
            row
            for row in c172.get("qa_batch_inputs", [])
            if row.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00323"
        ),
        None,
    )
    c_disp = next(
        (
            row
            for row in c172.get("qa_dispositions", [])
            if row.get("task_id") == "LOCALIZATION-LOCALIZATION_A-00323"
        ),
        None,
    )
    source_transport = roles.get("source_transport", {})
    drive_policy = source_transport.get("canonical_hd_source", {})

    checks = {
        "queue_identity_current_a_shard": bool(
            queue
            and queue.get("path") == QUEUE_PATH
            and queue.get("action") == "localize_text"
            and INDEX % 3 == 0
        ),
        "queue_retains_c172_identity_mismatch": (
            "Q00070 C172 A00323@d4071656 PASS PREFLIGHT_ONLY"
            in qnote
            and "SOURCE_IDENTITY_MISMATCH" in qnote
        ),
        "canonical_inventory_identity": canonical == LOCKED_CANONICAL,
        "a00323_result_identity": (
            a323.get("authoritative_result_sha") == LOCKED_A00323_RESULT
            and a323.get("material_deliverable", {}).get("final_source_outcome")
            == "SOURCE_IDENTITY_MISMATCH"
        ),
        "a00323_gate_identity": (
            gate.get("current_canonical", {}).get("expected_sha256")
            == LOCKED_CANONICAL["sha256"]
            and gate.get("acquisition_tiers", [])[0].get("sha256")
            == LOCKED_ACQUIRED_SHA256
            and gate.get("final_source_outcome") == "SOURCE_IDENTITY_MISMATCH"
            and gate.get("lineage_reconciliation", {}).get(
                "existing_candidate_reuse_authorized"
            )
            is False
        ),
        "c172_consumed_exact_a00323_result": bool(
            c_input
            and c_input.get("result_sha") == LOCKED_A00323_RESULT
            and c_disp
            and c_disp.get("status") == "PASS"
            and c_disp.get("production_readiness") == "PREFLIGHT_ONLY"
        ),
        "c172_validation_identity": (
            c172.get("validation_bearing_result_sha") == LOCKED_C172_RESULT
            and c172.get("automation_validation") == "PASS"
        ),
        "current_schema30_a_ownership": (
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
        "sticky_dependency_policy_present": (
            "A blocker with unchanged dependency inputs MUST NOT be re-reviewed every wave."
            in contract
            and "retry_requires_dependency_fingerprint_change_or_explicit_user_instruction"
            in json.dumps(roles.get("production_strategy", {}), sort_keys=True)
        ),
    }

    unchanged = all(checks.values())
    out = {
        "schema_version": 30,
        "task_id": "LOCALIZATION-LOCALIZATION_A-00373",
        "wave_id": "P00241",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "checks": checks,
        "current_canonical": canonical,
        "locked_canonical": LOCKED_CANONICAL,
        "locked_acquired_sha256": LOCKED_ACQUIRED_SHA256,
        "locked_a00323_result_sha": LOCKED_A00323_RESULT,
        "locked_c172_validation_bearing_result_sha": LOCKED_C172_RESULT,
        "source_reprobe_authorized": False,
        "noncanonical_source_substitution_authorized": False,
        "historical_candidate_reuse_authorized": False,
        "candidate_rebuild_authorized": False,
        "reactivation_triggers": [
            "index54 canonical inventory identity changes",
            "asset_queue no longer retains C172/A00323 SOURCE_IDENTITY_MISMATCH",
            "C172/A00323 source-identity evidence is superseded by authoritative later C evidence",
            "pinned source tag/commit/bundle or approved Drive transport policy changes",
            "an exact source matching f7695f10... is newly recorded by authoritative evidence",
            "explicit user instruction changes the dependency policy",
        ],
        "fresh_rescan_required": not unchanged,
        "result": (
            "BLOCKED_UNCHANGED_SOURCE_IDENTITY_MISMATCH_FINGERPRINT"
            if unchanged
            else "FRESH_RESCAN_REQUIRED"
        ),
        "runtime_validation": "UNTESTED",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if unchanged else 2)


if __name__ == "__main__":
    main()
