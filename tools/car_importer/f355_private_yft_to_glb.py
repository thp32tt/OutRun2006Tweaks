import bpy
import json
import os
from pathlib import Path

stream = Path(os.environ["F355_STREAM"]).resolve()
outdir = Path(os.environ["F355_OUTPUT"]).resolve()
outdir.mkdir(parents=True, exist_ok=True)

if not hasattr(bpy.types.Object, "sollum_type"):
    raise RuntimeError("Sollumz is not fully registered")
try:
    bpy.ops.sollumz.import_assets.get_rna_type()
except Exception as exc:
    raise RuntimeError("Sollumz import_assets operator unavailable") from exc

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

result = bpy.ops.sollumz.import_assets(
    directory=str(stream),
    files=[
        {"name": "f355s.ytd"},
        {"name": "f355s.yft"},
        {"name": "f355s_hi.yft"},
    ],
)
if "FINISHED" not in result:
    raise RuntimeError(f"Sollumz import failed: {result}")

rows = []
total_triangles = 0
total_vertices = 0
global_min = [float("inf")] * 3
global_max = [float("-inf")] * 3

for obj in bpy.data.objects:
    row = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "children": [c.name for c in obj.children],
        "custom_properties": {k: str(obj[k]) for k in obj.keys() if k != "_RNA_UI"},
    }
    for attr in ("sollum_type", "sollumz_lod_level", "lod_level"):
        if hasattr(obj, attr):
            try:
                row[attr] = str(getattr(obj, attr))
            except Exception:
                pass
    for attr in ("drawable_model_properties", "fragment_properties"):
        if hasattr(obj, attr):
            props = getattr(obj, attr)
            vals = {}
            for name in dir(props):
                if name.startswith("_") or "rna" in name.lower():
                    continue
                if "lod" not in name.lower() and name not in ("name",):
                    continue
                try:
                    value = getattr(props, name)
                    if isinstance(value, (str, int, float, bool)):
                        vals[name] = value
                except Exception:
                    pass
            if vals:
                row[attr] = vals

    if obj.type == "MESH":
        mesh = obj.data
        mesh.calc_loop_triangles()
        tris = len(mesh.loop_triangles)
        verts = len(mesh.vertices)
        total_triangles += tris
        total_vertices += verts
        row.update(
            vertices=verts,
            polygons=len(mesh.polygons),
            triangles=tris,
            materials=[m.name if m else None for m in mesh.materials],
        )
        if verts:
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            mins = [min(p[i] for p in points) for i in range(3)]
            maxs = [max(p[i] for p in points) for i in range(3)]
            row["bounds_world"] = [mins, maxs]
            for i in range(3):
                global_min[i] = min(global_min[i], mins[i])
                global_max[i] = max(global_max[i], maxs[i])
    rows.append(row)

images = []
for image in bpy.data.images:
    images.append({
        "name": image.name,
        "size": list(image.size),
        "filepath": image.filepath,
        "packed": image.packed_file is not None,
    })

report = {
    "blender_version": bpy.app.version_string,
    "objects": len(bpy.data.objects),
    "mesh_objects": sum(o.type == "MESH" for o in bpy.data.objects),
    "materials": len(bpy.data.materials),
    "images": len(bpy.data.images),
    "total_vertices_all_meshes": total_vertices,
    "total_triangles_all_meshes": total_triangles,
    "bounds_all_world": [global_min, global_max],
    "dimensions_all_world": [global_max[i] - global_min[i] for i in range(3)],
    "image_rows": images,
    "objects_rows": rows,
}
(outdir / "f355_import_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)

# Export imported hierarchy unchanged for forensic inspection. The next step
# selects the verified high-detail drawable rather than silently decimating it.
bpy.ops.export_scene.gltf(
    filepath=str(outdir / "f355_raw_import.glb"),
    export_format="GLB",
    export_animations=False,
    export_apply=False,
)
print("F355_IMPORT_SUMMARY", json.dumps({
    "objects": report["objects"],
    "mesh_objects": report["mesh_objects"],
    "vertices": total_vertices,
    "triangles": total_triangles,
    "materials": report["materials"],
    "images": report["images"],
    "bounds": report["bounds_all_world"],
    "dimensions": report["dimensions_all_world"],
}, ensure_ascii=False))
