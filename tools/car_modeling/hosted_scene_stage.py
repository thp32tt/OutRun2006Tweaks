#!/usr/bin/env python3
"""Blender stage for public GitHub VM; all source assets reside privately on runner.

Probe inventories actual current PMT-derived meshes without claiming a new model.
Edit applies an explicitly scoped Blender apply(bpy) function to existing meshes.
The stage never exports OVC/OVC3/PMT/GLB or publishes source .blend/real photos.
"""
import argparse
import array
import hashlib
import json
from pathlib import Path
import runpy
import sys

import bpy


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda: f.read(1024*1024), b""):
            h.update(data)
    return h.hexdigest()


def snapshot():
    records = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        h = hashlib.sha256()
        for row in obj.matrix_world:
            h.update(array.array("d", map(float, row)).tobytes())
        verts = array.array("f", [0.0]) * (3*len(mesh.vertices))
        mesh.vertices.foreach_get("co", verts)
        h.update(verts.tobytes())
        loops = array.array("i", [0]) * len(mesh.loops)
        mesh.loops.foreach_get("vertex_index", loops)
        h.update(loops.tobytes())
        for layer in mesh.uv_layers:
            uv = array.array("f", [0.0]) * (2 * len(layer.data))
            layer.data.foreach_get("uv", uv)
            h.update(layer.name.encode())
            h.update(uv.tobytes())
        h.update("|".join(m.name if m else "" for m in mesh.materials).encode())
        records[obj.name] = {
            "fingerprint": h.hexdigest(),
            "verts": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "source_object_id": str(obj.get("outrun_original_mesh_object_id") or ""),
        }
    return records


def path_below(root, relative):
    p = (root / relative).resolve()
    if p == root or not p.is_relative_to(root):
        raise RuntimeError("BLOCKED_PATH: asset escape")
    return p


def main():
    v = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("probe", "edit", "verify"), required=True)
    p.add_argument("--slot", choices=("A", "C"), required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--root", required=True)
    args = p.parse_args(v)
    root = Path(args.root).resolve()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if spec.get("slot") != args.slot:
        raise RuntimeError("BLOCKED_SLOT: different Ferrari cockpit owner")
    orig = path_below(root, spec["original_native_rel"])
    imported = path_below(root, spec["original_import_blend_rel"])
    source = path_below(root, spec["source_blend_rel"])
    output = path_below(root, spec["output_blend_rel"])
    receipt = path_below(root, spec["receipt_rel"])
    for file, expected in (
        (orig, spec["original_sha256"]),
        (imported, spec["original_import_sha256"]),
        (source, spec["source_sha256"]),
    ):
        if not file.is_file() or sha(file) != expected:
            raise RuntimeError("BLOCKED_SOURCE_SHA: original game resource/import/latest .blend")
    desired = source if args.stage != "verify" else output
    if Path(bpy.data.filepath).resolve() != desired:
        raise RuntimeError("BLOCKED_SCENE: wrong source-bound Blender file")
    before = snapshot()
    if not before:
        raise RuntimeError("BLOCKED_SCENE: no native Blender mesh")
    if args.stage == "probe":
        receipt.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "status": "SOURCE_SCENE_OPENED_ONLY_NO_MODEL_EDIT",
            "slot": args.slot, "part": spec["component"],
            "source_scene_sha256": sha(source),
            "original_native_sha256": sha(orig),
            "source_object_inventory": before,
            "model_changed": False,
            "whole_car_qa_pass": False,
            "ovc_exported": False,
        }
        receipt.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("FERRARI_HOSTED_ORIGINAL_SCENE_PROBE_PASS")
        return
    if args.stage == "edit":
        if output.exists():
            raise RuntimeError("BLOCKED_OUTPUT: refuse overwrite of immutable .blend")
        allowed = set(spec.get("allowed_existing_meshes") or [])
        script = Path(spec.get("edit_script") or "").resolve()
        project = Path(args.spec).resolve().parents[3]
        if not allowed or not script.is_relative_to(project / "tools/car_modeling/hosted_edits"):
            raise RuntimeError("BLOCKED_SCOPE: explicit original mesh list and hosted edit script required")
        if not script.is_file() or script.suffix != ".py":
            raise RuntimeError("BLOCKED_SCRIPT: missing trusted source edit")
        namespace = runpy.run_path(str(script), run_name="__ferrari_hosted_edit__")
        fn = namespace.get("apply")
        if not callable(fn):
            raise RuntimeError("BLOCKED_SCRIPT: define apply(bpy) editing EXISTING native objects")
        fn(bpy)
        after = snapshot()
        if before.keys() != after.keys():
            raise RuntimeError("BLOCKED_MODEL: new/deleted car objects prohibited")
        changed = [k for k in before if before[k] != after[k]]
        if not changed or not set(changed).issubset(allowed):
            raise RuntimeError("BLOCKED_SCOPE: edited wrong region or no genuine source changes")
        # Object provenance must pre-exist: a new synthesized replacement is forbidden.
        for name in changed:
            if (not before[name]["source_object_id"]
                    and not name.startswith(("V5_", "V8_", "PMT_"))):
                raise RuntimeError("BLOCKED_PROVENANCE: missing original-mesh lineage")
        output.parent.mkdir(parents=True, exist_ok=True)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
        receipt.write_text(json.dumps({
            "status": "SOURCE_NATIVE_GEOMETRY_EDIT_FRESH_REOPEN_PENDING",
            "slot": args.slot, "part": spec["component"],
            "input_blend_sha256": sha(source), "output_blend_sha256": sha(output),
            "original_native_sha256": sha(orig),
            "changed_existing_meshes": changed,
            "protected_meshes_unchanged": len(before)-len(changed),
            "before_meshes": before, "after_meshes": after,
            "whole_car_qa_pass": False, "ovc_exported": False,
        }, indent=2), encoding="utf-8")
        print("FERRARI_HOSTED_SOURCE_NATIVE_EDIT_SAVED", len(changed))
        return
    if not receipt.is_file() or not output.is_file():
        raise RuntimeError("BLOCKED_VERIFY: independent reopen source/receipt absent")
    prior = json.loads(receipt.read_text())
    if (prior["output_blend_sha256"] != sha(output)
            or snapshot() != prior["after_meshes"]):
        raise RuntimeError("BLOCKED_VERIFY: edited .blend failed independent mesh SHA check")
    prior["status"] = "SOURCE_NATIVE_EDIT_FRESH_BLENDER_REOPEN_PASS_NOT_WHOLE_CAR_QA"
    receipt.write_text(json.dumps(prior, indent=2), encoding="utf-8")
    print("FERRARI_HOSTED_SOURCE_NATIVE_INDEPENDENT_REOPEN_PASS")


if __name__ == "__main__":
    main()
