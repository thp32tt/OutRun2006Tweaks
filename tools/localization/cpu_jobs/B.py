#!/usr/bin/env python3
"""B316 q137 P0 IGR-041: four residual header/small source-family native glyphs, *trial first*.

Prior B287/B288 only changed strokes on the same generic narrow Korean.
This pass changes semantic phrasing and uses per-syllable native condensed
black weight to restore visual hierarchy without scaling prior bitmap DDS.
Never promote until persisted controller visual QA; game still untested.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
OUT=G/"role_B/20261009-B316-Q137-P0-FOUR-REWORK-REGIONS"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SRC="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
CLEAN="b128a8fd82f3ccae6300511c22e63bf40e2938e114b8417aada19bbd49bc9098"
OLD="1d684aaceeef4487bb6605cf8b4779950683970e6c18e1d5b175a25642409d68"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="137")
assert "four_rework_required" in row["artwork_status"] and "b315" in row["artwork_status"]
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","137","--require-safe-rerender"],text=True,capture_output=True)
assert tri.returncode==0,(tri.returncode,tri.stdout,tri.stderr)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
current=(G/"hd_candidates"/REL).read_bytes();assert sha(current)==OLD,"stale/current DDS changed"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
with urllib.request.urlopen(url,timeout=160) as f:src=f.read()
assert sha(src)==SRC and src[:128]==current[:128]
platepath=G/"role_B/20261009-B285-Q137-SOURCE-ALPHA-FAMILY/B285_PLATE_ONLY_RGBA.png"
platebytes=platepath.read_bytes();assert sha(platebytes)==CLEAN
def decode(buf):
 a=np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(1024,2048,4)
 return a
S=decode(src);P=decode(current)
C=np.asarray(Image.open(io.BytesIO(platebytes)).convert("RGBA"),dtype=np.uint8)
assert C.shape==P.shape
specs=[
 ("select_transmission","SELECT TRANSMISSION","변속 방식 선택",(5,67,868,130),60,255),
 ("transmission_small","TRANSMISSION","변속 방식",(1288,96,1569,128),29,170),
 ("manual_small","MANUAL","수동 변속",(14,148,339,210),59,170),
 ("automatic_small","AUTOMATIC","자동 변속",(822,147,1376,216),65,170),
 ("manual_large","MANUAL","수동 변속",(1,235,397,315),76,255),
 ("automatic_large","AUTOMATIC","자동 변속 모드",(889,233,1775,315),76,255)]
allow=np.zeros(P.shape[:2],bool)
for _,_,_,(l,t,r,b),_,_ in specs:allow[t:b,l:r]=True
assert np.count_nonzero(np.any(S!=C,axis=2)&~allow)==0,"authored source plate changes outside six regions"
# Canonical A22 CLEAN legitimately retains native source separator/guide
# artwork crossing the original glyph bounding boxes; do not erase it.
retained=int(np.count_nonzero((C[:,:,3]>0)&allow))
assert retained==3579,("canonical plate protected sprite/support drift",retained)
# Preserve all modal navigation, separators and panel art byte-for-byte.
assert np.count_nonzero(np.any(P!=S,axis=2)&~allow)==0
font="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(font).exists():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
assert Path(font).exists()
out=P.copy();report=[]
# Source-clean validated six; current rework is ONLY four previously C-rejected residual labels.
residual_only=np.zeros(P.shape[:2],bool)
for entry in specs[:4]:
 ll,tt,rr,bb=entry[3]
 residual_only[tt:bb,ll:rr]=True
def letter_master(word,font_px,targetw,sourceh):
 ft=ImageFont.truetype(font,font_px,index=1)
 # Build each syllable as an independent native outline. Unlike a broad word
 # squeeze, each glyph has its own narrow-vertical-stem profile and advance.
 parts=[]
 for ch in word:
  if ch==" ":
   parts.append(Image.new("L",(max(10,font_px//5),1),0));continue
  box=ft.getbbox(ch)
  im=Image.new("L",(box[2]-box[0]+12,box[3]-box[1]+12),0)
  ImageDraw.Draw(im).text((6-box[0],6-box[1]),ch,font=ft,fill=255)
  bb=im.getbbox();assert bb
  cropped=im.crop(bb)
  # independently narrow the syllable's *vector* contour, retaining vertical
  # height, with a measured source-style full-height heavy condensed profile.
  ww=max(6,round(cropped.width*0.92))
  part=cropped.resize((ww,cropped.height),Image.Resampling.LANCZOS)
  parts.append(part)
 height=max(a.height for a in parts)
 gap=max(4,round(font_px*.09))
 total=sum(a.width for a in parts)+(len(parts)-1)*gap
 # Source original height is the cap, and no suffix may collide with peers.
 assert height<=sourceh-5,(word,height,sourceh)
 result=Image.new("L",(total,height),0);pos=0
 for a in parts:
  result.paste(a,(pos,(height-a.height)//2));pos+=a.width+gap
 assert total<=targetw-10,(word,total,targetw)
 return result
for key,en,ko,(l,t,r,b),size,alpha in specs[:4]:
 # choose native source-like cap height, min 3px margins on each source bbox
 chosen=None
 for sz in range(size,size-16,-1):
  try:im=letter_master(ko,sz,r-l,b-t)
  except AssertionError:continue
  if im.height<=b-t-8 and im.width<=r-l-12:
   chosen=(sz,im);break
 assert chosen is not None,("unable to native-fit",key)
 sz,im=chosen
 bb=im.getbbox();assert bb
 # no foreign coloured plate. Composite only white/gray glyph coverage
 nx=l+(r-l-im.width)//2;ny=t+(b-t-im.height)//2
 margins=[nx-l,r-nx-im.width,ny-t,b-ny-im.height]
 assert min(margins)>=3,(key,margins)
 mask=np.asarray(im,dtype=np.uint8)
 rgba=np.zeros((im.height,im.width,4),dtype=np.uint8)
 rgba[:,:,:3]=255
 rgba[:,:,3]=np.round(mask.astype(np.float32)*(alpha/255)).astype(np.uint8)
 out[t:b,l:r]=C[t:b,l:r]  # qualified English-free source plate
 plate_here=C[ny:ny+im.height,nx:nx+im.width]
 overlap=(plate_here[:,:,3]>0)&(mask>0)
 assert not np.any(overlap),(key,"glyph intrudes into protected source separator",int(np.count_nonzero(overlap)))
 # Alpha-compose onto exact source-clean rather than erase canonical art.
 out[ny:ny+im.height,nx:nx+im.width]=rgba
 report.append(dict(id=key,english=en,korean=ko,source_bbox=[l,t,r,b],effect_bbox=[nx,ny,nx+im.width,ny+im.height],
  margins=margins,font_px=sz,vector_profile="new per-character native upright-stem 0.92, independent tracking 0.09, expanded semantic small labels; no whole-word skew",alpha=alpha))
changed=np.any(P!=out,axis=2)
assert np.count_nonzero(changed)>1000 and not np.any(changed&~residual_only)
assert not np.any((P[:,:,3]!=out[:,:,3])&~residual_only)
assert np.array_equal(out[~residual_only],P[~residual_only])
raw=np.frombuffer(current[128:],dtype=np.uint8).reshape(1024,2048,4)
if np.array_equal(raw[::-1],P):order="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(raw[::-1,:,[2,1,0,3]],P)
 order="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
data=current[:128]+body;assert len(data)==len(current) and sha(data)!=OLD
D=decode(data);assert np.array_equal(D,out)
(OUT/"B316_TRIAL_NOT_PROMOTED.dds").write_bytes(data)
def onbg(a,bg):
 layer=Image.new("RGBA",(a.shape[1],a.shape[0]),tuple(bg)+(255,))
 layer.alpha_composite(Image.fromarray(a,"RGBA"))
 return layer.convert("RGB")
views=[]
for reg in report:
 key=reg["id"];l,t,r,b=reg["source_bbox"]
 for orient in ("FLIPY","RAW"):
  crops=[a[t:b,l:r].copy() for a in (S,C,P,D)]
  if orient=="RAW":crops=[np.flipud(a).copy() for a in crops]
  for bgname,bg in (("GRAY",(110,110,110)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
   for scale in (100,50):
    frames=[onbg(a,bg) for a in crops]
    if scale!=100: frames=[im.resize((round(im.width/2),round(im.height/2)),Image.Resampling.LANCZOS) for im in frames]
    sheet=Image.new("RGB",(sum(im.width for im in frames)+12,max(im.height for im in frames)),bg)
    x=0
    for im in frames:sheet.paste(im,(x,0));x+=im.width+4
    filename=f"{key}_{orient}_{bgname}_{scale}_SOURCE_CLEAN_B285_B316.png"
    sheet.save(OUT/filename,optimize=True);views.append(filename)
evidence={"role":"B","run":"B316","queue_index":137,"regression":"IGR-041","source_sha256":SRC,
 "clean_png_sha256":CLEAN,"previous_candidate_sha256":OLD,"trial_sha256":sha(data),
 "new_trial_dds":1,"promoted_dds":0,"source_clean_outside6":0,
 "source_clean_retained_protected_separators":retained,"candidate_changed_outside_four_residual":0,
 "alpha_outside_four_residual":0,"header_exact":True,"persisted_decode":"EXACT",
 "raw_orientation":"mirror_y","native":[2048,1024],"dds_codec":order,"mips":1,
 "per_region":report,"proofs":views,"producer_visual":"PENDING_DIRECT_NATIVE_50_RAW_75",
 "C1":"NOT_RUN","C3":"NOT_RUN","user_game":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"github-actions (local network cannot resolve canonical raw source)",
 "excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B316_MACHINE_QA.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n")
print("B316_TRIAL",sha(data),"views",len(views))
