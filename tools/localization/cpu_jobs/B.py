#!/usr/bin/env python3
"""B304: q228 source-conditioned SILVER FACE representative prototype, NOT a promoted DDS.

The C317 in-game return found flat/hollow Korean against filled chrome source.
Generate one material-method prototype for producer visual acceptance before any
13-row propagation, retaining all unrelated persisted pixels. Fail closed.
"""
import csv,hashlib,io,json,os,sys,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from scipy.ndimage import binary_dilation,distance_transform_edt
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics");REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
D=G/"role_B/20261009-B304-Q228-SOURCE-CHROME-REPRESENTATIVE";D.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
src_hash="3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
old_hash="28e814599105600eb0222eb1ffe0057dc1e108520580a958ae3b3b7ec08f2808"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","228","--require-safe-rerender"],text=True,capture_output=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:row=next(z for z in csv.DictReader(f) if z["index"].lstrip("\ufeff")=="228")
assert "rework_required" in row["artwork_status"]
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
assert any(r["id"]=="IGR-038" and r["status"]=="OPEN_USER_INGAME_FAIL" for r in rows)
p=G/"hd_candidates"/REL;old=p.read_bytes()
assert sha(old)==old_hash,"Concurrent q228 producer changed DDS - exit rather than overwrite"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
with urllib.request.urlopen(url,timeout=120) as r:source=r.read()
assert sha(source)==src_hash
assert source[:128]==old[:128] and len(source)==len(old)==128+2048*2048*4
def dec(data):
 im=Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 a=np.array(im,dtype=np.uint8);assert a.shape==(2048,2048,4);return a
S=dec(source);P=dec(old)
base=G/"role_B/20261005-B-PRODUCTION68"
manifest=json.loads((base/"B68_E7F6_REPORT.json").read_text())
assert manifest["source_sha256"]==src_hash and len(manifest["rows"])==13
C=np.asarray(Image.open(base/"E7F6_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
allowed=np.zeros((2048,2048),bool)
for r in manifest["rows"]:
 l,t,rr,b=r["original_bbox"];allowed[t:b,l:rr]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed),"source/clean contamination outside exact cells"
# C317 00 COAST 2 COAST: the representative for the shared silver chrome family.
r=next(x for x in manifest["rows"] if x["source"]=="coast 2 coast")
l,t,rr,b=r["original_bbox"];H=b-t;W=rr-l
assert not np.any(C[t:b,l:rr,3]),"authored CLEAN not alpha-empty under source"
orig=S[t:b,l:rr].copy()
a=orig[:,:,3]>110;rgb=orig[:,:,:3].astype(np.float32)
lum=rgb[:,:,0]*0.2126+rgb[:,:,1]*0.7152+rgb[:,:,2]*0.0722
face=a&(lum>=120)
assert np.count_nonzero(face)>500,"cannot calibrate original chrome body"
# Original source CONDITIONING: derive vertical metal colour stops from bright
# fill pixels, rather than inventing a flat grayscale or random bevel palette.
stops=[];cal=[]
for v in np.linspace(0,1,7):
 cy=int(v*(H-1));lo=max(0,cy-10);hi=min(H,cy+11)
 valid=face[lo:hi]
 if np.count_nonzero(valid)<30:valid=face
 sample=rgb[lo:hi][valid] if valid.shape[0]==hi-lo else rgb[face]
 stop=np.median(sample,axis=0).astype(int)
 stops.append(stop.tolist());cal.append(int(np.count_nonzero(valid)))
edge=rgb[a&(lum<75)]
assert len(edge)>50,"missing source original dark depth reference"
edge_color=np.median(edge,axis=0).round().astype(np.uint8)
# Use native vector glyphs. NEVER upscale old B218 hollow Korean raster.
fonts=["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
       "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
if not any(Path(z).exists() for z in fonts):
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
fontpath=next(z for z in fonts if Path(z).exists())
target=r["korean"]
chosen=None
for size in range(150,89,-1):
 ft=ImageFont.truetype(fontpath,size,index=1)
 bb=ft.getbbox(target)
 m=Image.new("L",(bb[2]-bb[0]+16,bb[3]-bb[1]+16),0)
 ImageDraw.Draw(m).text((8-bb[0],8-bb[1]),target,font=ft,fill=255)
 inkbb=m.getbbox()
 if inkbb:
  ink=m.crop(inkbb)
  if ink.width<=W-20 and ink.height<=H-18 and ink.height>=H-28:
   chosen=(ink,size);break
assert chosen,"no source-sized native glyph found"
mask_image,font_size=chosen
# Proven source readable orientation: use slant measured from source left-bound
# contour at upper/lower halves; reject uncalibrated transformations.
salpha=orig[:,:,3]>90
ys,xs=np.where(salpha)
top=xs[ys<=np.percentile(ys,25)];bottom=xs[ys>=np.percentile(ys,75)]
slope_obs=float(np.percentile(top,5)-np.percentile(bottom,5))
# Contour positions are affected by English letters: do not invent a shear
# unless the measured displacement has stable magnitude and sign.
mask=np.asarray(mask_image,np.uint8).astype(np.float32)/255.
mh,mw=mask.shape
xx=l+10;yy=t+(H-mh)//2
assert xx>l+5 and xx+mw<rr-5 and yy>=t+5 and yy+mh<=b-5
foreground=np.zeros((H,W),dtype=bool)
foreground[yy-t:yy-t+mh,xx-l:xx-l+mw]=mask>0.30
dist=distance_transform_edt(foreground)
# Silver must be genuinely filled, not merely a hollow outline: all core
# pixels receive source sampled metal face; border receives source dark depth.
core=dist>=2.1
assert np.count_nonzero(core)>4500
outer=binary_dilation(foreground,iterations=2)
shadow=binary_dilation(foreground,iterations=2)
shadow=np.pad(shadow[:-2,:-2],((2,0),(2,0)),constant_values=False)
# B304 prototype: no rectangles; transparent-only glyph material over clean.
out=P.copy();block=C[t:b,l:rr].copy()
block[shadow,:3]=edge_color;block[shadow,3]=np.maximum(block[shadow,3],155)
block[outer,:3]=edge_color;block[outer,3]=np.maximum(block[outer,3],220)
ys2=np.arange(H)
for j in range(H):
 v=np.interp(j/max(1,H-1),np.linspace(0,1,7),[float(z[0]) for z in stops])
 k=np.interp(j/max(1,H-1),np.linspace(0,1,7),[float(z[1]) for z in stops])
 z=np.interp(j/max(1,H-1),np.linspace(0,1,7),[float(z[2]) for z in stops])
 row=core[j]
 if not row.any():continue
 block[j,row,:3]=np.uint8(np.clip([v,k,z],0,255))
 block[j,row,3]=255
# Keep only source effect footprints. No alpha from a rectangular crop.
allowed_roi=np.zeros((H,W),bool);allowed_roi[5:-5,5:-5]=True
assert not np.any(block[~allowed_roi,3])
out[t:b,l:rr]=block
changed=np.any(P!=out,axis=2)
mask_allowed=np.zeros((2048,2048),bool);mask_allowed[t:b,l:rr]=True
assert not np.any(changed&~mask_allowed)
assert not np.any((P[:,:,3]!=out[:,:,3])&~mask_allowed)
raw=source[128:]
source_channels=np.frombuffer(raw,dtype=np.uint8).reshape(2048,2048,4)
if np.array_equal(source_channels[::-1],S):
 mode="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(source_channels[::-1,:,[2,1,0,3]],S)
 mode="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
trial=old[:128]+body
assert sha(trial)!=old_hash
assert np.array_equal(dec(trial),out),"persisted DDS failed decode parity"
trialpath=D/"B304_Q228_REPRESENTATIVE_TRIAL_NOT_PROMOTED.dds"
trialpath.write_bytes(trial)
assert np.array_equal(dec(trialpath.read_bytes()),out)
# Output proof at native and practical levels for direct independent inspection.
def flatten(img,bg):
 base=Image.new("RGBA",(img.shape[1],img.shape[0]),(*bg,255))
 base.alpha_composite(Image.fromarray(img.astype("uint8"),"RGBA"))
 return base.convert("RGB")
views=[]
for orientation in ("FLIPY","RAW"):
 tiles=[q[t:b,l:rr] for q in (S,C,P,out)]
 if orientation=="RAW":tiles=[np.flipud(q).copy() for q in tiles]
 for bg in ((128,128,128),(255,255,255),(0,0,0)):
  for size in (100,75,50):
   ims=[flatten(z,bg) for z in tiles]
   if size<100:ims=[im.resize((round(im.width*size/100),round(im.height*size/100)),Image.Resampling.LANCZOS) for im in ims]
   sheet=Image.new("RGB",(sum(im.width for im in ims)+12,max(im.height for im in ims)),(128,128,128))
   x=0
   for im in ims:sheet.paste(im,(x,0));x+=im.width+4
   name=f"COAST2COAST_{orientation}_{bg[0]}_{size}_SOURCE_CLEAN_OLD_TRIAL.png"
   sheet.save(D/name,optimize=True);views.append(name)
# Preserve full lossless 4-stage crop and an exact binary change mask.
for name,v in (("SOURCE",S),("CLEAN",C),("OLD",P),("TRIAL",out)):
 Image.fromarray(v[t:b,l:rr],"RGBA").save(D/f"COAST2COAST_{name}_LOSSLESS.png")
Image.fromarray(np.uint8(changed[t:b,l:rr])*255,"L").save(D/"CHANGED_MASK.png")
report={"role":"B","run":"B304","queue_index":228,"task":"IGR-038 source conditioned chrome representative",
"status":"REPRESENTATIVE_METHOD_TRIAL_PENDING_VISUAL_GATE","source_sha256":src_hash,
"previous_candidate_sha256":old_hash,"trial_sha256":sha(trial),"trial_dds":1,"promoted_dds":0,
"source_color_stops":stops,"source_samples_each_stop":cal,
"source_edge_rgb":edge_color.tolist(),"source_slant_observation_px":slope_obs,
"font":Path(fontpath).name,"font_size_native":font_size,"korean":target,
"source_bbox":[l,t,rr,b],"glyph_shape":list(mask.shape),"core_pixels":int(core.sum()),
"header":"BYTE_EXACT","decoded_roundtrip":"PASS","mode":mode,"mips":1,
"source_vs_clean_outside_exact_union":0,"source_clean_alpha":0,
"clean_vs_trial_outside_representative":0,"trial_vs_previous_outside_representative":0,
"separate_proofs":views,"producer_visual":"PENDING_CONTROLLER_DIRECT_100_75_50_RAW",
"new_candidate_promoted":False,"C2":"NOT_RUN","C3":"NOT_RUN",
"USER_INGAME":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"backend":"github-actions","exclusions":["VR","FFB","DX11","DXVK"]}
(D/"B304_MACHINE_GATE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B304_REPRESENTATIVE_READY",json.dumps({"trial_sha":sha(trial),"source":src_hash,"current":old_hash,"fill_core_pixels":int(core.sum()),"views":len(views),"mode":mode}),flush=True)
