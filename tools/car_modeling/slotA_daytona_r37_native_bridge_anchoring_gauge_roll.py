#!/usr/bin/env python3
"""Slot A Daytona R37: refine only seven existing PMT-derived cockpit meshes.
This is source-bound geometry editing, NOT a vehicle reconstruction. Never export PMT/OVC/GLB.
Private original PMT/import/R36 remain untouched. Existing textures/UV/materials untouched.
"""
from pathlib import Path
import sys, subprocess, json, hashlib, math, importlib.util

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v34_r36.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v35_r37.blend"
HELPER=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
AUDIT=ROOT/"SLOTA_R37_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json"
QA=ROOT/"SLOTA_R37_FRESH_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R37_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R36_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=ROOT/"SLOTA_DAYTONA_R36_R37_REAL_CYCLES_BEFORE_AFTER.jpg"
SHA={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
     "ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
     "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
     "BASE":"fb8f676783b72f5933814f21f733944129500803a0b1e0b37ad1176c39336d3f",
     "PREV":"b92c7454373eafc073f6a8b3611076d7e78fb5d66884091247b8ed4b7fcb70d9"}
NAMES={"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
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
 x,y,z=p
 if tag in ("left","right"):
  t=max(0.,min(1.,(abs(x+.350)-.0945)/.08055))
 else:
  t=max(0.,min(1.,(.6975-z)/.080))
 target="rim" if t>.84 else "spoke" if t<.16 else None
 delta=Vector((0,0,0));dist=None
 if target:
  nearest,index,dist=kd[target].find(p)
  bound=.0065 if target=="rim" else .019
  if dist<bound:
   amount=min(.0024,(.25 if target=="rim" else .14)*dist)
   delta=(nearest-p).normalized()*amount if dist>1e-9 else Vector((0,0,0))
 # Pressing curves forwards between the original wheel sheet and rim.
 wave=math.sin(math.pi*t)**2
 delta.y-=.0022*wave
 if tag in ("left","right"):
  delta.z-=.115*wave*(z-.792)
 else:
  delta.x-=.115*wave*(x+.350)
 return delta,(target,dist)
def sculpt(tag,p,kd):
 from mathutils import Vector
 x,y,z=map(float,p)
 if tag in ("left","right","lower"):return anchor(tag,p,kd)
 dx=dy=dz=0.
 if tag=="cowl":
  # Keep the original visor: roll the two main gauge brows and flatten their
  # over-projecting median bridge; photo direction is from driver-left LHD.
  driver=smooth(-.645,-.613,x)*(1.-smooth(-.092,-.062,x))
  upper=smooth(.752,.802,z)*(1.-smooth(.922,.953,z))
  front=1.-smooth(.190,.315,y)
  lobes=bump(x,-.507,.115)+bump(x,-.187,.115)
  middle=bump(x,-.349,.080)
  dz=.0040*driver*upper*front*(.53*lobes-.25*middle)
  dy=-.0022*driver*upper*front*(.38+.45*lobes)
 elif tag=="bezel":
  front=1.-smooth(.147,.170,y)
  crown=smooth(.750,.810,z)*(1.-smooth(.907,.939,z))
  driver=smooth(-.647,-.612,x)*(1.-smooth(-.101,-.061,x))
  dy=.0020*front*crown*driver
  dz=-.0011*front*crown*driver
 elif tag=="spoke":
  r=math.hypot(x+.350,z-.785)
  boss=smooth(.021,.030,r)*(1.-smooth(.052,.062,r))
  front=1.-smooth(-.296,-.277,y)
  dy=-.0022*boss*front
  # Protect actual original punched holes away from the central hub.
 elif tag=="rim":
  # Keep wheel external diameter and circular source topology; reshape its
  # front grip in depth, maintaining steering animation anchor.
  front=1.-smooth(-.294,-.277,y)
  grip=smooth(.660,.696,z)*(1.-smooth(.866,.927,z))
  sides=bump(abs(x+.350),.144,.081)
  dy=-.0013*front*grip*(.6+.4*sides)
 return Vector((dx,dy,dz)),(None,None)

def original():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==ORIG.resolve()
 for n,v in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(n)
  assert o and o.type=="MESH" and len(o.data.vertices)==v,("BLOCKED_INPUT_NATIVE_IMPORT_ID",n)
 print("R37_ORIGINAL_IMPORTED_PMT_NATIVE_MESH_IDS_PASS",flush=True)
def build():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==BASE.resolve(),"BLOCKED_INPUT_WRONG_NATIVE_SCENE"
 assert not any(p.exists() for p in (OUT,AUDIT,QA,PNG,COMP)),"BLOCKED_IMMUTABLE_OUTPUT_ALREADY_EXISTS"
 m=helper()
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9732
 assert all(m.wheel_holes()),"BLOCKED_INPUT_NATIVE_SPOKE_EIGHT_HOLES"
 inv=m.inventory()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==106,("BLOCKED_UNRELATED_MESH_COUNT",len(protected))
 kd=references()
 report={}
 threshold={"cowl":800,"bezel":700,"spoke":45,"rim":1200,"left":12,"right":12,"lower":12}
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
 assert all(m.wheel_holes()),"BLOCKED_EIGHT_SOURCE_HOLES"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"status":"R37_ORIGINAL_PMT_NATIVE_7_EXISTING_MESHES_MODIFIED","slot":"A","car_id":"daytona365",
   "input_game_PMT_sha256":SHA["PMT"],"first_original_import_sha256":SHA["ORIG"],
   "first_original_native_mesh_objects":["object00_group01_material012_a0","object22_group00_material000_a0"],
   "input_R36_editable_blend_sha256":SHA["BASE"],"output_R37_editable_blend_sha256":sha(OUT),
   "reference_exact_1971_Spider_LHD_sha256":SHA["PHOTO"],
   "actual_existing_PMT_derived_mesh_changes":report,
   "protected_other_106_mesh_signatures_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
   "source_scene_inventory_unchanged":True,"native_spoke_through_holes":8,
   "source_nonmanifold":"UNCHANGED_UNRESOLVED","original_game_eye":"UNCALIBRATED","seven_authentic_photo_views":"INCOMPLETE",
   "GitHub_hosted_real_proprietary_blend":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "vehicle_complete":False,"slot_advance":False,"score_delta":0,"external_exports_textures_VR_other_slot_changes":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R37_NEW_GENUINE_SOURCE_GEOMETRY_SAVED",json.dumps({"sha":sha(OUT),"moves":{k:v["moved"] for k,v in report.items()}}),flush=True)

def verify():
 import bpy
 from mathutils import Vector
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 assert AUDIT.exists() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text());assert sha(OUT)==a["output_R37_editable_blend_sha256"]
 m=helper()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==106
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["protected_other_106_mesh_signatures_sha256"]
 for tag,v in a["actual_existing_PMT_derived_mesh_changes"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert m.state(o)==v["after"],("BLOCKED_REOPEN_MESH_SHA",tag)
  assert m.nonmanifold(o)==v["preexisting_nonmanifold_edges"]
 assert all(m.wheel_holes()),"BLOCKED_REOPEN_FACTORY_HOLES"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R37_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R37_UNSAVED_APPROX_EYE",cd);sc.collection.objects.link(cam)
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
 assert sha(OUT)==a["output_R37_editable_blend_sha256"]
 q={"status":"R37_LOCAL_OFFICIAL_BLENDER_4_5_15_PRIVATE_PMT_SCENE_FRESH_REOPEN_CYCLES_PASS",
    "R37_blend_sha256":sha(OUT),"R37_Cycles_sha256":sha(PNG),
    "existing_meshes_edited":len(NAMES),"other_meshes_untouched":106,"original_source_8_holes":"PASS",
    "camera":"APPROXIMATE_NOT_GAME_DRIVER_EYE","seven_exact_photo_views":"INCOMPLETE",
    "original_nonmanifold":"UNCHANGED_UNRESOLVED",
    "hosted_Actions_real_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
    "complete":False,"score_change":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R37_REAL_PRIVATE_BLENDER_FRESH_REOPEN_CYCLES_PASS",json.dumps(q),flush=True)

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
 q=json.loads(QA.read_text());q.update({"R36_R37_changed_pixels_RGB_gt3":pixels,
     "R36_Cycles_sha256":SHA["PREV"],"R36_R37_comparison_sha256":sha(COMP)})
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R37_ACTUAL_R36_R37_CYCLES_COMPARE_PASS",pixels,sha(COMP),flush=True)

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