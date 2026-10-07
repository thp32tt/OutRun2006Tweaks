#!/usr/bin/env python3
# C263 C2 fresh independent QA + strict visual evidence for q104/q112/q116.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import hashlib, io, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
OUT=ROOT/"localization/graphics/role_C/20261008-C263-C2-Q104-Q112-Q116"
OUT.mkdir(parents=True, exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def rgba_bytes(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def rgba_path(p): return np.array(Image.open(p).convert("RGBA"))
def flip(a): return np.flipud(a).copy()
def bbox(m):
    ys,xs=np.where(m)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def inside(a,b): return a and a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]
def neutral(a):
    rgb=a[...,:3].astype(np.float32); al=a[...,3:4].astype(np.float32)/255.0
    return np.clip(rgb*al+128*(1-al),0,255).astype(np.uint8)
def pil(a): return Image.fromarray(neutral(a),"RGB")
def source_bytes(cfg):
    if cfg.get("source_path"):
        b=(ROOT/cfg["source_path"]).read_bytes(); origin=cfg["source_path"]
    else:
        with urllib.request.urlopen(cfg["source_url"],timeout=60) as r: b=r.read()
        origin=cfg["source_url"]
    if sha(b)!=cfg["source_sha"]: raise RuntimeError(f'{cfg["id"]} source sha mismatch')
    return b,origin
def union(shape, boxes):
    m=np.zeros(shape[:2],bool)
    for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=True
    return m
def save_contacts(src,clean,cur,rows,path):
    strips=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; pad=12
        x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(src.shape[1],x1+pad);y1=min(src.shape[0],y1+pad)
        ims=[pil(a[y0:y1,x0:x1]) for a in (src,clean,cur)]
        s=min(1.0,520/max(i.width for i in ims))
        if s<1: ims=[i.resize((max(1,int(i.width*s)),max(1,int(i.height*s))),Image.Resampling.LANCZOS) for i in ims]
        w=max(i.width for i in ims);h=max(i.height for i in ims)
        c=Image.new("RGB",(w*3,h+30),(96,96,96));d=ImageDraw.Draw(c)
        d.text((4,4),f'SOURCE | CLEAN | CURRENT  {r["source"]} -> {r["korean"]}',fill=(255,255,255))
        for j,i in enumerate(ims):c.paste(i,(j*w,28))
        strips.append(c)
    W=max(i.width for i in strips);H=sum(i.height for i in strips)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for i in strips:out.paste(i,(0,y));y+=i.height
    out.save(path,quality=95,subsampling=0)
def save_raw(srcraw,curraw,path):
    items=[]
    for title,a in [("SOURCE RAW",srcraw),("CURRENT RAW",curraw),("SOURCE FLIP-Y",flip(srcraw)),("CURRENT FLIP-Y",flip(curraw))]:
        im=pil(a); s=min(1.0,1100/im.width)
        if s<1:im=im.resize((int(im.width*s),int(im.height*s)),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(im.width,im.height+26),(96,96,96));ImageDraw.Draw(c).text((4,4),title,fill=(255,255,255));c.paste(im,(0,24));items.append(c)
    W=max(i.width for i in items);H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for i in items:out.paste(i,(0,y));y+=i.height
    out.save(path,quality=93,subsampling=0)
def save_practical(src,cur,path):
    items=[]
    for scale in (1.0,.75,.5):
        a=pil(src);b=pil(cur)
        if scale!=1:
            a=a.resize((int(a.width*scale),int(a.height*scale)),Image.Resampling.LANCZOS)
            b=b.resize((int(b.width*scale),int(b.height*scale)),Image.Resampling.LANCZOS)
        w=max(a.width,b.width); c=Image.new("RGB",(w*2,a.height+28),(96,96,96))
        ImageDraw.Draw(c).text((4,4),f'SOURCE | CURRENT  scale={scale}',fill=(255,255,255));c.paste(a,(0,26));c.paste(b,(w,26));items.append(c)
    W=max(i.width for i in items);H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for i in items:out.paste(i,(0,y));y+=i.height
    out.save(path,quality=92,subsampling=0)

def evaluate(cfg):
    cb=(ROOT/cfg["candidate_path"]).read_bytes(); sb,origin=source_bytes(cfg)
    csha=sha(cb); srcraw=rgba_bytes(sb);curraw=rgba_bytes(cb);src=flip(srcraw);cur=flip(curraw);clean=rgba_path(ROOT/cfg["clean_path"])
    if src.shape!=cur.shape or clean.shape!=cur.shape: raise RuntimeError(f'{cfg["id"]} shape mismatch')
    allow=union(cur.shape,[r["source_bbox"] for r in cfg["rows"]])
    changed=np.any(cur!=clean,axis=2); alpha=(cur[...,3]!=clean[...,3])
    rows=[]
    for r in cfg["rows"]:
        x0,y0,x1,y1=r["source_bbox"]; d=changed[y0:y1,x0:x1]; bb=bbox(d)
        if bb: bb=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
        expected=r["localized_bbox"]
        row={
          "key":r["key"],"source":r["source"],"korean":r["korean"],"original_bbox":r["source_bbox"],
          "localized_bbox":bb,"producer_localized_bbox":expected,
          "derived_bbox_matches_producer":bb==expected,
          "delta_left":bb[0]-x0 if bb else None,"delta_right":x1-bb[2] if bb else None,
          "delta_top":bb[1]-y0 if bb else None,"delta_bottom":y1-bb[3] if bb else None,
          "containment":"PASS" if inside(bb,r["source_bbox"]) else "FAIL",
          "size_ceiling":"PASS" if bb and bb[2]-bb[0]<=x1-x0 and bb[3]-bb[1]<=y1-y0 else "FAIL",
          "positive_margin":"PASS" if bb and bb[0]>x0 and bb[1]>y0 and bb[2]<x1 and bb[3]<y1 else "FAIL"
        }
        rows.append(row)
    outside=int(np.count_nonzero(changed&~allow)); alpha_out=int(np.count_nonzero(alpha&~allow))
    pass_rows=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["derived_bbox_matches_producer"] for r in rows)
    machine=(csha==cfg["candidate_sha"] and sha(sb)==cfg["source_sha"] and sb[:128]==cb[:128] and outside==0 and alpha_out==0 and pass_rows)
    rep={
      "schema_version":1,"run":"C263","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
      "queue_index":cfg["index"],"asset":cfg["id"],"candidate_sha256":csha,"expected_candidate_sha256":cfg["candidate_sha"],
      "candidate_sha_match":csha==cfg["candidate_sha"],"source_sha256":sha(sb),"source_origin":origin,
      "dimensions":[int(cur.shape[1]),int(cur.shape[0])],"header_128_exact":sb[:128]==cb[:128],"raw_orientation":"mirror_y",
      "rows":rows,"changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
      "machine_result":"PASS" if machine else "FAIL","runtime_validation":"UNTESTED"
    }
    (OUT/f'C263_Q{cfg["index"]:03d}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    save_contacts(src,clean,cur,cfg["rows"],OUT/f'C263_Q{cfg["index"]:03d}_CONTACTS.jpg')
    save_raw(srcraw,curraw,OUT/f'C263_Q{cfg["index"]:03d}_RAW_FLIPY.jpg')
    save_practical(src,cur,OUT/f'C263_Q{cfg["index"]:03d}_PRACTICAL.jpg')
    return rep

configs=[
 {"id":"62BEBF33","index":104,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "candidate_sha":"c84a2703d0a22b36384e07ce72d4e761e651a1a23219cd78153b4a0aff022505",
  "source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
  "source_sha":"f0a8491585dd4f225c4707b63bd61ae43869cb9d243d9de881258add023c06e2",
  "clean_path":"localization/graphics/role_C/20261004-1720-C91/C91_62BEBF33_CLEAN_PLATE.png",
  "rows":[{"key":"outrun_mode","source":"OutRun Mode","korean":"아웃런 모드","source_bbox":[392,52,1357,201],"localized_bbox":[574,56,1174,197]}]},
 {"id":"D41D0B1","index":112,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds",
  "candidate_sha":"7714bd71b38bd38852ce6497695d872d7ba6b669fd2c6efdb43ba87dd1f3734d",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds",
  "source_sha":"524de4c0db3dbb69c6cda484ace71a9213a378e3e4895a035199ced0ac0a3617",
  "clean_path":"localization/graphics/role_B/20261007-B-MANUALQA223-D41D0B1/D41D0B1_CLEAN_PLATE.png",
  "rows":[
   {"key":"line1","source":"Try to reach the goal","korean":"여자친구와 함께","source_bbox":[435,19,1346,122],"localized_bbox":[526,22,1255,118]},
   {"key":"line2","source":"with your girlfriend.","korean":"골에 도착하세요.","source_bbox":[499,122,1357,238],"localized_bbox":[585,132,1270,228]}
  ]},
 {"id":"E3FD08BE","index":116,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "candidate_sha":"7e42aaa0f8aec535008bb816ec3660e075ce87c56a4ae44170c3340d1a32a6dc",
  "source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/E3FD08BE_512x64.dds",
  "source_sha":"ebc2d866597955c6e802de65eff2d07e048f66b4ae2770fffd86b81b61fd5845",
  "clean_path":"localization/graphics/role_C/20261004-1720-C91/C91_E3FD08BE_CLEAN_PLATE.png",
  "rows":[{"key":"heart_attack_mode","source":"Heart Attack Mode","korean":"하트 어택 모드","source_bbox":[393,54,1628,200],"localized_bbox":[647,57,1374,197]}]}
]
reports=[evaluate(c) for c in configs]
summary={"schema_version":1,"run":"C263","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
"execution_backend":"github_actions_cpu_worker_after_chatgpt_local_dns_block",
"assets":[{"queue_index":r["queue_index"],"asset":r["asset"],"candidate_sha256":r["candidate_sha256"],"machine_result":r["machine_result"]} for r in reports],
"controller_visual_qa":"PENDING","c3_strict":"PENDING","runtime_validation":"UNTESTED"}
(OUT/"C263_BATCH_COMPUTE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(ROOT/"localization/graphics/worker_results/C263_C2_Q104_Q112_Q116.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
