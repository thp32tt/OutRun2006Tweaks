#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION119-4F68708E"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

idx=99
asset="textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
SOURCE_SHA="d97206d8ab5e0898c81d9cc0d6562db1a381894b0fa3e2d9fa75303867a638e2"
prior_bboxes=[[537,41,1350,126],[517,126,1610,213]]
ko_lines=["고스트 카와 달리며","코스 기록에 도전하세요!"]

srcp=Path("/tmp/A119_4F68708E.dds")
urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:
    raise RuntimeError("source drift")
if raw[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]
W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]
FOURCC=raw[84:88]
if (W,H,MIPS,FOURCC)!=(2048,256,1,b"DXT5"):
    raise RuntimeError(("structure",W,H,MIPS,FOURCC))
blocks_x=(W+3)//4; blocks_y=(H+3)//4
expected=blocks_x*blocks_y*16
if len(raw)!=128+expected:
    raise RuntimeError(("source payload length",len(raw),expected))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>0

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

# A117 proved 606 source-visible pixels existed outside the older threshold bboxes.
# Re-derive the *complete* physical line footprints from every decoded non-zero alpha
# pixel. 126 is the source line break already established by the original two-row
# layout; assigning fringe pixels on either side to one physical row does not alter
# the union, and the union must cover every visible source pixel exactly.
yygrid=np.indices((H,W))[0]
line_masks=[alpha&(yygrid<126),alpha&(yygrid>=126)]
source_bboxes=[bbox(m) for m in line_masks]
if any(b is None for b in source_bboxes):
    raise RuntimeError(("empty line",source_bboxes))
union_rect=np.zeros((H,W),bool)
for b in source_bboxes:
    x0,y0,x1,y1=b
    union_rect[y0:y1,x0:x1]=True
source_visible_outside=int(np.count_nonzero(alpha & ~union_rect))
if source_visible_outside:
    raise RuntimeError(("full source footprint not covered",source_visible_outside,source_bboxes))

# The old bboxes are diagnostic only; quantify exactly why they were unsafe.
prior_union=np.zeros((H,W),bool)
for b in prior_bboxes:
    x0,y0,x1,y1=b; prior_union[y0:y1,x0:x1]=True
prior_nonzero_outside=int(np.count_nonzero(alpha & ~prior_union))
if prior_nonzero_outside<=0:
    raise RuntimeError(("expected A117 threshold-bbox undercoverage",prior_nonzero_outside))

# Clean plate is fully transparent inside the complete source text rectangles.
# This atlas contains no protected non-text visible pixels outside those physical rows.
clean_arr=sa.copy()
clean_arr[union_rect]=0
clean=Image.fromarray(clean_arr,"RGBA")
if int(np.count_nonzero(clean_arr[:,:,3]))!=0:
    raise RuntimeError(("unexpected protected visible pixels outside source rows",int(np.count_nonzero(clean_arr[:,:,3]))))

# Sample source family from robust opaque pixels.
opaque=sa[:,:,3]>=200
white=opaque&(sa[:,:,0]>190)&(sa[:,:,1]>190)&(sa[:,:,2]>190)
navy=opaque&(sa[:,:,0]<55)&(sa[:,:,1]<70)&(sa[:,:,2]<125)
if int(white.sum())<1000 or int(navy.sum())<1000:
    raise RuntimeError(("style samples",int(white.sum()),int(navy.sum())))
fill=tuple(int(x) for x in np.median(sa[white][:,:3],axis=0))+(255,)
stroke=tuple(int(x) for x in np.median(sa[navy][:,:3],axis=0))+(255,)
glow_rgb=(max(0,stroke[0]),min(255,stroke[1]+12),min(255,stroke[2]+28))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","imagemagick"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not FONT or not Path(FONT).exists():
    raise RuntimeError(("font",FONT))

def shear(im,k):
    add=max(1,int(round(k*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)

def render_line(text,box):
    x0,y0,x1,y1=box
    sw=x1-x0; sh=y1-y0
    # Fit largest source-height-faithful Korean render while retaining >=6px decoded
    # safety margin so fresh color blocks never touch partial DXT5 boundary blocks.
    for fs in range(min(92,sh),40,-1):
        inner=max(4,round(fs*0.075))
        outer=inner+3
        canvas=Image.new("RGBA",(max(1800,sw*2),max(320,sh*3)),(0,0,0,0))
        # Soft blue/navy family glow.
        glow=Image.new("RGBA",canvas.size,(0,0,0,0))
        gd=ImageDraw.Draw(glow)
        font=ImageFont.truetype(FONT,fs)
        tb=gd.textbbox((0,0),text,font=font,stroke_width=outer)
        ox=40-tb[0]; oy=40-tb[1]
        gd.text((ox,oy),text,font=font,fill=glow_rgb+(210,),stroke_width=outer,stroke_fill=glow_rgb+(210,))
        glow=glow.filter(ImageFilter.GaussianBlur(radius=2.2))
        base=Image.new("RGBA",canvas.size,(0,0,0,0))
        bd=ImageDraw.Draw(base)
        bd.text((ox,oy),text,font=font,fill=fill,stroke_width=inner,stroke_fill=stroke)
        comp=Image.alpha_composite(glow,base)
        comp=shear(comp,0.24)
        gb=comp.getchannel("A").getbbox()
        if not gb: continue
        glyph=comp.crop(gb)
        if glyph.width>sw-16 or glyph.height>sh-12:
            continue
        px=x0+8
        py=y0+(sh-glyph.height)//2
        # keep at least 6 px on every side, target deliberately away from partial blocks
        if min(px-x0,py-y0,x1-(px+glyph.width),y1-(py+glyph.height))<6:
            continue
        return glyph,px,py,fs,inner,outer
    raise RuntimeError(("no line fit",text,box))

desired=clean.copy()
target_masks=[]
rows=[]
for text,box in zip(ko_lines,source_bboxes):
    glyph,px,py,fs,inner,outer=render_line(text,box)
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    layer.alpha_composite(glyph,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox(lm)
    if lb is None: raise RuntimeError("empty target")
    x0,y0,x1,y1=box
    if not (lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
        raise RuntimeError(("target containment",text,box,lb))
    if (lb[2]-lb[0])>(x1-x0) or (lb[3]-lb[1])>(y1-y0):
        raise RuntimeError(("target size",text,box,lb))
    if target_masks and np.count_nonzero(target_masks[-1]&lm):
        raise RuntimeError(("target overlap",text))
    desired.alpha_composite(layer)
    target_masks.append(lm)
    rows.append({
      "source": ["Drive against the Ghost Car","and challenge for the course record!!"][len(rows)],
      "korean":text,
      "original_bbox":box,
      "localized_preencode_bbox":lb,
      "font":"Noto Sans CJK KR Bold",
      "font_size":fs,
      "stroke_px":inner,
      "outer_glow_stroke_px":outer,
      "shear":0.24
    })

target=np.zeros((H,W),bool)
for m in target_masks: target|=m
if int(np.count_nonzero(target & ~union_rect)):
    raise RuntimeError("target outside source rectangles")

# Encode complete desired raw-orientation image, then splice only exact-safe DXT5 blocks.
desired_raw=desired.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/A119_desired_raw.png"); desired_raw.save(tmp_png)
tmp_dds=Path("/tmp/A119_desired_dxt5.dds")
subprocess.run(["convert",str(tmp_png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(tmp_dds)],check=True)
enc=tmp_dds.read_bytes()
if enc[:4]!=b"DDS " or enc[84:88]!=b"DXT5":
    raise RuntimeError(("encoded DDS",enc[84:88]))
if (struct.unpack_from("<I",enc,16)[0],struct.unpack_from("<I",enc,12)[0])!=(W,H):
    raise RuntimeError("encoded dims")
if len(enc)<128+expected:
    raise RuntimeError(("encoded payload short",len(enc)))
enc_blocks=enc[128:128+expected]

# Convert readable allowed rectangles/target mask to raw mirror-Y.
raw_allowed=np.asarray(Image.fromarray((union_rect*255).astype(np.uint8),"L").transpose(Image.Transpose.FLIP_TOP_BOTTOM))>0
raw_target=np.asarray(Image.fromarray((target*255).astype(np.uint8),"L").transpose(Image.Transpose.FLIP_TOP_BOTTOM))>0

def alpha_palette(a0,a1):
    if a0>a1:
        return [a0,a1,(6*a0+a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(a0+6*a1)//7]
    return [a0,a1,(4*a0+a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(a0+4*a1)//5,0,255]

def patch_partial_to_zero(block,inside):
    b=bytearray(block)
    pal=alpha_palette(b[0],b[1])
    zero=[i for i,v in enumerate(pal) if v==0]
    if not zero:
        raise RuntimeError(("partial block lacks exact alpha zero",b[0],b[1],pal))
    zi=zero[0]
    bits=int.from_bytes(b[2:8],"little")
    for yy in range(4):
        for xx in range(4):
            if inside[yy,xx]:
                p=yy*4+xx
                bits=(bits & ~(7<<(3*p))) | (zi<<(3*p))
    b[2:8]=bits.to_bytes(6,"little")
    return bytes(b)

out_blocks=bytearray(raw[128:])
full=partial=outside=0
partial_target=0
for by in range(blocks_y):
    for bx in range(blocks_x):
        y=by*4; x=bx*4
        m=raw_allowed[y:y+4,x:x+4]
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
            if int(np.count_nonzero(raw_target[y:y+4,x:x+4])):
                partial_target+=1
                raise RuntimeError(("target touches partial boundary block",bx,by))
            out_blocks[off:off+16]=patch_partial_to_zero(bytes(out_blocks[off:off+16]),m)

payload=raw[:128]+bytes(out_blocks)
if len(payload)!=len(raw): raise RuntimeError("DDS length drift")
if payload[:128]!=raw[:128]: raise RuntimeError("header drift")
candidate.write_bytes(payload)
cand_sha=hashlib.sha256(payload).hexdigest()

dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
changed=np.any(sa!=da,axis=2)
alpha_changed=sa[:,:,3]!=da[:,:,3]
outside_changed=int(np.count_nonzero(changed & ~union_rect))
outside_alpha=int(np.count_nonzero(alpha_changed & ~union_rect))
if outside_changed or outside_alpha:
    raise RuntimeError(("outside decoded change",outside_changed,outside_alpha))

# Every source-visible pixel belongs to the two source rows; after rebuild, no source
# lettering may survive except where covered by the new Korean family.
guard=ndimage.binary_dilation(target,iterations=3)
source_core=sa[:,:,3]>8
decoded_visible=da[:,:,3]>8
source_residue=int(np.count_nonzero(source_core & decoded_visible & ~guard))
unexpected_visible=int(np.count_nonzero(decoded_visible & ~ndimage.binary_dilation(target,iterations=4)))
if source_residue or unexpected_visible:
    raise RuntimeError(("decoded residue",source_residue,unexpected_visible))

# Decoded per-line bboxes and mandatory positive margins.
for i,row in enumerate(rows):
    x0,y0,x1,y1=row["original_bbox"]
    local=(da[:,:,3]>0)&np.indices((H,W))[1].astype(bool)  # placeholder shape reuse
    # isolate this row by source rectangle
    m=(da[:,:,3]>0)
    sub=np.zeros((H,W),bool); sub[y0:y1,x0:x1]=m[y0:y1,x0:x1]
    db=bbox(sub)
    if db is None: raise RuntimeError(("decoded empty",i))
    # Since source rectangles are vertically disjoint, this is the row's decoded family.
    if not (db[0]>=x0 and db[1]>=y0 and db[2]<=x1 and db[3]<=y1):
        raise RuntimeError(("decoded containment",i,row["original_bbox"],db))
    deltas={"delta_left":db[0]-x0,"delta_right":x1-db[2],"delta_top":db[1]-y0,"delta_bottom":y1-db[3]}
    if min(deltas.values())<=0:
        raise RuntimeError(("decoded positive margin",i,deltas))
    row["localized_bbox"]=db
    row["source_width"]=x1-x0; row["source_height"]=y1-y0
    row["localized_width"]=db[2]-db[0]; row["localized_height"]=db[3]-db[1]
    row.update(deltas)
    row["containment"]="PASS"; row["size_ceiling"]="PASS"; row["positive_margin"]="PASS"

# Explicit no-overlap on decoded physical rows.
r0=rows[0]["localized_bbox"]; r1=rows[1]["localized_bbox"]
overlap_rect=max(0,min(r0[2],r1[2])-max(r0[0],r1[0]))*max(0,min(r0[3],r1[3])-max(r0[1],r1[1]))
if overlap_rect:
    raise RuntimeError(("decoded row bbox overlap",r0,r1))

# Evidence
src.save(out/"A119_SOURCE_READABLE.png")
src_raw.save(out/"A119_SOURCE_RAW.png")
clean.save(out/"A119_CLEAN_PLATE.png")
dec.save(out/"A119_FINAL_READABLE.png")
dec_raw.save(out/"A119_FINAL_RAW.png")
Image.fromarray((alpha*255).astype(np.uint8),"L").save(out/"A119_SOURCE_ALPHA_MASK.png")
Image.fromarray((union_rect*255).astype(np.uint8),"L").save(out/"A119_EXACT_SOURCE_RECTS.png")
Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A119_TARGET_MASK.png")

def on_white(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")

# Full/source-clean-final contact
cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
    v=on_white(im)
    bb=[min(b[0] for b in source_bboxes)-24,min(b[1] for b in source_bboxes)-16,
        max(b[2] for b in source_bboxes)+24,max(b[3] for b in source_bboxes)+16]
    box=(max(0,bb[0]),max(0,bb[1]),min(W,bb[2]),min(H,bb[3]))
    v=v.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+34),"white"); c.paste(v,(0,34))
    ImageDraw.Draw(c).text((8,8),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+8 for c in cards)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((2600,1800),Image.Resampling.LANCZOS)
sheet.save(out/"A119_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

# Per-line source/final zoom contact.
linecards=[]
for i,b in enumerate(source_bboxes):
    x0,y0,x1,y1=b; pad=12
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    for lab,im in [("SOURCE",src),("FINAL",dec)]:
        v=on_white(im).crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3),Image.Resampling.NEAREST)
        c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30))
        ImageDraw.Draw(c).text((6,7),f"ROW{i+1} {lab}",fill="black"); linecards.append(c)
mw=max(c.width for c in linecards); mh=sum(c.height+6 for c in linecards)
ls=Image.new("RGB",(mw,mh),"white"); yy=0
for c in linecards:
    ls.paste(c,(0,yy)); yy+=c.height+6
ls.thumbnail((2600,2200),Image.Resampling.LANCZOS)
ls.save(out/"A119_ROW_SOURCE_FINAL_CONTACT.jpg",quality=97)

rawsheet=Image.new("RGB",(1100,700),"white")
for i,(lab,im) in enumerate([("SOURCE RAW mirror_y",src_raw),("FINAL RAW mirror_y",dec_raw)]):
    v=on_white(im); v.thumbnail((1050,280),Image.Resampling.LANCZOS)
    y=i*335+30; rawsheet.paste(v,(20,y)); ImageDraw.Draw(rawsheet).text((20,y-22),lab,fill="black")
rawsheet.save(out/"A119_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":idx,"asset":asset,
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "translation":{
   "semantic_source":"Drive against the Ghost Car and challenge for the course record!!",
   "semantic_korean":"고스트 카와 달리며 코스 기록에 도전하세요!",
   "physical_lines":[
     {"source":"Drive against the Ghost Car","korean":ko_lines[0]},
     {"source":"and challenge for the course record!!","korean":ko_lines[1]}
   ]
 },
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "a117_reconciliation":{
   "prior_threshold_bboxes":prior_bboxes,
   "prior_nonzero_source_pixels_outside_bboxes":prior_nonzero_outside,
   "complete_source_bboxes":source_bboxes,
   "nonzero_source_pixels_outside_complete_bboxes":source_visible_outside,
   "decision":"A117 HOLD was caused by under-covered threshold bboxes. A119 expands each physical source line to the complete decoded non-zero alpha footprint before DXT5 boundary construction."
 },
 "construction":{
   "clean_plate":"all complete source-line rectangles cleared to transparent; atlas has zero protected non-text visible pixels outside them",
   "render":"native 2048x256 Noto Sans CJK KR Bold, source-sampled white fill/navy outline, soft blue/navy outer glow, 0.24 right shear, two physical Korean lines",
   "dxt5_boundary":"full-inside blocks use fresh desired DXT5 encode; partial blocks preserve original endpoints/color bytes/outside indices and only clear inside alpha via an existing exact-zero palette entry; target lettering is prohibited from partial boundary blocks; outside blocks remain byte-identical",
   "block_counts":{"full_inside":full,"partial_boundary":partial,"outside_unchanged":outside,"partial_target_blocks":partial_target}
 },
 "style":{"font":"Noto Sans CJK KR Bold","fill_rgba":fill,"stroke_rgba":stroke,"glow_rgb":glow_rgb,"shear":0.24},
 "elements":rows,
 "static_qa":{
   "prior_bbox_undercoverage_pixels":prior_nonzero_outside,
   "complete_source_visible_outside_rects":source_visible_outside,
   "changed_pixels_outside_complete_source_rects":outside_changed,
   "alpha_changed_outside_complete_source_rects":outside_alpha,
   "source_residue_outside_korean_guard":source_residue,
   "unexpected_visible_pixels_outside_korean_guard":unexpected_visible,
   "localized_row_bbox_overlap":overlap_rect,
   "header_128_exact":payload[:128]==raw[:128],
   "dds_size_preserved":len(payload)==len(raw),
   "status":"PASS"
 },
 "candidate_path":str(candidate.relative_to(repo)),
 "candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"A119_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A119_4F68708E_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A119_4F68708E.json").write_text(json.dumps({
 "role":"A","run":run,"queue_index":idx,"asset":"4F68708E",
 "source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "prior_bbox_undercoverage_pixels":prior_nonzero_outside,
 "complete_source_bboxes":source_bboxes,
 "elements":[{"original_bbox":r["original_bbox"],"localized_bbox":r["localized_bbox"],
              "deltas":{k:r[k] for k in ["delta_left","delta_right","delta_top","delta_bottom"]}} for r in rows],
 "outside_changed":outside_changed,"alpha_outside":outside_alpha,
 "source_residue":source_residue,"overlap":overlap_rect,
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
 "run":run,"candidate_sha256":cand_sha,"source_bboxes":source_bboxes,
 "prior_bbox_undercoverage_pixels":prior_nonzero_outside,
 "rows":[{"ko":r["korean"],"original_bbox":r["original_bbox"],"localized_bbox":r["localized_bbox"],
          "deltas":[r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"]],
          "font_size":r["font_size"]} for r in rows],
 "blocks":{"full":full,"partial":partial,"outside":outside},
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
},ensure_ascii=False),flush=True)
