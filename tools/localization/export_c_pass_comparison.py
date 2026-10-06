#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

SOURCE_REPO = "Sonic-TV/OR2006Sprites"
SOURCE_COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
OUTPUT_REL = Path("localization/graphics/role_C/PRE_INGAME_JPG_REVIEW")
VISUAL_REVIEW_CHECKLIST = [
    "plate_restoration_no_haze_or_source_residue",
    "readable_slant_direction_matches_source",
    "text_scale_and_hierarchy_not_visibly_undersized",
    "weight_outline_shadow_shading_remain_readable",
    "no_fill_outline_shadow_or_italic_end_clipping",
    "no_vehicle_name_icon_plate_or_neighbor_intrusion",
    "no_untranslated_visible_localizable_labels",
]
STOCK_ZIP_REL = Path("localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip")
ALIAS_SOURCE_BASENAME = {"06AB5CEE_1024x1024.dds": "6AB5CEE_1024x1024.dds"}
EXPECTED_SOURCE_SHA = {
    "D6DC1380": "42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352",
    "1F5FE6E9": "3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d",
}

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def current_c_pass(row):
    if row.get("action") != "localize_text":
        return False
    s = (row.get("artwork_status") or "").lower()
    return ((s.startswith("c") and "pass" in s and "pending_c" not in s)
            or ("alias_of_c" in s and "pass" in s))

def flatten(im, bg=(96, 96, 96)):
    im = im.convert("RGBA")
    base = Image.new("RGB", im.size, bg)
    base.paste(im.convert("RGB"), mask=im.getchannel("A"))
    return base

def fit(im, max_side=2048):
    scale = min(1.0, max_side / max(im.size))
    if scale >= 1.0:
        return im
    return im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.Resampling.LANCZOS)

def public_source_url(asset_path):
    parts = Path(asset_path).parts
    if len(parts) < 3 or parts[0:2] != ("textures", "load"):
        raise RuntimeError(f"unexpected asset path: {asset_path}")
    sub = Path(*parts[2:])
    sub = sub.with_name(ALIAS_SOURCE_BASENAME.get(sub.name, sub.name))
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/Release/{sub.as_posix()}"

def download_public_source(asset_path):
    url = public_source_url(asset_path)
    req = urllib.request.Request(url, headers={"User-Agent": "OutRun-Korean-C-QA"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    return data, url

def load_stock_zip_source(repo, asset_path):
    zp = repo / STOCK_ZIP_REL
    if not zp.exists():
        return None
    rel = asset_path.replace("\\", "/")
    with zipfile.ZipFile(zp) as z:
        if rel not in z.namelist():
            return None
        return z.read(rel)

def decode_dds(data):
    with Image.open(io.BytesIO(data)) as im:
        return im.convert("RGBA")

def select_english_source(repo, asset_path, key, candidate_size):
    public_data, public_url = download_public_source(asset_path)
    public_raw = decode_dds(public_data)
    public_sha = sha256_bytes(public_data)

    if candidate_size is None or public_raw.size == candidate_size:
        chosen = {
            "data": public_data,
            "raw": public_raw,
            "origin": "pinned_public_source",
            "location": public_url,
            "commit": SOURCE_COMMIT,
            "sha256": public_sha,
            "native_size": list(public_raw.size),
            "display_scale": 1,
        }
    else:
        sw, sh = public_raw.size
        cw, ch = candidate_size

        stock_data = load_stock_zip_source(repo, asset_path)
        stock_raw = decode_dds(stock_data) if stock_data is not None else None

        if stock_raw is not None and stock_raw.size == candidate_size:
            chosen = {
                "data": stock_data,
                "raw": stock_raw,
                "origin": "repository_stock_original_zip",
                "location": f"{STOCK_ZIP_REL.as_posix()}#{asset_path}",
                "commit": "",
                "sha256": sha256_bytes(stock_data),
                "native_size": list(stock_raw.size),
                "display_scale": 1,
            }
        elif cw % sw == 0 and ch % sh == 0 and cw // sw == ch // sh:
            scale = cw // sw
            if scale < 1:
                raise RuntimeError(f"{key}: invalid public-source scale {public_raw.size} -> {candidate_size}")
            chosen = {
                "data": public_data,
                "raw": public_raw,
                "origin": "pinned_public_source_display_scaled",
                "location": public_url,
                "commit": SOURCE_COMMIT,
                "sha256": public_sha,
                "native_size": list(public_raw.size),
                "display_scale": scale,
            }
        else:
            raise RuntimeError(
                f"{key}: no proven English source matching candidate size; "
                f"public={public_raw.size}, stock_zip={getattr(stock_raw, 'size', None)}, candidate={candidate_size}"
            )

    expected = EXPECTED_SOURCE_SHA.get(key)
    if expected and chosen["sha256"] != expected:
        raise RuntimeError(
            f"{key}: selected English source SHA mismatch {chosen['sha256']} != expected {expected}"
        )
    return chosen

def source_for_display(source, target_size):
    raw = source["raw"]
    if target_size is None or raw.size == target_size:
        return raw
    scale = source["display_scale"]
    if scale <= 1:
        raise RuntimeError(f"unsupported display source resize {raw.size} -> {target_size}")
    return raw.resize(target_size, Image.Resampling.NEAREST)

def draw_label(draw, xy, text, font, fill=(245, 245, 245)):
    draw.text(xy, text, font=font, fill=fill)

def make_pair_card(no, idx, key, status, source_raw, current_raw, source_native_size, source_scale, policy_preserve, font, small):
    source_readable = ImageOps.flip(source_raw)
    current_readable = ImageOps.flip(current_raw)
    sr = fit(flatten(source_readable))
    kr = fit(flatten(current_readable))
    sraw = fit(flatten(source_raw))
    kraw = fit(flatten(current_raw))
    cell_w = max(sr.width, kr.width, sraw.width, kraw.width)
    top_h = max(sr.height, kr.height)
    raw_h = max(sraw.height, kraw.height)
    gutter = 18
    header_h = 150
    label_h = 38
    width = cell_w * 2 + gutter
    height = header_h + label_h + top_h + gutter + label_h + raw_h + 24
    canvas = Image.new("RGB", (width, height), (28, 28, 28))
    d = ImageDraw.Draw(canvas)
    draw_label(d, (18, 10), f"{no:03d}  q{idx:03d}  {key}", font)
    draw_label(d, (18, 50), status, small, (220, 220, 220))
    if policy_preserve:
        note = "C POLICY PASS: CURRENT IS ORIGINAL ENGLISH ARTWORK (NO LOCALIZED PIXELS)"
    else:
        note = "COMPARE ENGLISH ORIGINAL vs CURRENT KOREAN CANDIDATE"
    draw_label(d, (18, 80), note, small, (210, 210, 210))
    scale_note = f"English native {source_native_size[0]}x{source_native_size[1]}"
    if source_scale > 1:
        scale_note += f" - DISPLAY ONLY scaled x{source_scale} with nearest-neighbor to candidate size"
    draw_label(d, (18, 108), scale_note, small, (190, 190, 190))

    x1, x2 = 0, cell_w + gutter
    y = header_h
    draw_label(d, (12, y + 5), "ENGLISH ORIGINAL - FLIP-Y REVIEW", small)
    draw_label(d, (x2 + 12, y + 5), "CURRENT KOREAN - FLIP-Y REVIEW" if not policy_preserve else "CURRENT - ORIGINAL PRESERVED", small)
    y += label_h
    canvas.paste(sr, (x1 + (cell_w - sr.width)//2, y))
    canvas.paste(kr, (x2 + (cell_w - kr.width)//2, y))
    y += top_h + gutter

    draw_label(d, (12, y + 5), "ENGLISH ORIGINAL - RAW DDS", small)
    draw_label(d, (x2 + 12, y + 5), "CURRENT KOREAN - RAW DDS" if not policy_preserve else "CURRENT RAW - ORIGINAL PRESERVED", small)
    y += label_h
    canvas.paste(sraw, (x1 + (cell_w - sraw.width)//2, y))
    canvas.paste(kraw, (x2 + (cell_w - kraw.width)//2, y))
    return canvas

def main():
    if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
        raise SystemExit("GitHub-hosted role C required")

    repo = Path.cwd()
    queue = repo / "localization/graphics/asset_queue.csv"
    out = repo / OUTPUT_REL
    out.mkdir(parents=True, exist_ok=True)
    for p in out.iterdir():
        if p.is_file():
            p.unlink()

    rows = list(csv.DictReader(queue.open(encoding="utf-8-sig", newline="")))
    rows = sorted((r for r in rows if current_c_pass(r)), key=lambda r: int(r["index"]))
    if not rows:
        raise RuntimeError("no current C-pass graphics")

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    except Exception:
        font = small = ImageFont.load_default()

    manifest = []
    for no, row in enumerate(rows, 1):
        idx = int(row["index"])
        asset_path = row["path"]
        key = Path(asset_path).name.split("_", 1)[0]
        candidate = repo / "localization/graphics/hd_candidates" / asset_path

        policy_preserve = not candidate.exists()
        if candidate.exists():
            candidate_bytes = candidate.read_bytes()
            candidate_sha = sha256_bytes(candidate_bytes)
            with Image.open(candidate) as im:
                current_native = im.convert("RGBA")
            candidate_size = current_native.size
            source_kind = "localized_candidate"
        else:
            candidate_sha = ""
            current_native = None
            candidate_size = None
            source_kind = "policy_pass_no_candidate"

        source = select_english_source(repo, asset_path, key, candidate_size)
        if policy_preserve:
            current_native = source["raw"].copy()
            candidate_size = current_native.size

        source_display = source_for_display(source, candidate_size)
        if source_display.size != current_native.size:
            raise RuntimeError(f"{key}: review display mismatch {source_display.size} != {current_native.size}")

        name = f"{no:03d}_q{idx:03d}_{key}.jpg"
        card = make_pair_card(
            no, idx, key, row["artwork_status"], source_display, current_native,
            source["native_size"], source["display_scale"], policy_preserve, font, small
        )
        card.save(out / name, "JPEG", quality=94, subsampling=0, optimize=True)

        manifest.append({
            "number": no,
            "queue_index": idx,
            "asset_key": key,
            "asset_path": asset_path,
            "artwork_status": row["artwork_status"],
            "source_kind": source_kind,
            "english_source_origin": source["origin"],
            "english_source_location": source["location"],
            "english_source_commit": source["commit"],
            "english_source_sha256": source["sha256"],
            "english_source_native_size": source["native_size"],
            "review_display_scale": source["display_scale"],
            "review_display_size": list(candidate_size),
            "candidate_sha256": candidate_sha,
            "jpg": name,
        })

    fields = [
        "number","queue_index","asset_key","asset_path","artwork_status","source_kind",
        "english_source_origin","english_source_location","english_source_commit",
        "english_source_sha256","english_source_native_size","review_display_scale",
        "review_display_size","candidate_sha256","jpg"
    ]
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        for e in manifest:
            row = dict(e)
            row["english_source_native_size"] = "x".join(str(x) for x in row["english_source_native_size"])
            row["review_display_size"] = "x".join(str(x) for x in row["review_display_size"])
            w.writerow({k: row.get(k, "") for k in fields})

    (out / "manifest.json").write_text(json.dumps({
        "schema_version": 3,
        "selection": "current localize_text C PASS plus exact aliases of C-approved candidate bytes; pending-C rework excluded",
        "public_english_source_repo": SOURCE_REPO,
        "public_english_source_commit": SOURCE_COMMIT,
        "stock_original_zip": STOCK_ZIP_REL.as_posix(),
        "count": len(manifest),
        "localized_candidate_count": sum(x["source_kind"] == "localized_candidate" for x in manifest),
        "policy_pass_no_candidate_count": sum(x["source_kind"] == "policy_pass_no_candidate" for x in manifest),
        "layout": "top row English original vs current Korean in FLIP-Y review; bottom row English original vs current Korean in RAW DDS",
        "display_scaling_policy": "Only a proven lower-resolution English source may be integer-nearest-neighbor scaled for review display; source native size and SHA stay recorded and unmodified.",
        "visual_review_checklist": VISUAL_REVIEW_CHECKLIST,
        "items": manifest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (out / "README.md").write_text(
        "# C QA PASS - English original vs Korean pre-in-game review\n\n"
        f"- Numbered C-pass rows: {len(manifest)}\n"
        f"- Primary English source: {SOURCE_REPO} pinned at {SOURCE_COMMIT}\n"
        f"- Exact stock-original fallback: {STOCK_ZIP_REL.as_posix()}\n"
        "- Every JPG contains the English original and current Korean candidate side-by-side.\n"
        "- Top: FLIP-Y review comparison. Bottom: RAW DDS comparison.\n"
        "- English source SHA-256, native dimensions, origin, and any review-only display scale are recorded in the manifests.\n"
        "- Lower-resolution English originals may be nearest-neighbor scaled only for human display; the English source bytes are never modified or treated as pixel-QA equivalents.\n"
        "- If no proven English source can be aligned to the candidate, export fails closed.\n"
        "- User visual rejection overrides prior C static PASS and reopens the asset for A/B rework before in-game testing.\n"
        "- C visual checklist: clean plate/source-footprint restoration; source-direction slant; source-relative scale/hierarchy; readable weight/effects; zero clipping; zero protected-art intrusion; no untranslated visible localizable labels.\n"
        "- Report defects by the leading JPG number.\n",
        encoding="utf-8",
    )

    thumb_w, thumb_h, cols = 360, 250, 4
    sheet = Image.new("RGB", (thumb_w*cols, thumb_h*((len(manifest)+cols-1)//cols)), (36,36,36))
    sd = ImageDraw.Draw(sheet)
    for i, e in enumerate(manifest):
        with Image.open(out / e["jpg"]) as im:
            im = im.convert("RGB")
            im.thumbnail((thumb_w-12, thumb_h-50), Image.Resampling.LANCZOS)
        x = (i % cols) * thumb_w
        y = (i // cols) * thumb_h
        sheet.paste(im, (x + (thumb_w-im.width)//2, y + 42))
        sd.text((x+8, y+8), f"{e['number']:03d} q{e['queue_index']:03d} {e['asset_key']}", font=small, fill="white")
    sheet.save(out / "000_INDEX.jpg", "JPEG", quality=92, subsampling=0, optimize=True)

    print(json.dumps({
        "output": str(OUTPUT_REL),
        "count": len(manifest),
        "localized_candidates": sum(x["source_kind"] == "localized_candidate" for x in manifest),
        "policy_cards": sum(x["source_kind"] == "policy_pass_no_candidate" for x in manifest),
        "display_scaled_sources": [x["asset_key"] for x in manifest if x["review_display_scale"] > 1],
        "stock_zip_sources": [x["asset_key"] for x in manifest if x["english_source_origin"] == "repository_stock_original_zip"],
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
