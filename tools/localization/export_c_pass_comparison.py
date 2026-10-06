#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

SOURCE_REPO = "Sonic-TV/OR2006Sprites"
SOURCE_COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
OUTPUT_REL = Path("localization/graphics/role_C/PRE_INGAME_JPG_REVIEW")
ALIAS_SOURCE_BASENAME = {"06AB5CEE_1024x1024.dds": "6AB5CEE_1024x1024.dds"}

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

def source_url(asset_path):
    parts = Path(asset_path).parts
    if len(parts) < 3 or parts[0:2] != ("textures", "load"):
        raise RuntimeError(f"unexpected asset path: {asset_path}")
    sub = Path(*parts[2:])
    sub = sub.with_name(ALIAS_SOURCE_BASENAME.get(sub.name, sub.name))
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/Release/{sub.as_posix()}"

def download_source(asset_path, key, cache):
    url = source_url(asset_path)
    dst = cache / f"{key}.dds"
    req = urllib.request.Request(url, headers={"User-Agent": "OutRun-Korean-C-QA"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    dst.write_bytes(data)
    return dst, url, sha256_bytes(data)

def draw_label(draw, xy, text, font, fill=(245, 245, 245)):
    draw.text(xy, text, font=font, fill=fill)

def make_pair_card(no, idx, key, status, source_raw, current_raw, policy_preserve, font, small):
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
    header_h = 126
    label_h = 38
    width = cell_w * 2 + gutter
    height = header_h + label_h + top_h + gutter + label_h + raw_h + 24
    canvas = Image.new("RGB", (width, height), (28, 28, 28))
    d = ImageDraw.Draw(canvas)
    draw_label(d, (18, 10), f"{no:03d}  q{idx:03d}  {key}", font)
    draw_label(d, (18, 50), status, small, (220, 220, 220))
    note = ("C POLICY PASS: CURRENT IS THE ORIGINAL ENGLISH ARTWORK (NO LOCALIZED PIXELS)"
            if policy_preserve else
            "COMPARE ENGLISH ORIGINAL vs CURRENT KOREAN CANDIDATE")
    draw_label(d, (18, 82), note, small, (210, 210, 210))
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
    cache = Path("/tmp/outrun_c_english_sources")
    cache.mkdir(parents=True, exist_ok=True)
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
        source_file, url, source_sha = download_source(asset_path, key, cache)
        with Image.open(source_file) as im:
            source_raw = im.convert("RGBA")
        policy_preserve = not candidate.exists()
        if candidate.exists():
            candidate_bytes = candidate.read_bytes()
            candidate_sha = sha256_bytes(candidate_bytes)
            with Image.open(candidate) as im:
                current_raw = im.convert("RGBA")
            source_kind = "localized_candidate"
        else:
            current_raw = source_raw.copy()
            candidate_sha = ""
            source_kind = "policy_pass_no_candidate"
        if source_raw.size != current_raw.size:
            raise RuntimeError(f"{key}: English source {source_raw.size} != current candidate {current_raw.size}")
        name = f"{no:03d}_q{idx:03d}_{key}.jpg"
        card = make_pair_card(no, idx, key, row["artwork_status"], source_raw, current_raw, policy_preserve, font, small)
        card.save(out / name, "JPEG", quality=94, subsampling=0, optimize=True)
        manifest.append({
            "number": no,
            "queue_index": idx,
            "asset_key": key,
            "asset_path": asset_path,
            "artwork_status": row["artwork_status"],
            "source_kind": source_kind,
            "english_source_repo": SOURCE_REPO,
            "english_source_commit": SOURCE_COMMIT,
            "english_source_url": url,
            "english_source_sha256": source_sha,
            "candidate_sha256": candidate_sha,
            "decoded_size": [source_raw.width, source_raw.height],
            "jpg": name,
        })
    fields = ["number","queue_index","asset_key","asset_path","artwork_status","source_kind",
              "english_source_repo","english_source_commit","english_source_url",
              "english_source_sha256","candidate_sha256","decoded_size","jpg"]
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        for e in manifest:
            row = dict(e)
            row["decoded_size"] = "x".join(str(x) for x in row["decoded_size"])
            w.writerow({k: row.get(k, "") for k in fields})
    (out / "manifest.json").write_text(json.dumps({
        "schema_version": 2,
        "selection": "current localize_text C PASS plus exact aliases of C-approved candidate bytes; pending-C rework excluded",
        "english_source_repo": SOURCE_REPO,
        "english_source_commit": SOURCE_COMMIT,
        "count": len(manifest),
        "localized_candidate_count": sum(x["source_kind"] == "localized_candidate" for x in manifest),
        "policy_pass_no_candidate_count": sum(x["source_kind"] == "policy_pass_no_candidate" for x in manifest),
        "layout": "top row English original vs current Korean in FLIP-Y review; bottom row English original vs current Korean in RAW DDS",
        "items": manifest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        "# C QA PASS - English original vs Korean pre-in-game review\n\n"
        f"- Numbered C-pass rows: {len(manifest)}\n"
        f"- English source: {SOURCE_REPO} pinned at {SOURCE_COMMIT}\n"
        "- Every JPG contains the English original and current Korean candidate side-by-side at the same decoded size/orientation.\n"
        "- Top: FLIP-Y review comparison. Bottom: RAW DDS comparison.\n"
        "- English source SHA-256 and candidate SHA-256 are recorded in the manifests.\n"
        "- If the source cannot be downloaded or its decoded size differs from the candidate, export fails closed.\n"
        "- User visual rejection overrides prior C static PASS and reopens the asset for A/B rework before in-game testing.\n"
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
        "english_source_commit": SOURCE_COMMIT,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
