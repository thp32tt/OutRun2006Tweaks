#!/usr/bin/env python3
"""Native 4-mip BC3 SOURCE-SHA canary for 11 owner-proven preexisting A/B PNGs."""
import argparse,hashlib,io,json,urllib.request
from collections import Counter
from pathlib import Path
from PIL import Image,ImageChops,ImageOps
from hd_bc3_4mip_patch import safe_patch,read_levels,BC3Hold
from hd_hold_closure_audit import exact_mask_files,png
from hd_bc3_native_codec import bc3_header

SHA_BRANCH="korean-localization-recovery-20260928"
ROOT="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
API="https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/"+SHA_BRANCH+"/"+ROOT+"/"
SOURCE_EVIDENCE="outrun-hd-source-protected-component-evidence-v1"
EDIT_EVIDENCE="outrun-hd-existing-pixel-auto-editor-v1"

def sha(raw):return hashlib.sha256(raw).hexdigest()

def canary(proof_dir,edit_dir,out,max_output=2):
    proof_dir,edit_dir,out=map(Path,(proof_dir,edit_dir,out))
    out.mkdir(parents=True,exist_ok=True)
    evidence=json.loads((proof_dir/"source_protection_evidence.json").read_text())
    edits=json.loads((edit_dir/"auto_edit_report.json").read_text())
    if (evidence.get("schema")!=SOURCE_EVIDENCE or edits.get("schema")!=EDIT_EVIDENCE
        or evidence.get("source_report_zip_sha256")!=edits.get("source_report_zip_sha256")
        or evidence.get("source_holds")!=640 or edits.get("original_hold_count_unchanged")!=640):
        raise ValueError("NATIVE_SOURCE_REPORT_NOT_PINNED")
    edit_by_roi={r["roi_id"]:r for r in edits["records"]}
    selected=[]
    for t in evidence["tickets"]:
        rid=t["roi_id"]
        e=edit_by_roi.get(rid)
        if not (t.get("full_component_owner_proven") is True
                and t.get("native_bc3_four_mips_requires_separate_codec_gate") is True
                and e and e.get("status") in
                ("EDITED_SOURCE_BOUND_PREVIEW_REVIEW_REQUIRED",
                 "RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD")):
            continue
        name=e.get("edited_transparent_png")
        if name!=rid+"_korean_fit_RGBA.png":raise ValueError("UNPINNED_A_B_CANDIDATE")
        raw=(edit_dir/name).read_bytes()
        if sha(raw)!=e.get("edited_transparent_sha256"):
            raise ValueError("TRANSLATED_IMAGE_SHA_CHANGED")
        selected.append((t,e))
    if len(selected)!=12:
        raise ValueError("EXPECTED_12_FULL_PROVEN_BC3_SOURCE_OWNER_ROWS")
    raws={}
    results=[]
    for t,e in sorted(selected,key=lambda x:x[0]["roi_id"]):
        rid=t["roi_id"]
        if not isinstance(t["source_dds_path"],str) or ".." in t["source_dds_path"].split("/"):
            raise ValueError("INVALID_SOURCE_PATH")
        key=t["source_dds_path"]
        if key not in raws:
            url=API+key
            with urllib.request.urlopen(url,timeout=55) as stream:
                buf=stream.read(40*1024*1024+1)
            if len(buf)>40*1024*1024:raise ValueError("SOURCE_DDS_OVERSIZED")
            raws[key]=buf
        raw=raws[key]
        if sha(raw)!=t["source_dds_sha256"]:
            raise ValueError("NATIVE_DDS_SOURCE_SHA_MISMATCH")
        item={"roi_id":rid,"original_sha256":sha(raw),
              "source_dds_path":key,"native_box":t["bbox_xyxy"],
              "edited_candidate_sha256":e["edited_transparent_sha256"],
              "approval":False}
        try:
            masks=exact_mask_files(proof_dir,t)
            source=read_levels(raw)[0][3]
            if t["native_orientation"]=="FLIPY":source=ImageOps.flip(source)
            box=tuple(t["bbox_xyxy"])
            crop=source.crop(box)
            if ImageChops.difference(crop,masks["source"]).getbbox():
                raise BC3Hold("SOURCE_CROP_SHA_OWNERSHIP_NOT_SAME_DDS")
            if masks["ambiguous"].getbbox():
                raise BC3Hold("AMBIGUOUS_MASK_NOT_NATIVE_OWNER")
            owner=Image.new("L",source.size,0)
            owner.paste(masks["owned"],box[:2])
            korean=Image.new("RGBA",source.size,(0,0,0,0))
            korean.alpha_composite(png(edit_dir/e["edited_transparent_png"]),box[:2])
            if korean.getchannel("A").getbbox() is None:
                raise BC3Hold("EDITED_SOURCE_TRANSLATION_MISSING")
            data,receipts=safe_patch(
                raw,owner,korean,[box],t["native_orientation"])
            item["status"]="MIP4_INDEX_ONLY_SOURCE_AND_PROTECTED_PASS_TEST_ONLY"
            item["saved_sha256"]=sha(data)
            item["mip_receipts"]=receipts
            if max_output>0:
                p=out/(rid+"_MIP4_TEST_ONLY.dds")
                p.write_bytes(data)
                item["test_dds_filename"]=p.name
                max_output-=1
        except (BC3Hold,ValueError,OSError) as err:
            item["status"]="HOLD_"+str(err).split(":",1)[0][:100]
        results.append(item)
    counts=dict(sorted(Counter(r["status"] for r in results).items()))
    report={"schema":"outrun-source-owner-bc3-4mip-canary-v1",
            "source_report_sha256":evidence["source_report_zip_sha256"],
            "full_proven_bc3_rows":12,"source_dds_targets":len(raws),
            "source_dds_modified":False,"release_approved":False,
            "runtime_validation":"UNTESTED","c1_c3":"UNTESTED",
            "machine_canary_pass_count":counts.get(
                "MIP4_INDEX_ONLY_SOURCE_AND_PROTECTED_PASS_TEST_ONLY",0),
            "statuses":counts,"records":results}
    (out/"mip4_canary_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},sort_keys=True))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--proof-dir",required=True)
    p.add_argument("--edited-dir",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    canary(args.proof_dir,args.edited_dir,args.out)
