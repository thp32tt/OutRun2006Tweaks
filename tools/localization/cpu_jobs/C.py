#!/usr/bin/env python3
# C237 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh C resolves q12 A162 HOLD by preserving A160 glyph orientation and correcting only raw Y placement.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib,json,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw

repo=Path.cwd()
RUN="20261007-C237-C2-Q012-D6DC1380-ORIENTATION-PLACEMENT"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_etc_xst/D6DC1380_256x64.dds"
candp=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
INPUT_SHA="fab100b99f42b773d820be5145866b07830637a2bee060ebbba133d1555739e5"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_etc_xst/D6DC1380_256x64.dds"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_raw(b,expected=None):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4: raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    im=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    if expected and (w,h)!=expected: raise RuntimeError(("dimensions",(w,h),expected))
    return im,{"width":w,"height":h,"mips":mips,"mode":mode}
def bbox_alpha(im):
    a=np.asarray(im.getchannel("A"))
    ys,xs=np.nonzero(a)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def flip_bbox(b,h): return [b[0],h-b[3],b[2],h-b[1]]
def visible_multiset(im):
    a=np.asarray(im)
    z=a[a[:,:,3]>0]
    if not len(z): return []
    # compare exact multiset of visible RGBA pixels, independent of placement
    z=np.ascontiguousarray(z).view([("r","u1"),("g","u1"),("b","u1"),("a","u1")]).reshape(-1)
    return np.sort(z,order=["r","g","b","a"])
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    z=comp(im); c=Image.new("RGB",(z.width,z.height+24),(22,22,22)); c.paste(z,(0,24))
    ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
def strip(items):
    w=sum(x.width for x in items); h=max(x.height for x in items)
    o=Image.new("RGB",(w,h),(20,20,20)); x=0
    for im in items:o.paste(im,(x,0));x+=im.width
    return o

tmp=Path("/tmp/c237"); tmp.mkdir(exist_ok=True)
sp=tmp/"source.dds"; urllib.request.urlretrieve(source_url,sp)
sb=sp.read_bytes(); ib=candp.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(ib)!=INPUT_SHA: raise RuntimeError(("input drift",sha(ib)))
src_raw,sm=decode_raw(sb,(256,64)); old_raw,cm=decode_raw(ib,(1024,256))
if sm["mips"]!=1 or cm["mips"]!=1 or sm["mode"]!=cm["mode"]:
    raise RuntimeError(("source/candidate DDS mode or mip drift",sm,cm))
# Headers differ in dimensions by design (native source 256x64 vs CREATE_NEW_HD 1024x256); candidate header itself must be preserved byte-exact.
src_bb=bbox_alpha(src_raw); old_bb=bbox_alpha(old_raw)
if src_bb!=[8,10,248,44]: raise RuntimeError(("source raw bbox drift",src_bb))
if old_bb!=[117,82,907,214]: raise RuntimeError(("A160 raw bbox drift",old_bb))
source_hd_bb=[v*4 for v in src_bb]
old_size=[old_bb[2]-old_bb[0],old_bb[3]-old_bb[1]]
target_x=source_hd_bb[0]+((source_hd_bb[2]-source_hd_bb[0])-old_size[0])//2
target_y=source_hd_bb[1]+((source_hd_bb[3]-source_hd_bb[1])-old_size[1])//2
target_bb=[target_x,target_y,target_x+old_size[0],target_y+old_size[1]]
shift=[target_x-old_bb[0],target_y-old_bb[1]]
if target_bb!=[117,42,907,174] or shift!=[0,-40]:
    raise RuntimeError(("unexpected correction",target_bb,shift))

# Small C corrective rework: translate existing A160 RAW pixels only; DO NOT vertical-flip glyphs.
# Text-only transparent sprite: preserve exact visible RGBA pixel multiset and alpha count.
oa=np.asarray(old_raw)
vis=oa[:,:,3]>0
ys,xs=np.nonzero(vis)
newa=np.zeros_like(oa)
ny=ys+shift[1]; nx=xs+shift[0]
if ny.min()<0 or nx.min()<0 or ny.max()>=256 or nx.max()>=1024: raise RuntimeError("translation clips")
newa[ny,nx]=oa[ys,xs]
new_raw=Image.fromarray(newa.astype(np.uint8),"RGBA")
new_bb=bbox_alpha(new_raw)
if new_bb!=target_bb: raise RuntimeError(("new bbox",new_bb,target_bb))
if int((oa[:,:,3]>0).sum())!=int((newa[:,:,3]>0).sum()): raise RuntimeError("alpha pixel count changed")
if not np.array_equal(visible_multiset(old_raw),visible_multiset(new_raw)): raise RuntimeError("visible RGBA multiset changed")

# Exact raw and readable containment against canonical source in the SAME transform.
src_flip=ImageOps.flip(src_raw).resize((1024,256),Image.Resampling.NEAREST)
# For bbox authority, mirror the exact source raw bbox; do not infer from visual crop.
source_flip_hd_bb=flip_bbox(source_hd_bb,256)
new_flip=ImageOps.flip(new_raw)
new_flip_bb=bbox_alpha(new_flip)
raw_contain=(new_bb[0]>=source_hd_bb[0] and new_bb[1]>=source_hd_bb[1] and new_bb[2]<=source_hd_bb[2] and new_bb[3]<=source_hd_bb[3])
flip_contain=(new_flip_bb[0]>=source_flip_hd_bb[0] and new_flip_bb[1]>=source_flip_hd_bb[1] and new_flip_bb[2]<=source_flip_hd_bb[2] and new_flip_bb[3]<=source_flip_hd_bb[3])
raw_margins=[new_bb[0]-source_hd_bb[0],source_hd_bb[2]-new_bb[2],new_bb[1]-source_hd_bb[1],source_hd_bb[3]-new_bb[3]]
flip_margins=[new_flip_bb[0]-source_flip_hd_bb[0],source_flip_hd_bb[2]-new_flip_bb[2],new_flip_bb[1]-source_flip_hd_bb[1],source_flip_hd_bb[3]-new_flip_bb[3]]
if not(raw_contain and flip_contain and min(raw_margins)>0 and min(flip_margins)>0):
    raise RuntimeError(("containment",raw_contain,flip_contain,raw_margins,flip_margins))

# Persist with exact A160 candidate header and format/mips.
payload=ib[:128]+new_raw.tobytes("raw",cm["mode"])
candp.write_bytes(payload)
ob=candp.read_bytes()
persisted_raw,pm=decode_raw(ob,(1024,256))
if ob[:128]!=ib[:128] or pm!=cm or bbox_alpha(persisted_raw)!=new_bb: raise RuntimeError("persisted roundtrip/header failure")
out_sha=sha(ob)

# Evidence: same RAW transform and same FLIP-Y transform, full canvas positions preserved.
source_raw4=src_raw.resize((1024,256),Image.Resampling.NEAREST)
source_flip4=ImageOps.flip(src_raw).resize((1024,256),Image.Resampling.NEAREST)
strip([card("SOURCE RAW 4x",source_raw4),card("A160 RAW INPUT",old_raw),card("C237 RAW SHIFT-ONLY",persisted_raw)]).save(out/"C237_RAW_SOURCE_A160_FINAL.jpg",quality=95)
strip([card("SOURCE FLIP-Y 4x",source_flip4),card("A160 FLIP-Y",ImageOps.flip(old_raw)),card("C237 FLIP-Y",ImageOps.flip(persisted_raw))]).save(out/"C237_FLIPY_SOURCE_A160_FINAL.jpg",quality=95)
# Readable practical scales use identical FLIP-Y transform for source/current.
cards=[]
for pct in (100,75,50):
    sc=pct/100
    s=comp(source_flip4).resize((int(1024*sc),int(256*sc)),Image.Resampling.LANCZOS)
    f=comp(ImageOps.flip(persisted_raw)).resize((int(1024*sc),int(256*sc)),Image.Resampling.LANCZOS)
    cards.append(strip([card(f"SOURCE READABLE {pct}%",s.convert("RGBA")),card(f"C237 READABLE {pct}%",f.convert("RGBA"))]))
mw=max(x.width for x in cards); mh=sum(x.height for x in cards)
sheet=Image.new("RGB",(mw,mh),(20,20,20)); y=0
for x in cards: sheet.paste(x,(0,y)); y+=x.height
sheet.save(out/"C237_PRACTICAL_100_75_50.jpg",quality=95)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"queue_index":12,"asset":asset,"priority":"P0","user_jpg_regression":"PJR-001-20261006",
 "source_sha256":SOURCE_SHA,"input_candidate_sha256":INPUT_SHA,"candidate_sha256":out_sha,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "conflict_resolution":{
   "c235_error":"C235 inferred orientation from absolute bbox position and labeled canonical RAW as normal/readable; A162 visual evidence proved source RAW and A160 RAW share the same upside-down transform.",
   "a162_error":"A162 corrected bbox position by vertically flipping glyph pixels, causing source and candidate to require opposite transforms.",
   "c237_fix":"Preserve A160 glyph pixel orientation exactly and translate RAW pixels by [0,-40] only, centering the 790x132 candidate inside the exact 4x canonical RAW source bbox 960x136."
 },
 "geometry":{
   "source_raw_bbox_native":src_bb,"source_raw_bbox_hd":source_hd_bb,
   "a160_raw_bbox":old_bb,"c237_raw_bbox":new_bb,"raw_shift_xy":shift,
   "source_flipy_bbox_hd":source_flip_hd_bb,"c237_flipy_bbox":new_flip_bb,
   "localized_size":old_size,"source_size_hd":[source_hd_bb[2]-source_hd_bb[0],source_hd_bb[3]-source_hd_bb[1]],
   "raw_margins":raw_margins,"flipy_margins":flip_margins,
   "raw_containment":"PASS" if raw_contain else "FAIL","flipy_containment":"PASS" if flip_contain else "FAIL"
 },
 "pixel_preservation":{
   "visible_rgba_multiset_preserved":True,
   "visible_alpha_pixel_count_preserved":int((oa[:,:,3]>0).sum()),
   "glyph_orientation_operation":"NONE_NO_FLIP_NO_ROTATION",
   "placement_operation":"RAW_TRANSLATE_Y_MINUS_40_ONLY",
   "header_128_exact_vs_a160":ob[:128]==ib[:128],"mip_count":pm["mips"],"raw_mode":pm["mode"]
 },
 "machine_status":"PASS",
 "fresh_c_machine":"PASS_AFTER_SMALL_CORRECTIVE_REWORK",
 "c3_required":True,
 "c3_machine":"PASS_PENDING_CONTROLLER_VISUAL",
 "visual_evidence":[str(out/"C237_RAW_SOURCE_A160_FINAL.jpg"),str(out/"C237_FLIPY_SOURCE_A160_FINAL.jpg"),str(out/"C237_PRACTICAL_100_75_50.jpg")],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_PENDING_CONTROLLER_C3",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C237_D6DC1380_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C237_D6DC1380.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":12,"asset":"D6DC1380",
 "input_candidate_sha256":INPUT_SHA,"candidate_sha256":out_sha,"machine_status":"PASS","c3_machine":"PASS_PENDING_CONTROLLER_VISUAL",
 "report":str(out/"C237_D6DC1380_MACHINE_QA.json"),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":out_sha,"shift":shift,"raw_bbox":new_bb,"flipy_bbox":new_flip_bb,"raw_margins":raw_margins,"flipy_margins":flip_margins},ensure_ascii=False,indent=2))
