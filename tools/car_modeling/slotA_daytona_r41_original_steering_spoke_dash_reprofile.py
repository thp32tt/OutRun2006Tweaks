#!/usr/bin/env python3
"""Ferrari Daytona Slot A R41: only native PMT-derived cockpit steering/dash geometry.
Immutable game PMT, original imported .blend and source R40. No car creation, GLB,
native exports, game integration, external model, texture, PBR or VR edits.
"""
from pathlib import Path
import hashlib, json, math, sys, subprocess, importlib.util

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v38_r40.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v39_r41.blend"
HELP=ROOT/"slotA_daytona_r34_original_gauge_visor_native_wheel_relief.py"
PREV=ROOT/"SLOTA_DAYTONA_R40_AFTER_REAL_CYCLES_APPROX_EYE.png"
PNG=ROOT/"SLOTA_DAYTONA_R41_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=ROOT/"SLOTA_DAYTONA_R40_R41_REAL_CYCLES_BEFORE_AFTER.jpg"
AUDIT=ROOT/"SLOTA_R41_SOURCE_WHEEL_DASH_AUDIT.json"
QA=ROOT/"SLOTA_R41_FRESH_REOPEN_REAL_CYCLES.json"
HASH={
 "PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
 "BASE":"e95bce97fc3e593577fef4db476d19f8a40fab22ad03dc5d1a922fc312ba6cce",
 "PREV":"3722e798efdfdce010f49d11cdb5890e076100606f291177302743b173891ed2"
}
NAMES={
 "pad":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "left":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "right":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "lower":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"
}
BRIDGES=("left","right","lower")
SOURCE_IDS=("object00_group01_material012_a0","object22_group00_material000_a0")

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()

def gate():
 for key,p in (("PMT",PMT),("ORIG",ORIG),("PHOTO",PHOTO),("BASE",BASE),("PREV",PREV)):
  assert p.is_file() and sha(p)==HASH[key],("BLOCKED_INPUT_FILE_OR_SHA",key,str(p))
 assert HELP.is_file() and BL.is_file(),"BLOCKED_INPUT_BLENDER_OR_SOURCE_HELPER"

def lib():
 spec=importlib.util.spec_from_file_location("slota_original_daytona_native_helper",str(HELP))
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 return module

def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3-2*t)

def bump(x,c,w):
 return math.exp(-((x-c)/w)**4)

def source_kdtree(name):
 from mathutils import kdtree
 obj=__import__("bpy").data.objects[name]
 kd=kdtree.KDTree(len(obj.data.vertices))
 for i,v in enumerate(obj.data.vertices):
  kd.insert(obj.matrix_world@v.co,i)
 kd.balance()
 return kd

def reshape(tag,world,kd):
 from mathutils import Vector
 x,y,z=[float(v) for v in world]
 dx=dy=dz=0.
 if tag in BRIDGES:
  # EXISTING old 20-vertex sheet bridges, never new cylinders/tubes.
  # Pull their source ends toward the actual native stamped spoke and
  # their outer ends into the existing black rim. No unsupported weld claim.
  side=abs(x+.350)
  t=smooth(.0945,.175,side) if tag!="lower" else smooth(.615,.6975,z)*-1.+1.
  tgt="spoke" if t<.18 else "rim" if t>.80 else None
  if tgt:
   near,idx,dist=kd[tgt].find(world)
   if dist<.018:
    d=(near-world)*(.82 if t<.18 else .90)
    dx,dy,dz=d.x,d.y,d.z
  belly=math.sin(math.pi*max(0.,min(1.,t)))**2
  # Flatten the inherited rectangular pipe silhouette into a low-relief
  # sheet, with no new objects or cross-section thickening.
  dy+=.0009*belly*(-1 if y<-.287 else 1)
 elif tag=="spoke":
  r=math.hypot(x+.350,z-.792)
  span=smooth(.034,.062,r)*(1.-smooth(.154,.169,r))
  lateral=smooth(.778,.788,z)*(1.-smooth(.804,.822,z))
  vertical=(1.-smooth(.018,.042,abs(x+.350)))*smooth(.627,.659,z)*(1.-smooth(.757,.784,z))
  front=1.-smooth(-.302,-.275,y)
  # Fine stamping in depth; keep all perforation x/z centers unchanged.
  dy=-.00175*span*max(lateral,vertical)*front
  hub=smooth(.014,.023,r)*(1.-smooth(.044,.054,r))
  dy-=.00080*hub*front
 elif tag=="rim":
  r=math.hypot(x+.350,z-.792)
  outer=smooth(.166,.178,r)
  left_right=bump(abs(x+.350),.146,.083)
  front=1.-smooth(-.294,-.279,y)
  dy=-.0011*outer*front*(.50+.50*left_right)
 elif tag=="bezel":
  driver=smooth(-.630,-.600,x)*(1.-smooth(-.103,-.073,x))
  ring=smooth(.777,.812,z)*(1.-smooth(.912,.935,z))
  front=1.-smooth(.145,.166,y)
  dy=-.00125*driver*front*(.50+.5*ring)
 elif tag=="cowl":
  driver=smooth(-.653,-.614,x)*(1.-smooth(-.098,-.052,x))
  face=1.-smooth(.191,.300,y)
  left=bump(x,-.508,.128);right=bump(x,-.187,.125)
  saddle=bump(x,-.348,.091)
  dz=.0024*driver*face*(.67*(left+right)-.43*saddle)
  dy=-.00115*driver*face*(.50+.5*(left+right))
 elif tag=="pad":
  driver=smooth(-.686,-.621,x)*(1.-smooth(-.095,-.044,x))
  face=1.-smooth(.180,.234,y)
  band=smooth(.774,.820,z)*(1.-smooth(.903,.940,z))
  # Recess the artificial dead-flat under-gauge ledge; shape original pad.
  dy=.00235*driver*face*band
  dz=-.00135*driver*face*band*bump(x,-.351,.126)
 return Vector((dx,dy,dz))

def all_open_holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 deps=bpy.context.evaluated_depsgraph_get()
 objects=[bpy.data.objects[NAMES[i]] for i in ("spoke","rim","left","right","lower")]
 bvhs=[(BVHTree.FromObject(o,deps),o.matrix_world.inverted()) for o in objects]
 passed=[]
 for x,z,r in lib().HOLES:
  source=Vector((x,-.55,z));direction=Vector((0.,1.,0.))
  passed.append(all(tree.ray_cast(inv@source,inv.to_3x3()@direction,1.5)[2] is None for tree,inv in bvhs))
 return passed

def origin():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==ORIG.resolve()
 for name,count in zip(SOURCE_IDS,(13,61)):
  obj=bpy.data.objects.get(name)
  assert obj and obj.type=="MESH" and len(obj.data.vertices)==count,("BLOCKED_NATIVE_OBJECT",name)
 print("R41_ORIGINAL_GAME_PMT_IMPORT_VERIFIED",flush=True)

def build():
 import bpy
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==BASE.resolve()
 assert not any(p.exists() for p in (OUT,PNG,AUDIT,QA,COMP)),"BLOCKED_IMMUTABLE_RESULT_EXISTS"
 m=lib()
 inv=m.inventory()
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9732
 assert all(m.wheel_holes()) and all(all_open_holes()),"BLOCKED_INPUT_8_THROUGH_HOLES"
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==105,("BLOCKED_UNRELATED_MESH_COUNT",len(protected))
 kd={"spoke":source_kdtree(NAMES["spoke"]),"rim":source_kdtree(NAMES["rim"])}
 report={}
 thresholds={"pad":150,"cowl":400,"bezel":400,"spoke":1000,"rim":500,"left":4,"right":4,"lower":4}
 for tag,name in NAMES.items():
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and o.data.users==1,("BLOCKED_MESH_ID",tag)
  pre=m.state(o);bad=m.nonmanifold(o);invmat=o.matrix_world.inverted()
  n=0;mx=0.;mean=0.
  for v in o.data.vertices:
   world=o.matrix_world@v.co
   delta=reshape(tag,world,kd)
   if delta.length<.000006:continue
   assert delta.length<.0175,("BLOCKED_EXCESSIVE_VERTEX_MOVE",tag,v.index,delta.length)
   v.co=invmat@(world+delta)
   n+=1;mx=max(mx,delta.length);mean+=delta.length
  o.data.update()
  post=m.state(o)
  assert n>=thresholds[tag],("BLOCKED_INSUFFICIENT_REAL_GEOMETRY",tag,n)
  for k in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert pre[k]==post[k],("BLOCKED_INVENTORY_OR_MATERIAL_DRIFT",tag,k)
  assert pre["geometry_sha256"]!=post["geometry_sha256"],("BLOCKED_NO_GEOMETRY_DELTA",tag)
  assert bad==m.nonmanifold(o),("BLOCKED_NEW_NONMANIFOLD",tag)
  report[tag]={"before":pre,"after":post,"moved":n,"max_move_m":round(mx,8),
               "mean_move_m":round(mean/n,8),"preexisting_nonmanifold_edges":bad}
 assert inv==m.inventory(),"BLOCKED_NATIVE_SCENE_INVENTORY_CHANGED"
 assert {o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==protected,"BLOCKED_OTHER_MESH_CHANGED"
 assert all(m.wheel_holes()) and all(all_open_holes()),"BLOCKED_WHEEL_HOLE_OCCLUSION"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 audit={"revision":"R41","slot":"A","car":"daytona365",
  "original_readonly_PMT_SHA256":HASH["PMT"],"original_import_blend_SHA256":HASH["ORIG"],
  "original_PMT_mesh_names":list(SOURCE_IDS),"input_R40_SHA256":HASH["BASE"],
  "new_private_R41_SHA256":sha(OUT),"exact_Spider_LHD_photo_sha256":HASH["PHOTO"],
  "source_original_derived_edited_objects":report,
  "protected_105_other_meshes_sig_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
  "8_spoke_open_holes":"PASS","bridge_visual_reanchor":"SOURCE_SHEET_ENDS_NOT_TOPOLOGICALLY_WELDED",
  "original_game_eye":"NOT_CALIBRATED","seven_authentic_photo_views":"INCOMPLETE",
  "GitHub_Actions_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"slot_advance":False,"score_delta":0}
 AUDIT.write_text(json.dumps(audit,indent=2),encoding="utf8")
 print("R41_NEW_REAL_ORIGINAL_GEOMETRY_SAVED",json.dumps({"blend_sha":sha(OUT),"moved":{k:v["moved"] for k,v in report.items()}}),flush=True)

def verify():
 import bpy
 from mathutils import Vector
 gate()
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 assert AUDIT.exists() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text());assert sha(OUT)==a["new_private_R41_SHA256"]
 m=lib()
 protected={o.name:m.sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==105
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["protected_105_other_meshes_sig_sha256"]
 for tag,record in a["source_original_derived_edited_objects"].items():
  o=bpy.data.objects[record["after"]["name"]]
  assert m.state(o)==record["after"],("BLOCKED_REOPEN_POST_SHA",tag)
  assert m.nonmanifold(o)==record["preexisting_nonmanifold_edges"]
 assert all(m.wheel_holes()) and all(all_open_holes()),"BLOCKED_REOPEN_8_ORIGINAL_HOLES"
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R41_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R41_UNSAVED_APPROX_EYE",cd);sc.collection.objects.link(cam)
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
 assert sha(OUT)==a["new_private_R41_SHA256"]
 qa={"status":"R41_OFFICIAL_BLENDER_4_5_15_PRIVATE_NATIVE_SCENE_SEPARATE_REOPEN_CYCLES_PASS",
   "private_R41_sha256":sha(OUT),"real_cycles_sha256":sha(PNG),
   "original_native_8_through_holes":"PASS","other_105_source_meshes_unchanged":"PASS",
   "real_game_eye":"NOT_CALIBRATED","seven_photo_views":"INCOMPLETE",
   "original_nonmanifold":"UNRESOLVED_NOT_WORSENED",
   "bridge_watertight":"NOT_WELDED",
   "github_hosted_real_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
   "complete":False,"score_delta":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("R41_PRIVATE_NATIVE_FRESH_REOPEN_CYCLES_PASS",json.dumps(qa),flush=True)

def compare():
 from PIL import Image
 assert PREV.exists() and PNG.exists() and QA.exists() and not COMP.exists()
 with Image.open(PREV) as pa,Image.open(PNG) as pb:
  a=pa.convert("RGB");b=pb.convert("RGB")
  assert a.size==b.size==(720,480)
  av,bv=a.load(),b.load()
  delta=sum(max(abs(av[x,y][c]-bv[x,y][c]) for c in range(3))>3
           for y in range(480) for x in range(720))
  assert delta>200,("BLOCKED_NO_MEASURABLE_REAL_RENDER_DELTA",delta)
  out=Image.new("RGB",(1440,480));out.paste(a,(0,0));out.paste(b,(720,0))
  out.save(COMP,quality=94,optimize=True)
 qa=json.loads(QA.read_text())
 qa.update({"R40_R41_pixels_RGB_gt3":delta,"comparison_SHA256":sha(COMP)})
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("R41_NATIVE_CYCLES_BEFORE_AFTER_PASS",delta,sha(COMP),flush=True)

def run(mode):
 gate()
 scene=ORIG if mode=="origin" else BASE if mode=="build" else OUT
 p=subprocess.run([str(BL),"--background",str(scene),"--threads","2",
                   "--python",str(Path(__file__).resolve()),"--",mode],
                  capture_output=True,text=True,timeout=240)
 print(p.stdout[-7000:],flush=True)
 if p.stderr:print("BLENDER_STDERR",p.stderr[-1400:],flush=True)
 if p.returncode:raise RuntimeError("BLOCKED_BLENDER_"+mode+"_"+str(p.returncode))

if __name__=="__main__":
 mode=sys.argv[-1]
 if mode=="all":
  for step in ("origin","build","verify"):run(step)
  compare()
 elif mode in ("origin","build","verify"):
  try:import bpy
  except ImportError:run(mode)
  else:{"origin":origin,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("expected all/origin/build/verify/compare")
