#!/usr/bin/env python3
import os, json, hashlib, struct, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-RECOVERY12"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
a10=repo/"localization/graphics/role_A/20261004-A-RECOVERY10"
a10_report=a10/"A_RECOVERY10_C075FB49_REPORT.json"
clean_path=a10/"C075FB49_CLEAN_PLATE.png"
allowed_path=a10/"C075FB49_ALLOWED_TEXT_REGION_MASK.png"
protected_path=a10/"C075FB49_PROTECTED_MASK.png"
top_source_mask_path=a10/"C075FB49_TOP_SOURCE_TEXT_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

SOURCE_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
INPUT_SHA="fc75a1a1b267dbc43f240483ffc1ec67e3d3dddd05061e504ab4c0c4ca2efacd"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)

if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
if sha(candidate)!=INPUT_SHA: raise RuntimeError(("input candidate SHA",sha(candidate),INPUT_SHA))

sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(2048,2048,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

ib=candidate.read_bytes()
if ib[:128]!=sb[:128]: raise RuntimeError("input header mismatch")
cur_raw=Image.frombytes("RGBA",(W,H),ib[128:],"raw","RGBA")
cur=cur_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

clean=Image.open(clean_path).convert("RGBA")
allowed=Image.open(allowed_path).convert("L")
protected=Image.open(protected_path).convert("L")
top_source_mask=Image.open(top_source_mask_path).convert("L")
if clean.size!=(W,H) or allowed.size!=(W,H) or protected.size!=(W,H): raise RuntimeError("evidence size mismatch")

rep=json.loads(a10_report.read_text(encoding="utf-8"))
rows0=list(rep["rows"])
if len(rows0)!=17: raise RuntimeError(("row count",len(rows0)))
bykey={r["key"]:r for r in rows0}

# C109 returned only the dense top source-style families; lower nine remain accepted and must stay exact.
rework_keys=[
 "long_distance","keep_passing","drift","maximum_speed",
 "transmission","dont_crash","go_gate","for_experts"
]
preserve_keys=[r["key"] for r in rows0 if r["key"] not in rework_keys]

# Material right-leaning source-family slant. Top is shifted right relative to bottom.
shear_by_key={
 "long_distance":0.34,
 "keep_passing":0.24,
 "drift":0.20,
 "maximum_speed":0.28,
 "transmission":0.30,
 "dont_crash":0.24,
 "go_gate":0.24,
 "for_experts":0.30,
}

# Validate A_RECOVERY10 clean plate remains source-residue free before lettering.
clean_top_residue=count(ImageChops.multiply(balpha(clean),top_source_mask))
if clean_top_residue!=0: raise RuntimeError(("A10 clean top residue",clean_top_residue))

# Clean plate changes are still constrained by the exact persisted A10 policy masks.
src_png=out/"C075FB49_SOURCE_READABLE.png"; src.save(src_png)
clean_png=out/"C075FB49_CLEAN_PLATE.png"; clean.save(clean_png)
allowed_png=out/"C075FB49_ALLOWED_TEXT_REGION_MASK.png"; allowed.save(allowed_png)
protected_png=out/"C075FB49_PROTECTED_MASK.png"; protected.save(protected_png)
top_source_mask.save(out/"C075FB49_TOP_SOURCE_TEXT_MASK.png")
subprocess_args=[
 "python3",str(validator),str(src_png),str(clean_png),str(allowed_png),
 "--protected-mask",str(protected_png),"--report",str(out/"A_RECOVERY12_CLEAN_PLATE_VALIDATION.json")
]
import subprocess
subprocess.run(subprocess_args,check=True)
clean_rep=json.loads((out/"A_RECOVERY12_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

def extract_delta_layer(box):
    box=tuple(map(int,box))
    cc=clean.crop(box); curc=cur.crop(box)
    m=dmask(cc,curc)
    bb=m.getbbox()
    if not bb: raise RuntimeError(("empty input localized layer",box))
    # Crop to the actual localized delta, not the whole bbox.
    m=m.crop(bb); curc=curc.crop(bb)
    layer=Image.new("RGBA",m.size,(0,0,0,0))
    layer.paste(curc,(0,0),m)
    return layer

def shear_rgba(im,s):
    if not s: return im.copy()
    # Pillow affine maps output -> input. This coefficient produces top-right lean.
    extra=max(4,int(math.ceil(abs(s)*im.height))+6)
    canvas=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0))
    canvas.paste(im,(extra,0),im)
    coeff=(1,-s,s*canvas.height,0,1,0)
    outim=canvas.transform(canvas.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=outim.getchannel("A").getbbox()
    if not bb: raise RuntimeError("empty sheared layer")
    return outim.crop(bb)

# Start from the exact accepted A_RECOVERY10 candidate so all lower nine labels and
# unrelated atlas pixels remain byte/pixel-identical. Only the eight C109-returned
# localized top layers are replaced from the verified A10 clean plate.
final=cur.copy()
masks={}
rows=[]
input_preserved_diffs={}

# Top eight: shear the current source-family Korean raster/effects; keep bottom/left anchor close to prior placement.
meta={}
for key in rework_keys:
    r=bykey[key]
    oldlb=list(map(int,r["localized_bbox"]))
    old_crop=cur.crop(tuple(oldlb))
    old_clean=clean.crop(tuple(oldlb))
    dm=dmask(old_clean,old_crop)
    db=dm.getbbox()
    if not db: raise RuntimeError(("top delta missing",key))
    layer=Image.new("RGBA",(db[2]-db[0],db[3]-db[1]),(0,0,0,0))
    layer.paste(old_crop.crop(db),(0,0),dm.crop(db))
    sh=shear_rgba(layer,shear_by_key[key])

    ob=list(map(int,r["original_bbox"]))
    # Old effective delta anchor, then right-lean grows mainly to the right.
    tx=oldlb[0]+db[0]
    ty=oldlb[1]+db[1]
    # Fail closed if source-style slant no longer fits exact source bbox with a positive inset.
    if tx<=ob[0]: tx=ob[0]+2
    if ty<=ob[1]: ty=ob[1]+2
    if tx+sh.width>=ob[2]:
        # Only horizontal fit is needed; preserve height and slant while narrowing minimally.
        maxw=ob[2]-tx-2
        if maxw<=0: raise RuntimeError(("no horizontal fit",key,ob,tx,sh.size))
        sh=sh.resize((maxw,sh.height),Image.Resampling.LANCZOS)
    if ty+sh.height>=ob[3]:
        maxh=ob[3]-ty-2
        if maxh<=0: raise RuntimeError(("no vertical fit",key,ob,ty,sh.size))
        scale=maxh/sh.height
        sh=sh.resize((max(1,int(sh.width*scale)),maxh),Image.Resampling.LANCZOS)
    # Remove only the old localized layer footprint by restoring its verified clean plate.
    # The old localized bboxes are mutually separated and contain no preserved source labels.
    final.paste(old_clean,(oldlb[0],oldlb[1]))
    final.alpha_composite(sh,(tx,ty))
    meta[key]={"shear":shear_by_key[key],"anchor":[tx,ty],"preencode_bbox":[tx,ty,tx+sh.width,ty+sh.height]}

# Per-label masks are candidate-vs-clean changes restricted to each non-overlapping localized placement.
for r in rows0:
    key=r["key"]; ob=list(map(int,r["original_bbox"]))
    if key in rework_keys:
        pb=meta[key]["preencode_bbox"]
        zone=pb
    else:
        zone=list(map(int,r["localized_bbox"]))
    z=tuple(zone)
    lm=dmask(clean.crop(z),final.crop(z))
    bb=lm.getbbox()
    if not bb: raise RuntimeError(("final label missing",key))
    loc=[zone[0]+bb[0],zone[1]+bb[1],zone[0]+bb[2],zone[1]+bb[3]]
    gm=Image.new("L",(W,H),0); gm.paste(lm,(zone[0],zone[1])); masks[key]=gm
    ok=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    pos=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    rows.append({
      "key":key,"source":r["source"],"korean":r["korean"],
      "original_bbox":ob,"localized_bbox":loc,
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if pos else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "raw_containment":"PASS" if ok else "FAIL",
      "shear":meta[key]["shear"] if key in meta else "PRESERVED_A10_EXACT",
      "rework_status":"A_RECOVERY12_SOURCE_SLANT_RERENDER" if key in rework_keys else "A10_PRESERVED_EXACT"
    })

# Exact pair-overlap and 1px-touch gates.
pair_overlap={}
touch_pairs=[]
keys=list(masks)
for i,k1 in enumerate(keys):
    for k2 in keys[i+1:]:
        ov=count(ImageChops.multiply(masks[k1],masks[k2]))
        if ov: pair_overlap[f"{k1}|{k2}"]=ov
        # 1-pixel neighborhood conflict: dilate k1 by one pixel then intersect k2.
        dil=masks[k1].filter(ImageFilter.MaxFilter(3)) if False else None
# PIL ImageFilter only needed for touch. Import lazily.
from PIL import ImageFilter
for i,k1 in enumerate(keys):
    dil=masks[k1].filter(ImageFilter.MaxFilter(3))
    for k2 in keys[i+1:]:
        if count(ImageChops.multiply(dil,masks[k2]))>0:
            touch_pairs.append([k1,k2])

pair_overlap_total=sum(pair_overlap.values())

# Encode exact RGBA32 with canonical header and raw mirror-Y storage.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb); csha=sha(candidate)
decoded_raw=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip")
final_png=out/"C075FB49_FINAL_READABLE.png"; decoded.save(final_png)

subprocess.run([
 "python3",str(validator),str(src_png),str(final_png),str(allowed_png),
 "--protected-mask",str(protected_png),"--report",str(out/"A_RECOVERY12_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_RECOVERY12_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError(("final validator",final_rep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
top_residue=count(ImageChops.multiply(balpha(clean),top_source_mask))

# Changes vs input must be confined to C109-returned top source boxes.
failed_allowed=Image.new("L",(W,H),0); fd=ImageDraw.Draw(failed_allowed)
for key in rework_keys:
    ob=bykey[key]["original_bbox"]; fd.rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
vs_input=dmask(cur,decoded)
changes_vs_input_out=count(ImageChops.multiply(vs_input,ImageOps.invert(failed_allowed)))

# Lower nine are exact preserved input pixels inside their original source bboxes.
for key in preserve_keys:
    ob=tuple(map(int,bykey[key]["original_bbox"]))
    input_preserved_diffs[key]=count(dmask(cur.crop(ob),decoded.crop(ob)))

# Preserved source English labels remain exact.
preserved_source_cells={
 "OutRun2SP":[1104,24,1592,128],
 "OutRun2":[1592,24,2048,128],
 "1P":[1840,144,1992,248],
}
preserved_source_diffs={}
for key,box in preserved_source_cells.items():
    preserved_source_diffs[key]=count(dmask(src.crop(tuple(box)),decoded.crop(tuple(box))))

all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_pos=all(r["positive_margin"]=="PASS" for r in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")

thumb=(1024,1024)
sheet=Image.new("RGB",(1024,3072),(64,64,64))
for i,im in enumerate([src,cur,decoded]):
    sheet.paste(gray(im).resize(thumb,Image.Resampling.LANCZOS),(0,i*1024))
sheet.save(out/"A_RECOVERY12_SOURCE_OLD_FINAL_GRAY.jpg",quality=95)

# Dense top SOURCE|OLD|NEW evidence at native width for typography comparison.
crop=(0,0,2048,440)
top=Image.new("RGB",(2048,440*3),(64,64,64))
for i,im in enumerate([src,cur,decoded]):
    top.paste(gray(im.crop(crop)),(0,i*440))
top.save(out/"A_RECOVERY12_TOP_SOURCE_OLD_FINAL.jpg",quality=95)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_RECOVERY12_FINAL_RAW_GRAY.jpg",quality=95)

# Row contacts for the eight style-reworked labels.
font=ImageFont.load_default()
contacts=[]
for key in rework_keys:
    ob=bykey[key]["original_bbox"]; m=12
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(x.crop(box)) for x in [src,cur,decoded]]
    total=sum(x.width for x in ims)+24
    if total>1500:
        sc=(1500-24)/sum(x.width for x in ims)
        ims=[x.resize((max(1,int(x.width*sc)),max(1,int(x.height*sc))),Image.Resampling.LANCZOS) for x in ims]
    row=Image.new("RGB",(sum(x.width for x in ims)+24,max(x.height for x in ims)+24),(230,230,230)); xx=0
    for im in ims: row.paste(im,(xx,24)); xx+=im.width+12
    ImageDraw.Draw(row).text((3,3),key+" SOURCE | OLD | NEW",font=font,fill=(0,0,0)); contacts.append(row)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contacts: cs.paste(x,(0,yy)); yy+=x.height+4
cs.save(out/"A_RECOVERY12_TOP_ROW_CONTACT_SOURCE_OLD_NEW.jpg",quality=95)

status=(
 clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and
 all_bbox and all_size and all_pos and pair_overlap_total==0 and len(touch_pairs)==0 and
 outside==0 and alpha_out==0 and prot==0 and top_residue==0 and changes_vs_input_out==0 and
 all(v==0 for v in input_preserved_diffs.values()) and all(v==0 for v in preserved_source_diffs.values())
)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "index":111,"asset":asset_rel,"source_sha256":SOURCE_SHA,
 "input_candidate_sha256":INPUT_SHA,"candidate_sha256":csha,
 "candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "c109_return_reason":"source style slant/italic mismatch on dense top source families",
 "reworked_keys":rework_keys,"shear_by_key":shear_by_key,"preserved_keys":preserve_keys,
 "method":"reuse A_RECOVERY10 source-clean plate and source-family Korean raster/effects; apply material right-lean affine slant to only the eight C109-returned top labels; preserve lower nine exact input pixels and canonical OutRun2SP/OutRun2/1P source pixels",
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "rows":rows,"all_17_readable_and_raw_bbox_pass":all_bbox,"all_17_size_ceiling_pass":all_size,"all_17_positive_margin":all_pos,
 "localized_pair_overlap_pixels":pair_overlap_total,"localized_pair_overlaps":pair_overlap,"localized_touch_pairs":touch_pairs,
 "decoded_changes":{"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"top_clean_source_residue_pixels":top_residue,"changes_vs_input_outside_8_c109_returned_bboxes":changes_vs_input_out},
 "preserved_lower_input_pixel_diffs":input_preserved_diffs,"preserved_source_label_pixel_diffs":preserved_source_diffs,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_RECOVERY12_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_RECOVERY12_WORKER_REWORK_REQUIRED"
}
(out/"A_RECOVERY12_C075FB49_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"C075FB49","index":111,"input_candidate_sha256":INPUT_SHA,"candidate_sha256":csha,
 "reworked_rows":8,"preserved_rows":9,"bbox_pass":"17/17" if all_bbox else "FAIL","size_ceiling":"17/17" if all_size else "FAIL","positive_margin":"17/17" if all_pos else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],"localized_pair_overlap_pixels":pair_overlap_total,"localized_touch_pairs":touch_pairs,
 "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"top_clean_source_residue_pixels":top_residue,"changes_vs_input_outside_8_c109_returned_bboxes":changes_vs_input_out,
 "preserved_lower_input_pixel_diffs":input_preserved_diffs,"preserved_source_label_pixel_diffs":preserved_source_diffs,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-RECOVERY12/A_RECOVERY12_C075FB49_REPORT.json"
}
(wr/"A_RECOVERY12_C075FB49.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
