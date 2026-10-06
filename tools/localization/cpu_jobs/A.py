#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION119R-4F68708E"
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
prior_core_boxes=[[537,41,1350,126],[517,126,1610,213]]
source_lines=["Drive against the Ghost Car","and challenge for the course record!!"]
ko_lines=["고스트 카와 달리며","코스 기록에 도전하세요!"]
superseded_a119="bd7185f454abfd326e7609eb4826c1a22388617824cd25e00c211e73b648f889"

srcp=Path("/tmp/A119R_4F68708E.dds")
urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise RuntimeError("source drift")
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]
W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]
FOURCC=raw[84:88]
if (W,H,MIPS,FOURCC)!=(2048,256,1,b"DXT5"):
    raise RuntimeError(("structure",W,H,MIPS,FOURCC))
blocks_x=(W+3)//4; blocks_y=(H+3)//4
expected=blocks_x*blocks_y*16
if len(raw)!=128+expected: raise RuntimeError(("source payload length",len(raw),expected))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
source_visible=sa[:,:,3]>0

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

# Complete source-effect hard ceiling: use every decoded non-zero-alpha pixel.
# The low-alpha outer glow from the two physical lines overlaps at their boundary,
# so an exact per-line fringe split is not reliable. The entire two-line block is
# the hard decoded-pixel ceiling; the established per-line core boxes remain the
# line typography/layout references.
complete_bbox=bbox(source_visible)
if complete_bbox is None: raise RuntimeError("empty source")
cx0,cy0,cx1,cy1=complete_bbox
allowed=np.zeros((H,W),bool); allowed[cy0:cy1,cx0:cx1]=True
source_visible_outside=int(np.count_nonzero(source_visible & ~allowed))
if source_visible_outside: raise RuntimeError(("source outside complete bbox",source_visible_outside))

prior_union=np.zeros((H,W),bool)
for b in prior_core_boxes:
    x0,y0,x1,y1=b; prior_union[y0:y1,x0:x1]=True
prior_undercoverage=int(np.count_nonzero(source_visible & ~prior_union))
if prior_undercoverage<=0: raise RuntimeError(("expected prior undercoverage",prior_undercoverage))

# This DDS is text-only: no visible protected artwork exists outside complete_bbox.
outside_visible=int(np.count_nonzero(source_visible & ~allowed))
if outside_visible: raise RuntimeError(("protected visible outside",outside_visible))
clean_arr=sa.copy()
clean_arr[allowed]=0
clean=Image.fromarray(clean_arr,"RGBA")
if int(np.count_nonzero(clean_arr[:,:,3]))!=0:
    raise RuntimeError(("clean visible residue",int(np.count_nonzero(clean_arr[:,:,3]))))

opaque=sa[:,:,3]>=200
white=opaque&(sa[:,:,0]>190)&(sa[:,:,1]>190)&(sa[:,:,2]>190)
navy=opaque&(sa[:,:,0]<55)&(sa[:,:,1]<70)&(sa[:,:,2]<125)
if int(white.sum())<1000 or int(navy.sum())<1000:
    raise RuntimeError(("style sample",int(white.sum()),int(navy.sum())))
fill=tuple(int(x) for x in np.median(sa[white][:,:3],axis=0))+(255,)
stroke=tuple(int(x) for x in np.median(sa[navy][:,:3],axis=0))+(255,)
glow_rgb=(max(0,stroke[0]),min(255,stroke[1]+12),min(255,stroke[2]+28))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","imagemagick"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def shear(im,k):
    add=max(1,int(round(k*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)

def glyph_for(text,fs,inner,outer):
    font=ImageFont.truetype(FONT,fs)
    canvas=Image.new("RGBA",(1900,320),(0,0,0,0))
    gd=ImageDraw.Draw(canvas)
    tb=gd.textbbox((0,0),text,font=font,stroke_width=outer)
    ox=42-tb[0]; oy=42-tb[1]
    glow=Image.new("RGBA",canvas.size,(0,0,0,0))
    gdraw=ImageDraw.Draw(glow)
    gdraw.text((ox,oy),text,font=font,fill=glow_rgb+(205,),stroke_width=outer,stroke_fill=glow_rgb+(205,))
    glow=glow.filter(ImageFilter.GaussianBlur(radius=1.8))
    face=Image.new("RGBA",canvas.size,(0,0,0,0))
    fdraw=ImageDraw.Draw(face)
    fdraw.text((ox,oy),text,font=font,fill=fill,stroke_width=inner,stroke_fill=stroke)
    comp=Image.alpha_composite(glow,face)
    comp=shear(comp,0.24)
    gb=comp.getchannel("A").getbbox()
    if not gb: raise RuntimeError("empty glyph")
    return comp.crop(gb)

# Source lines share the same typography. Choose ONE common font/stroke/glow/shear
# that fits both source line references with positive margins.
chosen=None
for fs in range(64,40,-1):
    inner=max(4,round(fs*0.07))
    outer=inner+3
    glyphs=[glyph_for(t,fs,inner,outer) for t in ko_lines]
    ok=True
    for g,b in zip(glyphs,prior_core_boxes):
        x0,y0,x1,y1=b
        if g.width>(x1-x0)-12 or g.height>(y1-y0)-4:
            ok=False; break
    if ok:
        chosen=(fs,inner,outer,glyphs); break
if chosen is None: raise RuntimeError("no shared-style fit")
font_size,inner_stroke,outer_stroke,glyphs=chosen

desired=clean.copy()
target_masks=[]
rows=[]
for i,(g,b,text,ko) in enumerate(zip(glyphs,prior_core_boxes,source_lines,ko_lines)):
    x0,y0,x1,y1=b
    px=x0+6
    py=y0+((y1-y0)-g.height)//2
    if min(px-x0,py-y0,x1-(px+g.width),y1-(py+g.height))<=0:
        raise RuntimeError(("positive core margin",i,b,g.size,px,py))
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    layer.alpha_composite(g,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox(lm)
    if lb is None: raise RuntimeError(("empty target",i))
    if not (lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
        raise RuntimeError(("core containment",i,b,lb))
    if int(np.count_nonzero(lm & ~allowed)):
        raise RuntimeError(("complete block escape",i))
    desired.alpha_composite(layer)
    target_masks.append(lm)
    rows.append({
      "source":text,"korean":ko,
      "line_core_reference_bbox":b,
      "localized_preencode_bbox":lb,
      "font":"Noto Sans CJK KR Bold","font_size":font_size,
      "stroke_px":inner_stroke,"outer_glow_stroke_px":outer_stroke,"shear":0.24
    })

target=np.zeros((H,W),bool)
for m in target_masks: target|=m
if int(np.count_nonzero(target_masks[0]&target_masks[1])):
    raise RuntimeError("preencode row overlap")

combined_target_bbox=bbox(target)
if combined_target_bbox is None: raise RuntimeError("empty combined target")
if not (combined_target_bbox[0]>cx0 and combined_target_bbox[1]>cy0 and combined_target_bbox[2]<cx1 and combined_target_bbox[3]<cy1):
    raise RuntimeError(("combined containment",complete_bbox,combined_target_bbox))

# Encode desired raw image to DXT5.
desired_raw=desired.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/A119R_desired_raw.png"); desired_raw.save(tmp_png)
tmp_dds=Path("/tmp/A119R_desired_dxt5.dds")
subprocess.run(["convert",str(tmp_png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(tmp_dds)],check=True)
enc=tmp_dds.read_bytes()
if enc[:4]!=b"DDS " or enc[84:88]!=b"DXT5": raise RuntimeError(("encoded dds",enc[84:88]))
if (struct.unpack_from("<I",enc,16)[0],struct.unpack_from("<I",enc,12)[0])!=(W,H):
    raise RuntimeError("encoded dims")
if len(enc)<128+expected: raise RuntimeError(("encoded short",len(enc)))
enc_blocks=enc[128:128+expected]

raw_allowed=np.asarray(Image.fromarray((allowed*255).astype(np.uint8),"L").transpose(Image.Transpose.FLIP_TOP_BOTTOM))>0
raw_target=np.asarray(Image.fromarray((target*255).astype(np.uint8),"L").transpose(Image.Transpose.FLIP_TOP_BOTTOM))>0

def alpha_palette(a0,a1):
    if a0>a1:
        return [a0,a1,(6*a0+a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(a0+6*a1)//7]
    return [a0,a1,(4*a0+a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(a0+4*a1)//5,0,255]

def patch_partial_to_zero(block,inside):
    b=bytearray(block)
    pal=alpha_palette(b[0],b[1])
    zeros=[i for i,v in enumerate(pal) if v==0]
    if not zeros: raise RuntimeError(("partial block lacks alpha0",b[0],b[1],pal))
    zi=zeros[0]
    bits=int.from_bytes(b[2:8],"little")
    for yy in range(4):
        for xx in range(4):
            if inside[yy,xx]:
                p=yy*4+xx
                bits=(bits & ~(7<<(3*p))) | (zi<<(3*p))
    b[2:8]=bits.to_bytes(6,"little")
    return bytes(b)

out_blocks=bytearray(raw[128:])
full=partial=outside=partial_target=0
for by in range(blocks_y):
    for bx in range(blocks_x):
        y=by*4; x=bx*4
        m=raw_allowed[y:y+4,x:x+4]
        n=int(m.sum())
        off=(by*blocks_x+bx)*16
        if n==0:
            outside+=1; continue
        if n==16:
            full+=1
            out_blocks[off:off+16]=enc_blocks[off:off+16]
        else:
            partial+=1
            if int(np.count_nonzero(raw_target[y:y+4,x:x+4])):
                partial_target+=1
                raise RuntimeError(("target touches partial boundary",bx,by))
            out_blocks[off:off+16]=patch_partial_to_zero(bytes(out_blocks[off:off+16]),m)

payload=raw[:128]+bytes(out_blocks)
if len(payload)!=len(raw): raise RuntimeError("length drift")
if payload[:128]!=raw[:128]: raise RuntimeError("header drift")
candidate.write_bytes(payload)
cand_sha=hashlib.sha256(payload).hexdigest()

dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
changed=np.any(sa!=da,axis=2)
alpha_changed=sa[:,:,3]!=da[:,:,3]
outside_changed=int(np.count_nonzero(changed & ~allowed))
outside_alpha=int(np.count_nonzero(alpha_changed & ~allowed))
if outside_changed or outside_alpha:
    raise RuntimeError(("outside change",outside_changed,outside_alpha))

decoded_visible=da[:,:,3]>8
guard=ndimage.binary_dilation(target,iterations=3)
source_core=sa[:,:,3]>8
source_residue=int(np.count_nonzero(source_core & decoded_visible & ~guard))
unexpected_visible=int(np.count_nonzero(decoded_visible & ~ndimage.binary_dilation(target,iterations=4)))
if source_residue or unexpected_visible:
    raise RuntimeError(("residue",source_residue,unexpected_visible))

# Per-line decoded bbox is isolated by the non-overlapping core reference bands.
for i,row in enumerate(rows):
    x0,y0,x1,y1=row["line_core_reference_bbox"]
    m=np.zeros((H,W),bool)
    m[y0:y1,x0:x1]=(da[y0:y1,x0:x1,3]>0)
    db=bbox(m)
    if db is None: raise RuntimeError(("decoded line empty",i))
    if not (db[0]>x0 and db[1]>y0 and db[2]<x1 and db[3]<y1):
        raise RuntimeError(("decoded line containment",i,db,row["line_core_reference_bbox"]))
    deltas={"delta_left":db[0]-x0,"delta_right":x1-db[2],"delta_top":db[1]-y0,"delta_bottom":y1-db[3]}
    if min(deltas.values())<=0: raise RuntimeError(("line positive margin",i,deltas))
    row["localized_bbox"]=db
    row["source_width"]=x1-x0; row["source_height"]=y1-y0
    row["localized_width"]=db[2]-db[0]; row["localized_height"]=db[3]-db[1]
    row.update(deltas)
    row["containment"]="PASS"; row["size_ceiling"]="PASS"; row["positive_margin"]="PASS"

# Decoded row overlap/touch.
a=rows[0]["localized_bbox"]; b=rows[1]["localized_bbox"]
overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
vertical_gap=b[1]-a[3]
if overlap or vertical_gap<=0:
    raise RuntimeError(("row overlap/touch",overlap,vertical_gap,a,b))

decoded_combined=bbox(da[:,:,3]>0)
if decoded_combined is None: raise RuntimeError("decoded combined empty")
combined_deltas={
 "delta_left":decoded_combined[0]-cx0,
 "delta_right":cx1-decoded_combined[2],
 "delta_top":decoded_combined[1]-cy0,
 "delta_bottom":cy1-decoded_combined[3]
}
if min(combined_deltas.values())<=0:
    raise RuntimeError(("combined positive margin",complete_bbox,decoded_combined,combined_deltas))

# Evidence.
src.save(out/"A119R_SOURCE_READABLE.png")
src_raw.save(out/"A119R_SOURCE_RAW.png")
clean.save(out/"A119R_CLEAN_PLATE.png")
dec.save(out/"A119R_FINAL_READABLE.png")
dec_raw.save(out/"A119R_FINAL_RAW.png")
Image.fromarray((source_visible*255).astype(np.uint8),"L").save(out/"A119R_SOURCE_ALPHA_MASK.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"A119R_COMPLETE_SOURCE_BBOX_MASK.png")
Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A119R_TARGET_MASK.png")

def on_white(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")

pad=18
box=(max(0,cx0-pad),max(0,cy0-pad),min(W,cx1+pad),min(H,cy1+pad))
cards=[]
for lab,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
    v=on_white(im).crop(box)
    v=v.resize((v.width*2,v.height*2),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+34),"white"); c.paste(v,(0,34))
    ImageDraw.Draw(c).text((8,8),lab,fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+8 for c in cards)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((2600,1800),Image.Resampling.LANCZOS)
sheet.save(out/"A119R_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

linecards=[]
for i,b in enumerate(prior_core_boxes):
    x0,y0,x1,y1=b; p=12
    bx=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    for lab,im in [("SOURCE",src),("FINAL",dec)]:
        v=on_white(im).crop(bx).resize(((bx[2]-bx[0])*3,(bx[3]-bx[1])*3),Image.Resampling.NEAREST)
        c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30))
        ImageDraw.Draw(c).text((6,7),f"ROW{i+1} {lab}",fill="black"); linecards.append(c)
mw=max(c.width for c in linecards); mh=sum(c.height+6 for c in linecards)
ls=Image.new("RGB",(mw,mh),"white"); yy=0
for c in linecards:
    ls.paste(c,(0,yy)); yy+=c.height+6
ls.thumbnail((2600,2200),Image.Resampling.LANCZOS)
ls.save(out/"A119R_ROW_SOURCE_FINAL_CONTACT.jpg",quality=97)

rawsheet=Image.new("RGB",(1100,700),"white")
for i,(lab,im) in enumerate([("SOURCE RAW mirror_y",src_raw),("FINAL RAW mirror_y",dec_raw)]):
    v=on_white(im); v.thumbnail((1050,280),Image.Resampling.LANCZOS)
    y=i*335+30; rawsheet.paste(v,(20,y)); ImageDraw.Draw(rawsheet).text((20,y-22),lab,fill="black")
rawsheet.save(out/"A119R_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":idx,"asset":asset,
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "translation":{
   "semantic_source":"Drive against the Ghost Car and challenge for the course record!!",
   "semantic_korean":"고스트 카와 달리며 코스 기록에 도전하세요!",
   "physical_lines":[{"source":s,"korean":k} for s,k in zip(source_lines,ko_lines)]
 },
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "a117_a119_reconciliation":{
   "prior_core_boxes":prior_core_boxes,
   "prior_nonzero_source_pixels_outside_core_boxes":prior_undercoverage,
   "complete_multiline_effect_bbox":complete_bbox,
   "source_visible_outside_complete_bbox":source_visible_outside,
   "a119_rejected_candidate_sha256":superseded_a119,
   "a119_controller_reject_reason":"numeric PASS but shared-source typography was normalized inconsistently (54px row1 vs 57px row2), and low-alpha cross-line glow made per-line full-alpha fringe boxes unreliable. A119R uses one shared style and the complete two-line alpha footprint as the hard decoded-pixel ceiling."
 },
 "construction":{
   "clean_plate":"complete multiline effect bbox cleared to transparent; DDS is text-only with zero visible protected artwork outside",
   "render":"both physical Korean lines use one shared Noto Sans CJK KR Bold font size/stroke/glow/shear, source-sampled white/navy family and source-left anchors",
   "dxt5_boundary":"full-inside blocks use fresh desired DXT5 encode; partial boundary blocks preserve original endpoints/color bytes/outside indices and clear only in-bbox alpha using existing exact-zero palette entries; target glyphs never enter partial boundary blocks; outside blocks remain source-exact",
   "block_counts":{"full_inside":full,"partial_boundary":partial,"outside_unchanged":outside,"partial_target_blocks":partial_target}
 },
 "style":{"font":"Noto Sans CJK KR Bold","font_size":font_size,"fill_rgba":fill,"stroke_rgba":stroke,
          "stroke_px":inner_stroke,"glow_rgb":glow_rgb,"outer_glow_stroke_px":outer_stroke,"shear":0.24,
          "shared_across_lines":True},
 "hard_multiline_gate":{
   "original_bbox":complete_bbox,"localized_bbox":decoded_combined,
   "source_width":cx1-cx0,"source_height":cy1-cy0,
   "localized_width":decoded_combined[2]-decoded_combined[0],
   "localized_height":decoded_combined[3]-decoded_combined[1],
   **combined_deltas,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
 },
 "elements":rows,
 "static_qa":{
   "prior_core_undercoverage_pixels":prior_undercoverage,
   "source_visible_outside_complete_bbox":source_visible_outside,
   "changed_pixels_outside_complete_bbox":outside_changed,
   "alpha_changed_outside_complete_bbox":outside_alpha,
   "source_residue_outside_korean_guard":source_residue,
   "unexpected_visible_pixels_outside_korean_guard":unexpected_visible,
   "localized_row_overlap_pixels":overlap,
   "localized_row_vertical_gap":vertical_gap,
   "shared_line_style":"PASS",
   "header_128_exact":payload[:128]==raw[:128],
   "dds_size_preserved":len(payload)==len(raw),
   "status":"PASS"
 },
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"A119R_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A119R_4F68708E_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A119R_4F68708E.json").write_text(json.dumps({
 "role":"A","run":run,"queue_index":idx,"asset":"4F68708E","source_sha256":SOURCE_SHA,
 "candidate_sha256":cand_sha,"superseded_a119_candidate_sha256":superseded_a119,
 "complete_source_bbox":complete_bbox,"localized_bbox":decoded_combined,
 "shared_font_size":font_size,"shared_style":True,"vertical_gap":vertical_gap,
 "outside_changed":outside_changed,"alpha_outside":outside_alpha,"source_residue":source_residue,"overlap":overlap,
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
 "run":run,"candidate_sha256":cand_sha,"complete_source_bbox":complete_bbox,
 "font_size":font_size,"vertical_gap":vertical_gap,
 "rows":[{"ko":r["korean"],"core":r["line_core_reference_bbox"],"localized":r["localized_bbox"],
          "deltas":[r["delta_left"],r["delta_right"],r["delta_top"],r["delta_bottom"]]} for r in rows],
 "status":"A119R_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
},ensure_ascii=False),flush=True)
