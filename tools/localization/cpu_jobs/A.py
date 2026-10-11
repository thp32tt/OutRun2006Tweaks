#!/usr/bin/env python3
"""A253 q103: right-leaning medium-light Korean lettering with original clean and native optical weighting.
A real isolated trial DDS only; no C2/C3 or runtime approval.
"""
import csv,hashlib,json,os,struct,sys,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
R=Path.cwd(); D=R/"localization/graphics/role_A/20261012-A253-Q103-SOURCE-ITALIC-REWORK"
D.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A253-Q103-A252-SOURCE-ITALIC-OPTICS-20261012-0700"
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
W=H=2048; BOX=(1432,1980,1786,2025)
ENGLISH="Normal Balance"; KOREAN="일반 밸런스"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
SOURCE_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
A224_SHA="2ad5e25e03bc1c9598548ef64ec397be91eae86f0b4f8d4cc161438c9e354c31"
A252_SHA="f27215f981457c6448fb7a84348998b525a13092b732b3e7de244e3a0f587fce"
A224_DIR=R/"localization/graphics/role_A/20261010-A224-Q103-SOURCE-OPTICAL-CONTOUR"
PREV=R/"localization/graphics/role_A/20261012-A252-Q103-NATIVE-BOLD-CLEAN/A252_Q103_NEW_NATIVE_BOLD_UNPROMOTED.dds"
CLEAN=A224_DIR/"A224_CLEAN_NATIVE_RGBA.png"
CLEAN_GIT_BLOB="f5628c70a5b41e60f29d27d1a4e17451f6d5e400"
SOURCE_CROP_GIT_BLOB="6058250220789ab5d33c9abbd4f463680e239521"
QA=R/"localization/graphics/role_C/20261012-C2-Q103-A252-NEW-SAVED-INDEPENDENT/C2_Q103_A252_INDEPENDENT_QA.json"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
def hs(b):return hashlib.sha256(b).hexdigest()
def check(v,msg):
 if not v:raise RuntimeError("A253_FAIL_CLOSED: "+msg)
def ref(p):return {"path":str(p.relative_to(R)),"sha256":hs(p.read_bytes())}
def pic(a):return Image.fromarray(np.asarray(a,dtype=np.uint8),"RGBA")
def save_png(name,im):
 p=D/(name+".png");im.save(p);return ref(p)
def save_json(name,obj):
 p=D/(name+".json");p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return ref(p)
def decode(b):
 check(b[:4]==b"DDS " and len(b)==128+W*H*4,"DDS RGBA32 dimensions/length")
 check(struct.unpack_from("<II",b,12)==(H,W),"DDS H W mismatch")
 check(struct.unpack_from("<II",b,28)[0]==1 and struct.unpack_from("<I",b,88)[0]==32,"source DDS mip/bitcount changed")
 return np.array(Image.frombytes("RGBA",(W,H),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
def onbg(p,bg):
 return Image.alpha_composite(Image.new("RGBA",p.size,(*bg,255)),p).convert("RGB")
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(t for t in csv.DictReader(f) if t["index"]=="103")
check(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),
      "q103 no longer needs rework")
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","103"],text=True))
status=tri["assets"][0]["next_action"]
check(status in ("NORMAL_QUEUE_SELECTION","MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),"triage denies render")
review=json.loads(QA.read_text(encoding="utf-8"))
check(review["candidate"]["sha256"]==A252_SHA and "REWORK" in review["decision"],"fresh q103 C2 failure SHA no longer matches target")
check(QA.exists() and FONT.exists(),"source-family font/review missing")
oldb=PREV.read_bytes()
check(hs(oldb)==A252_SHA,"A252 independent-rejected exact trial SHA drift")
cleanb=CLEAN.read_bytes()
check(subprocess.check_output(["git","hash-object",str(CLEAN)],text=True).strip()==CLEAN_GIT_BLOB,
      "authentic SHA-pinned source CLEAN image drift")
SOURCE_CROP=A224_DIR/"A224_SOURCE_NATIVE_RGBA.png"
check(subprocess.check_output(["git","hash-object",str(SOURCE_CROP)],text=True).strip()==SOURCE_CROP_GIT_BLOB,
      "authentic SHA-pinned English source cropped image drift")
req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-A253-canonical-source"})
with urllib.request.urlopen(req,timeout=60) as response: sb=response.read()
check(hs(sb)==SOURCE_SHA,"canonical SOURCE mismatch")
S=decode(sb); P=decode(oldb); C=np.array(Image.open(CLEAN).convert("RGBA"))
SOURCE_CROPPED=np.array(Image.open(SOURCE_CROP).convert("RGBA"))
check(C.shape==(105,454,4) and SOURCE_CROPPED.shape==C.shape,
      "source/CLEAN reference exact crop dimensions changed")
# Locate the original A224 source reference precisely within the canonical DDS.
# Never guess or hand-align a cropped clean plate before compositing.
checks=[(3,3),(15,15),(18,80),(17,220),(18,400),(50,30),(50,120),(50,280),(50,420),(88,22),(90,180),(90,430)]
best=(1e9,None,None,None)
for swapped in (False,True):
 for oy in range(1920,H-C.shape[0]+1):
  for ox in range(1335,1420):
   mismatch=0
   for sy,sx in checks:
    a=S[oy+sy,ox+sx]
    if swapped:a=a[[2,1,0,3]]
    mismatch+=int(np.count_nonzero(a!=SOURCE_CROPPED[sy,sx]))
   if mismatch<best[0]:best=(mismatch,ox,oy,swapped)
check(best[0]<=4,"pinned A224 source crop cannot be SHA-pixel aligned with canonical English")
_,OX,OY,SOURCE_SWIZZLED=best
x0,y0,x1,y1=BOX; w=x1-x0;h=y1-y0
rx0=x0-OX;ry0=y0-OY;rx1=x1-OX;ry1=y1-OY
check(0<=rx0<rx1<=454 and 0<=ry0<ry1<=105,"English text bbox outside reference clean crop")
C_REGION=C[ry0:ry1,rx0:rx1]
# Source must actually carry the named English source in this tight region, with
# a separate verified CLEAN plate prepared by A224. A different source fails.
check(np.count_nonzero(S[y0:y1,x0:x1,:3]!=C_REGION[:,:,:3])>6000,
      "source letters not separable from verified CLEAN")
# The old A224 letters must also be different from CLEAN and fully within region.
check(np.count_nonzero(np.any(P[y0:y1,x0:x1]!=C_REGION,axis=2))>2000,
      "old native Hangul not present within original ROI")
# Draw genuine high-resolution Noto Regular outlines from scratch, not upsampled
# rejected A224/A252 glyphs. Calibrate each Korean glyph's height to ~source 45px
# but keep natural translated phrase length; use source-conditioned forward lean.
SS=3
f=ImageFont.truetype(str(FONT),65*SS,index=1)
tmp=Image.new("L",(1800*SS,140*SS),0)
ImageDraw.Draw(tmp).text((12*SS,6*SS),KOREAN,font=f,fill=255)
b=tmp.getbbox()
check(b is not None,"fresh source font raster empty")
genuine=tmp.crop(b)
# High-res supersampling is used for NEW vector glyphs only; no old raster reuse.
target_h=40*SS
target_w=round(genuine.width*target_h/genuine.height)
check(target_w>=200*SS and target_w<=330*SS,"new native glyphs source-family condensed fit")
natural=genuine.resize((target_w,target_h),Image.Resampling.LANCZOS)
lean=0.28
sw=natural.width+int(round(lean*natural.height))+2*SS
sk=natural.transform((sw,natural.height),Image.Transform.AFFINE,
 (1,lean,-lean*natural.height,0,1,0),Image.Resampling.BICUBIC)
bounds=sk.getbbox()
check(bounds is not None,"forward italic missing glyphs")
letters=sk.crop(bounds)
check(letters.width<=w*SS-12*SS and letters.height<=h*SS-6*SS,
      "fresh italic text over English glyph+effect bbox")
layer=Image.new("L",(w*SS,h*SS),0)
px=(layer.width-letters.width)//2
py=(layer.height-letters.height)//2
check(px>=4*SS and py>=2*SS,"foreign overlap before native downsample")
layer.paste(letters,(px,py))
raw_mask=layer.resize((w,h),Image.Resampling.LANCZOS)
# Optical medium-light: small anti-aliased dilation blends 30%, not heavy Bold
# block lettering. Dark source-family face without invented shine.
expanded=raw_mask.filter(ImageFilter.MaxFilter(3))
mask=Image.blend(raw_mask,expanded,0.30)
outline=ImageChops.subtract(expanded,raw_mask)
rim=Image.new("RGBA",(w,h),(119,114,69,0))
rim.putalpha(outline.point(lambda a:int(a*0.25)))
face=Image.new("RGBA",(w,h),(143,137,84,0))
face.putalpha(mask)
trans=Image.alpha_composite(rim,face)
aa=np.asarray(trans)
yy,xx=np.nonzero(aa[:,:,3]>0)
check(len(xx)>3500,"new native regular-italic lettering vanished")
bbox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
margin=[bbox[0],bbox[1],w-bbox[2],h-bbox[3]]
check(min(margin)>=1,"over original source effect bbox: "+str(margin))
# Character-family optical evidence rather than arbitrary phrase-width ratio.
height_check=bbox[3]-bbox[1]
check(36<=height_check<=43,"native per-glyph height outside source family")
# The entire original English label area is reconstructed from the source-derived
# unmodified clean. Never paste a colored rectangle generated by the font into it.
T=P.copy()
T[y0:y1,x0:x1]=np.asarray(Image.alpha_composite(pic(C_REGION),trans))
delta=np.any(T!=P,axis=2)
allow=np.zeros((H,W),bool);allow[y0:y1,x0:x1]=True
check(int(np.count_nonzero(delta))>3000,"no material DDS difference")
check(int(np.count_nonzero(delta&~allow))==0,"unrelated sprite art changed")
check(np.array_equal(T[~allow],P[~allow]),"unrelated alpha RGB modified")
out=D/"A253_Q103_RIGHT_ITALIC_MEDIUM_UNPROMOTED.dds"
out.write_bytes(oldb[:128]+pic(T).transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
check(len(out.read_bytes())==len(oldb),"DDS header size")
V=decode(out.read_bytes())
check(np.array_equal(V,T),"saved persisted DDS decode mismatch")
proof={}
for key,im in [("GEOMETRY",raw_mask),("FACE",face),("RIM",rim),("LETTER",trans),("CLEAN",pic(C_REGION))]:
 proof[key]=save_png("A253_"+key+"_NATIVE",im)
native=(pic(S[y0:y1,x0:x1]),pic(C_REGION),pic(P[y0:y1,x0:x1]),pic(V[y0:y1,x0:x1]))
for bgid,color,percent in [("GRAY100",(110,110,110),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)]:
 ow,oh=max(1,round(w*percent/100)),max(1,round(h*percent/100))
 cmp=Image.new("RGB",(ow*4,oh),color)
 for i,im in enumerate(native):
  cmp.paste(onbg(im,color).resize((ow,oh),Image.Resampling.LANCZOS),(ow*i,0))
 proof[bgid]=save_png("A253_"+bgid+"_SOURCE_CLEAN_A252_NEW_SAVED",cmp)
proof["RAW"]=save_png("A253_NEW_SAVED_RAW",pic(V[y0:y1,x0:x1]).transpose(Image.Transpose.FLIP_TOP_BOTTOM))
proof["READABLE"]=save_png("A253_NEW_SAVED_READABLE",pic(V[y0:y1,x0:x1]))
report={
 "schema_version":2,"run_key":RUN,"role":"A","index":103,
 "independent_fail":"C2 q103 A252 too heavy, square and near-upright native/75/50; source is medium-light condensed right racing italic",
 "triage":status,"independent_C2_evidence":str(QA.relative_to(R)),"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "original_canonical_dds_sha256":SOURCE_SHA,"clean_sha256":hs(cleanb),
 "clean_git_blob_sha":CLEAN_GIT_BLOB,"reference_crop_xy":[OX,OY],
 "crop_source_channel_swapped":SOURCE_SWIZZLED,"crop_alignment_pixel_mismatch":best[0],
 "previous_trial_sha256":A252_SHA,"previous_A224_sha256":A224_SHA,"new_trial_dds":ref(out),"new_trial_count":1,"official_promoted":0,
 "target":{"english":ENGLISH,"korean":KOREAN,"source_exact_effect_bbox":BOX,
           "letter_bbox":[x0+bbox[0],y0+bbox[1],x0+bbox[2],y0+bbox[3]],
           "margin":margin},"method":"new native Noto Regular 65ppem supersampled outline, condensed source-family 40px individual Korean height, forward 0.28 shearing, 30% single-pixel optical medium weight; prior A252 Bold too upright and heavy; old raster NOT rescaled",
 "font":str(FONT),"font_sha256":hs(FONT.read_bytes()),"font_face_index":1,"font_ppem":65,
 "render_scale":SS,"source_shear_x_by_y":lean,"source_family_target":"condensed-medium-light-right-racing-italic","source_tight_bbox":BOX,"new_glyph_native_height":height_check,
 "new_rgba_changed_inside_bbox":int(delta.sum()),"clean_roi_full_source_pixel_match":best[0],
 "new_rgba_changed_outside_source_effect_bbox":int(np.count_nonzero(delta&~allow)),
 "outside_source_effect_alpha_changed":int(np.count_nonzero((T[:,:,3]!=P[:,:,3])&~allow)),
 "persisted_roundtrip_mismatch":int(np.count_nonzero(V!=T)),
 "dds_native":[W,H],"mips":1,"format":"RGBA32",
 "producer_machine":"PASS_SCOPED_SAVED_DDS; VISUAL_REVIEW_REQUIRED",
 "full_producer_visual":"PENDING_CONTROLLER",
 "C2":"NOT_RUN","C3":"NOT_RUN","game":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "original_provenance":"SHA-verified English release source + SHA-verified A224 CLEAN, C2 rejected A252 true saved DDS",
 "proof":proof,"excluded":["VR","FFB","DX11","DXVK"]
}
save_json("A253_MACHINE_AND_HANDOFF",report)
print(json.dumps({"new_sha":ref(out)["sha256"],"changed":int(delta.sum()),"margins":margin,"font_px":65},ensure_ascii=False),flush=True)
