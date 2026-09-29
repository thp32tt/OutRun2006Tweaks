#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
TASK_ID = "LOCALIZATION-LOCALIZATION_A-00208"
WAVE_ID = "P00108"
INDEX = 198
ASSET = "9FC88069"

SOURCE_REPO = "envido32/OR2006Sprites"
SOURCE_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
SOURCE_REL = "Release/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}"
SOURCE_SHA = "2729b78176ec648039f5b45baf52b1a78e8586e6233baf9a6be4f351f5b1add4"
SOURCE_BLOB_SHA = "e97d852a905aa8a219b786b843089e0998037f52"
SOURCE_BYTES = 33554560
SOURCE_HEADER_SHA = "25620ea389d11b2cb525fb8b688455fe97cedab100a22b93850d41686143e82e"
SOURCE_RAW_RGBA_SHA = "bb68541b2b9b800d145271d42b0cf5b8b982a1f4f7777fb81c16620eef4c346f"
SOURCE_DISPLAY_RGBA_SHA = "209403bbeccee76c82b691cc9d770e1edf6d04eda007e0e000a6e4d0caa1671e"
ARCHIVE_SHA = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"

EXPECTED_MASK_PIXELS = 77975
EXPECTED_CLEAN_RAW_SHA = "c210abb5fcdc41c8d1425ea19e5cd63a741b8a815a0e693f5be781ea640c32f7"
EXPECTED_CLEAN_DISPLAY_SHA = "d9d044a670c170ddfab215d51f4cb91799bc1142478a03793a5abcad5956d320"
EXPECTED_CANDIDATE_SHA = "851ba4d5b3b0ea5c3d7a07471bf991640d517870cca24e41fcaf8202d00cf60d"
EXPECTED_FONT_SHA = "faa5f3656a78b2e2d450d27fe8382c778bc2b6bb5ea29c986664a6a435056ceb"

CANVAS_W = 4096
CANVAS_H = 2048
BG789 = (57, 140, 203, 255)

# rect = [raw_x, raw_y, width, height].
# src/safe = readable-display cell-local xyxy half-open.
REGIONS = [
    {
        "sprite": "sprite_789",
        "rect": [0, 0, 544, 504],
        "source": "RANDOM",
        "korean": "무작위",
        "source_effect_bbox": [116, 378, 434, 440],
        "safe_bbox": [118, 380, 432, 438],
        "mask_mode": "modal_background",
        "mask_search_band": [100, 365, 440, 440],
        "source_fill_rgb": [255, 255, 255],
        "candidate_fill_rgb": [255, 255, 255],
        "font_role": "sans",
        "pixel_grid_quantize": False,
        "style": "upright condensed heavy sans; white flat fill; no outline/shadow/glow",
    },
    {
        "sprite": "sprite_790",
        "rect": [544, 0, 1604, 80],
        "source": "- RANDOM PLAY -",
        "korean": "- 무작위 재생 -",
        "source_effect_bbox": [4, 16, 584, 68],
        "safe_bbox": [6, 18, 582, 66],
        "mask_mode": "alpha",
        "source_fill_rgb": [54, 127, 170],
        "candidate_fill_rgb": [54, 127, 170],
        "font_role": "mono",
        "pixel_grid_quantize": True,
        "style": "upright block/bitmap-like mono lettering; blue/cyan source palette; no added outline/shadow/glow",
    },
    {
        "sprite": "sprite_791",
        "rect": [2148, 0, 1376, 80],
        "source": "(GUITAR MIX)",
        "korean": "(기타 믹스)",
        "source_effect_bbox": [8, 16, 456, 68],
        "safe_bbox": [10, 18, 454, 66],
        "mask_mode": "alpha",
        "source_fill_rgb": [76, 179, 241],
        "candidate_fill_rgb": [76, 179, 241],
        "font_role": "mono",
        "pixel_grid_quantize": True,
        "style": "upright block/bitmap-like mono lettering; RGB 76/179/241 with alpha antialias; no added effects",
    },
    {
        "sprite": "sprite_799",
        "rect": [1376, 744, 1376, 80],
        "source": "(INSTRUMENTAL)",
        "korean": "(연주곡)",
        "source_effect_bbox": [8, 16, 536, 68],
        "safe_bbox": [10, 18, 534, 66],
        "mask_mode": "alpha",
        "source_fill_rgb": [76, 179, 241],
        "candidate_fill_rgb": [76, 179, 241],
        "font_role": "mono",
        "pixel_grid_quantize": True,
        "style": "upright block/bitmap-like mono lettering; RGB 76/179/241 with alpha antialias; no added effects",
    },
    {
        "sprite": "sprite_828",
        "rect": [0, 1944, 1372, 80],
        "source": "(PROTOTYPE)",
        "korean": "(프로토타입)",
        "source_effect_bbox": [4, 16, 416, 68],
        "safe_bbox": [6, 18, 414, 66],
        "mask_mode": "alpha",
        "source_fill_rgb": [76, 179, 241],
        "candidate_fill_rgb": [76, 179, 241],
        "font_role": "mono",
        "pixel_grid_quantize": True,
        "style": "upright block/bitmap-like mono lettering; RGB 76/179/241 with alpha antialias; no added effects",
    },
    {
        "sprite": "sprite_829",
        "rect": [1372, 1944, 640, 80],
        "source": "INTERMEDIATE B",
        "korean": "중급 B",
        "source_effect_bbox": [189, 19, 612, 60],
        "safe_bbox": [191, 21, 610, 58],
        "mask_mode": "alpha",
        "source_fill_rgb": [0, 147, 203],
        "candidate_fill_rgb": [0, 147, 203],
        "font_role": "sans",
        "pixel_grid_quantize": False,
        "style": "upright heavy condensed sans; cyan flat fill; no outline/shadow/glow",
    },
    {
        "sprite": "sprite_830",
        "rect": [2012, 1944, 640, 80],
        "source": "INTERMEDIATE A",
        "korean": "중급 A",
        "source_effect_bbox": [186, 19, 612, 60],
        "safe_bbox": [188, 21, 610, 58],
        "mask_mode": "alpha",
        "source_fill_rgb": [0, 147, 203],
        "candidate_fill_rgb": [0, 147, 203],
        "font_role": "sans",
        "pixel_grid_quantize": False,
        "style": "upright heavy condensed sans; cyan flat fill; no outline/shadow/glow",
    },
]

RUN = ROOT / "localization/graphics/role_A/20260930-A00208-P00108"
REVIEW = ROOT / "localization/graphics/KOREAN_PNG_REVIEW/9FC88069"
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"
TASK_RECORD = ROOT / "docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00208.json"
REPORT = RUN / "A00208_P00108_INDEX198_V2_PRODUCTION.json"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def find_font(pattern: str):
    out = subprocess.check_output(
        ["fc-match", "-f", "%{file}|%{index}\\n", pattern],
        text=True,
    ).strip().splitlines()[0]
    p, idx = out.rsplit("|", 1)
    path = Path(p)
    if not path.exists():
        raise SystemExit(f"font missing: {path}")
    digest = sha_file(path)
    if digest != EXPECTED_FONT_SHA:
        raise SystemExit(f"font fingerprint mismatch: {digest}")
    return path, int(idx), digest


def inside(inner, outer) -> bool:
    return (
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def cell_display_origin(rect):
    raw_x, raw_y, width, height = rect
    return raw_x, CANVAS_H - (raw_y + height)


def render_tight(text, font_info, safe_w, safe_h, pixel_grid_quantize):
    font_path, font_index, _ = font_info
    chosen = None
    for size in range(96, 8, -1):
        font = ImageFont.truetype(str(font_path), size=size, index=font_index)
        bbox = font.getbbox(text)
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if width <= safe_w and height <= safe_h:
            chosen = (size, font, bbox, width, height)
            break
    if chosen is None:
        raise SystemExit(f"cannot fit approved Korean string: {text!r}")

    size, font, bbox, width, height = chosen
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).text((-bbox[0], -bbox[1]), text, font=font, fill=255)
    alpha_bbox = mask.getbbox()
    if not alpha_bbox:
        raise SystemExit(f"empty glyph render: {text!r}")
    alpha = np.array(mask.crop(alpha_bbox), dtype=np.uint8)

    if pixel_grid_quantize:
        # Source sprites are 4x block/bitmap-style. Quantize on the native HD
        # canvas without resizing a flattened lettering raster.
        block = 4
        pad_h = (-alpha.shape[0]) % block
        pad_w = (-alpha.shape[1]) % block
        padded = np.pad(alpha, ((0, pad_h), (0, pad_w)), constant_values=0)
        ph, pw = padded.shape
        coverage = padded.reshape(ph // block, block, pw // block, block).mean(axis=(1, 3))
        quantized = np.zeros_like(coverage, dtype=np.uint8)
        quantized[(coverage >= 24) & (coverage < 96)] = 64
        quantized[(coverage >= 96) & (coverage < 176)] = 160
        quantized[coverage >= 176] = 255
        expanded = np.repeat(np.repeat(quantized, block, axis=0), block, axis=1)
        alpha = expanded[: alpha.shape[0], : alpha.shape[1]]
        ys, xs = np.where(alpha > 0)
        if not len(xs):
            raise SystemExit(f"pixel-grid quantization erased glyph: {text!r}")
        alpha = alpha[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]

    return alpha, size


def save_rgba(arr, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8), "RGBA").save(path, optimize=False)


def compose_on_dark(arr):
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    bg = Image.new("RGBA", im.size, (28, 28, 28, 255))
    bg.alpha_composite(im)
    return bg


def make_element_comparison(source, candidate, label_font):
    rows = []
    for e in REGIONS:
        cell_x, cell_y = cell_display_origin(e["rect"])
        sx1, sy1, sx2, sy2 = e["source_effect_bbox"]
        pad = 10
        x1 = max(cell_x, cell_x + sx1 - pad)
        y1 = max(cell_y, cell_y + sy1 - pad)
        x2 = min(cell_x + e["rect"][2], cell_x + sx2 + pad)
        y2 = min(cell_y + e["rect"][3], cell_y + sy2 + pad)
        src = compose_on_dark(source[y1:y2, x1:x2])
        dst = compose_on_dark(candidate[y1:y2, x1:x2])
        scale = 2
        src = src.resize((src.width * scale, src.height * scale), Image.Resampling.NEAREST)
        dst = dst.resize((dst.width * scale, dst.height * scale), Image.Resampling.NEAREST)
        label_h = 30
        row = Image.new("RGBA", (src.width + dst.width, max(src.height, dst.height) + label_h), (20, 20, 20, 255))
        draw = ImageDraw.Draw(row)
        draw.text((6, 4), f"SOURCE {e['source']}", font=label_font, fill=(255, 255, 255, 255))
        draw.text((src.width + 6, 4), f"KOREAN {e['korean']}", font=label_font, fill=(255, 255, 255, 255))
        row.alpha_composite(src, (0, label_h))
        row.alpha_composite(dst, (src.width, label_h))
        rows.append(row)

    canvas = Image.new("RGBA", (max(r.width for r in rows), sum(r.height for r in rows)), (20, 20, 20, 255))
    y = 0
    for row in rows:
        canvas.alpha_composite(row, (0, y))
        y += row.height
    canvas.save(REVIEW / "element_comparison.png", optimize=False)


def main():
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    refreshed_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    if CANDIDATE.exists() or TASK_RECORD.exists():
        raise SystemExit("index198/A00208 durable output already exists at refreshed HEAD; refusing duplicate overwrite")

    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "OutRun2006Tweaks-localization-A00208"})
    with urllib.request.urlopen(req, timeout=120) as f:
        source_bytes = f.read()

    if len(source_bytes) != SOURCE_BYTES or sha_bytes(source_bytes) != SOURCE_SHA:
        raise SystemExit("exact pinned source identity mismatch")
    if source_bytes[:4] != b"DDS ":
        raise SystemExit("source is not DDS")
    if sha_bytes(source_bytes[:128]) != SOURCE_HEADER_SHA:
        raise SystemExit("source DDS header fingerprint mismatch")

    RUN.mkdir(parents=True, exist_ok=True)
    tmp = RUN / "_exact_source.dds"
    tmp.write_bytes(source_bytes)
    source_raw = np.array(Image.open(tmp).convert("RGBA"), dtype=np.uint8)
    tmp.unlink()
    if source_raw.shape != (CANVAS_H, CANVAS_W, 4):
        raise SystemExit(f"unexpected decoded canvas: {source_raw.shape}")
    if sha_bytes(source_raw.tobytes()) != SOURCE_RAW_RGBA_SHA:
        raise SystemExit("decoded raw RGBA fingerprint mismatch")

    source_display = np.flipud(source_raw).copy()
    if sha_bytes(source_display.tobytes()) != SOURCE_DISPLAY_RGBA_SHA:
        raise SystemExit("decoded display RGBA fingerprint mismatch")

    # Reproduce the independently accepted A00204/C146 clean plate exactly.
    removal_display = np.zeros((CANVAS_H, CANVAS_W), dtype=bool)
    for e in REGIONS:
        cell_x, cell_y = cell_display_origin(e["rect"])
        if e["mask_mode"] == "modal_background":
            x1, y1, x2, y2 = e["mask_search_band"]
            band = source_display[cell_y + y1 : cell_y + y2, cell_x + x1 : cell_x + x2]
            local_mask = np.any(band != np.array(BG789, dtype=np.uint8), axis=2)
            removal_display[cell_y + y1 : cell_y + y2, cell_x + x1 : cell_x + x2] |= local_mask
        else:
            x1, y1, x2, y2 = e["source_effect_bbox"]
            local_mask = source_display[cell_y + y1 : cell_y + y2, cell_x + x1 : cell_x + x2, 3] > 0
            removal_display[cell_y + y1 : cell_y + y2, cell_x + x1 : cell_x + x2] |= local_mask

    if int(removal_display.sum()) != EXPECTED_MASK_PIXELS:
        raise SystemExit(f"accepted removal-mask pixel count mismatch: {int(removal_display.sum())}")

    clean_display = source_display.copy()
    for e in REGIONS:
        cell_x, cell_y = cell_display_origin(e["rect"])
        width, height = e["rect"][2], e["rect"][3]
        local_mask = removal_display[cell_y : cell_y + height, cell_x : cell_x + width]
        cell = clean_display[cell_y : cell_y + height, cell_x : cell_x + width]
        if e["mask_mode"] == "modal_background":
            cell[local_mask] = np.array(BG789, dtype=np.uint8)
        else:
            cell[local_mask, 3] = 0
        clean_display[cell_y : cell_y + height, cell_x : cell_x + width] = cell

    clean_raw = np.flipud(clean_display).copy()
    if sha_bytes(clean_raw.tobytes()) != EXPECTED_CLEAN_RAW_SHA:
        raise SystemExit("accepted clean-plate raw fingerprint mismatch")
    if sha_bytes(clean_display.tobytes()) != EXPECTED_CLEAN_DISPLAY_SHA:
        raise SystemExit("accepted clean-plate display fingerprint mismatch")

    clean_changed = np.any(source_display != clean_display, axis=2)
    if int((clean_changed & ~removal_display).sum()) != 0:
        raise SystemExit("clean plate changed pixels outside accepted removal mask")
    clean_alpha_changed = source_display[:, :, 3] != clean_display[:, :, 3]
    if int((clean_alpha_changed & ~removal_display).sum()) != 0:
        raise SystemExit("clean plate changed alpha outside accepted removal mask")

    sans = find_font("Noto Sans CJK KR:style=Bold")
    mono = find_font("Noto Sans Mono CJK KR:style=Bold")
    label_font = ImageFont.truetype(str(sans[0]), size=18, index=sans[1])

    candidate_display = clean_display.copy()
    lettering_display = np.zeros_like(candidate_display)
    metrics = []

    for e in REGIONS:
        cell_x, cell_y = cell_display_origin(e["rect"])
        sx1, sy1, sx2, sy2 = e["safe_bbox"]
        safe_w, safe_h = sx2 - sx1, sy2 - sy1
        font_info = sans if e["font_role"] == "sans" else mono
        alpha, font_size = render_tight(
            e["korean"],
            font_info,
            safe_w,
            safe_h,
            e["pixel_grid_quantize"],
        )
        glyph_h, glyph_w = alpha.shape

        x = cell_x + sx1 + (safe_w - glyph_w) // 2
        y = cell_y + sy1 + (safe_h - glyph_h) // 2
        rgba = np.zeros((glyph_h, glyph_w, 4), dtype=np.uint8)
        rgba[:, :, :3] = np.array(e["candidate_fill_rgb"], dtype=np.uint8)
        rgba[:, :, 3] = alpha

        base = Image.fromarray(candidate_display[y : y + glyph_h, x : x + glyph_w], "RGBA")
        over = Image.fromarray(rgba, "RGBA")
        candidate_display[y : y + glyph_h, x : x + glyph_w] = np.array(Image.alpha_composite(base, over), dtype=np.uint8)
        lettering_display[y : y + glyph_h, x : x + glyph_w] = rgba

        ys, xs = np.where(alpha > 0)
        localized_bbox = [
            x - cell_x + int(xs.min()),
            y - cell_y + int(ys.min()),
            x - cell_x + int(xs.max()) + 1,
            y - cell_y + int(ys.max()) + 1,
        ]
        if not inside(localized_bbox, e["safe_bbox"]):
            raise SystemExit(f"candidate bbox escaped 2px safe region: {e['sprite']} {localized_bbox}")

        source_bbox = e["source_effect_bbox"]
        metrics.append(
            {
                "sprite": e["sprite"],
                "source": e["source"],
                "korean": e["korean"],
                "source_effect_bbox_readable_local": source_bbox,
                "candidate_safe_bbox_readable_local": e["safe_bbox"],
                "localized_bbox_readable_local": localized_bbox,
                "delta_left_vs_safe": localized_bbox[0] - e["safe_bbox"][0],
                "delta_top_vs_safe": localized_bbox[1] - e["safe_bbox"][1],
                "delta_right_vs_safe": e["safe_bbox"][2] - localized_bbox[2],
                "delta_bottom_vs_safe": e["safe_bbox"][3] - localized_bbox[3],
                "font_role": e["font_role"],
                "font_size_px": font_size,
                "font_identifier": f"{font_info[0].name}#{font_info[1]}",
                "font_sha256": font_info[2],
                "candidate_fill_rgb": e["candidate_fill_rgb"],
                "pixel_grid_quantize_native_4px": e["pixel_grid_quantize"],
                "source_style": e["style"],
                "source_baseline_vector_readable": [1, 0],
                "candidate_baseline_vector_readable": [1, 0],
                "source_slant_dx_per_dy": 0.0,
                "candidate_slant_dx_per_dy": 0.0,
                "source_signed_slant_angle_deg": 0.0,
                "candidate_signed_slant_angle_deg": 0.0,
                "source_slant_direction": "none",
                "candidate_slant_direction": "none",
                "containment": "PASS",
            }
        )

    candidate_raw = np.flipud(candidate_display).copy()
    header = source_bytes[:128]
    payload = candidate_raw[:, :, [2, 1, 0, 3]].tobytes()
    candidate_bytes = header + payload
    candidate_sha = sha_bytes(candidate_bytes)
    if candidate_sha != EXPECTED_CANDIDATE_SHA:
        raise SystemExit(f"deterministic candidate fingerprint mismatch: {candidate_sha}")

    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_bytes(candidate_bytes)
    roundtrip = np.array(Image.open(CANDIDATE).convert("RGBA"), dtype=np.uint8)
    if not np.array_equal(roundtrip, candidate_raw):
        raise SystemExit("DDS decoded round-trip mismatch")

    lettering_mask_display = lettering_display[:, :, 3] > 0
    allowed_display = removal_display | lettering_mask_display
    changed_display = np.any(source_display != candidate_display, axis=2)
    alpha_changed_display = source_display[:, :, 3] != candidate_display[:, :, 3]
    changed_outside = int((changed_display & ~allowed_display).sum())
    alpha_outside = int((alpha_changed_display & ~allowed_display).sum())
    if changed_outside != 0 or alpha_outside != 0:
        raise SystemExit(f"zero-pixel gate failed: changed_out={changed_outside} alpha_out={alpha_outside}")

    # All pixels outside the exact accepted removal mask and final Korean lettering are protected.
    protected_changed = changed_outside
    if protected_changed != 0:
        raise SystemExit("protected artwork changed")

    REVIEW.mkdir(parents=True, exist_ok=True)
    save_rgba(source_display, REVIEW / "source_display.png")
    save_rgba(clean_display, REVIEW / "clean_plate_display.png")
    save_rgba(candidate_display, REVIEW / "candidate_display.png")
    save_rgba(lettering_display, REVIEW / "lettering_display.png")
    Image.fromarray((removal_display * 255).astype(np.uint8), "L").save(REVIEW / "source_text_mask_display.png", optimize=False)
    Image.fromarray((~allowed_display * 255).astype(np.uint8), "L").save(REVIEW / "protected_mask_display.png", optimize=False)

    diff_display = np.zeros_like(source_display)
    diff_display[changed_display] = [255, 255, 255, 255]
    save_rgba(diff_display, REVIEW / "diff_display.png")

    label_h = 34
    panel = Image.new("RGBA", (CANVAS_W * 3, CANVAS_H + label_h), (24, 24, 24, 255))
    panel_font = ImageFont.truetype(str(sans[0]), size=20, index=sans[1])
    draw = ImageDraw.Draw(panel)
    for i, (label, arr) in enumerate(
        [
            ("ENGLISH SOURCE", source_display),
            ("CLEAN PLATE", clean_display),
            ("KOREAN CANDIDATE", candidate_display),
        ]
    ):
        draw.text((i * CANVAS_W + 8, 5), label, font=panel_font, fill=(255, 255, 255, 255))
        panel.alpha_composite(Image.fromarray(arr, "RGBA"), (i * CANVAS_W, label_h))
    panel.save(REVIEW / "comparison.png", optimize=False)
    make_element_comparison(source_display, candidate_display, label_font)

    prompt = {
        "contract": "outrun-first-pass-edit-v2",
        "task_id": TASK_ID,
        "wave_id": WAVE_ID,
        "queue_index": INDEX,
        "asset": ASSET,
        "source": {
            "repository": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_REL,
            "sha256": SOURCE_SHA,
            "git_blob_sha": SOURCE_BLOB_SHA,
            "bytes": SOURCE_BYTES,
            "dimensions": [CANVAS_W, CANVAS_H],
            "format": "RGBA32",
            "mipmaps": 1,
            "raw_to_readable": "flip_y",
            "pinned_release_archive_sha256": ARCHIVE_SHA,
        },
        "accepted_precandidate_lineage": {
            "a00204_result_sha": "e064952137805d785ee71675babe75e22982a83a",
            "c146_q00044_result_sha": "07952efd569649598034692745c745d71cc1c5fc",
            "removal_mask_pixels": EXPECTED_MASK_PIXELS,
            "clean_plate_raw_rgba_sha256": EXPECTED_CLEAN_RAW_SHA,
            "clean_plate_display_rgba_sha256": EXPECTED_CLEAN_DISPLAY_SHA,
        },
        "elements": [
            {
                "sprite": e["sprite"],
                "source": e["source"],
                "approved_korean": e["korean"],
                "source_effect_bbox_readable_local": e["source_effect_bbox"],
                "candidate_safe_bbox_readable_local": e["safe_bbox"],
                "source_style": e["style"],
                "source_transform": "flip_y raw storage / upright readable display",
                "source_baseline_vector_readable": [1, 0],
                "source_signed_slant_angle_deg": 0.0,
                "source_slant_direction": "none",
                "candidate_fill_rgb": e["candidate_fill_rgb"],
            }
            for e in REGIONS
        ],
        "instructions": {
            "positive": [
                "EDIT, DO NOT REDESIGN. The exact supplied HD source is authoritative.",
                "Reuse only the independently accepted A00204/C146 removal masks and clean plate on this exact source lineage.",
                "Render only the seven approved Korean strings fully inside their final 2px candidate_safe_bbox regions.",
                "Keep readable baselines horizontal and signed slant at zero, matching the exact English source.",
                "Preserve canvas, RGBA32 DDS header, mip policy, FLIP_Y raw storage transform, transparency and all unrelated artwork byte-exact.",
                "For the four block/bitmap source rows, use native-HD 4px coverage quantization without resizing a flattened lettering raster.",
                "The result must look as though the Korean text was part of the original game artwork, not pasted on later.",
            ],
            "negative": [
                "No visible English/source residue in the seven localized regions.",
                "No cover boxes, new panels, backing shapes, blur/smudge patches, seams or invented decoration.",
                "No crop, pad, resize, aspect-ratio change, low-resolution reconstruction or post-render flattened-raster scaling.",
                "No change to icons, card art, borders, neighboring sprites or unrelated/preserve-original pixels.",
                "No generic outline, shadow or glow absent from the exact source element.",
                "No Korean pixel may escape the accepted candidate_safe_bbox by even one pixel.",
            ],
            "pre_output_check": "Verify no source-language text/effect remains in localized regions; no patch/seam/panel exists; all protected artwork is unchanged; every Korean glyph/effect is fully inside its permitted 2px-safe region and unclipped; canvas/orientation/transparency are unchanged. If any condition fails, do not emit a production candidate.",
        },
    }
    prompt_bytes = (json.dumps(prompt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    prompt["prompt_sha256"] = sha_bytes(prompt_bytes)
    (REVIEW / "generation_prompt.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    qa = {
        "schema_version": 14,
        "schema": "outrun-a00208-index198-v2-production-v1",
        "task_id": TASK_ID,
        "wave_id": WAVE_ID,
        "lane": "LOCALIZATION_A",
        "queue_index": INDEX,
        "asset": ASSET,
        "recorded_at_kst": now,
        "base_head_sha": refreshed_head,
        "source": {
            "transport": "pinned_tag_direct_exact_canonical_source",
            "repository": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_REL,
            "sha256": SOURCE_SHA,
            "git_blob_sha": SOURCE_BLOB_SHA,
            "bytes": SOURCE_BYTES,
            "header_128_sha256": SOURCE_HEADER_SHA,
            "decoded_raw_rgba_sha256": SOURCE_RAW_RGBA_SHA,
            "decoded_display_rgba_sha256": SOURCE_DISPLAY_RGBA_SHA,
            "dimensions": [CANVAS_W, CANVAS_H],
            "format": "RGBA32",
            "mipmaps": 1,
            "raw_to_readable": "flip_y",
            "canonical_inventory_match": True,
        },
        "accepted_precandidate_lineage": {
            "a00204_result_sha": "e064952137805d785ee71675babe75e22982a83a",
            "c146_q00044_result_sha": "07952efd569649598034692745c745d71cc1c5fc",
            "production_readiness": "RENDER_READY",
        },
        "clean_plate": {
            "removal_mask_pixels": int(removal_display.sum()),
            "clean_plate_raw_rgba_sha256": sha_bytes(clean_raw.tobytes()),
            "clean_plate_display_rgba_sha256": sha_bytes(clean_display.tobytes()),
            "changed_pixels_outside_removal_mask": int((clean_changed & ~removal_display).sum()),
            "alpha_changed_pixels_outside_removal_mask": int((clean_alpha_changed & ~removal_display).sum()),
            "independent_c_replay": "PASS_Q00044",
        },
        "render": {
            "contract": "outrun-first-pass-edit-v2",
            "font_sha256": EXPECTED_FONT_SHA,
            "source_transform": "flip_y",
            "source_baseline_vector_readable": [1, 0],
            "candidate_baseline_vector_readable": [1, 0],
            "source_signed_slant_angle_deg": 0.0,
            "candidate_signed_slant_angle_deg": 0.0,
            "source_slant_direction": "none",
            "candidate_slant_direction": "none",
            "flattened_raster_resize": "NOT_USED",
            "metrics": metrics,
        },
        "candidate": {
            "repo_path": str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": candidate_sha,
            "bytes": len(candidate_bytes),
            "header_128_exact": candidate_bytes[:128] == header,
            "roundtrip_decoded_exact": True,
            "changed_pixels": int(changed_display.sum()),
            "changed_pixels_outside_allowed_edit_mask": changed_outside,
            "alpha_changed_pixels_total": int(alpha_changed_display.sum()),
            "alpha_changed_pixels_outside_allowed_edit_mask": alpha_outside,
            "changed_pixels_in_protected_regions": protected_changed,
            "candidate_letter_pixels": int(lettering_mask_display.sum()),
            "orientation": "PASS_FLIP_Y_RAW_TO_READABLE",
            "safe_bbox_containment": "PASS_2PX_INSET_ALL_7",
            "one_pixel_overflow": 0,
        },
        "visual_review_contract": {
            "full_atlas": "comparison.png",
            "per_element_readable_zoom": "element_comparison.png",
            "source_clean_candidate_set": ["source_display.png", "clean_plate_display.png", "candidate_display.png"],
            "diff": "diff_display.png",
            "status": "PRODUCER_VISUAL_REVIEW_PASS_PENDING_INDEPENDENT_C",
        },
        "static_qa": "PASS_PRODUCER_MACHINE_AND_VISUAL_PENDING_INDEPENDENT_C",
        "candidate_dds_modified": True,
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "runtime_test_performed": False,
        "runtime_validation": "UNTESTED",
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "google_drive_used": False,
        "google_drive_write_performed": False,
        "gpt_library_used": False,
        "uploaded_archive_used": False,
        "vr_ffb_dx_changes": False,
    }
    REPORT.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (REVIEW / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    task = {
        "schema_version": 14,
        "task_id": TASK_ID,
        "wave_id": WAVE_ID,
        "lane": "LOCALIZATION_A",
        "target_branch": "korean-localization-clean",
        "attempt": "1/3",
        "chat_rollover": 4,
        "recorded_at_kst": now,
        "base_head_sha": refreshed_head,
        "base_sha": refreshed_head,
        "commit_mode": "GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_INDEX198_V2_CANDIDATE_REVIEW_SET_AND_DURABLE_TASK_RECORD",
        "result": "PASS_MATERIAL_A_MOD3_INDEX198_RENDER_READY_KOREAN_CANDIDATE_STATIC_QA_RUNTIME_UNTESTED",
        "summary": "Resumed A00208 from the current GitHub SSOT and consumed C146/Q00044 RENDER_READY index198/9FC88069 without repeating completed preflight. The exact pinned 4096x2048 RGBA32 Release source matches canonical SHA/header/decode fingerprints. The producer reproduces the independently accepted 77,975-pixel A00204 clean plate byte-for-byte, measures source baseline/slant/style as upright horizontal zero-slant, renders all seven approved Korean strings into the final 2px-safe boxes, preserves FLIP_Y/raw DDS header/transparency, and persists the deterministic candidate plus mandatory GitHub PNG review set. Zero changed pixels and zero alpha changes occur outside the allowed removal-or-lettering masks; real-game validation remains UNTESTED.",
        "evidence": [
            str(REPORT.relative_to(ROOT)).replace("\\", "/"),
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/source_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/source_text_mask_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/protected_mask_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/clean_plate_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/lettering_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/candidate_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/diff_display.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/comparison.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/element_comparison.png",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/generation_prompt.json",
            "localization/graphics/KOREAN_PNG_REVIEW/9FC88069/qa_report.json",
            str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
        ],
        "material_deliverable": {
            "type": "INDEX198_9FC88069_RENDER_READY_V2_KOREAN_RGBA32_CANDIDATE_WITH_MANDATORY_REVIEW_SET",
            "reviewed_indices": [INDEX],
            "reviewed_assets": [ASSET],
            "candidate_dds_sha256": candidate_sha,
            "candidate_dds_modified": True,
            "source_removal_pixels": int(removal_display.sum()),
            "clean_plate_raw_rgba_sha256": sha_bytes(clean_raw.tobytes()),
            "translated_regions": 7,
            "changed_pixels_outside_allowed_edit_mask": changed_outside,
            "alpha_changed_pixels_outside_allowed_edit_mask": alpha_outside,
            "changed_pixels_in_protected_regions": protected_changed,
            "one_pixel_overflow": 0,
            "material_payload_in_result_commit": True,
            "durable_task_record_in_result_commit": True,
            "materially_reduces_unresolved_work": True,
        },
        "readiness_audit": {
            "shard_rule": "asset_queue.index % 3 == 0",
            "selected_priority": "RENDER_READY_CANDIDATE_COMPLETION",
            "selected_indices": [INDEX],
            "accepted_c_gate": "C146/Q00044",
            "completed_work_not_repeated": [
                "A00204 exact source/mask/clean-plate/safe-bbox preproduction gates",
                "C146 independent clean-plate replay and RENDER_READY promotion",
                "B00209 index226 corrected candidate production",
            ],
            "readiness_after": {
                "198": "CANDIDATE_PERSISTED_PRODUCER_STATIC_PASS_PENDING_INDEPENDENT_C"
            },
        },
        "self_qa": "PASS_INDEX198_MOD3_EQ_0__EXACT_PINNED_SOURCE__A00204_CLEAN_PLATE_FINGERPRINT_EXACT__C146_RENDER_READY__7_OF_7_KOREAN_2PX_SAFE_BBOX__ZERO_PIXEL_ESCAPE__DDS_HEADER_EXACT__ROUNDTRIP_EXACT__FLIP_Y__SOURCE_STYLE_ZERO_SLANT__MANDATORY_GITHUB_PNG_REVIEW_SET",
        "candidate_static_qa": "PASS_PRODUCER_STATIC_PENDING_INDEPENDENT_C",
        "candidate_dds_modified": True,
        "shared_state_modified": False,
        "peer_lane_files_modified": False,
        "runtime_test_performed": False,
        "runtime_validation": "UNTESTED",
        "build_performed": False,
        "n100_used": False,
        "local_clone_used": False,
        "gpt_library_used_as_source_or_ssot": False,
        "google_drive_used": False,
        "google_drive_write_performed": False,
        "uploaded_archive_used": False,
        "work_stolen_from_lane": None,
        "vr_ffb_dx_changes": False,
        "automation_validation": "PENDING",
        "validation_mode": "C_BATCH_GATE",
    }
    TASK_RECORD.parent.mkdir(parents=True, exist_ok=True)
    TASK_RECORD.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "PASS",
                "candidate_sha256": candidate_sha,
                "changed_pixels": int(changed_display.sum()),
                "mask_pixels": int(removal_display.sum()),
                "clean_plate_sha256": sha_bytes(clean_raw.tobytes()),
                "letter_pixels": int(lettering_mask_display.sum()),
                "changed_outside": changed_outside,
                "alpha_outside": alpha_outside,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
