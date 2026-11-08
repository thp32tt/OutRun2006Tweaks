#!/usr/bin/env python3
"""Slot A Daytona R38: refine only eight existing PMT-derived cockpit meshes.
This is source-bound geometry editing, NOT a vehicle reconstruction. Never export PMT/OVC/GLB.
Private original PMT/import/R36 remain untouched. Existing textures/UV/materials untouched.
"""
from pathlib import Path
import sys, subprocess, json, hashlib, math, importlib.util

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v35_r37.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v36_r38.blend"
HELPER=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
AUDIT=ROOT/"SLOTA_R38_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json"
QA=ROOT/"SLOTA_R38_FRESH_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R38_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R37_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=ROOT/"SLOTA_DAYTONA_R37_R38_REAL_CYCLES_BEFORE_AFTER.jpg"
SHA={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
     "ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
     "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
     "BASE":"bef16148b98554f0892b2aca080b7458139ebe4ee49d86a82d88a19cb551223e",
     "PREV":"ae74a7211f22c64771d828004d6491bc7d675e5b609edb9ae5c0804ac3b897f3"}
NAMES={"pad":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
       "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
       "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
       "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
       "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
       "left":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
       "right":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
       "lower":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"}

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
def references():
 import bpy
 from mathutils.kdtree import KDTree
 result={}
 for tag,name in (("rim",NAMES["rim"]),("spoke",NAMES["spoke"])):
  o=bpy.data.objects[name];kd=KDTree(len(o.data.vertices))
  for v in o.data.vertices:kd.insert(o.matrix_world@v.co,v.index)
  kd.balance();result[tag]=kd
 return result
def anchor(tag,p,kd):
 from mathutils import Vector
 x,y,z=map(float,p)
 t=max(0.,min(1.,(abs(x+.350)-.0945)/.08055)) if tag in ("left","right") else max(0.,min(1.,(.6975-z)/.080))
 target="rim" if t>=.76 else "spoke" if t<=.12 else None
 delta=Vector((0,0,0));dist=None
 if target:
  nearest,index,dist=kd[target].find(p)
  if target=="rim" and dist<.0075:
   # Actual source rim is within a few millimetres; merge the silhouette
   # visually by burying bridge terminal vertices into the existing grip.
   delta+=(nearest-p)*(.80 if t>.94 else .53)
  elif target=="spoke" and dist<.009:
   # Only register to the real source pressing where no factory perforation.
   delta+=(nearest-p)*.38
 arch=math.sin(math.pi*t)**2
 delta.y-=.00165*arch
 if tag in ("left","right"):
  # Steel-sheet edge returns: narrow the outer bridge cap. No cylinders.
  delta.z-=.24*arch*(z-.7918)
 else:
  delta.x-=.24*arch*(x+.350)
 return delta,(target,dist)

def sculpt(tag,p,kd):
 from mathutils import Vector
 x,y,z=map(float,p)
 if tag in ("left","right","lower"):return anchor(tag,p,kd)
 dx=dy=dz=0.
 if tag=="pad":
  driver=smooth(-.655,-.620,x)*(1.-smooth(-.090,-.052,x))
  upper=smooth(.813,.855,z)*(1.-smooth(.930,.961,z))
  face=1.-smooth(.170,.227,y)
  lobes=bump(x,-.508,.125)+bump(x,-.186,.125)
  middle=bump(x,-.350,.078)
  dz=.0048*driver*upper*face*(.62*lobes-.20*middle)
  dy=-.0026*driver*upper*face*(.28+.6*lobes)
 elif tag=="cowl":
  driver=smooth(-.635,-.606,x)*(1.-smooth(-.090,-.053,x))
  face=1.-smooth(.186,.311,y)
  lobes=bump(x,-.505,.114)+bump(x,-.186,.114)
  saddle=bump(x,-.347,.084)
  # Source visor has 2594 existing vertices, rather than a new false bar.
  # Raised peripheral large-gauge brows, dipped broad central saddle.
  dz=.0056*driver*face*(.70*lobes-.23*saddle)
  dy=-.0028*driver*face*(.40+.58*lobes)
 elif tag=="bezel":
  # Existing three original-derived recessed gauge rings and apertures.
  upper=smooth(.754,.798,z)*(1.-smooth(.915,.939,z))
  front=1.-smooth(.146,.168,y)
  driver=smooth(-.638,-.605,x)*(1.-smooth(-.099,-.068,x))
  dy=.0026*driver*front*(.65+.35*upper)
  dz=-.00125*driver*front*upper
 elif tag=="spoke":
  # Roll the existing perforated factory 3-spoke metal pressing in depth
  # (no new bars and no in-plane hole displacements).
  radius=math.hypot(x+.350,z-.790)
  mid=smooth(.017,.035,radius)*(1.-smooth(.145,.174,radius))
  horizontal=smooth(.765,.784,z)*(1.-smooth(.805,.829,z))
  vertical=smooth(.620,.656,z)*(1.-smooth(.754,.781,z))
  axis=math.exp(-((x+.350)/.026)**4)
  arm=max(horizontal,vertical*axis)
  front=1.-smooth(-.297,-.279,y)
  dy=-.0031*mid*arm*front
  # Extra inner hub radius relief; already belongs to PMT object22.
  boss=smooth(.017,.028,radius)*(1.-smooth(.038,.054,radius))
  dy-=.0014*boss*front
 elif tag=="rim":
  # Existing wheel grip; keep wheel pivot, radius, center, local transforms.
  front=1.-smooth(-.295,-.279,y)
  handgrip=smooth(.650,.680,z)*(1.-smooth(.895,.936,z))
  side=bump(abs(x+.35),.154,.065)
  dy=-.00145*front*handgrip*(.43+.57*side)
 return Vector((dx,dy,dz)),(None,None)

def wheel_union_holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 d=bpy.context.evaluated_depsgraph_get()
 bz=[BVHTree.FromObject(bpy.data.objects[NAMES[t]],d) for t in ("spoke","rim","left","right","lower")]
 m=helper()
 checks=[]
 for x,z,r in m.HOLES:
  checks.append(not any(bvh.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.)[2] is not None for bvh in bz))
 return checks

def original():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==ORIG.resolve()
 for n,v in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(n)
  assert o and o.type=="MESH" and len(o.data.vertices)==v,("BLOCKED_INPUT_NATIVE_IMPORT_ID",n)
 print("R38_ORIGINAL_IMPORTED_PMT_NATIVE_MESH_IDS_PASS",flush=True)
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
 assert len(protected)==105,("BLOCKED_UNRELATED_MESH_COUNT",len(protected))
 kd=references()
 report={}
 threshold={"pad":250,"cowl":800,"bezel":700,"spoke":45,"rim":1200,"left":12,"right":12,"lower":12}
 for tag,name in NAMES.items():
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and o.data.users==1,("BLOCKED_SOURCE_NODE",tag)
  before=m.state(o);nonmanifold_before=m.nonmanifold(o)
  inverse=o.matrix_world.inverted()
  n=0;maximum=0.;total=0.
  anchor_before=[];anchor_after=[]
  for v in o.data.vertices:
   p=o.matrix_world@v.co
   d,metadata=sculpt(tag,p,kd)
   if metadata[0] and metadata[1]!=None:
    anchor_before.append(metadata[1])
    nearest,idx,newdist=kd[metadata[0]].find(p+d)
    anchor_after.append(newdist)
   if d.length<=.000008:continue
   v.co=inverse@(p+d);n+=1;maximum=max(maximum,d.length);total+=d.length
  o.data.update();after=m.state(o)
  assert n>=threshold[tag],("BLOCKED_NO_MATERIAL_GEOMETRY_WORK",tag,n)
  assert maximum<.006,("BLOCKED_GEOMETRY_MOVE_EXCESSIVE",tag,maximum)
  for k in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert before[k]==after[k],("BLOCKED_PROTECTED_SOURCE_DRIFT",tag,k)
  assert before["geometry_sha256"]!=after["geometry_sha256"]
  assert nonmanifold_before==m.nonmanifold(o),("BLOCKED_NEW_NONMANIFOLD",tag)
  if tag in ("left","right","lower"):
   assert anchor_before and sum(anchor_after)<sum(anchor_before),("BLOCKED_BRIDGE_NOT_MORE_ANCHORED",tag)
  report[tag]={"before":before,"after":after,"moved":n,"max_move_m":round(maximum,8),
               "mean_move_m":round(total/n,8),"preexisting_nonmanifold_edges":nonmanifold_before,
               "anchor_vertex_distance_sum_before_m":round(sum(anchor_before),7),
               "anchor_vertex_distance_sum_after_m":round(sum(anchor_after),7)}
 assert inv==m.inventory(),"BLOCKED_SOURCE_INVENTORY_CHANGED"
 assert {o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==protected,"BLOCKED_UNRELATED_MESH_CHANGED"
 assert all(m.wheel_holes()) and all(wheel_union_holes()),"BLOCKED_EIGHT_SOURCE_HOLES"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"status":"R38_ORIGINAL_PMT_NATIVE_7_EXISTING_MESHES_MODIFIED","slot":"A","car_id":"daytona365",
   "input_game_PMT_sha256":SHA["PMT"],"first_original_import_sha256":SHA["ORIG"],
   "first_original_native_mesh_objects":["object00_group01_material012_a0","object22_group00_material000_a0"],
   "input_R37_editable_blend_sha256":SHA["BASE"],"output_R38_editable_blend_sha256":sha(OUT),
   "reference_exact_1971_Spider_LHD_sha256":SHA["PHOTO"],
   "actual_existing_PMT_derived_mesh_changes":report,
   "protected_other_105_mesh_signatures_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
   "source_scene_inventory_unchanged":True,"native_spoke_through_holes":8,
   "source_nonmanifold":"UNCHANGED_UNRESOLVED","original_game_eye":"UNCALIBRATED","seven_authentic_photo_views":"INCOMPLETE",
   "GitHub_hosted_real_proprietary_blend":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "vehicle_complete":False,"slot_advance":False,"score_delta":0,"external_exports_textures_VR_other_slot_changes":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R38_NEW_GENUINE_SOURCE_GEOMETRY_SAVED",json.dumps({"sha":sha(OUT),"moves":{k:v["moved"] for k,v in report.items()}}),flush=True)

def verify():
 import bpy
 from mathutils import Vector
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 assert AUDIT.exists() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text());assert sha(OUT)==a["output_R38_editable_blend_sha256"]
 m=helper()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==105
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["protected_other_105_mesh_signatures_sha256"]
 for tag,v in a["actual_existing_PMT_derived_mesh_changes"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert m.state(o)==v["after"],("BLOCKED_REOPEN_MESH_SHA",tag)
  assert m.nonmanifold(o)==v["preexisting_nonmanifold_edges"]
 assert all(m.wheel_holes()) and all(wheel_union_holes()),"BLOCKED_REOPEN_FACTORY_HOLES"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R38_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R38_UNSAVED_APPROX_EYE",cd);sc.collection.objects.link(cam)
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
 assert sha(OUT)==a["output_R38_editable_blend_sha256"]
 q={"status":"R38_LOCAL_OFFICIAL_BLENDER_4_5_15_PRIVATE_PMT_SCENE_FRESH_REOPEN_CYCLES_PASS",
    "R38_blend_sha256":sha(OUT),"R38_Cycles_sha256":sha(PNG),
    "existing_meshes_edited":len(NAMES),"other_meshes_untouched":105,"original_source_8_holes":"PASS",
    "camera":"APPROXIMATE_NOT_GAME_DRIVER_EYE","seven_exact_photo_views":"INCOMPLETE",
    "original_nonmanifold":"UNCHANGED_UNRESOLVED",
    "hosted_Actions_real_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
    "complete":False,"score_change":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R38_REAL_PRIVATE_BLENDER_FRESH_REOPEN_CYCLES_PASS",json.dumps(q),flush=True)

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
 q=json.loads(QA.read_text());q.update({"R37_R38_changed_pixels_RGB_gt3":pixels,
     "R37_Cycles_sha256":SHA["PREV"],"R37_R38_comparison_sha256":sha(COMP)})
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R38_ACTUAL_R36_R38_CYCLES_COMPARE_PASS",pixels,sha(COMP),flush=True)

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