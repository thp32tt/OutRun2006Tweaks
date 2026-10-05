#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request, statistics, math
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo = Path.cwd()
run = "20261005-B-PRODUCTION138-C598-SOLVER"
out = repo / "localization/graphics/role_B" / run
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)
asset = "textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds"
candidate = repo / "localization/graphics/hd_candidates" / asset
candidate.parent.mkdir(parents=True, exist_ok=True)

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB = "3ab34d5fcd66b5b8cb3d59e02d0d199e2e6b5456"
ATLAS_BLOB = "c2d82b14396fc89ca08affcb8ff9c615d644bc82"
SOURCE_SHA256 = "9caaf9d94bb853f8cc00faad6bf03fb6460e893a726c5e200fe4a7826768f3bf"
base = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT
tmp = Path("/tmp/outrun_B138")
tmp.mkdir(parents=True, exist_ok=True)
dds = tmp / "C598_HD.dds"
atlas = tmp / "C598_atlas.json"
urllib.request.urlretrieve(base + "/Release/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds", dds)
urllib.request.urlretrieve(base + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_ranking_cvt_Exst/4x_C598919A_1024x1024_atlas.json", atlas)

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def gitblob(b):
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def dds_meta(b):
    if b[:4] != b"DDS ":
        raise RuntimeError("not DDS")
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    fourcc = b[84:88]
    need = 128 + ((w + 3) // 4) * ((h + 3) // 4) * 16
    if fourcc != b"DXT5" or mips not in (0, 1) or len(b) != need:
        raise RuntimeError(("unexpected DDS", w, h, mips, fourcc, len(b), need))
    return w, h, mips

sb = dds.read_bytes()
ab = atlas.read_bytes()
if gitblob(sb) != SOURCE_BLOB or gitblob(ab) != ATLAS_BLOB or sha256_bytes(sb) != SOURCE_SHA256:
    raise RuntimeError(("pinned source drift", gitblob(sb), gitblob(ab), sha256_bytes(sb)))
W, H, MIPS = dds_meta(sb)
if (W, H) != (4096, 4096):
    raise RuntimeError(("dimension drift", W, H))
regs = {int(r["idx"]): r for r in json.loads(ab.decode("utf-8"))["regions"]}
raw_src = Image.open(dds).convert("RGBA")
src = raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa = np.asarray(src, dtype=np.uint8)

subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "fonts-noto-cjk", "fonts-noto-cjk-extra", "libnvtt-bin"], check=True)
FONT = subprocess.check_output(["fc-match", "-f", "%{file}", "Noto Sans CJK KR:style=Black"], text=True).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("CJK font unavailable", FONT))
if not Path("/usr/bin/nvcompress").exists():
    raise RuntimeError("nvcompress unavailable")

# C151's prose region numbers and B78's stage list were offset from the actual atlas.
# The canonical C151 contact sheet plus atlas geometry resolve the physical binding below.
# Product marks, MT/AT, Ferrari names, rank numerals/icons and non-text artwork stay original.
full_specs = [
    (30, "OutRun MODE", "아웃런 모드", "mode"),
    (40, "Top Runners of Each Goal", "각 골별 최고 기록", "header"),
    (43, "Heart Attack MODE", "하트 어택 모드", "mode"),
    (44, "OutRun MODE", "아웃런 모드", "mode"),
    (45, "Time Attack MODE", "타임 어택 모드", "mode"),
    (46, "15 Continuous Course", "15코스 연속", "mode"),
    (47, "Ranking", "랭킹", "mode"),
    (48, "NORMAL", "일반", "badge"),
    (49, "TUNED", "튜닝", "badge"),
    (64, "NORMAL", "일반", "small"),
    (65, "TUNED", "튜닝", "small"),
]
goal_specs = [
    (16, "GOAL E", "골 E"), (17, "GOAL D", "골 D"),
    (18, "GOAL C", "골 C"), (19, "GOAL B", "골 B"),
    (20, "GOAL A", "골 A"), (21, "GOAL E", "골 E"),
    (22, "GOAL D", "골 D"), (23, "GOAL C", "골 C"),
    (24, "GOAL B", "골 B"), (25, "GOAL A", "골 A"),
]
stage_specs = [
    (78, "Imperial Avenue", "임페리얼 애비뉴"),
    (79, "Cape Way", "케이프 웨이"),
    (80, "Metropolis", "메트로폴리스"),
    (81, "Ancient Ruins", "에인션트 루인스"),
    (82, "Skyscrapers", "스카이스크레이퍼스"),
    (83, "Tulip Garden", "튤립 가든"),
    (84, "Floral Village", "플로럴 빌리지"),
    (85, "Milky Way", "밀키 웨이"),
    (86, "Giant Statues", "자이언트 스태추스"),
    (87, "Legend", "레전드"),
]
product_specs = [
    (14, "OutRun2 15 Continuous Course", "15코스 연속", "OutRun2"),
    (15, "OutRun2SP 15 Continuous Course", "15코스 연속", "OutRun2SP"),
]
time_specs = [
    (26, "Time Attack MODE / TUNED / MT", "타임 어택 모드", "튜닝", "MT"),
    (27, "Time Attack MODE / TUNED / AT", "타임 어택 모드", "튜닝", "AT"),
    (28, "Time Attack MODE / NORMAL / MT", "타임 어택 모드", "일반", "MT"),
    (29, "Time Attack MODE / NORMAL / AT", "타임 어택 모드", "일반", "AT"),
]

def region_arrays(idx):
    r = regs[idx]
    x, y, w, h = map(int, r["rect"])
    arr = sa[y:y+h, x:x+w]
    alpha = arr[:, :, 3] > 1
    return (x, y, w, h), arr, alpha

def runs_of_false(v):
    runs = []
    start = None
    for i, val in enumerate(v):
        if not val and start is None:
            start = i
        elif val and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(v)))
    return runs

def choose_vertical_gap(alpha, lo_frac, hi_frac):
    cols = np.any(alpha, axis=0)
    lo = int(alpha.shape[1] * lo_frac)
    hi = int(alpha.shape[1] * hi_frac)
    cand = [(a,b) for a,b in runs_of_false(cols) if b > lo and a < hi and b-a >= 2]
    if not cand:
        raise RuntimeError(("no vertical split gap", alpha.shape, lo_frac, hi_frac))
    a,b = max(cand, key=lambda z: z[1]-z[0])
    return (a+b)//2, [a,b]

def choose_horizontal_gap(alpha, lo_frac, hi_frac):
    rows = np.any(alpha, axis=1)
    lo = int(alpha.shape[0] * lo_frac)
    hi = int(alpha.shape[0] * hi_frac)
    cand = [(a,b) for a,b in runs_of_false(rows) if b > lo and a < hi and b-a >= 2]
    if not cand:
        # Some compressed source rows have faint alpha bridge. Fall back to minimum occupancy row.
        occ = np.count_nonzero(alpha, axis=1)
        a = max(lo, 1); b = min(hi, len(occ)-1)
        if a >= b:
            raise RuntimeError(("no horizontal split range", alpha.shape))
        pos = a + int(np.argmin(occ[a:b]))
        return pos, [pos,pos+1]
    a,b = max(cand, key=lambda z: z[1]-z[0])
    return (a+b)//2, [a,b]

def exact_mask_bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise RuntimeError("empty source mask")
    return [int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1]

elements = []
def add_element(idx, source, korean, local_mask, kind, extra=None):
    (x,y,w,h), arr, alpha = region_arrays(idx)
    if local_mask.shape != alpha.shape:
        raise RuntimeError(("mask shape",idx,local_mask.shape,alpha.shape))
    local_mask = local_mask & alpha
    lb = exact_mask_bbox(local_mask)
    gb = [x+lb[0], y+lb[1], x+lb[2], y+lb[3]]
    gm = np.zeros((H,W), dtype=bool)
    gm[y:y+h,x:x+w] = local_mask
    elements.append({
        "region_idx": idx, "source": source, "korean": korean, "kind": kind,
        "cell": [x,y,w,h], "source_mask": gm, "original_bbox": gb,
        "source_mask_pixels": int(np.count_nonzero(gm)),
        "extra": extra or {}
    })

# Full-text cells.
for idx, source, korean, kind in full_specs:
    cell, arr, alpha = region_arrays(idx)
    add_element(idx, source, korean, alpha, kind)

# Goal cells: preserve the left icon; localize only the text to the right of the largest icon/text gap.
for idx, source, korean in goal_specs:
    cell, arr, alpha = region_arrays(idx)
    split, gap = choose_vertical_gap(alpha, 0.08, 0.48)
    m = alpha.copy()
    m[:, :split] = False
    add_element(idx, source, korean, m, "goal", {"icon_text_split_x":split,"gap":gap})

# Product cells: preserve OutRun2/OutRun2SP token, localize only descriptor after the largest product/descriptor gap.
for idx, source, korean, token in product_specs:
    cell, arr, alpha = region_arrays(idx)
    split, gap = choose_vertical_gap(alpha, 0.12, 0.50)
    m = alpha.copy()
    m[:, :split] = False
    add_element(idx, source + " descriptor", korean, m, "product_descriptor",
                {"protected_product_token":token,"product_descriptor_split_x":split,"gap":gap})

# Time Attack compound cells: preserve MT/AT at right; preserve source multi-line hierarchy by two Korean lines.
for idx, source, ko1, ko2, protected in time_specs:
    cell, arr, alpha = region_arrays(idx)
    xsplit, xgap = choose_vertical_gap(alpha, 0.55, 0.90)
    left = alpha.copy()
    left[:, xsplit:] = False
    ysplit, ygap = choose_horizontal_gap(left, 0.28, 0.78)
    top = left.copy(); top[ysplit:,:] = False
    bottom = left.copy(); bottom[:ysplit,:] = False
    add_element(idx, "Time Attack MODE", ko1, top, "time_mode_line",
                {"protected_indicator":protected,"indicator_split_x":xsplit,"line_split_y":ysplit,"xgap":xgap,"ygap":ygap})
    add_element(idx, "TUNED" if "TUNED" in source else "NORMAL", ko2, bottom, "time_variant_line",
                {"protected_indicator":protected,"indicator_split_x":xsplit,"line_split_y":ysplit,"xgap":xgap,"ygap":ygap})

# Corrected physical stage binding from the canonical C151 contact sheet.
for idx, source, korean in stage_specs:
    cell, arr, alpha = region_arrays(idx)
    add_element(idx, source, korean, alpha, "stage")

# Source masks may not overlap; overlapping semantics would make clean/render ownership ambiguous.
source_union = np.zeros((H,W), dtype=bool)
for e in elements:
    overlap = source_union & e["source_mask"]
    if np.any(overlap):
        raise RuntimeError(("source element overlap",e["region_idx"],e["source"],int(np.count_nonzero(overlap))))
    source_union |= e["source_mask"]

# Exact source bbox union is the only decoded-pixel region allowed to change.
allowed = np.zeros((H,W), dtype=bool)
for e in elements:
    x0,y0,x1,y1 = e["original_bbox"]
    allowed[y0:y1,x0:x1] = True

# Ensure known protected atlas cells remain outside target geometry.
protected_region_indices = list(range(31,40)) + list(range(50,64)) + list(range(66,78)) + list(range(88,106))
protected_region_indices = sorted(set(i for i in protected_region_indices if i in regs))
protected_before = {}
for idx in protected_region_indices:
    x,y,w,h = map(int, regs[idx]["rect"])
    protected_before[idx] = sa[y:y+h,x:x+w].copy()

clean_arr = sa.copy()
clean_arr[source_union,3] = 0
clean = Image.fromarray(clean_arr, "RGBA")

def style_from_mask(mask):
    pix = sa[mask]
    if not len(pix):
        return (240,240,240,255), (20,20,24,255)
    p = pix[pix[:,3] > 32]
    if not len(p):
        p = pix
    lum = p[:,:3].astype(np.float32) @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
    hi = p[lum >= np.quantile(lum,0.68)]
    lo = p[lum <= np.quantile(lum,0.28)]
    if not len(hi): hi=p
    if not len(lo): lo=p
    fill = tuple(int(np.median(hi[:,k])) for k in range(3)) + (255,)
    stroke = tuple(int(np.median(lo[:,k])) for k in range(3)) + (255,)
    # Never let the fill collapse into the outline on white source families.
    fl = sum(fill[:3]); sl = sum(stroke[:3])
    if fl - sl < 90:
        fill = tuple(min(255, int(v)+70) for v in fill[:3]) + (255,)
        stroke = tuple(max(0, int(v)-40) for v in stroke[:3]) + (255,)
    return fill, stroke

def shear_alpha(alpha, shear=0.16):
    w,h = alpha.size
    extra = int(math.ceil(abs(shear)*h)) + 2
    # x_input = x_output - shear*(h-y), producing a rightward lean at the top.
    return alpha.transform((w+extra,h), Image.Transform.AFFINE,
                           (1.0, -shear, shear*h, 0.0, 1.0, 0.0),
                           resample=Image.Resampling.BICUBIC)

def make_text_alpha(text, fs, stroke_w, italic=True):
    font = ImageFont.truetype(FONT, fs)
    d = ImageDraw.Draw(Image.new("L",(8,8),0))
    tb = d.textbbox((0,0), text, font=font, stroke_width=stroke_w)
    pad = stroke_w + 6
    a = Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-tb[0],pad-tb[1]), text, font=font, fill=255, stroke_width=stroke_w, stroke_fill=255)
    bb = a.getbbox()
    if not bb:
        return None
    a = a.crop(bb)
    if italic:
        a = shear_alpha(a, 0.14)
        bb = a.getbbox()
        if bb: a = a.crop(bb)
    return a

def render_element(e):
    x0,y0,x1,y1 = e["original_bbox"]
    # Target glyph blocks must be wholly inside the exact source bbox.
    bx0 = ((x0 + 3)//4)*4
    by0 = ((y0 + 3)//4)*4
    bx1 = (x1//4)*4
    by1 = (y1//4)*4
    if bx1-bx0 < 12 or by1-by0 < 12:
        raise RuntimeError(("no DXT5-safe interior",e["region_idx"],e["source"],e["original_bbox"]))
    maxw = bx1-bx0-8
    maxh = by1-by0-8
    fill, stroke = style_from_mask(e["source_mask"])
    italic = e["kind"] not in ("small",)
    best = None
    start_fs = min(180, max(18, int((y1-y0)*0.90)))
    for fs in range(start_fs, 11, -1):
        sw = max(1, int(round(fs*0.075)))
        a = make_text_alpha(e["korean"], fs, sw, italic=italic)
        if a is None:
            continue
        # Preserve wide, low source proportions when possible; only shrink to fit.
        scale = min(1.0, maxw/max(1,a.width), maxh/max(1,a.height))
        if scale < 0.42:
            continue
        if scale < 0.999:
            a = a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
            bb = a.getbbox()
            if bb: a = a.crop(bb)
        if a.width <= maxw and a.height <= maxh:
            best = (fs, sw, a, fill, stroke)
            break
    if best is None:
        raise RuntimeError(("render fit failed",e["region_idx"],e["source"],e["korean"],e["original_bbox"]))
    fs, sw, a, fill, stroke = best
    # Build separate fill and stroke masks so source-derived colors remain distinct.
    # Re-render once without stroke, using the same fitted geometry ratio.
    base = Image.new("RGBA",(a.width,a.height),fill)
    # Use the stroke alpha as silhouette; fill with source-derived bright color and a dark 1px edge via max-filter difference.
    aa = np.asarray(a,dtype=np.uint8)
    stroke_mask = a
    inner = a.filter(ImageFilter.MinFilter(3))
    layer_tile = Image.new("RGBA",a.size,stroke)
    layer_tile.putalpha(stroke_mask)
    fill_tile = Image.new("RGBA",a.size,fill)
    fill_tile.putalpha(inner)
    tile = Image.new("RGBA",a.size,(0,0,0,0))
    tile.alpha_composite(layer_tile)
    tile.alpha_composite(fill_tile)
    px = bx0 + 4 + max(0,(maxw-a.width)//2)
    py = by0 + 4 + max(0,(maxh-a.height)//2)
    layer = Image.new("RGBA",(W,H),(0,0,0,0))
    layer.alpha_composite(tile,(px,py))
    lb = layer.getchannel("A").getbbox()
    if not lb:
        raise RuntimeError(("empty render",e["source"]))
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    swd,shd=x1-x0,y1-y0
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1 and lw<=swd and lh<=shd):
        raise RuntimeError(("pre-encode bbox gate",e["source"],[x0,y0,x1,y1],lb))
    e.update({
        "localized_bbox_preencode":list(lb),
        "source_width":swd,"source_height":shd,
        "localized_width_preencode":lw,"localized_height_preencode":lh,
        "delta_left_preencode":lb[0]-x0,"delta_right_preencode":x1-lb[2],
        "delta_top_preencode":lb[1]-y0,"delta_bottom_preencode":y1-lb[3],
        "containment_preencode":"PASS","size_ceiling_preencode":"PASS","positive_margin_preencode":"PASS",
        "font_file":Path(FONT).name,"font_size":fs,"fill_rgba":list(fill),"stroke_rgba":list(stroke),
        "block_safe_bbox":[bx0,by0,bx1,by1]
    })
    return layer

final = clean.copy()
layers=[]
target_union=np.zeros((H,W),dtype=bool)
for e in elements:
    layer=render_element(e)
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(target_union & lm):
        raise RuntimeError(("localized overlap",e["region_idx"],e["source"],int(np.count_nonzero(target_union & lm))))
    target_union |= lm
    layers.append(layer)
    final.alpha_composite(layer)

# No localized target may approach a different localized target within 1px.
touch_count=0
for i,m1 in enumerate([np.asarray(z.getchannel("A"))>0 for z in layers]):
    dil=np.asarray(Image.fromarray((m1.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(layers)):
        m2=np.asarray(layers[j].getchannel("A"))>0
        touch_count += int(np.count_nonzero(dil & m2))
if touch_count:
    raise RuntimeError(("localized 1px touch",touch_count))

# Encode a full image, then transplant only exact-safe BC3 blocks.
raw_final = final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=tmp/"C598_final_raw.png"
tmp_dds=tmp/"C598_final_nv.dds"
raw_final.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,
               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes()
dds_meta(tb)

allowed_raw=np.flipud(allowed)
source_raw=np.flipud(source_union)
target_raw=np.flipud(target_union)
source_alpha_raw=np.flipud(sa[:,:,3])
bw=W//4; bh=H//4
outb=bytearray(sb)
target_blocks=set(); source_full_blocks=set(); source_partial_blocks=set()

def alpha_indices(block):
    bits=int.from_bytes(block[2:8],"little")
    return [(bits>>(3*i))&7 for i in range(16)]

def set_alpha_indices(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx))
    return block[:2]+bits.to_bytes(6,"little")+block[8:]

for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]):
        continue
    for bx in range(bw):
        x=bx*4
        am=allowed_raw[y:y+4,x:x+4]
        sm=source_raw[y:y+4,x:x+4]
        tm=target_raw[y:y+4,x:x+4]
        if not np.any(sm) and not np.any(tm):
            continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am):
                raise RuntimeError(("target block crosses exact bbox",bx,by))
            outb[off:off+16]=tb[off:off+16]
            target_blocks.add((bx,by))
            continue
        if np.all(am):
            # Source-only cleanup in an entirely permitted block:
            # use clean/final alpha coding but preserve original BC1 color bytes.
            outb[off:off+16]=tb[off:off+8]+sb[off+8:off+16]
            source_full_blocks.add((bx,by))
            continue
        # Boundary cleanup: preserve endpoints and color bytes, change only per-pixel alpha indices owned by source text.
        ob=bytes(outb[off:off+16])
        idxs=alpha_indices(ob)
        a4=source_alpha_raw[y:y+4,x:x+4]
        zero_candidates=[idxs[yy*4+xx] for yy in range(4) for xx in range(4)
                         if not sm[yy,xx] and a4[yy,xx] <= 1]
        if not zero_candidates:
            raise RuntimeError(("partial block lacks protected transparent alpha index",bx,by))
        zi=Counter(zero_candidates).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy,xx]:
                    idxs[yy*4+xx]=zi
        nb=set_alpha_indices(ob,idxs)
        if nb[:2]!=ob[:2] or nb[8:]!=ob[8:]:
            raise RuntimeError(("boundary endpoint/color drift",bx,by))
        outb[off:off+16]=nb
        source_partial_blocks.add((bx,by))

candidate.write_bytes(outb)
cand_sha=sha256_bytes(bytes(outb))
dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)

# Global exact decoded-pixel gate.
diff=np.any(sa!=da,axis=2)
diff_out=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3]) & ~allowed))
introduced_visible_out=int(np.count_nonzero((sa[:,:,3]<=1) & (da[:,:,3]>1) & ~allowed))
if diff_out or alpha_out or introduced_visible_out:
    raise RuntimeError(("decoded protected drift",diff_out,alpha_out,introduced_visible_out))

# Source text must be removed unless covered by localized glyph/effect pixels.
guard=np.asarray(Image.fromarray((target_union.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(source_union & (da[:,:,3]>8) & ~guard))
if residue:
    raise RuntimeError(("source residue",residue))

# Protected semantic/art regions remain decoded-pixel exact.
protected_changed={}
for idx,before in protected_before.items():
    x,y,w,h=map(int,regs[idx]["rect"])
    protected_changed[str(idx)]=int(np.count_nonzero(np.any(before!=da[y:y+h,x:x+w],axis=2)))
if any(protected_changed.values()):
    raise RuntimeError(("protected region changed", {k:v for k,v in protected_changed.items() if v}))

# Per-element decoded bbox and exact containment/size/margin report.
for e in elements:
    x0,y0,x1,y1=e["original_bbox"]
    # Candidate alpha inside the source element bbox is entirely localized after source cleanup.
    cm=da[y0:y1,x0:x1,3]>1
    ys,xs=np.nonzero(cm)
    if not len(xs):
        raise RuntimeError(("decoded element empty",e["region_idx"],e["source"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    dw,dh=db[2]-db[0],db[3]-db[1]
    swd,shd=x1-x0,y1-y0
    contain=(db[0]>=x0 and db[1]>=y0 and db[2]<=x1 and db[3]<=y1)
    size=(dw<=swd and dh<=shd)
    pos=(db[0]>x0 and db[1]>y0 and db[2]<x1 and db[3]<y1)
    if not(contain and size and pos):
        raise RuntimeError(("decoded bbox gate",e["region_idx"],e["source"],e["original_bbox"],db,contain,size,pos))
    e.update({
        "localized_bbox":db,"localized_width":dw,"localized_height":dh,
        "delta_left":db[0]-x0,"delta_right":x1-db[2],
        "delta_top":db[1]-y0,"delta_bottom":y1-db[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "rework_status":"B138_DXT5_SOLVER_CANDIDATE"
    })
    e.pop("source_mask",None)

changed_blocks=0; changed_outside_patch=0
patch=target_blocks|source_full_blocks|source_partial_blocks
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch:
                changed_outside_patch+=1
if changed_outside_patch:
    raise RuntimeError(("compressed change outside patch",changed_outside_patch))

# Evidence masks / validator evidence.
def save_mask(m,path):
    Image.fromarray((m.astype(np.uint8)*255),"L").save(path)
source_mask_png=out/"B138_SOURCE_TEXT_MASK.png"
allowed_png=out/"B138_ALLOWED_EXACT_BBOX_MASK.png"
protected_png=out/"B138_PROTECTED_MASK.png"
target_png=out/"B138_TARGET_TEXT_MASK.png"
clean_png=out/"B138_CLEAN_PLATE.png"
save_mask(source_union,source_mask_png)
save_mask(allowed,allowed_png)
save_mask(~allowed,protected_png)
save_mask(target_union,target_png)
clean.save(clean_png)
src_png=tmp/"source_readable.png"; dec_png=tmp/"candidate_readable.png"
src.save(src_png); dec.save(dec_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_png),str(source_mask_png),
                "--report",str(out/"B138_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(dec_png),str(allowed_png),
                "--protected-mask",str(protected_png),"--report",str(out/"B138_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B138_CLEAN_VALIDATION.json").read_text())
finalrep=json.loads((out/"B138_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS":
    raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

def comp(im,bg=(52,52,52,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

# Controller-readable full overview.
overview=Image.new("RGB",(1024,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    overview.paste(z,(0,i*1050+26))
    ImageDraw.Draw(overview).text((5,i*1050+5),label,fill="black")
overview.save(out/"B138_SOURCE_CLEAN_FINAL.jpg",quality=96)

# Target contact proof.
cards=[]
for e in elements:
    x0,y0,x1,y1=e["original_bbox"]; p=16
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=min(2.5,1200/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+42),"white")
    xx=0
    for z in ims:
        c.paste(z,(xx,42)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f"idx={e['region_idx']} {e['source']} -> {e['korean']}",fill="black")
    cards.append(c)
cw=max(c.width for c in cards)
sheet=Image.new("RGB",(cw,max(1,sum(c.height+5 for c in cards))),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+5
sheet.thumbnail((1800,14000),Image.Resampling.LANCZOS)
sheet.save(out/"B138_TARGET_CONTACTS.jpg",quality=96)

# Raw orientation proof.
raw_compare=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",dec_raw)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    raw_compare.paste(z,(0,i*1050+26))
    ImageDraw.Draw(raw_compare).text((5,i*1050+5),label,fill="black")
raw_compare.save(out/"B138_RAW_COMPARE.jpg",quality=96)

binding_correction={
    "prior_c151_stage_mapping":"77..86 as Cape/Imperial/Ancient/Metropolis/Tulip/Skyscrapers/Milky/Floral/Legend/Giant",
    "prior_b78_tested_stage_ids":list(range(77,87)),
    "canonical_contact_corrected_stage_mapping":{str(i):s for i,s,_ in stage_specs},
    "reason":"C151 canonical contact sheet row order plus atlas geometry shows idx76=AT artwork, idx77=MT artwork, with ten stage labels at idx78..87. B78 therefore tested an offset stage set and omitted idx87 Legend.",
    "status":"CORRECTED_IN_B138"
}

report={
    "schema_version":1,"role":"B","run":run,"queue_index":86,"asset":asset,
    "readiness_tier":"REWORK_REQUIRED_CONSTRAINED_DXT5_SOLVER_COMPLETED",
    "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
        "git_blob_sha1":SOURCE_BLOB,"atlas_git_blob_sha1":ATLAS_BLOB,"source_sha256":SOURCE_SHA256},
    "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
    "binding_correction":binding_correction,
    "protected_policy":["OutRun2/OutRun2SP product tokens","MT/AT","Ferrari model names","rank numerals/icons","non-text artwork"],
    "elements_total":len(elements),"elements":elements,
    "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
    "containment":{"elements_pass":len(elements),"decoded_pixels_changed_outside_exact_source_bboxes":diff_out,
        "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,
        "introduced_visible_pixels_outside_exact_source_bboxes":introduced_visible_out,
        "source_residue_pixels":residue,"localized_pair_overlap_pixels":0,
        "localized_pair_1px_touch_pixels":touch_count,"status":"PASS"},
    "compressed_patch":{"target_reencoded_blocks":len(target_blocks),
        "source_only_full_alpha_blocks":len(source_full_blocks),
        "boundary_alpha_index_only_blocks":len(source_partial_blocks),
        "changed_blocks":changed_blocks,"changed_blocks_outside_patch":changed_outside_patch,
        "boundary_endpoints_and_color_bytes_preserved":True,"status":"PASS"},
    "protected_region_changed_pixels":protected_changed,
    "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
    "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
    "status":"B138_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
    "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B138_C598_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":86,"asset":"C598919A","candidate_sha256":cand_sha,
         "localized_physical_elements":len(elements),"bbox_size_positive_margin":f"{len(elements)}/{len(elements)}",
         "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
         "source_residue":residue,"decoded_changed_outside":diff_out,"alpha_outside":alpha_out,
         "protected_regions_changed":sum(protected_changed.values()),
         "boundary_alpha_index_only_blocks":len(source_partial_blocks),
         "worker_status":report["status"],"runtime_validation":"UNTESTED",
         "report":f"localization/graphics/role_B/{run}/B138_C598_REPORT.json"}
(wr/"B138_C598919A.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
