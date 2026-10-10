#!/usr/bin/env python3
"""B345 q176: fresh native Hangul red-block source-family font construction.

A material TRIAL only; full persisted DDS, source->CLEAN->LETTERING->FINAL,
protected outside pixel proofs, raw and 100/75/50 readable visual exports.
Never change approved hd_candidates before independent direct producer review.
"""
import hashlib,io,json,os,struct,sys,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTCollection
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B345-Q176-SOURCE-HEAVY-RED-FONT-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE_SHA="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
CURRENT_SHA="494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407"
q=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","176"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert q["next_action"]=="MATERIAL_REWORK",q
assert subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","176","--require-safe-rerender"],stdout=subprocess.DEVNULL).returncode==0
prior=json.loads((G/"role_C/20261010-C343-C2-Q176-OPTICAL-SOURCE-FAMILY/C343_Q176_CONTROLLER_C2_REWORK.json").read_text())
assert prior["decision"]=="REWORK_REQUIRED" and prior["candidate_sha256"]==CURRENT_SHA and prior["source_sha256"]==SOURCE_SHA
cp=G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
current=cp.read_bytes()
sp=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
if sp.is_file():source=sp.read_bytes()
else:
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
 with urllib.request.urlopen(url,timeout=120) as f: source=f.read()
assert sha(current)==CURRENT_SHA and sha(source)==SOURCE_SHA
assert len(source)==len(current)==16777344 and source[:128]==current[:128] and struct.unpack_from("<II",source,12)==(2048,2048)
masks=struct.unpack_from("<IIII",source,92)
assert masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),masks
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(source);O=dec(current)
assert S.shape==O.shape==(2048,2048,4)
regions=[
 ("jennifer","JENNIFER","제니퍼",(0,374,838,532)),
 ("clarissa","CLARISSA","클라리사",(905,372,1745,532)),
 ("holly","HOLLY","홀리",(9,213,542,364)),
 ("flagman4","FLAGMAN 4","플래그맨 4",(8,49,988,204))]
# P1: exact source-derived clean transparent plate, no adapted Korean crop.
C=S.copy()
scope=np.zeros(S.shape[:2],bool)
for _,_,_,(x0,y0,x1,y1) in regions:
 assert not np.any(scope[y0:y1,x0:x1])
 scope[y0:y1,x0:x1]=True
 C[y0:y1,x0:x1]=0
assert np.all(C[scope,3]==0)
assert np.array_equal(S[~scope],C[~scope])
# Source and saved candidate preserve unrelated ??? and route art exactly.
assert np.array_equal(S[~scope],O[~scope]),"old candidate has unrelated source artwork modifications"
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")
assert fontp.is_file(), "The exact Black face must exist; no hidden fallback"
fb=fontp.read_bytes()
faces=TTCollection(str(fontp))
assert len(faces.fonts)>1
fontindex=1 # Korean CJK face
for _,_,word,_ in regions:
 cmap=faces.fonts[fontindex].getBestCmap()
 assert all(ord(z) in cmap for z in word if not z.isspace()),word
# Source flat-family RGBA opaque pixels: native red faces. Source median is
# measured per region. No artwork-color interpolation or arbitrary bevel.
L=np.zeros_like(S)
rows=[]
for name,eng,kor,(x0,y0,x1,y1) in regions:
 w,h=x1-x0,y1-y0
 srcroi=S[y0:y1,x0:x1]; oldroi=O[y0:y1,x0:x1]
 selected=srcroi[:,:,3]>245
 assert selected.sum()>10000,(name,selected.sum())
 rgb=np.median(srcroi[selected,:3],axis=0).astype(np.uint8)
 # Pinned English pixel samples should be flat red, not a blue/chrome case.
 assert rgb[0]>150 and rgb[1]<25 and rgb[2]<25,(name,rgb.tolist())
 target_h=h-10
 stroke=3  # PIL FreeType vector glyph stroke; NOT post-render dilation
 best=None
 for size in range(100,260):
  f=ImageFont.truetype(str(fontp),size,index=fontindex)
  b=ImageDraw.Draw(Image.new("L",(1,1))).textbbox((0,0),kor,font=f,stroke_width=stroke)
  tw,th=b[2]-b[0],b[3]-b[1]
  if th<=target_h and tw<=w-10 and (best is None or th>best[2]):
   best=(size,tw,th,b)
 assert best is not None,(name,"no source-safe font size")
 size,tw,th,bb=best
 xpad=max(4,min(8,w-tw-4))
 ypad=(h-th)//2
 assert xpad>0 and ypad>=4 and xpad+tw<w and ypad+th<h-3
 f=ImageFont.truetype(str(fontp),size,index=fontindex)
 mask=Image.new("L",(w,h),0)
 ImageDraw.Draw(mask).text((xpad-bb[0],ypad-bb[1]),kor,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
 alpha=np.array(mask)
 nz=np.nonzero(alpha)
 bx=(int(nz[1].min()),int(nz[0].min()),int(nz[1].max()+1),int(nz[0].max()+1))
 assert bx[0]>=3 and bx[1]>=3 and bx[2]<=w-3 and bx[3]<=h-3,(name,bx)
 pix=np.zeros((h,w,4),dtype=np.uint8)
 pix[:,:,:3]=rgb;pix[:,:,3]=alpha
 pix[alpha==0]=0
 L[y0:y1,x0:x1]=pix
 rows.append({"id":name,"english":eng,"korean":kor,"source_bbox":[x0,y0,x1,y1],
 "source_median_rgba":[*map(int,rgb),255],"font_size_px":size,"native_stroke_width":stroke,
 "native_lettering_bbox":[x0+bx[0],y0+bx[1],x0+bx[2],y0+bx[3]],
 "source_size_ceiling":[w,h],"final_size":[bx[2]-bx[0],bx[3]-bx[1]],
 "four_margins":[bx[0],w-bx[2],bx[1],h-bx[3]],
 "source_alpha_positive":int((srcroi[:,:,3]>0).sum()),
 "current_alpha_positive":int((oldroi[:,:,3]>0).sum()),"new_alpha_positive":int((alpha>0).sum())})
F=C.copy();F[scope]=L[scope]
assert np.array_equal(F[~scope],O[~scope])
assert np.array_equal(F[~scope],S[~scope])
assert np.array_equal(C[scope],np.zeros_like(C[scope]))
assert np.array_equal(F[scope],L[scope])
assert all(min(z["four_margins"])>=3 for z in rows)
# Current and source have zero unrelated edits, persisted encoding exact.
order=[0,1,2,3] if masks[0]==255 else [2,1,0,3]
output=current[:128]+np.flipud(F)[:,:,order].copy().tobytes()
assert len(output)==len(current) and np.array_equal(dec(output),F)
outdds=OUT/"B345_Q176_NATIVE_BLACK_SOURCE_FAMILY_UNAPPROVED.dds"
outdds.write_bytes(output)
for name,arr in (("P1_CLEAN_SOURCE_ONLY",C),("P2_TRANSPARENT_LETTERING_ONLY",L)):
 Image.fromarray(arr,"RGBA").save(OUT/(f"B345_{name}.png"),optimize=True)
Image.fromarray((scope*255).astype(np.uint8),"L").save(OUT/"B345_SOURCE_BOUNDED_PROTECTED_UNION_MASK.png")
views=[]
def flat(arr,bg):
 x=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg+(255,))
 x.alpha_composite(Image.fromarray(arr,"RGBA"))
 return x.convert("RGB")
for name,eng,kor,(x0,y0,x1,y1) in regions:
 for orientation in ("FLIPY","RAW"):
  for bgname,bg in (("GRAY",(128,128,128)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
   for pct in (100,75,50):
    imgs=[flat(z[y0:y1,x0:x1],bg) for z in (S,C,O,F)]
    if orientation=="RAW":imgs=[z.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for z in imgs]
    if pct!=100:imgs=[z.resize((round(z.width*pct/100),round(z.height*pct/100)),Image.Resampling.LANCZOS) for z in imgs]
    w,h=imgs[0].size
    view=Image.new("RGB",(w*4+18,h),bg)
    for i,im in enumerate(imgs):view.paste(im,(i*(w+6),0))
    fn=f"B345_{name}_{orientation}_{bgname}_{pct}_SOURCE_CLEAN_OLD_NEW.png"
    view.save(OUT/fn,optimize=True);views.append(fn)
qa={"run":"B345","role":"B","queue_index":176,
"run_key":"OUTRUN-KOR-B345-Q176-HEAVY-SOURCE-BLOCK-GLYPH-20261010",
"source_sha256":SOURCE_SHA,"current_candidate_sha256":CURRENT_SHA,
"new_trial_sha256":sha(output),"new_trial_bytes":len(output),
"format":"RGBA32","native":[2048,2048],"mips":1,
"source_clean_lettering_final":True,"P1":"MECHANICAL_SOURCE_CLEAN_CANDIDATE_SAVED_DIRECT_CONTROLLER_VISUAL_PENDING",
"P2":"NATIVE_FONT_BLACK_VECTOR_WITH_SOURCE_FLAT_RED_FACE_DIRECT_CONTROLLER_VISUAL_PENDING",
"P3":"DDS_ROUNDTRIP_EXACT_NO_OFFICIAL_PROMOTION",
"source_clean_outside_rgba":0,"clean_final_outside_rgba":0,
"source_final_outside_rgba":0,"prior_final_outside_rgba":0,
"protected_unchanged":True,"zero_source_alpha_in_4_clean":True,
"font_sha256":sha(fb),"font_path":str(fontp),"font_face_index":fontindex,
"font_license":"fonts-noto-cjk packaged OFL: /usr/share/doc/fonts-noto-cjk/copyright",
"glyph_coverage_all":True,"native_font_raster_not_resized":True,
"per_region":rows,"comparisons":views,
"same_SHA_repeated":False,"producer_visual":"PENDING_DIRECT_CONTROLLER",
"new_material_trial_dds":1,"new_promoted_dds":0,
"C2":"C343_CURRENT_REWORK_REQUIRED","C3":"BLOCKED",
"APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED",
"backend":"GITHUB_ACTIONS_CPU_WORKER","exclusions":["ODD_A","C1","VR","FFB","DX11","DXVK"]}
(OUT/"B345_MECHANICAL_AND_SOURCE_PLATE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({
"family":"red-flat-heavy-block-menu","source_sha256":SOURCE_SHA,
"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
"protected":"Entire unedited atlas including original ??? and route",
"source_regions":rows,"font_sha256":sha(fb),"font_face_index":fontindex,
"stroke_width":3,"render_method":"Pillow native font Black FreeType face; source sampled per-region face color; no resize or fallback",
"earlier_reject":"C343 optical source red-block face visibly thicker than B201 saved",
"source_to_clean":"zero exact canonical English source bboxes, preserve outside",
"clean_to_final":"replace each clean bbox with isolated native glyph pixels",
"RAW_FLIPY":"same exact source/current mirror-Y orientation",
"producer":"UNAPPROVED TRIAL / visual self-QA pending","runtime":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print("B345_TRIAL",sha(output),[(z["id"],z["font_size_px"],z["final_size"],z["four_margins"]) for z in rows],flush=True)
