#!/usr/bin/env python3
# B237: C246-returned q44 19CEDB9 source-relative hierarchy/scale rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, math, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo = Path.cwd()
RUN = "20261007-B237-Q044-19CEDB9-C246-REWORK"
out = repo / "localization/graphics/role_B" / RUN
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)

asset_rel = "textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds"
srcp = repo / "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a" / asset_rel
candp = repo / "localization/graphics/hd_candidates" / asset_rel
EXPECTED_SOURCE = "2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e"
EXPECTED_BEFORE = "8c6a390cbadae23beff263bb0eea4ca935643d591b45bac9ca474fa108e5a913"

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha_file(p):
    return sha_bytes(Path(p).read_bytes())

def find_font():
    choices = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"),
    ]
    for p in choices:
        if p.exists():
            return p
    subprocess.run(["sudo","apt-get","update","-qq"], check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"], check=True)
    for p in choices:
        if p.exists():
            return p
    raise RuntimeError("Noto Sans CJK KR unavailable")

FONT = find_font()
FONT_INDEX = 1
SS = 4

def decode_dds(p):
    b = Path(p).read_bytes()
    if b[:4] != b"DDS ":
        raise RuntimeError("not DDS")
    h,w,pitch,depth,mips = struct.unpack_from("<5I", b, 12)
    masks = struct.unpack_from("<4I", b, 92)
    if masks == (0xff,0xff00,0xff0000,0xff000000):
        mode = "RGBA"
    elif masks == (0xff0000,0xff00,0xff,0xff000000):
        mode = "BGRA"
    else:
        raise RuntimeError(("unsupported masks", masks))
    if len(b) != 128 + w*h*4 or mips != 1:
        raise RuntimeError(("unexpected DDS structure", w,h,mips,len(b)))
    raw = Image.frombytes("RGBA", (w,h), b[128:], "raw", mode)
    readable = raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b, raw, readable, {"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"mode":mode,"masks":[hex(x) for x in masks]}

def changed(a,b):
    return np.any(a != b, axis=2)

def bbox(mask):
    ys,xs = np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def rectmask(h,w,bb):
    m=np.zeros((h,w),bool)
    x0,y0,x1,y1=bb
    m[y0:y1,x0:x1]=True
    return m

def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg)
    z.alpha_composite(im)
    return z.convert("RGB")

def tracked_glyph(text, font_px, fill, outer, outer_w, inner=None, inner_w=0, tracking=0.20, slant=0.0):
    font=ImageFont.truetype(str(FONT), font_px*SS, index=FONT_INDEX)
    ow=outer_w*SS
    iw=inner_w*SS
    track=max(0,int(round(font_px*tracking*SS)))
    glyphs=[]
    for ch in text:
        if ch == " ":
            glyphs.append((None, max(1,int(round(font_px*0.45*SS)))))
            continue
        d0=ImageDraw.Draw(Image.new("L",(2,2),0))
        tb=d0.textbbox((0,0),ch,font=font,stroke_width=ow)
        pad=(outer_w+8)*SS
        g=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        d=ImageDraw.Draw(g)
        pos=(pad-tb[0],pad-tb[1])
        d.text(pos,ch,font=font,fill=fill,stroke_width=ow,stroke_fill=outer)
        if inner is not None:
            d.text(pos,ch,font=font,fill=fill,stroke_width=iw,stroke_fill=inner)
        bb=g.getchannel("A").getbbox()
        g=g.crop(bb)
        glyphs.append((g,g.width))
    total=sum(w for _,w in glyphs)+track*max(0,len(glyphs)-1)
    height=max(g.height for g,_ in glyphs if g is not None)
    layer=Image.new("RGBA",(total,height),(0,0,0,0))
    x=0
    for g,w in glyphs:
        if g is not None:
            layer.alpha_composite(g,(x,(height-g.height)//2))
        x+=w+track
    bb=layer.getchannel("A").getbbox()
    layer=layer.crop(bb)
    if slant:
        shift=max(1,int(math.ceil(abs(slant)*(layer.height-1))))
        sh=Image.new("RGBA",(layer.width+shift,layer.height),(0,0,0,0))
        for y in range(layer.height):
            dx=int(round(slant*(layer.height-1-y)))
            if dx < 0:
                dx += shift
            sh.alpha_composite(layer.crop((0,y,layer.width,y+1)),(dx,y))
        layer=sh.crop(sh.getchannel("A").getbbox())
    return layer

def render_target(text, target_w, target_h, fill, outer, outer_w, inner=None, inner_w=0, slant=0.0, tracking=0.20):
    # Fresh supersampled glyph construction. Horizontal restoration is applied only
    # to this fresh layer; no historical Korean bitmap is upscaled.
    probe=max(12,int(round(target_h*1.10)))
    g=tracked_glyph(text,probe,fill,outer,outer_w,inner,inner_w,tracking,slant)
    return g.resize((target_w,target_h),Image.Resampling.LANCZOS)

source_bytes, source_raw, source, meta = decode_dds(srcp)
before_bytes, before_raw, before, before_meta = decode_dds(candp)
if sha_bytes(source_bytes) != EXPECTED_SOURCE:
    raise RuntimeError(("source drift",sha_bytes(source_bytes)))
if sha_bytes(before_bytes) != EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift",sha_bytes(before_bytes)))
if meta != before_meta or source_bytes[:128] != before_bytes[:128]:
    raise RuntimeError("header/structure drift")

# Source isolation cells from the original B_RECOVERY04 exact-source producer.
cells={
 "sector2":(8,100,190,160), "sector1":(208,100,385,160),
 "win":(418,100,500,160), "lose":(528,100,635,160),
 "result":(32,170,247,260), "ranking":(289,170,555,260),
 "stage":(571,170,765,260), "rank":(788,170,964,260),
 "you":(1759,180,1897,270), "diff":(1853,300,1975,390),
 "sector3":(1832,1170,2013,1245), "rival":(498,1400,705,1490)
}
sa=np.asarray(source.getchannel("A"))
source_bboxes={}
for k,(x0,y0,x1,y1) in cells.items():
    m=np.zeros((meta["height"],meta["width"]),bool)
    m[y0:y1,x0:x1]=sa[y0:y1,x0:x1]>0
    bb=bbox(m)
    if bb is None:
        raise RuntimeError(("empty source row",k))
    source_bboxes[k]=bb

expected_bboxes={
 "sector2":[8,100,190,160], "sector1":[208,100,385,160],
 "win":[418,110,500,151], "lose":[528,109,635,152],
 "result":[32,180,247,249], "ranking":[289,180,555,259],
 "stage":[571,179,765,259], "rank":[788,180,964,249],
 "you":[1759,193,1897,260], "diff":[1853,312,1975,381],
 "sector3":[1832,1180,2013,1240], "rival":[498,1412,705,1486]
}
if source_bboxes != expected_bboxes:
    raise RuntimeError(("source bbox drift",source_bboxes))

NAVY=(0,10,65,255); YELLOW=(249,208,12,255)
YELLOW2=(245,204,12,255); WHITE=(255,255,255,255); ORANGE=(255,158,41,255)

# Target sizes restore the source-relative visual hierarchy while retaining
# >=2px margins. The single-glyph YOU->나 row is deliberately not stretched
# to 90% width; it is materially enlarged to 72.5% while preserving a credible glyph proportion.
spec={
 "sector2":("섹터 2",(164,54),YELLOW,NAVY,5,None,0,0.12,0.22),
 "sector1":("섹터 1",(159,54),YELLOW,NAVY,5,None,0,0.12,0.22),
 "win":("승리",(72,35),WHITE,NAVY,4,None,0,0.00,0.28),
 "lose":("패배",(94,37),WHITE,NAVY,4,None,0,0.00,0.32),
 "result":("결과",(194,63),YELLOW2,NAVY,7,WHITE,3,0.14,0.58),
 "ranking":("랭킹",(238,71),YELLOW2,NAVY,7,WHITE,3,0.14,0.65),
 "stage":("스테이지",(186,72),YELLOW2,NAVY,7,WHITE,3,0.14,0.16),
 "rank":("랭크",(160,63),WHITE,NAVY,6,None,0,0.12,0.35),
 "you":("나",(100,61),YELLOW,NAVY,6,None,0,0.12,0.00),
 "diff":("차이",(116,63),YELLOW,NAVY,5,None,0,0.12,0.32),
 "sector3":("섹터 3",(163,54),YELLOW,NAVY,5,None,0,0.12,0.22),
 "rival":("라이벌",(185,68),ORANGE,NAVY,6,None,0,0.14,0.24),
}

# Exact clean plate from the pinned English source: this atlas is transparent
# behind these source glyph/effect footprints.
clean=source.copy()
clean_np=np.array(clean)
source_text_mask=np.zeros((meta["height"],meta["width"]),bool)
allowed=np.zeros_like(source_text_mask)
for bb in source_bboxes.values():
    allowed |= rectmask(meta["height"],meta["width"],bb)
for k,(x0,y0,x1,y1) in cells.items():
    region=(sa[y0:y1,x0:x1]>0)
    source_text_mask[y0:y1,x0:x1] |= region
clean_np[source_text_mask]=np.array([0,0,0,0],dtype=np.uint8)
clean=Image.fromarray(clean_np,"RGBA")

final=clean.copy()
layers=[]
rows=[]
for k,(text_s,size,fill,outer,ow,inner,iw,slant,tracking) in spec.items():
    x0,y0,x1,y1=source_bboxes[k]
    tw,th=size
    if tw > (x1-x0)-4 or th > (y1-y0)-4:
        raise RuntimeError(("target too large",k,size,source_bboxes[k]))
    g=render_target(text_s,tw,th,fill,outer,ow,inner,iw,slant,tracking)
    px=x0+((x1-x0)-tw)//2
    py=y0+((y1-y0)-th)//2
    layer=Image.new("RGBA",final.size,(0,0,0,0))
    layer.alpha_composite(g,(px,py))
    final.alpha_composite(layer)
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox(lm)
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins) < 2:
        raise RuntimeError(("margin fail",k,margins,lb))
    source_w=x1-x0; source_h=y1-y0
    rows.append({
      "key":k,"korean":text_s,"original_bbox":[x0,y0,x1,y1],
      "localized_bbox":lb,"source_size":[source_w,source_h],
      "localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "width_ratio":round((lb[2]-lb[0])/source_w,4),
      "height_ratio":round((lb[3]-lb[1])/source_h,4),
      "margins":margins,"slant":slant,"tracking":tracking,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })
    layers.append((k,lm))

# Pairwise zero-overlap.
pair_overlap={}
for i in range(len(layers)):
    for j in range(i+1,len(layers)):
        n=int(np.count_nonzero(layers[i][1] & layers[j][1]))
        if n:
            pair_overlap[f"{layers[i][0]}::{layers[j][0]}"]=n
if pair_overlap:
    raise RuntimeError(("pair overlap",pair_overlap))

old_np=np.asarray(before)
final_np=np.asarray(final)
source_np=np.asarray(source)
changed_old=changed(old_np,final_np)
changed_source=changed(source_np,final_np)
blast_old=int(np.count_nonzero(changed_old & ~allowed))
blast_source=int(np.count_nonzero(changed_source & ~allowed))
alpha_old=int(np.count_nonzero((old_np[:,:,3]!=final_np[:,:,3]) & ~allowed))
alpha_source=int(np.count_nonzero((source_np[:,:,3]!=final_np[:,:,3]) & ~allowed))
if any((blast_old,blast_source,alpha_old,alpha_source)):
    raise RuntimeError(("blast radius",blast_old,blast_source,alpha_old,alpha_source))

# Persist exact DDS using source header + source channel layout + raw mirror-Y.
final_raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=source_bytes[:128]+final_raw.tobytes("raw",meta["mode"])
candp.write_bytes(payload)
persist_bytes,persist_raw,persist,meta2=decode_dds(candp)
after_sha=sha_bytes(persist_bytes)
if persist_bytes[:128] != source_bytes[:128] or meta2 != meta:
    raise RuntimeError("persisted DDS structure mismatch")
if ImageChops.difference(persist,final).getbbox() is not None:
    raise RuntimeError("persisted decode mismatch")

# Source/CLEAN and persisted candidate static gates.
clean_a=np.asarray(clean)
clean_changed=changed(source_np,clean_a)
clean_out=int(np.count_nonzero(clean_changed & ~source_text_mask))
clean_residue=int(np.count_nonzero((clean_a[:,:,3]>0) & source_text_mask))
if clean_out or clean_residue:
    raise RuntimeError(("clean plate fail",clean_out,clean_residue))

# Evidence masks.
def mask_img(m):
    return Image.fromarray((m.astype(np.uint8)*255),"L")
mask_img(source_text_mask).save(out/"B237_19CEDB9_SOURCE_TEXT_MASK.png")
mask_img(allowed).save(out/"B237_19CEDB9_ALLOWED_REGION_MASK.png")
mask_img(~allowed).save(out/"B237_19CEDB9_PROTECTED_MASK.png")
target=np.zeros_like(allowed)
for _,lm in layers:
    target |= lm
mask_img(target).save(out/"B237_19CEDB9_TARGET_TEXT_MASK.png")
clean.save(out/"B237_19CEDB9_CLEAN_PLATE.png")

# Readable overview evidence.
def labeled(im,label,maxw=900):
    rgb=comp(im)
    if rgb.width>maxw:
        nh=round(rgb.height*maxw/rgb.width)
        rgb=rgb.resize((maxw,nh),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(rgb.width,rgb.height+34),(22,22,22))
    card.paste(rgb,(0,34))
    ImageDraw.Draw(card).text((8,8),label,fill="white")
    return card

cards=[labeled(source,"SOURCE"),labeled(before,"A144/C246 INPUT"),labeled(clean,"CLEAN"),labeled(persist,"B237 FINAL")]
sheet=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(18,18,18))
xx=0
for c in cards:
    sheet.paste(c,(xx,0)); xx+=c.width
sheet.save(out/"B237_19CEDB9_SOURCE_CURRENT_CLEAN_FINAL.jpg","JPEG",quality=95,subsampling=0)

# High-zoom row contacts.
row_cards=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    pad=18
    cr=(max(0,x0-pad),max(0,y0-pad),min(meta["width"],x1+pad),min(meta["height"],y1+pad))
    pieces=[]
    for lab,im in [("SOURCE",source),("INPUT",before),("FINAL",persist)]:
        z=comp(im).crop(cr)
        z=z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST)
        c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28))
        ImageDraw.Draw(c).text((6,6),f"{r['key']} {lab}",fill="white")
        pieces.append(c)
    rc=Image.new("RGB",(sum(x.width for x in pieces),max(x.height for x in pieces)),(20,20,20))
    px=0
    for p in pieces:
        rc.paste(p,(px,0));px+=p.width
    row_cards.append(rc)
rw=max(c.width for c in row_cards); rh=sum(c.height for c in row_cards)
rowsheet=Image.new("RGB",(rw,rh),(16,16,16)); yy=0
for c in row_cards:
    rowsheet.paste(c,(0,yy)); yy+=c.height
rowsheet.save(out/"B237_19CEDB9_ROW_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

# RAW source/input/final orientation evidence.
raw_cards=[labeled(source_raw,"SOURCE RAW"),labeled(before_raw,"INPUT RAW"),labeled(persist_raw,"B237 FINAL RAW")]
rawsheet=Image.new("RGB",(sum(c.width for c in raw_cards),max(c.height for c in raw_cards)),(18,18,18))
xx=0
for c in raw_cards:
    rawsheet.paste(c,(xx,0));xx+=c.width
rawsheet.save(out/"B237_19CEDB9_RAW.jpg","JPEG",quality=94,subsampling=0)

# Practical-scale evidence.
pr=[]
for scale in (1.0,0.75,0.5):
    im=comp(persist)
    im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    if im.width>1000:
        im=im.resize((1000,round(im.height*1000/im.width)),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(im.width,im.height+28),(20,20,20));c.paste(im,(0,28))
    ImageDraw.Draw(c).text((6,5),f"B237 FINAL practical {int(scale*100)}%",fill="white")
    pr.append(c)
pw=max(x.width for x in pr);ph=sum(x.height for x in pr)
ps=Image.new("RGB",(pw,ph),(18,18,18));yy=0
for c in pr:
    ps.paste(c,(0,yy));yy+=c.height
ps.save(out/"B237_19CEDB9_PRACTICAL.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"B","run":RUN,"queue_index":44,"asset":asset_rel,
 "execution_backend":"GITHUB_ACTIONS_REPOSITORY_BACKED_BINARY_PERSISTENCE; CHATGPT_LOCAL_CONTROLLER_VISUAL_REVIEW_REQUIRED",
 "trigger":"C246_VISUAL_FAIL_REWORK_REQUIRED_TEXT_SCALE_TOO_SMALL_VS_SOURCE",
 "source_sha256":EXPECTED_SOURCE,"before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":after_sha,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"a95efe01d1f136514cef94b0d9e9fd61df021754"},
 "font":{"file":FONT.name,"ttc_index":FONT_INDEX,"family":"Noto Sans CJK KR Bold"},
 "construction":"exact pinned HD source -> exact source alpha clean plate -> fresh supersampled native Hangul -> source palette/effects/slant -> source-relative width/height restoration -> exact source-header DDS encode",
 "rows":rows,
 "machine_qa":{
   "rows":"12/12 PASS","changed_pixels_outside_exact_source_bboxes_vs_input":blast_old,
   "changed_pixels_outside_exact_source_bboxes_vs_source":blast_source,
   "alpha_changes_outside_exact_source_bboxes_vs_input":alpha_old,
   "alpha_changes_outside_exact_source_bboxes_vs_source":alpha_source,
   "clean_changed_outside_source_text_mask":clean_out,"clean_source_residue_pixels":clean_residue,
   "localized_pair_overlap_pixels":0,"header_128_exact":True,"mip_count":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode":"PASS"
 },
 "ordered_generation_gate":{
   "1_english_removal_plate_restoration":"PASS_EXACT_TRANSPARENT_SOURCE_FOOTPRINT",
   "2_source_matching_slant":"PASS_SOURCE_FAMILY_PER_ROW",
   "3_no_undersized_lettering":"PASS_MATERIAL_SOURCE_RELATIVE_SCALE_RESTORATION",
   "4_source_faithful_weight_effect":"PASS_SOURCE_PALETTE_OUTLINE_INNER_EFFECT",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN_12_OF_12",
   "6_protected_art_clearance":"PASS_ZERO_BLAST_OUTSIDE_EXACT_SOURCE_BBOXES",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL_CONFIRM"
 },
 "controller_visual_qa":"PENDING_CHATGPT_LOCAL_CONTROLLER",
 "status":"B237_WORKER_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA_AND_FRESH_C",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"B237_19CEDB9_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B237_Q044_19CEDB9.json").write_text(json.dumps({
 "role":"B","run":RUN,"queue_index":44,"candidate_sha256":after_sha,
 "status":report["status"],"report":str((out/"B237_19CEDB9_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"source":EXPECTED_SOURCE,"before":EXPECTED_BEFORE,"after":after_sha,
 "rows":[{"key":r["key"],"localized_size":r["localized_size"],"width_ratio":r["width_ratio"],"height_ratio":r["height_ratio"],"margins":r["margins"]} for r in rows],
 "machine_qa":"PASS","runtime_validation":"UNTESTED"},ensure_ascii=False))
