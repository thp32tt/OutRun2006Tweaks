#!/usr/bin/env python3
import io, json, hashlib, os, struct, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C131-12519155"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/12519155_256x256.dds"
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION44"
rep=json.loads((bdir/"B_PRODUCTION44_125_REPORT.json").read_text(encoding="utf-8"))
if rep["candidate_sha256"]!="29a10497efcd82ebe6be7101ea9a4e0c830044992e7ffb9ac567d08dd9c444c8":
    raise RuntimeError(("unexpected_input_candidate",rep["candidate_sha256"]))
if rep["structure"]["raw_orientation"]!="mirror_y":
    raise RuntimeError(("unexpected_orientation",rep["structure"]["raw_orientation"]))

source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(source_zip) as z:
    sb=z.read(asset)
candidate=repo/rep["candidate_path"]
cb=candidate.read_bytes()

def sha_bytes(b): return hashlib.sha256(b).hexdigest()

def decode_rgba_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    if len(b)!=128+w*h*4:
        raise RuntimeError(("unexpected_rgba_size",w,h,mips,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":w,"height":h,"mipmaps":mips,"format":"RGBA32","raw_orientation":"mirror_y"}

def mask_png(path):
    return np.asarray(Image.open(path).convert("L"))>0

def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=True
    return m

def bbox(m):
    yy,xx=np.nonzero(m)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def dil(m,px=2):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

if sha_bytes(sb)!=rep["source_sha256"]:
    raise RuntimeError(("source_sha",sha_bytes(sb),rep["source_sha256"]))
if sha_bytes(cb)!=rep["candidate_sha256"]:
    raise RuntimeError(("candidate_sha",sha_bytes(cb),rep["candidate_sha256"]))

src_raw,src_img,meta=decode_rgba_dds(sb)
old_raw,old_img,old_meta=decode_rgba_dds(cb)
if meta!=old_meta or (meta["width"],meta["height"])!=(1024,1024):
    raise RuntimeError(("structure",meta,old_meta))
if sb[:128]!=cb[:128]:
    raise RuntimeError("header mismatch")

src=np.asarray(src_img,dtype=np.uint8)
old=np.asarray(old_img,dtype=np.uint8)
target=mask_png(bdir/"12519155_TARGET_TEXT_MASK.png")
if target.shape!=src.shape[:2]:
    raise RuntimeError(("target_shape",target.shape,src.shape))

allowed=np.zeros(target.shape,bool)
full_source_effect=np.zeros(target.shape,bool)
row_regions=[]
for rr in rep["rows"]:
    ob=list(map(int,rr["original_bbox"]))
    region=rect(target.shape,ob)
    allowed |= region
    # Exact source bbox is text/effect-only for this transparent atlas.
    # C130 residue came from incomplete diff-derived masking, so C131 clears
    # every source alpha pixel inside each exact source text/effect bbox.
    sm=region & (src[:,:,3]>0)
    if not np.any(sm):
        raise RuntimeError(("empty_source_effect",rr["n"],ob))
    full_source_effect |= sm
    row_regions.append((rr,region))

clean=src.copy()
clean[full_source_effect,3]=0

final=clean.copy()
# Reuse only the already accepted Korean target pixels from the current
# mirror-y candidate; no source residue pixels are copied from the old DDS.
final[target]=old[target]

# Encode exact header + mirror-y raw payload.
final_img=Image.fromarray(final,"RGBA")
final_raw=final_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+final_raw.tobytes("raw","RGBA")
candidate.write_bytes(payload)
new_sha=sha_bytes(payload)
new_raw,new_img,new_meta=decode_rgba_dds(payload)
new=np.asarray(new_img,dtype=np.uint8)
if new_meta!=meta or payload[:128]!=sb[:128]:
    raise RuntimeError("structure regression")
if not np.array_equal(new,final):
    raise RuntimeError("roundtrip mismatch")

# Independent static gates.
clean_changed=np.any(clean!=src,axis=2)
clean_out=int(np.count_nonzero(clean_changed & ~full_source_effect))
clean_rgb_changed=int(np.count_nonzero(np.any(clean[:,:,:3]!=src[:,:,:3],axis=2)))
clean_source_alpha_remaining=int(np.count_nonzero(full_source_effect & (clean[:,:,3]>0)))

changed=np.any(new!=src,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((new[:,:,3]!=src[:,:,3]) & ~allowed))
target_out=int(np.count_nonzero(target & ~allowed))
target_invisible=int(np.count_nonzero(target & (new[:,:,3]==0)))
guard=dil(target,2)
residue=int(np.count_nonzero(full_source_effect & (new[:,:,3]>0) & ~guard))

rows=[]
row_masks=[]
for rr,region in row_regions:
    ob=list(map(int,rr["original_bbox"]))
    rm=target & region
    lb=bbox(rm)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    if lb is None:
        contain=size_ok=False; lw=lh=0; d=[None,None,None,None]
    else:
        lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        contain=(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3])
        size_ok=(lw<=sw and lh<=sh)
        d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],"stage_name":bool(rr.get("stage_name")),
      "original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "edge_touch_high_risk":bool(lb is not None and any(x==0 for x in d)),
      "rework_status":"C131_CORRECTIVE_REWORK"
    })
    row_masks.append((str(rr["n"]),rm))

overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i][1]&row_masks[j][1]))
        near=int(np.count_nonzero(dil(row_masks[i][1],1)&row_masks[j][1]))
        overlap+=ov
        if ov or near: touch.append([row_masks[i][0],row_masks[j][0],ov,near])

stage_expected={
 "Alpine":"알파인","Ancient Ruins":"에인션트 루인스","Bay Area":"베이 에어리어",
 "Big Forest":"빅 포레스트","Canyon":"캐니언","Cape Way":"케이프 웨이"
}
policy_ok=all((not r.get("stage_name")) or r["korean"]==stage_expected[r["source"]] for r in rep["rows"])
positive=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and not r["edge_touch_high_risk"] for r in rows)
ok=(clean_out==0 and clean_rgb_changed==0 and clean_source_alpha_remaining==0 and
    outside==0 and alpha_out==0 and target_out==0 and target_invisible==0 and
    residue==0 and overlap==0 and not touch and positive and policy_ok)

# Evidence.
Image.fromarray((full_source_effect.astype(np.uint8)*255),"L").save(out/"C131_FULL_SOURCE_EFFECT_MASK.png")
Image.fromarray(clean,"RGBA").save(out/"C131_CLEAN_PLATE.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"C131_TARGET_TEXT_MASK.png")

def comp(img,bg=(64,64,64,255)):
    z=Image.new("RGBA",img.size,bg); z.alpha_composite(img); return z.convert("RGB")
def card(label,img,bg=(64,64,64,255)):
    v=comp(img,bg); c=Image.new("RGB",(v.width,v.height+26),"white")
    c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c

cards=[card("SOURCE_READABLE",src_img),card("C131_CLEAN",Image.fromarray(clean,"RGBA")),
       card("C131_FINAL",new_img),card("C131_FINAL_WHITE",new_img,(255,255,255,255))]
sheet=Image.new("RGB",(2048,2100),"white")
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0))
sheet.paste(cards[2],(0,1050)); sheet.paste(cards[3],(1024,1050))
sheet.thumbnail((1800,1800),Image.Resampling.LANCZOS)
sheet.save(out/"C131_125_COMPARE.jpg",quality=96)

src_rgb=comp(src_img); clean_rgb=comp(Image.fromarray(clean,"RGBA")); fin_rgb=comp(new_img)
contacts=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]; p=10
    cr=(max(0,x0-p),max(0,y0-p),min(1024,x1+p),min(1024,y1+p))
    ims=[z.crop(cr) for z in (src_rgb,clean_rgb,fin_rgb)]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+26),"white")
    xx=0
    for z in ims: c.paste(z,(xx,26)); xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
row_sheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white")
yy=0
for c in contacts: row_sheet.paste(c,(0,yy)); yy+=c.height+4
row_sheet.save(out/"C131_125_ROW_CONTACT_2X.jpg",quality=96)

raws=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("C131_FINAL_RAW_MIRROR_Y",new_raw)]
raw_sheet=Image.new("RGB",(1024,2100),"white")
raw_sheet.paste(raws[0],(0,0)); raw_sheet.paste(raws[1],(0,1050))
raw_sheet.thumbnail((1200,1800),Image.Resampling.LANCZOS)
raw_sheet.save(out/"C131_125_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"asset":"12519155","queue_index":128,
 "input_candidate_sha256":rep["candidate_sha256"],"candidate_sha256":new_sha,
 "candidate_changed_by_C":True,"corrective_method":"clear all exact-source alpha/effect pixels inside each authoritative source bbox, then composite only the prior accepted Korean target mask",
 "source_sha256":rep["source_sha256"],"structure":meta,"header_128_exact":True,
 "full_source_effect_pixels":int(np.count_nonzero(full_source_effect)),
 "clean_changed_pixels_outside_full_source_effect":clean_out,
 "clean_rgb_changed_pixels":clean_rgb_changed,
 "clean_source_effect_alpha_remaining":clean_source_alpha_remaining,
 "changed_pixels_outside_original_bboxes":outside,
 "alpha_changed_pixels_outside_original_bboxes":alpha_out,
 "target_pixels_outside_original_bboxes":target_out,
 "target_mask_pixels_invisible_in_candidate":target_invisible,
 "source_residue_pixels_outside_2px_target_guard":residue,
 "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,
 "stage_naming_policy":"PASS" if policy_ok else "FAIL","rows":rows,
 "machine_status":"PASS" if ok else "FAIL","controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C131_12519155_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"12519155","index":128,"input_candidate_sha256":rep["candidate_sha256"],
 "candidate_sha256":new_sha,"machine_status":report["machine_status"],
 "bbox_size_pass":f'{sum(1 for r in rows if r["containment"]=="PASS" and r["size_ceiling"]=="PASS")}/{len(rows)}',
 "positive_margin_pass":f'{sum(1 for r in rows if not r["edge_touch_high_risk"])}/{len(rows)}',
 "clean_out":clean_out,"clean_rgb_changed":clean_rgb_changed,"source_residue":residue,
 "outside":outside,"alpha_outside":alpha_out,"overlap":overlap,"touch_pairs":len(touch),
 "stage_naming_policy":report["stage_naming_policy"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_C/{run}/C131_12519155_MACHINE_QA.json"
}
(wr/"C131_12519155.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
if not ok: raise SystemExit(2)
