#!/usr/bin/env python3
"""Independent new-process source-gated QA of real Daytona original-derived r10 Blender.

Original PMT and original import required. No synthetic scene fallback.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
a=json.loads((W/"SLOT_A_DAYTONA_P0_R10_ORIGINAL_SPIDER_DASH_WHEEL_GEOMETRY.json").read_text())
src=W/a["before_blend"]
dst=W/a["after_blend"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
  [(f.material_index,tuple(f.vertices)) for f in d.polygons])).encode()).hexdigest()
def matrix(o):return [[round(float(v),9) for v in row] for row in o.matrix_world]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==dst.resolve()
for p,h in ((src,a["before_blend_sha256"]),(dst,a["after_blend_sha256"]),
            (Path(a["original_pmt_resource"]),a["original_pmt_sha256"]),
            (Path(a["original_import_blend"]),a["original_import_sha256"]),
            (Path(a["exact_spider_photo"]),a["exact_spider_photo_sha256"])):
 assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SOURCE_MISMATCH",str(p))
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
changed={}
for key,record in a["modified_existing_source_derived_objects"].items():
 o=bpy.data.objects[record["name"]]
 assert o.type=="MESH" and o.data.users==1
 assert sig(o)==record["after_signature"] and sig(o)!=record["before"]["geometry_signature"]
 assert matrix(o)==record["before"]["matrix_world"],"changed original object matrix"
 assert (len(o.data.vertices),len(o.data.polygons))==(record["after_vertices"],record["after_faces"])
 assert (len(o.data.vertices),len(o.data.polygons))==(record["before"]["vertices"],record["before"]["faces"])
 assert len(o.data.uv_layers)>0 and len(o.data.materials)>0
 assert o["SLOTA_SOURCE_SHA256"]==a["original_pmt_sha256"]
 assert all(math.isfinite(float(t)) for v in o.data.vertices for t in v.co)
 bm=bmesh.new()
 bm.from_mesh(o.data)
 nonmanifold=sum(not e.is_manifold for e in bm.edges)
 bm.free()
 changed[key]={"original_derivative_object":o.name,"vertices":len(o.data.vertices),
               "faces":len(o.data.polygons),"moved":record["moved_vertices"],
               "max_displacement_mm":record["max_mm"],"nonmanifold":nonmanifold,
               "before":record["before"]["geometry_signature"],"after":sig(o)}
assert len(changed)==6
others={o.name:sig(o) for o in bpy.data.objects
        if o.type=="MESH" and o.name not in
        [r["name"] for r in a["modified_existing_source_derived_objects"].values()]}
assert len(others)==a["protected_other_meshes"]==107
assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==a["protected_other_mesh_signatures_sha256"]
assert changed["spoke"]["nonmanifold"]==1597
assert changed["dashboard"]["nonmanifold"]==184
assert changed["bezel"]["nonmanifold"]==466
assert changed["brow"]["nonmanifold"]==0
assert changed["rim"]["nonmanifold"]==0
assert changed["hub"]["nonmanifold"]==0
tree=BVHTree.FromObject(
 bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"],
 bpy.context.evaluated_depsgraph_get())
holes=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
       (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
       (-.350,.745,.0052),(-.350,.716,.0047)]
def hit(x,z):
 return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
for x,z,rad in holes:
 assert not hit(x,z) and hit(x+1.6*rad,z),("physical original through-hole violated",x,z)
record={
 "result":"SLOT_A_R10_GENUINE_NATIVE_BLENDER_FRESH_REOPEN_PASS",
 "output_sha256":a["after_blend_sha256"],
 "original_pmt_sha256":a["original_pmt_sha256"],
 "original_import_sha256":a["original_import_sha256"],
 "exact_spider_photo_sha256":a["exact_spider_photo_sha256"],
 "blender":bpy.app.version_string,
 "changed_existing_source_derived":changed,
 "untouched_other_mesh_count":len(others),
 "original_geometry_source_objects":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "existing_spoke_holes_preserved":8,
 "existing_nonmanifold_topology_remains":True,
 "original_game_camera":"NOT_CALIBRATED",
 "seven_exact_spider_views":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "source_pmt_not_written":True,
 "vehicle_complete":False,"slot_A_advance":False}
(W/"SLOTA_R10_INDEPENDENT_REOPEN.json").write_text(json.dumps(record,indent=2))
print(record["result"],json.dumps({"SHA256":record["output_sha256"],
 "modified":{k:v["moved"] for k,v in changed.items()},
 "nonmanifold":{k:v["nonmanifold"] for k,v in changed.items()}}),flush=True)