#!/usr/bin/env python3
"""A252 q103: new native bold Korean lettering from canonical English and CLEAN.
A real isolated trial DDS only; no C2/C3 or runtime approval.
"""
import csv,hashlib,json,os,struct,sys,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
R=Path.cwd(); D=R/"localization/graphics/role_A/20261012-A252-Q103-NATIVE-BOLD-CLEAN"
D.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A252-Q103-A224-SOURCE-WEIGHT-NATIVE-20261012-0600"
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
W=H=2048; BOX=(1432,1980,1786,2025)
ENGLISH="Normal Balance"; KOREAN="일반 밸런스"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
SOURCE_SHA="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
A224_SHA="2ad5e25e03bc1c9598548ef64ec397be91eae86f0b4f8d4cc161438c9e354c31"
A224_DIR=R/"localization/graphics/role_A/20261010-A224-Q103-SOURCE-OPTICAL-CONTOUR"
PREV=A224_DIR/"A224_Q103_OPTICAL_CONTOUR_UNPROMOTED.dds"
CLEAN=A224_DIR/"A224_CLEAN_NATIVE_RGBA.png"
CLEAN_GIT_BLOB="f5628c70a5b41e60f29d27d1a4e17451f6d5e400"
SOURCE_CROP_GIT_BLOB="6058250220789ab5d33c9abbd4f463680e239521"
QA=R/"localization/graphics/role_C/20261010-C1-Q103-A224-SOURCE-OPTICAL-REWORK/C1_Q103_A224_CONTROLLER_REWORK.json"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
def hs(b):return hashlib.sha256(b).hexdigest()
def check(v,msg):
 if not v:raise RuntimeError("A252_FAIL_CLOSED: "+msg)
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
check(review["reviewed_candidate_sha256"]==A224_SHA and "REWORK" in review["decision"],"independent evidence no longer matches target")
check(QA.exists() and FONT.exists(),"source-family font/review missing")
oldb=PREV.read_bytes()
check(hs(oldb)==A224_SHA,"A224 exact previous trial SHA drift")
cleanb=CLEAN.read_bytes()
check(subprocess.check_output(["git","hash-object",str(CLEAN)],text=True).strip()==CLEAN_GIT_BLOB,
      "authentic SHA-pinned source CLEAN image drift")
SOURCE_CROP=A224_DIR/"A224_SOURCE_NATIVE_RGBA.png"
check(subprocess.check_output(["git","hash-object",str(SOURCE_CROP)],text=True).strip()==SOURCE_CROP_GIT_BLOB,
      "authentic SHA-pinned English source cropped image drift")
req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-A252-canonical-source"})
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
# Native-source coordinate right italic, new bold outlines, no prior Korean raster resizing.
SS=3
chosen=None
for fs in range(58,38,-1):
 f=ImageFont.truetype(str(FONT),fs*SS,index=1)
 tmp=Image.new("L",(2000*SS,110*SS),0)
 dr=ImageDraw.Draw(tmp)
 dr.text((14*SS,8*SS),KOREAN,font=f,fill=255,stroke_width=0)
 b=tmp.getbbox()
 if not b:continue
 mask=tmp.crop(b)
 skew_k=.12
 sw=mask.width+int(round(skew_k*mask.height))+4*SS
 sk=mask.transform((sw,mask.height),Image.Transform.AFFINE,
                   (1,skew_k,-skew_k*mask.height,0,1,0),Image.Resampling.BICUBIC)
 bbox=sk.getbbox()
 if bbox:sk=sk.crop(bbox)
 if sk.width<=((w-8)*SS) and sk.height<=((h-4)*SS):
  chosen=(sk,fs);break
check(chosen is not None,"new native heavy glyph cannot fit original effect bbox")
letters,fs=chosen
layer=Image.new("L",(w*SS,h*SS),0)
px=(layer.width-letters.width)//2
py=(layer.height-letters.height)//2
check(px>=3*SS and py>=1*SS,"outside bbox before native downsample")
layer.paste(letters,(px,py))
mask=layer.resize((w,h),Image.Resampling.LANCZOS)
# Face and weak one-pixel source-family edge are separate lossless layers.
rim_mask=mask.filter(ImageFilter.MaxFilter(3))
rim=Image.new("RGBA",(w,h),(143,137,84,0))
rim.putalpha(rim_mask.point(lambda a:int(a*0.32)))
face=Image.new("RGBA",(w,h),(133,127,76,0))
face.putalpha(mask)
trans=Image.alpha_composite(rim,face)
aa=np.asarray(trans)
yy,xx=np.nonzero(aa[:,:,3]>0)
check(len(xx)>4000,"native glyph vanished")
bbox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
margin=[bbox[0],bbox[1],w-bbox[2],h-bbox[3]]
check(min(margin)>=1,"over original source effect bbox")
# The entire original English label area is reconstructed from the source-derived
# unmodified clean. Never paste a colored rectangle generated by the font into it.
T=P.copy()
T[y0:y1,x0:x1]=np.asarray(Image.alpha_composite(pic(C_REGION),trans))
delta=np.any(T!=P,axis=2)
allow=np.zeros((H,W),bool);allow[y0:y1,x0:x1]=True
check(int(np.count_nonzero(delta))>3000,"no material DDS difference")
check(int(np.count_nonzero(delta&~allow))==0,"unrelated sprite art changed")
check(np.array_equal(T[~allow],P[~allow]),"unrelated alpha RGB modified")
out=D/"A252_Q103_NEW_NATIVE_BOLD_UNPROMOTED.dds"
out.write_bytes(oldb[:128]+pic(T).transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
check(len(out.read_bytes())==len(oldb),"DDS header size")
V=decode(out.read_bytes())
check(np.array_equal(V,T),"saved persisted DDS decode mismatch")
proof={}
for key,im in [("GEOMETRY",mask),("FACE",face),("RIM",rim),("LETTER",trans),("CLEAN",pic(C_REGION))]:
 proof[key]=save_png("A252_"+key+"_NATIVE",im)
native=(pic(S[y0:y1,x0:x1]),pic(C_REGION),pic(P[y0:y1,x0:x1]),pic(V[y0:y1,x0:x1]))
for bgid,color,percent in [("GRAY100",(110,110,110),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)]:
 ow,oh=max(1,round(w*percent/100)),max(1,round(h*percent/100))
 cmp=Image.new("RGB",(ow*4,oh),color)
 for i,im in enumerate(native):
  cmp.paste(onbg(im,color).resize((ow,oh),Image.Resampling.LANCZOS),(ow*i,0))
 proof[bgid]=save_png("A252_"+bgid+"_SOURCE_CLEAN_A224_NEW_SAVED",cmp)
proof["RAW"]=save_png("A252_NEW_SAVED_RAW",pic(V[y0:y1,x0:x1]).transpose(Image.Transpose.FLIP_TOP_BOTTOM))
proof["READABLE"]=save_png("A252_NEW_SAVED_READABLE",pic(V[y0:y1,x0:x1]))
report={
 "schema_version":2,"run_key":RUN,"role":"A","index":103,
 "independent_fail":"C1 q103 A224 too thin native/50% compared with dark compact source",
 "triage":status,"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "original_canonical_dds_sha256":SOURCE_SHA,"clean_sha256":hs(cleanb),
 "clean_git_blob_sha":CLEAN_GIT_BLOB,"reference_crop_xy":[OX,OY],
 "crop_source_channel_swapped":SOURCE_SWIZZLED,"crop_alignment_pixel_mismatch":best[0],
 "previous_trial_sha256":A224_SHA,"new_trial_dds":ref(out),"new_trial_count":1,"official_promoted":0,
 "target":{"english":ENGLISH,"korean":KOREAN,"source_exact_effect_bbox":BOX,
           "letter_bbox":[x0+bbox[0],y0+bbox[1],x0+bbox[2],y0+bbox[3]],
           "margin":margin},"method":"new bold true native Hangul outlines; source-matched olive monochrome face + subtle contour + right italic, not A224 Regular glyph raster scaling",
 "font":str(FONT),"font_sha256":hs(FONT.read_bytes()),"font_face_index":1,"font_ppem":fs,
 "render_scale":SS,"source_shear_x_by_y":0.12,
 "new_rgba_changed_inside_bbox":int(delta.sum()),
 "new_rgba_changed_outside_source_effect_bbox":int(np.count_nonzero(delta&~allow)),
 "persisted_roundtrip_mismatch":int(np.count_nonzero(V!=T)),
 "dds_native":[W,H],"mips":1,"format":"RGBA32",
 "producer_machine":"PASS_SCOPED_SAVED_DDS; VISUAL_REVIEW_REQUIRED",
 "full_producer_visual":"PENDING_CONTROLLER",
 "C2":"NOT_RUN","C3":"NOT_RUN","game":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "original_provenance":"SHA-verified English release source + SHA-verified A224 CLEAN",
 "proof":proof,"excluded":["VR","FFB","DX11","DXVK"]
}
save_json("A252_MACHINE_AND_HANDOFF",report)
print(json.dumps({"new_sha":ref(out)["sha256"],"changed":int(delta.sum()),"margins":margin,"font_px":fs},ensure_ascii=False),flush=True)
