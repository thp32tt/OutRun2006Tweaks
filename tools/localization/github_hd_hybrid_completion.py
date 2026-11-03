#!/usr/bin/env python3
"""Complete TEST_ONLY HD Korean DDS package on GitHub CPU.

Priority:
1) exact imported A/B ImageGen PNG when it can safely replace a deterministic
   fallback glyph inside the same approved ROI;
2) deterministic reviewed Korean fallback for missing/unusable A/B candidates.

The fallback exists only to keep all 954 reviewed ROI represented while A/B
imports converge. It never becomes RELEASE approval. It preserves pixels
outside approved ROI, uses the SHA-pinned 104 HD DDS as the source basis, and
emits uncompressed RGBA32 mip1 DDS for deterministic compatibility testing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import struct
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

CROSS = "localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
PLAN = "localization/automation_inputs/hd_original_png_source_plan.json"
SOURCE_ROOT = "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
CANDIDATE_ROOT = "localization/automation_inputs/candidate_outputs"
ZIPNAME = "OUTRUN_HD_KOREAN_HYBRID_TEST_ONLY.zip"
ACTIVE_ROI = 954
ACTIVE_DDS = 104
MAX_CANDIDATE = 8 * 1024 * 1024
FONTS = (
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_target(value: str) -> bool:
    p = PurePosixPath(str(value))
    return (
        isinstance(value, str)
        and value.startswith("textures/load/")
        and value.endswith(".dds")
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in value
        and ":" not in value
    )


def font_path() -> str:
    for item in FONTS:
        if Path(item).is_file():
            return item
    raise RuntimeError("KOREAN_FONT_MISSING")


def korean_lines(text: str) -> list[str]:
    if " / " in text:
        return [x.strip() for x in text.split(" / ")]
    return text.splitlines() or [text]


def make_glyph(text: str, width: int, height: int, fontfile: str, reference: np.ndarray | None = None) -> Image.Image:
    if width < 4 or height < 4:
        raise ValueError("GLYPH_BOX_TOO_SMALL")
    color = (246, 249, 255, 255)
    if reference is not None and reference.size:
        pixels = reference.reshape(-1, 4)
        solid = pixels[:, 3] >= 192
        if int(np.count_nonzero(solid)):
            rgb = pixels[solid, :3].astype(np.int32)
            gold = (
                (rgb[:, 0] >= 145)
                & (rgb[:, 1] >= 95)
                & (rgb[:, 2] <= 165)
                & (rgb[:, 0] >= rgb[:, 2] * 1.35)
            )
            if np.count_nonzero(gold) / max(1, len(rgb)) >= 0.035:
                color = (255, 210, 40, 255)

    lines = korean_lines(text)
    margin = max(2, min(width, height) // 18)
    longest = max(1, max(map(len, lines)))
    maxfont = max(6, int(min(height / max(1, len(lines)) * 0.88, width / longest * 1.7)))
    best = None
    for size in range(maxfont, 4, -1):
        face = ImageFont.truetype(fontfile, size=size)
        stroke = max(1, round(size / 18))
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        widths, heights = [], []
        for line in lines:
            box = d.textbbox((0, 0), line, font=face, stroke_width=stroke)
            widths.append(box[2] - box[0])
            heights.append(box[3] - box[1])
        line_h = max(heights)
        spacing = max(1, size // 8)
        if max(widths) <= width - 2 * margin and len(lines) * line_h + max(0, len(lines) - 1) * spacing <= height - 2 * margin:
            best = (face, stroke, line_h, widths, spacing)
            break
    if best is None:
        raise ValueError("TRANSLATION_CANNOT_FIT")

    face, stroke, line_h, widths, spacing = best
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    painter = ImageDraw.Draw(out)
    total = len(lines) * line_h + (len(lines) - 1) * spacing
    for n, line in enumerate(lines):
        cx = width // 2
        cy = (height - total) // 2 + n * (line_h + spacing) + line_h // 2
        painter.text(
            (cx, cy),
            line,
            font=face,
            anchor="mm",
            fill=color,
            stroke_width=stroke,
            stroke_fill=(13, 32, 74, 245),
        )
    if not out.getchannel("A").getbbox():
        raise ValueError("RENDER_EMPTY")
    return out


def load_plan(path: Path) -> dict[str, dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("entries")
    if not isinstance(rows, list):
        raise ValueError("SOURCE_PLAN_ENTRIES_MISSING")
    result = {}
    for row in rows:
        target = row.get("target")
        expected = row.get("original_dds_sha256")
        orientation = row.get("orientation")
        if not safe_target(target) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("SOURCE_PLAN_INVALID_ENTRY")
        if orientation not in ("NORMAL", "FLIPY"):
            raise ValueError("SOURCE_PLAN_ORIENTATION_UNKNOWN:" + target)
        if target in result and result[target]["sha256"] != expected:
            raise ValueError("SOURCE_PLAN_SHA_CONFLICT:" + target)
        result[target] = {"sha256": expected, "orientation": orientation}
    if len(result) != ACTIVE_DDS:
        raise ValueError(f"SOURCE_PLAN_TARGET_COUNT_CHANGED:{len(result)}")
    return result


def candidate_relative(row: dict) -> str:
    match = re.fullmatch(
        r"/home/chatgpt-runner2/work/image-src/text_roi_batches/candidate_outputs/([AB])/([A-Za-z0-9_-]+\.png)",
        row["candidate_paths"],
    )
    if not match or match.group(1) != row["roles"]:
        raise ValueError("CANDIDATE_PATH_UNSAFE:" + row["roi_id"])
    basename = match.group(2)
    base_id = row["roi_id"].removesuffix("_RB_B")
    if basename not in (base_id + "_k.png", base_id + "_source_k.png"):
        raise ValueError("CANDIDATE_FILENAME_MISMATCH:" + row["roi_id"])
    return f"{CANDIDATE_ROOT}/{match.group(1)}/{basename}"


def load_crosswalk(path: Path, plan: dict[str, dict]) -> dict[str, list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != ACTIVE_ROI or len({x["roi_id"] for x in rows}) != ACTIVE_ROI:
        raise ValueError("ACTIVE_CROSSWALK_NOT_954_UNIQUE")
    grouped = defaultdict(list)
    for row in rows:
        target = row["source_dds_path"]
        if target not in plan or not safe_target(target):
            raise ValueError("CROSSWALK_TARGET_NOT_IN_PLAN:" + row["roi_id"])
        if row["source_dds_sha256"] != plan[target]["sha256"]:
            raise ValueError("CROSSWALK_SOURCE_SHA_CONFLICT:" + row["roi_id"])
        if row["candidate_status"] != "CANDIDATE_ONLY_QA_UNVERIFIED" or row["candidate_count"] != "1":
            raise ValueError("CROSSWALK_CANDIDATE_STATE_CHANGED:" + row["roi_id"])
        if row["roles"] not in ("A", "B"):
            raise ValueError("CROSSWALK_ROLE_INVALID:" + row["roi_id"])
        box = json.loads(row["bbox_xyxy"])
        if len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError("CROSSWALK_BBOX_INVALID:" + row["roi_id"])
        row = dict(row)
        row["_bbox"] = box
        row["_candidate_rel"] = candidate_relative(row)
        grouped[target].append(row)
    if len(grouped) != ACTIVE_DDS:
        raise ValueError(f"CROSSWALK_DDS_COUNT_CHANGED:{len(grouped)}")
    return grouped


def readable_from_dds(raw: bytes, orientation: str) -> Image.Image:
    if len(raw) < 128 or raw[:4] != b"DDS ":
        raise ValueError("SOURCE_DDS_HEADER_INVALID")
    with Image.open(io.BytesIO(raw)) as im:
        if im.format != "DDS":
            raise ValueError("SOURCE_NOT_DDS")
        im.load()
        native = im.convert("RGBA")
    return native if orientation == "NORMAL" else ImageOps.flip(native)


def rect_intersection(a, b) -> int:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


def intersects(a, b) -> bool:
    return rect_intersection(a, b) > 0


def iou(a, b) -> float:
    inter = rect_intersection(a, b)
    if not inter:
        return 0.0
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1, aa + bb - inter)


def subtract_rectangles(base, blocks):
    free = [tuple(base)]
    for block in blocks:
        nxt = []
        bx0, by0, bx1, by1 = block
        for part in free:
            x0, y0, x1, y1 = part
            ix0, iy0 = max(x0, bx0), max(y0, by0)
            ix1, iy1 = min(x1, bx1), min(y1, by1)
            if ix0 >= ix1 or iy0 >= iy1:
                nxt.append(part)
                continue
            if y0 < iy0:
                nxt.append((x0, y0, x1, iy0))
            if iy1 < y1:
                nxt.append((x0, iy1, x1, y1))
            if x0 < ix0:
                nxt.append((x0, iy0, ix0, iy1))
            if ix1 < x1:
                nxt.append((ix1, iy0, x1, iy1))
        free = [r for r in nxt if r[0] < r[2] and r[1] < r[3]]
        if not free:
            break
    return free


def tight_ink_box(placement, glyph: Image.Image, padding=3):
    x0, y0, x1, y1 = placement
    box = glyph.getchannel("A").getbbox()
    if not box:
        raise ValueError("RENDER_EMPTY")
    return (
        max(x0, x0 + box[0] - padding),
        max(y0, y0 + box[1] - padding),
        min(x1, x0 + box[2] + padding),
        min(y1, y0 + box[3] + padding),
    )


def fallback_compose(source: Image.Image, rows: list[dict], fontfile: str):
    before = np.asarray(source)
    out = source.copy()
    accepted = []
    held = []
    used_source_boxes = []

    ordered = sorted(
        rows,
        key=lambda r: (
            (r["_bbox"][2] - r["_bbox"][0]) * (r["_bbox"][3] - r["_bbox"][1]),
            r["_bbox"][1],
            r["_bbox"][0],
            r["roi_id"],
        ),
    )
    for row in ordered:
        box = tuple(row["_bbox"])
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
            held.append({"roi_id": row["roi_id"], "reason": "OUT_OF_BOUNDS"})
            continue
        if any(intersects(box, prior) for prior in used_source_boxes):
            held.append({"roi_id": row["roi_id"], "reason": "OVERLAPPING_ROI"})
            continue
        ref = before[y0:y1, x0:x1]
        try:
            glyph = make_glyph(row["korean"], x1 - x0, y1 - y0, fontfile, ref)
        except (ValueError, OSError, OverflowError) as exc:
            held.append({"roi_id": row["roi_id"], "reason": str(exc)[:100]})
            continue
        out.paste((0, 0, 0, 0), box)
        out.alpha_composite(glyph, (x0, y0))
        ink = tight_ink_box(box, glyph)
        used_source_boxes.append(box)
        accepted.append(
            {
                "roi_id": row["roi_id"],
                "english": row["english"],
                "korean": row["korean"],
                "bbox": list(box),
                "placement_bbox": list(box),
                "ink_box": list(ink),
                "resolution": "FALLBACK_PRIMARY",
                "_row": row,
            }
        )

    protected = [tuple(x["ink_box"]) for x in accepted]
    shield = np.zeros((source.height, source.width), dtype=bool)
    for a, b, c, d in protected:
        shield[b:d, a:c] = True

    by_id = {x["roi_id"]: x for x in rows}
    still = []
    represented = []
    for failure in held:
        if failure["reason"] != "OVERLAPPING_ROI":
            still.append(failure)
            continue
        row = by_id[failure["roi_id"]]
        box = tuple(row["_bbox"])
        duplicate = next(
            (
                prior
                for prior in accepted
                if prior["korean"] == row["korean"] and iou(box, tuple(prior["bbox"])) >= 0.8
            ),
            None,
        )
        if duplicate is not None:
            represented.append(
                {
                    "roi_id": row["roi_id"],
                    "matched_roi_id": duplicate["roi_id"],
                    "reason": "DUPLICATE_TRANSLATION_REPRESENTED",
                }
            )
            continue

        free = subtract_rectangles(box, protected)
        free.sort(
            key=lambda q: (
                (q[2] - q[0]) * (q[3] - q[1]),
                min(q[2] - q[0], q[3] - q[1]),
                -q[1],
                -q[0],
            ),
            reverse=True,
        )
        selected = None
        source_area = (box[2] - box[0]) * (box[3] - box[1])
        for rect in free[:32]:
            x0, y0, x1, y1 = rect
            if x1 - x0 > 1600:
                dx = (x1 - x0 - 1600) // 2
                x0 += dx
                x1 = x0 + 1600
            if y1 - y0 > 600:
                dy = (y1 - y0 - 600) // 2
                y0 += dy
                y1 = y0 + 600
            if min(x1 - x0, y1 - y0) < 14:
                continue
            if (x1 - x0) * (y1 - y0) < source_area * 0.012:
                continue
            try:
                glyph = make_glyph(
                    row["korean"],
                    x1 - x0,
                    y1 - y0,
                    fontfile,
                    before[y0:y1, x0:x1],
                )
            except (ValueError, OSError, OverflowError):
                continue
            local = glyph.getchannel("A").getbbox()
            if not local:
                continue
            ix0, iy0, ix1, iy1 = x0 + local[0], y0 + local[1], x0 + local[2], y0 + local[3]
            if np.any(shield[iy0:iy1, ix0:ix1]):
                continue
            selected = (x0, y0, x1, y1, glyph)
            break

        if selected is None:
            still.append({"roi_id": row["roi_id"], "reason": "INK_AWARE_NO_READABLE_SPACE"})
            continue

        x0, y0, x1, y1, glyph = selected
        placement = (x0, y0, x1, y1)
        out.paste((0, 0, 0, 0), placement)
        out.alpha_composite(glyph, (x0, y0))
        ink = tight_ink_box(placement, glyph)
        protected.append(tuple(ink))
        a, b, c, d = ink
        shield[b:d, a:c] = True
        accepted.append(
            {
                "roi_id": row["roi_id"],
                "english": row["english"],
                "korean": row["korean"],
                "bbox": list(box),
                "placement_bbox": list(placement),
                "ink_box": list(ink),
                "resolution": "FALLBACK_INK_RELOCATE",
                "original_english_may_remain": True,
                "_row": row,
            }
        )

    # Strictly prove no change escaped the union of approved source ROI.
    final = np.asarray(out)
    allowed = np.zeros((source.height, source.width), dtype=bool)
    for item in accepted:
        a, b, c, d = item["bbox"]
        allowed[b:d, a:c] = True
    change = np.any(before != final, axis=2)
    outside = int(np.count_nonzero(change & ~allowed))
    if outside:
        raise AssertionError("FALLBACK_CHANGED_OUTSIDE_APPROVED_ROI")
    return out, accepted, still, represented, int(np.count_nonzero(change))


def prepare_candidate(raw: bytes) -> Image.Image:
    if len(raw) > MAX_CANDIDATE:
        raise ValueError("AB_CANDIDATE_TOO_LARGE")
    with Image.open(io.BytesIO(raw)) as im:
        if im.format != "PNG" or not 8 <= im.width <= 4096 or not 8 <= im.height <= 4096:
            raise ValueError("AB_CANDIDATE_NOT_PNG")
        im.load()
        image = im.convert("RGBA")
    alpha = image.getchannel("A")
    raw_box = alpha.getbbox()
    if not raw_box:
        raise ValueError("AB_CANDIDATE_INVISIBLE")
    if raw_box[0] == 0 or raw_box[1] == 0 or raw_box[2] == image.width or raw_box[3] == image.height:
        raise ValueError("AB_CANDIDATE_BORDER_TOUCH")
    solid = alpha.point(lambda v: 255 if v >= 16 else 0).getbbox()
    if not solid:
        raise ValueError("AB_CANDIDATE_ALPHA16_EMPTY")
    pad = 4
    crop = (
        max(0, solid[0] - pad),
        max(0, solid[1] - pad),
        min(image.width, solid[2] + pad),
        min(image.height, solid[3] + pad),
    )
    return image.crop(crop)


def apply_ab_candidates(root: Path, fallback: Image.Image, accepted: list[dict]):
    out = fallback.copy()
    applied = []
    holds = []
    for item in accepted:
        row = item["_row"]
        path = root / row["_candidate_rel"]
        if not path.is_file() or path.is_symlink():
            continue
        try:
            raw = path.read_bytes()
            art = prepare_candidate(raw)
            x0, y0, x1, y1 = item["ink_box"]
            tw, th = x1 - x0, y1 - y0
            if tw < 2 or th < 2:
                raise ValueError("AB_TARGET_INK_BOX_TOO_SMALL")
            factor = min(tw / art.width, th / art.height)
            nw = max(1, min(tw, int(art.width * factor)))
            nh = max(1, min(th, int(art.height * factor)))
            rendered = art.resize((nw, nh), Image.Resampling.LANCZOS)
            px = x0 + (tw - nw) // 2
            py = y0 + (th - nh) // 2
            out.paste((0, 0, 0, 0), (x0, y0, x1, y1))
            out.alpha_composite(rendered, (px, py))
            applied.append(
                {
                    "roi_id": item["roi_id"],
                    "candidate": row["_candidate_rel"],
                    "candidate_sha256": sha(raw),
                    "fallback_resolution": item["resolution"],
                    "replacement_box": [x0, y0, x1, y1],
                    "new_ink": [px, py, px + nw, py + nh],
                }
            )
        except (OSError, ValueError, OverflowError, UnidentifiedImageError) as exc:
            holds.append(
                {
                    "roi_id": item["roi_id"],
                    "candidate": row["_candidate_rel"],
                    "reason": str(exc)[:120],
                }
            )
    return out, applied, holds


def encode_rgba_dds(readable: Image.Image, orientation: str) -> bytes:
    native = readable if orientation == "NORMAL" else ImageOps.flip(readable)
    w, h = native.size
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000)
    struct.pack_into("<I", header, 12, h)
    struct.pack_into("<I", header, 16, w)
    struct.pack_into("<I", header, 20, w * 4)
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x41)
    struct.pack_into("<I", header, 88, 32)
    struct.pack_into("<IIII", header, 92, 255, 65280, 16711680, 4278190080)
    struct.pack_into("<I", header, 108, 0x1000)
    raw = bytes(header) + native.tobytes("raw", "RGBA")
    with Image.open(io.BytesIO(raw)) as check:
        check.load()
        if check.size != native.size or ImageChops.difference(check.convert("RGBA"), native).getbbox():
            raise ValueError("OUTPUT_DDS_ROUNDTRIP_MISMATCH")
    return raw


def zput(zf: zipfile.ZipFile, name: str, raw: bytes):
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=3)


def build(repo_root: str, output: str):
    root = Path(repo_root).resolve()
    out = Path(output).resolve()
    if out.is_relative_to(root):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    out.mkdir(parents=True, exist_ok=True)

    plan = load_plan(root / PLAN)
    groups = load_crosswalk(root / CROSS, plan)
    fontfile = font_path()

    archive = {}
    atlas_reports = []
    source_verified = 0
    fallback_painted = 0
    duplicates = 0
    fallback_holds = []
    ab_imported = 0
    ab_applied = 0
    ab_holds = []

    for target, rows in sorted(groups.items()):
        source = root / SOURCE_ROOT / target
        if not source.is_file() or source.is_symlink():
            fallback_holds.append({"target": target, "reason": "SOURCE_DDS_NOT_SYNCHRONIZED"})
            continue
        raw = source.read_bytes()
        actual = sha(raw)
        if actual != plan[target]["sha256"]:
            fallback_holds.append(
                {
                    "target": target,
                    "reason": "SOURCE_DDS_SHA_MISMATCH",
                    "actual": actual,
                    "expected": plan[target]["sha256"],
                }
            )
            continue
        source_verified += 1
        readable = readable_from_dds(raw, plan[target]["orientation"])
        fallback, accepted, holds, represented, changed = fallback_compose(readable, rows, fontfile)
        imported_here = sum((root / row["_candidate_rel"]).is_file() for row in rows)
        ab_imported += imported_here
        hybrid, applied, local_ab_holds = apply_ab_candidates(root, fallback, accepted)
        ab_applied += len(applied)
        ab_holds.extend({"target": target, **x} for x in local_ab_holds)
        fallback_painted += len(accepted)
        duplicates += len(represented)
        fallback_holds.extend({"target": target, **x} for x in holds)

        # Hybrid edits are a subset of fallback ink, therefore still inside approved ROI.
        source_np = np.asarray(readable)
        hybrid_np = np.asarray(hybrid)
        allowed = np.zeros((readable.height, readable.width), dtype=bool)
        for item in accepted:
            a, b, c, d = item["bbox"]
            allowed[b:d, a:c] = True
        outside = int(np.count_nonzero(np.any(source_np != hybrid_np, axis=2) & ~allowed))
        if outside:
            raise AssertionError("HYBRID_CHANGED_OUTSIDE_APPROVED_ROI")

        output_dds = encode_rgba_dds(hybrid, plan[target]["orientation"])
        archive[target] = output_dds
        ident = PurePosixPath(target).stem.split("_")[0]
        thumb = hybrid.copy()
        thumb.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        thumb.save(out / f"PREVIEW_{ident}_{len(atlas_reports):03d}.png", format="PNG")

        clean_accepted = [{k: v for k, v in x.items() if k != "_row"} for x in accepted]
        atlas_reports.append(
            {
                "target": target,
                "source_sha256": actual,
                "orientation": plan[target]["orientation"],
                "roi_count": len(rows),
                "fallback_painted": len(accepted),
                "duplicates_represented": len(represented),
                "fallback_holds": holds,
                "ab_candidates_imported": imported_here,
                "ab_candidates_applied": len(applied),
                "ab_candidate_holds": local_ab_holds,
                "changed_pixels_from_source": changed,
                "output_dds_sha256": sha(output_dds),
                "accepted": clean_accepted,
                "represented": represented,
                "ab_applied": applied,
            }
        )

    coverage = fallback_painted + duplicates
    report = {
        "schema": "outrun.github-hd-korean-hybrid-completion.v1",
        "source_basis": "SHA-pinned OR2-HD-GUI-v0.25.10a DDS",
        "priority": "A/B original ImageGen PNG first; deterministic fallback only for coverage",
        "active_roi_total": ACTIVE_ROI,
        "active_dds_total": ACTIVE_DDS,
        "source_dds_verified": source_verified,
        "output_dds_count": len(archive),
        "fallback_painted_count": fallback_painted,
        "duplicate_translation_represented_count": duplicates,
        "translation_coverage_accounted": coverage,
        "translation_coverage_complete": coverage == ACTIVE_ROI,
        "ab_candidate_imported_count": ab_imported,
        "ab_candidate_applied_count": ab_applied,
        "ab_candidate_pending_import": ACTIVE_ROI - ab_imported,
        "ab_candidate_hold_count": len(ab_holds),
        "fallback_hold_count": len(fallback_holds),
        "fallback_holds": fallback_holds,
        "ab_holds": ab_holds,
        "atlases": atlas_reports,
        "dds_output_format": "RGBA32_UNCOMPRESSED_MIP1_TEST_ONLY",
        "known_limitations": [
            "fallback may simplify style and may erase protected art inside an approved ROI",
            "ink-aware overlap relocation can leave original English elsewhere inside a broad ROI",
            "compressed/mipmapped source DDS are emitted as deterministic RGBA32 mip1 test DDS",
            "C1/C3 and actual HD-mod game runtime validation are still required",
        ],
        "release_approved": False,
        "runtime_validation": "UNTESTED",
    }

    manifest = {
        "status": "TEST_ONLY_NOT_RUNTIME_APPROVED",
        "active_roi_total": ACTIVE_ROI,
        "translation_coverage_accounted": coverage,
        "translation_coverage_complete": coverage == ACTIVE_ROI,
        "ab_candidate_applied_count": ab_applied,
        "ab_candidate_pending_import": ACTIVE_ROI - ab_imported,
        "dds_count": len(archive),
        "entries": {path: sha(raw) for path, raw in sorted(archive.items())},
    }

    zip_path = out / ZIPNAME
    with zipfile.ZipFile(zip_path, "w", allowZip64=True) as zf:
        for target, raw in sorted(archive.items()):
            zput(zf, target, raw)
        zput(zf, "TEST_ONLY_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode())
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None:
            raise ValueError("ZIP_CRC_FAILED")
        for target, raw in archive.items():
            if zf.read(target) != raw:
                raise ValueError("ZIP_DDS_READBACK_MISMATCH:" + target)

    report["zip_sha256"] = sha(zip_path.read_bytes())
    (out / "qa_report.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_dds_verified": source_verified,
                "output_dds_count": len(archive),
                "translation_coverage_accounted": coverage,
                "translation_coverage_complete": coverage == ACTIVE_ROI,
                "ab_candidate_imported_count": ab_imported,
                "ab_candidate_applied_count": ab_applied,
                "ab_candidate_pending_import": ACTIVE_ROI - ab_imported,
                "fallback_hold_count": len(fallback_holds),
                "ab_candidate_hold_count": len(ab_holds),
                "zip_sha256": report["zip_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    if source_verified != ACTIVE_DDS or len(archive) != ACTIVE_DDS:
        raise SystemExit("HD_SOURCE_OR_OUTPUT_DDS_INCOMPLETE")
    if coverage != ACTIVE_ROI or fallback_holds:
        raise SystemExit("TRANSLATION_COVERAGE_NOT_COMPLETE")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", default="/tmp/outrun-hd-hybrid")
    args = parser.parse_args()
    build(args.repo_root, args.out)
