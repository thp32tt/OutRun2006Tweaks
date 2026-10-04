#!/usr/bin/env python3
import io, json, hashlib, os, struct, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
branch="korean-localization-recovery-20260928"
run="20261005-C129-12519155"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/12519155_256x256.dds"
bdir="localization/graphics/role_B/20261005-B-PRODUCTION44"
breport_path=f"{bdir}/B_PRODUCTION44_125_REPORT.json"
fail_path=f"{bdir}/B_PRODUCTION44_FAIL_CLOSED.json"

subprocess.run(["git","fetch","origin",branch],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)

def branch_bytes(path):
    p=repo/path
    if p.exists():
        return p.read_bytes()
    cp=subprocess.run(["git","show",f"origin/{branch}:{path}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if cp.returncode:
        raise FileNotFoundError(path)
    return cp.stdout

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def rgba_dds(b,orientation):
    if b[:4]!=b"DDS ":
        raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    if len(b)!=128+w*h*4:
        raise RuntimeError(("unexpected_rgba_size",w,h,mips,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    if orientation=="rotate_180":
        readable=raw.transpose(Image.Transpose.ROTATE_180)
    elif orientation=="mirror_x":
        readable=raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif orientation=="mirror_y":
        readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    elif orientation=="identity":
        readable=raw.copy()
    else:
        raise RuntimeError(("unknown_orientation",orientation))
    return raw,readable,{"width":w,"height":h,"mipmaps":mips,"format":"RGBA32","raw_orientation":orientation}

def load_rgba(path):
    return Image.open(io.BytesIO(branch_bytes(path))).convert("RGBA")

def load_mask(path):
    return np.asarray(Image.open(io.BytesIO(branch_bytes(path))).convert("L"))>0

def bbox(mask):
    y,x=np.nonzero(mask)
    if not len(x):
        return None
    return [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]

def rect(shape,b):
    h,w=shape
    x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool)
    m[y0:y1,x0:x1]=True
    return m

def dil(mask,px=2):
    return np.asarray(Image.fromarray((mask.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

try:
    rep=json.loads(branch_bytes(breport_path).decode("utf-8"))
except FileNotFoundError:
    try:
        fail=json.loads(branch_bytes(fail_path).decode("utf-8"))
    except FileNotFoundError:
        fail={"status":"B44_OUTPUT_NOT_FOUND"}
    blocked={
      "schema_version":1,"role":"C","run":run,"asset":"12519155","queue_index":128,
      "machine_status":"BLOCKED_BY_B_PRODUCTION44","producer_state":fail,
      "controller_visual_qa":"NOT_RUN","runtime_validation":"UNTESTED"
    }
    (out/"C129_12519155_MACHINE_QA.json").write_text(json.dumps(blocked,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"C129_12519155.json").write_text(json.dumps(blocked,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(blocked,ensure_ascii=False))
    raise SystemExit(0)

source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(source_zip) as z:
    sb=z.read(asset)
cb=branch_bytes(rep["candidate_path"])
if sha_bytes(sb)!=rep["source_sha256"]:
    raise RuntimeError(("source_sha_mismatch",sha_bytes(sb),rep["source_sha256"]))
if sha_bytes(cb)!=rep["candidate_sha256"]:
    raise RuntimeError(("candidate_sha_mismatch",sha_bytes(cb),rep["candidate_sha256"]))

orientation=rep["structure"]["raw_orientation"]
src_raw,src_img,src_meta=rgba_dds(sb,orientation)
cand_raw,cand_img,cand_meta=rgba_dds(cb,orientation)
if src_meta!=cand_meta or src_meta["width"]!=1024 or src_meta["height"]!=1024:
    raise RuntimeError(("structure",src_meta,cand_meta))
header_exact=sb[:128]==cb[:128]

src=np.asarray(src_img,dtype=np.uint8)
cand=np.asarray(cand_img,dtype=np.uint8)
clean_img=load_rgba(f"{bdir}/12519155_CLEAN_PLATE.png")
clean=np.asarray(clean_img,dtype=np.uint8)
source_mask=load_mask(f"{bdir}/12519155_SOURCE_TEXT_MASK.png")
producer_target=load_mask(f"{bdir}/12519155_TARGET_TEXT_MASK.png")
if not (src.shape==cand.shape==clean.shape):
    raise RuntimeError(("shape",src.shape,cand.shape,clean.shape))

allowed=np.zeros(source_mask.shape,bool)
for rr in rep["rows"]:
    allowed |= rect(source_mask.shape,rr["original_bbox"])

clean_changed=np.any(clean!=src,axis=2)
clean_changed_out=int(np.count_nonzero(clean_changed & ~source_mask))
clean_rgb_changed=int(np.count_nonzero(np.any(clean[:,:,:3]!=src[:,:,:3],axis=2)))
clean_source_alpha_remaining=int(np.count_nonzero(source_mask & (clean[:,:,3]>0)))

changed=np.any(cand!=src,axis=2)
outside=int(np.count_nonzero(changed & ~allowed))
alpha_out=int(np.count_nonzero((cand[:,:,3]!=src[:,:,3]) & ~allowed))
target_out=int(np.count_nonzero(producer_target & ~allowed))
target_invisible=int(np.count_nonzero(producer_target & (cand[:,:,3]==0)))
target_guard=dil(producer_target,2)
source_residue=int(np.count_nonzero(source_mask & (cand[:,:,3]>0) & ~target_guard))

stage_policy={
 "Alpine":"알파인",
 "Ancient Ruins":"에인션트 루인스",
 "Bay Area":"베이 에어리어",
 "Big Forest":"빅 포레스트",
 "Canyon":"캐니언",
 "Cape Way":"케이프 웨이"
}
rows=[]
row_masks=[]
policy_ok=True
for rr in rep["rows"]:
    ob=list(map(int,rr["original_bbox"]))
    region=rect(source_mask.shape,ob)
    rm=producer_target & region
    lb=bbox(rm)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    if lb is None:
        contain=size_ok=False
        lw=lh=0
        deltas=[None,None,None,None]
    else:
        lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        contain=(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3])
        size_ok=(lw<=sw and lh<=sh)
        deltas=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    edge=lb is not None and any(d==0 for d in deltas)
    expected=(stage_policy.get(rr["source"]) if rr.get("stage_name") else
              ("타임 어택 모드 / 15코스" if rr["source"]=="Time Attack Mode / 15 C." else rr["korean"]))
    this_policy=(rr["korean"]==expected)
    policy_ok=policy_ok and this_policy
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],
      "stage_name":bool(rr.get("stage_name")),"expected_korean":expected,
      "translation_policy":"PASS" if this_policy else "FAIL",
      "original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":deltas[0],"delta_right":deltas[1],
      "delta_top":deltas[2],"delta_bottom":deltas[3],
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size_ok else "FAIL",
      "edge_touch_high_risk":edge,
      "rework_status":"C129_REVALIDATED"
    })
    row_masks.append((str(rr["n"]),rm))

pair_overlap=0
touch_pairs=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i][1] & row_masks[j][1]))
        near=int(np.count_nonzero(dil(row_masks[i][1],1) & row_masks[j][1]))
        pair_overlap += ov
        if ov or near:
            touch_pairs.append([row_masks[i][0],row_masks[j][0],ov,near])

positive=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and not r["edge_touch_high_risk"] for r in rows)
ok=(header_exact and len(rows)==7 and clean_changed_out==0 and clean_rgb_changed==0 and
    clean_source_alpha_remaining==0 and outside==0 and alpha_out==0 and target_out==0 and
    target_invisible==0 and source_residue==0 and pair_overlap==0 and not touch_pairs and
    positive and policy_ok)

res={
 "schema_version":1,"role":"C","run":run,"asset":"12519155","queue_index":128,
 "producer_run":"B_PRODUCTION44","producer_report":breport_path,
 "source_sha256":rep["source_sha256"],"candidate_sha256":rep["candidate_sha256"],
 "structure":cand_meta,"header_128_exact":header_exact,
 "clean_changed_pixels_outside_source_mask":clean_changed_out,
 "clean_rgb_changed_pixels":clean_rgb_changed,
 "clean_source_mask_alpha_remaining":clean_source_alpha_remaining,
 "changed_pixels_outside_original_bboxes":outside,
 "alpha_changed_pixels_outside_original_bboxes":alpha_out,
 "target_pixels_outside_original_bboxes":target_out,
 "target_mask_pixels_invisible_in_candidate":target_invisible,
 "source_residue_pixels_outside_2px_target_guard":source_residue,
 "localized_pair_overlap_pixels":pair_overlap,
 "localized_touch_pairs":touch_pairs,
 "stage_naming_policy":"PASS" if policy_ok else "FAIL",
 "rows":rows,
 "machine_status":"PASS" if ok else "FAIL",
 "controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C129_12519155_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def composite(img,bg=(64,64,64,255)):
    z=Image.new("RGBA",img.size,bg)
    z.alpha_composite(img)
    return z.convert("RGB")

def card(label,img,bg=(64,64,64,255)):
    v=composite(img,bg)
    c=Image.new("RGB",(v.width,v.height+26),"white")
    c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="black")
    return c

cards=[card("SOURCE_READABLE",src_img),card("CLEAN",clean_img),card("FINAL",cand_img),card("FINAL_WHITE",cand_img,(255,255,255,255))]
sheet=Image.new("RGB",(2048,2100),"white")
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0))
sheet.paste(cards[2],(0,1050)); sheet.paste(cards[3],(1024,1050))
sheet.thumbnail((1800,1800),Image.Resampling.LANCZOS)
sheet.save(out/"C129_125_COMPARE.jpg",quality=96)

src_rgb=composite(src_img); clean_rgb=composite(clean_img); fin_rgb=composite(cand_img)
contacts=[]
for r in rows:
    x0,y0,x1,y1=r["original_bbox"]
    p=10
    cr=(max(0,x0-p),max(0,y0-p),min(1024,x1+p),min(1024,y1+p))
    ims=[z.crop(cr) for z in (src_rgb,clean_rgb,fin_rgb)]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+26),"white")
    xx=0
    for z in ims:
        c.paste(z,(xx,26)); xx+=z.width+6
    ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
row_sheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white")
yy=0
for c in contacts:
    row_sheet.paste(c,(0,yy)); yy+=c.height+4
row_sheet.save(out/"C129_125_ROW_CONTACT_2X.jpg",quality=96)

raws=[card("SOURCE_RAW_MIRROR_X",src_raw),card("FINAL_RAW_MIRROR_X",cand_raw)]
raw_sheet=Image.new("RGB",(1024,2100),"white")
raw_sheet.paste(raws[0],(0,0)); raw_sheet.paste(raws[1],(0,1050))
raw_sheet.thumbnail((1200,1800),Image.Resampling.LANCZOS)
raw_sheet.save(out/"C129_125_RAW_COMPARE.jpg",quality=96)

summary={
 "run":run,"asset":"12519155","index":128,
 "candidate_sha256":rep["candidate_sha256"],
 "machine_status":res["machine_status"],
 "bbox_size_pass":f'{sum(1 for r in rows if r["containment"]=="PASS" and r["size_ceiling"]=="PASS")}/{len(rows)}',
 "positive_margin_pass":f'{sum(1 for r in rows if not r["edge_touch_high_risk"])}/{len(rows)}',
 "outside":outside,"alpha_outside":alpha_out,"source_residue":source_residue,
 "localized_overlap_pixels":pair_overlap,"touch_pairs":len(touch_pairs),
 "stage_naming_policy":res["stage_naming_policy"],
 "runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_C/{run}/C129_12519155_MACHINE_QA.json"
}
(wr/"C129_12519155.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
