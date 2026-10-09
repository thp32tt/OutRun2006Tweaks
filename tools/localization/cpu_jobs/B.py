#!/usr/bin/env python3
"""B335 q060 P0: source-derived full-native PLATE guard and protected recipe.

C334 independently verified the entire canonical English DDS and saved B332R
q060, but only a cropped source/CLEAN protection proof. This is a substantive
P1 production-gate task on already-promoted exact bytes, NOT another DDS.
Fail closed if the authentic source/previous/current or original BEST orange
protected mask disagree. P2 family slant and P3 publication remain pending.
"""
import csv,hashlib,io,json,os,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
SRC=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
CAND=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
BASE_REF="e34eab0b1ff22a3cb448bd0e35f8e26e0bd803c8"
SRC_HASH="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
PREV_HASH="3480bef0369677d9e0b8d3d7b334d6a261de7bc2539c225a939843325a3e36a2"
FINAL_HASH="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
RUN="OUTRUN-KOR-B335-Q060-FULL-NATIVE-SOURCE-PLATE-P1-20261009-2310"
OUT=G/"role_B/20261009-B335-Q060-SOURCE-PLATE-P1-GUARD";OUT.mkdir(parents=True,exist_ok=True)
h=lambda x:hashlib.sha256(x).hexdigest()
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="60")
assert row["artwork_status"].startswith("c334_c2_hold_independent_canonical_source_authenticated"),row["artwork_status"]
Sbytes=SRC.read_bytes();Fbytes=CAND.read_bytes()
Pbytes=subprocess.check_output(["git","show",BASE_REF+":"+CAND.as_posix()])
assert h(Sbytes)==SRC_HASH and h(Fbytes)==FINAL_HASH and h(Pbytes)==PREV_HASH
assert Sbytes[:128]==Fbytes[:128]==Pbytes[:128] and len(Sbytes)==len(Pbytes)==len(Fbytes)==33554560
def decode(b):
 a=np.asarray(Image.open(io.BytesIO(b)).convert("RGBA"),dtype=np.uint8)
 assert a.shape==(2048,4096,4)
 return np.flipud(a).copy()  # READABLE coordinates, source native RAW mirrored
S=decode(Sbytes);P=decode(Pbytes);F=decode(Fbytes)
W,H=4096,2048
l,t,r,b=2081,230,2860,370
xl,yt,xr,yb=l-24,t-24,r+24,b+30
source_region=S[yt:yb,xl:xr]
Y=np.arange(yt,yb)[:,None]
rr=source_region[:,:,0].astype(np.int32);gg=source_region[:,:,1].astype(np.int32);bb=source_region[:,:,2].astype(np.int32)
orange=(source_region[:,:,3]>90)&(rr>150)&(gg>35)&(bb*100<rr*55)&(rr*100>gg*105)&(Y>=340)
assert int(np.count_nonzero(orange))>=8892,"Unrecognized source BEST artwork"
dilated=binary_dilation(orange,iterations=12)
protect=dilated[t-yt:b-yt,l-xl:r-xl]
orange_local=orange[t-yt:b-yt,l-xl:r-xl]
assert int(np.count_nonzero(orange_local))==8892
C=P.copy()
C[t:b,l:r]=0
C[t:b,l:r][protect]=S[t:b,l:r][protect]
assert np.array_equal(C[t:b,l:r][protect],S[t:b,l:r][protect])
assert np.array_equal(F[t:b,l:r][protect],S[t:b,l:r][protect])
assert not np.any(C[t:b,l:r][~protect,3]),"Source plate not empty outside protected BEST contour"
assert np.array_equal(C[:t],P[:t]) and np.array_equal(C[b:],P[b:])
assert np.array_equal(C[t:b,:l],P[t:b,:l]) and np.array_equal(C[t:b,r:],P[t:b,r:])
# Full-source-derived masks: NOT candidate-difference derived.
edited=np.zeros((H,W),bool);edited[t:b,l:r]=True
protected=np.zeros((H,W),bool);protected[t:b,l:r]=protect
remove=edited & ~protected
restore=protected.copy()
transparent=remove.copy()
assert (edited & protected).sum()==protect.sum()
assert (remove&protected).sum()==0
assert (np.any(S[t:b,l:r,:,] != C[t:b,l:r,:,],axis=2)&protected[t:b,l:r]).sum()==0
# A full-native RAW plate-only production guard is runnable against pinned
# canonical source + exact historical B331 byte baseline, without rewriting
# B332R. All masks are strictly binary L-mode 4096x2048.
def outpng(name,img,mode):
 p=OUT/name
 Image.fromarray(img,mode).save(p,optimize=True)
 return {"path":p.as_posix(),"sha256":h(p.read_bytes())}
def maskpng(name,arr):
 return outpng(name,np.flipud(arr).astype(np.uint8)*255,"L")
clean_ref=outpng("B335_P1_CLEAN_PLATE_FULL_NATIVE_RAW.png",np.flipud(C).copy(),"RGBA")
maskrefs={
 "removal":maskpng("B335_MASK_SOURCE_GOLD_REMOVAL_RAW.png",remove),
 "protected":maskpng("B335_MASK_SOURCE_ORANGE_PROTECTED_RAW.png",protected),
 "edit":maskpng("B335_MASK_SOURCE_BOUNDED_EDIT_RAW.png",edited),
 "transparent":maskpng("B335_MASK_SOURCE_TRANSPARENT_REMOVAL_RAW.png",transparent),
 "restore":maskpng("B335_MASK_SOURCE_ORANGE_EXACT_RESTORE_RAW.png",restore)
}
def bind(path,data,revision=None):
 d={"path":path.as_posix(),"sha256":h(data)}
 if revision:d["git_revision"]=revision
 return d
manifest={
 "version":"production-pixels-v1-20261009","coordinates":"native_raw","stage":"plate",
 "inputs":{"source":bind(SRC,Sbytes),"baseline":bind(CAND,Pbytes,BASE_REF),"clean":clean_ref},
 "masks":maskrefs
}
manifestpath=OUT/"B335_P1_PLATE_MANIFEST.json"
manifestpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
# Python -B prevents bytecode caches outside the GitHub role_B write boundary.
qa_file=OUT/"B335_P1_MACHINE_GUARD.json"
cmd=[sys.executable,"-B","tools/localization/production_pixel_guard.py","--manifest",str(manifestpath),"--report",str(qa_file)]
run=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
assert run.returncode==0,(run.stdout,run.stderr)
guard=json.loads(qa_file.read_text())
assert guard["result"]=="MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED",guard
assert all(v==0 for v in guard["counts"].values()),guard
# New mechanical evidence on full 4096x2048 original/baseline/CLEAN/saved
# atlas -- not merely the pre-existing C334 779x190 source ROI.
stage={
 "run":"B335","run_key":RUN,"queue_index":60,"source_sha256":SRC_HASH,
 "previous_candidate_sha256":PREV_HASH,"current_candidate_sha256":FINAL_HASH,
 "plate_manifest":manifestpath.as_posix(),"plate_guard":qa_file.as_posix(),
 "full_original_native":[4096,2048],"orientation":"SOURCE_AND_CANDIDATE_RAW_MIRROR_Y",
 "source_orange_pixels_exact":int(orange_local.sum()),
 "protected_source_contour_pixels":int(protect.sum()),
 "protected_source_vs_clean_rgba_diff":int(np.any(S[t:b,l:r][protect]!=C[t:b,l:r][protect],axis=1).sum()),
 "protected_source_vs_final_rgba_diff":int(np.any(S[t:b,l:r][protect]!=F[t:b,l:r][protect],axis=1).sum()),
 "P1":"MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED",
 "new_candidate":False,"new_DDS_count":0,
 "C2":"C334_SCOPED_HOLD_UNCHANGED","C3":"PENDING","user_IGR044":"OPEN_USER_INGAME_FAIL",
 "P2_font_style":"NOT_YET_QUALIFIED","P2_slant_top_bottom_anchors":"NOT_YET_MEASURED_DO_NOT_INVENT",
 "P3_final_manifest":"NOT_CREATED_DDS_UNCHANGED",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_ACTIONS","excluded":["VR","FFB","DX11","DXVK"]
}
assert stage["protected_source_vs_clean_rgba_diff"]==stage["protected_source_vs_final_rgba_diff"]==0
# Produce a directly examinable SOURCE / actual CLEAN / old / final, all
# including both GOLD and orange BEST siblings and unmasked adjacent bands.
window=(2070,205,2890,415)
x0,y0,x1,y1=window
proofs=[]
for ori in ("FLIPY","RAW"):
 for bgkey,bg in (("BLACK",(0,0,0)),("GRAY",(84,84,84)),("WHITE",(255,255,255))):
  for pct in (100,75,50):
   imlist=[]
   for arr in (S,C,P,F):
    a=arr[y0:y1,x0:x1]
    if ori=="RAW":a=np.flipud(a)
    img=Image.new("RGBA",(x1-x0,y1-y0),(*bg,255))
    img.alpha_composite(Image.fromarray(a.copy(),"RGBA"))
    if pct<100:img=img.resize((round((x1-x0)*pct/100),round((y1-y0)*pct/100)),Image.Resampling.LANCZOS)
    imlist.append(img.convert("RGB"))
   contact=Image.new("RGB",(sum(z.width for z in imlist)+12,max(z.height for z in imlist)),(84,84,84))
   xx=0
   for z in imlist:contact.paste(z,(xx,0));xx+=z.width+4
   name=f"B335_{ori}_{bgkey}_{pct}_FULL_SOURCE_PLATE_OLD_FINAL.png"
   contact.save(OUT/name,optimize=True);proofs.append(name)
stage["full_adjacent_proofs"]=proofs
# Store source-determined P1 recipe; P2 font hash and anchor evidence are
# deliberately not fabricated. They are explicit blocking requirements.
recipe={
 "schema_version":"production-family-recipe-v1","run_key":RUN,"family":"gold racing HUD title q060",
 "source":{"path":SRC.as_posix(),"sha256":SRC_HASH,"revision":"OR2-HD-GUI-v0.25.10a"},
 "baseline":{"sha256":PREV_HASH,"git_revision":BASE_REF},
 "current":{"sha256":FINAL_HASH,"candidate_path":CAND.as_posix()},
 "all_known_cells":["gold OUTRUN MILES","orange BEST TIME protected sibling","Stage kept outside edit","white Miles kept outside edit","all remaining current translated atlas cells unchanged"],
 "source_text":"OUTRUN MILES","korean_text":"아웃런 마일:",
 "protected_original":"orange BEST TIME color-labeled source + 12px contiguous nearby contour; exact 8892 orange alpha pixels; full-native 4096x2048",
 "native_readable_edit_bbox":[l,t,r,b],"native_readable_original_orange_lower_band_y":340,
 "font_recipe":{"family":"NotoSansCJK Bold used by B331/B332R","font_file":"/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
   "font_sha256":None,"glyph_coverage":"P2_SOURCE_REVALIDATION_REQUIRED_NOT_CONFIRMED_BY_P1",
   "native_size_and_hinting":"B332R inherited glyph reduced from 107px to 97px; further use requires P2 family validation",
   "font_license":"not newly checked by B335; confirm before new render"},
 "geometry":{"original_bbox":[2081,250,2860,370],"gold_relocated_bbox":[2133,235,2807,332],
   "gold_new_height":97,"native_readable_right_italic":"B331 +0.65 forward shear; P2 real top/bottom anchors not yet measured",
   "source_top_bottom_anchors":None,"candidate_top_bottom_anchors":None},
 "render_effect":{"source_samples":"cream/gold face, navy edge (B331 provenance)","gradient":"B331 derived; P2 must validate full glyph weight/counter spacing",
   "outline_shadow":"B331 layered, source style pending C2 qualification"},
 "masks":maskrefs,"source_orange_protected_source_derived":True,
 "intermediate_clean":clean_ref,"plate_manifest":manifestpath.as_posix(),
 "previous_rejections":["C326 SOURCE_FAMILY_MISMATCH/ITALIC_UNDERLEAN","C332 SOURCE_PROTECTED_ART_LOSS"],
 "current_quality_gate":"P1 FULL_NATIVE_SOURCE-DERIVED PLATE MACHINE PASS; direct producer visual pending; C334 C2 HOLD unchanged",
 "P2_status":"BLOCKED_FONT_HASH_AND_SLANT_ANCHOR_VERIFICATION",
 "P3_status":"NOT_RUN_UNCHANGED_PERSISTED_DDS",
 "runtime":"UNTESTED"
}
(OUT/"recipe.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n")
(OUT/"B335_P1_REPORT.json").write_text(json.dumps(stage,ensure_ascii=False,indent=2)+"\n")
print("B335_PLATE_MACHINE_PASS",json.dumps({"orange":stage["source_orange_pixels_exact"],"protect":stage["protected_source_contour_pixels"],"full_source":SRC_HASH,"manifest":str(manifestpath),"proofs":len(proofs)},ensure_ascii=False))
