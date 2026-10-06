#!/usr/bin/env python3
# C223 independent final QA for A147R q236 FEF70E85.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C223-FEF70E85-A147R"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION80/FEF_CLEAN_PLATE.png"
EXPECTED="e0a01c50df1aefb2a174dc318a1f6a041f0cf3b2759fff8fcafba7d134ec44c8"
SOURCE_SHA="a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
tmp=Path("/tmp/c223"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"src.dds"; atlas_path=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",src_dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_FEF70E85_512x512_atlas.json",atlas_path)

specs=[
 (0,"INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),(1,"WATERFALLS","워터폴스"),
 (2,"TULIP GARDEN","튤립 가든"),(3,"SUNNY BEACH","서니 비치"),
 (4,"SNOW MOUNTAIN","스노 마운틴"),(5,"SKYSCRAPERS","스카이스크레이퍼스"),
 (6,"PALM BEACH","팜 비치"),(7,"NATIONAL PARK","내셔널 파크"),
 (8,"MILKY WAY","밀키 웨이"),(9,"METROPOLIS","메트로폴리스"),
 (10,"LOST CITY","로스트 시티"),(11,"LEGEND","레전드"),
 (12,"JUNGLE","정글"),(13,"IMPERIAL AVENUE","임페리얼 애비뉴")
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not dds")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if mode is None or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mipmaps":mips,"raw_mode":mode}
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect(shape,b):
    m=np.zeros(shape,bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def composite(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255)); bg.alpha_composite(im); return bg.convert("RGB")

if sha(src_dds)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(src_dds)))
if sha(candidate)!=EXPECTED: raise RuntimeError(("candidate drift",sha(candidate)))
sb=src_dds.read_bytes(); cb=candidate.read_bytes()
src_raw,src,sm=decode(sb); cand_raw,cand,cm=decode(cb)
if sm!=cm or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError("clean dimensions")
sa=np.asarray(src,np.uint8); ca=np.asarray(clean,np.uint8); fa=np.asarray(cand,np.uint8)
H,W=sa.shape[:2]
regs={r["idx"]:r for r in json.loads(atlas_path.read_text())["regions"]}

source_mask=np.zeros((H,W),bool)
allowed=np.zeros((H,W),bool)
rows=[]
for idx,en,ko in specs:
    x,y,cw,ch=regs[idx]["rect"]
    alpha=sa[y:y+ch,x:x+cw,3]>0
    ys,xs=np.nonzero(alpha)
    if not len(xs): raise RuntimeError(("empty source",idx))
    ob=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    source_mask[y:y+ch,x:x+cw]|=alpha
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    diff=np.any(fa!=ca,axis=2)&rect((H,W),ob)
    lb=bbox(diff)
    if not lb: raise RuntimeError(("no localized pixels",idx))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("bbox fail",idx,ob,lb,margins))
    rows.append({"region_idx":idx,"source":en,"korean":ko,"original_bbox":ob,"localized_bbox":lb,
                 "source_size":[sw,sh],"localized_size":[lw,lh],
                 "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
                 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

clean_diff=np.any(sa!=ca,axis=2)
clean_out=int(np.count_nonzero(clean_diff&~source_mask))
clean_source_alpha=int(np.count_nonzero(source_mask&(ca[:,:,3]>0)))
if clean_out or clean_source_alpha: raise RuntimeError(("clean gate",clean_out,clean_source_alpha))
final_diff=np.any(fa!=ca,axis=2)
outside=int(np.count_nonzero(final_diff&~allowed))
alpha_out=int(np.count_nonzero((fa[:,:,3]!=ca[:,:,3])&~allowed))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))

x,y,cw,ch=regs[14]["rect"]
protected=int(np.count_nonzero(np.any(sa[y:y+ch,x:x+cw]!=fa[y:y+ch,x:x+cw],axis=2)))
if protected: raise RuntimeError(("protected REVERSED changed",protected))
if ImageChops.difference(cand_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),cand).getbbox() is not None:
    raise RuntimeError("raw/readable parity")

policy=(repo/"localization/graphics/TRANSLATION_NAMING_POLICY.md").read_text(encoding="utf-8")
missing=[ko for _,_,ko in specs if ko not in policy]
if missing: raise RuntimeError(("stage policy missing",missing))

def card(label,im):
    v=composite(im).resize((1024,1024),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,1050),(28,28,28)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
cards=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("A147R_FINAL",cand)]
sheet=Image.new("RGB",(3072,1050),(24,24,24))
for i,c in enumerate(cards): sheet.paste(c,(1024*i,0))
sheet.thumbnail((2100,760),Image.Resampling.LANCZOS)
sheet.save(out/"C223_FEF_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("A147R_RAW_MIRROR_Y",cand_raw)]
rawsheet=Image.new("RGB",(2048,1050),(24,24,24))
for i,c in enumerate(rawcards): rawsheet.paste(c,(1024*i,0))
rawsheet.thumbnail((1800,900),Image.Resampling.LANCZOS)
rawsheet.save(out/"C223_FEF_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

sr=composite(src); fr=composite(cand); contacts=[]
for rr in rows:
    x0,y0,x1,y1=rr["original_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    a=sr.crop(cr); b=fr.crop(cr)
    sc=min(2.0,900/max(1,a.width))
    a=a.resize((max(1,round(a.width*sc)),max(1,round(a.height*sc))),Image.Resampling.NEAREST)
    b=b.resize((max(1,round(b.width*sc)),max(1,round(b.height*sc))),Image.Resampling.NEAREST)
    c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(28,28,28)); d=ImageDraw.Draw(c)
    d.text((4,4),"SOURCE",fill="white"); d.text((a.width+10,4),"A147R_FINAL",fill="white"); c.paste(a,(0,26)); c.paste(b,(a.width+6,26)); contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(24,24,24))
yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+6
rowsheet.thumbnail((2200,12000),Image.Resampling.LANCZOS)
rowsheet.save(out/"C223_FEF_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C223","queue_index":236,"asset":asset,
 "producer_run":"A147R","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "independent_basis":"canonical upstream exact source + C153-validated clean plate + current A147R candidate; source bboxes and candidate diffs re-derived independently",
 "machine_status":"PASS",
 "structure":{"dimensions":[2048,2048],"format":"RGBA32","raw_mode":sm["raw_mode"],"mipmaps":sm["mipmaps"],"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "summary":{"bbox_size_positive_margin":"14/14 PASS","clean_changed_outside_source_mask":clean_out,
            "clean_source_alpha_remaining":clean_source_alpha,"candidate_changed_outside_source_bboxes":outside,
            "candidate_alpha_changed_outside_source_bboxes":alpha_out,"protected_REVERSED_changed_pixels":protected,
            "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION","raw_readable_parity":"PASS"},
 "visual_evidence":[str((out/"C223_FEF_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
                    str((out/"C223_FEF_ROW_CONTACT.jpg").relative_to(repo)),
                    str((out/"C223_FEF_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C223_FEF70E85_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/C223_FEF70E85.json").write_text(json.dumps({
 "role":"C","run":"C223","queue_index":236,"asset":asset,"candidate_sha256":EXPECTED,
 "machine_status":"PASS","report":str((out/"C223_FEF70E85_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C223","candidate":EXPECTED,"machine_status":"PASS","rows":"14/14"},ensure_ascii=False))
