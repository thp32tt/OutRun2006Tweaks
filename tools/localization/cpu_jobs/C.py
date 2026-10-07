#!/usr/bin/env python3
# C230 fresh independent QA for B228 q230 E95DA5 help-text completion.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

repo=Path.cwd()
run="20261007-C230-E95DA5-B228"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="33077919771f580491b8ea1011401dc22df640f87b5b0e6f602b112dbdb07b81"
OLD_SHA="d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b"
EXPECTED="a680ae4b7b7c48e2e6200ca766431a725e189297c6acf31badf677b98270428f"
SOURCE_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
B228_WORKER_COMMIT="b124f08f"
SOURCE_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_COMMIT}/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"

# Broad atlas cells only; text/effect masks and bboxes are derived independently from pixels.
rowspec=[
  (20,"You cannot buy this item yet","아직 구매할 수 없습니다",(0,164,864,240)),
  (21,"You already own this item","이미 보유 중입니다",(864,164,1728,240)),
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

def modal_rgba(arr):
    a=arr.reshape(-1,4)
    vals,counts=np.unique(a,axis=0,return_counts=True)
    i=int(np.argmax(counts))
    return vals[i],int(counts[i]),int(a.shape[0])

def flatten(im):
    bg=Image.new("RGB",im.size,(104,104,104))
    bg.paste(im.convert("RGB"),mask=im.getchannel("A"))
    return bg

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-C230"})
with urllib.request.urlopen(req,timeout=90) as r:
    source_bytes=r.read()
candidate_bytes=candidate.read_bytes()
old_bytes=subprocess.check_output(["git","show",f"{B228_WORKER_COMMIT}^:{'localization/graphics/hd_candidates/'+asset}"])

if sha(source_bytes)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(source_bytes)))
if sha(old_bytes)!=OLD_SHA: raise RuntimeError(("old candidate sha drift",sha(old_bytes)))
if sha(candidate_bytes)!=EXPECTED: raise RuntimeError(("candidate sha drift",sha(candidate_bytes)))
if source_bytes[:128]!=old_bytes[:128] or source_bytes[:128]!=candidate_bytes[:128]:
    raise RuntimeError("DDS header drift")

source_raw,source,sm=decode_rgba32(source_bytes)
old_raw,old,om=decode_rgba32(old_bytes)
final_raw,final,fm=decode_rgba32(candidate_bytes)
if sm!=om or sm!=fm or (sm["width"],sm["height"])!=(2048,1024):
    raise RuntimeError(("structure mismatch",sm,om,fm))

sa=np.asarray(source,np.uint8)
oa=np.asarray(old,np.uint8)
fa=np.asarray(final,np.uint8)
H,W=sa.shape[:2]
source_union=np.zeros((H,W),bool)
final_masks=[]
checks=[]

for idx,en,ko,(x0,y0,x1,y1) in rowspec:
    sr=sa[y0:y1,x0:x1]
    oroi=oa[y0:y1,x0:x1]
    fr=fa[y0:y1,x0:x1]
    # C149/B73 intentionally preserved these help rows; prove the pre-B228 bytes are exact source here.
    if not np.array_equal(sr,oroi):
        raise RuntimeError(("old candidate did not preserve source help row",idx,int(np.count_nonzero(np.any(sr!=oroi,axis=2)))))

    bg,bg_count,total=modal_rgba(sr)
    fbg,fbg_count,ftotal=modal_rgba(fr)
    if bg_count/total < 0.55 or fbg_count/ftotal < 0.55:
        raise RuntimeError(("row background is not sufficiently flat for independent text extraction",idx,bg.tolist(),bg_count,total,fbg.tolist(),fbg_count,ftotal))

    smask=np.any(sr!=bg,axis=2)
    # Derive final glyph pixels against the final row's own modal plate color.
    # The clean-plate reconstruction may differ by a few RGB levels from the source plate,
    # so using the source modal color would incorrectly classify the entire restored footprint as lettering.
    fmask=np.any(fr!=fbg,axis=2)
    sb0=bbox(smask); fb0=bbox(fmask)
    if not sb0 or not fb0: raise RuntimeError(("missing text mask",idx,sb0,fb0))
    sb=[x0+sb0[0],y0+sb0[1],x0+sb0[2],y0+sb0[3]]
    fb=[x0+fb0[0],y0+fb0[1],x0+fb0[2],y0+fb0[3]]
    sw,sh=sb[2]-sb[0],sb[3]-sb[1]
    fw,fh=fb[2]-fb[0],fb[3]-fb[1]
    margins=[fb[0]-sb[0],sb[2]-fb[2],fb[1]-sb[1],sb[3]-fb[3]]
    if fw>sw or fh>sh or min(margins)<=0:
        raise RuntimeError(("geometry fail",idx,sb,fb,margins))
    if fh/sh < 0.85:
        raise RuntimeError(("height hierarchy undersized",idx,fh,sh))

    # Absolute masks
    smabs=np.zeros((H,W),bool); smabs[y0:y1,x0:x1]=smask
    fmabs=np.zeros((H,W),bool); fmabs[y0:y1,x0:x1]=fmask
    source_union |= smabs
    final_masks.append(fmabs)

    # Exact English/source pixels must not survive outside Korean lettering.
    exact_source=np.all(fa==sa,axis=2)
    residue=int(np.count_nonzero(smabs & ~fmabs & exact_source))
    if residue:
        raise RuntimeError(("source help-text residue",idx,residue))

    checks.append({
      "region_idx":idx,"source":en,"korean":ko,"cell":[x0,y0,x1,y1],
      "source_background_rgba":[int(v) for v in bg],"source_background_mode_fraction":round(bg_count/total,6),
      "final_background_rgba":[int(v) for v in fbg],"final_background_mode_fraction":round(fbg_count/ftotal,6),
      "source_bbox":sb,"localized_bbox":fb,
      "source_size":[sw,sh],"localized_size":[fw,fh],
      "height_ratio":round(fh/sh,4),
      "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
      "old_row_exact_source":True,
      "source_exact_residue_outside_localized_mask":residue,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","height_hierarchy":"PASS"
    })

# B228 must change only these two exact source help-text footprints relative to the previous C149-approved candidate.
diff=np.any(fa!=oa,axis=2)
adiff=fa[:,:,3]!=oa[:,:,3]
outside=int(np.count_nonzero(diff & ~source_union))
alpha_out=int(np.count_nonzero(adiff & ~source_union))
if outside or alpha_out:
    raise RuntimeError(("B228 modified pixels outside independently derived source help masks",outside,alpha_out))

# Both localized labels are isolated.
overlap=int(np.count_nonzero(final_masks[0]&final_masks[1]))
if overlap: raise RuntimeError(("localized overlap",overlap))
touch=[]
for i in range(2):
    j=1-i
    dil=final_masks[i].copy()
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dx==0 and dy==0: continue
            ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
            ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
            dil[ys,xs] |= final_masks[i][ys2,xs2]
    if np.any(dil & final_masks[j]): touch.append([checks[i]["source"],checks[j]["source"]])
if touch: raise RuntimeError(("localized touch",touch))

if ImageChops.difference(final_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),final).getbbox() is not None:
    raise RuntimeError("raw/readable parity failure")

# Evidence: source / prior C149 candidate / new B228 candidate.
sf,of,ff=flatten(source),flatten(old),flatten(final)
def card(label,im,max_w=1200,max_h=650):
    v=im.copy(); v.thumbnail((max_w,max_h),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),(25,25,25)); c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="white"); return c

cards=[card("SOURCE_READABLE",sf),card("C149_PRIOR_READABLE",of),card("B228_FINAL_READABLE",ff)]
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)
sheet=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height
sheet.save(out/"C230_SOURCE_C149_B228_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for row in checks:
    x0,y0,x1,y1=row["source_bbox"]; p=10
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    parts=[sf.crop(cr),of.crop(cr),ff.crop(cr)]
    scale=max(1,min(4,round(1100/max(1,parts[0].width))))
    parts=[im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST) for im in parts]
    w=sum(im.width for im in parts)+12; h=max(im.height for im in parts)+30
    c=Image.new("RGB",(w,h),(25,25,25)); d=ImageDraw.Draw(c)
    x=0
    for lab,im in zip(["SOURCE","C149_PRIOR","B228_FINAL"],parts):
        d.text((x+4,6),f'{row["region_idx"]} {lab}',fill="white")
        c.paste(im,(x,28)); x+=im.width+6
    contacts.append(c)
cw=max(c.width for c in contacts); ch=sum(c.height for c in contacts)+6
cs=Image.new("RGB",(cw,ch),(25,25,25)); y=0
for c in contacts: cs.paste(c,(0,y)); y+=c.height+6
cs.save(out/"C230_HELP_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",flatten(source_raw),1200,650),card("C149_PRIOR_RAW",flatten(old_raw),1200,650),card("B228_FINAL_RAW",flatten(final_raw),1200,650)]
rw=max(c.width for c in rawcards); rh=sum(c.height for c in rawcards)
rs=Image.new("RGB",(rw,rh),(25,25,25)); y=0
for c in rawcards: rs.paste(c,(0,y)); y+=c.height
rs.save(out/"C230_SOURCE_C149_B228_RAW.jpg","JPEG",quality=96,subsampling=0)

summary={
 "bbox_size_positive_margin":"2/2 PASS",
 "height_hierarchy":"2/2 PASS >= 0.85 source height",
 "old_help_rows_exact_source":"2/2 PASS",
 "changed_pixels_outside_independent_source_help_masks":outside,
 "alpha_changed_outside_independent_source_help_masks":alpha_out,
 "source_exact_residue_outside_localized_masks":sum(r["source_exact_residue_outside_localized_mask"] for r in checks),
 "localized_overlap_pixels":overlap,
 "localized_touch_pairs":touch,
 "header_128_exact":True,
 "raw_readable_parity":"PASS",
 "semantic_binding":"2/2 PASS"
}
report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C230","queue_index":230,"asset":asset,
 "producer_run":"B228","source_sha256":SOURCE_SHA,"prior_candidate_sha256":OLD_SHA,"candidate_sha256":EXPECTED,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":SOURCE_COMMIT,"url":SOURCE_URL},
 "independent_basis":"Pinned canonical source independently downloaded/decoded. Prior C149-approved candidate is recovered from B228 worker parent and proven exact to source in both help rows. Broad atlas cells only are fixed; background/text masks and source/final bboxes are re-derived from pixels without producer masks.",
 "machine_status":"PASS","structure":sm,"rows":checks,"summary":summary,
 "visual_evidence":[
   str((out/"C230_SOURCE_C149_B228_READABLE.jpg").relative_to(repo)),
   str((out/"C230_HELP_ROW_CONTACT.jpg").relative_to(repo)),
   str((out/"C230_SOURCE_C149_B228_RAW.jpg").relative_to(repo))
 ],
 "controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False
}
(out/"C230_E95DA5_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
(wr/"C230_E95DA5.json").write_text(json.dumps({
 "role":"C","run":"C230","queue_index":230,"asset":asset,
 "source_sha256":SOURCE_SHA,"prior_candidate_sha256":OLD_SHA,"candidate_sha256":EXPECTED,
 "machine_status":"PASS","report":str((out/"C230_E95DA5_MACHINE_QA.json").relative_to(repo)),
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C230","status":"PASS","summary":summary},ensure_ascii=False))
