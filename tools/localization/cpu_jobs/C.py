#!/usr/bin/env python3
# C245 C2 batch: q26/q28/q30 fresh independent C QA.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
import hashlib,json,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw

repo=Path.cwd()
RUN="20261007-C245-C2-BATCH-Q026-Q028-Q030"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
SRC_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
ASSETS=[
 {"q":26,"key":"63C91067","asset":"textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",
  "cand_sha":"2dfc6214ce2383ef01f2739baeff04890d5ff78330b192fcee0d864f6caff719",
  "src_sha":"d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab",
  "src_rel":"Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",
  "clean":"localization/graphics/role_B/20261005-B-PRODUCTION137/63C_CLEAN_PLATE.png",
  "rows":[[747,1174,1271,1275],[599,156,1124,246]],"producer":"B235",
  "history":"C244 visual fail scale/slant; B235 material rerender"},
 {"q":28,"key":"A05BF610","asset":"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
  "cand_sha":"aa0692a2918326a494c1b04837603313faac7bdd9b7f043d4b679a8e8b1493f9",
  "src_sha":"52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129",
  "src_rel":"Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
  "clean":"localization/graphics/role_C/20261005-C175-A05BF610/C175_A05_CLEAN_PLATE.png",
  "rows":[[543,1185,1068,1275]],"producer":"A144",
  "history":"USER JPG #003 TOTAL_RANK_TEXT_TOO_SMALL"},
 {"q":30,"key":"8215FD25","asset":"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "cand_sha":"e2eccea39c4241477c5c9743e23ffb69d1cfe785f5186dbd992a865a917d6edc",
  "src_sha":"e8125cb52c6a135dcde0dade0dcf447ea5d806b8a9b2438d7d6732be84c9b66e",
  "src_rel":"Release/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "clean":"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_CLEAN_PLATE.png",
  "rows":[[1829,1179,2364,1281],[1682,150,2216,252]],"producer":"A144",
  "history":"USER JPG #004 TOTAL_RANK_TEXT_TOO_SMALL"},
]
def sha(b): return hashlib.sha256(b).hexdigest()
def decode_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+w*h*4: raise RuntimeError(("unsupported DDS",w,h,mips,masks,len(b)))
    return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode),{"width":w,"height":h,"mips":mips or 1,"mode":mode}
def mask_rect(shape,b):
    m=np.zeros(shape,bool);x0,y0,x1,y1=b;m[y0:y1,x0:x1]=1;return m
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im):
    z=Image.new("RGBA",im.size,(105,105,105,255)); z.alpha_composite(im); return z.convert("RGB")
def panel(label,im,w=760):
    z=comp(im) if im.mode!="RGB" else im.copy()
    if z.width!=w: z=z.resize((w,max(1,round(z.height*w/z.width))),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20));c.paste(z,(0,28));ImageDraw.Draw(c).text((6,6),label,fill="white");return c
def hstrip(xs):
    o=Image.new("RGB",(sum(x.width for x in xs),max(x.height for x in xs)),(18,18,18));x=0
    for im in xs:o.paste(im,(x,0));x+=im.width
    return o
def vstack(xs):
    o=Image.new("RGB",(max(x.width for x in xs),sum(x.height for x in xs)),(18,18,18));y=0
    for im in xs:o.paste(im,(0,y));y+=im.height
    return o

summary=[]
for a in ASSETS:
    candp=repo/"localization/graphics/hd_candidates"/a["asset"]
    cb=candp.read_bytes()
    if sha(cb)!=a["cand_sha"]: raise RuntimeError((a["key"],"candidate drift",sha(cb),a["cand_sha"]))
    u=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_COMMIT}/{a['src_rel']}"
    sp=Path("/tmp")/f"C245_{a['key']}_source.dds"; urllib.request.urlretrieve(u,sp)
    sb=sp.read_bytes()
    if sha(sb)!=a["src_sha"]: raise RuntimeError((a["key"],"source drift",sha(sb),a["src_sha"]))
    sr,sm=decode_dds(sb); cr,cm=decode_dds(cb)
    if sm!=cm or sb[:128]!=cb[:128]: raise RuntimeError((a["key"],"structure/header drift",sm,cm))
    src=ImageOps.flip(sr); cur=ImageOps.flip(cr)
    clean=Image.open(repo/a["clean"]).convert("RGBA")
    if clean.size!=src.size: raise RuntimeError((a["key"],"clean size",clean.size,src.size))
    sa,ca,k=np.asarray(src),np.asarray(cur),np.asarray(clean)
    H,W=sa.shape[:2]; allowed=np.zeros((H,W),bool)
    row_reports=[]; localized_masks=[]
    for i,b in enumerate(a["rows"]):
        allowed|=mask_rect((H,W),b)
        x0,y0,x1,y1=b
        diff=np.any(ca!=k,axis=2)&mask_rect((H,W),b)
        lbox=bbox(diff); localized_masks.append(diff)
        if lbox is None: raise RuntimeError((a["key"],i,"no localized diff"))
        sw,sh=x1-x0,y1-y0; lw,lh=lbox[2]-lbox[0],lbox[3]-lbox[1]
        margins=[lbox[0]-x0,x1-lbox[2],lbox[1]-y0,y1-lbox[3]]
        row_reports.append({"region":i,"source_bbox":b,"localized_bbox":lbox,
          "source_size":[sw,sh],"localized_size":[lw,lh],"width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
          "margins":margins,"containment":"PASS" if min(margins)>=0 else "FAIL",
          "size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL",
          "positive_margin":"PASS" if min(margins)>0 else "FAIL"})
    src_cur=np.any(sa!=ca,axis=2); src_cur_a=sa[:,:,3]!=ca[:,:,3]
    clean_cur=np.any(k!=ca,axis=2); clean_cur_a=k[:,:,3]!=ca[:,:,3]
    clean_src=np.any(k!=sa,axis=2)
    overlap=0
    for i in range(len(localized_masks)):
        for j in range(i+1,len(localized_masks)): overlap+=int(np.count_nonzero(localized_masks[i]&localized_masks[j]))
    checks={
      "source_current_changed_outside_source_bboxes":int(np.count_nonzero(src_cur&~allowed)),
      "source_current_alpha_outside_source_bboxes":int(np.count_nonzero(src_cur_a&~allowed)),
      "clean_current_changed_outside_source_bboxes":int(np.count_nonzero(clean_cur&~allowed)),
      "clean_current_alpha_outside_source_bboxes":int(np.count_nonzero(clean_cur_a&~allowed)),
      "clean_source_changed_outside_source_bboxes":int(np.count_nonzero(clean_src&~allowed)),
      "localized_pair_overlap_pixels":overlap,
      "header_128_exact":sb[:128]==cb[:128]
    }
    machine=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in row_reports) and all(checks[k]==0 for k in [
      "source_current_changed_outside_source_bboxes","source_current_alpha_outside_source_bboxes",
      "clean_current_changed_outside_source_bboxes","clean_current_alpha_outside_source_bboxes",
      "clean_source_changed_outside_source_bboxes","localized_pair_overlap_pixels"])
    if not machine: raise RuntimeError((a["key"],"machine fail",row_reports,checks))
    xs=[b[0] for b in a["rows"]];ys=[b[1] for b in a["rows"]];xe=[b[2] for b in a["rows"]];ye=[b[3] for b in a["rows"]]
    pad=70; focus=(max(0,min(xs)-pad),max(0,min(ys)-pad),min(W,max(xe)+pad),min(H,max(ye)+pad))
    hstrip([panel("SOURCE ENGLISH",src.crop(focus)),panel("VERIFIED CLEAN",clean.crop(focus)),panel("CURRENT KOREAN",cur.crop(focus))]).save(out/f"C245_Q{a['q']:03d}_{a['key']}_SOURCE_CLEAN_CURRENT.jpg","JPEG",quality=95,subsampling=0)
    # raw evidence uses matching canvas region mirrored vertically
    raw_focus=(focus[0],H-focus[3],focus[2],H-focus[1])
    hstrip([panel("SOURCE RAW",sr.crop(raw_focus),820),panel("CURRENT RAW",cr.crop(raw_focus),820)]).save(out/f"C245_Q{a['q']:03d}_{a['key']}_RAW.jpg","JPEG",quality=95,subsampling=0)
    practical=[]
    for pct in (100,75,50):
        row=[]
        for lab,im in [("SOURCE",src.crop(focus)),("CURRENT",cur.crop(focus))]:
            z=comp(im); sc=pct/100; z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
            row.append(panel(f"{lab} {pct}%",z,max(520,z.width)))
        practical.append(hstrip(row))
    vstack(practical).save(out/f"C245_Q{a['q']:03d}_{a['key']}_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)
    rep={"schema_version":1,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,
      "queue_index":a["q"],"asset":a["asset"],"asset_key":a["key"],"producer":a["producer"],"trigger":a["history"],
      "source_sha256":a["src_sha"],"candidate_sha256":a["cand_sha"],"source_provenance":{"repo":"Sonic-TV/OR2006Sprites","commit":SRC_COMMIT,"url":u},
      "verified_clean_plate":a["clean"],"structure":sm,"rows":row_reports,"checks":checks,"machine_status":"PASS",
      "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER","c3_required":a["q"]==26,
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    (out/f"C245_Q{a['q']:03d}_{a['key']}_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/f"C245_Q{a['q']:03d}_{a['key']}.json").write_text(json.dumps({"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":a["q"],"asset":a["key"],"candidate_sha256":a["cand_sha"],"machine_status":"PASS","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary.append({"q":a["q"],"key":a["key"],"rows":row_reports,"checks":checks})
print(json.dumps({"run":RUN,"status":"MACHINE_PASS_PENDING_CONTROLLER","assets":summary},ensure_ascii=False,indent=2))
