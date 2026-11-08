#!/usr/bin/env python3
"""Ferrari F50 slot C P0 v2. Modify only three PMT-origin cockpit meshes in an EXISTING Blender file.

Usage: blender -b F50_OriginalPMT_P0_DashboardSteering_v1.blend --python this.py -- \
  --source-native /private/obj_plcar_f50_pmt.sz --input /private/F50_..._v1.blend \
  --output /private/F50_..._v2.blend --report /private/F50_..._v2.json \
  --render-root /private/F50_SlotC_v2
No game-format export, source PMT modification, replacement GLB, new materials or external geometry.
The source object names are derived from native PMT object/group/material indices, not authored names.
"""
import argparse
import bpy
import bmesh
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

RESOURCE_SHA = "10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
BASELINE_SHA = "b7289f9ec1d772f9beca1c785f63c3536e8c501aee8a9a5710b2b086b7152e6d"
SOURCE_IDS = {
    "PMT_F50_object00_group01_material028_a0": "object00_group01_material028_a0",
    "PMT_F50_object21_group01_material002_a0": "object21_group01_material002_a0",
    "PMT_F50_object21_group00_material000_a0": "object21_group00_material000_a0",
}
EXPECTED_COUNTS = {
    "PMT_F50_object00_group01_material028_a0": (346, 472),
    "PMT_F50_object21_group01_material002_a0": (898, 1656),
    "PMT_F50_object21_group00_material000_a0": (78, 124),
}
EXPECTED_MESH_SHA = {
    "PMT_F50_object00_group01_material028_a0": "f9ea3c54a23e97814fbd261e15a7ed7914ab675275aaf6fee865ff86b2bd0284",
    "PMT_F50_object21_group01_material002_a0": "e4ef49558d14f50da2a538adc39e313337682385a9032e6eb051dc11fb226312",
    "PMT_F50_object21_group00_material000_a0": "52746a845210f49e41513efb278810443dda3dec39341ab63e1837caca646d6e",
}

def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def signature(mesh):
    h = hashlib.sha256()
    for vert in mesh.vertices:
        h.update(struct.pack("<3f", *vert.co))
    for poly in mesh.polygons:
        h.update(struct.pack("<I", len(poly.vertices)))
        for idx in poly.vertices:
            h.update(struct.pack("<I", idx))
    return h.hexdigest()

def snapshot(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    open_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return {
        "source_id": obj.get("outrun_original_mesh_object_id"),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "mesh_sha256": signature(mesh),
        "nonmanifold_edges": open_edges,
        "matrix_world": [round(v, 9) for row in obj.matrix_world for v in row],
        "location": [round(v, 9) for v in obj.location],
        "rotation": [round(v, 9) for v in obj.rotation_euler],
        "scale": [round(v, 9) for v in obj.scale],
    }

def refine(obj, mode):
    """Subdivide ORIGINAL vertices/faces, then displace newly sampled physical surfaces."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # No new detached primitives or new object. Every new vertex derives from native triangles.
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    vs = list(mesh.vertices)
    moved = 0
    max_delta = 0.0
    if mode == "cowl":
        xs = [v.co.x for v in vs]
        ys = [v.co.y for v in vs]
        xmid = (min(xs) + max(xs)) * 0.5
        xrad = max((max(xs)-min(xs))*0.5, 1e-8)
        ymin = min(ys)
        yrad = max(max(ys)-ymin, 1e-8)
        for v in vs:
            nx = (v.co.x-xmid)/xrad
            ny = (v.co.y-ymin)/yrad
            ell = math.hypot(nx, (ny-0.23)/0.92)
            # F50 real cockpit: rolled upper brow and sunken instrument binnacle.
            # Small displacements leave the original game dashboard silhouette/pivot intact.
            eyebrow = math.exp(-((ell-0.83)/0.14)**2) * (0.55+0.45*max(0, min(1, ny)))
            well = math.exp(-((ell-0.39)/0.23)**2) * max(0.0, min(1.0, ny))
            dz = 0.0042*eyebrow - 0.0025*well
            v.co.z += dz
            if abs(dz)>1e-5:
                moved += 1
                max_delta = max(max_delta, abs(dz))
        obj["source_edit_scope"] = "P0 v2 original F50 gauge cowl: formed upper rolled eyebrow, sculpted shallow instrument well"
    elif mode == "rim":
        for v in vs:
            x,y,z = v.co
            r = math.hypot(x,y)
            if r < 1e-8: continue
            # Actual source rim radius ~0.166m. Physically smooth upper/lower grip,
            # subtly build up leather-like thickness from original surface topology.
            ring = math.exp(-((r-0.147)/0.014)**2) if 0.105 < r < 0.171 else 0.0
            front = 1.0 if z > -0.001 else -0.45
            dz = 0.0034*ring*front
            dr = 0.0011*ring*max(-1.0, min(1.0, (r-0.147)/0.014))
            # Three original spokes remain; a subtle pressed section increases depth.
            if 0.043 < r < 0.116:
                dz += 0.0008*math.exp(-((r-0.082)/0.025)**2) * (1.0 if z > 0.0 else -0.4)
            v.co.z += dz
            v.co.x += dr*x/r
            v.co.y += dr*y/r
            if abs(dz)>1e-5 or abs(dr)>1e-5:
                moved += 1
                max_delta = max(max_delta, abs(dz), abs(dr))
        obj["source_edit_scope"] = "P0 v2 original F50 3-spoke rim: rounded grip cross-section and pressed-spoke relief"
    elif mode == "hub":
        # Original backing has a thin front panel; emboss the original hub surface,
        # keeping the wheel's exact source pivot, material slots, and axis untouched.
        for v in vs:
            x,y,z = v.co
            r = math.hypot(x, y+0.009)
            cap = 0.0035*math.exp(-((r/0.033)**4))
            bevel_ring = 0.0009*math.exp(-((r-0.040)/0.007)**2)
            dz = (cap + bevel_ring) * (1.0 if z >= -0.0002 else 0.20)
            v.co.z += dz
            if abs(dz)>1e-5:
                moved += 1
                max_delta = max(max_delta, abs(dz))
        obj["source_edit_scope"] = "P0 v2 original F50 hub: shallow embossed center cap and rolled hub transition"
    else:
        raise ValueError("Unknown mode")
    assert moved >= 8, (obj.name, moved)
    mesh.update()
    return {"displaced_vertices": moved, "max_abs_delta_m": round(max_delta,8)}

def render_diagnostic(scene, root, suffix, camera, selected):
    # Clearly diagnostic, NOT original OutRun driver-eye or photogrammetry proof.
    backup_camera = scene.camera
    backup_engine = scene.render.engine
    backup_filepath = scene.render.filepath
    backup_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    hidden = {o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = 800
        scene.render.resolution_y = 560
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.camera = bpy.data.objects[camera]
        for o in bpy.data.objects:
            if o.type == "MESH":
                o.hide_render = o.name not in selected
        scene.render.filepath = str(root) + suffix
        bpy.ops.render.render(write_still=True)
    finally:
        for o in bpy.data.objects:
            if o.type == "MESH":
                o.hide_render = hidden[o.name]
        scene.camera = backup_camera
        scene.render.engine = backup_engine
        scene.render.filepath = backup_filepath
        (scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage) = backup_res

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-native",type=Path,required=True)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--render-root",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    assert bpy.app.version[:3] == (4,5,15), bpy.app.version
    assert a.source_native.is_file() and sha_file(a.source_native)==RESOURCE_SHA
    assert a.input.is_file() and sha_file(a.input)==BASELINE_SHA
    assert not a.output.exists() and not a.report.exists(), "Versioned checkpoint already exists"
    assert str(Path(bpy.data.filepath).resolve()) == str(a.input.resolve())
    assert bpy.context.scene.get("outrun_original_game_resource_sha256")==RESOURCE_SHA
    assert bpy.context.scene.get("geometry_edit_count")==3
    before = {o.name:snapshot(o) for o in bpy.data.objects if o.type=="MESH"}
    assert len(before)==42 and all(x["source_id"] for x in before.values())
    for name,source_id in SOURCE_IDS.items():
        assert before[name]["source_id"] == source_id
        assert (before[name]["vertices"],before[name]["faces"])==EXPECTED_COUNTS[name]
        assert before[name]["mesh_sha256"]==EXPECTED_MESH_SHA[name]
        assert tuple(before[name]["location"]) == (0,0,0)
        assert tuple(before[name]["scale"]) == (1,1,1)
    modes={"PMT_F50_object00_group01_material028_a0":"cowl",
           "PMT_F50_object21_group01_material002_a0":"rim",
           "PMT_F50_object21_group00_material000_a0":"hub"}
    motion={}
    for name,mode in modes.items():
        motion[name]=refine(bpy.data.objects[name],mode)
    after = {o.name:snapshot(o) for o in bpy.data.objects if o.type=="MESH"}
    assert set(after)==set(before)
    for name in before:
        assert before[name]["source_id"]==after[name]["source_id"]
        assert before[name]["matrix_world"]==after[name]["matrix_world"]
        if name not in modes:
            assert before[name]==after[name], "Non-target source object changed: "+name
        else:
            assert before[name]["mesh_sha256"]!=after[name]["mesh_sha256"]
            assert after[name]["vertices"]>before[name]["vertices"]
            assert after[name]["faces"]>before[name]["faces"]
    assert all(not o.data.materials for o in bpy.data.objects if o.type=="MESH")
    scene=bpy.context.scene
    scene["geometry_edit_count"]=6
    scene["slot_c_p0_v2_input_sha256"]=BASELINE_SHA
    scene["slot_c_p0_v2_source_native_sha256"]=RESOURCE_SHA
    scene["slot_c_p0_v2_status"]="P0_PARTIAL_NATIVE_DRIVER_EYE_UNVERIFIED"
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
    assert sha_file(a.source_native)==RESOURCE_SHA
    result={"status":"SLOT_C_F50_ORIGINAL_COCKPIT_V2_SOURCE_GEOMETRY_SAVED_NOT_COMPLETE",
            "blender":bpy.app.version_string,"native_original_sha256":RESOURCE_SHA,
            "baseline_blend_sha256":BASELINE_SHA,"output_blend_sha256":sha_file(a.output),
            "input_path":str(a.input),"output_path":str(a.output),
            "source_mesh_count":len(before),"edited_original_source_ids":list(SOURCE_IDS.values()),
            "mesh_delta":{n:{"before":before[n],"after":after[n],"sculpt":motion[n]} for n in modes},
            "unchanged_other_source_meshes":39,"original_transforms_unchanged":True,
            "texture_material_changes":False,"exported_pmt_ovc_ovc3":False,
            "photo_7view_gate":"UNTESTED","driver_eye_camera":"UNVERIFIED",
            "github_actions_private_real_scene":"NOT_RUN_NO_PRIVATE_UPLOAD","qa_gate":"P0_PARTIAL_NOT_COMPLETE"}
    a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    render_diagnostic(scene,a.render_root,"_GAUGE_QA_NON_GAME.png",
        "QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"])
    render_diagnostic(scene,a.render_root,"_STEERING_QA_NON_GAME.png",
        "QA_F50_STEERING_LOCAL_NON_GAME",[
        "PMT_F50_object21_group00_material000_a0",
        "PMT_F50_object21_group01_material001_a0",
        "PMT_F50_object21_group01_material002_a0"])
    print("SLOT_C_F50_V2_ORIGINAL_GEOMETRY_PASS",result["output_blend_sha256"],
          {n: (after[n]["vertices"],after[n]["faces"]) for n in modes})

if __name__=="__main__":
    main()