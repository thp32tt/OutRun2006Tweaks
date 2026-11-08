#!/usr/bin/env python3
"""Independent original-PMT Daytona slot A R13 reopened Blender and real Cycles audit.
Separate Blender 4.5.15 process mandatory. No substitute scene, no export, no material edit.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
A=json.loads((W/"SLOT_A_DAYTONA_P0_R13_ORIGINAL_VISOR_RIM_EDGELOOPS.json").read_text())
SRC=W/A["source_blend"];DEST=W/A["output_blend"]
REPORT=W/"SLOTA_R13_INDEPENDENT_NATIVE_CYCLES_AND_TOPOLOGY.json"
OUT=W/"SLOTA_DAYTONA_R13_AFTER_REAL_CYCLES_APPROX_EYE.png"
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
 [(f.material_index,tuple(f.vertices)) for f in o.data.polygons])).encode()).hexdigest()
def mat(o):return [[round(float(c),9) for c in row] for row in o.matrix_world]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==DEST.resolve(),"BLOCKED_INPUT: open genuine private R13"
assert not REPORT.exists() and not OUT.exists(),"immutable R13 evidence"
assert A["slot"]=="A" and A["car_id"]=="daytona365"
for p,h in ((SRC,A["source_blend_sha256"]),(DEST,A["output_blend_sha256"]),
(Path(A["original_native_PMT"]),A["original_native_PMT_sha256"]),
(Path(A["verified_original_import"]),A["verified_original_import_sha256"])):
 assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SOURCE_SHA",p)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
changed={}
for key,r in A["source_derived_original_mesh_changes"].items():
 ob=bpy.data.objects[r["source_derived_original_object"]]
 b=r["before"]
 assert ob.type=="MESH" and ob.data.users==1
 assert sig(ob)==r["after_mesh_signature"] and sig(ob)!=b["sig"]
 assert mat(ob)==b["matrix"]
 assert (len(ob.data.vertices),len(ob.data.polygons))==(r["after_vertices"],r["after_faces"])
 assert [u.name for u in ob.data.uv_layers]==b["uv_layers"]
 assert [m.name if m else None for m in ob.data.materials]==b["material_names"]
 assert all(math.isfinite(float(c)) for v in ob.data.vertices for c in v.co)
 if key in ("brow","rim"):
  assert r["after_vertices"]>b["vertices"]
  assert r["after_faces"]>b["faces"]
  assert A["refined_original_topology"][key]=={"before":[b["vertices"],b["faces"]],
                                                 "after":[r["after_vertices"],r["after_faces"]]}
 else:
  assert (r["after_vertices"],r["after_faces"])==(b["vertices"],b["faces"])
 mesh=bmesh.new();mesh.from_mesh(ob.data)
 nonmanifold=sum(not e.is_manifold for e in mesh.edges)
 mesh.free()
 changed[key]={"object":ob.name,"before":[b["vertices"],b["faces"]],
               "after":[r["after_vertices"],r["after_faces"]],
               "moved":r["moved_vertices"],"nonmanifold":nonmanifold,
               "source_geom_sig":b["sig"],"target_geom_sig":r["after_mesh_signature"]}
assert {k:v["nonmanifold"] for k,v in changed.items()}=={
"dashboard":184,"brow":0,"bezel":466,"spoke":1597,"rim":0,"hub":0}
keepnames={r["source_derived_original_object"] for r in A["source_derived_original_mesh_changes"].values()}
others={ob.name:sig(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in keepnames}
assert len(others)==A["other_meshes_preserved"]==107
assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==A["other_meshes_sha256"]
tree=BVHTree.FromObject(bpy.data.objects[A["source_derived_original_mesh_changes"]["spoke"]["source_derived_original_object"]],
bpy.context.evaluated_depsgraph_get())
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def hit(x,z):return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
for x,z,r in HOLES:
 assert not hit(x,z) and hit(x+1.6*r,z),("existing genuine hole sealed",x,z)
# Transient EXACT same comparison camera parameters as R12 and R11.
# Never interpret as a calibrated original game/VR driver-eye transform.
sc=bpy.context.scene
cd=bpy.data.cameras.new("SLOTA_R13_APPROX_DRIVER_EYE_TRANSIENT")
eye=bpy.data.objects.new("SLOTA_R13_APPROX_DRIVER_EYE_TRANSIENT",cd)
sc.collection.objects.link(eye)
eye.location=(-.35,-.92,1.055)
look=Vector((-.24,.19,.797))
eye.rotation_euler=(look-eye.location).to_track_quat("-Z","Y").to_euler()
cd.type="PERSP";cd.lens=28;cd.clip_start=.01
sc.camera=eye
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.cycles.samples=3;sc.cycles.use_denoising=True
sc.render.resolution_x=720;sc.render.resolution_y=480
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
sc.render.filepath=str(OUT)
bpy.ops.render.render(write_still=True)
assert OUT.is_file() and OUT.stat().st_size>12000
assert sha(DEST)==A["output_blend_sha256"]
assert sha(SRC)==A["source_blend_sha256"]
record={"result":"SLOTA_R13_PRIVATE_GENUINE_ORIGINAL_BLEND_REOPEN_REAL_CYCLES_PASS",
 "blender":bpy.app.version_string,"original_game_native_pmt_sha256":A["original_native_PMT_sha256"],
 "original_import_sha256":A["verified_original_import_sha256"],
 "source_blend_sha256":A["source_blend_sha256"],
 "new_blend_sha256":A["output_blend_sha256"],
 "original_source_object_ids":A["original_native_mesh_object_ids"],
 "source_derived_existing_meshes":changed,"source_holes_physically_open":8,
 "unchanged_other_source_meshes":107,
 "actual_cycles_png":OUT.name,"actual_cycles_sha256":sha(OUT),
 "cycles_resolution":[720,480],"cycles_samples":3,
 "cycles_camera":"APPROXIMATE_NOT_ORIGINAL_GAME_DRIVER_EYE",
 "source_nonmanifold_remains":{"dashboard":184,"bezel":466,"spoke":1597},
 "no_exterior_texture_ovc_pmt_glb_game_VR_edits":True,
 "official_github_hosted_real_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "photo_7_exact_spider_views":"INCOMPLETE","vehicle_complete":False,"slot_a_advance":False}
REPORT.write_text(json.dumps(record,indent=2))
print(record["result"],json.dumps({"scene_sha":record["new_blend_sha256"],
"render_sha":record["actual_cycles_sha256"],
"counts":{k:v["after"] for k,v in changed.items()},
"moved":{k:v["moved"] for k,v in changed.items()}},ensure_ascii=False),flush=True)
