#!/usr/bin/env python3
# B220: q164 5B65E08C PRE_INGAME hierarchy/alignment rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA220-5B65E08C"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261004-B-PRODUCTION20/5B65E08C_CLEAN_PLATE.png"
EXPECTED_BEFORE="33da77625f6b6af22cab72db30394b6b8c0bdd78e9f9a6166f273d6fab4da609"
SOURCE_SHA="5ca485fc5bcad59ba4d23225a951660a5009c436cac23b590946cb1a64e4634e"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds"
tmp=Path("/tmp/b220"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

bbox_src=[590,565,1493,659]
source_text="SELECT LICENSE"; korean="라이선스 선택"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,1024) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"raw_mode":mode}
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size drift",clean.size,src.size))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fl=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=fl.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Black unavailable",fl))

x0,y0,x1,y1=bbox_src; sw=x1-x0; sh=y1-y0
MARGIN=2

def render_native(fs):
    font=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(4,4),0))
    tb=d.textbbox((0,0),korean,font=font,stroke_width=0)
    pad=12
    m=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0)
    ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),korean,font=font,fill=255)
    b=m.getbbox()
    return m.crop(b)

best=None
for fs in range(140,40,-1):
    m=render_native(fs)
    if m.height<=sh-2*MARGIN:
        best=(fs,m); break
if best is None: raise RuntimeError("fit failed")
fs,mask=best
target_w=min(sw-2*MARGIN, max(mask.width, round(sw*0.80)))
mask=mask.resize((target_w,mask.height),Image.Resampling.LANCZOS)
tile=Image.new("RGBA",mask.size,(255,255,255,255)); tile.putalpha(mask)
px=x0+MARGIN
py=y0+(sh-tile.height)//2
if py<=y0: py=y0+MARGIN
if py+tile.height>=y1: py=y1-MARGIN-tile.height

# Preserve source outside exact source bbox; use validated clean only inside it.
final=src.copy()
final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
final.alpha_composite(layer)
lm=np.asarray(layer.getchannel("A"))>0
lb=bb(lm); margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
if min(margins)<=0: raise RuntimeError(("margin fail",lb,margins))
if lb[2]-lb[0]>sw or lb[3]-lb[1]>sh: raise RuntimeError("size ceiling fail")

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
after=sha(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip failure")
sa=np.asarray(src); na=np.asarray(new)
allowed=np.zeros((meta["h"],meta["w"]),bool); allowed[y0:y1,x0:x1]=True
diff=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3]) & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))

old_arr=np.asarray(old)
oldmask=(old_arr[:,:,3]>0)&allowed
oldbb=bb(oldmask)
oldsize=None if oldbb is None else [oldbb[2]-oldbb[0],oldbb[3]-oldbb[1]]
newsize=[lb[2]-lb[0],lb[3]-lb[1]]
if newsize[0] < 680: raise RuntimeError(("insufficient hierarchy gain",newsize))

def comp(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255)); bg.alpha_composite(im); return bg.convert("RGB")
def card(label,im):
    c=Image.new("RGB",(1024,540),(25,25,25))
    v=comp(im).resize((1024,512),Image.Resampling.LANCZOS); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
cards=[card("SOURCE",src),card("C108",old),card("C108 CLEAN",clean),card("B220 SOURCE-LEFT WIDE",new)]
sheet=Image.new("RGB",(2048,1080),(22,22,22))
sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(1024,0));sheet.paste(cards[2],(0,540));sheet.paste(cards[3],(1024,540))
sheet.save(out/"B220_5B65_SOURCE_C108_CLEAN_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

crop=(max(0,x0-20),max(0,y0-20),min(meta["w"],x1+20),min(meta["h"],y1+20))
src_c,old_c,new_c=comp(src).crop(crop),comp(old).crop(crop),comp(new).crop(crop)
contact=Image.new("RGB",(src_c.width+old_c.width+new_c.width+12,max(src_c.height,old_c.height,new_c.height)+30),(25,25,25))
d=ImageDraw.Draw(contact); xx=0
for lab,z in (("SOURCE",src_c),("C108",old_c),("B220",new_c)):
    d.text((xx+4,5),lab,fill="white"); contact.paste(z,(xx,28)); xx+=z.width+6
contact.save(out/"B220_5B65_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawsheet=Image.new("RGB",(2048,540),(22,22,22)); rawsheet.paste(card("SOURCE RAW",src_raw),(0,0)); rawsheet.paste(card("B220 RAW",new_raw),(1024,0))
rawsheet.save(out/"B220_5B65_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B220","queue_index":164,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/024_q164_5B65E08C.jpg",
 "prior_c_status":"C108_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["TEXT_WIDTH_HIERARCHY_UNDERSIZED","SOURCE_LEFT_ALIGNMENT_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"exact pinned native-HD source + previously C-validated clean plate; fresh native Noto Sans CJK KR Black; 0.80 source-width target from native glyph raster; source-left 2px anchor; plain white source family",
 "row":{"source":source_text,"korean":korean,"source_bbox":bbox_src,"source_size":[sw,sh],
   "prior_localized_bbox":oldbb,"prior_localized_size":oldsize,"localized_bbox":lb,"localized_size":newsize,
   "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":fs,
   "horizontal_source_width_ratio":round(newsize[0]/sw,4),"alignment":"source_left"},
 "machine_qa":{"bbox_size_positive_margin":"1/1 PASS","changed_outside_exact_source_bbox":outside,
   "alpha_changed_outside_exact_source_bbox":alpha_out,"header_128_exact":True,"raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_INHERITED_C106_C108_VALIDATED_CLEAN",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT",
   "3_no_unnecessary_undersizing":"PASS_WIDTH_HIERARCHY_MATERIALLY_INCREASED",
   "4_source_weight_effect":"PASS_NATIVE_BLACK_PLAIN_WHITE",
   "5_no_clipping":"PASS_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_FINAL_CHANGE_OUTSIDE_EXACT_SOURCE_BBOX",
   "7_flip_y_raw":"PASS_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B220_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B220_5B65E08C_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B220_5B65E08C.json").write_text(json.dumps({"role":"B","run":"B220","queue_index":164,"asset":asset,
 "candidate_sha256":after,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B220","before":EXPECTED_BEFORE,"after":after,"old_size":oldsize,"new_size":newsize,"bbox":lb,"margins":margins,"font_size":fs,"status":report["status"]},ensure_ascii=False))
