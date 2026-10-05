#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C171-754F0599"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
srcp=Path("/tmp/C171_754F_source.dds")
urllib.request.urlretrieve(source_url,srcp)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(96,96,96,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def mask_png(m,p): Image.fromarray((m.astype(np.uint8)*255),"L").save(p)

sb=srcp.read_bytes(); cb=cand.read_bytes()
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
CAND_SHA="884f333b7217fd975aec1c1fc81c98bfd4287e52dc60255eb6b06803430b2250"
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(sb)))
if sha(cb)!=CAND_SHA: raise RuntimeError(("candidate sha drift",sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS header/length drift")
H,W=struct.unpack_from("<II",sb,12)
mips=struct.unpack_from("<I",sb,28)[0]
fourcc=sb[84:88]
if (W,H)!=(2048,1024) or mips not in (0,1) or fourcc!=b"\x00\x00\x00\x00" or len(sb)!=(128+W*H*4):
    raise RuntimeError(("DDS structure drift",W,H,mips,fourcc,len(sb)))

raws=Image.open(srcp).convert("RGBA"); rawf=Image.open(cand).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
sm=sa[:,:,3]>0; tm=fa[:,:,3]>0

bands=[(230,397),(397,550),(550,740)]
expected_src=[[6,254,1372,397],[6,397,956,529],[2,566,1386,717]]
expected_fin=[[10,274,1021,377],[10,415,561,510],[6,587,1030,696]]
rows=[]; allowed=np.zeros((H,W),bool); row_targets=[]
for i,(ya,yb) in enumerate(bands):
    s=sm.copy(); s[:ya,:]=False; s[yb:,:]=False
    t=tm.copy(); t[:ya,:]=False; t[yb:,:]=False
    ob=bbox(s); lb=bbox(t)
    if ob!=expected_src[i]: raise RuntimeError(("source bbox drift",i,ob,expected_src[i]))
    if lb!=expected_fin[i]: raise RuntimeError(("candidate bbox drift",i,lb,expected_fin[i]))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    ds=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(ds)<=0: raise RuntimeError(("containment/size/margin fail",i,ob,lb,ds))
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    row_targets.append(t)
    rows.append({"row":i,"original_bbox":ob,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
                 "delta_left":ds[0],"delta_right":ds[1],"delta_top":ds[2],"delta_bottom":ds[3],
                 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

diff=np.any(sa!=fa,axis=2)
ad=sa[:,:,3]!=fa[:,:,3]
outside=count(diff&~allowed)
alpha_out=count(ad&~allowed)
introduced=count(tm&~allowed)
if outside or alpha_out or introduced: raise RuntimeError(("outside change",outside,alpha_out,introduced))

overlap=0; touch=0
for i in range(len(row_targets)):
    for j in range(i+1,len(row_targets)):
        overlap += count(row_targets[i]&row_targets[j])
        dil=np.asarray(Image.fromarray((row_targets[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
        touch += count(dil&row_targets[j])
if overlap or touch: raise RuntimeError(("row overlap/touch",overlap,touch))

guard=np.asarray(Image.fromarray((tm.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(9)))>0
same=np.all(sa==fa,axis=2)
residue=count(sm&~guard&tm&same)
if residue: raise RuntimeError(("source residue",residue))

mask_png(sm,out/"C171_SOURCE_ALPHA_MASK.png")
mask_png(tm,out/"C171_TARGET_ALPHA_MASK.png")

full=Image.new("RGB",(1024,1100),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    full.paste(z,(0,i*550+28)); ImageDraw.Draw(full).text((6,i*550+6),label,fill="black")
full.save(out/"C171_754F_SOURCE_FINAL.jpg",quality=96)

cards=[]
for i,(ob,lb) in enumerate(zip(expected_src,expected_fin)):
    x0=min(ob[0],lb[0]); y0=min(ob[1],lb[1]); x1=max(ob[2],lb[2]); y1=max(ob[3],lb[3]); p=12
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    cw,ch=cr[2]-cr[0],cr[3]-cr[1]
    card=Image.new("RGB",(cw*2,ch*2+26),"white")
    card.paste(comp(src).crop(cr),(0,26))
    card.paste(comp(fin).crop(cr),(cw,26))
    d=ImageDraw.Draw(card); d.text((5,5),f"ROW {i} SOURCE",fill="black"); d.text((cw+5,5),f"ROW {i} FINAL",fill="black")
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+6 for c in cards)),"white")
y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+6
sheet.save(out/"C171_754F_ROW_CONTACT.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C171","queue_index":175,"asset":asset,
 "producer_run":"20261005-A-PRODUCTION29","source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,
 "candidate_changed_by_C":False,
 "independent_method":"Pinned canonical source re-download; exact DDS header/hash check; independent mirror_y decode; exact alpha bbox derivation for three physical rows; containment/size/positive-margin, outside/alpha/introduced-visible, row overlap/touch and source-residue checks.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y"},
 "semantic_binding":[{"source":"stage select","korean":"스테이지 선택"},{"source":"showroom","korean":"쇼룸"},{"source":"single player","korean":"싱글 플레이"}],
 "rows":rows,
 "machine_checks":{"decoded_changed_outside":outside,"alpha_changed_outside":alpha_out,"introduced_visible_outside":introduced,"localized_overlap":overlap,"localized_1px_touch":touch,"source_residue":residue},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C171_754F_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C171_754F0599.json").write_text(json.dumps({"run":run,"qa_id":"C171","asset":"754F0599","index":175,"candidate_sha256":CAND_SHA,"machine_status":"PASS","bbox_size_positive_margin":"3/3","runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C171_754F_MACHINE_QA.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C171","candidate_sha256":CAND_SHA,"machine_status":"PASS","rows":rows},ensure_ascii=False),flush=True)
