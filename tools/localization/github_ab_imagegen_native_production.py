#!/usr/bin/env python3
"""GitHub CPU only: compose original A/B ImageGen artwork into source-native DDS.

No fonts, no fresh synthetic lettering, no N100 compute, no game file writes.
Only SHA-pinned A/B PNG entries with exact native source geometry are eligible.
All outputs are TEST_ONLY pending independent visual and in-game QA.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import struct
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, ImageDraw, ImageOps

REGISTRY="localization/automation_inputs/ab_imagegen_registry.json"
CROSSWALK="localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
ORIGINAL="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
ZIPNAME="OUTRUN_AB_IMAGEGEN_NATIVE_TEST_ONLY.zip"
MASKS=(0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
MAX_SIZE=80*1024*1024

def sha(data):
    return hashlib.sha256(data).hexdigest()

def approved_target(path):
    p=PurePosixPath(path)
    return (isinstance(path,str) and path.startswith("textures/load/")
      and "\\" not in path and ":" not in path and ".." not in p.parts
      and len(p.parts) in (4,5) and p.suffix==".dds"
      and (len(p.parts)==4 or p.parts[2] in ("Keyboard","PlayStation","Switch","Xbox"))
      and all(re.fullmatch(r"[A-Za-z0-9_.-]+",x) for x in p.parts))

def native_rgba(dds):
    if len(dds)<128 or dds[:4]!=b"DDS " or struct.unpack_from("<I",dds,4)[0]!=124:
        raise ValueError("SOURCE_DDS_HEADER_INVALID")
    height,width=struct.unpack_from("<II",dds,12)
    if not 0<width<=4096 or not 0<height<=4096:raise ValueError("DDS_DIMENSIONS")
    if (struct.unpack_from("<I",dds,76)[0]!=32 or
        struct.unpack_from("<I",dds,80)[0]!=65 or
        struct.unpack_from("<I",dds,88)[0]!=32 or
        struct.unpack_from("<IIII",dds,92)!=MASKS or
        struct.unpack_from("<I",dds,28)[0]!=1 or
        dds[84:88]!=bytes(4) or len(dds)!=128+width*height*4):
        raise ValueError("SOURCE_DDS_NON_NATIVE_RGBA_MIP")
    with Image.open(io.BytesIO(dds)) as im:
        im.load()
        image=im.convert("RGBA")
    if image.tobytes("raw","BGRA")!=dds[128:]:
        raise ValueError("SOURCE_RGBA_ROUNDTRIP_MISMATCH")
    return image

def load_crosswalk(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=954:raise ValueError("ACTIVE_CROSSWALK_COUNT_CHANGED")
    if len(set(x["roi_id"] for x in rows))!=len(rows):
        raise ValueError("AMBIGUOUS_SOURCE_ROI")
    return {x["roi_id"]:x for x in rows}

def check_entry(entry,row,root):
    rid=entry["roi_id"]
    target=entry["target_path"]
    if not approved_target(target) or row["source_dds_path"]!=target:
        raise ValueError("CROSSWALK_TARGET_MISMATCH")
    if entry["original_sha256"]!=row["source_dds_sha256"]:
        raise ValueError("CROSSWALK_SOURCE_SHA_MISMATCH")
    if entry["source_hd_png_sha256"]!=row["source_hd_sha256"]:
        raise ValueError("CROSSWALK_HD_SHA_MISMATCH")
    if entry["role"] not in ("A","B") or entry["role"] not in row["roles"].split(";"):
        raise ValueError("CROSSWALK_ROLE_MISMATCH")
    if entry.get("orientation") not in ("NORMAL","FLIPY"):
        raise ValueError("ORIENTATION_NOT_REVIEWED")
    if entry.get("status")!="AB_CANDIDATE_EXACT_BYTES_IMPORTED_VISUAL_REVIEW_REQUIRED":
        raise ValueError("QA_INPUT_NOT_ADMITTED")
    candidate=entry["candidate"]
    folder="localization/automation_inputs/candidate_outputs/"+entry["role"]+"/"
    if not isinstance(candidate,str) or not candidate.startswith(folder) or "\\" in candidate or ".." in PurePosixPath(candidate).parts:
        raise ValueError("CANDIDATE_UNSAFE_PATH")
    if Path(candidate).name not in (
        rid+"_source_k.png",rid+"_k.png"):
        raise ValueError("CANDIDATE_ID_MISMATCH")
    if not re.fullmatch("[a-f0-9]{64}",entry["candidate_sha256"]):
        raise ValueError("CANDIDATE_SHA_INVALID")
    return root/candidate

def compose_one(dds,candidate,entry):
    source=native_rgba(dds)
    readable=source if entry["orientation"]=="NORMAL" else ImageOps.flip(source)
    required_box=tuple(entry["native_ink_box"])
    if len(required_box)!=4 or not all(type(v) is int for v in required_box):
        raise ValueError("NATIVE_INK_BOX_INVALID")
    if list(readable.size)!=entry["readable_source_dimensions"]:
        raise ValueError("READABLE_DIMENSIONS_CHANGED")
    x0,y0,x1,y1=required_box
    if not 0<=x0<x1<=readable.width or not 0<=y0<y1<=readable.height:
        raise ValueError("INK_BOX_OOB")
    if readable.getchannel("A").getbbox()!=required_box:
        # Explicit alpha isolated-text source only; for a complex atlas use a reviewed per-ROI mask.
        raise ValueError("SOURCE_HAS_OTHER_ART_OR_DIFFERENT_INK")
    with Image.open(io.BytesIO(candidate)) as im:
        if im.format!="PNG" or im.width>4096 or im.height>4096 or im.width<32 or im.height<16:
            raise ValueError("CANDIDATE_IMAGE_INVALID")
        glyph=im.convert("RGBA")
    raw_bounds=glyph.getchannel("A").getbbox()
    if raw_bounds is None:raise ValueError("CANDIDATE_EMPTY")
    if (raw_bounds[0]==0 or raw_bounds[1]==0 or
        raw_bounds[2]==glyph.width or raw_bounds[3]==glyph.height):
        raise ValueError("CANDIDATE_TOUCHES_BORDER")
    a=glyph.getchannel("A")
    alpha16=a.point(lambda value:255 if value>=16 else 0).getbbox()
    if alpha16 is None:raise ValueError("CANDIDATE_NO_VISIBLE_GLYPH")
    pad=4
    box=(max(0,alpha16[0]-pad),max(0,alpha16[1]-pad),
         min(glyph.width,alpha16[2]+pad),min(glyph.height,alpha16[3]+pad))
    cropped=glyph.crop(box)
    target_w=x1-x0
    target_h=y1-y0
    factor=min(target_w/cropped.width,target_h/cropped.height)
    scaled=(max(1,min(target_w,int(cropped.width*factor))),
            max(1,min(target_h,int(cropped.height*factor))))
    art=cropped.resize(scaled,Image.Resampling.LANCZOS)
    xx=x0+(target_w-scaled[0])//2
    yy=y0+(target_h-scaled[1])//2
    out=readable.copy()
    out.paste((0,0,0,0),required_box) # Only exact old text alpha footprint.
    out.alpha_composite(art,(xx,yy))
    mask=Image.new("L",source.size,0)
    ImageDraw.Draw(mask).rectangle((x0,y0,x1-1,y1-1),fill=255)
    changed=ImageChops.difference(readable,out)
    if any(ImageChops.multiply(ch,ImageOps.invert(mask)).getbbox() for ch in changed.split()):
        raise ValueError("PROTECTED_ART_CHANGED_OUTSIDE_NATIVE_SOURCE_INK")
    converted=out if entry["orientation"]=="NORMAL" else ImageOps.flip(out)
    result=dds[:128]+converted.tobytes("raw","BGRA")
    if result[:128]!=dds[:128] or len(result)!=len(dds) or result==dds:
        raise ValueError("DDS_HEADER_LENGTH_OR_CHANGE_FAILED")
    verify=native_rgba(result)
    if ImageChops.difference(verify,converted).getbbox():
        raise ValueError("DDS_REDECODE_PIXEL_MISMATCH")
    return result,out,{"candidate_size":list(glyph.size),
                       "candidate_visible_bounds":list(alpha16),
                       "native_ink_box":list(required_box),
                       "new_ink_box":[xx,yy,xx+scaled[0],yy+scaled[1]],
                       "outside_native_ink_pixel_changes":0}

def zip_write(z,path,data):
    info=zipfile.ZipInfo(path,(1980,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=0o100644<<16
    z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=4)

def produce(root,out):
    root=Path(root).resolve()
    out=Path(out).resolve()
    if out.is_relative_to(root):raise ValueError("OUTPUT_MUST_NOT_OVERWRITE_REPOSITORY")
    out.mkdir(parents=True,exist_ok=True)
    crosswalk=load_crosswalk(root/CROSSWALK)
    registry=json.loads((root/REGISTRY).read_text(encoding="utf-8"))
    if registry.get("schema")!="outrun.ab-imagegen-input-registry.v1":
        raise ValueError("MISSING_A_B_INPUT_REGISTRY")
    entries=registry["entries"]
    if not entries or len(entries)>954:raise ValueError("INVALID_REGISTRY_ENTRY_COUNT")
    ids=set();build={};reports=[];holds=[]
    for entry in sorted(entries,key=lambda x:x["roi_id"]):
        rid=entry["roi_id"]
        if rid in ids:raise ValueError("DUPLICATE_AB_INPUT")
        ids.add(rid)
        try:
            if rid not in crosswalk:raise ValueError("NOT_IN_ACTIVE_CROSSWALK")
            candidate_path=check_entry(entry,crosswalk[rid],root)
            target=entry["target_path"]
            source_path=root/ORIGINAL/target
            if not candidate_path.is_file():raise ValueError("A_B_CANDIDATE_NOT_IMPORTED")
            if candidate_path.is_symlink():raise ValueError("A_B_CANDIDATE_SYMLINK")
            if not source_path.is_file() or source_path.is_symlink():
                raise ValueError("NATIVE_SOURCE_NOT_IMPORTED")
            if source_path.stat().st_size>MAX_SIZE:raise ValueError("SOURCE_TOO_LARGE")
            candidate=candidate_path.read_bytes()
            if sha(candidate)!=entry["candidate_sha256"]:raise ValueError("AB_ART_SHA_MISMATCH")
            native=source_path.read_bytes()
            if sha(native)!=entry["original_sha256"]:raise ValueError("NATIVE_ORIGINAL_SHA_MISMATCH")
            if target in build:raise ValueError("MULTI_ROI_NATIVE_ATLAS_NEEDS_COMPOSITE_REVIEW")
            dds,preview,detail=compose_one(native,candidate,entry)
            build[target]=dds
            key=re.sub("[^A-Za-z0-9_-]","_",rid)
            preview.save(out/("PREVIEW_"+key+".png"),format="PNG")
            reports.append({"roi_id":rid,"target":target,"english":crosswalk[rid]["english"],
                            "korean":crosswalk[rid]["korean"],"candidate_sha256":sha(candidate),
                            "native_original_sha256":sha(native),"native_output_sha256":sha(dds),
                            **detail})
        except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
            holds.append({"roi_id":rid,"reason":str(exc)[:160]})
    with zipfile.ZipFile(out/ZIPNAME,"w") as z:
        for target,dds in sorted(build.items()):
            zip_write(z,target,dds)
        zip_write(z,"TEST_ONLY_MANIFEST.json",json.dumps({
            "origin":"EXACT_A_B_IMAGEGEN_PNG_ONLY","release_approved":False,
            "runtime_validation":"UNTESTED","visual_qa":"REVIEW_REQUIRED",
            "entries":[{"target":x["target"],"sha256":x["native_output_sha256"],
                        "imagegen_candidate_sha256":x["candidate_sha256"]} for x in reports],
        },ensure_ascii=False,sort_keys=True,indent=2).encode())
    with zipfile.ZipFile(out/ZIPNAME) as z:
        if z.testzip() is not None:raise ValueError("ZIP_CRC")
        for target,raw in build.items():
            if z.read(target)!=raw:raise ValueError("ZIP_CONTENT_MISMATCH")
    report={
        "schema":"outrun.github-ab-imagegen-native-qa.v1",
        "source":"A/B original ImageGen PNG (not synthetic font)",
        "original_dds_preserved":True,
        "native_generated_dds":len(build),
        "candidate_count":len(entries),
        "candidate_accepted_count":len(reports),
        "pending_visual_qa_count":len(reports),
        "holds":holds,
        "accepted":reports,
        "test_only_zip_sha256":sha((out/ZIPNAME).read_bytes()),
        "release_approved":False,"runtime_validation":"UNTESTED",
        "visual_qa":"REVIEW_REQUIRED",
    }
    (out/"qa_report.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ["candidate_count","candidate_accepted_count","native_generated_dds","holds","test_only_zip_sha256"]},ensure_ascii=False))
    if not build:raise SystemExit("NO_AB_SOURCE_NATIVE_DDS_GENERATED")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--out",default="/tmp/outrun-ab-native")
    a=ap.parse_args()
    produce(a.repo_root,a.out)
