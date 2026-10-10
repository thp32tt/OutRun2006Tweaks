#!/usr/bin/env python3
"""B360 q060 P0 new ORIGINAL-PALETTE-LAYER vector face rebuild.
Unlike B353 row median and B359 contour-normal diffuse approximation, construct
source-classified orange, cream, gold and navy depth as independent layers,
using measured native English face colors and per-row coverage; saved trial
is unapproved pending first-hand optical C2 and actual-game verification.
"""
import os,io,json,hashlib,struct,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B360-Q060-SOURCE-PALETTE-LAYER-VECTOR"
OUT.mkdir(parents=True,exist_ok=True)
hs=lambda b:hashlib.sha256(b).hexdigest()
SH={"source":"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc",
"official":"d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01",
"clean":"a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48",
"mask":"25a898178ea3e4fc08a16adfa35fa8612d8cdd4da274baf244ea67e29c24cca9"}
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],
                           capture_output=True,check=True,text=True).stdout)["assets"][0]
assert tri["next_action"]=="METHOD_CHANGE_REQUIRED",tri
srcp=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
if srcp.is_file():src=srcp.read_bytes()
else:
 import urllib.request
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
 with urllib.request.urlopen(url,timeout=90) as f:src=f.read()
off=(G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds").read_bytes()
pp=G/"role_B/20261010-B348-Q060-BEST-TIME-SOURCE-COMPONENT-PLATE"
cb=(pp/"B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png").read_bytes()
mb=(pp/"B348_SOURCE_BEST_TIME_PROPOSED_REMOVAL_MASK_READABLE.png").read_bytes()
for n,b in [("source",src),("official",off),("clean",cb),("mask",mb)]:assert hs(b)==SH[n],(n,hs(b))
def decode(data):
 return np.array(Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=decode(src);O=decode(off)
C=np.array(Image.open(io.BytesIO(cb)).convert("RGBA"))
M=np.array(Image.open(io.BytesIO(mb)).convert("L"))
assert S.shape==O.shape==C.shape==(2048,4096,4) and M.shape==S.shape[:2]
assert np.all(C[M>0]==0)
assert int(np.any(S!=C,axis=2).sum())==89391
assert int((np.any(S!=C,axis=2)&(M==0)).sum())==0
# The B348 source-first evidence proves the English component geometry.
# Repair an atlas-local fence including the former Korean overhang, restoring
# the canonical adjacent source sprites (rather than keeping dirty B343 pixels).
roi=(2090,337,3120,485);label_bbox=(2179,340,3028,474)
x0,y0,x1,y1=roi;W=x1-x0;H=y1-y0
# Source ROI contains exactly two English-alpha components. The Korean effect
# must be inside their combined source effect bbox with strictly positive margin.
original=S[y0:y1,x0:x1];plate=C[y0:y1,x0:x1]
# Rebuild from SOURCE/CLEAN, never composite old dirty Korean lettering.
# B360 source-conditioned thin-outline reconstruction: render individual
# CJK vector outlines at source-native ppem and lay out syllabic components
# separately, not a whole-word stretched raster or a flat filled font crop.
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fontb=fontp.read_bytes();fontsha=hs(fontb);font_index=1
cmap=TTCollection(str(fontp)).fonts[font_index].getBestCmap()
word="최고 기록:"
assert all(ord(ch) in cmap for ch in word if ch!=" ")
ppem=128
font=ImageFont.truetype(str(fontp),ppem,index=font_index)
# Each native glyph is an independent letterform with its own width, baseline
# and exactly one native contour resampling. Optical widths are chosen from the
# English source's racing title role, not a whole-word width post-transform.
target_hangul_w=132
tracking=35
letter_spacing=tracking
space_advance=37
local=Image.new("L",(W,H),0)
d=ImageDraw.Draw(local)
all_bb=[d.textbbox((0,0),ch,font=font) for ch in word if ch!=" "]
body_h=max(bb[3]-bb[1] for bb in all_bb)
assert 100<=body_h<=135,(body_h,ppem)
native_glyphs=[]
for ch in word:
 if ch==" ":
  native_glyphs.append((ch,None,space_advance));continue
 bb=d.textbbox((0,0),ch,font=font)
 im=Image.new("L",(bb[2]-bb[0]+4,body_h+4),0)
 dr=ImageDraw.Draw(im)
 dr.text((2-bb[0],2-bb[1]),ch,font=font,fill=255)
 native=im.getbbox();assert native
 im=im.crop(native)
 if ch==":":
  target_w=round(im.width*1.12)
 else:
  target_w=target_hangul_w
 # Each letterform expands horizontally as a vector-outline surrogate at
 # native size. This is not the rejected last-run whole-word spacing tweak.
 im=im.resize((target_w,im.height),Image.Resampling.LANCZOS)
 native_glyphs.append((ch,im,target_w))
glyph_width=sum(t[2] for t in native_glyphs)+tracking*(len(native_glyphs)-1)
advance=glyph_width-tracking*(len(native_glyphs)-1)
assert 700<=glyph_width<=845,("SOURCE_FAMILY_OPTICAL_WIDTH_GATE",glyph_width)
left=int(round((label_bbox[0]+label_bbox[2]-glyph_width)/2))-x0-7 # re-center 3px left to eliminate measured 1px source-right overflow
top=int(round((label_bbox[1]+label_bbox[3]-body_h)/2))-y0
top-=1  # +1px source anchor baseline reserves antialias+face expansion
pen=left
for ch,im,w0 in native_glyphs:
 if im is not None: local.paste(im,(pen,top),im)
 pen+=w0+tracking
mask=np.array(local)
gy,gx=np.nonzero(mask>16);assert len(gx)>1000
before=[int(gx.min()+x0),int(gy.min()+y0),int(gx.max()+1+x0),int(gy.max()+1+y0)]
# Original pixel-derived homologous leading-stem anchor: on the first English
# B use the 8th percentile of warm face x by native row, excluding neighboring
# letters. Fit x(y) with ordinary least squares in the central source band.
# A positive (top - bottom) slope in readable coordinates means right lean.
anchor_rgb=original[:,:,:3].astype(np.int16)
xa,ya=np.indices(original.shape[:2])[1],np.indices(original.shape[:2])[0]
eng_face=(original[:,:,3]>=180)&(anchor_rgb[:,:,0]>=165)&(anchor_rgb[:,:,1]>=75)&(anchor_rgb[:,:,0]>anchor_rgb[:,:,2]+45)
eng_face &= (xa+x0 >= label_bbox[0])&(xa+x0<label_bbox[0]+185)
stem=[]
for ry in range(label_bbox[1]-y0+18,label_bbox[3]-y0-18):
 xs=np.where(eng_face[ry])[0]
 if len(xs)>=5:stem.append((ry,float(np.percentile(xs,8))))
assert len(stem)>=42,("MISSING_CANONICAL_B_STEM",len(stem))
source_slope=float(np.polyfit([v[0] for v in stem],[v[1] for v in stem],1)[0])
incline=round(-source_slope,4)
assert .12<=incline<=1.15,("SOURCE_STEM_SLANT_UNQUALIFIED",incline)
(OUT/"B360_SOURCE_B_RIGHT_LEAN_STEM.json").write_text(json.dumps({"source_first_glyph":"B","source_alpha_warm_stem_rows":len(stem),"source_x_dy":source_slope,"readable_top_minus_bottom_per_y":incline,"anchors":[[round(y+y0),round(x+x0,3)] for y,x in stem[::max(1,len(stem)//12)]],"review":"P2 source-single-B calibration only; independent multi-stem QA required"},indent=2)+"\n")

local=local.transform((W,H),Image.Transform.AFFINE,(1,incline,-incline*(top+body_h+2),0,1,0),resample=Image.Resampling.BICUBIC)
letter=np.array(local)
# B360 source-conditioned pixel sampling rather than fabricated color stops.
# English SOURCE is immutable. Warm face is isolated from navy outlines,
# orange sibling art and alpha halos WITHIN the authenticated BEST TIME bbox.
from scipy.ndimage import distance_transform_edt,gaussian_filter1d
rgb_src=original[:,:,:3]
source_warm=(original[:,:,3]>=180)&(rgb_src[:,:,0]>=165)&(rgb_src[:,:,1]>=75)&(rgb_src[:,:,0].astype(np.int16)>rgb_src[:,:,2].astype(np.int16)+45)
source_warm &= (np.indices(source_warm.shape)[1]+x0 >= label_bbox[0]) & (np.indices(source_warm.shape)[1]+x0 < label_bbox[2])
row_counts=source_warm.sum(axis=1)
source_rows=np.where(row_counts>=12)[0]
assert len(source_rows)>65,("UNRESOLVED_ENGLISH_FACE_ROWS",len(source_rows),int(source_warm.sum()))
raw_row_medians=np.zeros((H,3),np.float64)
raw_row_high=np.zeros((H,3),np.float64)
for ry in source_rows:
 vals=rgb_src[ry,source_warm[ry]].astype(np.float64)
 raw_row_medians[ry]=np.median(vals,axis=0)
 raw_row_high[ry]=np.percentile(vals,80,axis=0)
row_profile=np.zeros((H,3),np.float64);row_high=np.zeros((H,3),np.float64)
for k in range(3):
 row_profile[:,k]=np.interp(np.arange(H),source_rows,raw_row_medians[source_rows,k])
 row_high[:,k]=np.interp(np.arange(H),source_rows,raw_row_high[source_rows,k])
row_profile=gaussian_filter1d(row_profile,sigma=1.5,axis=0)
row_high=gaussian_filter1d(row_high,sigma=1.5,axis=0)
# Exact-source dark edging extracted from actual alpha-opaque navy, not B360 brown.
navy_mask=(original[:,:,3]>=185)&(rgb_src[:,:,2]>=rgb_src[:,:,0]+14)&(rgb_src[:,:,0]<115)&(rgb_src[:,:,1]<115)
assert int(navy_mask.sum())>250,("MISSING_ENGLISH_NAVY",int(navy_mask.sum()))
navy=np.median(rgb_src[navy_mask],axis=0).astype(np.uint8).tolist()
navy=[min(65,navy[0]),min(80,navy[1]),max(52,navy[2])]
# Use SOURCE face ink height, not arbitrary fixed red/yellow gradients.
source_lo=int(source_rows.min());source_hi=int(source_rows.max())
# Material method change: a 1px native-resolution FACE stroke replaces the
# B359 thin crest; other source-conditioned shadow layers are separate.
face=np.array(local.filter(ImageFilter.MaxFilter(3)),dtype=np.uint8)
inside=face>=110
fy,fx=np.nonzero(face>110)
assert len(fx)>1000
k_lo,k_hi=int(fy.min()),int(fy.max())
assert k_hi-k_lo>=70
# Native glyph y -> original source warm-face row y for EVERY Hangul pixel.
ly,lx=np.indices((H,W));frac=np.clip((ly-k_lo)/max(1,k_hi-k_lo),0,1)
q=np.clip((source_lo+frac*(source_hi-source_lo)).astype(np.int32),0,H-1)
# P2 manual material replacement: isolate exact canonical English SOURCE
# face material classes before Korean lettering. No generic flat gradient or
# B359 normal-only pale highlight. Palette is sampled from the BEST TIME
# source glyph region only; source hue classes and row density are persisted.
rr=rgb_src[:,:,0].astype(np.int16)
gg=rgb_src[:,:,1].astype(np.int16)
bb=rgb_src[:,:,2].astype(np.int16)
opaque_source=original[:,:,3]>=200
srclabel=np.zeros((H,W),bool)
srclabel[label_bbox[1]-y0:label_bbox[3]-y0,label_bbox[0]-x0:label_bbox[2]-x0]=True
srcface=opaque_source & srclabel
orange_px=srcface&(rr>=176)&(rr>gg+47)&(gg>=54)&(gg<=211)&(bb<170)
cream_px=srcface&(rr>=205)&(gg>=184)&(bb>=132)&(rr-gg<=85)
gold_px=srcface&(rr>=180)&(gg>=120)&(bb<190)&(rr>=gg)
navy_px=srcface&(bb>=rr+12)&(rr<125)&(gg<127)
counts={"orange":int(orange_px.sum()),"cream":int(cream_px.sum()),
        "gold":int(gold_px.sum()),"navy":int(navy_px.sum())}
assert counts["orange"]>4500 and counts["cream"]>1200 and counts["gold"]>5000 and counts["navy"]>5000,("SOURCE_LAYER_CLASSIFICATION_FAILED",counts)
orange_rgb=np.median(rgb_src[orange_px],axis=0)
cream_rgb=np.percentile(rgb_src[cream_px],74,axis=0)
gold_rgb=np.median(rgb_src[gold_px],axis=0)
source_opaque_rows=srcface.sum(axis=1).astype(np.float64)
orrows=orange_px.sum(axis=1).astype(np.float64)/(source_opaque_rows+1)
crrows=cream_px.sum(axis=1).astype(np.float64)/(source_opaque_rows+1)
orrows=gaussian_filter1d(orrows,sigma=2.0)
crrows=gaussian_filter1d(crrows,sigma=2.0)
# Match English source's highest orange/ivory rows, instead of assuming a
# top/bottom gradient. The classes are projected onto every Korean glyph
# at native y with a short anti-aliased contour warm lip.
validrows=np.where(source_opaque_rows>=15)[0]
assert len(validrows)>65
orcut=float(np.quantile(orrows[validrows],.62))
crcut=float(np.quantile(crrows[validrows],.65))
orange_zone=inside & (orrows[q]>=orcut)
cream_zone=inside & (~orange_zone) & (crrows[q]>=crcut)
material_base=np.broadcast_to(gold_rgb,(H,W,3)).copy()
material_base[orange_zone]=orange_rgb
material_base[cream_zone]=cream_rgb
# Stronger original orange face atop native main strokes; keep orange at
# source-proven per-row bands, do not blindly paint the whole glyph orange.
dist=distance_transform_edt(inside)
gy_norm,gx_norm=np.gradient(dist.astype(np.float32))
raised_lip=inside&(dist<=3.2)&(gy_norm>.14)
material_base[raised_lip]=.74*material_base[raised_lip]+.26*cream_rgb
warm_side=inside&(dist<=2.5)&(gx_norm<-.22)
material_base[warm_side]=.60*material_base[warm_side]+.40*orange_rgb
colored=material_base
profile_layers={"canonical_source_samples":counts,
 "sampled_source_rgbs":{"orange":orange_rgb.round().astype(int).tolist(),
  "cream":cream_rgb.round().astype(int).tolist(),
  "gold":gold_rgb.round().astype(int).tolist()},
 "native_source_orange_row_threshold":orcut,
 "native_source_cream_row_threshold":crcut,
 "source_face_opaque_total":int(srcface.sum()),
 "candidate_face_orange_pixels":int(orange_zone.sum()),
 "candidate_face_cream_pixels":int(cream_zone.sum()),
 "source_face_method":"P2 FOUR SOURCE-COLOR LAYERS + native slight face expansion; independent palette/row occupancy (not B359 pixel-normal-only wash)",
 "source_rows_evidence":[{"native_y":int(ry+y0),"orange_fraction":round(float(orrows[ry]),5),
 "cream_fraction":round(float(crrows[ry]),5)} for ry in validrows[::max(1,len(validrows)//18)]]}
(OUT/"B360_SOURCE_ENGLISH_FOUR_MATERIAL_LAYERS.json").write_text(json.dumps(profile_layers,ensure_ascii=False,indent=2)+"\n")
ink=Image.new("RGBA",(W,H),(0,0,0,0))
# 3D sidewall: source-conditioned navy blue extrusion is visibly thick on
# English BEST TIME; use a true separated backplate (not flat all-red shadow).
edge=local.filter(ImageFilter.MaxFilter(7))
extrusion=ImageChops.offset(edge,2,3)
shade=Image.new("RGBA",(W,H),tuple(navy)+(0,));shade.putalpha(extrusion)
ink=Image.alpha_composite(ink,shade)
rim=Image.new("RGBA",(W,H),tuple(navy)+(0,));rim.putalpha(edge)
ink=Image.alpha_composite(ink,rim)
material=np.zeros((H,W,4),np.uint8)
material[:,:,:3]=np.clip(colored,0,255).astype(np.uint8)
material[:,:,3]=face
ink=Image.alpha_composite(ink,Image.fromarray(material,"RGBA"))
source_profile={"source_face_warm_pixels":int(source_warm.sum()),"source_face_qualified_rows":len(source_rows),"source_face_row_range":[source_lo+y0,source_hi+y0],"source_navy_pixels":int(navy_mask.sum()),"source_navy_median_rgb":navy,"source_color_samples":[{"y":int(y0+j),"count":int(row_counts[j]),"rgb_median":raw_row_medians[j].round().astype(int).tolist(),"rgb_high_80":raw_row_high[j].round().astype(int).tolist()} for j in source_rows[::max(1,len(source_rows)//14)]],"korean_face_row_range":[k_lo+y0,k_hi+y0],"construction":"B360 P2 manual separated native English face-material classes (orange/cream/gold) and source per-row mask density; native +1px vector stroke and distinct deep-navy extrusion; completely replaces B359 diffuse pixel-normal-only highlight model"}
(OUT/"B360_SOURCE_ENGLISH_PIXEL_MATERIAL_PROFILE.json").write_text(json.dumps(source_profile,indent=2,ensure_ascii=False)+"\n")
color_top=row_profile[source_lo].round().astype(int).tolist()
color_bottom=row_profile[source_hi].round().astype(int).tolist()
V=np.array(ink)
iy,ix=np.nonzero(V[:,:,3]>0);assert len(ix)>1000
render_bbox=[int(ix.min()+x0),int(iy.min()+y0),int(ix.max()+1+x0),int(iy.max()+1+y0)]
assert render_bbox[0]>label_bbox[0] and render_bbox[1]>label_bbox[1] and render_bbox[2]<label_bbox[2] and render_bbox[3]<label_bbox[3],(render_bbox,label_bbox)
# Source material and CLEAN/LETTERING remain separately persisted.
p=Image.fromarray(plate,"RGBA")
assert np.all(plate[M[y0:y1,x0:x1]>0,3]==0)
after=Image.alpha_composite(p,ink)
new=O.copy()
new[y0:y1,x0:x1]=np.asarray(after)
# The source-derived CLEAN replacement is bounded only to this q060 cell.
diff=np.any(new!=O,axis=2)
allowed=np.zeros(diff.shape,bool);allowed[y0:y1,x0:x1]=True
assert int((diff&~allowed).sum())==0
# Confirm source original neighbour alpha outside the original English mask
# remains pixel-exact where no Korean effect is drawn, even inside repair ROI.
in_effect=np.zeros((H,W),bool);in_effect[V[:,:,3]>0]=True
other_visible=(original[:,:,3]>0)&(M[y0:y1,x0:x1]==0)&(~in_effect)
assert int(np.any(np.asarray(after)[other_visible]!=original[other_visible],axis=1).sum())==0
# RAW DDS roundtrip. Preserve header/mip, channel masks and orientation.
assert len(off)==33554560 and len(src)==len(off) and off[:128]==src[:128]
rgba_masks=struct.unpack_from("<IIII",off,92)
assert rgba_masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),rgba_masks
order=[0,1,2,3] if rgba_masks[0]==255 else [2,1,0,3]
newdds=off[:128]+np.flipud(new)[:,:,order].copy().tobytes()
assert len(newdds)==len(off) and hs(newdds)!=SH["official"]
D=decode(newdds)
assert np.array_equal(D,new)
fn="B360_Q060_SOURCE_LAYERED_FACE_KOREAN_UNAPPROVED.dds"
(OUT/fn).write_bytes(newdds)
Image.fromarray(plate,"RGBA").save(OUT/"B360_BEST_TIME_PLATE_ONLY_ROI.png")
ink.save(OUT/"B360_BEST_TIME_TRANSPARENT_LETTERING_ROI.png")
Image.fromarray(new,"RGBA").save(OUT/"B360_Q060_DECODED_FINAL_FULL_READABLE.png")
# bounded proof panels; no visual PASS inferred by the worker.
ev=[]
r=[2075,212,3135,535]
def render(a,bg):
 i=Image.fromarray(a[r[1]:r[3],r[0]:r[2]],"RGBA")
 c=Image.new("RGBA",i.size,bg+(255,));c.alpha_composite(i)
 return c.convert("RGB")
for bgkey,bg in [("GRAY",(128,128,128)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
 for size in [100,75,50]:
  panels=[render(a,bg) for a in [S,C,O,new]]
  if size!=100:panels=[z.resize((round(z.width*size/100),round(z.height*size/100)),Image.Resampling.LANCZOS) for z in panels]
  w,h=panels[0].size
  sheet=Image.new("RGB",(4*w+36,h),bg)
  for k,panel in enumerate(panels):sheet.paste(panel,(k*(w+12),0))
  file=f"B360_SOURCE_CLEAN_OFFICIAL_NEW_{bgkey}_{size}_FLIPY.png"
  sheet.save(OUT/file,optimize=True);ev.append(file)
for view in ["RAW"]:
 panels=[render(a,(80,80,80)).transpose(Image.Transpose.FLIP_TOP_BOTTOM) for a in [S,C,O,new]]
 w,h=panels[0].size
 sheet=Image.new("RGB",(4*w+36,h),(80,80,80))
 for k,panel in enumerate(panels):sheet.paste(panel,(k*(w+12),0))
 fn2="B360_SOURCE_CLEAN_OFFICIAL_NEW_RAW_GRAY_100.png";sheet.save(OUT/fn2,optimize=True);ev.append(fn2)
Image.fromarray((diff.astype(np.uint8)*255),"L").save(OUT/"B360_PREVIOUS_TO_TRIAL_NATIVE_CHANGED_MASK.png")
# Readable top-minus-bottom optical evidence is a distinct manual inspection,
# not a computed homologous-source slant PASS.
report={"schema_version":2,"role":"B","run":"B360","queue_index":60,
"run_key":"OUTRUN-KOR-B360-Q060-P0-SOURCE-FOUR-LAYER-MANUAL-20261010-2230",
"method":"B360 materially changed P2: native English glyph color classification into orange/cream/gold/navy source layer profiles, native 1px contour face expansion, separate navy extrusion + measured English-B stem lean. Designed to repair C2 B359 too-pale thin racing title; old B359 normal-wash generator NOT reused. Only one unapproved pilot pending independent C2."
"triage":tri["next_action"],"priority":"P0","source_sha256":SH["source"],"prior_official_sha256":SH["official"],
"authored_clean_sha256":SH["clean"],"authored_mask_sha256":SH["mask"],"trial_persisted_sha256":hs(newdds),
"trial_DDS":fn,"bytes":len(newdds),"source_bbox":list(label_bbox),"new_effect_bbox":render_bbox,
"native_glyph_bbox_pre_italic":before,"text":word,"font_file":fontp.name,"font_sha256":fontsha,"font_license":"OFL Noto CJK; verify distribution before packaging",
"glyph_coverage":"ALL_CODEPOINTS_PRESENT","font_native_ppem":ppem,"letter_spacing":letter_spacing,"natural_advance_px":advance,
"source_gold_sample_rgb_upper":color_top,"source_gold_sample_rgb_lower":color_bottom,
"readable_single_affine_lean_SOURCE_B_STEM_ONLY_NOT_WHOLE_FAMILY":incline,"four_material_source_palette":profile_layers,"source_B_stem_fit_dx_dy":source_slope,
"gradient":"SOURCE_CLASSIFIED_ORANGE_CREAM_GOLD_SEPARATE_BANDS","stroke_px":3,"extrusion_offset":[2,3],
"roi":list(roi),"changed_rgba_pixels":int(diff.sum()),"changed_rgba_outside_roi":0,"original_protected_sibling_rgba_changed_outside_effect":0,
"persisted_dds_roundtrip_mismatch":int(np.any(D!=new,axis=2).sum()),"raw_channel_masks":list(rgba_masks),
"source_clean_source_pixels_removed":89391,"preview_files":ev,"new_trial_dds":1,"new_promoted_dds":0,
"P1":"REUSED_B348_SCOPED_SOURCE_CLEAN_VISUAL_PASS","P2":"NEW_TRANSPARENT_GLYPHS_NEED_CONTROLLER_OPTICAL_REVIEW",
"P3":"PERSISTED_TRIAL_MECHANICAL_ROUNDTRIP_PASS_VISUAL_PENDING",
"final_production_pixel_guard":"NOT_APPLICABLE_TO_UNPROMOTED_TRIAL","official_C2":"C342_REWORK_REQUIRED_UNCHANGED","C3":"BLOCKED",
"IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"forbidden":["A_ODD","C1","VR","FFB","DX11","DXVK"]}
(OUT/"B360_Q060_MACHINE_AND_SOURCE_FAMILY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"canonical_source":{"sha256":SH["source"],"revision":"OR2-HD-GUI-v0.25.10a"},
"source_clean":{"path":str(pp/"B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png"),"sha256":SH["clean"]},
"font":{"path":str(fontp),"sha256":fontsha,"index":font_index,"native_ppem":ppem,"glyphs":word},
"plate_mask_sha256":SH["mask"],"source_face_row_profile":"B360_SOURCE_ENGLISH_PIXEL_MATERIAL_PROFILE.json","face_gradient":[color_top,color_bottom],
"effect":{"outline":3,"navy_extrusion_offset":[2,3],"readable_lean_source_B_stem_measured":incline,"face_normal_lighting":"source-English face 85-percentile highlighted at top-facing glyph contour normals"},
"protected_siblings":["OUTRUN MILES","HOLLY WOLF","all other source atlas regions"],
"construction":"New B360 source English-palette manual 4-layer face: sampling orange/cream/gold/navy rgba and exact source-color per-row occupancy, 1px native surface stroke, separate navy extrusion; English B OLS right lean and B348 CLEAN retained, not repeating B359 gradient. C2 review required.",
"need_C2_source_slant_homologous_anchors":True,
"no_final_candidate_published":True},ensure_ascii=False,indent=2)+"\n")
print("B360",hs(newdds),"font_px",ppem,"bbox",render_bbox,"newchg",int(diff.sum()),flush=True)
