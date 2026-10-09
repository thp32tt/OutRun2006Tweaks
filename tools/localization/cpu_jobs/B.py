#!/usr/bin/env python3
"""B305 user IGR-037 q201 GOALS underfill: full native Korean '목표' localized DDS.

Only the source-exact original UI segment GOALS is affected. Preserve all 14
phonetic stage names, Special/STAGES, all artwork and protected song pixels.
No quarter-size Hangul upscale, no opaque composite crop. C and game pending.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds"
DIR=G/"role_B/20261009-B305-Q201-IGR037-GOALS-NATIVE"
DIR.mkdir(parents=True,exist_ok=True)
SHA=lambda b:hashlib.sha256(b).hexdigest()
SOURCE="6ac5ffd02c9162499f09f0b476176b56f0b144789f546ef34147d94e0a8451e5"
OLD="a7a4ea10fead816cd5bc8fe4011f31b9b2c308f61ab2bdbf0de233bc557a03c8"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","201","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="201")
assert "rework_required" in row["artwork_status"]
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 backlog=list(csv.DictReader(f))
assert any(z["id"]=="IGR-037" and z["owner_lane"]=="B" and z["status"]=="OPEN_USER_INGAME_FAIL" for z in backlog)
old=(G/"hd_candidates"/REL).read_bytes()
assert SHA(old)==OLD,"q201 changed by concurrent producer; refuse stale rerender"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds"
with urllib.request.urlopen(url,timeout=150) as response:srcbytes=response.read()
assert SHA(srcbytes)==SOURCE
assert srcbytes[:128]==old[:128]
def dec(buf):
 arr=np.array(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert arr.shape==(2048,2048,4)
 return arr
S=dec(srcbytes);P=dec(old)
BASE=G/"role_B/20261006-B-INGAME168-IGR004-GOAL-SELECT-WEIGHT"
manifest=json.loads((BASE/"B168_A9ABD877_REPORT.json").read_text())
assert manifest["source_provenance"]["source_sha256"]==SOURCE
assert manifest["candidate_sha256"]==OLD
rows=manifest["rows"];assert len(rows)==17
r=next(z for z in rows if z["source"]=="GOALS")
assert r["region_idx"]==16 and r["korean"]=="골" and r["kind"]=="ui"
l,t,rr,b=r["original_bbox"];assert (l,t,rr,b)==(1079,1734,1255,1785)
C=np.asarray(Image.open(BASE/"B168_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
union=np.zeros((2048,2048),bool)
for z in rows:
 x,y,x2,y2=z["original_bbox"];union[y:y2,x:x2]=True
assert not np.any(np.any(S!=C,axis=2)&~union),"canonical SOURCE-vs-CLEAN outside text/source target!"
assert not np.any(C[t:b,l:rr,3]),"English GOALS/ghost remains on CLEAN"
# Confirm current '골' remains wholly in canonical GOALS bbox and the
# plate used for the new glyph is the authorized legacy clean region.
current_tile=P[t:b,l:rr]
visible=np.where(current_tile[:,:,3]>16)
assert len(visible[0])>0
previous_bbox=[l+int(np.min(visible[1])),t+int(np.min(visible[0])),
               l+int(np.max(visible[1]))+1,t+int(np.max(visible[0]))+1]
assert min(previous_bbox[0]-l,rr-previous_bbox[2],previous_bbox[1]-t,b-previous_bbox[3])>=2
# GOALS = semantic UI/control label, not a proper stage name. '골' is an
# undersized one-syllable transliteration: replace with legible '목표'.
new_text="목표"
fontpaths=["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
           "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
if not any(Path(p).exists() for p in fontpaths):
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
font=next(Path(x) for x in fontpaths if Path(x).exists())
# Keep source family dark condensed weight with native 1px same-color
# perimeter; do not stretch, shear or pixel-upscale the actual glyph.
color=tuple(r["fill_rgba"])
assert color== (46,54,57,255)
chosen=None
for size in range(54,36,-1):
 f=ImageFont.truetype(str(font),size,index=1)
 bb=f.getbbox(new_text,stroke_width=1)
 im=Image.new("RGBA",(bb[2]-bb[0]+8,bb[3]-bb[1]+8),(0,0,0,0))
 ImageDraw.Draw(im).text((4-bb[0],4-bb[1]),new_text,font=f,fill=color,stroke_width=1,stroke_fill=color)
 ib=im.getchannel("A").getbbox()
 if not ib:continue
 im=im.crop(ib)
 if im.width<rr-l-9 and im.height<b-t-9 and im.height>=38:
  chosen=(im,size);break
assert chosen is not None, "native text won't safely fit original bbox"
im,size=chosen
x=l+5;y=t+(b-t-im.height)//2
assert x>l and x+im.width<rr and y>t and y+im.height<b
out=P.copy()
# Restore ONLY this previously-localized text cell to verified CLEAN.
out[t:b,l:rr]=C[t:b,l:rr]
out[y:y+im.height,x:x+im.width]=np.asarray(im,dtype=np.uint8)
changed=np.any(P!=out,axis=2)
alpha_changed=P[:,:,3]!=out[:,:,3]
allowed=np.zeros((2048,2048),bool);allowed[t:b,l:rr]=True
assert not np.any(changed&~allowed)
assert not np.any(alpha_changed&~allowed)
assert not np.any((S!=C).any(axis=2)&~union)
# No visible source residue even outside localized new text.
assert not np.any(C[t:b,l:rr,3])
# Preserve existing 14 canonical stage names, English music & Ferrari
# name pixels as decoded and physical bytes outside GOALS region.
assert np.array_equal(out[~allowed],P[~allowed])
# Source header/channel order fixed from exact source and proven original.
raw=np.frombuffer(srcbytes[128:],dtype=np.uint8).reshape(2048,2048,4)
if np.array_equal(raw[::-1],S):
 mode="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(raw[::-1,:,[2,1,0,3]],S)
 mode="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
trial=old[:128]+body
assert SHA(trial)!=OLD and len(trial)==len(old)
D=dec(trial)
assert np.array_equal(D,out),"persisted DDS decode mismatch"
# Independent authored plate vs decoded saved DDS proof.
assert np.array_equal(D[t:b,l:rr],out[t:b,l:rr])
assert not np.any(np.any(D!=P,axis=2)&~allowed)
assert not np.any((D[:,:,3]!=P[:,:,3])&~allowed)
newmask=out[t:b,l:rr,3]>16
zy,zx=np.where(newmask)
bbox=[l+int(zx.min()),t+int(zy.min()),l+int(zx.max())+1,t+int(zy.max())+1]
margins=[bbox[0]-l,rr-bbox[2],bbox[1]-t,b-bbox[3]]
assert min(margins)>=3
assert bbox[2]-bbox[0] <= rr-l and bbox[3]-bbox[1] <= b-t
candidate=G/"hd_candidates"/REL
candidate.write_bytes(trial)
assert SHA(candidate.read_bytes())==SHA(trial)
# Native lossless previews for SOURCE vs CLEAN, CLEAN vs FINAL,
# SOURCE vs FINAL: BGW 100/75/50 and readable/RAW.
def composite(v,bg):
 base=Image.new("RGBA",(v.shape[1],v.shape[0]),bg+(255,))
 base.alpha_composite(Image.fromarray(v.astype(np.uint8),"RGBA"))
 return base.convert("RGB")
views=[]
for orientation in ("FLIP_Y_READABLE","RAW"):
 tiles=[a[t:b,l:rr].copy() for a in (S,C,P,D)]
 if orientation=="RAW":tiles=[np.flipud(a).copy() for a in tiles]
 for bg in [(128,128,128),(255,255,255),(0,0,0)]:
  for scale in (100,75,50):
   pics=[composite(tile,bg) for tile in tiles]
   if scale!=100:pics=[im.resize((round(im.width*scale/100),round(im.height*scale/100)),Image.Resampling.LANCZOS) for im in pics]
   canvas=Image.new("RGB",(sum(im.width for im in pics)+12,max(im.height for im in pics)),bg)
   xx=0
   for pic in pics:canvas.paste(pic,(xx,0));xx+=pic.width+4
   name=f"B305_GOALS_{orientation}_{bg[0]}_{scale}_SOURCE_CLEAN_OLD_NEW.png"
   canvas.save(DIR/name,optimize=True)
   views.append(name)
for name,arr in [("SOURCE",S),("CLEAN",C),("PREVIOUS",P),("NEW_DECODED",D)]:
 Image.fromarray(arr[t:b,l:rr],"RGBA").save(DIR/(f"B305_GOALS_{name}_RGBA.png"),optimize=True)
Image.fromarray(np.uint8(changed[t:b,l:rr])*255,"L").save(DIR/"B305_GOALS_CHANGED_MASK.png")
qa={"role":"B","run":"B305","queue_index":201,"ingame_report":"IGR-037",
 "source_sha256":SOURCE,"previous_candidate_sha256":OLD,"candidate_sha256":SHA(trial),
 "asset":REL,"source":"GOALS","old_korean":"골","new_korean":"목표",
 "source_effect_bbox":[l,t,rr,b],"old_visible_bbox":previous_bbox,
 "new_visible_bbox":bbox,"delta_margins":margins,
 "native_typeface":font.name,"font_size":size,"native_glyph_upscale":1,
 "source_qa_clean_alpha_in_region":int(np.count_nonzero(C[t:b,l:rr,3])),
 "source_vs_clean_outside_17_source_bboxes":0,
 "new_vs_previous_changed_pixels_outside_selected":0,
 "new_vs_previous_alpha_changed_outside_selected":0,
 "other_16_rows_and_preserved_artwork":"PIXEL_EXACT_UNCHANGED",
 "pixel_changed_inside":int(changed[t:b,l:rr].sum()),
 "native_dimensions":[2048,2048],"DDS_header_exact":True,"mips":1,
 "DDS_format":mode,"raw_orientation":"mirror_y",
 "saved_DDS_decoded_exact":"PASS",
 "proof":views,"producer_visual":"PENDING_DIRECT_100_75_50_RAW",
 "independent_C1":"PENDING","C3":"PENDING","USER_INGAME":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","execution_backend":"github-actions",
 "excluded":["VR","FFB","DX11","DXVK"]}
(DIR/"B305_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B305_NEW_DDS",json.dumps({"sha":SHA(trial),"old":OLD,"source":SOURCE,"original_bbox":[l,t,rr,b],"new_bbox":bbox,"margins":margins,"outside":0,"proofs":len(views),"method":"direct_native_font_only_GOALS"},ensure_ascii=False),flush=True)
