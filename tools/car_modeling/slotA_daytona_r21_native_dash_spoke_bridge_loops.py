#!/usr/bin/env python3
"""SLOT A / OutRun 2006 Ferrari 365 GTS/4 Daytona R21.
Edit ONLY source-derived EXISTING cockpit Blender meshes. Private PMT and native
import are hashed read-only witnesses. Verified private R20 .blend is the required editable input.
P0 original-derived padded dashboard/binnacle + existing steering bridge meshes:
insert true longitudinal edge loops into existing three spoke bridge meshes,
sculpt an authentic gentle taper/crown without introducing substitute geometry.
No new vehicle/part objects or texture/material/PBR changes. No game export.
"""
from pathlib import Path
import bpy,bmesh,hashlib,json,math,os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
SOURCE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v18_r20.blend"
OUTPUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v19_r21.blend"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
PRIOR=ROOT/"SLOTA_R19_USER_FEEDBACK_SOURCE_GEOMETRY_AUDIT.json"
AUDIT=ROOT/"SLOTA_R21_NATIVE_DASH_BRIDGE_TOPOLOGY.json"
QA=ROOT/"SLOTA_R21_FRESH_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R21_AFTER_REAL_CYCLES_APPROX_EYE.png"
EXPECTED={
"source":"0e0d403e512d4f4612817fb71b9796fc84f2f58cc52b9b3625497727fbab8fcd",
"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
PARTS={
"dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"binnacle":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"left_spoke_bridge":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
"right_spoke_bridge":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
"lower_spoke_bridge":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"}
BRIDGES={"left_spoke_bridge","right_spoke_bridge","lower_spoke_bridge"}
FACTORY_SPOKE="V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"
RAW_DASH="V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
 [(f.material_index,tuple(f.vertices)) for f in o.data.polygons])).encode()).hexdigest()
def matrix(o):return [[round(float(a),9) for a in row] for row in o.matrix_world]
def state(o):
 return dict(name=o.name,vertices=len(o.data.vertices),faces=len(o.data.polygons),
  signature=sig(o),matrix=matrix(o),uv=[a.name for a in o.data.uv_layers],
  materials=[a.name if a else None for a in o.data.materials],hide_render=bool(o.hide_render))
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3.-2.*t)
def holes():
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(bpy.data.objects[FACTORY_SPOKE],bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return tree.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def gate():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_4515"
 assert Path(bpy.data.filepath).resolve()==SOURCE.resolve(),"BLOCKED_INPUT_NOT_R19"
 for tag,p,d in (("R19",SOURCE,EXPECTED["source"]),("ORIGINAL_PMT",PMT,EXPECTED["pmt"]),
  ("ORIGINAL_NATIVE_IMPORT",IMPORT,EXPECTED["import"]),("SPIDER_LHD_PHOTO",PHOTO,EXPECTED["photo"])):
  assert p.is_file() and sha(p)==d,("BLOCKED_INPUT_SHA",tag)
 assert PRIOR.is_file() and json.loads(PRIOR.read_text())["private_r19_output_sha256"]=="237f0add4f0a6e931bfcb86c24e0ac5aede13f05147c2be18116f1096b36c779"
 r20_audit=ROOT/"SLOTA_R20_REMOVE_FALSE_PHOTO_OVERLAP_BAR_SOURCE_AUDIT.json"
 assert r20_audit.is_file() and json.loads(r20_audit.read_text())["private_output_r20_sha256"]==EXPECTED["source"]
 assert len(bpy.data.objects[RAW_DASH].data.vertices)==13
 assert len(bpy.data.objects[FACTORY_SPOKE].data.vertices)==9720
 assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert all(holes()),"BLOCKED_NATIVE_EIGHT_HOLES"
def snapshot():
 protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(protected)==108,("PROTECTED_MESH_COUNT",len(protected))
 base=dict(
  objects=sorted(bpy.data.objects.keys()),meshes=sorted(bpy.data.meshes.keys()),
  materials=sorted(bpy.data.materials.keys()),curves=sorted(bpy.data.curves.keys()),
  images={a.name:[list(a.size),bool(a.packed_file)] for a in bpy.data.images},
  cameras={o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"})
 return protected,base
def invariants(protected,base):
 assert sorted(bpy.data.objects.keys())==base["objects"],"NEW_OBJECT"
 assert sorted(bpy.data.meshes.keys())==base["meshes"],"NEW_MESH_DATABLOCK"
 assert sorted(bpy.data.materials.keys())==base["materials"],"MATERIAL_EDIT"
 assert sorted(bpy.data.curves.keys())==base["curves"],"CURVE_EDIT"
 assert {a.name:[list(a.size),bool(a.packed_file)] for a in bpy.data.images}==base["images"],"IMAGE_EDIT"
 assert {o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}==base["cameras"],"CAMERA_EDIT"
 assert {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}==protected,"NON_TARGET_EDIT"
 assert all(holes()),"SOURCE_STEERING_HOLES_CHANGED"
def sculpt_dash(k,p):
 x,y,z=p
 if k=="dashboard":
  span=smooth(-.631,-.572,x)*(1-smooth(-.134,-.079,x))
  brow=math.exp(-((x+.356)/.210)**4)
  forward=1-smooth(.170,.253,y)
  height=smooth(.805,.845,z)*(1-smooth(.912,.945,z))
  return Vector((0.,-.00090*span*forward*brow, .00185*span*forward*height*(.45+.55*brow)))
 if k=="binnacle":
  center=math.exp(-((x+.351)/.216)**4)
  forward=1-smooth(.219,.297,y)
  side=smooth(-.635,-.595,x)*(1-smooth(-.105,-.051,x))
  dz=(.00365*center-.00095*(1-center))*forward*side
  dy=-.0024*center*forward*side
  return Vector((0.,dy,dz))
 raise AssertionError(k)
def refine_bridge(o,k):
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
 axis=2 if k=="lower_spoke_bridge" else 0
 longitudinal=[e for e in bm.edges if abs(e.verts[0].co[axis]-e.verts[1].co[axis])>.070]
 assert len(longitudinal)==4,(k,"BAD_EXISTING_LONGITUDINAL_EDGES",len(longitudinal))
 before=(len(bm.verts),len(bm.faces))
 assert before==(8,6),(k,before)
 bmesh.ops.subdivide_edges(bm,edges=longitudinal,cuts=3,use_grid_fill=True)
 bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
 after=(len(bm.verts),len(bm.faces))
 assert after[0]>before[0] and after[1]>before[1],(k,"NO_TOPOLOGY_CHANGE",after)
 assert sum(not e.is_manifold for e in bm.edges)==0,(k,"BRIDGE_NONMANIFOLD")
 bm.to_mesh(o.data);bm.free();o.data.update()
 inv=o.matrix_world.inverted()
 moved=0;max_move=0.
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  if k=="lower_spoke_bridge":
   t=smooth(.6205,.6975,p.z)
   center_x=-.350
   orig_half=.0037+.0040*t
   half=.0037+.0040*t*t*(3.-2.*t) - .00075*math.sin(math.pi*t)**2
   x=center_x+(1 if p.x>center_x else -1)*half
   z=p.z
  else:
   t=smooth(-.5215,-.4445,p.x) if k=="left_spoke_bridge" else 1.-smooth(-.2555,-.1785,p.x)
   # On right bridge the coordinate decreases from outer to inner.
   if k=="right_spoke_bridge":
    t=1.-smooth(-.2555,-.1785,p.x)
   center_z=.792+.002*t
   orig_half=.004+.0038*t
   half=.004+.0038*t*t*(3.-2.*t)-.00075*math.sin(math.pi*t)**2
   z=center_z+(1 if p.z>center_z else -1)*half
   x=p.x
  # Shallow stamped-metal bridge bow: front/rear faces shift together,
  # sheet thickness, native pivots and end anchors unchanged.
  y=p.y-.0016*math.sin(math.pi*t)**2
  dest=Vector((x,y,z))
  moved_delta=(dest-p).length
  if moved_delta>0.000001:
   v.co=inv@dest;moved+=1;max_move=max(max_move,moved_delta)
 o.data.update()
 assert moved>=8 and max_move<.004,(k,moved,max_move)
 return dict(before_topology=before,after_topology=after,moved_vertices=moved,max_move_model_units=max_move)
def run_build():
 gate()
 assert not OUTPUT.exists() and not AUDIT.exists(),"IMMUTABLE_R20_EXISTS"
 prior=json.loads(PRIOR.read_text())
 protected,base=snapshot()
 old={k:state(bpy.data.objects[name]) for k,name in PARTS.items()}
 for k in ("binnacle","left_spoke_bridge","right_spoke_bridge","lower_spoke_bridge"):
  prior_name={"binnacle":"instrument_visor"}.get(k,k)
  assert old[k]==prior["updated_existing_meshes"][prior_name]["after"],("R19_MESH_DRIFT",k)
 report={}
 for k,name in PARTS.items():
  obj=bpy.data.objects[name];before=old[k]
  if k in BRIDGES:
   detail=refine_bridge(obj,k)
  else:
   inv=obj.matrix_world.inverted();moves=0;mx=0.
   for v in obj.data.vertices:
    oldworld=obj.matrix_world@v.co
    delta=sculpt_dash(k,oldworld)
    if delta.length<.00001:continue
    v.co=inv@(oldworld+delta);moves+=1;mx=max(mx,delta.length)
   obj.data.update()
   assert moves>= (90 if k=="dashboard" else 600),(k,moves)
   assert mx<.005,(k,mx)
   detail=dict(before_topology=(before["vertices"],before["faces"]),after_topology=(len(obj.data.vertices),len(obj.data.polygons)),
    moved_vertices=moves,max_move_model_units=mx)
  after=state(obj)
  for tag in ("name","matrix","uv","materials","hide_render"):
   assert before[tag]==after[tag],(k,tag,"IDENTITY_DRIFT")
  assert before["signature"]!=after["signature"],(k,"NO_REAL_GEOMETRY_CHANGE")
  report[k]={"before":before,"after":after,**detail}
 invariants(protected,base)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 assert OUTPUT.is_file() and OUTPUT.stat().st_size>1_000_000
 rec=dict(status="R21_REAL_NATIVE_EDITABLE_COCKPIT_GEOMETRY_SAVED",
  slot="A",car="daytona365",revision="r21",
  original_game_resource=PMT.name,original_pmt_sha256=EXPECTED["pmt"],
  original_import_sha256=EXPECTED["import"],
  raw_original_object_ids=["object00_group01_material012_a0","object22_group00_material000_a0"],
  input_r20_sha256=EXPECTED["source"],output_r21_sha256=sha(OUTPUT),
  output_filename=OUTPUT.name,exact_spider_LHD_photo_sha256=EXPECTED["photo"],
  modified_original_derived_existing_objects=report,
  other_108_mesh_signatures_sha256=hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
  original_8_steering_spoke_holes_open=True,
  original_camera_matrices_steering_animation_pivots_unchanged=True,
  materials_UVs_images_not_remade=True,no_texture_normal_PBR_or_exterior=True,
  no_PMT_OVC3_OVC_GLB_game_or_VR_export=True,
  actual_game_driver_eye="NOT_CALIBRATED",
  seven_exact_spider_views="INCOMPLETE",
  github_actions_original_private_scene="BLOCKED_INPUT_NOT_TRANSFERRED",
  vehicle_complete=False,score_change=0)
 AUDIT.write_text(json.dumps(rec,indent=2),encoding="utf-8")
 print("SLOTA_R21_NATIVE_EXISTING_P0_MESH_EDIT_SAVED",json.dumps({"sha":rec["output_r21_sha256"],
  "geometry":{k:{"from":v["before_topology"],"to":v["after_topology"],"moved":v["moved_vertices"]} for k,v in report.items()}}),flush=True)
def run_verify():
 assert Path(bpy.data.filepath).resolve()==OUTPUT.resolve(),"BLOCKED_R21_REOPEN"
 assert AUDIT.is_file() and not PNG.exists() and not QA.exists(),"IMMUTABLE_R21_QA_EXISTS"
 for k,p in (("source",SOURCE),("pmt",PMT),("import",IMPORT),("photo",PHOTO)):
  assert sha(p)==EXPECTED[k],("INDEPENDENT_SOURCE_CHANGED",k)
 rec=json.loads(AUDIT.read_text())
 assert sha(OUTPUT)==rec["output_r21_sha256"]
 protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(protected)==108
 assert hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()==rec["other_108_mesh_signatures_sha256"]
 assert all(holes()),"EIGHT_SOURCE_HOLES_CLOSED"
 topo={}
 for k,v in rec["modified_original_derived_existing_objects"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert state(o)==v["after"],(k,"REOPEN_GEOMETRY_MISMATCH")
  bm=bmesh.new();bm.from_mesh(o.data)
  nonmanifold=sum(not e.is_manifold for e in bm.edges)
  topo[k]=dict(vertices=len(bm.verts),faces=len(bm.faces),nonmanifold_edges=nonmanifold)
  bm.free()
  if k in BRIDGES: assert nonmanifold==0,(k,"BROKEN_STEERING_BRIDGE")
 assert len(bpy.data.objects[RAW_DASH].data.vertices)==13
 assert len(bpy.data.objects[FACTORY_SPOKE].data.vertices)==9720
 sc=bpy.context.scene
 data=bpy.data.cameras.new("R21_TEMP_APPROX_EYE_NOT_SAVED")
 cam=bpy.data.objects.new("R20_TEMP_APPROX_EYE_NOT_SAVED",data)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 data.lens=28;data.clip_start=.01
 sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG);bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(OUTPUT)==rec["output_r21_sha256"]
 qa=dict(status="R21_NATIVE_PRIVATE_BLEND_FRESH_REOPEN_REAL_CYCLES_PASS",slot="A",
  car="daytona365",input_r20_sha256=EXPECTED["source"],r21_sha256=sha(OUTPUT),
  private_actual_cycles_sha256=sha(PNG),resolution=[720,480],samples=3,blender=bpy.app.version_string,
  changed_existing_mesh_topology=topo,other_108_meshes_untouched=True,
  eight_native_spoke_through_holes=True,original_eye="APPROXIMATE_NOT_GAME",
  github_actions_private_scene="BLOCKED_INPUT_NOT_TRANSFERRED",vehicle_complete=False,score_change=0)
 QA.write_text(json.dumps(qa,indent=2),encoding="utf-8")
 print("SLOTA_R21_NATIVE_FRESH_REOPEN_REAL_CYCLES_PASS",json.dumps(qa),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOTA_R21_MODE")
 if mode=="build":run_build()
 elif mode=="verify":run_verify()
 else:raise SystemExit("SLOTA_R21_MODE must be build or verify")