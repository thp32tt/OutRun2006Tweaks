#!/usr/bin/env python3
"""B300 q098: new dual-alpha/diffuse navy glow approach (C310 rework).
TRIAL ONLY. Must be inspected on actual persisted BC3 before promotion.
"""
import hashlib,io,json,os,struct,sys,tempfile,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
ASSET=G/"hd_candidates"/REL
DIR=G/"role_B/20261009-B300-Q098-ALPHA-GLOW-SOURCE-PROFILE"
DIR.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
PREV="192d627428dfa4328035d5105dcfbd4395d8bbadfa154a9f533a1c48583eac4b"
SRC="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
CLEAN_SHA="b5c9c07a2490abd055153f750b415193eb84ef14c298b3e3873fd915db3af9e8"
b=ASSET.read_bytes()
assert sha(b)==PREV,("concurrent q098 changed",sha(b))
t=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],capture_output=True,text=True,check=True)
tri=json.loads(t.stdout)["assets"][0]
assert tri["next_action"]=="MATERIAL_REWORK",tri
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with urllib.request.urlopen(url,timeout=160) as f: sourcebytes=f.read()
assert sha(sourcebytes)==SRC and sourcebytes[:128]==b[:128]
assert b[84:88]==b"DXT5" and len(b)==262272
h,w=128,2048
def dec(bytes_):
 return np.asarray(Image.open(io.BytesIO(bytes_)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(sourcebytes);P=dec(b)
cpath=G/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
mpath=G/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
sm=G/"role_B/20261005-B-PRODUCTION40/42E618FD_SOURCE_TEXT_MASK.png"
assert sha(cpath.read_bytes())==CLEAN_SHA
C=np.asarray(Image.open(cpath).convert("RGBA"))
mask=np.asarray(Image.open(mpath).convert("L"))
sourcemask=np.asarray(Image.open(sm).convert("L"))
assert S.shape==P.shape==C.shape==(128,2048,4)
srcbox=(431,6,1674,123); targetbox=(580,11,1524,116)
yy,xx=np.ogrid[:h,:w]
source_scope=(xx>=srcbox[0])&(xx<srcbox[2])&(yy>=srcbox[1])&(yy<srcbox[3])
assert not np.any(np.any(S!=C,axis=2)&~source_scope)
assert np.count_nonzero(C[:,:,3][source_scope&(sourcemask>80)]>16)==0
# Genuine material method change vs B279: alter stored BC3 alpha support
# for source-derived diffuse glow *and* rebalance the white face/narrow
# sharp keyline in one pass. No flat/shear/width scaling and no raster upscale.
# SOURCE profile: bright italic white core plus thick, softened navy perimeter.
sRgb=S[:,:,:3]; sa=S[:,:,3]
swhite=(np.min(sRgb,axis=2)>=230)&(sa>160)&source_scope
snavy=(sRgb[:,:,0]<55)&(sRgb[:,:,1]<78)&(sRgb[:,:,2]>sRgb[:,:,0]+12)&(sa>45)&source_scope
assert swhite.sum()>10000 and snavy.sum()>20000
WHITE=np.percentile(sRgb[swhite],90,axis=0).round().astype(np.uint8)
NAVY=np.percentile(sRgb[snavy],35,axis=0).round().astype(np.uint8)
assert WHITE.min()>210 and NAVY[2]>NAVY[0]+15,(WHITE,NAVY)
prgb=P[:,:,:3]
alpha=P[:,:,3].astype(np.float32)
# Treat the existing persisted nonzero alpha as retained glyph silhouette;
# avoid solid dark fill of entire Korean syllables.
strong=alpha>=170
wh=(prgb.min(axis=2)>=211)&strong
dist_white=distance_transform_edt(wh)
# Inner navy depth on a portion of the too-wide solid white face.
# Source original has much more substantial navy support than B279.
inner_ring=wh&(dist_white<=2.2)
# Expand the stored alpha by up to 3px with smooth falloff; respect source
# effect bbox and positive >=2px separation in both axes. This is a separate
# alpha effect from previous B279 color-only recolors.
glyph=alpha>=32
outside_dist=distance_transform_edt(~glyph)
halo=(outside_dist>0)&(outside_dist<=3.1)
valid=(xx>=576)&(xx<1528)&(yy>=8)&(yy<120)&source_scope
halo&=valid
newalpha=alpha.copy()
potential=115.0*np.exp(-0.5*(outside_dist/2.0)**2)
newalpha[halo]=np.maximum(newalpha[halo],potential[halo])
newalpha=np.uint8(np.clip(np.rint(newalpha),0,255))
# Recolor white edge within existing glyph and tint newly revealed halo
# with exact source-family navy. Retain core white and original Hangul shapes.
wantRGB=P[:,:,:3].copy()
wantRGB[inner_ring]=NAVY
wantRGB[halo]=NAVY
assert halo.sum()>1000 and inner_ring.sum()>1000,(halo.sum(),inner_ring.sum())
def rgb565(p):
 r,g,bl=[int(x) for x in p];return (((r*31+127)//255)<<11)|(((g*63+127)//255)<<5)|((bl*31+127)//255)
def exp565(v):
 return np.array([(((v>>11)&31)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31],dtype=np.int16)
w565,n565=rgb565(WHITE),rgb565(NAVY)
assert w565>n565
a,bcol=exp565(w565),exp565(n565)
pal=np.array([a,bcol,(2*a+bcol+1)//3,(a+2*bcol+1)//3],dtype=np.int16)
def alpha_palette(a0,a1):
 if a0>a1:return np.array([a0,a1,(6*a0+a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(a0+6*a1)//7],dtype=np.int16)
 return np.array([a0,a1,(4*a0+a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(a0+4*a1)//5,0,255],dtype=np.int16)
output=bytearray(b)
blocks=0
for y in range(8,120,4):
 for x in range(576,1528,4):
  x2,y2=x+4,y+4
  relevant=(halo[y:y2,x:x2]|inner_ring[y:y2,x:x2])
  if not relevant.any():continue
  # Fully enclosed within original source effect bbox, no protected art.
  assert x>=srcbox[0] and x2<=srcbox[2] and y>=srcbox[1] and y2<=srcbox[3]
  al=newalpha[y:y2,x:x2].astype(np.int16)
  assert al.shape==(4,4)
  oldalpha=alpha[y:y2,x:x2]
  desired=wantRGB[y:y2,x:x2].astype(np.int16)
  nearest=np.sum((desired[:,:,None,:]-pal[None,None,:,:])**2,axis=3).argmin(axis=2)
  alpha_changed=not np.array_equal(al,oldalpha)
  offset=128+(((h-y2)//4)*(w//4)+(x//4))*16
  if alpha_changed:
   a0,a1=int(np.max(al)),int(np.min(al))
   if a0==a1:
    a0,a1=255,0
   apa=alpha_palette(a0,a1)
   inds=np.abs(al[:,:,None]-apa[None,None,:]).argmin(axis=2)
   abits=0
   for iy in range(4):
    for ix in range(4):
     abits|=int(inds[iy,ix])<<(3*((3-iy)*4+ix))
   output[offset:offset+8]=bytes([a0,a1])+abits.to_bytes(6,"little")
  bits=0
  for iy in range(4):
   for ix in range(4):
    bits|=int(nearest[iy,ix])<<(2*((3-iy)*4+ix))
  struct.pack_into("<HHI",output,offset+8,w565,n565,bits)
  blocks+=1
assert blocks>700,blocks
trial=bytes(output)
assert trial[:128]==b[:128] and len(trial)==len(b)
D=dec(trial)
assert sha(trial)!=sha(b), "no material image change"
diff=np.any(D!=P,axis=2)
alpha_diff=D[:,:,3]!=P[:,:,3]
assert not np.any(diff&~source_scope),("outside source changed",int(np.sum(diff&~source_scope)))
assert not np.any(diff&~valid),("outside selected render zone",int(np.sum(diff&~valid)))
assert not np.any(alpha_diff&~valid)
assert np.count_nonzero((D[:,:,3]>8)&~source_scope)==np.count_nonzero((P[:,:,3]>8)&~source_scope)
# Formal exact original effect-bbox: no introduced alpha at or beyond edges.
newglyph=(D[:,:,3]>16)&valid
ys,xs=np.nonzero(newglyph)
bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
assert bbox[0]>srcbox[0] and bbox[1]>srcbox[1] and bbox[2]<srcbox[2] and bbox[3]<srcbox[3],bbox
# Verify the trial from the actual persisted bytes rather than desired arrays.
path=DIR/"Q098_B300_TRIAL_NOT_PROMOTED.dds"
path.write_bytes(trial)
assert sha(path.read_bytes())==sha(trial) and np.array_equal(dec(path.read_bytes()),D)
# Quantities are descriptive only; no threshold can supersede visual source match.
def ratios(v):
 rgb=v[:,:,:3];alp=v[:,:,3]
 white=(rgb.min(axis=2)>220)&(alp>120)&source_scope
 navy=(rgb[:,:,0]<55)&(rgb[:,:,1]<80)&(rgb[:,:,2]>rgb[:,:,0]+12)&(alp>80)&source_scope
 return {"white":int(white.sum()),"navy":int(navy.sum()),"white_navy":round(float(white.sum()/max(1,navy.sum())),3)}
def compose(arr,bg):
 im=Image.fromarray(arr,"RGBA")
 canvas=Image.new("RGBA",(w,h),bg)
 canvas.alpha_composite(im)
 return canvas.convert("RGB")
evidence=[]
for orientation in ("READABLE","RAW"):
 seq=(S,C,P,D) if orientation=="READABLE" else tuple(np.flipud(z).copy() for z in (S,C,P,D))
 for bgname,bg in [("GRAY",(116,116,116,255)),("WHITE",(255,255,255,255)),("BLACK",(0,0,0,255))]:
  for scale in (100,75,50):
   chunks=[compose(z,bg) for z in seq]
   if scale<100:
    chunks=[z.resize((round(w*scale/100),round(h*scale/100)),Image.Resampling.LANCZOS) for z in chunks]
   sheet=Image.new("RGB",(sum(z.width for z in chunks)+12,max(z.height for z in chunks)),(120,120,120))
   at=0
   for z in chunks:sheet.paste(z,(at,0));at+=z.width+4
   fname=f"{orientation}_{bgname}_{scale}_SOURCE_CLEAN_B279_B300.png"
   sheet.save(DIR/fname)
   evidence.append(fname)
for name,a in [("SOURCE",S),("CLEAN",C),("B279",P),("B300",D)]:
 Image.fromarray(a,"RGBA").save(DIR/f"{name}_NATIVE_LOSSLESS.png")
report={"role":"B","run":"B300","queue_index":98,"asset":REL,
 "triage":"MATERIAL_REWORK","source_sha256":SRC,"clean_sha256":CLEAN_SHA,
 "current_sha256":PREV,"trial_sha256":sha(trial),"trial_dds":1,
 "new_promoted_dds":0,"worker":"GITHUB_ACTIONS", "native":[2048,128],
 "format":"BC3 DXT5 mip1 RAW_FLIPY",
 "new_method":"source-conditioned dual-stage actual BC3 alpha halo (max 3.1px) plus inner navy redistribution 2.2px; distinct from B279 color-only sharp keyline; preserve font silhouette and old white core; no font stretching/upscale",
 "source_profile":{"face":WHITE.tolist(),"navy":NAVY.tolist(),"canonical_ratio":ratios(S)},
 "prior_ratio":ratios(P),"trial_ratio":ratios(D),
 "trial_bbox":bbox, "original_effect_bbox":srcbox,
 "changed_bc3_blocks":blocks,"changed_native_pixels":int(diff.sum()),
 "changed_alpha_native_pixels":int(alpha_diff.sum()),"outside_source_rgba":int((diff&~source_scope).sum()),
 "outside_render_zone_rgba":int((diff&~valid).sum()),"source_clean_outside_rgba":0,
 "clean_text_alpha_residual":0,"header_exact":True,"persisted_decode_exact":True,
 "evidence_comparisons":evidence,"producer_visual":"PENDING_FIRST_LOOK",
 "C2":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED",
 "excluded":["VR","FFB","DX11","DXVK"]}
(DIR/"B300_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B300_TRIAL_OK",json.dumps({"sha":sha(trial),"blocks":blocks,"diff":int(diff.sum()),"alpha_change":int(alpha_diff.sum()),"bbox":bbox,"ratios":[ratios(S),ratios(P),ratios(D)]},ensure_ascii=False))
