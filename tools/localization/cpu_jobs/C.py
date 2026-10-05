#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C178-A05BF610"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

prod=repo/"localization/graphics/role_B/20261005-B-PRODUCTION128"
report=json.loads((prod/"B128_A05_REPORT.json").read_text())
asset=report["asset"]
candidate=repo/report["candidate_path"]
expected_candidate=report["candidate_sha256"]
SOURCE_SHA=report["source_provenance"]["source_sha256"]
COMMIT=report["source_provenance"]["commit"]
source_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
tmp=Path("/tmp/c178"); tmp.mkdir(exist_ok=True)
source=tmp/"source.dds"; urllib.request.urlretrieve(source_url,source)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def decode(data):
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if data[:4]!=b"DDS " or mode is None or len(data)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw,{"W":W,"H":H,"mips":mips,"mode":mode,"header":data[:128]}
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=source.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha",sha(sb),SOURCE_SHA))
if sha(cb)!=expected_candidate: raise RuntimeError(("candidate sha",sha(cb),expected_candidate))
src,raw_src,ss=decode(sb); final,raw_final,cs=decode(cb)
if (ss["W"],ss["H"])!=(2048,2048) or (cs["W"],cs["H"])!=(2048,2048) or cb[:128]!=sb[:128] or cs["mips"]!=ss["mips"]:
    raise RuntimeError("DDS structure/header drift")
# independently downloaded source must match producer evidence
prod_src=Image.open(prod/"A05_SOURCE_READABLE.png").convert("RGBA")
if ImageChops.difference(src,prod_src).getbbox(): raise RuntimeError("producer source PNG mismatch canonical decode")
clean=Image.open(prod/"A05_CLEAN_PLATE.png").convert("RGBA")
sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
ob=[int(v) for v in report["row"]["original_bbox"]]; lb=[int(v) for v in report["row"]["localized_bbox"]]
x0,y0,x1,y1=ob; lx0,ly0,lx1,ly1=lb
allowed=np.zeros((ss["H"],ss["W"]),bool); allowed[y0:y1,x0:x1]=True

# Independent canonical title-core detection in a padded title neighborhood.
# White fill + dark/navy edge are source-title families; reject cyan oval border by hue/brightness.
pad=80; xx0=max(0,x0-pad); yy0=max(0,y0-pad); xx1=min(ss["W"],x1+pad); yy1=min(ss["H"],y1+pad)
roi=sa[yy0:yy1,xx0:xx1]
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>80)&(r>205)&(g>205)&(b>205)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<45)
navy=(a>80)&(b>r+10)&(b>g+4)&(r<120)&(g<135)&(b<210)
core_roi=white|navy
# Restrict to producer bbox for actual title core; neighborhood is used only to ensure no title-colored tail leaks immediately outside.
core=np.zeros((ss["H"],ss["W"]),bool); core[y0:y1,x0:x1]=core_roi[(y0-yy0):(y1-yy0),(x0-xx0):(x1-xx0)]
core_count=count(core)
if core_count<4000: raise RuntimeError(("source core unexpectedly small",core_count))

clean_diff=np.any(ca!=sa,axis=2); final_diff=np.any(fa!=sa,axis=2)
alpha_clean=ca[:,:,3]!=sa[:,:,3]; alpha_final=fa[:,:,3]!=sa[:,:,3]
render=np.any(fa!=ca,axis=2)
clean_out=count(clean_diff&~allowed); final_out=count(final_diff&~allowed)
clean_alpha_out=count(alpha_clean&~allowed); final_alpha_out=count(alpha_final&~allowed)
render_out=count(render&~allowed)
clean_core_unchanged=count(core & np.all(ca==sa,axis=2))
guard=np.asarray(Image.fromarray((render.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
source_core_residue=count(core & np.all(fa==sa,axis=2) & ~guard)
# Detect title-colored unchanged fragments in a 24px ring immediately around the allowed bbox.
ring=np.zeros((ss["H"],ss["W"]),bool)
rx0=max(0,x0-24); ry0=max(0,y0-24); rx1=min(ss["W"],x1+24); ry1=min(ss["H"],y1+24)
ring[ry0:ry1,rx0:rx1]=True; ring[y0:y1,x0:x1]=False
title_like=np.zeros_like(ring)
title_like[yy0:yy1,xx0:xx1]=core_roi
unchanged=np.all(fa==sa,axis=2)
outside_title_like_unchanged=count(ring & title_like & unchanged)

deltas=[lx0-x0,x1-lx1,ly0-y0,y1-ly1]
row_gate={
 "original_bbox":ob,"localized_bbox":lb,
 "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
 "containment":"PASS" if lx0>=x0 and ly0>=y0 and lx1<=x1 and ly1<=y1 else "FAIL",
 "size_ceiling":"PASS" if (lx1-lx0)<=x1-x0 and (ly1-ly0)<=y1-y0 else "FAIL",
 "positive_margin":"PASS" if min(deltas)>0 else "FAIL"
}
machine={
 "clean_changed_outside_original_bbox":clean_out,
 "final_changed_outside_original_bbox":final_out,
 "clean_alpha_outside_original_bbox":clean_alpha_out,
 "final_alpha_outside_original_bbox":final_alpha_out,
 "render_outside_original_bbox":render_out,
 "clean_source_core_unchanged":clean_core_unchanged,
 "source_core_residue_pixels":source_core_residue,
 "unchanged_title_like_pixels_in_24px_outer_ring":outside_title_like_unchanged
}
status="PASS" if row_gate["containment"]=="PASS" and row_gate["size_ceiling"]=="PASS" and row_gate["positive_margin"]=="PASS" and all(v==0 for v in machine.values()) else "FAIL"

# Controller visual evidence: detailed triptych + raw orientation overview.
crop=(max(0,x0-100),max(0,y0-100),min(ss["W"],x1+100),min(ss["H"],y1+100))
ims=[comp(z).crop(crop) for z in (src,clean,final)]
h=max(i.height for i in ims); w=max(i.width for i in ims)
card=Image.new("RGB",(w*3+24,h+36),"white"); d=ImageDraw.Draw(card)
for i,(lab,im) in enumerate(zip(["SOURCE","CLEAN","FINAL"],ims)):
    ox=i*w+8; card.paste(im,(ox,30)); d.text((ox,6),lab,fill="black")
buf=io.BytesIO(); card.save(buf,format="JPEG",quality=97,optimize=True)
(out/"C178_DETAIL_B64.txt").write_text(base64.b64encode(buf.getvalue()).decode("ascii"))

rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(z,(0,i*1035+20)); ImageDraw.Draw(rawcard).text((5,i*1035+3),lab,fill="black")
buf2=io.BytesIO(); rawcard.save(buf2,format="JPEG",quality=94,optimize=True)
(out/"C178_RAW_B64.txt").write_text(base64.b64encode(buf2.getvalue()).decode("ascii"))

outreport={
 "schema_version":1,"role":"C","run":run,"qa_id":"C178","queue_index":28,"asset":asset,
 "producer_run":report["run"],"source_sha256":SOURCE_SHA,"candidate_sha256":expected_candidate,
 "structure":{"dimensions":[ss["W"],ss["H"]],"format":"RGBA32","mipmaps":ss["mips"],"raw_orientation":"mirror_y","header_exact":True},
 "independent_source_decode_matches_producer_png":True,
 "row":row_gate,"source_core_pixels":core_count,"machine_checks":machine,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C178_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED",
 "preview_b64":["C178_DETAIL_B64.txt","C178_RAW_B64.txt"]
}
(out/"C178_A05_MACHINE_QA.json").write_text(json.dumps(outreport,ensure_ascii=False,indent=2)+"\n")
(wr/"C178_A05BF610.json").write_text(json.dumps({
 "run":run,"qa_id":"C178","index":28,"asset":"A05BF610","candidate_sha256":expected_candidate,
 "machine_status":status,"machine_checks":machine,"row":row_gate,
 "report":f"localization/graphics/role_C/{run}/C178_A05_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C178","machine_status":status,"machine_checks":machine,"row":row_gate},ensure_ascii=False))
