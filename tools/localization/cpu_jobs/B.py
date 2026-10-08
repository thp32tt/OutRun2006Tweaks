#!/usr/bin/env python3
"""B299 q212: source-conditioned native typography correction for two C318 FAIL cells.
PROOF-FIRST: publish an exact DDS trial, not a candidate, pending pixels-first controller review.
"""
import csv,hashlib,io,json,os,subprocess,tempfile,urllib.request,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="B"
R=Path.cwd()
G=R/"localization/graphics"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
OUT=G/"role_B/20261009-B299-Q212-NATIVE-SOURCE-FAMILY-TRIAL"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
ORIGINAL="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
CURRENT="01c7aded0bbaa393351d1b191dc08cfbd24fa542160f6a60d5584abd1bc0f1e6"
curr_bytes=(G/"hd_candidates"/ASSET).read_bytes()
assert sha(curr_bytes)==CURRENT,("candidate drift",sha(curr_bytes))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
with urllib.request.urlopen(url,timeout=140) as rsp:
 source_bytes=rsp.read()
assert sha(source_bytes)==ORIGINAL and source_bytes[:128]==curr_bytes[:128]
def decode(b):
 im=Image.open(io.BytesIO(b)).convert("RGBA")
 assert im.size==(2048,2048)
 return np.array(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
source=decode(source_bytes);current=decode(curr_bytes)
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as fh:
 row=next(x for x in csv.DictReader(fh) if x["index"].lstrip("\ufeff")=="212")
assert row["artwork_status"]=="c318_c2_rework_required_small_family_underfill_igr029_mapping_open"
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as fh:
 ig=next(x for x in csv.DictReader(fh) if x["id"]=="IGR-029")
assert ig["status"]=="OPEN_USER_INGAME_FAIL" and "SUSPECTED" in ig["mapping_status"]
qa=json.loads((G/"role_C/20261008-C264-C2-Q212-Q062-Q172/C264_BATCH_MACHINE_QA.json").read_text())
regions=next(a["rows"] for a in qa["assets"] if a["queue_index"]==212)
assert len(regions)==12
boxes={r["key"]:tuple(r["source_bbox"]) for r in regions}
target=[("showroom","차량 전시장","red"),("enter_name","이름 입력","gray")]
for name,_,_ in target:assert name in boxes
# Native font: never upscale the previous localized raster.
fonts=["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
       "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
       "/usr/share/fonts/opentype/noto/noto/NotoSansCJK-Bold.ttc"]
font=next((f for f in fonts if Path(f).exists()),None)
if not font:
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 font=next((f for f in fonts if Path(f).exists()),None)
assert font,("native Korean font unavailable",fonts)
clean=source.copy();out=current.copy()
allowed=np.zeros(source.shape[:2],dtype=bool)
for name,_,_ in target:
 l,t,r,b=boxes[name];allowed[t:b,l:r]=True
 # Reference has isolated alpha-only text on transparent sprite plate;
 # never paint an opaque crop or cover English under Hangul.
 clean[t:b,l:r]=0
 out[t:b,l:r]=0
# Source derives color: opaque source glyph RGB most common visual face,
# not arbitrary overlay shadow/glow or a flat Photoshop rectangle.
def family_rgb(box):
 l,t,r,b=box;reg=source[t:b,l:r];alpha=reg[:,:,3]
 opaque=reg[alpha>=245,:3]
 assert len(opaque)>300
 q=np.median(opaque.astype(np.float32),axis=0)
 return tuple(int(round(v)) for v in q)
def render_native(text,max_height,target_width,rgb):
 # Render direct at native source height. Korean semantic length, not
 # forced English width; source style height, family weight and color control.
 font_size=int(max_height*1.31)
 last=None
 for _ in range(40):
  f=ImageFont.truetype(font,font_size,index=1)
  box=f.getbbox(text)
  tmp=Image.new("RGBA",(box[2]-box[0]+10,box[3]-box[1]+10))
  ImageDraw.Draw(tmp).text((5-box[0],5-box[1]),text,font=f,fill=(*rgb,255))
  crop=tmp.getchannel("A").getbbox()
  im=tmp.crop(crop)
  last=im
  if im.height<=max_height and im.width<=target_width:return im,font_size
  font_size-=2
 assert False,("native font fit failed",text,last.size)
rows=[]
for name,text,family in target:
 l,t,r,b=boxes[name]
 color=family_rgb((l,t,r,b))
 margin=4
 glyph,fs=render_native(text,b-t-2*margin,r-l-2*margin,color)
 # Retain original left/top anchors, with balanced vertical alignment.
 x=l+margin
 y=t+(b-t-glyph.height)//2
 assert x>l and x+glyph.width<r and y>t and y+glyph.height<b
 # Transparent-only glyph mask; absence of background-rectangle edits.
 layer=np.asarray(glyph,dtype=np.uint8)
 dest=out[y:y+glyph.height,x:x+glyph.width]
 assert not np.any(dest[:,:,3])
 mask=layer[:,:,3].astype(np.float32)/255.0
 dest[:,:,:3]=layer[:,:,:3]
 dest[:,:,3]=layer[:,:,3]
 assert np.count_nonzero(dest[:,:,3])>100
 rr={"id":name,"source_text":next(q["source"] for q in regions if q["key"]==name),
     "korean_text":text,"source_bbox":[l,t,r,b],
     "candidate_bbox":[x,y,x+glyph.width,y+glyph.height],
     "margins":[x-l,r-x-glyph.width,y-t,b-y-glyph.height],
     "source_median_face_rgb":color,"font_file":Path(font).name,"font_size":fs,
     "glyph_alpha_pixels":int(np.count_nonzero(mask))}
 rows.append(rr)
raw=curr_bytes[:128]+np.flipud(out).copy().tobytes()
assert raw!=curr_bytes and raw[:128]==curr_bytes[:128] and len(raw)==len(curr_bytes)
persist=decode(raw)
assert np.array_equal(persist,out),"persisted DDS bytes decode mismatch"
chg=np.any(out!=current,axis=2)
assert int(np.count_nonzero(chg&~allowed))==0
assert int(np.count_nonzero((out[:,:,3]!=current[:,:,3])&~allowed))==0
# C264's other 10 localized regions and protected art remain byte-exact.
for q in regions:
 if q["key"] in [x[0] for x in target]:continue
 l,t,r,b=q["source_bbox"]
 assert np.array_equal(current[t:b,l:r],out[t:b,l:r]),("protected region",q["key"])
# Independent plate-only: all introduced source letters and effects gone,
# background outside source-glyph cells is identical.
assert np.count_nonzero(clean[:,:,3]&allowed)==0
assert not np.any(np.any(clean!=source,axis=2)&~allowed)
def comp(im,bg=(130,130,130,255)):
 p=Image.new("RGBA",(im.shape[1],im.shape[0]),bg)
 p.alpha_composite(Image.fromarray(im,"RGBA"))
 return p.convert("RGB")
files=[]
for name,_,_ in target:
 l,t,r,b=boxes[name]
 for kind,img in [("SOURCE",source),("CLEAN",clean),("OLD",current),("TRIAL",persist)]:
  for bgname,bg in [("GRAY",(130,130,130,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
   f=OUT/f"{name}_{kind}_{bgname}_NATIVE.png"
   comp(img[t:b,l:r],bg).save(f)
   files.append(str(f))
 for pct in (100,75,50):
  imgs=[comp(a[t:b,l:r]) for a in (source,clean,current,persist)]
  if pct!=100:
   imgs=[v.resize((max(1,v.width*pct//100),max(1,v.height*pct//100)),Image.Resampling.LANCZOS) for v in imgs]
  sheet=Image.new("RGB",(sum(v.width for v in imgs)+12,max(v.height for v in imgs)),(130,130,130))
  x=0
  for v in imgs:sheet.paste(v,(x,0));x+=v.width+4
  f=OUT/f"{name}_SOURCE_CLEAN_OLD_TRIAL_{pct}pct.png";sheet.save(f);files.append(str(f))
 rawimgs=[comp(np.flipud(img[t:b,l:r])) for img in (source,clean,current,persist)]
 sheet=Image.new("RGB",(sum(v.width for v in rawimgs)+12,max(v.height for v in rawimgs)),(130,130,130))
 x=0
 for v in rawimgs:sheet.paste(v,(x,0));x+=v.width+4
 f=OUT/f"{name}_RAW_FLIPY_4WAY.png";sheet.save(f);files.append(str(f))
trail=OUT/"Q212_B299_TRIAL_NOT_PROMOTED.dds";trail.write_bytes(raw)
report={"run":"B299","role":"B","task":"q212 C318 confirmed showroom/enter_name hierarchy underfill",
 "queue_index":212,"triage":"MATERIAL_REWORK","source_sha256":sha(source_bytes),
 "current_sha256":sha(curr_bytes),"trial_sha256":sha(raw),
 "new_trial_dds":1,"new_promoted_dds":0,"selection_mapping_IGR029":"SUSPECTED_UNRESOLVED",
 "outside_two_changed_pixels":0,"protected_other_ten_regions":"PIXEL_EXACT",
 "source_clean_alpha":0,"persisted_dds_roundtrip":"EXACT","header_raw_mip1":"PRESERVED",
 "font":"native Noto CJK KR bold/black","method":"native source-size source-color glyph composition; showroom semantic Korean expansion, no English-width stretch",
 "regions":rows,"preview_png_count":len(files),
 "plate_only":"PENDING_CONTROLLER_VISUAL","composite_only":"PENDING_CONTROLLER_VISUAL",
 "producer_visual":"PENDING_CONTROLLER_VISUAL","C2":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,
 "USER_INGAME":"OPEN","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GITHUB_ACTIONS_FONT_DEPENDENCY_UNAVAILABLE_GPT_DNS","excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B299_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B299_TRIAL_OK",json.dumps({"sha":sha(raw),"records":rows,"proof":len(files)},ensure_ascii=False),flush=True)
