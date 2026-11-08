#!/usr/bin/env python3
"""Independent fresh-process Blender 4.5.15 QA and real Cycles driver-area render.
PRIVATE genuine original OutRun Daytona-derived scene is mandatory. Does not
write the scene or export to any game format; camera used is APPROXIMATE only.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
audit=json.loads((W/"SLOT_A_DAYTONA_P0_R12_NATIVE_SPOKE_EDGE_AND_DASH_GEOMETRY.json").read_text())
source=W/audit["before_blend"];target=W/audit["after_blend"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
def matrix(o):return [[round(float(v),9) for v in row] for row in o.matrix_world]
assert bpy.app.version_string.startswith("4.5.15"),bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==target.resolve(),"BLOCKED_INPUT_PRIVATE_SCENE"
assert audit["slot"]=="A" and audit["car_id"]=="daytona365"
for p,h in (
 (source,audit["before_blend_sha256"]),(target,audit["after_blend_sha256"]),
 (Path(audit["original_pmt_resource"]),audit["original_pmt_sha256"]),
 (Path(audit["original_import_blend"]),audit["original_import_sha256"]),
 (Path(audit["exact_spider_photo"]),audit["exact_spider_photo_sha256"])):
 assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SHA",str(p))
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
assert len(audit["modified_existing_source_derived_objects"])==6
changes={}
for key,record in audit["modified_existing_source_derived_objects"].items():
 ob=bpy.data.objects[record["name"]]
 bef=record["before"]
 assert ob.type=="MESH" and ob.data.users==1 and ob.data.uv_layers and ob.data.materials
 assert matrix(ob)==bef["matrix"]
 assert (len(ob.data.vertices),len(ob.data.polygons))==(bef["vertices"],bef["faces"])
 assert (len(ob.data.vertices),len(ob.data.polygons))==(record["after_vertices"],record["after_faces"])
 assert sig(ob)==record["after_signature"] and sig(ob)!=bef["signature"]
 assert all(math.isfinite(float(c)) for v in ob.data.vertices for c in v.co)
 bm=bmesh.new();bm.from_mesh(ob.data)
 nonmanifold=sum(not ed.is_manifold for ed in bm.edges)
 bm.free()
 changes[key]={"name":ob.name,"vertices_before":bef["vertices"],"faces_before":bef["faces"],
 "vertices_after":record["after_vertices"],"faces_after":record["after_faces"],
 "vertices_moved":record["moved_vertices"],"nonmanifold_edges":nonmanifold,
 "before_geometry_sha256":bef["signature"],"after_geometry_sha256":record["after_signature"]}
assert {k:c["nonmanifold_edges"] for k,c in changes.items()}=={
 "dashboard":184,"brow":0,"bezel":466,"spoke":1597,"rim":0,"hub":0}
changed_names={rec["name"] for rec in audit["modified_existing_source_derived_objects"].values()}
other={ob.name:sig(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in changed_names}
assert len(other)==audit["protected_others_count"]==107
assert hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest()==audit["protected_others_sha256"]
spoke=bpy.data.objects[audit["modified_existing_source_derived_objects"]["spoke"]["name"]]
bvh=BVHTree.FromObject(spoke,bpy.context.evaluated_depsgraph_get())
holes=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
 (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
 (-.350,.745,.0052),(-.350,.716,.0047)]
def hit(x,z):
 return bvh.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
assert all(not hit(x,z) and hit(x+1.6*r,z) for x,z,r in holes),"SOURCE_SPOKE_HOLES_BLOCKED"
assert not (W/"SLOTA_DAYTONA_R12_AFTER_REAL_CYCLES_APPROX_EYE.png").exists()
scene=bpy.context.scene
# Transient reproduction of SAME exact R11 renderer camera, deliberately
# NOT represented as an original game driver-eye position.
cd=bpy.data.cameras.new("SLOTA_R12_APPROX_EYE_ONLY_TRANSIENT")
cam=bpy.data.objects.new("SLOTA_R12_APPROX_EYE_ONLY_TRANSIENT",cd)
scene.collection.objects.link(cam)
cam.location=(-.35,-.92,1.055)
look=Vector((-.24,.19,.797))
cam.rotation_euler=(look-cam.location).to_track_quat("-Z","Y").to_euler()
cd.type="PERSP";cd.lens=28;cd.clip_start=.01
scene.camera=cam
scene.render.engine="CYCLES";scene.cycles.device="CPU"
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.cycles.samples=3;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=480
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
png=W/"SLOTA_DAYTONA_R12_AFTER_REAL_CYCLES_APPROX_EYE.png"
scene.render.filepath=str(png)
bpy.ops.render.render(write_still=True)
assert png.is_file() and png.stat().st_size>12000
assert sha(target)==audit["after_blend_sha256"],"reopen/render must not edit original-derived blend"
assert sha(source)==audit["before_blend_sha256"]
record={"result":"SLOTA_DAYTONA_R12_FRESH_REOPEN_AND_NATIVE_CYCLES_PASS",
 "blender":bpy.app.version_string,
 "original_game_pmt_sha256":audit["original_pmt_sha256"],
 "original_import_blend_sha256":audit["original_import_sha256"],
 "scene_r11_sha256":audit["before_blend_sha256"],
 "scene_r12_sha256":audit["after_blend_sha256"],
 "original_source_object_ids":audit["original_mesh_ids"],
 "modified_source_derived_meshes":changes,"unmodified_other_meshes":107,
 "verified_spoke_holes":len(holes),"source_nonmanifold_edges_remain":True,
 "cycles_comparison_camera":"APPROXIMATE_NOT_GAME_DRIVER_EYE",
 "render_png":png.name,"render_png_sha256":sha(png),
 "render_resolution":[720,480],"cycles_samples":3,
 "separate_process_from_build":True,
 "no_game_export":True,"private_original_scene_in_github_actions":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "seven_exact_spider_views":"INCOMPLETE","vehicle_complete":False,"slot_a_advance":False}
(W/"SLOTA_R12_INDEPENDENT_REOPEN_REAL_CYCLES.json").write_text(json.dumps(record,indent=2))
print(record["result"],json.dumps({"blend_sha":record["scene_r12_sha256"],
"png_sha":record["render_png_sha256"],
"moved":{k:v["vertices_moved"] for k,v in changes.items()},
"nonmanifold":{k:v["nonmanifold_edges"] for k,v in changes.items()}}),flush=True)
