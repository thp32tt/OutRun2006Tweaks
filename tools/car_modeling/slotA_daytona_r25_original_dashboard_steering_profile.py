#!/usr/bin/env python3
"""Slot A Daytona R25: real original-PMT-derived existing cockpit mesh relief.
Edits 8 existing dashboard/instrument/three-spoke/rim/hub/column objects in
an immutable R24 private Blender scene. No assets converted/exported, no
new objects, external vehicle parts, materials, textures or game/VR changes.
Private licensed scene and photos remain on authorized N100 storage.
"""
from pathlib import Path
import sys,os,math,json,hashlib,subprocess
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v22_r24.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v23_r25.blend"
AUDIT=ROOT/"SLOTA_R25_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json"
QA=ROOT/"SLOTA_R25_FRESH_REOPEN_REAL_CYCLES.json"
RENDER=ROOT/"SLOTA_DAYTONA_R25_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R24_R25_ACTUAL_CYCLES_BEFORE_AFTER.jpg"
PREV_PNG=ROOT/"SLOTA_DAYTONA_R24_AFTER_REAL_CYCLES_APPROX_EYE.png"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"base":"15d2aea9058ff1bf6099fd349b89e200c178e722410a51be4d41bf790a513af9",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
"upper":"V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
"face":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB",
"column":"V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES"}
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
 # R25 subtle shaping of eight EXISTING original-PMT-derived P0 source meshes.
 # Use only the authenticated private 1971 GTS/4 LHD Spider cockpit reference.
 # The true game driver eye and source-photo camera angles remain uncalibrated.
 # Avoid another straight raised instrument bar; preserve all wheel-spoke holes.
 if k=="upper":
  driver=smooth(-.65,-.56,x)*(1-smooth(-.14,-.045,x))
  broad=math.exp(-((x+.35)/.255)**4)
  top=smooth(.938,.965,z)
  forward=1-smooth(.26,.48,y)
  dz=-.0036*driver*broad*top*forward
  dy=.0019*driver*broad*top*forward
 elif k=="face":
  center=math.exp(-((x+.35)/.24)**4)
  band=smooth(.755,.797,z)*(1-smooth(.884,.92,z))
  close=1-smooth(.18,.26,y)
  # Retain original fascia material boundaries; push only the underlying mesh.
  dy=.0030*center*band*close
  dz=-.0009*center*band*close
 elif k=="cowl":
  window=smooth(-.639,-.598,x)*(1-smooth(-.105,-.052,x))
  crown=smooth(.903,.918,z)
  front=1-smooth(.19,.33,y)
  center=math.exp(-((x+.35)/.184)**4)
  dz=-.0038*window*crown*front*(.5+.5*center)
  dy=.00145*window*crown*front
 elif k=="bezel":
  # Add physical ring recess separation without inventing any gauges/dials.
  inward=1-smooth(.146,.155,y)
  shoulder=smooth(.789,.824,z)*(1-smooth(.878,.922,z))
  dy=.00148*inward*(.65+.35*shoulder)
  dz=-.00066*inward*shoulder*math.tanh((x+.35)/.14)
 elif k=="spoke":
  ds=min(math.hypot(x-a,z-b)/r for a,b,r in HOLES)
  clear=smooth(1.25,2.65,ds)
  side=smooth(.066,.143,abs(x+.35))
  upper=math.exp(-((z-.799)/.047)**4)
  face=math.exp(-((y+.287)/.036)**2)
  dy=-.00305*clear*side*upper*face
  dz=.0012*clear*side*upper*face*math.tanh((x+.35)/.065)
  heel=smooth(.708,.753,z)*(1-smooth(.803,.831,z))
  dx=-.012*(x+.35)*clear*heel*face
 elif k=="rim":
  ux=x+.35;uz=z-.792;r=math.hypot(ux,uz)
  if r>.065:
   # Round the existing rim GRIP CROSS SECTION, not the wheel overall diameter.
   dr=.145*(r-.1747)
   dx=dr*ux/r;dz=dr*uz/r
  dy=.155*(y+.2857)
 elif k=="hub":
  r=math.hypot(x+.35,z-.767)
  nose=math.exp(-((y+.253)/.022)**2)
  shelf=smooth(.011,.026,r)*(1-smooth(.064,.080,r))
  dy=-.00155*nose*shelf
  if r>1.e-6:
   dx=.0009*shelf*(x+.35)/r
   dz=.0009*shelf*(z-.767)/r
 elif k=="column":
  zmask=smooth(.606,.655,z)*(1-smooth(.726,.781,z))
  shroud=math.exp(-((x+.35)/.102)**4)
  dy=.0021*zmask*shroud*(1-smooth(-.10,.095,y))
  dx=-.033*(x+.35)*zmask
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
 assert len(originals)==105,("PROTECTED_COUNT_MISMATCH",len(originals))
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
   "spoke":100,"rim":2500,"hub":10,"column":15}[k]),("INSUFFICIENT_SOURCE_GEOMETRY",k,moved)
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
 data={"status":"SLOTA_R25_REAL_PMT_DERIVED_P0_GEOMETRY_SAVED",
 "slot":"A","car_id":"daytona365","native_PMT_sha256":HASH["pmt"],
 "original_import_blend_sha256":HASH["import"],"r24_input_sha256":HASH["base"],
 "r25_output_blend_sha256":digest(OUT),
 "factory_original_object_names":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "exact_Spider_LHD_private_photo_sha256":HASH["photo"],
 "edited_existing_original_derived_meshes":report,
 "other_105_source_meshes_sha256":hashlib.sha256(json.dumps(originals,sort_keys=True).encode()).hexdigest(),
 "eight_original_steering_spoke_holes_open":True,
 "no_new_objects_meshes_materials_textures_or_other_vehicles":True,
 "camera_matrices_steering_pivots_UV_and_materials_unchanged":True,
 "no_OVC3_OVC_PMT_export_no_game_VR_integration":True,
 "original_game_eye":"NOT_CALIBRATED","seven_exact_Spider_views":"INCOMPLETE",
 "GitHub_hosted_private_blend_audit":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(data,indent=2),encoding="utf8")
 print("SLOTA_R25_BUILD_PASS",json.dumps({"r25":data["r25_output_blend_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy,bmesh
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve(),"BLOCKED_FRESH_REOPEN_SOURCE"
 assert AUDIT.is_file() and not QA.exists() and not RENDER.exists()
 gate();a=json.loads(AUDIT.read_text())
 assert digest(OUT)==a["r25_output_blend_sha256"]
 others={o.name:coords_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(others)==105
 assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==a["other_105_source_meshes_sha256"]
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
 cd=bpy.data.cameras.new("R25_UNSAVED_APPROXIMATE_EYE")
 cam=bpy.data.objects.new("R25_UNSAVED_APPROXIMATE_EYE",cd)
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
 assert digest(OUT)==a["r25_output_blend_sha256"]
 qa={"status":"SLOTA_R25_ACTUAL_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_CYCLES_PASS",
  "private_blend_sha256":digest(OUT),"actual_Cycles_png_sha256":digest(RENDER),
  "resolution":[720,480],"samples":3,"independently_verified_meshes":findings,
  "unmodified_other_meshes":105,"eight_factory_spoke_holes":"PASS",
  "exact_game_driver_eye":"NOT_CALIBRATED",
  "seven_Spider_photo_angle_matching":"INCOMPLETE",
  "GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R25_FRESH_REOPEN_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
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
 qa["r24_vs_r25_gt3_rgb_pixels"]=changed
 qa["r24_render_sha256"]=digest(PREV_PNG)
 qa["r25_render_sha256"]=digest(RENDER)
 qa["side_by_side_comparison_sha256"]=digest(COMPARE)
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R25_R24_R25_REAL_RENDER_COMPARE_PASS",changed,digest(COMPARE),flush=True)
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