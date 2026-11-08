#!/usr/bin/env python3
"""Slot A Daytona R40: shape original Daytona upper dashboard, gauge cowl, instrument pad, perforated factory 3-spoke, wheel grip, hub column and photographed under-stack return; no added objects.
This is source-bound geometry editing, NOT a vehicle reconstruction. Never export PMT/OVC/GLB.
Private original PMT/import/R39 remain untouched. Existing textures/UV/materials untouched.
"""
from pathlib import Path
import sys, subprocess, json, hashlib, math, importlib.util

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v37_r39.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v38_r40.blend"
HELPER=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
AUDIT=ROOT/"SLOTA_R40_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json"
QA=ROOT/"SLOTA_R40_FRESH_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R40_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R39_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=ROOT/"SLOTA_DAYTONA_R39_R40_REAL_CYCLES_BEFORE_AFTER.jpg"
SHA={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
     "ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
     "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
     "BASE":"85140adfa5fe3c57d79969b22df9c02a113ee22353adf4ba4b843e4839ae9db1",
     "PREV":"37627aa4046dd63f085436eb98e54fcd991f31952d4cca305a133137976e1a8f"}
NAMES={
 "pad":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "upper":"V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "column":"V7_SHORT_SHAFT_AT_WHEEL_HUB",
 "fairing":"V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"
}
HOLE_OBJECTS=[NAMES["spoke"],NAMES["rim"],
 "V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"]

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def gate():
 for key,p in (("PMT",PMT),("ORIG",ORIG),("PHOTO",PHOTO),("BASE",BASE),("PREV",PREV)):
  assert p.is_file() and sha(p)==SHA[key],("BLOCKED_INPUT_FILE_OR_SHA",key,str(p))
 assert BL.is_file() and HELPER.is_file(),"BLOCKED_INPUT_BLENDER_OR_HELPER"
def helper():
 spec=importlib.util.spec_from_file_location("slota_r34_native_source_lib",str(HELPER))
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3-2*t)
def bump(x,c,w):return math.exp(-((x-c)/w)**4)
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)))
 return t*t*(3.-2.*t)
def bump(x,c,w):return math.exp(-((x-c)/w)**4)
def sculpt(tag,p):
 from mathutils import Vector
 x,y,z=map(float,p)
 dx=dy=dz=0.
 if tag=="upper":
  # Deform only existing original-derived dash shell around driver gauge hood.
  driver=smooth(-.720,-.650,x)*(1.-smooth(-.072,-.008,x))
  face=1.-smooth(.280,.470,y)
  top=smooth(.912,.935,z)*(1.-smooth(.973,.997,z))
  large=bump(x,-.508,.130)+bump(x,-.184,.128)
  center=bump(x,-.346,.080)
  dz=.0042*driver*face*top*(.34+.46*large-.13*center)
  dy=-.0025*driver*face*top*(.4+.6*large)
 elif tag=="cowl":
  # Source-derived twin arch around original instrument binnacle.
  driver=smooth(-.646,-.606,x)*(1.-smooth(-.096,-.045,x))
  front=1.-smooth(.183,.291,y)
  lobes=bump(x,-.508,.129)+bump(x,-.185,.127)
  saddle=bump(x,-.347,.087)
  dz=.0046*driver*front*(.65*lobes-.30*saddle)
  dy=-.00215*driver*front*(.40+.50*lobes)
 elif tag=="pad":
  front=1.-smooth(.170,.235,y)
  driver=smooth(-.685,-.625,x)*(1.-smooth(-.085,-.031,x))
  band=smooth(.751,.808,z)*(1.-smooth(.913,.958,z))
  saddle=bump(x,-.348,.090)
  dz=-.0018*driver*front*band*saddle
  dy=.0025*driver*front*band*(.30+.7*saddle)
 elif tag=="spoke":
  # Flatten/roll existing factory 3-spoke in depth without moving its 8 openings.
  r=math.hypot(x+.350,z-.791)
  side=smooth(.774,.787,z)*(1.-smooth(.809,.831,z))*smooth(.029,.069,abs(x+.350))
  lower=smooth(.619,.668,z)*(1.-smooth(.747,.786,z))*(1.-smooth(.013,.039,abs(x+.350)))
  band=smooth(.030,.056,r)*(1.-smooth(.154,.176,r))
  facing=1.-smooth(-.302,-.277,y)
  dy=-.0023*band*facing*max(side,lower)
  inner=smooth(.010,.019,r)*(1.-smooth(.040,.052,r))
  dy-=.0011*inner*facing
 elif tag=="rim":
  # Existing wheel rim cross-section only; avoid adding replacement pipes.
  center=math.hypot(x+.350,z-.792)
  grip=smooth(.163,.174,center)
  side=bump(abs(x+.350),.151,.077)
  front=1.-smooth(-.298,-.281,y)
  dy=-.0014*grip*front*(.45+.55*side)
 elif tag=="column":
  # Existing source-derived hub column/collar, no added cylinders.
  r=math.hypot(x+.350,z-.780)
  ring=smooth(.013,.025,r)*(1.-smooth(.029,.050,r))
  front=1.-smooth(-.301,-.270,y)
  dy=-.00225*ring*front
 elif tag=="fairing":
  # Blender ray at reference camera pixel (488,344) proved this exact old
  # 16v/14f under-stack return caused protruding straight shelf silhouette.
  # Tuck/taper only existing vertices; preserve its original topology.
  height=smooth(.510,.584,z)
  front=1.-smooth(.185,.224,y)
  dy=.0065*front*(.55+.45*height)
  dx=-math.copysign(.0075*height,x)
  dz=-.0025*height
 return Vector((dx,dy,dz))
def wheel_union_holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 deps=bpy.context.evaluated_depsgraph_get()
 objs=[bpy.data.objects[n] for n in HOLE_OBJECTS]
 bvh=[(o,BVHTree.FromObject(o,deps),o.matrix_world.inverted()) for o in objs]
 checks=[]
 for x,z,r in helper().HOLES:
  world=Vector((x,-.55,z));world_dir=Vector((0.,1.,0.))
  filled=False
  for o,tree,inv in bvh:
   if tree.ray_cast(inv@world,inv.to_3x3()@world_dir,1.5)[2] is not None:
    filled=True;break
  checks.append(not filled)
 return checks

def original():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==ORIG.resolve()
 for n,v in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(n)
  assert o and o.type=="MESH" and len(o.data.vertices)==v,("BLOCKED_INPUT_NATIVE_IMPORT_ID",n)
 print("R40_ORIGINAL_IMPORTED_PMT_NATIVE_MESH_IDS_PASS",flush=True)
def build():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==BASE.resolve(),"BLOCKED_INPUT_WRONG_NATIVE_SCENE"
 assert not any(p.exists() for p in (OUT,AUDIT,QA,PNG,COMP)),"BLOCKED_IMMUTABLE_OUTPUT_ALREADY_EXISTS"
 m=helper()
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9732
 assert all(m.wheel_holes()) and all(wheel_union_holes()),"BLOCKED_INPUT_NATIVE_SPOKE_EIGHT_HOLES"
 inv=m.inventory()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==106,("BLOCKED_UNRELATED_MESH_COUNT",len(protected))
 
 report={}
 threshold={"pad":120,"cowl":300,"upper":200,"spoke":500,"rim":700,"column":15,"fairing":8}
 for tag,name in NAMES.items():
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and o.data.users==1,("BLOCKED_SOURCE_NODE",tag)
  before=m.state(o);nonmanifold_before=m.nonmanifold(o)
  inverse=o.matrix_world.inverted()
  n=0;maximum=0.;total=0.

  for v in o.data.vertices:
   p=o.matrix_world@v.co
   d=sculpt(tag,p)
   if d.length<=.000008:continue
   v.co=inverse@(p+d);n+=1;maximum=max(maximum,d.length);total+=d.length
  o.data.update();after=m.state(o)
  assert n>=threshold[tag],("BLOCKED_NO_MATERIAL_GEOMETRY_WORK",tag,n)
  assert maximum<(.019 if tag=="fairing" else .008),("BLOCKED_GEOMETRY_MOVE_EXCESSIVE",tag,maximum)
  for k in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert before[k]==after[k],("BLOCKED_PROTECTED_SOURCE_DRIFT",tag,k)
  assert before["geometry_sha256"]!=after["geometry_sha256"]
  assert nonmanifold_before==m.nonmanifold(o),("BLOCKED_NEW_NONMANIFOLD",tag)
  report[tag]={"before":before,"after":after,"moved":n,"max_move_m":round(maximum,8),
               "mean_move_m":round(total/n,8),"preexisting_nonmanifold_edges":nonmanifold_before}
 assert inv==m.inventory(),"BLOCKED_SOURCE_INVENTORY_CHANGED"
 assert {o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==protected,"BLOCKED_UNRELATED_MESH_CHANGED"
 assert all(m.wheel_holes()) and all(wheel_union_holes()),"BLOCKED_EIGHT_SOURCE_HOLES"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"status":"R40_ORIGINAL_PMT_NATIVE_7_EXISTING_MESHES_MODIFIED","slot":"A","car_id":"daytona365",
   "input_game_PMT_sha256":SHA["PMT"],"first_original_import_sha256":SHA["ORIG"],
   "first_original_native_mesh_objects":["object00_group01_material012_a0","object22_group00_material000_a0"],
   "input_R39_editable_blend_sha256":SHA["BASE"],"output_R40_editable_blend_sha256":sha(OUT),
   "reference_exact_1971_Spider_LHD_sha256":SHA["PHOTO"],
   "actual_existing_PMT_derived_mesh_changes":report,
   "protected_other_106_mesh_signatures_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
   "source_scene_inventory_unchanged":True,"native_spoke_through_holes":8,
   "source_nonmanifold":"UNCHANGED_UNRESOLVED","bridge_join":"R39_BRIDGE_ENDS_PRESERVED_NOT_TOPOLOGICALLY_WELDED","original_game_eye":"UNCALIBRATED","seven_authentic_photo_views":"INCOMPLETE",
   "GitHub_hosted_real_proprietary_blend":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "vehicle_complete":False,"slot_advance":False,"score_delta":0,"external_exports_textures_VR_other_slot_changes":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R40_NEW_GENUINE_SOURCE_GEOMETRY_SAVED",json.dumps({"sha":sha(OUT),"moves":{k:v["moved"] for k,v in report.items()}}),flush=True)

def verify():
 import bpy
 from mathutils import Vector
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 assert AUDIT.exists() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text());assert sha(OUT)==a["output_R40_editable_blend_sha256"]
 m=helper()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==106
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["protected_other_106_mesh_signatures_sha256"]
 for tag,v in a["actual_existing_PMT_derived_mesh_changes"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert m.state(o)==v["after"],("BLOCKED_REOPEN_MESH_SHA",tag)
  assert m.nonmanifold(o)==v["preexisting_nonmanifold_edges"]
 assert all(m.wheel_holes()) and all(wheel_union_holes()),"BLOCKED_REOPEN_FACTORY_HOLES"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R40_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R40_UNSAVED_APPROX_EYE",cd);sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.exists() and PNG.stat().st_size>12000
 assert sha(OUT)==a["output_R40_editable_blend_sha256"]
 q={"status":"R40_LOCAL_OFFICIAL_BLENDER_4_5_15_PRIVATE_PMT_SCENE_FRESH_REOPEN_CYCLES_PASS",
    "R40_blend_sha256":sha(OUT),"R40_Cycles_sha256":sha(PNG),
    "existing_meshes_edited":len(NAMES),"other_meshes_untouched":106,"original_source_8_holes":"PASS",
    "camera":"APPROXIMATE_NOT_GAME_DRIVER_EYE","seven_exact_photo_views":"INCOMPLETE",
    "original_nonmanifold":"UNCHANGED_UNRESOLVED",
    "hosted_Actions_real_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
    "complete":False,"score_change":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R40_REAL_PRIVATE_BLENDER_FRESH_REOPEN_CYCLES_PASS",json.dumps(q),flush=True)

def compare():
 from PIL import Image
 assert PNG.exists() and PREV.exists() and QA.exists() and not COMP.exists()
 with Image.open(PREV) as ap,Image.open(PNG) as bp:
  a=ap.convert("RGB");b=bp.convert("RGB");assert a.size==b.size==(720,480)
  av=a.load();bv=b.load()
  pixels=sum(max(abs(av[x,y][c]-bv[x,y][c]) for c in range(3))>3 for y in range(480) for x in range(720))
  assert pixels>800,("BLOCKED_NO_RENDER_DELTA",pixels)
  sheet=Image.new("RGB",(1440,480));sheet.paste(a,(0,0));sheet.paste(b,(720,0))
  sheet.save(COMP,quality=94,optimize=True)
 q=json.loads(QA.read_text());q.update({"R39_R40_changed_pixels_RGB_gt3":pixels,
     "R39_Cycles_sha256":SHA["PREV"],"R39_R40_comparison_sha256":sha(COMP)})
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R40_ACTUAL_R36_R40_CYCLES_COMPARE_PASS",pixels,sha(COMP),flush=True)

def run(mode):
 gate()
 s=ORIG if mode=="origin" else BASE if mode=="build" else OUT
 p=subprocess.run([str(BL),"--background",str(s),"--threads","2","--python",str(Path(__file__).resolve()),"--",mode],
                  capture_output=True,text=True,timeout=240)
 print(p.stdout[-8000:],flush=True)
 if p.stderr:print("BLENDER_STDERR",p.stderr[-1000:],flush=True)
 if p.returncode:raise RuntimeError("BLOCKED_BLENDER_"+mode+"_"+str(p.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode=="all":
  for action in ("origin","build","verify"):run(action)
  compare()
 elif mode in ("origin","build","verify"):
  try:import bpy
  except ImportError:run(mode)
  else:{"origin":original,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("expected all/origin/build/verify/compare")