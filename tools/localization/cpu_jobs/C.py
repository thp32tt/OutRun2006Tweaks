#!/usr/bin/env python3
# C254 C1 fresh independent QA: A166 repairs q57/q61/q65
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT=Path("localization/graphics/role_C/20261007-C254-C1-BATCH-Q057-Q061-Q065")
OUT.mkdir(parents=True,exist_ok=True)
C250=Path("localization/graphics/role_C/20261007-C250-C1-BATCH-Q057-Q061-Q065")
A166=Path("localization/graphics/role_A/20261007-A166-C250-Q057-Q061-Q065-STYLE-SEMANTIC")
PROD=json.loads((A166/"A166_BATCH_REPORT.json").read_text(encoding="utf-8"))
PIN="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"

CFG={
57:{"key":"39229D64","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds",
    "candidate_sha":"d2831fcfd1bb8027fc129ff50e70c90c21094df13765daa3d5fb9c6fda3ae70a",
    "prior_sha":"3dae27fdeb7d2cde6d440b45f1e94ddafe35a97fe749447fdf0f3974d5e90c16",
    "source_sha":"2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481",
    "source_dds":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds",
    "trigger":"C250 source-style/slant/gradient-depth FAIL -> A166 repair",
    "critical":["mission_cleared","total_rank_green","special_request","target","mission_failed","total_rank_brown","total_rank_pink","special_request_alt"]},
61:{"key":"C4A2937B","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds",
    "candidate_sha":"df250af92785727f38d176f3b2569c9d6d2b0e7a3f7d296adaa2f5c343b1d71e",
    "prior_sha":"fe1e7e7d264694c39f2bdbf50bb0a94ba15b88aea5b52873df4ceae749a8f95e",
    "source_sha":"821dddc662ca2349aa313f49278d5558c07e29b7a8f5d755e6987a349f0e7dd0",
    "source_dds":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds",
    "trigger":"C250 semantic + yellow/white/navy source-family FAIL -> A166 repair",
    "critical":["go_gate","cut_line","keep_passing"]},
65:{"key":"EBEF6D20","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds",
    "candidate_sha":"10d0e1899d8d167eb1dcb303429dd4dc7bdf09096e6c5720afce884cc32afe1f",
    "prior_sha":"2b39cf005e79149890f0cfee605d29144d7d257e9cc9179b6c1f583ce393fce5",
    "source_sha":"8d832df296241c372cf182439d9f44721b07f7555b9ee3b17b0750908194877c",
    "source_url":f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{PIN}/Release/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds",
    "trigger":"C250 EASY color + source outline/slant family FAIL -> A166 repair",
    "critical":["course","left","right","easy","hard"]}
}

def H(b): return hashlib.sha256(b).hexdigest()
def git_old(path,want):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:continue
        if H(b)==want:return b,c
    raise RuntimeError(f"prior SHA not found {want} {path}")
def dec(b): return Image.open(io.BytesIO(b)).convert("RGBA")
def meta(b):
    return {"height":struct.unpack_from("<I",b,12)[0],"width":struct.unpack_from("<I",b,16)[0],
            "mips":struct.unpack_from("<I",b,28)[0] or 1,"header_sha":H(b[:128])}
def mask_union(shape,boxes):
    m=np.zeros(shape[:2],bool)
    for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=True
    return m
def flat(im,bg=(72,72,72)):
    im=im.convert("RGBA"); base=Image.new("RGBA",im.size,bg+(255,)); base.alpha_composite(im); return base.convert("RGB")
def fit(im,mw,mh):
    im=flat(im); s=min(mw/im.width,mh/im.height,1.0)
    return im if s>=1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)
def overview(src,prior,cur,path,title):
    ims=[fit(x,560,560) for x in (src,prior,cur)]
    W=sum(x.width for x in ims)+18*2; H=max(x.height for x in ims)+44
    o=Image.new("RGB",(W,H),(24,24,24)); d=ImageDraw.Draw(o); xx=0
    for lab,im in zip(["SOURCE","C250_REJECTED","A166_CURRENT"],ims):
        d.text((xx+3,3),lab,fill="white"); o.paste(im,(xx,24)); xx+=im.width+18
    d.text((4,H-4),title,fill="white",anchor="ls")
    o.save(path,quality=84,subsampling=0,optimize=True)
def contacts(src,prior,cur,rows,keys,path):
    cards=[]
    for r in rows:
        if r["key"] not in keys: continue
        x0,y0,x1,y1=r["original_bbox"]; p=28
        box=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
        ims=[fit(x.crop(box),360,150) for x in (src,prior,cur)]
        W=sum(x.width for x in ims)+12*2; H=max(x.height for x in ims)+38
        c=Image.new("RGB",(W,H),(30,30,30));d=ImageDraw.Draw(c);xx=0
        for lab,im in zip(["SRC","C250","A166"] ,ims):
            d.text((xx+2,2),lab,fill="white");c.paste(im,(xx,20));xx+=im.width+12
        d.text((4,H-3),r["key"],fill="white",anchor="ls");cards.append(c)
    W=max(x.width for x in cards); H=sum(x.height for x in cards)+6*(len(cards)-1)
    o=Image.new("RGB",(W,H),(18,18,18)); y=0
    for c in cards:o.paste(c,(0,y));y+=c.height+6
    o.save(path,quality=88,subsampling=0,optimize=True)

summary={"schema_version":1,"role":"C","run":"C254","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
         "execution_backend":"github-actions repository-backed independent QA after ChatGPT-local github.com DNS failure",
         "assets":[],"runtime_validation":"UNTESTED","forbidden_domains_touched":[]}

for idx,a in CFG.items():
    c250=json.loads((C250/f"C250_q{idx:03d}_{a['key']}_MACHINE_QA.json").read_text(encoding="utf-8"))
    prod=PROD["assets"][f"q{idx}"]
    if prod["candidate_sha256"]!=a["candidate_sha"]: raise RuntimeError(("producer report candidate drift",idx))
    full_rows=c250["machine_qa"]["per_region"]
    touched={r["key"]:r for r in prod["machine_qa"]["per_region"]}
    rows=[]
    for r in full_rows:
        rr=dict(r)
        if rr["key"] in touched: rr["localized_bbox"]=touched[rr["key"]]["localized_bbox"]
        sb=rr["original_bbox"]; lb=rr["localized_bbox"]
        sw,sh=sb[2]-sb[0],sb[3]-sb[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        d=[lb[0]-sb[0],sb[2]-lb[2],lb[1]-sb[1],sb[3]-lb[3]]
        rr.update({"source_size":[sw,sh],"localized_size":[lw,lh],
                   "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
                   "containment":"PASS" if min(d)>=0 else "FAIL",
                   "size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL",
                   "positive_margin":"PASS" if min(d)>0 else "FAIL"})
        rows.append(rr)
    cb=Path(a["candidate"]).read_bytes()
    if H(cb)!=a["candidate_sha"]: raise RuntimeError(("candidate drift",idx,H(cb)))
    pb,pcommit=git_old(a["candidate"],a["prior_sha"])
    if "source_dds" in a:
        sb=Path(a["source_dds"]).read_bytes()
    else:
        with urllib.request.urlopen(a["source_url"],timeout=90) as r: sb=r.read()
    if H(sb)!=a["source_sha"]: raise RuntimeError(("source drift",idx,H(sb)))
    cm,pm,sm=meta(cb),meta(pb),meta(sb)
    if cm["header_sha"]!=sm["header_sha"]: raise RuntimeError(("header drift source",idx))
    if cm["mips"]!=1: raise RuntimeError(("unexpected mips",idx,cm["mips"]))
    cur_raw,prior_raw,src_raw=dec(cb),dec(pb),dec(sb)
    cur,prior,src=ImageOps.flip(cur_raw),ImageOps.flip(prior_raw),ImageOps.flip(src_raw)
    if not(cur.size==prior.size==src.size): raise RuntimeError(("size mismatch",idx,src.size,prior.size,cur.size))
    ca,pa,sa=np.array(cur),np.array(prior),np.array(src)
    full_boxes=[r["original_bbox"] for r in rows]
    touch_boxes=[r["original_bbox"] for r in rows if r["key"] in touched]
    full=mask_union(ca.shape,full_boxes); touch=mask_union(ca.shape,touch_boxes)
    sc=np.any(sa!=ca,axis=2); sca=sa[:,:,3]!=ca[:,:,3]
    pc=np.any(pa!=ca,axis=2); pca=pa[:,:,3]!=ca[:,:,3]
    source_out=int((sc&~full).sum()); source_alpha_out=int((sca&~full).sum())
    blast_out=int((pc&~touch).sum()); blast_alpha_out=int((pca&~touch).sum())
    if any(r["containment"]!="PASS" or r["size_ceiling"]!="PASS" or r["positive_margin"]!="PASS" for r in rows):
        raise RuntimeError(("geometry fail",idx))
    if source_out or source_alpha_out or blast_out or blast_alpha_out:
        raise RuntimeError(("scope fail",idx,source_out,source_alpha_out,blast_out,blast_alpha_out))
    overview(src,prior,cur,OUT/f"C254_q{idx:03d}_{a['key']}_ALPHA_OVERVIEW.jpg",f"q{idx} | {a['trigger']}")
    contacts(src,prior,cur,rows,a["critical"],OUT/f"C254_q{idx:03d}_{a['key']}_ALPHA_CONTACTS.jpg")
    overview(src_raw,prior_raw,cur_raw,OUT/f"C254_q{idx:03d}_{a['key']}_RAW.jpg",f"q{idx} RAW DDS")
    rep={"schema_version":1,"role":"C","run":"C254","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
         "queue_index":idx,"asset_key":a["key"],"candidate_sha256":H(cb),"canonical_source_sha256":H(sb),
         "prior_c250_rejected_sha256":H(pb),"prior_blob_commit":pcommit,"trigger":a["trigger"],
         "machine_qa":{"dimensions":[cm["width"],cm["height"]],"mips":cm["mips"],
           "header_128_exact_source_current":True,
           "source_vs_current_changed_outside_all_exact_source_bboxes":source_out,
           "source_vs_current_alpha_changed_outside_all_exact_source_bboxes":source_alpha_out,
           "c250_prior_vs_a166_current_changed_outside_touched_rework_bboxes":blast_out,
           "c250_prior_vs_a166_current_alpha_changed_outside_touched_rework_bboxes":blast_alpha_out,
           "full_geometry_count":len(rows),"touched_geometry_count":len(touched),
           "bbox_size_positive_margin":f"{len(rows)}/{len(rows)} PASS",
           "geometry_binding_note":"unchanged rows are byte-identical to C250 rejected candidate outside A166 touched source bboxes; touched localized bboxes are exact A166 producer report bound to current candidate SHA",
           "per_region":rows},
         "visual_evidence":[f"C254_q{idx:03d}_{a['key']}_ALPHA_OVERVIEW.jpg",f"C254_q{idx:03d}_{a['key']}_ALPHA_CONTACTS.jpg",f"C254_q{idx:03d}_{a['key']}_RAW.jpg"],
         "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","c3_strict_audit":"PENDING_CONTROLLER_REVIEW",
         "runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    if idx==61:
        rep["semantic_gate"]={"cut_line_source":"Cut the line!","required_proven_translation":"하트선을 통과하세요!","producer_current":"하트선을 통과하세요!","result":"PASS_BINDING_PENDING_VISUAL"}
    if idx==65:
        rep["color_gate"]={"easy_required":"green/navy/white source family","producer_current":"green/navy/white","result":"PASS_BINDING_PENDING_VISUAL"}
    (OUT/f"C254_q{idx:03d}_{a['key']}_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":idx,"key":a["key"],"candidate_sha256":H(cb),"machine_qa":"PASS","controller_visual_qa":"PENDING","c3":"PENDING"})
(OUT/"C254_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
