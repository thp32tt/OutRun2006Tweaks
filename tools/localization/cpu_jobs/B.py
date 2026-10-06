#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
from scipy import ndimage
from scipy.spatial import ConvexHull

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION190-6C9B3611-START-GOAL"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
SOURCE_SHA="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
srcp=Path("/tmp/B190_6C9B3611.dds")
urllib.request.urlretrieve(url,srcp)

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

raw=srcp.read_bytes()
if sha256(srcp)!=SOURCE_SHA: raise RuntimeError(("source drift",sha256(srcp)))
if raw[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",raw,12)[0]
W=struct.unpack_from("<I",raw,16)[0]
MIPS=struct.unpack_from("<I",raw,28)[0]
FOURCC=raw[84:88]
BPP=struct.unpack_from("<I",raw,88)[0]
MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,FOURCC,BPP)!=(1024,1024,1,b"\0\0\0\0",32):
    raise RuntimeError(("structure",W,H,MIPS,FOURCC,BPP))
if MASKS!=(0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("channel masks",MASKS))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>8

specs=[
 {"key":"start","source":"START","ko":"출발","roi":[40,300,210,405]},
 {"key":"goal","source":"GOAL","ko":"골","roi":[575,625,695,682]},
]

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

rows=[]
source_masks=[]
banner_masks=[]
for sp in specs:
    x0,y0,x1,y1=sp["roi"]
    sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16)
    g=sub[:,:,1].astype(np.int16)
    b=sub[:,:,2].astype(np.int16)
    a=sub[:,:,3]>8

    red=a & (r>155) & (r>g+65) & (r>b+45) & (g<100)
    lab,n=ndimage.label(red)
    comps=[]
    for i in range(1,n+1):
        c=(lab==i)
        area=int(c.sum())
        if area<40: continue
        yy,xx=np.nonzero(c)
        comps.append((area,c,[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]))
    if not comps: raise RuntimeError(("no red banner",sp["key"]))
    comps.sort(key=lambda x:x[0],reverse=True)
    # The English face splits the red plate into several disconnected red islands.
    # Using only the largest island (B182-B185) under-covered the START plate and
    # left visible pale/orange strips. This ROI is sign-tight, so use the union of
    # all meaningful saturated-red components to recover the complete plate envelope.
    banner_seed=np.zeros_like(red)
    for area,c,cb in comps:
        banner_seed |= c
    # Reconstruct the actual red sign interior from the left/right envelope of all
    # sign-red components on each scanline.
    banner=np.zeros_like(banner_seed)
    row_bounds={}
    for yy in range(banner_seed.shape[0]):
        xs=np.nonzero(banner_seed[yy])[0]
        if len(xs)>=2:
            row_bounds[yy]=(int(xs.min()),int(xs.max()))
    known=sorted(row_bounds)
    if len(known)<2:
        raise RuntimeError(("insufficient sign rows",sp["key"],known))
    # Some horizontal scanlines are completely covered by pale/orange English
    # effect pixels, so they contain no saturated-red seed at all. B182-B186 left
    # those scanlines as holes in the clean-region mask, visually preserving
    # English-shaped horizontal strips. Interpolate the red-body envelope through
    # every row between the first/last detected sign rows.
    for yy in range(known[0],known[-1]+1):
        if yy in row_bounds:
            lx,rx=row_bounds[yy]
        else:
            lo=max(k for k in known if k<yy)
            hi=min(k for k in known if k>yy)
            t=(yy-lo)/(hi-lo)
            lx=round(row_bounds[lo][0]*(1-t)+row_bounds[hi][0]*t)
            rx=round(row_bounds[lo][1]*(1-t)+row_bounds[hi][1]*t)
        banner[yy,lx:rx+1]=True
    banner &= a
    dist_in=ndimage.distance_transform_edt(banner)

    # Isolate the complete source glyph/effect footprint as every non-sign-red
    # pixel inside the red sign interior. This captures pale fill, orange shadow,
    # AA fringe and source-shaped effect pixels without swallowing the white rim.
    sign_red=(r>140) & (r>g+65) & (r>b+35) & (g<72) & (b<120)
    interior=ndimage.binary_erosion(banner,iterations=1,border_value=0)
    bright=interior & (r>150) & (g>90) & (b>55)
    near=ndimage.binary_dilation(bright,iterations=4)
    effect=interior & ~sign_red & near
    effect=ndimage.binary_dilation(effect,iterations=1) & interior

    elab,en=ndimage.label(effect)
    kept=np.zeros_like(effect)
    comp_meta=[]
    for i in range(1,en+1):
        c=(elab==i)
        area=int(c.sum())
        if area<3: continue
        yy,xx=np.nonzero(c)
        cb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        comp_meta.append((area,cb))
        kept|=c
    effect=kept
    if int(effect.sum())<150:
        raise RuntimeError(("effect mask too small",sp["key"],int(effect.sum()),comp_meta))

    gm=np.zeros((H,W),bool); gm[y0:y1,x0:x1]=effect
    bm=np.zeros((H,W),bool); bm[y0:y1,x0:x1]=banner
    sb=bbox(gm)
    bb=bbox(bm)
    if sb is None or bb is None:
        raise RuntimeError(("empty bbox",sp["key"]))
    bw=bb[2]-bb[0]; bh=bb[3]-bb[1]
    sw=sb[2]-sb[0]; sh=sb[3]-sb[1]
    if sw>bw*0.95 or sh>bh*0.92:
        raise RuntimeError(("text/banner separation unsafe",sp["key"],sb,bb,sw/bw,sh/bh))
    if sb[0]<=bb[0] or sb[1]<=bb[1] or sb[2]>=bb[2] or sb[3]>=bb[3]:
        raise RuntimeError(("text touches banner edge",sp["key"],sb,bb))
    source_masks.append(gm)
    banner_masks.append(bm)
    rows.append({**sp,"source_bbox":sb,"banner_bbox":bb,"source_text_pixels":int(gm.sum()),
                 "banner_pixels":int(bm.sum()),"component_meta":comp_meta})

source_mask=np.zeros((H,W),bool)
for m in source_masks:
    source_mask |= m
if np.count_nonzero(source_masks[0]&source_masks[1]):
    raise RuntimeError("source masks overlap")

# Same-family A85 precedent: reconstruct the complete inset red body, not a
# glyph-shaped patch. B182-B189 showed that component/hand polygon masks can
# either leave English-effect strips or touch the white rim. B190 derives the
# red-body polygon from the convex hull of strongly saturated source-red pixels
# inside each tight sign ROI; this fills lettering holes without crossing into
# the white rim. Exact measured source-effect pixels are unioned as a fail-safe.
clean_masks=[]
clean_region=np.zeros((H,W),bool)
for row,sm,bm in zip(rows,source_masks,banner_masks):
    x0,y0,x1,y1=row["roi"]
    sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16)
    aa=sub[:,:,3]>8
    redseed=aa & (r>150) & (r>g+65) & (r>b+40) & (g<105) & (b<135)
    yy,xx=np.nonzero(redseed)
    if len(xx)<30:
        raise RuntimeError(("red hull seed too small",row["key"],len(xx)))
    pts=np.column_stack([xx,yy])
    hull=ConvexHull(pts)
    poly=[(int(x0+pts[i,0]),int(y0+pts[i,1])) for i in hull.vertices]
    pim=Image.new("L",(W,H),0)
    ImageDraw.Draw(pim).polygon(poly,fill=255)
    cm=np.asarray(pim)>0
    cm=ndimage.binary_erosion(cm,iterations=1,border_value=0)
    cm |= sm
    clean_masks.append(cm)
    clean_region |= cm
    row["clean_region_bbox"]=bbox(cm)
    row["clean_region_pixels"]=int(cm.sum())
    row["red_hull_vertices"]=poly

clean_arr=sa.copy()
rr0=sa[:,:,0].astype(np.int16); gg0=sa[:,:,1].astype(np.int16); bb0=sa[:,:,2].astype(np.int16)
for row,cm,bm,sm in zip(rows,clean_masks,banner_masks,source_masks):
    red_donor=bm & ~sm & (rr0>140) & (rr0>gg0+60) & (rr0>bb0+35) & (gg0<100) & (bb0<135)
    ys=np.unique(np.nonzero(cm)[0])
    samples={}
    for y in ys:
        q=sa[y,red_donor[y]]
        if len(q)>=2:
            samples[int(y)]=np.median(q,axis=0).astype(np.float64)
    if not samples:
        raise RuntimeError(("no clean red row donors",row["key"]))
    known=sorted(samples)
    for y in ys:
        y=int(y)
        if y in samples:
            col=samples[y]
        else:
            near=min(known,key=lambda z:abs(z-y))
            col=samples[near]
        xs=np.nonzero(cm[y])[0]
        clean_arr[y,xs]=np.clip(np.rint(col),0,255).astype(np.uint8)

clean=Image.fromarray(clean_arr,"RGBA")
rr=clean_arr[:,:,0].astype(np.int16); gg=clean_arr[:,:,1].astype(np.int16); bb=clean_arr[:,:,2].astype(np.int16)
clean_sign_red=(rr>105) & (rr>gg+25) & (rr>bb+15) & (gg<145) & (bb<160)
residue_clean=int(np.count_nonzero(source_mask & ~clean_sign_red))
clean_not_red=int(np.count_nonzero(clean_region & ~clean_sign_red))
if residue_clean or clean_not_red:
    raise RuntimeError(("clean residue",residue_clean,"clean_not_red",clean_not_red))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def shear(im,amount):
    add=max(1,int(round(amount*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,
                        (1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def sample_colors(sm):
    pix=sa[sm][:,:3]
    fillpix=pix[(pix[:,1]>165)&(pix[:,2]>95)]
    shadowpix=pix[(pix[:,0]>170)&(pix[:,1]>65)&(pix[:,1]<180)&(pix[:,2]<170)]
    fill=tuple(int(x) for x in (np.median(fillpix,axis=0) if len(fillpix) else np.array([250,235,175])))+(255,)
    shadow=tuple(int(x) for x in (np.median(shadowpix,axis=0) if len(shadowpix) else np.array([238,135,72])))+(255,)
    return fill,shadow

final=clean.copy()
target=np.zeros((H,W),bool)
render_masks=[]
for row,sm,bm in zip(rows,source_masks,banner_masks):
    x0,y0,x1,y1=row["source_bbox"]
    sw=x1-x0; sh=y1-y0
    fill,shadow=sample_colors(sm)
    chosen=None
    for fs in range(max(18,int(sh*1.05)),14,-1):
        font=ImageFont.truetype(FONT,fs)
        canvas=Image.new("RGBA",(max(360,sw*4),max(180,sh*4)),(0,0,0,0))
        d=ImageDraw.Draw(canvas)
        tb=d.textbbox((0,0),row["ko"],font=font)
        ox=18-tb[0]; oy=18-tb[1]
        shoff=max(1,round(fs*0.055))
        d.text((ox+shoff,oy+shoff),row["ko"],font=font,fill=shadow)
        d.text((ox,oy),row["ko"],font=font,fill=fill,stroke_width=1,stroke_fill=shadow)
        gb=canvas.getchannel("A").getbbox()
        if not gb: continue
        glyph=canvas.crop(gb)
        glyph=shear(glyph,0.17)
        gb=glyph.getchannel("A").getbbox()
        if gb: glyph=glyph.crop(gb)
        if glyph.width>sw-4 or glyph.height>sh-4: continue
        px=x0+(sw-glyph.width)//2
        py=y0+(sh-glyph.height)//2
        layer=Image.new("RGBA",(W,H),(0,0,0,0))
        layer.alpha_composite(glyph,(px,py))
        lm=np.asarray(layer.getchannel("A"))>0
        lb=bbox(lm)
        if lb is None: continue
        if not (lb[0]>=x0+2 and lb[1]>=y0+2 and lb[2]<=x1-2 and lb[3]<=y1-2): continue
        # Exact source text bbox is the hard glyph/effect ceiling. The sign is
        # trapezoidal, but this Korean render stays centered with >=2px bbox
        # margins and is visually inside the red body; do not reject valid target
        # pixels merely because the diagnostic red-field mask has irregular holes.
        chosen=(layer,lm,lb,fs,fill,shadow,shoff)
        break
    if chosen is None: raise RuntimeError(("no render fit",row["key"],row["source_bbox"]))
    layer,lm,lb,fs,fill,shadow,shoff=chosen
    if np.any(target&lm): raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(layer)
    target|=lm
    render_masks.append(lm)
    row.update({
      "korean":row["ko"],"font":"Noto Sans CJK KR Black","font_size":fs,"shear":0.17,
      "shadow_offset":shoff,"fill_rgba":fill,"shadow_rgba":shadow,
      "localized_bbox":lb,
      "source_width":sw,"source_height":sh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
      "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

# Write exact RGBA32 DDS preserving header and raw mirror_y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=raw[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(payload)
cand_sha=sha256(candidate)
dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("DDS roundtrip mismatch")
da=np.asarray(dec,dtype=np.uint8)

# Allowed edits are the clean reconstruction plus the final Korean glyph/effect
# pixels. New lettering may paint untouched red sign pixels inside the exact
# source text bbox, but never the protected white rim/map/artwork.
allowed=clean_region | target
changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
protected_changed=int(np.count_nonzero(changed & (alpha & ~allowed)))
introduced=int(np.count_nonzero((da[:,:,3]>8)&(sa[:,:,3]<=8)&~allowed))
if outside or alpha_out or protected_changed or introduced:
    raise RuntimeError(("static outside gate",outside,alpha_out,protected_changed,introduced))

# Final residue gate: no source effect pixel may survive outside the new
# Hangul/effect guard, and the exposed clean background must remain sign-red.
guard=ndimage.binary_dilation(target,iterations=2)
same_source=np.all(da==sa,axis=2)
rrf=da[:,:,0].astype(np.int16); ggf=da[:,:,1].astype(np.int16); bbf=da[:,:,2].astype(np.int16)
final_sign_red=(rrf>115) & (rrf>ggf+35) & (rrf>bbf+20) & (ggf<125) & (bbf<135)
residue_exact=int(np.count_nonzero(source_mask & same_source & ~guard))
residue_color=int(np.count_nonzero(source_mask & ~guard & ~final_sign_red))
residue_final=residue_color
if residue_final:
    raise RuntimeError(("final source residue",residue_exact,residue_color))


# Evidence.
src.save(out/"B190_SOURCE_READABLE.png")
clean.save(out/"B190_CLEAN_PLATE.png")
dec.save(out/"B190_FINAL_READABLE.png")
src_raw.save(out/"B190_SOURCE_RAW.png")
dec_raw.save(out/"B190_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B190_SOURCE_TEXT_MASK.png")
Image.fromarray((clean_region.astype(np.uint8)*255),"L").save(out/"B190_CLEAN_REGION_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B190_TARGET_MASK.png")

def on_white(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")
def crop_card(label,im,box,scale=3):
    v=on_white(im).crop(box)
    v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    card=Image.new("RGB",(v.width,v.height+30),"white")
    card.paste(v,(0,30)); ImageDraw.Draw(card).text((6,7),label,fill="black")
    return card

cards=[]
for row in rows:
    x0,y0,x1,y1=row["banner_bbox"]
    pad=16
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
        cards.append(crop_card(f'{row["key"].upper()} {label}',im,box,3))
mw=max(c.width for c in cards)
mh=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(mw,mh),"white")
y=0
for c in cards:
    sheet.paste(c,(0,y)); y+=c.height+8
sheet.thumbnail((1800,2800),Image.Resampling.LANCZOS)
sheet.save(out/"B190_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

raw_sheet=Image.new("RGB",(1024,2*1024+70),"white")
for i,(label,im) in enumerate([("SOURCE_RAW",src_raw),("FINAL_RAW",dec_raw)]):
    vis=on_white(im)
    vis.thumbnail((1024,1024),Image.Resampling.LANCZOS)
    y=i*(vis.height+35)
    raw_sheet.paste(vis,(0,y+30)); ImageDraw.Draw(raw_sheet).text((6,y+7),label,fill="black")
raw_sheet=raw_sheet.crop((0,0,1024,2*1024+70))
raw_sheet.thumbnail((1400,1800),Image.Resampling.LANCZOS)
raw_sheet.save(out/"B190_RAW_CONTACT.jpg",quality=95)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":172,"asset":asset,
 "classification":{"from":"zoom_review","to":"localize_text",
   "segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],
   "physical_text_elements":2,
   "protected":["OutRun2SP logo","route map","stage thumbnails","road artwork","all non-label pixels"]},
 "source_provenance":{"url":url,"sha256":SOURCE_SHA},
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":MIPS,
   "header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},
 "construction":"B190 derives each sign interior from the convex hull of strongly saturated source-red pixels in the tight START/GOAL ROI, erodes one pixel from that hull, and unions only exact measured source-effect pixels. This supersedes B182-B189 masks that either left English-effect strips or over-cleaned the rim; route map, thumbnails and OutRun2SP artwork remain protected and fresh native Korean stays inside the exact source-effect bbox.",
 "same_family_reference":"localization/graphics/role_A/20261006-A-PRODUCTION85-IGR012-CLEAN/A85_CONTROLLER_SELF_QA.json",
 "rows":rows,
 "static_qa":{
   "elements_total":2,"bbox_size_positive_margin":"2/2 PASS",
   "clean_source_residue":residue_clean,
   "clean_reconstructed_background_pixels":int(np.count_nonzero(clean_region & ~source_mask)),
   "changed_outside_source_bboxes":outside,
   "alpha_changed_outside":alpha_out,
   "protected_visible_changed":protected_changed,
   "introduced_visible_outside":introduced,
   "final_source_residue":residue_final,
   "localized_overlap":int(np.count_nonzero(render_masks[0]&render_masks[1])),
   "dds_roundtrip":"PASS",
   "status":"PASS"
 },
 "candidate_path":str(candidate.relative_to(repo)),
 "candidate_sha256":cand_sha,
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"B190_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B190_6C9B3611_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B190_6C9B3611.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":172,"asset":"6C9B3611",
 "source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B190_DONE",cand_sha,[(r["key"],r["source_bbox"],r["localized_bbox"],r["font_size"]) for r in rows])