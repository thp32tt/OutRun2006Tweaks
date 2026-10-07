#!/usr/bin/env python3
# C247 C1 fresh independent QA batch: q43/q47/q53
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT = Path("localization/graphics/role_C/20261007-C247-C1-BATCH-Q043-Q047-Q053")
OUT.mkdir(parents=True, exist_ok=True)

ASSETS = [
    {
        "index":43, "key":"455717B2",
        "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",
        "candidate_sha":"a2b0db36e0283244037dccae5b65558a70d5b8547da245d92c840e0da3b3327c",
        "prior_sha":"c158430f8a4f3730fa3c7067b0d20db97af8fddf6c830ddeb80e2d16820368ae",
        "source_ref":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_SOURCE_READABLE.png",
        "source_ref_orientation":"readable",
        "bboxes":[[4,256,558,351],[113,352,1302,560],[6,560,2024,788],[44,788,1579,1026]],
        "localized_bboxes":[[122,261,439,346],[495,359,920,552],[493,568,1537,779],[567,796,1056,1017]],
        "high_risk_reason":"USER PRE_INGAME JPG REVIEW FAIL #009 TEXT_SCALE_TOO_SMALL_VS_SOURCE"
    },
    {
        "index":47, "key":"AD720950",
        "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds",
        "candidate_sha":"6386a41ffa4af599cc7076be0cc4ce59729026b4882c437ac397270290b7e4bf",
        "prior_sha":"6dad37489e7027b8f546c38b3729167697965fc8e33fcabff46f09aba1677955",
        "source_ref":"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_SOURCE_READABLE.png",
        "source_ref_orientation":"readable",
        "bboxes":[[3757,176,3873,222]],
        "localized_bboxes":[[3759,178,3871,220]],
        "high_risk_reason":"PRE_INGAME completeness false-negative: visible functional Shift remained English"
    },
    {
        "index":53, "key":"568D3696",
        "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds",
        "candidate_sha":"7df7e0309c621f59d29cac0b1f91d21c5a4a05262c9b916a55c3d87ac5f90e33",
        "prior_sha":"2e18e459005323b37413e404b3adf31501cc92bbc3cd2b994a1c05bbdf3cef4d",
        "source_ref":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds",
        "source_ref_orientation":"raw_mirror_y",
        "bboxes":[[1988,2061,2445,2164]],
        "localized_bboxes":[[1992,2072,2440,2156]],
        "high_risk_reason":"PRE_INGAME text-scale/hierarchy false-negative"
    },
]

def sha(b): return hashlib.sha256(b).hexdigest()

def git_blob_with_sha(path, wanted):
    commits = subprocess.check_output(["git","rev-list","HEAD","--",path], text=True).splitlines()
    for c in commits:
        try:
            b = subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:
            continue
        if sha(b) == wanted:
            return b, c
    raise RuntimeError(f"historical blob {wanted} not found for {path}")

def decode(b):
    return Image.open(io.BytesIO(b)).convert("RGBA")

def dds_meta(b):
    if b[:4] != b"DDS ":
        raise RuntimeError("not DDS")
    return {
        "height": struct.unpack_from("<I",b,12)[0],
        "width": struct.unpack_from("<I",b,16)[0],
        "mips": struct.unpack_from("<I",b,28)[0] or 1,
        "header_sha256": sha(b[:128]),
    }

def mask_union(shape, boxes):
    h,w = shape[:2]
    m=np.zeros((h,w),dtype=bool)
    for x0,y0,x1,y1 in boxes:
        m[max(0,y0):min(h,y1),max(0,x0):min(w,x1)] = True
    return m

def bbox_from_mask(m):
    ys,xs=np.where(m)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def fit_panel(im, maxw=1100, maxh=700):
    im=im.convert("RGB")
    scale=min(maxw/im.width,maxh/im.height,1.0)
    if scale<1:
        im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
    return im

def save_triptych(source, prior, current, path, title):
    panels=[fit_panel(source),fit_panel(prior),fit_panel(current)]
    W=sum(p.width for p in panels)+20*(len(panels)-1)
    H=max(p.height for p in panels)+44
    out=Image.new("RGB",(W,H),(35,35,35)); d=ImageDraw.Draw(out)
    x=0
    for label,p in zip(["SOURCE","PRIOR","CURRENT"],panels):
        d.text((x+4,6),label,fill=(255,255,255))
        out.paste(p,(x,38)); x+=p.width+20
    d.text((4,H-3),title,fill=(255,255,255),anchor="ls")
    out.save(path,quality=92,subsampling=0)

def save_contacts(source, prior, current, boxes, path):
    crops=[]
    for i,(x0,y0,x1,y1) in enumerate(boxes):
        pad=18
        bb=(max(0,x0-pad),max(0,y0-pad),min(source.width,x1+pad),min(source.height,y1+pad))
        trio=[source.crop(bb),prior.crop(bb),current.crop(bb)]
        maxh=max(x.height for x in trio)
        scale=min(1,280/maxh)
        trio=[x.resize((max(1,int(x.width*scale)),max(1,int(x.height*scale))),Image.Resampling.NEAREST).convert("RGB") for x in trio]
        W=sum(x.width for x in trio)+12*2; H=max(x.height for x in trio)+30
        row=Image.new("RGB",(W,H),(45,45,45)); d=ImageDraw.Draw(row)
        xx=0
        for lab,im in zip(["SRC","PRIOR","CUR"],trio):
            d.text((xx+3,3),lab,fill="white"); row.paste(im,(xx,24)); xx+=im.width+12
        crops.append(row)
    W=max(r.width for r in crops); H=sum(r.height for r in crops)+8*(len(crops)-1)
    out=Image.new("RGB",(W,H),(20,20,20)); y=0
    for r in crops: out.paste(r,(0,y)); y+=r.height+8
    out.save(path,quality=94,subsampling=0)

summary={"schema_version":1,"role":"C","run":"C247","temp_backlog_relief":"C1","shard":"ODD(+UNINDEXED_SPECIAL)","assets":[]}
for a in ASSETS:
    cur_b=Path(a["path"]).read_bytes()
    prior_b, prior_commit=git_blob_with_sha(a["path"],a["prior_sha"])
    actual=sha(cur_b)
    if actual != a["candidate_sha"]:
        raise RuntimeError(f'q{a["index"]} candidate drift {actual}')
    if sha(prior_b) != a["prior_sha"]:
        raise RuntimeError("prior SHA mismatch")
    cm,pm=dds_meta(cur_b),dds_meta(prior_b)
    cur_raw=decode(cur_b); prior_raw=decode(prior_b)
    if cur_raw.size != prior_raw.size:
        raise RuntimeError("dimension drift")
    ca=np.array(cur_raw); pa=np.array(prior_raw)
    diff=np.any(ca!=pa,axis=2)
    adiff=ca[:,:,3]!=pa[:,:,3]
    allowed=mask_union(ca.shape,a["bboxes"])
    outside=int((diff & ~allowed).sum())
    alpha_out=int((adiff & ~allowed).sum())
    if outside or alpha_out:
        raise RuntimeError(f'q{a["index"]} change outside source bbox: {outside}/{alpha_out}')
    changed_bbox=bbox_from_mask(diff)
    per=[]
    for sb,lb in zip(a["bboxes"],a["localized_bboxes"]):
        sx0,sy0,sx1,sy1=sb; lx0,ly0,lx1,ly1=lb
        entry={
            "source_bbox":sb,"localized_bbox":lb,
            "source_size":[sx1-sx0,sy1-sy0],"localized_size":[lx1-lx0,ly1-ly0],
            "delta_left":lx0-sx0,"delta_right":sx1-lx1,"delta_top":ly0-sy0,"delta_bottom":sy1-ly1,
        }
        entry["containment"]="PASS" if min(entry["delta_left"],entry["delta_right"],entry["delta_top"],entry["delta_bottom"])>=0 else "FAIL"
        entry["size_ceiling"]="PASS" if entry["localized_size"][0]<=entry["source_size"][0] and entry["localized_size"][1]<=entry["source_size"][1] else "FAIL"
        entry["positive_margin"]="PASS" if min(entry["delta_left"],entry["delta_right"],entry["delta_top"],entry["delta_bottom"])>0 else "FAIL"
        per.append(entry)
    if any(x["containment"]!="PASS" or x["size_ceiling"]!="PASS" or x["positive_margin"]!="PASS" for x in per):
        raise RuntimeError(f'q{a["index"]} bbox gate fail')

    # Readable orientation is FLIP-Y for current/prior raw DDS.
    cur_read=ImageOps.flip(cur_raw)
    prior_read=ImageOps.flip(prior_raw)
    sr=Image.open(a["source_ref"]).convert("RGBA")
    src_read=ImageOps.flip(sr) if a["source_ref_orientation"]=="raw_mirror_y" else sr
    if src_read.size != cur_read.size:
        raise RuntimeError(f'q{a["index"]} source/current dimension mismatch {src_read.size} {cur_read.size}')

    save_triptych(src_read,prior_read,cur_read,OUT/f'C247_Q{a["index"]:03d}_{a["key"]}_FLIPY.jpg',f'q{a["index"]} readable/FLIP-Y')
    # For source reference that is readable-only, RAW source is mirror-y of it.
    src_raw=ImageOps.flip(src_read)
    save_triptych(src_raw,prior_raw,cur_raw,OUT/f'C247_Q{a["index"]:03d}_{a["key"]}_RAW.jpg',f'q{a["index"]} RAW DDS orientation')
    save_contacts(src_read,prior_read,cur_read,a["bboxes"],OUT/f'C247_Q{a["index"]:03d}_{a["key"]}_CONTACTS.jpg')

    report={
        "schema_version":1,"role":"C","run":"C247",
        "TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
        "queue_index":a["index"],"asset_key":a["key"],"candidate_path":a["path"],
        "candidate_sha256":actual,"prior_candidate_sha256":a["prior_sha"],"prior_blob_commit":prior_commit,
        "high_risk_reason":a["high_risk_reason"],
        "independent_machine_qa":{
            "candidate_sha_exact":True,
            "dimensions":[cm["width"],cm["height"]],
            "mips":cm["mips"],
            "header_128_exact_to_prior":cm["header_sha256"]==pm["header_sha256"],
            "decoded_changed_pixels":int(diff.sum()),
            "decoded_changed_bbox":changed_bbox,
            "changed_pixels_outside_exact_source_bboxes":outside,
            "alpha_changed_outside_exact_source_bboxes":alpha_out,
            "bbox_size_positive_margin":f'{len(per)}/{len(per)} PASS',
            "per_region":per,
            "raw_and_flip_y_evidence":"WRITTEN_FOR_CONTROLLER_REVIEW",
        },
        "decision":"PENDING_CONTROLLER_VISUAL_AND_C3",
        "runtime_validation":"UNTESTED",
        "forbidden_domains_touched":[]
    }
    (OUT/f'C247_Q{a["index"]:03d}_{a["key"]}_MACHINE_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":actual,"machine_qa":"PASS","controller_visual":"PENDING","c3":"PENDING"})
(OUT/"C247_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
