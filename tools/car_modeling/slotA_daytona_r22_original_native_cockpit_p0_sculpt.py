#!/usr/bin/env python3
"""Slot A Daytona R22. Edit existing original PMT-derived P0 dashboard and steering
meshes in immutable private R21 .blend. Original PMT/source import read-only.
No new objects, meshes, textures, normals, materials, export, game or VR changes.
"""
from pathlib import Path
import bpy,bmesh,os,math,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORTED=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
SOURCE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v19_r21.blend"
OUTPUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v20_r22.blend"
PREVIOUS=ROOT/"SLOTA_R21_NATIVE_DASH_BRIDGE_TOPOLOGY.json"
AUDIT=ROOT/"SLOTA_R22_NATIVE_DASH_WHEEL_VERTEX_SCULPT_AUDIT.json"
QA=ROOT/"SLOTA_R22_INDEPENDENT_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R22_AFTER_REAL_CYCLES_APPROX_EYE.png"
HASH={
"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"source":"581ef8d73f36b18c559b97d5f50867da0002b1abf4c76335a5d732ab917b4938",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
PARTS={
"dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for data in iter(lambda:f.read(1048576),b""):h.update(data)
 return h.hexdigest()
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3.-2.*t)
def signature(o):
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
 [(poly.material_index,tuple(poly.vertices)) for poly in o.data.polygons])).encode()).hexdigest()
def uv_signature(o):
 return hashlib.sha256(repr([(layer.name,[
  (round(v.uv.x,8),round(v.uv.y,8)) for v in layer.data])
  for layer in o.data.uv_layers]).encode()).hexdigest()
def matrix(o):return [[round(float(a),9) for a in row] for row in o.matrix_world]
def mesh_state(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "signature":signature(o),"matrix":matrix(o),"uv":[a.name for a in o.data.uv_layers],
 "uv_content_sha256":uv_signature(o),
 "materials":[m.name if m else None for m in o.data.materials],
 "hide_render":bool(o.hide_render)}
def spoke_holes():
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(bpy.data.objects[PARTS["spoke"]],
  bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return tree.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.0)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def registry():
 return {"objects":sorted(bpy.data.objects.keys()),
  "meshes":sorted(bpy.data.meshes.keys()),
  "materials":sorted(bpy.data.materials.keys()),
  "curves":sorted(bpy.data.curves.keys()),
  "images":{im.name:(tuple(im.size),bool(im.packed_file),im.filepath) for im in bpy.data.images},
  "cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}}
def input_gate(expected_file):
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_VERSION"
 assert Path(bpy.data.filepath).resolve()==expected_file.resolve(),"BLOCKED_INPUT_WRONG_SOURCE"
 for tag,p in (("pmt",PMT),("import",IMPORTED),("source",SOURCE),("photo",PHOTO)):
  assert p.is_file() and sha(p)==HASH[tag],("BLOCKED_INPUT_SHA",tag)
 assert PREVIOUS.is_file()
 last=json.loads(PREVIOUS.read_text())
 assert last["output_r21_sha256"]==HASH["source"],"BLOCKED_INPUT_R21_LINEAGE"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[PARTS["spoke"]].data.vertices)==9720
 assert all(spoke_holes()),"BLOCKED_INPUT_ORIGINAL_SPOKE_HOLES"
def displacement(k,p):
 x,y,z=p
 dx=dy=dz=0.
 if k=="dashboard":
  # Original-source padded dash at driver-eye: a continuous rounded edge
  # above instrument fascia, without rebuilding the photographed dashboard.
  span=smooth(-.63,-.57,x)*(1-smooth(-.13,-.075,x))
  front=1-smooth(.173,.237,y)
  crown=smooth(.793,.833,z)*(1-smooth(.92,.956,z))
  focus=.50+.50*math.exp(-((x+.346)/.22)**4)
  dz=.00225*span*front*crown*focus
  dy=-.00112*span*front*crown
 elif k=="cowl":
  # Shallow, broad gauge hood: avoid the previously rejected high fake arc.
  width=smooth(-.629,-.590,x)*(1-smooth(-.098,-.055,x))
  front=1-smooth(.200,.289,y)
  zband=smooth(.903,.909,z)
  mid=math.exp(-((x+.34)/.210)**4)
  dz=.00185*width*front*(.27+.73*mid)*zband
  dy=-.00105*width*front*mid
 elif k=="bezel":
  # Real 3-D ring reveal. Recess rear lip and gently roll forward edge;
  # preserve all existing source UV loops and source nonmanifold topology.
  front=1-smooth(.1460,.1530,y)
  rear=smooth(.152,.1575,y)
  dy=-.00125*front+.00038*rear
  dz=.00018*front*math.tanh((z-.823)/.033)
 elif k=="spoke":
  # Retain 8 original drilled holes via distance mask plus BVH recheck.
  ds=[math.hypot(x-hx,z-hz)/r for hx,hz,r in HOLES]
  clear=smooth(1.12,2.15,min(ds))
  wing=smooth(.072,.138,abs(x+.35))*math.exp(-((z-.795)/.048)**4)
  face=math.exp(-((y+.288)/.035)**2)
  lip=math.exp(-((min(ds)-1.8)/.5)**2)*clear
  dy=clear*face*(-.00128*wing-.00035*lip)
  dz=clear*face*.00055*wing*math.tanh((x+.35)/.05)
  low=smooth(.688,.717,z)*(1-smooth(.760,.804,z))
  dx=-.027*(x+.35)*low*clear*face
 elif k=="rim":
  # Compress tube, not steering circle: reference black rim is slim.
  ux=x+.35;vz=z-.792
  r=math.hypot(ux,vz)
  if r>.06:
   tube=r-.1740
   dr=-.105*tube
   dx=dr*ux/r;dz=dr*vz/r
  dy=-.075*(y+.286)
 elif k=="hub":
  # Tiny real existing 3-spoke hub shoulder radius relief.
  r=math.hypot(x+.35,z-.767)
  shoulder=math.exp(-((y+.252)/.015)**2)*smooth(.011,.025,r)
  if r>1e-6:
   dx=.0008*shoulder*(x+.35)/r
   dz=.0008*shoulder*(z-.767)/r
  dy=-.00084*shoulder
 return Vector((dx,dy,dz))
def build():
 input_gate(SOURCE)
 assert not OUTPUT.exists() and not AUDIT.exists(),"BLOCKED_OUTPUT_COLLISION"
 baseline=registry()
 protected={o.name:signature(o) for o in bpy.data.objects
  if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(protected)==107,("WRONG_OTHER_MESH_COUNT",len(protected))
 report={}
 for tag,name in PARTS.items():
  o=bpy.data.objects[name];assert o.type=="MESH" and o.data.users==1
  before=mesh_state(o);inverse=o.matrix_world.inverted()
  n=0;total=0.;maxmove=0.
  for v in o.data.vertices:
   p=o.matrix_world@v.co;delta=displacement(tag,p)
   if delta.length<0.000009:continue
   v.co=inverse@(p+delta);n+=1;total+=delta.length;maxmove=max(maxmove,delta.length)
  o.data.update()
  minimum={"dashboard":90,"cowl":150,"bezel":900,"spoke":300,"rim":5800,"hub":10}[tag]
  assert n>=minimum,("TOO_FEW_CHANGED_VERTICES",tag,n,minimum)
  assert maxmove<.004,("OVER_LIMIT_DISPLACEMENT",tag,maxmove)
  after=mesh_state(o)
  for key in ("name","vertices","faces","matrix","uv","uv_content_sha256","materials","hide_render"):
   assert after[key]==before[key],("SOURCE_IDENTITY_UV_TOPOLOGY_DRIFT",tag,key)
  assert before["signature"]!=after["signature"],("NO_REAL_GEOMETRY_CHANGE",tag)
  report[tag]={"before":before,"after":after,"moved_vertices":n,
   "max_move_m":round(maxmove,7),"average_move_m":round(total/n,7)}
 assert registry()==baseline,"BLOCKED_NEW_OR_MODIFIED_SCENE_OBJECT_OR_MATERIAL"
 assert {o.name:signature(o) for o in bpy.data.objects
  if o.type=="MESH" and o.name not in PARTS.values()}==protected,"OTHER_MESH_DRIFT"
 assert all(spoke_holes()),"ORIGINAL_EIGHT_HOLES_CLOSED"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 assert OUTPUT.is_file() and OUTPUT.stat().st_size>1000000
 audit={"status":"SLOTA_R22_SOURCE_DERIVED_P0_GEOMETRY_SAVED","slot":"A",
  "vehicle":"daytona365","original_game_pmt":PMT.name,"raw_native_object_ids":[
  "object00_group01_material012_a0","object22_group00_material000_a0"],
  "original_pmt_sha256":HASH["pmt"],"original_import_sha256":HASH["import"],
  "input_r21_sha256":HASH["source"],"output_r22_sha256":sha(OUTPUT),
  "photo_sha256":HASH["photo"],"edited_existing_meshes":report,
  "untouched_107_meshes_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
  "eight_factory_spoke_holes_open":True,"no_new_objects_materials_textures_or_exterior":True,
  "UV_materials_cameras_pivots_transforms_preserved":True,
  "no_game_or_native_export":True,"actual_game_eye":"NOT_CALIBRATED",
  "seven_spider_photo_views":"INCOMPLETE",
  "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print("SLOTA_R22_GEOMETRY_SAVED",json.dumps({"sha":audit["output_r22_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==OUTPUT.resolve(),"BLOCKED_INDEPENDENT_REOPEN"
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists(),"IMMUTABLE_R22_QA_COLLISION"
 assert bpy.app.version_string.startswith("4.5.15")
 for tag,p in (("pmt",PMT),("import",IMPORTED),("source",SOURCE),("photo",PHOTO)):
  assert sha(p)==HASH[tag],("INDEPENDENT_SOURCE_SHA",tag)
 record=json.loads(AUDIT.read_text())
 assert sha(OUTPUT)==record["output_r22_sha256"]
 protected={o.name:signature(o) for o in bpy.data.objects
  if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(protected)==107
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==record["untouched_107_meshes_sha256"]
 assert all(spoke_holes()),"INDEPENDENT_REOPEN_HOLES_FAILED"
 checks={}
 for tag,data in record["edited_existing_meshes"].items():
  obj=bpy.data.objects[data["after"]["name"]]
  assert mesh_state(obj)==data["after"],("REOPEN_MESH_MISMATCH",tag)
  bm=bmesh.new();bm.from_mesh(obj.data)
  checks[tag]={"vertices":len(bm.verts),"faces":len(bm.faces),
   "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert checks["rim"]["nonmanifold_edges"]==0 and checks["hub"]["nonmanifold_edges"]==0
 assert checks["spoke"]["nonmanifold_edges"]==1597
 # Transient camera is NOT saved to the immutable .blend.
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R22_UNSAVED_APPROXIMATE_EYE")
 cam=bpy.data.objects.new("R22_UNSAVED_APPROXIMATE_EYE",cd)
 sc.collection.objects.link(cam);cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG"
 sc.render.image_settings.color_mode="RGBA";sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG);bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(OUTPUT)==record["output_r22_sha256"]
 qa={"status":"SLOTA_R22_OFFICIAL_4_5_15_REAL_BLENDER_FRESH_REOPEN_CYCLES_PASS",
  "slot":"A","vehicle":"daytona365","input_r21_sha256":HASH["source"],
  "output_r22_sha256":sha(OUTPUT),"real_cycles_sha256":sha(PNG),
  "resolution":[720,480],"cycles_samples":3,
  "edited_mesh_nonmanifold_and_counts":checks,
  "other_107_meshes_unchanged":True,"eight_source_spoke_holes":True,
  "actual_game_eye":"APPROXIMATE_NOT_CALIBRATED",
  "hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf-8")
 print("SLOTA_R22_INDEPENDENT_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOTA_R22_MODE")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("SLOTA_R22_MODE must be build or verify")