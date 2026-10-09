#!/usr/bin/env python3
"""B332 q060 C332 P0: restore original protected orange sibling while repairing gold.

This is NEW material rework: B331 cleared the entire rectangular gold region,
destroying the upper part of the distinct orange BEST... sprite. Use a
canonical source-conditioned ORANGE COMPONENT MASK, copy protected source
pixels exactly, and relocate the previously native-rendered gold Korean text
above the protected boundary, without touching other atlas art.
Only an unapproved DDS trial is produced until direct multi-view self-QA.
"""
import csv,hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
OUT=G/"role_B/20261009-B332-Q060-ORANGE-PROTECTED-SIBLING-RESTORE"
OUT.mkdir(parents=True,exist_ok=True)
RUN_KEY="OUTRUN-KOR-B332-Q060-C332-ORANGE-PROTECTED-ART-20261009-2110"
SOURCE_SHA="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
CURRENT_SHA="3480bef0369677d9e0b8d3d7b334d6a261de7bc2539c225a939843325a3e36a2"
h=lambda b:hashlib.sha256(b).hexdigest()
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="60")
assert q["artwork_status"]=="c332_c2_rework_required_b331_orange_neighbor_protected_art_loss",q["artwork_status"]
c332=json.loads((G/"role_C/20261009-C332-C2-Q060-B331-ORANGE-PROTECTED-ART-FAIL/C332_Q060_CONTROLLER_C2_REWORK.json").read_text())
assert c332["current_candidate_sha256"]==CURRENT_SHA and c332["result"]=="REWORK_REQUIRED"
src_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with urllib.request.urlopen(src_url,timeout=180) as response:src= response.read()
assert h(src)==SOURCE_SHA
old=(G/"hd_candidates"/REL).read_bytes()
assert h(old)==CURRENT_SHA and old[:128]==src[:128] and len(src)==len(old)==33554560
assert src[84:88] in (b"\x00\x00\x00\x00",b"RGBA")  # uncompressed DDS
H,W=2048,4096
assert (struct.unpack_from("<I",old,12)[0],struct.unpack_from("<I",old,16)[0],struct.unpack_from("<I",old,28)[0])==(H,W,1)
def decode(b):
 a=np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(H,W,4);return a
S=decode(src);P=decode(old)
l,t,r,b=2081,250,2860,370
ol,ot,orr,ob=2133,256,2807,363
assert c332["new_pixel_finding"]["source_orange_pixels"]>8000
# Core shape from exact English source orange pixels, not B331's contaminated
# CLEAN plate. Expand in a small padded ROI to retain original navy border.
xl,yt,xr,yb=l-24,t-24,r+24,b+30
sr=S[yt:yb,xl:xr]; yy=np.arange(yt,yb)[:,None]
R=sr[:,:,0].astype(np.int32);Gg=sr[:,:,1].astype(np.int32);B=sr[:,:,2].astype(np.int32)
orange=(sr[:,:,3]>90)&(R>150)&(Gg>35)&(B*100<R*55)&(R*100>Gg*105)&(yy>=340)
assert int(np.count_nonzero(orange))>8000,"No identifiable original orange sibling"
protected=binary_dilation(orange,iterations=12)
# Everything original-orange and nearby edge is preserved in source RGBA.
inside=protected[t-yt:b-yt,l-xl:r-xl]
source_orange=(orange[t-yt:b-yt,l-xl:r-xl])
assert int(source_orange.sum())>=8892,(source_orange.sum(),8892)
C=P[t:b,l:r].copy()
C[:]=0  # clean gold rectangle: needs no original English pixels
C[inside]=S[t:b,l:r][inside]
# Strongest guard: every previously lost orange source pixel reappears
# pixel-identical, including its transparent shadow and neighbouring art.
assert np.array_equal(C[source_orange],S[t:b,l:r][source_orange])
# B331 native Korean lettering gets reduced (never enlarged) into the intact
# original gold-only upper lane. Source title is highly horizontally condensed;
# high-quality native reduction changes height from 107 to 80 while retaining
# 674px width, attaining similarly racing/italic proportions.
old_ink=Image.fromarray(P[ot:ob,ol:orr].copy(),"RGBA")
new_ink=old_ink.resize((orr-ol,80),Image.Resampling.LANCZOS)
nx,ny=ol,251
assert nx>=l+1 and nx+new_ink.width<=r-1 and ny>=t+1 and ny+new_ink.height<=b-1
active=np.asarray(new_ink)[:,:,3]>0
protect_at_dest=inside[ny-t:ny-t+80,nx-l:nx-l+new_ink.width]
assert not np.any(active&protect_at_dest),"Condensed gold overlaps protected original orange neighbouring art"
out=P.copy()
out[t:b,l:r]=C
gold_layer=Image.fromarray(out[ny:ny+80,nx:nx+new_ink.width].copy(),"RGBA")
gold_layer.alpha_composite(new_ink)
out[ny:ny+80,nx:nx+new_ink.width]=np.asarray(gold_layer,dtype=np.uint8)
roi=out[t:b,l:r]; sroi=S[t:b,l:r]
assert np.array_equal(roi[inside],sroi[inside]),"All protected graphic pixels MUST be restored byte-exact"
assert np.count_nonzero(roi[:,:,3][source_orange])==int(source_orange.sum()),"Orange lost"
# Original lower-band orange inventory must be restored exactly.
source_orange_count=int(source_orange.sum())
orange_saved=roi[source_orange]
assert np.array_equal(orange_saved,sroi[source_orange])
# No writes at all to any non-gold atlas pixel.
outside=np.ones((H,W),dtype=bool);outside[t:b,l:r]=False
assert np.array_equal(out[outside],P[outside]),"Other labels or HDR sprite modified"
assert np.count_nonzero(np.any(out!=P,axis=2))>1500
# The source RGB for orange is restored in protected region; old English
# is cleaned in nonprotected gold rectangle; the native Hangul has no foreign
# backdrop beyond its own alpha.
assert np.count_nonzero(roi[:,:,3])>source_orange_count
assert np.count_nonzero(roi[:,:,3][~inside])>3000
raw=np.frombuffer(old[128:],dtype=np.uint8).reshape(H,W,4)
if np.array_equal(raw[::-1],P): mode="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(raw[::-1,:,[2,1,0,3]],P);mode="BGRA"
 body=out[::-1,:,[2,1,0,3]].copy().tobytes()
data=old[:128]+body
assert len(data)==len(old) and data[:128]==old[:128] and h(data)!=CURRENT_SHA
final=decode(data)
assert np.array_equal(final,out),"Persisted actual DDS roundtrip"
assert np.array_equal(final[t:b,l:r][inside],S[t:b,l:r][inside])
assert np.array_equal(final[outside],P[outside])
outpath=OUT/"B332_Q060_ORANGE_PROTECTED_UNAPPROVED.dds";outpath.write_bytes(data)
assert h(outpath.read_bytes())==h(data)
# Include complete 779x160 window to catch sibling-text loss the previous
# producer gold-only crop hid. Never use a cropped gold-only view for approval.
px0,py0,px1,py1=l,230,r,400
proofs=[]
view={"SOURCE":S,"CLEAN_PLATE":out*0,"OLD_B331":P,"NEW_B332":final}
# Clean plate is current saved before lettering stripped in scoped gold region:
# outside source gold it keeps current other atlas art, inside it keeps protected orange.
clean=P.copy()
clean[t:b,l:r]=C
view["CLEAN_PLATE"]=clean
for ori in ("FLIPY","RAW"):
 for background,bg in (("BLACK",(0,0,0)),("GRAY",(85,85,85)),("WHITE",(255,255,255))):
  for percent in (100,75,50):
   chunks=[]
   for name,A in view.items():
    roi0=A[py0:py1,px0:px1].copy()
    if ori=="RAW":roi0=np.flipud(roi0)
    im=Image.new("RGBA",(px1-px0,py1-py0),(*bg,255))
    im.alpha_composite(Image.fromarray(roi0,"RGBA"))
    if percent<100:im=im.resize((round(im.width*percent/100),round(im.height*percent/100)),Image.Resampling.LANCZOS)
    chunks.append(im.convert("RGB"))
   contact=Image.new("RGB",(sum(q.width for q in chunks)+12,max(q.height for q in chunks)),(85,85,85));xcur=0
   for im in chunks:contact.paste(im,(xcur,0));xcur+=im.width+4
   name=f"B332_{ori}_{background}_{percent}_FULL_GOLD_ORANGE_SOURCE_CLEAN_OLD_NEW.png"
   contact.save(OUT/name,optimize=True);proofs.append(name)
for name,A in view.items():
 Image.fromarray(A[py0:py1,px0:px1].copy(),"RGBA").save(OUT/f"B332_{name}_READABLE_ROI.png",optimize=True)
 Image.fromarray(np.flipud(A[py0:py1,px0:px1]).copy(),"RGBA").save(OUT/f"B332_{name}_RAW_ROI.png",optimize=True)
Image.fromarray(np.uint8(inside)*255,"L").save(OUT/"B332_PROTECTED_ORANGE_MASK.png")
report={
 "schema_version":2,"run":"B332","run_key":RUN_KEY,"role":"B","queue_index":60,
 "priority":"P0","user_igr":"IGR044_OPEN_USER_INGAME_FAIL","source_sha256":SOURCE_SHA,
 "previous_sha256":CURRENT_SHA,"trial_sha256":h(data),"trial_promoted":False,
 "unapproved_trial_dds_count":1,"approved_dds_count":0,
 "method":"canonical source orange component + 12px expansion, exact original protected pixels restored within gold source ROI; relocate and downsize native B331 racing italic to upper lane",
 "protected_original_orange_exact_pixels":source_orange_count,
 "protected_original_orange_rgba_diff":0,
 "protected_dilated_rgba_diff":0,
 "outside_gold_rgba_diff":0,"outside_gold_alpha_diff":0,
 "prior_candidate_native_region":[ol,ot,orr,ob],
 "new_gold_region":[nx,ny,nx+new_ink.width,ny+80],
 "source_gold_bbox":[l,t,r,b],
 "full_comparison_window":[px0,py0,px1,py1],
 "protected_overlap_with_new_gold_ink":0,
 "DDS_header":"EXACT","DDS_native":[W,H],"DDS_mode":mode,"mips":1,
 "persisted_decode":"EXACT","raw_orientation":"MIRROR_Y","proofs":proofs,
 "controller_visual":"PENDING_DIRECT_NATIVE_AND_RAW_SIBLING_REVIEW",
 "independent_C2":"NOT_RUN","C3":"NOT_RUN",
 "RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GitHub Actions","excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B332_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B332_TRIAL",json.dumps({"sha":h(data),"orange":source_orange_count,"mask":int(inside.sum()),"proofs":len(proofs)},ensure_ascii=False))
