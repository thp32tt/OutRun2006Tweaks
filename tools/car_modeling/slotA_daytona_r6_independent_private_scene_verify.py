#!/usr/bin/env python3
"""Independent Blender process validation of the PRIVATE original-derived Daytona r6.

Must run on a machine possessing the actual original import + PMT + edited
private scene. A GitHub hosted runner without those files is BLOCKED_INPUT;
a smoke cube is never accepted as original-car evidence.
"""
import bpy
import bmesh
import hashlib
import json
import math
import os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
REPORT = W / "SLOT_A_DAYTONA_P0_R6_PHYSICAL_LIPS_GRIP_HUB_BEZEL.json"
r = json.loads(REPORT.read_text())
SOURCE = W / r["input_blend"]
OUT = W / r["output_blend"]
PMT = Path(r["original_game_resource"])
IMPORT = Path(r["original_game_import_blend"])
PHOTO = Path(r["exact_spider_photo"])

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def signature(o):
    d=o.data
    return hashlib.sha256(repr((
        [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
        [(f.material_index,tuple(f.vertices)) for f in d.polygons],
    )).encode("utf8")).hexdigest()

def matrix(o):
    return [[round(float(c),9) for c in row] for row in o.matrix_world]

assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve() == OUT.resolve()
for p,s in ((SOURCE,r["input_blend_sha256"]),(OUT,r["output_blend_sha256"]),
            (PMT,r["original_game_resource_sha256"]),
            (IMPORT,r["original_game_import_sha256"]),
            (PHOTO,r["exact_spider_photo_sha256"])):
    assert p.is_file() and digest(p)==s, str(p)
assert bpy.context.scene.camera.name == "V7_Camera_Reference_ThreeQuarter"
audit={}
names=set()
for k, entry in r["original_derived_edited_meshes"].items():
    name=entry["before"]["object_name"]
    names.add(name)
    o=bpy.data.objects[name]
    assert o.type=="MESH" and o.data.users==1
    assert (len(o.data.vertices),len(o.data.polygons))==(entry["after_vertices"],entry["after_faces"])
    assert signature(o)==entry["after_signature"]!=entry["before"]["signature"]
    assert matrix(o)==entry["before"]["world_matrix"]
    assert o["SLOTA_SOURCE_SHA256"]==r["original_game_resource_sha256"]
    assert o.data.uv_layers and o.data.materials
    assert all(math.isfinite(float(c)) for layer in o.data.uv_layers for lp in layer.data for c in lp.uv)
    bm=bmesh.new();bm.from_mesh(o.data)
    nonmanifold=sum(not ed.is_manifold for ed in bm.edges)
    bm.free()
    audit[k]={"source_mesh":name,"before":[entry["before"]["vertices"],entry["before"]["faces"]],
              "after":[entry["after_vertices"],entry["after_faces"]],
              "vertices_moved":entry["vertices_moved"],"signature":signature(o),
              "nonmanifold_edges":nonmanifold}
assert len(audit)==5
untouched={o.name:signature(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in names}
assert len(untouched)==r["unchanged_other_mesh_count"]
assert hashlib.sha256(json.dumps(untouched,sort_keys=True).encode()).hexdigest()==r["unchanged_other_mesh_sha256_aggregate"]
wheel=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
assert [m.name for m in wheel.data.materials]==["V7_Machined_Aluminum"]
tree=BVHTree.FromObject(wheel,bpy.context.evaluated_depsgraph_get())
for x,z,rad in r["source_spoke_perforation_centers"]:
    assert tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is None,(x,z,"hole filled")
    assert tree.ray_cast(Vector((x+rad*1.6,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None,(x,z,"metal missing")
result={"status":"DAYTONA_SLOT_A_R6_FRESH_REAL_ORIGINAL_SCENE_REOPEN_PASS",
    "official_blender":bpy.app.version_string,
    "private_blend_sha256":r["output_blend_sha256"],"original_pmt_sha256":r["original_game_resource_sha256"],
    "source_original_import_sha256":r["original_game_import_sha256"],
    "edited":audit,"unchanged_meshes":len(untouched),
    "physical_hole_rays_verified":8,"source_original_pmts_unmodified":True,
    "original_game_camera":"UNVERIFIED_APPROX_CAMERA_ONLY",
    "7_photo_views":"INCOMPLETE","24h_window":"NOT_ELAPSED",
    "github_actions_private_scene":"BLOCKED_INPUT_NOT_UPLOADED",
    "complete":False,"advance_slot":False}
(W/"SLOT_A_DAYTONA_P0_R6_FRESH_REOPEN.json").write_text(json.dumps(result,indent=2))
print(result["status"],json.dumps({"sha256":result["private_blend_sha256"],"meshes":list(audit),"holes":8}),flush=True)
