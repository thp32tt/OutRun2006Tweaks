#!/usr/bin/env python3
"""OutRun 2006 Daytona Slot A R35: taper existing PMT-derived stamped spokes/bridges.
Only four already-existing original-derived steering meshes; native source/read-only.
No replacement mesh, no textures, exports, game integration or other slot.
"""
from pathlib import Path
import hashlib, json, sys, struct, math, subprocess, importlib.util
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
NATIVE=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
PRIOR=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v32_r34.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v33_r35.blend"
AUDIT=ROOT/"SLOTA_R35_NATIVE_STEERING_TAPER_MESH_AUDIT.json"
QA=ROOT/"SLOTA_R35_INDEPENDENT_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R35_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R34_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R34_R35_REAL_CYCLES_BEFORE_AFTER.jpg"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
SHA={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
     "NATIVE":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
     "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
     "BASE":"a7496d2669e626c612e2a94686b584f28db624e9363121cf46e86c9a4dfda824"}
PARTS={
 "factory_spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "left_bridge":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "right_bridge":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "lower_bridge":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def gate():
 for key,p in (("PMT",PMT),("NATIVE",NATIVE),("PHOTO",PHOTO),("BASE",BASE)):
  assert p.is_file() and sha(p)==SHA[key],("BLOCKED_INPUT_MISSING_OR_SHA_DRIFT",key)
 assert PRIOR.is_file() and BLENDER.is_file(),"BLOCKED_INPUT_BLENDER_OR_PRIOR_SCRIPT"
def helper():
 s=importlib.util.spec_from_file_location("daytona_native_r34_utils",str(PRIOR))
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 return m
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def delta(tag,p):
 from mathutils import Vector
 x,y,z=map(float,p);dx=dy=dz=0.
 if tag=="factory_spoke":
  # Original perforation pattern x=-0.431..-0.269 is untouched.
  radius=abs(x+.350)
  outer=smooth(.091,.156,radius)
  arm=smooth(.746,.770,z)*(1.-smooth(.828,.853,z))
  influence=outer*arm
  # Turn abrupt rectangular tips into a narrow, gently rising stamped sheet.
  # Sideways spoke width tapers toward the real wooden rim.
  dz=-(z-.792)*(.24*influence)+.00055*influence
  dy=-.00075*influence*(1.-smooth(-.287,-.275,y))
 elif tag in ("left_bridge","right_bridge"):
  radius=abs(x+.350)
  outer=smooth(.099,.172,radius)
  # Existing source-derived 20v/18f solids, NO new connector/pipe.
  dz=-(z-.793)*(.24*outer)
  dy=-(y+.286)*(.16*outer)
  dx=(-1. if tag=="left_bridge" else 1.)*.00055*outer
 elif tag=="lower_bridge":
  outer=1.-smooth(.615,.696,z)
  dx=-(x+.350)*(.21*outer)
  dy=-(y+.288)*(.16*outer)
 return Vector((dx,dy,dz))
def original():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==NATIVE.resolve()
 gate()
 for name,count in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and len(o.data.vertices)==count,("BLOCKED_NATIVE_ORIGINAL_OBJECT",name)
 print("R35_ORIGINAL_GAME_NATIVE_IMPORT_OBJECT_IDS_VERIFIED",flush=True)
def build():
 import bpy
 from mathutils.bvhtree import BVHTree
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==BASE.resolve()
 gate()
 m=helper()
 assert all(not p.exists() for p in (OUT,AUDIT,QA,PNG,COMPARE)),"BLOCKED_OUTPUT_VERSION_EXISTS"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects[PARTS["factory_spoke"]].data.vertices)==9732
 assert all(m.wheel_holes()),"BLOCKED_INPUT_EIGHT_STEERING_HOLES_NOT_OPEN"
 original_inventory=m.inventory()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(protected)==109,("BLOCKED_PROTECTED_MESH_COUNT",len(protected))
 report={}
 for tag,name in PARTS.items():
  obj=bpy.data.objects.get(name)
  assert obj and obj.type=="MESH" and obj.data.users==1,("BLOCKED_SOURCE_OBJECT",tag)
  before=m.state(obj);nm_before=m.nonmanifold(obj);inverted=obj.matrix_world.inverted()
  if tag.endswith("_bridge"):
   assert (len(obj.data.vertices),len(obj.data.polygons))==(20,18),("BLOCKED_BRIDGE_SOURCE_TOPOLOGY",tag)
  moved=0;maxmove=0.;sum_move=0.
  for vertex in obj.data.vertices:
   world=obj.matrix_world@vertex.co;shift=delta(tag,world)
   if shift.length<.000008:continue
   vertex.co=inverted@(world+shift)
   moved+=1;maxmove=max(maxmove,shift.length);sum_move+=shift.length
  obj.data.update()
  after=m.state(obj)
  assert moved >= (28 if tag=="factory_spoke" else 6),("BLOCKED_NO_REAL_SOURCE_VERTICES",tag,moved)
  assert maxmove<.009,("BLOCKED_EXCESSIVE_MESH_DEFORMATION",tag,maxmove)
  for fixed in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert before[fixed]==after[fixed],("BLOCKED_TOPOLOGY_UV_TRANSFORM_MATERIAL_CHANGE",tag,fixed)
  assert before["geometry_sha256"]!=after["geometry_sha256"]
  assert nm_before==m.nonmanifold(obj),("BLOCKED_NEW_NONMANIFOLD",tag)
  report[tag]={"before":before,"after":after,"changed_vertices":moved,
   "max_movement_m":round(maxmove,8),"mean_movement_m":round(sum_move/moved,8),
   "preexisting_nonmanifold_edges":nm_before}
 assert original_inventory==m.inventory(),"BLOCKED_SCENE_INVENTORY_CHANGE"
 assert {o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}==protected,"BLOCKED_OTHER_MESH_CHANGED"
 assert all(m.wheel_holes()),"BLOCKED_NATIVE_THROUGH_HOLES_OBSTRUCTED"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"slot":"A","car":"daytona365","status":"R35_PRIVATE_SOURCE_DERIVED_STEERING_TAPER_SAVED",
 "native_readonly_PMT":str(PMT),"original_native_PMT_sha256":SHA["PMT"],
 "authentic_original_import":str(NATIVE),"original_import_sha256":SHA["NATIVE"],
 "original_game_mesh_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "base_R34_sha256":SHA["BASE"],"output_R35_sha256":sha(OUT),
 "photo_genuine_1971_Spider_LHD_sha256":SHA["PHOTO"],
 "only_four_existing_source_steering_objects_modified":report,
 "protected_other_109_meshes_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
 "source_eight_spoke_holes":"PASS","transforms_pivots_uv_materials_untouched":True,
 "preexisting_nonmanifold":"UNRESOLVED_NOT_WORSENED",
 "game_eye":"NOT_CALIBRATED","authentic_7_view_photo_QA":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"advance_slot_A":False,"score_change":0,
 "native_exports_game_vr_textures_exterior_other_slot":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R35_ACTUAL_NATIVE_STEERING_MESH_SAVED",json.dumps({"sha":sha(OUT),"moves":{k:v["changed_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 gate()
 assert AUDIT.exists() and not QA.exists() and not PNG.exists()
 m=helper();a=json.loads(AUDIT.read_text())
 assert sha(OUT)==a["output_R35_sha256"]
 other={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(other)==109
 assert hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest()==a["protected_other_109_meshes_sha256"]
 for k,v in a["only_four_existing_source_steering_objects_modified"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert m.state(o)==v["after"],("BLOCKED_NEW_BLEND_REOPEN_MESH_DRIFT",k)
  assert m.nonmanifold(o)==v["preexisting_nonmanifold_edges"]
 assert all(m.wheel_holes()),"BLOCKED_REOPEN_THROUGH_HOLES"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R35_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R35_UNSAVED_APPROX_EYE",cd)
 sc.collection.objects.link(cam);cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000 and sha(OUT)==a["output_R35_sha256"]
 q={"status":"R35_OFFICIAL_BLENDER_4_5_15_PRIVATE_SOURCE_FRESH_REOPEN_CYCLES_PASS",
 "private_blend_sha256":sha(OUT),"actual_cycles_sha256":sha(PNG),"resolution":[720,480],
 "source_native_eight_holes":"PASS","all_four_edited_mesh_signatures":"PASS","other_109_meshes":"UNCHANGED",
 "real_in_game_eye":"UNCALIBRATED","seven_Spider_photo_angles":"INCOMPLETE",
 "GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED","car_complete":False,"score_change":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R35_INDEPENDENT_PRIVATE_REAL_SCENE_REOPEN_CYCLES_PASS",json.dumps(q),flush=True)
def compare():
 from PIL import Image
 assert QA.is_file() and PREV.is_file() and PNG.is_file() and not COMPARE.exists()
 with Image.open(PREV) as p,Image.open(PNG) as q:
  a=p.convert("RGB");b=q.convert("RGB");assert a.size==b.size==(720,480)
  ap=a.load();bp=b.load()
  diff=sum(max(abs(ap[x,y][k]-bp[x,y][k]) for k in range(3))>3 for x in range(720) for y in range(480))
  assert diff>300,("BLOCKED_NO_VISIBLE_GEOMETRY_CHANGE",diff)
  c=Image.new("RGB",(1440,480));c.paste(a,(0,0));c.paste(b,(720,0))
  c.save(COMPARE,quality=94,optimize=True)
 q=json.loads(QA.read_text())
 q.update({"R34_vs_R35_RGB_gt3_changed_pixels":diff,"R34_render_sha256":sha(PREV),
  "comparison_sha256":sha(COMPARE)})
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R35_TRUE_GEOMETRY_CYCLES_COMPARISON_PASS",diff,sha(COMPARE),flush=True)
def run(mode):
 assert BLENDER.is_file(),"BLOCKED_INPUT_BLENDER_NOT_PRESENT"
 scene=NATIVE if mode=="origin" else BASE if mode=="build" else OUT
 p=subprocess.run([str(BLENDER),"--background",str(scene),"--threads","2","--python",str(Path(__file__).resolve()),"--",mode],
                  capture_output=True,text=True,timeout=240)
 print(p.stdout[-11000:],flush=True)
 if p.stderr:print("BLENDER_STDERR",p.stderr[-1800:],flush=True)
 if p.returncode:raise RuntimeError("R35_BLENDER_FAILURE_"+mode+"_"+str(p.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("origin","build","verify"):
  try: import bpy
  except ImportError:run(mode)
  else: {"origin":original,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("Usage: script.py origin|build|verify|compare")