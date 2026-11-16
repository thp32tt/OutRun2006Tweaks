#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--sourceio-parent", type=Path, required=True)
    p.add_argument("--content-root", type=Path, required=True)
    p.add_argument("--mdl", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--car-id", required=True)
    p.add_argument("--vehicle-name", required=True)
    p.add_argument("--source-repo", required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--runtime-id", type=int, required=True)
    return p.parse_args(raw)


def bounds_for(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def scene_bounds(meshes):
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    for obj in meshes:
        a, b = bounds_for(obj)
        for i in range(3):
            lo[i] = min(lo[i], a[i])
            hi[i] = max(hi[i], b[i])
    return lo, hi


def wheel_bones():
    aliases = {
        "lf": ("wheel_fl", "wheel_lf", "wheel_front_left", "wheel_left_front"),
        "rf": ("wheel_fr", "wheel_rf", "wheel_front_right", "wheel_right_front"),
        "lr": ("wheel_rl", "wheel_lr", "wheel_rear_left", "wheel_left_rear"),
        "rr": ("wheel_rr", "wheel_rear_right", "wheel_right_rear"),
    }
    out = {}
    for arm in [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]:
        for bone in arm.data.bones:
            n = bone.name.lower()
            role = next((r for r, names in aliases.items() if n in names or any(x in n for x in names)), None)
            if role and role not in out:
                out[role] = arm.matrix_world @ bone.head_local
    return out


def main():
    ns = args()
    ns.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ns.sourceio_parent.resolve()))

    import SourceIO
    from SourceIO.blender_bindings.bindings import register as sourceio_register

    sourceio_register()
    print("SOURCEIO_IMPORTED", getattr(SourceIO, "bl_info", {}).get("version"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Factory reset can remove classes, so register once more.
    try:
        sourceio_register()
    except Exception:
        pass

    mdl = ns.mdl.resolve()
    if not mdl.is_file():
        raise RuntimeError(f"MDL missing: {mdl}")

    result = bpy.ops.sourceio.mdl(
        filepath=str(mdl),
        directory=str(mdl.parent),
        files=[{"name": mdl.name}],
        discover_resources=True,
        scale=0.0254,
        import_physics=False,
        import_textures=True,
        bodygroup_grouping=True,
        bodygroup_vis_switches=True,
        import_animations=False,
        import_include_animations=False,
        create_flex_drivers=False,
        generate_wrinkle_map_node_group=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"SourceIO MDL import failed: {result}")

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_get()]
    if not meshes:
        raise RuntimeError("No visible mesh objects imported")

    before_lo, before_hi = scene_bounds(meshes)
    before_dims = before_hi - before_lo
    wheels = wheel_bones()

    # Source 1 vehicle convention is +X forward, +Y left, +Z up.
    # Prefer explicit wheel bones when available; otherwise keep that canonical convention.
    current_forward = Vector((1.0, 0.0, 0.0))
    center = (before_lo + before_hi) * 0.5
    ground = before_lo.z
    alignment = {"wheel_bones_found": sorted(wheels.keys()), "source_convention": "+X forward,+Y left,+Z up"}

    if all(k in wheels for k in ("lf", "rf", "lr", "rr")):
        front = (wheels["lf"] + wheels["rf"]) * 0.5
        rear = (wheels["lr"] + wheels["rr"]) * 0.5
        current_forward = front - rear
        current_forward.z = 0
        if current_forward.length < 0.5:
            raise RuntimeError("Wheel-bone axle separation too small")
        axle_center = (front + rear) * 0.5
        center.x, center.y = axle_center.x, axle_center.y
        alignment.update({
            "front_axle_center": list(front),
            "rear_axle_center": list(rear),
            "axle_center": list(axle_center),
            "wheel_forward_vector": list(current_forward),
        })

    current_angle = math.atan2(current_forward.y, current_forward.x)
    target_angle = -math.pi / 2.0  # Blender -Y -> glTF +Z
    yaw = target_angle - current_angle

    roots = [o for o in bpy.context.scene.objects if o.parent is None]
    if not roots:
        raise RuntimeError("Imported scene has no roots")
    transform = (
        Matrix.Translation((0.0, 0.0, -ground))
        @ Matrix.Rotation(yaw, 4, "Z")
        @ Matrix.Translation((-center.x, -center.y, 0.0))
    )
    for root in roots:
        root.matrix_world = transform @ root.matrix_world

    after_lo, after_hi = scene_bounds(meshes)
    dims = after_hi - after_lo
    width, length, height = float(dims.x), float(dims.y), float(dims.z)
    print("SOURCEIO_BOUNDS", json.dumps({
        "before": [list(before_lo), list(before_hi)],
        "after": [list(after_lo), list(after_hi)],
        "dimensions_width_length_height": [width, length, height],
        "yaw": yaw,
        **alignment,
    }))

    if not (1.2 <= width <= 2.6):
        raise RuntimeError(f"vehicle width invalid after normalization: {width:.3f}")
    if not (3.0 <= length <= 6.0):
        raise RuntimeError(f"vehicle length invalid after normalization: {length:.3f}")
    if not (0.7 <= height <= 2.2):
        raise RuntimeError(f"vehicle height invalid after normalization: {height:.3f}")
    if after_lo.z < -0.04 or after_lo.z > 0.10:
        raise RuntimeError(f"vehicle ground contact invalid: minZ={after_lo.z:.4f}")

    vertices = triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        vertices += len(obj.data.vertices)
        triangles += len(obj.data.loop_triangles)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "EMPTY", "ARMATURE"} and not obj.hide_get():
            obj.select_set(True)

    glb = ns.output / "source.glb"
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
        raise RuntimeError("GLB export failed")

    manifest = {
        "schema": 1,
        "car_id": ns.car_id,
        "runtime_id": ns.runtime_id,
        "vehicle_name": ns.vehicle_name,
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
        "rights_note": "PRIVATE_TEST_ONLY; public repository redistribution exists but upstream 3D model is credited to Turn 10; no public redistribution permission asserted",
        "redistribution_verified": False,
        "source_repo": ns.source_repo,
        "source_repo_commit": ns.source_commit,
        "selected_mdl": str(mdl.relative_to(ns.content_root.resolve())),
        "selected_mdl_sha256": sha256(mdl),
        "converter": "REDxEYE/SourceIO 6.0.0 + Blender 5.2.4",
        "normalization": {
            **alignment,
            "yaw_radians": yaw,
            "before_bounds_blender_zup": [list(before_lo), list(before_hi)],
            "after_bounds_blender_zup": [list(after_lo), list(after_hi)],
            "dimensions_m_width_length_height": [width, length, height],
            "glb_expected_axes": {"right": "+X", "up": "+Y", "forward": "+Z"},
        },
        "mesh_stats": {
            "visible_mesh_objects": len(meshes),
            "vertices": vertices,
            "triangles": triangles,
            "materials": len(bpy.data.materials),
            "images": len(bpy.data.images),
        },
        "blender_version": bpy.app.version_string,
    }
    (ns.output / "source.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SOURCEIO_CONVERSION_SUMMARY", json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
