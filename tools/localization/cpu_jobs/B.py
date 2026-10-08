#!/usr/bin/env python3
"""B264 q172 new per-syllable high-resolution cream-face emboss reconstruction, SHA guarded."""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B264 source-family method-change requires GitHub CPU worker")
root=Path.cwd()
gfx=root/"localization/graphics"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
target=gfx/"hd_candidates"/asset
run="20261008-B264-Q172-PER-SYLLABLE-CREAM-EMBOSS"
out=gfx/"role_B"/run
out.mkdir(parents=True, exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
source_sha="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
candidate_sha="812373b09831dd2886ab5e6f3a74adc5d357e9e5871ac37752e91b24871a950a"
clean_sha="9a0750d0db62345a21dbf4006f2da0b2fe7e96151f40dd5e3d1f5e422bd1d809"
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
 "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
 "Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds")
triage=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","172"],check=True,capture_output=True,text=True)
triage_decision=json.loads(triage.stdout)["assets"][0]
if triage_decision["next_action"]!="METHOD_CHANGE_REQUIRED" or "SOURCE_FAMILY_BEVEL_MISMATCH" not in triage_decision["repeated_root_causes"]:
    raise RuntimeError(("B264 needs actual C291+C295 method change escalation",triage_decision))
blind=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","172","--require-safe-rerender"],capture_output=True,text=True)
if blind.returncode!=2:raise RuntimeError("same-method rerender guard failed")
(out/"B264_TRIAGE.json").write_text(json.dumps(triage_decision,ensure_ascii=False,indent=2)+"\n")
oldbytes=target.read_bytes()
if sha(oldbytes)!=candidate_sha:raise RuntimeError(("concurrent q172 change",sha(oldbytes)))
cleanpath=gfx/"role_B/20261008-B255-Q172-EXPLICIT-KOREAN-FONT-SHEAR/CLEAN.png"
if sha(cleanpath.read_bytes())!=clean_sha:raise RuntimeError("pinned clean plate changed")
with tempfile.TemporaryDirectory(prefix="outrun_b262_") as td:
    sf=Path(td)/"source.dds"
    urllib.request.urlretrieve(url,sf)
    sourcebytes=sf.read_bytes()
if sha(sourcebytes)!=source_sha:raise RuntimeError(("canonical source changed",sha(sourcebytes)))
if sourcebytes[:128]!=oldbytes[:128]:raise RuntimeError("DDS headers differ")
W,H=struct.unpack_from("<II",sourcebytes,16)[0],struct.unpack_from("<I",sourcebytes,12)[0]
mips=struct.unpack_from("<I",sourcebytes,28)[0]
masks=struct.unpack_from("<IIII",sourcebytes,92)
if (W,H,mips,len(sourcebytes),len(oldbytes))!=(1024,1024,1,128+1024*1024*4,128+1024*1024*4):
    raise RuntimeError(("unexpected size or mips",W,H,mips,len(sourcebytes),len(oldbytes)))
if masks not in ((0xff0000,0xff00,0xff,0xff000000),(0xff,0xff00,0xff0000,0xff000000)):
    raise RuntimeError(("unknown channel masks",masks))
def readable(b):
    return Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=np.asarray(readable(sourcebytes),dtype=np.uint8).copy()
old=np.asarray(readable(oldbytes),dtype=np.uint8).copy()
clean=np.asarray(Image.open(cleanpath).convert("RGBA"),dtype=np.uint8).copy()
if src.shape!=clean.shape or src.shape!=old.shape:raise RuntimeError("source/clean/candidate native dimensions differ")
spec=[
    {"id":"START","korean":"출발","source_bbox":[55,373,136,396],"glyph_width":23,"face_height":17,"shear_px":7},
    {"id":"GOAL","korean":"골","source_bbox":[595,635,672,659],"glyph_width":32,"face_height":17,"shear_px":7},
]
allowed=np.zeros((H,W),bool)
for item in spec:
    x0,y0,x1,y1=item["source_bbox"]
    allowed[y0:y1,x0:x1]=True
if int(np.count_nonzero(np.any(src!=clean,axis=2)&~allowed))!=0:
    raise RuntimeError("clean plate blast-radius outside source regions")
if int(np.count_nonzero(np.any(src!=old,axis=2)&~allowed))!=0:
    raise RuntimeError("old candidate differs from English outside source regions")
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
f=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Black"],text=True).strip().split("|")
fontpath,fontidx,family=f[0],int(f[1] or "0"),f[2]
if "NotoSansCJK" not in fontpath or "Noto Sans CJK" not in family:
    raise RuntimeError(("unexpected Hangul font",f))
font=ImageFont.truetype(fontpath,170,index=fontidx)
tofu=bytes(font.getmask(chr(0x10ffff)))
for ch in "출발골":
    if bytes(font.getmask(ch))==tofu:raise RuntimeError(("missing Hangul glyph",ch))
result=old.copy()
for item in spec:
    x0,y0,x1,y1=item["source_bbox"]
    source_crop=src[y0:y1,x0:x1,:3]
    # The original cream/orange letterface—not a hand-set flat palette—
    # establishes the upper and lower face colors for continuous per-pixel fill.
    R=source_crop[:,:,0].astype(float);G=source_crop[:,:,1].astype(float);B=source_crop[:,:,2].astype(float)
    gold=(R>=180)&(G>=95)&(B>=45)&(G>=B*0.70)&(R>=G*0.96)
    ys,xs=np.where(gold)
    if len(xs)<40:raise RuntimeError(("missing gold source face",item["id"],len(xs)))
    px=source_crop[gold].astype(np.float64)
    top=np.percentile(px[ys <= np.median(ys)],77,axis=0)
    bottom=np.percentile(px[ys > np.median(ys)],42,axis=0)
    item["profile"]={"source_gold_pixels":len(xs),"source_face_top_rgb":[int(x) for x in top],
                      "source_face_bottom_rgb":[int(x) for x in bottom]}
    # MATERIAL METHOD CHANGE after independent C291+C295:
    # Per-syllable vector-like supersampled masks, not a fixed-width stretched
    # phrase or categorical horizontal color bands. Individual italic transforms
    # and source-matched bright cream faces precede native 1px bevel/extrusion.
    U=8
    glyphs=[]
    for ch in item["korean"]:
        glyph_can=Image.new("L",(450,340),0)
        gd=ImageDraw.Draw(glyph_can)
        gb=gd.textbbox((0,0),ch,font=font)
        gd.text((36-gb[0],36-gb[1]),ch,font=font,fill=255)
        bounds=glyph_can.getbbox()
        if not bounds:raise RuntimeError(("empty glyph",ch))
        w=item["glyph_width"];h=item["face_height"];shear=item["shear_px"]
        # Reconstruct each Hangul syllable at 8x BEFORE forward-italic affine,
        # then antialias ONCE at native display size to preserve curved strokes.
        high=glyph_can.crop(bounds).resize((w*U,h*U),Image.Resampling.LANCZOS)
        high=high.transform(((w+shear)*U,h*U),Image.Transform.AFFINE,
                            (1,shear/(h-1),-shear*U,0,1,0),
                            resample=Image.Resampling.BICUBIC)
        glyphs.append(np.asarray(high.resize((w+shear,h),Image.Resampling.LANCZOS),dtype=np.uint8))
    gap=2 if len(glyphs)>1 else 0
    content_w=sum(g.shape[1] for g in glyphs)+gap*(len(glyphs)-1)
    content_h=max(g.shape[0] for g in glyphs)
    canvas=np.zeros((content_h,content_w),dtype=np.uint8)
    gx=0
    for g in glyphs:
        canvas[:g.shape[0],gx:gx+g.shape[1]]=np.maximum(canvas[:g.shape[0],gx:gx+g.shape[1]],g)
        gx+=g.shape[1]+gap
    cov=np.pad(canvas,((1,1),(1,1)),constant_values=0)
    face=cov>=105
    if np.count_nonzero(face)<65:raise RuntimeError(("native cream face sparse",item["id"]))
    outer=binary_dilation(face,iterations=1)
    shadow=np.zeros_like(face,dtype=bool)
    shadow[1:,1:]=face[:-1,:-1]
    shadow&=~face
    edge=outer&~face
    above=np.zeros_like(face,dtype=bool);above[1:]=face[:-1]
    below=np.zeros_like(face,dtype=bool);below[:-1]=face[1:]
    # Face colors continuously cream-white: no horizontal brown stripes.
    # True gold/copper only on narrow contour and 1px extruded depth.
    top_edge=face&~above
    lower_edge=face&~below
    h,w=face.shape
    shape=(y1-y0,x1-x0)
    gw,gh=w,h
    cx=(x1-x0)//2;cy=(y1-y0)//2
    x=cx-gw//2;y=cy-gh//2
    if min(x-1,y-1,shape[1]-(x+gw+1),shape[0]-(y+gh+1))<0:
        raise RuntimeError(("per-syllable effect exceeds exact source bbox",item["id"],shape,w,h,x,y))
    patch=clean[y0:y1,x0:x1].copy().astype(np.float32)
    region=patch[y:y+gh,x:x+gw]
    region[shadow,:3]=[145,49,32];region[shadow,3]=255
    region[edge,:3]=[231,125,56];region[edge,3]=255
    YY,XX=np.indices(face.shape)
    # Only a subtle 30% bottom-warmth and per-pixel right edge highlight;
    # the full inner Hangul face stays luminous and continuous.
    t=(YY.astype(float)/max(1,h-1))[:, :, None]*0.30
    continuous=top[None,None,:]*(1-t)+bottom[None,None,:]*t
    continuous=np.maximum(continuous,[245,222,190])
    continuous=np.minimum(continuous,255)
    region[face,:3]=continuous[face];region[face,3]=255
    # Physically located contours follow each glyph—not horizontal rows.
    region[lower_edge,:3]=[247,173,106]
    region[top_edge,:3]=[255,251,230]
    # The exact 1px warm fringe only follows low-coverage pixels.
    fringe=(cov>22)&(~face)&(~outer)
    region[fringe,:3]=[230,166,102];region[fringe,3]=255
    bright=(region[:,:,0]>=244)&(region[:,:,1]>=210)&face
    item["bright_cream_face_pixels"]=int(bright.sum())
    item["native_face_pixels"]=int(face.sum())
    if bright.sum()<face.sum()*0.60:
        raise RuntimeError(("cream interior underfilled; no brown-slab retry",item["id"],int(bright.sum()),int(face.sum())))
    item["rendering_method"]="SUPERSAMPLED_PER_SYLLABLE_AFFINE_THEN_CREAM_FACE_WITH_CONTOUR_EMBOSS"
    item["glyph_shapes"]=[list(map(int,g.shape)) for g in glyphs]
    patch=np.clip(patch,0,255).astype(np.uint8)
    result[y0:y1,x0:x1]=patch
    geom=np.zeros(shape,dtype=bool)
    geom[y:y+gh,x:x+gw]=outer|shadow
    by,bx=np.where(geom)
    bbox=[x0+int(bx.min()),y0+int(by.min()),x0+int(bx.max())+1,y0+int(by.max())+1]
    margins=[bbox[0]-x0,bbox[1]-y0,x1-bbox[2],y1-bbox[3]]
    if min(margins)<1:raise RuntimeError(("no glyph-effect positive margin",item["id"],margins))
    item["localized_effect_bbox"]=bbox
    item["margins"]=margins
    Image.fromarray(np.asarray(result[y0:y1,x0:x1]).astype(np.uint8),"RGBA").resize(((x1-x0)*8,(y1-y0)*8),Image.Resampling.NEAREST).save(out/f"{item['id']}_TRIAL_8X.png")
# Restore exact HDR/source DDS packing; no new mips, dimensions or orientation.
raw=np.flipud(result)
if masks[0]==0xff0000: raw=raw[:,:,[2,1,0,3]]
newbytes=sourcebytes[:128]+raw.copy(order="C").tobytes()
roundtrip=np.asarray(readable(newbytes),dtype=np.uint8)
if not np.array_equal(roundtrip,result):raise RuntimeError("DDS persisted decoded pixels differ")
if newbytes[:128]!=sourcebytes[:128]:raise RuntimeError("header mismatch")
outside=int(np.count_nonzero(np.any(result!=src,axis=2)&~allowed))
alpha_outside=int(np.count_nonzero((result[:,:,3]!=src[:,:,3])&~allowed))
if outside or alpha_outside:raise RuntimeError(("out-of-scope graphics changes",outside,alpha_outside))
if newbytes==oldbytes:raise RuntimeError("no material changes")
newsha=sha(newbytes)
target.write_bytes(newbytes)
Image.fromarray(result,"RGBA").save(out/"FINAL_DECODED.png")
Image.fromarray(np.flipud(result),"RGBA").save(out/"FINAL_RAW.png")
Image.fromarray(clean,"RGBA").save(out/"CLEAN_NATIVE.png")
src_img=Image.fromarray(src,"RGBA"); final_img=Image.fromarray(result,"RGBA"); clean_img=Image.fromarray(clean,"RGBA")
for item in spec:
    x0,y0,x1,y1=item["source_bbox"]
    cards=[]
    for label,im in [("ENGLISH SOURCE",src_img),("VERIFIED CLEAN",clean_img),("NEW KOREAN DDS",final_img)]:
        crop=im.crop((x0-4,y0-4,x1+4,y1+4))
        bg=Image.new("RGB",crop.size,(80,80,80));bg.paste(crop,mask=crop.getchannel("A"))
        cards.append(bg.resize((bg.width*7,bg.height*7),Image.Resampling.NEAREST))
    card=Image.new("RGB",(sum(i.width for i in cards),max(i.height for i in cards)),(70,70,70))
    pos=0
    for i in cards: card.paste(i,(pos,0));pos+=i.width
    card.save(out/f"{item['id']}_ENGLISH_CLEAN_FINAL_CONTACT.png")
for sp in spec:
    x0,y0,x1,y1=sp["source_bbox"]
    for percent in (100,75,50):
        pics=[]
        for im in (src_img,clean_img,final_img):
            crop=im.crop((x0-8,y0-8,x1+8,y1+8))
            bg=Image.new("RGB",crop.size,(85,85,85));bg.paste(crop,mask=crop.getchannel("A"))
            sz=(max(1,round(bg.width*percent/100)),max(1,round(bg.height*percent/100)))
            pics.append(bg.resize(sz,Image.Resampling.LANCZOS))
        gap=9;w=sum(z.width for z in pics)+gap*2
        card=Image.new("RGB",(w,max(z.height for z in pics)),(85,85,85));x=0
        for im in pics:card.paste(im,(x,0));x+=im.width+gap
        card.save(out/f"{sp['id']}_PRACTICAL_{percent}.png")
    # Exact persisted DDS orientation compared to canonical source/verified clean.
    pics=[]
    for im in (src_img,clean_img,final_img):
        raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        crop=raw.crop((x0-6,H-y1-6,x1+6,H-y0+6))
        bg=Image.new("RGB",crop.size,(85,85,85));bg.paste(crop,mask=crop.getchannel("A"))
        pics.append(bg.resize((bg.width*5,bg.height*5),Image.Resampling.NEAREST))
    card=Image.new("RGB",(sum(z.width for z in pics)+18,max(z.height for z in pics)),(85,85,85));x=0
    for im in pics:card.paste(im,(x,0));x+=im.width+9
    card.save(out/f"{sp['id']}_RAW_SOURCE_CLEAN_FINAL.png")
qa={"run":"B264","run_key":"OUTRUN-KOR-B264-Q172-METHOD-CHANGE-20261008-1830",
    "queue_index":172,"source_sha256":source_sha,"prior_candidate_sha256":candidate_sha,
    "new_candidate_sha256":newsha,"clean_plate_sha256":clean_sha,
    "method":"PER_SYLLABLE_SUPERSAMPLED_ITALIC_CREAM_FACE_CONTOUR_EMBOSS",
    "source_anchored_regions":spec,"native_size":[W,H],"DDS":"RGBA32 mip1 raw mirror_y",
    "machine":{"exact_dds_header":True,"roundtrip_decoded_final":"PASS","changed_rgba_outside_source_boxes":outside,"alpha_outside_source_boxes":alpha_outside,
               "bbox_size_margin":"PASS_BOTH","persisted_file":str(target.relative_to(root))},
    "producer_visual":"PENDING_CONTROLLER_FRESH_NATIVE_75_50_RAW_REVIEW",
    "status":"NEW_MATERIAL_CANDIDATE_NOT_PRODUCER_PASS",
    "C":"NOT_RUN","C3":"NOT_RUN","approval":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED",
    "execution_backend":"GITHUB_ACTIONS_EPHEMERAL_CPU_WORKER","cleanup":"tempfile auto-removes; runner workspace ephemeral",
    "protected_domains_touched":[]}
(out/"B264_MACHINE_AND_PRODUCTION_GATE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"result":"MATERIAL_DDS_PRODUCED_PENDING_VISUAL","candidate_sha256":newsha,"qa":str(out)},ensure_ascii=False))
