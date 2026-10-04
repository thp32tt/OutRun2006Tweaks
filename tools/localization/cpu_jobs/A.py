#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION19"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod19"); work.mkdir(parents=True,exist_ok=True)
source=work/"313DB8CB_HD.dds"
atlas=work/"4x_313DB8CB_512x256_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="616eecec37dd04de4ee25f174e7453f6d2209f98"
ATLAS_BLOB_SHA1="d776a6f530d567d7a6d8e7d09a9c57bb67ee98be"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_313DB8CB_512x256_atlas.json",atlas)

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
if (W,H,pitch,depth,mips)!=(2048,1024,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text())
regions={r["idx"]:r for r in aj["regions"]}
if len(regions)!=47: raise RuntimeError(("region count",len(regions)))
target_defs=[
  ("tuned","TUNED","튜닝",15,[1404,968,320,56]),
  ("normal","NORMAL","일반",16,[1724,968,320,56]),
]
for key,st,kt,idx,expect in target_defs:
    if regions[idx]["rect"]!=expect: raise RuntimeError(("target cell drift",idx,regions[idx]["rect"],expect))

source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows0=[]
palette=[]
for key,st,kt,idx,rect in target_defs:
    x,y,w,h=rect
    cell=src.crop((x,y,x+w,y+h))
    a=cell.getchannel("A")
    bb=a.getbbox()
    if not bb: raise RuntimeError(("empty target",key))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    # Target cell is dedicated text-only; exact source effect mask is decoded alpha.
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x,y,x+w,y+h)),a.point(lambda v:255 if v else 0)),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    rows0.append({"key":key,"source":st,"korean":kt,"region_idx":idx,"cell":rect,"original_bbox":ob})
    cp=cell.load()
    for yy in range(h):
        for xx in range(w):
            r,g,b,aa=cp[xx,yy]
            if aa and min(r,g,b)>170 and max(r,g,b)-min(r,g,b)<55:
                palette.append((r,g,b,aa))

fill_color=median_rgba(palette) if palette else (248,248,248,255)
source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"313DB8CB_HD_SOURCE_READABLE.png"; cp=out/"313DB8CB_HD_CLEAN_PLATE.png"
smp=out/"313DB8CB_HD_SOURCE_TEXT_MASK.png"; ap=out/"313DB8CB_HD_ALLOWED_SOURCE_BBOX_MASK.png"
pp=out/"313DB8CB_HD_PROTECTED_VISIBLE_MASK.png"; cpp=out/"313DB8CB_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(ap); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A_PRODUCTION19_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION19_CLEAN_PLATE_VALIDATION.json").read_text())
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

def render(text,ob):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(max(18,int(ah*1.35)),12,-1):
        f=ImageFont.truetype(FONT,fs)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=f)
        pad=6
        layer=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ImageDraw.Draw(layer).text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill_color)
        bb=layer.getchannel("A").getbbox()
        if not bb: continue
        layer=layer.crop(bb)
        if layer.width<=aw-4 and layer.height<=ah-4:
            tx=ob[0]+(aw-layer.width)//2
            ty=ob[1]+(ah-layer.height)//2
            return layer,(tx,ty),fs
    raise RuntimeError(("fit",text,ob))

final=clean.copy()
masks={}
rows=[]
for r0 in rows0:
    ob=r0["original_bbox"]
    layer,(tx,ty),fs=render(r0["korean"],ob)
    final.alpha_composite(layer,(tx,ty))
    lm=Image.new("L",(W,H),0); lm.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
    masks[r0["key"]]=lm
    loc=list(lm.getbbox() or ())
    contain=len(loc)==4 and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=contain and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    positive=contain and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    rows.append({**r0,"localized_bbox":loc,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],"raw_containment":"PASS" if contain else "FAIL",
      "font":"Noto Sans CJK KR Black/Bold","font_size":fs,"style":"source-matched heavy plain white sans; no invented outline/slant",
      "rework_status":"A_PRODUCTION19_NEW_EXACT_HD_CANDIDATE"})

overlap=count(ImageChops.multiply(masks["tuned"],masks["normal"]))
touch=count(ImageChops.multiply(masks["tuned"].filter(ImageFilter.MaxFilter(3)),masks["normal"]))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw","RGBA"))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")
dp=out/"313DB8CB_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)

subprocess.run(["python3",str(validator),str(sp),str(dp),str(ap),"--protected-mask",str(pp),
                "--report",str(out/"A_PRODUCTION19_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION19_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final",finalrep))
diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(80,80,80,255)); bg.alpha_composite(im); return bg.convert("RGB")
thumb=(1024,512)
sheet=Image.new("RGB",(1024,1536),(70,70,70))
for i,im in enumerate([src,clean,decoded]): sheet.paste(gray(im).resize(thumb,Image.Resampling.LANCZOS),(0,i*512))
sheet.save(out/"A_PRODUCTION19_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_PRODUCTION19_FINAL_RAW_GRAY.jpg",quality=96)
contacts=[]
for r in rows:
    ob=r["original_bbox"]; m=8
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    a=gray(src.crop(box)); b=gray(decoded.crop(box))
    ri=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+24),(235,235,235))
    ri.paste(a,(0,24)); ri.paste(b,(a.width+12,24)); ImageDraw.Draw(ri).text((3,2),r["key"]+" SOURCE | FINAL",fill=(0,0,0)); contacts.append(ri)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+4
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contacts: cs.paste(x,(0,yy)); yy+=x.height+4
cs.save(out/"A_PRODUCTION19_CONTACT_SOURCE_FINAL.jpg",quality=96)

status_ok=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and all_bbox and all_size and all_positive and overlap==0 and touch==0 and outside==0 and alpha_out==0 and prot==0 and residue==0)
report={"schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":139,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds","classification":"authoritative high-resolution source; DDS header 2048x1024 RGBA32"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translation":[{"source":"TUNED","korean":"튜닝"},{"source":"NORMAL","korean":"일반"}],
 "source_style":{"fill_median":fill_color,"family":"heavy plain white sans, shared style"},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,"rows":rows,
 "all_2_readable_and_raw_bbox_pass":all_bbox,"all_2_size_ceiling_pass":all_size,"all_2_positive_margin":all_positive,
 "localized_label_overlap_pixels":overlap,"localized_label_touch_pixels":touch,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
   "protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION19_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION19_WORKER_REWORK_REQUIRED"}
(out/"A_PRODUCTION19_313DB8CB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"313DB8CB","index":139,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"format":"RGBA32","bbox_pass":"2/2" if all_bbox else "FAIL","size_ceiling":"2/2" if all_size else "FAIL","positive_margin":"2/2" if all_positive else "FAIL",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"localized_label_overlap_pixels":overlap,"localized_label_touch_pixels":touch,
 "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"clean_plate_source_text_residue_pixels":residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION19/A_PRODUCTION19_313DB8CB_REPORT.json"}
(wr/"A_PRODUCTION19_313DB8CB.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
