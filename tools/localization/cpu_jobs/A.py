#!/usr/bin/env python3
"""A232 q217: SOURCE-SAMPLED depth-layer native Korean lettering trial.
C1 rejected previous A231 trial's pale flat Korean; source-protected rim and
plate were restored pixel-exact. Do NOT replicate rejected NanumSquareRound
flat font method: draw a NEW NotoCJK-native mask, then source-sample top lip,
face, inset and bottom extrusion, bounded by exact original text cells.
Shared plate C1 HOLD: exploratory trial only; do not falsely promote/PASS.
"""
import hashlib,io,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import binary_dilation,binary_erosion,distance_transform_edt
root=Path.cwd()
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
run="20261011-A232-Q217-SOURCE-SAMPLED-NATIVE-GOLD-DEPTH"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(x,p):(out/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
t=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","217"],text=True,capture_output=True)
assert t.returncode==0 and '"index": 217' in t.stdout
dump({"exit":t.returncode,"stdout":t.stdout[-6000:]},"A232_TRIAGE.json")
manifest_path=root/"localization/graphics/plate_library/entries/d924332dbb5cb52b72dc0fa31b3d0277135a5d6fcbc35e306ac1bcdde69e1d1c.json"
m=json.loads(manifest_path.read_text())
assert m["queue_index"]==217 and m["source_sha256"]=="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
c1_review_path=root/"localization/graphics/plate_library/reviews/d924332dbb5cb52b72dc0fa31b3d0277135a5d6fcbc35e306ac1bcdde69e1d1c.json"
r=json.loads(c1_review_path.read_text())
assert r["status"]=="HOLD" and r["reviewer"]=="C1", "Do not reuse as approved CLEAN"
oldQ=json.loads((root/"localization/graphics/role_C/20261011-C1-Q217-A231-INDEPENDENT/C1_Q217_A231_INDEPENDENT_QA.json").read_text())
assert oldQ["fresh_C1_trial_decision"]=="REWORK_REQUIRED_INHERITED_SOURCE_STYLE_WIDTH"
source_path=root/"localization/graphics/role_A/20261008-A189-Q217-SOURCE-GOLD-ITALIC/A189_SOURCE_READABLE.png"
clean_path=root/m["clean"]["path"]
source_bytes=source_path.read_bytes();clean_bytes=clean_path.read_bytes()
assert sha(clean_bytes)==m["clean"]["sha256"]
src=np.array(Image.open(io.BytesIO(source_bytes)).convert("RGBA"))
cln=np.array(Image.open(io.BytesIO(clean_bytes)).convert("RGBA"))
assert src.shape==cln.shape==(2048,2048,4)
old_path=root/"localization/graphics/role_A/20261011-A231-Q217-SOURCE-RED-RIM-RESTORE/A231_Q217_RED_RIM_RESTORED_UNPROMOTED.dds"
old_bytes=old_path.read_bytes()
assert sha(old_bytes)=="8043bd79fe6b5b235c5e7c119e64c8f11e65f34c77b9d69071bfd2ca37b11f1b"
assert old_bytes[:4]==b"DDS " and len(old_bytes)==128+2048*2048*4
old_arr=np.array(Image.open(io.BytesIO(old_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
assert old_arr.shape==cln.shape
# Use the checked previous A189 source rectangles, not expanded badge hulls.
rects=[
 {"id":"start","english":"START","korean":"출발","bbox":(803,509,884,532),"font_px":20},
 {"id":"goal","english":"GOAL","korean":"골","bbox":(1343,771,1420,795),"font_px":21},
]
font_path=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert font_path.is_file()
font_sha=sha(font_path.read_bytes())
allowed=np.zeros((2048,2048),bool)
for q in rects:
 x0,y0,x1,y1=q["bbox"];allowed[y0:y1,x0:x1]=True
assert int(np.count_nonzero(np.any(src!=cln,axis=2)&~allowed))==0, "Reused CLEAN outside original English glyphs changed"
# Re-render the two labels from scratch. Unlike previous generic color corrections,
# source-native English pixels define the different depth-material strata and
# outline, with top-down sampled face gradient.
result=cln.copy()
records=[];layers=[]
scale=4
for q in rects:
 x0,y0,x1,y1=q["bbox"];W,H=x1-x0,y1-y0
 src_rgb=src[y0:y1,x0:x1,:3]
 src_changed=np.any(src[y0:y1,x0:x1]!=cln[y0:y1,x0:x1],axis=2)
 sR=src_rgb[:,:,0].astype(int);sG=src_rgb[:,:,1].astype(int);sB=src_rgb[:,:,2].astype(int)
 # Source cream/gold face; excludes saturated crimson badge background.
 english_face=(sR>200)&(sG>115)&(sB>65)&(sG>sB*1.04)&src_changed
 assert int(english_face.sum())>120,(q["id"],int(english_face.sum()))
 face_sample=src_rgb[english_face].astype(np.float64)
 y_sample=np.indices((H,W))[0][english_face]
 def robust_color(sel,default):
  vals=face_sample[sel]
  if len(vals)<10:vals=face_sample
  return np.clip(np.percentile(vals,55,axis=0),0,255).astype(np.uint8)
 bright=robust_color(y_sample<=max(2,int(H*.31)),[255,241,202])
 middle=robust_color((y_sample>H*.30)&(y_sample<H*.71),[252,210,143])
 low=robust_color(y_sample>=int(H*.68),[247,135,82])
 # Force depth from SOURCE palettes, not arbitrary generic P1 flat coloring.
 # Top cream lip, warm beveled face, copper/red lower extrusion.
 font=ImageFont.truetype(str(font_path),q["font_px"]*scale)
 try:
  assert all(font.getmask(k).getbbox() is not None for k in q["korean"])
 except Exception as ex: raise AssertionError("Missing Korean font glyph") from ex
 canvas=Image.new("L",(W*scale,H*scale),0);d=ImageDraw.Draw(canvas)
 bb=d.textbbox((0,0),q["korean"],font=font,anchor="lt",stroke_width=0)
 txw,tyh=bb[2]-bb[0],bb[3]-bb[1]
 # Adaptive horizontal size/center: actual font glyph 2 char vs 5 Latin is
 # allowed shorter, but must occupy plausible native title height.
 x=max(0,(W*scale-txw)//2-bb[0])
 y=max(0,(H*scale-tyh)//2-bb[1])
 d.text((x,y),q["korean"],font=font,fill=255,anchor="lt")
 # Source is genuinely right-italic. Native 0.26 derives prior A189 sampled
 # source right-lean 0.28; top glyph leaning right in readable coordinates.
 shear=.28
 canvas=canvas.transform(canvas.size,Image.Transform.AFFINE,
    (1,-shear,-0.28*H*scale,0,1,0),resample=Image.Resampling.BICUBIC)
 alpha=np.array(canvas.resize((W,H),Image.Resampling.LANCZOS))
 binary=alpha>=55
 yy,xx=np.nonzero(binary)
 assert len(xx)>100,(q["id"],len(xx))
 glyphbox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
 # If text touches source 1px ceiling, use native canonical rescale once, not
 # enlarging any low-resolution previous Hangul pixels.
 margin=[glyphbox[0],W-glyphbox[2],glyphbox[1],H-glyphbox[3]]
 assert all(m>=1 for m in margin),(q["id"],margin)
 # Source-family material is built by topology of newly native-rendered Hangul,
 # not a flat tinted Korean glyph: orange/red 1px offset extrusion, cream face
 # with near-edge warm bevel, near-white upper highlight, darker bottom inset.
 core=binary
 extrusion=np.zeros_like(core)
 extrusion[1:,1:] |= core[:-1,:-1]
 extrusion[2:,1:] |= core[:-2,:-1]
 outline=binary_dilation(core,iterations=1)&~core
 inside_edge=core&~binary_erosion(core,iterations=1)
 # Build masks constrained to exact source text bbox + 1px inward margin.
 guard=np.zeros_like(core);guard[1:H-1,1:W-1]=True
 active=(core|extrusion|outline)&guard
 patch=cln[y0:y1,x0:x1].copy()
 R=patch[:,:,:3].astype(np.float64)
 alphaN=np.clip(alpha.astype(np.float64)/255,0,1)
 mask_ex=(extrusion&~core&guard).astype(float)*.92
 mask_out=(outline&guard).astype(float)*.72
 red_edge=np.array([max(164,int(low[0])*.80),max(35,int(low[1])*.42),max(20,int(low[2])*.47)],dtype=np.float64)
 # No change outside active; source-native red backdrop always underlying.
 for mm,col in [(mask_ex,red_edge),(mask_out,low.astype(float)*.87)]:
  R=R*(1-mm[:,:,None])+col[None,None,:]*mm[:,:,None]
 inside_y=np.arange(H)[:,None].astype(float)/(H-1)
 grad=np.empty((H,3),float)
 for k in range(H):
  t=k/max(1,H-1)
  if t<.25: c=bright
  elif t<.67: c=(1-(t-.25)/.42)*bright+((t-.25)/.42)*middle
  else: c=(1-(t-.67)/.33)*middle+((t-.67)/.33)*low
  grad[k]=c
 col=np.repeat(grad[:,None,:],W,axis=1)
 # Clear top ridge inside face with sampled source highlight; keep the
 # source-derived gradient and a lower bevel inside the glyph.
 lip=(inside_edge&core&(np.arange(H)[:,None]<int(.30*H)))
 bevel=(inside_edge&core&(np.arange(H)[:,None]>=int(.67*H)))
 col[lip]=np.clip(bright.astype(float)*1.06,0,255)
 col[bevel]=low
 R=R*(1-alphaN[:,:,None])+col*alphaN[:,:,None]
 patch[:,:,:3]=np.uint8(np.clip(np.round(R),0,255))
 # NOTE original red badge fully opaque inside the title, so alpha retained.
 patch[:,:,3]=cln[y0:y1,x0:x1,3]
 result[y0:y1,x0:x1]=patch
 records.append({"id":q["id"],"original_text":q["english"],"korean":q["korean"],
  "original_bbox":list(q["bbox"]),"source_natural_bbox_size":[W,H],
  "new_ko_bbox_readable":[x0+glyphbox[0],y0+glyphbox[1],x0+glyphbox[2],y0+glyphbox[3]],
  "new_ko_margin":margin,"font_px":q["font_px"],"font_sha256":font_sha,
  "source_english_face_sampled_pixels":int(english_face.sum()),
  "source_palette_upper":bright.tolist(),"source_palette_middle":middle.tolist(),"source_palette_bottom":low.tolist(),
  "layers":["source-color rim ORIGINAL CLEAN","source-sampled dark 1px extrusion","native outline","source-sampled copper bottom bevel","source-sampled cream face","bright source top ridge"],
  "source_italic_readable_shear":shear,"new_effect_mask_pixels":int(active.sum())})
 layers.append({"id":q["id"],"x0":x0,"y0":y0,"x1":x1,"y1":y1,"mask":active})
# Safeguard full-atlas source, alpha, and candidate snapshots.
delta_old=np.any(result!=old_arr,axis=2)
assert int((delta_old&~allowed).sum())==0,"Existing protected atlas changed"
delta_clean=np.any(result!=cln,axis=2)
assert int((delta_clean&~allowed).sum())==0,"New lettering outside source glyph boxes"
assert np.array_equal(result[:,:,3],cln[:,:,3])
assert np.array_equal(result[~allowed],src[~allowed]),"Source red rim/protected art not exact"
# Re-encode from previous DDS, patch exact 4B bytes only in original text rects;
# old file DDS packing was independently q217 verified as RGBA.
data=bytearray(old_bytes)
for q in rects:
 x0,y0,x1,y1=q["bbox"]
 for y in range(y0,y1):
  start=128+((2047-y)*2048+x0)*4
  data[start:start+(x1-x0)*4]=result[y,x0:x1].tobytes()
bytes_final=bytes(data)
assert bytes_final[:128]==old_bytes[:128] and len(bytes_final)==len(old_bytes)
out_file=out/"A232_Q217_SOURCE_SAMPLED_GOLD_DEPTH_UNPROMOTED.dds"
out_file.write_bytes(bytes_final)
decoded=np.array(Image.open(out_file).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
assert np.array_equal(decoded,result),"Saved DDS RGB mismatch"
assert sha(bytes_final)!=sha(old_bytes)
# Source exact protection check stronger than previous-only:
assert int((np.any(decoded!=src,axis=2)&~allowed).sum())==0
# Producer inspection contact sheets; never promote same method on pixel metrics
# before viewing 100/75/50. Unapproved clean cannot be called C1 PASS.
src_img=Image.fromarray(src,"RGBA");cln_img=Image.fromarray(cln,"RGBA")
prior_img=Image.fromarray(old_arr,"RGBA");new_img=Image.fromarray(decoded,"RGBA")
for q in rects:
 x0,y0,x1,y1=q["bbox"]
 R=[max(0,x0-10),max(0,y0-8),min(2048,x1+10),min(2048,y1+8)]
 tiles=[o.crop(tuple(R)) for o in (src_img,cln_img,prior_img,new_img)]
 for bgname,bg in [("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
  for pct in (100,75,50):
   panels=[]
   for im in tiles:
    filled=Image.alpha_composite(Image.new("RGBA",im.size,bg+(255,)),im).convert("RGB")
    if pct!=100:filled=filled.resize((int(filled.width*pct/100),int(filled.height*pct/100)),Image.Resampling.LANCZOS)
    panels.append(filled)
   w,h=panels[0].size;sheet=Image.new("RGB",(4*w,h+22),bg);d=ImageDraw.Draw(sheet)
   for i,(label,panel) in enumerate(zip(("SOURCE","CLEAN","A231_FAILED","A232_NEW"),panels)):
    sheet.paste(panel,(i*w,22));d.text((i*w+1,3),label,fill="black" if bgname=="WHITE" else "white")
   sheet.save(out/f"A232_{q['id']}_{bgname}_{pct}.png")
 new_img.crop(tuple(R)).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/f"A232_{q['id']}_RAW.png")
 # Source-conditioned silhouette and effects preview (transparent L mask).
 layer=next(a for a in layers if a["id"]==q["id"])
 crop=np.any(decoded[y0:y1,x0:x1,:3]!=cln[y0:y1,x0:x1,:3],axis=2).astype(np.uint8)*255
 Image.fromarray(crop,"L").save(out/f"A232_{q['id']}_EFFECT_MASK_NATIVE.png")
report={
 "run":"A232","run_key":"OUTRUN-KOR-A232-Q217-SOURCE-SAMPLED-GOLD-DEPTH-NEW-FAMILY-20261011-0505",
 "role":"A","index":217,"method_change":"replace rejected A189/A231 NanumSquareRound flat gold letter pass by independently Noto CJK native glyph mask + source-sampled face-top/highlight/midface/warm depth/outline/extrusion; existing source-conditioned CLEAN and verified rim unchanged",
 "source_sha256":m["source_sha256"],"source_png_sha256":sha(source_bytes),
 "plate_manifest_sha256":"d924332dbb5cb52b72dc0fa31b3d0277135a5d6fcbc35e306ac1bcdde69e1d1c",
 "clean_sha256":sha(clean_bytes),"plate_C1_status":r["status"],
 "prior_A231_trial_sha256":sha(old_bytes),"new_trial_sha256":sha(bytes_final),
 "new_trial_path":str(out_file.relative_to(root)),
 "font_path":str(font_path),"font_sha256":font_sha,"glyph_coverage":"ALL_VERIFIED",
 "regions":records,"old_to_new_changed_rgba":int(delta_old.sum()),
 "source_to_new_outside_original_bboxes":0,"old_to_new_outside_original_bboxes":0,
 "clean_to_new_outside_original_bboxes":0,"source_red_rim_protected_exact":True,
 "all_alpha_unchanged":True,"header_and_mip_preserved":True,"native":[2048,2048],
 "persisted_decode_equal_exact":True,"independent_C1":"NOT_RUN_NEW_BYTES",
 "producer_self_visual":"PENDING_CONTROLLER_DIRECT_VIEW_NO_PASS",
 "official_updated":False,"new_unpromoted_dds":1,"C3":"NOT_RUN",
 "RUNTIME_VALIDATION":"UNTESTED","VR_FFB_DX11_DXVK":False,
 "next_action":"Producer inspect source-native original face vs new saved Korean on BGW 100/75/50/RAW; if still small/wrong family, fail closed and use extracted PSD/native vector hand glyph instead of more Noto recolors"}
dump(report,"A232_MACHINE_QA.json")
print(json.dumps({"run":"A232","new_sha":sha(bytes_final),"changed":int(delta_old.sum()),
 "source_red_protected":True,"trial_only":True},ensure_ascii=False))
