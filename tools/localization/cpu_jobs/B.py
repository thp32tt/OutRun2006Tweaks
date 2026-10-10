#!/usr/bin/env python3
"""B362 P1 q212 r43: source-sized Korean lighter outline counter-preserving FINAL pilot.
Do not repeat B358 untouched Noto Bold whole-word weak 284/395 typography:
draw individually positioned glyph outlines with native 1px stroke,
original orange face, source-limited 10px native tracking, and clean-before-ink.\nB361 first saved native 2px counter-collapse visual FAIL is immutable and\nexcluded from official promotion; this is the final same-family correction.
Only r43 changed; r44 and other 10 atlas cells remain exact official bytes.
This is a scoped unapproved trial, never independent C/C3/game PASS.
"""
import io,json,os,hashlib,subprocess,sys,urllib.request,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
ROOT=Path("localization/graphics")
ASSET=ROOT/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
OUT=ROOT/"role_B/20261011-B362-Q212-R43-NATIVE-OPEN-COUNTERS";OUT.mkdir(parents=True,exist_ok=True)
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
# Source q212 and original sprite ROI are independently pinned.
# Inspect reusable CLEAN library before creation. A missing q212 entry is
# not a license to reuse an unrelated plate. B358 established source alpha0
# exact r43, so reconstruct only that SCOPED transparent source sprite.
lookup=subprocess.run([sys.executable,"tools/localization/plate_library.py","inspect",
 "--index","212","--source-sha",SOURCE_SHA,"--region","r43_professional",
 "--orientation","readable_flip_y"],capture_output=True,text=True)
plate_library_status="NOT_REGISTERED_REUSE_B358_SOURCE_ALPHA_ZERO_SCOPED_PROOF"
if lookup.returncode==0:
 evidence_lookup=json.loads(lookup.stdout)
 plate_library_status=evidence_lookup.get("plate_review","HOLD")
 # No new CLEAN construction if a named exact reusable plate exists.
 assert plate_library_status=="PLATE_PASS",("REGISTERED_PLATE_REQUIRES_C2_REVIEW",evidence_lookup)
 # Registered plate is not silently disregarded; require a separate migration.
 raise RuntimeError("EXACT_REGISTERED_PLATE_EXISTS_REVIEW_PREPARE_FIRST")
assert "missing or ambiguous" in lookup.stderr.lower(),("UNEXPECTED_PLATE_LIBRARY_ERROR",lookup.stderr[-350:])
# Deliberately one r43 pilot only, whole atlas retains 11 existing cells.
regions=[
 {"id":"r43_professional","english":"PROFESSIONAL","ko":"프로페셔널 모드",
  "original_bbox":[240,341,637,386],"atlas_roi":[0,341,638,404],"source_opaque_width":395},
]
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fb=fontpath.read_bytes();font_sha=sha(fb)
fontindex=1;coverage=TTCollection(str(fontpath)).fonts[fontindex].getBestCmap()
for reg in regions:assert all(ord(ch) in coverage for ch in reg["ko"] if ch!=" ")
result=O.copy();mask=np.zeros(S.shape[:2],bool)
for r in regions:
 l,t,x,b=r["atlas_roi"];mask[t:b,l:x]=True
# C2 B357 proved old Korean pixels leaked because C was constructed but
# result stayed initialized from O outside original English glyph bboxes.
# Do not paint Korean onto those stale bytes. The known source-transparent
# English title sprites get an independently decoded zero-alpha CLEAN PLATE;
# preserve the other ten atlas cells, and make this full-roi CLEAN the actual
# composite base BEFORE any glyph is added.
C=O.copy()
for r in regions:
 l,t,x,b=r["atlas_roi"]
 assert np.count_nonzero(S[t:b,l:x,3])>100,("canonical_source_slot_empty",r["id"])
 C[t:b,l:x]=0
 assert np.count_nonzero(C[t:b,l:x,3])==0,("P1_DIRTY_CLEAN",r["id"])
result[mask]=C[mask]
assert np.count_nonzero(result[mask,3])==0,"P3_COMPOSITE_BASE_DIRTY"
# C158 full CLEAN provenance is separately sourced; scoped source-clean uses
# two designated empty text cells, not a false whole-atlas identity claim.
rec=[]
for reg in regions:
 l,t,x,b=reg["original_bbox"];left,top,right,bottom=reg["atlas_roi"]
 source_crop=S[t:b,l:x];values=source_crop[source_crop[:,:,3]>=230][:,:3]
 assert len(values)>500,(reg["id"],"SOURCE_FACE_MISSING")
 # Original source orange face is directly sampled; not a guessed UI color.
 keys,counts=np.unique(values,axis=0,return_counts=True)
 core=keys[counts.argmax()].astype(np.uint8)
 # One source-sized manual letter-layout method, not whole-word width stretch.
 # First determine a legitimate source-limited native point size; stroke
 # outlines at the final 2048 native atlas scale without bitmap resizing.
 stroke_px=1
 tracking_px=10
 trial_geom=[]
 for font_size in range(43,37,-1):
  font=ImageFont.truetype(str(fontpath),font_size,index=fontindex)
  measure=ImageDraw.Draw(Image.new("L",(1,1),0))
  bb=measure.textbbox((0,0),reg["ko"],font=font,stroke_width=stroke_px)
  text_w=bb[2]-bb[0]+tracking_px*(len(reg["ko"])-1)
  text_h=bb[3]-bb[1]
  trial_geom.append([font_size,text_w,text_h])
  if text_w<=(x-l)-4 and text_h<=(b-t)-4:break
 else:
  raise ValueError(("NATIVE_OUTLINE_TOO_WIDE_OR_TALL",trial_geom))
 img=Image.new("L",(x-l,b-t),0);d=ImageDraw.Draw(img)
 natural_w,natural_h=text_w,text_h
 pen=float(((x-l)-natural_w)//2-bb[0])
 baseline=((b-t)-natural_h)//2-bb[1]
 for ch in reg["ko"]:
  if ch!=" ":
   d.text((round(pen),baseline),ch,font=font,fill=255,
          stroke_width=stroke_px,stroke_fill=255)
  pen += float(d.textlength(ch,font=font))+tracking_px
 assert natural_w>reg["source_opaque_width"]*.84,("SOURCE_HIERARCHY_UNDERFILL",natural_w)
 a=np.array(img)
 ys,xs=np.nonzero(a>16);assert len(xs)>150
 nb=[l+int(xs.min()),t+int(ys.min()),l+int(xs.max()+1),t+int(ys.max()+1)]
 assert nb[0]>l and nb[1]>t and nb[2]<x and nb[3]<b,(reg["id"],nb)
 layer=np.zeros((b-t,x-l,4),np.uint8)
 layer[:,:,:3]=core
 layer[:,:,3]=a
 result[t:b,l:x]=layer
 # Existing official r44 and other ten atlas cells must remain bit-exact.
 # C2 hard-fail gate: no inherited official glyph may survive anywhere
 # inside the full sprite ROI outside the original English glyph bbox.
 inside=np.zeros((bottom-top,right-left),bool)
 inside[t-top:b-top,l-left:x-left]=True
 old_outside=int(np.count_nonzero(O[top:bottom,left:right,3][~inside]))
 new_outside=int(np.count_nonzero(result[top:bottom,left:right,3][~inside]))
 assert new_outside==0,("OLD_KOREAN_LEAK",reg["id"],old_outside,new_outside)
 assert np.array_equal(result[t:b,l:x,3],a),("P3_GLYPH_ONLY_ALPHA",reg["id"])
 rec.append({"inherited_old_alpha_pixels_removed_outside_source_bbox":old_outside,"persisted_alpha_outside_source_bbox":new_outside,
  "P1_plate_qa":"SCOPED_TRANSPARENT_ALPHA_ZERO","P3_composite_qa":"GLYPH_ONLY_ALPHA_NO_STALE_OFF_BBOX",
  "id":reg["id"],"source_english":reg["english"],"translated_text":reg["ko"],
  "new_text_has_semantic_suffix_for_source_hierarchy":True,
  "glyph_rendering":"native_per_syllable_stroked_outline","stroke_px":stroke_px,"native_tracking_px":tracking_px,
  "geometry_attempts":trial_geom,"plate_library_status":plate_library_status,
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
(OUT/"B362_Q212_R43_SOURCE_OUTLINE_UNAPPROVED.dds").write_bytes(dds)
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
    fn=f"B362_{r['id']}_SOURCE_CLEAN_OFFICIAL_TRIAL_{orient}_{bg_name}_{pct}.png"
    sheet.save(OUT/fn,optimize=True);evidence.append(fn)
 l,t,x,b=r["atlas_roi"]
 Image.fromarray(C[t:b,l:x],"RGBA").save(OUT/f"B362_{r['id']}_PLATE_ONLY.png")
 Image.fromarray(D[t:b,l:x],"RGBA").save(OUT/f"B362_{r['id']}_LETTERING_ONLY.png")
qa={"schema_version":2,"role":"B","run":"B362","queue_index":212,
 "run_key":"OUTRUN-KOR-B362-Q212-R43-OPEN-COUNTERS-SECOND-20261011-0340",
 "priority":"P1_IGR029_SHARED_MODE_ATLAS","triage":tri["next_action"],
 "method":"B362 second/final source-bounded individual-syllable native glyph layout: preserve orange SOURCE core and spacing, decrease B361 stroke 2px to 1px while increasing native glyph point size within 45px source bound to reopen Korean counters. Exact source-zero-alpha CLEAN used, r44 and other 10 atlas cells protected. Previously B361 visual counter-collapse rejected; no arbitrary bitmap scaling. Independent C2/C3/USER game untested.",
 "canonical_source_sha256":SOURCE_SHA,"full_C158_clean_reference_sha256":C158_CLEAN_SHA,
 "source_clean_stage":"P1_REUSE_B358_EXACT_SOURCE-TRANSPARENT_SCOPED_R43_PERSISTED_BASE",
 "current_official_sha256":OFFICIAL_SHA,"new_unapproved_trial_sha256":sha(dds),
 "B361_rejected_trial_sha256":"c787825e932ef2fe2f7623accc8466967bada76b4a8965b30f6964a2aab01b3d",
 "B361_root_cause":"HEAVY_2PX_STROKE_CAUSED_KOREAN_COUNTER_COLLAPSE_AT_PRACTICAL_50PCT",
 "fix_stage":"P2_NATIVELY_REOPEN_GLYPH_COUNTERS_WITH_1PX_OUTLINE",
 "new_saved_trial_DDS":1,"official_promoted_DDS":0,
 "native_size":[2048,2048],"dds_format":"RGBA32","mips":1,"raw_orientation":"MIRROR_Y",
 "font_file":str(fontpath),"font_sha256":font_sha,"font_index":fontindex,
 "regions":rec,"changed_rgba_pixels":int(change.sum()),
 "outside_two_rois_rgba_change":int(np.count_nonzero(change&~mask)),
 "protected_other_11_current_cells_byte_exact":True,
 "plate_library_status":plate_library_status,
 "decoded_persisted_mismatch":int(np.count_nonzero(np.any(D!=result,axis=2))),
 "evidence_previews":evidence,"producer_visual":"HOLD_CONTROLLER_ACTUAL_SOURCE_FAMILY_AND_50PCT_REVIEW",
 "independent_C2":"NOT_RUN","C3":"BLOCKED",
 "IGR029":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED"}
(OUT/"B362_MACHINE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"source":{"uri":url,"sha256":SOURCE_SHA,"revision":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"},"full_clean_reference":C158_CLEAN_SHA,"old_official":OFFICIAL_SHA,"font":{"path":str(fontpath),"sha256":font_sha,"index":fontindex},"regions":rec,"protected":"other 11 current atlas cells exact","method":"second/final native per-glyph positioned outlines+1px stroke after B361 2px counter visual FAIL, source-proven zero-alpha r43; no lowres resampling/whole-word scaling","C2_and_runtime_required":True},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B362","sha256":sha(dds),"regions":rec,"changed":int(change.sum()),"outside":0},ensure_ascii=False),flush=True)
