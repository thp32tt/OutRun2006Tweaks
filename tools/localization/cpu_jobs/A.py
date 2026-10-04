#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("This deterministic job must run in the GitHub-hosted localization CPU worker as role A.")

repo = Path.cwd()
run = "20261004-A-RECOVERY08"
out = repo / "localization/graphics/role_A" / run
out.mkdir(parents=True, exist_ok=True)
worker_out = repo / "localization/graphics/worker_results"
worker_out.mkdir(parents=True, exist_ok=True)

asset_rel = "textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
srcp = repo / "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a" / asset_rel
candp = repo / "localization/graphics/hd_candidates" / asset_rel
a07dir = repo / "localization/graphics/role_A/20261004-A-RECOVERY07"
a07reportp = a07dir / "A_RECOVERY07_FD90AA9_REPORT.json"
clean07p = a07dir / "FD90AA9_CLEAN_PLATE.png"
source_mask07p = a07dir / "FD90AA9_SOURCE_TEXT_MASK.png"
allowed07p = a07dir / "FD90AA9_ALLOWED_TEXT_REGION_MASK.png"
protected07p = a07dir / "FD90AA9_PROTECTED_MASK.png"
validator = repo / "tools/localization/validate_clean_plate.py"

SOURCE_SHA = "f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
INPUT_SHA = "58a8bd06a38375694da7d3109fc2615ccd6d45092828f7eb5b7a9317afc13010"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_rgba_dds(p):
    b = Path(p).read_bytes()
    assert b[:4] == b"DDS "
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    pitch = struct.unpack_from("<I", b, 20)[0]
    depth = struct.unpack_from("<I", b, 24)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    pf = struct.unpack_from("<8I", b, 76)
    assert (w,h)==(4096,4096), (w,h)
    assert pitch == w*4 and depth == 1 and mips == 1
    assert pf[2] == 0 and pf[3] == 32 and pf[4:] == (0xff,0xff00,0xff0000,0xff000000), pf
    assert len(b) == 128 + w*h*4
    raw = Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    return b[:128], raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def write_dds(src_path, readable, out_path):
    sb = Path(src_path).read_bytes()
    raw = readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    Path(out_path).write_bytes(sb[:128] + raw.tobytes("raw","RGBA"))
    return sha(out_path)

def diffmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

def binary_alpha(im):
    return im.getchannel("A").point(lambda v:255 if v else 0)

def count(mask):
    return sum(mask.histogram()[1:])

def full_mask(size, local, origin):
    m=Image.new("L",size,0)
    m.paste(local,origin)
    return m

def contains(ob,bb):
    return bb and bb[0]>=ob[0] and bb[1]>=ob[1] and bb[2]<=ob[2] and bb[3]<=ob[3]

def intersects(a,b):
    return not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])

assert sha(srcp)==SOURCE_SHA
assert sha(candp)==INPUT_SHA
source_header, src = load_rgba_dds(srcp)
cand_header, before = load_rgba_dds(candp)
assert source_header == cand_header
W,H=src.size
clean07=Image.open(clean07p).convert("RGBA")
source_mask07=Image.open(source_mask07p).convert("L")
allowed07=Image.open(allowed07p).convert("L")
protected07=Image.open(protected07p).convert("L")
a07=json.loads(a07reportp.read_text(encoding="utf-8"))
rows=a07["rows"]
rowmap={r["key"]:r for r in rows}

targets={"more_engine","experts_long","for_experts","normal_difficult"}
assert targets.issubset(rowmap)
assert len(rows)==29

def layer_mask_from_clean(key):
    r=rowmap[key]
    bb=tuple(r["localized_bbox"])
    local=diffmask(before.crop(bb),clean07.crop(bb))
    # Existing localized visible/effect pixels only.
    local=ImageChops.multiply(local,binary_alpha(before.crop(bb)))
    return full_mask(before.size,local,(bb[0],bb[1]))

old_masks={k:layer_mask_from_clean(k) for k in targets}
for k,m in old_masks.items():
    assert m.getbbox(),k

# Start from the A_RECOVERY07 candidate and remove only the four returned visual layers.
final=before.copy()
for k,m in old_masks.items():
    final.paste(clean07,(0,0),m)

# Build an improved clean plate for the More Engine source label.
# C92 showed source English surviving under the Korean layer. The source bbox slightly
# overlaps the separate "You" sprite at x>=3169, so clip source cleanup before that
# neighbor and derive a glyph/effect-shaped high-frequency mask inside the source bbox.
clean08=clean07.copy()
engine_ob=list(rowmap["more_engine"]["original_bbox"])
engine_safe=[engine_ob[0],engine_ob[1],min(engine_ob[2],3169),engine_ob[3]]
pad=8
px0=max(0,engine_safe[0]-pad); py0=max(0,engine_safe[1]-pad)
px1=min(W,engine_safe[2]+pad); py1=min(H,engine_safe[3]+pad)
source_patch=src.crop((px0,py0,px1,py1))
blur=source_patch.filter(ImageFilter.GaussianBlur(radius=5.0))
hf=ImageChops.difference(source_patch,blur)
hb=hf.split()
score=hb[0]
for b in hb[1:3]:
    score=ImageChops.lighter(score,b)
# Low threshold, then dilation, captures fill/outline/shadow but remains clipped to the
# original text bbox and away from the You neighbor.
local_hf=score.point(lambda v:255 if v>=11 else 0)
clip=Image.new("L",source_patch.size,0)
cd=ImageDraw.Draw(clip)
cd.rectangle((engine_safe[0]-px0,engine_safe[1]-py0,engine_safe[2]-px0-1,engine_safe[3]-py0-1),fill=255)
local_hf=ImageChops.multiply(local_hf,clip).filter(ImageFilter.MaxFilter(7))
# Union prior A07 source mask for this safe region so all earlier-cleaned English
# pixels and newly detected residue are reconstructed together.
prior_local=source_mask07.crop((px0,py0,px1,py1))
engine_mask_local=ImageChops.lighter(local_hf,prior_local)
engine_mask_local=ImageChops.multiply(engine_mask_local,clip)
engine_mask=full_mask(src.size,engine_mask_local,(px0,py0))
emb=engine_mask.getbbox()
assert emb and contains(engine_safe,emb),(engine_safe,emb)
engine_mask_pixels=count(engine_mask)
safe_area=(engine_safe[2]-engine_safe[0])*(engine_safe[3]-engine_safe[1])
assert 1500 < engine_mask_pixels < int(safe_area*0.72),(engine_mask_pixels,safe_area)

# Harmonic-ish inpaint using a blurred initialization and repeated 4-neighbor relaxation.
arr=np.asarray(source_patch).astype(np.float32)
mask_np=np.asarray(engine_mask_local)>0
init=np.asarray(source_patch.filter(ImageFilter.GaussianBlur(radius=9.0))).astype(np.float32)
work=arr.copy()
work[mask_np]=init[mask_np]
for _ in range(180):
    avg=(np.roll(work,1,0)+np.roll(work,-1,0)+np.roll(work,1,1)+np.roll(work,-1,1))*0.25
    work[mask_np]=avg[mask_np]
inp=Image.fromarray(np.clip(work,0,255).astype(np.uint8),"RGBA")
clean08.paste(inp,(px0,py0),engine_mask_local)
# Ensure current candidate's old Korean engine layer is cleared to the improved plate.
final.paste(clean08,(0,0),ImageChops.lighter(engine_mask,old_masks["more_engine"]))

# The three expert-related cells physically overlap in the atlas. C92 showed the old
# oversized layers intruding into each other's sprite crops. Render into disjoint vertical
# bands that remain inside each exact source bbox and avoid current neighboring layers.
zones={
    "experts_long":[1940,618,3380,700],   # ends before lower expert cells begin at y704
    "for_experts":[1810,785,2290,850],    # after experts_long ends; before select_music starts at y857
    "normal_difficult":[2580,785,3330,870],
    "more_engine":[2790,380,3148,444],    # stops before You sprite begins at x3169
}
for k,z in zones.items():
    assert contains(rowmap[k]["original_bbox"],z),(k,rowmap[k]["original_bbox"],z)

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try:
            fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception:
            fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists():
            return fp
    raise RuntimeError("Noto Sans CJK KR unavailable")

FONT=resolve_font()

def shear_rgba(im,slant):
    if not slant:
        return im
    shift=max(0,int(round(abs(slant)*(im.height-1))))
    out=Image.new("RGBA",(im.width+shift+2,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(slant*(im.height-1-y)))
        if dx<0: dx += shift
        out.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    bb=out.getchannel("A").getbbox()
    return out.crop(bb) if bb else out

def text_layer(text,zone,max_fs,fill,outer,inner=None,slant=0.0):
    x0,y0,x1,y1=zone; aw=x1-x0; ah=y1-y0
    dummy=ImageDraw.Draw(Image.new("L",(8,8),0))
    for fs in range(max_fs,15,-1):
        font=ImageFont.truetype(FONT,fs)
        outer_w=max(2,int(round(fs*0.08)))
        inner_w=max(1,int(round(fs*0.035)))
        tb=dummy.textbbox((0,0),text,font=font,stroke_width=outer_w)
        tw,th=tb[2]-tb[0],tb[3]-tb[1]
        pad=outer_w+5
        g=Image.new("RGBA",(tw+pad*2,th+pad*2),(0,0,0,0))
        d=ImageDraw.Draw(g)
        d.text((pad-tb[0],pad-tb[1]),text,font=font,fill=fill,stroke_width=outer_w,stroke_fill=outer)
        if inner is not None:
            d.text((pad-tb[0],pad-tb[1]),text,font=font,fill=fill,stroke_width=inner_w,stroke_fill=inner)
        bb=g.getchannel("A").getbbox()
        g=g.crop(bb)
        g=shear_rgba(g,slant)
        if g.width<=aw-2 and g.height<=ah-2:
            tx=x0+(aw-g.width)//2; ty=y0+(ah-g.height)//2
            layer=Image.new("RGBA",(W,H),(0,0,0,0))
            layer.alpha_composite(g,(tx,ty))
            return layer,fs,list(layer.getchannel("A").getbbox())
    raise RuntimeError(("fit failed",text,zone))

def split_layer(parts,zone,max_fs,outer,inner=None,slant=0.0):
    x0,y0,x1,y1=zone; aw=x1-x0; ah=y1-y0
    dummy=ImageDraw.Draw(Image.new("L",(8,8),0))
    for fs in range(max_fs,15,-1):
        font=ImageFont.truetype(FONT,fs)
        ow=max(2,int(round(fs*0.08))); iw=max(1,int(round(fs*0.035)))
        metrics=[]
        total=0
        maxh=0
        for text,fill in parts:
            tb=dummy.textbbox((0,0),text,font=font,stroke_width=ow)
            w,h=tb[2]-tb[0],tb[3]-tb[1]
            metrics.append((text,fill,tb,w,h))
            total+=w
            maxh=max(maxh,h)
        total += max(4,int(fs*0.12))*(len(parts)-1)
        pad=ow+5
        g=Image.new("RGBA",(total+pad*2,maxh+pad*2),(0,0,0,0))
        d=ImageDraw.Draw(g)
        xx=pad
        gap=max(4,int(fs*0.12))
        for text,fill,tb,w,h in metrics:
            pos=(xx-tb[0],pad-tb[1])
            d.text(pos,text,font=font,fill=fill,stroke_width=ow,stroke_fill=outer)
            if inner is not None:
                d.text(pos,text,font=font,fill=fill,stroke_width=iw,stroke_fill=inner)
            xx += w+gap
        bb=g.getchannel("A").getbbox()
        g=g.crop(bb)
        g=shear_rgba(g,slant)
        if g.width<=aw-2 and g.height<=ah-2:
            tx=x0+(aw-g.width)//2; ty=y0+(ah-g.height)//2
            layer=Image.new("RGBA",(W,H),(0,0,0,0))
            layer.alpha_composite(g,(tx,ty))
            return layer,fs,list(layer.getchannel("A").getbbox())
    raise RuntimeError(("split fit failed",parts,zone))

layers={}
layers["more_engine"],fs_engine,bb_engine=text_layer(
    "엔진음 크게",zones["more_engine"],48,(255,235,105,255),(75,60,5,255),(255,248,205,255),0.12
)
layers["experts_long"],fs_long,bb_long=text_layer(
    "상급자용 · 골까지 장거리",zones["experts_long"],62,(226,42,50,255),(10,24,72,255),(248,248,248,255),0.08
)
layers["for_experts"],fs_for,bb_for=text_layer(
    "상급자용",zones["for_experts"],54,(226,42,50,255),(10,24,72,255),(248,248,248,255),0.08
)
layers["normal_difficult"],fs_normal,bb_normal=split_layer(
    [("보통",(25,210,110,255)),("난이도",(228,45,55,255))],
    zones["normal_difficult"],62,(10,24,72,255),(248,248,248,255),0.04
)
font_sizes={"more_engine":fs_engine,"experts_long":fs_long,"for_experts":fs_for,"normal_difficult":fs_normal}
new_bboxes={"more_engine":bb_engine,"experts_long":bb_long,"for_experts":bb_for,"normal_difficult":bb_normal}

# New layers must fit both their exact source bbox and isolated placement zone.
for k,layer in layers.items():
    bb=layer.getchannel("A").getbbox()
    assert bb and contains(rowmap[k]["original_bbox"],bb),(k,bb,rowmap[k]["original_bbox"])
    assert contains(zones[k],bb),(k,bb,zones[k])
    final.paste(layer,(0,0),binary_alpha(layer))

# Enforce that repaired expert layers do not physically intersect each other.
for a,b in [("experts_long","for_experts"),("experts_long","normal_difficult"),("for_experts","normal_difficult")]:
    assert count(ImageChops.multiply(binary_alpha(layers[a]),binary_alpha(layers[b])))==0,(a,b)

# Persist clean evidence before encode.
source_png=out/"_SOURCE_READABLE.png"
clean_png=out/"FD90AA9_CLEAN_PLATE_RECOVERY08.png"
final_pre_png=out/"_FINAL_PREENCODE_READABLE.png"
src.save(source_png); clean08.save(clean_png); final.save(final_pre_png)
source_mask08=ImageChops.lighter(source_mask07,engine_mask)
source_mask08.save(out/"FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png")
clean_protected08=ImageOps.invert(source_mask08)
clean_protected08.save(out/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK_RECOVERY08.png")

subprocess.run([
    "python3",str(validator),str(source_png),str(clean_png),
    str(out/"FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png"),
    "--protected-mask",str(out/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK_RECOVERY08.png"),
    "--report",str(out/"A_RECOVERY08_CLEAN_PLATE_VALIDATION.json")
],check=True)
cleanrep=json.loads((out/"A_RECOVERY08_CLEAN_PLATE_VALIDATION.json").read_text())
assert cleanrep["status"]=="PASS"

# Exact canonical RGBA32/raw mirror_y encode.
tmpdds=out/"FD90AA9_A_RECOVERY08.dds"
candidate_sha=write_dds(srcp,final,tmpdds)
h2,decoded=load_rgba_dds(tmpdds)
assert h2==source_header
assert ImageChops.difference(decoded,final).getbbox() is None
decoded_png=out/"_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)

subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(allowed07p),"--protected-mask",str(protected07p),
    "--report",str(out/"A_RECOVERY08_FINAL_MASK_VALIDATION.json")
],check=True)
finalrep=json.loads((out/"A_RECOVERY08_FINAL_MASK_VALIDATION.json").read_text())
assert finalrep["status"]=="PASS"

# Changes vs A07 are restricted to the four returned source bboxes.
repair_allowed=Image.new("L",(W,H),0)
rd=ImageDraw.Draw(repair_allowed)
for k in targets:
    x0,y0,x1,y1=rowmap[k]["original_bbox"]
    rd.rectangle((x0,y0,x1-1,y1-1),fill=255)
delta08=diffmask(before,decoded)
outside08=count(ImageChops.multiply(delta08,ImageOps.invert(repair_allowed)))
assert outside08==0,outside08

# Preserve all 25 unaffected localized target layers exactly.
preserve_diffs={}
delta_before_final=diffmask(before,decoded)
for r in rows:
    k=r["key"]
    if k in targets:
        continue
    bb=tuple(r["localized_bbox"])
    layer_local=ImageChops.multiply(
        diffmask(before.crop(bb),clean07.crop(bb)),
        binary_alpha(before.crop(bb))
    )
    layer_full=full_mask((W,H),layer_local,(bb[0],bb[1]))
    n=count(ImageChops.multiply(delta_before_final,layer_full))
    preserve_diffs[k]=n
    assert n==0,(k,n)

# Recompute target rows from new final-vs-clean08 layers.
qa=[]
for k in ["more_engine","experts_long","for_experts","normal_difficult"]:
    r=rowmap[k]; bb=list(layers[k].getchannel("A").getbbox()); ob=r["original_bbox"]
    assert contains(ob,bb)
    raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]
    raw_bb=[bb[0],H-bb[3],bb[2],H-bb[1]]
    qa.append({
        "key":k,"source":r["source"],"korean":r["korean"],
        "original_bbox":ob,"localized_bbox":bb,
        "delta_left":bb[0]-ob[0],"delta_right":ob[2]-bb[2],
        "delta_top":bb[1]-ob[1],"delta_bottom":ob[3]-bb[3],
        "containment":"PASS",
        "raw_original_bbox":raw_ob,"raw_localized_bbox":raw_bb,
        "raw_delta_left":raw_bb[0]-raw_ob[0],"raw_delta_right":raw_ob[2]-raw_bb[2],
        "raw_delta_top":raw_bb[1]-raw_ob[1],"raw_delta_bottom":raw_ob[3]-raw_bb[3],
        "raw_containment":"PASS",
        "placement_zone":zones[k],"font_size":font_sizes[k],
        "rework_status":"A_RECOVERY08_FRESH_RECONSTRUCTION"
    })

# Engine cleanup must not touch the You neighbor.
you=rowmap["you"]["localized_bbox"]
assert not intersects(new_bboxes["more_engine"],you),(new_bboxes["more_engine"],you)
engine_mask_vs_you=count(ImageChops.multiply(engine_mask,full_mask((W,H),Image.new("L",(you[2]-you[0],you[3]-you[1]),255),(you[0],you[1]))))
assert engine_mask_vs_you==0,engine_mask_vs_you

# Render high-zoom controller evidence for the four returned rows.
label_font=ImageFont.truetype(FONT,20)
cards=[]
for k in ["more_engine","experts_long","for_experts","normal_difficult"]:
    r=rowmap[k]
    ob=r["original_bbox"]; lb_old=r["localized_bbox"]; lb_new=new_bboxes[k]
    x0=max(0,min(ob[0],lb_old[0],lb_new[0])-24)
    y0=max(0,min(ob[1],lb_old[1],lb_new[1])-24)
    x1=min(W,max(ob[2],lb_old[2],lb_new[2])+24)
    y1=min(H,max(ob[3],lb_old[3],lb_new[3])+24)
    box=(x0,y0,x1,y1)
    ims=[src.crop(box),clean08.crop(box),before.crop(box),decoded.crop(box)]
    scale=2
    cw=(x1-x0)*scale; ch=(y1-y0)*scale
    rowimg=Image.new("RGB",(cw*4+30,ch+32),(245,245,245))
    d=ImageDraw.Draw(rowimg)
    for i,(im,name) in enumerate(zip(ims,["SOURCE","CLEAN08","BEFORE_C92_FAIL","FINAL08"])):
        bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
        v=bg.convert("RGB").resize((cw,ch),Image.Resampling.NEAREST)
        xx=i*(cw+10)
        rowimg.paste(v,(xx,32))
        d.text((xx+4,4),f"{k} {name}",font=label_font,fill=(0,0,0))
    cards.append(rowimg)
sheet_w=max(c.width for c in cards)
sheet_h=sum(c.height for c in cards)+10*(len(cards)-1)
sheet=Image.new("RGB",(sheet_w,sheet_h),(230,230,230))
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+10
sheet.save(out/"A_RECOVERY08_C92_RETURN_CONTACT_COMPARE.jpg",quality=94)

# Full readable/raw QA evidence.
def gray(im):
    bg=Image.new("RGBA",im.size,(150,150,150,255)); bg.alpha_composite(im)
    return bg.convert("RGB")
gray(decoded).resize((2048,2048),Image.Resampling.LANCZOS).save(out/"A_RECOVERY08_FINAL_READABLE_GRAY_QA.jpg",quality=91)
gray(decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)).resize((2048,2048),Image.Resampling.LANCZOS).save(out/"A_RECOVERY08_FINAL_RAW_GRAY_QA.jpg",quality=91)

report={
    "schema_version":1,"role":"A","run":run,
    "worker":os.environ.get("OUTRUN_CPU_WORKER","unknown"),
    "base_head":os.environ.get("GITHUB_SHA"),
    "asset":asset_rel,
    "c92_return_report":"localization/graphics/role_C/20261004-1740-C92/C92_FD90AA9_FINAL_QA.json",
    "source_sha256":SOURCE_SHA,"input_candidate_sha256":INPUT_SHA,
    "candidate_sha256":candidate_sha,
    "method":"C92 visual-return repair on GitHub-hosted worker: preserve 25 A07 layers exact; remove four returned A07 layers to clean plate; expand More Engine glyph/effect cleanup with high-frequency source mask clipped away from You; harmonic RGBA inpaint; fresh native Korean rerender; physically isolate three overlapping expert labels into non-overlapping vertical atlas bands; exact source-header RGBA32 encode; decoded static QA",
    "structure":{"dimensions":[4096,4096],"format":"RGBA32","mipmaps":1,"raw_orientation":"mirror_y","header_128_exact_source":True,"bytes":tmpdds.stat().st_size},
    "c92_blocking_failures":["more_engine","experts_long","for_experts","normal_difficult"],
    "engine_cleanup":{
        "source_bbox":engine_ob,"safe_cleanup_bbox":engine_safe,
        "mask_bbox":list(emb),"mask_pixels":engine_mask_pixels,
        "mask_overlap_with_you_localized_pixels":engine_mask_vs_you,
        "method":"source high-frequency glyph/effect mask + A07 prior source mask + harmonic RGBA inpaint"
    },
    "reworked_rows":qa,
    "preserved_unaffected_target_layer_diffs":preserve_diffs,
    "preserved_unaffected_count":len(preserve_diffs),
    "changes_vs_a07_outside_four_source_bboxes":outside08,
    "clean_plate_validator":cleanrep,"final_validator":finalrep,
    "fresh_layer_overlap_pairs":[],
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED",
    "status":"A_RECOVERY08_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"
}
(out/"A_RECOVERY08_FD90AA9_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Persist candidate only after all static gates.
candp.write_bytes(tmpdds.read_bytes())
assert sha(candp)==candidate_sha
tmpdds.unlink()
source_png.unlink(); final_pre_png.unlink(); decoded_png.unlink()

summary={
    "run":run,"asset":"FD90AA9","source_sha256":SOURCE_SHA,
    "input_candidate_sha256":INPUT_SHA,"candidate_sha256":candidate_sha,
    "c92_blocking_failures_before":4,"c92_target_rows_rebuilt":4,
    "reworked_bbox_pass":"4/4","unaffected_layers_preserved_exact":"25/25",
    "clean_plate_validator":"PASS","final_mask_validator":"PASS",
    "changes_vs_a07_outside_four_source_bboxes":0,
    "runtime_validation":"UNTESTED",
    "status":"A_RECOVERY08_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA",
    "report":"localization/graphics/role_A/20261004-A-RECOVERY08/A_RECOVERY08_FD90AA9_REPORT.json"
}
(worker_out/"A_RECOVERY08_FD90AA9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
