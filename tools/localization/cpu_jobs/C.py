#!/usr/bin/env python3
# C249 C2 fresh independent QA batch: q86/q44/q48
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import hashlib, json, os, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C249-C2-BATCH-Q086-Q044-Q048"
OUT=Path("localization/graphics/role_C")/RUN
OUT.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()

def git_blob(path,wanted):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try:
            b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:
            continue
        if sha(b)==wanted:
            return b,c
    raise RuntimeError(f"historical blob not found: {path} {wanted}")

def rgba32_decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported RGBA32 DDS",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,ImageOps.flip(raw),{"w":w,"h":h,"mips":mips or 1,"mode":mode,"header_sha256":sha(b[:128])}

def rectmask(h,w,boxes):
    m=np.zeros((h,w),bool)
    for x0,y0,x1,y1 in boxes:
        m[y0:y1,x0:x1]=True
    return m

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def q44():
    base=Path("localization/graphics/role_B/20261007-B238-Q044-19CEDB9-C246-REWORK")
    prod=json.loads((base/"B238_19CEDB9_MACHINE_QA.json").read_text(encoding="utf-8"))
    path=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds")
    cur_b=path.read_bytes()
    wanted=prod["candidate_sha256"]
    if sha(cur_b)!=wanted: raise RuntimeError(("q44 candidate drift",sha(cur_b),wanted))
    prev_b,prev_commit=git_blob(str(path),prod["before_candidate_sha256"])
    cur_raw,cur,meta=rgba32_decode(cur_b); prev_raw,prev,pmeta=rgba32_decode(prev_b)
    if meta["header_sha256"]!=pmeta["header_sha256"]: raise RuntimeError("q44 header drift")
    boxes=[r["original_bbox"] for r in prod["rows"]]
    allow=rectmask(meta["h"],meta["w"],boxes)
    ca,pa=np.array(cur),np.array(prev)
    diff=np.any(ca!=pa,axis=2); adiff=ca[:,:,3]!=pa[:,:,3]
    outside=int((diff & ~allow).sum()); alpha_out=int((adiff & ~allow).sum())
    clean=np.array(Image.open(base/"B238_19CEDB9_CLEAN_PLATE.png").convert("RGBA"))
    if clean.shape!=ca.shape: raise RuntimeError(("q44 clean dimensions",clean.shape,ca.shape))
    localized=np.any(ca!=clean,axis=2) & allow
    per=[]
    for row in prod["rows"]:
        sb=row["original_bbox"]; x0,y0,x1,y1=sb
        rm=np.zeros_like(allow); rm[y0:y1,x0:x1]=True
        lb=bbox(localized & rm)
        if lb is None: raise RuntimeError(("q44 no localized pixels",row["key"]))
        sx,sy=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        ok=min(margins)>0 and lw<=sx and lh<=sy
        if not ok: raise RuntimeError(("q44 bbox gate",row["key"],lb,sb,margins))
        per.append({"key":row["key"],"source_bbox":sb,"localized_bbox":lb,"source_size":[sx,sy],
                    "localized_size":[lw,lh],"margins":margins,
                    "width_ratio":round(lw/sx,4),"height_ratio":round(lh/sy,4)})
    if outside or alpha_out: raise RuntimeError(("q44 blast radius",outside,alpha_out))
    return {
      "queue_index":44,"asset_key":"19CEDB9","candidate_sha256":wanted,
      "candidate_path":str(path),"prior_candidate_sha256":prod["before_candidate_sha256"],
      "prior_blob_commit":prev_commit,"high_risk_reason":"PJR-010 TEXT_SCALE_TOO_SMALL_VS_SOURCE after prior C pass",
      "independent_machine_qa":{
        "candidate_sha_exact":True,"dimensions":[meta["w"],meta["h"]],"mips":meta["mips"],
        "header_128_exact_to_prior":True,"changed_pixels_outside_exact_source_bboxes":outside,
        "alpha_changed_outside_exact_source_bboxes":alpha_out,
        "bbox_size_positive_margin":f"{len(per)}/{len(per)} PASS","per_region":per,
        "clean_plate_recomparison":"PASS","raw_orientation":"mirror_y"
      },
      "visual_evidence":[
        str(base/"B238_19CEDB9_ROW_CONTACTS.jpg"),
        str(base/"B238_19CEDB9_RAW.jpg"),
        str(base/"B238_19CEDB9_PRACTICAL.jpg")
      ]
    }

def q48():
    base=Path("localization/graphics/role_B/20261006-B-USERREWORK203-B169-SLIPSTREAM-SLANT")
    prod=json.loads((base/"B203_B1696633_REPORT.json").read_text(encoding="utf-8"))
    path=Path(prod["candidate_path"])
    cur_b=path.read_bytes()
    wanted=prod["candidate_sha256"]
    if sha(cur_b)!=wanted: raise RuntimeError(("q48 candidate drift",sha(cur_b),wanted))
    prev_b,prev_commit=git_blob(str(path),prod["superseded_candidate_sha256"])
    cur_raw,cur,meta=rgba32_decode(cur_b); prev_raw,prev,pmeta=rgba32_decode(prev_b)
    if meta["header_sha256"]!=pmeta["header_sha256"]: raise RuntimeError("q48 header drift")
    sb=prod["slipstream"]["original_bbox"]; allow=rectmask(meta["h"],meta["w"],[sb])
    ca,pa=np.array(cur),np.array(prev)
    diff=np.any(ca!=pa,axis=2); adiff=ca[:,:,3]!=pa[:,:,3]
    outside=int((diff & ~allow).sum()); alpha_out=int((adiff & ~allow).sum())
    prot=np.array(Image.open(base/"B1696633_PROTECTED_MASK.png").convert("L"))>0
    if prot.shape!=allow.shape: raise RuntimeError(("q48 protected dims",prot.shape,allow.shape))
    protected_changed=int((diff & prot).sum())
    change_bbox=bbox(diff)
    if outside or alpha_out or protected_changed:
        raise RuntimeError(("q48 scope",outside,alpha_out,protected_changed))
    loc=prod["slipstream"]["localized_bbox"]; x0,y0,x1,y1=sb
    margins=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
    if min(margins)<=0: raise RuntimeError(("q48 margin",margins))
    return {
      "queue_index":48,"asset_key":"B1696633","candidate_sha256":wanted,
      "candidate_path":str(path),"prior_candidate_sha256":prod["superseded_candidate_sha256"],
      "prior_blob_commit":prev_commit,"high_risk_reason":"IGR-009 USER_INGAME_FAIL Slipstream + slant/readability follow-up",
      "independent_machine_qa":{
        "candidate_sha_exact":True,"dimensions":[meta["w"],meta["h"]],"mips":meta["mips"],
        "header_128_exact_to_prior":True,"changed_pixels_outside_exact_source_bbox":outside,
        "alpha_changed_outside_exact_source_bbox":alpha_out,"protected_changed_pixels":protected_changed,
        "changed_pixel_bbox":change_bbox,"source_bbox":sb,"localized_bbox":loc,
        "positive_margin":"PASS","margins":margins,"other_rows_preserved_by_binary_scope":"PASS",
        "raw_orientation":"mirror_y"
      },
      "visual_evidence":[
        str(base/"B203_SLIPSTREAM_SOURCE_OLD_CLEAN_FINAL.jpg"),
        str(base/"B203_RAW_COMPARE.jpg"),
        str(base/"B203_SLIPSTREAM_2X.jpg")
      ]
    }

def q86():
    base=Path("localization/graphics/role_A/20261006-A-USERJPG144-CLEANUP")
    rep=json.loads((base/"A_USERJPG144_REWORK_REPORT.json").read_text(encoding="utf-8"))
    item=next(x for x in rep.get("assets",rep.get("results",rep.get("items",[]))) if "C598919A" in x["asset"])
    path=Path("localization/graphics/hd_candidates")/item["asset"]
    cur_b=path.read_bytes(); wanted=item["after_sha256"]
    if sha(cur_b)!=wanted: raise RuntimeError(("q86 candidate drift",sha(cur_b),wanted))
    prev_b,prev_commit=git_blob(str(path),item["before_sha256"])
    if cur_b[:4]!=b"DDS " or prev_b[:4]!=b"DDS ": raise RuntimeError("q86 not DDS")
    h,w=struct.unpack_from("<2I",cur_b,12)
    ph,pw=struct.unpack_from("<2I",prev_b,12)
    if (w,h)!=(pw,ph): raise RuntimeError(("q86 dimensions",(w,h),(pw,ph)))
    pf=struct.unpack_from("<8I",cur_b,76); ppf=struct.unpack_from("<8I",prev_b,76)
    fourcc=struct.pack("<I",pf[2]).decode("latin1")
    if fourcc!="DXT5": raise RuntimeError(("q86 expected DXT5",repr(fourcc),pf))
    if cur_b[:128]!=prev_b[:128]: raise RuntimeError("q86 header drift")
    bw=(w+3)//4; bh=(h+3)//4; expected=128+bw*bh*16
    if len(cur_b)!=expected or len(prev_b)!=expected: raise RuntimeError(("q86 dxt5 length",len(cur_b),expected))
    cb=np.frombuffer(cur_b,dtype=np.uint8,offset=128).reshape(bh,bw,16)
    pb=np.frombuffer(prev_b,dtype=np.uint8,offset=128).reshape(bh,bw,16)
    changed=np.any(cb!=pb,axis=2)
    allowed=np.zeros((bh,bw),bool)
    details=item["details"]
    for d in details:
        x0,y0,x1,y1=d["bbox"]
        ry0=h-y1; ry1=h-y0
        bx0=x0//4; bx1=(x1+3)//4; by0=ry0//4; by1=(ry1+3)//4
        allowed[by0:by1,bx0:bx1]=True
    outside=int((changed & ~allowed).sum())
    inside=int((changed & allowed).sum())
    if outside or inside==0: raise RuntimeError(("q86 dxt5 block scope",inside,outside))
    per=[]
    for d in details:
        sb=d["bbox"]; lb=d["localized_bbox"]; x0,y0,x1,y1=sb
        margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
        sx,sy=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        if min(margins)<=0 or lw>sx or lh>sy:
            raise RuntimeError(("q86 bbox gate",d["region_idx"],sb,lb,margins))
        per.append({"region_idx":d["region_idx"],"kind":d["kind"],"source_bbox":sb,"localized_bbox":lb,
                    "margins":margins,"width_ratio":round(lw/sx,4),"height_ratio":round(lh/sy,4)})
    return {
      "queue_index":86,"asset_key":"C598919A","candidate_sha256":wanted,
      "candidate_path":str(path),"prior_candidate_sha256":item["before_sha256"],"prior_blob_commit":prev_commit,
      "high_risk_reason":"PJR-022 TEXT_CLIPPING|WRONG_SLANT_DIRECTION|STYLE_OVERDONE|READABILITY_DEGRADED",
      "independent_machine_qa":{
        "candidate_sha_exact":True,"format":"DXT5","dimensions":[w,h],"header_128_exact_to_prior":True,
        "changed_dxt5_blocks_inside_allowed_raw_mirror_y_targets":inside,
        "changed_dxt5_blocks_outside_allowed_raw_mirror_y_targets":outside,
        "bbox_size_positive_margin":f"{len(per)}/{len(per)} PASS","per_region":per,
        "raw_orientation_from_producer_roundtrip":"mirror_y"
      },
      "visual_evidence":[
        str(base/"022_C598919A_SOURCE_OLD_NEW.jpg"),
        str(base/"A144_RAW_FLIPY_SHEET_4.jpg")
      ]
    }

# Priority within C2 batch: P0 user JPG q86, then newest fresh B q44, then user in-game q48.
assets=[q86(),q44(),q48()]
summary={"schema_version":1,"role":"C","run":"C249","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
         "selection_priority":["q86 P0 user JPG regression","q44 fresh B238/PJR-010","q48 IGR-009"],
         "assets":[],"runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
for a in assets:
    out={"schema_version":2,"role":"C","run":"C249","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",**a,
         "controller_visual_qa":"PENDING_CONTROLLER","c3_strict":"PENDING_CONTROLLER",
         "decision":"PENDING_CONTROLLER_VISUAL_AND_C3","runtime_validation":"UNTESTED",
         "forbidden_domains_touched":[]}
    p=OUT/f"C249_Q{a['queue_index']:03d}_{a['asset_key']}_MACHINE_QA.json"
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["queue_index"],"key":a["asset_key"],
                              "candidate_sha256":a["candidate_sha256"],"machine_qa":"PASS"})
(OUT/"C249_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
