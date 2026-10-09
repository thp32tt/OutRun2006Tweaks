#!/usr/bin/env python3
"""B307 C325 q212 three SELECT headings: full native heavy gray glyph master.

C325 queue REWORK_REQUIRED triage-token normalization verified before rerun.

Only region IDs 25/26/27 independently returned by C325. Other nine
sprites including B299 15/28 and unrelated approved/protected artwork must
remain exact. C2/C3/user remain open.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics");REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
OUT=G/"role_B/20261009-B307-Q212-C325-THREE-NATIVE-SELECT-HEADINGS";OUT.mkdir(parents=True,exist_ok=True)
h=lambda x:hashlib.sha256(x).hexdigest()
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
OLD="efe1750f9cd9d20a147c96fdf20aa729667a93a9982e5d932e645ac2dfc3b089"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212","--require-safe-rerender"],text=True,capture_output=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="212")
assert "rework_required" in row["artwork_status"]
b=(G/"hd_candidates"/REL).read_bytes()
assert h(b)==OLD,"concurrent q212 producer changed current candidate; refuse stale edit"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
with urllib.request.urlopen(url,timeout=160) as response:src=response.read()
assert h(src)==SOURCE and src[:128]==b[:128]
def decoded(buf):
 a=np.array(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(2048,2048,4);return a
S=decoded(src);P=decoded(b)
C=np.array(Image.open(G/"role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
evidence=json.loads((G/"role_C/20261009-C325-C2-Q212-TEN-PRESERVED-NATIVE/C325_MACHINE_FULL_12.json").read_text())
assert evidence["source_sha256"]==SOURCE and evidence["candidate_sha256"]==OLD
rows=evidence["regions"];assert len(rows)==12
assert all(not np.any(C[y:y2,x:x2,3]) for x,y,x2,y2 in (z["bbox"] for z in rows))
allregions=np.zeros((2048,2048),bool)
for z in rows:
 x,y,x2,y2=z["bbox"];allregions[y:y2,x:x2]=True
assert not np.any(np.any(S!=C,axis=2)&~allregions),"source CLEAN mismatch outside allowed union"
font="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(font).exists():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
assert Path(font).exists(),"native sans black unavailable"
ids=[25,26,27];expect={25:("별자리 선택","SELECT STAR SIGN",[0,788,726,860]),
 26:("사진 선택","SELECT PHOTO",[0,692,566,758]),
 27:("국적 선택","SELECT NATIONALITY",[1,604,845,670])}
out=P.copy();allowed=np.zeros((2048,2048),bool);details=[]
for z in rows:
 n=z["idx"]
 if n not in ids:continue
 ko,en,bb=expect[n];assert z["korean"]==ko and z["label"]==en and z["bbox"]==bb
 l,t,r,b2=bb;allowed[t:b2,l:r]=True
 src_roi=S[t:b2,l:r]
 # Dark source is uniformly flat CJK-control heading family, not metallic.
 face=src_roi[(src_roi[:,:,3]>230)]
 assert len(face)>2000 and np.median(face[:,0])<130
 median=np.median(face,axis=0).round().astype(int).tolist()
 assert median[3]==255 and max(median[:3])-min(median[:3])<28
 # choose native near source height; use heavy sans with source dark gray.
 choice=None
 for size in range(92,53,-1):
  ft=ImageFont.truetype(font,size,index=1)
  anchor=ft.getbbox(ko)
  im=Image.new("RGBA",(anchor[2]-anchor[0]+20,anchor[3]-anchor[1]+20),(0,0,0,0))
  ImageDraw.Draw(im).text((10-anchor[0],10-anchor[1]),ko,font=ft,fill=tuple(median))
  bbink=im.getchannel("A").getbbox()
  if not bbink:continue
  glyph=im.crop(bbink)
  if glyph.height <= (b2-t)-10 and glyph.height >= (b2-t)-16 and glyph.width<r-l-12:
   choice=(size,glyph);break
 assert choice is not None,("cannot fit native target height",n)
 size,glyph=choice
 # Header is left-aligned (native source), preserve original source grouping.
 xx=l+5;yy=t+((b2-t)-glyph.height)//2
 assert min(xx-l,r-xx-glyph.width,yy-t,b2-yy-glyph.height)>=4
 out[t:b2,l:r]=C[t:b2,l:r]
 imarr=np.asarray(glyph,dtype=np.uint8)
 assert not np.any(out[yy:yy+glyph.height,xx:xx+glyph.width,3])
 out[yy:yy+glyph.height,xx:xx+glyph.width]=imarr
 details.append({"region_idx":n,"source":en,"korean":ko,"source_bbox":bb,
  "new_bbox":[xx,yy,xx+glyph.width,yy+glyph.height],
  "margin":[xx-l,r-xx-glyph.width,yy-t,b2-yy-glyph.height],
  "source_face":median,"font":"NotoSansCJK-Black.ttc","native_px":size,
  "native_glyph_width":glyph.width,"native_glyph_height":glyph.height})
changed=np.any(out!=P,axis=2)
assert np.count_nonzero(changed)>1000
assert not np.any(changed&~allowed)
assert not np.any((out[:,:,3]!=P[:,:,3])&~allowed)
assert np.array_equal(out[~allowed],P[~allowed])
assert all(r["region_idx"] in ids for r in details)
native=np.frombuffer(src[128:],dtype=np.uint8).reshape(2048,2048,4)
if np.array_equal(native[::-1],S):mode="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(native[::-1,:,[2,1,0,3]],S)
 mode="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
data=b[:128]+body;assert h(data)!=OLD and len(data)==len(b)
D=decoded(data);assert np.array_equal(D,out)
newpath=G/"hd_candidates"/REL;newpath.write_bytes(data)
assert h(newpath.read_bytes())==h(data)
def onbg(a,bg):
 im=Image.new("RGBA",(a.shape[1],a.shape[0]),tuple(bg)+(255,))
 im.alpha_composite(Image.fromarray(a,"RGBA"));return im.convert("RGB")
proof=[]
for n in ids:
 z=next(r for r in rows if r["idx"]==n)
 l,t,r,b2=z["bbox"];tiles=[a[t:b2,l:r].copy() for a in (S,C,P,D)]
 for orientation in ("FLIPY","RAW"):
  imgs=[np.flipud(q).copy() for q in tiles] if orientation=="RAW" else tiles
  for name,bg in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
   for size in (100,75,50):
    parts=[onbg(v,bg) for v in imgs]
    if size!=100:parts=[im.resize((round(im.width*size/100),round(im.height*size/100)),Image.Resampling.LANCZOS) for im in parts]
    contact=Image.new("RGB",(sum(im.width for im in parts)+12,max(im.height for im in parts)),bg)
    x=0
    for part in parts:contact.paste(part,(x,0));x+=part.width+4
    namefile=f"r{n}_{orientation}_{name}_{size}_SOURCE_CLEAN_OLD_NEW.png"
    contact.save(OUT/namefile,optimize=True);proof.append(namefile)
 for name,arr in [("SOURCE",S),("CLEAN",C),("OLD",P),("NEW",D)]:
  Image.fromarray(arr[t:b2,l:r],"RGBA").save(OUT/f"r{n}_{name}_NATIVE_RGBA.png",optimize=True)
 Image.fromarray(np.uint8(changed[t:b2,l:r])*255,"L").save(OUT/f"r{n}_DIFF_MASK.png")
qa={"role":"B","run":"B307","queue_index":212,"source_sha256":SOURCE,"previous_sha256":OLD,
 "candidate_sha256":h(data),"new_dds":1,"source_clean_outside_all_twelve":0,
 "SOURCE_CLEAN_selected_alpha":"ZERO_3","outside_3_changed_rgba":0,"outside_3_changed_alpha":0,
 "preserved_other_9_source_cells":"EXACT_PERSISTED_RGBA","header_exact":True,
 "dds_native":[2048,2048],"dds_format":mode,"mips":1,"saved_dds_decode":"EXACT",
 "raw_orientation":"mirror_y","regions":details,"proofs":proof,
 "method":"native heavy flat gray Noto Black at actual source height, no old bitmap upscale",
 "producer_visual":"PENDING_DIRECT_100_75_50_RAW","C2":"NOT_RUN","C3":"NOT_RUN",
 "IGR029":"OPEN_MAPPING_SUSPECTED","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"github-actions","excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B307_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B307_NEW_DDS",json.dumps({"sha":h(data),"details":details,"proofs":len(proof)},ensure_ascii=False))
