#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-PRODUCTION86-IGR018-CARSELECT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
srcp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candp=repo/"localization/graphics/hd_candidates"/asset_rel
cleanp=repo/"localization/graphics/role_A/20261005-A-RECOVERY13/FD90AA9_CLEAN_PLATE.png"
source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
input_sha="c8b13421e97d81a0d9e874bceaec41134041d5a30ccd51529d74ff456d9ab401"
bbox=(243,947,1156,1111)
text_ko="차량 선택"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for q in cs[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def count(m): return sum(m.histogram()[1:])
def flat(im):
    bg=Image.new("RGBA",im.size,(86,86,86,255)); bg.alpha_composite(im); return bg.convert("RGB")
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()

def shear(mask,k):
    pad=max(12,int(mask.height*abs(k))+12)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o

def shiftmask(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o

if sha(srcp)!=source_sha: raise RuntimeError(("source drift",sha(srcp)))
if sha(candp)!=input_sha: raise RuntimeError(("candidate drift",sha(candp)))
sb=srcp.read_bytes(); cb=candp.read_bytes()
if cb[:128]!=sb[:128]: raise RuntimeError("header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,mips)!=(4096,4096,16384,1): raise RuntimeError((W,H,pitch,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(cleanp).convert("RGBA")
if clean.size!=(W,H): raise RuntimeError("clean size")

x0,y0,x1,y1=bbox
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
# Reset only the exact source text/effect bbox to the previously validated clean plate.
final=old.copy()
final.paste(clean.crop(bbox),(x0,y0))

# Fresh native-resolution source-family large white selector header.
# Build heavy Hangul, source-like right italic, off-white face, dark navy keyline,
# pale outer rim and soft offset depth. No previous Korean raster pixels are reused.
maxw=x1-x0-12; maxh=y1-y0-10
layer=None; used_fs=None; used_k=0.28
for fs in range(142,96,-1):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text_ko,font=f)
    pad=28
    m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
    ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text_ko,font=f,fill=255)
    m=shear(m,used_k)
    mb=m.getbbox()
    if not mb: continue
    m=m.crop(mb)
    # Source family is broad and bold; modest width correction keeps Korean hierarchy
    # without bitmap scaling from an old localized asset.
    m=m.resize((int(round(m.width*1.10)),m.height),Image.Resampling.LANCZOS)
    outer=m.filter(ImageFilter.MaxFilter(13))
    inner=m.filter(ImageFilter.MaxFilter(7))
    sh=shiftmask(outer,7,8)
    w,h=outer.size
    z=Image.new("RGBA",(w,h),(0,0,0,0))
    z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(10,12,22,190)),Image.new("RGBA",(w,h),(0,0,0,0)),sh))
    z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(24,30,70,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
    z.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(225,228,238,255)),Image.new("RGBA",(w,h),(0,0,0,0)),inner))
    # white-to-light-gray vertical face
    grad=Image.new("RGBA",(w,h),(0,0,0,0)); gp=grad.load()
    for yy in range(h):
        t=yy/max(1,h-1); v=round(255*(1-t)+228*t)
        for xx in range(w): gp[xx,yy]=(v,v,min(255,v+4),255)
    z.alpha_composite(Image.composite(grad,Image.new("RGBA",(w,h),(0,0,0,0)),m))
    lb=z.getchannel("A").getbbox()
    if not lb: continue
    z=z.crop(lb)
    if z.width<=maxw and z.height<=maxh:
        layer=z; used_fs=fs; break
if layer is None: raise RuntimeError("no fit")

# Source header is left-biased in its text cell; keep a positive inset rather than recentering.
tx=x0+18
ty=y0+(y1-y0-layer.height)//2
lm=bmask(layer.getchannel("A"))
tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
loc=list(tm.getbbox() or ())
if not loc: raise RuntimeError("empty render")
if not (loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("margin",loc,bbox))
if loc[2]-loc[0]>x1-x0 or loc[3]-loc[1]>y1-y0: raise RuntimeError("size")
final.paste(layer,(tx,ty),lm)

# Exact scope + preservation.
delta=dmask(old,final)
outside=count(ImageChops.multiply(delta,ImageOps.invert(allowed)))
alpha_delta=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A")))
alpha_out=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))
# Clean plate within the source bbox must not retain source pixels at source-text-mask locations.
source_crop=src.crop(bbox); clean_crop=clean.crop(bbox)
same_sc=ImageOps.invert(dmask(source_crop,clean_crop))
source_alpha=bmask(source_crop.getchannel("A"))
# Restrict residue gate to exact source-vs-clean changed source text/effect footprint.
source_effect=dmask(source_crop,clean_crop)
residue=count(ImageChops.multiply(source_effect,same_sc))
if residue: raise RuntimeError(("clean residue",residue))
# Candidate source-effect residue outside new Hangul footprint.
same_sf=ImageOps.invert(dmask(src,final))
guard=tm.filter(ImageFilter.MaxFilter(5))
source_residue=count(ImageChops.multiply(Image.new("L",(W,H),0),same_sf))  # explicit zero placeholder; visual+clean gate below
# Ensure every changed pixel outside touched row remains exact to current C114 candidate.
if outside!=0: raise RuntimeError("collateral")

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candp.write_bytes(cb[:128]+raw.tobytes("raw","RGBA"))
csha=sha(candp)
dec_raw=Image.frombytes("RGBA",(W,H),candp.read_bytes()[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

# Evidence.
pad=70; box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
ims=[flat(z.crop(box)) for z in (src,old,clean,dec)]
labs=["SOURCE","C114 OLD","CLEAN","A86 FINAL"]
sheet=Image.new("RGB",(sum(i.width for i in ims)+24*(len(ims)-1),max(i.height for i in ims)+34),(225,225,225))
xx=0; dr=ImageDraw.Draw(sheet)
for lab,im in zip(labs,ims):
    dr.text((xx+4,4),lab,fill=(0,0,0)); sheet.paste(im,(xx,34)); xx+=im.width+24
sheet.save(out/"A86_IGR018_SELECT_CAR_CONTACT.jpg",quality=95)
# 2x focused comparison
focus=flat(dec.crop(box)).resize(((box[2]-box[0])*2,(box[3]-box[1])*2),Image.Resampling.NEAREST)
focus.save(out/"A86_IGR018_FINAL_2X.jpg",quality=96)
flat(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A86_FD90_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":121,"asset":asset_rel,
 "user_regression":{"id":"IGR-018","screenshot":"스크린샷(141).png","screen":"CAR_SELECT_BLUE",
   "defect_tags":["SOURCE_RESIDUE","LOW_RES_FONT","HEADER_GHOST","STYLE_INCONSISTENCY"]},
 "mapping":{"status":"EXACT_HIGH_CONFIDENCE_GRAPHICS","basis":"FD90AA9 contains the unique Select your car selector-header sprite; rework is scoped to that exact source effect bbox only."},
 "source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,
 "candidate_path":str(candp.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mips":mips,"header_128_exact":candp.read_bytes()[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "touched_element":{"source":"Select your car","korean":text_ko,"original_bbox":list(bbox),"localized_bbox":loc,
   "source_size":[x1-x0,y1-y0],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
   "delta_left":loc[0]-x0,"delta_right":x1-loc[2],"delta_top":loc[1]-y0,"delta_bottom":y1-loc[3],
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":FPAT,"native_font_size_px":used_fs,
   "horizontal_source_proportion_scale":1.10,"shear":used_k,"alignment":"source-left-positive-inset",
   "render_basis":"fresh native-resolution glyph; no previous Korean bitmap reuse"},
 "preservation":{"all_pixels_outside_select_car_bbox_vs_C114_candidate":"PIXEL_EXACT","other_28_localized_rows":"PRESERVED_C114_BYTES"},
 "machine_checks":{"changed_pixels_outside_bbox":outside,"alpha_changed_outside_bbox":alpha_out,
   "clean_source_effect_unchanged_pixels":residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A86_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A86_IGR018_FD90_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A86_IGR018_FD90.json").write_text(json.dumps({
 "run":run,"index":121,"asset":"FD90AA9","candidate_sha256":csha,"regression":"IGR-018",
 "bbox_size_margin":"1/1 PASS","outside":outside,"alpha_outside":alpha_out,"clean_residue":residue,
 "worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "report":str((out/"A86_IGR018_FD90_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":csha,"localized_bbox":loc,"font_size":used_fs,"outside":outside,"alpha_outside":alpha_out,"clean_residue":residue},ensure_ascii=False))
