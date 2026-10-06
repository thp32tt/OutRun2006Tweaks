#!/usr/bin/env python3
# C227 fresh independent QA for A151 q175 754F0599.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
import hashlib,json,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops

repo=Path.cwd()
run="20261007-C227R-754F0599-A151"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261007-A-MANUALQA151-754F0599/754F0599_HD_CLEAN_PLATE.png"
EXPECTED="f21970a3d6d8ae69954d0159524856b5019cd1445daa65c55d85213f73e431f5"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
regions=[
 ("stage_select","stage select","스테이지 선택",[0,240,1500,397]),
 ("showroom","showroom","쇼룸",[0,397,1100,550]),
 ("single_player","single player","싱글 플레이",[0,550,1500,735]),
]
def h(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    height,width,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6])
    mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
    if mode is None: raise RuntimeError(("pixel masks",masks))
    if len(b)!=128+width*height*4: raise RuntimeError(("bytes",len(b),width,height))
    raw=Image.frombytes("RGBA",(width,height),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":width,"height":height,"pitch":pitch,"depth":depth,"mips":mips,"raw_mode":mode}
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def flat(im):
    z=Image.new("RGB",im.size,(104,104,104)); z.paste(im.convert("RGB"),mask=im.getchannel("A")); return z

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C227"})
with urllib.request.urlopen(req,timeout=90) as r: sb=r.read()
cb=candidate.read_bytes()
if h(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",h(sb)))
if h(cb)!=EXPECTED: raise RuntimeError(("candidate sha drift",h(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header drift")
sr,s,sm=decode(sb); fr,f,fm=decode(cb)
if sm!=fm or (sm["width"],sm["height"])!=(2048,1024): raise RuntimeError(("structure",sm,fm))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=s.size: raise RuntimeError(("clean size",clean.size))
sa=np.asarray(s,np.uint8); fa=np.asarray(f,np.uint8); ca=np.asarray(clean,np.uint8); H,W=sa.shape[:2]

allowed=np.zeros((H,W),bool); rows=[]; final_masks=[]
for key,en,ko,r in regions:
    x0,y0,x1,y1=r
    smask=sa[y0:y1,x0:x1,3]>0
    ob0=bbox(smask)
    if not ob0: raise RuntimeError(("no source alpha",key))
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    # exact source glyph/effect alpha footprint must be absent from the clean plate.
    source_alpha=np.zeros((H,W),bool); source_alpha[ob[1]:ob[3],ob[0]:ob[2]]=sa[ob[1]:ob[3],ob[0]:ob[2],3]>0
    clean_source_alpha=int(np.count_nonzero((ca[:,:,3]>0)&source_alpha))
    if clean_source_alpha: raise RuntimeError(("clean source alpha residue",key,clean_source_alpha))
    fmask=fa[y0:y1,x0:x1,3]>0
    lb0=bbox(fmask)
    if not lb0: raise RuntimeError(("no candidate alpha",key))
    lb=[x0+lb0[0],y0+lb0[1],x0+lb0[2],y0+lb0[3]]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("geometry",key,ob,lb,margins))
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    mask=np.zeros((H,W),bool); mask[lb[1]:lb[3],lb[0]:lb[2]]=fa[lb[1]:lb[3],lb[0]:lb[2],3]>0; final_masks.append(mask)
    rows.append({"key":key,"source":en,"korean":ko,"original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],"width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
      "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
      "clean_source_alpha_remaining":clean_source_alpha,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

diff=np.any(fa!=sa,axis=2); ad=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(diff&~allowed)); alpha_out=int(np.count_nonzero(ad&~allowed))
if outside or alpha_out: raise RuntimeError(("candidate outside exact source bboxes",outside,alpha_out))

overlap=0; touch=[]
for i in range(len(final_masks)):
  for j in range(i+1,len(final_masks)):
    overlap+=int(np.count_nonzero(final_masks[i]&final_masks[j]))
    dil=final_masks[i].copy()
    for dy in (-1,0,1):
      for dx in (-1,0,1):
        if dx==0 and dy==0: continue
        ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
        ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
        dil[ys,xs]|=final_masks[i][ys2,xs2]
    if np.any(dil&final_masks[j]): touch.append([rows[i]["key"],rows[j]["key"]])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))
if ImageChops.difference(fr.transpose(Image.Transpose.FLIP_TOP_BOTTOM),f).getbbox() is not None:
    raise RuntimeError("raw/readable parity")

def card(label,im):
    v=flat(im); v.thumbnail((1600,800),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),(25,25,25)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
cards=[card("SOURCE_READABLE",s),card("A151_CLEAN",clean),card("A151_FINAL",f)]
w=max(x.width for x in cards); hh=sum(x.height for x in cards); sheet=Image.new("RGB",(w,hh),(25,25,25)); y=0
for x in cards: sheet.paste(x,(0,y)); y+=x.height
sheet.save(out/"C227R_754_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

sf=flat(s); ff=flat(f); contacts=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=10; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    a=sf.crop(cr); b=ff.crop(cr); scale=max(1,min(2,round(1200/max(1,a.width))))
    a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST)
    b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(25,25,25)); d=ImageDraw.Draw(c)
    d.text((4,4),"SOURCE",fill="white"); d.text((a.width+10,4),"A151_FINAL",fill="white"); c.paste(a,(0,26)); c.paste(b,(a.width+6,26)); contacts.append(c)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+6*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for x in contacts: cs.paste(x,(0,y)); y+=x.height+6
cs.save(out/"C227R_754_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",sr),card("A151_RAW_MIRROR_Y",fr)]
rw=max(x.width for x in rawcards); rh=sum(x.height for x in rawcards); rs=Image.new("RGB",(rw,rh),(25,25,25)); y=0
for x in rawcards: rs.paste(x,(0,y)); y+=x.height
rs.save(out/"C227R_754_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

report={"schema_version":1,"role":"C","run":run,"qa_id":"C227R","queue_index":175,"asset":asset,
 "producer_run":"A151","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"pinned canonical BGRA/RGBA32 source independently decoded; three source/candidate alpha bboxes re-derived directly from broad semantic row regions; producer masks not consumed",
 "machine_status":"PASS","structure":sm,"rows":rows,
 "summary":{"bbox_size_positive_margin":"3/3 PASS","candidate_changed_outside_exact_source_bboxes":outside,
  "candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,"localized_pair_overlap_pixels":overlap,
  "localized_touch_pairs":touch,"header_128_exact":True,"raw_readable_parity":"PASS"},
 "visual_evidence":[str((out/"C227R_754_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
  str((out/"C227R_754_ROW_CONTACT.jpg").relative_to(repo)),str((out/"C227R_754_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER","runtime_validation":"UNTESTED",
 "vr_ffb_dx11_dxvk_changes":False}
(out/"C227R_754F0599_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C227R_754F0599.json").write_text(json.dumps({"role":"C","run":"C227","queue_index":175,"asset":asset,
 "candidate_sha256":EXPECTED,"machine_status":"PASS","report":str((out/"C227R_754F0599_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C227","status":"PASS","rows":rows,"summary":report["summary"]},ensure_ascii=False))
