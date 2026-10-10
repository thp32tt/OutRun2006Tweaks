#!/usr/bin/env python3
"""B347 q212: source-core 45px native vector rebuild of two mis-sized labels.

Material new DDS trial from canonical HD source+C158 exact transparent CLEAN.
Other 10 atlas regions stay bit-identical to the B341 already independent-reviewed
trial; no official promotion, C2/C3 or runtime approval.
"""
import os,io,json,hashlib,struct,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics");OUT=G/"role_B/20261010-B347-Q212-SOURCE-CORE45-NATIVE-REBUILD";OUT.mkdir(parents=True,exist_ok=True)
hs=lambda v:hashlib.sha256(v).hexdigest()
SH={"source":"f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61",
"official":"e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea",
"B341":"fa0acb5629318d772eb6e7cb989e5d6840c63b3e699f51073ac201f1210b43e7",
"clean":"c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67"}
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"]=="MATERIAL_REWORK",tri
report=json.loads((G/"role_C/20261010-C349-C2-Q212-B341-INDEPENDENT-SOURCE-ANCHOR/C349_Q212_C2_TRIAL_HOLD.json").read_text())
assert report["unapproved_trial"]["sha256"]==SH["B341"] and report["official"]["sha256"]==SH["official"]
assert report["machine"]["alpha32_source_core_height"]==45 and report["machine"]["alpha32_trial_height_r43"]==55 and report["machine"]["alpha32_trial_height_r44"]==52
base=G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
tp=G/"role_B/20261010-B341-Q212-PLACEMENT-REWORK/B341_UNAPPROVED_Q212_TWO_ANCHOR_TRIAL.dds"
cleanp=G/"role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png"
sourcelocal=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
old=base.read_bytes();b341=tp.read_bytes();cp=cleanp.read_bytes()
assert hs(old)==SH["official"] and hs(b341)==SH["B341"] and hs(cp)==SH["clean"]
if sourcelocal.is_file():source=sourcelocal.read_bytes()
else:
 import urllib.request
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
 with urllib.request.urlopen(url,timeout=90) as u:source=u.read()
assert hs(source)==SH["source"]
assert len(source)==len(old)==len(b341)==16777344 and source[:128]==b341[:128]==old[:128]
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(source);O=dec(old);B=dec(b341);C=np.array(Image.open(io.BytesIO(cp)).convert("RGBA"))
assert S.shape==B.shape==C.shape==(2048,2048,4)
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert fontp.is_file()
fontbytes=fontp.read_bytes()
index=1;faces=TTCollection(str(fontp));cmap=faces.fonts[index].getBestCmap()
rs=[{"id":43,"english":"PROFESSIONAL","korean":"프로페셔널","roi":[0,341,638,404],"source_bbox":[240,341,637,386],"source_core_height":45,"old_trial_core_height":55},
{"id":44,"english":"OUTRUN","korean":"아웃런","roi":[1626,524,1837,587],"source_bbox":[1626,524,1837,569],"source_core_height":45,"old_trial_core_height":52}]
trial=B.copy();alpha_proof=[]
for reg in rs:
 x0,y0,x1,y1=reg["roi"];sx0,sy0,sx1,sy1=reg["source_bbox"]
 k=reg["korean"]
 assert all(ord(ch) in cmap for ch in k)
 assert np.all(C[y0:y1,x0:x1,3]==0),("C158 CLEAN not transparent ROI",reg["id"])
 # Explicit SOURCE-conditioned draw: pinned original opaque RGB median rather
 # than text-only same-size resizing of B341. Protect anti-aliased Korean counters.
 sr=S[y0:y1,x0:x1];core=sr[sr[:,:,3]>=180,:3]
 assert len(core)>2000
 color=tuple(map(int,np.median(core,axis=0).astype(np.uint8)))
 # Source font family is upright flat condensed face; no slant by arbitrary shear.
 # Text first rendered at native target high-opacity core height 45px.
 best=None
 for ppem in range(34,64):
  f=ImageFont.truetype(str(fontp),size=ppem,index=index)
  bbox=ImageDraw.Draw(Image.new("L",(1,1))).textbbox((0,0),k,font=f,stroke_width=0)
  w,h=bbox[2]-bbox[0],bbox[3]-bbox[1]
  if w<=(sx1-sx0)-8 and h<=45 and (best is None or h>best[2] or (h==best[2] and w>best[1])):best=(ppem,w,h,bbox)
 assert best is not None
 ppem,w,h,bbox=best
 canvas=Image.new("L",(x1-x0,y1-y0),0)
 # Anchor to same original core x +2, vertically centered to core source line
 # and entirely inside the exact original source-effect cell.
 px=sx0+2-x0
 py=sy0+max(0,(45-h)//2)-y0
 assert px>=2 and py>=0 and px+w<x1-x0-2 and py+h<y1-y0
 ImageDraw.Draw(canvas).text((px-bbox[0],py-bbox[1]),k,font=ImageFont.truetype(str(fontp),ppem,index=index),fill=255)
 A=np.array(canvas)
 # Pixel-level content bounded exactly inside the canonical source effect ROI,
 # preserving other 10 semantic siblings bit-for-bit.
 assert np.count_nonzero(A)>500
 ink=np.zeros((y1-y0,x1-x0,4),dtype=np.uint8)
 ink[:,:,:3]=color;ink[:,:,3]=A;ink[A==0]=0
 trial[y0:y1,x0:x1]=C[y0:y1,x0:x1] # P1 clean first
 trial[y0:y1,x0:x1]=ink # P2 transparent glyphs, no background rectangles
 yy,xx=np.nonzero(A>32)
 db=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max()+1),y0+int(yy.max()+1)]
 assert db[0]>=sx0 and db[2]<=sx1 and db[1]>=sy0 and db[3]<=sy1
 assert db[3]-db[1]<=45
 reg.update({"font_size":ppem,"source_opaque_RGB":list(color),"new_high_alpha_bbox":db,"new_high_alpha_height":db[3]-db[1],
 "new_left_anchor_dx":db[0]-sx0,"count_alpha_visible":int(np.count_nonzero(A>0)),
 "P1_clean_alpha_nonzero":0})
 Image.fromarray(ink,"RGBA").save(OUT/f"B347_R{reg['id']}_TRANSPARENT_LETTERING_NATIVE.png")
 alpha_proof.append((reg["id"],A))
diff=np.any(trial!=B,axis=2)
scope=np.zeros(diff.shape,bool)
for reg in rs:
 x0,y0,x1,y1=reg["roi"];scope[y0:y1,x0:x1]=True
assert int((diff&~scope).sum())==0
assert int(diff.sum())>1000
masks=struct.unpack_from("<IIII",b341,92)
assert masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),masks
order=[0,1,2,3] if masks[0]==255 else [2,1,0,3]
out=b341[:128]+np.flipud(trial)[:,:,order].copy().tobytes()
assert hs(out)!=SH["B341"] and len(out)==len(b341) and np.array_equal(dec(out),trial)
filename="B347_Q212_TWO_CORE45_SOURCE_REBUILD_UNAPPROVED.dds"
(OUT/filename).write_bytes(out)
views=[]
def comp(z,bg):
 frame=Image.new("RGBA",(z.shape[1],z.shape[0]),bg+(255,))
 frame.alpha_composite(Image.fromarray(z,"RGBA"))
 return frame.convert("RGB")
for reg in rs:
 x0,y0,x1,y1=reg["roi"]
 for orient in ("FLIPY","RAW"):
  for bgname,bg in (("GRAY",(128,128,128)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
   for pct in (100,75,50):
    panels=[comp(a[y0:y1,x0:x1],bg) for a in (S,C,O,B,trial)]
    if orient=="RAW":panels=[p.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for p in panels]
    if pct<100:panels=[p.resize((round(p.width*pct/100),round(p.height*pct/100)),Image.Resampling.LANCZOS) for p in panels]
    w,h=panels[0].size;combined=Image.new("RGB",(w*5+24,h),bg)
    for i,p in enumerate(panels):combined.paste(p,(i*(w+6),0))
    fn=f"B347_R{reg['id']}_{orient}_{bgname}_{pct}_SOURCE_CLEAN_OLD_B341_NEW.png"
    combined.save(OUT/fn,optimize=True);views.append(fn)
Image.fromarray((diff*255).astype(np.uint8),"L").save(OUT/"B347_B341_TO_NEW_NATIVE_CHANGED_MASK.png")
qa={"role":"B","run":"B347","queue_index":212,
"run_key":"OUTRUN-KOR-B347-Q212-C349-SOURCE-CORE45-REBUILD-20261010",
"reason":"C349 scoped C2 HOLD high-alpha Korean r43=55,r44=52 vs English native core45; reconstruct new native vectors, preserve B341 source-matched horizontal anchors",
"source_sha256":SH["source"],"clean_sha256":SH["clean"],"official_sha256":SH["official"],"B341_sha256":SH["B341"],
"new_trial_sha256":hs(out),"new_trial_bytes":len(out),"font_sha256":hs(fontbytes),
"font_family":"NotoSansCJK-Bold.ttc Korean index1, native raster, zero stroke, source sampled RGBA",
"dimensions":[2048,2048],"DDS":"RGBA32 1mip","raw_orientation":"Y-mirror; FLIP-Y readable",
"changed_pixels_vs_B341":int(diff.sum()),"outside_two_regions_changed_RGBA":0,
"clean_source_12_region_baseline":"C349 independently verified unchanged; this trial only alters r43+r44",
"P1":"SHA_VERIFIED_C158_SOURCE_CLEAN_NATIVE_TWO_CELLS",
"P2":"NATIVE_SOURCE_45PX_CORE_FONT_PILOT_UNAPPROVED",
"P3":"PERSISTED_DDS_DECODE_VERIFIED_UNAPPROVED",
"regions":rs,"view_files":views,"producer_direct_visual":"PENDING_CONTROLLER",
"new_trial_DDS":1,"new_promoted_DDS":0,"C2":"C338_OFFICIAL_REWORK_B341_C349_HOLD","C3":"BLOCKED",
"APPROVAL":False,"IGR029":"OPEN","RUNTIME_VALIDATION":"UNTESTED",
"excluded":["A_ODD","C1","VR","FFB","DX11","DXVK"]}
(OUT/"B347_Q212_MACHINE_AND_SCOPE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"B347_Q212_RECIPE.json").write_text(json.dumps({"source_sha256":SH["source"],"clean_sha256":SH["clean"],"B341_sha256":SH["B341"],"font_sha256":hs(fontbytes),"font_face":index,"method":"native source-conditioned 45px high-alpha core glyph vector, original matched x, P1 clean before P2 native","regions":rs,"note":"source family only producer pilot, C hold retained"},ensure_ascii=False,indent=2)+"\n")
print("B347",hs(out),[(r["id"],r["new_high_alpha_bbox"],r["new_high_alpha_height"]) for r in rs],flush=True)
