#!/usr/bin/env python3
"""Independent fresh-Blender process QA for *real* private original-derived Daytona r8."""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
a=json.loads((W/"SLOT_A_DAYTONA_P0_R8_PHOTO_GUIDED_EXISTING_MESH.json").read_text())
f=W/a["output_blend"]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==f.resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
def mat(o):return [[round(float(c),9) for c in row] for row in o.matrix_world]
for p,s in [
 (f,a["output_sha256"]),(W/a["source_blend"],a["source_sha256"]),
 (Path(a["original_game_file"]),a["original_game_sha256"]),
 (Path(a["original_import_file"]),a["original_import_sha256"]),
 (Path(a["exact_photo"]),a["exact_photo_sha256"])]:
 assert p.is_file() and sha(p)==s,("wrong native input",p)
changes={}
for k,v in a["changed_existing_meshes"].items():
 o=bpy.data.objects[v["source_original_or_derivative_object"]]
 assert o.type=="MESH" and o.data.users==1
 assert sig(o)==v["after_signature"]!=v["before"]["signature"]
 assert mat(o)==v["before"]["matrix"]
 assert (len(o.data.vertices),len(o.data.polygons))==tuple(v["after_counts"])
 assert tuple(v["after_counts"])==tuple(v["before"]["counts"])
 assert len(o.data.uv_layers)>0 and len(o.data.materials)>0
 assert o["SLOTA_SOURCE_SHA256"]==a["original_game_sha256"]
 assert all(math.isfinite(float(c)) for vtx in o.data.vertices for c in vtx.co)
 bm=bmesh.new();bm.from_mesh(o.data)
 nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
 changes[k]={"object":o.name,"vertices":len(o.data.vertices),
             "faces":len(o.data.polygons),"nonmanifold_edges":nonmanifold,
             "vertices_moved":v["vertices_moved"],"pre":v["before"]["signature"],
             "post":v["after_signature"]}
others={o.name:sig(o) for o in bpy.data.objects
        if o.type=="MESH" and o.name not in
        {v["source_original_or_derivative_object"] for v in a["changed_existing_meshes"].values()}}
assert len(others)==108
assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==a["untouched_other_geometry_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
wheel=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
tree=BVHTree.FromObject(wheel,bpy.context.evaluated_depsgraph_get())
holes=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),(-.310,.804,.0068),
       (-.290,.804,.0068),(-.269,.804,.0068),(-.350,.745,.0052),(-.350,.716,.0047)]
def hit(x,z):return tree.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.)[2] is not None
assert all(not hit(x,z) and hit(x+rad*1.6,z) for x,z,rad in holes)
assert changes["spoke"]["nonmanifold_edges"]==1597
assert changes["dashboard"]["nonmanifold_edges"]==184
assert changes["cowl"]["nonmanifold_edges"]==0
assert changes["rim"]["nonmanifold_edges"]==0
audit={"result":"SLOTA_R8_REAL_PRIVATE_BLENDER_FRESH_REOPEN_PASS",
       "sha256":a["output_sha256"],"original_resource_sha256":a["original_game_sha256"],
       "original_import_sha256":a["original_import_sha256"],"blender":bpy.app.version_string,
       "changed_existing_source_derived_meshes":changes,"untouched_other_meshes":len(others),
       "through_holes_preserved":8,
       "preexisting_nonmanifold_spoke_edges":1597,
       "preexisting_nonmanifold_dashboard_edges":184,
       "original_camera":"UNVERIFIED","seven_exact_spider_views":"INCOMPLETE",
       "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
       "vehicle_complete":False}
(W/"SLOTA_R8_FRESH_REOPEN_AUDIT.json").write_text(json.dumps(audit,indent=2))
print(audit["result"],json.dumps({"hash":audit["sha256"],"changes":{k:v["vertices_moved"] for k,v in changes.items()},
         "nonmanifold":{k:v["nonmanifold_edges"] for k,v in changes.items()}}),flush=True)
