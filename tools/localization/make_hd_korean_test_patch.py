#!/usr/bin/env python3
"""Stage a SHA-verified, TEST_ONLY HD Korean DDS patch; never approve game release."""
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from pathlib import Path, PurePosixPath

DDS_ZIP = "OUTRUN_AB_HD_STRICT_CLEAN_TEST_ONLY.zip"
SOURCE_MANIFEST = "TEST_ONLY_MANIFEST.json"
STAGED_MANIFEST = "TEST_ONLY_INSTALL_MANIFEST.json"
OUTPUT_ZIP = "OUTRUN_KOREAN_HD_PREVIEW_TEST_ONLY.zip"
QA_SCHEMA = "outrun.ab-imagegen-hd-strict.v2"
PATH_RE = re.compile(r"^textures/load/(?:(?:Keyboard|PlayStation|Switch|Xbox)/)?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.dds$")

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def safe_dds_path(path):
    if not isinstance(path, str) or not PATH_RE.fullmatch(path):
        return False
    p = PurePosixPath(path)
    return not p.is_absolute() and ".." not in p.parts and "\\" not in path

def zwrite(z, name, raw):
    entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100644 << 16
    z.writestr(entry, raw, compresslevel=4)

def stage(qa_path, source_zip, installer_path, output_dir, source_run_id, source_commit):
    qa = json.loads(Path(qa_path).read_text(encoding="utf-8"))
    assert qa["schema"] == QA_SCHEMA, "QA_SCHEMA"
    assert qa["active_roi_total"] == 954, "TOTAL_ROI"
    assert qa["imported_roi_total"] == 954 and qa["pending_import"] == 0, "NOT_ALL_AB_IMPORTED"
    assert qa["release_approved"] is False and qa["runtime_validation"] == "UNTESTED", "INVALID_APPROVAL"
    assert qa["source_dds_missing_rows"] == 0 and qa["source_sha_conflict_rows"] == 0, "BAD_SOURCE_SHA"
    assert qa["translated_roi_generated"] + sum(qa["hold_roi_reason_counts"].values()) == 954, "COVERAGE_MISMATCH"
    assert re.fullmatch(r"[0-9a-f]{40}", source_commit), "BAD_COMMIT"
    assert str(source_run_id).isdecimal() and int(source_run_id) > 0, "BAD_RUN_ID"
    archive = Path(source_zip)
    assert sha256(archive.read_bytes()) == qa["zip_sha256"], "QA_ZIP_SHA_MISMATCH"
    installer = Path(installer_path).read_bytes()
    assert b"ConfirmTestOnly" in installer and b"Backup" in installer, "INSTALLER_MISSING_SAFETY"
    reported = qa["generated"]
    grouped = {record["target"]: record for record in reported}
    assert len(grouped) == len(reported), "DUPLICATE_ATLAS"
    manifest_files, ids = [], set()
    with zipfile.ZipFile(archive) as src:
        assert src.testzip() is None, "BAD_ZIP_CRC"
        source_members = src.namelist()
        assert len(source_members) == len(set(source_members)), "DUPLICATE_ZIP_MEMBER"
        declaration = json.loads(src.read(SOURCE_MANIFEST))
        assert declaration["release_approved"] is False and declaration["game_runtime"] == "UNTESTED", "BAD_SOURCE_GATE"
        assert set(declaration["entries"]) == set(grouped), "SOURCE_MANIFEST_MISMATCH"
        assert set(source_members) == set(grouped) | {SOURCE_MANIFEST}, "UNEXPECTED_SOURCE_FILE"
        for name,record in sorted(grouped.items()):
            assert safe_dds_path(name), "UNSAFE_DDS_PATH:" + name
            raw = src.read(name)
            assert raw[:4] == b"DDS " and len(raw) >= 128, "BAD_DDS"
            digest = sha256(raw)
            assert digest == declaration["entries"][name] == record["dds_sha256"], "DDS_HASH_MISMATCH"
            assert re.fullmatch(r"[0-9a-f]{64}", record["origin_sha256"]), "ORIGINAL_SHA_UNPINNED"
            assert record["painted"], "EMPTY_ATLAS"
            roi_ids = [r["roi_id"] for r in record["painted"]]
            assert not any(r in ids for r in roi_ids), "DUPLICATE_PAINTED_ROI"
            ids.update(roi_ids)
            manifest_files.append({
                "path":name, "original_hd_sha256":record["origin_sha256"],
                "test_only_dds_sha256":digest, "orientation":record["orientation"],
                "painted_roi_ids":roi_ids,
                "held_roi_ids":[h["roi_id"] for h in record.get("holds",[])]
            })
        assert len(manifest_files) == qa["native_dds_generated"], "ATLAS_COUNT"
        assert len(ids) == qa["translated_roi_generated"], "ROI_COUNT"
        output = {
            "schema":"outrun.korean.hd-preview-install.v1",
            "status":"TEST_ONLY_NOT_RELEASE_APPROVED",
            "release_approved":False, "runtime_validation":"UNTESTED",
            "visual_qa":"REVIEW_REQUIRED",
            "install_requires_explicit_test_consent":True,
            "source_run_id":int(source_run_id), "source_commit":source_commit,
            "source_zip_sha256":qa["zip_sha256"],
            "total_roi":954, "translated_roi_test_only":len(ids),
            "held_roi":sum(qa["hold_roi_reason_counts"].values()),
            "atlas_count":len(manifest_files), "files":manifest_files,
            "warning":"NOT GAME APPROVED. Some atlases have held ROI; independent image/game review required."
        }
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        output_path = outdir / OUTPUT_ZIP
        with zipfile.ZipFile(output_path,"w") as final:
            for name in sorted(grouped):
                zwrite(final,name,src.read(name))
            zwrite(final,STAGED_MANIFEST,(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode())
            zwrite(final,"Install-OutRunKoreanTest.ps1",installer)
            zwrite(final,"README_TEST_ONLY.txt",(
                "OUTRUN HD Korean existing A/B pixels: TEST ONLY, no visual or runtime approval.\n"
                "Unzip to a safe location. Run Install-OutRunKoreanTest.ps1 -GameDirectory <game folder> -ConfirmTestOnly.\n"
                "Default canary installs only five verified atlas DDS; back up and test game before expanding.\n"
            ).encode())
    with zipfile.ZipFile(output_path) as z:
        assert z.testzip() is None, "OUTPUT_ZIP_CORRUPT"
        assert json.loads(z.read(STAGED_MANIFEST)) == output, "OUTPUT_MANIFEST_MISMATCH"
        assert set(z.namelist()) == set(grouped) | {STAGED_MANIFEST,"Install-OutRunKoreanTest.ps1","README_TEST_ONLY.txt"}, "OUTPUT_UNEXPECTED"
    summary = {k:output[k] for k in ("status","source_run_id","source_commit","atlas_count","translated_roi_test_only","held_roi")}
    summary["output_sha256"] = sha256(output_path.read_bytes())
    (outdir/"preview_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return summary

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--qa-report",type=Path,required=True)
    p.add_argument("--source-zip",type=Path,required=True)
    p.add_argument("--installer",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--source-run-id",required=True)
    p.add_argument("--source-commit",required=True)
    a = p.parse_args()
    print(json.dumps(stage(a.qa_report,a.source_zip,a.installer,a.output_dir,a.source_run_id,a.source_commit),ensure_ascii=False))
