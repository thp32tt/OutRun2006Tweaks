#!/usr/bin/env python3
"""Identify the exact, SHA-bound subset of real HD HOLDs eligible for *next* QA.

No fabricated reductions: full connected-component source ownership is necessary,
not sufficient. A/B pixel edits that stay outside original foreign alpha are
staged as C1-review evidence. DDS editing, C3 and game approval remain separate.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

RID=re.compile(r"^Q[0-9]{3}_[a-f0-9]{16}(?:_RB_B)?$")
EDITED_STATUSES={"EDITED_SOURCE_BOUND_PREVIEW_REVIEW_REQUIRED",
                 "RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD"}
MASK_SCHEMA="outrun-hd-source-protected-component-evidence-v1"
EDIT_SCHEMA="outrun-hd-existing-pixel-auto-editor-v1"
VERSION="outrun-hd-full-owner-candidate-reconciliation-v1"


def h(raw):
    return hashlib.sha256(raw).hexdigest()


def png(path,mode="RGBA"):
    path=Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("UNAVAILABLE_OR_SYMLINK_IMAGE")
    with Image.open(path) as im:
        if im.format!="PNG":
            raise ValueError("INPUT_NOT_PNG")
        im.load()
        return im.convert(mode)


def exact_mask_files(proof_dir,t):
    paths={}
    rid=t["roi_id"]
    for kind in ("source","owned","protected","ambiguous"):
        expected=f"native_masks/{rid}_{kind}.png"
        if t.get("mask_pngs",{}).get(kind)!=expected:
            raise ValueError("SOURCE_NATIVE_MASK_NOT_PINNED")
        paths[kind]=png(Path(proof_dir)/expected,"L" if kind!="source" else "RGBA")
    return paths


def verify_pixel_ownership(t,record,proof_dir,edited_dir):
    rid=t["roi_id"]
    path=record.get("edited_transparent_png")
    if path!=f"{rid}_korean_fit_RGBA.png":
        return "NO_PIXEL_EDITED_KOREAN"
    raw=(Path(edited_dir)/path).read_bytes()
    if h(raw)!=record.get("edited_transparent_sha256"):
        raise ValueError("EDITED_CANDIDATE_SHA_CONFLICT")
    images=exact_mask_files(proof_dir,t)
    source=images["source"]
    owned=images["owned"]
    protected=images["protected"]
    ambiguous=images["ambiguous"]
    text=png(Path(edited_dir)/path)
    if not all(im.size==source.size for im in (owned,protected,ambiguous,text)):
        return "NATIVE_PIXEL_DIMENSIONS_DIFFER"
    core=source.getchannel("A").point(lambda v:255 if v>15 else 0)
    if ImageChops.difference(ImageChops.lighter(owned,protected),core).getbbox():
        raise ValueError("SOURCE_CORE_NOT_PARTITIONED")
    if ImageChops.multiply(owned,protected).getbbox():
        raise ValueError("OWNED_FOREIGN_PIXEL_CONFLICT")
    if ImageChops.multiply(ambiguous,owned).getbbox():
        raise ValueError("AMBIGUOUS_OWNER_CONFLICT")
    if ambiguous.getbbox() or t["ambiguous_component_pixels"]:
        return "AMBIGUOUS_NATIVE_SOURCE_EXISTS"
    if not owned.getbbox():
        return "OWNER_MASK_EMPTY"
    # The glyph must NOT extend over another original source sprite (1px
    # alpha halo). An RGBA source-crop replacement would destroy this art.
    glyph=text.getchannel("A").point(lambda n:255 if n>15 else 0)
    if not glyph.getbbox():
        return "TRANSLATED_GLYPH_INVISIBLE"
    unsafe=protected.filter(ImageFilter.MaxFilter(3))
    if ImageChops.multiply(glyph,unsafe).getbbox():
        return "TRANSLATED_INK_TOUCHES_FOREIGN_SOURCE"
    if glyph.getbbox()[0]<2 or glyph.getbbox()[1]<2 or (
       glyph.getbbox()[2]>text.width-2 or glyph.getbbox()[3]>text.height-2):
        return "TRANSLATED_INK_TOUCHES_FRAME"
    # Removing only the source-owned layer preserves all other source pixels.
    clean=source.copy()
    clean.paste((0,0,0,0),(0,0),owned)
    delta=ImageChops.difference(source,clean)
    if any(ImageChops.multiply(ch,protected).getbbox() for ch in delta.split()):
        raise ValueError("CLEAN_DAMAGED_PROTECTED_SOURCE")
    if ImageChops.multiply(clean.getchannel("A"),owned).getbbox():
        raise ValueError("SOURCE_ENGLISH_OWNER_NOT_REMOVED")
    if int(t.get("native_bc3_four_mips_requires_separate_codec_gate",0)):
        return "BC3_MIP_NATIVE_CODEC_GATE_PENDING"
    if record.get("status") not in EDITED_STATUSES:
        return "PIXEL_EDIT_NOT_AVAILABLE_FOR_C1"
    return "READY_FOR_C1_STATIC_SOURCE_OWNER_TEST_ONLY"


def audit(proof_dir,edited_dir,out):
    proof_dir,edited_dir,out=map(Path,(proof_dir,edited_dir,out))
    out.mkdir(parents=True,exist_ok=True)
    ev=json.loads((proof_dir/"source_protection_evidence.json").read_text())
    edits=json.loads((edited_dir/"auto_edit_report.json").read_text())
    if (ev.get("schema")!=MASK_SCHEMA or edits.get("schema")!=EDIT_SCHEMA
            or ev.get("source_report_zip_sha256")!=edits.get("source_report_zip_sha256")
            or ev.get("source_total_roi")!=954 or ev.get("source_holds")!=640
            or edits.get("original_hold_count_unchanged")!=640
            or ev.get("release_approved") is not False
            or edits.get("release_approved") is not False):
        raise ValueError("MISMATCHED_PINNED_20261112_SOURCE_EVIDENCE")
    tickets={t["roi_id"]:t for t in ev["tickets"]}
    edit_records={x["roi_id"]:x for x in edits["records"]}
    if len(tickets)!=450 or len(edit_records)!=len(edits["records"]):
        raise ValueError("OVERLAP_EDIT_COVERAGE_INVALID")
    full=[t for t in tickets.values() if t.get("full_component_owner_proven") is True]
    if len(full)!=ev["full_owner_rows_diagnostic_only"]:
        raise ValueError("FULL_NATIVE_OWNER_COUNT_CONFLICT")
    counts=Counter()
    rows=[]
    for t in sorted(full,key=lambda x:x["roi_id"]):
        rid=t["roi_id"]
        if not RID.fullmatch(rid):
            raise ValueError("INVALID_NATIVE_ROI_ID")
        record=edit_records.get(rid)
        if record is None:
            result="SOURCE_OWNER_PROVEN_BUT_NO_EDITED_A_B_CANDIDATE"
        elif record.get("source_dds_sha256")!=t["source_dds_sha256"]:
            raise ValueError("SOURCE_DDS_SHA_ID_MISMATCH")
        else:
            result=verify_pixel_ownership(t,record,proof_dir,edited_dir)
        counts[result]+=1
        rows.append({
            "roi_id":rid,"source_dds_sha256":t["source_dds_sha256"],
            "source_dds_path":t["source_dds_path"],
            "native_bbox_xyxy":t["bbox_xyxy"],
            "english":t["english"],"korean":t["korean"],
            "full_native_owner_component":True,
            "source_core_owned_pixels":t["exclusive_anchored_component_pixels"],
            "original_other_art_protected_pixels":t["protected_or_unclaimed_pixels"],
            "status":result,
            "edited_candidate_sha256":(record or {}).get("edited_transparent_sha256"),
        })
    result={
        "schema":VERSION,
        "source_report_zip_sha256":ev["source_report_zip_sha256"],
        "original_holds_unchanged":640,"original_roi_total":954,
        "full_native_owner_source_rows":len(full),
        "source_owned_rows_with_pixel_edits":sum(r.get("edited_candidate_sha256") is not None for r in rows),
        "next_c1_static_candidate_count":counts["READY_FOR_C1_STATIC_SOURCE_OWNER_TEST_ONLY"],
        "gate_status_counts":dict(sorted(counts.items())),
        "items":rows,
        "original_dds_unchanged":True,
        "new_generated_pixels":False,
        "release_approved":False,
        "visual_qa":"C1_C3_PENDING",
        "runtime_validation":"UNTESTED",
        "source_clean_scope":"OWNER_ONLY_NOT_FULL_EXTERNAL_BACKGROUND_RECONSTRUCTION",
        "note":"A static C1-ready result is not a QA PASS or decrease in validated HOLD count."
    }
    (out/"hold_closure_audit.json").write_text(
      json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("items","note")},
                     ensure_ascii=False,sort_keys=True))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--proof-dir",required=True)
    p.add_argument("--edited-dir",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args()
    audit(x.proof_dir,x.edited_dir,x.out)
