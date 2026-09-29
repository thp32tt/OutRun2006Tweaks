#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "LOCALIZATION-LOCALIZATION_B-00167"
WAVE_ID = "P00082"
ASSET_ID = "49BB5FE5"
INDEX = 152
SOURCE_REPO = "envido32/OR2006Sprites"
SOURCE_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL = "Release/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_BLOB_SHA = "0288babbb9c70e8f092bdd15561db4cadc19dcb3"
SOURCE_SHA256 = "de306cb464b93f6bc3ec63dc9b35b23089ce7d557d1d67fa42d6bba00556fd77"
W, H = 512, 128
EXPECTED_BYTES = 128 + W * H

CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds"
REVIEW = ROOT / "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5"
RUN = ROOT / "localization/graphics/role_B/20260930-B00167-P00082"
REPORT = RUN / "B00167_P00082_INDEX152_DXT5_DECODED_FINAL_QA.json"
TASK_RECORD = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00167.json"
MASK_ARTIFACT = ROOT / "localization/graphics/role_B/20260929-2216-B00152-P00072/B00152_P00072_INDEX152_MASKS_RLE.json"

ELEMENTS = [
    {
        "source": "PRO.", "korean": "프로", "sprite": "sprite_832",
        "bg": [143, 62, 120],
        "effect_raw": [18, 7, 104, 41],
        "safe_raw": [20, 9, 102, 39],
        "safe_readable": [20, 89, 102, 119],
        "expected_removal_pixels": 1688,
    },
    {
        "source": "INS.", "korean": "연주", "sprite": "sprite_833",
        "bg": [107, 161, 77],
        "effect_raw": [136, 6, 214, 41],
        "safe_raw": [138, 8, 212, 39],
        "safe_readable": [138, 89, 212, 120],
        "expected_removal_pixels": 1546,
    },
    {
        "source": "G.M.", "korean": "기타", "sprite": "sprite_834",
        "bg": [244, 104, 46],
        "effect_raw": [252, 7, 333, 41],
        "safe_raw": [254, 9, 331, 39],
        "safe_readable": [254, 89, 331, 119],
        "expected_removal_pixels": 1449,
    },
    {
        "source": "E.R.", "korean": "유로", "sprite": "sprite_835",
        "bg": [192, 60, 63],
        "effect_raw": [374, 8, 444, 40],
        "safe_raw": [376, 10, 442, 38],
        "safe_readable": [376, 90, 442, 118],
        "expected_removal_pixels": 1193,
    },
]
EXPECTED_UNION_PIXELS = 5876

# C127 accepted stable source measurements. The single PRO bowl-biased edge is
# excluded from the family slant lock; the stable median is exactly upright.
STABLE_SLANT_DEG = [0.0, 0.0, -3.2704879231835657, 0.0, -0.8425242607404146,
                    0.0, 0.8951737102110744, -0.8951737102110744]

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dds_info(b: bytes):
    if len(b) < 128 or b[:4] != b"DDS ":
        raise SystemExit("invalid DDS")
    return {
        "height": struct.unpack_from("<I", b, 12)[0],
        "width": struct.unpack_from("<I", b, 16)[0],
        "mips": struct.unpack_from("<I", b, 28)[0] or 1,
        "fourcc": b[84:88].decode("latin1"),
        "header": b[:128],
    }

def rgb565(v: int):
    return np.array([
        ((v >> 11) & 31) * 255 // 31,
        ((v >> 5) & 63) * 255 // 63,
        (v & 31) * 255 // 31,
    ], dtype=np.uint8)

def alpha_palette(a0: int, a1: int):
    if a0 > a1:
        return [
            a0, a1,
            int(round((6*a0 + a1)/7)), int(round((5*a0 + 2*a1)/7)),
            int(round((4*a0 + 3*a1)/7)), int(round((3*a0 + 4*a1)/7)),
            int(round((2*a0 + 5*a1)/7)), int(round((a0 + 6*a1)/7)),
        ]
    return [
        a0, a1,
        int(round((4*a0 + a1)/5)), int(round((3*a0 + 2*a1)/5)),
        int(round((2*a0 + 3*a1)/5)), int(round((a0 + 4*a1)/5)),
        0, 255,
    ]

def color_palette(c0: int, c1: int):
    p0 = rgb565(c0).astype(np.int32)
    p1 = rgb565(c1).astype(np.int32)
    p2 = np.rint((2.0*p0 + p1) / 3.0).astype(np.int32)
    p3 = np.rint((p0 + 2.0*p1) / 3.0).astype(np.int32)
    return np.stack([p0, p1, p2, p3], axis=0)

def decode_bc3(data: bytes):
    info = dds_info(data)
    if (info["width"], info["height"], info["mips"], info["fourcc"]) != (W, H, 1, "DXT5"):
        raise SystemExit(f"unexpected DDS metadata: {info}")
    payload = data[128:]
    if len(payload) != W * H:
        raise SystemExit(f"unexpected DXT5 payload bytes: {len(payload)}")
    out = np.zeros((H, W, 4), dtype=np.uint8)
    pos = 0
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            block = payload[pos:pos+16]; pos += 16
            a0, a1 = block[0], block[1]
            ap = alpha_palette(a0, a1)
            abits = int.from_bytes(block[2:8], "little")
            c0, c1 = struct.unpack_from("<HH", block, 8)
            cp = color_palette(c0, c1)
            cbits = struct.unpack_from("<I", block, 12)[0]
            for py in range(4):
                for px in range(4):
                    i = py*4 + px
                    out[by+py, bx+px, :3] = cp[(cbits >> (2*i)) & 3]
                    out[by+py, bx+px, 3] = ap[(abits >> (3*i)) & 7]
    return out

def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]

def inside(inner, outer):
    return inner is not None and inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]

def find_font():
    spec = "Noto Sans CJK KR:style=Black"
    row = subprocess.check_output(["fc-match", "-f", "%{file}|%{index}\n", spec], text=True).strip().splitlines()[0]
    p, idx = row.rsplit("|", 1)
    if not Path(p).exists():
        raise SystemExit(f"Hangul font not found: {p}")
    return p, int(idx)

def build_removal_masks(src):
    # Reuse the exact immutable B00152 mask that C127 independently reproduced.
    # The dependency fingerprint is unchanged (same canonical blob/SHA and QA contract lineage),
    # so recomputing the heavy mask is intentionally avoided.
    j=json.loads(MASK_ARTIFACT.read_text(encoding="utf-8"))
    sj=j["source"]
    if sj.get("git_blob_sha")!=SOURCE_BLOB_SHA or sj.get("canonical_sha256_from_C125")!=SOURCE_SHA256:
        raise SystemExit("accepted mask artifact source fingerprint mismatch")
    if sj.get("dimensions")!=[W,H] or sj.get("format")!="DXT5_BC3" or int(sj.get("mip_count",0))!=1:
        raise SystemExit("accepted mask artifact DDS fingerprint mismatch")
    runs=j["removal_union"]["runs"]
    if len(runs)!=556 or int(j["removal_union"]["pixels"])!=EXPECTED_UNION_PIXELS:
        raise SystemExit("accepted mask artifact union metadata mismatch")
    union=np.zeros((H,W),dtype=bool)
    for y,x0,x1 in runs:
        if not (0<=y<H and 0<=x0<x1<=W):
            raise SystemExit("accepted mask artifact contains invalid RLE run")
        union[y,x0:x1]=True
    if int(union.sum())!=EXPECTED_UNION_PIXELS:
        raise SystemExit(f"accepted RLE materialization mismatch {int(union.sum())}")
    records=[]
    for e in ELEMENTS:
        x0,y0,x1,y1=e["effect_raw"]
        m=np.zeros((H,W),dtype=bool)
        m[y0:y1,x0:x1]=union[y0:y1,x0:x1]
        n=int(m.sum())
        if n!=e["expected_removal_pixels"] or bbox(m)!=e["effect_raw"]:
            raise SystemExit(f"{e['source']} accepted RLE partition mismatch pixels={n} bbox={bbox(m)}")
        records.append({"source":e["source"],"korean":e["korean"],"pixels":n,"bbox_raw":bbox(m)})
    return union, records

def make_clean(src):
    clean = src.copy()
    effect_union = np.zeros((H,W), dtype=bool)
    for e in ELEMENTS:
        x0,y0,x1,y1 = e["effect_raw"]
        effect_union[y0:y1,x0:x1] = True
        clean[y0:y1,x0:x1,:3] = np.array(e["bg"], dtype=np.uint8)
    # Alpha is immutable for this opaque-cell family.
    clean[:,:,3] = src[:,:,3]
    changed = np.any(clean != src, axis=2)
    outside = changed & ~effect_union
    if int(outside.sum()) != 0:
        raise SystemExit("clean plate changed working pixels outside accepted full-effect bboxes")
    return clean, effect_union
def render_text_mask(text, font_path, font_index, maxw, maxh):
    for size in range(34, 11, -1):
        font = ImageFont.truetype(font_path, size=size, index=font_index)
        probe = Image.new("L", (256,96), 0)
        d = ImageDraw.Draw(probe)
        bb = d.textbbox((0,0), text, font=font)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        if tw <= maxw-2 and th <= maxh-2:
            im = Image.new("L", (tw+4, th+4), 0)
            di = ImageDraw.Draw(im)
            di.text((2-bb[0],2-bb[1]), text, font=font, fill=255)
            ab = im.getbbox()
            if ab is None:
                continue
            im = im.crop(ab)
            if im.width <= maxw-2 and im.height <= maxh-2:
                return im, size
    raise SystemExit(f"cannot fit Korean text {text} in {maxw}x{maxh}")

def render_korean(clean_raw, font_path, font_index):
    clean_disp = np.flipud(clean_raw).copy()
    cand_disp = clean_disp.copy()
    text_mask_disp = np.zeros((H,W), dtype=bool)
    placements = []
    for e in ELEMENTS:
        x0,y0,x1,y1 = e["safe_readable"]
        sw, sh = x1-x0, y1-y0
        mask_img, size = render_text_mask(e["korean"], font_path, font_index, sw, sh)
        x = x0 + (sw-mask_img.width)//2
        y = y0 + (sh-mask_img.height)//2
        a = np.array(mask_img, dtype=np.uint8)
        region = cand_disp[y:y+mask_img.height, x:x+mask_img.width, :3].astype(np.float32)
        af = a.astype(np.float32)[:,:,None] / 255.0
        region = np.rint(region*(1.0-af) + 255.0*af).clip(0,255).astype(np.uint8)
        cand_disp[y:y+mask_img.height, x:x+mask_img.width, :3] = region
        text_mask_disp[y:y+mask_img.height, x:x+mask_img.width] |= (a > 0)
        placements.append({
            "source":e["source"],"korean":e["korean"],"font_size":size,
            "precompression_bbox_readable":bbox(text_mask_disp & rect_mask(e["safe_readable"]))
        })
    return np.flipud(cand_disp).copy(), np.flipud(text_mask_disp).copy(), placements

def rect_mask(r):
    x0,y0,x1,y1 = r
    m=np.zeros((H,W),dtype=bool); m[y0:y1,x0:x1]=True
    return m

def pack565(c):
    r,g,b=[int(v) for v in c]
    return (((r*31+127)//255)<<11) | (((g*63+127)//255)<<5) | ((b*31+127)//255)

def encode_color_block(rgb):
    pts=np.asarray(rgb,dtype=np.int32).reshape(16,3)
    best_i,best_j,best_d=0,0,-1
    for i in range(16):
        for j in range(i+1,16):
            d=int(np.sum((pts[i]-pts[j])**2))
            if d>best_d:
                best_i,best_j,best_d=i,j,d
    c0=pack565(pts[best_i]); c1=pack565(pts[best_j])
    if c0<c1:
        c0,c1=c1,c0
    pal=color_palette(c0,c1)
    bits=0
    for i,p in enumerate(pts):
        ds=np.sum((pal-p[None,:])**2,axis=1)
        idx=int(np.argmin(ds))
        bits |= idx << (2*i)
    return struct.pack("<HHI",c0,c1,bits)

def encode_bc3_color_blocks(base_bytes, base_dec, target_raw, requested_mask):
    logical_diff=np.any(target_raw!=base_dec,axis=2)
    if np.any(logical_diff & ~requested_mask):
        raise SystemExit("precompression target changed outside requested edit mask")
    payload=base_bytes[128:]
    out=bytearray(base_bytes[:128])
    pos=0
    touched_blocks=0
    touched_mask=np.zeros((H,W),dtype=bool)
    for by in range(0,H,4):
        for bx in range(0,W,4):
            block=bytearray(payload[pos:pos+16]); pos+=16
            local=logical_diff[by:by+4,bx:bx+4]
            if np.any(local):
                touched_blocks+=1
                touched_mask[by:by+4,bx:bx+4]=True
                # Preserve the source/base alpha block byte-for-byte; re-encode
                # only the BC1 color half from the complete target 4x4 block.
                block[8:16]=encode_color_block(target_raw[by:by+4,bx:bx+4,:3])
            out += block
    return bytes(out), {
        "touched_color_blocks":touched_blocks,
        "block_aligned_permitted_pixels":int(touched_mask.sum()),
        "logical_edit_pixels":int(logical_diff.sum()),
    }, touched_mask
def residue_count(arr, e, exclude=None):
    x0,y0,x1,y1=e["effect_raw"]
    sub=arr[y0:y1,x0:x1,:3].astype(np.int32)
    bg=np.array(e["bg"],dtype=np.int32)
    delta=sub-bg[None,None,:]
    dist=np.sqrt(np.sum(delta*delta,axis=2))
    m=dist>=10.0
    if exclude is not None:
        m &= ~exclude[y0:y1,x0:x1]
    return int(m.sum())

def nearest_background_palette_gate(dds_bytes, global_mask, e):
    bg=np.array(e["bg"],dtype=np.int32)
    payload=dds_bytes[128:]
    checked=0
    mismatches=0
    ys,xs=np.nonzero(global_mask)
    for y,x in zip(ys.tolist(),xs.tolist()):
        block_index=(y//4)*(W//4)+(x//4)
        off=block_index*16
        block=payload[off:off+16]
        c0,c1=struct.unpack_from("<HH",block,8)
        pal=color_palette(c0,c1)
        ds=np.sum((pal-bg[None,:])**2,axis=1)
        best_dist=int(ds.min())
        cbits=struct.unpack_from("<I",block,12)[0]
        i=(y%4)*4+(x%4)
        actual=(cbits>>(2*i))&3
        checked+=1
        # Different 2-bit indices may decode to the same RGB when BC3 palette
        # interpolation collapses after 565 quantization; compare decoded color
        # distance rather than the index number itself.
        if int(ds[actual])!=best_dist:
            mismatches+=1
    return {"checked_pixels":checked,"non_background_palette_index_pixels":mismatches}

def save_rgba(arr,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(arr,"RGBA").save(path,optimize=False)

def make_comparison(source_disp, clean_disp, final_disp):
    label_h=24
    canvas=Image.new("RGBA",(W*3,H+label_h),(24,24,24,255))
    for i,(im,label) in enumerate([(source_disp,"ENGLISH SOURCE"),(clean_disp,"CLEAN PLATE"),(final_disp,"KOREAN CANDIDATE")]):
        canvas.paste(Image.fromarray(im,"RGBA"),(i*W,label_h))
        ImageDraw.Draw(canvas).text((i*W+6,5),label,fill=(255,255,255,255))
    return canvas

def main():
    now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun2006Tweaks-localization-B00167"})
    with urllib.request.urlopen(req,timeout=60) as f:
        source_bytes=f.read()
    if len(source_bytes)!=EXPECTED_BYTES or sha256_bytes(source_bytes)!=SOURCE_SHA256:
        raise SystemExit(f"canonical source identity mismatch bytes={len(source_bytes)} sha={sha256_bytes(source_bytes)}")
    info=dds_info(source_bytes)
    if (info["width"],info["height"],info["mips"],info["fourcc"])!=(W,H,1,"DXT5"):
        raise SystemExit(f"canonical structure mismatch {info}")

    source_raw=decode_bc3(source_bytes)
    removal_union,mask_records=build_removal_masks(source_raw)
    clean_target,effect_union=make_clean(source_raw)

    # CLEAN_PLATE second visual rework: B visual QA on the first block-reencode
    # result still saw faint English ghosts in source antialias/background
    # transition pixels outside the threshold RLE. C115/C127 already accepted
    # the full-effect envelopes, and these tabs have independently measured
    # flat backgrounds. Flatten the complete accepted effect bbox, then
    # re-encode only color halves of touched BC3 blocks; alpha remains exact.
    clean_bytes,clean_patch_stats,clean_block_mask=encode_bc3_color_blocks(
        source_bytes,source_raw,clean_target,effect_union
    )
    if clean_bytes[:128]!=source_bytes[:128]:
        raise SystemExit("clean DDS header changed")
    for p in range(128,len(source_bytes),16):
        if clean_bytes[p:p+8]!=source_bytes[p:p+8]:
            raise SystemExit("clean BC3 alpha bytes changed")
    clean_final=decode_bc3(clean_bytes)
    clean_changed=np.any(clean_final!=source_raw,axis=2)
    clean_changed_outside_blocks=int((clean_changed & ~clean_block_mask).sum())
    if clean_changed_outside_blocks:
        raise SystemExit(f"decoded clean plate changed outside touched BC3 blocks: {clean_changed_outside_blocks}")
    clean_alpha_changed=int(np.count_nonzero(clean_final[:,:,3]!=source_raw[:,:,3]))
    if clean_alpha_changed:
        raise SystemExit(f"decoded clean plate alpha changed: {clean_alpha_changed}")
    clean_background_gate={}
    for e in ELEMENTS:
        x0,y0,x1,y1=e["effect_raw"]
        clean_sub=clean_final[y0:y1,x0:x1,:3].astype(np.int32)
        bg=np.array(e["bg"],dtype=np.int32)
        clean_dist=np.sqrt(np.sum((clean_sub-bg[None,None,:])**2,axis=2))
        clean_effect_max=float(clean_dist.max()) if clean_dist.size else 0.0
        clean_effect_mean=float(clean_dist.mean()) if clean_dist.size else 0.0
        white_dist=np.sqrt(np.sum((clean_sub-255)**2,axis=2))
        white_core=int((white_dist<=48.0).sum())
        gate={
            "effect_bbox_pixels":int((x1-x0)*(y1-y0)),
            "clean_effect_max_background_distance":clean_effect_max,
            "clean_effect_mean_background_distance":clean_effect_mean,
            "white_core_pixels_in_effect_bbox":white_core,
            "strict_background_distance_limit":12.0,
        }
        clean_background_gate[e["source"]]=gate
        if clean_effect_max>12.0 or white_core:
            raise SystemExit("clean plate full-effect visual-residue gate failed: "+json.dumps(clean_background_gate))
    font_path,font_index=find_font()

    target_raw,text_mask_raw,placements=render_korean(clean_final,font_path,font_index)

    safe_union=np.zeros((H,W),dtype=bool)
    for e in ELEMENTS:
        safe_union |= rect_mask(e["safe_raw"])
    if np.any(text_mask_raw & ~safe_union):
        raise SystemExit("Korean precompression lettering escaped safe boxes")
    allowed_final = effect_union | safe_union
    # Build the Korean candidate from the validated clean DDS, not the original
    # English DDS. Only blocks containing actual Korean working-pixel changes
    # are re-encoded; clean-only blocks remain byte-identical to clean_bytes.
    candidate_bytes,patch_stats,korean_block_mask=encode_bc3_color_blocks(
        clean_bytes,clean_final,target_raw,text_mask_raw
    )
    if len(candidate_bytes)!=EXPECTED_BYTES or candidate_bytes[:128]!=source_bytes[:128]:
        raise SystemExit("candidate DDS size/header changed")
    for p in range(128,len(source_bytes),16):
        if candidate_bytes[p:p+8]!=source_bytes[p:p+8]:
            raise SystemExit("candidate BC3 alpha bytes changed")

    final_raw=decode_bc3(candidate_bytes)
    changed=np.any(final_raw!=source_raw,axis=2)
    block_permitted=clean_block_mask | korean_block_mask
    changed_outside=int((changed & ~block_permitted).sum())
    if changed_outside:
        raise SystemExit(f"decoded-final pixels changed outside touched BC3 blocks: {changed_outside}")
    alpha_changed=int(np.count_nonzero(final_raw[:,:,3]!=source_raw[:,:,3]))
    if alpha_changed:
        raise SystemExit(f"decoded-final alpha changed: {alpha_changed}")
    # Decoded-final visual-geometry gates. Korean foreground is measured
    # by contrast from the accepted flat cell background; old English may not
    # leave high-contrast pixels outside the Korean safe box.
    final_vs_clean=np.any(final_raw!=clean_final,axis=2)
    per_element=[]
    for e in ELEMENTS:
        sm=rect_mask(e["safe_raw"])
        em=rect_mask(e["effect_raw"])
        bg=np.array(e["bg"],dtype=np.int32)
        dist_bg=np.sqrt(np.sum((final_raw[:,:,:3].astype(np.int32)-bg[None,None,:])**2,axis=2))
        dist_white=np.sqrt(np.sum((final_raw[:,:,:3].astype(np.int32)-255)**2,axis=2))
        contrast_threshold=60.0
        fg=(dist_bg>=contrast_threshold) & sm
        rb=bbox(fg)
        fg_pixels=int(fg.sum())
        white_core_pixels=int(((dist_white<=64.0)&sm).sum())
        outside_safe_high_contrast=int(((dist_bg>=contrast_threshold)&em&~sm).sum())
        requested=text_mask_raw & sm
        requested_pixels=int(requested.sum())
        covered=int((final_vs_clean & requested).sum())
        coverage=(covered/requested_pixels) if requested_pixels else 0.0
        if rb is None or not inside(rb,e["safe_raw"]):
            raise SystemExit(f"{e['source']} decoded Korean foreground bbox invalid: {rb}")
        if fg_pixels<80 or white_core_pixels<40 or coverage<0.55:
            raise SystemExit(f"{e['source']} decoded Korean foreground too weak: fg={fg_pixels} white={white_core_pixels} coverage={coverage:.3f}")
        if outside_safe_high_contrast:
            raise SystemExit(f"{e['source']} high-contrast residue escaped safe box: {outside_safe_high_contrast}")
        # Every pixel of the accepted full source-effect envelope not occupied
        # by Korean must stay visually close to the flat reconstructed background.
        bgmask=em & ~text_mask_raw
        residual_high=int(((dist_bg>=contrast_threshold)&bgmask).sum())
        if residual_high:
            raise SystemExit(f"{e['source']} old-English high-contrast residue outside Korean: {residual_high}")
        per_element.append({
            "source":e["source"],"korean":e["korean"],"sprite":e["sprite"],
            "removal_pixels":e["expected_removal_pixels"],
            "source_effect_bbox_raw":e["effect_raw"],
            "candidate_safe_bbox_raw":e["safe_raw"],
            "candidate_safe_bbox_readable":e["safe_readable"],
            "decoded_korean_foreground_bbox_raw":rb,
            "decoded_korean_foreground_pixels":fg_pixels,
            "decoded_korean_white_core_pixels":white_core_pixels,
            "requested_text_pixels":requested_pixels,
            "requested_text_changed_coverage":coverage,
            "high_contrast_pixels_outside_safe":outside_safe_high_contrast,
            "old_english_high_contrast_residue_outside_korean":residual_high,
            "contrast_threshold":contrast_threshold,
            "containment":"PASS",
        })

    # Explicit years and untouched-block gates.
    year_cells=[[0,48,116,96],[116,48,232,96]]
    for yr in year_cells:
        x0,y0,x1,y1=yr
        if not np.array_equal(final_raw[y0:y1,x0:x1],source_raw[y0:y1,x0:x1]):
            raise SystemExit(f"preserve-original year cell changed: {yr}")
    preserve_exact_pixels=int((~block_permitted).sum())
    median_slant=float(np.median(np.array(STABLE_SLANT_DEG,dtype=np.float64)))
    if abs(median_slant)>0.25:
        raise SystemExit(f"unexpected family slant median {median_slant}")

    source_disp=np.flipud(source_raw).copy()
    clean_disp=np.flipud(clean_final).copy()
    final_disp=np.flipud(final_raw).copy()
    REVIEW.mkdir(parents=True,exist_ok=True)
    RUN.mkdir(parents=True,exist_ok=True)
    CANDIDATE.parent.mkdir(parents=True,exist_ok=True)
    save_rgba(source_disp,REVIEW/"source_readable.png")
    save_rgba(clean_disp,REVIEW/"clean_plate_readable.png")
    save_rgba(final_disp,REVIEW/"candidate_readable.png")
    comp=make_comparison(source_disp,clean_disp,final_disp)
    comp.save(REVIEW/"comparison_full_readable.png",optimize=False)
    crop=(0,82,464,126)
    crop_canvas=Image.new("RGBA",((crop[2]-crop[0])*2,(crop[3]-crop[1])+24),(24,24,24,255))
    crop_canvas.paste(Image.fromarray(source_disp,"RGBA").crop(crop),(0,24))
    crop_canvas.paste(Image.fromarray(final_disp,"RGBA").crop(crop),(crop[2]-crop[0],24))
    d=ImageDraw.Draw(crop_canvas)
    d.text((6,5),"ENGLISH SOURCE",fill=(255,255,255,255))
    d.text((crop[2]-crop[0]+6,5),"KOREAN CANDIDATE",fill=(255,255,255,255))
    crop_canvas.save(REVIEW/"comparison_textrow_readable.png",optimize=False)

    CANDIDATE.write_bytes(candidate_bytes)
    candidate_sha=sha256_bytes(candidate_bytes)
    base_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    report={
        "schema_version":9,
        "schema":"outrun-b00167-index152-dxt5-decoded-final-qa-v1",
        "task_id":TASK_ID,"wave_id":WAVE_ID,"lane":"LOCALIZATION_B",
        "recorded_at_kst":now,"status":"PASS",
        "result":"PASS_INDEX152_49BB5FE5_KOREAN_DXT5_SECOND_REWORK_MACHINE_QA_PENDING_B_VISUAL_C_RUNTIME_UNTESTED",
        "supersedes_rejected_commits":[
            "47031bd5b9d3aa0646d5419a12e5685eeda2824d",
            "d6fbe37406b026658b76397d2858d3a0ed184ef7"
        ],
        "second_rework_reason":"Direct B visual inspection of d6fbe found faint English ghosts in CLEAN_PLATE despite threshold-RLE machine gates; CLEAN_PLATE now flattens the complete C115/C127-accepted full-effect envelopes.",
        "source_transport":{
            "google_drive_exact_relative_path":"textures/load/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds",
            "google_drive_outcome":"SOURCE_TRANSPORT_MISS",
            "fallback":"PINNED_UPSTREAM_DIRECT_FILE",
            "fallback_result":"PASS_EXACT_BLOB_AND_SHA256"
        },
        "source":{
            "repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_REL,
            "git_blob_sha":SOURCE_BLOB_SHA,"sha256":SOURCE_SHA256,"bytes":len(source_bytes),
            "width":W,"height":H,"fourcc":"DXT5","mip_count":1,"raw_to_readable":"flip_y"
        },
        "translations":[{"source":e["source"],"korean":e["korean"],"sprite":e["sprite"]} for e in ELEMENTS],
        "mask_lineage":{
            "accepted_input":"LOCALIZATION-LOCALIZATION_B-00152 + C127/Q00025",
            "rule":"inside accepted full-effect bbox AND alpha>16 AND Euclidean RGB distance from accepted dominant background >=10",
            "per_element":mask_records,"union_pixels":int(removal_union.sum()),
            "union_expected":EXPECTED_UNION_PIXELS
        },
        "clean_plate":{
            "method":"second visual rework: flatten complete C115/C127-accepted full-effect bbox to each measured flat cell background; fully re-encode touched BC1 color halves while preserving BC3 alpha bytes exactly",
            "mask_rle_role":"B00152 5876-pixel RLE retained as accepted source-effect evidence; visual-clean coverage intentionally expands only to the already accepted full-effect bbox to remove compression/antialias ghost pixels",
            "decoded_changed_pixels_outside_touched_bc3_blocks":clean_changed_outside_blocks,
            "alpha_changed_pixels":clean_alpha_changed,
            "accepted_rle_reuse":"PASS_B00152_C127_UNCHANGED_FINGERPRINT_5876_PIXELS_556_RUNS",
            "full_effect_bbox_visual_residue_gate_by_element":clean_background_gate,
            "bc3_patch_stats":clean_patch_stats,
            "status":"PASS"
        },
        "style":{
            "font_identifier":f"{Path(font_path).name}#{font_index}",
            "fill":"white core antialiased into canonical cell background",
            "outline_shadow":"none invented; source family is opaque white core with BC3 transition into flat colored cell background",
            "slant_lock":"UPRIGHT_0_DEG",
            "stable_measurement_median_deg":median_slant,
            "source_measurement_note":"PRO bowl-biased edge excluded; accepted stable C127 component measurements center at 0 degrees",
            "placements":placements
        },
        "dds":{
            "candidate_path":str(CANDIDATE.relative_to(ROOT)).replace("\\","/"),
            "candidate_sha256":candidate_sha,"bytes":len(candidate_bytes),
            "header_128_exact":candidate_bytes[:128]==source_bytes[:128],
            "bc3_alpha_bytes_exact_all_blocks":True,
            "bc3_color_endpoints_reencoded_on_touched_blocks":True,
            "patch_strategy":"CLEAN_PLATE and Korean touched blocks fully re-encode BC1 color endpoints+indices; BC3 alpha half remains byte-identical",
            "clean_patch_stats":clean_patch_stats,
            "korean_patch_stats":patch_stats
        },
        "decoded_final":{
            "changed_pixels_outside_block_aligned_permitted_region":changed_outside,
            "alpha_changed_pixels":alpha_changed,
            "protected_pixels_exact":preserve_exact_pixels,
            "per_element":per_element,
            "preserve_year_cells":"PASS_'89_AND_'86_DECODED_RGBA_EXACT",
            "orientation":"PASS_FLIP_Y_RAW_TO_READABLE",
            "containment":"PASS_NO_CHANGE_OUTSIDE_TOUCHED_BC3_BLOCKS"
        },
        "comparison_evidence":[
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_full_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_textrow_readable.png"
        ],
        "visual_validation":"SOURCE_VS_CLEAN_VS_KOREAN_PROOF_RETAINED__B_VISUAL_PENDING__INDEPENDENT_C_VISUAL_PENDING",
        "candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_B_VISUAL_AND_INDEPENDENT_C_VISUAL",
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE",
        "runtime_validation":"UNTESTED","runtime_test_performed":False,
        "build_performed":False,"n100_used":False,"local_clone_used":False,
        "google_drive_used":True,"google_drive_probe_attempted":True,
        "gpt_library_used":False,"uploaded_archive_used":True,"uploaded_archive_role":"NON_AUTHORITATIVE_LOCAL_VISUAL_PREVIEW_ONLY; final candidate source reacquired from pinned upstream direct file","vr_ffb_dx_changes":False
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    task={
        "schema_version":9,"task_id":TASK_ID,"lane":"LOCALIZATION_B",
        "target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":4,
        "wave_id":WAVE_ID,"recorded_at_kst":now,"base_head_sha":base_sha,
        "commit_mode":"GITHUB_ACTIONS_ONE_SHOT_LANE_LOCAL_CANDIDATE_AND_TASK_RECORD",
        "result":report["result"],
        "supersedes_rejected_result_commits":[
            "47031bd5b9d3aa0646d5419a12e5685eeda2824d",
            "d6fbe37406b026658b76397d2858d3a0ed184ef7"
        ],
        "summary":"B00167 second visual rework supersedes 47031 machine-only output and d6fbe first block-reencode output. Direct B visual review showed d6fbe Korean lettering was clear but CLEAN_PLATE retained faint source-English ghosts from antialias/background-transition pixels outside the threshold RLE. The accepted B00152/C127 RLE remains unchanged as source-effect evidence, while clean reconstruction now expands only to the already accepted C115/C127 full-effect bboxes and fills them with each independently measured flat cell background. Touched BC3 blocks fully re-encode their BC1 color half; all alpha bytes stay exact. Korean rendering, safe-bbox containment, zero high-contrast English residue, block-aligned protection, exact '89/'86 preservation and flip_y orientation are machine-gated; final proof is emitted for direct B visual QA before independent C validation. Runtime remains untested.",
        "evidence":[
            str(REPORT.relative_to(ROOT)).replace("\\","/"),
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/source_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/clean_plate_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/candidate_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_full_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_textrow_readable.png",
            str(CANDIDATE.relative_to(ROOT)).replace("\\","/")
        ],
        "material_deliverable":{
            "type":"INDEX152_49BB5FE5_KOREAN_DXT5_CANDIDATE_WITH_DECODED_FINAL_MACHINE_QA",
            "index":INDEX,"asset":ASSET_ID,"candidate_dds_sha256":candidate_sha,
            "candidate_dds_modified":True,"source_removal_union_pixels":int(removal_union.sum()),
            "localized_elements":4,"changed_pixels_outside_block_aligned_permitted_region":changed_outside,
            "alpha_changed_pixels":alpha_changed,"protected_pixels_exact":preserve_exact_pixels,
            "materially_reduces_unresolved_work":True,"material_payload_in_result_commit":True
        },
        "self_qa":"PASS_INDEX152_RLE_LINEAGE__FULL_EFFECT_BBOX_CLEAN_PLATE__BLOCK_REENCODE__ALPHA_EXACT__UPRIGHT_STYLE__FOUR_KOREAN_SAFE_BBOX_FOREGROUND_GATES__ZERO_HIGH_CONTRAST_ENGLISH_RESIDUE__ZERO_CHANGE_OUTSIDE_TOUCHED_BLOCKS__FLIP_Y__YEARS_EXACT",
        "candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_B_VISUAL_AND_INDEPENDENT_C_VISUAL",
        "shared_state_modified":False,"peer_lane_files_modified":False,
        "candidate_dds_modified":True,"runtime_test_performed":False,"build_performed":False,
        "n100_used":False,"local_clone_used":False,"google_drive_used":True,
        "google_drive_probe_attempted":True,"google_drive_source_outcome":"SOURCE_TRANSPORT_MISS",
        "source_acquisition_fallback":"PINNED_UPSTREAM_DIRECT_FILE",
        "gpt_library_used":False,"uploaded_archive_used":True,"uploaded_archive_role":"NON_AUTHORITATIVE_LOCAL_VISUAL_PREVIEW_ONLY; final material reacquired from pinned upstream direct file","vr_ffb_dx_changes":False,
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","runtime_validation":"UNTESTED"
    }
    TASK_RECORD.parent.mkdir(parents=True,exist_ok=True)
    TASK_RECORD.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","candidate_sha256":candidate_sha,
                      "changed_outside":changed_outside,"alpha_changed":alpha_changed,
                      "clean_background_gate":clean_background_gate,"per_element":per_element},ensure_ascii=False))

if __name__ == "__main__":
    main()
