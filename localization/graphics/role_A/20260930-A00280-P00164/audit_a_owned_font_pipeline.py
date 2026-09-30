#!/usr/bin/env python3
"""Validate the static runtime crosswalk for A-owned font-pipeline assets.

This intentionally does not edit or generate DDS files. It proves which stock
font descriptor/resource handle corresponds to each A-owned queue atlas and
checks that the canonical graphics inventory remains bound to the same asset
hash. Runtime KoreanK3Trace evidence is still required before any stock font
resource can be repurposed or page-switched.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
QUEUE = ROOT / "localization/graphics/asset_queue.csv"
INVENTORY = ROOT / "localization/graphics/inventory.csv"
STOCK_MAP = ROOT / "localization/font/stock_font_map.json"
MANIFEST = ROOT / "localization/font/hangul_glyph_manifest.json"

TARGETS = {
    15: "20389D70",
    18: "7B65A191",
    21: "D7CE8BC3",
}


def csv_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    queue = {int(r["index"]): r for r in csv_rows(QUEUE)}
    inventory = {r["path"]: r for r in csv_rows(INVENTORY)}
    stock = json.loads(STOCK_MAP.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    descriptors = {d["dds_hash"]: d for d in stock["descriptors"]}
    out = {
        "schema": "outrun-a00280-a-owned-font-pipeline-static-crosswalk-v1",
        "manifest": {
            "glyph_count": manifest["glyph_count"],
            "page_count": manifest["page_count"],
            "page_capacity": manifest["page_capacity"],
            "grid": manifest["grid"],
        },
        "targets": [],
    }

    for index, asset_hash in TARGETS.items():
        q = queue[index]
        assert q["action"] == "font_pipeline"
        assert q["artwork_status"] == "blocked_runtime_font"
        assert asset_hash in q["path"]

        inv = inventory[q["path"]]
        desc = descriptors[asset_hash]
        stock_w, stock_h = desc["dds_size"]
        hd_w, hd_h = int(inv["width"]), int(inv["height"])

        out["targets"].append({
            "index": index,
            "path": q["path"],
            "asset_hash": asset_hash,
            "queue_status": q["artwork_status"],
            "canonical_inventory": {
                "sha256": inv["sha256"],
                "width": hd_w,
                "height": hd_h,
                "mode": inv["mode"],
                "category": inv["category"],
            },
            "stock_runtime_descriptor": {
                "descriptor_index": desc["descriptor_index"],
                "resource_handle": desc["resource_handle"],
                "cell": desc["cell"],
                "base_code": desc["base_code"],
                "letter_spacing": desc["letter_spacing"],
                "stock_dds_size": desc["dds_size"],
                "stock_dds_format": desc["dds_format"],
            },
            "inventory_to_stock_dimension_ratio": [
                hd_w / stock_w,
                hd_h / stock_h,
            ],
            "static_crosswalk": "PASS",
            "candidate_generation": "BLOCKED_PENDING_RUNTIME_FONT_HANDLE_USAGE",
        })

    out["conclusion"] = {
        "static_identity_complete": True,
        "safe_repurpose_inferred_from_static_data": False,
        "required_next": (
            "Collect KoreanK3Trace font-state usage for the relevant screens and "
            "prove which resource handle/descriptor may be switched without "
            "damaging stock ASCII rendering. Do not generate a replacement DDS "
            "from this static crosswalk alone."
        ),
        "runtime_validation": "UNTESTED",
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
