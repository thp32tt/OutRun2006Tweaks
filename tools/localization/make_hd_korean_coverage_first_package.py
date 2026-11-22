#!/usr/bin/env python3
"""Package a complete-coverage HD Korean TEST_ONLY preview with verified rollback.

The manifest is intentionally compatible with Install-OutRunKoreanTest.ps1.
No release or game-runtime approval is inferred from mechanical ROI coverage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

SOURCE_ZIP = "OUTRUN_HD_KOREAN_HYBRID_TEST_ONLY.zip"
OUTPUT_ZIP = "OUTRUN_HD_KOREAN_COVERAGE_FIRST_TEST_ONLY.zip"
MANIFEST = "TEST_ONLY_INSTALL_MANIFEST.json"
TOTAL_ROI = 954
TOTAL_DDS = 104
SAFE_PATH = re.compile(r"^textures/load/(?:(?:Keyboard|PlayStation|Switch|Xbox)/)?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.dds$")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def zput(z, path: str, raw: bytes) -> None:
    info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    z.writestr(info, raw, compresslevel=3)


def package(report_file: str, source_zip: str, installer_file: str, output_dir: str) -> dict:
    report = json.loads(Path(report_file).read_text(encoding="utf-8"))
    if (report.get("schema") != "outrun.github-hd-korean-hybrid-completion.v1"
            or report.get("release_approved") is not False
            or report.get("runtime_validation") != "UNTESTED"
            or report.get("active_roi_total") != TOTAL_ROI
            or report.get("active_dds_total") != TOTAL_DDS
            or report.get("source_dds_verified") != TOTAL_DDS
            or report.get("output_dds_count") != TOTAL_DDS
            or report.get("translation_coverage_accounted") != TOTAL_ROI
            or report.get("translation_coverage_complete") is not True
            or report.get("fallback_hold_count") != 0):
        raise ValueError("COVERAGE_FIRST_INCOMPLETE_OR_UNVERIFIED")
    if report.get("ab_candidate_applied_count", 0) > TOTAL_ROI:
        raise ValueError("INVALID_A_B_USAGE_COUNTER")

    installer = Path(installer_file).read_bytes()
    if (b"ConfirmTestOnly" not in installer or b"Backup" not in installer
            or b"Rollback" not in installer or b"ApplyAll" not in installer):
        raise ValueError("INSTALLER_NOT_REVERSIBLE")
    input_zip = Path(source_zip)
    if digest(input_zip.read_bytes()) != report.get("zip_sha256"):
        raise ValueError("SOURCE_OUTPUT_ZIP_SHA_CONFLICT")
    expected = {item["target"]: item for item in report.get("atlases", [])}
    if len(expected) != TOTAL_DDS or len(report["atlases"]) != TOTAL_DDS:
        raise ValueError("DUPLICATE_OR_MISSING_ATLASES")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    result = out / OUTPUT_ZIP

    with zipfile.ZipFile(input_zip) as src:
        if src.testzip() is not None:
            raise ValueError("SOURCE_ZIP_CRC_BAD")
        names = src.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected) | {"TEST_ONLY_MANIFEST.json"}:
            raise ValueError("EXTRA_OR_MISSING_SOURCE_DDS")
        source_manifest = json.loads(src.read("TEST_ONLY_MANIFEST.json"))
        if (source_manifest.get("status") != "TEST_ONLY_NOT_RUNTIME_APPROVED"
                or source_manifest.get("dds_count") != TOTAL_DDS
                or source_manifest.get("translation_coverage_complete") is not True
                or source_manifest.get("translation_coverage_accounted") != TOTAL_ROI
                or source_manifest.get("entries") != {
                    p: item["output_dds_sha256"] for p, item in expected.items()}):
            raise ValueError("SOURCE_HYBRID_MANIFEST_CONFLICT")
        for name in sorted(expected):
            item = expected[name]
            if not SAFE_PATH.fullmatch(name):
                raise ValueError("UNSAFE_TARGET_PATH")
            if not re.fullmatch(r"[0-9a-f]{64}", item.get("source_sha256", "")):
                raise ValueError("ORIGINAL_SHA_NOT_PINNED")
            if item.get("orientation") not in ("NORMAL", "FLIPY"):
                raise ValueError("SOURCE_ORIENTATION_UNVERIFIED")
            raw = src.read(name)
            if raw[:4] != b"DDS " or digest(raw) != item["output_dds_sha256"]:
                raise ValueError("DDS_BYTES_OR_SHA_INVALID")
            files.append({
                "path": name,
                "original_hd_sha256": item["source_sha256"],
                "test_only_dds_sha256": digest(raw),
                "orientation": item["orientation"],
                "painted_roi_count": item["fallback_painted"],
                "ab_applied": item["ab_candidates_applied"],
            })
        manifest = {
            "schema": "outrun.korean.hd-preview-install.v1",
            "status": "TEST_ONLY_NOT_RELEASE_APPROVED",
            "release_approved": False,
            "runtime_validation": "UNTESTED",
            "visual_qa": "BEST_EFFORT_NOT_INDEPENDENTLY_APPROVED",
            "source_mode": "HD_SHA_PINNED_A_B_FIRST_FALLBACK",
            "total_roi": TOTAL_ROI,
            "translated_roi_test_only": report["translation_coverage_accounted"],
            "represented_roi_not_unique_paint": report["duplicate_translation_represented_count"],
            "held_roi": report["fallback_hold_count"],
            "atlas_count": TOTAL_DDS,
            "ab_candidate_applied_count": report["ab_candidate_applied_count"],
            "needs_actual_game_test": True,
            "install_requires_explicit_test_consent": True,
            "files": files,
            "warning": "Best-effort Korean: text can overlap, English may remain in merged ROIs, DDS source formats may differ; use backed-up test copy first.",
        }
        with zipfile.ZipFile(result, "w", allowZip64=True) as dst:
            for name in sorted(expected):
                zput(dst, name, src.read(name))
            zput(dst, MANIFEST, (json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode())
            zput(dst, "Install-OutRunKoreanTest.ps1", installer)
            zput(dst, "README_TEST_ONLY.txt", (
                "OutRun 2006 HD Korean coverage-first TEST ONLY.\n"
                "This is a 954-ROI mechanical coverage candidate, NOT verified in game.\n"
                "Some original English/background art may remain, or Korean may overlap.\n"
                "Use an independent COPY of the game with the verified original HD textures.\n"
                "Unzip this file. Open PowerShell in the extracted folder.\n"
                "Canary (default 5 DDS): .\\Install-OutRunKoreanTest.ps1 -GameDirectory 'C:\\Path\\To\\Game' -ConfirmTestOnly\n"
                "After canary, rollback using the printed BACKUP path, then all DDS: .\\Install-OutRunKoreanTest.ps1 -GameDirectory 'C:\\Path\\To\\Game' -ConfirmTestOnly -ApplyAll\n"
                "If original DDS files were missing, consider -AllowMissingSource only after verifying the mod loader.\n"
                "Backup and rollback journal are created automatically.\n"
                "Rollback: use -Rollback -BackupDirectory with the printed BACKUP path.\n"
            ).encode())
    with zipfile.ZipFile(result) as z:
        if z.testzip() is not None:
            raise ValueError("PACKAGED_ZIP_CRC_BAD")
        if json.loads(z.read(MANIFEST)) != manifest:
            raise ValueError("PACKAGED_MANIFEST_READBACK_FAILED")
        if len(z.namelist()) != TOTAL_DDS + 3:
            raise ValueError("PACKAGED_FILE_COUNT_INVALID")
    summary = {
        "status": "COVERAGE_FIRST_TEST_ONLY",
        "total_roi": TOTAL_ROI,
        "coverage_accounted": manifest["translated_roi_test_only"],
        "dds_count": TOTAL_DDS,
        "a_b_applied": manifest["ab_candidate_applied_count"],
        "represented_roi_not_unique_paint": manifest["represented_roi_not_unique_paint"],
        "release_approved": False, "runtime_validation": "UNTESTED",
        "archive": OUTPUT_ZIP, "sha256": digest(result.read_bytes()),
    }
    (out / "coverage_package_summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--source-zip", required=True)
    p.add_argument("--installer", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    package(a.report, a.source_zip, a.installer, a.out)
