#!/usr/bin/env python3
from __future__ import annotations

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
TASK_ID = "LOCALIZATION-LOCALIZATION_A-00168"
WAVE_ID = "P00083"
TAG = "v0.25.10a"
ASSET_ID = 306630789
ZIP_URL = "https://github.com/envido32/OR2006Sprites/releases/download/v0.25.10a/OR2-HD-GUI-v0.25.10a.zip"
ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
ZIP_SIZE = 306223257
REPORT = ROOT / "localization/graphics/role_A/20260930-A00168-P00083/A00168_P00083_PINNED_RELEASE_SOURCE_AUDIT.json"
TASK = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00168.json"

ASSETS = [
    {
        "index": 65,
        "asset": "EBEF6D20",
        "queue_path": "textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds",
        "canonical_sha256": "1ee491be92af2e70d0dae33a8c205b13b152f198f8a534136fac1c3c4e164a3e",
        "canonical_width": 512,
        "canonical_height": 512,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS",
        "pinned_direct_sha256": "78fdc0d8591689f2743de4700a681b05d08376a391a6f1e2855e186a80c12f23",
    },
    {
        "index": 89,
        "asset": "43B07A77",
        "queue_path": "textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
        "canonical_sha256": "0a2c9a32070771338dabc04a7bda67d9b474fd21d6a3456f60d9e1221fc8a96c",
        "canonical_width": 512,
        "canonical_height": 64,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS",
        "pinned_direct_sha256": "6db8e65661f76e5ac12e7090c039ced565731765e0cfc5dbe45329b52b5307f2",
    },
    {
        "index": 241,
        "asset": "E1639D2E",
        "queue_path": "textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",
        "canonical_sha256": "0af7362ff57b2ee9bfa04811838035861e919f5886244994dbede9aca6ed6c63",
        "canonical_width": 256,
        "canonical_height": 64,
        "canonical_mode": "RGBA",
        "drive_outcome": "SOURCE_TRANSPORT_MISS",
        "pinned_direct_sha256": "3277d04661e0e348d41d0393df57676ce620bef445ee7cf7d461057547d4ac8b",
    },
]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

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

def download_verified_zip(dst: Path) -> dict:
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "OutRun2006Tweaks-A00168"})
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
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    TASK.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="a00168-") as td:
        zpath = Path(td) / "OR2-HD-GUI-v0.25.10a.zip"
        zip_identity = download_verified_zip(zpath)
        rows = []
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            for a in ASSETS:
                suffix = "/" + a["queue_path"]
                matches = [n for n in names if n == a["queue_path"] or n.endswith(suffix)]
                if len(matches) == 0:
                    release_outcome = "SOURCE_TRANSPORT_MISS"
                    rec = {**a, "release_outcome": release_outcome, "archive_matches": []}
                elif len(matches) > 1:
                    release_outcome = "AMBIGUOUS_ARCHIVE_PATH_FAIL_CLOSED"
                    rec = {**a, "release_outcome": release_outcome, "archive_matches": matches}
                else:
                    member = matches[0]
                    data = zf.read(member)
                    info = dds_info(data)
                    digest = sha256_bytes(data)
                    identity_ok = (
                        digest == a["canonical_sha256"]
                        and info.get("valid_dds")
                        and info.get("width") == a["canonical_width"]
                        and info.get("height") == a["canonical_height"]
                    )
                    release_outcome = "SOURCE_ACQUIRED_EXACT_CANONICAL" if identity_ok else "SOURCE_IDENTITY_MISMATCH"
                    rec = {
                        **a,
                        "release_outcome": release_outcome,
                        "archive_member": member,
                        "archive_member_bytes": len(data),
                        "archive_member_sha256": digest,
                        "dds": info,
                        "identity_ok": identity_ok,
                    }
                # A00166 exhausted Drive; A00149 proved pinned direct bytes mismatched.
                if rec["release_outcome"] == "SOURCE_ACQUIRED_EXACT_CANONICAL":
                    final_source_outcome = "SOURCE_ACQUIRED_EXACT_CANONICAL"
                    next_state = "PREFLIGHT_ONLY_EXACT_SOURCE_ACQUIRED__CURRENT_CANONICAL_MASK_CLEAN_PLATE_REQUIRED"
                elif rec["release_outcome"] in ("SOURCE_TRANSPORT_MISS", "SOURCE_IDENTITY_MISMATCH"):
                    final_source_outcome = "SOURCE_ACQUISITION_EXHAUSTED"
                    next_state = "SOURCE_ACQUISITION_EXHAUSTED__SKIP_AND_CONTINUE_OTHER_RUNNABLE_ASSET"
                else:
                    final_source_outcome = "HOLD_STRICT_RECHECK"
                    next_state = "AMBIGUOUS_RELEASE_PATH_FAIL_CLOSED"
                rec["final_source_outcome"] = final_source_outcome
                rec["next_state"] = next_state
                rows.append(rec)

    exact_count = sum(r["release_outcome"] == "SOURCE_ACQUIRED_EXACT_CANONICAL" for r in rows)
    mismatch_count = sum(r["release_outcome"] == "SOURCE_IDENTITY_MISMATCH" for r in rows)
    miss_count = sum(r["release_outcome"] == "SOURCE_TRANSPORT_MISS" for r in rows)
    exhausted_count = sum(r["final_source_outcome"] == "SOURCE_ACQUISITION_EXHAUSTED" for r in rows)

    report = {
        "schema_version": 9,
        "schema": "outrun-a00168-pinned-release-source-audit-v1",
        "task_id": TASK_ID,
        "lane": "LOCALIZATION_A",
        "wave_id": WAVE_ID,
        "recorded_at_kst": now,
        "status": "PASS",
        "result": "PASS_PINNED_RELEASE_SOURCE_TIER_AUDIT_FAIL_CLOSED_RUNTIME_UNTESTED",
        "bundle": {
            "repository": "envido32/OR2006Sprites",
            "tag": TAG,
            "release_asset_id": ASSET_ID,
            "url": ZIP_URL,
            "expected_size": ZIP_SIZE,
            "expected_sha256": ZIP_SHA256,
            "verified_size": zip_identity["bytes"],
            "verified_sha256": zip_identity["sha256"],
            "identity_gate": "PASS",
        },
        "prior_tiers": {
            "google_drive": "A00166_SOURCE_TRANSPORT_MISS_3_OF_3",
            "pinned_direct_file": "A00149_SOURCE_IDENTITY_MISMATCH_3_OF_3",
        },
        "assets": rows,
        "summary_counts": {
            "assets": len(rows),
            "release_exact_canonical": exact_count,
            "release_identity_mismatch": mismatch_count,
            "release_transport_miss": miss_count,
            "source_acquisition_exhausted": exhausted_count,
        },
        "candidate_completion_rescan": {
            "candidate_dds_modified": False,
            "reason": "No asset becomes RENDER_READY solely from this audit unless the pinned Release member is exact canonical. Any exact source still lacks current-canonical source-effect/removal mask, independently QAed CLEAN_PLATE and final candidate_safe_bbox in the shared C-accepted state.",
            "qa_pending_skip": {"task_id": "LOCALIZATION-LOCALIZATION_A-00164", "index": 99, "asset": "4F68708E"},
            "dependency_blocked_direct_rework_indices": [51, 53, 111, 121],
        },
        "self_qa": {
            "zip_digest": "PASS",
            "exact_path_binding": "PASS_SUFFIX_BOUND_TO_FULL_QUEUE_RELATIVE_PATH",
            "inventory_identity": "PASS_CHECKED_SHA256_DIMENSIONS_PER_ASSET",
            "stale_4x_reuse": "REJECTED",
            "shared_state_modified": False,
            "peer_lane_files_modified": False,
            "runtime_validation": "UNTESTED",
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if exact_count:
        material_type = "PINNED_RELEASE_EXACT_CANONICAL_SOURCE_ACQUISITION_OR_AUDIT"
        material_advance = f"Pinned Release identity verified and {exact_count} exact canonical DDS source(s) acquired by path+SHA/dimensions; current-canonical mask/CLEAN_PLATE evidence remains required before render."
    else:
        material_type = "PINNED_RELEASE_FINAL_SOURCE_TIER_EXHAUSTION"
        material_advance = f"Pinned Release identity verified; no exact canonical DDS among the three target paths. {exhausted_count} asset(s) now have all approved acquisition tiers exhausted and can be skipped without repeating Drive/direct/Release probes."

    task = {
        "schema_version": 9,
        "task_id": TASK_ID,
        "lane": "LOCALIZATION_A",
        "target_branch": "korean-localization-clean",
        "attempt": "1/3",
        "wave_id": WAVE_ID,
        "recorded_at_kst": now,
        "commit_mode": "GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_MATERIAL_AND_TASK_RECORD",
        "base_head_sha": os.environ.get("GITHUB_SHA"),
        "result": "PASS_MATERIAL_PINNED_RELEASE_SOURCE_TIER_AUDIT_RUNTIME_UNTESTED",
        "summary": material_advance,
        "evidence": [str(REPORT.relative_to(ROOT)).replace("\\", "/")],
        "material_deliverable": {
            "fallback_ladder_step": 4,
            "type": material_type,
            "indices": [65, 89, 241],
            "assets": ["EBEF6D20", "43B07A77", "E1639D2E"],
            "verified_release_asset_id": ASSET_ID,
            "verified_release_sha256": ZIP_SHA256,
            "release_exact_canonical": exact_count,
            "release_identity_mismatch": mismatch_count,
            "release_transport_miss": miss_count,
            "source_acquisition_exhausted": exhausted_count,
            "candidate_dds_modified": False,
            "materially_reduces_unresolved_work": True,
            "material_payload_in_result_commit": True,
            "report_path": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
        },
        "readiness_audit": {
            "selected_priority": "PREFLIGHT_ONLY_FINAL_APPROVED_SOURCE_ACQUISITION_TIER",
            "qa_pending_skip": {"task_id": "LOCALIZATION-LOCALIZATION_A-00164", "index": 99, "asset": "4F68708E"},
            "direct_rework_dependency_blocked_indices": [51, 53, 111, 121],
            "explicit_render_ready_count": 0,
            "explicit_one_stage_to_render_count": 0,
            "selected_indices": [65, 89, 241],
            "post_evidence_render_ready_count": 0,
            "conclusion": "ZERO_NEW_CANDIDATE_EXCEPTION_VALID__PINNED_RELEASE_FINAL_SOURCE_TIER_EXECUTED",
        },
        "fingerprints": {
            "automation_contract_blob_sha": "8b7a840fcd756185761bbc39aafff255a7b3aefc",
            "controller_roles_blob_sha": "1479ad52b3e2e36b5dcfef9f10be865638c732fa",
            "inventory_blob_sha": "5a3d3b09d97063c65e2b2e356a20878e4c0a83df",
            "a00149_task_blob_sha": "90530a8a36fdd17e674972bfd9df421ce1c7e9db",
            "a00166_task_blob_sha": "c5acce98b3aeb4f92b9138703a7d932a279da56e",
            "pinned_release_sha256": ZIP_SHA256,
        },
        "self_qa": "PASS_ODD_65_89_241_PINNED_RELEASE_BUNDLE_VERIFIED__EXACT_PATH_AND_INVENTORY_IDENTITY_CHECKED__NO_STALE_SOURCE_RENDER__NO_SHARED_STATE",
        "candidate_static_qa": "HOLD_NO_NEW_CANDIDATE",
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "candidate_dds_modified": False,
        "runtime_test_performed": False,
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "google_drive_used": False,
        "gpt_library_used": False,
        "uploaded_archive_used": False,
        "work_stolen_from_lane": None,
        "vr_ffb_dx_changes": False,
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
        "runtime_validation": "UNTESTED",
    }
    TASK.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
