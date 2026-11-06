#!/usr/bin/env python3
"""Build a separate Dino cockpit experiment from verified native PMT groups."""
import argparse
from collections import Counter
import hashlib
import io
from pathlib import Path

from PIL import Image

from dino_cockpit_hdgeometry_v1 import Mesh, write_ovc
from dino_original_pmt_to_glb import build_glb, decode_dds, decode_object, open_pmt


# Player Dino object 0: seats, instrument face, radio/control panel.
GROUPS = {19: 19, 22: 15, 27: 17}
TRIM_COLOR = (24, 25, 26, 255)


def instrument_trim(panel):
    vertices = panel["vertices"]
    faces = panel["indices"]
    if max(v[2] for v in vertices) - min(v[2] for v in vertices) > 0.0001:
        raise ValueError("instrument face is not planar in native XY")
    edges = [(vertices[faces[i + a]], vertices[faces[i + b]])
             for i in range(0, len(faces), 3) for a, b in ((0, 1), (1, 2), (2, 0))]
    counts = Counter(tuple(sorted(edge)) for edge in edges)
    boundary = [edge for edge in edges if counts[tuple(sorted(edge))] == 1]
    degree = Counter(vertex for edge in boundary for vertex in edge)
    if not boundary or any(count != 2 for count in degree.values()) or max(counts.values()) > 2:
        raise ValueError("instrument perimeter is not a closed manifold boundary")
    cx, cy = [(min(axis) + max(axis)) / 2 for axis in list(zip(*vertices))[:2]]

    def outer(vertex, depth):
        x, y, z = vertex
        return (cx + (x - cx) * 1.035, cy + (y - cy) * 1.075, z + depth)

    trim = {"name": "authored_instrument_perimeter_trim", "object": 0,
            "tex_index": None, "color": [channel / 255 for channel in TRIM_COLOR],
            "vertices": [], "normals": [], "uvs": [], "indices": []}
    for a, b in boundary:
        oa, ob = outer(a, -0.001), outer(b, -0.001)
        for quad in ((a, b, ob, oa), (oa, ob, outer(b, -0.005), outer(a, -0.005))):
            u = [quad[1][i] - quad[0][i] for i in range(3)]
            v = [quad[2][i] - quad[0][i] for i in range(3)]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            length = sum(x*x for x in cross) ** 0.5
            if length < 1e-10:
                raise ValueError("degenerate trim surface")
            normal = tuple(x / length for x in cross)
            start = len(trim["vertices"])
            trim["vertices"].extend(quad)
            trim["normals"].extend([normal] * 4)
            trim["uvs"].extend([(0.5, 0.5)] * 4)
            trim["indices"].extend(start + index for index in (0, 1, 2, 0, 2, 3))
    return trim


def export(source, output, scale):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    asset = open_pmt(source)
    native = [part for part in decode_object(asset, 0) if part["material_group"] in GROUPS]
    actual = {part["material_group"]: part["tex_index"] for part in native}
    if len(native) != len(GROUPS) or actual != GROUPS or any(part["alpha"] for part in native):
        raise ValueError("native cockpit group identities do not match the verified Dino layout")
    panel = next(part for part in native if part["material_group"] == 22)
    trim = instrument_trim(panel)
    parts = [*native, trim]
    textures = {}
    meshes = []
    for part in parts:
        slot = part["tex_index"]
        if slot is None:
            image = Image.new("RGBA", (4, 4), TRIM_COLOR)
        else:
            png, _, _ = decode_dds(asset, slot, scale)
            with Image.open(io.BytesIO(png)) as decoded:
                image = decoded.convert("RGBA")
            if part["color"] != [1, 1, 1, 1]:
                raise ValueError("native material tint cannot be preserved by this OVC export")
        textures[part["name"]] = image
        mesh = Mesh(part["name"], part["name"])
        mesh.vertices, mesh.normals = part["vertices"], part["normals"]
        mesh.uvs, mesh.faces = part["uvs"], part["indices"]
        meshes.append(mesh)
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError("source PMT changed during export")
    output.mkdir(parents=True, exist_ok=True)
    stem = output / "Dino246_Native_Cockpit_Partial"
    build_glb(asset, parts, scale, stem.with_suffix(".glb"))
    write_ovc(meshes, textures, stem.with_suffix(".ovc"))
    return {"source_sha256": digest, "native_groups": actual,
            "native_triangles": sum(len(part["indices"]) // 3 for part in native),
            "added_trim_triangles": len(trim["indices"]) // 3,
            "runtime_validation": "UNTESTED"}


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--texture-scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    try:
        report = export(args.source, args.output, args.texture_scale)
    except (OSError, ValueError) as error:
        parser.exit(2, f"FAIL: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
