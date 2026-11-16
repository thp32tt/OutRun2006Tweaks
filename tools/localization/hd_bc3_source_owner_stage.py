#!/usr/bin/env python3
"""Stage only real SHA-checked BC3 saved-DDS canary PASS PNGs, never approvals."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from hd_bc3_source_owner_import import BASE,SCHEMA

ROI=re.compile(r"^Q[0-9]{3}_[a-f0-9]{16}(?:_RB_B)?$")
PASS="MIP1_INDEX_ONLY_SOURCE_AND_PROTECTED_PASS_TEST_ONLY"

def sha(b):return hashlib.sha256(b).hexdigest()

def stage(proof_dir,edits_dir,canary_dir,crosswalk,out):
    proof_dir,edits_dir,canary_dir,out=map(Path,
        (proof_dir,edits_dir,canary_dir,out))
    data=json.loads((proof_dir/"source_protection_evidence.json").read_text())
    edits=json.loads((edits_dir/"auto_edit_report.json").read_text())
    canary=json.loads((canary_dir/"mip4_canary_report.json").read_text())
    if (canary.get("schema")!="outrun-source-owner-bc3-4mip-canary-v1"
       or canary.get("release_approved") is not False
       or canary.get("c1_c3")!="UNTESTED"
       or canary.get("machine_canary_pass_count",0)<1
       or canary.get("source_report_sha256")!=data.get("source_report_zip_sha256")
       or canary.get("source_report_sha256")!=edits.get("source_report_zip_sha256")):
       raise ValueError("SOURCE_MIP_CANARY_APPROVAL_OR_SHA_MISMATCH")
    with open(crosswalk,newline="",encoding="utf-8-sig") as f:
        cross={r["roi_id"]:r for r in csv.DictReader(f)}
    if len(cross)!=954:raise ValueError("ORIGINAL_954_CROSSWALK_REQUIRED")
    masks={t["roi_id"]:t for t in data["tickets"]}
    pixels={r["roi_id"]:r for r in edits["records"]}
    out.mkdir(parents=True,exist_ok=True)
    staged=[]
    for rec in canary["records"]:
        if rec["status"]!=PASS:continue
        rid=rec["roi_id"]
        if not ROI.fullmatch(rid) or rid not in masks or rid not in pixels or rid not in cross:
            raise ValueError("CANARY_ROI_NOT_SOURCE_BOUND")
        t,r,row=masks[rid],pixels[rid],cross[rid]
        if not t.get("full_component_owner_proven") or rec.get("actual_mip_count")!=1:
            raise ValueError("CANARY_NATIVE_MIP_OR_OWNER_UNVERIFIED")
        if (rec["original_sha256"]!=t["source_dds_sha256"]
            or row["source_dds_sha256"]!=t["source_dds_sha256"]
            or row["source_dds_path"]!=t["source_dds_path"]
            or json.loads(row["bbox_xyxy"])!=t["bbox_xyxy"]
            or rec["native_box"]!=t["bbox_xyxy"]
            or not rec.get("test_dds_filename")):
            raise ValueError("CANARY_NATIVE_ID_OR_SOURCE_CHANGED")
        name=r.get("edited_transparent_png")
        if name!=rid+"_korean_fit_RGBA.png":
            raise ValueError("CANARY_GLYPH_INPUT_UNVERIFIED")
        blob=(edits_dir/name).read_bytes()
        if sha(blob)!=rec["edited_candidate_sha256"] or sha(blob)!=r["edited_transparent_sha256"]:
            raise ValueError("CANARY_A_B_GLYPH_SHA_CHANGED")
        actual=(canary_dir/rec["test_dds_filename"]).read_bytes()
        if sha(actual)!=rec["saved_sha256"] or actual[:4]!=b"DDS ":
            raise ValueError("CANARY_SAVED_DDS_SHA_CHANGED")
        path=out/(rid+".png")
        path.write_bytes(blob)
        receipt={
            "schema":SCHEMA,"roi_id":rid,"role":row["roles"],
            "status":PASS,"source_dds_sha256":t["source_dds_sha256"],
            "source_dds_path":t["source_dds_path"],
            "source_native_bbox_xyxy":t["bbox_xyxy"],
            "old_candidate_sha256":r["candidate_sha256"],
            "candidate_sha256":r["edited_transparent_sha256"],
            "native_test_dds_sha256":rec["saved_sha256"],
            "source_native_ownership_proof_sha256":data["source_report_zip_sha256"],
            "source_dds_native_mips":1,
            "native_canary_method":rec["mip_receipts"][0].get("owner_repair_method"),
            "visual_qa":"C1_C3_UNTESTED","release_approved":False,
            "runtime_validation":"UNTESTED",
            "real_game_test":"NOT_PERFORMED"}
        (out/(rid+".json")).write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
        staged.append(rid)
    if len(staged)!=canary["machine_canary_pass_count"]:
        raise ValueError("CANARY_PASS_COUNT_NOT_COPIED")
    print(json.dumps({"staged_test_only_source_owner_native_png":len(staged),
                      "not_game_approved":True,
                      "source_archive_sha256":data["source_report_zip_sha256"],
                      "source_bound_roi_ids":staged},sort_keys=True))
    return staged

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--proof-dir",required=True)
    p.add_argument("--edits-dir",required=True)
    p.add_argument("--canary-dir",required=True)
    p.add_argument("--crosswalk",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    stage(a.proof_dir,a.edits_dir,a.canary_dir,a.crosswalk,a.out)
