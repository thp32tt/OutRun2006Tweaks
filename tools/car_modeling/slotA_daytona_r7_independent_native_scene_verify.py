#!/usr/bin/env python3
"""Fresh-process verification: real native-PMT-derived Daytona Slot A r7 .blend.

This deliberately requires the PRIVATE source PMT, original import, real
candidate scene and exact vehicle photo. CI without licensed scene is
BLOCKED_INPUT, not a pretend Blender source/model PASS.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
r=json.loads((W/"SLOT_A_DAYTONA_P0_R7_ORIGINAL_BINNACLE_SPOKE.json").read_text())
src=W/r["input_blend"];out=W/r["output_blend"]
pmt=Path(r["original_game_resource"])
original=Path(r["original_import_blend"])
photo=Path(r["exact_spider_lhd_photo"])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
  [(p.material_index,tuple(p.vertices)) for p in d.polygons],
 )).encode("utf8")).hexdigest()
def matrix(o):return [[round(float(x),9) for x in row] for row in o.matrix_world]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==out.resolve()
for p,s in ((src,r["input_sha256"]),(out,r["output_sha256"]),
            (pmt,r["original_game_sha256"]),(original,r["original_import_sha256"]),
            (photo,r["photo_sha256"])):
 assert p.is_file() and sha(p)==s,(str(p),s)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
changed={}
names=set()
for k,v in r["changed_existing_source_derived_meshes"].items():
 o=bpy.data.objects[v["source_original_object"]]
 names.add(o.name)
 assert o.type=="MESH" and o.data.users==1
 assert (len(o.data.vertices),len(o.data.polygons))==(v["after_vertices"],v["after_faces"])
 assert sig(o)==v["after_signature"] and sig(o)!=v["before"]["signature"]
 assert matrix(o)==v["before"]["matrix"]
 assert o["SLOTA_SOURCE_SHA256"]==r["original_game_sha256"]
 assert o.data.uv_layers and o.data.materials
 assert all(math.isfinite(float(c)) for uv in o.data.uv_layers for loop in uv.data for c in loop.uv)
 bm=bmesh.new();bm.from_mesh(o.data)
 count_nm=sum(not e.is_manifold for e in bm.edges)
 bm.free()
 changed[k]={"object":o.name,"before":[v["before"]["vertices"],v["before"]["faces"]],
     "after":[v["after_vertices"],v["after_faces"]],"moved":v["moved_vertices"],
     "nonmanifold_edges":count_nm,"before_sig":v["before"]["signature"],"after_sig":sig(o)}
assert len(changed)==5
other={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in names}
assert len(other)==r["untouched_other_meshes"]
assert hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest()==r["protected_mesh_geometry_aggregate_sha256"]
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
wheel=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
assert [mat.name for mat in wheel.data.materials]==["V7_Machined_Aluminum"]
tree=BVHTree.FromObject(wheel,bpy.context.evaluated_depsgraph_get())
holes=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
 (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
 (-.350,.745,.0052),(-.350,.716,.0047)]
def hit(x,z):return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
for x,z,rad in holes:
 assert not hit(x,z) and hit(x+rad*1.6,z),(x,z,"hole")
record={"result":"SLOTA_R7_REAL_PRIVATE_BLENDER_INDEPENDENT_REOPEN_PASS",
 "output_blend":str(out),"output_sha256":r["output_sha256"],
 "original_game_sha256":r["original_game_sha256"],
 "original_import_sha256":r["original_import_sha256"],
 "source_object_modified":changed,"other_meshes_unchanged":len(other),
 "physical_steering_holes_verified":len(holes),
 "source_pmt_preserved":True,"original_game_camera":"UNVERIFIED",
 "seven_real_photo_views":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_NO_PRIVATE_SCENE_UPLOAD",
 "vehicle_complete":False}
(W/"SLOTA_R7_INDEPENDENT_REOPEN.json").write_text(json.dumps(record,indent=2))
print(record["result"],json.dumps({"hash":record["output_sha256"],
 "changed_objects":list(changed),"remaining_non_manifold":{k:v["nonmanifold_edges"] for k,v in changed.items()}}),flush=True)
