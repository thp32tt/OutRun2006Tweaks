#!/usr/bin/env python3
"""Cleanplate-first TEST_ONLY rebuild, isolated from the old coverage-first ZIP.

Each atlas is restarted from the SHA-pinned ORIGINAL, never from the broad-ROI
hybrid output. Only strict source-owned lettering masks are erased. Existing
Korean artwork is fit inside measured native source ink/effect boxes (95%).
Ambiguous text/art and opaque backgrounds remain source-original and HOLD.
All 104 atlases get individual ORIGINAL/CLEAN/FINAL preview evidence, even when
no safe edit can be made. No visual, C1/C3, or game-runtime approval is implied.
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, re, zipfile
from pathlib import Path, PurePosixPath
from collections import Counter
from unittest.mock import patch
from PIL import Image, ImageChops, ImageOps
import github_ab_imagegen_atlas_batch as atlas
import hd_strict_qa as strict
from hd_cleanplate_flat_background import add_flat_repairs

SCHEMA="outrun.hd.cleanplate-repair.v1"
FAMILIES=("FA7BBB13","39229D64","455717B2","ACF61D7C","31C58963")
P0=set("B7E25BAD AA04D779 B1696633 BF3EE5C6 FF2462BB A064FDFC C4A2937B C598919A 2DA43E41 37759842 411827E C075FB49 FD90AA9 1F5FE6E9 4D38BBB0 97E863AD 9CE4E175 BA0147DA E3C455FA E596B7AC EBFC709F FF514CEB DCC7B488 E989E3B7 6AB5CEE CBF8ECBF 568D3696 33491F83 53CE39D5 841E796B F6811E94 4EDA9DE3 55B57CDE 6DC89C6E 5B65E08C 9F060EC1 EBE401C8".split())
H64=re.compile(r"[0-9a-f]{64}\Z")
BASE_FIT=strict.fit_line
BASE_CANDIDATE=strict.strict_candidate

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def priority(path):
    ident=PurePosixPath(path).stem.split("_")[0]
    return (0,FAMILIES.index(ident),path) if ident in FAMILIES else (1 if ident in P0 else 2,0,path)

def fit_line95(glyph, source_box):
    # Fit relative to source INK, never the coarse OCR/atlas rectangle.
    w,h=source_box[2]-source_box[0],source_box[3]-source_box[1]
    a=glyph.getchannel("A")
    b=a.getbbox()
    if b is None:
        raise strict.QualityHold("REPAIR_EMPTY_KOREAN")
    glyph=glyph.crop(b)
    # Integer floor (no +1 overflow), centered by strict placer in original box.
    capw,caph=math.floor(w*0.95),math.floor(h*0.95)
    if capw<3 or caph<3:
        raise strict.QualityHold("REPAIR_SOURCE_INK_TOO_SMALL")
    result=BASE_FIT(glyph,(0,0,capw,caph))
    if result.width>capw or result.height>caph:
        raise strict.QualityHold("REPAIR_95_PERCENT_OVERFLOW")
    return result

def candidate_no_panel(raw):
    img,actions=BASE_CANDIDATE(raw)
    a=img.getchannel("A")
    b=a.getbbox()
    if b is None:
        raise strict.QualityHold("REPAIR_EMPTY_KOREAN")
    core=a.crop(b).point(lambda n:255 if n>=192 else 0)
    w,h=core.size
    # A filled opaque rectangle has solid opposing edge strips and high
    # fill. Reject it rather than treating a black background as Hangul ink.
    if w>=8 and h>=8:
        borders=[core.crop(q) for q in ((0,0,w,1),(0,h-1,w,h),(0,0,1,h),(w-1,0,w,h))]
        fill=lambda im: im.histogram()[255]/(im.width*im.height)
        if fill(core)>=0.72 and all(fill(x)>=0.80 for x in borders):
            raise strict.QualityHold("REPAIR_CANDIDATE_OPAQUE_RECTANGLE")
    return img,actions+["CLEANPLATE_REPAIR_RECTANGLE_GATE"]

def readable(raw,orientation):
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        x=im.convert("RGBA")
    return ImageOps.flip(x) if orientation=="FLIPY" else x

def preview(im,path):
    # PNG only for browser attachment; full DDS and native evidence in build.
    x=im.copy()
    x.thumbnail((1600,1600),Image.Resampling.LANCZOS)
    # Neutral gray exposes black rectangles, dark glyphs, and transparency.
    base=Image.new("RGBA",x.size,(99,105,112,255))
    base.alpha_composite(x)
    base.convert("RGB").quantize(colors=192).save(path,format="PNG",compress_level=6)
    return {"name":path.name,"sha256":sha(path.read_bytes()),"size":list(x.size)}

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def load_refinements(path, groups):
    # Optional next-round GPT suggestions: coordinate PROPOSALS only. Each is
    # bound to an original source DDS and exact previous task, contained within
    # the old ROI. All existing strict owner/line/clean checks still run.
    if path is None or not path.is_file():
        return {},0
    doc=json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema")!="outrun.hd.cleanplate-feedback.v1":
        raise ValueError("REPAIR_FEEDBACK_SCHEMA")
    proposals={}
    byid={r["roi_id"]:(t,r) for t,rs in groups.items() for r in rs}
    for item in doc.get("proposals",[]):
        rid=item.get("roi_id")
        if rid not in byid or rid in proposals:continue
        target,row=byid[rid]
        b=item.get("bbox_xyxy")
        old=row["_bbox"]
        if (item.get("target")!=target or item.get("source_dds_sha256")!=row["source_dds_sha256"]
            or not isinstance(b,list) or len(b)!=4 or any(type(v) is not int for v in b)
            or not(old[0]<=b[0]<b[2]<=old[2] and old[1]<=b[1]<b[3]<=old[3])
            or b==old or min(b[2]-b[0],b[3]-b[1])<8):
            continue
        proposals[rid]=b
    return proposals,len(proposals)

def build(root,out,asset_sha,feedback=None,limit=104):
    root,out=Path(root).resolve(),Path(out).resolve()
    if out.is_relative_to(root) or not re.fullmatch("[0-9a-f]{40}",asset_sha):
        raise ValueError("REPAIR_OUTPUT_OR_ASSET_SHA")
    if not 1<=limit<=104:raise ValueError("REPAIR_LIMIT")
    groups=atlas.load_cross(root/atlas.CROSS)
    directions=atlas.load_pinned_orientations(root,groups)
    atlas.apply_user_manual_candidates(root,groups)
    atlas.apply_test_only_source_owner_overrides(root,groups)
    atlas.apply_c1_preliminary_overrides(root,groups)
    proposed,n=load_refinements(feedback,groups)
    # Refinements are only applied to the working copy, never the crosswalk.
    for rs in groups.values():
        for r in rs:
            if r["roi_id"] in proposed:
                r["_repair_gpt_original_bbox"]=r["_bbox"]
                r["_bbox"]=proposed[r["roi_id"]]
    (out/"vision").mkdir(parents=True,exist_ok=True)
    (out/"build").mkdir(parents=True,exist_ok=True)
    tasks=[]; totals=Counter(); files={}
    with zipfile.ZipFile(out/"build"/"OUTRUN_HD_CLEANPLATE_REPAIR_TEST_ONLY.zip","w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for i,target in enumerate(sorted(groups,key=priority)[:limit],1):
            rows=groups[target]; direction=directions[target]
            src=root/atlas.ORIGINAL/target
            if not src.is_file() or src.is_symlink() or src.stat().st_size>80*1024*1024:
                raise ValueError("REPAIR_SOURCE_MISSING_OR_UNSAFE:"+target)
            raw=src.read_bytes()
            digest=sha(raw)
            if {r["source_dds_sha256"] for r in rows}!={digest}:raise ValueError("REPAIR_SOURCE_SHA:"+target)
            source=readable(raw,direction)
            with patch.object(strict,"fit_line",fit_line95),patch.object(strict,"strict_candidate",candidate_no_panel):
                try:
                    dds,final,clean,painted,holds=atlas.process_strict_with_bc3_quarantine(raw,rows,root,direction)
                except (ValueError,OSError,OverflowError) as exc:
                    dds=final=clean=None
                    painted=[]
                    holds=[{"roi_id":r["roi_id"],"reason":str(exc)[:150]} for r in rows]
            if not painted:
                dds=None;final=clean=source
            # Separate explicit flat opaque-panel restoration lane; nonuniform
            # photographs/gradients and shared art remain untouched HOLDs.
            flat=add_flat_repairs(raw,source,clean,final,painted,holds,rows,root,direction,fit_line95,candidate_no_panel,atlas.native_image)
            if flat is not None:
                dds,final,clean,painted,holds=flat
            totals["flat_background_repaired"]+=sum(p.get("clean_type")=="EXACT_UNIFORM_OPAQUE_BORDER_BACKGROUND_TEST_ONLY" for p in painted)
            if len(painted)+len(holds)!=len(rows):
                raise ValueError("REPAIR_ROI_ACCOUNTING:"+target)
            byid={r["roi_id"]:r for r in rows}
            for record in painted:
                if record["original_line_count"]!=record["translated_line_count"]:
                    raise ValueError("REPAIR_LINE_COUNT")
                for s,t in zip(record["original_native_lines"],record["translated_native_lines"]):
                    if (t[2]-t[0]>math.floor((s[2]-s[0])*0.95)
                        or t[3]-t[1]>math.floor((s[3]-s[1])*0.95)):
                        raise ValueError("REPAIR_SIZE_GATE")
            output_hash=sha(dds) if dds is not None else digest
            ident="HDAT-"+sha((target+":"+digest+":"+output_hash+":"+asset_sha).encode())[:24]
            if dds is not None:
                z.writestr(target,dds);files[target]=output_hash
            images={}
            for kind,img in (("source",source),("clean",clean),("final",final)):
                images[kind]=preview(img,out/"vision"/(ident+"_"+kind+".png"))
            task={"task_id":ident,"target":target,"source_dds_sha256":digest,"candidate_dds_sha256":output_hash,
                  "native_size":list(source.size),"orientation":direction,"priority":priority(target)[0],
                  "images":images,"painted":painted,"holds":[dict(h,english=byid[h["roi_id"]]["english"],korean=byid[h["roi_id"]]["korean"],bbox_xyxy=byid[h["roi_id"]]["_bbox"]) for h in holds],
                  "roi_count":len(rows),"painted_count":len(painted),"hold_count":len(holds),
                  "source_unchanged":dds is None,"runtime_validation":"UNTESTED","release_approved":False}
            tasks.append(task)
            totals.update({"atlases":1,"roi":len(rows),"painted":len(painted),"held":len(holds),"changed_dds":int(dds is not None)})
            print(json.dumps({"atlas":i,"target":target,"painted":len(painted),"held":len(holds)},ensure_ascii=False),flush=True)
        z.writestr("TEST_ONLY_MANIFEST.json",json.dumps({"schema":SCHEMA,"entries":files,"release_approved":False,"runtime_validation":"UNTESTED","partial_patch":True},sort_keys=True))
    with zipfile.ZipFile(out/"build"/"OUTRUN_HD_CLEANPLATE_REPAIR_TEST_ONLY.zip") as z:
        if z.testzip() is not None:raise ValueError("REPAIR_ZIP_CRC")
        for name,h in files.items():
            if sha(z.read(name))!=h:raise ValueError("REPAIR_DDS_HASH")
    summary={"schema":SCHEMA,"asset_sha":asset_sha,"scope":"FULL_104" if limit==104 else "SAMPLE",
             "counts":dict(totals),"feedback_proposals_used_for_geometry_trials":n,
             "source_native_size_ceiling":0.95,"release_approved":False,"runtime_validation":"UNTESTED",
             "visual_qa":"PENDING","tasks":tasks}
    if limit==104 and (totals["atlases"]!=104 or totals["roi"]!=954):raise ValueError("REPAIR_FULL_SCOPE")
    write_json(out/"vision"/"manifest.json",summary)
    write_json(out/"build"/"qa_report.json",summary)
    print(json.dumps({k:v for k,v in summary.items() if k!="tasks"}),flush=True)
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",default=".")
    p.add_argument("--out",required=True)
    p.add_argument("--asset-sha",required=True)
    p.add_argument("--feedback",type=Path)
    p.add_argument("--limit",type=int,default=104)
    args=p.parse_args()
    build(args.repo_root,args.out,args.asset_sha,args.feedback,args.limit)
