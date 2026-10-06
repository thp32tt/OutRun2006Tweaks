#!/usr/bin/env python3
# B216: q132 1F5FE6E9 manual PRE_INGAME visual rework.
# Fixes prior C139 false-negative: Korean request-family labels are visibly
# undersized/light versus the English source family. Rebuild from the validated
# B55 clean plate using one shared native Hangul style; no old Korean bitmap upscale.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA216-1F5FE6E9"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION55/1F5_CLEAN_PLATE.png"
EXPECTED_BEFORE="e503bb29d87501453e3f0ba4b7b9528a4cc53a198a148845ea8cdad6c97ec6be"
SOURCE_SHA="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d"
ROWS=[
 {"n":1,"source":"REQUEST","ko":"요청","bbox":[641,140,744,160]},
 {"n":2,"source":"SPECIAL REQUEST 1","ko":"스페셜 요청 1","bbox":[641,164,861,184]},
 {"n":3,"source":"SPECIAL REQUEST 2","ko":"스페셜 요청 2","bbox":[641,188,865,208]},
 {"n":4,"source":"SPECIAL REQUEST 3","ko":"스페셜 요청 3","bbox":[641,211,865,232]},
]
FILL=(101,97,79,255)
HORIZONTAL_SCALE=1.25

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode_rgba(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
    if len(b)!=128+w*h*4: raise RuntimeError(("rgba32 size",w,h,m,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mipmaps":m,"format":"RGBA32","raw_orientation":"mirror_y"}
def bbox_bool(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect_bool(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def dil(m,px=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

with zipfile.ZipFile(source_zip) as z: sb=z.read(asset)
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha_bytes(sb)))
if sha_file(candidate)!=EXPECTED_BEFORE: raise RuntimeError(("candidate sha drift",sha_file(candidate),EXPECTED_BEFORE))
cb=candidate.read_bytes()
src_raw,src,meta=decode_rgba(sb); old_raw,old,old_meta=decode_rgba(cb)
if meta!=old_meta or cb[:128]!=sb[:128]: raise RuntimeError("candidate structure/header drift")
if src.size!=(1024,512): raise RuntimeError(("source size",src.size))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))

sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); oa=np.asarray(old,dtype=np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool); source_mask=np.zeros((H,W),bool)
for r in ROWS:
    x0,y0,x1,y1=r["bbox"]
    allowed[y0:y1,x0:x1]=True
    source_mask[y0:y1,x0:x1]=sa[y0:y1,x0:x1,3]>0

# The prior B55/C139 clean plate is exact-source validated. Recheck fail-closed.
if np.count_nonzero(np.any(ca!=sa,axis=2)&~source_mask):
    raise RuntimeError("validated clean plate drift outside exact source mask")
if np.count_nonzero(source_mask&(ca[:,:,3]>0)):
    raise RuntimeError("validated clean plate retains source alpha")

def font_black():
    q="Noto Sans CJK KR:style=Black"
    p=subprocess.check_output(["fc-match","-f","%{file}",q],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}",q],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        raise RuntimeError(("Noto Sans CJK KR unavailable",p))
    return p
FONT=font_black()

def render_text(text,fs):
    f=ImageFont.truetype(FONT,fs)
    probe=Image.new("L",(8,8),0); d=ImageDraw.Draw(probe)
    tb=d.textbbox((0,0),text,font=f,stroke_width=0)
    pad=4
    im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=FILL)
    bb=im.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty render",text,fs))
    return im.crop(bb)

# One shared source-family style. Find the largest shared native font that leaves
# at least a 1px vertical margin in all four exact source bboxes after 1.25x width scale.
shared=None
for fs in range(22,14,-1):
    trials=[]; ok=True
    for r in ROWS:
        t=render_text(r["ko"],fs)
        if HORIZONTAL_SCALE!=1.0:
            t=t.resize((max(1,round(t.width*HORIZONTAL_SCALE)),t.height),Image.Resampling.LANCZOS)
            bb=t.getchannel("A").getbbox()
            if bb: t=t.crop(bb)
        x0,y0,x1,y1=r["bbox"]; sw=x1-x0; sh=y1-y0
        if t.width>sw-2 or t.height>sh-2:
            ok=False; break
        trials.append((r,t))
    if ok:
        shared=(fs,trials); break
if shared is None: raise RuntimeError("no safe shared request-family style")
shared_fs,trials=shared

final=clean.copy()
target=np.zeros((H,W),bool)
row_reports=[]
for r,tile in trials:
    x0,y0,x1,y1=r["bbox"]; sw=x1-x0; sh=y1-y0
    px=x0+1
    py=y0+(sh-tile.height)//2
    if py<=y0: py=y0+1
    if py+tile.height>=y1: py=y1-1-tile.height
    layer=Image.new("RGBA",final.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox_bool(lm)
    if not lb: raise RuntimeError(("empty placed",r["n"]))
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if lb[0]<x0 or lb[1]<y0 or lb[2]>x1 or lb[3]>y1 or lw>sw or lh>sh:
        raise RuntimeError(("bbox ceiling",r["n"],r["bbox"],lb))
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin",r["n"],margins))
    final.alpha_composite(layer); target |= lm

    oldm=(oa[:,:,3]>0)&rect_bool((H,W),r["bbox"])
    oldb=bbox_bool(oldm)
    oldsz=None if oldb is None else [oldb[2]-oldb[0],oldb[3]-oldb[1]]
    row_reports.append({
      "n":r["n"],"source":r["source"],"korean":r["ko"],
      "original_bbox":r["bbox"],"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_family":"Noto Sans CJK KR Black","font_size":shared_fs,
      "horizontal_scale":HORIZONTAL_SCALE,"fill_rgba":list(FILL),
      "alignment":"LEFT_SOURCE_FAMILY","fresh_native_render":True,
      "prior_localized_bbox":oldb,"prior_localized_size":oldsz,
      "width_gain_px":None if oldsz is None else lw-oldsz[0],
      "height_gain_px":None if oldsz is None else lh-oldsz[1]
    })

# Exact raw mirror-Y RGBA32 DDS.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(payload)
after=sha_bytes(payload)
fb=candidate.read_bytes()
new_raw,new,new_meta=decode_rgba(fb)
if fb[:128]!=sb[:128] or new_meta!=meta: raise RuntimeError("header/meta regression")
if ImageChops.difference(new,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
na=np.asarray(new,dtype=np.uint8)

changed=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3])&~allowed))
protected=int(np.count_nonzero(changed&~allowed))
source_residue=int(np.count_nonzero(source_mask&(na[:,:,3]>0)&~dil(target,1)))
if outside or alpha_out or protected or source_residue:
    raise RuntimeError(("scope/residue",outside,alpha_out,protected,source_residue))

row_masks=[target & rect_bool((H,W),r["original_bbox"]) for r in row_reports]
overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
        near=int(np.count_nonzero(dil(row_masks[i],1)&row_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))

width_improved=sum(1 for x in row_reports if (x["width_gain_px"] or 0)>0)
height_not_smaller=sum(1 for x in row_reports if x["prior_localized_size"] and x["localized_size"][1]>=x["prior_localized_size"][1])
if width_improved!=4 or height_not_smaller!=4:
    raise RuntimeError(("scale improvement gate",width_improved,height_not_smaller))

def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im); c=Image.new("RGB",(v.width,v.height+28),(28,28,28)); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c

cards=[card("SOURCE_READABLE",src),card("C139_OLD",old),card("B55_CLEAN",clean),card("B216_FINAL",new)]
sheet=Image.new("RGB",(2048,1080),(24,24,24))
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0)); sheet.paste(cards[2],(0,540)); sheet.paste(cards[3],(1024,540))
sheet.thumbnail((1800,1100),Image.Resampling.LANCZOS)
sheet.save(out/"B216_1F5_SOURCE_OLD_CLEAN_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("C139_RAW_MIRROR_Y",old_raw),card("B216_RAW_MIRROR_Y",new_raw)]
rawsheet=Image.new("RGB",(3072,540),(24,24,24))
for i,c in enumerate(rawcards): rawsheet.paste(c,(1024*i,0))
rawsheet.thumbnail((2000,650),Image.Resampling.LANCZOS)
rawsheet.save(out/"B216_1F5_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

src_rgb=comp(src); old_rgb=comp(old); new_rgb=comp(new)
contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; p=5
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[]
    for im in (src_rgb,old_rgb,new_rgb):
        z=im.crop(cr); z=z.resize((z.width*4,z.height*4),Image.Resampling.NEAREST); ims.append(z)
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(28,28,28)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","C139","B216"),ims):
        d.text((xx+4,4),lab,fill="white"); c.paste(z,(xx,26)); xx+=z.width+6
    contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(24,24,24))
yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+6
rowsheet.save(out/"B216_1F5_ROW_CONTACT_4X.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B216","queue_index":132,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_ENGLISH_ORIGINAL_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/038_q132_1F5FE6E9.jpg",
 "prior_c_status":"C139_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["TEXT_SCALE_TOO_SMALL_VS_SOURCE","SOURCE_WEIGHT_HIERARCHY_TOO_WEAK"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"exact canonical 1024x512 RGBA32 source + prior B55/C139 validated clean plate -> one shared fresh native Noto Sans CJK KR Black family -> maximum shared positive-margin vertical fit + modest 1.25x horizontal source-family fit -> exact-header raw mirror-Y encode -> decoded strict QA",
 "shared_style":{"font_family":"Noto Sans CJK KR Black","font_size":shared_fs,"horizontal_scale":HORIZONTAL_SCALE,"fill_rgba":list(FILL)},
 "rows":row_reports,
 "qa":{
   "header_128_exact_canonical":True,"raw_orientation":"mirror_y",
   "changed_pixels_outside_exact_source_bboxes":outside,
   "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,
   "protected_changed_pixels":protected,"source_residue_pixels":source_residue,
   "localized_overlap_pixels":overlap,"localized_touch_pairs":touch,
   "width_improved_rows":width_improved,"height_not_smaller_rows":height_not_smaller,
   "fresh_native_render":"PASS_NO_PRIOR_KOREAN_BITMAP_UPSCALE",
   "readable_source_old_clean_new_visual_review":"PENDING_CONTROLLER",
   "raw_source_old_new_visual_review":"PENDING_CONTROLLER",
   "ordered_gate":{
      "plate_restoration":"PASS_INHERITED_B55_C139_VALIDATED_CLEAN_PLATE",
      "source_matching_slant_direction":"PASS_SHARED_UPRIGHT_SOURCE_FAMILY",
      "no_unnecessary_undersizing":"REWORKED_PENDING_CONTROLLER_VISUAL",
      "source_faithful_weight_outline_shadow":"REWORKED_BLACK_NO_INVENTED_OUTLINE_PENDING_CONTROLLER",
      "clipping":"PASS_MACHINE_POSITIVE_MARGIN",
      "protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX",
      "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
      "immediate_readability":"PENDING_CONTROLLER"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"B216_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B216_1F5FE6E9_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B216_1F5FE6E9.json").write_text(json.dumps({
 "role":"B","run":"B216","queue_index":132,"asset":asset,"candidate_sha256":after,
 "report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B216","before":EXPECTED_BEFORE,"after":after,"shared_fs":shared_fs,"width_improved":width_improved,"rows":row_reports,"status":report["status"]},ensure_ascii=False))
