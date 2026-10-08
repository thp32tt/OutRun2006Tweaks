#!/usr/bin/env python3
"""B265 q172 per-stroke signed-distance metal normal reconstruction, SHA guarded."""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, gaussian_filter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B265 source-family geometry change requires GitHub CPU worker")
root=Path.cwd()
gfx=root/"localization/graphics"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
target=gfx/"hd_candidates"/asset
run="20261008-B265-Q172-STROKE-NORMAL-MAP-CREAM"
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
    raise RuntimeError(("B265 needs C291+C295 method change escalation",triage_decision))
blind=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","172","--require-safe-rerender"],capture_output=True,text=True)
if blind.returncode!=2:raise RuntimeError("same-method rerender guard failed")
(out/"B265_TRIAGE.json").write_text(json.dumps(triage_decision,ensure_ascii=False,indent=2)+"\n")
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
    {"id":"START","korean":"출발","source_bbox":[55,373,136,396],"glyph_width":22,"face_height":18,"shear_px":7},
    {"id":"GOAL","korean":"골","source_bbox":[595,635,672,659],"glyph_width":29,"face_height":19,"shear_px":7},
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

    # Replace the C291/C295/B264 flat-band technique with physically located
    # per-stroke surface normals, source-anchored cream-white highlights and
    # copper extrusion. Never sample one horizontal gold band across Hangul.
    U=8
    glyphs=[]
    for ch in item["korean"]:
        gc=Image.new("L",(460,350),0);d=ImageDraw.Draw(gc)
        bb=d.textbbox((0,0),ch,font=font)
        d.text((30-bb[0],30-bb[1]),ch,font=font,fill=255)
        ink=gc.getbbox()
        if not ink:raise RuntimeError(("no glyph",ch))
        w,h,s=item["glyph_width"],item["face_height"],item["shear_px"]
        high=gc.crop(ink).resize((w*U,h*U),Image.Resampling.LANCZOS)
        high=high.transform(((w+s)*U,h*U),Image.Transform.AFFINE,
                            (1,s/(h-1),-s*U,0,1,0),resample=Image.Resampling.BICUBIC)
        glyphs.append(np.asarray(high.resize((w+s,h),Image.Resampling.LANCZOS),dtype=np.uint8))
    gap=2 if len(glyphs)>1 else 0
    w=sum(g.shape[1] for g in glyphs)+(len(glyphs)-1)*gap
    h=max(g.shape[0] for g in glyphs)
    cov=np.zeros((h,w),dtype=np.uint8)
    off=0
    for g in glyphs:
        cov[:g.shape[0],off:off+g.shape[1]]=np.maximum(cov[:g.shape[0],off:off+g.shape[1]],g)
        off+=g.shape[1]+gap
    cov=np.pad(cov,((2,2),(2,2)))
    face=cov>=100
    if np.count_nonzero(face)<75:raise RuntimeError(("invalid native syllable mask",item["id"]))
    outer=binary_dilation(face,iterations=1)
    shadow=np.zeros_like(face)
    shadow[2:,2:]=binary_dilation(face,iterations=1)[:-2,:-2]
    outer_detail=outer&~face
    shadow_only=shadow&~outer
    dist=distance_transform_edt(face).astype(np.float32)
    surface=gaussian_filter(cov.astype(np.float32)/255.0,0.85)
    gy,gx=np.gradient(surface)
    norm=np.sqrt(gx*gx+gy*gy)+1e-5
    nx,ny=gx/norm,gy/norm
    # Specularity follows actual curved stems/counters: no horizontal stripes.
    specular=np.clip(0.58*(-nx)+0.82*(-ny),0,1)
    micro=specular*np.exp(-np.maximum(dist-1,0)*0.85)
    near_face=face&(dist<=1.12)
    body=face&~near_face
    shape=(y1-y0,x1-x0);gw,gh=face.shape[1],face.shape[0]
    x=(shape[1]-gw)//2;y=(shape[0]-gh)//2
    if min(x,y,shape[1]-x-gw,shape[0]-y-gh)<0:
        raise RuntimeError(("normal-map effect cannot fit original source bbox",item["id"],shape,gw,gh))
    patch=clean[y0:y1,x0:x1].copy().astype(np.float32)
    region=patch[y:y+gh,x:x+gw]
    region[shadow_only,:3]=[121,42,27];region[shadow_only,3]=255
    copper=shadow&~face&~shadow_only
    region[copper,:3]=[168,59,35];region[copper,3]=255
    region[outer_detail,:3]=[229,118,49];region[outer_detail,3]=255
    p85=np.array(item["profile"]["source_face_top_rgb"],dtype=np.float32)
    p48=np.array(item["profile"]["source_face_bottom_rgb"],dtype=np.float32)
    base=np.maximum(p85*0.89+p48*0.11,[248,223,191])
    ycoords=np.indices(face.shape)[0].astype(np.float32)/max(gh-1,1)
    base_rgb=base[None,None,:]-ycoords[:,:,None]*np.array([3,13,19])[None,None,:]
    rgbs=np.broadcast_to(base_rgb,region[:,:,:3].shape).copy()
    rgbs+=micro[:,:,None]*np.array([8,25,25])[None,None,:]
    rgbs=np.clip(rgbs,0,255)
    region[body,:3]=rgbs[body];region[body,3]=255
    warm=np.clip(0.50*nx+0.70*ny,0,1)
    edge_rgb=(np.array([248,200,135],dtype=np.float32)[None,None,:]
              -warm[:,:,None]*np.array([25,65,70])[None,None,:])
    edge_rgb+=micro[:,:,None]*np.array([7,40,60])[None,None,:]
    edge_rgb=np.clip(edge_rgb,0,255)
    region[near_face,:3]=edge_rgb[near_face];region[near_face,3]=255
    highlights=near_face&(specular>0.40)
    region[highlights,:3]=[255,250,224]
    fringe=(cov>24)&(~face)&(~outer_detail)
    region[fringe,:3]=[240,171,103];region[fringe,3]=255
    creams=(region[:,:,0]>=247)&(region[:,:,1]>=220)&face
    item["cream_face_pixels"]=int(creams.sum())
    item["face_pixels"]=int(face.sum())
    item["surface_method"]="SDF_STROKE_NORMALS_SOURCE_WHITE_CREAM_AND_COPPER_DEPTH"
    if creams.sum()<face.sum()*0.40:
        raise RuntimeError(("too little source-white face",item["id"],int(creams.sum()),int(face.sum())))
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
qa={"run":"B265","run_key":"OUTRUN-KOR-B265-Q172-STROKE-SDF-20261008-1930",
    "queue_index":172,"source_sha256":source_sha,"prior_candidate_sha256":candidate_sha,
    "new_candidate_sha256":newsha,"clean_plate_sha256":clean_sha,
    "method":"SDF_PER_STROKE_NORMALS_SOURCE_CREAM_CHROME_AND_COPPER_DEPTH",
    "source_anchored_regions":spec,"native_size":[W,H],"DDS":"RGBA32 mip1 raw mirror_y",
    "machine":{"exact_dds_header":True,"roundtrip_decoded_final":"PASS","changed_rgba_outside_source_boxes":outside,"alpha_outside_source_boxes":alpha_outside,
               "bbox_size_margin":"PASS_BOTH","persisted_file":str(target.relative_to(root))},
    "producer_visual":"PENDING_CONTROLLER_FRESH_NATIVE_75_50_RAW_REVIEW",
    "status":"NEW_MATERIAL_CANDIDATE_NOT_PRODUCER_PASS",
    "C":"NOT_RUN","C3":"NOT_RUN","approval":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED",
    "execution_backend":"GITHUB_ACTIONS_EPHEMERAL_CPU_WORKER","cleanup":"tempfile auto-removes; runner workspace ephemeral",
    "protected_domains_touched":[]}
(out/"B265_MACHINE_AND_PRODUCTION_GATE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"result":"MATERIAL_DDS_PRODUCED_PENDING_VISUAL","candidate_sha256":newsha,"qa":str(out)},ensure_ascii=False))
