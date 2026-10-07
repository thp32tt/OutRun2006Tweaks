#!/usr/bin/env python3
# B241: q212 BA0147DA C251 title-family proportion/hierarchy rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import base64, hashlib, json, struct, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

repo=Path.cwd()
RUN="20261007-B241-Q212-BA0147DA-TITLE-FAMILY"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
PRIOR_SHA="61ae0c45568e023cc258379173f8d80f43cc5257f2d8facefbcf3c87759179e1"
FINAL_SHA="c3b362c4aadde15c18075f65f24d341cf08315b32fd67bf19db3e017b8ac0df6"
SOURCE_SHA="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
PATCH_PACKAGE=json.loads(r'''{"prior_sha256":"61ae0c45568e023cc258379173f8d80f43cc5257f2d8facefbcf3c87759179e1","candidate_sha256":"c3b362c4aadde15c18075f65f24d341cf08315b32fd67bf19db3e017b8ac0df6","width":2048,"height":2048,"patches":[{"key":"heart_attack_title","readable_bbox":[21,1316,1780,1474],"raw_bbox":[21,574,1780,732],"raw_bytes":1111688,"raw_sha256":"0986c6dae1e6a1997e35dc6e7c31d8131fe680ecc2b2a598bfb1fcbf03052a25","zlib_base64":"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"},{"key":"coast2coast_title","readable_bbox":[0,964,1760,1124],"raw_bbox":[0,924,1760,1084],"raw_bytes":1126400,"raw_sha256":"d215bacbd2ba4844180c2b5de6e2b6cf95fe82328e94464369e28f4214c04598","zlib_base64":"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"}]}''')

def sha(b): return hashlib.sha256(b).hexdigest()

prior_bytes=cand.read_bytes()
if sha(prior_bytes)!=PRIOR_SHA:
    raise RuntimeError(("q212 candidate drift",sha(prior_bytes),PRIOR_SHA))
if prior_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",prior_bytes,12)[0];W=struct.unpack_from("<I",prior_bytes,16)[0]
MIPS=struct.unpack_from("<I",prior_bytes,28)[0]
if (W,H,MIPS)!=(2048,2048,1) or len(prior_bytes)!=128+W*H*4:
    raise RuntimeError(("unexpected DDS",W,H,MIPS,len(prior_bytes)))

# Exact raw patch replay from controller-produced B241 bytes. This avoids
# font-package/version drift on the hosted runner while preserving the exact
# native-HD result already visually adjudicated.
outb=bytearray(prior_bytes)
for p in PATCH_PACKAGE["patches"]:
    raw=zlib.decompress(base64.b64decode(p["zlib_base64"]))
    if len(raw)!=p["raw_bytes"] or sha(raw)!=p["raw_sha256"]:
        raise RuntimeError(("patch integrity",p["key"]))
    x0,y0,x1,y1=p["raw_bbox"];rowbytes=(x1-x0)*4
    if len(raw)!=(y1-y0)*rowbytes: raise RuntimeError(("patch size",p["key"]))
    pos=0
    for y in range(y0,y1):
        off=128+(y*W+x0)*4
        outb[off:off+rowbytes]=raw[pos:pos+rowbytes]
        pos+=rowbytes
final_bytes=bytes(outb)
if sha(final_bytes)!=FINAL_SHA:
    raise RuntimeError(("final SHA mismatch",sha(final_bytes),FINAL_SHA))
if final_bytes[:128]!=prior_bytes[:128]:
    raise RuntimeError("header changed")
cand.write_bytes(final_bytes)

# Decode raw mirror-Y into readable orientation.
prior_raw=np.frombuffer(prior_bytes,dtype=np.uint8,offset=128,count=W*H*4).reshape(H,W,4).copy()
final_raw=np.frombuffer(final_bytes,dtype=np.uint8,offset=128,count=W*H*4).reshape(H,W,4).copy()
prior=prior_raw[::-1].copy();final=final_raw[::-1].copy()
clean=prior.copy()
rows=[
 {"key":"heart_attack_title","source":"HEART ATTACK","korean":"하트 어택","source_bbox":[21,1316,1780,1474],"prior_bbox":[25,1322,618,1468],"prior_size":[593,146]},
 {"key":"coast2coast_title","source":"COAST 2 COAST","korean":"코스트 2 코스트","source_bbox":[0,964,1760,1124],"prior_bbox":[4,982,1033,1105],"prior_size":[1029,123]},
]
allowed=np.zeros((H,W),bool)
report_rows=[]
label_masks=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]
    allowed[y0:y1,x0:x1]=True
    clean[y0:y1,x0:x1,3]=0
    m=final[y0:y1,x0:x1,3]>0
    ys,xs=np.nonzero(m)
    if not len(xs): raise RuntimeError(("empty final title",r["key"]))
    lb=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("non-positive margin",r["key"],margins))
    lm=np.zeros((H,W),bool);lm[y0:y1,x0:x1]=m;label_masks.append((r["key"],lm))
    size=[lb[2]-lb[0],lb[3]-lb[1]]
    report_rows.append({**r,"localized_bbox":lb,"source_size":[x1-x0,y1-y0],"localized_size":size,
      "margins":margins,"prior_width_ratio":round(r["prior_size"][0]/(x1-x0),4),
      "prior_height_ratio":round(r["prior_size"][1]/(y1-y0),4),
      "final_width_ratio":round(size[0]/(x1-x0),4),"final_height_ratio":round(size[1]/(y1-y0),4),
      "width_gain_px":size[0]-r["prior_size"][0],"height_gain_px":size[1]-r["prior_size"][1],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

diff=np.any(prior!=final,axis=2);ad=prior[:,:,3]!=final[:,:,3]
outside=int(np.count_nonzero(diff&~allowed));alpha_out=int(np.count_nonzero(ad&~allowed))
overlap=int(np.count_nonzero(label_masks[0][1]&label_masks[1][1]))
if outside or alpha_out or overlap:
    raise RuntimeError(("blast/overlap",outside,alpha_out,overlap))

def comp(a,bg=(64,64,64,255)):
    im=Image.fromarray(a.astype(np.uint8),"RGBA")
    base=Image.new("RGBA",im.size,bg);return Image.alpha_composite(base,im).convert("RGB")
P,C,F=comp(prior),comp(clean),comp(final)
for rr in report_rows:
    x0,y0,x1,y1=rr["source_bbox"];pad=24
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[P.crop(box),C.crop(box),F.crop(box)]
    ims=[im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST) for im in ims]
    sh=Image.new("RGB",(max(i.width for i in ims),sum(i.height for i in ims)+72),(20,20,20))
    d=ImageDraw.Draw(sh);y=0
    for lab,im in zip(["C251 REJECTED PRIOR","CLEAN","B241 FINAL"],ims):
        d.text((4,y+2),lab,fill="white");y+=22;sh.paste(im,(0,y));y+=im.height+2
    sh.save(out/f"B241_{rr['key']}_PRIOR_CLEAN_FINAL_2X.jpg",quality=96,subsampling=0)

def full_sheet(name,arrs):
    ims=[comp(a) for a in arrs];target=1024
    ims=[im.resize((target,round(im.height*target/im.width)),Image.Resampling.LANCZOS) for im in ims]
    sh=Image.new("RGB",(sum(i.width for i in ims)+16,max(i.height for i in ims)+28),(20,20,20))
    d=ImageDraw.Draw(sh);x=0
    for lab,im in zip(["C251 REJECTED PRIOR","B241 FINAL"],ims):
        d.text((x+4,4),lab,fill="white");sh.paste(im,(x,24));x+=im.width+16
    sh.save(out/name,quality=94,subsampling=0)
full_sheet("B241_FULL_READABLE.jpg",[prior,final])
full_sheet("B241_FULL_RAW.jpg",[prior_raw,final_raw])

cards=[]
for rr in report_rows:
    x0,y0,x1,y1=rr["source_bbox"];pad=20
    crop=F.crop((max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad)))
    for scale in (1.0,.75,.5):
        im=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
        card=Image.new("RGB",(im.width,im.height+24),(20,20,20));card.paste(im,(0,24))
        ImageDraw.Draw(card).text((4,4),f"{rr['key']} {int(scale*100)}%",fill="white");cards.append(card)
cw=max(c.width for c in cards);ch=sum(c.height for c in cards)
sheet=Image.new("RGB",(cw,ch),(20,20,20));y=0
for c in cards:sheet.paste(c,(0,y));y+=c.height
sheet.save(out/"B241_PRACTICAL_100_75_50.jpg",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"B","run":RUN,"queue_index":212,"asset":asset,
 "source_sha256":SOURCE_SHA,
 "source_provenance":"A88/B166 exact English-source contacts + C251 exact source title bboxes",
 "prior_candidate_sha256":PRIOR_SHA,"candidate_sha256":FINAL_SHA,
 "reason":"C251_REWORK_REQUIRED_SOURCE_TITLE_FAMILY_PROPORTION_HIERARCHY",
 "source_ui_family":"SUMO_FRONTEND_LARGE_RED_TALL_CONDENSED_TITLE",
 "construction":"controller-produced native whole-string NanumGothicCodingBold B241 patches replayed byte-exact inside only the two title bboxes",
 "font":{"family":"NanumGothicCoding","weight":"Bold","whole_string_shaping":True,"artificial_tracking":False},
 "rows":report_rows,
 "machine_qa":{"bbox_size_positive_margin":"2/2 PASS","changed_pixels":int(np.count_nonzero(diff)),
  "changed_outside_source_bboxes":outside,"alpha_changed_outside_source_bboxes":alpha_out,
  "localized_pair_overlap_pixels":overlap,"protected_changed_pixels":0,"header_128_exact":True,
  "dimensions":[W,H],"format":"RGBA32","mips":MIPS,"raw_orientation":"mirror_y",
  "persisted_decode":"PASS","non_target_candidate_pixels_exact":"PASS"},
 "execution_backend":"CHATGPT_CONTROLLER_N100_MCP_FALLBACK_EXACT_PATCH_REPLAY_ON_GITHUB_HOSTED_WORKER",
 "controller_visual_qa":"PENDING_CONTROLLER_CONFIRM_OF_PERSISTED_OUTPUT",
 "runtime_validation":"UNTESTED",
 "status":"B241_WORKER_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA_AND_FRESH_C"
}
(out/"B241_Q212_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B241_Q212_BA0147DA.json").write_text(json.dumps({
 "role":"B","run":RUN,"queue_index":212,"candidate_sha256":FINAL_SHA,
 "report":str((out/"B241_Q212_MACHINE_QA.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"prior":PRIOR_SHA,"candidate":FINAL_SHA,"rows":report_rows,
 "machine_qa":report["machine_qa"],"runtime_validation":"UNTESTED"},ensure_ascii=False))
