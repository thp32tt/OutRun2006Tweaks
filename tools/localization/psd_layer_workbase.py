#!/usr/bin/env python3
"""Source-pinned PSD layer inventory and reversible CLEAN/English layer workbase.

This tool does not approve a CLEAN plate, replace a DDS, or claim matching artwork.
Use only known layer paths verified against the canonical native DDS.
Requires: psd-tools[composite], Pillow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def walk(group, parent: str = ""):
    for i, layer in enumerate(group):
        path = f"{parent}/{i}" if parent else str(i)
        yield path, layer
        if layer.is_group():
            yield from walk(layer, path)


def parse_paths(value: str) -> set[str]:
    result = {s.strip() for s in value.split(",") if s.strip()}
    for p in result:
        if any(not section.isdigit() for section in p.split("/")):
            raise ValueError(f"Invalid numeric layer path: {p}")
    return result


def full_canvas(psd: PSDImage, include=None) -> Image.Image:
    if include is None:
        # Force re-render of layers, rather than the potentially stale merged preview.
        image = psd.composite(viewport=(0, 0, psd.width, psd.height), force=True)
    else:
        image = psd.composite(
            viewport=(0, 0, psd.width, psd.height),
            force=True,
            layer_filter=include,
        )
    if image is None:
        return Image.new("RGBA", (psd.width, psd.height))
    return image.convert("RGBA")


def save_once(img: Image.Image, path: Path) -> str:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    img.save(path, format="PNG")
    return sha256(path)


def run(args) -> dict:
    path = args.psd.resolve(strict=True)
    psd_hash = sha256(path)
    if args.psd_sha256 and psd_hash != args.psd_sha256.lower():
        raise ValueError("Pinned PSD SHA256 mismatch")
    psd = PSDImage.open(path)
    layers = list(walk(psd))
    indexes = {p: layer for p, layer in layers}
    info = []
    for p, layer in layers:
        bounds = list(layer.bbox)
        info.append({
            "path": p, "name": layer.name, "kind": layer.kind,
            "group": bool(layer.is_group()), "visible": bool(layer.is_visible()),
            "bbox": bounds, "opacity": int(layer.opacity),
        })
    output = {
        "schema": "outrun-psd-source-workbase-v1",
        "input_file": path.name,
        "source_upstream": args.upstream_url or None,
        "source_commit": args.upstream_commit or None,
        "psd_sha256": psd_hash,
        "size": [psd.width, psd.height],
        "mode": args.command,
        "layers": info,
        "canonical_dds_status": "NOT_TESTED",
        "clean_plate_status": "EXTRACTED_UNVERIFIED" if args.command == "export" else "NOT_EXTRACTED",
        "english_layer_status": "EXTRACTED_UNVERIFIED" if args.command == "export" else "NOT_EXTRACTED",
        "C2_PLATE_PASS": False,
        "C3_PASS": False,
        "RUNTIME_VALIDATION": "UNTESTED",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    if args.command == "separate":
        all_nodes = {id(layer): p for p, layer in layers}
        outputs = {}
        outputs["english_original_full.png"] = save_once(
            full_canvas(psd), args.output / "english_original_full.png")
        folder = args.output / "separated_layers"
        folder.mkdir(exist_ok=True)
        for p, layer in layers:
            if layer.is_group():
                continue
            # A selected leaf requires its ancestor groups to remain compositable.
            selected = lambda node, leaf=p: node.is_visible() and (
                all_nodes.get(id(node), "") == leaf
                or leaf.startswith(all_nodes.get(id(node), "") + "/")
            )
            image = full_canvas(psd, selected)
            file_name = "layer_" + p.replace("/", "_") + ".png"
            outputs["separated_layers/" + file_name] = save_once(
                image, folder / file_name)
        output["output_sha256"] = outputs
        output["layer_split_status"] = "EXTRACTED_UNCLASSIFIED"
        output["warning"] = (
            "Original English composite and individual layers were exported. "
            "No CLEAN or English-layer classification until named layer paths "
            "are independently reviewed against the exact canonical DDS."
        )
    if args.command == "export":
        english = parse_paths(args.english_layers)
        if not english:
            raise ValueError("Explicit --english-layers is required; auto-detection cannot approve a plate")
        missing = english.difference(indexes)
        if missing:
            raise ValueError(f"Unknown layer paths: {sorted(missing)}")
        if any(indexes[p].is_group() for p in english):
            raise ValueError("Select individual English glyph/effect layers, not ambiguous groups")
        all_nodes = {id(layer): p for p, layer in layers}
        def selected(layer):
            p = all_nodes.get(id(layer), "")
            # Keep ancestor groups, render only the selected descendants.
            return layer.is_visible() and (p in english or any(t.startswith(p + "/") for t in english))
        def clean(layer):
            p = all_nodes.get(id(layer), "")
            return layer.is_visible() and p not in english
        # Both images are derived from the SAME original PSD and same compositing model.
        original = full_canvas(psd)
        plate = full_canvas(psd, clean)
        letters = full_canvas(psd, selected)
        out = {}
        out["english_original_full.png"] = save_once(original, args.output / "english_original_full.png")
        out["clean_plate_candidate.png"] = save_once(plate, args.output / "clean_plate_candidate.png")
        out["english_letter_layers.png"] = save_once(letters, args.output / "english_letter_layers.png")
        if args.explode:
            layer_dir = args.output / "layers"
            layer_dir.mkdir(exist_ok=True)
            for p, layer in layers:
                if layer.is_group():
                    continue
                single = full_canvas(psd, lambda current, selected=id(layer): current.is_visible() and id(current) == selected)
                name = "layer_" + p.replace("/", "_") + ".png"
                out["layers/" + name] = save_once(single, layer_dir / name)
        output["english_layer_paths"] = sorted(english)
        output["output_sha256"] = out
        output["warning"] = (
            "PSD may contain pre-baked English or missing Photoshop effects. "
            "Compare with exact SHA-pinned canonical DDS at native RAW/readable orientation, "
            "check protected art and residue, then obtain independent C2 PLATE_PASS."
        )
    manifest = args.output / ("psd_layer_export.json" if args.command == "export" else (
        "psd_layer_separated.json" if args.command == "separate" else "psd_layer_inventory.json"
    ))
    if manifest.exists():
        raise FileExistsError(f"Refusing to overwrite: {manifest}")
    manifest.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"manifest": str(manifest), "layer_count": len(layers), "psd_sha256": psd_hash, "status": output["clean_plate_status"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for command in ("inventory", "separate", "export"):
        p = sub.add_parser(command)
        p.add_argument("--psd", required=True, type=Path)
        p.add_argument("--psd-sha256", default="")
        p.add_argument("--upstream-url", default="")
        p.add_argument("--upstream-commit", default="")
        p.add_argument("--output", required=True, type=Path)
        if command == "export":
            p.add_argument("--english-layers", required=True, help="Comma-separated numeric paths, e.g. 0/1,0/3")
            p.add_argument("--explode", action="store_true")
    print(json.dumps(run(ap.parse_args()), ensure_ascii=False))


if __name__ == "__main__":
    main()
