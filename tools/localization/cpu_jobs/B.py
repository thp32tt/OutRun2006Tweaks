#!/usr/bin/env python3
"""B311 q060 P0 gold OUTRUN MILES: new filled native Hangul face master (trial, fail closed).

Reconstruction method intentionally differs from B286/B297's thin silhouette,
palette recolour and radius-one expansion: a newly rendered continuous Hangul
master gets separate original-source gold face, navy separation and white rim.
NEVER promote the trial or call QA PASS without controller visual inspection.
"""
import csv, hashlib, io, json, os, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
ASSET="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
OUT=G/"role_B/20261009-B311-Q060-P0-GOLD-MILES-FILLED-MASTER"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE_SHA="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
CURRENT_SHA="7c05f2fe3f8e9e51a6ca79871e23b35f7bb7e5a1622fa52c69b2a0bf96d14295"
PBOX=(2081,250,2860,370)
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="60")
assert "rework_required" in row["artwork_status"],row["artwork_status"]
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60","--require-safe-rerender"],text=True,capture_output=True)
assert tri.returncode==0,(tri.stdout,tri.stderr)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"

candidate=(G/"hd_candidates"/ASSET).read_bytes()
assert sha(candidate)==CURRENT_SHA,"q060 current changed: do not overwrite or retry stale SHA"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with urllib.request.urlopen(url,timeout=160) as f: original=f.read()
assert sha(original)==SOURCE_SHA, "pinned English source provenance not matched"
assert original[:128]==candidate[:128],"canonical English DDS header mismatch"

def decode(b):
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
S=decode(original)
P=decode(candidate)
assert S.shape==P.shape==(2048,4096,4)
l,t,r,b=PBOX
source=S[t:b,l:r].copy()
prior=P[t:b,l:r].copy()
# The pinned original plate is transparent around the lettering. A clean
# plate must restore 0 source opacity, not cover English with foreign boxes.
assert np.count_nonzero(source[:,:,3]>8)>500
C=P.copy()
C[t:b,l:r]=0
assert not np.any(C[t:b,l:r,3])
# Outside selected source bbox, exactly preserve every current byte/pixel.
assert np.array_equal(C[:t],P[:t])

font="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(font).exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
assert Path(font).is_file()

# Source-derived palette: sample opaque native English gold, navy and white
# clusters. This is not the old flat recolour of existing narrow Korean glyphs.
pix=source.reshape(-1,4)
opaque=pix[:,3]>=210
gold=pix[opaque & (pix[:,0]>175)&(pix[:,1]>130)&(pix[:,2]>75)&(pix[:,2]<225)]
navy=pix[opaque & (pix[:,0]<70)&(pix[:,1]<95)&(pix[:,2]<145)]
white=pix[opaque & (pix[:,0]>210)&(pix[:,1]>200)&(pix[:,2]>145)]
assert min(len(gold),len(navy),len(white))>20,(len(gold),len(navy),len(white))
GOLD=tuple(np.median(gold[:,:3],axis=0).round().astype(int))
NAVY=tuple(np.median(navy[:,:3],axis=0).round().astype(int))
WHITE=tuple(np.median(white[:,:3],axis=0).round().astype(int))
assert GOLD[0]>170 and GOLD[1]>130 and NAVY[2]<145 and WHITE[0]>200
# Native contour master, with source-sized target bbox; no low-res upscale.
# The 4 Hangul syllables need controlled *whole-glyph* horizontal fitting.
word="아웃런 마일:"
selected=None
for font_size in range(119,85,-1):
    ft=ImageFont.truetype(font,font_size,index=1)
    bb=ft.getbbox(word)
    im=Image.new("L",(bb[2]-bb[0]+36,bb[3]-bb[1]+36),0)
    ImageDraw.Draw(im).text((18-bb[0],18-bb[1]),word,font=ft,fill=255)
    ib=im.getbbox()
    if not ib:continue
    glyph=im.crop(ib)
    if not (82<=glyph.height<=94):continue
    width=min(690,max(610,round(glyph.width*1.05)))
    resized=glyph.resize((width,glyph.height),Image.Resampling.LANCZOS)
    # Opposite-script slant is forbidden: readable top is moved right.
    shear=0.16; ext=int(round(shear*resized.height))
    slanted=resized.transform((width+ext,resized.height),Image.Transform.AFFINE,
        (1,shear,-shear*(resized.height-1),0,1,0),
        resample=Image.Resampling.BICUBIC)
    sb=slanted.getbbox()
    if not sb:continue
    slanted=slanted.crop(sb)
    # Native thick Hangul body, then navy separator and bright white rim.
    # This materially changes glyph geometry, not the old outline colours.
    master=slanted.filter(ImageFilter.MaxFilter(3))
    navy_layer=master.filter(ImageFilter.MaxFilter(9))
    outer_layer=navy_layer.filter(ImageFilter.MaxFilter(9))
    if outer_layer.width<=r-l-10 and outer_layer.height<=b-t-10:
        selected=(font_size,slanted,master,navy_layer,outer_layer);break
assert selected is not None,"cannot source-fit thick gold face+navy+white rings"
size,slanted,master,navy_layer,outer_layer=selected
# MaxFilter does not resize PIL images: pad mask before dilation, otherwise
# outward source bboxes can be clipped. Build all rings on padded master.
pad=12
def padded(img):
    z=Image.new("L",(img.width+pad*2,img.height+pad*2),0)
    z.paste(img,(pad,pad))
    return z
face=padded(master)
navy_mask=face.filter(ImageFilter.MaxFilter(11))
white_mask=navy_mask.filter(ImageFilter.MaxFilter(9))
dark_mask=white_mask.filter(ImageFilter.MaxFilter(3))
bbox=dark_mask.getbbox()
assert bbox
layers=Image.new("RGBA",face.size,(0,0,0,0))
def paint(color,mask):
    layer=Image.new("RGBA",face.size,tuple(color)+(0,))
    layer.putalpha(mask)
    layers.alpha_composite(layer)
paint((13,17,42),dark_mask)
paint(NAVY,white_mask)
paint(WHITE,navy_mask)
gradient=np.zeros((face.height,face.width,4),dtype=np.uint8)
top=np.array((255,249,214),dtype=np.float32)
bottom=np.array((max(210,GOLD[0]-3),max(162,GOLD[1]-15),max(75,GOLD[2]-12)),dtype=np.float32)
for i in range(face.height):
    ratio=i/max(1,face.height-1)
    gradient[i,:,0:3]=np.clip(np.round(top*(1-ratio)+bottom*ratio),0,255).astype(np.uint8)
gradient[:,:,3]=np.asarray(face,dtype=np.uint8)
layers.alpha_composite(Image.fromarray(gradient,"RGBA"))
layers=layers.crop(bbox)
xx=l+(r-l-layers.width)//2
yy=t+(b-t-layers.height)//2
assert min(xx-l,r-xx-layers.width,yy-t,b-yy-layers.height)>=5,(xx-l,r-xx-layers.width,yy-t,b-yy-layers.height)
N=C.copy()
new=np.asarray(layers,dtype=np.uint8)
N[yy:yy+layers.height,xx:xx+layers.width]=new
changed=np.any(P!=N,axis=2)
allow=np.zeros(P.shape[:2],bool)
allow[t:b,l:r]=True
assert np.any(changed&allow) and not np.any(changed&~allow)
assert not np.any((P[:,:,3]!=N[:,:,3])&~allow)
assert np.array_equal(N[~allow],P[~allow])
assert not np.any((N[t:b,l:r,3]>0)&(C[t:b,l:r,3]>0))
# Persist native DDS in exactly the original format, flip and mip structure.
raw=np.frombuffer(candidate[128:],dtype=np.uint8).reshape(2048,4096,4)
if np.array_equal(raw[::-1],P): mode="RGBA";body=N[::-1].copy().tobytes()
else:
    assert np.array_equal(raw[::-1,:,[2,1,0,3]],P),"unrecognized raw pixel order"
    mode="BGRA";body=N[::-1,:,[2,1,0,3]].copy().tobytes()
data=candidate[:128]+body
assert len(data)==len(candidate) and sha(data)!=CURRENT_SHA
assert np.array_equal(decode(data),N)
# DO NOT TOUCH hd_candidates UNTIL direct human visual acceptance.
trial=OUT/"B311_Q060_TRIAL_NOT_PROMOTED.dds"
trial.write_bytes(data)
assert sha(trial.read_bytes())==sha(data)
def tile(a,orient):
    v=a[t:b,l:r].copy()
    return np.flipud(v).copy() if orient=="RAW" else v
def onbg(a,bg):
    im=Image.new("RGBA",(a.shape[1],a.shape[0]),tuple(bg)+(255,))
    im.alpha_composite(Image.fromarray(a,"RGBA"))
    return im.convert("RGB")
proofs=[]
for orient in ("FLIPY","RAW"):
    for color,bg in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
        for percent in (100,75,50):
            parts=[]
            for name,arr in (("ENGLISH",S),("CLEAN",C),("CURRENT",P),("TRIAL",N)):
                im=onbg(tile(arr,orient),bg)
                if percent!=100:
                    im=im.resize((round(im.width*percent/100),round(im.height*percent/100)),Image.Resampling.LANCZOS)
                parts.append(im)
            contact=Image.new("RGB",(sum(x.width for x in parts)+12,max(x.height for x in parts)),bg)
            pos=0
            for part in parts:contact.paste(part,(pos,0));pos+=part.width+4
            name=f"B311_{orient}_{color}_{percent}_SOURCE_CLEAN_CURRENT_TRIAL.png"
            contact.save(OUT/name,optimize=True);proofs.append(name)
for name,arr in (("SOURCE",S),("CLEAN",C),("CURRENT",P),("TRIAL",N)):
    Image.fromarray(arr[t:b,l:r],"RGBA").save(OUT/f"B311_{name}_LOSSLESS.png",optimize=True)
report={
"schema_version":2,"role":"B","run":"B311","queue_index":60,"priority":"P0",
"source_sha256":SOURCE_SHA,"candidate_sha256":CURRENT_SHA,"trial_sha256":sha(data),
"trial_only_dds":1,"new_production_dds":0,"trial_promoted":False,
"asset":ASSET,"source_bbox":list(PBOX),
"trial_bbox":[xx,yy,xx+layers.width,yy+layers.height],
"margins":[xx-l,r-xx-layers.width,yy-t,b-yy-layers.height],
"font":"native NotoSansCJK Black",
"font_size":size,"palette_from_native_source":{"gold":GOLD,"navy":NAVY,"white":WHITE},
"method":"Native filled source-family Hangul cream-to-gold face gradient, navy depth, warm rim, right lean. B310 STAGE and B296 white protected",
"machine_checks":{"dds_header_exact":True,"format":mode,"mips":1,"native":[4096,2048],
"roundtrip":"PASS","changed_outside_gold":0,"alpha_outside_gold":0,
"protected_outside_gold":"UNCHANGED_EXACT","source_cell_clean_alpha":0,
"source_size_and_positive_margins":"PASS"},
"proofs":proofs,"producer_visual":"PENDING_INDEPENDENT_DIRECT_CONTROLLER_REVIEW",
"status":"TRIAL_ONLY_NOT_PROMOTED_NO_QA_PASS","IGR044":"OPEN_USER_INGAME_FAIL",
"C2":"NOT_RUN","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
"backend":"github-actions",
"excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B311_MACHINE_AND_METHOD.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda x: x.item() if hasattr(x,'item') else str(x))+"\n")
print("B311_TRIAL_ONLY",sha(data),"bbox",report["trial_bbox"],"status",report["status"])
