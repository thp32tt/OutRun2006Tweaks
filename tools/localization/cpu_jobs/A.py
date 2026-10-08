#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261008-A191-Q119-SOURCE-WHITE-HALO"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

idx=119
asset="textures/load/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/F6811E94_512x64.dds"
SOURCE_SHA="2336da3c2d08d1bfb99e3a8612a3fe7d39f9c852d7da433204c8d4a19b49c552"
source_bbox=[390,54,1632,200]
ko="타임 어택 모드"

# Fail closed against concurrent producer changes and the exact rejected C290 bytes.
REJECTED_SHA="d7e1378f1adac5ba1069985583cbcba30d8bc2f9b496110e865a3dd827b55490"
if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=REJECTED_SHA:
    raise RuntimeError("C290 rejected q119 bytes have changed; abort stale A191 job")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","119","--require-safe-rerender"],capture_output=True,text=True)
print("A191 REWORK TRIAGE "+triage.stdout,flush=True)
if triage.returncode: raise RuntimeError(("q119 rework triage blocked",triage.returncode,triage.stderr))


srcp=Path("/tmp/A191_F6811E94.dds")
urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise RuntimeError("source drift")
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]; W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]; FOURCC=raw[84:88]
if (W,H,MIPS,FOURCC)!=(2048,256,1,b"DXT5"): raise RuntimeError(("structure",W,H,MIPS,FOURCC))
blocks_x=W//4; blocks_y=H//4
if len(raw)!=128+blocks_x*blocks_y*16: raise RuntimeError(("unexpected payload",len(raw)))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
x0,y0,x1,y1=source_bbox
source_alpha=sa[:,:,3]>0
ys,xs=np.nonzero(source_alpha)
actual=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
if actual!=source_bbox: raise RuntimeError(("bbox drift",actual))
if np.count_nonzero(source_alpha & ~((np.indices((H,W))[1]>=x0)&(np.indices((H,W))[1]<x1)&(np.indices((H,W))[0]>=y0)&(np.indices((H,W))[0]<y1))):
    raise RuntimeError("unexpected nontransparent protected pixels")

# Transparent clean plate: this atlas contains only the source title/effect.
clean_arr=sa.copy()
clean_arr[y0:y1,x0:x1,:]=0
clean=Image.fromarray(clean_arr,"RGBA")
if np.count_nonzero(clean_arr[:,:,3]): raise RuntimeError("clean plate residue")

# Source style measurement uses opaque/core pixels only, avoiding low-alpha unpremultiplied fringe RGB.
core=sa[y0:y1,x0:x1,:]
opaque=core[:,:,3]>=200
orange=opaque&(core[:,:,0]>160)&(core[:,:,1]>55)&(core[:,:,1]<190)&(core[:,:,2]<90)
navy=opaque&(core[:,:,0]<55)&(core[:,:,1]<70)&(core[:,:,2]<115)
source_bright=(core[:,:,3]>=16)&(np.min(core[:,:,:3],axis=2)>=215)
if int(source_bright.sum())<1000: raise RuntimeError("source white luminous halo absent from exact English source")
white_rgb=tuple(int(v) for v in np.median(core[source_bright][:,:3],axis=0))
if orange.sum()<1000 or navy.sum()<1000: raise RuntimeError(("style sample",int(orange.sum()),int(navy.sum())))
fill=tuple(int(v) for v in np.median(core[orange][:,:3],axis=0))+(255,)
outline=tuple(int(v) for v in np.median(core[navy][:,:3],axis=0))+(255,)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","imagemagick"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def shear(im,k):
    add=max(1,int(round(k*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)

# Render at native HD. Preserve the strong orange fill, navy outline and right italic lean.
sw=x1-x0; sh=y1-y0
chosen=None
for fs in range(136,70,-1):
    font=ImageFont.truetype(FONT,fs)
    pad=30
    canvas=Image.new("RGBA",(1600,260),(0,0,0,0))
    d=ImageDraw.Draw(canvas)
    tb=d.textbbox((0,0),ko,font=font,stroke_width=10)
    ox=pad-tb[0]; oy=pad-tb[1]
    d.text((ox,oy),ko,font=font,fill=fill,stroke_width=10,stroke_fill=outline)
    gb=canvas.getchannel("A").getbbox()
    if not gb: continue
    glyph=canvas.crop(gb)
    glyph=shear(glyph,0.25)
    gb=glyph.getchannel("A").getbbox()
    if gb: glyph=glyph.crop(gb)
    if glyph.width>sw-42 or glyph.height>sh-32: continue
    px=x0+(sw-glyph.width)//2; py=y0+(sh-glyph.height)//2
    # DXT5 boundary safety: final visible render stays well away from every partial block.
    if min(px-x0,py-y0,x1-(px+glyph.width),y1-(py+glyph.height))<15: continue
    chosen=(glyph,px,py,fs); break
if chosen is None: raise RuntimeError("no source-faithful fit")
glyph,px,py,font_size=chosen
# Source-family rebuild: high-luminance white rim *outside* navy stroke,
# then warm diffuse halo. This is not a flat recolor or a width stretch.
HALO_PAD=12
padded=(glyph.width+2*HALO_PAD,glyph.height+2*HALO_PAD)
letter_alpha=Image.new("L",padded,0)
letter_alpha.paste(glyph.getchannel("A"),(HALO_PAD,HALO_PAD))
# Controller black/gray first-look A190: former 6px opaque white
# border looked rigid unlike diffuse/luminous English. Keep the source-
# white colour, but separate narrow softened keyline from wide soft halo.
rim=letter_alpha.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.3))
diffuse=letter_alpha.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(3.5))
rim_alpha=rim.point(lambda a: min(255,int(a*0.86)))
diffuse_alpha=diffuse.point(lambda a: min(255,int(a*0.73)))
halo_alpha=ImageChops.lighter(rim_alpha,diffuse_alpha)
letter_glow=Image.new("RGBA",padded,white_rgb+(0,))
letter_glow.putalpha(halo_alpha)
letter_glow.alpha_composite(glyph,(HALO_PAD,HALO_PAD))
px-=HALO_PAD; py-=HALO_PAD
# A controlled margin is required because the 4x4 DXT5 edge-blocks
# must remain byte/pixel safe outside the exact English effect boundary.
if min(px-x0,py-y0,x1-(px+letter_glow.width),y1-(py+letter_glow.height))<2:
    raise RuntimeError("white halo reaches source-effect border")
desired=clean.copy()
desired.alpha_composite(letter_glow,(px,py))
desired_arr=np.asarray(desired,dtype=np.uint8)
pre_mask=desired_arr[:,:,3]>0
pyy,pxx=np.nonzero(pre_mask)
pre_bbox=[int(pxx.min()),int(pyy.min()),int(pxx.max()+1),int(pyy.max()+1)]
if not (pre_bbox[0]>x0 and pre_bbox[1]>y0 and pre_bbox[2]<x1 and pre_bbox[3]<y1): raise RuntimeError(("pre bbox",pre_bbox))
if (pre_bbox[2]-pre_bbox[0])>sw or (pre_bbox[3]-pre_bbox[1])>sh: raise RuntimeError("pre size overflow")

# Encode a full desired DXT5 image with ImageMagick, then splice only block-safe data.
desired_raw=desired.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/A191_desired_raw.png"); desired_raw.save(tmp_png)
tmp_dds=Path("/tmp/A191_desired_dxt5.dds")
cmd=["convert",str(tmp_png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(tmp_dds)]
subprocess.run(cmd,check=True)
enc=tmp_dds.read_bytes()
if enc[:4]!=b"DDS " or enc[84:88]!=b"DXT5": raise RuntimeError(("imagemagick dds",enc[84:88]))
ew=struct.unpack_from("<I",enc,16)[0]; eh=struct.unpack_from("<I",enc,12)[0]
if (ew,eh)!=(W,H): raise RuntimeError(("encoded dims",ew,eh))
expected=blocks_x*blocks_y*16
if len(enc)<128+expected: raise RuntimeError(("encoded too short",len(enc),expected))
enc_blocks=enc[128:128+expected]

# Readable bbox -> raw-orientation allowed rectangle.
raw_y0=H-y1; raw_y1=H-y0
raw_allowed=np.zeros((H,W),dtype=bool)
raw_allowed[raw_y0:raw_y1,x0:x1]=True
raw_target=np.asarray(desired_raw)[:,:,3]>0

def alpha_palette(a0,a1):
    if a0>a1:
        return [a0,a1,(6*a0+a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(a0+6*a1)//7]
    return [a0,a1,(4*a0+a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(a0+4*a1)//5,0,255]

def patch_partial(block,inside_mask):
    b=bytearray(block)
    a0,a1=b[0],b[1]; pal=alpha_palette(a0,a1)
    zero_ids=[i for i,v in enumerate(pal) if v==0]
    if not zero_ids: raise RuntimeError(("partial block lacks alpha0",a0,a1,pal))
    zi=zero_ids[0]
    bits=int.from_bytes(b[2:8],"little")
    for yy in range(4):
        for xx in range(4):
            if inside_mask[yy,xx]:
                p=yy*4+xx
                bits=(bits & ~(7<<(3*p))) | (zi<<(3*p))
    b[2:8]=bits.to_bytes(6,"little")
    return bytes(b)

out_blocks=bytearray(raw[128:])
partial=full=outside=0
for by in range(blocks_y):
    for bx in range(blocks_x):
        yy=by*4; xx=bx*4
        m=raw_allowed[yy:yy+4,xx:xx+4]
        n=int(m.sum())
        off=(by*blocks_x+bx)*16
        if n==0:
            outside+=1
            continue
        if n==16:
            full+=1
            out_blocks[off:off+16]=enc_blocks[off:off+16]
        else:
            partial+=1
            # Korean target is intentionally kept off partial boundary blocks.
            if np.count_nonzero(raw_target[yy:yy+4,xx:xx+4]):
                raise RuntimeError(("target touches partial block",bx,by))
            out_blocks[off:off+16]=patch_partial(bytes(out_blocks[off:off+16]),m)

payload=raw[:128]+bytes(out_blocks)
candidate.write_bytes(payload)
cand_sha=hashlib.sha256(payload).hexdigest()

dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
changed=np.any(sa!=da,axis=2)
alpha_changed=sa[:,:,3]!=da[:,:,3]
allowed=np.zeros((H,W),bool); allowed[y0:y1,x0:x1]=True
outside_changed=int(np.count_nonzero(changed&~allowed))
outside_alpha=int(np.count_nonzero(alpha_changed&~allowed))
if outside_changed or outside_alpha: raise RuntimeError(("outside changed",outside_changed,outside_alpha))

decoded_mask=da[:,:,3]>0
dys,dxs=np.nonzero(decoded_mask)
db=[int(dxs.min()),int(dys.min()),int(dxs.max()+1),int(dys.max()+1)]
if not (db[0]>=x0 and db[1]>=y0 and db[2]<=x1 and db[3]<=y1): raise RuntimeError(("decoded containment",db))
if (db[2]-db[0])>sw or (db[3]-db[1])>sh: raise RuntimeError(("decoded size",db))
deltas={"delta_left":db[0]-x0,"delta_right":x1-db[2],"delta_top":db[1]-y0,"delta_bottom":y1-db[3]}
if min(deltas.values())<=0: raise RuntimeError(("no positive margin",deltas))

# Residue check against intended Korean footprint. Compression may add a few AA pixels, so use a 2px guard.
expected_guard=ndimage.binary_dilation(pre_mask,iterations=2)
source_core=sa[:,:,3]>8
residue=int(np.count_nonzero(source_core & (da[:,:,3]>8) & ~expected_guard))
if residue: raise RuntimeError(("source residue outside korean guard",residue))
decoded_outside_guard=int(np.count_nonzero((da[:,:,3]>8)&~ndimage.binary_dilation(pre_mask,iterations=3)))
if decoded_outside_guard: raise RuntimeError(("unexpected decoded visible pixels",decoded_outside_guard))

# Verify exact source header and format behavior.
if payload[:128]!=raw[:128]: raise RuntimeError("header drift")
if len(payload)!=len(raw): raise RuntimeError("size drift")

# Evidence
src.save(out/"A191_SOURCE_READABLE.png"); src_raw.save(out/"A191_SOURCE_RAW.png")
clean.save(out/"A191_CLEAN_PLATE.png"); dec.save(out/"A191_FINAL_READABLE.png"); dec_raw.save(out/"A191_FINAL_RAW.png")
Image.fromarray((source_alpha*255).astype(np.uint8),"L").save(out/"A191_SOURCE_TEXT_MASK.png")
Image.fromarray((pre_mask*255).astype(np.uint8),"L").save(out/"A191_TARGET_MASK.png")

def white(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")
box=(max(0,x0-24),max(0,y0-24),min(W,x1+24),min(H,y1+24))
cards=[]
for lab,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
    v=white(im).crop(box)
    v=v.resize((v.width*2,v.height*2),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+34),"white"); c.paste(v,(0,34))
    ImageDraw.Draw(c).text((8,8),lab,fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+8 for c in cards)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((2200,1500),Image.Resampling.LANCZOS)
sheet.save(out/"A191_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

rawsheet=Image.new("RGB",(1100,700),"white")
for i,(lab,im) in enumerate([("SOURCE RAW mirror_y",src_raw),("FINAL RAW mirror_y",dec_raw)]):
    v=white(im); v.thumbnail((1050,280),Image.Resampling.LANCZOS)
    y=i*335+30; rawsheet.paste(v,(20,y)); ImageDraw.Draw(rawsheet).text((20,y-22),lab,fill="black")
rawsheet.save(out/"A191_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":idx,"asset":asset,
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "translation":{"source":"Time Attack Mode","korean":ko},
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
 "construction":{
   "clean_plate":"exact source glyph/effect bbox cleared to transparent; source contains no nontransparent pixels outside bbox",
   "render":"native 2048x256 Noto Sans CJK KR Black; C290 material defect correction: source-sampled white softened 3px keyline plus source-like diffuse outer halo behind orange/navy outline (A190 hard 6px rim visually rejected), same 0.25 right shear; height refit for 12px padding",
   "dxt5_boundary":"full-inside 4x4 blocks use fresh DXT5 encode; partial boundary blocks retain original endpoints/color bytes/outside indices and set only inside alpha indices to an existing exact-zero palette entry; outside blocks byte-identical source",
   "block_counts":{"full_inside":full,"partial_boundary":partial,"outside_unchanged":outside}
 },
 "style":{"font":"Noto Sans CJK KR Black","font_size":font_size,"fill_rgba":fill,"outline_rgba":outline,"outline_px":10,"shear":0.25,"white_halo_rgb":white_rgb,"halo_pad":HALO_PAD,"source_bright_pixel_count":int(source_bright.sum())},
 "elements":[{
   "source":"Time Attack Mode","korean":ko,
   "original_bbox":source_bbox,"localized_bbox":db,
   "source_width":sw,"source_height":sh,
   "localized_width":db[2]-db[0],"localized_height":db[3]-db[1],
   **deltas,
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
 }],
 "static_qa":{
   "clean_plate_source_residue_pixels":0,
   "changed_pixels_outside_original_bbox":outside_changed,
   "alpha_changed_outside_original_bbox":outside_alpha,
   "source_residue_outside_korean_guard":residue,
   "unexpected_visible_pixels_outside_korean_guard":decoded_outside_guard,
   "localized_overlap_pixels":0,
   "protected_pixels_changed":outside_changed,
   "dds_size_preserved":len(payload)==len(raw),
    "source_bright_count":int(source_bright.sum()),
    "decoded_final_bright_count":int(np.count_nonzero((np.min(da[:,:,:3],axis=2)>=215)&(da[:,:,3]>=16))),
   "status":"PASS"
 },
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"A191_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True,
 "supersedes_rejected_candidate_sha256":REJECTED_SHA,
 "previous_visual_failure":"A190 native BWG black/gray revealed a too-hard white rim rather than source diffuse halo; this reconstruction materially softens glow and revisits slant",
 "qa_gate":"Pending first-hand native SOURCE/CLEAN/FINAL, 4x/practical/RAW controller review; numeric PASS never authorizes C approval"
}
rp=out/"A191_F6811E94_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A191_F6811E94.json").write_text(json.dumps({
 "role":"A","run":run,"queue_index":idx,"asset":"F6811E94",
 "source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "original_bbox":source_bbox,"localized_bbox":db,"deltas":deltas,
 "outside_changed":outside_changed,"alpha_outside":outside_alpha,"residue":residue,
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False),flush=True)
