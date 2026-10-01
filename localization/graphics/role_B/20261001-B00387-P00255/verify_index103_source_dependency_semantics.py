#!/usr/bin/env python3
"""Schema31 fail-closed semantic source-dependency guard for B-owned index103/590A4724.

This tool performs no network/source acquisition and never directly authorizes a
candidate rebuild. It fingerprints only dependencies that can legitimately
reactivate the C141-accepted SOURCE_ACQUISITION_EXHAUSTED blocker: queue and
canonical inventory identity, the exact B00195 task/result evidence, approved
Drive transport semantics, pinned source identity, and sticky source-exhaustion
reselection policy. GitHub access/recovery policy churn is intentionally
excluded because it cannot change canonical source bytes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

INDEX = 103
ASSET = "590A4724"
QUEUE_PATH = "textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
LOCKED_CANONICAL = {
    "sha256": "b3ef4a34649ac699bd4c23d1d311b9850e0928f6cb5b98c1835f84de31561222",
    "width": 2048,
    "height": 2048,
    "mode": "RGBA",
}
LOCKED_B00195_RESULT = "0601de6d80e500fa95a254e820a6aa58c83409c9"
LOCKED_B00195_TASK_BLOB = "13ce41c5d2a414739900e1dfb1fd73bf9c66bbbc"
C_ACCEPTANCE_MARKER = "Q00039 C141 B00195 PASS PREFLIGHT_ONLY"
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

def git_blob_sha(data: bytes) -> str:
    hdr = ("blob %d\0" % len(data)).encode("ascii")
    return hashlib.sha1(hdr + data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    root = Path(args.repo_root)

    queue = csv_row(root, "localization/graphics/asset_queue.csv", lambda r: r.get("index") == str(INDEX))
    inv = csv_row(root, "localization/graphics/inventory.csv", lambda r: r.get("path") == QUEUE_PATH)
    roles = load_json(root, "localization/controller_roles.json")
    b00195_path = root / "docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00195.json"
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
    prior_bytes = b00195_path.read_bytes()

    semantic_dependencies = {
        "queue": {
            "index": INDEX,
            "path": None if queue is None else queue.get("path"),
            "action": None if queue is None else queue.get("action"),
            "shard_modulo_3": INDEX % 3,
        },
        "canonical_inventory": current_canonical,
        "accepted_guard": {
            "task_id": "LOCALIZATION-LOCALIZATION_B-00195",
            "result_commit_sha": LOCKED_B00195_RESULT,
            "task_blob_sha": git_blob_sha(prior_bytes),
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
        "queue": {"index": INDEX, "path": QUEUE_PATH, "action": "localize_text", "shard_modulo_3": 1},
        "canonical_inventory": LOCKED_CANONICAL,
        "accepted_guard": {
            "task_id": "LOCALIZATION-LOCALIZATION_B-00195",
            "result_commit_sha": LOCKED_B00195_RESULT,
            "task_blob_sha": LOCKED_B00195_TASK_BLOB,
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
        "b_owns_index103": roles.get("lanes", {}).get("B", {}).get("primary_index_modulo_3") == 1 and INDEX % 3 == 1,
        "semantic_dependencies_equal_locked": semantic_dependencies == locked_semantics,
        "github_access_policy_excluded_from_source_fingerprint": "github_access_validation" not in semantic_dependencies,
    }
    unchanged = all(checks.values())
    result = {
        "schema_version": 31,
        "schema": "outrun-b00387-index103-source-dependency-semantics-guard-v1",
        "task_id": "LOCALIZATION-LOCALIZATION_B-00387",
        "wave_id": "P00255",
        "lane": "LOCALIZATION_B",
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
