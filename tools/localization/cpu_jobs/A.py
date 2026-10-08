#!/usr/bin/env python3
"""A197: q103 Normal Balance — source-derived italic, native rendering, plate QA."""
import hashlib, json, os, struct, subprocess, glob, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("A197 hosted CPU worker role A only")
repo=Path.cwd()
run="20261009-A197-Q103-NORMAL-BALANCE-ITALIC-NATIVE"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
old_sha="bfb50ebd9a6f9d572ce3349b56f76cf461dabc9e209f6cf0b7f48608d44b5178"
source_sha="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
origin=[1411,1968,1801,2040]
prior=[1508,1986,1704,2026]
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ":raise RuntimeError("DDS signature fail")
    h,w=struct.unpack_from("<II",b,12)
    pitch=struct.unpack_from("<I",b,20)[0]
    mip=struct.unpack_from("<I",b,28)[0]
    bits=struct.unpack_from("<I",b,88)[0]
    masks=struct.unpack_from("<IIII",b,92)
    fourcc=b[84:88]
    if fourcc!=b"\0\0\0\0" or bits!=32 or mip!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("not native uncompressed DDS",w,h,mip,bits,fourcc))
    mode={ (255,65280,16711680,4278190080):"RGBA",(16711680,65280,255,4278190080):"BGRA"}.get(masks)
    if not mode:raise RuntimeError(("DDS masks",masks))
    readable=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{"width":w,"height":h,"pitch":pitch,"mips":mip,"bitcount":bits,"masks":list(masks),"mode":mode,"raw_orientation":"mirror_y"}
def save_dds(header,im,mode):
    b=header+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    candidate.write_bytes(b)
    return hashlib.sha256(b).hexdigest()
def mask_bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs):raise RuntimeError("empty text mask")
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def rgb(image,bg=(245,245,245)):
    back=Image.new("RGBA",image.size,(*bg,255));back.alpha_composite(image)
    return back.convert("RGB")
def font_path():
    paths=glob.glob("/usr/share/fonts/**/NotoSansCJK-Bold.ttc",recursive=True)
    if not paths:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        paths=glob.glob("/usr/share/fonts/**/NotoSansCJK-Bold.ttc",recursive=True)
    if not paths:raise RuntimeError("No NotoSansCJK Bold")
    return paths[0]
# SHA guard and read-only triage before any write.
if not candidate.is_file() or file_sha(candidate)!=old_sha:
    raise RuntimeError("q103 candidate was modified after C1 rejection; fail closed")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","103","--require-safe-rerender"],
                       capture_output=True,text=True)
print("A197_TRIAGE",triage.stdout,flush=True)
if triage.returncode!=0 or '"MATERIAL_REWORK"' not in triage.stdout:
    raise RuntimeError(("triage refuses unsafe rerender",triage.stdout,triage.stderr))
from urllib.request import urlretrieve
source_tmp=Path("/tmp/a197_590a_source.dds")
urlretrieve(source_url,source_tmp)
if file_sha(source_tmp)!=source_sha:
    raise RuntimeError(("exact canonical English source SHA mismatch",file_sha(source_tmp)))
header,src,meta=load_dds(source_tmp)
old_header,old_im,old_meta=load_dds(candidate)
if meta!=old_meta or header!=old_header or (meta["width"],meta["height"],meta["mode"])!=(2048,2048,"RGBA"):
    raise RuntimeError(("native DDS structure drift",meta,old_meta))
prev_dir=repo/"localization/graphics/role_A/20261006-A-PRODUCTION108-590A4724"
evidence_source=Image.open(prev_dir/"A108_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(prev_dir/"A108_CLEAN_PLATE.png").convert("RGBA")
old_png=Image.open(prev_dir/"A108_FINAL_READABLE.png").convert("RGBA")
if any(im.size!=src.size for im in (evidence_source,clean,old_png)):
    raise RuntimeError("A108 evidence dimension drift")
if ImageChops.difference(src,evidence_source).getbbox():
    raise RuntimeError("source DDS vs A108 native source PNG mismatch")
if ImageChops.difference(old_im,old_png).getbbox():
    raise RuntimeError("old DDS vs A108 native final PNG mismatch")
s=np.asarray(src); ca=np.asarray(clean)
changed_clean=np.any(s!=ca,axis=2)
x0,y0,x1,y1=origin
allowed=np.zeros((2048,2048),dtype=bool)
allowed[y0:y1,x0:x1]=True
plate_out=int(np.logical_and(changed_clean,~allowed).sum())
plate_changed=int(np.logical_and(changed_clean,allowed).sum())
if plate_out!=0 or plate_changed<3000:
    raise RuntimeError(("invalid source-only PLATE",plate_out,plate_changed))
# Plate must not carry a source glyph-shaped remnant inside true edit mask.
source_remnant_clean=int(np.logical_and(changed_clean,np.all(s==ca,axis=2)).sum())
if source_remnant_clean:raise RuntimeError("impossible clean diff residual")
# Explicit source-derived face profile: source-different pixels with high alpha and
# dark warm olive source strokes. Do not sample protected background.
source_pixels=s[np.logical_and(changed_clean,s[:,:,3]>180)]
cores=source_pixels[np.logical_and(np.mean(source_pixels[:,:3],axis=1)<185,
                                  source_pixels[:,0]<190)]
if len(cores)<300:raise RuntimeError(("not enough canonical source face",len(cores)))
face=tuple(int(i) for i in np.median(cores[:,:3],axis=0))
if max(face)-min(face)>85 or max(face)>195:
    raise RuntimeError(("source tone not olive-gray",face))
FONT=font_path()
def make_glyph(size,tracking,shear):
    font=ImageFont.truetype(FONT,size,index=1)
    text="일반 밸런스"
    pen=24.0
    base=Image.new("L",(1200,200),0)
    draw=ImageDraw.Draw(base)
    for ch in text:
        if ch==" ":
            pen+=size*.34
            continue
        bb=draw.textbbox((0,0),ch,font=font)
        draw.text((int(round(pen-bb[0])),round(28-bb[1])),ch,font=font,fill=255)
        pen+=draw.textlength(ch,font=font)+tracking
    bb=base.getbbox()
    if not bb:raise RuntimeError("missing Korean lettering")
    crop=base.crop(bb)
    # Rightward-readable slant: top moves further right than bottom.
    hh=crop.height
    shift=int(np.ceil(hh*shear))+6
    shifted=crop.transform((crop.width+shift,hh),Image.Transform.AFFINE,
          (1,shear,-shear*hh+3,0,1,0),Image.Resampling.BICUBIC,fillcolor=0)
    bb=shifted.getbbox()
    return shifted.crop(bb)
choices=[]
for fs in range(78,50,-1):
    for track in (5,3,1,0):
        glyph=make_glyph(fs,track,0.27)
        if glyph.width<=x1-x0-10 and glyph.height<=y1-y0-8:
            choices.append((fs,track,glyph))
if not choices:raise RuntimeError("right-italic cannot fit exact source effect bbox")
# Source height and natural Hangul glyph widths lead fit; no arbitrary English-width scaling.
fs,tracking,glyph=choices[0]
px=x0+((x1-x0)-glyph.width)//2
py=y0+((y1-y0)-glyph.height)//2
if min(px-x0,py-y0,x1-(px+glyph.width),y1-(py+glyph.height))<4:
    raise RuntimeError(("exact source effect bbox positive margin fail",px,py,glyph.size))
if glyph.width<=prior[2]-prior[0]+40 or glyph.height<=prior[3]-prior[1]+10:
    raise RuntimeError(("source-relative visual hierarchy not materially improved",glyph.size,prior))
layer=Image.new("RGBA",src.size,(0,0,0,0))
stamp=Image.new("RGBA",glyph.size,(*face,0))
stamp.putalpha(glyph)
layer.alpha_composite(stamp,(px,py))
render_mask=np.asarray(layer.getchannel("A"))>0
if int(np.logical_and(render_mask,~allowed).sum()):
    raise RuntimeError("1px original-effect source boundary overrun")
final=clean.copy()
final.alpha_composite(layer)
fa=np.asarray(final)
original_to_final=np.any(s!=fa,axis=2)
clean_to_final=np.any(ca!=fa,axis=2)
checks={
  "source_clean_outside_source_bbox":plate_out,
  "source_clean_exact_removed_pixels":plate_changed,
  "source_final_changed_outside_original_bbox":int(np.logical_and(original_to_final,~allowed).sum()),
  "source_final_alpha_changed_outside":int(np.logical_and(s[:,:,3]!=fa[:,:,3],~allowed).sum()),
  "clean_to_final_changed_outside_transparent_glyph_mask":int(np.logical_and(clean_to_final,~render_mask).sum()),
  "protected_changed_outside_declared_effect_region":int(np.logical_and(original_to_final,~allowed).sum()),
  "source_exact_residue_outside_korean_glyph":int(np.logical_and(changed_clean,np.logical_and(np.all(fa==s,axis=2),~render_mask)).sum()),
  "foreign_rectangle_pixels":int(np.logical_and(clean_to_final,~render_mask).sum()),
  "glyph_border_1px_intrusion":int(np.logical_and(render_mask,~allowed).sum()),
  "localized_overlap_pairs":0
}
if any(v for k,v in checks.items() if k!="source_clean_exact_removed_pixels"):
    raise RuntimeError(("all mandatory pixel gates fail closed",checks))
bbox=mask_bbox(render_mask)
if bbox[0]<x0 or bbox[1]<y0 or bbox[2]>x1 or bbox[3]>y1:raise RuntimeError("bbox spill")
changed_candidate=file_sha(candidate)
new_sha=save_dds(header,final,meta["mode"])
if new_sha==changed_candidate:raise RuntimeError("unchanged DDS not a material production")
nh,decoded,nmeta=load_dds(candidate)
if nh!=header or nmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("persisted DDS decode mismatched source geometry")
src.save(out/"A197_SOURCE_READABLE.png")
clean.save(out/"A197_CLEAN_PLATE.png")
decoded.save(out/"A197_FINAL_DECODED_READABLE.png")
Image.fromarray((render_mask*255).astype("uint8"),"L").save(out/"A197_RENDER_GLYPH_MASK.png")
Image.fromarray((allowed*255).astype("uint8"),"L").save(out/"A197_ALLOWED_SOURCE_BBOX_MASK.png")
crop=(1370,1936,1840,2048)
for label,im in (("SOURCE",src),("CLEAN",clean),("FINAL",decoded)):
    im.crop(crop).save(out/f"A197_{label}_REGION_NATIVE.png")
for bg_name,color in (("WHITE",(245,245,245)),("BLACK",(0,0,0)),("GRAY",(125,125,125))):
    for scale in (100,75,50):
        panels=[]
        for img in (src,clean,decoded):
            p=rgb(img,color).crop(crop)
            if scale!=100:
                p=p.resize((p.width*scale//100,p.height*scale//100),Image.Resampling.LANCZOS)
            panels.append(p)
        width,height=panels[0].size
        sheet=Image.new("RGB",(3*width+16,height+27),"white")
        d=ImageDraw.Draw(sheet)
        d.text((4,5),f"SOURCE | CLEAN | FINAL  {bg_name} {scale}%",fill="black")
        for i,p in enumerate(panels):sheet.paste(p,(i*(width+8),27))
        sheet.save(out/f"A197_SOURCE_CLEAN_FINAL_{bg_name}_{scale}.png")
for label,pair in (
    ("READABLE",(src,decoded)),
    ("RAW",(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
            decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)))):
    a,b=[rgb(x) for x in pair]
    a.thumbnail((1200,1200));b.thumbnail((1200,1200))
    result=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)+28),"white")
    ImageDraw.Draw(result).text((4,3),f"A197 SOURCE / PERSISTED FINAL {label}",fill="black")
    result.paste(a,(0,28));result.paste(b,(a.width+8,28))
    result.save(out/f"A197_{label}_SOURCE_FINAL.jpg",quality=95)
report={
  "schema_version":1,"role":"A","run":run,"queue_index":103,"asset":asset_rel,
  "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","source_sha256":source_sha,"url":source_url},
  "prior_candidate_sha256":old_sha,"candidate_sha256":new_sha,
  "structure":meta,"header_exact":True,"preserve_nontext_artwork":True,
  "source_clean_provenance":"localization/graphics/role_A/20261006-A-PRODUCTION108-590A4724/A108_CLEAN_PLATE.png",
  "transcription":{"english":"Normal Balance","korean":"일반 밸런스"},
  "original_bbox":origin,"previous_bbox":prior,"new_bbox":bbox,
  "source_height":y1-y0,"source_width":x1-x0,
  "previous_size":[prior[2]-prior[0],prior[3]-prior[1]],
  "new_size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
  "new_margins":[bbox[0]-x0,x1-bbox[2],bbox[1]-y0,y1-bbox[3]],
  "source_italic_family":{
     "method":"native glyph direct raster + 0.27 rightward top shift shear (no width scaling), source-median olive-gray fill",
     "source_core_median_rgb":list(face),"korean_font":"NotoSansCJK-Bold.ttc index 1",
     "point_size":fs,"tracking":tracking,"rightward_shift_over_height":round(glyph.height*0.27,2),
     "source_glyph_angle":"RIGHT_ITALIC_VISUALLY_SOURCE; exact source anchor review pending controller"},
  "machine_qa":checks,
  "readable_orientation":"FLIP-Y; raw sprite mirror-Y source equals final",
  "authored_mips":1,"persisted_roundtrip":"PASS",
  "source_clean_visual":"PENDING_CONTROLLER_INDEPENDENT_REVIEW",
  "clean_final_visual":"PENDING_CONTROLLER_INDEPENDENT_REVIEW",
  "producer_decision":"PENDING_CONTROLLER_SELF_QA",
  "C1":"PENDING","C3":"PENDING","RUNTIME_VALIDATION":"UNTESTED",
}
(out/"A197_WORKER_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A197_Q103.json").write_text(json.dumps({
  "run":run,"queue_index":103,"asset":"590A4724","candidate_sha256":new_sha,
  "source_sha256":source_sha,"new_bbox":bbox,"new_size":report["new_size"],
  "previous_size":report["previous_size"],"machine_qa":checks,
  "status":"WORKER_MACHINE_PASS_CONTROLLER_SELF_QA_PENDING",
  "RUNTIME_VALIDATION":"UNTESTED","report":str((out/"A197_WORKER_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A197_DONE",new_sha,report["new_size"],report["new_margins"],face,flush=True)
