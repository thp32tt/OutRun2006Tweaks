#!/usr/bin/env python3
"""A230 retry source-cached q121 P0: source-exact Gas Pedal leftover removal bounded by Korean
lettering protection. Source remainder is a confirmed text-only original
label region from A229, NOT the unresolved A221 neighbor sources. Trial only.
"""
import hashlib,io,json,os,urllib.request,subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd(); run="20261010-A230-Q121-GAS-PEDAL-ORIGINAL-GHOST-CLEAN"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
qproc=subprocess.run(["python","tools/localization/rework_triage.py","--index","121","--require-safe-rerender"],capture_output=True,text=True)
(out/"A230_TRIAGE.json").write_text(json.dumps({"exit":qproc.returncode,"stdout":qproc.stdout[-6000:],"stderr":qproc.stderr[-1600:]},ensure_ascii=False,indent=2)+"\n")
assert qproc.returncode==0,"q121 triage prevents routine rerender"
q=json.loads(qproc.stdout)["assets"][0];assert q["index"]==121
a229=json.loads((root/"localization/graphics/role_A/20261010-A229-Q121-P0-ALL30-SOURCE-REMAINDER-INVENTORY/A229_ALL30_SOURCE_EXACT_REPORT.json").read_text())
r20=next(x for x in a229["rows"] if x["rank"]==20)
assert r20["source_bbox"]==[3490,391,3722,440]
assert r20["a220_exact_source_rgba_alpha_positive"]==266
assert r20["official_to_trial_changed_rgba_pixels"]==0
old_path=root/"localization/graphics/role_A/20261010-A220-Q121-THE-SOURCE-RESIDUE/A220_Q121_THE_RESIDUE_PLUS_GOAL33_UNPROMOTED.dds"
current_bytes=old_path.read_bytes()
assert sha(current_bytes)==a229["a220_trial_sha256"]
official_path=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
official_bytes=official_path.read_bytes()
assert sha(official_bytes)==a229["official_sha256"]
# The 67-MB public source DDS timed out in initial A230 runner attempt.
# Reuse the A215 lossless native source-region PNG (Git-tracked) previously
# produced from the exact English SHA and cross-checked in successful A229.
a215=json.loads((root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS/A215_COMPONENT_QA.json").read_text())
rank20=next(i for i in a215["regions"] if i["rank"]==20)
assert a215["source_sha256"]==a229["source_sha256"]
assert rank20["bbox_readable"]==r20["source_bbox"]
ex0,ey0,ex1,ey1=rank20["expanded_crop_readable"]
source_png=root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS/A215_component_20_SOURCE_NATIVE_RGBA.png"
source_tile=Image.open(source_png).convert("RGBA")
assert source_tile.size==(ex1-ex0,ey1-ey0)
assert len(current_bytes)==len(official_bytes)==128+4096*4096*4 and current_bytes[:4]==official_bytes[:4]==b"DDS "
def decode(x):return Image.open(io.BytesIO(x)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
current=decode(current_bytes); official=decode(official_bytes)
assert current.size==official.size==(4096,4096)
x0,y0,x1,y1=r20["source_bbox"];rect=(x0,y0,x1,y1)
source_crop=source_tile.crop((x0-ex0,y0-ey0,x1-ex0,y1-ey0))
S=np.array(source_crop,dtype=np.uint8)
C=np.array(current.crop(rect),dtype=np.uint8)
exact=(S[:,:,3]>0)&(C[:,:,3]>0)&np.all(S==C,axis=2)
assert int(exact.sum())==266
# Korean/nonoriginal letter foreground is protected; never touch equal-looking
# outline pixels immediately attached to its alpha-positive native glyphs.
korean=(C[:,:,3]>=64)&~exact
protect=binary_dilation(korean,iterations=2)
removable=exact&~protect
# Bound conservatively to original visible pixels and do not remove any source
# text that is ambiguously joined to the newly lettered Hangul.
pixels=int(removable.sum())
assert pixels>0, "No provably isolated original remaining: preserve official"
# A text-only label has no non-text source art inside its pinned source bbox,
# validated by source English Gas Pedal visual and A229 native triptych.
# 'per-pixel previous official' must not be rendered over entire rectangle.
new=bytearray(current_bytes)
ys,xs=np.nonzero(removable)
for ly,lx in zip(ys,xs):
 X=x0+int(lx);Y=y0+int(ly);row=4095-Y
 off=128+(row*4096+X)*4
 new[off:off+4]=b"\x00\x00\x00\x00"
new=bytes(new)
assert sha(new)!=sha(current_bytes)
ddspath=out/"A230_Q121_GAS_PEDAL_SOURCE_GHOST_SCOPED_UNPROMOTED.dds"
ddspath.write_bytes(new)
saved=decode(new)
N=np.array(saved.crop(rect),dtype=np.uint8)
change=np.any(C!=N,axis=2)
assert int(change.sum())==pixels
assert np.count_nonzero(N[:,:,3][removable])==0
assert np.array_equal(C[~removable],N[~removable])
# Byte proof is stronger than an atlas bounding-box claim:
assert new[:128]==current_bytes[:128] and len(new)==len(current_bytes)
assert sum(a!=b for a,b in zip(new,current_bytes))==int((C[removable]!=N[removable]).sum())
orig_exact=(S[:,:,3]>0)&(N[:,:,3]>0)&np.all(S==N,axis=2)
remaining=int(orig_exact.sum())
assert remaining==266-pixels
# Every alpha-positive neighbor not explicitly cleared remains exact.
beforeA=np.frombuffer(current_bytes[128:],dtype=np.uint8).reshape(4096,4096,4)
afterA=np.frombuffer(new[128:],dtype=np.uint8).reshape(4096,4096,4)
raw_changed=np.any(beforeA!=afterA,axis=2)
expected=np.zeros((4096,4096),dtype=bool)
for ly,lx in zip(ys,xs):expected[4095-(y0+int(ly)),x0+int(lx)]=True
assert np.array_equal(raw_changed,expected),"No unrelated-pixel changes allowed"
# New source/CLEAN/final persisted view only for source text, with protected
# and isolated original remnants separated. Both RAW/readable shown.
def comp(im,bg):
 return Image.alpha_composite(Image.new("RGBA",im.size,bg+(255,)),im).convert("RGB")
imgs=[source_crop,official.crop(rect),current.crop(rect),saved.crop(rect)]
for bgname,bg in [("BLACK",(0,0,0)),("GRAY",(100,100,100)),("WHITE",(255,255,255))]:
 for pct in (100,75,50):
  cells=[comp(im,bg) for im in imgs]
  if pct!=100:cells=[im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS) for im in cells]
  w,h=cells[0].size
  sheet=Image.new("RGB",(w*4,h+22),bg)
  d=ImageDraw.Draw(sheet)
  for i,(name,im) in enumerate(zip(("SOURCE","OFFICIAL","A220","A230_CLEAN"),cells)):
   sheet.paste(im,(i*w,22))
   d.text((i*w+2,3),name,fill=(0,0,0) if bgname=="WHITE" else (255,255,255))
  sheet.save(out/f"A230_GAS_PEDAL_{bgname}_{pct}.png")
Image.fromarray(removable.astype(np.uint8)*255,mode="L").save(out/"A230_SOURCE_IDENTICAL_REMOVAL_MASK_NATIVE.png")
Image.fromarray((protect.astype(np.uint8)*255),mode="L").save(out/"A230_PROTECTED_KOREAN_2PX_MASK_NATIVE.png")
# raw preview in actual DDS Y, not a hypothetical render
rawrect=(x0,4096-y1,x1,4096-y0)
saved.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(rawrect).save(out/"A230_FINAL_PERSISTED_RAW_GAS_PEDAL.png")
report={"run":"A230","run_key":"OUTRUN-KOR-A230-Q121-P0-GAS-PEDAL-ISOLATED-SOURCE-REMAINDER-20261010-2220","role":"A","index":121,
 "P0_ingame_backlog":["IGR-030","IGR-031","IGR-040"],
 "semantic_binding":"Gas Pedal -> 가속 페달: source text only; 30-region A229 inventory rank20",
 "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "source_sha256":a229["source_sha256"],"source_region_png_sha256":sha(source_png.read_bytes()),"canonical_source_full_dds_reused_from_prior_verified_A229":True,"official_sha256":sha(official_bytes),
 "A220_sha256":sha(current_bytes),"new_trial_sha256":sha(new),
 "trial_path":str(ddspath.relative_to(root)),"source_bbox_readable":list(rect),
 "source_exact_remaining_before":266,"source_exact_isolated_removal_pixels":pixels,"source_exact_remaining_after":remaining,
 "remove_rule":"alpha_positive source==trial RGBA EXACT && NOT within 2px dilation of non-original Korean glyph",
 "unchanged_existing_Korean_foreground":True,"untouched_pixels_raw_exact":True,
 "alpha_after_removed_pixels_zero":True,"header_raw_mirror_y_preserved":True,
 "source_to_final_protected_neighbor_intersection":0,
 "persisted_DDS_redecoded":True,
 "production_stage":"P1_SOURCE_CLEAN_ISOLATED_ORIGINAL_REMNANT_PILOT",
 "visual_qa":"PENDING_CONTROLLER_INDEPENDENT_OPTICAL_EVIDENCE",
 "C1":"PENDING","C3":"NOT_RUN","promoted_DDS":0,"trial_DDS":1,
 "other_29_atlas_text_regions":"NOT_CHANGED",
 "user_accepted":False,"RUNTIME_VALIDATION":"UNTESTED",
 "next_action":"Direct native/source/CLEAN/FINAL visual inspection; retain HOLD full atlas, C1 exact-byte independent approval if and only if plate proves clean",
 "exclusions":["VR","FFB","DX11","DXVK"]}
(out/"A230_MACHINE_SCOPED_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"rank20":pixels,"remaining_exact":remaining,"new_trial":sha(new),"promoted":0}))
