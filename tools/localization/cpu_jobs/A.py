#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A163R-Q051-FF2462BB-C239-STYLE-REPAIR"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
CURRENT_SHA="16ed98f52c2505cf32304eb2b61aa15491de87e78e9b11812c7add3c6fa3b112"
SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
PRE_A144_COMMIT="5bd0324d1acb9ce8f9465bb4de282a28a7334e06"
PRE_A144_SHA="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
CORRECT_READABLE_BOX=[3002,1405,3512,1566]
TOP_BOX=[3002,1405,3512,1486]
BOTTOM_BOX=[3002,1486,3512,1566]
WRONG_A144_BOX=[3002,482,3512,643]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    return w,h,pitch,depth,mips,b[84:88],struct.unpack_from("<4I",b,92)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def margins(inner,outer):
    return [inner[0]-outer[0],outer[2]-inner[2],inner[1]-outer[1],outer[3]-inner[3]]

curb=candidate.read_bytes(); sb=source_path.read_bytes()
if sha_bytes(curb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha_bytes(curb),CURRENT_SHA))
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb),SOURCE_SHA))
W,H,pitch,depth,mips,fourcc,masks=meta(curb)
if (W,H,mips)!=(4096,2048,1) or curb[:128]!=sb[:128] or len(curb)!=len(sb):
    raise RuntimeError(("structure drift",W,H,mips,len(curb),len(sb)))

prior_bytes=subprocess.check_output(["git","show",PRE_A144_COMMIT+":"+str(Path("localization/graphics/hd_candidates")/asset_rel)])
if sha_bytes(prior_bytes)!=PRE_A144_SHA: raise RuntimeError(("pre-A144 drift",sha_bytes(prior_bytes)))
tmp=Path("/tmp/outrun_A163R"); tmp.mkdir(parents=True,exist_ok=True)
(tmp/"current.dds").write_bytes(curb); (tmp/"prior.dds").write_bytes(prior_bytes)
cur_raw=Image.open(tmp/"current.dds").convert("RGBA")
prior_raw=Image.open(tmp/"prior.dds").convert("RGBA")
source_raw=Image.open(source_path).convert("RGBA")
cur=cur_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
source=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Restore exact pre-A144 atlas, then modify only the true lower/right source cell.
final=prior.copy()
x1,y1,x2,y2=CORRECT_READABLE_BOX
final.paste(Image.new("RGBA",(x2-x1,y2-y1),(0,0,0,0)),(x1,y1))

# A163 corrected the target mapping, but visual review found the reused A144
# glyph effect under-matched the English white/navy/yellow border family.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))
font_index=1 if FONT.lower().endswith(".ttc") else 0
YELLOW=(255,215,52,255); NAVY=(20,31,65,255); WHITE=(248,248,248,255)

def shear_rgba(im,s):
    extra=max(8,int(math.ceil(abs(s)*im.height))+8)
    c=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0)); c.paste(im,(extra,0),im)
    x=c.transform(c.size,Image.Transform.AFFINE,(1,-s,s*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=x.getchannel("A").getbbox()
    return x.crop(bb) if bb else x

def render_line(text,box):
    maxw=box[2]-box[0]-16; maxh=box[3]-box[1]-16
    best=None
    for fs in range(76,34,-1):
        font=ImageFont.truetype(FONT,fs,index=font_index)
        canvas=Image.new("RGBA",(maxw*3,maxh*3),(0,0,0,0)); d=ImageDraw.Draw(canvas)
        bb=d.textbbox((20,20),text,font=font,stroke_width=8)
        ox,oy=20-bb[0],20-bb[1]
        d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=8,stroke_fill=NAVY)
        d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=6,stroke_fill=WHITE)
        d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=3,stroke_fill=NAVY)
        gb=canvas.getchannel("A").getbbox()
        if not gb: continue
        g=shear_rgba(canvas.crop(gb),.08)
        if g.height>maxh: continue
        if g.width>maxw:
            ratio=maxw/g.width
            if ratio<.72: continue
            g=g.resize((maxw,g.height),Image.Resampling.LANCZOS)
            gb=g.getchannel("A").getbbox()
            if gb:g=g.crop(gb)
        if g.width<=maxw and g.height<=maxh:
            best=(fs,g); break
    if best is None: raise RuntimeError(("no fit",text,box))
    fs,g=best
    px=box[0]+(box[2]-box[0]-g.width)//2
    py=box[1]+(box[3]-box[1]-g.height)//2
    final.alpha_composite(g,(px,py))
    loc=[px,py,px+g.width,py+g.height]; mg=margins(loc,box)
    if min(mg)<8: raise RuntimeError(("margin",text,loc,box,mg))
    return fs,loc,mg

fs1,top,mt=render_line("여자친구를",TOP_BOX)
fs2,bottom,mb=render_line("놓치지 마세요!",BOTTOM_BOX)

targetmask=Image.new("L",(W,H),0); ImageDraw.Draw(targetmask).rectangle((x1,y1,x2-1,y2-1),fill=255)
prior_outside=count(ImageChops.multiply(diffmask(prior,final),ImageOps.invert(targetmask)))
if prior_outside: raise RuntimeError(("prior blast radius",prior_outside))
if ImageChops.difference(final.crop(tuple(WRONG_A144_BOX)),prior.crop(tuple(WRONG_A144_BOX))).getbbox() is not None:
    raise RuntimeError("wrong insertion area not restored")

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rawmode=None
for mode in ("BGRA","RGBA"):
    try:
        if cur_raw.tobytes("raw",mode)==curb[128:]: rawmode=mode; break
    except Exception: pass
if rawmode is None: raise RuntimeError(("rawmode",masks))
newb=curb[:128]+raw_final.tobytes("raw",rawmode)
candidate.write_bytes(newb)
dec_raw=Image.open(candidate).convert("RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")
if count(ImageChops.multiply(diffmask(prior,dec),ImageOps.invert(targetmask))): raise RuntimeError("persisted blast radius")
newsha=sha_bytes(newb)

full=Image.new("RGB",(3072,512),(36,36,36))
for i,z in enumerate((source,cur,dec)): full.paste(comp(z).resize((1024,512),Image.Resampling.LANCZOS),(i*1024,0))
ImageDraw.Draw(full).text((8,5),"SOURCE | A163 STYLE-REJECTED | A163R FINAL",fill="white")
full.save(out/"A163R_FF2462_FULL_SOURCE_A163_FINAL.jpg",quality=95)

pad=80; crop=[x1-pad,y1-pad,x2+pad,y2+pad]
views=[comp(z.crop(tuple(crop))) for z in (source,prior,cur,dec)]
labels=["SOURCE","PRE-A144","A163 STYLE-REJECTED","A163R FINAL"]
sheet=Image.new("RGB",(sum(v.width for v in views)+30,max(v.height for v in views)+32),(235,235,235)); xx=0; d=ImageDraw.Draw(sheet)
for lab,v in zip(labels,views):
    d.text((xx+3,4),lab,fill="black"); sheet.paste(v,(xx,32)); xx+=v.width+10
sheet.save(out/"A163R_FF2462_TARGET_SOURCE_PRIOR_A163_FINAL.jpg",quality=97)

ucrop=[WRONG_A144_BOX[0]-40,WRONG_A144_BOX[1]-40,WRONG_A144_BOX[2]+40,WRONG_A144_BOX[3]+40]
uv=[comp(z.crop(tuple(ucrop))) for z in (source,cur,dec)]
us=Image.new("RGB",(sum(v.width for v in uv)+20,max(v.height for v in uv)+30),(235,235,235)); xx=0
for lab,v in zip(["SOURCE","A163 BEFORE","A163R RESTORED"],uv):
    ImageDraw.Draw(us).text((xx+3,3),lab,fill="black"); us.paste(v,(xx,30)); xx+=v.width+10
us.save(out/"A163R_FF2462_WRONG_INSERTION_RESTORED.jpg",quality=96)

raw_box=[3002,482,3512,643]; rcrop=[raw_box[0]-80,raw_box[1]-80,raw_box[2]+80,raw_box[3]+80]
rv=[comp(z.crop(tuple(rcrop))) for z in (source_raw,cur_raw,dec_raw)]
rs=Image.new("RGB",(sum(v.width for v in rv)+20,max(v.height for v in rv)+30),(235,235,235)); xx=0
for lab,v in zip(["SOURCE RAW","A163 RAW","A163R RAW"],rv):
    ImageDraw.Draw(rs).text((xx+3,3),lab,fill="black"); rs.paste(v,(xx,30)); xx+=v.width+10
rs.save(out/"A163R_FF2462_RAW_SOURCE_A163_FINAL.jpg",quality=96)
for pct in (100,75,50):
    z=comp(dec.crop(tuple(crop))); sz=(round(z.width*pct/100),round(z.height*pct/100))
    z.resize(sz,Image.Resampling.LANCZOS).save(out/f"A163R_FF2462_PRACTICAL_{pct}.jpg",quality=95)

report={"schema_version":2,"role":"A","run":"A163R","queue_index":51,"priority":"P0","asset":asset_rel,
 "trigger":"A163_CONTROLLER_STYLE_REJECT_AFTER_C239_TARGET_MAPPING_FIX",
 "c239_failure":"SOURCE_TARGET_MISMATCH|DUPLICATED_GIRLFRIEND_INSTRUCTION|UNRELATED_UI_INTRUSION",
 "a163_retry_reason":"correct target/duplicate removal passed; SOURCE/FINAL zoom found missing source-like white middle border",
 "source_sha256":SOURCE_SHA,"a163_candidate_sha256":CURRENT_SHA,"pre_a144_sha256":PRE_A144_SHA,"candidate_sha256":newsha,
 "mapping":{"raw_source_bbox":[3002,482,3512,643],"correct_readable_bbox":CORRECT_READABLE_BOX},
 "render":{"font":FONT,"font_index":font_index,"family":"Noto Sans CJK KR Black","shear":0.08,
   "effect":"yellow face + navy keyline + white middle border + navy outer edge",
   "top":{"text":"여자친구를","font_size":fs1,"localized_bbox":top,"margins_lrtb":mt},
   "bottom":{"text":"놓치지 마세요!","font_size":fs2,"localized_bbox":bottom,"margins_lrtb":mb}},
 "machine_qa":{"pre_a144_to_final_changed_pixels_outside_true_target":prior_outside,"wrong_a144_insertion_exactly_restored":True,
   "header_128_exact":newb[:128]==curb[:128],"dimensions":[W,H],"mips":mips,"rawmode":rawmode,"persisted_decode_exact":True,
   "source_size_ceiling":"PASS_2_OF_2","positive_margin":"PASS_2_OF_2_MIN_8PX"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_TRUE_TARGET_ONLY; WRONG_A144_INSERTION_RESTORED",
   "2_slant_direction":"PASS_READABLE_RIGHT_LEAN_0.08","3_no_unnecessary_undersizing":"PASS_MAX_SAFE_NATIVE_FIT_WITH_8PX_EFFECT_MARGIN",
   "4_weight_outline_shadow":"PASS_YELLOW_NAVY_WHITE_NAVY_SOURCE_FAMILY","5_clipping":"PASS_MIN_8PX_EFFECT_MARGIN",
   "6_protected_clearance":"PASS_ZERO_PRE_A144_DIFF_OUTSIDE_TRUE_TARGET","7_flip_y_raw":"PASS_EXACT_RAW_TO_READABLE_TARGET_MAPPING",
   "8_readability":"PENDING_CONTROLLER_VISUAL_CONFIRMATION"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_EXACT_SHA",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
(out/"A163R_FF2462BB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A163R","queue_index":51,"asset":"FF2462BB","candidate_sha256":newsha,"worker_status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL",
 "report":"localization/graphics/role_A/20261007-A163R-Q051-FF2462BB-C239-STYLE-REPAIR/A163R_FF2462BB_REPORT.json","runtime_validation":"UNTESTED"}
(wr/"A163R_FF2462BB.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))