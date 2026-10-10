#!/usr/bin/env python3
"""B348 q060 P0: source-first BEST TIME lettering removal-mask calibration.

This worker creates lossless PLATE_ONLY evidence from canonical English source.
It does not promote a Korean DDS or grant producer PASS: mask ownership and the
plate must be independently viewed before transparent Korean lettering.
"""
import os, io, json, hashlib, urllib.request, sys, subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as ndi
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
O=G/"role_B/20261010-B348-Q060-BEST-TIME-SOURCE-COMPONENT-PLATE"
O.mkdir(parents=True,exist_ok=True)
hs=lambda b:hashlib.sha256(b).hexdigest()
srcsha="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
current_sha="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
trial_sha="8774e3993fc5a13f455f2c95ea5b358b2f75eae0634ab54bed137aeea819c9f6"
srcp=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
if srcp.is_file():
    raw=srcp.read_bytes()
else:
    url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
    with urllib.request.urlopen(url,timeout=90) as f:raw=f.read()
assert hs(raw)==srcsha,("CANONICAL_SOURCE_MISMATCH",hs(raw))
base=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
bb=base.read_bytes()
assert hs(bb)==current_sha,("REMOTE_CURRENT_CHANGED",hs(bb))
def dec(v):
    return np.array(Image.open(io.BytesIO(v)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
s=dec(raw);cur=dec(bb)
assert s.shape==cur.shape==(2048,4096,4)
# C347 observed exact source glyph and 11px halo; this region is a
# discovery fence, NOT an approved source-removal mask.
roi=(2090,337,3120,485)
face=(2188,345,3016,460)
x0,y0,x1,y1=roi
patch=s[y0:y1,x0:x1]
visible=patch[:,:,3]>0
# Preserve native connected alpha artwork rather than RGB equality or
# hand-tuned recolor. No modifications outside selected source components.
labs,n=ndi.label(visible,structure=np.ones((3,3),dtype=np.uint8))
fx0,fy0,fx1,fy1=face
seeds=np.zeros(visible.shape,bool)
seeds[max(fy0-y0,0):min(fy1-y0,y1-y0),max(fx0-x0,0):min(fx1-x0,x1-x0)]=True
component_stats=[];selected=np.zeros(visible.shape,bool)
for k in range(1,n+1):
    mask=labs==k
    count=int(mask.sum())
    yy,xx=np.nonzero(mask)
    box=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)]
    within=int((mask&seeds).sum())
    edge=bool((mask[0]|mask[-1]).any() or (mask[:,0]|mask[:,-1]).any())
    # A component touching the English source face with at least a real
    # visible stroke enters the proposed removal mask; other components
    # remain immutable until a human resolves their semantic ownership.
    included=(within>=12 and count>=12 and not edge)
    if included:selected|=mask
    component_stats.append(dict(id=k,bbox=box,pixels=count,english_face_pixels=within,
                                roi_boundary=edge,proposed_removal=included))
# Reject when no unambiguous source component was found. A residual face
# indicates remaining unclassified glyph/halo; do not call the plate CLEAN PASS.
assert int(selected.sum())>1000,"NO_TARGET_SOURCE_COMPONENTS"
fullmask=np.zeros(s.shape[:2],np.uint8)
fullmask[y0:y1,x0:x1]=selected.astype(np.uint8)*255
clean=s.copy()
clean[fullmask>0]=0
assert not np.any(clean[fullmask>0]),"REMOVAL_ALPHA_NOT_ZERO"
assert int(np.count_nonzero(np.any(clean!=s,axis=2)&(fullmask==0)))==0
inside=seeds & ~selected
unclassified_in_face=int((visible&inside).sum())
touches_boundaries=sum(o["proposed_removal"] and o["roi_boundary"] for o in component_stats)
Image.fromarray(fullmask,"L").save(O/"B348_SOURCE_BEST_TIME_PROPOSED_REMOVAL_MASK_READABLE.png")
Image.fromarray(clean,"RGBA").save(O/"B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png")
Image.fromarray(np.flipud(clean),"RGBA").save(O/"B348_BEST_TIME_SOURCE_FIRST_PLATE_RAW.png")
# Separate original/PLATE-only review across neutral backgrounds, NEVER
# hide English remnants by layering already-authored Korean over this proof.
from PIL import ImageOps
rbox=(2050,205,3160,535)
panels=[]
for bg in [(128,128,128),(0,0,0),(255,255,255)]:
    v=[]
    for a in (s,clean,cur):
        layer=Image.fromarray(a[rbox[1]:rbox[3],rbox[0]:rbox[2]],"RGBA")
        canvas=Image.new("RGBA",layer.size,bg+(255,))
        canvas.alpha_composite(layer);v.append(canvas.convert("RGB"))
    for pct in (100,75,50):
        parts=[p.resize((round(p.width*pct/100),round(p.height*pct/100))) if pct<100 else p for p in v]
        w,h=parts[0].size;canvas=Image.new("RGB",(w*3+24,h),bg)
        for i,p in enumerate(parts):canvas.paste(p,(i*(w+12),0))
        fn=f"B348_SOURCE_PLATE_OLD_{bg[0]}_{pct}_READABLE.png"
        canvas.save(O/fn,optimize=True)
        panels.append(fn)
r={
 "schema_version":2,"run":"B348","role":"B","owner":"EVEN","queue_index":60,
 "run_key":"OUTRUN-KOR-B348-Q060-P0-SOURCE-COMPONENT-PLATE-20261010-1230",
 "source_sha256":srcsha,"official_sha256":current_sha,"prior_unapproved_trial_sha256":trial_sha,
 "method_change":"SOURCE alpha-connected original English glyph topology; NOT B343 source/current RGB equality or B344 tiny disconnected residual pixel deletion",
 "P1":"SOURCE_FIRST_PROPOSED_PLATE_AWAITING_CONTROLLER_VISUAL_SEMANTIC_REVIEW",
 "P2":"NOT_STARTED_BEFORE_P1","P3":"NOT_STARTED_NO_NEW_DDS",
 "source_shape":list(s.shape),"readable_roi":list(roi),"canonical_english_face_bbox":list(face),
 "removed_original_source_visible_pixels":int(selected.sum()),
 "source_alpha_visible_unclassified_inside_english_face":unclassified_in_face,
 "source_components_total":n,
 "source_components_selected":sum(c["proposed_removal"] for c in component_stats),
 "components":component_stats,"source_outside_proposed_mask_changed_rgba":0,
 "source_provenance":"OR2-HD-GUI-v0.25.10a SHA pinned; remote fallback Sonic-TV/OR2006Sprites at fixed commit",
 "qa_semantics":"HOLD_PRE_VISUAL_COMPONENT_OWNERSHIP; source-sibling preservation must be verified at native 100/75/50 + RAW/FLIP-Y before lettering. Unclassified alpha is not called clean.",
 "images":panels,"new_promoted_dds":0,"independent_C2":"C347_REWORK_UNCHANGED",
 "IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GITHUB_ACTIONS","forbidden_untouched":["A_ODD","C1","VR","FFB","DX11","DXVK"]
}
(O/"B348_P1_COMPONENT_CALIBRATION_MACHINE.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
print("B348 P1 source component evidence",r["removed_original_source_visible_pixels"],"unclassified_face_alpha",unclassified_in_face,"components",n,flush=True)
