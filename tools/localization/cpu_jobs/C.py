#!/usr/bin/env python3
import json, hashlib, os, struct, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C132-12519155"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/12519155_256x256.dds"
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION44"
brep=json.loads((bdir/"B_PRODUCTION44_125_REPORT.json").read_text(encoding="utf-8"))
c131=json.loads((repo/"localization/graphics/role_C/20261005-C131-12519155/C131_12519155_MACHINE_QA.json").read_text(encoding="utf-8"))
candidate=repo/brep["candidate_path"]
cb=candidate.read_bytes()
if hashlib.sha256(cb).hexdigest()!=c131["candidate_sha256"]:
    raise RuntimeError(("unexpected_current_candidate",hashlib.sha256(cb).hexdigest(),c131["candidate_sha256"]))

source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(source_zip) as z: sb=z.read(asset)

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
    if len(b)!=128+w*h*4: raise RuntimeError(("size",w,h,m,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    read=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,read,{"width":w,"height":h,"mipmaps":m,"format":"RGBA32","raw_orientation":"mirror_y"}
def mask_png(p): return np.asarray(Image.open(p).convert("L"))>0
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=True; return m
def dil(m,px=2):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

if sha(sb)!=brep["source_sha256"]: raise RuntimeError(("source_sha",sha(sb),brep["source_sha256"]))
src_raw,src_img,meta=decode(sb); old_raw,old_img,old_meta=decode(cb)
if meta!=old_meta or sb[:128]!=cb[:128]: raise RuntimeError("structure/header mismatch")
src=np.asarray(src_img,dtype=np.uint8); old=np.asarray(old_img,dtype=np.uint8)
target=mask_png(repo/"localization/graphics/role_C/20261005-C131-12519155/C131_TARGET_TEXT_MASK.png")

# C130/C131 visual evidence proved the historical-diff boxes clipped source effect
# fringe. Re-measure each row directly from exact-source alpha, using midpoint bands
# only to separate adjacent semantic rows.
anchors=[list(map(int,r["original_bbox"])) for r in brep["rows"]]
bands=[]
for i,a in enumerate(anchors):
    if i==0: y0=max(0,a[1]-32)
    else: y0=(anchors[i-1][3]+a[1])//2
    if i==len(anchors)-1: y1=min(src.shape[0],a[3]+32)
    else: y1=(a[3]+anchors[i+1][1])//2
    bands.append((y0,y1))

rows=[]; source_masks=[]; allowed=np.zeros(target.shape,bool); full_source=np.zeros(target.shape,bool)
for rr,oldbb,(y0,y1) in zip(brep["rows"],anchors,bands):
    band=np.zeros(target.shape,bool); band[y0:y1,:]=True
    sm=band & (src[:,:,3]>0)
    nb=bb(sm)
    if nb is None: raise RuntimeError(("empty_source_row",rr["n"],y0,y1))
    # Fail closed if unrelated source art unexpectedly broadens the row beyond a
    # reasonable neighborhood of the prior text discovery box.
    if nb[0] < max(0,oldbb[0]-80) or nb[2] > min(src.shape[1],oldbb[2]+80):
        raise RuntimeError(("row_source_scope_ambiguous",rr["n"],oldbb,nb))
    source_masks.append(sm); full_source|=sm; allowed|=rect(target.shape,nb)
    rm=target & rect(target.shape,nb)
    lb=bb(rm)
    sw,sh=nb[2]-nb[0],nb[3]-nb[1]
    if lb is None:
        contain=size_ok=False; lw=lh=0; d=[None]*4
    else:
        lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        contain=lb[0]>=nb[0] and lb[1]>=nb[1] and lb[2]<=nb[2] and lb[3]<=nb[3]
        size_ok=lw<=sw and lh<=sh
        d=[lb[0]-nb[0],nb[2]-lb[2],lb[1]-nb[1],nb[3]-lb[3]]
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],"stage_name":bool(rr.get("stage_name")),
      "previous_original_bbox":oldbb,"original_bbox":nb,"measurement_band_y":[y0,y1],
      "source_size":[sw,sh],"localized_bbox":lb,"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "edge_touch_high_risk":bool(lb is not None and any(x==0 for x in d)),
      "source_effect_pixels":int(np.count_nonzero(sm)),
      "rework_status":"C132_EXACT_SOURCE_ALPHA_REMEASURE"
    })

# Source masks are row-separated by construction.
for i in range(len(source_masks)):
    for j in range(i+1,len(source_masks)):
        if np.any(source_masks[i]&source_masks[j]): raise RuntimeError(("source_row_overlap",i+1,j+1))

clean=src.copy(); clean[full_source,3]=0
final=clean.copy(); final[target]=old[target]
final_img=Image.fromarray(final,"RGBA")
raw=final_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw.tobytes("raw","RGBA")
candidate.write_bytes(payload)
new_sha=sha(payload)
new_raw,new_img,new_meta=decode(payload); new=np.asarray(new_img,dtype=np.uint8)
if new_meta!=meta or payload[:128]!=sb[:128] or not np.array_equal(new,final):
    raise RuntimeError("encode regression")

clean_changed=np.any(clean!=src,axis=2)
clean_out=int(np.count_nonzero(clean_changed & ~full_source))
clean_rgb=int(np.count_nonzero(np.any(clean[:,:,:3]!=src[:,:,:3],axis=2)))
clean_residue=int(np.count_nonzero(full_source & (clean[:,:,3]>0)))
changed=np.any(new!=src,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((new[:,:,3]!=src[:,:,3]) & ~allowed))
target_out=int(np.count_nonzero(target & ~allowed))
target_invisible=int(np.count_nonzero(target & (new[:,:,3]==0)))
guard=dil(target,2)
residue=int(np.count_nonzero(full_source & (new[:,:,3]>0) & ~guard))

row_masks=[target & rect(target.shape,r["original_bbox"]) for r in rows]
overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
        near=int(np.count_nonzero(dil(row_masks[i],1)&row_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])

stage_expected={"Alpine":"알파인","Ancient Ruins":"에인션트 루인스","Bay Area":"베이 에어리어","Big Forest":"빅 포레스트","Canyon":"캐니언","Cape Way":"케이프 웨이"}
policy_ok=all((not r.get("stage_name")) or r["korean"]==stage_expected[r["source"]] for r in brep["rows"])
positive=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and not r["edge_touch_high_risk"] for r in rows)
ok=(clean_out==0 and clean_rgb==0 and clean_residue==0 and outside==0 and alpha_out==0 and
    target_out==0 and target_invisible==0 and residue==0 and overlap==0 and not touch and positive and policy_ok)

Image.fromarray((full_source.astype(np.uint8)*255),"L").save(out/"C132_FULL_SOURCE_EFFECT_MASK.png")
Image.fromarray(clean,"RGBA").save(out/"C132_CLEAN_PLATE.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"C132_TARGET_TEXT_MASK.png")

def comp(img,bg=(64,64,64,255)):
    z=Image.new("RGBA",img.size,bg); z.alpha_composite(img); return z.convert("RGB")
def card(label,img,bg=(64,64,64,255)):
    v=comp(img,bg); c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c

cards=[card("SOURCE_READABLE",src_img),card("C132_CLEAN",Image.fromarray(clean,"RGBA")),card("C132_FINAL",new_img),card("C132_FINAL_WHITE",new_img,(255,255,255,255))]
sheet=Image.new("RGB",(2048,2100),"white"); sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0)); sheet.paste(cards[2],(0,1050)); sheet.paste(cards[3],(1024,1050)); sheet.thumbnail((1800,1800),Image.Resampling.LANCZOS); sheet.save(out/"C132_125_COMPARE.jpg",quality=96)

src_rgb_img=comp(src_img); clean_rgb_img=comp(Image.fromarray(clean,"RGBA")); fin_rgb_img=comp(new_img)
contacts=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; p=10; cr=(max(0,x0-p),max(0,y0-p),min(1024,x1+p),min(1024,y1+p))
    ims=[z.crop(cr) for z in (src_rgb_img,clean_rgb_img,fin_rgb_img)]; ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+26),"white"); xx=0
    for z in ims: c.paste(z,(xx,26)); xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white"); yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+4
rowsheet.save(out/"C132_125_ROW_CONTACT_2X.jpg",quality=96)

raws=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("C132_FINAL_RAW_MIRROR_Y",new_raw)]
rawsheet=Image.new("RGB",(1024,2100),"white"); rawsheet.paste(raws[0],(0,0)); rawsheet.paste(raws[1],(0,1050)); rawsheet.thumbnail((1200,1800),Image.Resampling.LANCZOS); rawsheet.save(out/"C132_125_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"asset":"12519155","queue_index":128,
 "input_candidate_sha256":c131["candidate_sha256"],"candidate_sha256":new_sha,"candidate_changed_by_C":True,
 "corrective_method":"remeasure exact source glyph/effect bboxes from exact-source alpha within row midpoint bands; clear all source alpha in those measured rows; composite only accepted Korean target pixels",
 "source_sha256":brep["source_sha256"],"structure":meta,"header_128_exact":True,
 "full_source_effect_pixels":int(np.count_nonzero(full_source)),
 "clean_changed_pixels_outside_source_effect":clean_out,"clean_rgb_changed_pixels":clean_rgb,
 "clean_source_effect_alpha_remaining":clean_residue,"changed_pixels_outside_original_bboxes":outside,
 "alpha_changed_pixels_outside_original_bboxes":alpha_out,"target_pixels_outside_original_bboxes":target_out,
 "target_mask_pixels_invisible_in_candidate":target_invisible,"source_residue_pixels_outside_2px_target_guard":residue,
 "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,
 "stage_naming_policy":"PASS" if policy_ok else "FAIL","rows":rows,
 "machine_status":"PASS" if ok else "FAIL","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"
}
(out/"C132_12519155_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"12519155","index":128,"input_candidate_sha256":c131["candidate_sha256"],"candidate_sha256":new_sha,
 "machine_status":report["machine_status"],"bbox_size_pass":f'{sum(1 for r in rows if r["containment"]=="PASS" and r["size_ceiling"]=="PASS")}/{len(rows)}',
 "positive_margin_pass":f'{sum(1 for r in rows if not r["edge_touch_high_risk"])}/{len(rows)}',"clean_out":clean_out,"source_residue":residue,
 "outside":outside,"alpha_outside":alpha_out,"overlap":overlap,"touch_pairs":len(touch),"stage_naming_policy":report["stage_naming_policy"],
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C132_12519155_MACHINE_QA.json"}
(wr/"C132_12519155.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
if not ok: raise SystemExit(2)
