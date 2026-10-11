#!/usr/bin/env python3
"""B366 q176 P3 saved DDS from reviewed source-conditioned stroke graph.

Stage 1 created native handwritten Hangul outlines and retained source "4".
The controller directly inspected 100% gray, 50% black and RAW comparison
before allowing GEOMETRY_READY in this stage. This remains UNAPPROVED C2/C3.
"""
import os,sys,io,hashlib,json,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
H=lambda b:hashlib.sha256(b).hexdigest()
R=Path(".").resolve()
G=Path("localization/graphics")
P=G/"role_B/20261011-B366-Q176-SOURCE-NUMERAL-MANUAL-STROKES"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
source_sha="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
clean_sha="29e77ca7391022eff23b84a197a41c123938f3aa03a6fb7c69a783d0ce0b6ebe"
official_sha="494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407"
old=(G/"hd_candidates"/asset).read_bytes()
assert H(old)==official_sha,("OFFICIAL_CONCURRENT_CHANGE",H(old))
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","176"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
with urllib.request.urlopen(url,timeout=90) as f: sb=f.read()
assert H(sb)==source_sha and old[:128]==sb[:128] and len(old)==len(sb)==16777344
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(sb);O=dec(old)
cleanpath=G/"role_B/20261010-B346-Q176-SOURCE-HEAVY-RED-FONT-PILOT/B346_P1_CLEAN_SOURCE_ONLY.png"
cb=cleanpath.read_bytes()
assert H(cb)==clean_sha
C=np.array(Image.open(io.BytesIO(cb)).convert("RGBA"))
simg=(P/"SOURCE_RAW_RGBA.png").read_bytes()
saved_raw=np.array(Image.open(io.BytesIO(simg)).convert("RGBA"))
assert np.array_equal(saved_raw,S[::-1]),"CANONICAL_SOURCE_REFERENCE_MUTATED"
x0,y0,x1,y1=8,49,988,204
assert np.count_nonzero(C[y0:y1,x0:x1,3])==0
proposal=json.loads((P/"B366_GEOMETRY_PROPOSAL.json").read_text())
assert proposal["source_bbox"]==[8,49,988,204] and proposal["source_number_component_relative"]==[870,980]
def ref(path):
 b=Path(path).read_bytes()
 return {"path":Path(path).as_posix(),"sha256":H(b)}
refs={
 "source":ref(P/"SOURCE_RAW_RGBA.png"),
 "geometry":ref(P/"GEOMETRY_RAW_ALPHA.png"),
 "face":ref(P/"FACE_RAW_RGBA.png"),
 "geometry_recipe":ref("tools/localization/recipes/B366_q176_manual_stroke_graph.py"),
 "native":ref(P/"B366_SOURCE_CLEAN_OLD_MANUAL_FLIPY_BG128_100.png"),
 "practical":ref(P/"B366_SOURCE_CLEAN_OLD_MANUAL_FLIPY_BG0_50.png"),
 "raw":ref(P/"B366_SOURCE_CLEAN_OLD_MANUAL_RAW_BG128_100.png")
}
# Geometry was viewed firsthand by the controller AFTER stage1 output. Producer
# decision is scoped P2 only, independent C2/C3 and actual-game still absent.
rev={
 "status":"GEOMETRY_READY","reviewer":"B","route":"vector_title",
 "source_sha256":refs["source"]["sha256"],
 "geometry_sha256":refs["geometry"]["sha256"],
 "canonical_source_dds_sha256":source_sha,"index":176,"region":"FLAGMAN_4",
 "firsthand_visual_review":"2026-10-11 09:40 KST, saved Stage1 four-column native-gray100, black50 and RAW100 controller read; new manual block-type Hangul legible, numeral 4 visually source-matched and unmodified; potential geometric stiffness retained for independent C2.",
 "observations":{
 "stroke":"Manual individually authored 3x antialias native square red Hangul strokes (approx 18-23px at actual 150px source height); source English thick solid deep-red racing family, improved fill/hierarchy vs B365 thin glyph, C2 must qualify native source stem equivalents.",
 "counterspace":"Visible independent counters in 래 and 맨; consonant 플 has dense stacked horizontals, no observed hard clipping at saved native/black50 but C2 can reject if structure is malformed.",
 "proportions":"Source full FLAGMAN 4 height155,width980; candidate proposal bbox [29,54,988,204], glyphs distributed across source width rather than B365 706px, 8,928 original numeric visible pixels preserved.",
 "slant":"Source label appears upright; proposed Hangul also upright with square stems; homologous top-minus-bottom calibration unresolved, no fabricated numeric slope.",
 "readability":"Source/clean/old/new native gray100 and black50 first-hand readable; producer P2 scoped only, final DDS/AA/RAW still to verify."},
 "evidence":[refs["native"],refs["practical"],refs["raw"]],
 "limitations":"P2 source-family conditional; not final C PASS/C3/real-game. No promotion if post-DDS visual shows malformed glyph."
}
review_path=P/"B366_GEOMETRY_REVIEW.json"
review_path.write_text(json.dumps(rev,ensure_ascii=False,indent=2)+"\n")
recipe={"version":"separated-lettering-v1","coordinates":"native_raw","route":"vector_title",
 "source":refs["source"],"geometry":refs["geometry"],
 "geometry_recipe":refs["geometry_recipe"],
 "geometry_review":ref(review_path),
 "layers":[{"role":"face","input":refs["face"]}]}
recipe_path=P/"B366_LETTERING_RECIPE.json"
recipe_path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n")
sys.dont_write_bytecode=True  # Keep CPU worker output in role_B only; no __pycache__ outside boundary.
sys.path.insert(0,str(Path("tools/localization").resolve()))
from compose_lettering import compose
lettering,comp=compose(R,recipe)
lettering_path=P/"B366_COMPOSED_LETTERING_RAW_RGBA.png"
lettering.save(lettering_path)
L=np.array(lettering)[::-1].copy()
assert L.shape==(2048,2048,4)
assert np.array_equal(L[:,:,3],np.array(Image.open(P/"GEOMETRY_RAW_ALPHA.png"))[::-1])
N=O.copy()
N[y0:y1,x0:x1]=L[y0:y1,x0:x1]
# Source-number original 4 exact native visible RGB+alpha including AA.
a=S[y0:y1,878:988];n=N[y0:y1,878:988]
visible=a[:,:,3]>0
assert np.array_equal(a[visible],n[visible]),"ORIGINAL_NUMERAL_NOT_PRESERVED"
allow=np.zeros((2048,2048),bool);allow[y0:y1,x0:x1]=True
chg=np.any(N!=O,axis=2)
assert int(np.count_nonzero(chg&~allow))==0, "PROTECTED_OUTSIDE_CHANGE"
b=old[:128]+N[::-1].tobytes()  # original DDS RGBA32 0x00ff0000 B mask
ddspath=P/"B366_Q176_MANUAL_SOURCE_DIGIT_UNAPPROVED.dds"
ddspath.write_bytes(b)
D=dec(ddspath.read_bytes())
assert np.array_equal(D,N) and ddspath.stat().st_size==16777344
assert np.count_nonzero(np.any(D!=O,axis=2)&~allow)==0
# Re-derive optical bounding and exact original-derived ceiling from SAVED.
loc=np.argwhere(D[y0:y1,x0:x1,3]>0)
mn=loc.min(axis=0);mx=loc.max(axis=0)+1
bbox=[x0+int(mn[1]),y0+int(mn[0]),x0+int(mx[1]),y0+int(mx[0])]
assert bbox==proposal["new_bbox"]==[29,54,988,204]
# Native100, practical75/50, RAW rebuilt from actual saved DDS bytes, not
# unsaved renderer intent.
ev={}
for orient in ["FLIPY","RAW"]:
 for bg,pct in ([(128,100),(255,75),(0,50)] if orient=="FLIPY" else [(128,100)]):
  imgs=[]
  for a in ([S,C,O,D] if orient=="FLIPY" else [v[::-1] for v in [S,C,O,D]]):
   yy0,yy1=(y0-4,y1+4) if orient=="FLIPY" else (2048-y1-4,2048-y0+4)
   im=Image.fromarray(a[yy0:yy1,x0-4:x1+4].copy(),"RGBA")
   back=Image.new("RGBA",im.size,(bg,bg,bg,255));back.alpha_composite(im)
   z=back.convert("RGB")
   if pct!=100:z=z.resize((z.width*pct//100,z.height*pct//100),Image.Resampling.LANCZOS)
   imgs.append(z)
  w,h=imgs[0].size;sheet=Image.new("RGB",(w*4+30,h),(bg,bg,bg))
  for i,im in enumerate(imgs):sheet.paste(im,(i*(w+10),0))
  name=f"B366_SAVED_SOURCE_CLEAN_OFFICIAL_MANUAL_{orient}_BG{bg}_{pct}.png"
  sheet.save(P/name)
  ev[name]=H((P/name).read_bytes())
report={
 "run":"B366","role":"B","queue_index":176,"method":"native manually authored 4-Hangul source block-stroke graphs + 8928 original numeral 4 visible source pixels, separated face-only geometry composition",
 "original_dds_sha":source_sha,"plate_sha":clean_sha,"official_unchanged_sha":official_sha,
 "saved_unapproved_dds_sha":H(b),"geometry_sha":refs["geometry"]["sha256"],"lettering_sha":H(lettering_path.read_bytes()),
 "lettering_recipe":ref(recipe_path),"geometry_review":ref(review_path),"source_bbox":[x0,y0,x1,y1],
 "result_bbox":bbox,"source_numeral_visible_exact":int(np.count_nonzero(visible)),
 "native_size":[2048,2048],"format":"RGBA32","mips":1,"raw":"MIRROR_Y",
 "changed_inside_source_bbox":int(chg.sum()),"outside_changed":0,"protected_other3":"EXACT_UNCHANGED",
 "saved_dds_roundtrip_rgba_difference":0,"source_digit_visible_changed":0,"source_clean_alpha_residue":0,
 "new_trial_dds":1,"official_promoted":0,"P2":"GEOMETRY_READY_SCOPED_FIRST_HAND",
 "P3":"PERSISTED_PIXEL_EXACT_PENDING_CONTROLLER_VISUAL",
 "C2":"NOT_RUN","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "images":ev,"compose":comp,"excluded":["VR","FFB","DX11","DXVK"]
}
(P/"B366_PERSISTED_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B366","new_sha":H(b),"changed":int(chg.sum()),"number_original":int(np.count_nonzero(visible)),"roundtrip":0},ensure_ascii=False),flush=True)
