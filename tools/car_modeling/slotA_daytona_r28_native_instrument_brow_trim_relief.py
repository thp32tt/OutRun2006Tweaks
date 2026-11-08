#!/usr/bin/env python3
"""Slot A Daytona R28: in-place Daytona original dash lower crescent, wheel press-form and trim geometry refinement.
Edits 8 existing original-derived dashboard/instrument/steering/lower-trim meshes in
an immutable R27 private Blender scene. No assets converted/exported, no
new objects, external vehicle parts, materials, textures or game/VR changes.
Private licensed scene and photos remain on authorized N100 storage.
"""
from pathlib import Path
import sys,os,math,json,hashlib,subprocess
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v25_r27.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v26_r28.blend"
AUDIT=ROOT/"SLOTA_R28_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json"
QA=ROOT/"SLOTA_R28_FRESH_REOPEN_REAL_CYCLES.json"
RENDER=ROOT/"SLOTA_DAYTONA_R28_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R27_R28_ACTUAL_CYCLES_BEFORE_AFTER.jpg"
PREV_PNG=ROOT/"SLOTA_DAYTONA_R27_AFTER_REAL_CYCLES_APPROX_EYE.png"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"base":"3eef4b5106c324202612947ec99dda91f840564d3f755ad243260736f55549b4",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
"upper":"V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
"face":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
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
 x,y,z=p
 dx=dy=dz=0.
 # Source-backed R28 targeted photo-guided instrument lower crescent
 # and excess straight trim reduction. All original geometry object IDs
 # and packed materials retained. Spider LHD photo is NOT camera-registered.
 if k=="upper":
  driver=smooth(-.653,-.598,x)*(1-smooth(-.111,-.063,x))
  front=1-smooth(.24,.42,y)
  crown=smooth(.936,.973,z)
  center=math.exp(-((x+.35)/.216)**4)
  dz=-.0043*driver*front*crown*(.57+.43*center)
  dy=.00115*driver*front*crown
 elif k=="face":
  # Recess the broad flat lower gauge-face ledge behind original instruments.
  region=math.exp(-((x+.35)/.248)**4)
  chin=smooth(.736,.760,z)*(1-smooth(.813,.85,z))
  front=1-smooth(.168,.231,y)
  dy=.0040*region*chin*front
  dz=-.0006*region*chin*front
 elif k=="cowl":
  # Keep the original-source binnacle footprint; roll the top on a shallow arch.
  center=math.exp(-((x+.35)/.18)**4)
  depth=smooth(.185,.290,y)
  dz=.00265*center*(.62+.38*depth)-.00075*(1-center)
  dy=.0009*center*(1-smooth(.263,.313,y))
 elif k=="bezel":
  # The R27 bright silver crescent is wider than in authenticated Spider LHD photo.
  # Recede only the *existing* lower/chin geometry, not dial faces or textures.
  band=smooth(.741,.752,z)*(1-smooth(.811,.853,z))
  driver=math.exp(-((x+.35)/.269)**4)
  front=1-smooth(.149,.160,y)
  dy=.0076*band*driver*front
  dz=-.00155*band*driver*front
 elif k=="spoke":
  # Light press-form relief on surviving factory-source three-spoke metal.
  # Existing eight actual through holes are strictly BVH tested after edit.
  safe_dist=min(math.hypot(x-a,z-b)/r for a,b,r in HOLES)
  clearance=smooth(1.5,2.75,safe_dist)
  arms=smooth(.058,.127,abs(x+.35))
  upper=math.exp(-((z-.794)/.054)**4)
  metal=math.exp(-((y+.284)/.034)**2)
  dy=.0017*clearance*arms*upper*metal
  dz=.0006*clearance*arms*upper*metal*math.tanh((x+.35)/.083)
 elif k=="rim":
  # Refine cross-section only; keep source wheel ring radius and pivot.
  ux=x+.35;uz=z-.792;rad=math.hypot(ux,uz)
  if rad>.09:
   dr=-.031*(rad-.1747)
   dx=dr*ux/rad;dz=dr*uz/rad
  dy=-.095*(y+.2857)
 elif k=="lower_lip":
  # Ray-identified existing original-derived V8_2 lower dash lip x=480..680.
  # Recede its straight forward passenger-side brow and soften driver transition.
  near=1-smooth(.196,.229,y)
  passenger=smooth(-.19,.14,x)
  dy=(.0035+.0041*passenger)*near
  dz=-.0019*(.45+.55*passenger)*near
 elif k=="trim":
  # Eight vertices of the source-derived bright 1.39m straight trim strip.
  # Physically position existing strip further inside and below original padded
  # dashboard to avoid an artificial bright chrome bar across passenger side.
  dy=.012
  dz=-.0038
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
 data={"status":"SLOTA_R28_REAL_PMT_DERIVED_P0_GEOMETRY_SAVED",
 "slot":"A","car_id":"daytona365","native_PMT_sha256":HASH["pmt"],
 "original_import_blend_sha256":HASH["import"],"r27_input_sha256":HASH["base"],
 "r28_output_blend_sha256":digest(OUT),
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
 print("SLOTA_R28_BUILD_PASS",json.dumps({"r28":data["r28_output_blend_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy,bmesh
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve(),"BLOCKED_FRESH_REOPEN_SOURCE"
 assert AUDIT.is_file() and not QA.exists() and not RENDER.exists()
 gate();a=json.loads(AUDIT.read_text())
 assert digest(OUT)==a["r28_output_blend_sha256"]
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
 assert findings["rim"]["nonmanifold_edges"]==0
 assert findings["spoke"]["nonmanifold_edges"]==1597
 # Render camera is transient only, never written into the proprietary scene.
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R28_UNSAVED_APPROXIMATE_EYE")
 cam=bpy.data.objects.new("R28_UNSAVED_APPROXIMATE_EYE",cd)
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
 assert digest(OUT)==a["r28_output_blend_sha256"]
 qa={"status":"SLOTA_R28_ACTUAL_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_CYCLES_PASS",
  "private_blend_sha256":digest(OUT),"actual_Cycles_png_sha256":digest(RENDER),
  "resolution":[720,480],"samples":3,"independently_verified_meshes":findings,
  "unmodified_other_meshes":105,"eight_factory_spoke_holes":"PASS",
  "exact_game_driver_eye":"NOT_CALIBRATED",
  "seven_Spider_photo_angle_matching":"INCOMPLETE",
  "GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R28_FRESH_REOPEN_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
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
 qa["r27_vs_r28_gt3_rgb_pixels"]=changed
 qa["r27_render_sha256"]=digest(PREV_PNG)
 qa["r28_render_sha256"]=digest(RENDER)
 qa["side_by_side_comparison_sha256"]=digest(COMPARE)
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R28_R27_R28_REAL_RENDER_COMPARE_PASS",changed,digest(COMPARE),flush=True)
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