"""Executed by an explicitly selected official Blender binary, not a Python interpreter.

The output is a stage, NEVER an OutRun PMT/OVC/OVC3 game asset.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError as exc:
    raise RuntimeError("Run with Blender --background --python blender_worker.py") from exc

sys.path.insert(0, str(Path(__file__).parent))
from profiles import get_profile


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bounds(meshes):
    pts = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    if not pts:
        raise ValueError("Imported model contains no mesh objects")
    mi = [min(p[i] for p in pts) for i in range(3)]
    ma = [max(p[i] for p in pts) for i in range(3)]
    return {"min": mi, "max": ma,
            "extents": [ma[i] - mi[i] for i in range(3)],
            "center": [(ma[i] + mi[i]) / 2 for i in range(3)]}


def fingerprint(meshes):
    digest = hashlib.sha256()
    for o in sorted(meshes, key=lambda x: x.name):
        digest.update(o.name.encode("utf-8"))
        for v in o.data.vertices:
            digest.update(struct.pack("<3f", *v.co))
        for face in o.data.polygons:
            digest.update(struct.pack("<I", len(face.vertices)))
            for i in face.vertices:
                digest.update(struct.pack("<I", i))
        for row in o.matrix_world:
            for value in row:
                digest.update(struct.pack("<f", value))
    return digest.hexdigest()


def orient_camera(scene):
    cam_data = bpy.data.cameras.new("OutRun_Importer_Preview_Camera")
    cam = bpy.data.objects.new("OutRun_Importer_Preview_Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector((7.0, 3.3, 2.8))
    forward = (Vector((0, 0.45, 0)) - cam.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward).normalized()
    cam.rotation_euler = Matrix(((right.x, up.x, -forward.x),
                                 (right.y, up.y, -forward.y),
                                 (right.z, up.z, -forward.z))).to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 6.6
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    return cam


def run_stage(args):
    profile = get_profile(args.slot)
    src = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve(strict=True)
    ref = Path(args.reference_blend).resolve(strict=True) if args.reference_blend else None
    source_hash = sha256(src)
    if ref:
        reference_hash = sha256(ref)
        bpy.ops.wm.open_mainfile(filepath=str(ref))
        native_meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        if not native_meshes:
            raise ValueError("Reference Blender file has no mesh data")
        native_fingerprint = fingerprint(native_meshes)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        native_meshes = []
        native_fingerprint = None
        reference_hash = None
    scene = bpy.context.scene
    native_coll = None
    if native_meshes:
        native_coll = bpy.data.collections.new("ORIGINAL_OUTRUN_REFERENCE_UNMODIFIED")
        scene.collection.children.link(native_coll)
        for o in native_meshes:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            native_coll.objects.link(o)
        native_coll.hide_render = True
    prior = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(src))
    added = [o for o in bpy.data.objects if o not in prior]
    imported = [o for o in added if o.type == "MESH"]
    if not imported:
        raise ValueError("Blender imported zero meshes")
    ext_coll = bpy.data.collections.new("EXTERNAL_MODEL_STAGED_NOT_GAME_ASSET")
    scene.collection.children.link(ext_coll)
    for obj in added:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        ext_coll.objects.link(obj)
    roots = [o for o in added if o.parent is None]
    if not roots:
        raise ValueError("Imported glTF scene has no root nodes")
    before = bounds(imported)
    if before["extents"][1] >= before["extents"][0]:
        axis = "Y"
        rotation = Matrix.Rotation(-math.pi / 2, 4, "X")
    else:
        axis = "X"
        rotation = Matrix.Rotation(-math.pi / 2, 4, "X") @ Matrix.Rotation(math.pi / 2, 4, "Z")
    if profile.flip_front:
        rotation = Matrix.Rotation(math.pi, 4, "Y") @ rotation
    for o in roots:
        o.matrix_world = rotation @ o.matrix_world
    bpy.context.view_layer.update()
    oriented = bounds(imported)
    if oriented["extents"][2] <= 1e-8:
        raise ValueError("Car length zero after coordinate conversion")
    scale = profile.dimensions[2] / oriented["extents"][2]
    if not (0.001 <= scale <= 100_000):
        raise ValueError("Unreasonable model scale; refusing conversion")
    scaling = Matrix.Scale(scale, 4)
    for o in roots:
        o.matrix_world = scaling @ o.matrix_world
    bpy.context.view_layer.update()
    sized = bounds(imported)
    delta = Vector((profile.center[0] - sized["center"][0],
                    profile.ground_y - sized["min"][1],
                    profile.center[2] - sized["center"][2]))
    for o in roots:
        o.matrix_world = Matrix.Translation(delta) @ o.matrix_world
    bpy.context.view_layer.update()
    aligned = bounds(imported)
    if abs(aligned["extents"][2] - profile.dimensions[2]) > 0.002:
        raise ValueError("Vehicle length mismatch after alignment")
    if abs(aligned["min"][1] - profile.ground_y) > 0.002:
        raise ValueError("Vehicle ground alignment mismatch")
    if native_meshes and fingerprint(native_meshes) != native_fingerprint:
        raise ValueError("Native reference geometry was modified")
    # Export only user-supplied meshes and their imported parent nodes.
    bpy.ops.object.select_all(action="DESELECT")
    for o in added:
        o.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.export_scene.gltf(filepath=str(output / "staged_car.glb"),
                              export_format="GLB", use_selection=True)
    if not (output / "staged_car.glb").is_file():
        raise ValueError("Blender GLB export did not produce an output")
    bpy.ops.object.select_all(action="DESELECT")
    orient_camera(scene)
    if native_coll:
        native_coll.hide_render = True
    ext_coll.hide_render = False
    scene.render.filepath = str(output / "car_preview.png")
    bpy.ops.render.render(write_still=True)
    scene["car_importer_status"] = "BLENDER_STAGED_NOT_GAME_INSTALLABLE"
    scene["external_input_sha256"] = source_hash
    scene["requires_native_serializer_and_runtime_QA"] = True
    scene["reference_blend_sha256"] = reference_hash or "none"
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "staged_car.blend"), compress=True)
    if ref and sha256(ref) != reference_hash:
        raise ValueError("Reference file changed while processing")
    tri_count = sum(len(o.data.loop_triangles) for o in imported)
    report = {
        "status": "BLENDER_STAGED_NOT_GAME_INSTALLABLE",
        "profile": profile.slug,
        "source_sha256": source_hash,
        "source_file_name": src.name,
        "reference_blend_sha256": reference_hash,
        "reference_geometry_unchanged": native_fingerprint is None or fingerprint(native_meshes) == native_fingerprint,
        "reference_geometry_fingerprint": native_fingerprint,
        "external_meshes": len(imported), "external_triangles": tri_count,
        "orientation_axis_detected": axis,
        "model_scale": scale,
        "bounds_before": before,
        "bounds_after": aligned,
        "blender_sha256": sha256(output / "staged_car.blend"),
        "glb_sha256": sha256(output / "staged_car.glb"),
        "blender_version": bpy.app.version_string,
        "game_installable": False,
        "game_files_modified": False,
        "license_and_original_rights": "USER_MUST_VERIFY_INDEPENDENTLY",
    }
    (output / "stage_manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OUTRUN_CAR_STAGE_PASS " + json.dumps(report, ensure_ascii=False), flush=True)


def run_verify(args):
    """Fresh process reopen verifies derived scene without writing any file."""
    out = Path(args.output).resolve(strict=True)
    manifest = json.loads((out / "stage_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "BLENDER_STAGED_NOT_GAME_INSTALLABLE":
        raise ValueError("Invalid staging status")
    for filename, hash_field in (("staged_car.blend", "blender_sha256"), ("staged_car.glb", "glb_sha256")):
        if sha256(out / filename) != manifest[hash_field]:
            raise ValueError("Staging file hash mismatch: " + filename)
    bpy.ops.wm.open_mainfile(filepath=str(out / "staged_car.blend"))
    coll = bpy.data.collections.get("EXTERNAL_MODEL_STAGED_NOT_GAME_ASSET")
    if not coll:
        raise ValueError("Staged Blender file lacks external mesh collection")
    meshes = [o for o in coll.objects if o.type == "MESH"]
    if len(meshes) != manifest["external_meshes"]:
        raise ValueError("Staged mesh count mismatch")
    if bpy.context.scene.get("car_importer_status") != manifest["status"]:
        raise ValueError("Blender checkpoint status mismatch")
    print("OUTRUN_CAR_INDEPENDENT_REOPEN_PASS meshes=" + str(len(meshes)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--slot", default="f50")
    parser.add_argument("--reference-blend")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.verify:
        run_verify(args)
    else:
        if not args.input:
            raise ValueError("Missing --input GLB path")
        run_stage(args)


if __name__ == "__main__":
    main()