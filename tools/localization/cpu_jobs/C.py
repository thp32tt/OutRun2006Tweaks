#!/usr/bin/env python3
# C251 C2 fresh independent QA batch: q60/q54/q212
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import hashlib, io, json, os, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT=Path("localization/graphics/role_C/20261007-C251-C2-BATCH-Q060-Q054-Q212")
OUT.mkdir(parents=True,exist_ok=True)

def H(b): return hashlib.sha256(b).hexdigest()
def load_bytes(path): return Path(path).read_bytes()
def find_blob(path,want):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError: continue
        if H(b)==want: return b,c
    raise RuntimeError(f"historical blob not found {path} {want}")

def decode(b):
    with Image.open(io.BytesIO(b)) as im:
        return im.convert("RGBA")
def readable(b): return ImageOps.flip(decode(b))
def mask_boxes(shape,boxes):
    h,w=shape; m=np.zeros((h,w),bool)
    for x0,y0,x1,y1 in boxes: m[y0:y1,x0:x1]=True
    return m
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def rect_intersects(a,b,allow_touch=False):
    if allow_touch:
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
def geometry(rows):
    out=[]
    for r in rows:
        sb=r["original_bbox"] if "original_bbox" in r else r["source_effect_bbox"]
        lb=r["localized_bbox"]
        sx,sy=sb[2]-sb[0],sb[3]-sb[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        margins=[lb[0]-sb[0],sb[2]-lb[2],lb[1]-sb[1],sb[3]-lb[3]]
        ok=lw<=sx and lh<=sy and min(margins)>0
        if not ok: raise RuntimeError(("geometry gate",r.get("key"),sb,lb,margins))
        out.append({"key":r.get("key"),"source_bbox":sb,"localized_bbox":lb,
                    "source_size":[sx,sy],"localized_size":[lw,lh],"margins":margins,
                    "width_ratio":round(lw/sx,4),"height_ratio":round(lh/sy,4)})
    for i in range(len(out)):
        for j in range(i+1,len(out)):
            if rect_intersects(out[i]["localized_bbox"],out[j]["localized_bbox"]):
                raise RuntimeError(("localized bbox overlap",out[i]["key"],out[j]["key"]))
    return out

def flat(im,bg=(96,96,96)):
    base=Image.new("RGBA",im.size,bg+(255,))
    return Image.alpha_composite(base,im).convert("RGB")
def fit(im,mw=1000,mh=900):
    s=min(mw/im.width,mh/im.height,1.0)
    return im if s>=1 else im.resize((max(1,round(im.width*s)),max(1,round(im.height*s))),Image.Resampling.LANCZOS)
def overview(src,prior,cur,path,raw=False):
    ims=[fit(flat(x)) for x in (src,prior,cur)]
    W=sum(i.width for i in ims)+32; H=max(i.height for i in ims)+46
    o=Image.new("RGB",(W,H),(22,22,22)); d=ImageDraw.Draw(o); x=0
    labs=["SOURCE RAW" if raw else "SOURCE FLIP-Y","PRIOR RAW" if raw else "PRIOR FLIP-Y","CURRENT RAW" if raw else "CURRENT FLIP-Y"]
    for lab,im in zip(labs,ims):
        d.text((x+3,3),lab,fill="white"); o.paste(im,(x,24)); x+=im.width+16
    o.save(path,"JPEG",quality=92,subsampling=0,optimize=True)
def contacts(src,prior,cur,geo,path):
    cards=[]
    for r in geo:
        x0,y0,x1,y1=r["source_bbox"]; p=24
        bb=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
        ims=[fit(flat(x.crop(bb)),620,260) for x in (src,prior,cur)]
        W=sum(i.width for i in ims)+24; H=max(i.height for i in ims)+44
        c=Image.new("RGB",(W,H),(26,26,26)); d=ImageDraw.Draw(c); xx=0
        for lab,im in zip(["SRC","PRIOR","CUR"],ims):
            d.text((xx+3,3),lab,fill="white"); c.paste(im,(xx,22)); xx+=im.width+12
        d.text((4,H-4),r["key"],fill="white",anchor="ls"); cards.append(c)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+6*(len(cards)-1)
    o=Image.new("RGB",(W,H),(18,18,18)); y=0
    for c in cards:o.paste(c,(0,y)); y+=c.height+6
    o.save(path,"JPEG",quality=94,subsampling=0,optimize=True)

def verify_lineage(idx,key,path,current_sha,prior_sha,source_sha,source_path,rows,reason):
    cb=load_bytes(path)
    if H(cb)!=current_sha: raise RuntimeError((idx,"candidate drift",H(cb),current_sha))
    pb,pcommit=find_blob(path,prior_sha)
    if source_path:
        sb=load_bytes(source_path)
        if H(sb)!=source_sha: raise RuntimeError((idx,"source drift",H(sb),source_sha))
        scommit="tracked_hd_source"
    else:
        sb,scommit=find_blob(path,source_sha)
    cur=readable(cb); prior=readable(pb); src=readable(sb)
    if cur.size!=prior.size or cur.size!=src.size: raise RuntimeError((idx,"size mismatch",cur.size,prior.size,src.size))
    if cb[:128]!=pb[:128]: raise RuntimeError((idx,"header drift current-prior"))
    geo=geometry(rows)
    boxes=[g["source_bbox"] for g in geo]
    allow=mask_boxes((cur.height,cur.width),boxes)
    ca,pa=np.array(cur),np.array(prior)
    diff=np.any(ca!=pa,axis=2); ad=np.array(cur)[:,:,3]!=np.array(prior)[:,:,3]
    outside=int((diff & ~allow).sum()); alpha_out=int((ad & ~allow).sum())
    if outside or alpha_out: raise RuntimeError((idx,"lineage scope fail",outside,alpha_out))
    raw_cur,raw_prior,raw_src=decode(cb),decode(pb),decode(sb)
    overview(src,prior,cur,OUT/f"C251_Q{idx:03d}_{key}_READABLE.jpg")
    overview(raw_src,raw_prior,raw_cur,OUT/f"C251_Q{idx:03d}_{key}_RAW.jpg",raw=True)
    contacts(src,prior,cur,geo,OUT/f"C251_Q{idx:03d}_{key}_CONTACTS.jpg")
    return {
      "queue_index":idx,"asset_key":key,"candidate_path":path,"candidate_sha256":current_sha,
      "prior_candidate_sha256":prior_sha,"prior_blob_commit":pcommit,
      "source_sha256":source_sha,"source_provenance":source_path or f"historical_blob:{scommit}",
      "high_risk_reason":reason,
      "machine_qa":{
        "candidate_sha_exact":True,"dimensions":list(cur.size),
        "header_128_exact_to_prior":True,
        "changed_pixels_outside_declared_source_bboxes":outside,
        "alpha_changed_outside_declared_source_bboxes":alpha_out,
        "bbox_size_positive_margin":f"{len(geo)}/{len(geo)} PASS",
        "localized_bbox_pair_overlap":"0 by rectangle gate",
        "per_region":geo,
        "raw_orientation":"mirror_y"
      },
      "visual_evidence":[
        f"C251_Q{idx:03d}_{key}_READABLE.jpg",
        f"C251_Q{idx:03d}_{key}_RAW.jpg",
        f"C251_Q{idx:03d}_{key}_CONTACTS.jpg"
      ],
      "controller_visual_qa":"PENDING_CONTROLLER","c3_strict":"PENDING_CONTROLLER",
      "decision":"PENDING_CONTROLLER_VISUAL_AND_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }

# q54: current B229 all-17-row source-transform/scale rework.
b229=json.loads(Path("localization/graphics/role_B/20261007-B-MANUALQA229-FA7BBB13/B229_FA7_REPORT.json").read_text(encoding="utf-8"))
q54=verify_lineage(
  54,"FA7BBB13",
  "localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds",
  b229["candidate_sha256"],b229["before_candidate_sha256"],b229["source_sha256"],
  "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds",
  b229["rows"],"PRE_INGAME current-policy source-transform/slant + Slipstream scale false-negative"
)

# q60: current A139 adds two OUTRUN MILES rows onto B204's Stage repair.
a139=json.loads(Path("localization/graphics/role_A/20261006-A-USERREWORK139-IGR012-SLANT/A139_USER_REWORK_IGR012_IGR012_REPORT.json").read_text(encoding="utf-8"))
b204=json.loads(Path("localization/graphics/role_B/20261006-B-USERREWORK204-A064-STAGE-SLANT/B204_IGR010_REPORT.json").read_text(encoding="utf-8"))
q60_rows=[{
 "key":"stage",
 "original_bbox":b204["mapping"]["localized_binding"]["source_effect_bbox"],
 "localized_bbox":b204["material_fix"]["new_localized_bbox"]
}]
for r in a139["assets"]["A064FDFC"]["rows"]:
    q60_rows.append({"key":r["key"],"original_bbox":r["source_effect_bbox"],"localized_bbox":r["localized_bbox"]})
q60=verify_lineage(
  60,"A064FDFC",
  "localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds",
  a139["assets"]["A064FDFC"]["candidate_sha256"],b204["material_fix"]["candidate_sha256"],a139["assets"]["A064FDFC"]["source_sha256"],
  "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds",
  a139["assets"]["A064FDFC"]["rows"],"IGR-010 Stage + IGR-012 OUTRUN MILES user in-game/JPG regression"
)
# verify B204 Stage bytes are preserved exactly by A139.
cur60=readable(load_bytes(q60["candidate_path"]))
prior60=readable(find_blob(q60["candidate_path"],b204["material_fix"]["candidate_sha256"])[0])
sb=b204["mapping"]["localized_binding"]["source_effect_bbox"]
x0,y0,x1,y1=sb
stage_exact=bool(np.array_equal(np.array(cur60)[y0:y1,x0:x1],np.array(prior60)[y0:y1,x0:x1]))
if not stage_exact: raise RuntimeError("q60 B204 Stage not preserved")
q60["machine_qa"]["b204_stage_source_bbox_pixel_exact_after_a139"]=True
q60["machine_qa"]["combined_regions"] = geometry(q60_rows)
# regenerate contacts including preserved Stage + current A139 rows.
src60=readable(load_bytes("localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"))
contacts(src60,prior60,cur60,q60["machine_qa"]["combined_regions"],OUT/"C251_Q060_A064FDFC_COMBINED_CONTACTS.jpg")
q60["visual_evidence"].append("C251_Q060_A064FDFC_COMBINED_CONTACTS.jpg")

# q212: A88 current C2C title layered on B166 Heart Attack title.
a88=json.loads(Path("localization/graphics/role_A/20261006-A-INGAME88-IGR001-C2C/A88_IGR001_REPORT.json").read_text(encoding="utf-8"))
b166=json.loads(Path("localization/graphics/role_B/20261006-B-INGAME166-IGR002-INTRO/B166_IGR002_REPORT.json").read_text(encoding="utf-8"))
cur212=a88["assets"]["BA"]; prior212=b166["assets"]["BA"]
q212=verify_lineage(
  212,"BA0147DA",cur212["candidate_path"],cur212["candidate_sha256"],prior212["candidate_sha256"],
  cur212["source_sha256"],None,[cur212["rows"][0]],"IGR-001 C2C title + IGR-002 Heart Attack title user in-game regressions"
)
curim=readable(load_bytes(cur212["candidate_path"]))
priorim=readable(find_blob(cur212["candidate_path"],prior212["candidate_sha256"])[0])
hr=prior212["rows"][0]
hb=hr["original_bbox"]; x0,y0,x1,y1=hb
heart_exact=bool(np.array_equal(np.array(curim)[y0:y1,x0:x1],np.array(priorim)[y0:y1,x0:x1]))
if not heart_exact: raise RuntimeError("q212 B166 Heart Attack title not preserved by A88")
heart_geo=geometry([hr])[0]
q212["machine_qa"]["b166_heart_attack_source_bbox_pixel_exact_after_a88"]=True
q212["machine_qa"]["combined_regions"]=[heart_geo]+q212["machine_qa"]["per_region"]
# combined contacts using exact source recovered by source SHA.
src212=readable(find_blob(cur212["candidate_path"],cur212["source_sha256"])[0])
contacts(src212,priorim,curim,q212["machine_qa"]["combined_regions"],OUT/"C251_Q212_BA0147DA_COMBINED_CONTACTS.jpg")
q212["visual_evidence"].append("C251_Q212_BA0147DA_COMBINED_CONTACTS.jpg")

for q in (q60,q54,q212):
    p=OUT/f"C251_Q{q['queue_index']:03d}_{q['asset_key']}_MACHINE_QA.json"
    p.write_text(json.dumps({"schema_version":2,"role":"C","run":"C251","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",**q},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

summary={
 "schema_version":1,"role":"C","run":"C251","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "selection_priority":["q60 IGR-010/012 user regression","q54 fresh B229 high-risk PRE_INGAME rework","q212 IGR-001/002 user regressions"],
 "assets":[{"index":q["queue_index"],"key":q["asset_key"],"candidate_sha256":q["candidate_sha256"],"machine_qa":"PASS"} for q in (q60,q54,q212)],
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(OUT/"C251_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
