#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Matrix, Vector


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--source-audit", type=Path, required=True)
    p.add_argument("--kn5-tools", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args(argv)


def mesh_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return mins, maxs


def scene_mesh_bounds(meshes):
    mins = Vector((1e30, 1e30, 1e30))
    maxs = Vector((-1e30, -1e30, -1e30))
    for obj in meshes:
        lo, hi = mesh_bounds(obj)
        for i in range(3):
            mins[i] = min(mins[i], lo[i])
            maxs[i] = max(maxs[i], hi[i])
    return mins, maxs


def wheel_role(name: str):
    n = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not any(token in n for token in ("wheel", "tyre", "tire", "rim")):
        return None
    tokens = set(n.split("_"))
    for role in ("lf", "rf", "lr", "rr"):
        if role in tokens or n.endswith(role) or f"_{role}_" in f"_{n}_":
            return role
    aliases = {
        "lf": ("front_left", "left_front"),
        "rf": ("front_right", "right_front"),
        "lr": ("rear_left", "left_rear"),
        "rr": ("rear_right", "right_rear"),
    }
    for role, names in aliases.items():
        if any(alias in n for alias in names):
            return role
    return None


def wheel_candidates(meshes):
    result = {}
    for obj in meshes:
        role = wheel_role(obj.name)
        if not role:
            original = str(obj.get("kn5_original_name", ""))
            role = wheel_role(original)
        if not role:
            continue
        lo, hi = mesh_bounds(obj)
        center = (lo + hi) * 0.5
        score = (hi - lo).length
        existing = result.get(role)
        if existing is None or score > existing["score"]:
            result[role] = {"object": obj, "center": center, "lo": lo, "hi": hi, "score": score}
    return result


def choose_kn5(car_root: Path, kn5_pkg):
    try:
        lods = kn5_pkg.ac_folders.car_lods(car_root)
        if lods:
            return Path(lods[0].path), [str(x.path) for x in lods], "car_lods.ini_or_main"
    except Exception as exc:
        print("LOD discovery warning:", exc)
    files = [p for p in car_root.rglob("*.kn5") if p.is_file()]
    visual = []
    for p in files:
        n = p.stem.lower()
        if n in {"collider", "collision"} or "collider" in n or "collision" in n:
            continue
        if re.search(r"(?:^|[_-])lod[_-]?[bcd](?:$|[_-])", n):
            continue
        visual.append(p)
    if not visual:
        visual = files
    if not visual:
        raise RuntimeError("No KN5 candidate found")
    visual.sort(key=lambda p: p.stat().st_size, reverse=True)
    return visual[0], [str(p) for p in visual], "largest_non_collision_non_low_lod"


def main():
    ns = parse_args()
    audit = json.loads(ns.source_audit.read_text(encoding="utf-8"))
    rights = audit["rights"]
    if not rights.get("private_conversion_allowed"):
        raise RuntimeError("Source rights audit did not allow private conversion")

    car_root = Path(audit["car_root"]).resolve()
    output = ns.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(ns.kn5_tools.resolve()))
    kn5_pkg = importlib.import_module("kn5_blender_tools")
    kn5_pkg.register()
    ac_folders = importlib.import_module("kn5_blender_tools.ac_folders")
    kn5_pkg.ac_folders = ac_folders

    source_kn5, lod_candidates, lod_method = choose_kn5(car_root, kn5_pkg)
    print("SELECTED_KN5", source_kn5)
    print("LOD_METHOD", lod_method)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Factory reset unregisters regular runtime classes; register again.
    try:
        kn5_pkg.unregister()
    except Exception:
        pass
    kn5_pkg.register()

    result = bpy.ops.import_scene.assetto_corsa_kn5(
        filepath=str(source_kn5),
        import_textures=True,
        import_materials=True,
        import_hidden=False,
        scale=1.0,
        organize_meshes=False,
        clean_mesh_names=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"KN5 import failed: {result}")

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("KN5 import produced no mesh objects")

    before_min, before_max = scene_mesh_bounds(meshes)
    wheels = wheel_candidates(meshes)
    alignment = {
        "wheel_roles_found": sorted(wheels.keys()),
        "before_bounds_blender_zup": [list(before_min), list(before_max)],
    }

    center_x = (before_min.x + before_max.x) * 0.5
    center_y = (before_min.y + before_max.y) * 0.5
    ground_z = before_min.z
    yaw = 0.0
    axle_center = None

    if all(role in wheels for role in ("lf", "rf", "lr", "rr")):
        front = (wheels["lf"]["center"] + wheels["rf"]["center"]) * 0.5
        rear = (wheels["lr"]["center"] + wheels["rr"]["center"]) * 0.5
        axle_center = (front + rear) * 0.5
        forward = front - rear
        if math.hypot(forward.x, forward.y) < 0.5:
            raise RuntimeError("Wheel axle separation is too small to establish vehicle forward axis")
        current_angle = math.atan2(forward.y, forward.x)
        target_angle = -math.pi / 2.0  # Blender -Y -> glTF +Z after Y-up export.
        yaw = target_angle - current_angle
        center_x, center_y = axle_center.x, axle_center.y
        ground_z = min(wheels[role]["lo"].z for role in ("lf", "rf", "lr", "rr"))
        alignment.update({
            "front_axle_center": list(front),
            "rear_axle_center": list(rear),
            "axle_center": list(axle_center),
            "yaw_radians": yaw,
            "ground_source": "four_wheel_bbox_min_z",
        })
    else:
        alignment.update({
            "yaw_radians": 0.0,
            "ground_source": "whole_vehicle_bbox_min_z_fallback",
        })

    transform = (
        Matrix.Translation((0.0, 0.0, -ground_z))
        @ Matrix.Rotation(yaw, 4, "Z")
        @ Matrix.Translation((-center_x, -center_y, 0.0))
    )
    roots = [o for o in bpy.context.scene.objects if o.parent is None]
    if not roots:
        raise RuntimeError("Imported model has no root object")
    for obj in roots:
        obj.matrix_world = transform @ obj.matrix_world

    after_min, after_max = scene_mesh_bounds(meshes)
    dims = after_max - after_min
    width, length, height = dims.x, dims.y, dims.z
    if not (1.20 <= width <= 2.50):
        raise RuntimeError(f"Normalized vehicle width out of range: {width:.3f}m")
    if not (3.00 <= length <= 6.00):
        raise RuntimeError(f"Normalized vehicle length out of range: {length:.3f}m")
    if not (0.70 <= height <= 2.20):
        raise RuntimeError(f"Normalized vehicle height out of range: {height:.3f}m")
    if after_min.z < -0.03:
        raise RuntimeError(f"Vehicle still below ground after normalization: minZ={after_min.z:.4f}")
    if after_min.z > 0.08:
        raise RuntimeError(f"Vehicle floats too high after normalization: minZ={after_min.z:.4f}")

    total_vertices = 0
    total_triangles = 0
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        total_vertices += len(mesh.vertices)
        total_triangles += len(mesh.loop_triangles)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        obj.select_set(True)

    glb = output / "source.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_animations=False,
        export_skins=False,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_extras=True,
    )
    if not glb.is_file() or glb.stat().st_size < 1024:
        raise RuntimeError("GLB export missing or unexpectedly small")

    # Blender Z-up -> glTF Y-up maps the normalized Blender -Y forward axis to +Z.
    source_manifest = {
        "schema": 1,
        "car_id": "dino246gts",
        "vehicle_name": "Dino 246 GTS",
        "source_sha256": sha256(glb),
        "geometry_space": "outrun_local_y_up_meters",
        "alignment_verified": True,
        "model_scope": "full_car",
        "origin_type": "external_mod",
        "external_to_game_matrix": [
            1,0,0,0,
            0,1,0,0,
            0,0,1,0,
            0,0,0,1,
        ],
        "rights_note": rights.get("rights_note", "PRIVATE_TEST_ONLY_NO_REDISTRIBUTION_ASSERTION"),
        "redistribution_verified": False,
        "selected_kn5": str(source_kn5.relative_to(car_root)) if source_kn5.is_relative_to(car_root) else source_kn5.name,
        "selected_kn5_sha256": sha256(source_kn5),
        "lod_selection_method": lod_method,
        "lod_candidates": lod_candidates,
        "normalization": {
            **alignment,
            "after_bounds_blender_zup": [list(after_min), list(after_max)],
            "dimensions_m_blender_width_length_height": [width, length, height],
            "glb_expected_axes": {"right": "+X", "up": "+Y", "forward": "+Z"},
            "ground_contact_expected_y_m": 0.0,
        },
        "mesh_stats": {
            "mesh_objects": len(meshes),
            "vertices": total_vertices,
            "triangles": total_triangles,
            "materials": len(bpy.data.materials),
            "images": len(bpy.data.images),
        },
        "blender_version": bpy.app.version_string,
        "kn5_tools_source": "nazariyKul/kn5-blender-tools@502ab4861dd3f324a794db5874c0f8237dbeaa79",
    }
    (output / "source.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("DINO_CONVERT_SUMMARY", json.dumps(source_manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
