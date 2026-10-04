#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261004-A-RECOVERY09"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
source=Path("/tmp/39229D64_HD.dds")
c_rejected=Path("/tmp/39229D64_C_OVERLAP05_REJECTED.dds")
SOURCE_REPO_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="81c10922293dcdfdc75090c980fb38ee5c3bedd1"
SOURCE_SHA="2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481"
C_WORKER_COMMIT="ddfc5afbff650bfefe6e7de55d39f20a1f109450"
C_REJECTED_SHA="dfa2c39fba8c397191af804767ede25fef35f92b5b21f583130190b701bdb9a4"
validator=repo/"tools/localization/validate_clean_plate.py"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

# Exact authoritative HD source.
url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_REPO_COMMIT}/Release/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
urllib.request.urlretrieve(url,source)
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))
source_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Recover the C_OVERLAP05 rejected machine candidate from exact Git history.
blob=subprocess.check_output(["git","show",f"{C_WORKER_COMMIT}:localization/graphics/hd_candidates/{asset_rel}"])
c_rejected.write_bytes(blob)
if sha(c_rejected)!=C_REJECTED_SHA: raise RuntimeError(("C rejected SHA",sha(c_rejected),C_REJECTED_SHA))
cb=c_rejected.read_bytes()
if cb[:128]!=sb[:128]: raise RuntimeError("C rejected header mismatch")
c_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
c_new=c_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
c_clean=Image.open(repo/"localization/graphics/role_C/20261004-C-OVERLAP05/39229D64_FULL_CLEAN.png").convert("RGBA")
if c_clean.size!=(W,H): raise RuntimeError(("C clean size",c_clean.size))

c_report=json.loads((repo/"localization/graphics/role_C/20261004-C-OVERLAP05/C_OVERLAP05_39229D64_REPORT.json").read_text(encoding="utf-8"))
rows=c_report["rows"]
if len(rows)!=15: raise RuntimeError(("row count",len(rows)))
row_by_key={r["key"]:r for r in rows}

# Background classes. All non-total-rank targets are transparent text/effect overlays in source.
# The three Total Rank labels sit on opaque speech/starburst art and require source-faithful fill reconstruction.
opaque_keys={"total_rank_green","total_rank_brown","total_rank_pink"}
allowed=Image.new("L",(W,H),0)
ad=ImageDraw.Draw(allowed)
clean_arr=np.asarray(src,dtype=np.uint8).copy()
src_arr=np.asarray(src,dtype=np.uint8)

def reconstruct_opaque_rowwise(arr, ob):
    x1,y1,x2,y2=ob
    h=y2-y1; w=x2-x1
    # Sample same-row interior background just outside the exact text/effect bbox.
    # Wide enough to average antialias/glow noise but still inside the speech/starburst interior.
    for yy in range(y1,y2):
        stripes=[]
        if x1>=48: stripes.append(src_arr[yy, x1-48:x1-8])
        if x2+48<=W: stripes.append(src_arr[yy, x2+8:x2+48])
        vals=np.concatenate(stripes,axis=0) if stripes else np.empty((0,4),dtype=np.uint8)
        vals=vals[vals[:,3]>0]
        if len(vals)==0:
            # fallback: median of nontransparent pixels in the source row inside the box
            vals=src_arr[yy,x1:x2]
            vals=vals[vals[:,3]>0]
        if len(vals)==0:
            fill=np.array([0,0,0,0],dtype=np.uint8)
        else:
            # Robust per-row background estimate; source art here is flat/vertical-gradient interior.
            fill=np.median(vals,axis=0).astype(np.uint8)
        arr[yy,x1:x2]=fill

for r in rows:
    ob=list(map(int,r["source_bbox"]))
    x1,y1,x2,y2=ob
    ad.rectangle((x1,y1,x2-1,y2-1),fill=255)
    if r["key"] in opaque_keys:
        reconstruct_opaque_rowwise(clean_arr,ob)
    else:
        clean_arr[y1:y2,x1:x2]=0

clean=Image.fromarray(clean_arr,"RGBA")

# Build source-text/effect mask as source-vs-reconstructed-clean change within each exact permitted bbox.
source_text_mask=changed_mask(src,clean)
# It must not extend outside exact allowed union.
source_text_out=count(ImageChops.multiply(source_text_mask,ImageOps.invert(allowed)))
if source_text_out!=0: raise RuntimeError(("source text mask outside allowed",source_text_out))

# Protected source art is every visible source pixel outside the exact allowed union.
src_visible=src.getchannel("A").point(lambda v:255 if v else 0)
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))
clean_protected=protected.copy()

source_png=out/"39229D64_HD_SOURCE_READABLE.png"
clean_png=out/"39229D64_REPAIRED_CLEAN_PLATE.png"
allowed_png=out/"39229D64_ALLOWED_TEXT_REGION_MASK.png"
source_text_mask_png=out/"39229D64_SOURCE_TEXT_EFFECT_MASK.png"
protected_png=out/"39229D64_PROTECTED_VISIBLE_MASK.png"
clean_protected_png=out/"39229D64_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(source_png); clean.save(clean_png)
allowed.save(allowed_png)
source_text_mask.save(source_text_mask_png)
protected.save(protected_png)
clean_protected.save(clean_protected_png)

subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(source_text_mask_png),
                "--protected-mask",str(clean_protected_png),
                "--report",str(out/"A_RECOVERY09_CLEAN_PLATE_VALIDATION.json")],check=True)
clean_rep=json.loads((out/"A_RECOVERY09_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

# Isolate only the Korean layer that C_OVERLAP05 added over its clean plate.
# This intentionally excludes unchanged source-English residue that caused C's visual rejection.
c_layer_diff=changed_mask(c_clean,c_new)
final=clean.copy()
localized_masks={}
layer_meta={}
for r in rows:
    key=r["key"]; ob=list(map(int,r["source_bbox"])); eb=list(map(int,r["new_effect_bbox"]))
    x1,y1,x2,y2=eb
    dm=c_layer_diff.crop((x1,y1,x2,y2))
    # Keep only nontransparent output pixels from the C machine layer; never reapply erasure/background pixels.
    ca=c_new.crop((x1,y1,x2,y2)).getchannel("A").point(lambda v:255 if v else 0)
    lm=ImageChops.multiply(dm,ca)
    if not lm.getbbox(): raise RuntimeError(("empty localized layer",key))
    crop=c_new.crop((x1,y1,x2,y2))
    final.paste(crop,(x1,y1),lm)
    full=Image.new("L",(W,H),0); full.paste(lm,(x1,y1)); localized_masks[key]=full
    bb=lm.getbbox()
    gb=[x1+bb[0],y1+bb[1],x1+bb[2],y1+bb[3]]
    layer_meta[key]={"localized_bbox":gb,"layer_pixels":count(lm)}

# Exact RGBA32 candidate with original header/raw mirror-Y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb)
cand_sha=sha(candidate)
if outb[:128]!=sb[:128]: raise RuntimeError("candidate header changed")
dec_raw=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")
dec_png=out/"39229D64_FINAL_DECODED_READABLE.png"; dec.save(dec_png)

subprocess.run(["python3",str(validator),str(source_png),str(dec_png),str(allowed_png),
                "--protected-mask",str(protected_png),
                "--report",str(out/"A_RECOVERY09_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A_RECOVERY09_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError(("final validator",final_rep))

diff=changed_mask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=ImageChops.difference(src.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))

# Exact source residue check: no pixel from the source text/effect mask may survive unchanged
# unless it is also part of the newly isolated Korean layer at that pixel.
same=ImageChops.difference(src,dec).point(lambda v:255 if v==0 else 0)
same_rgba=ImageChops.multiply(ImageChops.multiply(same.split()[0],same.split()[1]),ImageChops.multiply(same.split()[2],same.split()[3]))
localized_union=Image.new("L",(W,H),0)
for m in localized_masks.values(): localized_union=ImageChops.lighter(localized_union,m)
residue_mask=ImageChops.multiply(source_text_mask,ImageOps.invert(localized_union))
source_residue_unchanged=count(ImageChops.multiply(residue_mask,same_rgba))

# Pairwise localized overlap must be zero.
keys=list(localized_masks)
pair_overlaps=[]
for i,k1 in enumerate(keys):
    for k2 in keys[i+1:]:
        n=count(ImageChops.multiply(localized_masks[k1],localized_masks[k2]))
        if n: pair_overlaps.append({"a":k1,"b":k2,"pixels":n})
localized_pair_overlap=sum(x["pixels"] for x in pair_overlaps)

qa_rows=[]
for r in rows:
    key=r["key"]; ob=list(map(int,r["source_bbox"])); loc=layer_meta[key]["localized_bbox"]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=loc[2]-loc[0],loc[3]-loc[1]
    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=lw<=sw and lh<=sh
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    qa_rows.append({
      "key":key,"source":r.get("source"),"korean":r.get("korean"),
      "original_bbox":ob,"localized_bbox":loc,
      "source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "raw_containment":"PASS" if contain else "FAIL",
      "layer_pixels":layer_meta[key]["layer_pixels"],
      "style":"C_OVERLAP05 source-matched localized raster/effects reused without source-English pixels",
      "rework_status":"A_RECOVERY09_FULL_BBOX_CLEAN_RECONSTRUCTION"
    })

all_bbox=all(x["containment"]=="PASS" and x["raw_containment"]=="PASS" for x in qa_rows)
all_size=all(x["size_ceiling"]=="PASS" for x in qa_rows)
all_positive=all(x["positive_margin"]=="PASS" for x in qa_rows)

# Persist residue mask for independent review.
residue_mask.save(out/"39229D64_SOURCE_RESIDUE_CHECK_MASK.png")
localized_union.save(out/"39229D64_LOCALIZED_LAYER_UNION_MASK.png")

# Visual evidence. Four panels show exactly why this supersedes C_OVERLAP05.
def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")
thumb=(1024,1024)
panel=Image.new("RGB",(thumb[0]*2,thumb[1]*2),(235,235,235))
panel.paste(gray(src).resize(thumb,Image.Resampling.LANCZOS),(0,0))
panel.paste(gray(c_clean).resize(thumb,Image.Resampling.LANCZOS),(thumb[0],0))
panel.paste(gray(clean).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]))
panel.paste(gray(dec).resize(thumb,Image.Resampling.LANCZOS),(thumb[0],thumb[1]))
pd=ImageDraw.Draw(panel)
try:
    font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR"],text=True).strip()
    labelfont=ImageFont.truetype(font_path,28)
except Exception:
    labelfont=ImageFont.load_default()
for xy,label in [((8,8),"SOURCE"),((1032,8),"C_OVERLAP05 CLEAN (rejected)"),((8,1032),"A09 REPAIRED CLEAN"),((1032,1032),"A09 FINAL")]:
    pd.rectangle((xy[0]-4,xy[1]-4,xy[0]+520,xy[1]+38),fill=(245,245,245))
    pd.text(xy,label,font=labelfont,fill=(0,0,0))
panel.save(out/"A_RECOVERY09_SOURCE_CLEAN_REPAIR_FINAL.jpg",quality=94)

contact=[]
for q in qa_rows:
    ob=q["original_bbox"]; m=16
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    ims=[gray(src.crop((x1,y1,x2,y2))),gray(c_clean.crop((x1,y1,x2,y2))),gray(clean.crop((x1,y1,x2,y2))),gray(dec.crop((x1,y1,x2,y2)))]
    maxw=1200
    total=sum(i.width for i in ims)+24
    if total>maxw:
        sc=(maxw-24)/sum(i.width for i in ims)
        ims=[i.resize((max(1,int(i.width*sc)),max(1,int(i.height*sc))),Image.Resampling.LANCZOS) for i in ims]
    row=Image.new("RGB",(sum(i.width for i in ims)+24,max(i.height for i in ims)+30),(230,230,230))
    xx=0
    for im in ims:
        row.paste(im,(xx,30)); xx+=im.width+8
    ImageDraw.Draw(row).text((3,3),q["key"]+" SRC | C-CLEAN | A09-CLEAN | FINAL",font=labelfont,fill=(0,0,0))
    contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+4*(len(contact)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in contact:
    sheet.paste(im,(0,yy)); yy+=im.height+4
sheet.save(out/"A_RECOVERY09_ROW_CONTACT.jpg",quality=94)
gray(dec_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_RECOVERY09_FINAL_RAW_GRAY.jpg",quality=94)

status_ok=(clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and all_bbox and all_size and all_positive
           and outside==0 and alpha_outside==0 and protected_changed==0 and localized_pair_overlap==0
           and source_residue_unchanged==0)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":57,"asset":asset_rel,
 "return_reason":"C_OVERLAP05 controller visual FAIL: source-English residue/layer overlap despite machine 15/15 placement",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":SOURCE_REPO_COMMIT,"git_blob_sha1":SOURCE_BLOB,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds","classification":"authoritative HD source; DDS header 4096x4096 RGBA32"},
 "source_sha256":SOURCE_SHA,"rejected_c_candidate_sha256":C_REJECTED_SHA,"rejected_c_worker_commit":C_WORKER_COMMIT,
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "repair_method":{
   "clean_plate":"replace full exact source text/effect bbox for all 15 targets; transparent overlays become transparent, three Total Rank labels receive row-wise source-art interior reconstruction",
   "korean_layer":"reuse only C_OVERLAP05 candidate pixels that differ from C_FULL_CLEAN inside each C-validated new_effect_bbox; unchanged English/source residue is intentionally excluded",
   "non_target_art":"source pixels outside exact 15 allowed bboxes remain byte/pixel identical"
 },
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,
   "alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed,
   "source_residue_unchanged_pixels_outside_localized_layers":source_residue_unchanged,
   "localized_pair_overlap_pixels":localized_pair_overlap},
 "pair_overlaps":pair_overlaps,"rows":qa_rows,
 "all_15_readable_and_raw_bbox_pass":all_bbox,"all_15_size_ceiling_pass":all_size,"all_15_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_RECOVERY09_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_RECOVERY09_WORKER_REWORK_REQUIRED"
}
(out/"A_RECOVERY09_39229D64_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"39229D64","index":57,"source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "rejected_c_candidate_sha256":C_REJECTED_SHA,"target_occurrences":15,"bbox_pass":"15/15" if all_bbox else "FAIL",
 "size_ceiling":"15/15" if all_size else "FAIL","positive_margin":"15/15" if all_positive else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
 "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
 "protected_visible_pixels_changed":protected_changed,"source_residue_unchanged_pixels_outside_localized_layers":source_residue_unchanged,
 "localized_pair_overlap_pixels":localized_pair_overlap,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261004-A-RECOVERY09/A_RECOVERY09_39229D64_REPORT.json"}
(worker_out/"A_RECOVERY09_39229D64.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
