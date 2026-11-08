#!/usr/bin/env python3
"""Slot A Daytona R26: real original-PMT-derived existing cockpit mesh relief.
Edits 13 existing dashboard/instrument/three-spoke/rim/hub/column objects in
an immutable R25 private Blender scene. No assets converted/exported, no
new objects, external vehicle parts, materials, textures or game/VR changes.
Private licensed scene and photos remain on authorized N100 storage.
"""
from pathlib import Path
import sys,os,math,json,hashlib,subprocess
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v23_r25.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v24_r26.blend"
AUDIT=ROOT/"SLOTA_R26_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json"
QA=ROOT/"SLOTA_R26_FRESH_REOPEN_REAL_CYCLES.json"
RENDER=ROOT/"SLOTA_DAYTONA_R26_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R25_R26_ACTUAL_CYCLES_BEFORE_AFTER.jpg"
PREV_PNG=ROOT/"SLOTA_DAYTONA_R25_AFTER_REAL_CYCLES_APPROX_EYE.png"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"base":"e9dd86adb27b25ea49f7eeb5335ef5b312bac180bf336a833f96d7cfe57715a5",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
"upper":"V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
"face":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB",
"column":"V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES",
"left_bridge":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
"right_bridge":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
"lower_bridge":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
"lower_lip":"V8_2_CONTINUOUS_LOWER_DASH_LIP",
"trim":"V8_2_DASH_TRIM_STRIP"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def gate():
 for tag,p in (("pmt",GAME),("import",IMPORT),("base",BASE),("photo",PHOTO)):
  assert p.is_file() and digest(p)==HASH[tag],("BLOCKED_INPUT",tag,str(p))
def smooth(a,b,v):
 t=max(0.0,min(1.0,(v-a)/(b-a)))
 return t*t*(3.0-2.0*t)
def coords_sig(o):
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
  [(p.material_index,tuple(p.vertices)) for p in o.data.polygons])).encode()).hexdigest()
def uv_sig(o):
 return hashlib.sha256(repr([(l.name,[(round(u.uv.x,8),round(u.uv.y,8)) for u in l.data])
  for l in o.data.uv_layers]).encode()).hexdigest()
def mat(o):
 return [[round(float(v),9) for v in row] for row in o.matrix_world]
def state(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
  "mesh_sha256":coords_sig(o),"world_matrix":mat(o),"uv_sha256":uv_sig(o),
  "materials":[m.name if m else None for m in o.data.materials],
  "hide_render":bool(o.hide_render)}
def global_inventory():
 import bpy
 return {"objects":sorted(bpy.data.objects.keys()),
 "meshes":sorted(bpy.data.meshes.keys()),
 "materials":sorted(bpy.data.materials.keys()),
 "curves":sorted(bpy.data.curves.keys()),
 "images":{a.name:(tuple(a.size),bool(a.packed_file),a.filepath) for a in bpy.data.images},
 "camera":{o.name:mat(o) for o in bpy.data.objects if o.type=="CAMERA"}}
def holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 bvh=BVHTree.FromObject(bpy.data.objects[NAMES["spoke"]],
  bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return bvh.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.0)[2] is not None
 return [(not hit(x,z)) and hit(x+1.6*r,z) for x,z,r in HOLES]
def displacement(k,p):
 from mathutils import Vector
 x,y,z=p;dx=dy=dz=0.0
 # R26: authentic 1971 GTS/4 Spider LHD photograph comparison:
 # Original wheel has thin perforated metal arms + shallow dash lip.
 # Retain all original hole centers, material boundaries, UVs and matrices.
 # True game-eye/photo registration still not established; this is P0 partial.
 if k=="upper":
  driver=smooth(-.66,-.58,x)*(1-smooth(-.13,-.06,x))
  near=1-smooth(.26,.48,y)
  brow=smooth(.944,.972,z)
  center=math.exp(-((x+.35)/.223)**4)
  dz=-.00425*driver*brow*near*(.56+.44*center)
  dy=.0019*driver*brow*near
 elif k=="face":
  gauge=math.exp(-((x+.35)/.232)**4)
  lip=smooth(.741,.766,z)*(1-smooth(.851,.877,z))
  front=1-smooth(.17,.28,y)
  dy=.0041*gauge*lip*front
  dz=-.0011*gauge*lip*front
 elif k=="cowl":
  window=smooth(-.646,-.604,x)*(1-smooth(-.095,-.047,x))
  rear=1-smooth(.203,.307,y)
  top=smooth(.901,.916,z)
  arch=math.exp(-((x+.35)/.17)**4)
  dz=-.0052*window*rear*top*(.52+.48*arch)
  dy=.0018*window*rear*top
 elif k=="bezel":
  # Recess existing metal gauge bezel front rather than generating fake dials.
  edge=math.exp(-((x+.35)/.22)**4)
  face=1-smooth(.147,.157,y)
  arch=smooth(.793,.829,z)*(1-smooth(.882,.912,z))
  dy=.0021*face*(.65+.35*edge)
  dz=-.00065*face*arch
 elif k=="spoke":
  # Source-punched 8 through-holes are checked again by independent BVH.
  dist=min(math.hypot(x-a,z-b)/r for a,b,r in HOLES)
  clearance=smooth(1.35,2.7,dist)
  upper=math.exp(-((z-.801)/.048)**4)
  wing=smooth(.069,.148,abs(x+.35))
  metal=math.exp(-((y+.288)/.042)**2)
  dy=.0031*clearance*upper*wing*metal
  dz=.0010*clearance*upper*wing*metal*math.tanh((x+.35)/.078)
  neck=smooth(.698,.737,z)*(1-smooth(.806,.840,z))
  dx=-.016*(x+.35)*clearance*neck*metal
 elif k=="rim":
  ux=x+.35;uz=z-.792;r=math.hypot(ux,uz)
  if r>.056:
   # Only grip CROSS SECTION, not wheel radius, is refined.
   dr=.11*(r-.1747)
   dx=dr*ux/r;dz=dr*uz/r
  dy=.115*(y+.2857)
 elif k=="hub":
  r=math.hypot(x+.35,z-.767)
  ring=smooth(.013,.025,r)*(1-smooth(.062,.079,r))
  face=math.exp(-((y+.252)/.017)**2)
  dy=.00165*ring*face
  if r>.00001:
   dx=.0009*ring*(x+.35)/r
   dz=.0009*ring*(z-.767)/r
 elif k=="column":
  shroud=smooth(.611,.645,z)*(1-smooth(.731,.782,z))
  near=1-smooth(-.09,.11,y)
  dx=-.046*(x+.35)*shroud
  dy=.0021*shroud*near
 elif k in ("left_bridge","right_bridge"):
  cx=-.483 if k=="left_bridge" else -.217
  arch=max(0.,1-abs(x-cx)/.066)
  # Existing flat chrome-bridge protrusion recessed toward dashboard.
  dy=.0048*(.42+.58*arch)
  dz=-.0014*arch*(1-smooth(.796,.814,z))
 elif k=="lower_bridge":
  near=math.exp(-((z-.667)/.054)**4)
  dy=.0045*near
  dx=-.035*(x+.35)*near
 elif k=="lower_lip":
  # N100 image comparison shows an overlong false horizontal rim.
  # Recess only source-derived existing lower-lip surface, not a new bar.
  near=1-smooth(.19,.225,y)
  stripe=smooth(.586,.626,z)
  dy=.0068*near*stripe
  dz=-.0030*near*stripe
 elif k=="trim":
  # Narrow bright source strip by setting its existing vertices inward.
  dy=.0080
  dz=-.0034
 return Vector((dx,dy,dz))
def origin():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==IMPORT.resolve(),"BLOCKED_ORIGINAL_IMPORT"
 assert digest(GAME)==HASH["pmt"] and digest(IMPORT)==HASH["import"]
 ids={"object00_group01_material012_a0":13,
      "object22_group00_material000_a0":61}
 for name,n in ids.items():
  o=bpy.data.objects.get(name)
  assert o is not None and o.type=="MESH" and len(o.data.vertices)==n,("ORIGIN_ID_MISMATCH",name)
 print("SOURCE_NATIVE_ORIGINAL_IMPORT_REOPEN_PASS",ids,flush=True)
def build():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 gate()
 assert Path(bpy.data.filepath).resolve()==BASE.resolve()
 assert not any(p.exists() for p in (OUT,AUDIT,QA,RENDER,COMPARE)),"BLOCKED_IMMUTABLE_OUTPUT_COLLISION"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9720
 assert all(holes()),"SOURCE_SPOKE_HOLES"
 scene=global_inventory()
 originals={o.name:coords_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(originals)==100,("PROTECTED_COUNT_MISMATCH",len(originals))
 report={}
 for k,name in NAMES.items():
  o=bpy.data.objects[name]
  assert o.type=="MESH" and o.data.users==1
  before=state(o); inv=o.matrix_world.inverted()
  moved=0;mx=0.;total=0.
  for v in o.data.vertices:
   wp=o.matrix_world@v.co
   dp=displacement(k,wp)
   if dp.length<.000008:continue
   v.co=inv@(wp+dp)
   moved+=1;mx=max(mx,dp.length);total+=dp.length
  o.data.update()
  assert moved>=({"upper":100,"face":70,"cowl":100,"bezel":500,
   "spoke":100,"rim":2500,"hub":10,"column":15,
   "left_bridge":6,"right_bridge":6,"lower_bridge":6,"lower_lip":8,"trim":8}[k]),("INSUFFICIENT_SOURCE_GEOMETRY",k,moved)
  assert mx<.014,("DISPLACEMENT_TOO_LARGE",k,mx)
  after=state(o)
  for invariant in ("name","vertices","faces","world_matrix","uv_sha256","materials","hide_render"):
   assert before[invariant]==after[invariant],("CHANGED_SOURCE_ID_UV_MATERIAL_OR_TOPOLOGY",k,invariant)
  assert before["mesh_sha256"]!=after["mesh_sha256"],("NO_REAL_SOURCE_MESH_CHANGE",k)
  report[k]={"before":before,"after":after,"moved_vertices":moved,
   "max_delta_m":round(mx,8),"mean_delta_m":round(total/moved,8)}
 assert scene==global_inventory(),"ASSET_OR_CAMERA_INVENTORY_DRIFT"
 assert {o.name:coords_sig(o) for o in bpy.data.objects
  if o.type=="MESH" and o.name not in NAMES.values()}==originals
 assert all(holes()),"EIGHT_NATIVE_THROUGH_HOLES_REGRESSION"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 data={"status":"SLOTA_R26_REAL_PMT_DERIVED_P0_GEOMETRY_SAVED",
 "slot":"A","car_id":"daytona365","native_PMT_sha256":HASH["pmt"],
 "original_import_blend_sha256":HASH["import"],"r25_input_sha256":HASH["base"],
 "r26_output_blend_sha256":digest(OUT),
 "factory_original_object_names":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "exact_Spider_LHD_private_photo_sha256":HASH["photo"],
 "edited_existing_original_derived_meshes":report,
 "other_100_source_meshes_sha256":hashlib.sha256(json.dumps(originals,sort_keys=True).encode()).hexdigest(),
 "eight_original_steering_spoke_holes_open":True,
 "no_new_objects_meshes_materials_textures_or_other_vehicles":True,
 "camera_matrices_steering_pivots_UV_and_materials_unchanged":True,
 "no_OVC3_OVC_PMT_export_no_game_VR_integration":True,
 "original_game_eye":"NOT_CALIBRATED","seven_exact_Spider_views":"INCOMPLETE",
 "GitHub_hosted_private_blend_audit":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(data,indent=2),encoding="utf8")
 print("SLOTA_R26_BUILD_PASS",json.dumps({"r26":data["r26_output_blend_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy,bmesh
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve(),"BLOCKED_FRESH_REOPEN_SOURCE"
 assert AUDIT.is_file() and not QA.exists() and not RENDER.exists()
 gate();a=json.loads(AUDIT.read_text())
 assert digest(OUT)==a["r26_output_blend_sha256"]
 others={o.name:coords_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(others)==100
 assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==a["other_100_source_meshes_sha256"]
 assert all(holes())
 findings={}
 for tag,entry in a["edited_existing_original_derived_meshes"].items():
  o=bpy.data.objects[entry["after"]["name"]]
  assert state(o)==entry["after"],("FRESH_REOPEN_MESH_DRIFT",tag)
  bm=bmesh.new();bm.from_mesh(o.data)
  findings[tag]={"vertices":len(bm.verts),"faces":len(bm.faces),
    "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert findings["rim"]["nonmanifold_edges"]==0 and findings["hub"]["nonmanifold_edges"]==0
 assert findings["spoke"]["nonmanifold_edges"]==1597
 # Render camera is transient only, never written into the proprietary scene.
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R26_UNSAVED_APPROXIMATE_EYE")
 cam=bpy.data.objects.new("R26_UNSAVED_APPROXIMATE_EYE",cd)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(RENDER)
 bpy.ops.render.render(write_still=True)
 assert RENDER.is_file() and RENDER.stat().st_size>12000
 assert digest(OUT)==a["r26_output_blend_sha256"]
 qa={"status":"SLOTA_R26_ACTUAL_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_CYCLES_PASS",
  "private_blend_sha256":digest(OUT),"actual_Cycles_png_sha256":digest(RENDER),
  "resolution":[720,480],"samples":3,"independently_verified_meshes":findings,
  "unmodified_other_meshes":100,"eight_factory_spoke_holes":"PASS",
  "exact_game_driver_eye":"NOT_CALIBRATED",
  "seven_Spider_photo_angle_matching":"INCOMPLETE",
  "GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R26_FRESH_REOPEN_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
def run(mode):
 assert BLENDER.is_file()
 asset=IMPORT if mode=="origin" else (BASE if mode=="build" else OUT)
 cmd=[str(BLENDER),"--background",str(asset),"--threads","2","--python",str(Path(__file__).resolve()),"--",mode]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=210)
 print(r.stdout[-22000:],flush=True)
 if r.stderr:print("BLENDER_STDERR",r.stderr[-3000:],flush=True)
 assert r.returncode==0,("BLENDER_FAILED",mode,r.returncode)
def compare():
 from PIL import Image,ImageChops
 assert PREV_PNG.is_file() and RENDER.is_file()
 with Image.open(PREV_PNG) as ia,Image.open(RENDER) as ib:
  a=ia.convert("RGB");b=ib.convert("RGB")
  assert a.size==b.size==(720,480)
  pa=a.load();pb=b.load()
  changed=sum(1 for y in range(480) for x in range(720)
   if max(abs(pa[x,y][c]-pb[x,y][c]) for c in range(3))>3)
  assert changed>500,("INSUFFICIENT_RENDER_DIFFERENCE",changed)
  dest=Image.new("RGB",(1440,480));dest.paste(a,(0,0));dest.paste(b,(720,0))
  dest.save(COMPARE,quality=93,optimize=True)
 qa=json.loads(QA.read_text())
 qa["r25_vs_r26_gt3_rgb_pixels"]=changed
 qa["r25_render_sha256"]=digest(PREV_PNG)
 qa["r26_render_sha256"]=digest(RENDER)
 qa["side_by_side_comparison_sha256"]=digest(COMPARE)
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R26_R25_R26_REAL_RENDER_COMPARE_PASS",changed,digest(COMPARE),flush=True)
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("origin","build","verify"):
  try:
   import bpy
  except ImportError:
   run(mode)
  else:
   {"origin":origin,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("mode must be origin/build/verify/compare")