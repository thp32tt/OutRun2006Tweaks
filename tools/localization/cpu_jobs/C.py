#!/usr/bin/env python3
"""C2 q214 B258 independent native DDS evidence; NO C/C3 approval by script."""
import hashlib, io, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.getenv("OUTRUN_CPU_WORKER")!="github-actions" or os.getenv("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C only")
root=Path(".")
out=root/"localization/graphics/role_C/20261008-C285-C2-Q214-B258-INDEPENDENT"
out.mkdir(parents=True,exist_ok=True)
candidate=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
clean=root/"localization/graphics/role_B/20261006-B-PRODUCTION194-BF229CF4-START-GOAL/B194_CLEAN_PLATE.png"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3da79726739ac631d8e2703a65330dbb0c310770/Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
with urllib.request.urlopen(source_url,timeout=180) as f: sb=f.read()
cb=candidate.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
source_sha="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
candidate_sha="8b13c2aed450aad4072b97c9adaceaf0e413cd71554c6106b037ad6011fb5549"
assert sha(sb)==source_sha,(sha(sb),source_sha)
assert sha(cb)==candidate_sha,(sha(cb),candidate_sha)
assert sb[:128]==cb[:128],"DDS header diverged"
as_rgba=lambda b:np.asarray(Image.open(io.BytesIO(b)).convert("RGBA")).copy()
raws=as_rgba(sb); rawc=as_rgba(cb)
src=np.flipud(raws).copy(); cur=np.flipud(rawc).copy()
cl=np.asarray(Image.open(clean).convert("RGBA")).copy()
assert src.shape==cur.shape==cl.shape==(2048,2048,4)
rows=[("start","START","출발",(815,495,899,517)),("goal","GOAL","골",(1343,764,1417,787))]
allowed=np.zeros(src.shape[:2],dtype=bool)
for _,_,_,(x0,y0,x1,y1) in rows: allowed[y0:y1,x0:x1]=True
changed=np.any(src!=cur,axis=2)
alpha=src[:,:,3]!=cur[:,:,3]
outside=int(np.count_nonzero(changed&~allowed))
alpha_outside=int(np.count_nonzero(alpha&~allowed))
def bb(m):
    ys,xs=np.where(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def neutral(a):
    al=a[...,3:4].astype(np.uint16)
    rgb=a[...,:3].astype(np.uint16)
    return ((rgb*al+128*(255-al)+127)//255).astype(np.uint8)
details=[]
for rid,english,korean,box in rows:
    x0,y0,x1,y1=box
    srcmask=np.any(src[y0:y1,x0:x1]!=cl[y0:y1,x0:x1],axis=2)
    finmask=np.any(cur[y0:y1,x0:x1]!=cl[y0:y1,x0:x1],axis=2)
    sbbox=bb(srcmask); cbbox=bb(finmask)
    def globalbb(b):return None if b is None else [b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0]
    sbbox=globalbb(sbbox);cbbox=globalbb(cbbox)
    margins=None if cbbox is None else [cbbox[0]-x0,cbbox[1]-y0,x1-cbbox[2],y1-cbbox[3]]
    padding=16
    l=max(0,x0-padding);t=max(0,y0-padding);r=min(2048,x1+padding);b=min(2048,y1+padding)
    crops=[arr[t:b,l:r] for arr in (src,cl,cur)]
    for tag,a in zip(("ENGLISH_SOURCE","CLEAN_B194","PERSISTED_B258"),crops):
        Image.fromarray(a).save(out/f"{rid}_{tag}.png")
    labels=("ENGLISH SOURCE","B194 CLEAN","B258 DDS DECODE")
    imgs=[Image.fromarray(neutral(a),"RGB") for a in crops]
    w,h=imgs[0].size; contact=Image.new("RGB",(3*w,h+20),(50,50,50))
    draw=ImageDraw.Draw(contact)
    for i,(im,label) in enumerate(zip(imgs,labels)):
        contact.paste(im,(i*w,20));draw.text((i*w+2,2),label,fill="white")
    contact.save(out/f"{rid}_SOURCE_CLEAN_FINAL_NATIVE.png")
    contact.resize((contact.width*4,contact.height*4),Image.Resampling.NEAREST).save(out/f"{rid}_SOURCE_CLEAN_FINAL_ZOOM4X.png")
    for pct in (75,50):
        contact.resize((round(contact.width*pct/100),round(contact.height*pct/100)),Image.Resampling.LANCZOS).save(out/f"{rid}_SOURCE_CLEAN_FINAL_PRACTICAL{pct}.png")
    # Corresponding RAW crop must use H-y1:H-y0, not readable bbox coordinates.
    rt,rb=2048-b,2048-t
    Image.fromarray(raws[rt:rb,l:r]).save(out/f"{rid}_SOURCE_RAW_NATIVE.png")
    Image.fromarray(rawc[rt:rb,l:r]).save(out/f"{rid}_FINAL_RAW_NATIVE.png")
    subchange=changed[y0:y1,x0:x1]
    details.append({"id":rid,"english":english,"korean":korean,"source_effect_bbox":list(box),
        "source_vs_B194_clean_bbox":sbbox,"candidate_vs_B194_clean_bbox":cbbox,
        "margins_native":margins,"changed_source_to_candidate_inside_bbox":int(np.count_nonzero(subchange)),
        "bbox_containment":"PASS" if margins is not None and all(x>=0 for x in margins) else "HOLD",
        "inspection_images":[f"{rid}_SOURCE_CLEAN_FINAL_NATIVE.png",f"{rid}_SOURCE_CLEAN_FINAL_ZOOM4X.png",
                             f"{rid}_SOURCE_CLEAN_FINAL_PRACTICAL50.png",f"{rid}_SOURCE_RAW_NATIVE.png",f"{rid}_FINAL_RAW_NATIVE.png"]})
report={"run":"C285","queue_index":214,"TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
    "execution_backend":"GITHUB_HOSTED_CPU_INPUT_UNAVAILABLE_IN_GPT_LOCAL_DNS",
    "source_url":source_url,"source_sha256":source_sha,"candidate_sha256":candidate_sha,
    "clean_plate_path":str(clean),"clean_plate_sha256":sha(clean.read_bytes()),
    "native_dimensions":[2048,2048],"format":"DXT5_BC3","raw_orientation":"mirror_y","dds_header_128_identical":True,
    "decoded_changed_outside_source_effect_boxes":outside,
    "decoded_alpha_changed_outside_source_effect_boxes":alpha_outside,
    "rows":details,"machine_result":"PASS" if outside==alpha_outside==0 and all(x["bbox_containment"]=="PASS" for x in details) else "HOLD",
    "visual_result":"PENDING_CONTROLLER_INDEPENDENT_REVIEW",
    "policy_gate":"NO_APPROVAL_WITHOUT_CALIBRATION_AND_COMPLETE_PER_REGION_C_C3_EVIDENCE",
    "runtime_validation":"UNTESTED"}
(out/"C285_Q214_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("C285_SHA",candidate_sha,"machine",report["machine_result"],"outside",outside,alpha_outside)
