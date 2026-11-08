"""Blender 4.5.x standalone geometry QA: smoke never counts as a Ferrari rework."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "audit"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--input", default="")
    return parser.parse_args(argv)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_smoke_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # A test primitive only; deliberately NOT a vehicle-modeling deliverable.
    bpy.ops.mesh.primitive_cube_add(size=2)
    ob = bpy.context.object
    ob.name = "TOOLCHAIN_TEST_CUBE_NOT_A_FERRARI"
    ob.scale = (1.8, 0.8, 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = ob.modifiers.new("CI_BEVEL_PROBE", "BEVEL")
    bevel.width = 0.06
    bevel.segments = 2


def audit_meshes():
    result = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        tiny_faces = sum(1 for face in mesh.polygons if face.area <= 1e-12)
        result.append({
            "object": obj.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "faces": len(mesh.polygons),
            "triangles": len(mesh.loop_triangles),
            "zero_area_faces": tiny_faces,
            "wireframe_visible": False,
        })
    if not result or sum(item["faces"] for item in result) == 0:
        raise RuntimeError("GEOMETRY_GATE_FAILED: no faces in loaded scene")
    return result


def scene_bounds():
    pts = [obj.matrix_world @ Vector(corner)
           for obj in bpy.context.scene.objects if obj.type == "MESH"
           for corner in obj.bound_box]
    if not pts:
        raise RuntimeError("no scene bounding points")
    low = Vector([min(p[i] for p in pts) for i in range(3)])
    high = Vector([max(p[i] for p in pts) for i in range(3)])
    return low, high


def save_views(out, low, high):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 2
    scene.render.resolution_x = 320
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("GEOMETRY_QA_WORLD") if scene.world is None else scene.world
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.7, 0.7, 0.7, 1)
        background.inputs["Strength"].default_value = 1
    center = (low + high) * 0.5
    extent = max((high - low).length, 0.01)
    cam_data = bpy.data.cameras.new("GEOMETRY_QA_ORTHO")
    cam = bpy.data.objects.new("GEOMETRY_QA_ORTHO", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = extent * 1.4
    # Axis assumptions are labeled: actual car orientation must be recorded separately.
    directions = [
        ("front_assumed_minus_y", (0, -1, 0)),
        ("rear_assumed_plus_y", (0, 1, 0)),
        ("left_assumed_minus_x", (-1, 0, 0)),
        ("right_assumed_plus_x", (1, 0, 0)),
        ("top_plus_z", (0, 0, 1)),
        ("cockpit_diagonal", (1, -1, 1)),
    ]
    for label, xyz in directions:
        direction = Vector(xyz).normalized()
        cam.location = center + direction * extent * 2.5
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(out / (label + ".png"))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def main():
    args = cli()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == "smoke":
        make_smoke_scene()
    elif not args.input or not Path(args.input).is_file():
        raise RuntimeError("BLOCKED_INPUT: audit requires real scene loaded by Blender")
    meshes = audit_meshes()
    low, high = scene_bounds()
    if min((high - low)) < 0:
        raise RuntimeError("invalid bounding box")
    save_views(out, low, high)
    scene_file = out / "geometry_audited.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file), compress=True)
    report = {
        "mode": args.mode,
        "claim_scope": "TOOLCHAIN_ONLY_NOT_FERRARI" if args.mode == "smoke" else "SCENE_GEOMETRY_AUDIT_NOT_PHOTO_OR_RUNTIME_VALIDATION",
        "blender": bpy.app.version_string,
        "source_blend": args.input if args.mode == "audit" else None,
        "source_sha256": digest(args.input) if args.mode == "audit" else None,
        "output_blend_sha256": digest(scene_file),
        "bounds_low": list(low),
        "bounds_high": list(high),
        "objects": meshes,
        "total_vertices": sum(x["vertices"] for x in meshes),
        "total_faces": sum(x["faces"] for x in meshes),
        "total_zero_area_faces": sum(x["zero_area_faces"] for x in meshes),
        "photos_compared": False,
        "original_game_runtime_tested": False,
    }
    (out / "geometry_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
