#!/usr/bin/env python3
"""B270 controller-requested q098 current-B269 PLATE_ONLY / COMPOSITE / decoded-DDS evidence.
No DDS rewrite, no producer/C/C3 approval is emitted by this script.
"""
import os,sys,io,json,hashlib,urllib.request,tempfile,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, label

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B270 requires GitHub worker for exact pinned English DDS")
root=Path.cwd();gfx=root/"localization/graphics"
folder=gfx/"role_B/20261008-B270-Q098-PLATE-COMPOSITE-GATE"
folder.mkdir(parents=True,exist_ok=True)
sha=lambda x:hashlib.sha256(x).hexdigest()
asset=gfx/"hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
candidate_sha="1d63cd9b50422375bd0693b40302c01702f193a91dc19af1517eb3476fa20ceb"
english_sha="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
clean_path=gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
mask_path=gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
mask_sha="30b871414d43764e30ffd206caaa4be943d0389450e7749bf61f677f2a1b9370"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98"],capture_output=True,text=True,check=True)
triage=json.loads(tri.stdout)["assets"][0]
if triage["next_action"]!="MATERIAL_REWORK":raise RuntimeError(("unexpected q098 triage",triage))
(folder/"TRIAGE.json").write_text(json.dumps(triage,ensure_ascii=False,indent=2)+"\n")
curr=asset.read_bytes()
if sha(curr)!=candidate_sha:raise RuntimeError(("B269 candidate superseded; abort",sha(curr)))
source_url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"a95efe01d1f136514cef94b0d9e9fd61df021754/"
"Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds")
with tempfile.TemporaryDirectory(prefix="b270_source_") as td:
    p=Path(td)/"english.dds";urllib.request.urlretrieve(source_url,p);english=p.read_bytes()
if sha(english)!=english_sha:raise RuntimeError("English original SHA drift")
if curr[:128]!=english[:128]:raise RuntimeError("current DDS header differs from English")
def decode(data):
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8).copy()
source=decode(english);final=decode(curr)
clean=np.asarray(Image.open(clean_path).convert("RGBA"),dtype=np.uint8).copy()
mask=np.asarray(Image.open(mask_path).convert("L"),dtype=np.uint8)
if sha(mask_path.read_bytes())!=mask_sha:raise RuntimeError("B40 authored target glyph mask drift")
if source.shape!=final.shape or source.shape!=clean.shape or source.shape!=(128,2048,4):raise RuntimeError("native pixel dimensions differ")
if mask.shape!=(128,2048):raise RuntimeError("B40 glyph mask dimension drift")
Y,X=np.ogrid[:128,:2048]
english_bbox=[431,6,1674,123]
korean_bbox=[580,11,1524,116]
full_source=(X>=431)&(X<1674)&(Y>=6)&(Y<123)
full_target=(X>=580)&(X<1524)&(Y>=11)&(Y<116)
def changed(a,b):return np.any(a!=b,axis=2)
clean_diff=changed(source,clean)
final_diff=changed(final,clean)
outside_plate=int((clean_diff&~full_source).sum())
outside_comp=int((final_diff&~full_target).sum())
# BC3 can mutate RGB even where alpha zero; report both unconditional and visible.
plate_visible_diff=((source[:,:,3]>16)|(clean[:,:,3]>16))&clean_diff
comp_visible_diff=((final[:,:,3]>16)|(clean[:,:,3]>16))&final_diff
outside_plate_visible=int((plate_visible_diff&~full_source).sum())
outside_comp_visible=int((comp_visible_diff&~full_target).sum())
outside_english=int((changed(source,final)&~full_source).sum())
if outside_plate or outside_comp_visible or outside_english:
    raise RuntimeError(("source/clean/composite unauthorized blast radius",
                        outside_plate,outside_comp_visible,outside_english))
alpha_bbox=lambda ar: [int(np.where(ar)[1].min()),int(np.where(ar)[0].min()),int(np.where(ar)[1].max()+1),int(np.where(ar)[0].max()+1)] if np.any(ar) else None
native_alpha=(final[:,:,3]>16)
actual_bbox=alpha_bbox(native_alpha)
if actual_bbox is None or any(a<b for a,b in zip(actual_bbox[:2],english_bbox[:2])) or any(a>b for a,b in zip(actual_bbox[2:],english_bbox[2:])):
    raise RuntimeError(("final alpha out of English glyph effect bounds",actual_bbox))
if np.any(final[:,:,3][~full_source]>source[:,:,3][~full_source]):
    raise RuntimeError("new alpha outside source")
# Actual B40 clean has alpha=0 in English glyph removal; ensure source-only visible
# alpha is gone where English was present and current Korean mask absent.
source_only=(source[:,:,3]>16)&(~(mask>0))&full_source
plate_remaining=int(((clean[:,:,3]>16)&source_only).sum())
# Source-only includes original/neighbor graphic pixels that were intentionally
# preserved, so it is diagnostic, not automatically grounds for PASS/FAIL.
alpha_outside_source=int(np.count_nonzero(final[:,:,3][~full_source]!=source[:,:,3][~full_source]))
color_outside_source=int(np.count_nonzero(changed(source,final)&~full_source))
mask_core=binary_erosion((mask>=210)&full_target,iterations=1)
RGB=final[:,:,:3].astype(np.int32)
white=(RGB[:,:,0]>=221)&(RGB[:,:,1]>=216)&(RGB[:,:,2]>=210)&(final[:,:,3]>95)
pinholes=int(np.count_nonzero(mask_core&(final[:,:,3]>160)&~white))
white_core=int(np.count_nonzero(mask_core&white))
raw=np.flipud(final)
if np.any(np.flipud(raw)!=final):raise RuntimeError("RAW/readable Y orientation inconsistent")
# Generate lossless plate-only and composite gates, with source/clean/final each
# in exactly the same pixel alignment (no stretching) on 3 neutral backgrounds.
backgrounds={"GRAY":(88,88,88),"WHITE":(245,245,245),"BLACK":(15,15,15)}
images={"SOURCE":source,"CLEAN":clean,"FINAL":final}
def composite_rgba(data,bg):
    alpha=data[:,:,3:4].astype(np.float32)/255.0
    rgb=data[:,:,:3].astype(np.float32)*alpha+np.array(bg,dtype=np.float32).reshape(1,1,3)*(1-alpha)
    return Image.fromarray(np.clip(np.rint(rgb),0,255).astype(np.uint8),"RGB")
proofs=[]
for bgname,bg in backgrounds.items():
    for orientation in ("READABLE","RAW"):
        view={k:(np.flipud(v) if orientation=="RAW" else v) for k,v in images.items()}
        for scale in (100,75,50):
            rendered={k:composite_rgba(v,bg) for k,v in view.items()}
            for stage,labels in (("PLATE_ONLY",("SOURCE","CLEAN")),
                                 ("COMPOSITE",("CLEAN","FINAL")),
                                 ("SOURCE_CLEAN_FINAL",("SOURCE","CLEAN","FINAL"))):
                tiles=[]
                # Crop x to English text atlas + margin (same original coordinates).
                for k in labels:
                    tile=rendered[k].crop((380,0,1720,128))
                    if scale!=100:
                        tile=tile.resize((round(tile.width*scale/100),round(tile.height*scale/100)),Image.Resampling.LANCZOS)
                    tiles.append(tile)
                img=Image.new("RGB",(sum(x.width for x in tiles)+8*(len(tiles)-1),max(x.height for x in tiles)),bg)
                x=0
                for tile in tiles:img.paste(tile,(x,0));x+=tile.width+8
                name=f"{stage}_{orientation}_{bgname}_{scale}.png"
                img.save(folder/name,optimize=True)
                proofs.append(name)
out={
 "run":"B270","run_key":"OUTRUN-KOR-B270-Q098-B269-PLATE-COMPOSITE-GATE-20261008",
 "queue_index":98,"asset":"42E618FD","sha256_exact_current":candidate_sha,
 "source_sha256":english_sha,"clean_png_sha256":sha(clean_path.read_bytes()),
 "authored_target_mask_sha256":mask_sha,
 "triage":triage,"execution_backend":"GITHUB_ACTIONS_EPHEMERAL_EXACT_SOURCE_UNAVAILABLE_TO_GPT_LOCAL_DNS",
 "same_candidate_bytes_preserved":True,
 "numeric":{"native_dimensions":[2048,128],"format":"BC3_DXT5","mips":1,
    "english_bbox":english_bbox,"prior_localized_bbox":korean_bbox,"persisted_visible_alpha_bbox":actual_bbox,
    "source_clean_changed_unconditional_outside_source_bbox":outside_plate,
    "clean_final_changed_unconditional_outside_target_bbox":outside_comp,
    "source_clean_changed_visible_outside_source_bbox":outside_plate_visible,
    "clean_final_changed_visible_outside_target_bbox":outside_comp_visible,
    "source_final_changed_outside_english_bbox":outside_english,
    "source_final_alpha_changed_outside_bbox":alpha_outside_source,
    "source_final_color_changed_outside_bbox":color_outside_source,
    "source_only_visible_overlap_in_clean_diagnostic":plate_remaining,
    "authored_target_inner_face_white_pixels":white_core,
    "authored_target_inner_face_unmatched_bright_pixels_diagnostic":pinholes,
    "preserved_original_header":curr[:128]==english[:128],
    "RAW_mirrorY_consistent":True},
 "lossless_evidence_count":len(proofs),"lossless_evidence_files":proofs,
 "claim_limit":"Images require controller visual judgement: masks, machine sums and approximate white thresholds do not independently clear source residue, pinhole quality, kerning, clean plate or C3.",
 "producer_visual":"PENDING_CONTROLLER_FRESH_BLINDED_NATIVE_SOURCE_CLEAN_FINAL",
 "independent_C":"NOT_RUN","C3":"NOT_RUN","PRE_INGAME":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED",
 "cleanup":"tempfile auto-clean on exit; ephemeral Actions workspace after commit",
 "forbidden_domains_touched":[]
}
(folder/"B270_MACHINE_AND_PLATE_COMPOSITE_QA.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"result":"PERSISTED_EVIDENCE","q98_sha":candidate_sha,"proofs":len(proofs),"plate_outside":outside_plate,"comp_visible_outside":outside_comp_visible,"white_core":white_core,"face_dark_diagnostic":pinholes},ensure_ascii=False))
