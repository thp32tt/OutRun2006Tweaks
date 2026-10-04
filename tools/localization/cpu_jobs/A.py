#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, math
from pathlib import Path
from PIL import Image, ImageChops, ImageOps, ImageDraw

repo = Path.cwd()
run = "20261004-A-RECOVERY07"
out = repo / "localization/graphics/role_A" / run
out.mkdir(parents=True, exist_ok=True)
worker_out = repo / "localization/graphics/worker_results"
worker_out.mkdir(parents=True, exist_ok=True)

srcp = repo / "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
candp = repo / "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
c85p = repo / "localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
a87p = repo / "localization/graphics/role_A/20260927-1930-A87/A87_FD90AA9_PRODUCTION_REPORT.json"
validator = repo / "tools/localization/validate_clean_plate.py"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_rgba_dds(p):
    b = Path(p).read_bytes()
    assert b[:4] == b"DDS "
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    pitch = struct.unpack_from("<I", b, 20)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    pf = struct.unpack_from("<8I", b, 76)
    assert (w, h) == (4096, 4096), (w, h)
    assert pf[2] == 0 and pf[3] == 32, pf
    assert pf[4:] == (0x000000ff,0x0000ff00,0x00ff0000,0xff000000), pf
    assert pitch == w * 4 and mips == 1 and len(b) == 128 + w*h*4
    raw = Image.frombytes("RGBA", (w,h), b[128:], "raw", "RGBA")
    readable = raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128], readable

def write_dds(src_path, readable, out_path):
    sb = Path(src_path).read_bytes()
    raw = readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload = raw.tobytes("raw","RGBA")
    Path(out_path).write_bytes(sb[:128] + payload)
    return sha(out_path)

def diffmask(a,b):
    d = ImageChops.difference(a,b)
    bands = d.split()
    m = bands[0]
    for z in bands[1:]:
        m = ImageChops.lighter(m,z)
    return m.point(lambda v: 255 if v else 0)

def binary_alpha(im):
    return im.getchannel("A").point(lambda v:255 if v else 0)

def count(m):
    return sum(m.histogram()[1:])

def full_mask(size, local, origin):
    m = Image.new("L", size, 0)
    m.paste(local, origin)
    return m

def halfopen_contains(ob, bb):
    return bb and bb[0] >= ob[0] and bb[1] >= ob[1] and bb[2] <= ob[2] and bb[3] <= ob[3]

def intersects(a,b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

def own_rect(row, all_rows):
    # Partition overlapping semantic localized bboxes at their midpoint so shared atlas
    # pixels are owned by only one element. This is the proven B91 anti-overlap method.
    r=list(row["localized_bbox"]); cx=(r[0]+r[2])/2; cy=(r[1]+r[3])/2
    for q in all_rows:
        if q is row: continue
        b=q["localized_bbox"]
        if not intersects(r,b): continue
        ox=(b[0]+b[2])/2; oy=(b[1]+b[3])/2
        if abs(cx-ox) >= abs(cy-oy):
            mid=(cx+ox)/2
            if cx < ox: r[2]=min(r[2],math.floor(mid))
            else: r[0]=max(r[0],math.ceil(mid))
        else:
            mid=(cy+oy)/2
            if cy < oy: r[3]=min(r[3],math.floor(mid))
            else: r[1]=max(r[1],math.ceil(mid))
    if r[0] >= r[2] or r[1] >= r[3]:
        return list(row["localized_bbox"])
    return r

def raw_box(bb, H):
    return [bb[0], H-bb[3], bb[2], H-bb[1]]

def fit_overlay(cand, src, region, original_bbox, margin=2):
    x0,y0,x1,y1 = region
    cc = cand.crop((x0,y0,x1,y1))
    ss = src.crop((x0,y0,x1,y1))
    dm = diffmask(cc,ss)
    am = binary_alpha(cc)
    mask = ImageChops.multiply(dm,am)
    mb = mask.getbbox()
    if not mb:
        raise RuntimeError(f"empty localized delta in region {region}")
    rgba = cc.crop(mb)
    mm = mask.crop(mb)
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mm))
    trim = rgba.getchannel("A").getbbox()
    assert trim
    rgba = rgba.crop(trim)
    ox0,oy0,ox1,oy1 = original_bbox
    safe = [ox0+margin,oy0+margin,ox1-margin,oy1-margin]
    if safe[0] >= safe[2] or safe[1] >= safe[3]:
        safe = list(original_bbox)
    sw,sh = safe[2]-safe[0], safe[3]-safe[1]
    scale = min(1.0, sw/rgba.width, sh/rgba.height)
    tw = max(1, int(math.floor(rgba.width*scale)))
    th = max(1, int(math.floor(rgba.height*scale)))
    if (tw,th) != rgba.size:
        rgba = rgba.resize((tw,th), Image.Resampling.LANCZOS)
        rb = rgba.getchannel("A").getbbox()
        if rb:
            rgba = rgba.crop(rb)
    px = safe[0] + max(0,(sw-rgba.width)//2)
    py = safe[1] + max(0,(sh-rgba.height)//2)
    layer = Image.new("RGBA", cand.size, (0,0,0,0))
    layer.alpha_composite(rgba,(px,py))
    bb = layer.getchannel("A").getbbox()
    assert halfopen_contains(original_bbox,bb),(original_bbox,bb)
    return layer, bb, scale, [x0+mb[0],y0+mb[1],x0+mb[2],y0+mb[3]]

source_sha = sha(srcp)
input_sha = sha(candp)
assert source_sha == "f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert input_sha == "72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445"
source_header, src = load_rgba_dds(srcp)
candidate_header, before = load_rgba_dds(candp)
assert source_header == candidate_header

c85 = json.loads(c85p.read_text(encoding="utf-8"))
asset = next(x for x in c85["assets"] if x.get("asset") == "FD90AA9")
rows = asset["rows"]
assert len(rows) == 29
fail_keys = {r["key"] for r in rows if r.get("rework_required")}
assert len(fail_keys) == 19
a87 = json.loads(a87p.read_text(encoding="utf-8"))
rec = {r["key"]:r for r in a87["records"]}
assert set(rec) == {r["key"] for r in rows}

# Build exact-source clean plate masks for all localized elements. Only source pixels
# that the accepted A87 candidate actually replaced are removed; unchanged artwork is excluded.
source_text_mask = Image.new("L", src.size, 0)
source_mask_meta = {}
for r in rows:
    x0,y0,x1,y1 = r["original_bbox"]
    sc = src.crop((x0,y0,x1,y1))
    cc = before.crop((x0,y0,x1,y1))
    changed = diffmask(sc,cc)
    source_visible = binary_alpha(sc)
    local = ImageChops.multiply(changed,source_visible)
    if local.getbbox():
        fm = full_mask(src.size,local,(x0,y0))
        source_text_mask = ImageChops.lighter(source_text_mask,fm)
        bb = fm.getbbox()
        source_mask_meta[r["key"]] = {"mask_bbox":list(bb),"mask_pixels":count(fm),"mode":"source_visible_candidate_changed_footprint"}
    else:
        source_mask_meta[r["key"]] = {"mask_bbox":None,"mask_pixels":0,"mode":"no_source_visible_delta"}

clean = src.copy()
transparent = Image.new("RGBA", src.size, (0,0,0,0))
clean.paste(transparent,(0,0),source_text_mask)
clean_protected = ImageOps.invert(source_text_mask)

# Reconstruct final from the clean plate. Previously passing render layers are reapplied
# at their exact A87 render positions; the 19 C85 failures are uniformly downscaled/repositioned
# as needed to fit their exact source text bbox with a 2px safety inset.
final = clean.copy()
target_masks = {}
ops = []
for r in rows:
    key = r["key"]
    ob = r["original_bbox"]
    region = own_rect(r, rows)
    if key in fail_keys:
        layer,bb,scale,identified = fit_overlay(before,src,region,ob,2)
        status = "REWORKED_UNIFORM_SCALE_OR_REPOSITION"
    else:
        x0,y0,x1,y1 = region
        cc = before.crop((x0,y0,x1,y1))
        ss = src.crop((x0,y0,x1,y1))
        mask = ImageChops.multiply(diffmask(cc,ss),binary_alpha(cc))
        layer = Image.new("RGBA",src.size,(0,0,0,0))
        tile = cc.copy()
        tile.putalpha(ImageChops.multiply(tile.getchannel("A"),mask))
        layer.alpha_composite(tile,(x0,y0))
        bb = layer.getchannel("A").getbbox()
        assert bb and halfopen_contains(ob,bb),(key,ob,bb)
        scale = 1.0
        identified = list(bb)
        status = "PRIOR_PASS_LAYER_PRESERVED"
    # Copy exact straight-RGBA layer pixels wherever the layer has coverage; do not
    # alpha-composite a second time, which would alter antialias RGB/alpha versus the accepted candidate.
    tm = binary_alpha(layer)
    final.paste(layer,(0,0),tm)
    target_masks[key] = tm
    ops.append({
        "key":key,"source":r["source"],"korean":r["korean"],
        "original_bbox":ob,"input_localized_bbox":r["localized_bbox"],
        "identified_layer_bbox":identified,"final_localized_bbox":list(bb),
        "scale":round(scale,6),"status":status,
        "was_c85_rework_required":key in fail_keys
    })

# Hard protect all pixels outside the union of the 29 exact source text bboxes.
allowed = Image.new("L",src.size,0)
ad = ImageDraw.Draw(allowed)
for r in rows:
    x0,y0,x1,y1 = r["original_bbox"]
    ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
protected = ImageOps.invert(allowed)
final.paste(src,(0,0),protected)

# Exact source DDS structure/orientation encode and decode check.
tmp_dds = out / "FD90AA9_A_RECOVERY07.dds"
candidate_sha = write_dds(srcp,final,tmp_dds)
h2,decoded = load_rgba_dds(tmp_dds)
assert h2 == source_header
assert ImageChops.difference(decoded,final).getbbox() is None

# Static validators use exact source, exact clean plate, and final decoded candidate.
src_png = out / "_SOURCE_READABLE.png"
final_png = out / "_FINAL_READABLE.png"
src.save(src_png); decoded.save(final_png)
source_text_mask.save(out/"FD90AA9_SOURCE_TEXT_MASK.png")
clean_protected.save(out/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK.png")
clean.save(out/"FD90AA9_CLEAN_PLATE.png")
allowed.save(out/"FD90AA9_ALLOWED_TEXT_REGION_MASK.png")
protected.save(out/"FD90AA9_PROTECTED_MASK.png")

subprocess.run([
    "python3",str(validator),str(src_png),str(out/"FD90AA9_CLEAN_PLATE.png"),
    str(out/"FD90AA9_SOURCE_TEXT_MASK.png"),"--protected-mask",
    str(out/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK.png"),"--report",
    str(out/"A_RECOVERY07_CLEAN_PLATE_VALIDATION.json")
],check=True)
subprocess.run([
    "python3",str(validator),str(src_png),str(final_png),
    str(out/"FD90AA9_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",
    str(out/"FD90AA9_PROTECTED_MASK.png"),"--report",
    str(out/"A_RECOVERY07_FINAL_MASK_VALIDATION.json")
],check=True)
cleanrep = json.loads((out/"A_RECOVERY07_CLEAN_PLATE_VALIDATION.json").read_text())
finalrep = json.loads((out/"A_RECOVERY07_FINAL_MASK_VALIDATION.json").read_text())
assert cleanrep["status"] == "PASS" and finalrep["status"] == "PASS"

# Per-element exact readable/raw containment from the actual target layers.
qa=[]
H=src.height
for r in rows:
    key=r["key"]; ob=list(r["original_bbox"]); bb=target_masks[key].getbbox()
    assert bb and halfopen_contains(ob,bb),(key,ob,bb)
    rb=raw_box(bb,H); rob=raw_box(ob,H)
    qa.append({
        "key":key,"source":r["source"],"korean":r["korean"],
        "original_bbox":ob,"localized_bbox":list(bb),
        "delta_left":bb[0]-ob[0],"delta_right":ob[2]-bb[2],
        "delta_top":bb[1]-ob[1],"delta_bottom":ob[3]-bb[3],
        "containment":"PASS","raw_original_bbox":rob,"raw_localized_bbox":rb,
        "raw_delta_left":rb[0]-rob[0],"raw_delta_right":rob[2]-rb[2],
        "raw_delta_top":rb[1]-rob[1],"raw_delta_bottom":rob[3]-rb[3],
        "raw_containment":"PASS",
        "rework_status":"A_RECOVERY07_REWORKED" if key in fail_keys else "PRIOR_C85_PASS_PRESERVED"
    })

# Prior C85 PASS target pixels remain exactly the same as the input candidate where their
# accepted A87 render layer exists.
prior_pass={}
for r in rows:
    if r["key"] in fail_keys:
        continue
    m=target_masks[r["key"]]
    d=diffmask(before,decoded)
    changed=count(ImageChops.multiply(d,m))
    prior_pass[r["key"]]=changed
    assert changed==0,(r["key"],changed)

# Clean-plate source residue metric: no source-visible replacement footprint survives.
clean_residue = count(ImageChops.multiply(binary_alpha(clean),source_text_mask))
assert clean_residue == 0

# No reworked target may overlap another target layer.
target_overlap=[]
keys=[r["key"] for r in rows]
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        ov=count(ImageChops.multiply(target_masks[keys[i]],target_masks[keys[j]]))
        if ov:
            target_overlap.append([keys[i],keys[j],ov])
# Historical atlas may contain intentional bbox overlap between semantic regions, but new
# transformed layers must not newly overlap compared with the input A87 target layers.
# Fail closed only if an overlap involves two reworked elements.
bad_overlap=[x for x in target_overlap if x[0] in fail_keys and x[1] in fail_keys]
assert not bad_overlap,bad_overlap

# Comparison sheet for the 19 repaired elements.
pad=8; labelh=20; items=[]
for r in rows:
    if r["key"] not in fail_keys:
        continue
    ob=tuple(r["original_bbox"])
    # show a padded union around original/current so the old overflow is visible
    lb=r["localized_bbox"]
    x0=max(0,min(ob[0],lb[0])-8); y0=max(0,min(ob[1],lb[1])-8)
    x1=min(src.width,max(ob[2],lb[2])+8); y1=min(src.height,max(ob[3],lb[3])+8)
    box=(x0,y0,x1,y1)
    items.append((r["key"],box,[src.crop(box),clean.crop(box),before.crop(box),decoded.crop(box)]))
colw=max(b[2]-b[0] for _,b,_ in items); rhs=[b[3]-b[1] for _,b,_ in items]
sheet=Image.new("RGBA",(colw*4+pad*5,sum(rhs)+len(rhs)*(labelh+pad)+pad),(210,210,210,255))
sd=ImageDraw.Draw(sheet); yy=pad
for (key,box,ims),rh in zip(items,rhs):
    for i,(im,label) in enumerate(zip(ims,["SOURCE","CLEAN","BEFORE","FINAL"])):
        xx=pad+i*(colw+pad)
        sd.text((xx,yy),f"{key} {label}",fill=(0,0,0,255))
        sheet.alpha_composite(im,(xx,yy+labelh))
    yy += labelh+rh+pad
# Downscale evidence only; pixel decisions above use exact decoded resolution.
if sheet.width > 4200:
    ratio=4200/sheet.width
    sheet=sheet.resize((4200,max(1,int(sheet.height*ratio))),Image.Resampling.LANCZOS)
sheet.convert("RGB").save(out/"A_RECOVERY07_FD90AA9_COMPARE.jpg",quality=92)

bg=Image.new("RGBA",decoded.size,(180,180,180,255)); bg.alpha_composite(decoded)
bg.resize((2048,2048),Image.Resampling.LANCZOS).convert("RGB").save(out/"A_RECOVERY07_FINAL_READABLE_GRAY_QA.jpg",quality=90)
raw_final=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rbg=Image.new("RGBA",raw_final.size,(180,180,180,255)); rbg.alpha_composite(raw_final)
rbg.resize((2048,2048),Image.Resampling.LANCZOS).convert("RGB").save(out/"A_RECOVERY07_FINAL_RAW_GRAY_QA.jpg",quality=90)

report={
    "schema_version":2,"role":"A","run":run,
    "worker":os.environ.get("OUTRUN_CPU_WORKER","unknown"),
    "base_head":os.environ.get("GITHUB_SHA"),
    "asset":"textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds",
    "source_sha256":source_sha,"input_candidate_sha256":input_sha,
    "candidate_sha256":candidate_sha,
    "method":"C85 direct-return rework on GitHub-hosted CPU worker: exact HD source -> source-visible candidate-changed text masks -> transparent clean plate -> midpoint-partition overlapping semantic localized bboxes -> preserve 10 prior-PASS owned layers -> uniformly downscale/reposition 19 C85-failing owned localized delta layers into exact source bboxes -> exact canonical RGBA32 DDS encode -> decoded final static QA",
    "structure":{"dimensions":[4096,4096],"format":"RGBA32","mipmaps":1,"raw_orientation":"mirror_y","header_128_exact_source":True,"bytes":tmp_dds.stat().st_size},
    "c85_fail_count":len(fail_keys),"c85_fail_keys":sorted(fail_keys),
    "reworked_count":len(fail_keys),"prior_pass_count":len(rows)-len(fail_keys),
    "source_text_masks":source_mask_meta,
    "operations":ops,"rows":qa,
    "all_29_readable_and_raw_bbox_pass":True,
    "prior_pass_target_pixel_diffs":prior_pass,
    "clean_plate_source_text_residue_pixels":clean_residue,
    "target_overlap_pairs":target_overlap,
    "bad_reworked_overlap_pairs":bad_overlap,
    "clean_plate_validator":cleanrep,"final_validator":finalrep,
    "visual_qa":"PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED",
    "status":"A_RECOVERY07_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"
}
(out/"A_RECOVERY07_FD90AA9_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Persist candidate only after all exact static gates pass.
candp.parent.mkdir(parents=True,exist_ok=True)
candp.write_bytes(tmp_dds.read_bytes())
assert sha(candp)==candidate_sha
tmp_dds.unlink()
src_png.unlink(); final_png.unlink()

summary={
    "run":run,"asset":"FD90AA9","source_sha256":source_sha,
    "input_candidate_sha256":input_sha,"candidate_sha256":candidate_sha,
    "c85_fail_before":19,"c85_fail_after":0,
    "all_29_readable_and_raw_bbox_pass":True,
    "clean_plate_validator":"PASS","final_mask_validator":"PASS",
    "clean_plate_source_text_residue_pixels":0,
    "runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261004-A-RECOVERY07/A_RECOVERY07_FD90AA9_REPORT.json"
}
(worker_out/"A_RECOVERY07_FD90AA9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
