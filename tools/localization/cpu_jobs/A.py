#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, shutil, statistics, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION18"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A_prod18"); work.mkdir(parents=True,exist_ok=True)
source=work/"F6811E94_HD.dds"
atlas=work/"4x_F6811E94_512x64_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="c6bcd8b847e0f0a2f34ca9f9ea3b1616512bd1e6"
ATLAS_BLOB_SHA1="d25537314b6dd42b2eb624d4c4499fee8e666131"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_F6811E94_512x64_atlas.json",atlas)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_blob_sha1(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def median_rgba(vals):
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(4))

sb=source.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob",git_blob_sha1(sb)))
ab=atlas.read_bytes()
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob",git_blob_sha1(ab)))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS " or sb[84:88]!=b"DXT5": raise RuntimeError("not DXT5")
H,W=struct.unpack_from("<2I",sb,12)
if (W,H)!=(2048,256) or len(sb)!=524416: raise RuntimeError((W,H,len(sb)))
aj=json.loads(atlas.read_text())
if aj.get("regions_count")!=1 or aj["regions"][0]["rect"]!=[0,0,2048,256]: raise RuntimeError(("atlas drift",aj))

raw_source=Image.open(source).convert("RGBA")
src=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src_alpha=src.getchannel("A")
ob=list(src_alpha.getbbox() or ())
if len(ob)!=4: raise RuntimeError("source alpha bbox missing")
block_aligned=all(v%4==0 for v in ob)
if not block_aligned:
    report={"schema_version":1,"role":"A","run":run,"index":119,"asset":asset_rel,
      "source_sha256":SOURCE_SHA,"source_bbox":ob,"status":"A_PRODUCTION18_FAIL_CLOSED_DXT5_EXACT_BBOX_NOT_BLOCK_ALIGNED",
      "runtime_validation":"UNTESTED"}
    (out/"A_PRODUCTION18_F6811E94_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    (wr/"A_PRODUCTION18_F6811E94.json").write_text(json.dumps({"run":run,"asset":"F6811E94","index":119,"worker_status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    # Persist this fail-closed result as useful evidence; no candidate is written.
    raise SystemExit(0)

source_text_mask=balpha(src)
allowed=Image.new("L",(W,H),0)
ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"F6811E94_HD_SOURCE_READABLE.png"
cp=out/"F6811E94_HD_CLEAN_PLATE.png"
smp=out/"F6811E94_HD_SOURCE_TEXT_MASK.png"
ap=out/"F6811E94_HD_ALLOWED_SOURCE_BBOX_MASK.png"
pp=out/"F6811E94_HD_PROTECTED_VISIBLE_MASK.png"
cpp=out/"F6811E94_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)

subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A_PRODUCTION18_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION18_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
residue=count(ImageChops.multiply(balpha(clean),source_text_mask))
if residue: raise RuntimeError(("clean residue",residue))

def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    fp=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not fp: raise RuntimeError("font missing")
    return fp
FONT=resolve_font()

# Derive source palette families from decoded pixels: orange fill, dark outline, light outer fringe.
pix=src.load()
orange=[]; dark=[]; light=[]
for y in range(ob[1],ob[3]):
    for x in range(ob[0],ob[2]):
        r,g,b,a=pix[x,y]
        if not a: continue
        if r>140 and g>45 and g<190 and b<80 and r-g>35: orange.append((r,g,b,a))
        elif max(r,g,b)<105: dark.append((r,g,b,a))
        elif max(r,g,b)-min(r,g,b)<45 and min(r,g,b)>120: light.append((r,g,b,a))
fill_color=median_rgba(orange) if orange else (244,125,0,255)
dark_color=median_rgba(dark) if dark else (10,10,18,255)
light_color=median_rgba(light) if light else (230,230,230,255)

def shear_rgba(im,s=0.24):
    extra=max(8,int(math.ceil(abs(s)*im.height))+8)
    c=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0)); c.alpha_composite(im,(extra,0))
    coeff=(1,-s,s*c.height,0,1,0)
    z=c.transform(c.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=z.getchannel("A").getbbox()
    return z.crop(bb) if bb else z

def render(text):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(190,int(ah*1.05)),24,-1):
        f=ImageFont.truetype(FONT,fs)
        outer=max(5,round(fs*0.075))
        inner=max(3,round(fs*0.045))
        pad=outer+12
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=f,stroke_width=outer)
        layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ld=ImageDraw.Draw(layer)
        # Light outer fringe, then dark outline, then orange fill.
        ld.text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill_color,
                stroke_width=outer,stroke_fill=light_color)
        ld.text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill_color,
                stroke_width=inner,stroke_fill=dark_color)
        bb=layer.getchannel("A").getbbox(); layer=layer.crop(bb)
        layer=shear_rgba(layer,0.24)
        if layer.width<=aw-8 and layer.height<=ah-8:
            tx=ob[0]+(aw-layer.width)//2; ty=ob[1]+(ah-layer.height)//2
            if tx<=ob[0]: tx=ob[0]+2
            if ty<=ob[1]: ty=ob[1]+2
            if tx+layer.width>=ob[2]: tx=ob[2]-layer.width-2
            if ty+layer.height>=ob[3]: ty=ob[3]-layer.height-2
            return layer,(tx,ty),fs,outer,inner
    raise RuntimeError(("fit","타임 어택 모드",ob))

layer,(tx,ty),fs,outer,inner=render("타임 어택 모드")
final=clean.copy(); final.alpha_composite(layer,(tx,ty))
intended=Image.new("L",(W,H),0); intended.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
loc=list(intended.getbbox() or ())
if len(loc)!=4: raise RuntimeError("localized bbox missing")
contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]

exe=shutil.which("convert") or shutil.which("magick")
if not exe:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","imagemagick"],check=True)
    exe=shutil.which("convert") or shutil.which("magick")
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
png=work/"raw_final.png"; encp=work/"encoded.dds"; raw_final.save(png)
cmd=[exe]+(["convert"] if Path(exe).name=="magick" else [])+[str(png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(encp)]
subprocess.run(cmd,check=True)
enc=encp.read_bytes()
if len(enc)!=len(sb) or enc[84:88]!=b"DXT5": raise RuntimeError(("encode",len(enc),enc[84:88]))

outb=bytearray(sb); bw=W//4
raw_y1=H-ob[3]; raw_y2=H-ob[1]
touched=0
for by in range(raw_y1//4,raw_y2//4):
    for bx in range(ob[0]//4,ob[2]//4):
        p=128+(by*bw+bx)*16; outb[p:p+16]=enc[p:p+16]; touched+=1
candidate.write_bytes(outb)
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")

decoded_raw=Image.open(candidate).convert("RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
dp=out/"F6811E94_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),
                "--report",str(out/"A_PRODUCTION18_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION18_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))

def gray(im):
    bg=Image.new("RGBA",im.size,(128,128,128,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W,H*3),(80,80,80))
sheet.paste(gray(src),(0,0)); sheet.paste(gray(clean),(0,H)); sheet.paste(gray(decoded),(0,H*2))
sheet.save(out/"A_PRODUCTION18_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A_PRODUCTION18_FINAL_RAW_GRAY.jpg",quality=96)
m=16; box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
a=gray(src.crop(box)); b=gray(decoded.crop(box))
contact=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+26),(235,235,235))
contact.paste(a,(0,26)); contact.paste(b,(a.width+12,26)); ImageDraw.Draw(contact).text((3,3),"SOURCE | FINAL",fill=(0,0,0))
contact.save(out/"A_PRODUCTION18_CONTACT_SOURCE_FINAL.jpg",quality=96)

status_ok=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and contain and size_ok and positive and residue==0 and outside==0 and alpha_out==0 and prot==0)
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":119,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds","classification":"authoritative high-resolution source; DDS header 2048x256 DXT5"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"compression":"DXT5","bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y","source_bbox_block_aligned":block_aligned},
 "translation":{"source":"Time Attack Mode","korean":"타임 어택 모드"},
 "style":{"source_fill_median":fill_color,"source_dark_median":dark_color,"source_light_outer_median":light_color,
   "font":"Noto Sans CJK KR Black/Bold","font_size":fs,"outer_stroke":outer,"inner_stroke":inner,"shear":0.24},
 "original_bbox":ob,"localized_bbox":loc,
 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
 "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
 "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
 "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],"raw_containment":"PASS" if contain else "FAIL",
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "dxt5_touched_blocks":touched,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_out,"protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION18_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION18_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION18_F6811E94_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"F6811E94","index":119,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"compression":"DXT5","bbox_pass":"1/1" if contain else "FAIL","size_ceiling":"1/1" if size_ok else "FAIL","positive_margin":"1/1" if positive else "FAIL",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_out,
 "protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION18/A_PRODUCTION18_F6811E94_REPORT.json"}
(wr/"A_PRODUCTION18_F6811E94.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
