#!/usr/bin/env python3
# B213: q128 12519155 manual PRE_INGAME visual rework.
# Fixes source-family alignment/scale false-negative: shared stage rows must keep
# one Korean vertical style and source-like left alignment instead of per-row
# centered/shrunk text. Fresh native Hangul only; no old Korean bitmap upscale.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA213-12519155"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/12519155_256x256.dds"
source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_C/20261005-C132-12519155/C132_CLEAN_PLATE.png"
EXPECTED_BEFORE="14bc44a69775206c5771023408d0752ee925542fda48359c14c4e5b2f767119d"
SOURCE_SHA="ad88efc25b705be8960f373f8a06ea88ce39f086857e68c851595f7c867c14c3"
ROWS=[
 {"n":1,"source":"Time Attack Mode / 15 C.","ko":"타임 어택 모드 / 15코스","bbox":[6,508,648,558],"stage":False},
 {"n":2,"source":"Alpine","ko":"알파인","bbox":[5,582,165,640],"stage":True},
 {"n":3,"source":"Ancient Ruins","ko":"에인션트 루인스","bbox":[5,660,362,708],"stage":True},
 {"n":4,"source":"Bay Area","ko":"베이 에어리어","bbox":[6,737,232,794],"stage":True},
 {"n":5,"source":"Big Forest","ko":"빅 포레스트","bbox":[6,810,256,868],"stage":True},
 {"n":6,"source":"Canyon","ko":"캐니언","bbox":[6,886,191,944],"stage":True},
 {"n":7,"source":"Cape Way","ko":"케이프 웨이","bbox":[6,962,258,1020],"stage":True},
]
STAGE_EXPECTED={"Alpine":"알파인","Ancient Ruins":"에인션트 루인스","Bay Area":"베이 에어리어","Big Forest":"빅 포레스트","Canyon":"캐니언","Cape Way":"케이프 웨이"}

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
if src.size!=(1024,1024): raise RuntimeError(("source size",src.size))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))
sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); oa=np.asarray(old,dtype=np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool); source_mask=np.zeros((H,W),bool)
for r in ROWS:
    x0,y0,x1,y1=r["bbox"]; allowed[y0:y1,x0:x1]=True
    source_mask[y0:y1,x0:x1]=sa[y0:y1,x0:x1,3]>0
if np.count_nonzero(np.any(ca!=sa,axis=2)&~source_mask): raise RuntimeError("C132 clean drift outside exact source alpha")
if np.count_nonzero(source_mask&(ca[:,:,3]>0)): raise RuntimeError("C132 clean still has source alpha")

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

def source_color(b):
    x0,y0,x1,y1=b; p=sa[y0:y1,x0:x1].reshape(-1,4); p=p[p[:,3]>8]
    if len(p)<10: return (57,54,46,255)
    # Source is a flat dark condensed label family. Use median visible RGB and full alpha.
    rgb=np.median(p[:,:3],axis=0).astype(int)
    return (int(rgb[0]),int(rgb[1]),int(rgb[2]),255)
palette=source_color(ROWS[1]["bbox"])

def source_slant(b):
    x0,y0,x1,y1=b; m=sa[y0:y1,x0:x1,3]>0
    ys=[]; left=[]
    for y in range(m.shape[0]):
        xs=np.flatnonzero(m[y])
        if len(xs)>=3:
            ys.append(y); left.append(float(np.percentile(xs,15)))
    if len(ys)<8: return 0.0
    slope=float(np.polyfit(np.asarray(ys),np.asarray(left),1)[0])
    return float(np.clip(-slope,-0.25,0.25))
stage_slants=[source_slant(r["bbox"]) for r in ROWS if r["stage"]]
shared_slant=float(np.median(stage_slants))
if abs(shared_slant)<0.025: shared_slant=0.0

def shear_right(im,s):
    if abs(s)<0.005: return im
    # top-vs-bottom readable displacement follows measured source sign.
    maxshift=int(np.ceil(abs(s)*max(1,im.height-1)))+4
    src2=Image.new("RGBA",(im.width+2*maxshift,im.height),(0,0,0,0)); src2.alpha_composite(im,(maxshift,0))
    dst=Image.new("RGBA",src2.size,(0,0,0,0))
    for y in range(src2.height):
        dx=int(round(s*(src2.height-1-y)))
        row=src2.crop((0,y,src2.width,y+1))
        dst.alpha_composite(row,(dx,y))
    bb=dst.getchannel("A").getbbox()
    if not bb: raise RuntimeError("empty shear")
    return dst.crop(bb)

def render_native(text,fs,stroke):
    f=ImageFont.truetype(FONT,fs)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+6
    size=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
    im=Image.new("RGBA",size,(0,0,0,0))
    pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(im).text(pos,text,font=f,fill=palette,stroke_width=stroke,stroke_fill=palette)
    bb=im.getchannel("A").getbbox()
    if not bb: raise RuntimeError(("empty render",text,fs))
    return im.crop(bb)

# Pick ONE shared native stage font size. Long Korean rows may use modest horizontal
# condensation to match the source condensed family, but vertical style stays shared.
stage_rows=[r for r in ROWS if r["stage"]]
shared=None
for fs in range(64,30,-1):
    stroke=max(1,round(fs*0.035))
    trial=[]; ok=True
    for r in stage_rows:
        t=shear_right(render_native(r["ko"],fs,stroke),shared_slant)
        x0,y0,x1,y1=r["bbox"]; aw=x1-x0-4; ah=y1-y0-4
        if t.height>ah: ok=False; break
        sx=min(1.0,aw/t.width)
        if sx<0.80: ok=False; break
        trial.append((r,t,sx))
    if ok:
        shared=(fs,stroke,trial); break
if shared is None: raise RuntimeError("no safe shared stage style")
stage_fs,stage_stroke,stage_trial=shared

# Header gets its own source-intentional smaller family but is maximized to the exact source bbox.
header=ROWS[0]; hx0,hy0,hx1,hy1=header["bbox"]; header_slant=source_slant(header["bbox"])
header_pick=None
for fs in range(60,28,-1):
    stroke=max(1,round(fs*0.035))
    t=shear_right(render_native(header["ko"],fs,stroke),header_slant)
    aw=hx1-hx0-4; ah=hy1-hy0-4
    if t.height<=ah:
        sx=min(1.0,aw/t.width)
        if sx>=0.88:
            header_pick=(fs,stroke,t,sx); break
if header_pick is None: raise RuntimeError("no safe header style")
header_fs,header_stroke,header_tile,header_sx=header_pick

final=clean.copy()
target=np.zeros((H,W),bool)
row_reports=[]
def place(r,tile,sx,fs,stroke,slant,family):
    x0,y0,x1,y1=r["bbox"]; sw=x1-x0; sh=y1-y0
    if sx<0.999:
        tile=tile.resize((max(1,round(tile.width*sx)),tile.height),Image.Resampling.LANCZOS)
        bb=tile.getchannel("A").getbbox()
        if bb: tile=tile.crop(bb)
    # Source family is left aligned. Keep a small positive 2px source-bbox margin.
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
    final.alpha_composite(layer); target[:] |= lm
    return {
      "n":r["n"],"source":r["source"],"korean":r["ko"],"stage_name":r["stage"],
      "original_bbox":r["bbox"],"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS",
      "font_family":"Noto Sans CJK KR Black","font_size":fs,"stroke_width":stroke,
      "shared_stage_style":family,"horizontal_scale":sx,"source_slant_measure":slant,
      "alignment":"LEFT_SOURCE_FAMILY","fresh_native_render":True,
      "edge_touch_high_risk":any(v==0 for v in [lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]])
    }

row_reports.append(place(header,header_tile,header_sx,header_fs,header_stroke,header_slant,"HEADER"))
for r,t,sx in stage_trial:
    row_reports.append(place(r,t,sx,stage_fs,stage_stroke,shared_slant,"STAGE_SHARED"))
row_reports.sort(key=lambda x:x["n"])

# Encode exact raw mirror-Y RGBA32 DDS.
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

# Zero-overlap/touch across localized rows.
row_masks=[target & rect_bool(target.shape,r["original_bbox"]) for r in row_reports]
overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
        near=int(np.count_nonzero(dil(row_masks[i],1)&row_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))

stage_policy=all((not r["stage_name"]) or STAGE_EXPECTED[r["source"]]==r["korean"] for r in row_reports)
if not stage_policy: raise RuntimeError("stage naming policy")
stage_heights=[r["localized_size"][1] for r in row_reports if r["stage_name"]]
if max(stage_heights)-min(stage_heights)>2: raise RuntimeError(("shared stage height drift",stage_heights))
if any(r["edge_touch_high_risk"] for r in row_reports): raise RuntimeError(("unexpected edge touch",row_reports))

# Compare old alignment/scale to new for the visual false-negative record.
old_alpha=np.asarray(old.getchannel("A"))>0
for rr in row_reports:
    rm=old_alpha & rect_bool(old_alpha.shape,rr["original_bbox"])
    rr["prior_localized_bbox"]=bbox_bool(rm)
    if rr["prior_localized_bbox"]:
        pb=rr["prior_localized_bbox"]
        rr["prior_delta_left"]=pb[0]-rr["original_bbox"][0]
        rr["left_alignment_gain_px"]=rr["prior_delta_left"]-rr["delta_left"]

# Evidence.
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im); c=Image.new("RGB",(v.width,v.height+28),(30,30,30)); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
cards=[card("SOURCE_READABLE",src),card("OLD_C132",old),card("C132_CLEAN",clean),card("B213_FINAL",new)]
sheet=Image.new("RGB",(2048,2104),(24,24,24))
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0)); sheet.paste(cards[2],(0,1052)); sheet.paste(cards[3],(1024,1052))
sheet.thumbnail((1800,1800),Image.Resampling.LANCZOS)
sheet.save(out/"B213_125_SOURCE_OLD_CLEAN_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)
rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("OLD_RAW_MIRROR_Y",old_raw),card("B213_RAW_MIRROR_Y",new_raw)]
rawsheet=Image.new("RGB",(1024,1052*3),(24,24,24))
for i,c in enumerate(rawcards): rawsheet.paste(c,(0,1052*i))
rawsheet.thumbnail((1200,2200),Image.Resampling.LANCZOS)
rawsheet.save(out/"B213_125_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

# Per-row SOURCE/OLD/NEW 2x contact.
src_rgb=comp(src); old_rgb=comp(old); new_rgb=comp(new)
contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[]
    for im in (src_rgb,old_rgb,new_rgb):
        z=im.crop(cr); z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST); ims.append(z)
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),(28,28,28)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","C132","B213"),ims):
        d.text((xx+4,5),lab,fill="white"); c.paste(z,(xx,28)); xx+=z.width+6
    contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(24,24,24)); yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+6
rowsheet.save(out/"B213_125_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B213","queue_index":128,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_ENGLISH_ORIGINAL_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/036_q128_12519155.jpg",
 "prior_c_status":"C132_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["SOURCE_LEFT_ALIGNMENT_MISMATCH","STAGE_FAMILY_SIZE_INCONSISTENCY","VISIBLE_UNDERSIZING"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"exact 1024 source + C132 exact clean plate -> fresh native Noto Sans CJK KR Black render; shared stage nominal font/weight; source-family left alignment; modest per-row horizontal condensation only when required by exact source width -> exact-header RGBA32 raw mirror-Y encode -> decoded strict QA",
 "shared_stage_style":{"font_family":"Noto Sans CJK KR Black","font_size":stage_fs,"stroke_width":stage_stroke,
                       "source_slant_measure":shared_slant,"localized_heights":stage_heights},
 "header_style":{"font_family":"Noto Sans CJK KR Black","font_size":header_fs,"stroke_width":header_stroke,
                 "source_slant_measure":header_slant,"horizontal_scale":header_sx},
 "rows":row_reports,
 "qa":{
   "header_128_exact_canonical":True,"raw_orientation":"mirror_y",
   "changed_pixels_outside_exact_source_bboxes":outside,
   "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,
   "protected_changed_pixels":protected,"source_residue_pixels":source_residue,
   "localized_overlap_pixels":overlap,"localized_touch_pairs":touch,
   "stage_naming_policy":"PASS","shared_stage_height_drift_px":max(stage_heights)-min(stage_heights),
   "fresh_native_render":"PASS_NO_PRIOR_KOREAN_BITMAP_UPSCALE",
   "readable_source_old_clean_new_visual_review":"PENDING_CONTROLLER",
   "raw_source_old_new_visual_review":"PENDING_CONTROLLER",
   "ordered_gate":{
      "plate_restoration":"PASS_INHERITED_C132_EXACT_CLEAN",
      "source_matching_slant_direction":"PASS_MEASURED_SOURCE_FAMILY",
      "no_unnecessary_undersizing":"REWORKED_PENDING_CONTROLLER_VISUAL",
      "source_faithful_weight_outline_shadow":"REWORKED_SHARED_BLACK_FAMILY_PENDING_CONTROLLER_VISUAL",
      "clipping":"PASS_MACHINE_CONTAINMENT",
      "protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX",
      "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
      "immediate_readability":"PENDING_CONTROLLER"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"B213_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B213_12519155_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B213_12519155.json").write_text(json.dumps({
 "role":"B","run":"B213","queue_index":128,"asset":asset,"candidate_sha256":after,
 "report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B213","before":EXPECTED_BEFORE,"after":after,"stage_fs":stage_fs,"stage_heights":stage_heights,"rows":row_reports,"status":report["status"]},ensure_ascii=False))
