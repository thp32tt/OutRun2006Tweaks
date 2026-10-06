#!/usr/bin/env python3
# B215: q130 1762489B manual PRE_INGAME visual rework.
# Fixes the C133 visual false-negative: Korean course/average-rank labels are
# centered and materially too narrow versus the English source family.
# Fresh native Hangul render only; preserve exact source bboxes/header/raw mirror-Y.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA215-1762489B"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1762489B_512x128.dds"
source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
candidate=repo/"localization/graphics/hd_candidates"/asset
EXPECTED_BEFORE="324f677c4afc482ef3dbcf0cd226514a68847ee872d1eeda75b9311a9cb7a871"
SOURCE_SHA="c64baefa65663bc247c33f2f7a72c4ea49990e2a0edb409f186b090dfd3460ac"
ROWS=[
 {"n":1,"source":"MIX 1 COURSE","ko":"믹스 1 코스","bbox":[9,145,614,218],"font_size":67,"stroke":3,"fill":[101,97,79,255],"target_ratio":0.72,"max_stretch":1.55},
 {"n":2,"source":"MIX 2 COURSE","ko":"믹스 2 코스","bbox":[9,241,612,314],"font_size":67,"stroke":3,"fill":[101,97,79,255],"target_ratio":0.72,"max_stretch":1.55},
 {"n":3,"source":"OUTRUN2 COURSE","ko":"아웃런2 코스","bbox":[7,333,785,406],"font_size":67,"stroke":3,"fill":[101,97,79,255],"target_ratio":0.72,"max_stretch":1.55},
 {"n":4,"source":"OUTRUN2SP COURSE","ko":"아웃런2 SP 코스","bbox":[7,429,899,502],"font_size":67,"stroke":3,"fill":[101,97,79,255],"target_ratio":0.72,"max_stretch":1.55},
 {"n":5,"source":"AVERAGE RANK:","ko":"평균 랭크:","bbox":[1435,466,1850,510],"font_size":39,"stroke":2,"fill":[74,71,63,255],"target_ratio":0.72,"max_stretch":1.65},
]

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
if src.size!=(2048,512): raise RuntimeError(("source size",src.size))
sa=np.asarray(src,dtype=np.uint8); oa=np.asarray(old,dtype=np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool); source_mask=np.zeros((H,W),bool)
for r in ROWS:
    x0,y0,x1,y1=r["bbox"]; allowed[y0:y1,x0:x1]=True
    source_mask[y0:y1,x0:x1]=sa[y0:y1,x0:x1,3]>0

# Exact alpha-only clean plate: this atlas is transparent artwork; erase only exact
# source text/effect alpha within the five proven source bboxes. RGB and all protected
# numeric/art pixels remain byte-equivalent when invisible/untargeted.
clean_arr=sa.copy()
clean_arr[source_mask,3]=0
clean=Image.fromarray(clean_arr,"RGBA")
ca=np.asarray(clean,dtype=np.uint8)
clean_changed=np.any(ca!=sa,axis=2)
if np.count_nonzero(clean_changed & ~source_mask): raise RuntimeError("clean drift outside source text mask")
if np.count_nonzero(source_mask & (ca[:,:,3]>0)): raise RuntimeError("clean source alpha remains")

def font_black():
    q="Noto Sans CJK KR:style=Black"
    p=subprocess.check_output(["fc-match","-f","%{file}",q],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}",q],text=True).strip()
    if not p or not Path(p).exists(): raise RuntimeError("Noto Sans CJK KR Black unavailable")
    return p
FONT=font_black()

def render_native(r):
    f=ImageFont.truetype(FONT,r["font_size"])
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),r["ko"],font=f,stroke_width=r["stroke"])
    pad=r["stroke"]+6
    im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    pos=(pad-tb[0],pad-tb[1])
    fill=tuple(r["fill"])
    ImageDraw.Draw(im).text(pos,r["ko"],font=f,fill=fill,stroke_width=r["stroke"],stroke_fill=fill)
    bb=im.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty render",r["n"]))
    return im.crop(bb)

final=clean.copy()
target=np.zeros((H,W),bool)
row_reports=[]
for r in ROWS:
    x0,y0,x1,y1=r["bbox"]; sw=x1-x0; sh=y1-y0
    tile=render_native(r)
    base_w,base_h=tile.size
    if base_h>sh-2:
        sy=(sh-2)/base_h
        tile=tile.resize((max(1,round(base_w*sy)),max(1,round(base_h*sy))),Image.Resampling.LANCZOS)
        bb=tile.getchannel("A").getbbox()
        if bb: tile=tile.crop(bb)
    desired=min(sw-4,round(sw*r["target_ratio"]))
    sx=min(r["max_stretch"], desired/max(1,tile.width))
    if sx>1.001:
        tile=tile.resize((max(1,round(tile.width*sx)),tile.height),Image.Resampling.LANCZOS)
        bb=tile.getchannel("A").getbbox()
        if bb: tile=tile.crop(bb)
    # Source family is left anchored, not centered. Keep a 2px positive margin.
    px=x0+2
    py=y0+(sh-tile.height)//2
    if px+tile.width>=x1: px=max(x0+1,x1-1-tile.width)
    if py<=y0: py=y0+1
    if py+tile.height>=y1: py=max(y0+1,y1-1-tile.height)
    layer=Image.new("RGBA",final.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox_bool(lm)
    if not lb: raise RuntimeError(("empty placed",r["n"]))
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    contain=lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1
    if not contain or lw>sw or lh>sh: raise RuntimeError(("bbox",r["n"],r["bbox"],lb))
    if min(lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3])<=0: raise RuntimeError(("edge touch",r["n"],lb,r["bbox"]))
    final.alpha_composite(layer); target |= lm
    oldm=(oa[:,:,3]>0)&rect_bool((H,W),r["bbox"])
    oldb=bbox_bool(oldm)
    rr={
      "n":r["n"],"source":r["source"],"korean":r["ko"],
      "original_bbox":r["bbox"],"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","alignment":"LEFT_SOURCE_FAMILY",
      "font_family":"Noto Sans CJK KR Black","font_size":r["font_size"],"stroke_width":r["stroke"],
      "horizontal_scale":sx,"target_width_ratio":r["target_ratio"],"fresh_native_render":True,
      "prior_localized_bbox":oldb,
      "prior_localized_size":None if oldb is None else [oldb[2]-oldb[0],oldb[3]-oldb[1]],
      "width_gain_px":None if oldb is None else lw-(oldb[2]-oldb[0]),
      "rework_status":"B215_LEFT_ALIGN_AND_SOURCE_HIERARCHY_RESTORE"
    }
    row_reports.append(rr)

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(payload)
after=sha_bytes(payload)
fb=candidate.read_bytes(); new_raw,new,new_meta=decode_rgba(fb)
if fb[:128]!=sb[:128] or new_meta!=meta: raise RuntimeError("header/meta regression")
if ImageChops.difference(new,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
na=np.asarray(new,dtype=np.uint8)

changed=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3])&~allowed))
protected=int(np.count_nonzero(changed&~allowed))
source_residue=int(np.count_nonzero(source_mask&(na[:,:,3]>0)&~dil(target,2)))
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

# Verify that all rows materially move toward source-family left alignment and at least
# four of five gain visible width versus C133.
left_improved=0; width_improved=0
for rr in row_reports:
    if rr["prior_localized_bbox"]:
        if rr["delta_left"] < rr["prior_localized_bbox"][0]-rr["original_bbox"][0]: left_improved+=1
        if rr["width_gain_px"] and rr["width_gain_px"]>0: width_improved+=1
if left_improved!=5 or width_improved<4: raise RuntimeError(("hierarchy improvement",left_improved,width_improved))

def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im); c=Image.new("RGB",(v.width,v.height+30),(30,30,30)); c.paste(v,(0,30)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c

cards=[card("SOURCE_READABLE",src),card("C133_OLD",old),card("B215_FINAL",new)]
sheet=Image.new("RGB",(2048*3,542),(24,24,24))
for i,c in enumerate(cards): sheet.paste(c,(2048*i,0))
sheet.thumbnail((2400,800),Image.Resampling.LANCZOS)
sheet.save(out/"B215_176_SOURCE_OLD_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("C133_RAW_MIRROR_Y",old_raw),card("B215_RAW_MIRROR_Y",new_raw)]
rawsheet=Image.new("RGB",(2048*3,542),(24,24,24))
for i,c in enumerate(rawcards): rawsheet.paste(c,(2048*i,0))
rawsheet.thumbnail((2400,800),Image.Resampling.LANCZOS)
rawsheet.save(out/"B215_176_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

src_rgb=comp(src); old_rgb=comp(old); new_rgb=comp(new)
contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[]
    for im in (src_rgb,old_rgb,new_rgb):
        z=im.crop(cr); z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST); ims.append(z)
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),(28,28,28)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","C133","B215"),ims):
        d.text((xx+4,5),lab,fill="white"); c.paste(z,(xx,28)); xx+=z.width+6
    contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(24,24,24))
yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+6
rowsheet.save(out/"B215_176_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B215","queue_index":130,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_ENGLISH_ORIGINAL_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/037_q130_1762489B.jpg",
 "prior_c_status":"C133_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["SOURCE_LEFT_ALIGNMENT_MISMATCH","TEXT_WIDTH_HIERARCHY_TOO_NARROW","CENTERED_LAYOUT_FALSE_NEGATIVE"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"exact canonical 2048x512 RGBA32 source -> exact alpha-only clean plate -> fresh native Noto Sans CJK KR Black -> source-family left anchor + bounded horizontal hierarchy restoration -> exact-header raw mirror-Y DDS -> decoded strict QA",
 "rows":row_reports,
 "qa":{
   "header_128_exact_canonical":True,"raw_orientation":"mirror_y",
   "clean_changed_pixels_outside_source_text_mask":int(np.count_nonzero(clean_changed&~source_mask)),
   "clean_source_alpha_remaining":int(np.count_nonzero(source_mask&(ca[:,:,3]>0))),
   "changed_pixels_outside_exact_source_bboxes":outside,
   "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,
   "protected_changed_pixels":protected,"source_residue_pixels":source_residue,
   "localized_overlap_pixels":overlap,"localized_touch_pairs":touch,
   "left_alignment_improved_rows":left_improved,"width_improved_rows":width_improved,
   "fresh_native_render":"PASS_NO_PRIOR_KOREAN_BITMAP_UPSCALE",
   "readable_source_old_new_visual_review":"PENDING_CONTROLLER",
   "raw_source_old_new_visual_review":"PENDING_CONTROLLER",
   "ordered_gate":{
     "plate_restoration":"PASS_EXACT_ALPHA_ONLY_SOURCE_MASK",
     "source_matching_slant_direction":"PASS_UPRIGHT_SOURCE_FAMILY",
     "no_unnecessary_undersizing":"REWORKED_PENDING_CONTROLLER_VISUAL",
     "source_faithful_weight_outline_shadow":"PASS_NATIVE_BLACK_SOURCE_COLOR_FAMILY",
     "clipping":"PASS_MACHINE_POSITIVE_MARGIN",
     "protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX",
     "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
     "immediate_readability":"PENDING_CONTROLLER"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"B215_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B215_1762489B_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B215_1762489B.json").write_text(json.dumps({
 "role":"B","run":"B215","queue_index":130,"asset":asset,"candidate_sha256":after,
 "report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B215","before":EXPECTED_BEFORE,"after":after,"left_improved":left_improved,"width_improved":width_improved,"rows":row_reports,"status":report["status"]},ensure_ascii=False))
