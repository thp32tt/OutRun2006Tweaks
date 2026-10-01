#!/usr/bin/env python3
"""Schema31 fail-closed semantic source-dependency guard for A-owned index36/06AB5CEE.

This tool performs no network/source acquisition and never directly authorizes a
candidate rebuild. It fingerprints only dependencies that can legitimately
reactivate the sticky source-acquisition blocker: queue/inventory identity,
the C-accepted A00290 exact-name guard, canonical Drive transport semantics,
pinned source identity, and the source-exhaustion reselection policy. GitHub
access/recovery policy churn is intentionally excluded because it does not
change source bytes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

INDEX = 36
ASSET = "06AB5CEE"
QUEUE_PATH = "textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
LOCKED_CANONICAL = {
    "sha256": "e02db9b4e04747e2a74295e8f5a01e07f0ed88d31832f4169b1e5996bc30f1eb",
    "width": 4096,
    "height": 4096,
    "mode": "RGBA",
}
LOCKED_A00290_RESULT = "2c86a9f3a0a5fef5990fc7adffc18be73310660f"
C_ACCEPTANCE_MARKER = "Q00063 C165 consumed A00290@2c86a9f3 PASS"
PINNED_TAG = "v0.25.10a"
PINNED_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
DRIVE_FOLDER_ID = "1TpFYOgf0ulxmj6lJozHjAS-69asQajXr"
DRIVE_SUBTREE = "OutRun2006_Korean_Artifacts/90_ARCHIVE/LOCALIZATION_SNAPSHOT_20260927_0302/03_ORIGINAL_REFERENCE/hd_source/OR2-HD-GUI-v0.25.10a/textures/load"
ACQUISITION_ORDER = [
    "GOOGLE_DRIVE_EXACT_RELATIVE_PATH",
    "PINNED_UPSTREAM_DIRECT_FILE",
    "PINNED_V0.25.10A_RELEASE",
]

def load_json(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))

def csv_row(root: Path, rel: str, predicate):
    with (root / rel).open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if predicate(row):
                return row
    return None

def digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    root = Path(args.repo_root)

    queue = csv_row(root, "localization/graphics/asset_queue.csv", lambda r: r.get("index") == str(INDEX))
    inv = csv_row(root, "localization/graphics/inventory.csv", lambda r: r.get("path") == QUEUE_PATH)
    roles = load_json(root, "localization/controller_roles.json")
    a00290 = load_json(root, "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00290.json")
    contract = (root / "docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")

    current_canonical = None if inv is None else {
        "sha256": inv.get("sha256"),
        "width": int(inv.get("width") or 0),
        "height": int(inv.get("height") or 0),
        "mode": inv.get("mode"),
    }
    source_transport = roles.get("source_transport", {})
    drive = source_transport.get("canonical_hd_source", {})
    source_reselection = roles.get("production_strategy", {}).get("source_exhaustion_reselection", {})

    semantic_dependencies = {
        "queue": {
            "index": INDEX,
            "path": None if queue is None else queue.get("path"),
            "action": None if queue is None else queue.get("action"),
            "shard_modulo_3": INDEX % 3,
        },
        "canonical_inventory": current_canonical,
        "accepted_guard": {
            "task_id": "LOCALIZATION-LOCALIZATION_A-00290",
            "result_sha": a00290.get("authoritative_result_sha") or a00290.get("result_sha"),
            "c_acceptance_marker_present": bool(queue and C_ACCEPTANCE_MARKER in queue.get("notes", "")),
        },
        "source_transport": {
            "provider": drive.get("provider"),
            "folder_id": drive.get("folder_id"),
            "allowed_subtree": drive.get("allowed_subtree"),
            "acquisition_order": source_transport.get("acquisition_order"),
        },
        "pinned_source": {
            "tag": PINNED_TAG,
            "commit": PINNED_COMMIT,
            "zip_sha256": PINNED_ZIP_SHA256,
            "tokens_present_in_contract": all(x in contract for x in (PINNED_TAG, PINNED_COMMIT, PINNED_ZIP_SHA256, DRIVE_FOLDER_ID)),
        },
        "sticky_policy": {
            "skip_unchanged_source_acquisition_exhausted": source_reselection.get("skip_unchanged_source_acquisition_exhausted"),
            "retry_only_on_dependency_fingerprint_change": source_reselection.get("retry_only_on_dependency_fingerprint_change"),
        },
    }

    locked_semantics = {
        "queue": {"index": INDEX, "path": QUEUE_PATH, "action": "localize_text", "shard_modulo_3": 0},
        "canonical_inventory": LOCKED_CANONICAL,
        "accepted_guard": {
            "task_id": "LOCALIZATION-LOCALIZATION_A-00290",
            "result_sha": LOCKED_A00290_RESULT,
            "c_acceptance_marker_present": True,
        },
        "source_transport": {
            "provider": "google_drive",
            "folder_id": DRIVE_FOLDER_ID,
            "allowed_subtree": DRIVE_SUBTREE,
            "acquisition_order": ACQUISITION_ORDER,
        },
        "pinned_source": {
            "tag": PINNED_TAG,
            "commit": PINNED_COMMIT,
            "zip_sha256": PINNED_ZIP_SHA256,
            "tokens_present_in_contract": True,
        },
        "sticky_policy": {
            "skip_unchanged_source_acquisition_exhausted": True,
            "retry_only_on_dependency_fingerprint_change": True,
        },
    }

    checks = {
        "current_schema_at_least_31": int(roles.get("schema_version") or 0) >= 31,
        "a_owns_index36": roles.get("lanes", {}).get("A", {}).get("primary_index_modulo_3") == 0 and INDEX % 3 == 0,
        "semantic_dependencies_equal_locked": semantic_dependencies == locked_semantics,
        "exact_name_alias_guard_retained": bool(queue and "alias substitution forbidden" in queue.get("notes", "").lower()),
        "github_access_policy_excluded_from_source_fingerprint": "github_access_validation" not in semantic_dependencies,
    }
    unchanged = all(checks.values())
    result = {
        "schema_version": 31,
        "schema": "outrun-a00388-index36-source-dependency-semantics-guard-v2",
        "task_id": "LOCALIZATION-LOCALIZATION_A-00388",
        "wave_id": "P00256",
        "lane": "LOCALIZATION_A",
        "index": INDEX,
        "asset": ASSET,
        "queue_path": QUEUE_PATH,
        "current_controller_schema_version": roles.get("schema_version"),
        "semantic_dependencies": semantic_dependencies,
        "locked_semantic_dependencies": locked_semantics,
        "semantic_dependency_fingerprint": digest(semantic_dependencies),
        "locked_semantic_dependency_fingerprint": digest(locked_semantics),
        "checks": checks,
        "excluded_non_source_dependency_families": [
            "github_access_validation",
            "runtime_recovery",
            "runtime_tuning",
            "controller_prompt_transport_wording",
        ],
        "source_reprobe_authorized": False,
        "alias_substitution_authorized": False,
        "candidate_rebuild_authorized": False,
        "fresh_producer_rescan_required": not unchanged,
        "result": "BLOCKED_UNCHANGED_SOURCE_DEPENDENCY_SEMANTICS" if unchanged else "FRESH_PRODUCER_RESCAN_REQUIRED",
        "runtime_validation": "UNTESTED",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if unchanged else 2)

if __name__ == "__main__":
    main()
