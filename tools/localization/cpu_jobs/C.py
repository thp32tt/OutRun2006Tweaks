#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")

repo=Path.cwd()
run="20261006-C219-37759842"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

producer_dir=repo/"localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX"
pr=json.loads((producer_dir/"A81_37759842_REPORT.json").read_text(encoding="utf-8"))
cand=repo/pr["candidate_path"]
tmp=Path("/tmp/c219"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"
src_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
urllib.request.urlretrieve(src_url,src_dds)

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def decode_rgba_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
    if fourcc!=0 or bpp!=32: raise RuntimeError(("format",fourcc,bpp))
    if (rm,gm,bm)==(0xff,0xff00,0xff0000): mode="RGBA"
    elif (rm,gm,bm)==(0xff0000,0xff00,0xff): mode="BGRA"
    else: raise RuntimeError(("masks",hex(rm),hex(gm),hex(bm),hex(am)))
    raw=Image.frombytes("RGBA",(W,H),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return W,H,pitch,mips,mode,raw,readable

sb=src_dds.read_bytes(); cb=cand.read_bytes()
source_sha=sha256_bytes(sb); candidate_sha=sha256_bytes(cb)
if source_sha!=pr["source_provenance"]["sha256"]: raise RuntimeError(("source hash",source_sha,pr["source_provenance"]["sha256"]))
if candidate_sha!=pr["candidate_sha256"]: raise RuntimeError(("candidate hash",candidate_sha,pr["candidate_sha256"]))
if sb[:128]!=cb[:128]: raise RuntimeError("header mismatch")
W,H,pitch,mips,mode,raws,src=decode_rgba_dds(sb)
W2,H2,pitch2,mips2,mode2,rawf,final=decode_rgba_dds(cb)
if (W,H,pitch,mips,mode)!=(4096,4096,16384,1,"RGBA") or (W2,H2,pitch2,mips2,mode2)!=(W,H,pitch,mips,mode):
    raise RuntimeError(("structure",(W,H,pitch,mips,mode),(W2,H2,pitch2,mips2,mode2)))

producer_src=Image.open(producer_dir/"37759842_HD_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(producer_dir/"37759842_HD_CLEAN_PLATE.png").convert("RGBA")
core_mask=np.asarray(Image.open(producer_dir/"37759842_HD_SOURCE_CORE_MASK.png").convert("L"))>0
protected_mask=np.asarray(Image.open(producer_dir/"37759842_HD_PROTECTED_VISIBLE_MASK.png").convert("L"))>0

sa=np.asarray(src,dtype=np.uint8); psa=np.asarray(producer_src,dtype=np.uint8)
ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
if np.count_nonzero(np.any(sa!=psa,axis=2))!=0: raise RuntimeError("producer source image differs from canonical decode")

allowed=np.zeros((H,W),dtype=bool)
for r in pr["rows"]:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"])
    allowed[y0:y1,x0:x1]=True

clean_changed=np.any(ca!=sa,axis=2)
final_changed=np.any(fa!=sa,axis=2)
alpha_changed=fa[:,:,3]!=sa[:,:,3]
clean_outside=int(np.count_nonzero(clean_changed & ~allowed))
final_outside=int(np.count_nonzero(final_changed & ~allowed))
alpha_outside=int(np.count_nonzero(alpha_changed & ~allowed))
protected_clean=int(np.count_nonzero(np.any(ca!=sa,axis=2) & protected_mask))
protected_final=int(np.count_nonzero(np.any(fa!=sa,axis=2) & protected_mask))
core_clean_unchanged=int(np.count_nonzero(np.all(ca==sa,axis=2) & core_mask))
core_final_source_exact=int(np.count_nonzero(np.all(fa==sa,axis=2) & core_mask))

render=np.any(fa!=ca,axis=2)

def bbox(mask):
    yy,xx=np.nonzero(mask)
    if len(xx)==0: return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]

row_checks=[]
row_masks=[]
for r in pr["rows"]:
    ob=list(map(int,r["source_effect_bbox"]))
    x0,y0,x1,y1=ob
    m=np.zeros((H,W),dtype=bool)
    m[y0:y1,x0:x1]=render[y0:y1,x0:x1]
    lb=bbox(m)
    prod_lb=list(map(int,r["localized_bbox"]))
    sw,sh=x1-x0,y1-y0
    lw,lh=(lb[2]-lb[0],lb[3]-lb[1]) if lb else (0,0)
    contain=bool(lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1)
    size=bool(lb and lw<=sw and lh<=sh)
    margin=bool(lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1)
    exact=(lb==prod_lb)
    row_checks.append({
      "idx":int(r["idx"]),"korean_lines":r["korean_lines"],
      "original_bbox":ob,"localized_bbox_independent":lb,"localized_bbox_producer":prod_lb,
      "localized_bbox_exact_match":exact,
      "source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-x0 if lb else None,"delta_right":x1-lb[2] if lb else None,
      "delta_top":lb[1]-y0 if lb else None,"delta_bottom":y1-lb[3] if lb else None,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL",
      "positive_margin":"PASS" if margin else "FAIL"
    })
    row_masks.append((int(r["idx"]),m))

overlap_pairs=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        n=int(np.count_nonzero(row_masks[i][1] & row_masks[j][1]))
        if n: overlap_pairs.append([row_masks[i][0],row_masks[j][0],n])

bbox_mismatch=sum(1 for r in row_checks if not r["localized_bbox_exact_match"])
row_fail=sum(1 for r in row_checks if r["containment"]!="PASS" or r["size_ceiling"]!="PASS" or r["positive_margin"]!="PASS")
machine_status="PASS" if all(v==0 for v in [clean_outside,final_outside,alpha_outside,protected_clean,protected_final,core_clean_unchanged,core_final_source_exact,bbox_mismatch,row_fail,len(overlap_pairs)]) else "FAIL"

# Independent C evidence using canonical source + producer clean + decoded candidate.
focus_idx=[2,3,4,5,6,7,8,9,10,11,29,43,44,45,46,47,48,49,50,51,52]
focus_rows=[next(r for r in pr["rows"] if int(r["idx"])==i) for i in focus_idx]
cards=[]
for r in focus_rows:
    x0,y0,x1,y1=map(int,r["source_effect_bbox"]); pad=12
    bx0=max(0,x0-pad);by0=max(0,y0-pad);bx1=min(W,x1+pad);by1=min(H,y1+pad)
    ims=[]
    for lab,im in (("SOURCE",src),("CLEAN",clean),("FINAL",final)):
        q=Image.new("RGBA",(bx1-bx0,by1-by0),(90,90,90,255))
        q.alpha_composite(im.crop((bx0,by0,bx1,by1)))
        rgb=q.convert("RGB")
        d=ImageDraw.Draw(rgb); d.rectangle((0,0,rgb.width-1,rgb.height-1),outline=(255,255,255),width=1)
        d.text((3,3),lab,fill=(255,255,0))
        ims.append(rgb)
    h=max(z.height for z in ims); w=sum(z.width for z in ims)
    card=Image.new("RGB",(w,h+20),(200,200,200)); d=ImageDraw.Draw(card); d.text((3,2),f"idx {r['idx']}",fill=(0,0,0))
    xx=0
    for z in ims: card.paste(z,(xx,20)); xx+=z.width
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(180,180,180)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS)
sheet.save(out/"C219_3775_FOCUS_CONTACTS.jpg",quality=90,optimize=True)

# Full readable overview and raw mirror_y.
overview=Image.new("RGB",(3072,1040),(80,80,80))
for i,(lab,im) in enumerate((("SOURCE",src),("CLEAN",clean),("FINAL",final))):
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im)
    q=bg.convert("RGB").resize((1024,1024),Image.Resampling.LANCZOS)
    overview.paste(q,(i*1024,18)); ImageDraw.Draw(overview).text((i*1024+5,2),lab,fill=(255,255,0))
overview.save(out/"C219_3775_SOURCE_CLEAN_FINAL.jpg",quality=91)

rawsheet=Image.new("RGB",(2048,1040),(80,80,80))
for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf))):
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im)
    q=bg.convert("RGB").resize((1024,1024),Image.Resampling.LANCZOS)
    rawsheet.paste(q,(i*1024,18)); ImageDraw.Draw(rawsheet).text((i*1024+5,2),lab,fill=(255,255,0))
rawsheet.save(out/"C219_3775_RAW_COMPARE.jpg",quality=91)

rep={
 "schema_version":1,"role":"C","run":run,"qa_id":"C219","queue_index":95,
 "asset":pr["asset"],"producer_run":pr["run"],"candidate_sha256":candidate_sha,"source_sha256":source_sha,
 "user_ingame_regressions":["IGR-014","IGR-015","IGR-016"],
 "structure":{"dimensions":[W,H],"pitch":pitch,"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "independent_basis":"canonical source DDS decode + current candidate DDS + producer clean/core/protected masks; allowed geometry reconstructed from all 33 producer source-effect bboxes; localized bboxes re-derived from candidate-vs-clean pixels",
 "row_checks":row_checks,
 "machine_checks":{
   "producer_source_vs_canonical_decode_diff_pixels":0,
   "clean_changed_outside_union_source_effect_bboxes":clean_outside,
   "candidate_changed_outside_union_source_effect_bboxes":final_outside,
   "alpha_changed_outside_union_source_effect_bboxes":alpha_outside,
   "protected_clean_changed_pixels":protected_clean,
   "protected_candidate_changed_pixels":protected_final,
   "source_core_exact_pixels_remaining_in_clean":core_clean_unchanged,
   "source_core_exact_pixels_remaining_in_candidate":core_final_source_exact,
   "localized_bbox_mismatches":bbox_mismatch,
   "row_containment_size_margin_failures":row_fail,
   "localized_pair_overlap_count":len(overlap_pairs),
   "localized_pair_overlaps":overlap_pairs
 },
 "machine_status":machine_status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C219_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "backlog_close_allowed":False,
 "preview_files":[
  f"localization/graphics/role_C/{run}/C219_3775_FOCUS_CONTACTS.jpg",
  f"localization/graphics/role_C/{run}/C219_3775_SOURCE_CLEAN_FINAL.jpg",
  f"localization/graphics/role_C/{run}/C219_3775_RAW_COMPARE.jpg"
 ]
}
(out/"C219_37759842_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C219_37759842.json").write_text(json.dumps({
 "run":run,"qa_id":"C219","index":95,"asset":"37759842","candidate_sha256":candidate_sha,
 "machine_status":machine_status,"machine_checks":rep["machine_checks"],
 "report":f"localization/graphics/role_C/{run}/C219_37759842_MACHINE_QA.json",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"candidate_sha256":candidate_sha,"machine_status":machine_status,"checks":rep["machine_checks"]},ensure_ascii=False,indent=2))
if machine_status!="PASS": raise SystemExit(2)
