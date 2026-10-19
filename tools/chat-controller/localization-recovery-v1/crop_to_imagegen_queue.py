#!/usr/bin/env python3
"""Bridge verified native C crops into the A/B ImageGen ROI queue.

This never edits DDS files and never promotes game/runtime approval. It accepts
only direct, unsplit, SHA-bound HD source crops whose English text has exactly
one reviewed Korean mapping. Existing queue order is append-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time

from PIL import Image

DEFAULT_C_ROOT = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
DEFAULT_TRANSCRIPT = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012/transcriptions.jsonl")
DEFAULT_IMAGEGEN_ROOT = Path("/data/imagegen")
SCHEMA = "outrun-text-roi-production-v1"
ACTIVATION = "AUTO_NATIVE_CROP_TO_IMAGEGEN_20261019"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE = re.compile(r"^[A-Za-z0-9_-]{4,96}$")
ACCEPT_STATUS = {"TEST_ONLY_UNTESTED_IN_GAME", "CROP_TEST_ONLY_REVIEW_REQUIRED"}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
        tmp = Path(f.name)
    os.replace(tmp, path)

def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()

def translations(path: Path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") != "transcribed_reviewed":
            continue
        q = "Q" + str(row.get("index", "")).zfill(3)
        for seg in row.get("segments", []):
            en, ko = seg.get("source"), seg.get("korean")
            if not isinstance(en, str) or not isinstance(ko, str) or not en.strip() or not ko.strip():
                continue
            if normalized(en) == normalized(ko):
                continue
            out.setdefault((q, normalized(en)), set()).add(ko.strip())
    return out

def qid(source_png: str):
    m = re.match(r"Q(\d{3})_", source_png or "")
    return ("Q" + m.group(1)) if m else None

def source_manifests(croot: Path):
    yield from sorted((croot / "hd108_outputs").glob("*/*/manifest.json"))

def fit_reference(src: Path, dst: Path):
    """Create only an ImageGen reference copy; the canonical native crop stays unchanged."""
    with Image.open(src) as im:
        if im.format != "PNG" or im.mode != "RGBA":
            raise ValueError("CROP_NOT_RGBA_PNG")
        w, h = im.size
        if w < 8 or h < 8:
            raise ValueError("CROP_TOO_SMALL")
        scale = 1
        # Small lettering benefits from a larger reference. Never exceed 2048.
        while h * scale < 160 and max(w, h) * (scale * 2) <= 2048 and scale < 4:
            scale *= 2
        if max(w, h) * scale > 2048:
            scale = max(1, 2048 // max(w, h))
        out = im if scale == 1 else im.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp.png")
        out.save(tmp, format="PNG")
        os.replace(tmp, dst)
        return scale, out.size

def archive_legacy_state(root: Path):
    base = root / "text_roi_batches"
    marker = base / "auto_activation_20261019.json"
    if marker.exists():
        return
    hist = base / "history"
    hist.mkdir(parents=True, exist_ok=True)
    for name in ("A_state.json", "B_state.json", "production_manifest.json"):
        p = base / name
        if p.exists() and not p.is_symlink():
            target = hist / ("pre_auto_20261019_" + name)
            if not target.exists():
                shutil.copy2(p, target)
    # Old pilot state must not block the new source-only auto queue.
    for name in ("A_state.json", "B_state.json"):
        p = base / name
        if p.exists() and not p.is_symlink():
            p.unlink()
    atomic_json(marker, {
        "activation": ACTIVATION,
        "legacy_state_preserved_under": str(hist),
        "legacy_986_tiles_used": False,
        "dds_auto_write": False,
        "game_pass_auto_promote": False,
    })

def load_manifest(path: Path):
    if not path.exists():
        return {"schema": SCHEMA, "activation": ACTIVATION, "items": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    # First active run replaces the old single Q104 pilot manifest after backup.
    if data.get("activation") != ACTIVATION:
        return {"schema": SCHEMA, "activation": ACTIVATION, "items": []}
    if data.get("schema") != SCHEMA or not isinstance(data.get("items"), list):
        raise ValueError("ACTIVE_MANIFEST_INVALID")
    return data

def scan_once(croot: Path, transcript: Path, imagegen_root: Path):
    if not croot.is_dir() or not transcript.is_file():
        raise ValueError("SOURCE_ROOT_OR_TRANSCRIPT_MISSING")
    archive_legacy_state(imagegen_root)
    tr = translations(transcript)
    base = imagegen_root / "text_roi_batches"
    inputs = base / "inputs"
    manifest_path = base / "production_manifest.json"
    data = load_manifest(manifest_path)
    existing = {x.get("source_key") for x in data["items"] if isinstance(x, dict)}
    added = 0
    held = 0
    for mp in source_manifests(croot):
        try:
            j = json.loads(mp.read_text(encoding="utf-8"))
            if j.get("status") not in ACCEPT_STATUS:
                continue
            if j.get("source_type") != "SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG":
                continue
            if j.get("old_split_tiles_used") is not False:
                continue
            if j.get("edge_warning") not in (None, ""):
                continue
            source_sha = j.get("source_sha256")
            dds_sha = j.get("reference_dds_sha256")
            crop_sha = j.get("crop_sha256")
            if not all(isinstance(x, str) and HEX64.fullmatch(x) for x in (source_sha, dds_sha, crop_sha)):
                held += 1
                continue
            q = qid(j.get("source_png", ""))
            en = j.get("english")
            bbox = j.get("bbox_xyxy")
            if not q or not isinstance(en, str) or not en.strip():
                held += 1
                continue
            if not (isinstance(bbox, list) and len(bbox) == 4 and all(type(x) is int for x in bbox)):
                held += 1
                continue
            kos = tr.get((q, normalized(en)), set())
            if len(kos) != 1:
                continue
            crop = mp.parent / "english_original_native_crop.png"
            if not crop.is_file() or crop.is_symlink() or digest(crop) != crop_sha:
                held += 1
                continue
            key = hashlib.sha256((source_sha + "|" + en + "|" + ",".join(map(str, bbox))).encode()).hexdigest()
            if key in existing:
                continue
            ident = f"{q}_{key[:16]}"
            if not SAFE.fullmatch(ident):
                raise ValueError("UNSAFE_GENERATED_ID")
            role = "A" if int(q[1:]) % 2 else "B"
            outname = ident + "_source.png"
            outpath = inputs / outname
            if outpath.exists():
                # A pre-existing file must be byte-identical to our generated reference.
                outpath.unlink()
            scale, dimensions = fit_reference(crop, outpath)
            in_sha = digest(outpath)
            data["items"].append({
                "id": ident,
                "role": role,
                "queue_index": q[1:],
                "status": "ROI_APPROVED_FOR_IMAGEGEN",
                "source_provenance": "SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
                "source_dds_path": j.get("reference_dds_path"),
                "source_dds_sha256": dds_sha,
                "source_png_sha256": source_sha,
                "bbox_xyxy": bbox,
                "imagegen_input_png": outname,
                "imagegen_input_sha256": in_sha,
                "alpha_crop_margin_checked": True,
                "english": en.strip(),
                "korean": next(iter(kos)),
                "source_key": key,
                "native_crop_sha256": crop_sha,
                "reference_scale": scale,
                "reference_dimensions": list(dimensions),
                "old_split_tiles_used": False,
                "auto_admission": "EXACT_REVIEWED_TRANSLATION_AND_SHA_VERIFIED_NATIVE_CROP",
                "runtime_validation": "UNTESTED",
            })
            existing.add(key)
            added += 1
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            held += 1
    data["activation"] = ACTIVATION
    data["legacy_986_tiles_used"] = False
    data["dds_auto_write"] = False
    data["game_pass_auto_promote"] = False
    data["item_count"] = len(data["items"])
    atomic_json(manifest_path, data)
    return {"status": "QUEUE_SYNC", "added": added, "held": held, "total": len(data["items"]),
            "A": sum(x["role"] == "A" for x in data["items"]),
            "B": sum(x["role"] == "B" for x in data["items"])}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c-root", type=Path, default=DEFAULT_C_ROOT)
    ap.add_argument("--transcript", type=Path, default=DEFAULT_TRANSCRIPT)
    ap.add_argument("--imagegen-root", type=Path, default=DEFAULT_IMAGEGEN_ROOT)
    ap.add_argument("--interval-seconds", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.interval_seconds < 20:
        raise SystemExit("INTERVAL_TOO_SHORT")
    while True:
        try:
            print(json.dumps(scan_once(args.c_root, args.transcript, args.imagegen_root),
                             ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"status": "QUEUE_SYNC_HOLD", "reason": type(exc).__name__ + ":" + str(exc)[:300]},
                             ensure_ascii=False), flush=True)
        if args.once:
            break
        time.sleep(args.interval_seconds)

if __name__ == "__main__":
    main()
