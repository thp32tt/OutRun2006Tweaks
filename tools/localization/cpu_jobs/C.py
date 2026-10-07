#!/usr/bin/env python3
# C246 C2 batch fresh independent QA: q28/q30/q44.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
import hashlib,json,math,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt,binary_dilation
from PIL import Image,ImageOps,ImageDraw

repo=Path.cwd()
RUN="20261007-C246-C2-BATCH-Q028-Q030-Q044"
out=repo/"localization/graphics/role_C"/RUN; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
SRC_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
ASSETS=[
 {"q":28,"key":"A05BF610","asset":"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
  "candidate_sha":"1ced3cfa2042d7b0d0b708e3521a7043bd7528b0347ddbe38b2b7ee51a4c0d3a",
  "source_sha":"52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129",
  "source_rel":"Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
  "rows":[{"key":"total_rank","bbox":[543,1185,1068,1275]}],
  "clean_mode":"reconstruct_from_A144","a144_commit":"c268f99db3f454d1fe3b62e8d32a3f74dae30f90",
  "a144_sha":"aa0692a2918326a494c1b04837603313faac7bdd9b7f043d4b679a8e8b1493f9",
  "a144_old_box":[649,1190,961,1270],
  "producer":"A165R2","trigger":"USER_JPG_003_TOTAL_RANK_TEXT_TOO_SMALL"},
 {"q":30,"key":"8215FD25","asset":"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "candidate_sha":"fa294ef9bcd4e96db8848da3846cea7d90fd6668e1a30d6957f6e1c881f4a547",
  "source_sha":"e8125cb52c6a135dcde0dade0dcf447ea5d806b8a9b2438d7d6732be84c9b66e",
  "source_rel":"Release/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
  "rows":[{"key":"total_rank_0","bbox":[1829,1179,2364,1281]},{"key":"total_rank_1","bbox":[1682,150,2216,252]}],
  "clean_mode":"repo_png","clean":"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_CLEAN_PLATE.png",
  "producer":"A165","trigger":"USER_JPG_004_TOTAL_RANK_TEXT_TOO_SMALL"},
 {"q":44,"key":"19CEDB9","asset":"textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds",
  "candidate_sha":"8c6a390cbadae23beff263bb0eea4ca935643d591b45bac9ca474fa108e5a913",
  "source_sha":"2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e",
  "source_repo":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds",
  "rows":[
   {"key":"sector2","bbox":[8,100,190,160]},{"key":"sector1","bbox":[208,100,385,160]},
   {"key":"win","bbox":[418,110,500,151]},{"key":"lose","bbox":[528,109,635,152]},
   {"key":"result","bbox":[32,180,247,249]},{"key":"ranking","bbox":[289,180,555,259]},
   {"key":"stage","bbox":[571,179,765,259]},{"key":"rank","bbox":[788,180,964,249]},
   {"key":"you","bbox":[1759,193,1897,260]},{"key":"diff","bbox":[1853,312,1975,381]},
   {"key":"sector3","bbox":[1832,1180,2013,1240]},{"key":"rival","bbox":[498,1412,705,1486]}],
  "clean_mode":"repo_png","clean":"localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_CLEAN_PLATE.png",
  "producer":"A144","trigger":"USER_JPG_010_TEXT_SCALE_TOO_SMALL_VS_SOURCE"}
]
def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not dds")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+w*h*4: raise RuntimeError(("unsupported",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,ImageOps.flip(raw),{"width":w,"height":h,"pitch":pitch,"mips":mips or 1,"mode":mode,"masks":[hex(x) for x in masks]}
def rect(shape,b):
    m=np.zeros(shape,bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=1; return m
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def label_panel(label,im,w=720):
    z=comp(im) if im.mode!="RGB" else im.copy()
    if z.width!=w: z=z.resize((w,max(1,round(z.height*w/z.width))),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(18,18,18)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
def hstrip(xs):
    o=Image.new("RGB",(sum(x.width for x in xs),max(x.height for x in xs)),(18,18,18)); x=0
    for im in xs:o.paste(im,(x,0));x+=im.width
    return o
def vstack(xs):
    o=Image.new("RGB",(max(x.width for x in xs),sum(x.height for x in xs)),(18,18,18)); y=0
    for im in xs:o.paste(im,(0,y));y+=im.height
    return o

all_summary=[]
for a in ASSETS:
    cp=repo/"localization/graphics/hd_candidates"/a["asset"]; cb=cp.read_bytes()
    if sha(cb)!=a["candidate_sha"]: raise RuntimeError((a["key"],"candidate drift",sha(cb),a["candidate_sha"]))
    if "source_repo" in a:
        sp=repo/a["source_repo"]; sb=sp.read_bytes()
    else:
        u=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_COMMIT}/{a['source_rel']}"
        sp=Path("/tmp")/f"C246_{a['key']}_source.dds"; urllib.request.urlretrieve(u,sp); sb=sp.read_bytes()
    if sha(sb)!=a["source_sha"]: raise RuntimeError((a["key"],"source drift",sha(sb),a["source_sha"]))
    sraw,src,sm=decode(sb); craw,cur,cm=decode(cb)
    if sm!=cm or sb[:128]!=cb[:128]: raise RuntimeError((a["key"],"structure/header drift",sm,cm))

    if a["clean_mode"]=="repo_png":
        clean=Image.open(repo/a["clean"]).convert("RGBA")
        if clean.size!=src.size: raise RuntimeError((a["key"],"clean size",clean.size,src.size))
    else:
        oldb=subprocess.check_output(["git","show",a["a144_commit"]+":localization/graphics/hd_candidates/"+a["asset"]])
        if sha(oldb)!=a["a144_sha"]: raise RuntimeError((a["key"],"A144 historical drift",sha(oldb)))
        _,old,om=decode(oldb)
        if om!=sm or oldb[:128]!=sb[:128]: raise RuntimeError((a["key"],"A144 structure drift"))
        oa=np.asarray(old).copy(); x0,y0,x1,y1=a["a144_old_box"]
        crop=oa[y0:y1,x0:x1,:3].astype(np.int16)
        seed=((crop[:,:,0]<90)&(crop[:,:,1]<110)&(crop[:,:,2]<155))|((crop[:,:,0]>220)&(crop[:,:,1]>220)&(crop[:,:,2]>220))
        ml=binary_dilation(seed,iterations=2)
        pad=10; px0=x0-pad;py0=y0-pad;px1=x1+pad;py1=y1+pad
        arr=oa[py0:py1,px0:px1].copy(); m=np.zeros(arr.shape[:2],bool);m[pad:pad+y1-y0,pad:pad+x1-x0]=ml
        _,inds=distance_transform_edt(m,return_indices=True);yy,xx=np.nonzero(m);arr[yy,xx]=arr[inds[0,yy,xx],inds[1,yy,xx]]
        kn=oa.copy();kn[py0:py1,px0:px1]=arr; clean=Image.fromarray(kn.astype(np.uint8),"RGBA")

    sa,ka,ca=map(np.asarray,(src,clean,cur)); H,W=sa.shape[:2]
    allowed=np.zeros((H,W),bool); row_reports=[]; loc_masks=[]
    for row in a["rows"]:
        b=row["bbox"]; allowed|=rect((H,W),b)
        dm=np.any(ca!=ka,axis=2)&rect((H,W),b); lb=bbox(dm)
        if lb is None: raise RuntimeError((a["key"],row["key"],"no localized diff"))
        x0,y0,x1,y1=b; sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        mar=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        row_reports.append({"key":row["key"],"original_bbox":b,"localized_bbox":lb,
          "source_size":[sw,sh],"localized_size":[lw,lh],"width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
          "delta_left":mar[0],"delta_right":mar[1],"delta_top":mar[2],"delta_bottom":mar[3],
          "containment":"PASS" if min(mar)>=0 else "FAIL","size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL",
          "positive_margin":"PASS" if min(mar)>0 else "FAIL"})
        loc_masks.append(dm)
    overlap=0
    for i in range(len(loc_masks)):
        for j in range(i+1,len(loc_masks)): overlap+=int(np.count_nonzero(loc_masks[i]&loc_masks[j]))
    checks={
      "source_current_changed_outside_source_bboxes":int(np.count_nonzero(np.any(sa!=ca,axis=2)&~allowed)),
      "source_current_alpha_outside_source_bboxes":int(np.count_nonzero((sa[:,:,3]!=ca[:,:,3])&~allowed)),
      "source_clean_changed_outside_source_bboxes":int(np.count_nonzero(np.any(sa!=ka,axis=2)&~allowed)),
      "source_clean_alpha_outside_source_bboxes":int(np.count_nonzero((sa[:,:,3]!=ka[:,:,3])&~allowed)),
      "clean_current_changed_outside_source_bboxes":int(np.count_nonzero(np.any(ka!=ca,axis=2)&~allowed)),
      "clean_current_alpha_outside_source_bboxes":int(np.count_nonzero((ka[:,:,3]!=ca[:,:,3])&~allowed)),
      "localized_pair_overlap_pixels":overlap,"header_128_exact":sb[:128]==cb[:128]
    }
    rows_ok=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in row_reports)
    machine=rows_ok and checks["clean_current_changed_outside_source_bboxes"]==0 and checks["clean_current_alpha_outside_source_bboxes"]==0 and overlap==0 and checks["header_128_exact"]
    # Source-current/source-clean may legitimately include prior clean reconstruction within the declared boxes only; outside must be zero.
    machine=machine and checks["source_current_changed_outside_source_bboxes"]==0 and checks["source_current_alpha_outside_source_bboxes"]==0 and checks["source_clean_changed_outside_source_bboxes"]==0 and checks["source_clean_alpha_outside_source_bboxes"]==0
    if not machine: raise RuntimeError((a["key"],"machine FAIL",checks,row_reports))

    # Evidence contacts. q44 uses per-row contact because rows are distributed.
    if a["q"]==44:
        contacts=[]
        for rr in a["rows"]:
            x0,y0,x1,y1=rr["bbox"]; pad=20; cr=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
            contacts.append(hstrip([label_panel("SOURCE "+rr["key"],src.crop(cr),520),label_panel("CLEAN",clean.crop(cr),520),label_panel("CURRENT",cur.crop(cr),520)]))
        vstack(contacts).save(out/"C246_Q044_19CEDB9_ROW_CONTACTS.jpg","JPEG",quality=95,subsampling=0)
        # full atlas comparison
        hstrip([label_panel("SOURCE ENGLISH",src,700),label_panel("CURRENT KOREAN",cur,700)]).save(out/"C246_Q044_19CEDB9_FULL.jpg","JPEG",quality=94,subsampling=0)
    else:
        xs=[r["bbox"][0] for r in a["rows"]];ys=[r["bbox"][1] for r in a["rows"]];xe=[r["bbox"][2] for r in a["rows"]];ye=[r["bbox"][3] for r in a["rows"]]
        pad=70; focus=(max(0,min(xs)-pad),max(0,min(ys)-pad),min(W,max(xe)+pad),min(H,max(ye)+pad))
        hstrip([label_panel("SOURCE ENGLISH",src.crop(focus)),label_panel("INDEPENDENT CLEAN",clean.crop(focus)),label_panel("CURRENT KOREAN",cur.crop(focus))]).save(out/f"C246_Q{a['q']:03d}_{a['key']}_SOURCE_CLEAN_CURRENT.jpg","JPEG",quality=96,subsampling=0)
        practical=[]
        for pct in (100,75,50):
            row=[]
            for lab,im in [("SOURCE",src.crop(focus)),("CURRENT",cur.crop(focus))]:
                z=comp(im); sc=pct/100; z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
                row.append(label_panel(f"{lab} {pct}%",z,max(520,z.width)))
            practical.append(hstrip(row))
        vstack(practical).save(out/f"C246_Q{a['q']:03d}_{a['key']}_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)
    # RAW full compare for all
    hstrip([label_panel("SOURCE RAW",sraw,760),label_panel("CURRENT RAW",craw,760)]).save(out/f"C246_Q{a['q']:03d}_{a['key']}_RAW.jpg","JPEG",quality=93,subsampling=0)

    rep={"schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,
      "queue_index":a["q"],"asset":a["asset"],"asset_key":a["key"],"producer":a["producer"],"trigger":a["trigger"],
      "source_sha256":a["source_sha"],"candidate_sha256":a["candidate_sha"],"structure":sm,
      "independent_clean_mode":a["clean_mode"],"rows":row_reports,"checks":checks,"machine_status":"PASS",
      "controller_visual_qa":"PENDING_CONTROLLER","c3_required":True,"c3_strict_decision":"PENDING_CONTROLLER",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    (out/f"C246_Q{a['q']:03d}_{a['key']}_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/f"C246_Q{a['q']:03d}_{a['key']}.json").write_text(json.dumps({"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,
      "queue_index":a["q"],"asset":a["key"],"candidate_sha256":a["candidate_sha"],"machine_status":"PASS",
      "controller_visual_qa":"PENDING_CONTROLLER","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    all_summary.append({"q":a["q"],"key":a["key"],"rows":row_reports,"checks":checks})
print(json.dumps({"run":RUN,"status":"MACHINE_PASS_PENDING_CONTROLLER","assets":all_summary},ensure_ascii=False,indent=2))
