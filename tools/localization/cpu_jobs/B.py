#!/usr/bin/env python3
"""B262 q172 source-measured continuous gold bevel reconstruction, SHA guarded."""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B262 runs only on the controlled GitHub CPU worker")
root=Path.cwd()
gfx=root/"localization/graphics"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
target=gfx/"hd_candidates"/asset
run="20261008-B262-Q172-SOURCE-GOLD-BEVEL"
out=gfx/"role_B"/run
out.mkdir(parents=True, exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","172","--require-safe-rerender"],check=True,capture_output=True,text=True)
triage=json.loads(tri.stdout)["assets"][0]
if triage["next_action"]!="MATERIAL_REWORK": raise RuntimeError(("Not material rework",triage))
(out/"TRIAGE.json").write_text(json.dumps(triage,indent=2,ensure_ascii=False)+"\n")
source_sha="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
candidate_sha="7282687bbc3f5b4e7ea45c03043d84b27204a5b183a8eaa9a08c35bb63eb84e2"
clean_sha="9a0750d0db62345a21dbf4006f2da0b2fe7e96151f40dd5e3d1f5e422bd1d809"
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
 "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
 "Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds")
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
    {"id":"START","korean":"출발","source_bbox":[55,373,136,396],"face_width":62,"face_height":16,"shear_px":8},
    {"id":"GOAL","korean":"골","source_bbox":[595,635,672,659],"face_width":49,"face_height":17,"shear_px":8},
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
    can=Image.new("L",(700,300),0);d=ImageDraw.Draw(can)
    bb=d.textbbox((0,0),item["korean"],font=font)
    d.text((30-bb[0],30-bb[1]),item["korean"],font=font,fill=255)
    bounds=can.getbbox()
    if not bounds:raise RuntimeError("empty Hangul glyph")
    mask=can.crop(bounds).resize((item["face_width"],item["face_height"]),Image.Resampling.LANCZOS)
    w,h=mask.size;s=item["shear_px"]
    mask=mask.transform((w+s,h),Image.Transform.AFFINE,(1,s/(h-1),-s,0,1,0),
                        resample=Image.Resampling.BICUBIC)
    cov=np.asarray(mask,dtype=np.uint8)
    face=cov>105
    if np.count_nonzero(face)<100:raise RuntimeError(("too little Hangul face",item["id"]))
    # 2-pixel right-italic extrusion, warm gold contour and continuous
    # face gradient. This replaces B255 horizontal-bar fill, not its shear.
    shadow=np.zeros_like(face)
    shadow[1:,1:]=binary_dilation(face,iterations=1)[:-1,:-1]
    outer=binary_dilation(face,iterations=1)
    bevel=face & ~binary_erosion(face,iterations=1)
    top_edge=bevel & (np.indices(face.shape)[0]<=h//2)
    inner=face & ~bevel
    # The glyph-effect extent must remain strictly inside the native English bbox.
    shape=(y1-y0,x1-x0)
    patch=result[y0:y1,x0:x1].copy().astype(np.float32)
    cleanpatch=clean[y0:y1,x0:x1].copy().astype(np.float32)
    patch[:]=cleanpatch
    gw,gh=outer.shape[1],outer.shape[0]
    cx=(x1-x0)//2;cy=(y1-y0)//2
    x=cx-gw//2;y=cy-gh//2
    if min(x-2,y-2,shape[1]-(x+gw+2),shape[0]-(y+gh+2))<0:
        raise RuntimeError(("effect doesn't fit native English bbox",item["id"],x,y,gw,gh,shape))
    region=patch[y:y+gh,x:x+gw]
    shadow_only=shadow & ~outer
    region[shadow_only,:3]=[129,31,28]
    region[shadow_only,3]=255
    edge=outer & ~face
    region[edge,:3]=[179,64,28]
    region[edge,3]=255
    region[bevel,:3]=[230,135,48]
    region[bevel,3]=255
    region[top_edge,:3]=[255,217,118]
    region[top_edge,3]=255
    YY,XX=np.indices(face.shape)
    # Across each Hangul stroke: continuous bright center to warm bottom.
    # No discrete horizontal-palette stripes or post-scale bitmap effects.
    mix=np.clip((YY / max(h-1,1))*0.82 + 0.05,0,1)[...,None]
    grad=top[None,None,:]*(1-mix)+bottom[None,None,:]*mix
    grad=np.maximum(grad,[218,139,85])
    grad=np.clip(grad,0,255)
    region[inner,:3]=grad[inner]
    region[inner,3]=255
    # Native antialiased fringe blends with warm contour at partial coverage.
    aa=(cov>12)&~outer
    region[aa,:3]=[183,83,39]
    region[aa,3]=255
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
qa={"run":"B262","run_key":"OUTRUN-KOR-B262-Q172-SOURCE-GOLD-20261008-1730",
    "queue_index":172,"source_sha256":source_sha,"prior_candidate_sha256":candidate_sha,
    "new_candidate_sha256":newsha,"clean_plate_sha256":clean_sha,
    "method":"SOURCE-SAMPLED-CONTINUOUS-CREAM-GOLD-GRADIENT_PLUS_PER_GLYPH_BEVEL",
    "source_anchored_regions":spec,"native_size":[W,H],"DDS":"RGBA32 mip1 raw mirror_y",
    "machine":{"exact_dds_header":True,"roundtrip_decoded_final":"PASS","changed_rgba_outside_source_boxes":outside,"alpha_outside_source_boxes":alpha_outside,
               "bbox_size_margin":"PASS_BOTH","persisted_file":str(target.relative_to(root))},
    "producer_visual":"PENDING_CONTROLLER_FRESH_NATIVE_75_50_RAW_REVIEW",
    "status":"NEW_MATERIAL_CANDIDATE_NOT_PRODUCER_PASS",
    "C":"NOT_RUN","C3":"NOT_RUN","approval":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED",
    "execution_backend":"GITHUB_ACTIONS_EPHEMERAL_CPU_WORKER","cleanup":"tempfile auto-removes; runner workspace ephemeral",
    "protected_domains_touched":[]}
(out/"B262_MACHINE_AND_PRODUCTION_GATE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"result":"MATERIAL_DDS_PRODUCED_PENDING_VISUAL","candidate_sha256":newsha,"qa":str(out)},ensure_ascii=False))
