#!/usr/bin/env python3
"""B329 C327 q212 PROFESSIONAL full-term source-hierarchy reconstruction.

Source-native gray/orange/red family sampling and preserved recent B307 repairs.

C327 independently rejected B308 id43 "프로" at 120px of source 638px.
Repair only id43 using full transliteration, preserve all other eleven
regions exactly, publish trial and inspect before separate promotion.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics");REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
OUT=G/"role_B/20261009-B329-Q212-PROFESSIONAL-SOURCE-ANCHOR";OUT.mkdir(parents=True,exist_ok=True)
h=lambda x:hashlib.sha256(x).hexdigest()
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
OLD="209f8358c8f7a6ce88d54dfd0b39f3b6051e6a055f83db84dbeaa8f5dd97e74e"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212","--require-safe-rerender"],text=True,capture_output=True,check=True)
action=json.loads(tri.stdout)["assets"][0]
assert action["next_action"] in ("MATERIAL_REWORK","NORMAL_QUEUE_SELECTION"),action
c327=json.loads((G/"role_C/20261009-C327-C2-Q212-Q228-VISUAL/C327_Q212_B308_SOURCE_HIERARCHY_REWORK.json").read_text())
assert c327["decision"]=="REWORK_REQUIRED" and c327["queue_index"]==212
assert c327["new_candidate_sha256"]==OLD
assert any(x["region_id"]==43 and x["decision"]=="REWORK_REQUIRED" for x in c327["observed_regions"])
assert action["current_status"]=="c327_c2_b308_visual_rework_professional_underfill_igr029_open",action
# The read-only triage parser currently misses C327's status spelling; exact
# independent C2 decision + source SHA supersede that lexical false negative.
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="212")
assert "rework" in row["artwork_status"]
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
assert evidence["source_sha256"]==SOURCE and evidence["candidate_sha256"]=="efe1750f9cd9d20a147c96fdf20aa729667a93a9982e5d932e645ac2dfc3b089"
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
ids=[43]
expect={
 30:("완료","DONE",[1080,423,1274,496],"gray","left"),
 43:("프로페셔널","PROFESSIONAL",[0,341,638,404],"orange","left"),
 44:("아웃런","OUTRUN",[1626,524,1837,587],"red","right"),
 53:("완료","DONE",[4,78,138,122],"gray","left")}
out=P.copy();allowed=np.zeros((2048,2048),bool);details=[]
for z in rows:
 n=z["idx"]
 if n not in ids:continue
 ko,en,bb,family,alignment=expect[n];assert z["korean"]==("프로" if n==43 else ko) and z["label"]==en and z["bbox"]==bb
 l,t,r,b2=bb;allowed[t:b2,l:r]=True
 src_roi=S[t:b2,l:r]
 # Dark source is uniformly flat CJK-control heading family, not metallic.
 face=src_roi[(src_roi[:,:,3]>230)]
 assert len(face)>500,("source face missing",n)
 median=np.median(face,axis=0).round().astype(int).tolist()
 assert median[3]==255
 if family=="gray": assert median[0]<130 and max(median[:3])-min(median[:3])<35,(n,median)
 elif family=="orange": assert median[0]>160 and median[1]>75 and median[2]<150,(n,median)
 elif family=="red": assert median[0]>120 and median[1]<75 and median[2]<75,(n,median)
 # choose native near source height; use heavy sans with source dark gray.
 choice=None
 for size in range(100,24,-1):
  ft=ImageFont.truetype(font,size,index=1)
  anchor=ft.getbbox(ko)
  track=16 if n==43 else 0  # Original PROFESSIONAL source spans 638px in uppercase.
  im=Image.new("RGBA",(anchor[2]-anchor[0]+20+track*max(0,len(ko)-1),anchor[3]-anchor[1]+20),(0,0,0,0))
  pen=ImageDraw.Draw(im)
  px=float(10-anchor[0])
  for ch in ko:
   pen.text((round(px),10-anchor[1]),ch,font=ft,fill=tuple(median))
   px+=ft.getlength(ch)+track
  bbink=im.getchannel("A").getbbox()
  if not bbink:continue
  glyph=im.crop(bbink)
  if glyph.height <= (b2-t)-8 and glyph.height >= (b2-t)-13 and glyph.width<r-l-10:
   choice=(size,glyph);break
 assert choice is not None,("cannot fit native target height",n)
 size,glyph=choice
 assert n!=43 or glyph.width>=300,("still underfilling source hierarchy",glyph.width)
 # C327: original letter bbox starts at x0, so retain source leading anchor.
 xx=l+5 if n==43 else ((r-5-glyph.width) if alignment=="right" else l+5)
 assert n!=43 or xx-l==5,("source left-anchor not preserved",xx,l)
 yy=t+((b2-t)-glyph.height)//2
 assert min(xx-l,r-xx-glyph.width,yy-t,b2-yy-glyph.height)>=4
 out[t:b2,l:r]=C[t:b2,l:r]
 imarr=np.asarray(glyph,dtype=np.uint8)
 assert not np.any(out[yy:yy+glyph.height,xx:xx+glyph.width,3])
 out[yy:yy+glyph.height,xx:xx+glyph.width]=imarr
 details.append({"region_idx":n,"source":en,"korean":ko,"source_bbox":bb,
  "new_bbox":[xx,yy,xx+glyph.width,yy+glyph.height],
  "margin":[xx-l,r-xx-glyph.width,yy-t,b2-yy-glyph.height],
  "source_face":median,"source_family":family,"alignment":alignment,"font":"NotoSansCJK-Black.ttc","native_px":size,
  "native_glyph_width":glyph.width,"native_glyph_height":glyph.height,"source_derived_uppercase_tracking_px":(16 if n==43 else 0)})
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
newpath=OUT/"B329_UNAPPROVED_PROFESSIONAL_HIERARCHY_TRIAL.dds";newpath.write_bytes(data)
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
qa={"role":"B","run":"B329","queue_index":212,"source_sha256":SOURCE,"previous_sha256":OLD,
 "candidate_sha256":h(data),"new_dds":0,"unapproved_trial_dds":1,"source_clean_outside_all_twelve":0,
 "SOURCE_CLEAN_selected_alpha":"ZERO_1","outside_1_changed_rgba":0,"outside_1_changed_alpha":0,
 "preserved_other_11_source_cells":"EXACT_PERSISTED_RGBA","header_exact":True,
 "dds_native":[2048,2048],"dds_format":mode,"mips":1,"saved_dds_decode":"EXACT",
 "raw_orientation":"mirror_y","regions":details,"proofs":proof,
 "method":"native full Korean PROFESSIONAL glyph from source orange face, source-leading left anchor matched at x+5, original bbox and other 11 regions strictly pixel exact; no bitmap stretching",
 "producer_visual":"PENDING_DIRECT_100_75_50_RAW","initial_state":"TRIAL_NOT_PROMOTED","C2":"NOT_RUN","C3":"NOT_RUN",
 "IGR029":"OPEN_MAPPING_SUSPECTED","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"github-actions","excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B329_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B329_TRIAL_DDS",json.dumps({"sha":h(data),"details":details,"proofs":len(proof)},ensure_ascii=False))
