#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-PRODUCTION82-IGR008-RANK"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
source_sha="b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887"
input_sha="7956df939b40013a145abb53c1734508b33070d187466caf891c7953ee40ac68"
rank_bbox=(1068,756,1413,882)
work=Path("/tmp/outrun_A82"); work.mkdir(parents=True,exist_ok=True)
source=work/"BF3EE5C6_HD.dds"
COMMIT="3ce344e7ed6b535f5e4d34c1192071ff7afbe6"
# Correct canonical commit is fixed below before download.
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds",source)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def flatten(im):
    bg=Image.new("RGBA",im.size,(88,88,88,255)); bg.alpha_composite(im); return bg.convert("RGB")

if sha(source)!=source_sha: raise RuntimeError(("source SHA drift",sha(source)))
if sha(candidate)!=input_sha: raise RuntimeError(("candidate SHA drift",sha(candidate)))
sb=source.read_bytes(); cb=candidate.read_bytes()
if sb[:4]!=b"DDS " or cb[:128]!=sb[:128]: raise RuntimeError("DDS header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,depth,mips)!=(2048,2048,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Exact rank-label source region from the previously C111-approved BF3 family report.
x0,y0,x1,y1=rank_bbox
source_rank=src.crop(rank_bbox)
if source_rank.getchannel("A").getbbox() is None: raise RuntimeError("empty canonical Rank source")

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
protected_old=ImageChops.multiply(bmask(old.getchannel("A")),ImageOps.invert(allowed))
protected_source=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))

# Rank clean plate is transparent: this source sprite is isolated baked lettering.
source_clean=src.copy()
source_clean.paste(Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0)),(x0,y0))
srcp=out/"BF3EE5C6_HD_SOURCE_READABLE.png"; cleanp=out/"BF3EE5C6_RANK_CLEAN_PLATE.png"
src.save(srcp); source_clean.save(cleanp); allowed.save(out/"BF3EE5C6_RANK_ALLOWED_MASK.png"); protected_source.save(out/"BF3EE5C6_SOURCE_PROTECTED_MASK.png")

# Resolve a native Korean Black face and render directly at the 2048x2048 HD resolution.
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception: q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:
                return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()

def shear_mask(mask,k):
    pad=max(8,int(mask.height*abs(k))+8)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o

def offset_mask(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0: o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o

def make_rank_layer():
    # Current in-game regression shows the prior Korean rank label as low-resolution/broken.
    # Render a fresh native-resolution Black glyph with source-like silver/lavender gloss,
    # dark keyline, pale rim and offset depth; mild source-proportion width correction only.
    for fs in range(112,88,-1):
        f=ImageFont.truetype(FONT,fs,index=FI)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        bb=d.textbbox((0,0),"랭크",font=f)
        pad=24
        m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
        ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),"랭크",font=f,fill=255)
        m=shear_mask(m,0.29)
        mb=m.getbbox()
        if not mb: continue
        m=m.crop(mb)
        # Source Rank is materially wider than two Hangul syllables; a 1.20x source-proportion
        # correction keeps Hangul legible without reusing/upscaling any old Korean bitmap.
        m=m.resize((int(round(m.width*1.20)),m.height),Image.Resampling.LANCZOS)
        outer=m.filter(ImageFilter.MaxFilter(15))
        key=m.filter(ImageFilter.MaxFilter(9))
        shadow=offset_mask(outer,7,8)
        w,h=outer.size
        layer=Image.new("RGBA",(w,h),(0,0,0,0))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(16,17,25,235)),Image.new("RGBA",(w,h),(0,0,0,0)),shadow))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(235,232,246,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(54,55,68,255)),Image.new("RGBA",(w,h),(0,0,0,0)),key))
        grad=Image.new("RGBA",(w,h),(0,0,0,0)); gp=grad.load()
        for yy in range(h):
            t=yy/max(1,h-1)
            top=(255,255,255,255); bot=(211,205,232,255)
            c=tuple(round(top[i]*(1-t)+bot[i]*t) for i in range(4))
            for xx in range(w): gp[xx,yy]=c
        layer.alpha_composite(Image.composite(grad,Image.new("RGBA",(w,h),(0,0,0,0)),m))
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        if layer.width<=x1-x0-8 and layer.height<=y1-y0-8:
            return layer,fs
    raise RuntimeError("rank native render does not fit")
layer,fs=make_rank_layer()

# Rework only the Rank sprite region. Every other previously C111-approved BF3 pixel stays exact.
final=old.copy()
final.paste(Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0)),(x0,y0))
tx=x0+(x1-x0-layer.width)//2; ty=y0+(y1-y0-layer.height)//2
final.alpha_composite(layer,(tx,ty))
loc=[tx,ty,tx+layer.width,ty+layer.height]
if not (loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("positive margin",loc,rank_bbox))
if (loc[2]-loc[0])>(x1-x0) or (loc[3]-loc[1])>(y1-y0): raise RuntimeError("size ceiling")

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw","RGBA"))
csha=sha(candidate)
dec_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("DDS roundtrip")
decp=out/"BF3EE5C6_A82_FINAL_READABLE.png"; dec.save(decp)

# Scoped exact-pixel gates: source geometry for the touched Rank row; previous C111 candidate is
# the preservation baseline for every untouched localized/protected pixel.
delta=dmask(old,dec)
outside=count(ImageChops.multiply(delta,ImageOps.invert(allowed)))
alpha_delta=bmask(ImageChops.difference(old.getchannel("A"),dec.getchannel("A")))
alpha_out=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(delta,protected_old))
clean_diff=dmask(src,source_clean)
clean_out=count(ImageChops.multiply(clean_diff,ImageOps.invert(allowed)))
clean_protected=count(ImageChops.multiply(clean_diff,protected_source))
newmask=Image.new("L",(W,H),0); newmask.paste(bmask(layer.getchannel("A")),(tx,ty))
new_vs_clean=dmask(source_clean,Image.composite(dec,source_clean,allowed))
render_out=count(ImageChops.multiply(newmask,ImageOps.invert(allowed)))

# Exact source text residue check outside the newly rendered Hangul footprint within the Rank bbox.
same=ImageOps.invert(dmask(src,dec))
source_alpha=ImageChops.multiply(bmask(src.getchannel("A")),allowed)
guard=newmask.filter(ImageFilter.MaxFilter(5))
residue=count(ImageChops.multiply(source_alpha,ImageChops.multiply(same,ImageOps.invert(guard))))
if any(v!=0 for v in [outside,alpha_out,protected_changed,clean_out,clean_protected,render_out,residue]):
    raise RuntimeError(("zero gate fail",outside,alpha_out,protected_changed,clean_out,clean_protected,render_out,residue))

# Visual evidence with nearby source rank letters B/C and the old/new Rank sprite.
ctx=(930,675,1540,1045)
ims=[flatten(z.crop(ctx)) for z in (src,source_clean,old,dec)]
labels=["SOURCE","CLEAN","OLD","A82 FINAL"]
card=Image.new("RGB",(sum(i.width for i in ims)+24*(len(ims)-1),max(i.height for i in ims)+34),(225,225,225))
x=0; dr=ImageDraw.Draw(card)
for lab,im in zip(labels,ims):
    dr.text((x+4,4),lab,fill=(0,0,0)); card.paste(im,(x,34)); x+=im.width+24
card.save(out/"A82_IGR008_RANK_CONTEXT.jpg",quality=95)

full=Image.new("RGB",(1024*3,1024),(80,80,80))
for i,z in enumerate((src,old,dec)):
    full.paste(flatten(z).resize((1024,1024),Image.Resampling.LANCZOS),(i*1024,0))
full.save(out/"A82_BF3_SOURCE_OLD_FINAL.jpg",quality=94)
flatten(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A82_BF3_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":49,"asset":asset_rel,
 "user_regression_ids":["IGR-008","IGR-011"],"mapping_basis":"IGR-008 screen contains Next Stage plus Rank B; B1696633 uniquely supplies Next Stage while BF3EE5C6 uniquely supplies localized Rank plus preserved A-E rank glyphs. Rank-label material defect is BF3EE5C6; B/C glyph art remains exact source pixels.",
 "source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,
 "candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":candidate.read_bytes()[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "touched_element":{"source":"Rank","korean":"랭크","original_bbox":list(rank_bbox),"localized_bbox":loc,
   "source_size":[x1-x0,y1-y0],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
   "delta_left":loc[0]-x0,"delta_right":x1-loc[2],"delta_top":loc[1]-y0,"delta_bottom":y1-loc[3],
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":FPAT,"native_font_size_px":fs,
   "horizontal_source_proportion_scale":1.20,"shear":0.29,"render_basis":"fresh native-resolution glyph; no previous Korean bitmap reuse"},
 "preservation":{"all_pixels_outside_rank_bbox_vs_C111_candidate":"PIXEL_EXACT","rank_letters_A_B_C_D_E":"PRESERVED_SOURCE_ART","other_12_localized_rows":"PRESERVED_C111_BYTES"},
 "machine_checks":{"changed_pixels_outside_rank_bbox":outside,"alpha_changed_outside_rank_bbox":alpha_out,
   "protected_pixels_changed":protected_changed,"clean_changed_outside_rank_bbox":clean_out,"clean_protected_changed":clean_protected,
   "render_pixels_outside_rank_bbox":render_out,"source_rank_residue_outside_new_glyph_guard":residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A82_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A82_IGR008_BF3_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A82_IGR008_BF3.json").write_text(json.dumps({
 "run":run,"index":49,"asset":"BF3EE5C6","candidate_sha256":csha,"regressions":["IGR-008","IGR-011"],
 "bbox_size_margin":"1/1 PASS","outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
 "source_residue":residue,"worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "report":str((out/"A82_IGR008_BF3_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":csha,"localized_bbox":loc,"font_size":fs,"outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,"residue":residue},ensure_ascii=False))
