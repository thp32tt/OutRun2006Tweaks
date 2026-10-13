#!/usr/bin/env python3
"""Rebuild Q097 Korean icon DDS from byte-verified HD original; no Pillow DDS encoder."""
from pathlib import Path
from PIL import Image
import numpy as np
import hashlib
import json

here=Path(__file__).resolve().parent
repo=here.parents[2]
base=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
source=base.read_bytes()
s_sha=hashlib.sha256(source).hexdigest()
assert s_sha=="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364", s_sha
assert len(source)==16777344 and source[:4]==b"DDS "
header=source[:128]
raw=np.frombuffer(source[128:],dtype=np.uint8).reshape(2048,2048,4)
atlas=raw[::-1].copy()
original=atlas.copy()
x,y,w,h=790,825,780,295
icon=atlas[y:y+h,x:x+w]
bounds={"TUNED":(105,47,333,113),"NORMAL_TOP":(494,47,716,71),"NORMAL_LOWER":(482,71,716,113)}
allowed=np.zeros((h,w),dtype=bool)
for label,(x0,y0,x1,y1) in bounds.items():
    roi=icon[y0:y1,x0:x1]
    flat=np.array([196,0,0] if label=="TUNED" else [0,150,0],dtype=np.int16)
    mask=np.max(np.abs(roi[:,:,:3].astype(np.int16)-flat),axis=2)>3
    bordered=np.pad(mask,1)
    dilated=np.zeros_like(mask)
    for dy in range(3):
        for dx in range(3):
            dilated|=bordered[dy:dy+mask.shape[0],dx:dx+mask.shape[1]]
    dilated &= roi[:,:,3]>248
    roi[:,:,:3][dilated]=flat.astype(np.uint8)
    allowed[y0:y1,x0:x1]=True
composite=Image.fromarray(icon,"RGBA")
for name,pos in (("TUNED",(149,48)),("NORMAL",(542,48))):
    text=Image.open(here/f"sprite_{name}_64c.png").convert("RGBA")
    composite.alpha_composite(text,pos)
new_icon=np.array(composite)
new_icon[:,:,3]=original[y:y+h,x:x+w,3]
atlas[y:y+h,x:x+w]=new_icon
changed=np.any(atlas!=original,axis=2)
assert not np.any(changed[:y,:]) and not np.any(changed[y+h:,:])
assert not np.any(changed[y:y+h,:x]) and not np.any(changed[y:y+h,x+w:])
assert not np.any(changed[y:y+h,x:x+w]&~allowed)
assert np.array_equal(atlas[:,:,3],original[:,:,3])
dds=header+np.ascontiguousarray(atlas[::-1]).tobytes()
sha=hashlib.sha256(dds).hexdigest()
assert sha=="bb306b9a38de88d49602f3c45ff293302d0132290368984af2af65ecf1a766ac", sha
(here/"411827E_512x512_KOR.dds").write_bytes(dds)
png=new_icon.copy();png[png[:,:,3]==0,:3]=0
Image.fromarray(png,"RGBA").save(here/"Q097_KOR_ICON_TRANSPARENT.png")
qa={"source_sha256":s_sha,"candidate_sha256":sha,"format":"uncompressed RGBA32 2048x2048, original 128-byte header, no mips","size_bytes":len(dds),"original_alpha_preserved":True,"other_ui_changed_pixels":0,"modified_pixel_count":int(changed.sum()),"translation":{"TUNED":"튜닝","NORMAL":"일반"},"static_qa":"PASS","runtime_validation":"UNTESTED"}
(here/"Q097_KOR_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(qa,ensure_ascii=False))
