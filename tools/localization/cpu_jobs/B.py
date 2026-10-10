#!/usr/bin/env python3
"""B353 even q060: second/final bold-condensed family pilot after B352 visual thin-stroke rejection.
Unapproved scoped producer trial; P1 B348 is reused verbatim. Does not alter
hd_candidates nor queue; the controller must review persisted pixels first.
"""
import os,io,json,hashlib,struct,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B353-Q060-ENGLISH-PERROW-MATERIAL-PILOT"
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
# B353 source-conditioned thin-outline reconstruction: render individual
# CJK vector outlines at source-native ppem and lay out syllabic components
# separately, not a whole-word stretched raster or a flat filled font crop.
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fontb=fontp.read_bytes();fontsha=hs(fontb);font_index=1
cmap=TTCollection(str(fontp)).fonts[font_index].getBestCmap()
word="최고 기록:"
assert all(ord(ch) in cmap for ch in word if ch!=" ")
ppem=122
font=ImageFont.truetype(str(fontp),ppem,index=font_index)
# Each native glyph is an independent letterform with its own width, baseline
# and exactly one native contour resampling. Optical widths are chosen from the
# English source's racing title role, not a whole-word width post-transform.
target_hangul_w=116
tracking=34
letter_spacing=tracking
space_advance=37
local=Image.new("L",(W,H),0)
d=ImageDraw.Draw(local)
all_bb=[d.textbbox((0,0),ch,font=font) for ch in word if ch!=" "]
body_h=max(bb[3]-bb[1] for bb in all_bb)
assert 100<=body_h<=130,(body_h,ppem)
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
assert 620<=glyph_width<=830,("SOURCE_FAMILY_OPTICAL_WIDTH_GATE",glyph_width)
left=int(round((label_bbox[0]+label_bbox[2]-glyph_width)/2))-x0-18 # native contour overhang: shift 18px left to keep 1px+ right source margin
top=int(round((label_bbox[1]+label_bbox[3]-body_h)/2))-y0
top+=1
pen=left
for ch,im,w0 in native_glyphs:
 if im is not None: local.paste(im,(pen,top),im)
 pen+=w0+tracking
mask=np.array(local)
gy,gx=np.nonzero(mask>16);assert len(gx)>1000
before=[int(gx.min()+x0),int(gy.min()+y0),int(gx.max()+1+x0),int(gy.max()+1+y0)]
# B353: ONE readable right-lean affine placement after native per-glyph shaping.
# B353 applied two stacked transforms (0.39 + 0.22), an unmeasured optical
# distortion. Single 0.32 source-oriented matrix only; final anchors remain
# C2-review-required, not mechanically certified source-homologous strokes.
incline=.40
local=local.transform((W,H),Image.Transform.AFFINE,(1,incline,-incline*(top+body_h+2),0,1,0),resample=Image.Resampling.BICUBIC)
letter=np.array(local)
# B353 source-conditioned pixel sampling rather than fabricated color stops.
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
# Exact-source dark edging extracted from actual alpha-opaque navy, not B353 brown.
navy_mask=(original[:,:,3]>=185)&(rgb_src[:,:,2]>=rgb_src[:,:,0]+14)&(rgb_src[:,:,0]<115)&(rgb_src[:,:,1]<115)
assert int(navy_mask.sum())>250,("MISSING_ENGLISH_NAVY",int(navy_mask.sum()))
navy=np.median(rgb_src[navy_mask],axis=0).astype(np.uint8).tolist()
navy=[min(65,navy[0]),min(80,navy[1]),max(52,navy[2])]
# Use SOURCE face ink height, not arbitrary fixed red/yellow gradients.
source_lo=int(source_rows.min());source_hi=int(source_rows.max())
face=np.array(local,dtype=np.uint8)
inside=face>=110
fy,fx=np.nonzero(face>110)
assert len(fx)>1000
k_lo,k_hi=int(fy.min()),int(fy.max())
assert k_hi-k_lo>=70
# Native glyph y -> original source warm-face row y for EVERY Hangul pixel.
ly,lx=np.indices((H,W));frac=np.clip((ly-k_lo)/max(1,k_hi-k_lo),0,1)
q=np.clip((source_lo+frac*(source_hi-source_lo)).astype(np.int32),0,H-1)
colored=(0.68*row_profile[q]+0.32*row_high[q]).copy()
# Raised top-facing contour receives actual source face upper quantiles, not
# uniform white bars. Preserve Hangul counter-space by tight native masks.
dist=distance_transform_edt(inside)
bevel_high=(dist>1.5)&(dist<5.5)&(frac>.45)&(frac<.9)
colored[bevel_high]=.55*colored[bevel_high]+.45*row_high[q][bevel_high]
# 1-2px inner lip sampled from source's warmer low-quantile tone.
inner_lip=(dist>0)&(dist<2.5)
colored[inner_lip]=.82*colored[inner_lip]+.18*np.array([254,118,17],dtype=np.float64)
ink=Image.new("RGBA",(W,H),(0,0,0,0))
# Source navy modeled with separate long lower extrusion and compact dark rim.
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
source_profile={"source_face_warm_pixels":int(source_warm.sum()),"source_face_qualified_rows":len(source_rows),"source_face_row_range":[source_lo+y0,source_hi+y0],"source_navy_pixels":int(navy_mask.sum()),"source_navy_median_rgb":navy,"source_color_samples":[{"y":int(y0+j),"count":int(row_counts[j]),"rgb_median":raw_row_medians[j].round().astype(int).tolist(),"rgb_high_80":raw_row_high[j].round().astype(int).tolist()} for j in source_rows[::max(1,len(source_rows)//14)]],"korean_face_row_range":[k_lo+y0,k_hi+y0],"construction":"real source warm-face row-median/80th material bound to native glyph face depth, single readable affine; not B353 manual hot-orange stops and double transform"}
(OUT/"B353_SOURCE_ENGLISH_PIXEL_MATERIAL_PROFILE.json").write_text(json.dumps(source_profile,indent=2,ensure_ascii=False)+"\n")
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
fn="B353_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds"
(OUT/fn).write_bytes(newdds)
Image.fromarray(plate,"RGBA").save(OUT/"B353_BEST_TIME_PLATE_ONLY_ROI.png")
ink.save(OUT/"B353_BEST_TIME_TRANSPARENT_LETTERING_ROI.png")
Image.fromarray(new,"RGBA").save(OUT/"B353_Q060_DECODED_FINAL_FULL_READABLE.png")
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
  file=f"B353_SOURCE_CLEAN_OFFICIAL_NEW_{bgkey}_{size}_FLIPY.png"
  sheet.save(OUT/file,optimize=True);ev.append(file)
for view in ["RAW"]:
 panels=[render(a,(80,80,80)).transpose(Image.Transpose.FLIP_TOP_BOTTOM) for a in [S,C,O,new]]
 w,h=panels[0].size
 sheet=Image.new("RGB",(4*w+36,h),(80,80,80))
 for k,panel in enumerate(panels):sheet.paste(panel,(k*(w+12),0))
 fn2="B353_SOURCE_CLEAN_OFFICIAL_NEW_RAW_GRAY_100.png";sheet.save(OUT/fn2,optimize=True);ev.append(fn2)
Image.fromarray((diff.astype(np.uint8)*255),"L").save(OUT/"B353_PREVIOUS_TO_TRIAL_NATIVE_CHANGED_MASK.png")
# Readable top-minus-bottom optical evidence is a distinct manual inspection,
# not a computed homologous-source slant PASS.
report={"schema_version":2,"role":"B","run":"B353","queue_index":60,
"run_key":"OUTRUN-KOR-B353-Q060-P0-CONTOUR-OPTICAL-PILOT-20261010-1635",
"method":"B353 second and last native source-derived font-family pilot. Correct B352 optical underweight and height with Bold 122ppem native contours while preserving slim 3px source-navy edge, high-percentile original face, bounded readable lean and B348 CLEAN. Unlike rejected B351 huge 8px rim and broad glyphs; trial is not promoted without controller source review.",
"triage":tri["next_action"],"priority":"P0","source_sha256":SH["source"],"prior_official_sha256":SH["official"],
"authored_clean_sha256":SH["clean"],"authored_mask_sha256":SH["mask"],"trial_persisted_sha256":hs(newdds),
"trial_DDS":fn,"bytes":len(newdds),"source_bbox":list(label_bbox),"new_effect_bbox":render_bbox,
"native_glyph_bbox_pre_italic":before,"text":word,"font_file":fontp.name,"font_sha256":fontsha,"font_license":"OFL Noto CJK; verify distribution before packaging",
"glyph_coverage":"ALL_CODEPOINTS_PRESENT","font_native_ppem":ppem,"letter_spacing":letter_spacing,"natural_advance_px":advance,
"source_gold_sample_rgb_upper":color_top,"source_gold_sample_rgb_lower":color_bottom,
"readable_single_affine_lean_UNQUALIFIED_SOURCE_HOMOLOGY":incline,
"gradient":"SOURCE_MEASURED_ENGLISH_FACE_ROWS_AND_QUANTILES","stroke_px":3,"extrusion_offset":[2,3],
"roi":list(roi),"changed_rgba_pixels":int(diff.sum()),"changed_rgba_outside_roi":0,"original_protected_sibling_rgba_changed_outside_effect":0,
"persisted_dds_roundtrip_mismatch":int(np.any(D!=new,axis=2).sum()),"raw_channel_masks":list(rgba_masks),
"source_clean_source_pixels_removed":89391,"preview_files":ev,"new_trial_dds":1,"new_promoted_dds":0,
"P1":"REUSED_B348_SCOPED_SOURCE_CLEAN_VISUAL_PASS","P2":"NEW_TRANSPARENT_GLYPHS_NEED_CONTROLLER_OPTICAL_REVIEW",
"P3":"PERSISTED_TRIAL_MECHANICAL_ROUNDTRIP_PASS_VISUAL_PENDING",
"final_production_pixel_guard":"NOT_APPLICABLE_TO_UNPROMOTED_TRIAL","official_C2":"C342_REWORK_REQUIRED_UNCHANGED","C3":"BLOCKED",
"IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"forbidden":["A_ODD","C1","VR","FFB","DX11","DXVK"]}
(OUT/"B353_Q060_MACHINE_AND_SOURCE_FAMILY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"canonical_source":{"sha256":SH["source"],"revision":"OR2-HD-GUI-v0.25.10a"},
"source_clean":{"path":str(pp/"B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png"),"sha256":SH["clean"]},
"font":{"path":str(fontp),"sha256":fontsha,"index":font_index,"native_ppem":ppem,"glyphs":word},
"plate_mask_sha256":SH["mask"],"source_face_row_profile":"B353_SOURCE_ENGLISH_PIXEL_MATERIAL_PROFILE.json","face_gradient":[color_top,color_bottom],
"effect":{"outline":3,"shadow_offset":[2,3],"readable_right_italic_shear":incline},
"protected_siblings":["OUTRUN MILES","HOLLY WOLF","all other source atlas regions"],
"construction":"Second/final native contour test: Bold 122ppem glyph silhouette, slender 116px individual glyph width, 3px navy contour and 2x3 extrusion, original face row gradient plus high percentile highlights, 0.40 readable lean; fixes B352 too-thin/short Regular and avoids B351 swollen 8px outline",
"need_C2_source_slant_homologous_anchors":True,
"no_final_candidate_published":True},ensure_ascii=False,indent=2)+"\n")
print("B353",hs(newdds),"font_px",ppem,"bbox",render_bbox,"newchg",int(diff.sum()),flush=True)
