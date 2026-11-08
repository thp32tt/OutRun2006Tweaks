#!/usr/bin/env python3
"""Ferrari F50: import existing OutRun 2006 original PMT mesh DIRECTLY to private editable .blend.
No GLB, OVC, OVC3, PMT extraction/export, new vehicle generation, texture/PBR creation, or game edits.
Diagnostic cameras are NOT the original game's camera.
"""
import sys,hashlib,json,zlib
from pathlib import Path
import bpy
from mathutils import Vector
THIS=Path(__file__).resolve().parent
sys.path.insert(0,str(THIS))
from f50_native_mesh_reader import open_pmt,decode_object
SOURCE=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
EXPECTED_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
BASE=THIS/"F50_OriginalPMT_CockpitSource_v1.blend"
REPORT=THIS/"F50_OriginalPMT_SourceMeshInventory_v1.json"
assert not BASE.exists(), "Immutable original-import Blender baseline already exists"
original=SOURCE.read_bytes()
assert hashlib.sha256(original).hexdigest()==EXPECTED_SHA, "Fail closed: original game source SHA mismatch"
original_stat=SOURCE.stat()
asset=open_pmt(SOURCE)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
source_col=bpy.data.collections.new("SOURCE_F50_Original_OutRun2006_PMT_DO_NOT_REPLACE")
bpy.context.scene.collection.children.link(source_col)
qa_col=bpy.data.collections.new("QA_DIAGNOSTIC_CAMERA_NOT_GAME_POSE")
bpy.context.scene.collection.children.link(qa_col)
scene=bpy.context.scene
scene["outrun_original_game_resource_file"]=str(SOURCE)
scene["outrun_original_game_resource_sha256"]=EXPECTED_SHA
scene["outrun_original_pmt_sha256"]=hashlib.sha256(zlib.decompress(original)).hexdigest()
scene["outrun_model"]="FERRARI_F50"
scene["source_cockpit_coordinate_mode"]="native PMT object-local XYZ; no guessed game transforms"
scene["source_game_camera_provenance"]="UNVERIFIED; QA views are diagnostic only"
scene["original_steering_local_pivot"]="F50 PMT object21 local (0,0,0), no guessed vehicle-space placement"
scene["geometry_edit_count"]=0
scene["prohibited_outputs"]=0
scene["read_only_original"]=True
original_metrics=[]
for oi in (0,20,21):
 parts=decode_object(asset,oi)
 for part in parts:
  name="PMT_F50_"+part["name"]
  verts=part["vertices"]
  triangles=[tuple(part["indices"][i:i+3]) for i in range(0,len(part["indices"]),3)]
  assert all(len(t)==3 and len(set(t))==3 for t in triangles)
  me=bpy.data.meshes.new(name+"_source")
  me.from_pydata(verts,[],triangles)
  me.update(calc_edges=True)
  uv=me.uv_layers.new(name="Source_PMT_UV0")
  for polygon in me.polygons:
   for loop_id in polygon.loop_indices:
    uv.data[loop_id].uv=part["uvs"][me.loops[loop_id].vertex_index]
  ob=bpy.data.objects.new(name,me)
  source_col.objects.link(ob)
  ob["outrun_original_mesh_object_id"]=part["name"]
  ob["outrun_original_pmt_object_index"]=oi
  ob["outrun_original_game_resource_sha256"]=EXPECTED_SHA
  ob["outrun_source_tex_index"]=part["tex_index"] if part["tex_index"] is not None else -1
  ob["source_vertex_count"]=len(verts)
  ob["source_face_count"]=len(triangles)
  # Original PMT object-local coordinates. NOT a guessed animation placement.
  ob.location=(0,0,0)
  ob.rotation_euler=(0,0,0)
  ob.scale=(1,1,1)
  # Blender Workbench only: neutral per-object display tint, NOT texture/PBR work.
  ob.color=(0.45,0.57,0.68,1) if oi==21 else (0.65,0.64,0.61,1)
  original_metrics.append({"name":name,"original_id":part["name"],"source_pmt_object":oi,
                           "verts":len(verts),"faces":len(triangles),"texture_id":part["tex_index"],
                           "native_xyz_no_transform":True})
def make_camera(name,at,look,ortho):
 cam=bpy.data.cameras.new(name)
 cam.type="ORTHO"
 cam.ortho_scale=ortho
 cam.clip_start=0.01
 cam.clip_end=30
 ob=bpy.data.objects.new(name,cam)
 qa_col.objects.link(ob)
 ob.location=at
 ob.rotation_euler=(Vector(look)-Vector(at)).to_track_quat("-Z","Y").to_euler()
 ob["diagnostic_only_no_game_camera_claim"]=True
 return ob
dash=make_camera("QA_F50_GAUGE_DETAIL_NON_GAME",(-0.355,0.715,0.48),(-0.355,0.715,-0.565),0.54)
wheel=make_camera("QA_F50_STEERING_LOCAL_NON_GAME",(0,0,0.9),(0,0,0),0.49)
scene.camera=dash
scene.render.engine="BLENDER_WORKBENCH"
scene.render.resolution_x=800;scene.render.resolution_y=560;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.display.shading.light="STUDIO"
scene.display.shading.color_type="OBJECT"
scene.display.shading.show_cavity=True
scene.render.film_transparent=False
scene.world.color=(0.12,0.12,0.12)
bpy.ops.wm.save_as_mainfile(filepath=str(BASE),compress=True)
def do_render(stem,cam,predicate):
 old=[(o,o.hide_render) for o in source_col.objects]
 try:
  for ob in source_col.objects:ob.hide_render=not predicate(ob)
  scene.camera=cam
  scene.render.filepath=str(THIS/stem)
  bpy.ops.render.render(write_still=True)
 finally:
  for ob,old_hide in old:ob.hide_render=old_hide
# Separate source-only diagnostic renders; same views will be used for refined scene.
do_render("F50_Before_Original_Source_GaugeDetail.png",dash,lambda o:o.get("outrun_original_mesh_object_id")=="object00_group01_material028_a0")
do_render("F50_Before_Original_Source_SteeringLocal.png",wheel,lambda o:o.get("outrun_original_pmt_object_index")==21)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA
report={"status":"SOURCE_IMPORT_BASELINE_PROVENANCE_PASS", "source_file":str(SOURCE),
 "source_compressed_sha256":EXPECTED_SHA,"source_raw_pmt_sha256":scene["outrun_original_pmt_sha256"],
 "source_bytes":len(original),"source_object_names":[v["original_id"] for v in original_metrics],
 "source_parts":len(original_metrics),"native_objects":[0,20,21],
 "cockpit_semantics":"candidate instrument panel texture8 object00_material028; steering object21 local; driver-eye/game placement unverified",
 "native_camera_verified":False,"original_game_files_modified":False,"new_vehicle_created":False,
 "textures_pbr_modified":False,"ovc3_ovc_pmt_generated":False,
 "scene":str(BASE),"scene_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
 "mesh_objects":original_metrics}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("F50_REAL_ORIGINAL_PMTSOURCE_BLENDER_BASELINE_PASS",report["scene_sha256"],"MESHES",len(original_metrics))