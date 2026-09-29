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
    return np.stack([p0, p1, (2*p0+p1)//3, (p0+2*p1)//3], axis=0)

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
    union = np.zeros((H, W), dtype=bool)
    records = []
    for e in ELEMENTS:
        x0,y0,x1,y1 = e["effect_raw"]
        sub = src[y0:y1, x0:x1]
        bg = np.array(e["bg"], dtype=np.int16)
        dist = np.sqrt(np.sum((sub[:,:,:3].astype(np.int16)-bg[None,None,:])**2, axis=2))
        local = (sub[:,:,3] > 16) & (dist >= 10.0)
        m = np.zeros((H,W), dtype=bool)
        m[y0:y1,x0:x1] = local
        n = int(m.sum())
        if n != e["expected_removal_pixels"]:
            raise SystemExit(f"{e['source']} removal mask count mismatch {n} != {e['expected_removal_pixels']}")
        if np.any(union & m):
            raise SystemExit(f"{e['source']} removal mask overlaps another element")
        union |= m
        records.append({"source":e["source"],"korean":e["korean"],"pixels":n,"bbox_raw":bbox(m)})
    if int(union.sum()) != EXPECTED_UNION_PIXELS:
        raise SystemExit(f"union removal mask mismatch {int(union.sum())}")
    return union, records

def make_clean(src, removal_union):
    clean = src.copy()
    for e in ELEMENTS:
        x0,y0,x1,y1 = e["effect_raw"]
        submask = removal_union[y0:y1,x0:x1]
        clean_sub = clean[y0:y1,x0:x1]
        clean_sub[submask,:3] = np.array(e["bg"], dtype=np.uint8)
        clean[y0:y1,x0:x1] = clean_sub
    # Alpha is immutable for this opaque-cell family.
    clean[:,:,3] = src[:,:,3]
    changed = np.any(clean != src, axis=2)
    outside = changed & ~removal_union
    if int(outside.sum()) != 0:
        raise SystemExit("clean plate changed pixels outside accepted removal union")
    return clean

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

def patch_bc3_color_indices(source_bytes, src_dec, target_raw, allowed_change):
    payload = source_bytes[128:]
    out = bytearray(source_bytes[:128])
    pos=0
    touched_blocks=0
    changed_index_pixels=0
    target_diff = np.any(target_raw != src_dec, axis=2)
    if np.any(target_diff & ~allowed_change):
        raise SystemExit("precompression target changed outside allowed edit union")
    for by in range(0,H,4):
        for bx in range(0,W,4):
            block=bytearray(payload[pos:pos+16]); pos+=16
            c0,c1=struct.unpack_from("<HH",block,8)
            pal=color_palette(c0,c1)
            bits=struct.unpack_from("<I",block,12)[0]
            orig_bits=bits
            for py in range(4):
                for px in range(4):
                    y,x=by+py,bx+px
                    if not target_diff[y,x]:
                        continue
                    i=py*4+px
                    pix=target_raw[y,x,:3].astype(np.int32)
                    ds=np.sum((pal-pix[None,:])**2,axis=1)
                    ni=int(np.argmin(ds))
                    oi=(bits>>(2*i))&3
                    if ni!=oi:
                        bits &= ~(3<<(2*i))
                        bits |= ni<<(2*i)
                        changed_index_pixels += 1
            if bits != orig_bits:
                touched_blocks += 1
                struct.pack_into("<I",block,12,bits)
            out += block
    return bytes(out), {"touched_blocks":touched_blocks,"changed_color_index_pixels":changed_index_pixels}

def residue_count(arr, e, exclude=None):
    x0,y0,x1,y1=e["effect_raw"]
    sub=arr[y0:y1,x0:x1,:3].astype(np.int16)
    bg=np.array(e["bg"],dtype=np.int16)
    dist=np.sqrt(np.sum((sub-bg[None,None,:])**2,axis=2))
    m=dist>=10.0
    if exclude is not None:
        m &= ~exclude[y0:y1,x0:x1]
    return int(m.sum())

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
    clean_target=make_clean(source_raw,removal_union)

    # Clean-only BC3 roundtrip with immutable alpha/endpoints and per-pixel color-index edits.
    clean_bytes,clean_patch_stats=patch_bc3_color_indices(source_bytes,source_raw,clean_target,removal_union)
    if clean_bytes[:128]!=source_bytes[:128]:
        raise SystemExit("clean DDS header changed")
    clean_final=decode_bc3(clean_bytes)
    clean_changed=np.any(clean_final!=source_raw,axis=2)
    if int((clean_changed & ~removal_union).sum())!=0:
        raise SystemExit("decoded clean plate changed protected pixels")
    clean_residue={e["source"]:residue_count(clean_final,e) for e in ELEMENTS}
    if any(v!=0 for v in clean_residue.values()):
        raise SystemExit("decoded clean plate retains >=10 RGB-distance source effect residue: "+json.dumps(clean_residue))

    font_path,font_index=find_font()
    target_raw,text_mask_raw,placements=render_korean(clean_final,font_path,font_index)

    safe_union=np.zeros((H,W),dtype=bool)
    for e in ELEMENTS:
        safe_union |= rect_mask(e["safe_raw"])
    if np.any(text_mask_raw & ~safe_union):
        raise SystemExit("Korean precompression lettering escaped safe boxes")
    allowed_final = removal_union | safe_union
    candidate_bytes,patch_stats=patch_bc3_color_indices(source_bytes,source_raw,target_raw,allowed_final)
    if len(candidate_bytes)!=EXPECTED_BYTES or candidate_bytes[:128]!=source_bytes[:128]:
        raise SystemExit("candidate DDS size/header changed")
    # Alpha sections are byte-identical for every BC3 block by construction.
    for p in range(128,len(source_bytes),16):
        if candidate_bytes[p:p+8]!=source_bytes[p:p+8]:
            raise SystemExit("BC3 alpha bytes changed")
        if candidate_bytes[p+8:p+12]!=source_bytes[p+8:p+12]:
            raise SystemExit("BC3 color endpoints changed")

    final_raw=decode_bc3(candidate_bytes)
    changed=np.any(final_raw!=source_raw,axis=2)
    changed_outside=int((changed & ~allowed_final).sum())
    if changed_outside:
        raise SystemExit(f"decoded-final protected pixels changed: {changed_outside}")
    alpha_changed=int(np.count_nonzero(final_raw[:,:,3]!=source_raw[:,:,3]))
    if alpha_changed:
        raise SystemExit(f"decoded-final alpha changed: {alpha_changed}")

    # Compare final Korean candidate to decoded clean plate to isolate Korean lettering.
    final_vs_clean=np.any(final_raw!=clean_final,axis=2)
    per_element=[]
    for e in ELEMENTS:
        sm=rect_mask(e["safe_raw"])
        lm=final_vs_clean & sm
        rb=bbox(lm)
        if rb is None or not inside(rb,e["safe_raw"]):
            raise SystemExit(f"{e['source']} decoded Korean lettering bbox invalid: {rb}")
        # Outside Korean lettering, old source effect must remain fully cleaned.
        res=residue_count(final_raw,e,exclude=lm)
        if res:
            raise SystemExit(f"{e['source']} decoded final source residue: {res}")
        per_element.append({
            "source":e["source"],"korean":e["korean"],"sprite":e["sprite"],
            "removal_pixels":e["expected_removal_pixels"],
            "source_effect_bbox_raw":e["effect_raw"],
            "candidate_safe_bbox_raw":e["safe_raw"],
            "candidate_safe_bbox_readable":e["safe_readable"],
            "decoded_korean_change_bbox_raw":rb,
            "decoded_korean_change_pixels":int(lm.sum()),
            "source_residue_pixels_outside_korean":res,
            "containment":"PASS",
        })

    # Explicit years/preserved-area gate: every pixel outside removal+safe union is byte-identical after decode.
    preserve_exact_pixels=int((~allowed_final).sum())
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
        "result":"PASS_INDEX152_49BB5FE5_KOREAN_DXT5_CANDIDATE_MACHINE_SELF_QA_PENDING_C_RUNTIME_UNTESTED",
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
            "method":"replace accepted removal-mask pixels with each cell's independently measured dominant background, then patch only original BC3 color indices while preserving endpoints+alpha",
            "decoded_changed_pixels_outside_removal_union":int((clean_changed & ~removal_union).sum()),
            "decoded_source_residue_by_element":clean_residue,
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
            "bc3_color_endpoints_exact_all_blocks":True,
            "patch_strategy":"preserve source BC3 endpoints/alpha; modify only 2-bit color indices for pixels whose clean/render target differs",
            "patch_stats":patch_stats
        },
        "decoded_final":{
            "changed_pixels_outside_removal_or_safe_union":changed_outside,
            "alpha_changed_pixels":alpha_changed,
            "protected_pixels_exact":preserve_exact_pixels,
            "per_element":per_element,
            "preserve_year_cells":"'89 and '86 untouched because all final changes are confined to removal_union OR four safe bboxes",
            "orientation":"PASS_FLIP_Y_RAW_TO_READABLE",
            "containment":"PASS_ZERO_PIXEL_OUTSIDE_EDIT_UNION"
        },
        "comparison_evidence":[
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_full_readable.png",
            "localization/graphics/KOREAN_PNG_REVIEW/49BB5FE5/comparison_textrow_readable.png"
        ],
        "visual_validation":"SOURCE_VS_KOREAN_PROOF_RETAINED__INDEPENDENT_C_VISUAL_PENDING",
        "candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_INDEPENDENT_C_VISUAL",
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE",
        "runtime_validation":"UNTESTED","runtime_test_performed":False,
        "build_performed":False,"n100_used":False,"local_clone_used":False,
        "google_drive_used":False,"google_drive_probe_attempted":True,
        "gpt_library_used":False,"uploaded_archive_used":False,"vr_ffb_dx_changes":False
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    task={
        "schema_version":9,"task_id":TASK_ID,"lane":"LOCALIZATION_B",
        "target_branch":"korean-localization-clean","attempt":"1/3","chat_rollover":1,
        "wave_id":WAVE_ID,"recorded_at_kst":now,"base_head_sha":base_sha,
        "commit_mode":"GITHUB_ACTIONS_ONE_SHOT_LANE_LOCAL_CANDIDATE_AND_TASK_RECORD",
        "result":report["result"],
        "summary":"Resumed B00167 from current GitHub SSOT without repeating QA-pending B00160/index112. Selected even index152/49BB5FE5 as the closest non-QA-pending one-stage-to-render asset after C127 accepted exact canonical source identity and 4/4 pixel removal/protection masks. The approved Drive exact-relative-path source probe missed and correctly fell through to the pinned immutable v0.25.10a upstream blob. Reproduced all accepted masks, built a clean plate, locked the near-upright family slant to 0 degrees from stable accepted measurements, rendered the four approved Korean labels, and produced a DXT5 candidate by preserving every source BC3 alpha byte/color endpoint and changing only per-pixel color indices. Decoded-final machine QA passes zero protected-pixel changes, exact alpha preservation, four safe-bbox containments, source-residue removal outside Korean lettering, raw/readable flip_y orientation, and explicit preservation of '89/'86. Independent C visual/static QA and real-game validation remain pending.",
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
            "localized_elements":4,"changed_pixels_outside_edit_union":changed_outside,
            "alpha_changed_pixels":alpha_changed,"protected_pixels_exact":preserve_exact_pixels,
            "materially_reduces_unresolved_work":True,"material_payload_in_result_commit":True
        },
        "self_qa":"PASS_INDEX152_EXACT_SOURCE_MASK_REPRODUCTION__CLEAN_PLATE_NO_RESIDUE__UPRIGHT_STYLE_LOCK__FOUR_KOREAN_SAFE_BBOXES__DXT5_HEADER_ALPHA_ENDPOINTS_EXACT__DECODED_FINAL_ZERO_PROTECTED_CHANGE__FLIP_Y__YEARS_PRESERVED",
        "candidate_static_qa":"PASS_MACHINE_DECODED_FINAL_PENDING_INDEPENDENT_C_VISUAL",
        "shared_state_modified":False,"peer_lane_files_modified":False,
        "candidate_dds_modified":True,"runtime_test_performed":False,"build_performed":False,
        "n100_used":False,"local_clone_used":False,"google_drive_used":False,
        "google_drive_probe_attempted":True,"google_drive_source_outcome":"SOURCE_TRANSPORT_MISS",
        "source_acquisition_fallback":"PINNED_UPSTREAM_DIRECT_FILE",
        "gpt_library_used":False,"uploaded_archive_used":False,"vr_ffb_dx_changes":False,
        "automation_validation":"PENDING","validation_mode":"C_BATCH_GATE","runtime_validation":"UNTESTED"
    }
    TASK_RECORD.parent.mkdir(parents=True,exist_ok=True)
    TASK_RECORD.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","candidate_sha256":candidate_sha,
                      "changed_outside":changed_outside,"alpha_changed":alpha_changed,
                      "clean_residue":clean_residue,"per_element":per_element},ensure_ascii=False))

if __name__ == "__main__":
    main()
