#!/usr/bin/env python3
"""Inventory every static object in a read-only Dino PMT."""
import argparse
import hashlib
import json
from pathlib import Path

from dino_original_pmt_to_glb import decode_object, open_pmt


def inventory(path):
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    asset = open_pmt(path)
    objects = []
    for index in range(asset["obj_count"]):
        groups = []
        for part in decode_object(asset, index):
            vertices = part["vertices"]
            low = [min(axis) for axis in zip(*vertices)]
            high = [max(axis) for axis in zip(*vertices)]
            groups.append({
                "name": part["name"], "group": part["group"],
                "material_group": part["material_group"], "texture": part["tex_index"],
                "alpha_pass": bool(part["alpha"]), "vertices": len(vertices),
                "triangles": len(part["indices"]) // 3,
                "bounds_min": low, "bounds_max": high,
                "bounds_center": [(a + b) / 2 for a, b in zip(low, high)],
            })
        objects.append({"object": index, "groups": groups})
    if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha:
        raise ValueError("source changed during inventory")
    return {"sha256": source_sha, "texture_count": asset["tex_count"],
            "coordinate_space": "decoded PMT object-local, native units",
            "bounds_center_role": "geometric candidate only, not a measured pivot",
            "objects": objects}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.source), indent=2))


if __name__ == "__main__":
    main()
