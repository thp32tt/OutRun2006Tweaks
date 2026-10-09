#!/usr/bin/env python3
"""B330 q098 English terminal-residue removal in *persisted* BC3 DDS.

C328's first-look rejected the promoted B327R: its BC3 rewrite covered
only x475..1580 while the source English effect extends x431..1674.
This changes ONLY original-English remnants outside the Korean cell.
No fresh same-style Korean rerender and no new typography claims.
Work product is a quarantined DDS trial until DIRECT full-frame visual QA.
"""
import hashlib, io, json, os, struct, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
OUT=G/"role_B/20261009-B330-Q098-ENGLISH-FLANK-REMOVAL"
OUT.mkdir(parents=True,exist_ok=True)
h=lambda b: hashlib.sha256(b).hexdigest()
SOURCE="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
CURRENT="472392829d96cc1dc6ed980d942c56df883758f2777490ac6e7f6dafb5f86028"
CLEAN_SHA="b5c9c07a2490abd055153f750b415193eb84ef14c298b3e3873fd915db3af9e8"
assert json.loads((G/"role_C/20261009-C328-C2-Q098-PERSISTED-ENGLISH-RESIDUE/C328_Q098_CONTROLLER_REWORK.json").read_text())["decision"]=="REWORK_REQUIRED"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],text=True,capture_output=True,check=True)
action=json.loads(tri.stdout)["assets"][0]
assert action["next_action"] in ("MATERIAL_REWORK","NORMAL_QUEUE_SELECTION"),action
old=(G/"hd_candidates"/REL).read_bytes()
assert h(old)==CURRENT,"Concurrent B/C mutation of current q098; halt"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with urllib.request.urlopen(url,timeout=160) as fh: source=fh.read()
assert h(source)==SOURCE and old[:128]==source[:128]
assert (len(old),old[84:88],struct.unpack_from("<I",old,28)[0])==(262272,b"DXT5",1)
def decode(buf):
    return np.array(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
S=decode(source)
P=decode(old)
clean_path=G/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
assert h(clean_path.read_bytes())==CLEAN_SHA
C=np.array(Image.open(clean_path).convert("RGBA"),dtype=np.uint8)
assert S.shape==P.shape==C.shape==(128,2048,4)
sourcebox=(431,6,1674,123)
koreanbox=(475,9,1580,120)
yy,xx=np.indices((128,2048))
source_mask=(xx>=431)&(xx<1674)&(yy>=6)&(yy<123)
ko_cell=(xx>=475)&(xx<1580)&(yy>=9)&(yy<120)
erase=source_mask & ~ko_cell
assert np.count_nonzero(P[:,:,3][erase])>250,"Expected C328 verified English remnants missing"
assert np.count_nonzero(C[:,:,3][erase])==0,"Plate not transparent under original English remnants"
assert np.count_nonzero((S!=C).any(axis=2)&~source_mask)==0,"CLEAN changed protected pixels"
A=P[:,:,3].copy()
A[erase]=C[:,:,3][erase]
# BC3 DXT5 decompressor stores alpha in the first 8 bytes per 4x4 RAW block.
# Preserve each block's exact 8-byte RGB encoding. Only alpha is re-encoded,
# so source/Korean color textures and outside-source RGB are never repainted.
buf=bytearray(old); changed_blocks=0
alpha_levels=np.array([255,0,218,182,145,109,72,36],dtype=np.int16)
for y in range(0,128,4):
    for x in range(0,2048,4):
        roi=erase[y:y+4,x:x+4]
        if not roi.any() or not np.any(P[y:y+4,x:x+4,3][roi]!=0):
            continue
        target=A[y:y+4,x:x+4].astype(np.int16)
        idx=np.abs(target[:,:,None]-alpha_levels[None,None,:]).argmin(axis=2)
        bits=0
        for iy in range(4):
            for ix in range(4):
                # BC3 memory is RAW bottom-to-top versus decoded READABLE Y.
                raw_position=(3-iy)*4+ix
                bits|=int(idx[iy,ix])<<(3*raw_position)
        off=128+(((128-y-4)//4)*(2048//4)+(x//4))*16
        assert bytes(buf[off+8:off+16])==old[off+8:off+16]
        buf[off:off+8]=bytes([255,0])+bits.to_bytes(6,"little")
        changed_blocks+=1
assert changed_blocks>20,changed_blocks
trial=bytes(buf);assert trial[:128]==old[:128] and len(trial)==len(old)
D=decode(trial)
# Full-frame gates: no English alpha left at both flanks; bytes/pixels outside
# source completely unchanged; Korean reconstructed center remains EXACT.
assert np.count_nonzero(D[:,:,3][erase])==0,"English alpha residue after BC3"
assert np.array_equal(D[ko_cell],P[ko_cell]),"Korean glyph or its outline touched"
assert np.array_equal(D[~source_mask],P[~source_mask]),"Protected outside-source artwork touched"
assert np.array_equal(trial[84:128],old[84:128]),"DDS header changed"
assert trial!=old
# Anything in the source lettering area outside the Korean cell must be
# composition-transparent even when BC3 retains irrelevant hidden RGB.
assert np.count_nonzero(D[:,:,3][erase])==0
outside=int(np.count_nonzero(np.any(D!=P,axis=2)&~source_mask))
assert outside==0
old_left=int(np.count_nonzero(P[:,:,3][erase&(xx<475)]))
old_right=int(np.count_nonzero(P[:,:,3][erase&(xx>=1580)]))
assert old_left>0 and old_right>0,(old_left,old_right)
target_path=OUT/"B330_Q098_UNAPPROVED_FULL_ENGLISH_ERASE_TRIAL.dds"
target_path.write_bytes(trial)
assert h(target_path.read_bytes())==h(trial)
assert np.array_equal(decode(target_path.read_bytes()),D)

def contact(bg,orientation,size):
    chunks=[]
    arrays=(S,C,P,D)
    for arr in arrays:
        if orientation=="RAW":arr=np.flipud(arr)
        im=Image.new("RGBA",(2048,128),(*bg,255))
        im.alpha_composite(Image.fromarray(arr,"RGBA"))
        if size!=100:im=im.resize((round(2048*size/100),round(128*size/100)),Image.Resampling.LANCZOS)
        chunks.append(im.convert("RGB"))
    frame=Image.new("RGB",(sum(x.width for x in chunks)+12,max(x.height for x in chunks)),(96,96,96))
    cursor=0
    for im in chunks:
        frame.paste(im,(cursor,0));cursor+=im.width+4
    return frame
proofs=[]
for orientation in ("READABLE","RAW"):
    for bgname,bg in (("GRAY",(72,72,72)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
        for scale in (100,75,50):
            name=f"FULL_{orientation}_{bgname}_{scale}_SOURCE_CLEAN_OLD_NEW.png"
            contact(bg,orientation,scale).save(OUT/name,optimize=True)
            proofs.append(name)
for title,arr in (("SOURCE",S),("CLEAN",C),("OLD",P),("NEW",D)):
    Image.fromarray(arr,"RGBA").save(OUT/f"FULL_{title}_READABLE_RGBA.png")
    Image.fromarray(np.flipud(arr),"RGBA").save(OUT/f"FULL_{title}_RAW_RGBA.png")
report={
  "run":"B330","queue_index":98,"asset":REL,
  "source_sha256":SOURCE,"verified_clean_sha256":CLEAN_SHA,
  "old_sha256":CURRENT,"new_trial_sha256":h(trial),
  "candidate_promoted":False,"unapproved_trial_count":1,"new_promoted_dds_count":0,
  "root_cause":"SOURCE_RESIDUE_UNDER_KOREAN: original English bbox 431..1674 versus narrower B327R BC3 edit 475..1580",
  "correction":"Erase persisted BC3 terminal-original-alpha outside Korean cell; unchanged Korean bytes/pixels; use exact clean source for transparency",
  "bc3_alpha_blocks_rebuilt":changed_blocks,"old_left_alpha_sum":old_left,
  "old_right_alpha_sum":old_right,"new_english_outside_korean_alpha_pixels":0,
  "persisted_dds_exact_decode":"PASS",
  "untouched_korean_native_rgba":"PASS_EXACT",
  "outside_english_bbox_rgba_changed":outside,
  "plate_gate":"SOURCE_VS_CLEAN_ZERO_SOURCE_RESIDUE_ALPHA_AND_ZERO_OUTSIDE",
  "composite_gate":"OUTSIDE_KOREAN_ALL_SOURCE_ALPHA_REMOVED; KOREAN_EXACT",
  "native":[2048,128],"format":"BC3_DXT5","mips":1,"orientation":"MIRROR_Y",
  "full_frame_native_75_50_RAW_READABLE_BG_W_G_BLACK":proofs,
  "full_frame_visual":"AWAIT_CONTROLLER_DIRECT_INSPECTION",
  "producer_qa":"MACHINE_PASS_VISUAL_NOT_YET_APPROVED",
  "C2":"NOT_RUN","C3":"NOT_RUN","user_game":"UNTESTED",
  "RUNTIME_VALIDATION":"UNTESTED","backend":"github-actions",
  "excluded":["VR","FFB","DX11","DXVK"]
}
(OUT/"B330_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B330_Q098_TRIAL",json.dumps({"trial_sha":h(trial),"alpha_blocks":changed_blocks,
  "source_left_alpha":old_left,"source_right_alpha":old_right,"new_english_alpha":0,
  "proof_count":len(proofs)},ensure_ascii=False))
