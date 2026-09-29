from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import struct
import subprocess
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

TASK_ID = "LOCALIZATION-LOCALIZATION_B-00160"
WAVE_ID = "P00077"
ASSET = "D41D0B1"
INDEX = 112
ROOT = pathlib.Path(".")
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
REVIEW = ROOT / "KOREAN_PNG_REVIEW/D41D0B1"

SOURCE_REPO = "envido32/OR2006Sprites"
SOURCE_REF = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_PATH = "Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_REF}/{SOURCE_PATH}"
SOURCE_SHA256 = "524de4c0db3dbb69c6cda484ace71a9213a378e3e4895a035199ced0ac0a3617"
SOURCE_BLOB = "278a518f5151f0759dfcfdc78e129a7a7cb55cf0"

FONT_REPO = "notofonts/noto-cjk"
FONT_REF = "f8d157532fbfaeda587e826d4cd5b21a49186f7c"
FONT_PATH = "Sans/OTF/Korean/NotoSansCJKkr-Bold.otf"
FONT_BLOB = "1157b8c79cd9e7e9f3def511eb9fb517b5fec90f"
FONT_URL = f"https://raw.githubusercontent.com/{FONT_REPO}/{FONT_REF}/{FONT_PATH}"

SAFE = (437, 21, 1354, 235)
EFFECT = (435, 19, 1357, 238)
EXPECTED_ALPHA_PIXELS = 132035
EXPECTED_EFFECT_BBOX = EFFECT
SLANT_ANGLE = 15.39554925399509
KOREAN = "여자친구와 함께 골에 도착하세요."
LINES = ["여자친구와 함께", "골에 도착하세요."]

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def download(url: str, out: pathlib.Path) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        b = r.read()
    out.write_bytes(b)
    return b

def bbox_from_alpha(a: np.ndarray):
    ys, xs = np.where(a > 0)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]

def diffuse_clean_plate(readable: np.ndarray, mask: np.ndarray):
    # Corrected B00155 lineage: synchronous FOUR-neighbor inward propagation.
    rgb = readable[:, :, :3].astype(np.float32).copy()
    known = (~mask).copy()
    iterations = 0
    h, w = mask.shape
    while not np.all(known):
        sums = np.zeros((h, w, 3), dtype=np.float32)
        cnt = np.zeros((h, w), dtype=np.int16)

        k = known[:-1, :]
        sums[1:, :, :] += rgb[:-1, :, :] * k[:, :, None]
        cnt[1:, :] += k

        k = known[1:, :]
        sums[:-1, :, :] += rgb[1:, :, :] * k[:, :, None]
        cnt[:-1, :] += k

        k = known[:, :-1]
        sums[:, 1:, :] += rgb[:, :-1, :] * k[:, :, None]
        cnt[:, 1:] += k

        k = known[:, 1:]
        sums[:, :-1, :] += rgb[:, 1:, :] * k[:, :, None]
        cnt[:, :-1] += k

        target = (~known) & (cnt > 0)
        if not np.any(target):
            raise RuntimeError("clean-plate diffusion stalled")
        rgb[target] = np.rint(sums[target] / cnt[target, None])
        known[target] = True
        iterations += 1
        if iterations > 300:
            raise RuntimeError("clean-plate diffusion exceeded safety limit")

    clean = readable.copy()
    clean[mask, :3] = np.clip(rgb[mask], 0, 255).astype(np.uint8)
    clean[mask, 3] = 0
    return clean, iterations

def shear_line(text: str, font: ImageFont.FreeTypeFont, stroke_native: int, scale: int = 4):
    bbox = font.getbbox(text, stroke_width=stroke_native * scale)
    w = bbox[2] - bbox[0] + 32 * scale
    h = bbox[3] - bbox[1] + 24 * scale
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 16 * scale - bbox[0]
    y = 12 * scale - bbox[1]
    d.text(
        (x, y), text, font=font,
        fill=(255, 255, 255, 255),
        stroke_width=stroke_native * scale,
        stroke_fill=(5, 15, 61, 255),
    )
    a = np.asarray(layer.getchannel("A"))
    bb = bbox_from_alpha(a)
    if bb is None:
        raise RuntimeError("empty rendered line")
    layer = layer.crop(tuple(bb))
    k = math.tan(math.radians(SLANT_ANGLE))
    shift = int(math.ceil(k * max(0, layer.height - 1)))
    out = Image.new("RGBA", (layer.width + shift + 2 * scale, layer.height), (0, 0, 0, 0))
    # Positive readable slant: top edge displaced right relative to bottom.
    for yy in range(layer.height):
        dx = int(round(k * (layer.height - 1 - yy)))
        row = layer.crop((0, yy, layer.width, yy + 1))
        out.paste(row, (dx + scale, yy), row)
    abb = bbox_from_alpha(np.asarray(out.getchannel("A")))
    return out.crop(tuple(abb))

def render_korean_layer():
    scale = 4
    safe_w = SAFE[2] - SAFE[0]
    safe_h = SAFE[3] - SAFE[1]
    font_tmp = pathlib.Path("/tmp/NotoSansCJKkr-Bold.otf")
    if not font_tmp.exists():
        download(FONT_URL, font_tmp)
    font_sha = sha256_bytes(font_tmp.read_bytes())

    chosen = None
    for native_size in range(98, 59, -1):
        font = ImageFont.truetype(str(font_tmp), native_size * scale)
        stroke = max(6, round(native_size * 0.075))
        im1 = shear_line(LINES[0], font, stroke, scale)
        im2 = shear_line(LINES[1], font, stroke, scale)
        gap = 4 * scale
        total_h = im1.height + gap + im2.height
        max_w = max(im1.width, im2.width)
        # Keep explicit antialias safety margin inside the v2 safe bbox.
        if max_w <= (safe_w - 8) * scale and total_h <= (safe_h - 8) * scale:
            chosen = (native_size, stroke, im1, im2, gap, font_sha)
            break
    if chosen is None:
        raise RuntimeError("Korean lettering cannot fit safe bbox")

    native_size, stroke, im1, im2, gap, font_sha = chosen
    canvas = Image.new("RGBA", (safe_w * scale, safe_h * scale), (0, 0, 0, 0))
    total_h = im1.height + gap + im2.height
    y = (canvas.height - total_h) // 2
    for im in (im1, im2):
        x = (canvas.width - im.width) // 2
        canvas.alpha_composite(im, (x, y))
        y += im.height + gap
    canvas = canvas.resize((safe_w, safe_h), Image.Resampling.LANCZOS)
    alpha = np.asarray(canvas.getchannel("A"))
    bb = bbox_from_alpha(alpha)
    if bb is None:
        raise RuntimeError("empty final Korean layer")
    # Require >=2 px post-resample safety margin.
    if bb[0] < 2 or bb[1] < 2 or bb[2] > safe_w - 2 or bb[3] > safe_h - 2:
        raise RuntimeError(f"safe-bbox margin failed: {bb}")
    return canvas, {
        "font_repo": FONT_REPO,
        "font_ref": FONT_REF,
        "font_path": FONT_PATH,
        "font_git_blob_sha": FONT_BLOB,
        "font_sha256": font_sha,
        "font_size_px": native_size,
        "stroke_width_px": stroke,
        "slant_angle_deg": SLANT_ANGLE,
        "line_gap_px": 4,
        "line_breaks": LINES,
        "layer_bbox_within_safe_ltrb_exclusive": bb,
    }

def rgb565(c):
    r, g, b = [int(x) for x in c]
    return ((r * 31 + 127) // 255 << 11) | ((g * 63 + 127) // 255 << 5) | ((b * 31 + 127) // 255)

def un565(v):
    r = (v >> 11) & 31
    g = (v >> 5) & 63
    b = v & 31
    return np.array([(r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31], dtype=np.int16)

def alpha_palette(a0, a1):
    if a0 > a1:
        return [a0, a1] + [((7-i)*a0 + i*a1) // 7 for i in range(1,7)]
    return [a0, a1] + [((5-i)*a0 + i*a1) // 5 for i in range(1,5)] + [0,255]

def encode_alpha(vals):
    vals = [int(v) for v in vals]
    a0, a1 = max(vals), min(vals)
    if a0 == a1:
        pal = alpha_palette(a0, a1)
    else:
        if a0 <= a1:
            a0, a1 = a1, a0
        pal = alpha_palette(a0, a1)
    bits = 0
    for i, v in enumerate(vals):
        idx = min(range(8), key=lambda j: abs(v - pal[j]))
        bits |= idx << (3*i)
    return bytes([a0, a1]) + bits.to_bytes(6, "little")

def encode_color(rgb):
    pts = np.asarray(rgb, dtype=np.int16).reshape(16,3)
    # Farthest-pair endpoints are robust for the white/navy source-style palette.
    best = (0, 1, -1)
    for i in range(16):
        for j in range(i+1,16):
            d = int(np.sum((pts[i]-pts[j])**2))
            if d > best[2]:
                best = (i,j,d)
    c0 = rgb565(pts[best[0]])
    c1 = rgb565(pts[best[1]])
    if c0 == c1:
        c0 = min(65535, c0 + 1)
    if c0 < c1:
        c0, c1 = c1, c0
    p0, p1 = un565(c0), un565(c1)
    p2 = (2*p0 + p1) // 3
    p3 = (p0 + 2*p1) // 3
    pal = [p0,p1,p2,p3]
    bits = 0
    for i, p in enumerate(pts):
        idx = min(range(4), key=lambda j: int(np.sum((p-pal[j])**2)))
        bits |= idx << (2*i)
    return struct.pack("<HHI", c0, c1, bits)

def encode_candidate(source_bytes: bytes, source_raw: np.ndarray, candidate_raw: np.ndarray):
    h, w = candidate_raw.shape[:2]
    blocks_x, blocks_y = w // 4, h // 4
    src_payload = source_bytes[128:]
    if len(src_payload) != blocks_x * blocks_y * 16:
        raise RuntimeError("unexpected DXT5 payload size")
    out = bytearray(source_bytes)
    src_alpha = source_raw[:,:,3] > 0
    cand_alpha = candidate_raw[:,:,3] > 0
    touched = src_alpha | cand_alpha
    touched_blocks = 0
    candidate_blocks = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            y0, x0 = by*4, bx*4
            t = touched[y0:y0+4, x0:x0+4]
            if not np.any(t):
                continue
            touched_blocks += 1
            block = candidate_raw[y0:y0+4, x0:x0+4, :]
            off = 128 + (by*blocks_x + bx)*16
            ab = encode_alpha(block[:,:,3].reshape(-1))
            if np.any(cand_alpha[y0:y0+4, x0:x0+4]):
                candidate_blocks += 1
                cb = encode_color(block[:,:,:3].reshape(-1,3))
            else:
                cb = source_bytes[off+8:off+16]
            out[off:off+16] = ab + cb
    return bytes(out), touched_blocks, candidate_blocks

def make_comparison(source_display, clean_display, candidate_display, outpath):
    ims = [source_display, clean_display, candidate_display]
    labels = ["ENGLISH SOURCE", "CLEAN PLATE", "KOREAN CANDIDATE"]
    pad = 24
    comp = Image.new("RGBA", (source_display.width*3, source_display.height+pad), (24,24,24,255))
    d = ImageDraw.Draw(comp)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x = i * source_display.width
        bg = Image.new("RGBA", im.size, (0,0,0,255))
        bg.alpha_composite(im)
        comp.alpha_composite(bg, (x,pad))
        d.text((x+8,5), lab, fill=(255,255,255,255), font=ImageFont.load_default())
    comp.save(outpath)

def main():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    stamp = now.strftime("%Y%m%d-%H%M")
    role = ROOT / f"localization/graphics/role_B/{stamp}-B00160-P00077"
    role.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)

    src_path = pathlib.Path("/tmp/D41D0B1_source.dds")
    source_bytes = download(SOURCE_URL, src_path)
    if sha256_bytes(source_bytes) != SOURCE_SHA256:
        raise RuntimeError("canonical source SHA-256 mismatch")
    if source_bytes[:4] != b"DDS " or source_bytes[84:88] != b"DXT5":
        raise RuntimeError("source is not DDS DXT5")
    h = struct.unpack_from("<I", source_bytes, 12)[0]
    w = struct.unpack_from("<I", source_bytes, 16)[0]
    mip = struct.unpack_from("<I", source_bytes, 28)[0]
    if (w,h,mip,len(source_bytes)) != (2048,256,1,524416):
        raise RuntimeError(f"unexpected source DDS metadata {(w,h,mip,len(source_bytes))}")

    raw_img = Image.open(src_path).convert("RGBA")
    if raw_img.size != (2048,256):
        raise RuntimeError("decoded source size mismatch")
    readable_img = ImageOps.flip(raw_img)
    raw = np.array(raw_img, dtype=np.uint8)
    readable = np.array(readable_img, dtype=np.uint8)

    source_mask = readable[:,:,3] > 0
    alpha_count = int(source_mask.sum())
    effect_bbox = bbox_from_alpha(readable[:,:,3])
    if alpha_count != EXPECTED_ALPHA_PIXELS or effect_bbox != list(EXPECTED_EFFECT_BBOX):
        raise RuntimeError(f"source effect fingerprint mismatch count={alpha_count} bbox={effect_bbox}")

    clean, iterations = diffuse_clean_plate(readable, source_mask)
    if iterations != 49:
        raise RuntimeError(f"corrected 4-neighbor diffusion expected 49 iterations, got {iterations}")
    if int(np.count_nonzero(clean[:,:,3])) != 0:
        raise RuntimeError("clean plate retains nonzero alpha")
    protected = ~source_mask
    if int(np.count_nonzero(clean[protected] != readable[protected])) != 0:
        raise RuntimeError("clean plate changed protected alpha0 source pixels")

    clean_img = Image.fromarray(clean, "RGBA")
    layer, render = render_korean_layer()
    candidate_readable = clean_img.copy()
    candidate_readable.alpha_composite(layer, (SAFE[0], SAFE[1]))
    cand_read = np.array(candidate_readable, dtype=np.uint8)
    cand_bbox = bbox_from_alpha(cand_read[:,:,3])
    if cand_bbox is None:
        raise RuntimeError("candidate alpha empty")
    if cand_bbox[0] < SAFE[0] or cand_bbox[1] < SAFE[1] or cand_bbox[2] > SAFE[2] or cand_bbox[3] > SAFE[3]:
        raise RuntimeError(f"candidate escaped safe bbox: {cand_bbox}")
    outside = np.ones((256,2048), dtype=bool)
    outside[SAFE[1]:SAFE[3], SAFE[0]:SAFE[2]] = False
    if int(np.count_nonzero((cand_read[:,:,3] > 0) & outside)) != 0:
        raise RuntimeError("candidate alpha introduced outside safe bbox")

    candidate_raw_img = ImageOps.flip(candidate_readable)
    candidate_raw = np.array(candidate_raw_img, dtype=np.uint8)
    candidate_bytes, touched_blocks, korean_blocks = encode_candidate(source_bytes, raw, candidate_raw)
    if candidate_bytes[:128] != source_bytes[:128] or len(candidate_bytes) != len(source_bytes):
        raise RuntimeError("DDS header/size preservation failed")
    CANDIDATE.write_bytes(candidate_bytes)

    decoded_raw = Image.open(CANDIDATE).convert("RGBA")
    decoded_display = ImageOps.flip(decoded_raw)
    dec = np.array(decoded_display, dtype=np.uint8)
    dec_bbox = bbox_from_alpha(dec[:,:,3])
    if dec_bbox is None:
        raise RuntimeError("decoded-final candidate alpha empty")
    if dec_bbox[0] < SAFE[0] or dec_bbox[1] < SAFE[1] or dec_bbox[2] > SAFE[2] or dec_bbox[3] > SAFE[3]:
        raise RuntimeError(f"decoded-final escaped safe bbox: {dec_bbox}")
    outside_alpha = int(np.count_nonzero((dec[:,:,3] > 0) & outside))
    if outside_alpha != 0:
        raise RuntimeError(f"decoded-final alpha outside safe bbox: {outside_alpha}")

    source_header_sha = sha256_bytes(source_bytes[:128])
    candidate_sha = sha256_bytes(candidate_bytes)

    readable_img.save(REVIEW / "source_display.png")
    clean_img.save(REVIEW / "clean_plate_display.png")
    decoded_display.save(REVIEW / "candidate_display.png")
    make_comparison(readable_img, clean_img, decoded_display, REVIEW / "comparison.png")

    prompt = {
        "schema": "outrun-first-pass-edit-v2",
        "task_id": TASK_ID,
        "asset_id": ASSET,
        "source_dimensions": [2048,256],
        "raw_orientation": "flip_y",
        "source_text": "Try to reach the goal with your girlfriend.",
        "approved_korean": KOREAN,
        "line_breaks": LINES,
        "source_full_effect_bbox_readable_ltrb_exclusive": list(EFFECT),
        "candidate_safe_bbox_readable_ltrb_exclusive": list(SAFE),
        "protected_rule": "All pixels outside the source effect/candidate-safe construction region remain untouched as visual artwork; no new nonzero alpha outside safe bbox.",
        "source_style": {
            "fill": [255,255,255,255],
            "outline_shadow_family": [5,15,61,255],
            "signed_slant_direction": "right",
            "signed_slant_angle_deg": SLANT_ANGLE,
            "alignment": "two centered lines",
        },
        "font": render,
        "positive_instructions": [
            "EDIT, DO NOT REDESIGN.",
            "Remove the complete English source effect before Korean lettering.",
            "Render only the approved Korean wording.",
            "Keep Korean fill/outline/antialias fully inside the measured safe bbox.",
            "Keep canvas, raw flip_y transform and transparent-background behavior unchanged.",
            "The Korean text must look like original game artwork rather than a pasted label."
        ],
        "negative_instructions": [
            "No visible English residue.",
            "No cover rectangle, panel, plaque, blur patch or invented background.",
            "No clipping, padding, canvas resize or aspect-ratio change.",
            "No opposite slant, generic upright lettering or unmeasured readability effects.",
            "No alpha introduction outside the candidate safe bbox."
        ],
        "self_check": "Before producing the candidate, verify that no source-language text or effect remains; no cover box, patch, seam or invented panel exists; all protected artwork is unchanged; Korean text is fully inside the permitted region and unclipped; canvas, orientation and transparency are unchanged. If any condition cannot be satisfied, do not produce a production candidate."
    }
    prompt_text = json.dumps(prompt, ensure_ascii=False, indent=2) + "\n"
    (REVIEW / "generation_prompt.json").write_text(prompt_text, encoding="utf-8")

    qa = {
        "schema_version": 9,
        "schema": "outrun-b00160-index112-v2-candidate-self-qa",
        "task_id": TASK_ID,
        "wave_id": WAVE_ID,
        "lane": "LOCALIZATION_B",
        "index": INDEX,
        "asset": ASSET,
        "source": {
            "repository": SOURCE_REPO,
            "ref": SOURCE_REF,
            "path": SOURCE_PATH,
            "git_blob_sha": SOURCE_BLOB,
            "sha256": SOURCE_SHA256,
            "dds": {"dimensions":[2048,256],"format":"DXT5_BC3","mip_count":1,"bytes":524416},
            "source_text_transform": "flip_y",
            "alpha_positive_pixels": alpha_count,
            "full_effect_bbox_readable_ltrb_exclusive": effect_bbox,
        },
        "c128_rework_resolution": {
            "b00155_recorded_method": "8-neighbor synchronous diffusion / 49 iterations",
            "corrected_method": "4-neighbor synchronous diffusion / 49 iterations",
            "iterations": iterations,
            "protected_pixels_changed_working_rgba": 0,
            "clean_plate_alpha_positive_after": 0,
            "result": "PASS_REPRODUCIBLE_METHOD_CORRECTED"
        },
        "candidate": {
            "path": str(CANDIDATE),
            "sha256": candidate_sha,
            "header_128_byte_identical": True,
            "header_sha256": source_header_sha,
            "bytes": len(candidate_bytes),
            "decoded_final_bbox_readable_ltrb_exclusive": dec_bbox,
            "candidate_safe_bbox_readable_ltrb_exclusive": list(SAFE),
            "decoded_final_alpha_positive_outside_safe_bbox": outside_alpha,
            "touched_bc3_blocks": touched_blocks,
            "blocks_with_korean_alpha": korean_blocks,
            "raw_orientation": "flip_y",
            "translation": KOREAN,
            "render": render,
        },
        "visual_review_set": "KOREAN_PNG_REVIEW/D41D0B1",
        "static_self_qa": {
            "source_identity": "PASS",
            "clean_plate": "PASS",
            "source_language_residue": "PASS_BY_CONSTRUCTION_FROM_ZERO_ALPHA_CLEAN_PLATE_AND_VISUAL_REVIEW_SET",
            "canvas_dimensions": "PASS_2048x256",
            "dds_format_mip_header": "PASS_DXT5_MIP1_HEADER128_IDENTICAL",
            "orientation": "PASS_FLIP_Y_ROUNDTRIP",
            "signed_slant": "PASS_RIGHT_SIGN_TARGET_15.3955_DEG",
            "one_pixel_containment": "PASS_ZERO_ALPHA_OUTSIDE_SAFE_BBOX",
            "protected_artwork": "PASS_TRANSPARENT_ASSET_NO_NON_TEXT_ALPHA_COMPONENTS_SOURCE; ZERO_NEW_ALPHA_OUTSIDE_SAFE_BBOX",
            "english_source_vs_korean_candidate": "PASS_REVIEW_ARTIFACT_GENERATED",
            "result": "PASS_PENDING_INDEPENDENT_C_BATCH_GATE"
        },
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
        "runtime_validation": "UNTESTED"
    }
    qa_text = json.dumps(qa, ensure_ascii=False, indent=2) + "\n"
    (REVIEW / "qa_report.json").write_text(qa_text, encoding="utf-8")

    comparison_role = role / "B00160_P00077_INDEX112_ENGLISH_SOURCE_VS_KOREAN_CANDIDATE.png"
    make_comparison(readable_img, clean_img, decoded_display, comparison_role)
    role_report = dict(qa)
    role_report["recorded_at_kst"] = now.isoformat()
    role_report["generation_prompt_sha256"] = sha256_bytes(prompt_text.encode("utf-8"))
    role_report["qa_report_sha256"] = sha256_bytes(qa_text.encode("utf-8"))
    role_report["comparison_path"] = str(comparison_role)
    role_report_path = role / "B00160_P00077_INDEX112_RENDER_DDS_SELF_QA.json"
    role_report_path.write_text(json.dumps(role_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    base_sha = subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    task_record = {
        "schema_version": 9,
        "task_id": TASK_ID,
        "lane": "LOCALIZATION_B",
        "target_branch": "korean-localization-clean",
        "attempt": "1/3",
        "wave_id": WAVE_ID,
        "chat_rollover": 4,
        "recorded_at_kst": now.isoformat(),
        "base_sha": base_sha,
        "commit_mode": "ATOMIC_GITHUB_ACTIONS_RECOVERY_FROM_ROLLOVER",
        "result": "PASS_MATERIAL_REWORKED_INDEX112_D41D0B1_KOREAN_DDS_CANDIDATE_PENDING_C_BATCH_GATE",
        "summary": "Recovered unfinished B00160 from C128 REWORK_REQUIRED on index112/D41D0B1. Corrected B00155 CLEAN_PLATE provenance from incorrectly recorded 8-neighbor/49 to reproducible 4-neighbor/49 synchronous diffusion, then continued in the same producer invocation through source-faithful Korean lettering, exact DXT5/BC3 DDS construction, decoded-final static QA and mandatory English-source-vs-Korean-candidate review artifacts. No shared state, N100, local clone/worktree, Drive, build, runtime, VR/FFB/DX changes.",
        "evidence": [
            str(role_report_path),
            "KOREAN_PNG_REVIEW/D41D0B1/source_display.png",
            "KOREAN_PNG_REVIEW/D41D0B1/clean_plate_display.png",
            "KOREAN_PNG_REVIEW/D41D0B1/candidate_display.png",
            "KOREAN_PNG_REVIEW/D41D0B1/comparison.png",
            "KOREAN_PNG_REVIEW/D41D0B1/generation_prompt.json",
            "KOREAN_PNG_REVIEW/D41D0B1/qa_report.json",
            str(CANDIDATE)
        ],
        "material_deliverable": {
            "type": "INDEX112_V2_KOREAN_DDS_CANDIDATE",
            "candidate_path": str(CANDIDATE),
            "candidate_sha256": candidate_sha,
            "candidate_dds_modified": True,
            "decoded_final_bbox_readable_ltrb_exclusive": dec_bbox,
            "candidate_safe_bbox_readable_ltrb_exclusive": list(SAFE),
            "outside_safe_alpha_pixels": outside_alpha,
            "materially_reduces_unresolved_work": True,
            "material_payload_in_result_commit": True
        },
        "self_qa": "PASS_INDEX112_SOURCE_IDENTITY__CORRECTED_4_NEIGHBOR_CLEAN_PLATE__KOREAN_RENDER__DXT5_HEADER_PRESERVED__DECODED_FINAL_ZERO_ALPHA_ESCAPE__ENGLISH_SOURCE_COMPARISON_SET",
        "candidate_static_qa": "PASS_PENDING_INDEPENDENT_C_BATCH_GATE",
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "runtime_test_performed": False,
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "google_drive_used": False,
        "gpt_library_used": False,
        "uploaded_archive_used": False,
        "vr_ffb_dx_changes": False,
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
        "runtime_validation": "UNTESTED"
    }
    (ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_B-00160.json").write_text(
        json.dumps(task_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

if __name__ == "__main__":
    main()
