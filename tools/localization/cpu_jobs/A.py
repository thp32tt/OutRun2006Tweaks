#!/usr/bin/env python3
"""A198R q227 source-family native text rework, independent PLATE/COMPOSITE QA."""
from pathlib import Path
import os,json,hashlib,struct,subprocess,urllib.request,glob
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("A198R GitHub hosted worker A only")
repo=Path.cwd()
run="20261009-A198R-Q227-COUNTER-REPAIR"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E596B7AC_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
prior="502bc3ba19e32647c3a429c43064f5f8a9d43925c7366191d1de19275d866b69"
source_sha="769308121df7229766b50eea1d43c68703e1720df4147ec8f34b735e2a9527f3"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E596B7AC_512x512.dds"
base=repo/"localization/graphics/role_A/20261006-A-REWORK96R-E596B7AC"
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dds(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ":raise RuntimeError("DDS invalid magic")
    h,w=struct.unpack_from("<II",b,12)
    mip=struct.unpack_from("<I",b,28)[0]
    pitch=struct.unpack_from("<I",b,20)[0]
    depth=struct.unpack_from("<I",b,88)[0]
    fourcc=b[84:88]
    masks=struct.unpack_from("<IIII",b,92)
    mode={(0xff,0xff00,0xff0000,0xff000000):"RGBA",
          (0xff0000,0xff00,0xff,0xff000000):"BGRA"}.get(masks)
    if not mode or depth!=32 or fourcc!=bytes(4) or mip!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS unexpected",w,h,mode,mip,depth,len(b)))
    im=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],im,{"w":w,"h":h,"mips":mip,"pitch":pitch,"masks":list(masks),"mode":mode}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs):raise RuntimeError("mask is empty")
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font_path():
    pp=glob.glob("/usr/share/fonts/**/NotoSansCJK-Bold.ttc",recursive=True)
    if not pp:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        pp=glob.glob("/usr/share/fonts/**/NotoSansCJK-Bold.ttc",recursive=True)
    if not pp:raise RuntimeError("NotoSansCJK-Bold required; no thin fallback")
    return pp[0]
def make_mask(text,pt):
    ff=ImageFont.truetype(FONT,pt,index=1)
    canv=Image.new("L",(3000,500),0)
    ImageDraw.Draw(canv).text((20,20),text,font=ff,fill=255)
    bb=canv.getbbox()
    if not bb:raise RuntimeError(("blank Hangul",text))
    if bb[0]<3 or bb[1]<3 or bb[2]>canv.width-3 or bb[3]>canv.height-3:
        raise RuntimeError(("glyph crop clipping",text,bb))
    return canv.crop(bb)
def solid_bg(im,rgb=(235,235,235)):
    b=Image.new("RGBA",im.size,(*rgb,255));b.alpha_composite(im);return b.convert("RGB")
def pic_compare(name,images,rect):
    imgs=[solid_bg(x).crop(rect) for x in images]
    w,h=imgs[0].size
    joined=Image.new("RGB",(w*3+16,h+24),"white")
    ImageDraw.Draw(joined).text((4,4),f"{name}  SOURCE | CLEAN | FINAL",fill=(0,0,0))
    for i,im in enumerate(imgs):joined.paste(im,(i*(w+8),24))
    return joined
if not candidate.is_file() or digest(candidate)!=prior:raise RuntimeError("candidate changed; no overwrite")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","227","--require-safe-rerender"],
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
print("A198 TRIAGE",triage.stdout,flush=True)
if triage.returncode!=0 or '"MATERIAL_REWORK"' not in triage.stdout:
    raise RuntimeError(("triage blocked",triage.returncode,triage.stderr))
url=Path("/tmp/a198_e596b7ac_source.dds")
urllib.request.urlretrieve(source_url,url)
if digest(url)!=source_sha:raise RuntimeError(("canonical source SHA unexpected",digest(url)))
header,source,meta=dds(url)
hh,current,mm=dds(candidate)
if header!=hh or meta!=mm or (meta["w"],meta["h"],meta["mode"])!=(2048,2048,"RGBA"):
    raise RuntimeError(("exact-source DDS header mismatch",meta,mm))
rp=json.loads((base/"A96R_E596B7AC_REPORT.json").read_text(encoding="utf-8"))
if rp["candidate_sha256"]!="e60eb09818ce79c1afc005905ce0d5f7d2678c7f69a2b25f418f2679200499b2" or rp["source_provenance"]["source_sha256"]!=source_sha:
    raise RuntimeError("old A96R report SHA unexpected")
rows=rp["rows"]
if len(rows)!=16 or len({r["key"] for r in rows})!=16:
    raise RuntimeError("16 physical rows required")
srcpng=Image.open(base/"A96R_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(base/"A96R_CLEAN_PLATE.png").convert("RGBA")
prevpng=Image.open(repo/"localization/graphics/role_A/20261009-A198-Q227-SOURCE-WEIGHT-HEIGHT/A198_FINAL_PERSISTED_READABLE.png").convert("RGBA")
if any(im.size!=source.size for im in (srcpng,clean,prevpng)):
    raise RuntimeError("authored baseline dimension drift")
if ImageChops.difference(source,srcpng).getbbox() or ImageChops.difference(current,prevpng).getbbox():
    raise RuntimeError("canonical DDS != original evidence PNG")
sa=np.asarray(source); ca=np.asarray(clean); olda=np.asarray(current)
allowed=np.zeros((meta["h"],meta["w"]),dtype=bool)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    if not (0<=x0<x1<=meta["w"] and 0<=y0<y1<=meta["h"]):raise RuntimeError(("bad bboxes",row))
    allowed[y0:y1,x0:x1]=True
source_clean=np.any(sa!=ca,axis=2)
outside_plate=int(np.logical_and(source_clean,~allowed).sum())
source_removed=int(source_clean.sum())
source_clean_protected=int(np.logical_and(source_clean,~allowed).sum())
if outside_plate or source_clean_protected or source_removed<100000:
    raise RuntimeError(("PLATE_ONLY failure",outside_plate,source_removed))
FONT=font_path()
final=clean.copy()
masks=[]
result=[]
# Source-derived flat-family face is preserved. Do not invent a bevel, shadow or
# bounding-background crop. Per-region maximum NATIVE font size recovers
# the specific glyph-height shortfall rather than scaling old Korean bitmaps.
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    rw,rh=x1-x0,y1-y0
    family=row["family"]
    fill=(79,97,101,255) if family!="red_flag" else (186,0,0,255)
    # A96R C1 root cause: an unintended thin Korean glyph impression.
    # Use native Bold TTC, with a single 1px native no artificial face extension.
    pad=1  # visually rejected A198 Black+dilation filled Hangul counters; preserve native Bold interior
    effect_r=(pad-1)//2
    options=[]
    upper=191 if family=="red_flag" else 100
    lower=117 if family=="red_flag" else 49
    for pt in range(upper,lower-1,-1):
        ink=make_mask(row["korean"],pt)
        if ink.width+2*effect_r<rw-2 and ink.height+2*effect_r<rh-2:
            options.append((pt,ink))
            break
    if not options:raise RuntimeError(("source-bbox glyph-fit unavailable",row["key"]))
    pt,ink=options[0]
    # Render from native mask, not the old candidate, and remeasure effects.
    buffered=Image.new("L",(ink.width+2*effect_r,ink.height+2*effect_r),0)
    buffered.paste(ink,(effect_r,effect_r))
    mask=buffered.filter(ImageFilter.MaxFilter(pad))
    ink_density=float(np.mean(np.asarray(mask)>170))
    if ink_density>0.74:raise RuntimeError(("new counter occlusion too dense",row["key"],ink_density))
    mw,mh=mask.size
    px=x0+2;py=y0+(rh-mh)//2
    if px+mw>x1-1 or py<y0+1 or py+mh>y1-1:
        raise RuntimeError(("native glyph over original text limits",row["key"],(mw,mh),(rw,rh)))
    alpha_layer=Image.new("L",final.size,0)
    alpha_layer.paste(mask,(px,py))
    gm=np.asarray(alpha_layer)>0
    if np.any(gm & ~allowed):raise RuntimeError(("1px protected pixel overlap",row["key"]))
    for prior_mask in masks:
        if np.any(gm & prior_mask):raise RuntimeError(("localized label overlap",row["key"]))
    glyph=Image.new("RGBA",final.size,fill[:3]+(0,))
    glyph.putalpha(alpha_layer)
    final.alpha_composite(glyph)
    bb=bbox(gm)
    if not (x0<bb[0] and y0<bb[1] and bb[2]<x1 and bb[3]<y1):
        raise RuntimeError(("source bbox escaped",row["key"],bb))
    masks.append(gm)
    oldbb=row["localized_bbox"]
    result.append(dict(key=row["key"],source=row["source"],korean=row["korean"],family=family,
       original_bbox=row["original_bbox"],old_bbox=oldbb,new_bbox=bb,
       old_width=oldbb[2]-oldbb[0],old_height=oldbb[3]-oldbb[1],
       new_width=bb[2]-bb[0],new_height=bb[3]-bb[1],
       source_width=rw,source_height=rh,
       margin_px=[bb[0]-x0,x1-bb[2],bb[1]-y0,y1-bb[3]],
       fill_rgba=list(fill),font="NotoSansCJK-Bold index 1",font_pt=pt,
       native_face_extension_px=effect_r,native_ink_density=round(ink_density,4),
       anti_aliased_native=True,effect="FLAT_SOURCE_FACE_NO_SHADOW_NO_BOX"))
# A correction to the visual-failed A198 must restore legible Hangul counters while preserving material height gain.
pro=next(x for x in result if x["key"]=="professional")
if pro["new_height"]<65 or pro["new_height"]<=pro["old_height"]+12:
    raise RuntimeError(("PROFESSIONAL still too small",pro))
fa=np.asarray(final)
global_mask=np.zeros_like(allowed)
for m in masks:global_mask|=m
changed=np.any(sa!=fa,axis=2)
composite=np.any(ca!=fa,axis=2)
residue=int(np.logical_and(source_clean,np.logical_and(np.all(fa==sa,axis=2),~global_mask)).sum())
check={
 "source_clean_removed_pixels":source_removed,
 "source_clean_changed_outside_source_bboxes":outside_plate,
 "source_final_changed_outside_source_bboxes":int(np.logical_and(changed,~allowed).sum()),
 "source_final_alpha_changed_outside":int(np.logical_and(sa[:,:,3]!=fa[:,:,3],~allowed).sum()),
 "clean_final_changed_outside_Korean_glyphs":int(np.logical_and(composite,~global_mask).sum()),
 "source_script_exact_residue_outside_final_glyphs":residue,
 "protected_art_changed":int(np.logical_and(changed,~allowed).sum()),
 "localized_overlap_pairs":0,"glyph_original_bbox_failures":0
}
if any(v for k,v in check.items() if k!="source_clean_removed_pixels"):
    raise RuntimeError(("PLATE_COMPOSITE_SOURCE contamination",check))
raw=header+final.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",meta["mode"])
if hashlib.sha256(raw).hexdigest()==prior:raise RuntimeError("unchanged DDS")
candidate.write_bytes(raw)
digest_candidate=digest(candidate)
reheader,roundtrip,re_meta=dds(candidate)
if reheader!=header or re_meta!=meta or ImageChops.difference(final,roundtrip).getbbox():
    raise RuntimeError("PERSISTED DDS roundtrip wrong")
# Persistent lossless SOURCE/CLEAN/FINAL native whole atlases; per-region proof.
source.save(out/"A198R_SOURCE_READABLE.png")
clean.save(out/"A198R_CLEAN_PLATE.png")
roundtrip.save(out/"A198R_FINAL_PERSISTED_READABLE.png")
Image.fromarray((allowed*255).astype("uint8"),"L").save(out/"A198R_SOURCE_BBOX_SCOPE.png")
Image.fromarray((global_mask*255).astype("uint8"),"L").save(out/"A198R_KOREAN_GLYPH_SCOPE.png")
for row in result:
    x0,y0,x1,y1=row["original_bbox"]
    rect=(max(0,x0-5),max(0,y0-5),min(2048,x1+5),min(2048,y1+5))
    for label,im in (("SOURCE",source),("CLEAN",clean),("FINAL",roundtrip)):
        im.crop(rect).save(out/f"A198R_{row['key']}_{label}_NATIVE.png")
    sheet=pic_compare(row["key"],(source,clean,roundtrip),rect)
    sheet.save(out/f"A198R_{row['key']}_SOURCE_CLEAN_FINAL.jpg",quality=94)
    for scale in (100,75,50):
        if scale==100:im=sheet
        else:im=sheet.resize((max(1,int(sheet.width*scale/100)),max(1,int(sheet.height*scale/100))),Image.Resampling.LANCZOS)
        im.save(out/f"A198R_{row['key']}_TRIPLE_{scale}.jpg",quality=93)
for label,images in (("READABLE",(source,roundtrip)),("RAW",tuple(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for im in (source,roundtrip)))):
    a,b=[solid_bg(im) for im in images]
    a.thumbnail((1050,1050));b.thumbnail((1050,1050))
    picture=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+30),"white")
    ImageDraw.Draw(picture).text((2,5),f"A198 English SOURCE | Korean persisted FINAL {label}",fill="black")
    picture.paste(a,(0,30));picture.paste(b,(a.width+12,30))
    picture.save(out/f"A198R_{label}_SOURCE_FINAL.jpg",quality=94)
# Dedicated controller references: representative small gray, long stage and flat red.
selected=("professional","coniferous_forest","flagman1")
contact=[Image.open(out/f"A198R_{key}_SOURCE_CLEAN_FINAL.jpg").convert("RGB") for key in selected]
W=max(x.width for x in contact)
H=sum(x.height for x in contact)+10*(len(contact)-1)
contact_im=Image.new("RGB",(W,H),"white")
off=0
for im in contact:contact_im.paste(im,(0,off));off+=im.height+10
contact_im.save(out/"A198R_QA_REPRESENTATIVE_TRIPTYCH.jpg",quality=95)
report={
 "schema_version":1,"role":"A","run":run,"queue_index":227,"asset":asset,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","source_sha256":source_sha,"url":source_url},
 "previous_candidate_sha256":prior,"candidate_sha256":digest_candidate,
 "native_structure":meta,"header128_exact":True,"raw_orientation":"mirror_y",
 "source_clean_provenance":"localization/graphics/role_A/20261006-A-REWORK96R-E596B7AC/A96R_CLEAN_PLATE.png",
 "construction":"native font size by exact English per-line bbox, NotoSansCJK-Bold, source flat gray/red samples, NO morphological dilation; naturally heavy native Bold glyphs keep Hangul internal counter-space; source-gray/flat-red, no opaque crop, bevel or shadow",
 "rows":result,"machine_qa":check,"persisted_dds_roundtrip":"PASS",
 "localized_rows":len(result),"producer_visual":"PENDING_CONTROLLER_REVIEW",
 "C1":"PENDING","C3":"PENDING","APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED"}
(out/"A198R_WORKER_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A198R_Q227.json").write_text(json.dumps({
 "run":run,"queue_index":227,"candidate_sha256":digest_candidate,
 "prior_sha256":prior,"rows":len(result),
 "professional_before_after":[pro["old_height"],pro["new_height"]],
 "machine_qa":check,"report":str((out/"A198R_WORKER_REPORT.json").relative_to(repo)),
 "producer_status":"MACHINE_PASS_CONTROLLER_VISUAL_PENDING","RUNTIME_VALIDATION":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A198R_MACHINE_DONE",digest_candidate,"PROFESSIONAL",pro["old_height"],pro["new_height"],
      "ROWS",len(result),flush=True)
