#!/usr/bin/env python3
# C224 fresh independent final QA for q55 A148R 2EA557B4.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, io, json, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageChops

repo=Path.cwd()
run="20261007-C224-2EA557B4-A148R"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261007-A-MANUALQA148R-2EA557B4/2EA557B4_HD_CLEAN_PLATE.png"
EXPECTED="ee11a2521e3c79c4d327acab28d87aacdb3f59b31d68c843eac20c7a87e88c5c"
SOURCE_SHA="b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def decode(data):
    with Image.open(io.BytesIO(data)) as im:
        return im.convert("RGBA")
def flatten(im,bg=(96,96,96)):
    im=im.convert("RGBA"); z=Image.new("RGB",im.size,bg); z.paste(im.convert("RGB"),mask=im.getchannel("A")); return z

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-Korean-C224"})
with urllib.request.urlopen(req,timeout=90) as resp: sb=resp.read()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha_bytes(sb)))
cb=candidate.read_bytes()
if sha_bytes(cb)!=EXPECTED: raise RuntimeError(("candidate drift",sha_bytes(cb),EXPECTED))
if sb[:4]!=b"DDS " or cb[:4]!=b"DDS ": raise RuntimeError("not DDS")
if len(sb)!=len(cb) or len(cb)!=524416: raise RuntimeError(("byte size",len(sb),len(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("DDS header drift")

src_raw=decode(sb); cand_raw=decode(cb)
if src_raw.size!=(2048,256) or cand_raw.size!=src_raw.size: raise RuntimeError(("dimensions",src_raw.size,cand_raw.size))
src=ImageOps.flip(src_raw); cand=ImageOps.flip(cand_raw)
sa=np.asarray(src,np.uint8); fa=np.asarray(cand,np.uint8)
source_vis=sa[:,:,3]>0; target_vis=fa[:,:,3]>0
ob=bbox(source_vis); lb=bbox(target_vis)
if ob!=[1,105,1090,248]: raise RuntimeError(("source bbox drift",ob))
if lb!=[9,113,890,240]: raise RuntimeError(("localized bbox drift",lb))
sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("bbox/size/margin fail",ob,lb,margins))
allowed=np.zeros(source_vis.shape,bool); allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
visible_out=int(np.count_nonzero(target_vis & ~allowed))
if visible_out: raise RuntimeError(("visible target outside source bbox",visible_out))

clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))
cla=np.asarray(clean,np.uint8)
clean_visible=int(np.count_nonzero(cla[:,:,3]>0))
if clean_visible!=0: raise RuntimeError(("clean plate visible alpha remains",clean_visible))

# DXT5 block-boundary containment: no changed block wholly outside bbox.
W,H=src_raw.size; bx_count=W//4; by_count=H//4
changed=[]; changed_out=[]; partial=[]; partial_color_or_endpoint_drift=[]
for by in range(by_count):
    for bx in range(bx_count):
        off=128+(by*bx_count+bx)*16
        a=sb[off:off+16]; b=cb[off:off+16]
        if a==b: continue
        changed.append([bx,by])
        # RAW bbox corresponding to readable bbox under vertical flip.
        raw_ob=[ob[0], H-ob[3], ob[2], H-ob[1]]
        x0,y0,x1,y1=bx*4,by*4,bx*4+4,by*4+4
        intersects=not (x1<=raw_ob[0] or x0>=raw_ob[2] or y1<=raw_ob[1] or y0>=raw_ob[3])
        fully=(x0>=raw_ob[0] and x1<=raw_ob[2] and y0>=raw_ob[1] and y1<=raw_ob[3])
        if not intersects: changed_out.append([bx,by])
        elif not fully:
            partial.append([bx,by])
            if a[:2]!=b[:2] or a[8:16]!=b[8:16]:
                partial_color_or_endpoint_drift.append([bx,by])
if changed_out or partial_color_or_endpoint_drift:
    raise RuntimeError(("DXT5 boundary gate",len(changed_out),len(partial_color_or_endpoint_drift)))

# RAW/readable orientation parity.
if ImageChops.difference(ImageOps.flip(cand_raw),cand).getbbox() is not None: raise RuntimeError("raw/readable parity")

# Build evidence from exact source + current candidate + transparent clean plate.
def card(label,im,scale=1):
    v=flatten(im)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,max(v.height+30,286)),(28,28,28)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((6,5),label,fill="white"); return c

cards=[card("SOURCE_READABLE",src),card("CLEAN_PLATE",clean),card("A148R_FINAL",cand)]
sheet=Image.new("RGB",(2048,286*3),(24,24,24))
for i,c in enumerate(cards): sheet.paste(c,(0,i*286))
sheet.save(out/"C224_2EA_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

rawsheet=Image.new("RGB",(2048,286*2),(24,24,24))
for i,c in enumerate([card("SOURCE_RAW_MIRROR_Y",src_raw),card("A148R_RAW_MIRROR_Y",cand_raw)]): rawsheet.paste(c,(0,i*286))
rawsheet.save(out/"C224_2EA_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

# High-zoom readable detail, same practical scale.
crop=(0,96,1120,255)
sc=2
ss=flatten(src).crop(crop).resize(((crop[2]-crop[0])*sc,(crop[3]-crop[1])*sc),Image.Resampling.NEAREST)
ff=flatten(cand).crop(crop).resize(((crop[2]-crop[0])*sc,(crop[3]-crop[1])*sc),Image.Resampling.NEAREST)
detail=Image.new("RGB",(ss.width,max(ss.height,ff.height)*2+60),(24,24,24)); d=ImageDraw.Draw(detail)
d.text((6,5),"SOURCE",fill="white"); detail.paste(ss,(0,26)); y=ss.height+30; d.text((6,y+5),"A148R_FINAL",fill="white"); detail.paste(ff,(0,y+26))
detail.save(out/"C224_2EA_SOURCE_FINAL_DETAIL.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C224","queue_index":55,"asset":asset,
 "producer_run":"A148R","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"canonical pinned source decoded independently; source visible bbox re-derived from alpha; current candidate decoded independently; no producer bbox/mask consumed for containment",
 "machine_status":"PASS",
 "structure":{"dimensions":[2048,256],"format":"DXT5","header_128_exact":True,"raw_orientation":"mirror_y","bytes":len(cb)},
 "geometry":{"original_bbox":ob,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
             "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
             "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","source_relative_width":round(lw/sw,4)},
 "pixel_gates":{"localized_visible_pixels_outside_source_bbox":visible_out,"clean_visible_alpha_pixels":clean_visible,
                "changed_dxt5_blocks":len(changed),"changed_dxt5_blocks_wholly_outside_allowed":len(changed_out),
                "partial_boundary_changed_blocks":len(partial),"partial_boundary_endpoint_or_color_drift":len(partial_color_or_endpoint_drift),
                "raw_readable_parity":"PASS"},
 "visual_evidence":[str((out/"C224_2EA_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
                    str((out/"C224_2EA_SOURCE_FINAL_DETAIL.jpg").relative_to(repo)),
                    str((out/"C224_2EA_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C224_2EA557B4_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C224_2EA557B4.json").write_text(json.dumps({
 "role":"C","run":"C224","queue_index":55,"asset":asset,"candidate_sha256":EXPECTED,
 "machine_status":"PASS","report":str((out/"C224_2EA557B4_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C224","candidate":EXPECTED,"machine_status":"PASS","geometry":report["geometry"],"dxt5":report["pixel_gates"]},ensure_ascii=False))
