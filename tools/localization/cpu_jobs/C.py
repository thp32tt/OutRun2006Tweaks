#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C173-A05BF610"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
srcp=Path("/tmp/C173_A05_source.dds")
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
urllib.request.urlretrieve(f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",srcp)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=srcp.read_bytes(); cb=cand.read_bytes()
SOURCE_SHA="52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129"
CAND_SHA="d124775363f3e989a312d13fa0ee17436a28cd927837933b0ea9c8a98a89e6a2"
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=CAND_SHA: raise RuntimeError(("candidate drift",sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS header/length drift")
H,W=struct.unpack_from("<II",sb,12); mips=struct.unpack_from("<I",sb,28)[0]
if (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,len(sb)))

raws=Image.open(srcp).convert("RGBA"); rawf=Image.open(cand).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

# Independently find Total Rank source core only in the oval title band.
x0,x1=400,1050; y0,y1=1120,1330
roi=sa[y0:y1,x0:x1]
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>40)&(r>215)&(g>215)&(b>215)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<35)
navy=(a>40)&(b>r+8)&(b>g+4)&(r<125)&(g<125)&(b<190)
core=np.zeros((H,W),bool); core[y0:y1,x0:x1]=(white|navy)
# Grow to include antialias/effect fringe and derive exact source title effect bbox.
effect=np.asarray(Image.fromarray((core.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(7)))>0
ob=bbox(effect)
if not ob: raise RuntimeError("source title not found")
# Candidate changed pixels should remain inside source title bbox; this is necessary but not sufficient.
allowed=np.zeros((H,W),bool); allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
diff=np.any(sa!=fa,axis=2); ad=sa[:,:,3]!=fa[:,:,3]
outside=count(diff&~allowed); alpha_out=count(ad&~allowed)
# Exact unchanged source-title core proves source-script residue. Remove a small guard around all candidate pixels
# that differ from source; unchanged original core outside that guard is residue even if producer mask missed it.
changed_guard=np.asarray(Image.fromarray((diff.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue_mask=core & ~changed_guard & np.all(sa==fa,axis=2)
residue=count(residue_mask)
rb=bbox(residue_mask)
if residue==0: raise RuntimeError("expected source-script residue was not independently reproduced")

# Evidence, readable and raw.
crop=(max(0,ob[0]-40),max(0,ob[1]-45),min(W,ob[2]+180),min(H,ob[3]+45))
ims=[("SOURCE",src),("FINAL",fin)]
cw,ch=crop[2]-crop[0],crop[3]-crop[1]
sheet=Image.new("RGB",(cw*2,ch+28),"white")
d=ImageDraw.Draw(sheet)
for i,(lab,im) in enumerate(ims):
    sheet.paste(comp(im).crop(crop),(i*cw,28)); d.text((i*cw+4,5),lab,fill="black")
sheet.save(out/"C173_A05_SOURCE_FINAL_DETAIL.jpg",quality=97)
rm=Image.fromarray((residue_mask.astype(np.uint8)*255),"L"); rm.save(out/"C173_A05_SOURCE_RESIDUE_MASK.png")
raw=Image.new("RGB",(1024,1070),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    raw.paste(z,(0,i*535+25)); ImageDraw.Draw(raw).text((5,i*535+5),lab,fill="black")
raw.save(out/"C173_A05_RAW_COMPARE.jpg",quality=94)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C173","queue_index":28,"asset":asset,
 "producer_run":"20261005-B-PRODUCTION115","source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,
 "candidate_changed_by_C":False,
 "independent_method":"Pinned canonical source re-download; exact DDS header/hash/readable+raw orientation; independent white/navy title-core detection in oval title band; exact changed-pixel containment; unchanged canonical source-core residue detection outside changed-pixel guard.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y"},
 "source_effect_bbox":ob,
 "machine_checks":{"decoded_changed_outside_source_effect_bbox":outside,"alpha_changed_outside_source_effect_bbox":alpha_out,
                   "unchanged_source_title_core_residue_pixels":residue,"source_residue_bbox":rb},
 "machine_status":"REWORK_REQUIRED_SOURCE_TEXT_RESIDUE",
 "controller_visual_qa":"PENDING",
 "decision":"C173_REWORK_REQUIRED_SOURCE_TEXT_RESIDUE",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C173_A05_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C173_A05BF610.json").write_text(json.dumps({"run":run,"qa_id":"C173","asset":"A05BF610","index":28,"candidate_sha256":CAND_SHA,
 "machine_status":"REWORK_REQUIRED_SOURCE_TEXT_RESIDUE","source_residue_pixels":residue,
 "report":f"localization/graphics/role_C/{run}/C173_A05_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C173","source_effect_bbox":ob,"outside":outside,"alpha_outside":alpha_out,"source_residue_pixels":residue,"source_residue_bbox":rb},ensure_ascii=False))
