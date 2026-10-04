#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION20"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/9CE4E175_256x32.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod20"); work.mkdir(parents=True,exist_ok=True)
source=work/"9CE4E175_HD.dds"
atlas=work/"4x_9CE4E175_256x32_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="b70d3aa184d8d00a561ab72133cd3f830943fb41"
ATLAS_BLOB_SHA1="0b87a3a9b40b06b8cadfc66643280ed5dee09a01"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/9CE4E175_256x32.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_9CE4E175_256x32_atlas.json",atlas)

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
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(1024,128,4096,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text())
regions={r["idx"]:r for r in aj["regions"]}
if len(regions)!=2 or regions[0]["rect"]!=[0,72,580,56] or regions[1]["rect"]!=[580,108,56,20]:
    raise RuntimeError(("atlas drift",aj))

# Region 0 is the dedicated NOT AVAILABLE red label. Region 1 is protected artwork.
x,y,cw,ch=regions[0]["rect"]
cell=src.crop((x,y,x+cw,y+ch))
pix=cell.load()

# Discover bright neutral source glyph fill first.
seed=Image.new("L",(cw,ch),0); sp=seed.load()
for yy in range(ch):
    for xx in range(cw):
        r,g,b,a=pix[xx,yy]
        if a>80 and min(r,g,b)>=145 and max(r,g,b)-min(r,g,b)<=55:
            sp[xx,yy]=255
seed_bb=seed.getbbox()
if not seed_bb: raise RuntimeError("NOT AVAILABLE bright seed missing")

# Red plate background family from pixels away from the white glyphs.
red_samples=[]
for yy in range(ch):
    for xx in range(cw):
        if sp[xx,yy]: continue
        r,g,b,a=pix[xx,yy]
        if a>160 and r>90 and r-g>25 and r-b>25 and g<150 and b<150:
            red_samples.append((r,g,b,a))
if len(red_samples)<100: raise RuntimeError(("insufficient red background samples",len(red_samples)))
global_red=median_rgba(red_samples)

# Build exact glyph/effect mask only around the text seed. Include antialias/shadow pixels
# that depart from the local red plate, while excluding the plate border/background.
sx1,sy1,sx2,sy2=seed_bb
zone=(max(0,sx1-12),max(0,sy1-8),min(cw,sx2+12),min(ch,sy2+8))
effect=Image.new("L",(cw,ch),0); ep=effect.load()
for yy in range(zone[1],zone[3]):
    for xx in range(zone[0],zone[2]):
        r,g,b,a=pix[xx,yy]
        if a==0: continue
        dist=sum(abs(v-e) for v,e in zip((r,g,b,a),global_red))
        neutral=max(r,g,b)-min(r,g,b)<=75
        bright=min(r,g,b)>=85
        dark_effect=(r<80 and g<80 and b<80)
        if sp[xx,yy] or (dist>=34 and (neutral and bright or dark_effect)):
            ep[xx,yy]=255

ebb=effect.getbbox()
if not ebb: raise RuntimeError("source effect mask empty")
ob=[x+ebb[0],y+ebb[1],x+ebb[2],y+ebb[3]]

# The label must be materially within the dedicated red plate, not the whole cell.
if not (ob[0]>=x and ob[1]>=y and ob[2]<=x+cw and ob[3]<=y+ch):
    raise RuntimeError(("source bbox outside cell",ob))

# Reconstruct plate color by row median from red-family pixels outside effect.
row_bg={}
for yy in range(ch):
    vals=[]
    for xx in range(cw):
        if ep[xx,yy]: continue
        r,g,b,a=pix[xx,yy]
        if a>120 and r>80 and r-g>20 and r-b>20 and g<170 and b<170:
            vals.append((r,g,b,a))
    if len(vals)>=8: row_bg[yy]=median_rgba(vals)
usable=sorted(row_bg)
if not usable: raise RuntimeError("row background missing")
for yy in range(ch):
    if yy not in row_bg:
        row_bg[yy]=row_bg[min(usable,key=lambda z:abs(z-yy))]

source_text_mask=Image.new("L",(W,H),0); source_text_mask.paste(effect,(x,y))
allowed=Image.new("L",(W,H),0)
ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))

clean=src.copy(); cpix=clean.load()
for yy in range(ch):
    for xx in range(cw):
        if ep[xx,yy]:
            cpix[x+xx,y+yy]=row_bg[yy]

spng=out/"9CE4E175_HD_SOURCE_READABLE.png"
cpng=out/"9CE4E175_HD_CLEAN_PLATE.png"
smp=out/"9CE4E175_HD_SOURCE_TEXT_MASK.png"
ap=out/"9CE4E175_HD_ALLOWED_SOURCE_BBOX_MASK.png"
pp=out/"9CE4E175_HD_PROTECTED_VISIBLE_MASK.png"
cpp=out/"9CE4E175_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(spng); clean.save(cpng); source_text_mask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)

subprocess.run(["python3",str(validator),str(spng),str(cpng),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A_PRODUCTION20_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION20_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
residue=count(ImageChops.multiply(dmask(src,clean),ImageOps.invert(source_text_mask)))
if residue!=0: raise RuntimeError(("clean changed outside exact source mask",residue))

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    def pick():
        for pat in pats:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" not in spec: continue
            fp,idx=spec.rsplit("|",1)
            try: idx=int(idx or "0")
            except Exception: idx=0
            if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp,idx,pat
        return None
    got=pick()
    if got: return got
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    got=pick()
    if not got: raise RuntimeError("font missing")
    return got
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

# Source fill color from white seed.
white_vals=[]
for yy in range(ch):
    for xx in range(cw):
        if sp[xx,yy]: white_vals.append(pix[xx,yy])
fill_color=median_rgba(white_vals)

def render(text):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(max(16,int(ah*1.35)),12,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        stroke=1
        tb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        pad=7
        layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ImageDraw.Draw(layer).text((pad-tb[0],pad-tb[1]),text,font=font,fill=fill_color,
                                   stroke_width=stroke,stroke_fill=fill_color)
        bb=layer.getchannel("A").getbbox()
        if not bb: continue
        layer=layer.crop(bb)
        if layer.width<=aw-4 and layer.height<=ah-4:
            tx=ob[0]+(aw-layer.width)//2
            ty=ob[1]+(ah-layer.height)//2
            return layer,(tx,ty),fs,stroke
    raise RuntimeError(("fit","이용 불가",ob))

layer,(tx,ty),fs,stroke=render("이용 불가")
final=clean.copy(); final.alpha_composite(layer,(tx,ty))
localized_mask=Image.new("L",(W,H),0)
localized_mask.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
loc=list(localized_mask.getbbox() or ())
if len(loc)!=4: raise RuntimeError("localized bbox missing")
contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
size_ok=contain and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
positive=contain and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw","RGBA"))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")
dp=out/"9CE4E175_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)

subprocess.run(["python3",str(validator),str(spng),str(dp),str(ap),"--protected-mask",str(pp),
                "--report",str(out/"A_PRODUCTION20_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION20_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
source_residue=count(ImageChops.multiply(balpha(clean),source_text_mask))

def gray(im):
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W,H*3),(70,70,70))
sheet.paste(gray(src),(0,0)); sheet.paste(gray(clean),(0,H)); sheet.paste(gray(decoded),(0,H*2))
sheet.save(out/"A_PRODUCTION20_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A_PRODUCTION20_FINAL_RAW_GRAY.jpg",quality=96)
m=12; box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
a=gray(src.crop(box)); b=gray(clean.crop(box)); c=gray(decoded.crop(box))
contact=Image.new("RGB",(a.width+b.width+c.width+24,max(a.height,b.height,c.height)+26),(235,235,235))
contact.paste(a,(0,26)); contact.paste(b,(a.width+12,26)); contact.paste(c,(a.width+b.width+24,26))
ImageDraw.Draw(contact).text((3,3),"SOURCE | CLEAN | FINAL",fill=(0,0,0))
contact.save(out/"A_PRODUCTION20_CONTACT_SOURCE_CLEAN_FINAL.jpg",quality=96)

status_ok=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and contain and size_ok and positive and
           outside==0 and alpha_out==0 and prot==0 and source_residue==0)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":195,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_sumo_fe_cvt_Exst/9CE4E175_256x32.dds","classification":"authoritative high-resolution source; DDS header 1024x128 RGBA32"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translation":{"source":"NOT AVAILABLE","korean":"이용 불가"},
 "source_style":{"fill_median":fill_color,"background_red_median":global_red,"family":"heavy white sans on red plate; no invented contrasting outline/slant",
                 "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,"same_color_weight_stroke":stroke},
 "source_seed_bbox":[x+seed_bb[0],y+seed_bb[1],x+seed_bb[2],y+seed_bb[3]],"original_bbox":ob,"localized_bbox":loc,
 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
 "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
 "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
 "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],"raw_containment":"PASS" if contain else "FAIL",
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_out,
   "protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":source_residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION20_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION20_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION20_9CE4E175_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"9CE4E175","index":195,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"format":"RGBA32","bbox_pass":"1/1" if contain else "FAIL","size_ceiling":"1/1" if size_ok else "FAIL","positive_margin":"1/1" if positive else "FAIL",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_out,
 "protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":source_residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION20/A_PRODUCTION20_9CE4E175_REPORT.json"}
(wr/"A_PRODUCTION20_9CE4E175.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
