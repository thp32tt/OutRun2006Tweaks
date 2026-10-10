#!/usr/bin/env python3
"""B349 even q060: NEW source-CLEAN native Korean gradient/outline trial.
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
OUT=G/"role_B/20261010-B349-Q060-SOURCE-CLEAN-KOREAN-GOLD-LETTERING"
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
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fontb=fontp.read_bytes();fontsha=hs(fontb);font_index=1
cmap=TTCollection(str(fontp)).fonts[font_index].getBestCmap()
word="최고 기록:"
assert all(ord(ch) in cmap for ch in word if ch!=" ")
letter_spacing=12
# Draw at native ppem from glyph metrics; no resized/older Korean raster.
best=None
for ppem in range(92,161):
 f=ImageFont.truetype(str(fontp),ppem,index=font_index)
 d=ImageDraw.Draw(Image.new("L",(1,1)))
 bbox=d.textbbox((0,0),word,font=f)
 height=bbox[3]-bbox[1]
 adv=float(d.textlength(word,font=f))
 # 134px source effect height incl outline+drop shadow, require natural
 # 95-108 native glyph pixels and a 3px source-effect margin on all sides.
 if height<=99 and height>=82 and adv+(len(word)-1)*letter_spacing < 820:
  if best is None or height>best[2]: best=(ppem,adv,height,bbox)
assert best is not None,("NO_NATIVE_FONT_FIT",word)
ppem,advance,body_h,tbb=best
font=ImageFont.truetype(str(fontp),ppem,index=font_index)
# Put glyphs on a transparent image with native Unicode glyph coverage.
# Conservative natural tracking, no whole-word geometric width warping.
local=Image.new("L",(W,H),0)
d=ImageDraw.Draw(local)
glyph_width=advance+(len(word)-1)*letter_spacing
left=int(round((label_bbox[0]+label_bbox[2]-glyph_width)/2))-x0
top=int(round((label_bbox[1]+label_bbox[3]-body_h)/2))-y0
left=max(left,label_bbox[0]+7-x0);top=max(top,label_bbox[1]+10-y0)
pen=left
for ch in word:
 # Shared baseline: the whole-word textbbox top y is subtracted once.
 d.text((pen,top-tbb[1]),ch,font=font,fill=255)
 pen+=float(d.textlength(ch,font=font))+letter_spacing
mask=np.array(local)
gy,gx=np.nonzero(mask>16);assert len(gx)>1000
before=[int(gx.min()+x0),int(gy.min()+y0),int(gx.max()+1+x0),int(gy.max()+1+y0)]
# Source material is italic right: in readable coordinates top.x-bottom.x >0.
# Anchor a glyph contour to the observed source right-lean WITHOUT matching
# unrelated English vs Korean contour points in the mechanical report.
# Source optical slant requires subsequent independent anchor review.
incline=.22
transform=Image.Transform.AFFINE
local=local.transform((W,H),transform,(1,incline,-incline*(top+body_h+2),0,1,0),resample=Image.Resampling.BICUBIC)
# The affine inverse above intentionally sends output top to source x at
# +incline*(remaining height); any negative left edge is fail-closed below.
letter=np.array(local)
# Source-original sampled gold material not an arbitrary flat primary color.
# Sample original BEST TIME face warm pixels; clamp only to exclude navy edge.
sub=original[:,:,:3]
warm=(original[:,:,3]>=180)&(sub[:,:,0]>=155)&(sub[:,:,1]>=65)&(sub[:,:,0]>sub[:,:,2]+50)
upper=warm & (np.indices(warm.shape)[0] < (345+65-y0))
lower=warm & (np.indices(warm.shape)[0] >= (345+65-y0))
assert int(warm.sum())>10000 and int(upper.sum())>1000 and int(lower.sum())>1000
color_top=np.median(sub[upper],axis=0).astype(np.uint8).tolist()
color_bottom=np.median(sub[lower],axis=0).astype(np.uint8).tolist()
# Gold face SOURCE samples become a continuously interpolated face layer.
# Optical source effect: navy outline plus brown soft extrusion.
source_navy=[16,25,75]
source_brown=[83,32,25]
ink=Image.new("RGBA",(W,H),(0,0,0,0))
stroke=local.filter(ImageFilter.MaxFilter(11))  # 5px boundary
shadow=ImageChops.offset(stroke,5,5)
sh=Image.new("RGBA",(W,H),tuple(source_brown)+(0,));sh.putalpha(shadow)
ink=Image.alpha_composite(ink,sh)
rim=Image.new("RGBA",(W,H),tuple(source_navy)+(0,));rim.putalpha(stroke)
ink=Image.alpha_composite(ink,rim)
ly,lx=np.indices((H,W))
frac=np.clip((ly-(label_bbox[1]-y0+14))/max(1,(label_bbox[3]-label_bbox[1]-26)),0,1)
rgb=np.stack([color_top[k]*(1-frac)+color_bottom[k]*frac for k in range(3)],axis=2)
gradient=np.zeros((H,W,4),dtype=np.uint8);gradient[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8);gradient[:,:,3]=letter
ink=Image.alpha_composite(ink,Image.fromarray(gradient,"RGBA"))
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
fn="B349_Q060_SOURCE_FIRST_GOLD_KOREAN_UNAPPROVED.dds"
(OUT/fn).write_bytes(newdds)
Image.fromarray(plate,"RGBA").save(OUT/"B349_BEST_TIME_PLATE_ONLY_ROI.png")
ink.save(OUT/"B349_BEST_TIME_TRANSPARENT_LETTERING_ROI.png")
Image.fromarray(new,"RGBA").save(OUT/"B349_Q060_DECODED_FINAL_FULL_READABLE.png")
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
  file=f"B349_SOURCE_CLEAN_OFFICIAL_NEW_{bgkey}_{size}_FLIPY.png"
  sheet.save(OUT/file,optimize=True);ev.append(file)
for view in ["RAW"]:
 panels=[render(a,(80,80,80)).transpose(Image.Transpose.FLIP_TOP_BOTTOM) for a in [S,C,O,new]]
 w,h=panels[0].size
 sheet=Image.new("RGB",(4*w+36,h),(80,80,80))
 for k,panel in enumerate(panels):sheet.paste(panel,(k*(w+12),0))
 fn2="B349_SOURCE_CLEAN_OFFICIAL_NEW_RAW_GRAY_100.png";sheet.save(OUT/fn2,optimize=True);ev.append(fn2)
Image.fromarray((diff.astype(np.uint8)*255),"L").save(OUT/"B349_PREVIOUS_TO_TRIAL_NATIVE_CHANGED_MASK.png")
# Readable top-minus-bottom optical evidence is a distinct manual inspection,
# not a computed homologous-source slant PASS.
report={"schema_version":2,"role":"B","run":"B349","queue_index":60,
"run_key":"OUTRUN-KOR-B349-Q060-P0-SOURCE-FIRST-NATIVE-LETTERING-20261010-1430",
"method":"B348 authenticated original English two-component alpha CLEAN, new native direct glyphs with pinned font, sampled SOURCE warm face, transparent-only gradient/navy rim/brown extrusion",
"triage":tri["next_action"],"priority":"P0","source_sha256":SH["source"],"prior_official_sha256":SH["official"],
"authored_clean_sha256":SH["clean"],"authored_mask_sha256":SH["mask"],"trial_persisted_sha256":hs(newdds),
"trial_DDS":fn,"bytes":len(newdds),"source_bbox":list(label_bbox),"new_effect_bbox":render_bbox,
"native_glyph_bbox_pre_italic":before,"text":word,"font_file":fontp.name,"font_sha256":fontsha,"font_license":"OFL Noto CJK; verify distribution before packaging",
"glyph_coverage":"ALL_CODEPOINTS_PRESENT","font_native_ppem":ppem,"letter_spacing":letter_spacing,"natural_advance_px":advance,
"source_gold_sample_rgb_upper":color_top,"source_gold_sample_rgb_lower":color_bottom,
"source_italic_readable_right_anchor_shear_ESTIMATE_NOT_C_QUALIFIED":incline,
"gradient":"SOURCE_NATIVE_WARM_FACE_ROW_MEDIAN_INTERPOLATED","stroke_px":5,"extrusion_offset":[5,5],
"roi":list(roi),"changed_rgba_pixels":int(diff.sum()),"changed_rgba_outside_roi":0,"original_protected_sibling_rgba_changed_outside_effect":0,
"persisted_dds_roundtrip_mismatch":int(np.any(D!=new,axis=2).sum()),"raw_channel_masks":list(rgba_masks),
"source_clean_source_pixels_removed":89391,"preview_files":ev,"new_trial_dds":1,"new_promoted_dds":0,
"P1":"REUSED_B348_SCOPED_SOURCE_CLEAN_VISUAL_PASS","P2":"NEW_TRANSPARENT_GLYPHS_NEED_CONTROLLER_OPTICAL_REVIEW",
"P3":"PERSISTED_TRIAL_MECHANICAL_ROUNDTRIP_PASS_VISUAL_PENDING",
"final_production_pixel_guard":"NOT_APPLICABLE_TO_UNPROMOTED_TRIAL","official_C2":"C342_REWORK_REQUIRED_UNCHANGED","C3":"BLOCKED",
"IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"forbidden":["A_ODD","C1","VR","FFB","DX11","DXVK"]}
(OUT/"B349_Q060_MACHINE_AND_SOURCE_FAMILY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"canonical_source":{"sha256":SH["source"],"revision":"OR2-HD-GUI-v0.25.10a"},
"source_clean":{"path":str(pp/"B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png"),"sha256":SH["clean"]},
"font":{"path":str(fontp),"sha256":fontsha,"index":font_index,"native_ppem":ppem,"glyphs":word},
"plate_mask_sha256":SH["mask"],"face_gradient":[color_top,color_bottom],
"effect":{"outline":5,"shadow_offset":[5,5],"readable_right_italic_shear":incline},
"protected_siblings":["OUTRUN MILES","HOLLY WOLF","all other source atlas regions"],
"construction":"new transparent lettering without copying dirty B343 Korean composite",
"need_C2_source_slant_homologous_anchors":True,
"no_final_candidate_published":True},ensure_ascii=False,indent=2)+"\n")
print("B349",hs(newdds),"font_px",ppem,"bbox",render_bbox,"newchg",int(diff.sum()),flush=True)
