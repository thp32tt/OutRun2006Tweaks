#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona, SLOT A R19 corrective original-derived mesh edit.

Direct user feedback: high disconnected cowl arc and block-like steering spoke
bridges are inconsistent with actual Daytona Spider dash/wheel photographs.

Only modify existing PMT-derived private R18 Blender scene in-place at the mesh
coordinate level, saving a NEW private R19 .blend. Never export PMT, OVC3, OVC,
GLB, native game or VR integration. Do not edit other vehicles, materials, PBR,
textures, UV names, transforms, source PMT or source .blend. Photographic
reference is for proportions only, not an inferred exact CAD measurement.
"""
from pathlib import Path
import bpy, bmesh, json, hashlib, math, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
SOURCE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v16_r18.blend"
OUTPUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v17_r19.blend"
AUDIT=ROOT/"SLOTA_R19_USER_FEEDBACK_SOURCE_GEOMETRY_AUDIT.json"
QA=ROOT/"SLOTA_R19_INDEPENDENT_REOPEN_CYCLES_AUDIT.json"
PNG=ROOT/"SLOTA_DAYTONA_R19_AFTER_REAL_CYCLES_APPROX_EYE.png"
PRIOR=ROOT/"SLOT_A_DAYTONA_P0_R18_NATIVE_DASH_SPOKE_RELIEF_GEOMETRY.json"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED={"r18":"9e280cba0bd3f90fbfb5a7a474452867302beca95c3eefc7a3a44aa6cca90117",
 "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
EDIT={
 "instrument_visor":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "misleading_stitch_arc":"DAYTONA_DASH_RAISED_STITCHING_ACTUAL_GEOMETRY",
 "left_spoke_bridge":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "right_spoke_bridge":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "lower_spoke_bridge":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
 "steering_rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "factory_spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
 (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
 (-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""): h.update(c)
 return h.hexdigest()
def signature(o):
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
  [(p.material_index,tuple(p.vertices)) for p in o.data.polygons])).encode()).hexdigest()
def matrix(o):
 return [[round(float(c),9) for c in row] for row in o.matrix_world]
def state(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "signature":signature(o),"matrix":matrix(o),"uv":[x.name for x in o.data.uv_layers],
 "materials":[m.name if m else None for m in o.data.materials],
 "hide_render":bool(o.hide_render)}
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3.-2.*t)
def source_gate():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_4_5_15"
 for n,p,h in (("SOURCE R18",SOURCE,EXPECTED["r18"]),("ORIGINAL PMT",PMT,EXPECTED["pmt"]),
  ("ORIGINAL PMT Blender Import",IMPORT,EXPECTED["import"]),("1971 Spider LHD photo",PHOTO,EXPECTED["photo"])):
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SHA",n)
 assert PRIOR.is_file() and json.loads(PRIOR.read_text())["r18_sha256"]==EXPECTED["r18"]
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[EDIT["factory_spoke"]].data.vertices)==9720
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
def all_holes(o):
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
 def ray(x,z):
  return tree.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.)[2] is not None
 return [not ray(x,z) and ray(x+1.6*r,z) for x,z,r in HOLES]
def snap():
 before={n:signature(o) for n,o in bpy.data.objects.items() if o.type=="MESH"}
 assert len(before)==113
 base={
 "objects":sorted(bpy.data.objects.keys()),
 "meshes":sorted(bpy.data.meshes.keys()),
 "materials":sorted(bpy.data.materials.keys()),
 "curves":sorted(bpy.data.curves.keys()),
 "images":{im.name:{"size":list(im.size),"packed":bool(im.packed_file)} for im in bpy.data.images},
 "cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"},
 "parts":{k:state(bpy.data.objects[v]) for k,v in EDIT.items()}
 }
 return before,base
def assert_preserved(before,base):
 assert sorted(bpy.data.objects.keys())==base["objects"],"OBJECTS_MODIFIED"
 assert sorted(bpy.data.meshes.keys())==base["meshes"],"MESH_DATABLOCKS_MODIFIED"
 assert sorted(bpy.data.materials.keys())==base["materials"],"MATERIALS_MODIFIED"
 assert sorted(bpy.data.curves.keys())==base["curves"],"CURVES_MODIFIED"
 assert {im.name:{"size":list(im.size),"packed":bool(im.packed_file)} for im in bpy.data.images}==base["images"],"IMAGES_CHANGED"
 assert {o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}==base["cameras"],"CAMERAS_CHANGED"
 untouched={n:v for n,v in before.items() if n not in EDIT.values()}
 assert len(untouched)==106,(len(untouched),"UNTOUCHED_COUNT")
 assert all(signature(bpy.data.objects[n])==v for n,v in untouched.items()),"OTHER_MESH_CHANGED"
 for k,name in EDIT.items():
  a=state(bpy.data.objects[name]);b=base["parts"][k]
  for tag in ("name","vertices","faces","matrix","uv","materials","hide_render"):
   assert a[tag]==b[tag],(k,tag)
 assert all(all_holes(bpy.data.objects[EDIT["factory_spoke"]])), "SOURCE_8_HOLES_CLOSED"
def edit_delta(part,p):
 dx=dy=dz=0.
 if part=="instrument_visor":
  # P0 corrective removal of false high arch: keep SOURCE-derivative hood mesh
  # but tuck the swollen standalone crest into the existing dashboard contour.
  # Linear positive z-scale cannot invert winding; no new object is created.
  target_z=.9035+.145*(p.z-.9070)
  dz=target_z-p.z
  dy=.082
 elif part=="misleading_stitch_arc":
  # This front strip formed another fake horizontal bar at the edge of gauges.
  # Recess existing curve inside dashboard, not delete any source mesh.
  dy=.099
  dz=-.016
 elif part in ("left_spoke_bridge","right_spoke_bridge"):
  # Existing 8-vertex chrome brick -> thin original-like tapered stamped metal.
  # Outer end touches steering rim, inner end overlaps the native 3-spoke metal.
  radial=abs(p.x+.35)
  t=smooth(.0945,.1715,radial)
  half=.0078-.0038*t
  mid_z=.794-.002*t
  dz=(mid_z+(half if p.z>.790 else -half))-p.z
  newy=-.2912+(.00140 if p.y>-.290 else -.00140)
  dy=newy-p.y
 elif part=="lower_spoke_bridge":
  t=smooth(.0945,.1715,abs(p.z-.792))
  half=.0077-.0040*t
  dx=(-.350+(half if p.x>-.35 else -half))-p.x
  dy=(-.2912+(.00140 if p.y>-.291 else -.00140))-p.y
 elif part=="steering_rim":
  # Reduce visually bulky toroidal cross section, preserve overall diameter,
  # rim centreline and original steer-axis/pivot.
  ux=p.x+.350;vz=p.z-.792
  radial=math.hypot(ux,vz)
  if radial>.06:
   tube=radial-.1740
   d=-.23*tube
   dx=d*ux/radial
   dz=d*vz/radial
  dy=-.16*(p.y+.286)
 elif part=="factory_spoke":
  # Taper native original-derived pressed tips OUTSIDE all 8 original holes;
  # no fake perforations, new rims, or replacement spokes.
  u=abs(p.x+.35)
  face=math.exp(-((p.y+.287)/.026)**2)
  side=smooth(.101,.116,u)*math.exp(-((p.z-.792)/.035)**4)*face
  lower=(1.-smooth(.687,.708,p.z))*math.exp(-((p.x+.35)/.028)**4)*face
  dz=-.18*(p.z-.792)*side
  dx=-.11*(p.x+.35)*lower
  dy=.00045*(side+lower)
 return Vector((dx,dy,dz))
def build():
 assert Path(bpy.data.filepath).resolve()==SOURCE.resolve(),"BLOCKED_INPUT_NOT_R18"
 assert not OUTPUT.exists() and not AUDIT.exists(),"IMMUTABLE_OUTPUT_EXISTS"
 source_gate()
 prev=json.loads(PRIOR.read_text())
 before,baseline=snap()
 for k in ("cowl","rim","spoke"):
  objname={"cowl":EDIT["instrument_visor"],"rim":EDIT["steering_rim"],"spoke":EDIT["factory_spoke"]}[k]
  assert signature(bpy.data.objects[objname])==prev["source_derived_existing_objects"][k]["after"]["signature"],"BAD_PRIOR_R18_PART_"+k
 assert all(all_holes(bpy.data.objects[EDIT["factory_spoke"]]))
 changes={}
 for part,n in EDIT.items():
  o=bpy.data.objects[n];inv=o.matrix_world.inverted()
  old=state(o);moved=0;max_mm=0.;sum_mm=0.
  for v in o.data.vertices:
   world=o.matrix_world@v.co
   delta=edit_delta(part,world)
   if delta.length<.000005:continue
   v.co=inv@(world+delta)
   moved+=1
   mm=delta.length*1000.
   max_mm=max(max_mm,mm);sum_mm+=mm
  o.data.update()
  now=state(o)
  assert now["signature"]!=old["signature"],part
  assert moved>={"instrument_visor":2000,"misleading_stitch_arc":150,
  "left_spoke_bridge":8,"right_spoke_bridge":8,"lower_spoke_bridge":8,
  "steering_rim":5000,"factory_spoke":50}[part],(part,moved)
  assert max_mm<{"instrument_visor":130.0,"misleading_stitch_arc":110.0,
  "left_spoke_bridge":15.0,"right_spoke_bridge":15.0,"lower_spoke_bridge":15.0,
  "steering_rim":6.0,"factory_spoke":4.5}[part],(part,max_mm)
  changes[part]={"source_name":n,"before":old,"after":now,"moved_vertices":moved,
   "max_mm":round(max_mm,5),"average_mm":round(sum_mm/moved,5)}
 assert_preserved(before,baseline)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 assert OUTPUT.is_file() and OUTPUT.stat().st_size>1000000
 untouched={n:v for n,v in before.items() if n not in EDIT.values()}
 rec={"status":"R19_REAL_ORIGINAL_DERIVED_VISUAL_CORRECTION_SAVED","slot":"A","car":"daytona365",
 "revision":"r19","blender":bpy.app.version_string,
 "original_game_pmt_path":str(PMT),"original_game_pmt_sha256":EXPECTED["pmt"],
 "original_import_path":str(IMPORT),"original_import_sha256":EXPECTED["import"],
 "raw_original_object_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "private_r18_source_sha256":EXPECTED["r18"],"private_r19_output_sha256":sha(OUTPUT),
 "private_output_filename":OUTPUT.name,"photo_sha256":EXPECTED["photo"],
 "updated_existing_meshes":changes,
 "untouched_106_meshes_sha256":hashlib.sha256(json.dumps(untouched,sort_keys=True).encode()).hexdigest(),
 "objects_materials_UVs_images_camera_matrices_pivots_preserved":True,
 "eight_original_stamped_spoke_holes_preserved":True,
 "no_PMT_OVC3_OVC_GLB_or_game_export":True,
 "no_new_texture_normal_PBR_or_exterior":True,
 "independent_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "actual_game_driver_eye":"NOT_CALIBRATED",
 "all_seven_exact_spider_views":"INCOMPLETE","vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(rec,indent=2),encoding="utf-8")
 print("SLOTA_R19_TRUE_SOURCE_COWL_WHEEL_CORRECTED",json.dumps({"sha":rec["private_r19_output_sha256"],
  "moved":{k:v["moved_vertices"] for k,v in changes.items()}},ensure_ascii=False),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==OUTPUT.resolve(),"BLOCKED_INPUT_NOT_R19"
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists(),"IMMUTABLE_QA_COLLISION"
 source_gate()
 rec=json.loads(AUDIT.read_text())
 assert sha(OUTPUT)==rec["private_r19_output_sha256"]
 old={k:v["before"] for k,v in rec["updated_existing_meshes"].items()}
 changes=rec["updated_existing_meshes"]
 untouched={o.name:signature(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in EDIT.values()}
 assert len(untouched)==106
 assert hashlib.sha256(json.dumps(untouched,sort_keys=True).encode()).hexdigest()==rec["untouched_106_meshes_sha256"]
 topo={}
 for k,v in changes.items():
  o=bpy.data.objects[v["source_name"]]
  assert state(o)==v["after"],("REOPEN_MESH_DIFFERENCE",k)
  bm=bmesh.new();bm.from_mesh(o.data)
  topo[k]={"vertices":len(bm.verts),"faces":len(bm.faces),"nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert all(all_holes(bpy.data.objects[EDIT["factory_spoke"]])),"REOPEN_SOURCE_HOLES_FAIL"
 assert topo["instrument_visor"]["nonmanifold_edges"]==0
 assert topo["factory_spoke"]["nonmanifold_edges"]==1597
 assert topo["steering_rim"]["nonmanifold_edges"]==0
 # Fresh-process Cycles. Camera is temporarily created, never saved.
 sc=bpy.context.scene
 camdata=bpy.data.cameras.new("R19_TRANSIENT_APPROX_EYE")
 cam=bpy.data.objects.new("R19_TRANSIENT_APPROX_EYE",camdata)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 camdata.lens=28;camdata.clip_start=.01
 sc.camera=cam;sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG"
 sc.render.image_settings.color_mode="RGBA";sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(OUTPUT)==rec["private_r19_output_sha256"]
 r={"status":"R19_REAL_BLENDER_INDEPENDENT_REOPEN_CYCLES_PASS","slot":"A","car":"daytona365",
 "source_r18_sha256":EXPECTED["r18"],"output_r19_sha256":sha(OUTPUT),
 "actual_cycles_sha256":sha(PNG),"actual_cycles_filename":PNG.name,
 "resolution":[720,480],"samples":3,"blender":bpy.app.version_string,
 "edited_mesh_topology":topo,"other_106_meshes_untouched":True,
 "source_8_spoke_holes":True,"photo_eye":"APPROXIMATE_NOT_GAME",
 "github_hosted_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(r,indent=2),encoding="utf-8")
 print("SLOTA_R19_INDEPENDENT_REOPEN_REAL_CYCLES_OK",json.dumps(r),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOTA_R19_MODE")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("set SLOTA_R19_MODE build or verify")