#!/usr/bin/env python3
"""A248: materially new q121 P0 original-conditioned native italic font/face/rim
trial after independent A240 punctuation and A241 crowded/angular rejections.
Only Gas Pedal rank20 cell; official DDS and other 29 labels unchanged.
Producer-only trial: C2 PLATE + full C2/C3/actual user-game still required.
"""
import csv, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageFilter
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
DEST=ROOT/"localization/graphics/role_A/20261012-A248-Q121-NATIVE-ITALIC-FONT-NEW-METHOD"
DEST.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A248-Q121-P0-NATIVE-ITALIC-FONT-20261012-0100"
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
OFF=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
PREV=ROOT/"localization/graphics/role_A/20261011-A241-Q121-PUNCTUATION-TRACKING-REFIT/A241_Q121_MANUAL_SOURCE_FAMILY_UNPROMOTED.dds"
HASHES={"source":"f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e",
"official":"38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844",
"a241":"dba8745f3cadac8bc35b2ad1d19862d57c3207cb368ac626df0e4aa287ba1659"}
W=4096
ROI=(3490,391,3722,440)
TEXT="가속 페달:"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
def sha(x):return hashlib.sha256(x).hexdigest()
def guard(b,why):
 if not b:raise RuntimeError("A248_FAIL_CLOSED: "+why)
def digest(p):return sha(p.read_bytes())
def ref(p):return {"path":str(p.relative_to(ROOT)),"sha256":digest(p)}
def png(name,im):
 p=DEST/(name+".png");im.save(p);return ref(p)
def jfile(name,data):
 p=DEST/(name+".json");p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return ref(p)
def decode(blob):
 guard(blob[:4]==b"DDS " and len(blob)==128+W*W*4,"RGBA32 DDS file size")
 guard(struct.unpack_from("<II",blob,12)==(W,W),"native dimensions")
 guard(struct.unpack_from("<I",blob,28)[0]==1,"mips")
 guard(struct.unpack_from("<I",blob,88)[0]==32,"RGBBitCount")
 guard(struct.unpack_from("<IIII",blob,92)==(255,65280,16711680,4278190080),"channel masks")
 return np.array(Image.frombytes("RGBA",(W,W),blob[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
def background(img,rgb):return Image.alpha_composite(Image.new("RGBA",img.size,(*rgb,255)),img).convert("RGB")
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as fh:
 rec=next(q for q in csv.DictReader(fh) if q["index"]=="121")
guard(rec["action"]=="localize_text" and "rework" in rec["artwork_status"].lower(),"q121 no longer in rework")
# CSV freeform notes contain legacy embedded quoting; do not use them as a SHA gate.
# Exact A241/official/source SHA below is the fail-closed identity protection.
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","121"],check=True,capture_output=True,text=True)
jfile("A248_PRIOR_REWORK_TRIAGE",{"run":RUN,"decision":"MATERIAL_NEW_METHOD_AFTER_A241_OPTICAL_SOURCE_FAMILY_FAIL", "command":"rework_triage --index 121","stdout":tri.stdout,"stderr":tri.stderr})
guard(FONT.is_file(),"pinned exact installed native CJK font")
font_sha=digest(FONT)
sb,ob,pb=SOURCE.read_bytes(),OFF.read_bytes(),PREV.read_bytes()
for label,blob in [("source",sb),("official",ob),("a241",pb)]:guard(sha(blob)==HASHES[label],label+" SHA changed")
guard(sb[:128]==ob[:128]==pb[:128],"DDS headers differ")
S,O,P=decode(sb),decode(ob),decode(pb)
x0,y0,x1,y1=ROI
src=Image.fromarray(S[y0:y1,x0:x1],"RGBA")
old=Image.fromarray(O[y0:y1,x0:x1],"RGBA")
previous=Image.fromarray(P[y0:y1,x0:x1],"RGBA")
guard(np.count_nonzero(S[y0:y1,x0:x1,3])>5000,"source glyph unexpectedly blank")
guard(np.count_nonzero(O[y0:y1,x0:x1,3])>1000,"official legacy glyph unexpectedly blank")
guard(np.array_equal(O[:y0],P[:y0]),"old A241 changed upstream atlas")
# Native Hangul contours from licensed genuine glyphs; supersampled ONCE. The
# old angular hand-lettered faces are NOT reused. Forward racing-italic
# shear in readable orientation. Separate navy rim and white face.
SCALE=4
cw,ch=x1-x0,y1-y0
font=ImageFont.truetype(str(FONT),38*S,index=1)
canvas=Image.new("L",(380*S,100*S))
ImageDraw.Draw(canvas).text((12*S,0),TEXT,font=font,fill=255)
bb=canvas.getbbox();guard(bb is not None,"no font glyphs")
plain=canvas.crop(bb)
shear=0.28
affine_w=plain.width+round(plain.height*shear)+4*S
lean=plain.transform((affine_w,plain.height),Image.Transform.AFFINE,
                      (1,shear,-round(plain.height*shear),0,1,0),
                      resample=Image.Resampling.BICUBIC)
bb=lean.getbbox();guard(bb is not None,"affine lost glyphs")
lean=lean.crop(bb)
guard(lean.width<=(cw-10)*S and lean.height<=(ch-8)*S,"native glyph must fit strict bbox and margins")
face_mask=Image.new("L",(cw*S,ch*S))
ax=6*S
ay=(ch*S-lean.height)//2
guard(ay>=4*S and (ch*S-ay-lean.height)>=4*S,"effect inset fail")
face_mask.paste(lean,(ax,ay))
# Curved anti-aliased font glyph topology with a rounded, not squared,
# source-family navy keyline. No rectangle or invented external artwork.
outline_mask=face_mask.filter(ImageFilter.MaxFilter(17))
face=Image.new("RGBA",face_mask.size,(246,250,250,0));face.putalpha(face_mask)
rim=Image.new("RGBA",face_mask.size,(0,31,63,0));rim.putalpha(outline_mask)
composed=Image.alpha_composite(rim,face).resize((cw,ch),Image.Resampling.LANCZOS)
face_native=face.resize((cw,ch),Image.Resampling.LANCZOS)
rim_native=rim.resize((cw,ch),Image.Resampling.LANCZOS)
arr=np.array(composed)
al=np.asarray(composed.getchannel("A"))
ys,xs=np.nonzero(al>0)
guard(xs.size>1300 and ys.size>1300,"empty/low density new glyph")
bbox_local=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
margin=(bbox_local[0],bbox_local[1],cw-bbox_local[2],ch-bbox_local[3])
guard(min(margin)>=1,"source effect 1px overflow/touch")
guard(bbox_local[2]-bbox_local[0]<=cw and bbox_local[3]-bbox_local[1]<=ch,"source text box overflow")
guard(np.count_nonzero(np.asarray(previous)!=arr)>1000,"new material technique did not change face")
# Scoping: the only authorized rework rectangle is this exact English source
# glyph/effect bbox. Every other pixel, including 29 other ranks and protected
# model art, must remain exactly as existing official candidate.
T=O.copy()
T[y0:y1,x0:x1]=arr
allowed=np.zeros((W,W),bool);allowed[y0:y1,x0:x1]=True
delta=np.any(T!=O,axis=2)
outside=int(np.count_nonzero(delta&~allowed))
guard(outside==0,"altered adjacent sprite")
guard(np.array_equal(T[~allowed],O[~allowed]),"background changed outside rank20")
plate=Image.fromarray(np.zeros_like(arr),"RGBA")
glyph=Image.fromarray(arr,"RGBA")
full=Image.fromarray(T,"RGBA")
out=DEST/"A248_Q121_RANK20_NATIVE_ITALIC_TRIAL_UNPROMOTED.dds"
out.write_bytes(ob[:128]+full.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
actual=decode(out.read_bytes())
guard(np.array_equal(actual,T),"saved DDS decoded pixels differ")
guard(out.stat().st_size==len(ob),"DDS size changed")
newref=ref(out)
images={"english_source":png("A248_SOURCE_ENGLISH_GAS_PEDAL_NATIVE",src),
"official":png("A248_OLD_OFFICIAL_KOREAN_NATIVE",old),
"a241":png("A248_PREVIOUS_A241_ANGULAR_NATIVE",previous),
"clean":png("A248_EXACT_SOURCE_BBOX_CLEAN_NATIVE",plate),
"native_rim":png("A248_RIM_NAVY_NATIVE",rim_native),
"native_face":png("A248_FACE_WHITE_NATIVE",face_native),
"native_lettering":png("A248_NEW_ITALIC_LETTERING_NATIVE",glyph),
"saved_native":png("A248_SAVED_DDS_FLIPY_RANK20_NATIVE",Image.fromarray(actual[y0:y1,x0:x1],"RGBA")),
"saved_raw":png("A248_SAVED_DDS_RAW_RANK20_NATIVE",Image.fromarray(actual[y0:y1,x0:x1],"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))}
for label,rgb,pct in (("GRAY100",(110,110,110),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)):
 panels=[background(v,rgb) for v in [src,old,previous,plate,face_native,rim_native,Image.fromarray(actual[y0:y1,x0:x1],"RGBA")]]
 w=max(1,round(cw*pct/100));h=max(1,round(ch*pct/100))
 canvas=Image.new("RGB",(len(panels)*w,h),rgb)
 for i,panel in enumerate(panels):
  canvas.paste(panel.resize((w,h),Image.Resampling.LANCZOS),(i*w,0))
 images[label]=png("A248_"+label+"_SOURCE_OFFICIAL_A241_CLEAN_FACE_RIM_SAVED",canvas)
recipe={"schema":"a248-native-source-conditioned-italic-font-v1","role":"A","run_key":RUN,
"source":ref(SOURCE),"official":ref(OFF),"prior_rejected_a241":ref(PREV),
"font":ref(FONT) if False else {"installed_font_file":str(FONT),"sha256":font_sha,"font_family":"Noto Sans CJK KR Bold","font_collection_index":1,"license":"SIL OFL"},
"text":TEXT,"source_english":"Gas Pedal :","source_readable_bbox":ROI,"raw_orientation":"Y_MIRROR",
"native_rendered_px":38,"supersample":4,"right_italic_shear":shear,
"face_rgb":[246,250,250],"navy_rim_rgb":[0,31,63],"max_filter_supersampled":17,
"font_glyph_face":images["native_face"],"navy_rim":images["native_rim"],
"clean":images["clean"],"lettering":images["native_lettering"],
"new_persisted_dds":newref,"stage_gate":"UNPROMOTED_PRODUCER_SCOPED_PENDING_FIRSTHAND_C2"}
recipe_ref=jfile("A248_SOURCE_FAMILY_AND_SEPARATE_LAYERS_RECIPE",recipe)
summary={"role":"A","run":"A248","run_key":RUN,"asset_index":121,"priority":"P0",
"source_sha256":HASHES["source"],"official_sha256":HASHES["official"],
"prior_A241_sha256":HASHES["a241"],"saved_new_sha256":newref["sha256"],
"source_bbox_readable":ROI,"actual_new_effect_bbox_local":bbox_local,"positive_margins_ltrb":margin,
"official_vs_trial_changed_px":int(np.count_nonzero(delta)),
"outside_original_source_bbox_changed":outside,
"old_A241_to_new_rgba_changed":int(np.count_nonzero(np.any(P[y0:y1,x0:x1]!=arr,axis=2))),
"other29_cells_exact":True,"saved_roundtrip_mismatch":int(np.count_nonzero(actual!=T)),
"native_dimensions":[W,W],"DDS_format":"RGBA32","mips":1,
"new_saved_trial_dds":1,"official_promoted_dds":0,
"producer_visual":"PENDING_FIRSTHAND_SOURCE_NATIVE_75_50_RAW",
"plate":"SOURCE_BOUNDED_TRANSPARENT_DIAGNOSTIC_C2_PLATE_UNAPPROVED",
"C2":"NOT_RUN_NEW_SHA","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
"user_IGR":["IGR030","IGR031","IGR040"],"images":images,"recipe":recipe_ref,
"excluded":["VR","FFB","DX11","DXVK"]}
jfile("A248_MACHINE_AND_SELF_QA_HANDOFF",summary)
print(json.dumps({"run":"A248","SHA":newref["sha256"],"outside":outside,"rgba_changed":summary["official_vs_trial_changed_px"],"margin":margin,"new_trial":1},ensure_ascii=False),flush=True)
