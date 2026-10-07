#!/usr/bin/env python3
# C248 C2 fresh independent QA batch: q32/q34/q36 (+q38 exact alias evidence)
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import hashlib, io, json, os, struct, subprocess, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C248-C2-BATCH-Q032-Q034-Q036"
OUT=Path("localization/graphics/role_C")/RUN
OUT.mkdir(parents=True,exist_ok=True)

ASSETS=[
 {"index":32,"key":"DCC7B488",
  "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",
  "candidate_sha":"2bb9d21e95a99da036657da5d696982d5ee44875c91cd798dbcb7b99830757e8",
  "prior_sha":"9e0b5dcd66b1aaeb031f60090d3c8f919cc59f7c6f8860602bcbc9990eb87867",
  "source_sha":"ecd0607fd021b6aa0c78700bffa05f70546a4d37da6182edc4a35bc41ab5ee4e",
  "source_png":"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_SOURCE_READABLE.png",
  "clean_png":"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_CLEAN_PLATE.png",
  "source_bboxes":[[547,164,1065,248]],"old_bboxes":[],
  "high_risk":"USER PRE_INGAME #005 TEXT_TOO_SMALL|TOTAL_RANK_TEXT_TOO_SMALL"},
 {"index":34,"key":"B7E25BAD",
  "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",
  "candidate_sha":"a23761d1160933d968347c87ca40496b9f8e8257a102f865b2047df2a8d92763",
  "prior_sha":"590f868ac4b99addf1bf41a87de29498584b770e54649809f8398bb699aad467",
  "source_sha":"3d5539326e4c75877457f946622c561aa20557520007dfd5851f7fe9f2056023",
  "source_png":"localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_SOURCE_READABLE.png",
  "clean_png":"localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_CLEAN_PLATE.png",
  "source_bboxes":[[2021,1179,2556,1281]],"old_bboxes":[],
  "high_risk":"USER PRE_INGAME #006 TEXT_TOO_SMALL|TOTAL_RANK_TEXT_TOO_SMALL"},
 {"index":36,"key":"06AB5CEE",
  "path":"localization/graphics/hd_candidates/textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds",
  "alias_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds",
  "candidate_sha":"7503318fa51afb2578f4d4997567a54c849be1d9ded593f8b4d84453ca4f96e8",
  "prior_sha":"e3854f79be83cdd5fac7e9af91ab8f2beb9707000a7c6abbc564c2ca443fa553",
  "source_sha":"cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a",
  "source_png":"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_SOURCE_READABLE.png",
  "clean_png":None,
  "source_bboxes":[[1829,3227,2364,3329],[594,1622,1128,1724],[2266,1643,2785,1728]],
  "old_bboxes":[[1948,3240,2245,3316],[712,1635,1009,1711],[2378,1648,2672,1723]],
  "high_risk":"USER PRE_INGAME #007/#008 TOTAL_RANK_TEXT_TOO_SMALL|PLATE_RECONSTRUCTION_DIRTY|SOURCE_FOOTPRINT_HAZE"}
]

def sha(b): return hashlib.sha256(b).hexdigest()
def git_blob(path,wanted):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:continue
        if sha(b)==wanted:return b,c
    raise RuntimeError(f"historical blob not found {path} {wanted}")
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4: raise RuntimeError(("unsupported DDS",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,ImageOps.flip(raw),{"w":w,"h":h,"mips":mips or 1,"mode":mode,"header_sha":sha(b[:128])}
def rectmask(h,w,boxes):
    m=np.zeros((h,w),bool)
    for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=True
    return m
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def glyph_clean(old,boxes):
    out=old.copy(); total=0
    for x0,y0,x1,y1 in boxes:
        a=np.array(out); crop=a[y0:y1,x0:x1]
        rgb=crop[:,:,:3].astype(np.int16); al=crop[:,:,3]
        white=(al>20)&(rgb.min(axis=2)>145)
        navy=(al>20)&(rgb[:,:,0]<75)&(rgb[:,:,1]<90)&(rgb[:,:,2]<145)
        m=ndimage.binary_dilation(white|navy,iterations=2)
        if int(m.sum())<200: raise RuntimeError(("clean mask too small",int(m.sum())))
        _,inds=ndimage.distance_transform_edt(m,return_indices=True)
        fixed=crop.copy(); yy,xx=np.nonzero(m)
        fixed[yy,xx]=crop[inds[0,yy,xx],inds[1,yy,xx]]
        out.paste(Image.fromarray(fixed,"RGBA"),(x0,y0)); total+=int(m.sum())
    return out,total
def panel(im,maxw=1000,maxh=700):
    im=im.convert("RGB"); s=min(maxw/im.width,maxh/im.height,1)
    if s<1: im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)
    return im
def save_quad(src,prior,clean,current,path,title):
    ims=[panel(x) for x in [src,prior,clean,current]]
    labs=["SOURCE","PRIOR","CLEAN","CURRENT"]
    W=sum(x.width for x in ims)+18*3; H=max(x.height for x in ims)+42
    out=Image.new("RGB",(W,H),(28,28,28)); d=ImageDraw.Draw(out); x=0
    for lab,im in zip(labs,ims):
        d.text((x+4,5),lab,fill="white"); out.paste(im,(x,30)); x+=im.width+18
    d.text((4,H-3),title,fill="white",anchor="ls"); out.save(path,quality=94,subsampling=0)
def save_contacts(src,prior,clean,current,boxes,path):
    rows=[]
    for i,(x0,y0,x1,y1) in enumerate(boxes):
        pad=24; bb=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        ims=[src.crop(bb),prior.crop(bb),clean.crop(bb),current.crop(bb)]
        sc=min(1,340/max(x.height for x in ims))
        ims=[x.resize((max(1,int(x.width*sc)),max(1,int(x.height*sc))),Image.Resampling.NEAREST).convert("RGB") for x in ims]
        W=sum(x.width for x in ims)+12*3; H=max(x.height for x in ims)+25
        row=Image.new("RGB",(W,H),(35,35,35));d=ImageDraw.Draw(row);xx=0
        for lab,im in zip(["SRC","PRIOR","CLEAN","CUR"],ims):
            d.text((xx+3,3),lab,fill="white");row.paste(im,(xx,20));xx+=im.width+12
        rows.append(row)
    W=max(x.width for x in rows); H=sum(x.height for x in rows)+8*(len(rows)-1)
    out=Image.new("RGB",(W,H),(20,20,20));y=0
    for r in rows:out.paste(r,(0,y));y+=r.height+8
    out.save(path,quality=95,subsampling=0)

summary={"schema_version":1,"role":"C","run":"C248","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","assets":[]}
for a in ASSETS:
    cur_b=Path(a["path"]).read_bytes()
    if sha(cur_b)!=a["candidate_sha"]: raise RuntimeError(("candidate drift",a["index"],sha(cur_b)))
    prior_b,prior_commit=git_blob(a["path"],a["prior_sha"])
    cur_raw,cur,cm=decode(cur_b); prior_raw,prior,pm=decode(prior_b)
    if cm["w"]!=pm["w"] or cm["h"]!=pm["h"] or cm["header_sha"]!=pm["header_sha"]: raise RuntimeError(("header/dim drift",a["index"]))
    src=Image.open(a["source_png"]).convert("RGBA")
    if src.size!=cur.size: raise RuntimeError(("source png dimension",a["index"],src.size,cur.size))
    if a["clean_png"]:
        clean=Image.open(a["clean_png"]).convert("RGBA")
        clean_mode="INDEPENDENT_C_USES_PRIOR_C_APPROVED_CLEAN_PLATE"
        removed=0
    else:
        clean,removed=glyph_clean(prior,a["old_bboxes"])
        clean_mode="INDEPENDENT_C_RECONSTRUCTED_FROM_PRE_B236_GLYPH_MASK"
    if clean.size!=cur.size: raise RuntimeError(("clean dimension",a["index"]))
    ca=np.array(cur); pa=np.array(prior); cla=np.array(clean)
    allowed=rectmask(cm["h"],cm["w"],a["source_bboxes"])
    prevdiff=np.any(ca!=pa,axis=2); alphadiff=ca[:,:,3]!=pa[:,:,3]
    outside=int((prevdiff & ~allowed).sum()); alpha_out=int((alphadiff & ~allowed).sum())
    if outside or alpha_out: raise RuntimeError(("blast outside",a["index"],outside,alpha_out))
    localized=np.any(ca!=cla,axis=2) & allowed
    per=[]; loc_union=np.zeros_like(allowed)
    for sb in a["source_bboxes"]:
        x0,y0,x1,y1=sb
        local=localized & rectmask(cm["h"],cm["w"],[sb])
        lb=bbox(local)
        if lb is None: raise RuntimeError(("no localized pixels",a["index"],sb))
        sx,sy=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        status="PASS" if min(margins)>0 and lw<=sx and lh<=sy else "FAIL"
        per.append({"original_bbox":sb,"localized_bbox":lb,"source_size":[sx,sy],"localized_size":[lw,lh],
                    "margins":margins,"width_ratio":round(lw/sx,4),"height_ratio":round(lh/sy,4),
                    "containment":"PASS" if min(margins)>=0 else "FAIL","size_ceiling":"PASS" if lw<=sx and lh<=sy else "FAIL",
                    "positive_margin":"PASS" if min(margins)>0 else "FAIL"})
        if status!="PASS": raise RuntimeError(("bbox gate",a["index"],per[-1]))
        loc_union|=local
    # pair overlap cannot occur for disjoint source boxes; still assert localized pixels do not escape allowed.
    localized_outside=0
    alias_exact=None
    if a.get("alias_path"):
        alias_exact=sha(Path(a["alias_path"]).read_bytes())==a["candidate_sha"]
        if not alias_exact: raise RuntimeError("q38 alias drift")
    save_quad(src,prior,clean,cur,OUT/f"C248_Q{a['index']:03d}_{a['key']}_SOURCE_PRIOR_CLEAN_CURRENT.jpg",f"q{a['index']} readable/FLIP-Y")
    save_quad(ImageOps.flip(src),prior_raw,ImageOps.flip(clean),cur_raw,OUT/f"C248_Q{a['index']:03d}_{a['key']}_RAW.jpg",f"q{a['index']} RAW DDS")
    save_contacts(src,prior,clean,cur,a["source_bboxes"],OUT/f"C248_Q{a['index']:03d}_{a['key']}_CONTACTS.jpg")
    report={
      "schema_version":2,"role":"C","run":"C248","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
      "queue_index":a["index"],"asset_key":a["key"],"candidate_path":a["path"],
      "candidate_sha256":a["candidate_sha"],"prior_candidate_sha256":a["prior_sha"],"prior_blob_commit":prior_commit,
      "canonical_source_dds_sha256_from_producer_provenance":a["source_sha"],
      "source_readable_png":a["source_png"],"source_readable_png_sha256":sha(Path(a["source_png"]).read_bytes()),
      "clean_plate_mode":clean_mode,"independent_clean_mask_pixels_removed":removed,
      "high_risk_reason":a["high_risk"],
      "independent_machine_qa":{
        "candidate_sha_exact":True,"dimensions":[cm["w"],cm["h"]],"mips":cm["mips"],
        "header_128_exact_to_prior":cm["header_sha"]==pm["header_sha"],
        "changed_pixels_outside_exact_source_bboxes":outside,
        "alpha_changed_outside_exact_source_bboxes":alpha_out,
        "localized_pixels_outside_exact_source_bboxes":localized_outside,
        "bbox_size_positive_margin":f"{len(per)}/{len(per)} PASS","per_region":per,
        "raw_and_flip_y_evidence":"WRITTEN",
        "q38_alias_exact_bytes":alias_exact
      },
      "controller_visual_qa":"PENDING_CONTROLLER",
      "c3_strict":"PENDING_CONTROLLER",
      "decision":"PENDING_CONTROLLER_VISUAL_AND_C3",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    (OUT/f"C248_Q{a['index']:03d}_{a['key']}_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":a["candidate_sha"],"machine_qa":"PASS","q38_alias_exact_bytes":alias_exact})
(OUT/"C248_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
