#!/usr/bin/env python3
import os, json, hashlib, struct, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-RECOVERY13"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
a8=repo/"localization/graphics/role_A/20261004-A-RECOVERY08"
a8_report_path=a8/"A_RECOVERY08_FD90AA9_REPORT.json"
clean_path=a8/"FD90AA9_CLEAN_PLATE_RECOVERY08.png"
source_mask_path=a8/"FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png"
clean_protected_path=a8/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK_RECOVERY08.png"
c109_path=repo/"localization/graphics/role_C/20261004-C109-PENDING-AND-C075/C109_FD90AA9_MACHINE_QA.json"
validator=repo/"tools/localization/validate_clean_plate.py"

SOURCE_SHA="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
INPUT_SHA="0b7a3138c140617a90207f63eb580c18e953a241951d4832867e8e3ce184338b"

rework_keys=["more_engine","experts_long","for_experts","normal_difficult"]
shear_by_key={
    "more_engine":0.32,
    "experts_long":0.26,
    "for_experts":0.30,
    "normal_difficult":0.27,
}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")
def rect_mask(size,box):
    m=Image.new("L",size,0)
    d=ImageDraw.Draw(m)
    d.rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    return m
def shear_rgba(im,s):
    extra=max(6,int(math.ceil(abs(s)*im.height))+8)
    canvas=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0))
    canvas.paste(im,(extra,0),im)
    coeff=(1,-s,s*canvas.height,0,1,0)
    z=canvas.transform(canvas.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=z.getchannel("A").getbbox()
    if not bb:
        raise RuntimeError("empty sheared layer")
    return z.crop(bb)

if sha(source)!=SOURCE_SHA:
    raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
if sha(candidate)!=INPUT_SHA:
    raise RuntimeError(("input candidate SHA",sha(candidate),INPUT_SHA))

sb=source.read_bytes()
if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1):
    raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4:
    raise RuntimeError(("byte size",len(sb)))

src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

ib=candidate.read_bytes()
if ib[:128]!=sb[:128]:
    raise RuntimeError("input header mismatch")
old_raw=Image.frombytes("RGBA",(W,H),ib[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
clean_protected=Image.open(clean_protected_path).convert("L")
if any(im.size!=(W,H) for im in (clean,source_mask,clean_protected)):
    raise RuntimeError("evidence size mismatch")

a8_report=json.loads(a8_report_path.read_text(encoding="utf-8"))
a8_rows={r["key"]:r for r in a8_report["reworked_rows"]}
if set(a8_rows)!=set(rework_keys):
    raise RuntimeError(("unexpected A8 rework keys",sorted(a8_rows)))

c109=json.loads(c109_path.read_text(encoding="utf-8"))
if c109.get("candidate_sha256")!=INPUT_SHA:
    raise RuntimeError(("C109 candidate mismatch",c109.get("candidate_sha256"),INPUT_SHA))
rows0=list(c109["rows"])
if len(rows0)!=29:
    raise RuntimeError(("C109 row count",len(rows0)))
bykey={r["key"]:r for r in rows0}
for k in rework_keys:
    if k not in bykey:
        raise RuntimeError(("missing C109 row",k))

src_png=out/"FD90AA9_SOURCE_READABLE.png"
clean_png=out/"FD90AA9_CLEAN_PLATE.png"
mask_png=out/"FD90AA9_SOURCE_TEXT_MASK.png"
protected_png=out/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK.png"
src.save(src_png); clean.save(clean_png); source_mask.save(mask_png); clean_protected.save(protected_png)
subprocess.run([
    "python3",str(validator),str(src_png),str(clean_png),str(mask_png),
    "--protected-mask",str(protected_png),
    "--report",str(out/"A_RECOVERY13_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_RECOVERY13_CLEAN_PLATE_VALIDATION.json").read_text(encoding="utf-8"))
if clean_rep["status"]!="PASS":
    raise RuntimeError(("clean plate validator",clean_rep))

final=old.copy()
new_masks={}
new_rows={}
style_meta={}

for key in rework_keys:
    a8r=a8_rows[key]
    oldlb=list(map(int,a8r["localized_bbox"]))
    zone=list(map(int,a8r["placement_zone"]))
    ob=list(map(int,a8r["original_bbox"]))

    old_crop=old.crop(tuple(oldlb))
    clean_crop=clean.crop(tuple(oldlb))
    dm=dmask(clean_crop,old_crop)
    db=dm.getbbox()
    if not db:
        raise RuntimeError(("empty localized delta",key,oldlb))

    layer=Image.new("RGBA",(db[2]-db[0],db[3]-db[1]),(0,0,0,0))
    layer.paste(old_crop.crop(db),(0,0),dm.crop(db))
    slanted=shear_rgba(layer,shear_by_key[key])

    old_actual=[oldlb[0]+db[0],oldlb[1]+db[1],oldlb[0]+db[2],oldlb[1]+db[3]]
    cx=(old_actual[0]+old_actual[2])/2.0
    bottom=old_actual[3]
    tx=int(round(cx-slanted.width/2.0))
    ty=int(round(bottom-slanted.height))

    inset=2
    fit=[max(zone[0],ob[0])+inset,max(zone[1],ob[1])+inset,
         min(zone[2],ob[2])-inset,min(zone[3],ob[3])-inset]
    maxw=fit[2]-fit[0]; maxh=fit[3]-fit[1]
    if maxw<=0 or maxh<=0:
        raise RuntimeError(("invalid fit zone",key,fit))
    if slanted.width>maxw or slanted.height>maxh:
        sc=min(maxw/slanted.width,maxh/slanted.height)
        if sc<=0:
            raise RuntimeError(("no fit",key,slanted.size,fit))
        slanted=slanted.resize((max(1,int(slanted.width*sc)),max(1,int(slanted.height*sc))),Image.Resampling.LANCZOS)
        tx=int(round(cx-slanted.width/2.0))
        ty=int(round(bottom-slanted.height))
    tx=min(max(tx,fit[0]),fit[2]-slanted.width)
    ty=min(max(ty,fit[1]),fit[3]-slanted.height)

    final.paste(clean_crop,(oldlb[0],oldlb[1]))
    final.alpha_composite(slanted,(tx,ty))

    z=tuple(zone)
    lm=dmask(clean.crop(z),final.crop(z))
    bb=lm.getbbox()
    if not bb:
        raise RuntimeError(("final localized layer missing",key))
    loc=[zone[0]+bb[0],zone[1]+bb[1],zone[0]+bb[2],zone[1]+bb[3]]
    gm=Image.new("L",(W,H),0); gm.paste(lm,(zone[0],zone[1]))
    new_masks[key]=gm

    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    new_rows[key]={
        "key":key,"source":a8r["source"],"korean":a8r["korean"],
        "original_bbox":ob,"localized_bbox":loc,
        "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
        "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
        "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
        "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
        "containment":"PASS" if contain else "FAIL",
        "size_ceiling":"PASS" if size_ok else "FAIL",
        "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
        "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
        "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
        "raw_containment":"PASS" if contain else "FAIL",
        "placement_zone":zone,"shear":shear_by_key[key],
        "rework_status":"A_RECOVERY13_SOURCE_SLANT_RERENDER"
    }
    style_meta[key]={
        "shear":shear_by_key[key],
        "input_actual_bbox":old_actual,
        "fit_zone":fit,
        "new_bbox":loc
    }

four_union=Image.new("L",(W,H),0)
ud=ImageDraw.Draw(four_union)
for key in rework_keys:
    ob=bykey[key]["original_bbox"]
    ud.rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
vs_input=dmask(old,final)
changes_vs_input_out=count(ImageChops.multiply(vs_input,ImageOps.invert(four_union)))

unaffected_diffs={}
for r in rows0:
    key=r["key"]
    if key in rework_keys:
        continue
    # Source bboxes overlap semantically adjacent rows in this atlas, so preservation
    # is measured on the accepted localized layer bbox itself. Global confinement to
    # the four returned source bboxes is checked separately below.
    lb=tuple(map(int,r["localized_bbox"]))
    unaffected_diffs[key]=count(dmask(old.crop(lb),final.crop(lb)))

pair_overlap={}
touch_pairs=[]
for i,k1 in enumerate(rework_keys):
    for k2 in rework_keys[i+1:]:
        ov=count(ImageChops.multiply(new_masks[k1],new_masks[k2]))
        if ov:
            pair_overlap[f"{k1}|{k2}"]=ov
        if count(ImageChops.multiply(new_masks[k1].filter(ImageFilter.MaxFilter(3)),new_masks[k2]))>0:
            touch_pairs.append([k1,k2])

preserved_guard_conflicts={}
for key in rework_keys:
    dil=new_masks[key].filter(ImageFilter.MaxFilter(3))
    for r in rows0:
        pk=r["key"]
        if pk in rework_keys:
            continue
        pm=rect_mask((W,H),list(map(int,r["localized_bbox"])))
        c=count(ImageChops.multiply(dil,pm))
        if c:
            preserved_guard_conflicts[f"{key}|{pk}"]=c

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb)
csha=sha(candidate)
decoded_raw=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError("RGBA roundtrip mismatch")
if candidate.read_bytes()[:128]!=sb[:128]:
    raise RuntimeError("final header mismatch")

outside_four=count(ImageChops.multiply(dmask(old,decoded),ImageOps.invert(four_union)))

rows=[]
for r in rows0:
    key=r["key"]
    if key in rework_keys:
        rows.append(new_rows[key])
    else:
        rr=dict(r)
        rr["rework_status"]="C109_PASS_PRESERVED_PIXEL_EXACT"
        rows.append(rr)

all_bbox=all(r.get("containment")=="PASS" for r in rows)
all_size=all(r.get("size_ceiling")=="PASS" for r in rows)
all_changed_positive=all(new_rows[k]["positive_margin"]=="PASS" for k in rework_keys)
all_unaffected_zero=all(v==0 for v in unaffected_diffs.values())
pair_overlap_total=sum(pair_overlap.values())

decoded.save(out/"FD90AA9_FINAL_READABLE.png")
gray(decoded).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A_RECOVERY13_FINAL_READABLE_GRAY_QA.jpg",quality=95)
gray(decoded_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A_RECOVERY13_FINAL_RAW_GRAY_QA.jpg",quality=95)

font=ImageFont.load_default()
contacts=[]
for key in rework_keys:
    ob=list(map(int,bykey[key]["original_bbox"]))
    m=20
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(x.crop(box)) for x in (src,old,decoded)]
    total=sum(x.width for x in ims)+24
    if total>1800:
        sc=(1800-24)/sum(x.width for x in ims)
        ims=[x.resize((max(1,int(x.width*sc)),max(1,int(x.height*sc))),Image.Resampling.LANCZOS) for x in ims]
    row=Image.new("RGB",(sum(x.width for x in ims)+24,max(x.height for x in ims)+24),(235,235,235))
    xx=0
    for im in ims:
        row.paste(im,(xx,24)); xx+=im.width+12
    ImageDraw.Draw(row).text((3,3),key+" SOURCE | OLD | NEW",font=font,fill=(0,0,0))
    contacts.append(row)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+4*(len(contacts)-1)
sheet=Image.new("RGB",(cw,ch),(240,240,240)); yy=0
for x in contacts:
    sheet.paste(x,(0,yy)); yy+=x.height+4
sheet.save(out/"A_RECOVERY13_STYLE_RETURN_CONTACT_SOURCE_OLD_NEW.jpg",quality=96)

status=(
    clean_rep["status"]=="PASS" and all_bbox and all_size and all_changed_positive and
    all_unaffected_zero and changes_vs_input_out==0 and outside_four==0 and
    pair_overlap_total==0 and not touch_pairs and not preserved_guard_conflicts
)

report={
    "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
    "index":121,"asset":asset_rel,"source_sha256":SOURCE_SHA,
    "input_candidate_sha256":INPUT_SHA,"candidate_sha256":csha,
    "candidate_path":str(candidate.relative_to(repo)),
    "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact_source":True,"raw_orientation":"mirror_y"},
    "c109_return_reason":"source typography slant/italic mismatch on More Engine Sound and experts/normal-difficult rows",
    "reworked_keys":rework_keys,"shear_by_key":shear_by_key,
    "method":"preserve A_RECOVERY08 clean plate and source-family Korean fill/outline/effects; materially right-shear only the four C109-returned Korean layers inside their isolated placement zones; preserve the other 25 localized rows and all unrelated atlas pixels exact",
    "clean_plate_validator":clean_rep,
    "style_meta":style_meta,
    "rows":rows,
    "all_29_bbox_pass":all_bbox,
    "all_29_size_ceiling_pass":all_size,
    "all_4_reworked_positive_margin":all_changed_positive,
    "localized_pair_overlap_pixels_reworked":pair_overlap_total,
    "localized_pair_overlaps_reworked":pair_overlap,
    "localized_touch_pairs_reworked":touch_pairs,
    "reworked_vs_preserved_1px_guard_conflicts":preserved_guard_conflicts,
    "changes_vs_input_outside_4_c109_returned_source_bboxes":changes_vs_input_out,
    "decoded_changes_outside_4_c109_returned_source_bboxes":outside_four,
    "preserved_25_input_pixel_diffs":unaffected_diffs,
    "preserved_25_all_zero":all_unaffected_zero,
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED",
    "status":"A_RECOVERY13_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_RECOVERY13_WORKER_REWORK_REQUIRED"
}
(out/"A_RECOVERY13_FD90AA9_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"FD90AA9","index":121,
    "input_candidate_sha256":INPUT_SHA,"candidate_sha256":csha,
    "reworked_rows":4,"preserved_rows":25,
    "bbox_pass":"29/29" if all_bbox else "FAIL",
    "size_ceiling":"29/29" if all_size else "FAIL",
    "reworked_positive_margin":"4/4" if all_changed_positive else "FAIL",
    "clean_plate_validator":clean_rep["status"],
    "reworked_pair_overlap_pixels":pair_overlap_total,
    "reworked_touch_pairs":touch_pairs,
    "reworked_vs_preserved_1px_guard_conflicts":preserved_guard_conflicts,
    "changes_vs_input_outside_4_returned_source_bboxes":changes_vs_input_out,
    "preserved_25_all_zero":all_unaffected_zero,
    "worker_status":report["status"],
    "runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261005-A-RECOVERY13/A_RECOVERY13_FD90AA9_REPORT.json"
}
(wr/"A_RECOVERY13_FD90AA9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status:
    raise SystemExit(2)
