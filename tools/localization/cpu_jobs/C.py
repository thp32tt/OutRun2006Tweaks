#!/usr/bin/env python3
# C262 C1 fresh independent QA for q205/q193/q173.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
OUT=ROOT/"localization/graphics/role_C/20261008-C262-C1-Q205-Q193-Q173"
OUT.mkdir(parents=True, exist_ok=True)
SRC_BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def sha256_path(p): return sha256_bytes(Path(p).read_bytes())
def rgba_from_bytes(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def rgba_from_path(p): return np.array(Image.open(p).convert("RGBA"))
def flip(a): return np.flipud(a).copy()
def bbox(mask):
    ys,xs=np.where(mask)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def inside(inner, outer):
    return inner is not None and inner[0]>=outer[0] and inner[1]>=outer[1] and inner[2]<=outer[2] and inner[3]<=outer[3]
def neutral(a):
    rgb=a[...,:3].astype(np.float32); al=a[...,3:4].astype(np.float32)/255.0
    out=rgb*al+128.0*(1-al)
    return np.clip(out,0,255).astype(np.uint8)
def pil_neutral(a): return Image.fromarray(neutral(a),"RGB")
def fetch_source(name, expected):
    u=f"{SRC_BASE}/{name}"
    with urllib.request.urlopen(u, timeout=60) as r: b=r.read()
    got=sha256_bytes(b)
    if got!=expected: raise RuntimeError(f"source sha mismatch {name}: {got} != {expected}")
    return b,u
def union_mask(shape, boxes):
    m=np.zeros(shape[:2],dtype=bool)
    for x0,y0,x1,y1 in boxes: m[y0:y1,x0:x1]=True
    return m
def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def make_contacts(source, clean, current, rows, path, maxw=420):
    strips=[]
    for row in rows:
        x0,y0,x1,y1=row["source_bbox"]
        pad=8
        x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(source.shape[1],x1+pad); y1=min(source.shape[0],y1+pad)
        crops=[pil_neutral(a[y0:y1,x0:x1]) for a in (source,clean,current)]
        h=max(im.height for im in crops)
        scale=min(1.0,maxw/max(im.width for im in crops))
        if scale<1:
            crops=[im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS) for im in crops]
            h=max(im.height for im in crops)
        label=f'q{row.get("queue_index","")} {row.get("key",row.get("source",""))}'
        cw=max(im.width for im in crops)
        strip=Image.new("RGB",(cw*3+16,h+26),(128,128,128))
        d=ImageDraw.Draw(strip); d.text((2,2),label,fill=(255,255,255))
        for i,im in enumerate(crops): strip.paste(im,(i*cw,24))
        strips.append(strip)
    W=max(im.width for im in strips); H=sum(im.height for im in strips)
    out=Image.new("RGB",(W,H),(96,96,96)); y=0
    for im in strips: out.paste(im,(0,y)); y+=im.height
    out.save(path,quality=94,subsampling=0)
def make_raw_flipy(source_raw,current_raw,path):
    panels=[]
    for title,a in [("SOURCE RAW",source_raw),("CURRENT RAW",current_raw),("SOURCE FLIP-Y",flip(source_raw)),("CURRENT FLIP-Y",flip(current_raw))]:
        im=pil_neutral(a)
        scale=min(1.0,1000/im.width)
        if scale<1: im=im.resize((int(im.width*scale),int(im.height*scale)),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(im.width,im.height+24),(96,96,96)); ImageDraw.Draw(canvas).text((4,4),title,fill=(255,255,255)); canvas.paste(im,(0,24)); panels.append(canvas)
    W=max(x.width for x in panels); H=sum(x.height for x in panels)
    out=Image.new("RGB",(W,H),(96,96,96)); y=0
    for im in panels: out.paste(im,(0,y)); y+=im.height
    out.save(path,quality=92,subsampling=0)

def evaluate(cfg):
    cand_path=ROOT/cfg["candidate_path"]
    cand_bytes=cand_path.read_bytes(); cand_sha=sha256_bytes(cand_bytes)
    src_bytes,src_url=fetch_source(cfg["source_file"],cfg["source_sha"])
    raw_src=rgba_from_bytes(src_bytes); raw_cur=rgba_from_bytes(cand_bytes)
    cur=flip(raw_cur); src=flip(raw_src)
    clean=rgba_from_path(ROOT/cfg["clean_path"])
    if clean.shape!=cur.shape or src.shape!=cur.shape:
        raise RuntimeError(f'{cfg["id"]} dimension mismatch source={src.shape} clean={clean.shape} current={cur.shape}')
    header_equal=(src_bytes[:128]==cand_bytes[:128])
    rows=cfg["rows"]
    row_results=[]; localized_masks=[]
    for r in rows:
        sb=list(map(int,r["source_bbox"])); x0,y0,x1,y1=sb
        diff=np.any(cur[y0:y1,x0:x1]!=clean[y0:y1,x0:x1],axis=2)
        db=bbox(diff)
        if db is not None: db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
        expected=r.get("localized_bbox")
        source_w=x1-x0; source_h=y1-y0
        loc_w=(db[2]-db[0]) if db else 0; loc_h=(db[3]-db[1]) if db else 0
        rr={
            "key":r.get("key"),"source":r.get("source"),"korean":r.get("korean") or r.get("text"),
            "source_bbox":sb,"derived_localized_bbox":db,"producer_localized_bbox":expected,
            "derived_bbox_matches_producer": (expected is None or db==list(map(int,expected))),
            "containment": inside(db,sb),"size_ceiling": bool(db and loc_w<=source_w and loc_h<=source_h),
            "positive_margins": bool(db and db[0]>x0 and db[1]>y0 and db[2]<x1 and db[3]<y1),
            "margins": [db[0]-x0,x1-db[2],db[1]-y0,y1-db[3]] if db else None
        }
        rr["result"]="PASS" if rr["containment"] and rr["size_ceiling"] and rr["derived_bbox_matches_producer"] else "FAIL"
        row_results.append(rr)
        full=np.zeros(cur.shape[:2],dtype=bool); full[y0:y1,x0:x1]=diff; localized_masks.append(full)
    diff_all=np.any(cur!=clean,axis=2)
    if cfg.get("allowed_mask"):
        am=np.array(Image.open(ROOT/cfg["allowed_mask"]).convert("L"))>0
        if am.shape!=diff_all.shape: raise RuntimeError("allowed mask shape mismatch")
        outside=int(np.count_nonzero(diff_all & ~am))
    else:
        allow=union_mask(cur.shape,[r["source_bbox"] for r in rows])
        outside=int(np.count_nonzero(diff_all & ~allow))
    protected_changed=0
    if cfg.get("protected_mask"):
        pm=np.array(Image.open(ROOT/cfg["protected_mask"]).convert("L"))>0
        protected_changed=int(np.count_nonzero(np.any(cur!=src,axis=2)&pm))
    token_checks=[]
    for t in cfg.get("protected_tokens",[]):
        x0,y0,x1,y1=t["bbox"]
        changed=int(np.count_nonzero(np.any(cur[y0:y1,x0:x1]!=src[y0:y1,x0:x1],axis=2)))
        token_checks.append({"name":t["name"],"bbox":t["bbox"],"changed_pixels":changed,"result":"PASS" if changed==0 else "FAIL"})
    pair=[]
    for i in range(len(localized_masks)):
        for j in range(i+1,len(localized_masks)):
            ov=int(np.count_nonzero(localized_masks[i]&localized_masks[j]))
            if ov: pair.append({"a":rows[i].get("key"),"b":rows[j].get("key"),"pixels":ov})
    # Diagnostic only: exact source pixels that survived in a source-vs-clean changed footprint.
    residue=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]
        sm=np.any(src[y0:y1,x0:x1]!=clean[y0:y1,x0:x1],axis=2)
        eq=np.all(cur[y0:y1,x0:x1]==src[y0:y1,x0:x1],axis=2)
        n=int(np.count_nonzero(sm&eq)); den=int(np.count_nonzero(sm))
        residue.append({"key":r.get("key"),"source_footprint_pixels":den,"exact_source_pixels_retained":n,"ratio":(n/den if den else 0.0)})
    overall=(cand_sha==cfg["candidate_sha"] and header_equal and outside==0 and protected_changed==0 and all(x["result"]=="PASS" for x in row_results) and all(x["result"]=="PASS" for x in token_checks) and not pair)
    report={
      "schema_version":1,"run":"C262","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
      "queue_index":cfg["index"],"asset":cfg["source_file"],"candidate_sha256":cand_sha,"expected_candidate_sha256":cfg["candidate_sha"],
      "candidate_sha_match":cand_sha==cfg["candidate_sha"],"source_sha256":cfg["source_sha"],"source_url":src_url,
      "dimensions":[int(cur.shape[1]),int(cur.shape[0])],"header_128_exact":header_equal,"raw_orientation":"mirror_y",
      "rows":row_results,"changed_pixels_outside_allowed":outside,"protected_mask_changed_pixels":protected_changed,
      "protected_tokens":token_checks,"localized_overlap_pairs":pair,"source_residue_diagnostic":residue,
      "machine_result":"PASS" if overall else "FAIL","runtime_validation":"UNTESTED"
    }
    Path(OUT/f'C262_Q{cfg["index"]:03d}_MACHINE_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    make_contacts(src,clean,cur,[dict(r,queue_index=cfg["index"]) for r in rows],OUT/f'C262_Q{cfg["index"]:03d}_CONTACTS.jpg')
    make_raw_flipy(raw_src,raw_cur,OUT/f'C262_Q{cfg["index"]:03d}_RAW_FLIPY.jpg')
    return report

b240=load_json("localization/graphics/role_B/20261008-B240-Q205-NATIVE-HD/B240_Q205_REPORT.json")
a76=load_json("localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF61D7C_REPORT.json")
latest205={r["key"]:dict(r) for r in a76["rows"]}
for r in b240["rows"]: latest205[r["key"]]=dict(r)
rows205=list(latest205.values())
a171=load_json("localization/graphics/role_A/20261008-A171-Q121-Q193-CLEAN-PLATE/A171_Q193_97E863AD_REPORT.json")
a90=load_json("localization/graphics/role_A/20261006-A-INGAME90-IGR013-BRACKET-STAGE/A90_IGR013_6DC89C6E_REPORT.json")
rows173=[]
for r in a90["native_rework"]["rows"]:
    rows173.append({"key":f'region_{r["region_idx"]:02d}',"source":r["source"],"korean":r["korean"],"source_bbox":r["original_bbox"],"localized_bbox":r["localized_bbox"]})
configs=[
 {"id":"q205","index":205,"candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds",
  "candidate_sha":"e3d421a165bdb6e7b3e1bda7b35a6d994d69017407e345d7a339a15d87f79088","source_file":"ACF61D7C_1024x512.dds","source_sha":"58a75fe75b5672169dcc2ed1f9993d462d80b700d4e12dad453b70f2ab701a5f",
  "clean_path":"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_CLEAN_PLATE.png","allowed_mask":"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_ALLOWED_BBOX_MASK.png",
  "protected_mask":"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF_PROTECTED_VISIBLE_MASK.png",
  "protected_tokens":[{"name":"OutRun","bbox":[1959,1066,2184,1121]},{"name":"OutRun2SP","bbox":[2356,909,2696,964]}],"rows":rows205},
 {"id":"q193","index":193,"candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
  "candidate_sha":"e21851f5d35ca41bdab1cbfa45db4c1266bc6d0ba03b8bc5791ff785bf313166","source_file":"97E863AD_512x256.dds","source_sha":"d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451",
  "clean_path":"localization/graphics/role_A/20261008-A171-Q121-Q193-CLEAN-PLATE/A171_Q193_97E863AD_CLEAN.png","rows":a171["rows"]},
 {"id":"q173","index":173,"candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/6DC89C6E_512x512.dds",
  "candidate_sha":"8783e565f205e03a805a9d2d9a78bd8f20a3896da52afe1a4c11d2d38be61830","source_file":"6DC89C6E_512x512.dds","source_sha":"2c08a6fc224d2263f8c7d4e97d1bd8cfe2fad060688ef5665f78791449510cb3",
  "clean_path":"localization/graphics/role_A/20261006-A-INGAME90-IGR013-BRACKET-STAGE/A90_6DC_CLEAN_PLATE.png","rows":rows173}
]
reports=[evaluate(c) for c in configs]
summary={"schema_version":1,"run":"C262","role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
         "execution_backend":"github_actions_cpu_worker","assets":[{"queue_index":r["queue_index"],"candidate_sha256":r["candidate_sha256"],"machine_result":r["machine_result"]} for r in reports],
         "controller_visual_qa":"PENDING","c3_strict":"PENDING","runtime_validation":"UNTESTED"}
(OUT/"C262_BATCH_COMPUTE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=ROOT/"localization/graphics/worker_results/C262_C1_Q205_Q193_Q173.json"
wr.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
