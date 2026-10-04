#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION21"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod21")
work.mkdir(parents=True,exist_ok=True)
source=work/"EBEF6D20_HD.dds"
atlas=work/"4x_EBEF6D20_512x512_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="f05e35654433b4ce010d119d4a705f505cdd80c2"
ATLAS_BLOB_SHA1="6f30c47b87dd67726d0945a04096fae7670b0526"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_loading_cvt_Exst/4x_EBEF6D20_512x512_atlas.json",atlas)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_blob_sha1(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def median_rgba(vals):
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(4))
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")

sb=source.read_bytes()
ab=atlas.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1:
    raise RuntimeError(("source blob mismatch",git_blob_sha1(sb),SOURCE_BLOB_SHA1))
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("atlas blob mismatch",git_blob_sha1(ab),ATLAS_BLOB_SHA1))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()

if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,2048,8192,1) or depth not in (0,1):
    raise RuntimeError(("structure",W,H,pitch,depth,mips))
if len(sb)!=128+W*H*4:
    raise RuntimeError(("byte size",len(sb)))
if pf[1]!=65 or pf[2]!=0 or pf[3]!=32 or pf[7]!=0xff000000:
    raise RuntimeError(("pixel format",pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000):
    RAWMODE="RGBA"
elif masks==(0xff0000,0xff00,0xff):
    RAWMODE="BGRA"
else:
    raise RuntimeError(("unsupported RGB masks",masks))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

aj=json.loads(atlas.read_text(encoding="utf-8"))
regions={int(r["idx"]):r for r in aj["regions"]}
if len(regions)!=7 or regions[5]["rect"]!=[0,424,920,120] or regions[6]["rect"]!=[920,424,920,120]:
    raise RuntimeError(("atlas drift",len(regions),regions.get(5),regions.get(6)))

targets=[
    {"key":"loading_left","region_idx":5,"cell":[0,424,920,120],"source":"Loading","korean":"로딩"},
    {"key":"loading_right","region_idx":6,"cell":[920,424,920,120],"source":"Loading","korean":"로딩"},
]

source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows0=[]
bright_vals=[]
dark_vals=[]
for t in targets:
    x,y,cw,ch=t["cell"]
    cell=src.crop((x,y,x+cw,y+ch))
    a=cell.getchannel("A")
    bb=a.getbbox()
    if not bb:
        raise RuntimeError(("empty Loading target",t["key"]))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    # These two atlas cells are dedicated Loading text sprites. Their decoded alpha
    # is therefore the exact glyph/effect footprint including outline/shadow fringe.
    source_text_mask.paste(ImageChops.lighter(
        source_text_mask.crop((x,y,x+cw,y+ch)),
        a.point(lambda v:255 if v else 0)),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    cp=cell.load()
    for yy in range(ch):
        for xx in range(cw):
            r,g,b,aa=cp[xx,yy]
            if aa==0:
                continue
            if min(r,g,b)>=150 and max(r,g,b)-min(r,g,b)<=55:
                bright_vals.append((r,g,b,aa))
            if max(r,g,b)<=100:
                dark_vals.append((r,g,b,aa))
    rows0.append({**t,"original_bbox":ob})

if len(bright_vals)<50 or len(dark_vals)<20:
    raise RuntimeError(("source style samples",len(bright_vals),len(dark_vals)))
fill_color=median_rgba(bright_vals)
dark_color=median_rgba(dark_vals)

source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"EBEF6D20_HD_SOURCE_READABLE.png"
cp=out/"EBEF6D20_HD_CLEAN_PLATE.png"
smp=out/"EBEF6D20_HD_SOURCE_TEXT_MASK.png"
ap=out/"EBEF6D20_HD_ALLOWED_SOURCE_BBOX_MASK.png"
pp=out/"EBEF6D20_HD_PROTECTED_VISIBLE_MASK.png"
cpp=out/"EBEF6D20_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)

subprocess.run([
    "python3",str(validator),str(sp),str(cp),str(smp),
    "--protected-mask",str(cpp),
    "--report",str(out/"A_PRODUCTION21_CLEAN_PLATE_VALIDATION.json")
],check=True)
cleanrep=json.loads((out/"A_PRODUCTION21_CLEAN_PLATE_VALIDATION.json").read_text(encoding="utf-8"))
if cleanrep["status"]!="PASS":
    raise RuntimeError(("clean validator",cleanrep))
source_mask_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(src,clean))))
if source_mask_unchanged!=0:
    raise RuntimeError(("source effect unchanged in clean",source_mask_unchanged))

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    def pick():
        for pat in pats:
            try:
                spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception:
                spec=""
            if "|" not in spec:
                continue
            fp,idx=spec.rsplit("|",1)
            try: idx=int(idx or "0")
            except Exception: idx=0
            if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
                return fp,idx,pat
        return None
    got=pick()
    if got:
        return got
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    got=pick()
    if not got:
        raise RuntimeError("Noto CJK Korean unavailable")
    return got

FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

# Measure source alpha-vs-bright margins to preserve the Loading outline/shadow family.
style_margins=[]
for r0 in rows0:
    x,y,cw,ch=r0["cell"]
    cell=src.crop((x,y,x+cw,y+ch))
    ab=cell.getchannel("A").getbbox()
    bright=Image.new("L",(cw,ch),0); bp=bright.load(); cpix=cell.load()
    for yy in range(ch):
        for xx in range(cw):
            rr,gg,bb,aa=cpix[xx,yy]
            if aa and min(rr,gg,bb)>=150 and max(rr,gg,bb)-min(rr,gg,bb)<=55:
                bp[xx,yy]=255
    bbx=bright.getbbox()
    if not ab or not bbx:
        raise RuntimeError(("style bbox missing",r0["key"]))
    style_margins.append({
      "left":bbx[0]-ab[0],"right":ab[2]-bbx[2],
      "top":bbx[1]-ab[1],"bottom":ab[3]-bbx[3]
    })

stroke_guess=max(2,int(round(statistics.median(
    [max(1,m["left"]) for m in style_margins]+[max(1,m["top"]) for m in style_margins]
))))
shadow_dx=max(0,int(round(statistics.median([max(0,m["right"]-m["left"]) for m in style_margins]))))
shadow_dy=max(0,int(round(statistics.median([max(0,m["bottom"]-m["top"]) for m in style_margins]))))
shadow_dx=min(shadow_dx,12); shadow_dy=min(shadow_dy,12)
stroke_guess=min(stroke_guess,10)

def render_loading(text,ob):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(max(24,int(ah*1.2)),16,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=font,stroke_width=stroke_guess)
        pad=stroke_guess+max(shadow_dx,shadow_dy)+8
        layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2+shadow_dx,tb[3]-tb[1]+pad*2+shadow_dy),(0,0,0,0))
        ld=ImageDraw.Draw(layer)
        anchor=(pad-tb[0],pad-tb[1])
        if shadow_dx or shadow_dy:
            ld.text((anchor[0]+shadow_dx,anchor[1]+shadow_dy),text,font=font,fill=dark_color,
                    stroke_width=stroke_guess,stroke_fill=dark_color)
        ld.text(anchor,text,font=font,fill=fill_color,stroke_width=stroke_guess,stroke_fill=dark_color)
        bb=layer.getchannel("A").getbbox()
        if not bb:
            continue
        layer=layer.crop(bb)
        if layer.width<=aw-4 and layer.height<=ah-4:
            tx=ob[0]+(aw-layer.width)//2
            ty=ob[1]+(ah-layer.height)//2
            return layer,(tx,ty),fs
    raise RuntimeError(("Korean Loading fit failed",text,ob))

final=clean.copy()
masks={}
rows=[]
for r0 in rows0:
    ob=r0["original_bbox"]
    layer,(tx,ty),fs=render_loading(r0["korean"],ob)
    final.alpha_composite(layer,(tx,ty))
    lm=Image.new("L",(W,H),0)
    lm.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
    masks[r0["key"]]=lm
    loc=list(lm.getbbox() or ())
    if len(loc)!=4:
        raise RuntimeError(("localized bbox missing",r0["key"]))
    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    rows.append({
      "key":r0["key"],"source":r0["source"],"korean":r0["korean"],"region_idx":r0["region_idx"],
      "cell":r0["cell"],"original_bbox":ob,"localized_bbox":loc,
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "raw_containment":"PASS" if contain else "FAIL",
      "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,
      "font_size":fs,"stroke_width":stroke_guess,"shadow_offset":[shadow_dx,shadow_dy],
      "rework_status":"A_PRODUCTION21_NEW_EXACT_HD_CANDIDATE"
    })

pair_overlap=count(ImageChops.multiply(masks["loading_left"],masks["loading_right"]))
pair_touch=count(ImageChops.multiply(masks["loading_left"].filter(ImageFilter.MaxFilter(3)),masks["loading_right"]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]:
    raise RuntimeError("DDS header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError("RGBA roundtrip mismatch")
dp=out/"EBEF6D20_HD_FINAL_DECODED_READABLE.png"
decoded.save(dp)

subprocess.run([
    "python3",str(validator),str(sp),str(dp),str(ap),
    "--protected-mask",str(pp),
    "--report",str(out/"A_PRODUCTION21_FINAL_MASK_VALIDATION.json")
],check=True)
finalrep=json.loads((out/"A_PRODUCTION21_FINAL_MASK_VALIDATION.json").read_text(encoding="utf-8"))
if finalrep["status"]!="PASS":
    raise RuntimeError(("final validator",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(
    ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),
    ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

# Controller evidence: full readable triptych, raw mirror_y, and both target rows.
thumb=(1024,1024)
sheet=Image.new("RGB",(1024,3072),(96,96,96))
for i,im in enumerate([src,clean,decoded]):
    sheet.paste(gray(im).resize(thumb,Image.Resampling.LANCZOS),(0,i*1024))
sheet.save(out/"A_PRODUCTION21_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_PRODUCTION21_FINAL_RAW_GRAY.jpg",quality=96)

contacts=[]
for r in rows:
    ob=r["original_bbox"]; m=16
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    a=gray(src.crop(box)); b=gray(clean.crop(box)); c=gray(decoded.crop(box))
    ri=Image.new("RGB",(a.width+b.width+c.width+24,max(a.height,b.height,c.height)+26),(235,235,235))
    ri.paste(a,(0,26)); ri.paste(b,(a.width+12,26)); ri.paste(c,(a.width+b.width+24,26))
    ImageDraw.Draw(ri).text((3,3),r["key"]+" SOURCE | CLEAN | FINAL",fill=(0,0,0))
    contacts.append(ri)
cw=max(i.width for i in contacts); ch=sum(i.height for i in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for i in contacts:
    cs.paste(i,(0,yy)); yy+=i.height+4
cs.save(out/"A_PRODUCTION21_CONTACT_SOURCE_CLEAN_FINAL.jpg",quality=96)

status_ok=(
    cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and source_mask_unchanged==0
    and all_bbox and all_size and all_positive and pair_overlap==0 and pair_touch==0
    and outside==0 and alpha_out==0 and prot==0
)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"index":65,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
   "git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds",
   "classification":"authoritative high-resolution source; DDS header 2048x2048 32-bit alpha RGB"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":RAWMODE,"pitch":pitch,
   "depth":depth,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translation":{"source":"Loading","korean":"로딩","physical_occurrences":2},
 "source_style":{"fill_median":fill_color,"dark_effect_median":dark_color,
   "family":"upright heavy white Loading text with dark outline/shadow",
   "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,
   "derived_stroke_width":stroke_guess,"derived_shadow_offset":[shadow_dx,shadow_dy],
   "source_margin_samples":style_margins},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "rows":rows,
 "all_2_readable_and_raw_bbox_pass":all_bbox,
 "all_2_size_ceiling_pass":all_size,
 "all_2_positive_margin":all_positive,
 "localized_pair_overlap_pixels":pair_overlap,
 "localized_pair_touch_pixels":pair_touch,
 "decoded_changes":{"changed_pixels_total":count(diff),
   "changed_pixels_outside_source_bboxes":outside,
   "alpha_changed_pixels_outside_source_bboxes":alpha_out,
   "protected_visible_pixels_changed":prot},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION21_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION21_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION21_EBEF6D20_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"EBEF6D20","index":65,"source_sha256":SOURCE_SHA,
 "candidate_sha256":CANDIDATE_SHA,"source_dimensions":[W,H],"format":"RGBA32",
 "pixel_raw_mode":RAWMODE,
 "bbox_pass":"2/2" if all_bbox else "FAIL",
 "size_ceiling":"2/2" if all_size else "FAIL",
 "positive_margin":"2/2" if all_positive else "FAIL",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "localized_pair_overlap_pixels":pair_overlap,"localized_pair_touch_pixels":pair_touch,
 "changed_pixels_outside_source_bboxes":outside,
 "alpha_changed_pixels_outside_source_bboxes":alpha_out,
 "protected_visible_pixels_changed":prot,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION21/A_PRODUCTION21_EBEF6D20_REPORT.json"
}
(wr/"A_PRODUCTION21_EBEF6D20.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok:
    raise SystemExit(2)
