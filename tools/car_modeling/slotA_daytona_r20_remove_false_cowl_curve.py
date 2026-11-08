#!/usr/bin/env python3
"""SLOT A Daytona R20: remove erroneous duplicated synthetic cowl bar.

Source: authentic game PMT -> independently authenticated original .blend ->
private R19 derivative. Direct corrective edit to existing Blender curve
geometry, never original native PMT, source blend, body, materials or textures.
The V6 curve was an ADDED derivative with 11-mm bevel, not PMT source geometry.
"""
from pathlib import Path
import bpy,hashlib,json,os,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
ORIGINAL=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORTED=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
R19=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v17_r19.blend"
R20=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v18_r20.blend"
R19_AUDIT=ROOT/"SLOTA_R19_USER_FEEDBACK_SOURCE_GEOMETRY_AUDIT.json"
AUDIT=ROOT/"SLOTA_R20_REMOVE_FALSE_PHOTO_OVERLAP_BAR_SOURCE_AUDIT.json"
QA=ROOT/"SLOTA_R20_FRESH_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R20_AFTER_REAL_CYCLES_APPROX_EYE.png"
TUBE="V6_BLENDER_INSTRUMENT_COWL_ROUNDED_LEATHER_EDGE"
SPOKE="V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"
HASH={"source":"237f0add4f0a6e931bfcb86c24e0ac5aede13f05147c2be18116f1096b36c779",
"game":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
  [(p.material_index,tuple(p.vertices)) for p in o.data.polygons])).encode()).hexdigest()
def matrix(o):
 return [[round(float(c),9) for c in row] for row in o.matrix_world]
def points(obj):
 data=obj.data
 return [[round(float(k),8) for k in p.co] for s in data.splines for p in s.points]
def curve_state(obj):
 return {"name":obj.name,"type":obj.type,"matrix":matrix(obj),
 "curve_name":obj.data.name,"bevel_depth":round(float(obj.data.bevel_depth),8),
 "bevel_resolution":int(obj.data.bevel_resolution),
 "splines":len(obj.data.splines),
 "points":points(obj),
 "materials":[m.name if m else None for m in obj.data.materials],
 "hide_render":bool(obj.hide_render)}
def gate():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_VERSION"
 for name,p,h in (("PMT",ORIGINAL,HASH["game"]),("IMPORT",IMPORTED,HASH["import"]),("R19",R19,HASH["source"])):
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SHA",name)
 assert R19_AUDIT.is_file() and json.loads(R19_AUDIT.read_text())["private_r19_output_sha256"]==HASH["source"]
 assert bpy.data.objects[TUBE].type=="CURVE"
 assert len(bpy.data.objects[SPOKE].data.vertices)==9720
def holes():
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(bpy.data.objects[SPOKE],bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return tree.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def meshes():
 return {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH"}
def registry():
 return {"objects":sorted(bpy.data.objects.keys()),"meshes":sorted(bpy.data.meshes.keys()),
 "curves":sorted(bpy.data.curves.keys()),"materials":sorted(bpy.data.materials.keys()),
 "images":{i.name:(list(i.size),bool(i.packed_file)) for i in bpy.data.images},
 "cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}}
def build():
 assert Path(bpy.data.filepath).resolve()==R19.resolve(),"BLOCKED_NOT_VERIFIED_R19"
 assert not R20.exists() and not AUDIT.exists(),"IMMUTABLE_R20_COLLISION"
 gate()
 obj=bpy.data.objects[TUBE]
 assert len(obj.data.splines)==1 and obj.data.splines[0].type=="POLY"
 assert abs(obj.data.bevel_depth-.011)<.0001,"UNEXPECTED_FALSE_BAR_SOURCE"
 initial=curve_state(obj)
 assert len(initial["points"])>=50
 before=meshes();base=registry()
 assert len(before)==113 and all(holes())
 # Genuine correction: the separate V6 curve is an invented duplicated,
 # 11mm-radius curved tube. Recess its points entirely inside the existing
 # dashboard and cancel its surface sweep. No source vehicle mesh is deleted.
 for spline in obj.data.splines:
  for point in spline.points:
   point.co.y+=.108
   point.co.z-=.030
 obj.data.bevel_depth=0.0
 obj.data.update_tag()
 bpy.context.view_layer.update()
 finished=curve_state(obj)
 assert finished["bevel_depth"]==0.0 and finished["name"]==initial["name"]
 assert len(finished["points"])==len(initial["points"])
 assert len(before)==len(meshes()) and all(meshes()[n]==h for n,h in before.items()),"GAME_DERIVED_MESH_MODIFIED"
 assert registry()==base,"OTHER_SCENE_DATA_CHANGED"
 assert all(holes()),"SOURCE_HOLES_CHANGED"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(R20),compress=True)
 assert R20.stat().st_size>1000000
 rec={"status":"SLOT_A_R20_VERIFIED_ORIGINAL_COCKPIT_FALSE_BAR_CORRECTED",
 "car":"daytona365","slot":"A","blender":"4.5.15 LTS",
 "original_game_PMT_sha256":HASH["game"],"original_import_blend_sha256":HASH["import"],
 "original_native_object_names":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "private_input_r19_sha256":HASH["source"],"private_output_r20_sha256":sha(R20),
 "private_output_blend":str(R20),
 "corrected_preexisting_non_native_curve":TUBE,
 "curve_before":initial,"curve_after":finished,
 "original_113_meshes_unchanged_sha256":hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
 "same_scene_registries_cameras_materials_images_matrices":True,
 "all_original_8_spoke_holes_open":True,
 "source_PMT_untouched":True,"no_exterior_or_new_textures":True,
 "no_ovc_ovc3_pmt_glb_game_VR_export":True,
 "github_hosted_original_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "game_eye":"NOT_CALIBRATED","7_real_spider_views":"INCOMPLETE",
 "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding="utf-8")
 print("SLOTA_R20_FALSE_ADDED_TUBE_GEOMETRY_CORRECTED",json.dumps({"blend_sha":rec["private_output_r20_sha256"],"curve_point_count":len(finished["points"]),"old_bevel_m":initial["bevel_depth"],"new_bevel_m":finished["bevel_depth"]}),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==R20.resolve(),"BLOCKED_R20_REOPEN"
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists(),"IMMUTABLE_QA_COLLISION"
 gate()
 rec=json.loads(AUDIT.read_text())
 assert sha(R20)==rec["private_output_r20_sha256"]
 assert curve_state(bpy.data.objects[TUBE])==rec["curve_after"]
 sigs=meshes()
 assert len(sigs)==113 and hashlib.sha256(json.dumps(sigs,sort_keys=True).encode()).hexdigest()==rec["original_113_meshes_unchanged_sha256"]
 assert all(holes())
 sc=bpy.context.scene
 c=bpy.data.cameras.new("TEMP_R20_APPROX_EYE_NOT_SAVED")
 cam=bpy.data.objects.new("TEMP_R20_APPROX_EYE_NOT_SAVED",c)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 c.lens=28;c.clip_start=.01
 sc.camera=cam;sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG"
 sc.render.image_settings.color_mode="RGBA";sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(R20)==rec["private_output_r20_sha256"]
 qa={"status":"SLOT_A_R20_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_REAL_CYCLES_PASS",
 "blender":bpy.app.version_string,"r20_blend_sha256":sha(R20),
 "cycles_image_sha256":sha(PNG),"image":PNG.name,"resolution":[720,480],
 "curve_removed_from_visible_geometry":bpy.data.objects[TUBE].data.bevel_depth==0,
 "original_113_meshes_same":True,"original_spoke_8_holes_open":True,
 "game_camera":"APPROXIMATE_NOT_CALIBRATED","hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf-8")
 print("SLOTA_R20_INDEPENDENT_REAL_SOURCE_RENDER_PASS",json.dumps(qa),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOTA_R20_MODE")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("set SLOTA_R20_MODE=build or verify")