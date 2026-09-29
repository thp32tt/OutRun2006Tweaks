#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import struct
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "LOCALIZATION-LOCALIZATION_A-00191"
TARGET_BRANCH = "korean-localization-clean"
TAG = "v0.25.10a"
ZIP_URL = "https://github.com/envido32/OR2006Sprites/releases/download/v0.25.10a/OR2-HD-GUI-v0.25.10a.zip"
ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
ZIP_SIZE = 306223257
REPORT = ROOT / "localization/graphics/role_A/20260930-A00191-rollover1/A00191_MOD3_CANONICAL_SOURCE_AUDIT.json"
TASK = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00191.json"
INVENTORY = ROOT / "localization/graphics/inventory.csv"

ASSETS = [
    {
        "index": 135,
        "asset": "2B0863D6",
        "queue_path": "textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",
        "canonical_sha256": "7cb768c657869981b0e548293f68975a84d4e2fb179f29a7568dbf096c365521",
        "canonical_width": 2048,
        "canonical_height": 256,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS_VERIFIED_PRE_DISPATCH",
    },
    {
        "index": 147,
        "asset": "39BCA907",
        "queue_path": "textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds",
        "canonical_sha256": "c52f48b1d08781c70e9637b9c95103dc3ae8cc637ca0ed951f74cf1d69e40b72",
        "canonical_width": 2048,
        "canonical_height": 1024,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS_VERIFIED_PRE_DISPATCH",
    },
    {
        "index": 159,
        "asset": "4EDA9DE3",
        "queue_path": "textures/load/spr_sprani_sumo_fe_cvt_Exst/4EDA9DE3_512x256.dds",
        "canonical_sha256": "7ed5e0c85d3ef42b770dad21bdfa331b5eef374b80bff27bc1715f3c5b29fdbd",
        "canonical_width": 2048,
        "canonical_height": 1024,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS_VERIFIED_PRE_DISPATCH",
    },
    {
        "index": 201,
        "asset": "A9ABD877",
        "queue_path": "textures/load/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds",
        "canonical_sha256": "6ac5ffd02c9162499f09f0b476176b56f0b144789f546ef34147d94e0a8451e5",
        "canonical_width": 2048,
        "canonical_height": 2048,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS_VERIFIED_PRE_DISPATCH",
    },
]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob(path: str) -> str:
    import subprocess
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True).strip()

def dds_info(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        return {"valid_dds": False}
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    mip_count = struct.unpack_from("<I", data, 28)[0] or 1
    pf_flags = struct.unpack_from("<I", data, 80)[0]
    fourcc = data[84:88]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    rmask, gmask, bmask, amask = struct.unpack_from("<IIII", data, 92)
    if pf_flags & 0x4:
        fmt = fourcc.decode("latin1")
    elif rgb_bits == 32:
        fmt = "RGBA32"
    else:
        fmt = f"RGB{rgb_bits}"
    return {
        "valid_dds": True,
        "width": width,
        "height": height,
        "mip_count": mip_count,
        "pixel_format_flags": pf_flags,
        "fourcc": fourcc.decode("latin1"),
        "rgb_bit_count": rgb_bits,
        "r_mask": f"0x{rmask:08x}",
        "g_mask": f"0x{gmask:08x}",
        "b_mask": f"0x{bmask:08x}",
        "a_mask": f"0x{amask:08x}",
        "format_summary": fmt,
    }

def verify_inventory() -> None:
    rows = {}
    with INVENTORY.open(newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            rows[row[0]] = row
    failures = []
    for a in ASSETS:
        row = rows.get(a["queue_path"])
        if not row:
            failures.append(f"{a['index']}:{a['queue_path']}:missing")
            continue
        got_sha = row[1]
        got_w = int(row[2])
        got_h = int(row[3])
        got_mode = row[4]
        if (got_sha, got_w, got_h, got_mode) != (
            a["canonical_sha256"],
            a["canonical_width"],
            a["canonical_height"],
            a["canonical_mode"],
        ):
            failures.append(
                f"{a['index']}:inventory_changed sha={got_sha} size={got_w}x{got_h} mode={got_mode}"
            )
    if failures:
        raise SystemExit("current inventory fingerprint mismatch; fail closed: " + "; ".join(failures))

def download_verified_zip(dst: Path) -> dict:
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "OutRun2006Tweaks-A00191"})
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=120) as resp, dst.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            h.update(chunk)
            size += len(chunk)
    digest = h.hexdigest()
    if size != ZIP_SIZE or digest != ZIP_SHA256:
        raise SystemExit(f"pinned Release ZIP identity mismatch size={size} sha256={digest}")
    return {"bytes": size, "sha256": digest}

def main() -> None:
    verify_inventory()
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    base_sha = os.environ.get("A00191_BASE_SHA", "").strip() or os.environ.get("GITHUB_SHA", "").strip()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    TASK.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="a00191-") as td:
        zpath = Path(td) / "OR2-HD-GUI-v0.25.10a.zip"
        zip_identity = download_verified_zip(zpath)
        rows = []
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            for a in ASSETS:
                suffix = "/" + a["queue_path"]
                matches = [n for n in names if n == a["queue_path"] or n.endswith(suffix)]
                rec = dict(a)
                rec["archive_matches"] = matches
                if len(matches) == 0:
                    rec["release_outcome"] = "SOURCE_TRANSPORT_MISS"
                    rec["final_source_outcome"] = "SOURCE_ACQUISITION_EXHAUSTED"
                    rec["production_readiness_after"] = "PREFLIGHT_ONLY_SOURCE_ACQUISITION_EXHAUSTED"
                elif len(matches) > 1:
                    rec["release_outcome"] = "AMBIGUOUS_ARCHIVE_PATH_FAIL_CLOSED"
                    rec["final_source_outcome"] = "HOLD_STRICT_RECHECK"
                    rec["production_readiness_after"] = "PREFLIGHT_ONLY_AMBIGUOUS_RELEASE_PATH"
                else:
                    member = matches[0]
                    data = zf.read(member)
                    info = dds_info(data)
                    digest = sha256_bytes(data)
                    mode_ok = info.get("format_summary") == "RGBA32"
                    identity_ok = (
                        digest == a["canonical_sha256"]
                        and info.get("valid_dds")
                        and info.get("width") == a["canonical_width"]
                        and info.get("height") == a["canonical_height"]
                        and info.get("mip_count") == 1
                        and mode_ok
                    )
                    rec.update({
                        "archive_member": member,
                        "archive_member_bytes": len(data),
                        "archive_member_sha256": digest,
                        "dds": info,
                        "canonical_identity_ok": identity_ok,
                    })
                    if identity_ok:
                        rec["release_outcome"] = "SOURCE_ACQUIRED_EXACT_CANONICAL"
                        rec["final_source_outcome"] = "SOURCE_ACQUIRED_EXACT_CANONICAL"
                        rec["production_readiness_after"] = (
                            "PREFLIGHT_ONLY_EXACT_SOURCE_ACQUIRED__DIRECT_DECODED_SEMANTIC_BINDING_"
                            "SOURCE_EFFECT_MASK_CLEAN_PLATE_AND_V2_SAFE_BBOX_STILL_REQUIRED"
                        )
                    else:
                        rec["release_outcome"] = "SOURCE_IDENTITY_MISMATCH"
                        rec["final_source_outcome"] = "SOURCE_ACQUISITION_EXHAUSTED"
                        rec["production_readiness_after"] = "PREFLIGHT_ONLY_SOURCE_ACQUISITION_EXHAUSTED"
                rows.append(rec)

    exact = [r for r in rows if r["final_source_outcome"] == "SOURCE_ACQUIRED_EXACT_CANONICAL"]
    exhausted = [r for r in rows if r["final_source_outcome"] == "SOURCE_ACQUISITION_EXHAUSTED"]
    hold = [r for r in rows if r["final_source_outcome"] == "HOLD_STRICT_RECHECK"]

    report = {
        "schema_version": 13,
        "schema": "outrun-a00191-mod3-pinned-release-source-audit-v1",
        "task_id": TASK_ID,
        "lane": "LOCALIZATION_A",
        "target_branch": TARGET_BRANCH,
        "attempt": "1/3",
        "chat_rollover": 1,
        "recorded_at_kst": now,
        "base_sha": base_sha,
        "status": "PASS" if not hold else "HOLD_STRICT_RECHECK",
        "bundle": {
            "repository": "envido32/OR2006Sprites",
            "tag": TAG,
            "url": ZIP_URL,
            "expected_size": ZIP_SIZE,
            "expected_sha256": ZIP_SHA256,
            "verified_size": zip_identity["bytes"],
            "verified_sha256": zip_identity["sha256"],
            "identity_gate": "PASS",
        },
        "google_drive_pre_dispatch": {
            "account_label": "ezflash557",
            "search_mode": "exact_filename",
            "filenames": [Path(a["queue_path"]).name for a in ASSETS],
            "result": "SOURCE_TRANSPORT_MISS_4_OF_4",
            "write_performed": False,
        },
        "candidate_completion_fresh_scan": {
            "current_c_task": "LOCALIZATION-LOCALIZATION_C-00192",
            "current_c_batch": "Q00037",
            "render_ready_indices": [],
            "one_stage_to_render_indices": [],
            "already_rendered_static_qa_pass_indices": [99, 112, 130, 152, 237],
            "a00187_index99": "STATIC_QA_PASS_BY_C139_DO_NOT_RERENDER",
            "sticky_source_exhausted_a_indices_not_repeated": [30, 36, 48, 132, 228],
            "runtime_or_dependency_blocked_existing_candidates_not_rewritten": [12, 51, 54, 57, 60, 63, 102, 111, 195, 237],
            "index231": "FAIL_CLOSED_SEMANTIC_BINDING_INCOMPLETE",
            "selected_priority": "ONE_NEW_PREFLIGHT_SOURCE_TIER_BATCH_AFTER_ZERO_RUNNABLE_READY_TIER",
        },
        "assets": rows,
        "summary_counts": {
            "assets": len(rows),
            "exact_canonical_sources_acquired": len(exact),
            "source_acquisition_exhausted": len(exhausted),
            "hold_strict_recheck": len(hold),
        },
        "readiness_rule": (
            "Exact source acquisition alone does not create RENDER_READY. These assets still require direct decoded "
            "semantic-to-pixel binding, source-effect/removal/protected masks, independently QAed CLEAN_PLATE, "
            "measured orientation/slant and non-empty v2 candidate_safe_bbox before Korean lettering is permitted."
        ),
        "candidate_dds_modified": False,
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "runtime_test_performed": False,
        "runtime_validation": "UNTESTED",
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "google_drive_used": True,
        "google_drive_write_performed": False,
        "uploaded_archive_used": False,
        "gpt_library_used": False,
        "vr_ffb_dx_changes": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    task = {
        "schema_version": 13,
        "task_id": TASK_ID,
        "lane": "LOCALIZATION_A",
        "target_branch": TARGET_BRANCH,
        "attempt": "1/3",
        "chat_rollover": 1,
        "recorded_at_kst": now,
        "base_sha": base_sha,
        "base_head_sha": base_sha,
        "commit_mode": "GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_SOURCE_AUDIT_RESULT_THEN_BOOKKEEP_RESULT_SHA",
        "result": "PASS_MATERIAL_A_MOD3_INDICES135_147_159_201_PINNED_RELEASE_SOURCE_AUDIT_RUNTIME_UNTESTED",
        "summary": (
            f"Fresh C139/Q00037-aware A-shard scan has no runnable RENDER_READY or ONE_STAGE_TO_RENDER item. "
            f"Index99 is already STATIC_QA PASS and is not rerendered. This single legal preflight batch verifies "
            f"the pinned v0.25.10a bundle and audits A-owned indices135/147/159/201 after approved ezflash557 "
            f"exact-filename Drive misses. Exact canonical source acquired={len(exact)}, acquisition exhausted={len(exhausted)}, "
            f"strict hold={len(hold)}. No candidate DDS/shared state/runtime/build/N100/local-clone change is made."
        ),
        "evidence": [str(REPORT.relative_to(ROOT)).replace("\\", "/")],
        "material_deliverable": {
            "fallback_ladder_step": 4,
            "type": "A_MOD3_FOUR_ASSET_APPROVED_SOURCE_TIER_AUDIT",
            "indices": [a["index"] for a in ASSETS],
            "assets": [a["asset"] for a in ASSETS],
            "drive_exact_filename_misses": 4,
            "pinned_release_bundle_verified": True,
            "exact_canonical_sources_acquired": len(exact),
            "source_acquisition_exhausted": len(exhausted),
            "hold_strict_recheck": len(hold),
            "candidate_dds_modified": False,
            "materially_reduces_unresolved_work": True,
            "material_payload_in_result_commit": True,
            "report_path": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
        },
        "readiness_audit": {
            "shard_rule": "asset_queue.index % 3 == 0",
            "selected_indices": [a["index"] for a in ASSETS],
            "selected_priority": "ONE_PREFLIGHT_ONLY_BATCH_AFTER_FRESH_ZERO_RUNNABLE_CANDIDATE_SCAN",
            "current_c_gate": "C139/Q00037",
            "static_pass_not_repeated": [99, 112, 130, 152, 237],
            "sticky_source_exhausted_not_repeated": [30, 36, 48, 132, 228],
            "dependency_or_runtime_blocked_existing_candidates_not_rewritten": [12, 51, 54, 57, 60, 63, 102, 111, 195],
            "semantic_binding_fail_closed_not_rendered": [231],
            "readiness_after": {str(r["index"]): r["production_readiness_after"] for r in rows},
            "post_evidence_render_ready_count": 0,
            "post_evidence_one_stage_to_render_count": 0,
        },
        "source_results": [
            {
                "index": r["index"],
                "asset": r["asset"],
                "drive": r["drive_outcome"],
                "release": r["release_outcome"],
                "final": r["final_source_outcome"],
                "archive_member_sha256": r.get("archive_member_sha256"),
                "canonical_sha256": r["canonical_sha256"],
            }
            for r in rows
        ],
        "fingerprints": {
            "automation_contract_blob_sha": git_blob("docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md"),
            "controller_roles_blob_sha": git_blob("docs/automation/QUEUE_CONTROLLER_CONTRACT.md"),
            "inventory_blob_sha": git_blob("localization/graphics/inventory.csv"),
            "asset_queue_blob_sha": git_blob("localization/graphics/asset_queue.csv"),
            "c00192_task_blob_sha": git_blob("docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00192.json"),
            "a00187_task_blob_sha": git_blob("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00187.json"),
            "pinned_release_sha256": ZIP_SHA256,
        },
        "self_qa": (
            "PASS_A_MOD3_135_147_159_201__C139_ZERO_RUNNABLE_READY_TIER__DRIVE_EXACT_FILENAME_MISS_4_OF_4__"
            "PINNED_RELEASE_BUNDLE_SHA256_VERIFIED__PER_ASSET_SHA256_DIMENSIONS_RGBA32_MIP1_IDENTITY_FAIL_CLOSED__"
            "NO_PIXEL_CONSTRUCTION_WITHOUT_DIRECT_DECODED_BINDING_CLEAN_PLATE_SAFE_BBOX__NO_SHARED_STATE"
        ),
        "candidate_static_qa": "HOLD_NO_NEW_CANDIDATE_SOURCE_TIER_AUDIT_ONLY",
        "candidate_dds_modified": False,
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "runtime_test_performed": False,
        "runtime_validation": "UNTESTED",
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "google_drive_used": True,
        "google_drive_write_performed": False,
        "uploaded_archive_used": False,
        "gpt_library_used": False,
        "work_stolen_from_lane": None,
        "vr_ffb_dx_changes": False,
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
    }
    TASK.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
