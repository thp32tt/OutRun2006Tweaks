#!/usr/bin/env python3
"""Daytona Slot A R34: original source-native driver-eye gauge hood shaping and three-spoke hub relief.
Modify ONLY coordinates of six EXISTING source-derived cockpit mesh objects
inside a cloned original OutRun2006 PMT-derived Blender scene.
No new mesh/model, no GLB, textures, materials, native exports or game integration.
The original PMT/import and photo remain immutable and private.
"""
from pathlib import Path
import sys, subprocess, hashlib, json, math, struct
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v31_r33.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v32_r34.blend"
AUDIT=ROOT/"SLOTA_R34_ACTUAL_SOURCE_GAUGE_HUB_AUDIT.json"
QA=ROOT/"SLOTA_R34_INDEPENDENT_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R34_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=ROOT/"SLOTA_DAYTONA_R33_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R33_R34_REAL_CYCLES_BEFORE_AFTER.jpg"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"PMT":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
      "ORIG":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
      "PHOTO":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
      "BASE":"aaaeaaa09af1d971c34d15373d54f3c89e20ca76c1208af9a6c7838852711a3d"}
NAMES={
 "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "pad":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "lower":"V8_21_SOURCE_LOWER_GAUGE_SHROUD"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
       (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
       (-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def blocked(m):raise RuntimeError("BLOCKED_INPUT_"+m)
def gate():
 for k,p in (("PMT",PMT),("ORIG",ORIG),("PHOTO",PHOTO),("BASE",BASE)):
  if not p.is_file() or sha(p)!=HASH[k]:blocked("MISSING_OR_BAD_SHA_"+k)
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3-2*t)
def sig(o):
 h=hashlib.sha256()
 for v in o.data.vertices:
  h.update(struct.pack("<ddd",round(v.co.x,8),round(v.co.y,8),round(v.co.z,8)))
 for p in o.data.polygons:
  h.update((",".join(str(i) for i in p.vertices)+":"+str(p.material_index)+";").encode())
 return h.hexdigest()
def uv(o):
 return hashlib.sha256(repr([(layer.name,[(round(a.uv.x,8),round(a.uv.y,8)) for a in layer.data])
                            for layer in o.data.uv_layers]).encode()).hexdigest()
def matrix(o):
 return [[round(float(v),9) for v in row] for row in o.matrix_world]
def state(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
         "geometry_sha256":sig(o),"uv_sha256":uv(o),
         "world_matrix":matrix(o),"materials":[m.name if m else None for m in o.data.materials],
         "hide_render":bool(o.hide_render)}
def inventory():
 import bpy
 return {"objects":sorted(bpy.data.objects.keys()),
         "meshes":sorted(bpy.data.meshes.keys()),
         "materials":sorted(bpy.data.materials.keys()),
         "curves":sorted(bpy.data.curves.keys()),
         "images":{a.name:(tuple(a.size),bool(a.packed_file),a.filepath) for a in bpy.data.images},
         "cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}}
def components(o):
 # Existing Blender mesh edge connectivity; does NOT generate or alter geometry.
 adj=[set() for _ in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 remaining=set(range(len(adj)));result=[]
 while remaining:
  seed=remaining.pop();stack=[seed];group=[seed]
  while stack:
   for k in adj[stack.pop()]:
    if k in remaining:remaining.remove(k);stack.append(k);group.append(k)
  result.append(group)
 return sorted(result,key=len,reverse=True)
def wheel_holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 bvh=BVHTree.FromObject(bpy.data.objects[NAMES["spoke"]],bpy.context.evaluated_depsgraph_get())
 def hit(x,z):return bvh.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.0)[2] is not None
 return [(not hit(x,z)) and hit(x+1.6*r,z) for x,z,r in HOLES]
def nonmanifold(o):
 import bmesh
 bm=bmesh.new();bm.from_mesh(o.data)
 edges=sum(not e.is_manifold for e in bm.edges)
 bm.free();return edges
def displace(tag,p,is_native_hub):
 from mathutils import Vector
 x,y,z=p;dx=dy=dz=0.
 if tag=="bezel":
  # The existing original-PMT-derived three metal gauge rings stay registered.
  # Gently deepen the upper rolled lip, preserving real gauge bore size/artwork.
  front=1.-smooth(.147,.161,y)
  above=smooth(.755,.824,z)
  dy=-.00155*front*(.65+.35*above)
  dz=.00038*front*(1.-smooth(.861,.902,z))
 elif tag=="pad":
  # Original-derived dashboard leather pad. Shape the Daytona factory raised
  # driver-side instrument shoulder only; keep passenger side/upper reach fixed.
  driver=smooth(-.695,-.620,x)*(1.-smooth(-.095,-.025,x))
  zband=smooth(.708,.759,z)*(1.-smooth(.911,.962,z))
  forward=1.-smooth(.178,.237,y)
  dy=.0035*driver*zband*forward
  dz=.0011*driver*zband*forward*math.tanh((z-.827)/.066)
 elif tag=="cowl":
  # True full-width inherited instrument-visor sheet, 2-lobed arch sculpt.
  # Sculpt smooth large-gauge eyebrow peaks above the driver's real instrument
  # positions without creating any new dashboard mesh/material or gauge art.
  left=math.exp(-((x+.510)/.125)**4)
  right=math.exp(-((x+.183)/.123)**4)
  center=math.exp(-((x+.347)/.31)**4)
  front=1.-smooth(.198,.305,y)
  dz=.00365*front*(.31*center+.69*max(left,right))
  dy=-.00165*front*center
 elif tag=="spoke":
  # Existing first-game-PMT wheel stem's 190-vertex boss; not a loose pipe
  # or newly created steering hub. Eight source perforations remain protected.
  if is_native_hub:
   r=math.hypot(x+.350,z-.79174)
   boss=smooth(.009,.021,r)*(1.-smooth(.037,.046,r))
   dy=-.00172*boss
 elif tag=="rim":
  # Preserve true rim circle diameter/animation pivot, sculpt the existing
  # factory-derived grip cross-section with small front-facing relief.
  top=smooth(.734,.891,z)
  forward=1.-smooth(-.2903,-.2781,y)
  side=.48+.52*math.exp(-((abs(x+.35)-.124)/.068)**2)
  dy=-.00096*forward*(.35+.65*top)*side
 elif tag=="lower":
  # Return of existing source-derived lower binnacle under the main gauges.
  driver=smooth(-.674,-.610,x)*(1.-smooth(-.100,-.046,x))
  front=1.-smooth(.165,.205,y)
  dy=-.00215*driver*front
  dz=-.00085*driver*front
 return Vector((dx,dy,dz))
def original():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==ORIG.resolve(), "WRONG_FIRST_SOURCE"
 gate()
 for name,count in (("object00_group01_material012_a0",13),
                    ("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and len(o.data.vertices)==count,("BLOCKED_NATIVE_IMPORT_ID",name)
 print("R34_ORIGINAL_GAME_PMT_IMPORT_OBJECTS_SHA_PASS",flush=True)
def build():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==BASE.resolve(), "BLOCKED_NOT_R33_ORIGINAL_DERIVATIVE"
 gate()
 assert all(not p.exists() for p in (OUT,AUDIT,QA,PNG,COMPARE)),"BLOCKED_IMMUTABLE_OUTPUT_EXISTS"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].type=="MESH"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9732
 assert all(wheel_holes()),"BLOCKED_ORIGINAL_SPOKE_THROUGH_HOLES"
 inv=inventory()
 protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==107,("BLOCKED_PROTECTED_MESH_COUNT",len(protected))
 bezel_components=components(bpy.data.objects[NAMES["bezel"]])
 assert sorted(len(g) for g in bezel_components)==[903,903,1351],"BLOCKED_GAUGE_COMPONENT_SIGNATURE"
 wheel=bpy.data.objects[NAMES["spoke"]]
 wcomps=components(wheel)
 assert len(wcomps)==12 and sum(len(g)==190 for g in wcomps)==1, "BLOCKED_NATIVE_STEERING_HUB_SIGNATURE"
 center_comp=next(g for g in wcomps if len(g)==190)
 hub_verts=set(center_comp)
 hub_center=[sum((wheel.matrix_world@wheel.data.vertices[i].co)[k] for i in center_comp)/190 for k in range(3)]
 assert abs(hub_center[0]+.35)<.002 and abs(hub_center[2]-.78047)<.003, "BLOCKED_WRONG_NATIVE_HUB"
 report={}
 for tag,name in NAMES.items():
  o=bpy.data.objects[name];assert o.type=="MESH" and o.data.users==1
  before=state(o);bad_edges=nonmanifold(o);invmat=o.matrix_world.inverted()
  moved=0;max_delta=0.;s=0.
  for v in o.data.vertices:
   world=o.matrix_world@v.co
   delta=displace(tag,world,tag=="spoke" and v.index in hub_verts)
   if delta.length<.000008:continue
   v.co=invmat@(world+delta)
   moved+=1;max_delta=max(max_delta,delta.length);s+=delta.length
  o.data.update();after=state(o)
  min_change={"bezel":900,"pad":100,"cowl":700,"spoke":20,"rim":800,"lower":60}[tag]
  assert moved>=min_change,("BLOCKED_INSUFFICIENT_ACTUAL_MESH_MODIFICATION",tag,moved)
  assert max_delta<.0055,("BLOCKED_EXCESSIVE_SOURCE_VERTEX_DISPLACEMENT",tag,max_delta)
  for k in ("name","vertices","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert before[k]==after[k],("BLOCKED_ASSET_TRANSFORM_OR_MATERIAL_DRIFT",tag,k)
  assert before["geometry_sha256"]!=after["geometry_sha256"]
  assert nonmanifold(o)==bad_edges,("BLOCKED_NEW_NONMANIFOLD",tag)
  report[tag]={"before":before,"after":after,"moved":moved,
               "max_move_m":round(max_delta,8),"mean_move_m":round(s/moved,8),
               "preexisting_nonmanifold_edges":bad_edges}
 assert inventory()==inv,"BLOCKED_SCENE_CAMERA_OR_MATERIAL_INVENTORY_CHANGED"
 assert {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==protected
 assert all(wheel_holes()),"BLOCKED_EIGHT_NATIVE_SOURCE_HOLES_FILLED"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 a={"status":"R34_PRIVATE_ORIGINAL_DERIVED_GAUGE_VISOR_AND_NATIVE_WHEEL_RELIEF_SAVED",
    "slot":"A","car_id":"daytona365",
    "original_game_PMT_file":str(PMT),"original_game_PMT_sha256":HASH["PMT"],
    "original_import_blend_file":str(ORIG),"original_import_blend_sha256":HASH["ORIG"],
    "original_object_names":["object00_group01_material012_a0","object22_group00_material000_a0"],
    "base_R33_blend_sha256":HASH["BASE"],"result_R34_private_blend_sha256":sha(OUT),
    "verified_exact_variant_Spider_LHD_photo_sha256":HASH["PHOTO"],
    "changed_existing_original_derived_source_objects":report,
    "untouched_107_original_derived_mesh_signatures_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
    "three_gauge_source_component_sizes":[len(x) for x in bezel_components],
    "native_factory_wheel_hub_component_vertices":len(hub_verts),
    "factory_eight_steering_through_holes":"PASS",
    "object_camera_pivots_UV_material_texture_inventory_unchanged":True,
    "private_originals_read_only":True,
    "original_game_eye_alignment":"NOT_CALIBRATED","seven_real_Spider_photos":"INCOMPLETE",
    "hosted_Actions_private_game_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
    "vehicle_complete":False,"advance_slot_A":False,"score_change":0,
    "prohibited_native_exports_or_game_integration":0}
 AUDIT.write_text(json.dumps(a,indent=2),encoding="utf8")
 print("R34_OFFICIAL_BLENDER_REAL_ORIGINAL_DERIVED_SOURCE_SAVED",json.dumps({"blend_sha256":sha(OUT),
   "mesh_changes":{k:v["moved"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve(),"BLOCKED_NOT_FRESH_R34_OPEN"
 gate()
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text())
 assert sha(OUT)==a["result_R34_private_blend_sha256"]
 protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(protected)==107
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==a["untouched_107_original_derived_mesh_signatures_sha256"]
 for k,v in a["changed_existing_original_derived_source_objects"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert state(o)==v["after"],("BLOCKED_BLENDER_REOPEN_CHANGED_MESH",k)
  assert nonmanifold(o)==v["preexisting_nonmanifold_edges"]
 assert all(wheel_holes())
 # Temporary approximate camera is never saved to the edited original file.
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R34_UNSAVED_APPROX_EYE")
 cam=bpy.data.objects.new("R34_UNSAVED_APPROX_EYE",cd)
 sc.collection.objects.link(cam);cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(OUT)==a["result_R34_private_blend_sha256"]
 q={"status":"R34_ORIGINAL_SOURCE_PRIVATE_SCENE_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_CYCLES_PASS",
 "R34_editable_blend_sha256":sha(OUT),"R34_render_sha256":sha(PNG),
 "render":[720,480,3],"six_existing_original_derived_meshes_verified":True,
 "other_107_meshes_identical":True,"native_spoke_8_holes":"PASS",
 "preexisting_nonmanifold":"UNRESOLVED_NOT_WORSENED",
 "exact_original_game_eye":"NOT_CALIBRATED","seven_authentic_Spider_angles":"INCOMPLETE",
 "hosted_GitHub_Actions_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"slotA_advance":False,"score_change":0}
 QA.write_text(json.dumps(q,indent=2),encoding="utf8")
 print("R34_FRESH_BLENDER_REOPEN_TRUE_CYCLES_PASS",json.dumps(q),flush=True)
def compare():
 from PIL import Image
 assert PREV.is_file() and PNG.is_file() and QA.is_file()
 with Image.open(PREV) as i,Image.open(PNG) as j:
  a=i.convert("RGB");b=j.convert("RGB");assert a.size==b.size==(720,480)
  ai,bi=a.load(),b.load()
  diff=sum(max(abs(ai[x,y][k]-bi[x,y][k]) for k in range(3))>3
           for y in range(480) for x in range(720))
  assert diff>500,("BLOCKED_NO_USEFUL_RENDER_CHANGE",diff)
  im=Image.new("RGB",(1440,480));im.paste(a,(0,0));im.paste(b,(720,0))
  im.save(COMPARE,quality=93,optimize=True)
 qa=json.loads(QA.read_text())
 qa.update({"R33_vs_R34_changed_pixels_RGB_gt3":diff,"R33_real_render_sha256":sha(PREV),
            "R34_real_render_sha256":sha(PNG),"R33_R34_real_compare_sha256":sha(COMPARE)})
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("R34_REAL_MODEL_BEFORE_AFTER_COMPARE_PASS",diff,sha(COMPARE),flush=True)
def run(mode):
 assert BLENDER.is_file(),"BLOCKED_MISSING_BLENDER_4_5_15"
 scene=ORIG if mode=="origin" else BASE if mode=="build" else OUT
 args=[str(BLENDER),"--background",str(scene),"--threads","2",
       "--python",str(Path(__file__).resolve()),"--",mode]
 res=subprocess.run(args,capture_output=True,text=True,timeout=210)
 print(res.stdout[-22000:],flush=True)
 if res.stderr:print("BLENDER_STDERR",res.stderr[-1800:],flush=True)
 if res.returncode:raise RuntimeError("BLENDER_FAILURE_"+mode+"_"+str(res.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("origin","build","verify"):
  try:import bpy
  except ImportError:run(mode)
  else:{"origin":original,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("invalid mode")