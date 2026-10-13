"""Audit source tile orientation and publish a reproducible upright input manifest.

Only known, reviewed orientation exceptions are converted; don't overwrite
user-supplied English originals. The one known truncated PNG stays quarantined.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

try:
    from app.tile_batch_queue import _source_rows, _sha_png, TILE_DIR
    from app.tile_orientation_policy import resolve_upright_source
except ModuleNotFoundError:
    from tile_batch_queue import _source_rows, _sha_png, TILE_DIR
    from tile_orientation_policy import resolve_upright_source

COLUMNS = (
    "part_filename", "queue_indexes", "source_dds_path", "x", "y",
    "width", "height", "source_orientation",
    "original_png_sha256", "upright_png_path", "upright_png_sha256",
    "source_to_upright", "upright_to_source", "dds_orientation",
    "translation_imagegen_status"
)

def publish_manifest(root):
    root = Path(root).resolve()
    records, orig, tr = _source_rows(root)
    results = []
    for row in records:
        original = root / TILE_DIR / row["part_filename"]
        size = (int(row["width"]), int(row["height"]))
        _sha_png(original, row["part_png_sha256"], size)
        working = resolve_upright_source(root, row, original)
        _sha_png(Path(working["path"]), working["sha256"], size)
        results.append({
            "part_filename": row["part_filename"],
            "queue_indexes": row["queue_indexes"],
            "source_dds_path": row["source_dds_path"],
            "x": row["x"],
            "y": row["y"],
            "width": row["width"],
            "height": row["height"],
            "source_orientation": working["source_orientation"],
            "original_png_sha256": working["source_png_sha256"],
            "upright_png_path": str(Path(working["path"]).relative_to(root)),
            "upright_png_sha256": working["sha256"],
            "source_to_upright": working["source_to_upright"],
            "upright_to_source": working["upright_to_source"],
            "dds_orientation": working["dds_orientation"],
            "translation_imagegen_status": "PENDING",
        })
    if len(results) != 985:
        raise ValueError("EXPECTED_985_QA_VALID_SOURCES_AFTER_ONE_QUARANTINE")
    dest = root / "a_tile_batches" / "UPRIGHT_SOURCE_MANIFEST_20261014.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    temp.replace(dest)
    counters = {
        "source_total": 986,
        "qa_valid_reference_count": len(results),
        "source_corrupt_quarantined_count": 1,
        "source_to_upright_flipped": sum(x["source_to_upright"] == "FLIP_Y" for x in results),
        "already_readable_preserved": sum(x["source_to_upright"] == "IDENTITY" for x in results),
        "manifest_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "verified_rgba_and_dimensions": "Q012_RGBA_and_roundtrip_verified; other tiles checked for CRC/size, not all visually inspected",
        "imagegen_completed": 0,
        "dds_runtime_validation": "UNTESTED",
    }
    summary = dest.with_suffix(".summary.json")
    summary.write_text(json.dumps(counters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest, counters


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path("/data/imagegen")
    p, data = publish_manifest(root)
    print(json.dumps({"path":str(p),**data},ensure_ascii=False))