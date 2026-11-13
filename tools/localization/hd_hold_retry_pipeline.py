#!/usr/bin/env python3
"""Repair failed HD A/B edits first; stage only genuinely unresolved TEXT-ONLY ImageGen.

Inputs are the exact SHA-bound GitHub artifact from the native DDS QA run,
and the existing auto-edit artifact. No fonts, paid APIs or guessed CLEAN plates.
Every result remains TEST_ONLY and must be independently checked before DDS use.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

SCHEMA = "outrun-hd-edit-then-text-only-regen-v1"
QUEUE_SCHEMA = "outrun-hd-qa-chat-workqueue-v1"
BASE = "localization/automation_runs/hd_imagegen_fallback"
RID = re.compile(r"Q[0-9]{3}_[a-f0-9]{16}(?:_RB_B)?\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
TERMINAL = frozenset(("AB_SENT", "AB_CLAIMED", "C1_READY", "C1_SENT",
 "C1_PASS_STAGED_FOR_GITHUB_TEST_ONLY", "C1_REWORK_REQUIRED", "HOLD"))
GLYPH_ERRORS = frozenset(("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED",
                          "QA_TRANSLATION_TOO_SMALL_TO_READ"))
SOURCE_ERRORS = frozenset(("AUTO_EDIT_SOURCE_OWNER_LINE_LAYOUT",))
MIN_SIDE = 4
MAX_REFERENCE = 650 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_png(path, mode="RGBA"):
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise ValueError("SOURCE_PROOF_OR_INPUT_PNG_MISSING")
    with Image.open(p) as im:
        if im.format != "PNG":
            raise ValueError("NON_PNG_PROOF")
        im.load()
        return im.convert(mode)


def assert_safe_mask(source, owned, protected, ambiguous):
    if not all(im.size == source.size for im in (owned,protected,ambiguous)):
        raise ValueError("PROOF_MASK_DIMENSIONS")
    core = source.getchannel("A").point(lambda a: 255 if a > 15 else 0)
    if ImageChops.multiply(owned,protected).getbbox():
        raise ValueError("OWNED_PROTECTED_MIXED")
    if ImageChops.subtract(ambiguous,protected).getbbox():
        raise ValueError("AMBIGUOUS_NOT_PROTECTED")
    if ImageChops.difference(ImageChops.lighter(owned,protected),core).getbbox():
        raise ValueError("NOT_EXACT_SOURCE_CORE_PARTITION")


def candidate_positions(center, lower, upper):
    if upper < lower:
        return []
    offsets=(0,-2,2,-4,4,-8,8,-12,12,-16,16,-24,24,-32,32,-48,48,-64,64)
    result=[]
    for delta in offsets:
        val=max(lower,min(upper,center+delta))
        if val not in result: result.append(val)
    return result


def safe_fit_existing(source, owned, protected, ambiguous, text, lines):
    """Pixel-only constrained fit. No source pixels can be altered by moving text."""
    assert_safe_mask(source,owned,protected,ambiguous)
    if text.size != source.size or not 1 <= len(lines) <= 3:
        raise ValueError("UNSAFE_GEOMETRY")
    foreign = protected.filter(ImageFilter.MaxFilter(3))
    output = Image.new("RGBA",source.size,(0,0,0,0))
    placed = Image.new("L",source.size,0)
    operations=[]
    for line in lines:
        b=line["translated"]
        slot=line["source"]
        if (len(b)!=4 or len(slot)!=4 or
            not 0 <= slot[0] < slot[2] <= source.width or
            not 0 <= slot[1] < slot[3] <= source.height):
            raise ValueError("INVALID_NATIVE_LINE")
        component=text.crop(tuple(b))
        bounding=component.getchannel("A").getbbox()
        if not bounding:
            return None,"LINE_EMPTY",operations
        component=component.crop(bounding)
        original_width,original_height=component.size
        found=False
        for numer in (100,95,90,85,80,75,70,65,60,55,50,45,40):
            w=max(1,original_width*numer//100)
            h=max(1,original_height*numer//100)
            if min(w,h)<MIN_SIDE or w>slot[2]-slot[0] or h>slot[3]-slot[1]:
                continue
            im=component.resize((w,h),Image.Resampling.LANCZOS)
            mask=im.getchannel("A").point(lambda a:255 if a>15 else 0)
            if mask.getbbox() is None: continue
            cx=(b[0]+b[2]-w)//2
            cy=(b[1]+b[3]-h)//2
            xs=candidate_positions(cx,slot[0],slot[2]-w)
            ys=candidate_positions(cy,slot[1],slot[3]-h)
            for y in ys:
                for x in xs:
                    obstruction=ImageChops.lighter(foreign.crop((x,y,x+w,y+h)),
                                                   placed.crop((x,y,x+w,y+h)))
                    if ImageChops.multiply(mask,obstruction).getbbox():
                        continue
                    output.alpha_composite(im,(x,y))
                    placed.paste(ImageChops.lighter(placed.crop((x,y,x+w,y+h)),mask),(x,y))
                    operations.append({"scale_pct":numer,"xy":[x,y],"size":[w,h]})
                    found=True
                    break
                if found: break
            if found: break
        if not found:
            return None,"NO_NONCOLLIDING_NATIVE_FIT",operations
    # Never change an original protected/foreign source pixel. This is still
    # ONLY partial-source CLEAN, not a completed English removal proof.
    clean=source.copy()
    clean.paste((0,0,0,0),(0,0),owned)
    composite=Image.alpha_composite(clean,output)
    delta=ImageChops.difference(source,composite)
    if any(ImageChops.multiply(ch,protected).getbbox() for ch in delta.split()):
        return None,"PROTECTED_PIXEL_DELTA",operations
    return (output,clean,composite),"REVIEW_REQUIRED_PARTIAL_OWNER",operations


def proof_paths(proof_dir,rid,ticket):
    paths=ticket.get("mask_pngs",{})
    result={}
    for kind in ("source","owned","protected","ambiguous"):
        want="native_masks/"+rid+"_"+kind+".png"
        if paths.get(kind)!=want: return None
        result[kind]=Path(proof_dir)/want
    return result


def make_task(record,ticket,source,role,source_sha):
    rid=record["roi_id"]
    reason=record["hold_reason"]
    if role not in ("A","B") or not SHA.fullmatch(source_sha):
        raise ValueError("REGEN_ROLE_OR_SHA_INVALID")
    digest=hashlib.sha256(("HD_AUTO_EDIT_GLYPH_REGEN_V1|"+rid+"|"+source_sha+
             "|"+record["candidate_sha256"]+"|"+reason).encode()).hexdigest()[:20]
    task_id="HDRW-"+role+"-"+digest
    raw=io.BytesIO()
    source.save(raw,format="PNG",optimize=True)
    payload=raw.getvalue()
    if len(payload)>MAX_REFERENCE:
        return None,None,"SOURCE_HD_REFERENCE_TOO_LARGE"
    name=task_id+"_HD_SOURCE.png"
    native=record["source_native_bbox_xyxy"]
    task={
        "task_id":task_id,"roi_id":rid,"role":role,
        "source_dds_sha256":source_sha,
        "source_dds_path":ticket["source_dds_path"],
        "source_native_bbox_xyxy":native,
        "old_candidate_sha256":record["candidate_sha256"],
        "english":ticket["english"],"korean":ticket["korean"],
        "reason":reason,
        "status":"READY_FOR_IMAGEGEN_ONLY_AFTER_DETERMINISTIC_PIXEL_EDIT_FAILED",
        "qa_authority":"NOT_C1_APPROVED_NOT_GAME_APPROVED",
        "reference":{
            "name":name,"sha256":sha(payload),
            "width":source.width,"height":source.height,
            "source_box_xyxy":native,
            "roi_within_reference_xyxy":[0,0,source.width,source.height],
            "source_native_size":ticket.get("native_size", [source.width,source.height]),
        },
        "generation_mode":"ONLY_KOREAN_TEXT_RGBA_USE_ORIGINAL_HD_STYLE_NO_BACKGROUND",
        "required":["ORIGINAL_HD_TEXT_STYLE_COLOR_STROKE_SHADOW_ANGLE",
                    "PRESERVE_SOURCE_LINE_COUNT_AND_SIZE",
                    "KOREAN_GLYPHS_ONLY_TRANSPARENT_RGBA",
                    "NO_ENGLISH_NO_ICONS_NO_BACKGROUND",
                    "SOURCE_CLEAN_IS_SEPARATE_NOT_APPROVED",
                    "C1_C3_VISUAL_AND_NATIVE_DDS_TEST_REQUIRED"],
    }
    return task,payload,None


def build(edited_dir,proof_dir,out_dir,crosswalk,state_dir,prior_queue=None,max_tasks=8):
    edited_dir,proof_dir,out_dir=map(Path,(edited_dir,proof_dir,out_dir))
    out_dir.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((edited_dir/"auto_edit_report.json").read_text(encoding="utf-8"))
    evidence=json.loads((proof_dir/"source_protection_evidence.json").read_text(encoding="utf-8"))
    if (manifest.get("schema")!="outrun-hd-existing-pixel-auto-editor-v1"
        or evidence.get("schema")!="outrun-hd-source-protected-component-evidence-v1"
        or manifest.get("source_report_zip_sha256")!=evidence.get("source_report_zip_sha256")
        or manifest.get("original_hold_count_unchanged")!=640
        or manifest.get("release_approved") is not False
        or evidence.get("release_approved") is not False
        or not 0<=max_tasks<=8):
        raise ValueError("NOT_EXACT_SOURCE_TEST_ONLY_EVIDENCE")
    import csv
    with open(crosswalk,encoding="utf-8-sig",newline="") as f:
        rows={r["roi_id"]:r for r in csv.DictReader(f)}
    if len(rows)!=954:
        raise ValueError("NOT_954_SOURCE_ROIS")
    masks={r["roi_id"]:r for r in evidence["tickets"]}
    states={}
    for path in Path(state_dir).glob("HDRW-*.json"):
        if path.stat().st_size>40000: raise ValueError("OVERSIZE_PRIOR_STATE")
        s=json.loads(path.read_text(encoding="utf-8"))
        if s.get("status") in TERMINAL:
            states[s.get("roi_id")]=s.get("status")
    q_existing=None
    if prior_queue is not None and Path(prior_queue).is_file():
        q_existing=json.loads(Path(prior_queue).read_text(encoding="utf-8"))
    open_prior=[]
    if q_existing and q_existing.get("tasks"):
        open_prior=[t["task_id"] for t in q_existing["tasks"] if
                    t["roi_id"] not in states]
    repaired=0
    failed=Counter()
    regen=[]
    role_count=Counter()
    tasks=[]
    for record in manifest["records"]:
        rid=record.get("roi_id")
        if rid not in masks or not RID.fullmatch(rid):
            raise ValueError("UNVERIFIED_EDIT_SOURCE_ROI")
        if record["status"] not in ("RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD",
                                    "EDIT_UNSAFE_HOLD"):
            continue
        t=masks[rid]
        row=rows[rid]
        if (t["source_dds_sha256"]!=row["source_dds_sha256"] or
            record["source_dds_sha256"]!=row["source_dds_sha256"] or
            t["bbox_xyxy"]!=json.loads(row["bbox_xyxy"])):
            raise ValueError("UNPINNED_SOURCE_OR_BOUNDARY")
        paths=proof_paths(proof_dir,rid,t)
        if not paths:
            failed["NO_VERIFIED_MASKS"]+=1
            continue
        imgs={k:load_png(v,"L" if k!="source" else "RGBA") for k,v in paths.items()}
        assert_safe_mask(imgs["source"],imgs["owned"],
                         imgs["protected"],imgs["ambiguous"])
        if record["status"]=="RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD":
            img_name=record["edited_transparent_png"]
            if img_name!=rid+"_korean_fit_RGBA.png":
                raise ValueError("UNTRUSTED_EDITED_PNG_NAME")
            raw=(edited_dir/img_name).read_bytes()
            if sha(raw)!=record["edited_transparent_sha256"]:
                raise ValueError("EDITED_PNG_SHA_CHANGED")
            text=load_png(edited_dir/img_name)
            lines=[{"source":a,"translated":b}
                   for a,b in zip(record["source_native_line_boxes"],
                                  record["translated_native_line_boxes"])]
            output,status,actions=safe_fit_existing(
                imgs["source"],imgs["owned"],imgs["protected"],imgs["ambiguous"],
                text,lines)
            if output:
                prefix=rid+"_AUTO_REPAIRED_"
                for name,im in zip(("text_RGBA.png","clean_ONLY_TEST.png","composite_TEST.png"),output):
                    im.save(out_dir/(prefix+name),format="PNG",optimize=True)
                repaired+=1
                continue
            failed[status]+=1
            reason="AUTO_EDIT_KOREAN_TOUCHES_PROTECTED_ART"
        else:
            reason=record.get("hold_reason","")
            failed[reason]+=1
        if reason in SOURCE_ERRORS:
            continue
        if reason not in GLYPH_ERRORS and reason!="AUTO_EDIT_KOREAN_TOUCHES_PROTECTED_ART":
            continue
        if rid in states:
            failed["PREVIOUS_CHAT_TASK_ALREADY_SENT_NO_DUPLICATE"]+=1
            continue
        if len(tasks)>=max_tasks or role_count[row["roles"]]>=4:
            continue
        candidate,ticket_blob,err=make_task(record,t,imgs["source"],
                                            row["roles"],row["source_dds_sha256"])
        if err:
            failed[err]+=1
            continue
        (out_dir/candidate["reference"]["name"]).write_bytes(ticket_blob)
        tasks.append(candidate)
        role_count[row["roles"]]+=1
    # No published overwrite when previous unclaimed tasks await the worker.
    safe_publish=not open_prior
    queue={
       "schema":QUEUE_SCHEMA,
       "policy":"HD_AUTO_EDIT_FIRST_ORIGINAL_STYLE_TEXT_ONLY_REGEN_20261113",
       "source_asset_sha256":manifest["source_report_zip_sha256"],
       "qa_report_schema":"outrun.ab-imagegen-hd-strict.v2",
       "source_roi_count":954,"hold_count":640,
       "old_painted_count_invalid_for_release":314,
       "selection_policy":"UNRESOLVED_GLYPHS_ONLY_SOURCE_STYLE_RGBA_NO_BACKGROUND",
       "new_imagegen_disabled":False,
       "release_approved":False,"runtime_validation":"UNTESTED",
       "reference_blockers":dict(failed),
       "ab_eligible_counts":dict(role_count),
       "prior_unclaimed_tasks":len(open_prior),
       "source_reference_count_verified":0,
       "tasks":tasks if safe_publish else [],
    }
    (out_dir/"queue.json").write_text(json.dumps(queue,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    summary={
        "schema":SCHEMA,
        "input_failed_edits":sum(r.get("status") in ("RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD","EDIT_UNSAFE_HOLD") for r in manifest["records"]),
        "collision_repaired_source_protected_previews":repaired,
        "regeneration_imagegen_tasks_prepared":len(queue["tasks"]),
        "remote_queue_safe_to_publish":safe_publish,
        "existing_unclaimed_tasks_not_overwritten":len(open_prior),
        "failure_reasons":dict(failed),
        "native_dds_edited":False,"release_approved":False,
        "runtime_validation":"UNTESTED","visual_qa":"C1_C3_NOT_PERFORMED",
    }
    (out_dir/"repair_summary.json").write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--edited-dir",required=True)
    p.add_argument("--source-proof-dir",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--crosswalk",required=True)
    p.add_argument("--state-dir",required=True)
    p.add_argument("--prior-queue")
    p.add_argument("--max-tasks",type=int,default=8)
    a=p.parse_args()
    build(a.edited_dir,a.source_proof_dir,a.out,a.crosswalk,
          a.state_dir,a.prior_queue,a.max_tasks)


if __name__=="__main__":
    main()
