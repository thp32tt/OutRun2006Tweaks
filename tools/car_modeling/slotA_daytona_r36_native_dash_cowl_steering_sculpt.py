#!/usr/bin/env python3
"""Ferrari Daytona Slot A R36: original-game-derived dash/binnacle and native steering sheet sculpt.
Strict: NO new cockpit or vehicle, no alternate GLB, no material/texture/exterior/native export/game.
Load only exact private PMT-import-derived R35 editable scene. Original PMT is read-only.
"""
from pathlib import Path
import sys,subprocess,hashlib,json,math,importlib.util
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
HELPER=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v33_r35.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v34_r36.blend"
AUDIT=ROOT/"SLOTA_R36_ORIGINAL_SOURCE_DASH_STEERING_AUDIT.json"
QA=ROOT/"SLOTA_R36_FRESH_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R36_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R35_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=ROOT/"SLOTA_DAYTONA_R35_R36_REAL_CYCLES_BEFORE_AFTER.jpg"
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
SHA={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
"BASE":"e64722b0d72fe79ade93bae0c03dc97771db585020440e85e5f7765455155c9f"}
NAMES={"pad":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"lower":"V8_21_SOURCE_LOWER_GAUGE_SHROUD"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def gate():
 for key,path in (("PMT",PMT),("ORIG",ORIG),("PHOTO",PHOTO),("BASE",BASE)):
  assert path.is_file() and sha(path)==SHA[key],("BLOCKED_INPUT_MISSING_OR_SHA",key)
 assert HELPER.is_file() and BL.is_file(),"BLOCKED_INPUT_BLENDER_OR_AUDIT_HELPERS"
def mhelper():
 s=importlib.util.spec_from_file_location("slotA_r34_source_helper",str(HELPER))
 module=importlib.util.module_from_spec(s);s.loader.exec_module(module);return module
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3-2*t)
def gauss(x,c,w):
 return math.exp(-((x-c)/w)**4)
def sculpt(tag,p):
 from mathutils import Vector
 x,y,z=map(float,p);dx=dy=dz=0.
 # Use measured existing R35 source vertices: never generate synthetic dashboard objects.
 if tag=="pad":
  span=smooth(-.656,-.622,x)*(1.-smooth(-.082,-.052,x))
  front=1.-smooth(.173,.232,y)
  brow=smooth(.800,.842,z)*(1.-smooth(.912,.956,z))
  field=.57*gauss(x,-.513,.149)+.57*gauss(x,-.188,.149)+.30*gauss(x,-.349,.235)
  dy=-.0031*span*front*brow*field
  dz=.0038*span*front*brow*(.7*field-.14)
 elif tag=="cowl":
  driver=smooth(-.635,-.605,x)*(1.-smooth(-.082,-.050,x))
  forward=1.-smooth(.202,.305,y)
  far=gauss(x,-.511,.111)+gauss(x,-.183,.111)
  center=gauss(x,-.348,.083)
  # Two softly raised eyebrow crowns taper into the factory upper dash,
  # replacing the overly flat visual arch without blocking instruments.
  dz=driver*forward*(.0043*far-.0014*center)
  dy=-.0025*driver*forward*(.5+.5*far)
 elif tag=="bezel":
  # Keep real existing three gauge bores; roll their front-upper housing
  # inward while preserving all ring topology and aperture vertex IDs.
  front=1.-smooth(.147,.161,y)
  upper=smooth(.765,.827,z)*(1.-smooth(.895,.921,z))
  driver=smooth(-.63,-.615,x)*(1.-smooth(-.095,-.07,x))
  dy=.0026*front*upper*driver
  dz=-.0010*front*upper*driver
 elif tag=="spoke":
  # The existing original object22 3-spoke metal pressing, NOT a substitute.
  # Only a thin front sheet crown; factory punched holes left physically open.
  left_right=smooth(.047,.10,abs(x+.350))*(1.-smooth(.17,.185,abs(x+.350)))
  band=smooth(.763,.777,z)*(1.-smooth(.810,.830,z))
  front=1.-smooth(-.296,-.278,y)
  dy=-.0021*left_right*band*front
  dz=.0005*left_right*band*front*((z-.795)/.035)
 elif tag=="lower":
  driver=smooth(-.633,-.615,x)*(1.-smooth(-.090,-.061,x))
  front=1.-smooth(.174,.201,y)
  dy=.0036*driver*front
  dz=-.0012*driver*front
 return Vector((dx,dy,dz))
def original():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==ORIG.resolve()
 gate()
 for name,v in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and len(o.data.vertices)==v,("BLOCKED_INPUT_ORIGINAL_OBJECT",name)
 print("R36_NATIVE_PMT_ORIGINAL_IMPORT_OBJECTS_VERIFIED",flush=True)
def build():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==BASE.resolve()
 gate()
 assert all(not x.exists() for x in (OUT,AUDIT,QA,PNG,COMP)),"BLOCKED_IMMUTABLE_OUTPUT_EXISTS"
 m=mhelper()
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9732
 assert all(m.wheel_holes()),"BLOCKED_INPUT_ORIGINAL_EIGHT_HOLES"
 inv=m.inventory()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==108,("BLOCKED_PROTECTED_MESH_COUNT",len(protected))
 report={};threshold={"pad":125,"cowl":850,"bezel":750,"spoke":90,"lower":60}
 for tag,name in NAMES.items():
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and o.data.users==1,("BLOCKED_INPUT_MISSING_EXISTING_SOURCE",tag)
  before=m.state(o);bad=m.nonmanifold(o);invmat=o.matrix_world.inverted()
  n=0;maximum=0.;travel=0.
  for v in o.data.vertices:
   old=o.matrix_world@v.co;delta=sculpt(tag,old)
   if delta.length<.000008:continue
   v.co=invmat@(old+delta);n+=1;maximum=max(maximum,delta.length);travel+=delta.length
  o.data.update();after=m.state(o)
  assert n>=threshold[tag],("BLOCKED_INSUFFICIENT_REAL_EDIT",tag,n)
  assert maximum<.0068,("BLOCKED_PHOTO_GEOMETRY_EXCESSIVE",tag,maximum)
  for key in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert before[key]==after[key],("BLOCKED_TRANSFORM_UV_TOPOLOGY_DRIFT",tag,key)
  assert before["geometry_sha256"]!=after["geometry_sha256"]
  assert bad==m.nonmanifold(o),"BLOCKED_NEW_NONMANIFOLD"
  report[tag]={"before":before,"after":after,"moved":n,"max_move_m":round(maximum,8),
              "mean_move_m":round(travel/n,8),"existing_nonmanifold_edges":bad}
 assert inv==m.inventory(),"BLOCKED_SCENE_OBJECT_OR_TEXTURE_INVENTORY_CHANGED"
 assert {o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==protected,"BLOCKED_UNRELATED_MESH_CHANGE"
 assert all(m.wheel_holes()),"BLOCKED_ORIGINAL_EIGHT_PUNCH_HOLES"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"status":"R36_GENUINE_ORIGINAL_DERIVED_DASH_GAUGE_STEERING_GEOMETRY_SAVED","slot":"A","car_id":"daytona365",
   "original_PMT":str(PMT),"original_PMT_sha256":SHA["PMT"],
   "initial_native_import":str(ORIG),"initial_native_import_sha256":SHA["ORIG"],
   "native_original_mesh_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
   "source_R35_blend_sha256":SHA["BASE"],"output_R36_blend_sha256":sha(OUT),
   "LHD_Spider_private_photo_sha256":SHA["PHOTO"],"edited_existing_source_backed_P0_meshes":report,
   "protected_other_108_meshes_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
   "original_8_spoke_through_holes":"PASS","preserved_object_material_UV_camera_pivot":True,
   "prior_nonmanifold":"UNRESOLVED_UNCHANGED","native_game_driver_eye":"UNCALIBRATED",
   "seven_genuine_Spider_photo_views":"INCOMPLETE","hosted_GitHub_Actions_private_source":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "car_complete":False,"advance_slot":False,"score_change":0,
   "native_exports_or_runtime_texture_exterior_other_car":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R36_NATIVE_P0_SCENE_SAVED",json.dumps({"SHA":sha(OUT),"moves":{k:v["moved"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 gate()
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
 m=mhelper();a=json.loads(AUDIT.read_text());assert sha(OUT)==a["output_R36_blend_sha256"]
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==108
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["protected_other_108_meshes_sha256"]
 for k,v in a["edited_existing_source_backed_P0_meshes"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert m.state(o)==v["after"],("BLOCKED_REOPEN_GEOMETRY_DRIFT",k)
  assert m.nonmanifold(o)==v["existing_nonmanifold_edges"]
 assert all(m.wheel_holes()),"BLOCKED_REOPEN_SPOKE_HOLES_CLOSED"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R36_UNSAVED_APPROX_DRIVER_EYE")
 cam=bpy.data.objects.new("R36_UNSAVED_APPROX_DRIVER_EYE",cd);sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(OUT)==a["output_R36_blend_sha256"]
 q={"status":"R36_OFFICIAL_BLENDER_4_5_15_REAL_PRIVATE_SOURCE_INDEPENDENT_FRESH_REOPEN_CYCLES_PASS",
   "output_blend_sha256":sha(OUT),"real_Cycles_render_sha256":sha(PNG),
   "existing_P0_mesh_count":len(NAMES),"other_108_meshes":"UNCHANGED","native_steering_holes":8,
   "camera":"APPROXIMATE_NOT_ORIGINAL_GAME","seven_Spider_views":"INCOMPLETE",
   "preexisting_nonmanifold":"UNRESOLVED","GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "complete":False,"score_delta":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R36_REAL_SCENE_FRESH_REOPEN_CYCLES_PASS",json.dumps(q),flush=True)
def compare():
 from PIL import Image
 assert PREV.is_file() and PNG.is_file() and QA.is_file() and not COMP.exists()
 with Image.open(PREV) as a,Image.open(PNG) as b:
  a=a.convert("RGB");b=b.convert("RGB");assert a.size==b.size==(720,480)
  aa=a.load();bb=b.load()
  diff=sum(max(abs(aa[x,y][c]-bb[x,y][c]) for c in range(3))>3 for y in range(480) for x in range(720))
  assert diff>800,("BLOCKED_NO_MEANINGFUL_ACTUAL_RENDER_DELTA",diff)
  sheet=Image.new("RGB",(1440,480));sheet.paste(a,(0,0));sheet.paste(b,(720,0))
  sheet.save(COMP,quality=94,optimize=True)
 q=json.loads(QA.read_text())
 q.update({"R35_R36_changed_pixels_RGB_gt3":diff,"previous_Cycles_sha256":sha(PREV),
           "comparison_Cycles_sha256":sha(COMP)})
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R36_REAL_R35_R36_CYCLES_COMPARISON_PASS",diff,sha(COMP),flush=True)
def run(mode):
 assert BL.is_file()
 scene=ORIG if mode=="origin" else BASE if mode=="build" else OUT
 p=subprocess.run([str(BL),"--background",str(scene),"--threads","2","--python",str(Path(__file__).resolve()),"--",mode],
                  text=True,capture_output=True,timeout=250)
 print(p.stdout[-14000:],flush=True)
 if p.stderr:print("BLENDER_STDERR",p.stderr[-2300:],flush=True)
 if p.returncode:raise RuntimeError("R36_BLENDER_FAILED_"+mode+"_"+str(p.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("origin","build","verify"):
  try:import bpy
  except ImportError:run(mode)
  else:{"origin":original,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("Usage: script.py origin|build|verify|compare")