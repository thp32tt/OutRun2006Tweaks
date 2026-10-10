#!/usr/bin/env python3
"""B354 q154 C356 gray-menu optical-stroke REWORK: native Regular Korean glyph reconstruction.
Three C2-rejected gray labels ONLY; exact canonical HD English SOURCE, preserved
other five rows. Unapproved DDS trial until source-vs-final optical producer QA.
"""
import os,io,json,hashlib,struct,tempfile,urllib.request,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTCollection
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B354-Q154-THIN-NATIVE-GRAY-SOURCE-FAMILY";OUT.mkdir(parents=True,exist_ok=True)
ASSET=G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
SOURCE_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
OFFICIAL_SHA="c4d6c1515716476123b69dfb645dcc27a3cc7a69f31a1368a831004a0b40d524"
AUTHORED_CLEAN_SHA="a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380"
sha=lambda b:hashlib.sha256(b).hexdigest()
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","154"],check=True,capture_output=True,text=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri["next_action"]
p=ASSET.read_bytes();assert sha(p)==OFFICIAL_SHA,("CONCURRENT_BRANCH_DRIFT",sha(p))
source_path=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
if source_path.exists():s=source_path.read_bytes()
else:
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
 with urllib.request.urlopen(url,timeout=90) as rr:s=rr.read()
assert sha(s)==SOURCE_SHA and p[:128]==s[:128],("CANONICAL_ENGLISH_FAIL",sha(s))
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
source,old=dec(s),dec(p)
assert source.shape==old.shape==(1024,4096,4) and len(p)==16777344
# The C344 independently byte-authenticated eight original regions, and all
# target regions are source-text-only transparency. Never paste any OLD Korean
# glyph beneath a new glyph or modify a non-gray row.
c344=json.loads((G/"role_C/20261010-C344-C2-Q154-EXACT-FULL-CLEAN-PLATE/C344_Q154_EXACT_FULL_CLEAN_MACHINE.json").read_text())
assert c344["sha256"]["SOURCE"]==SOURCE_SHA and c344["sha256"]["FINAL"]==OFFICIAL_SHA
all_regions={r["id"]:tuple(r["bbox"]) for r in c344["regions"]}
assert len(all_regions)==8
all_mask=np.zeros(source.shape[:2],bool)
for l,t,r,b in all_regions.values():all_mask[t:b,l:r]=True
clean=source.copy()
for l,t,r,b in all_regions.values():clean[t:b,l:r]=0
assert not np.any(clean[:,:,3][all_mask])
assert not np.any(np.any(source!=clean,axis=2)&~all_mask)
# C344 authored clean SHA is reported separately and not falsely relabeled
# when a source-derived transparent plate differs in alpha-zero RGB channels.
CLEAN_DERIVED_SHA=sha(Image.fromarray(clean,"RGBA").tobytes())
labels=[
 ("06_single_player_gray","싱글 플레이",(1610,286,2197,350)),
 ("07_showroom_gray","쇼룸",(2674,288,3094,350)),
 ("08_multiplayer_gray","멀티플레이",(2566,952,3086,1014)),
]
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
fontsha=sha(fontpath.read_bytes());font_index=1;ppem=62
font=ImageFont.truetype(str(fontpath),ppem,index=font_index)
cm=TTCollection(str(fontpath)).fonts[font_index].getBestCmap()
for _,word,_ in labels:
 assert all(ord(x) in cm for x in word if x!=" "),("MISSING_GLYPH",word)
# Native-size REGULAR glyph strokes and larger open Korean counters, NOT
# previous Bold silhouette/dilate-by-1 or downscaled/reinflated old raster.
# Source flat gray face is sampled and pinned instead of invented gradient.
face=np.array([78,96,100],np.uint8)
out=old.copy();regions=[];glyph_evidence=[]
for id,word,(l,t,r,b) in labels:
 native_source=source[t:b,l:r]
 sample=(native_source[:,:,3]>=245)&(np.max(np.abs(native_source[:,:,:3].astype(np.int16)-face.astype(np.int16)),axis=2)<=3)
 assert int(sample.sum())>1500,(id,"NO_SOURCE_GRAY_FACE")
 h=b-t;w=r-l
 # Shape each native vector glyph independently with measured ppem, no affine
 # width stretch / shear, and preserve English left baseline anchor.
 d=ImageDraw.Draw(Image.new("L",(10,10)))
 chars=[];adv=0
 for ch in word:
  if ch==" ":
   chars.append((ch,None,22));adv+=22;continue
  bb=d.textbbox((0,0),ch,font=font)
  g=Image.new("L",(bb[2]-bb[0]+4,bb[3]-bb[1]+4),0)
  ImageDraw.Draw(g).text((2-bb[0],2-bb[1]),ch,font=font,fill=255)
  crop=g.getbbox();assert crop,(id,ch)
  g=g.crop(crop)
  assert g.height <= h-3,(id,"NATIVE_HEIGHT",g.height,h)
  chars.append((ch,g,g.width));adv+=g.width
 tracking=10 if id!="07_showroom_gray" else 12
 advance=adv+tracking*(len(chars)-1)
 assert advance < w-8,(id,"SOURCE_WIDTH_LIMIT",advance,w)
 layer=Image.new("L",(w,h),0)
 cursor=5;top=(h-max(z[1].height for z in chars if z[1] is not None))//2
 assert top>=2
 for ch,g,gw in chars:
  if g is not None:layer.paste(g,(cursor,top))
  cursor+=gw+tracking
 mask=np.asarray(layer)
 yy,xx=np.nonzero(mask)
 bb=[l+int(xx.min()),t+int(yy.min()),l+int(xx.max()+1),t+int(yy.max()+1)]
 assert bb[0]>l and bb[1]>t and bb[2]<r and bb[3]<b,(id,bb)
 new=np.zeros_like(old[t:b,l:r])
 new[mask>0,:3]=face;new[:,:,3]=mask
 out[t:b,l:r]=new
 # Source and CLEAN are independently compared before glyph visibility.
 assert np.count_nonzero(clean[t:b,l:r,3])==0
 regions.append({"id":id,"source_bbox":[l,t,r,b],"new_bbox":bb,"text":word,
  "source_gray_pixels":int(sample.sum()),"new_opaque_pixels":int(np.sum(mask>=245)),
  "new_alpha_pixels":int(np.sum(mask>0)),"native_tracking":tracking,
  "advance":advance,"margins":[bb[0]-l,r-bb[2],bb[1]-t,b-bb[3]],
  "glyph_coverage":True,"source_to_clean_alpha_remainder":0})
allowed=np.zeros(old.shape[:2],bool)
for _,_,(l,t,r,b) in labels:allowed[t:b,l:r]=True
changed=np.any(old!=out,axis=2)
assert int((changed&~allowed).sum())==0
assert np.array_equal(old[~allowed],out[~allowed])
# DDS masks/order validated, mirror-Y preserved exactly, decoded persisted.
masks=struct.unpack_from("<IIII",p,92)
assert masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),masks
order=[0,1,2,3] if masks[0]==255 else [2,1,0,3]
saved=p[:128]+np.flipud(out)[:,:,order].copy().tobytes()
assert len(saved)==len(p) and sha(saved)!=OFFICIAL_SHA
persist=dec(saved);assert np.array_equal(persist,out),("DDS_ROUNDTRIP_MISMATCH")
(OUT/"B354_Q154_NATIVE_REGULAR_GRAY_UNAPPROVED.dds").write_bytes(saved)
def vis(a,box,bg=(110,110,110)):
 l,t,r,b=box
 im=Image.fromarray(a[t:b,l:r],"RGBA")
 back=Image.new("RGBA",im.size,bg+(255,));back.alpha_composite(im)
 return back.convert("RGB")
evidence=[]
for name,word,box in labels:
 for scale in (100,75,50):
  panels=[vis(a,box) for a in (source,clean,old,persist)]
  if scale!=100:panels=[a.resize((max(1,round(a.width*scale/100)),max(1,round(a.height*scale/100))),Image.Resampling.LANCZOS) for a in panels]
  W=sum(a.width for a in panels)+30;H=max(a.height for a in panels)
  canvas=Image.new("RGB",(W,H),(110,110,110));offset=0
  for a in panels:canvas.paste(a,(offset,0));offset+=a.width+10
  fn=f"B354_{name}_SOURCE_CLEAN_OFFICIAL_TRIAL_GRAY_{scale}_FLIPY.png"
  canvas.save(OUT/fn,optimize=True);evidence.append(fn)
 panels=[vis(np.flipud(a),[box[0],1024-box[3],box[2],1024-box[1]]) for a in (source,clean,old,persist)]
 W=sum(a.width for a in panels)+30;H=max(a.height for a in panels)
 sheet=Image.new("RGB",(W,H),(110,110,110));offset=0
 for a in panels:sheet.paste(a,(offset,0));offset+=a.width+10
 fn=f"B354_{name}_SOURCE_CLEAN_OFFICIAL_TRIAL_GRAY_100_RAW.png"
 sheet.save(OUT/fn,optimize=True);evidence.append(fn)
 # Preserve lossless isolated CLEAN and Korean-only compositing evidence.
 l,t,r,b=box
 Image.fromarray(clean[t:b,l:r],"RGBA").save(OUT/f"B354_{name}_PLATE_ONLY.png")
 Image.fromarray(out[t:b,l:r],"RGBA").save(OUT/f"B354_{name}_COMPOSITE_ONLY.png")
qa={"role":"B","run":"B354","index":154,"run_key":"OUTRUN-KOR-B354-Q154-NEW-NATIVE-REGULAR-GRAY-20261010-1830",
 "triage":tri["next_action"],"method":"New per-character vector Regular CJK at native ppem62 with unscaled glyph contours and real source-gray RGB; replaced C356-rejected Bold 1px dilation and tight counters, retained canonical SOURCE/CLEAN and five red source-family rows.",
 "source_sha256":SOURCE_SHA,"source_provenance":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "original_clean_sha256_recorded_by_C344":AUTHORED_CLEAN_SHA,"source_derived_alpha_zero_clean_rgba_sha256":CLEAN_DERIVED_SHA,
 "original_official_sha256":OFFICIAL_SHA,"new_unapproved_trial_sha256":sha(saved),
 "native":[4096,1024],"codec":"RGBA32","mip_count":1,"raw_transform":"MIRROR_Y",
 "font_path":str(fontpath),"font_sha256":fontsha,"font_index":font_index,"ppem":ppem,
 "regions":regions,"changed_pixels":int(changed.sum()),"outside_3_regions":int((changed&~allowed).sum()),
 "protected_other_five_unchanged":bool(np.array_equal(old[~allowed],out[~allowed])),
 "persisted_decode_mismatch":int(np.any(persist!=out,axis=2).sum()),
 "evidence":evidence,"producer_stage":"PERSISTED_MECHANICAL_PASS_CONTROLLER_VISUAL_PENDING",
 "fresh_C2":"NOT_RUN","C3":"BLOCKED","official_promoted_dds":0,
 "IGR_STATUS":"NO_NEW_INGAME_EVIDENCE","RUNTIME_VALIDATION":"UNTESTED"}
(OUT/"B354_Q154_MACHINE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"source":{"sha256":SOURCE_SHA,"revision":"Sonic-TV OR2006Sprites 3ce344e7","bbox":all_regions},"clean":{"reference_sha256":AUTHORED_CLEAN_SHA,"derived_full_native_sha256":CLEAN_DERIVED_SHA},"font":{"file":str(fontpath),"sha256":fontsha,"index":font_index,"ppem":ppem},"normal":"CJK native Regular vector no dilation, English left anchor, source-gray [78,96,100]","targets":regions,"protected":"other five original red cells byte-exact","repair_of":"C356 SOURCE_FAMILY_STROKE_OVERWEIGHT|COUNTERSPACE_COMPRESSION","independent_controller_optical_required":True},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B354","saved_sha256":sha(saved),"changed":int(changed.sum()),"outside":0,"regions":regions},ensure_ascii=False),flush=True)
