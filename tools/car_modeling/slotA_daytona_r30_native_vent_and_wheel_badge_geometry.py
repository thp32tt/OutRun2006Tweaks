#!/usr/bin/env python3
"""Slot A Daytona R30: reshape the source-derived cockpit airvent depth and original three-spoke steering badge.
Only vertex positions of 17 PRE-EXISTING original/native-backed cockpit objects
are changed in a cloned immutable R29 real Blender .blend. No new geometry
objects, GLB substitutes, materials, textures, outer-body edits or game output.
PMT/photos remain privately stored and read-only. R30 scene is private.
"""
from pathlib import Path
import sys,os,math,json,hashlib,subprocess
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v27_r29.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v28_r30.blend"
AUDIT=ROOT/"SLOTA_R30_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json"
QA=ROOT/"SLOTA_R30_FRESH_REOPEN_REAL_CYCLES.json"
RENDER=ROOT/"SLOTA_DAYTONA_R30_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R29_R30_ACTUAL_CYCLES_BEFORE_AFTER.jpg"
PREV_PNG=ROOT/"SLOTA_DAYTONA_R29_AFTER_REAL_CYCLES_APPROX_EYE.png"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"base":"8383d235ca0dbfa89f541ebe3681bbcaea6df65c57dda4fa8a7834f738253e36",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
 "upper": "V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
 "cowl": "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "spoke": "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim": "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "emblem": "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
 "vent_bezel_080": "V5_3D_AIRVENT_0.080_CHROME_BEZEL",
 "vent_slat_080_0": "V5_3D_AIRVENT_0.080_SLAT0",
 "vent_slat_080_1": "V5_3D_AIRVENT_0.080_SLAT1",
 "vent_slat_080_2": "V5_3D_AIRVENT_0.080_SLAT2",
 "vent_bezel_255": "V5_3D_AIRVENT_0.255_CHROME_BEZEL",
 "vent_slat_255_0": "V5_3D_AIRVENT_0.255_SLAT0",
 "vent_slat_255_1": "V5_3D_AIRVENT_0.255_SLAT1",
 "vent_slat_255_2": "V5_3D_AIRVENT_0.255_SLAT2",
 "vent_bezel_430": "V5_3D_AIRVENT_0.430_CHROME_BEZEL",
 "vent_slat_430_0": "V5_3D_AIRVENT_0.430_SLAT0",
 "vent_slat_430_1": "V5_3D_AIRVENT_0.430_SLAT1",
 "vent_slat_430_2": "V5_3D_AIRVENT_0.430_SLAT2"
}
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
 dx=dy=dz=0.0
 # Authenticated 1971 Ferrari Daytona Spider LHD photo is qualitative,
 # NOT registered to the OutRun game's exact eye. Never invent measured dims.
 if k=="upper":
  # Lightly round original-source upper dash over the driver gauge binnacle.
  driver=smooth(-.62,-.55,x)*(1-smooth(-.16,-.06,x))
  near=1-smooth(.195,.355,y)
  ridge=smooth(.918,.968,z)
  dz=-.0031*driver*near*ridge
  dy=.00075*driver*near*ridge
 elif k=="cowl":
  # Turn the long flat cluster visor toward an inherited shallow convex lip.
  inboard=math.exp(-((x+.35)/.239)**4)
  face=1-smooth(.190,.29,y)
  dz=.0026*inboard*face
  dy=-.0011*inboard*face
 elif k=="spoke":
  # Roll the original three-spoke pressing, avoiding ALL 8 factory openings.
  aperture_clearance=min(math.hypot(x-a,z-b)/r for a,b,r in HOLES)
  safe=smooth(1.7,3.0,aperture_clearance)
  arms=smooth(.043,.115,abs(x+.35))
  metal=math.exp(-((y+.289)/.041)**2)
  band=math.exp(-((z-.788)/.065)**4)
  dy=.0021*safe*arms*metal*band
  dz=.0006*safe*arms*metal*band*math.tanh((x+.35)/.094)
 elif k=="rim":
  # Profile of inherited ring is refined in place, leaving object pivot.
  dx0=x+.35;dz0=z-.792
  radial=math.hypot(dx0,dz0)
  if radial>.12:
   dr=-.00072*math.tanh((radial-.176)/.012)
   dx=dr*dx0/radial
   dz=dr*dz0/radial
  dy=-.061*(y+.286)
 elif k=="emblem":
  # Unlike the oversized badge in previous driver view, authentic photo
  # shows a smaller yellow badge within a wider metal steering boss.
  # Directly shrink 4 existing ORIGINAL imported emblem vertices, same UV.
  dx=-.18*(x+.35)
  dz=-.18*(z-.79174)
  dy=-.00045
 elif k.startswith("vent_bezel_"):
  # Three EXISTING elongated dashboard ventilation bezels. Add actual
  # physical stepped lip depth by shifting the original leading vertices.
  cx=int(k.split("_")[-1])/1000.0
  ex=(x-cx)/.05452
  ez=(z-.943)/.02057
  rho=math.hypot(ex,ez)
  leading=1-smooth(.172,.180,y)
  edge=smooth(.36,.68,rho)*(1-smooth(1.00,1.22,rho))
  dy=-.0042*leading*edge+.0005*(1-leading)*edge
  dz=.00065*leading*edge*math.tanh((x-cx)/.037)
 elif k.startswith("vent_slat_"):
  # Deepen and lightly pitch the preexisting 3 louver blades of each
  # air vent; each blade stays a source-derived 27-v/32-face object.
  cx=int(k.split("_")[2])/1000.0
  lx=(x-cx)/.045
  dy=.0047+.0015*lx
  dz=.00065*math.tanh(lx)
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
 assert len(originals)==96,("PROTECTED_COUNT_MISMATCH",len(originals))
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
  assert moved>=({"upper":100,"cowl":800,"spoke":300,
   "rim":5000,"emblem":4,
   "vent_bezel_080":100,"vent_bezel_255":100,"vent_bezel_430":100,
   "vent_slat_080_0":27,"vent_slat_080_1":27,"vent_slat_080_2":27,
   "vent_slat_255_0":27,"vent_slat_255_1":27,"vent_slat_255_2":27,
   "vent_slat_430_0":27,"vent_slat_430_1":27,"vent_slat_430_2":27}[k]),("INSUFFICIENT_SOURCE_GEOMETRY",k,moved)
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
 data={"status":"SLOTA_R30_REAL_PMT_DERIVED_P0_GEOMETRY_SAVED",
 "slot":"A","car_id":"daytona365","native_PMT_sha256":HASH["pmt"],
 "original_import_blend_sha256":HASH["import"],"r29_input_sha256":HASH["base"],
 "r30_output_blend_sha256":digest(OUT),
 "factory_original_object_names":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "exact_Spider_LHD_private_photo_sha256":HASH["photo"],
 "edited_existing_original_derived_meshes":report,
 "other_96_source_meshes_sha256":hashlib.sha256(json.dumps(originals,sort_keys=True).encode()).hexdigest(),
 "eight_original_steering_spoke_holes_open":True,
 "no_new_objects_meshes_materials_textures_or_other_vehicles":True,
 "camera_matrices_steering_pivots_UV_and_materials_unchanged":True,
 "no_OVC3_OVC_PMT_export_no_game_VR_integration":True,
 "original_game_eye":"NOT_CALIBRATED","seven_exact_Spider_views":"INCOMPLETE",
 "GitHub_hosted_private_blend_audit":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(data,indent=2),encoding="utf8")
 print("SLOTA_R30_BUILD_PASS",json.dumps({"r30":data["r30_output_blend_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy,bmesh
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve(),"BLOCKED_FRESH_REOPEN_SOURCE"
 assert AUDIT.is_file() and not QA.exists() and not RENDER.exists()
 gate();a=json.loads(AUDIT.read_text())
 assert digest(OUT)==a["r30_output_blend_sha256"]
 others={o.name:coords_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(others)==96
 assert hashlib.sha256(json.dumps(others,sort_keys=True).encode()).hexdigest()==a["other_96_source_meshes_sha256"]
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
 cd=bpy.data.cameras.new("R30_UNSAVED_APPROXIMATE_EYE")
 cam=bpy.data.objects.new("R30_UNSAVED_APPROXIMATE_EYE",cd)
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
 assert digest(OUT)==a["r30_output_blend_sha256"]
 qa={"status":"SLOTA_R30_ACTUAL_OFFICIAL_BLENDER_4_5_15_FRESH_REOPEN_CYCLES_PASS",
  "private_blend_sha256":digest(OUT),"actual_Cycles_png_sha256":digest(RENDER),
  "resolution":[720,480],"samples":3,"independently_verified_meshes":findings,
  "unmodified_other_meshes":96,"eight_factory_spoke_holes":"PASS",
  "exact_game_driver_eye":"NOT_CALIBRATED",
  "seven_Spider_photo_angle_matching":"INCOMPLETE",
  "GitHub_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R30_FRESH_REOPEN_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
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
 qa["r29_vs_r30_gt3_rgb_pixels"]=changed
 qa["r29_render_sha256"]=digest(PREV_PNG)
 qa["r30_render_sha256"]=digest(RENDER)
 qa["side_by_side_comparison_sha256"]=digest(COMPARE)
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R30_R29_R30_REAL_RENDER_COMPARE_PASS",changed,digest(COMPARE),flush=True)
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