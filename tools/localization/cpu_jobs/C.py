#!/usr/bin/env python3
# C225 fresh independent QA for B219 q232 EBFC709F.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, io, json, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C225-EBFC709F-B219"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_C/20261005-C135-EBFC709F/EBFC709F_CLEAN_PLATE.png"
EXPECTED="54ed1e64dde7be9686b882748ab934d3e465d9966289c6ec7772daeeef8f7221"
SOURCE_SHA="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"

regions=[
 ("join_small","JOIN GAME","게임 참가",[0,270,450,370]),
 ("create_small","CREATE GAME","게임 만들기",[870,270,1450,375]),
 ("create_large","CREATE GAME","게임 만들기",[0,660,1280,860]),
 ("join_large","JOIN GAME","게임 참가",[0,850,1020,1024]),
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(data):
    with Image.open(io.BytesIO(data)) as im: return im.convert("RGBA")
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def flatten(im,bg=(105,105,105)):
    z=Image.new("RGB",im.size,bg); z.paste(im.convert("RGB"),mask=im.getchannel("A")); return z

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C225"})
with urllib.request.urlopen(req,timeout=90) as resp: sb=resp.read()
cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source SHA drift",sha(sb)))
if sha(cb)!=EXPECTED: raise RuntimeError(("candidate SHA drift",sha(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header mismatch")
src_raw=decode(sb); fin_raw=decode(cb)
if src_raw.size!=(2048,1024) or fin_raw.size!=src_raw.size: raise RuntimeError(("dimensions",src_raw.size,fin_raw.size))
src=ImageOps.flip(src_raw); fin=ImageOps.flip(fin_raw)
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))
sa=np.asarray(src,np.uint8); ca=np.asarray(clean,np.uint8); fa=np.asarray(fin,np.uint8)
H,W=sa.shape[:2]

# Independent source/clean difference per broad semantic region derives exact source effect bboxes.
rows=[]
allowed=np.zeros((H,W),bool)
source_effect_union=np.zeros((H,W),bool)
localized_union=np.zeros((H,W),bool)
for key,en,ko,r in regions:
    x0,y0,x1,y1=r
    diff_sc=np.any(sa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    ob0=bb(diff_sc)
    if not ob0: raise RuntimeError(("no source-clean effect",key))
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    source_effect_union[ob[1]:ob[3],ob[0]:ob[2]] |= np.any(sa[ob[1]:ob[3],ob[0]:ob[2]]!=ca[ob[1]:ob[3],ob[0]:ob[2]],axis=2)
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    diff_fc=np.any(fa[ob[1]:ob[3],ob[0]:ob[2]]!=ca[ob[1]:ob[3],ob[0]:ob[2]],axis=2)
    lb0=bb(diff_fc)
    if not lb0: raise RuntimeError(("no final localized pixels",key))
    lb=[ob[0]+lb0[0],ob[1]+lb0[1],ob[0]+lb0[2],ob[1]+lb0[3]]
    localized_union[lb[1]:lb[3],lb[0]:lb[2]] |= np.any(fa[lb[1]:lb[3],lb[0]:lb[2]]!=ca[lb[1]:lb[3],lb[0]:lb[2]],axis=2)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("geometry fail",key,ob,lb,margins))
    rows.append({"key":key,"source":en,"korean":ko,"original_bbox":ob,"localized_bbox":lb,
                 "source_size":[sw,sh],"localized_size":[lw,lh],
                 "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
                 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

all_final_diff=np.any(fa!=ca,axis=2)
all_alpha_diff=fa[:,:,3]!=ca[:,:,3]
outside=int(np.count_nonzero(all_final_diff & ~allowed))
alpha_out=int(np.count_nonzero(all_alpha_diff & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside allowed",outside,alpha_out))

# Clean plate must equal source outside exact source-effect union.
clean_diff=np.any(sa!=ca,axis=2)
clean_out=int(np.count_nonzero(clean_diff & ~source_effect_union))
if clean_out: raise RuntimeError(("clean changed outside exact source effect",clean_out))

# No residual source-effect pixel within removed heading footprints where clean is transparent / changed.
# This is conservative: candidate pixel exactly equal to source within source-effect mask counts residue only if not part of localized diff.
source_exact=np.all(fa==sa,axis=2)
residue=int(np.count_nonzero(source_effect_union & source_exact & ~localized_union))
if residue: raise RuntimeError(("source effect residue",residue))

# Pair overlap/touch on derived localized masks.
row_masks=[]
for row in rows:
    x0,y0,x1,y1=row["localized_bbox"]
    m=np.zeros((H,W),bool)
    m[y0:y1,x0:x1]=np.any(fa[y0:y1,x0:x1]!=ca[y0:y1,x0:x1],axis=2)
    row_masks.append(m)
overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        overlap += int(np.count_nonzero(row_masks[i]&row_masks[j]))
        # 1px dilation by shifts without scipy
        dil=row_masks[i].copy()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
                ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
                dil[ys,xs]|=row_masks[i][ys2,xs2]
        if np.any(dil & row_masks[j]): touch.append([rows[i]["key"],rows[j]["key"]])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))

if ImageChops.difference(ImageOps.flip(fin_raw),fin).getbbox() is not None: raise RuntimeError("raw/readable parity")

# Evidence
def make_card(label,im):
    v=flatten(im)
    v.thumbnail((1536,768),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),(24,24,24)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c

cards=[make_card("SOURCE_READABLE",src),make_card("C135_VALIDATED_CLEAN",clean),make_card("B219_FINAL",fin)]
w=max(c.width for c in cards); h=sum(c.height for c in cards)
sheet=Image.new("RGB",(w,h),(24,24,24)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height
sheet.save(out/"C225_EBFC_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
sf=flatten(src); ff=flatten(fin)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=10; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    a=sf.crop(cr); b=ff.crop(cr); scale=max(1,min(3,round(900/max(1,a.width))))
    a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST)
    b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(24,24,24)); d=ImageDraw.Draw(c)
    d.text((4,4),"SOURCE",fill="white"); d.text((a.width+10,4),"B219_FINAL",fill="white"); c.paste(a,(0,26)); c.paste(b,(a.width+6,26)); contacts.append(c)
cw=max(c.width for c in contacts); ch=sum(c.height for c in contacts)+6*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(24,24,24)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+6
cs.save(out/"C225_EBFC_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawcards=[make_card("SOURCE_RAW_MIRROR_Y",src_raw),make_card("B219_RAW_MIRROR_Y",fin_raw)]
rw=max(c.width for c in rawcards); rh=sum(c.height for c in rawcards)
rs=Image.new("RGB",(rw,rh),(24,24,24)); yy=0
for c in rawcards: rs.paste(c,(0,yy)); yy+=c.height
rs.save(out/"C225_EBFC_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C225","queue_index":232,"asset":asset,
 "producer_run":"B219","source_sha256":SOURCE_SHA,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"pinned canonical source decoded independently; exact source effect bboxes re-derived as SOURCE-vs-C135 independently validated CLEAN changes within broad semantic regions; final localized diffs re-derived from current candidate vs CLEAN",
 "machine_status":"PASS","structure":{"dimensions":[2048,1024],"format":"RGBA32","header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "summary":{"bbox_size_positive_margin":"4/4 PASS","candidate_changed_outside_exact_source_bboxes":outside,
            "candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,
            "clean_changed_outside_exact_source_effect":clean_out,"source_effect_residue_pixels":residue,
            "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,"raw_readable_parity":"PASS"},
 "visual_evidence":[str((out/"C225_EBFC_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),
                    str((out/"C225_EBFC_ROW_CONTACT.jpg").relative_to(repo)),
                    str((out/"C225_EBFC_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C225_EBFC709F_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C225_EBFC709F.json").write_text(json.dumps({"role":"C","run":"C225","queue_index":232,"asset":asset,
 "candidate_sha256":EXPECTED,"machine_status":"PASS","report":str((out/"C225_EBFC709F_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C225","status":"PASS","rows":rows,"summary":report["summary"]},ensure_ascii=False))
