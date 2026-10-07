#!/usr/bin/env python3
# C228 fresh independent QA for A154 q163 59A79158.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C228-59A79158-A154"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True, exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261007-A-MANUALQA154-59A79158/A154_CLEAN_PLATE.png"
EXPECTED="201044a91730bc9cbde0e68a86a2e39a518d123c7728fdc96d87c9c76d998fa6"
SOURCE_SHA="7cf4f4c63eb95aea8b98a652051eb4c453596c2214124983d63c46a2f152885d"
SOURCE_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_COMMIT}/Release/spr_sprani_sumo_fe_cvt_Exst/59A79158_256x512.dds"

names=[
 ("Waterfalls","워터폴스"),("Tulip Garden","튤립 가든"),("Sunny Beach","서니 비치"),
 ("Snow Mountain","스노 마운틴"),("Skyscrapers","스카이스크레이퍼스"),("Palm Beach","팜 비치"),
 ("National Park","내셔널 파크"),("Milky Way","밀키 웨이"),("Metropolis","메트로폴리스"),
 ("Lost City","로스트 시티"),("Legend","레전드"),("Jungle","정글"),
 ("Industrial Complex","인더스트리얼 컴플렉스"),("Imperial Avenue","임페리얼 애비뉴"),
 ("Ice Scape","아이스스케이프"),("Giant Statues","자이언트 스태추스"),
 ("Ghost Forest","고스트 포레스트"),("Floral Village","플로럴 빌리지"),("Desert","데저트"),
 ("Deep Lake","딥 레이크"),("Coniferous Forest","코니퍼러스 포레스트"),
 ("Cloudy Highland","클라우디 하이랜드"),("Casino Town","카지노 타운"),("Castle Wall","캐슬 월")
]

def sha256(b): return hashlib.sha256(b).hexdigest()

def decode_dds(b):
    if b[:4] != b"DDS ": raise RuntimeError("not DDS")
    height,width,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6])
    mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
    if mode is None: raise RuntimeError(("unsupported pixel masks",masks))
    if len(b) != 128+width*height*4: raise RuntimeError(("unexpected DDS size",len(b),width,height))
    raw=Image.frombytes("RGBA",(width,height),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":width,"height":height,"pitch":pitch,"depth":depth,"mips":mips,"raw_mode":mode}

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def flatten(im):
    z=Image.new("RGB",im.size,(104,104,104))
    z.paste(im.convert("RGB"),mask=im.getchannel("A"))
    return z

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C228"})
with urllib.request.urlopen(req,timeout=90) as r:
    source_bytes=r.read()
candidate_bytes=candidate.read_bytes()
if sha256(source_bytes)!=SOURCE_SHA:
    raise RuntimeError(("source sha drift",sha256(source_bytes)))
if sha256(candidate_bytes)!=EXPECTED:
    raise RuntimeError(("candidate sha drift",sha256(candidate_bytes)))
if source_bytes[:128] != candidate_bytes[:128]:
    raise RuntimeError("header drift")

source_raw,source,source_meta=decode_dds(source_bytes)
final_raw,final,final_meta=decode_dds(candidate_bytes)
if source_meta != final_meta or (source_meta["width"],source_meta["height"])!=(1024,2048):
    raise RuntimeError(("structure mismatch",source_meta,final_meta))

clean=Image.open(clean_path).convert("RGBA")
if clean.size != source.size:
    raise RuntimeError(("clean size mismatch",clean.size,source.size))

sa=np.asarray(source,np.uint8)
fa=np.asarray(final,np.uint8)
ca=np.asarray(clean,np.uint8)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool)
rows=[]
final_masks=[]

for i,(en,ko) in enumerate(names):
    y0=1972-76*i
    y1=y0+76
    x0,x1=0,960
    source_local=sa[y0:y1,x0:x1,3]>0
    ob0=bbox(source_local)
    if not ob0:
        raise RuntimeError(("no source alpha",i,en))
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    source_alpha=np.zeros((H,W),bool)
    source_alpha[ob[1]:ob[3],ob[0]:ob[2]]=sa[ob[1]:ob[3],ob[0]:ob[2],3]>0
    clean_source_alpha=int(np.count_nonzero((ca[:,:,3]>0)&source_alpha))
    if clean_source_alpha:
        raise RuntimeError(("clean source alpha residue",i,en,clean_source_alpha))

    final_local=fa[y0:y1,x0:x1,3]>0
    lb0=bbox(final_local)
    if not lb0:
        raise RuntimeError(("no candidate alpha",i,en))
    lb=[x0+lb0[0],y0+lb0[1],x0+lb0[2],y0+lb0[3]]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0:
        raise RuntimeError(("geometry fail",i,en,ob,lb,margins))

    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    fm=np.zeros((H,W),bool)
    fm[lb[1]:lb[3],lb[0]:lb[2]]=fa[lb[1]:lb[3],lb[0]:lb[2],3]>0
    final_masks.append(fm)
    rows.append({
      "region_idx":i,"source":en,"korean":ko,
      "original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
      "delta_left":margins[0],"delta_right":margins[1],
      "delta_top":margins[2],"delta_bottom":margins[3],
      "clean_source_alpha_remaining":clean_source_alpha,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

diff=np.any(fa!=sa,axis=2)
alpha_diff=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero(alpha_diff & ~allowed))
if outside or alpha_out:
    raise RuntimeError(("candidate changed outside exact source bboxes",outside,alpha_out))

overlap=0
touch=[]
for i in range(len(final_masks)):
    for j in range(i+1,len(final_masks)):
        overlap += int(np.count_nonzero(final_masks[i] & final_masks[j]))
        dil=final_masks[i].copy()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
                ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
                dil[ys,xs] |= final_masks[i][ys2,xs2]
        if np.any(dil & final_masks[j]):
            touch.append([rows[i]["source"],rows[j]["source"]])
if overlap or touch:
    raise RuntimeError(("localized overlap/touch",overlap,touch))

if ImageChops.difference(final_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),final).getbbox() is not None:
    raise RuntimeError("raw/readable parity failure")

# Source naming policy guard: exact mandatory transliterations for this atlas.
policy_map=dict(names)
if len(policy_map)!=24 or len(set(policy_map.values()))!=24:
    raise RuntimeError("semantic mapping cardinality drift")

def card(label,im,max_w=1500,max_h=1100):
    v=flatten(im)
    v.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),(25,25,25))
    c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="white")
    return c

cards=[card("SOURCE_READABLE",source),card("A154_CLEAN",clean),card("A154_FINAL",final)]
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)
sheet=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in cards:
    sheet.paste(c,(0,y)); y+=c.height
sheet.save(out/"C228_59A_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

sf=flatten(source); ff=flatten(final)
contacts=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; pad=8
    cr=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    a=sf.crop(cr); b=ff.crop(cr)
    scale=max(1,min(3,round(900/max(1,a.width))))
    a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST)
    b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(25,25,25))
    d=ImageDraw.Draw(c)
    d.text((4,4),f'{row["region_idx"]:02d} SOURCE {row["source"]}',fill="white")
    d.text((a.width+10,4),f'A154 {row["korean"]}',fill="white")
    c.paste(a,(0,26)); c.paste(b,(a.width+6,26))
    contacts.append(c)
cw=max(c.width for c in contacts)
ch=sum(c.height for c in contacts)+6*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in contacts:
    cs.paste(c,(0,y)); y+=c.height+6
cs.save(out/"C228_59A_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

raw_cards=[card("SOURCE_RAW_MIRROR_Y",source_raw,1000,1200),card("A154_RAW_MIRROR_Y",final_raw,1000,1200)]
rw=max(c.width for c in raw_cards); rh=sum(c.height for c in raw_cards)
rs=Image.new("RGB",(rw,rh),(25,25,25)); y=0
for c in raw_cards:
    rs.paste(c,(0,y)); y+=c.height
rs.save(out/"C228_59A_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

summary={
 "bbox_size_positive_margin":"24/24 PASS",
 "candidate_changed_outside_exact_source_bboxes":outside,
 "candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,
 "localized_pair_overlap_pixels":overlap,
 "localized_touch_pairs":touch,
 "clean_source_alpha_residue_total":sum(r["clean_source_alpha_remaining"] for r in rows),
 "header_128_exact":True,
 "raw_readable_parity":"PASS",
 "canonical_stage_name_mapping":"24/24 PASS"
}
report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C228","queue_index":163,"asset":asset,
 "producer_run":"A154","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":SOURCE_COMMIT,"url":SOURCE_URL},
 "independent_basis":"Pinned canonical BGRA/RGBA32 source independently downloaded/decoded. Exact source/candidate alpha bboxes are re-derived from 24 broad fixed stage-row semantic regions; producer masks are not consumed for containment. Canonical stage-name policy mapping is independently fixed in this job.",
 "machine_status":"PASS","structure":source_meta,"rows":rows,"summary":summary,
 "visual_evidence":[
   str((out/"C228_59A_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
   str((out/"C228_59A_ROW_CONTACT.jpg").relative_to(repo)),
   str((out/"C228_59A_SOURCE_FINAL_RAW.jpg").relative_to(repo))
 ],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C228_59A79158_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
(wr/"C228_59A79158.json").write_text(json.dumps({
 "role":"C","run":"C228","queue_index":163,"asset":asset,
 "source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "machine_status":"PASS",
 "report":str((out/"C228_59A79158_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C228","status":"PASS","summary":summary},ensure_ascii=False))
