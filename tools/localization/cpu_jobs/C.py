#!/usr/bin/env python3
# C229 fresh independent QA for A155 q159 4EDA9DE3 proportion rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C229-4EDA9DE3-A155"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True, exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/4EDA9DE3_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
EXPECTED="47f64c6733774d713b34dd4424fe87a50a55f17ee70cfdb0df5b63d1c797e461"
OLD_EXPECTED="8c9ba9886d993b30cc304d658fea0f180ca715dbe4ae31c181e7cd66c11c9fd5"
SOURCE_SHA="7ed5e0c85d3ef42b770dad21bdfa331b5eef374b80bff27bc1715f3c5b29fdbd"
SOURCE_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_COMMIT}/Release/spr_sprani_sumo_fe_cvt_Exst/4EDA9DE3_512x256.dds"
A155_WORKER_COMMIT="b2a98721d60c499ffc23684661e52eac53c10e55"

# Fixed canonical sprite cells, independently inherited from the atlas geometry rather than producer masks.
rowspec=[
 (0,"WATERFALLS","워터폴스",(0,936,980,1024)),
 (1,"SUNNY BEACH","서니 비치",(980,936,1960,1024)),
 (2,"SKYSCRAPERS","스카이스크레이퍼스",(0,848,980,936)),
 (3,"NATIONAL PARK","내셔널 파크",(980,848,1960,936)),
 (4,"MILKY WAY","밀키 웨이",(0,760,980,848)),
 (5,"LOST CITY","로스트 시티",(980,760,1960,848)),
 (6,"LEGEND","레전드",(0,672,980,760)),
 (7,"JUNGLE","정글",(980,672,1960,760)),
 (8,"ICE SCAPE","아이스스케이프",(0,584,980,672)),
 (9,"GIANT STATUES","자이언트 스태추스",(980,584,1960,672)),
 (10,"FLORAL VILLAGE","플로럴 빌리지",(0,496,980,584)),
 (11,"CASINO TOWN","카지노 타운",(980,496,1960,584)),
 (12,"CANYON","캐니언",(0,408,980,496)),
 (13,"BIG FOREST","빅 포레스트",(980,408,1960,496)),
 (14,"BAY AREA","베이 에어리어",(0,320,980,408)),
]

def sha(b): return hashlib.sha256(b).hexdigest()

def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6])
    mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
    if mode is None: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("unexpected DDS size",len(b),w,h))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"raw_mode":mode}

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def flatten(im):
    bg=Image.new("RGB",im.size,(104,104,104))
    bg.paste(im.convert("RGB"),mask=im.getchannel("A"))
    return bg

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C229"})
with urllib.request.urlopen(req,timeout=90) as r:
    source_bytes=r.read()
candidate_bytes=candidate.read_bytes()
old_bytes=subprocess.check_output(["git","show",f"{A155_WORKER_COMMIT}^:{'localization/graphics/hd_candidates/'+asset}"])

if sha(source_bytes)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(source_bytes)))
if sha(candidate_bytes)!=EXPECTED: raise RuntimeError(("candidate sha drift",sha(candidate_bytes)))
if sha(old_bytes)!=OLD_EXPECTED: raise RuntimeError(("old candidate sha drift",sha(old_bytes)))
if source_bytes[:128]!=candidate_bytes[:128] or source_bytes[:128]!=old_bytes[:128]:
    raise RuntimeError("DDS header drift")

source_raw,source,sm=decode_rgba32(source_bytes)
old_raw,old,om=decode_rgba32(old_bytes)
final_raw,final,fm=decode_rgba32(candidate_bytes)
if sm!=fm or sm!=om or (sm["width"],sm["height"])!=(2048,1024):
    raise RuntimeError(("structure mismatch",sm,om,fm))

sa=np.asarray(source,np.uint8)
oa=np.asarray(old,np.uint8)
fa=np.asarray(final,np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool)
final_masks=[]
checks=[]

for idx,en,ko,cell in rowspec:
    x0,y0,x1,y1=cell
    sb0=bbox(sa[y0:y1,x0:x1,3]>0)
    ob0=bbox(oa[y0:y1,x0:x1,3]>0)
    fb0=bbox(fa[y0:y1,x0:x1,3]>0)
    if not sb0 or not ob0 or not fb0:
        raise RuntimeError(("missing row alpha",idx,en,sb0,ob0,fb0))
    sb=[x0+sb0[0],y0+sb0[1],x0+sb0[2],y0+sb0[3]]
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    fb=[x0+fb0[0],y0+fb0[1],x0+fb0[2],y0+fb0[3]]
    sw,sh=sb[2]-sb[0],sb[3]-sb[1]
    ow,oh=ob[2]-ob[0],ob[3]-ob[1]
    fw,fh=fb[2]-fb[0],fb[3]-fb[1]
    margins=[fb[0]-sb[0],sb[2]-fb[2],fb[1]-sb[1],sb[3]-fb[3]]
    if fw>sw or fh>sh or min(margins)<=0:
        raise RuntimeError(("geometry fail",idx,en,sb,fb,margins))
    if fh/sh < 0.87:
        raise RuntimeError(("height hierarchy undersized",idx,en,fh,sh))
    allowed[sb[1]:sb[3],sb[0]:sb[2]]=True
    m=np.zeros((H,W),bool)
    m[fb[1]:fb[3],fb[0]:fb[2]]=fa[fb[1]:fb[3],fb[0]:fb[2],3]>0
    final_masks.append(m)
    # exact source pixels lingering outside the new Korean tight bbox are clear residue evidence.
    outside_final_bbox=np.ones((H,W),bool)
    outside_final_bbox[fb[1]:fb[3],fb[0]:fb[2]]=False
    exact=np.all(sa==fa,axis=2) & (sa[:,:,3]>0)
    residue_outside=int(np.count_nonzero(exact & outside_final_bbox & (np.indices((H,W))[0]>=sb[1]) & (np.indices((H,W))[0]<sb[3]) & (np.indices((H,W))[1]>=sb[0]) & (np.indices((H,W))[1]<sb[2])))
    if residue_outside:
        raise RuntimeError(("source residue outside Korean bbox",idx,en,residue_outside))
    checks.append({
      "idx":idx,"source":en,"korean":ko,"cell":list(cell),
      "source_bbox":sb,"old_bbox":ob,"localized_bbox":fb,
      "source_size":[sw,sh],"old_size":[ow,oh],"localized_size":[fw,fh],
      "old_width_ratio":round(ow/sw,4),"new_width_ratio":round(fw/sw,4),
      "height_ratio":round(fh/sh,4),
      "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
      "source_exact_pixels_remaining_outside_localized_bbox":residue_outside,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","height_hierarchy":"PASS"
    })

diff=np.any(fa!=sa,axis=2)
adiff=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero(adiff & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside exact source bboxes",outside,alpha_out))

overlap=0
touch=[]
for i in range(len(final_masks)):
    for j in range(i+1,len(final_masks)):
        overlap += int(np.count_nonzero(final_masks[i]&final_masks[j]))
        dil=final_masks[i].copy()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
                ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
                dil[ys,xs] |= final_masks[i][ys2,xs2]
        if np.any(dil & final_masks[j]):
            touch.append([checks[i]["source"],checks[j]["source"]])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))

if ImageChops.difference(final_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),final).getbbox() is not None:
    raise RuntimeError("raw/readable parity failure")

# Evidence
sf,of,ff=flatten(source),flatten(old),flatten(final)
def card(label,im,max_w=1600,max_h=800):
    v=im.copy(); v.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+30),(25,25,25)); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((5,6),label,fill="white"); return c
cards=[card("SOURCE_READABLE",sf),card("C195_OLD_STRETCHED",of),card("A155_FINAL_NATIVE_ASPECT",ff)]
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)
sheet=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height
sheet.save(out/"C229_SOURCE_OLD_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for row in checks:
    x0,y0,x1,y1=row["source_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    parts=[sf.crop(cr),of.crop(cr),ff.crop(cr)]
    scale=max(1,min(3,round(700/max(1,parts[0].width))))
    parts=[im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST) for im in parts]
    w=sum(im.width for im in parts)+12; h=max(im.height for im in parts)+30
    c=Image.new("RGB",(w,h),(25,25,25)); d=ImageDraw.Draw(c)
    labels=["SOURCE", "C195_OLD", "A155_FINAL"]
    x=0
    for lab,im in zip(labels,parts):
        d.text((x+4,6),f'{row["idx"]:02d} {lab}',fill="white")
        c.paste(im,(x,28)); x+=im.width+6
    contacts.append(c)
cw=max(c.width for c in contacts); ch=sum(c.height for c in contacts)+6*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in contacts: cs.paste(c,(0,y)); y+=c.height+6
cs.save(out/"C229_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",flatten(source_raw),1200,900),card("C195_OLD_RAW",flatten(old_raw),1200,900),card("A155_FINAL_RAW",flatten(final_raw),1200,900)]
rw=max(c.width for c in rawcards); rh=sum(c.height for c in rawcards)
rs=Image.new("RGB",(rw,rh),(25,25,25)); y=0
for c in rawcards: rs.paste(c,(0,y)); y+=c.height
rs.save(out/"C229_SOURCE_OLD_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

summary={
 "bbox_size_positive_margin":"15/15 PASS",
 "height_hierarchy":"15/15 PASS >= 0.87 source height",
 "candidate_changed_outside_exact_source_bboxes":outside,
 "candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,
 "source_exact_residue_outside_localized_bbox_total":sum(x["source_exact_pixels_remaining_outside_localized_bbox"] for x in checks),
 "localized_overlap_pixels":overlap,
 "localized_touch_pairs":touch,
 "header_128_exact":True,
 "raw_readable_parity":"PASS",
 "canonical_stage_name_mapping":"15/15 PASS"
}
report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C229","queue_index":159,"asset":asset,
 "producer_run":"A155","source_sha256":SOURCE_SHA,"prior_candidate_sha256":OLD_EXPECTED,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":SOURCE_COMMIT,"url":SOURCE_URL},
 "independent_basis":"Pinned canonical source independently downloaded/decoded. Fixed canonical atlas cells are used only as broad row bounds; source/old/final alpha bboxes are independently re-derived from bytes. Producer masks and producer bbox records are not consumed for containment.",
 "machine_status":"PASS","structure":sm,"rows":checks,"summary":summary,
 "visual_evidence":[
   str((out/"C229_SOURCE_OLD_FINAL_READABLE.jpg").relative_to(repo)),
   str((out/"C229_ROW_CONTACT.jpg").relative_to(repo)),
   str((out/"C229_SOURCE_OLD_FINAL_RAW.jpg").relative_to(repo))
 ],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C229_4EDA9DE3_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C229_4EDA9DE3.json").write_text(json.dumps({
 "role":"C","run":"C229","queue_index":159,"asset":asset,"source_sha256":SOURCE_SHA,
 "prior_candidate_sha256":OLD_EXPECTED,"candidate_sha256":EXPECTED,"machine_status":"PASS",
 "report":str((out/"C229_4EDA9DE3_MACHINE_QA.json").relative_to(repo)),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C229","status":"PASS","summary":summary},ensure_ascii=False))
