"""Import only exact-source, protected-art-safe, native BC3 pixel fixes TEST_ONLY.

This lane is separate from C1 approval; original A/B files are preserved.
Native strict DDS QA must run again; C1/C3 and game runtime remain pending.
"""
import hashlib,json,re
from pathlib import Path

BASE="localization/automation_inputs/native_source_owner_canary"
SCHEMA="outrun-hd-bc3-single-mip-full-owner-pixel-fix-testonly-v1"
SHA=re.compile(r"^[0-9a-f]{64}$")
RID=re.compile(r"^Q[0-9]{3}_[a-f0-9]{16}(?:_RB_B)?$")

def sha(b):return hashlib.sha256(b).hexdigest()

def apply_test_only_source_owner_overrides(root,groups):
    root=Path(root)
    directory=root/BASE
    if not directory.is_dir():return 0
    indexed={r["roi_id"]:r for rows in groups.values() for r in rows}
    total=0
    for p in sorted(directory.glob("Q*.json")):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>16000:
            raise ValueError("BC3_OWNER_RECEIPT_UNSAFE_FILE")
        rec=json.loads(p.read_text(encoding="utf-8"))
        rid=rec.get("roi_id","")
        if not RID.fullmatch(rid) or p.stem!=rid or rid not in indexed:
            raise ValueError("BC3_OWNER_RECEIPT_NOT_ORIGINAL_ROI")
        row=indexed[rid]
        if (rec.get("schema")!=SCHEMA or
            rec.get("status")!="MIP1_INDEX_ONLY_SOURCE_AND_PROTECTED_PASS_TEST_ONLY" or
            rec.get("release_approved") is not False or
            rec.get("runtime_validation")!="UNTESTED" or
            rec.get("visual_qa")!="C1_C3_UNTESTED" or
            rec.get("source_dds_path")!=row["source_dds_path"] or
            rec.get("source_dds_sha256")!=row["source_dds_sha256"] or
            rec.get("role")!=row["roles"] or
            not SHA.fullmatch(rec.get("old_candidate_sha256","")) or
            not SHA.fullmatch(rec.get("candidate_sha256","")) or
            not SHA.fullmatch(rec.get("native_test_dds_sha256",""))):
            raise ValueError("BC3_OWNER_RECEIPT_UNVERIFIED")
        old=root/row["_candidate_rel"]
        if not old.is_file() or old.is_symlink() or sha(old.read_bytes())!=rec["old_candidate_sha256"]:
            raise ValueError("BC3_OWNER_ORIGINAL_AB_CANDIDATE_SHA_CHANGED")
        candidate=directory/(rid+".png")
        if (not candidate.is_file() or candidate.is_symlink()
            or candidate.stat().st_size>4*1024*1024
            or sha(candidate.read_bytes())!=rec["candidate_sha256"]):
            raise ValueError("BC3_OWNER_REPAIRED_PNG_SHA_CHANGED")
        if rec.get("source_native_bbox_xyxy")!=row["_bbox"]:
            raise ValueError("BC3_OWNER_ORIGINAL_BBOX_CHANGED")
        row["_candidate_rel"]=str(candidate.relative_to(root))
        row["_candidate_import_mode"]="SOURCE_OWNER_BC3_MIP1_TEST_ONLY_C1_C3_PENDING"
        row["_source_owner_canary_sha256"]=rec["native_test_dds_sha256"]
        total+=1
    return total
