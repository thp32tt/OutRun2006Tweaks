#!/usr/bin/env python3
"""B310: native BG/WHITE/BLACK persisted proof of B309 q060 trial.

This proof job never changes the deployable candidate; controller must visually
compare first. Prepared DDS is only promoted after those views pass.
"""
import io, json, hashlib, os
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
A=G/"role_B/20261009-B309-Q060-P0-NATIVE-FILLED-GOLD-MASTER"
O=G/"role_B/20261009-B310-Q060-BGW-STRICT-NATIVE-REVIEW"
O.mkdir(parents=True,exist_ok=True)
h=lambda b:hashlib.sha256(b).hexdigest()
asset="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
old=(G/"hd_candidates"/asset).read_bytes()
trial=(A/"B309_Q060_TRIAL_NOT_PROMOTED.dds").read_bytes()
assert h(old)=="d938fdd1c92e43bd9fe2f51e3f0ba87c60662c39aaea41e8905e8f850901c2f2"
assert h(trial)=="7c05f2fe3f8e9e51a6ca79871e23b35f7bb7e5a1622fa52c69b2a0bf96d14295"
assert trial[:128]==old[:128] and len(trial)==len(old)
dec=lambda buf:np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
P=dec(old);T=dec(trial);assert P.shape==T.shape==(2048,4096,4)
l,t,r,b=455,245,690,350
allowed=np.zeros(P.shape[:2],bool);allowed[t:b,l:r]=True
delta=np.any(P!=T,axis=2)
assert np.any(delta) and np.count_nonzero(delta&~allowed)==0
assert np.count_nonzero((P[:,:,3]!=T[:,:,3])&~allowed)==0
assert np.array_equal(P[~allowed],T[~allowed])
source=np.asarray(Image.open(A/"B309_SOURCE_LOSSLESS.png").convert("RGBA"))
clean=np.asarray(Image.open(A/"B309_CLEAN_LOSSLESS.png").convert("RGBA"))
assert source.shape==clean.shape==(105,235,4)
assert not np.any(clean[:,:,3])
assert np.array_equal(P[t:b,l:r],np.asarray(Image.open(A/"B309_CURRENT_LOSSLESS.png").convert("RGBA")))
assert np.array_equal(T[t:b,l:r],np.asarray(Image.open(A/"B309_TRIAL_LOSSLESS.png").convert("RGBA")))
evidence={"q":60,"run":"B310","prior_run":"B309","source_sha256":"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc",
"old_sha256":h(old),"trial_sha256":h(trial),"bbox":[l,t,r,b],"encoded_roundtrip":"PASS",
"protected_full_atlas_outside_cell":"PIXEL_EXACT","outside_changed_rgba":0,"outside_changed_alpha":0,
"plate_alpha":0,"candidate_bytes_promoted":False,"runtime":"UNTESTED",
"independent_C2":"NOT_RUN","C3":"NOT_RUN","IGR044":"OPEN","backend":"github-actions",
"inspection":"PENDING_DIRECT_BGW_CONTROLLER"}
for orient in ("FLIPY","RAW"):
    sections=[source,clean,P[t:b,l:r].copy(),T[t:b,l:r].copy()]
    if orient=="RAW":sections=[np.flipud(x).copy() for x in sections]
    for bgname,rgb in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
        for scale in (100,75,50):
            imgs=[]
            for a in sections:
                bg=Image.new("RGBA",(235,105),tuple(rgb)+(255,))
                bg.alpha_composite(Image.fromarray(a,"RGBA"))
                im=bg.convert("RGB")
                if scale!=100:im=im.resize((round(235*scale/100),round(105*scale/100)),Image.Resampling.LANCZOS)
                imgs.append(im)
            gap=7
            contact=Image.new("RGB",(sum(im.width for im in imgs)+3*gap,max(im.height for im in imgs)),rgb)
            x=0
            for im in imgs:contact.paste(im,(x,0));x+=im.width+gap
            fn=f"B310_{orient}_{bgname}_{scale}_SOURCE_CLEAN_OLD_NEW.png"
            contact.save(O/fn,optimize=True)
            evidence.setdefault("views",[]).append(fn)
(O/"B310_MACHINE_QA.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n")
print("B310_REVIEW_PROOF",len(evidence["views"]),h(trial),"candidate_unchanged")
