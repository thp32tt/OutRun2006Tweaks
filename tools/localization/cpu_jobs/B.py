#!/usr/bin/env python3
"""B356 q212 P1 IGR029: new native Korean source-family two-label pilot.
Producer must inspect actual DDS and maintain C2 official REWORK unless pass.
"""
import io,json,os,hashlib,subprocess,sys,urllib.request,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
ROOT=Path("localization/graphics")
ASSET=ROOT/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
OUT=ROOT/"role_B/20261010-B356-Q212-NATIVE-SOURCE-MODE-FAMILY";OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE_SHA="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
OFFICIAL_SHA="e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea"
C158_CLEAN_SHA="c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67"
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri["next_action"]
raw=ASSET.read_bytes();assert sha(raw)==OFFICIAL_SHA,("concurrent_q212_sha_change",sha(raw))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
with urllib.request.urlopen(url,timeout=90) as response:src=response.read()
assert sha(src)==SOURCE_SHA and raw[:128]==src[:128],("invalid_source",sha(src))
def decode(data):
 return np.array(Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=decode(src);O=decode(raw)
assert S.shape==O.shape==(2048,2048,4) and len(src)==len(raw)==16777344
# Source properties C353 mechanically authenticated at exact current SHAs.
# Only two source-text-only sprites are allowed to change. Preserve all 10
# other q212 source/final localized cells, RAW orientation and header.
regions=[
 {"id":"r43_professional","english":"PROFESSIONAL","ko":"프로페셔널 모드",
  "original_bbox":[240,341,637,386],"atlas_roi":[0,341,638,404],"source_opaque_width":395},
 {"id":"r44_outrun","english":"OUTRUN","ko":"아웃런",
  "original_bbox":[1626,524,1837,569],"atlas_roi":[1626,524,1837,587],"source_opaque_width":209},
]
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fb=fontpath.read_bytes();font_sha=sha(fb)
fontindex=1;coverage=TTCollection(str(fontpath)).fonts[fontindex].getBestCmap()
for reg in regions:assert all(ord(ch) in coverage for ch in reg["ko"] if ch!=" ")
result=O.copy();mask=np.zeros(S.shape[:2],bool)
for r in regions:
 l,t,x,b=r["atlas_roi"];mask[t:b,l:x]=True
# For these two slots, existing official Korean may be at the wrong English
# x anchor and tall outside source glyph footprint; we replace the ENTIRE
# source-text ROI with the SOURCE-derived transparent plate before rendering.
C=O.copy()
for r in regions:
 l,t,x,b=r["atlas_roi"];C[t:b,l:x]=0
# C158 full CLEAN provenance is separately sourced; scoped source-clean uses
# two designated empty text cells, not a false whole-atlas identity claim.
rec=[]
for reg in regions:
 l,t,x,b=reg["original_bbox"];left,top,right,bottom=reg["atlas_roi"]
 source_crop=S[t:b,l:x];values=source_crop[source_crop[:,:,3]>=230][:,:3]
 assert len(values)>500,(reg["id"],"SOURCE_FACE_MISSING")
 # In opaque English cores colors are source-conditioned (original orange/red).
 # Use the dominant near-opaque face color, never a guessed brand palette.
 keys,counts=np.unique(values,axis=0,return_counts=True)
 core=keys[counts.argmax()].astype(np.uint8)
 font_size=47 if reg["id"].startswith("r43") else 47
 font=ImageFont.truetype(str(fontpath),font_size,index=fontindex)
 img=Image.new("L",(x-l,b-t),0);d=ImageDraw.Draw(img)
 # Draw directly at output pixel resolution, do not resample old Korean.
 bb=d.textbbox((0,0),reg["ko"],font=font)
 natural_w=bb[2]-bb[0];natural_h=bb[3]-bb[1]
 assert natural_w<=x-l-5 and natural_h<=b-t-3,(reg["id"],natural_w,natural_h,x-l,b-t)
 x0=2-bb[0];y0=((b-t)-natural_h)//2-bb[1]
 assert y0+bb[1]>=1 and y0+bb[3]<b-t
 d.text((x0,y0),reg["ko"],fill=255,font=font,stroke_width=0)
 a=np.array(img)
 ys,xs=np.nonzero(a>16);assert len(xs)>150
 nb=[l+int(xs.min()),t+int(ys.min()),l+int(xs.max()+1),t+int(ys.max()+1)]
 assert nb[0]>l and nb[1]>t and nb[2]<x and nb[3]<b,(reg["id"],nb)
 layer=np.zeros((b-t,x-l,4),np.uint8)
 layer[:,:,:3]=core
 layer[:,:,3]=a
 result[t:b,l:x]=layer
 # O may have historic text in left part of the same ROI; untouched neighbors
 # protected because only exact two ROIs are replaced.
 rec.append({"id":reg["id"],"source_english":reg["english"],"translated_text":reg["ko"],
  "new_text_has_semantic_suffix_for_source_hierarchy":reg["id"].startswith("r43"),
  "native_font_ppem":font_size,"source_bbox":reg["original_bbox"],
  "source_opaque_width":reg["source_opaque_width"],
  "candidate_bbox":nb,"candidate_width":nb[2]-nb[0],
  "candidate_width_ratio":round((nb[2]-nb[0])/reg["source_opaque_width"],4),
  "positive_margins":[nb[0]-l,x-nb[2],nb[1]-t,b-nb[3]],
  "original_source_core_rgb":core.tolist(),
  "clean_alpha_zero":int(np.count_nonzero(C[top:bottom,left:right,3]))==0,
  "source_opaque_face_count":len(values)})
change=np.any(result!=O,axis=2)
assert change.any() and np.count_nonzero(change&~mask)==0
assert np.array_equal(result[~mask],O[~mask])
ddsmasks=struct.unpack_from("<IIII",raw,92)
assert ddsmasks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080))
order=[0,1,2,3] if ddsmasks[0]==255 else [2,1,0,3]
dds=raw[:128]+np.flipud(result)[:,:,order].copy().tobytes()
assert len(dds)==len(raw) and sha(dds)!=OFFICIAL_SHA
D=decode(dds)
assert np.array_equal(D,result),("DDS_ROUNDTRIP_FAIL")
(OUT/"B356_Q212_TWO_FAMILY_NATIVE_UNAPPROVED.dds").write_bytes(dds)
def compose(a,roi,bg,rawview=False):
 l,t,r,b=roi
 if rawview:a=np.flipud(a);t,b=2048-b,2048-t
 im=Image.fromarray(a[t:b,l:r],"RGBA")
 background=Image.new("RGBA",im.size,bg+(255,));background.alpha_composite(im)
 return background.convert("RGB")
evidence=[]
for r in regions:
 for orient in ["FLIPY","RAW"]:
  for bg_name,bg in [("GRAY",(122,122,122)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
   for pct in ([100,75,50] if orient=="FLIPY" else [100]):
    ims=[compose(im,r["atlas_roi"],bg,rawview=orient=="RAW") for im in (S,C,O,D)]
    if pct!=100:ims=[im.resize((max(1,round(im.width*pct/100)),max(1,round(im.height*pct/100))),Image.Resampling.LANCZOS) for im in ims]
    width=sum(im.width for im in ims)+3*8
    sheet=Image.new("RGB",(width,max(im.height for im in ims)),bg)
    off=0
    for im in ims:sheet.paste(im,(off,0));off+=im.width+8
    fn=f"B356_{r['id']}_SOURCE_CLEAN_OFFICIAL_TRIAL_{orient}_{bg_name}_{pct}.png"
    sheet.save(OUT/fn,optimize=True);evidence.append(fn)
 l,t,x,b=r["atlas_roi"]
 Image.fromarray(C[t:b,l:x],"RGBA").save(OUT/f"B356_{r['id']}_PLATE_ONLY.png")
 Image.fromarray(D[t:b,l:x],"RGBA").save(OUT/f"B356_{r['id']}_LETTERING_ONLY.png")
qa={"schema_version":2,"role":"B","run":"B356","queue_index":212,
 "run_key":"OUTRUN-KOR-B356-Q212-P1-SOURCE-FAMILY-SEMANTIC-NATIVE-20261010-1935",
 "priority":"P1_IGR029_SHARED_MODE_ATLAS","triage":tri["next_action"],
 "method":"Complete ROI source-text removal plus native vector Bold English-source-palette Korean titles. For PROFESSIONAL add semantic mode qualifier to fit source hierarchy without single-word stretch or artificial overtracking; OUTRUN title retained Korean established rendering.",
 "canonical_source_sha256":SOURCE_SHA,"full_C158_clean_reference_sha256":C158_CLEAN_SHA,
 "source_clean_stage":"TWO_REGION_SCOPED_ZERO_ALPHA_NOT_FULL_C158_ATLAS",
 "current_official_sha256":OFFICIAL_SHA,"new_unapproved_trial_sha256":sha(dds),
 "new_saved_trial_DDS":1,"official_promoted_DDS":0,
 "native_size":[2048,2048],"dds_format":"RGBA32","mips":1,"raw_orientation":"MIRROR_Y",
 "font_file":str(fontpath),"font_sha256":font_sha,"font_index":fontindex,
 "regions":rec,"changed_rgba_pixels":int(change.sum()),
 "outside_two_rois_rgba_change":int(np.count_nonzero(change&~mask)),
 "protected_other_10_current_cells_byte_exact":True,
 "decoded_persisted_mismatch":int(np.count_nonzero(np.any(D!=result,axis=2))),
 "evidence_previews":evidence,"producer_visual":"CONTROLLER_REQUIRED",
 "independent_C2":"NOT_RUN","C3":"BLOCKED",
 "IGR029":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED"}
(OUT/"B356_MACHINE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"source":{"uri":url,"sha256":SOURCE_SHA,"revision":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"},"full_clean_reference":C158_CLEAN_SHA,"old_official":OFFICIAL_SHA,"font":{"path":str(fontpath),"sha256":font_sha,"index":fontindex},"regions":rec,"protected":"other 10 current atlas cells exact","method":"source native single-pass letters, no lowres upscaling, no width/shear affine","C2_and_runtime_required":True},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B356","sha256":sha(dds),"regions":rec,"changed":int(change.sum()),"outside":0},ensure_ascii=False),flush=True)
