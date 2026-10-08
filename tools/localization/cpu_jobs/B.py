#!/usr/bin/env python3
"""B260 q214: BC3 face-priority, constrained original-block Hangul correction.

Do not reuse an old Korean raster. New native Noto CJK glyph mask is rendered on the
verified source-derived B253 clean plate, then RGB565 BC3 blocks are fitted to
cream face + source red badge. Only exact original START/GOAL effect bboxes may
change from canonical DDS. Machine quality NEVER establishes visual approval.
"""
import os, hashlib, json, struct, urllib.request, subprocess, tempfile, sys
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
if os.getenv("OUTRUN_CPU_WORKER")!="github-actions" or os.getenv("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B260 GitHub-hosted CPU runner (ChatGPT local GitHub raw DNS unavailable)")
root=Path.cwd()
RUN="20261008-B260-Q214-BC3-FACE-PRIORITY"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
loc=root/"localization/graphics"
path=loc/"hd_candidates"/asset
out=loc/"role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
# Rework convergence must detect the C285+C289 repetition on current queue.
# A routine same-method rerender is intentionally rejected (exit 2).
triage_cmd=[sys.executable,"tools/localization/rework_triage.py","--index","214"]
check=subprocess.run(triage_cmd,capture_output=True,text=True,check=True)
triage=json.loads(check.stdout)
result=triage["assets"][0]
if result["next_action"]!="METHOD_CHANGE_REQUIRED" or "SOURCE_FAMILY_BEVEL_MISMATCH" not in result["repeated_root_causes"]:
    raise RuntimeError(("B260 requires genuine repeated-source-style defect",result))
blocked=subprocess.run(triage_cmd+["--require-safe-rerender"],capture_output=True,text=True)
if blocked.returncode!=2:
    raise RuntimeError(("blind ordinary rerender not safely blocked",blocked.returncode))
(out/"B260_REWORK_TRIAGE.json").write_text(json.dumps(triage,ensure_ascii=False,indent=2)+"\n")

SOURCE_SHA="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
PRIOR_SHA="ace42cb3d539df7c538c6d93b6c3f001e3d18e4f41aaa29bdab1466fe412fc30"
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"3da79726739ac631d8e2703a65330dbb0c310770/"
"Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
cleanpath=loc/"role_B/20261008-B253-Q214-BC3-COUNTER-SPACE/B253_CLEAN_PLATE.png"
def sha(b):return hashlib.sha256(b).hexdigest()
old=path.read_bytes()
if sha(old)!=PRIOR_SHA: raise RuntimeError(("q214 changed concurrently",sha(old),PRIOR_SHA))
with tempfile.TemporaryDirectory(prefix="b260_source_") as tmp:
    sourcefile=Path(tmp)/"source.dds"
    urllib.request.urlretrieve(url,sourcefile)
    sourcebytes=sourcefile.read_bytes()
if sha(sourcebytes)!=SOURCE_SHA:raise RuntimeError(("source changed",sha(sourcebytes)))
W=struct.unpack_from("<I",sourcebytes,16)[0]
H=struct.unpack_from("<I",sourcebytes,12)[0]
mip=struct.unpack_from("<I",sourcebytes,28)[0]
if (W,H,mip,sourcebytes[84:88],len(sourcebytes))!=(2048,2048,1,b"DXT5",128+2048*2048):
    raise RuntimeError(("unexpected source format",W,H,mip,sourcebytes[84:88],len(sourcebytes)))
if old[:128]!=sourcebytes[:128]:raise RuntimeError("DDS header changed")
def decode(buf):
    return Image.open(BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=decode(sourcebytes)
prev=decode(old)
clean=Image.open(cleanpath).convert("RGBA")
if clean.size!=(W,H):raise RuntimeError("clean plate wrong dimensions")
source=np.asarray(src,dtype=np.uint8)
base=np.asarray(clean,dtype=np.uint8)
previous=np.asarray(prev,dtype=np.uint8)
# Source effect bboxes measured from the canonical English HD DDS, not Korean pixels.
specs=[
    {"id":"start","english":"START","korean":"출발","source_bbox":[815,495,899,517],"size":[56,18],"right_lean_px":8},
    {"id":"goal","english":"GOAL","korean":"골","source_bbox":[1343,764,1417,787],"size":[33,18],"right_lean_px":8}
]
# A NEW source-conditioned render method, not B259 categorical cream repaint.
# Measure actual source English face colors and readable-space face centroid slope
# for each badge. This report is a material source-family construction input.
source_profile=[]
for item in specs:
    sx0,sy0,sx1,sy1=item["source_bbox"]
    patch=source[sy0:sy1,sx0:sx1,:3].astype(np.int16)
    # Warm cream/gold English pixels versus deep sign red (both native).
    cream=(patch[:,:,0]>=190)&(patch[:,:,1]>=100)&(patch[:,:,2]>=55)&(patch[:,:,1]>=patch[:,:,0]*0.46)
    ys,xs=np.nonzero(cream)
    if len(xs)<50:raise RuntimeError(("not enough source English face pixels",item["id"],len(xs)))
    pixels=patch[cream]
    # Source luminance/color percentiles drive RGB565 face endpoint and depth.
    bright=np.percentile(pixels,85,axis=0)
    mid=np.percentile(pixels,48,axis=0)
    bottom=np.percentile(pixels,20,axis=0)
    topcent=[float(np.median(xs[ys<max(2,int(patch.shape[0]*0.3))]))] if np.any(ys<max(2,int(patch.shape[0]*0.3))) else []
    botcent=[float(np.median(xs[ys>=int(patch.shape[0]*0.7)]))] if np.any(ys>=int(patch.shape[0]*0.7)) else []
    centroid_shift=round(topcent[0]-botcent[0],2) if topcent and botcent else None
    item["source_family"]={
        "source_face_pixel_count":int(len(xs)),
        "english_warm_face_rgb_p85":[int(round(v)) for v in bright],
        "english_warm_face_rgb_p48":[int(round(v)) for v in mid],
        "english_warm_face_rgb_p20":[int(round(v)) for v in bottom],
        "proxy_rightward_top_centroid_shift_px":centroid_shift,
        "proxy_limit":"Whole-word centroid not independent per-glyph slant anchor"
    }
    source_profile.append({"id":item["id"],"source_bbox":item["source_bbox"],**item["source_family"]})
(out/"B260_SOURCE_FAMILY_PROFILE.json").write_text(json.dumps({
   "schema_version":1,"method":"native English warm-face percentile source sampling + signed-distance Hangul surface",
   "source_sha256":SOURCE_SHA,"prior_rejected_sha256":PRIOR_SHA,
   "independent_rejections":["C285","C289"],"source_family":source_profile,
   "limitations":["Centroid proxy is not per-glyph slant measurement",
     "Colors estimated from visible canonical English face; BC3 palette may quantize gradients"]},ensure_ascii=False,indent=2)+"\n")

allowed=np.zeros((H,W),bool)
for r in specs:
    x0,y0,x1,y1=r["source_bbox"]
    allowed[y0:y1,x0:x1]=True
# Install and probe exact KR glyph coverage before altering bytes.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
subprocess.run(["fc-cache","-f"],check=True)
f=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Bold"],text=True).strip().split("|")
fontpath,fontidx,family=f[0],int(f[1] or "0"),f[2]
if "NotoSansCJK" not in Path(fontpath).name or "Noto Sans CJK KR" not in family:
    raise RuntimeError(("wrong glyph family",fontpath,fontidx,family))
font=ImageFont.truetype(fontpath,4*26,index=fontidx)
tofu=bytes(font.getmask(chr(0x10ffff)))
for ch in "출발골":
    bm=bytes(font.getmask(ch))
    if bm==tofu or not bm or not any(bm):raise RuntimeError(("tofu glyph",ch))
glyphkind=np.zeros((H,W),np.uint8)
previews=[]
for r in specs:
    w,h=r["size"]
    canvas=Image.new("L",(900,350),0)
    painter=ImageDraw.Draw(canvas)
    bb=painter.textbbox((0,0),r["korean"],font=font)
    painter.text((40-bb[0],40-bb[1]),r["korean"],font=font,fill=255)
    ink=canvas.getbbox()
    if not ink:raise RuntimeError(("no real glyph",r["id"]))
    mask=canvas.crop(ink).resize((w,h),Image.Resampling.LANCZOS)
    dx=r["right_lean_px"]
    mask=mask.transform((w+dx,h),Image.Transform.AFFINE,(1,dx/(h-1),-dx,0,1,0),
                        resample=Image.Resampling.BICUBIC)
    # Signed-distance reconstruction: an actual inner light face, 1px warm
    # bevel contour and offset dark-red extrusion, not B259's flat stroke mask.
    from scipy.ndimage import distance_transform_edt
    coverage=np.asarray(mask,dtype=np.uint8)
    core=coverage>=125
    if int(core.sum())<80:raise RuntimeError(("native face sparse",r["id"]))
    dist=distance_transform_edt(core)
    expanded=np.asarray(mask.filter(ImageFilter.MaxFilter(3)),dtype=np.uint8)>=70
    extruded=np.zeros_like(core)
    extruded[1:]=expanded[:-1]
    extruded[1:]|=expanded[:-1]  # a restrained one-pixel source-depth return
    class_local=np.zeros_like(core,np.uint8)
    class_local[extruded]=1
    class_local[expanded]=2
    class_local[core]=3
    # Only the outer-most real glyph contour gets gold bevel. The center is
    # protected as a continuous, luminous face for BC3 post-encode integrity.
    bevel=core&(dist<=1.05)
    class_local[bevel]=2
    if np.count_nonzero(class_local==3)<40:
        raise RuntimeError(("source bevel erodes inner Hangul too much",r["id"]))
    ly,lx=np.nonzero(class_local)
    if not len(lx):raise RuntimeError(("empty raster",r["id"]))
    xmin,xmax=int(lx.min()),int(lx.max())+1
    ymin,ymax=int(ly.min()),int(ly.max())+1
    tile=class_local[ymin:ymax,xmin:xmax]
    x0,y0,x1,y1=r["source_bbox"]
    cx=(x0+x1)//2; cy=(y0+y1)//2
    px=cx-tile.shape[1]//2;py=cy-tile.shape[0]//2
    # Partial BC3 edge blocks can contain protected red-rim/photo pixels.
    # Full blocks in readable space are [ceil(y0/4)*4, floor(y1/4)*4).
    # Constrain text to full source-contained blocks BEFORE encoding, with
    # independent +1px margin from the original English text-effect bbox.
    first_safe_y=((y0+3)//4)*4
    last_safe_y=(y1//4)*4
    if tile.shape[0]>last_safe_y-max(y0+1,first_safe_y):
        raise RuntimeError(("glyph too tall for safe complete BC3 blocks",r["id"],tile.shape))
    py=min(py,last_safe_y-tile.shape[0])
    py=max(py,max(y0+1,first_safe_y))
    if py+tile.shape[0]>last_safe_y:
        raise RuntimeError(("glyph would enter partial BC3 boundary",r["id"],py,tile.shape[0],last_safe_y))
    bound=[px,py,px+tile.shape[1],py+tile.shape[0]]
    margins=[px-x0,py-y0,x1-bound[2],y1-bound[3]]
    if min(margins)<1:raise RuntimeError(("glyph touches exact source boundary",r["id"],bound,margins))
    if np.any(glyphkind[py:bound[3],px:bound[2]]):raise RuntimeError("localized overlap")
    glyphkind[py:bound[3],px:bound[2]]=tile
    r["localized_bbox"]=bound
    r["margins"]=margins
    r["native_core_pixels"]=int(np.count_nonzero(tile==3))
    r["native_keyline_pixels"]=int(np.count_nonzero(tile==2))
    preview=Image.new("RGBA",(tile.shape[1],tile.shape[0]),(0,0,0,0))
    parr=np.asarray(preview).copy()
    parr[tile==1]=[155,56,32,255]
    parr[tile==2]=[238,141,73,255]
    parr[tile==3]=[255,242,205,255]
    Image.fromarray(parr,"RGBA").save(out/("B260_"+r["id"]+"_PREENCODE.png"))
if np.any((glyphkind>0)&~allowed):raise RuntimeError("glyph outside original text effect boxes")
# Compose ideal RGBA for human comparison, but QA uses actual saved BC3 decode.
ideal=base.copy()
ideal[glyphkind==1,:3]=[157,53,34]
ideal[glyphkind==2,:3]=[237,141,72]
ideal[glyphkind==3,:3]=[255,243,208]
ideal[glyphkind>0,3]=255
# BC3 4-color palette endpoints and indices, in DDS raw coordinate space.
def rgb565(rgb):
    r,g,b=[int(x) for x in rgb]
    return (round(r*31/255)<<11)|(round(g*63/255)<<5)|round(b*31/255)
def col565(v):
    return np.array([(v>>11&31)*255/31,(v>>5&63)*255/63,(v&31)*255/31],dtype=np.float64)
def palette(hi,lo):
    p0,p1=col565(hi),col565(lo)
    return np.array([p0,p1,(2*p0+p1)/3,(p0+2*p1)/3],dtype=np.float64)
def oldcolor(block):
    a=int.from_bytes(block[8:10],"little")
    b=int.from_bytes(block[10:12],"little")
    return palette(a,b)
def get_ci(block):
    z=int.from_bytes(block[12:16],"little")
    return [(z>>(2*i))&3 for i in range(16)]
def set_ci(block,idx):
    z=sum((int(idx[i])&3)<<(2*i) for i in range(16))
    return block[:12]+z.to_bytes(4,"little")
encoded=bytearray(old)
bw=W//4;bh=H//4
full=0;partial=0;retouched=0;face_blocks=0
rgba_raw=np.flipud(ideal)
kind_raw=np.flipud(glyphkind)
allowed_raw=np.flipud(allowed)
# Only visit source effect rectangles and their partial blocks.
block_ids=set()
for r in specs:
    x0,y0,x1,y1=r["source_bbox"]
    for y in range(y0//4,(y1+3)//4):
        for x in range(x0//4,(x1+3)//4):
            block_ids.add((x,bh-1-y))
for bx,by in sorted(block_ids):
    xx=bx*4;yy=by*4
    m=allowed_raw[yy:yy+4,xx:xx+4]
    if not np.any(m):continue
    off=128+(by*bw+bx)*16
    oldblock=bytes(encoded[off:off+16])
    pix=rgba_raw[yy:yy+4,xx:xx+4,:3]
    kind=kind_raw[yy:yy+4,xx:xx+4]
    if np.all(m):
        # Face-priority: never ask a generic compressor to interpolate tiny
        # cream strokes against red horizontally-striped badge backing.
        if np.any(kind):
            face_blocks+=1
            bgpix=pix[kind==0]
            plate_rgb=np.median(bgpix,axis=0) if len(bgpix) else np.array([220,25,44])
            # NEW: source English face P85/P48/P20 governs block color; B259
            # hand-written (255,251,226) flat face is forbidden by C285/C289.
            readable_y=H-1-yy
            family=next(i["source_family"] for i in specs
                        if i["source_bbox"][1] <= readable_y < i["source_bbox"][3])
            lo_y=next(i["source_bbox"][1] for i in specs
                      if i["source_bbox"][1] <= readable_y < i["source_bbox"][3])
            hi_y=next(i["source_bbox"][3] for i in specs
                      if i["source_bbox"][1] <= readable_y < i["source_bbox"][3])
            t=max(0.,min(1.,(readable_y-lo_y)/max(1,hi_y-lo_y-1)))
            a=np.asarray(family["english_warm_face_rgb_p85"],dtype=np.float64)
            b=np.asarray(family["english_warm_face_rgb_p48"],dtype=np.float64)
            cream=np.clip((1-t)*a+t*b,0,255).round().astype(np.uint8)
            # Cream endpoint must encode visibly luminous Korean center.
            cream[0]=max(cream[0],237)
            cream[1]=max(cream[1],191)
            cream[2]=max(cream[2],125)
            hi=rgb565(cream);lo=rgb565(plate_rgb)
            if hi<=lo:raise RuntimeError("BC3 endpoints invalid")
            idx=np.zeros((4,4),dtype=np.uint8)
            idx[kind==0]=1 # original red plate
            idx[kind==1]=3 # red-orange shadow
            idx[kind==2]=2 # source warm orange keyline
            idx[kind==3]=0 # full cream white face
        else:
            # Clean all old Korean/English from source-effect area, retain
            # source-derived red plate variation using red-family endpoints.
            colors=pix.reshape(-1,3).astype(np.float64)
            lumas=(colors[:,0]*0.5+colors[:,1]*0.4+colors[:,2]*0.1)
            hi=rgb565(colors[int(np.argmax(lumas))])
            lo=rgb565(colors[int(np.argmin(lumas))])
            if hi==lo:hi=min(65535,hi+1)
            if hi<lo:hi,lo=lo,hi
            pp=palette(hi,lo)
            idx=np.argmin(((colors[:,None,:]-pp[None,:,:])**2).sum(axis=2),axis=1).reshape(4,4)
        nb=oldblock[:8]+int(hi).to_bytes(2,"little")+int(lo).to_bytes(2,"little")
        nb=set_ci(nb+b"\x00\x00\x00\x00",idx.reshape(16))
        full+=1
    else:
        # Keep original BC3 endpoints + all protected texel indices *exact*.
        # Restore partial-edge English/B253 fragments only within original bbox.
        pp=oldcolor(oldblock)
        idx=get_ci(oldblock)
        for dy in range(4):
            for dx in range(4):
                if not m[dy,dx]:continue
                if kind[dy,dx]:
                    # Source bbox border with glyph is invalid: design should
                    # leave a positive margin on every side.
                    raise RuntimeError(("glyph enters partial boundary block",bx,by,dx,dy))
                # Choose the nearest source-red original BC3 palette entry.
                opts=[i for i,p in enumerate(pp) if p[0]>p[1]+34 and p[0]>p[2]+20]
                if not opts:
                    # This boundary block carries protected non-red artwork
                    # (e.g., adjacent badge white rim). B253's original color
                    # endpoints cannot represent a red clean plate here.
                    # Preserve its original indices rather than recolor.
                    continue
                color=pix[dy,dx].astype(np.float64)
                idx[dy*4+dx]=min(opts,key=lambda i:float(np.sum((pp[i]-color)**2)))
        nb=set_ci(oldblock,idx)
        partial+=1
    if nb!=oldblock:retouched+=1
    encoded[off:off+16]=nb
if bytes(encoded[:128])!=sourcebytes[:128]:raise RuntimeError("header mismatch")
# Validate exact saved DDS and the English source, not PNG approximation.
dst=bytes(encoded)
after=decode(dst)
actual=np.asarray(after,dtype=np.uint8)
delta=np.any(source!=actual,axis=2)
outside=int(np.count_nonzero(delta&~allowed))
alpha_out=int(np.count_nonzero((source[:,:,3]!=actual[:,:,3])&~allowed))
visible_out=int(np.count_nonzero((actual[:,:,3]>8)&(source[:,:,3]<=8)&~allowed))
if outside or alpha_out or visible_out:
    raise RuntimeError(("protected source pixel drift",outside,alpha_out,visible_out))
# The B253 prior may contain original colored English/scratch outside rectangles;
# do not let production reencode unrelated full atlas blocks.
oldout=int(np.count_nonzero(np.any(previous!=actual,axis=2)&~allowed))
if oldout:raise RuntimeError(("altered previous protected pixels",oldout))
integrity=[]
for r in specs:
    x0,y0,x1,y1=r["source_bbox"]
    origkind=glyphkind[y0:y1,x0:x1]
    img=actual[y0:y1,x0:x1,:3].astype(np.int16)
    face=(origkind==3)
    # Cream should remain visibly bright across the glyph's native scanlines.
    good=(img[:,:,0]>=220)&(img[:,:,1]>=155)&(img[:,:,2]>=85)
    ratio=float(np.count_nonzero(good&face))/max(1,np.count_nonzero(face))
    row_ratios=[]
    for row in range(face.shape[0]):
        n=int(face[row].sum())
        if n>=3:row_ratios.append(round(float((good[row]&face[row]).sum())/n,4))
    minimum=min(row_ratios) if row_ratios else 0
    integrity.append({"id":r["id"],"core_pixels":int(face.sum()),
        "bright_core_retention":round(ratio,4),"worst_native_scanline":minimum,
        "row_ratios":row_ratios})
    if ratio<0.965 or minimum<0.86:
        raise RuntimeError(("BC3 cream glyph has broken strokes",integrity[-1]))
# Actual DDS bytes only after confirmed generation+QA, file remains changed only
# within the measured original text-effect area.
path.write_bytes(dst)
if sha(path.read_bytes())!=sha(dst):raise RuntimeError("publish byte drift")
src.save(out/"B260_SOURCE_READABLE.png")
clean.save(out/"B260_CLEAN_PLATE.png")
Image.fromarray(ideal,"RGBA").save(out/"B260_PREENCODE_READABLE.png")
prev.save(out/"B260_PREVIOUS_READABLE.png")
after.save(out/"B260_FINAL_READABLE.png")
after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"B260_FINAL_RAW.png")
def over_bg(im,col=(115,115,115,255)):
    canvas=Image.new("RGBA",im.size,col)
    canvas.alpha_composite(im)
    return canvas.convert("RGB")
def make_contact():
    strips=[]
    for r in specs:
        x0,y0,x1,y1=r["source_bbox"]
        box=(x0-10,y0-7,x1+10,y1+7)
        tiles=[]
        for name,im in [("SOURCE",src),("CLEAN",clean),("B257_PREVIOUS",prev),("B260_NEW",after)]:
            crop=over_bg(im).crop(box)
            crop=crop.resize((crop.width*6,crop.height*6),Image.Resampling.NEAREST)
            tile=Image.new("RGB",(crop.width,crop.height+24),(35,35,35))
            tile.paste(crop,(0,24))
            ImageDraw.Draw(tile).text((3,4),r["id"]+" "+name,fill=(255,255,255))
            tiles.append(tile)
        strip=Image.new("RGB",(sum(t.width for t in tiles),max(t.height for t in tiles)),(35,35,35))
        px=0
        for t in tiles:strip.paste(t,(px,0));px+=t.width
        strips.append(strip)
    board=Image.new("RGB",(max(x.width for x in strips),sum(x.height for x in strips)+16),(35,35,35))
    py=0
    for im in strips:board.paste(im,(0,py));py+=im.height+16
    return board
make_contact().save(out/"B260_SOURCE_CLEAN_B253_NEW_NATIVE6X.png")
for percent in (100,75,50):
    dest=over_bg(after).resize((W*percent//100,H*percent//100),Image.Resampling.LANCZOS)
    dest.save(out/("B260_PRACTICAL_"+str(percent)+".png"))
report={
  "schema_version":2,"role":"B","run":RUN,"queue_index":214,"asset":asset,
  "source_sha256":SOURCE_SHA,"prior_rejected_candidate_sha256":PRIOR_SHA,
  "candidate_sha256":sha(dst),"format":"DXT5_BC3","size":[W,H],
  "header_exact":bytes(encoded[:128])==sourcebytes[:128],"raw_orientation":"mirror_y",
  "construction":"B260_METHOD_CHANGE: source English P85/P48/P20 per-region cream/gold palette sampling + signed-distance 1px bevel Hangul surface + BC3 per-block endpoint adaptation; explicitly replaces B259 flat categorical cream/shear retry",
  "font_coverage_probed":"출발골","native_masks":specs,
  "source_family_profile":source_profile,
  "convergence_triage":"METHOD_CHANGE_REQUIRED",
  "prior_rejections":["C285","C289"],
  "full_blocks_reencoded":full,"partial_blocks_protected_indices":partial,
  "changed_bc3_blocks":retouched,"blocks_with_new_hangul":face_blocks,
  "source_vs_candidate_changed_inside":int(np.count_nonzero(delta&allowed)),
  "source_vs_candidate_changed_outside":outside,
  "source_vs_candidate_alpha_outside":alpha_out,
  "source_vs_candidate_introduced_visible_outside":visible_out,
  "previous_vs_candidate_changed_outside":oldout,
  "post_encode_native_face_integrity":integrity,
  "machine_status":"PASS",
  "controller_visual_qa":"PENDING_CONTROLLER_DIRECT_PERSISTED_DDS_REVIEW",
  "independent_C2":"REQUIRED_NEW_SHA","C3":"BLOCKED_PENDING_C2",
  "PRE_INGAME":"BLOCKED_PENDING_EVIDENCE","RUNTIME_VALIDATION":"UNTESTED",
  "execution_backend":"GITHUB_HOSTED_CPU_DUE_TO_GPT_LOCAL_GITHUB_RAW_DNS_UNAVAILABLE",
  "forbidden_domains_touched":[]
}
reportpath=out/"B260_BF229CF4_REPORT.json"
reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
wr=loc/"worker_results/B260_BF229CF4.json"
wr.write_text(json.dumps({
  "role":"B","run":RUN,"queue_index":214,"asset":"BF229CF4",
  "source_sha256":SOURCE_SHA,"prior_sha256":PRIOR_SHA,
  "candidate_sha256":sha(dst),"status":"MACHINE_PASS_PENDING_CONTROLLER_VISUAL",
  "report":str(reportpath.relative_to(root)),"RUNTIME_VALIDATION":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print("B260_DONE",json.dumps({"sha":sha(dst),"blocks":retouched,"face":integrity,"outside":outside},ensure_ascii=False),flush=True)
