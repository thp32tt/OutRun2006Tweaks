#!/usr/bin/env python3
# C226 fresh independent QA for A150 q139 313DB8CB.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C226-313DB8CB-A150"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261007-A-MANUALQA150-313DB8CB/313DB8CB_HD_CLEAN_PLATE.png"
EXPECTED="50ee1f3b43dc0bdbe6c9b198e9e382239e7b624088e0ef9d45bbb2e978ec4fd7"
SOURCE_SHA="4c85be80485375876cdcc6be0ebd1e5578032894a194a820b47f01b271fe4786"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds"
cells=[
 ("tuned","TUNED","튜닝 사양",[1404,968,1724,1024]),
 ("normal","NORMAL","일반 사양",[1724,968,2044,1024]),
]

def sha(p_or_b):
    if isinstance(p_or_b,(bytes,bytearray)): return hashlib.sha256(p_or_b).hexdigest()
    return hashlib.sha256(Path(p_or_b).read_bytes()).hexdigest()

def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if mode is None: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("unexpected bytes",len(b),w,h))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"raw_mode":mode}

def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def flatten(im):
    bg=Image.new("RGB",im.size,(104,104,104))
    bg.paste(im.convert("RGB"),mask=im.getchannel("A"))
    return bg

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C226"})
with urllib.request.urlopen(req,timeout=90) as resp: sb=resp.read()
cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(sb)))
if sha(cb)!=EXPECTED: raise RuntimeError(("candidate sha drift",sha(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header drift")
src_raw,src,sm=decode_rgba32(sb); cand_raw,cand,cm=decode_rgba32(cb)
if sm!=cm or (sm["width"],sm["height"])!=(2048,1024): raise RuntimeError(("structure",sm,cm))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))
sa=np.asarray(src,np.uint8); fa=np.asarray(cand,np.uint8); ca=np.asarray(clean,np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool); rows=[]; final_masks=[]
for key,en,ko,cell in cells:
    x0,y0,x1,y1=cell
    src_alpha=sa[y0:y1,x0:x1,3]>0
    ob0=bbox(src_alpha)
    if not ob0: raise RuntimeError(("no source alpha",key))
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    # exact clean plate must remove all visible source alpha within original source glyph bbox
    clean_source_alpha=int(np.count_nonzero(ca[ob[1]:ob[3],ob[0]:ob[2],3]>0))
    if clean_source_alpha: raise RuntimeError(("clean source alpha residue",key,clean_source_alpha))
    fin_alpha=fa[y0:y1,x0:x1,3]>0
    lb0=bbox(fin_alpha)
    if not lb0: raise RuntimeError(("no candidate alpha",key))
    lb=[x0+lb0[0],y0+lb0[1],x0+lb0[2],y0+lb0[3]]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("geometry",key,ob,lb,margins))
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    m=np.zeros((H,W),bool); m[lb[1]:lb[3],lb[0]:lb[2]]=fa[lb[1]:lb[3],lb[0]:lb[2],3]>0; final_masks.append(m)
    rows.append({"key":key,"source":en,"korean":ko,"cell":cell,"original_bbox":ob,"localized_bbox":lb,
                 "source_size":[sw,sh],"localized_size":[lw,lh],
                 "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
                 "width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
                 "clean_source_alpha_remaining":clean_source_alpha,
                 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

diff=np.any(fa!=sa,axis=2)
alpha_diff=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero(alpha_diff & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))

overlap=int(np.count_nonzero(final_masks[0]&final_masks[1]))
touch=[]
dil=final_masks[0].copy()
for dy in (-1,0,1):
    for dx in (-1,0,1):
        if dx==0 and dy==0: continue
        ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
        ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
        dil[ys,xs]|=final_masks[0][ys2,xs2]
if np.any(dil&final_masks[1]): touch.append(["tuned","normal"])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))

if ImageChops.difference(cand_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),cand).getbbox() is not None:
    raise RuntimeError("raw/readable parity")

# Evidence
def card(label,im):
    v=flatten(im)
    v.thumbnail((1600,800),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),(25,25,25)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
cards=[card("SOURCE_READABLE",src),card("A150_CLEAN",clean),card("A150_FINAL",cand)]
w=max(x.width for x in cards); h=sum(x.height for x in cards)
sheet=Image.new("RGB",(w,h),(25,25,25)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height
sheet.save(out/"C226_313_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

sf=flatten(src); ff=flatten(cand); contacts=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    a=sf.crop(cr); b=ff.crop(cr); scale=4
    a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST)
    b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(25,25,25)); d=ImageDraw.Draw(c)
    d.text((4,4),"SOURCE",fill="white"); d.text((a.width+10,4),"A150_FINAL",fill="white")
    c.paste(a,(0,26)); c.paste(b,(a.width+6,26)); contacts.append(c)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+6*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(25,25,25)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+6
cs.save(out/"C226_313_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("A150_RAW_MIRROR_Y",cand_raw)]
rw=max(x.width for x in rawcards); rh=sum(x.height for x in rawcards)
rs=Image.new("RGB",(rw,rh),(25,25,25)); yy=0
for c in rawcards: rs.paste(c,(0,yy)); yy+=c.height
rs.save(out/"C226_313_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

report={"schema_version":1,"role":"C","run":run,"qa_id":"C226","queue_index":139,"asset":asset,
"producer_run":"A150","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
"source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
"independent_basis":"pinned canonical RGBA32 source independently decoded; source and candidate alpha bboxes re-derived directly inside canonical sprite cells; producer masks not consumed",
"machine_status":"PASS","structure":sm,"rows":rows,
"summary":{"bbox_size_positive_margin":"2/2 PASS","candidate_changed_outside_exact_source_bboxes":outside,
"candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,"localized_pair_overlap_pixels":overlap,
"localized_touch_pairs":touch,"header_128_exact":True,"raw_readable_parity":"PASS"},
"visual_evidence":[str((out/"C226_313_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
str((out/"C226_313_ROW_CONTACT.jpg").relative_to(repo)),str((out/"C226_313_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
"controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
"runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}
(out/"C226_313DB8CB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C226_313DB8CB.json").write_text(json.dumps({"role":"C","run":"C226","queue_index":139,"asset":asset,
"candidate_sha256":EXPECTED,"machine_status":"PASS","report":str((out/"C226_313DB8CB_MACHINE_QA.json").relative_to(repo)),
"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C226","status":"PASS","rows":rows,"summary":report["summary"]},ensure_ascii=False))
