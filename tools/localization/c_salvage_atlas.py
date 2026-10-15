#!/usr/bin/env python3
"""C-SALVAGE stage 0: losslessly reassemble split English HD source tiles.

Never composites a generated image into the source, calls ImageGen, alters A/B,
promotes QA, or claims equivalence with the canonical DDS without verification.
Only complete, non-overlapping, SHA-pinned tile groups are exported.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

SCHEMA = "outrun-c-source-atlas-reassembly-v1"
MAP_REL = Path("inputs/A/HD_EN_TILES_20261014/ALL_TILE_MAPPING.csv")
REQUIRED = ("part_filename", "source_png", "source_dds_path", "source_width",
            "source_height", "x", "y", "width", "height", "orientation",
            "source_png_sha256", "part_png_sha256")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def safe_filename(value: str) -> str:
    if not value or value in (".", "..") or Path(value).name != value or "/" in value or "\\" in value:
        raise ValueError("Unsafe mapping filename")
    return value


def load_groups(mapping: Path):
    with mapping.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in REQUIRED):
            raise ValueError("Missing required tile mapping columns")
        groups = {}
        for row in reader:
            for field in REQUIRED:
                if not (row.get(field) or "").strip():
                    raise ValueError("Empty tile mapping field " + field)
            safe_filename(row["source_png"])
            safe_filename(row["part_filename"])
            key = (row["source_png"], row["source_dds_path"], row["source_png_sha256"])
            groups.setdefault(key, []).append(row)
    return groups


def group_key(key):
    name, path, original_sha = key
    return Path(name).stem + "--" + sha((path + "|" + original_sha).encode())[:12]


def _identical_metadata(rows):
    columns = ("source_png", "source_dds_path", "source_width", "source_height",
               "orientation", "source_png_sha256")
    if any(any(row[col] != rows[0][col] for col in columns) for row in rows):
        raise ValueError("Conflicting source metadata within atlas")
    width, height = int(rows[0]["source_width"]), int(rows[0]["source_height"])
    if width <= 0 or height <= 0 or width * height > 4096 * 4096:
        raise ValueError("Unreasonable source atlas dimensions")
    if rows[0]["orientation"] not in ("NORMAL", "FLIP_Y_PREVIEW_PER_SPRITE_VERIFY"):
        raise ValueError("Unreviewed orientation")
    return width, height


def assemble(mapping: Path, key, rows, output: Path):
    width, height = _identical_metadata(rows)
    base = mapping.parent
    covered = np.zeros((height, width), dtype=np.uint8)
    atlas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    manifest = []
    seen = set()
    for row in rows:
        filename = safe_filename(row["part_filename"])
        if filename in seen:
            raise ValueError("Duplicate tile filename")
        seen.add(filename)
        x, y, w, h = (int(row[k]) for k in ("x", "y", "width", "height"))
        if min(x, y) < 0 or w <= 0 or h <= 0 or x+w > width or y+h > height:
            raise ValueError("Out of bounds tile: " + filename)
        region = covered[y:y+h, x:x+w]
        if region.any():
            raise ValueError("Overlapping tiles: " + filename)
        src = base / filename
        if not src.is_file() or not src.resolve().is_relative_to(base.resolve()):
            raise ValueError("Missing or escaped source tile: " + filename)
        raw = src.read_bytes()
        if sha(raw).lower() != row["part_png_sha256"].lower():
            raise ValueError("Tile SHA mismatch: " + filename)
        with Image.open(src) as im:
            if im.format != "PNG" or im.mode != "RGBA" or im.size != (w, h):
                raise ValueError("Tile PNG mode/size mismatch: " + filename)
            im.load()
            atlas.paste(im, (x, y))
        region[:] = 1
        manifest.append({"tile": filename, "tile_sha256": sha(raw), "bbox": [x, y, x+w, y+h]})
    if not np.all(covered):
        raise ValueError("Missing pixels / incomplete atlas coverage: " +
                         str(int(np.count_nonzero(covered == 0))))
    del covered

    full = base / safe_filename(key[0])
    original_match = "REFERENCE_FULL_PNG_NOT_STAGED"
    if full.is_file():
        data = full.read_bytes()
        if sha(data).lower() != key[2].lower():
            raise ValueError("Full English PNG SHA mismatch")
        with Image.open(full) as im:
            if im.format != "PNG" or im.size != (width, height) or im.mode != "RGBA":
                raise ValueError("Full English PNG size/mode mismatch")
            if not np.array_equal(np.asarray(im), np.asarray(atlas)):
                raise ValueError("Reassembled pixels differ from canonical source PNG")
        original_match = "FULL_PNG_SHA_AND_PIXELS_MATCH"

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Previous partial atlas directory requires review")
    with tempfile.TemporaryDirectory(prefix=".atlas-build-", dir=output.parent) as staging:
        tmp = Path(staging)
        exported = tmp / "source_reassembled_readable.png"
        atlas.save(exported, "PNG")
        evidence = {
            "schema": SCHEMA,
            "status": "REASSEMBLED_READABLE_SOURCE_TEST_ONLY_DDS_NOT_VERIFIED",
            "original_full_png_comparison": original_match,
            "source_png": key[0],
            "source_dds_path": key[1],
            "source_png_sha256_declared": key[2],
            "orientation": rows[0]["orientation"],
            "source_size": [width, height],
            "tile_count": len(manifest),
            "tiles": manifest,
            "output_sha256": sha(exported.read_bytes()),
            "C1": "NOT_RUN",
            "C3": "NOT_RUN",
            "RUNTIME_VALIDATION": "UNTESTED",
            "DDS_EQUIVALENCE": "UNVERIFIED",
        }
        (tmp / "atlas_manifest.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
        os.rename(tmp, output)
    return evidence


def run_atlas_first(input_root: Path, output_root: Path, max_groups: int = 4):
    mapping = input_root / MAP_REL
    result = {"mapping_present": mapping.is_file(), "new": 0, "counts": {}, "ready": {}}
    if not mapping.is_file():
        return result
    groups = load_groups(mapping)
    generated = set()
    for role in ("A", "B"):
        generated.update(p.name for p in (input_root / "ab_batches/candidate_outputs" / role).glob("*.png"))
    selected = sorted(groups.items(),
                      key=lambda item: (-sum(row["part_filename"][:-4] + "_k.png" in generated
                                             for row in item[1]), group_key(item[0])))
    for key, rows in selected:
        name = group_key(key)
        done = output_root / "atlases" / name
        manifest_path = done / "atlas_manifest.json"
        if manifest_path.is_file() and (done / "source_reassembled_readable.png").is_file():
            try:
                old = json.loads(manifest_path.read_text())
                if old.get("schema") == SCHEMA and old.get("source_png_sha256_declared") == key[2]:
                    for row in rows:
                        result["ready"][row["part_filename"]] = {
                            "full_atlas_path": str(done / "source_reassembled_readable.png"),
                            "atlas_manifest_path": str(manifest_path),
                            "atlas_sha256": old["output_sha256"],
                            "source_dds_path": key[1],
                            "orientation": old["orientation"],
                            "status": old["status"],
                        }
                    continue
            except (ValueError, OSError, KeyError):
                pass
        if result["new"] >= max_groups:
            continue
        failure = output_root / "atlas_failures" / (name + ".json")
        try:
            ev = assemble(mapping, key, rows, done)
            result["counts"]["REASSEMBLED_SOURCE_TEST_ONLY"] = result["counts"].get("REASSEMBLED_SOURCE_TEST_ONLY", 0) + 1
            for row in rows:
                result["ready"][row["part_filename"]] = {
                    "full_atlas_path": str(done / "source_reassembled_readable.png"),
                    "atlas_manifest_path": str(manifest_path),
                    "atlas_sha256": ev["output_sha256"],
                    "source_dds_path": key[1],
                    "orientation": ev["orientation"],
                    "status": ev["status"],
                }
            if failure.is_file():
                failure.unlink()
        except (OSError, ValueError, OverflowError) as error:
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_text(json.dumps({
                "schema": SCHEMA, "source_png": key[0], "source_dds_path": key[1],
                "status": "HOLD_ATLAS_REASSEMBLY", "reason": str(error),
                "RUNTIME_VALIDATION": "UNTESTED"}, ensure_ascii=False, indent=2) + "\n")
            result["counts"]["HOLD_ATLAS_REASSEMBLY"] = result["counts"].get("HOLD_ATLAS_REASSEMBLY", 0) + 1
        result["new"] += 1
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-root", required=True)
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--max-groups", type=int, default=4)
    opts = ap.parse_args()
    if Path(opts.output_root).resolve().is_relative_to(Path(opts.input_root).resolve()):
        ap.error("C output must be separate from read-only input")
    result = run_atlas_first(Path(opts.input_root), Path(opts.output_root), opts.max_groups)
    print(json.dumps({k: v for k, v in result.items() if k != "ready"}, ensure_ascii=False))
