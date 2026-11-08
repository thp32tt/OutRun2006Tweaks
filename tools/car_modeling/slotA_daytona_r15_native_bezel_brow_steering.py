#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona SLOT A R15 -- original OutRun 2006 geometry only.
Tight provenance: original native .sz + original imported .blend -> verified R14
private scene -> R15 edited ORIGINAL-DERIVED cockpit mesh. No unrelated objects.
No PMT/OVC/OVC3/GLB, textures, materials, outside body, game, VR or other slots.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, math, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(os.environ["SLOT_A_WORK"])
OLD=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v12_r14.blend"
NEW=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v13_r15.blend"
PREV=ROOT/"SLOT_A_DAYTONA_P0_R14_NATIVE_DASH_COWL_WHEEL_GRIP.json"
AUDIT=ROOT/"SLOT_A_DAYTONA_P0_R15_NATIVE_BEZEL_BROW_STEERING.json"
QA=ROOT/"SLOTA_R15_INDEPENDENT_REAL_SCENE_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R15_AFTER_REAL_CYCLES_APPROX_EYE.png"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED={
 "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "r14":"ce021c82b8b26a9edfaef3c6dcc953ee133717f875d0ba32cd8b6b474a7b23df",
 "photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
PARTS={"dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"brow":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7))
 for v in o.data.vertices],[(f.material_index,tuple(f.vertices)) for f in o.data.polygons])).encode()).hexdigest()
def matrix(o):return [[round(float(v),9) for v in row] for row in o.matrix_world]
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3.-2.*t)
def holes(o):
 bpy.context.view_layer.update()
 t=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
 def hit(x,z):return t.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def objstate(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "signature":sig(o),"matrix":matrix(o),"uv":[x.name for x in o.data.uv_layers],
 "materials":[x.name if x else None for x in o.data.materials]}
def verify_sources():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT: Blender 4.5.15 required"
 for label,p,h in (("original game PMT",PMT,EXPECTED["pmt"]),
 ("original import blend",IMPORT,EXPECTED["import"]),
 ("R14 genuine editable",OLD,EXPECTED["r14"]),
 ("1971 Spider LHD photo",PHOTO,EXPECTED["photo"])):
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SHA",label)
 assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert "object22_group00_material000_a0" in bpy.data.objects or \
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0" in bpy.data.objects
def build():
 assert Path(bpy.data.filepath).resolve()==OLD.resolve(),"BLOCKED_INPUT: R14 private original required"
 assert not NEW.exists() and not AUDIT.exists(),"R15 immutable output collision"
 verify_sources()
 prev=json.loads(PREV.read_text())
 assert prev["slot"]=="A" and prev["car_id"]=="daytona365"
 assert prev["output_blend_sha256"]==EXPECTED["r14"]
 assert prev["original_native_pmt_sha256"]==EXPECTED["pmt"]
 assert prev["original_import_blend_sha256"]==EXPECTED["import"]
 objs={k:bpy.data.objects[n] for k,n in PARTS.items()}
 BEFORE={k:objstate(o) for k,o in objs.items()}
 for k,o in objs.items():
  assert o.type=="MESH" and o.data.users==1
  prior=prev["source_derived_original_objects"][k]["after"]
  assert BEFORE[k]["vertices"]==prior["verts"] and BEFORE[k]["faces"]==prior["faces"] and BEFORE[k]["signature"]==prior["signature"],("R14 source mesh signature",k)
  assert BEFORE[k]["name"]==prior["name"] and BEFORE[k]["matrix"]==prior["matrix"] and BEFORE[k]["uv"]==prior["uv"] and BEFORE[k]["materials"]==prior["materials"],("R14 source identity",k)
 assert all(holes(objs["spoke"])),"BLOCKED_INPUT: native eight source holes already damaged"
 keep={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(keep)==107
 baseline={"objects":set(bpy.data.objects),"materials":set(bpy.data.materials),
 "curves":set(bpy.data.curves),"camera":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"},
 "images":{im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}}
 # Existing source-derived gauge metal bezel gains ACTUAL edge loops, not another mesh or primitive.
 o=objs["bezel"];bm=bmesh.new();bm.from_mesh(o.data)
 try:
  bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True,smooth=0.0)
  assert len(bm.verts)>len(o.data.vertices) and len(bm.faces)>len(o.data.polygons)
  bm.to_mesh(o.data)
 finally:bm.free()
 o.data.update()
 changes={}
 for k,o in objs.items():
  inv=o.matrix_world.inverted();n=0;mx=0.;acc=0.
  for v in o.data.vertices:
   p=o.matrix_world@v.co
   dx=dy=dz=0.
   if k=="dashboard":
    # Modelled from exact Spider reference: gently raised padded front shelf
    # below clock hood, tapering to untouched ends. No independent object.
    lateral=smooth(-.664,-.600,p.x)*(1.-smooth(-.110,-.053,p.x))
    band=smooth(.729,.788,p.z)*(1.-smooth(.914,.955,p.z))
    front=1.-smooth(.185,.232,p.y)
    arch=math.exp(-((p.x+.35)/.198)**4)
    dz=.0038*lateral*band*front*(.45+.55*arch)
    dy=-.0035*lateral*band*front
   elif k=="brow":
    # Photo-matched padded instrument shroud with lowered leading edge
    # and gently arched crown, still same original source-derived topology.
    lateral=smooth(-.634,-.609,p.x)*(1.-smooth(-.085,-.051,p.x))
    lead=1.-smooth(.136,.188,p.y)
    center=math.exp(-((p.x+.348)/.211)**4)
    under=1.-smooth(.930,.957,p.z)
    upper=smooth(.934,.956,p.z)
    dz=-.0065*lateral*lead*under*(.56+.44*center)+.0028*lateral*lead*upper*center
    dy=-.0048*lateral*lead*(.4+.6*center)
   elif k=="bezel":
    # Original source-derived chrome rings: pressed circular lip and
    # inset flange using NEW IN-PLACE interpolated mesh loops.
    front=math.exp(-((p.y-.1511)/.0014)**2)
    shoulder=math.exp(-((p.y-.1549)/.0017)**2)
    back=math.exp(-((p.y-.1572)/.0013)**2)
    dy=-.0034*front+.0016*shoulder-.0004*back
    dz=.0013*front*math.tanh((p.z-.824)/.031)
   elif k=="spoke":
    # Visually restore a rolled pressing around the eight VERIFIED
    # genuine metal holes without sealing any hole/cutting new holes.
    hs=[math.hypot(p.x-hx,p.z-hz)/rad for hx,hz,rad in HOLES]
    g=min(hs);safe=smooth(1.04,1.55,g)
    edge=max(math.exp(-((d-1.30)/.23)**2) for d in hs)
    arms=math.exp(-((p.z-.802)/.024)**4)*smooth(.036,.088,abs(p.x+.35))
    tail=math.exp(-((p.z-.741)/.063)**4)*math.exp(-((p.x+.35)/.029)**4)
    facing=math.exp(-((p.y+.286)/.019)**2)
    dy=-.0026*edge*facing+.0013*safe*(arms+.8*tail)*facing
    dz=-.0006*edge*facing*math.tanh((p.z-.764)/.027)
   elif k=="rim":
    # Existing ring center is unchanged. Oval section like Daytona
    # leather wheel (radial broader, axial shallower) with 10/2 hand grip.
    u=p.x+.35;w=p.z-.792;r=math.hypot(u,w)
    if r>.01:
     # radial tube around 174 mm centerline, intentionally modest <= 3 mm.
     radial=(r-.1740)
     d=.15*radial
     dx=d*u/r;dz=d*w/r
     angle=math.atan2(w,u)
     upper=math.exp(-((angle-.80)/.27)**4)+math.exp(-((angle-2.34)/.27)**4)
     grip=upper*math.exp(-((p.y+.284)/.016)**2)
     dx+=.00135*grip*u/r;dz+=.00135*grip*w/r
    dy=-.17*(p.y+.286)
   elif k=="hub":
    # Existing shaft/column flange shoulder and axial roll.
    r=math.hypot(p.x+.35,p.z-.767)
    ring=math.exp(-((p.y+.251)/.009)**2)*smooth(.010,.020,r)
    if r>1e-7:
     dx=.00165*ring*(p.x+.35)/r
     dz=.00165*ring*(p.z-.767)/r
    dy=-.0018*ring
   d=Vector((dx,dy,dz))
   if d.length<.000022:continue
   v.co=inv@(p+d);n+=1
   mx=max(mx,d.length*1000.);acc+=d.length*1000.
  o.data.update()
  assert n>={"dashboard":90,"brow":180,"bezel":350,"spoke":600,"rim":5000,"hub":25}[k],(k,n)
  assert mx<9.0,(k,mx)
  after=objstate(o)
  assert after["signature"]!=BEFORE[k]["signature"],k
  for unchanged in ("name","matrix","uv","materials"):
   assert after[unchanged]==BEFORE[k][unchanged],(k,unchanged)
  if k!="bezel":
   assert (after["vertices"],after["faces"])==(BEFORE[k]["vertices"],BEFORE[k]["faces"])
  else:
   assert after["vertices"]>BEFORE[k]["vertices"] and after["faces"]>BEFORE[k]["faces"]
  changes[k]={"before":BEFORE[k],"after":after,"moved":n,"max_mm":round(mx,5),"mean_mm":round(acc/n,5)}
 assert all(holes(objs["spoke"])),"SLOTA native eight through holes SEALED"
 assert set(bpy.data.objects)==baseline["objects"] and set(bpy.data.materials)==baseline["materials"]
 assert set(bpy.data.curves)==baseline["curves"]
 assert {o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}==baseline["camera"]
 assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==baseline["images"]
 assert {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}==keep
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(NEW),compress=True)
 assert NEW.is_file() and NEW.stat().st_size>1_000_000
 record={"result":"SLOTA_R15_NATIVE_SOURCE_MESH_GEOMETRY_SAVED","car":"daytona365","slot":"A",
 "blender":bpy.app.version_string,"original_native_resource":PMT.name,"pmt_sha256":EXPECTED["pmt"],
 "import_sha256":EXPECTED["import"],"photo_sha256":EXPECTED["photo"],
 "prior_r14_sha256":EXPECTED["r14"],"output_blend":NEW.name,"output_sha256":sha(NEW),
 "output_bytes":NEW.stat().st_size,
 "original_native_mesh_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "original_derived_existing_meshes":changes,
 "protected_107_other_mesh_sha256":hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest(),
 "bezel_real_topology_edited":True,"spoke_8_holes_open":True,
 "same_camera_pivots_UVs_materials_images":True,
 "no_new_objects_or_substitute_vehicle":True,"no_new_texture_PBR_normal_exterior":True,
 "no_PMT_OVC3_OVC_or_game_export":True,"driver_eye":"APPROXIMATE_NOT_GAME",
 "seven_Spider_photo_views":"INCOMPLETE","github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 AUDIT.write_text(json.dumps(record,indent=2))
 print(record["result"],json.dumps({"sha":record["output_sha256"],"moved":{k:v["moved"] for k,v in changes.items()},
 "before_after":{k:[[v["before"]["vertices"],v["before"]["faces"]],[v["after"]["vertices"],v["after"]["faces"]]] for k,v in changes.items()}},ensure_ascii=False),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==NEW.resolve(),"BLOCKED_INPUT: reopen actual R15 .blend"
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
 verify_sources()
 a=json.loads(AUDIT.read_text())
 assert a["slot"]=="A" and a["car"]=="daytona365"
 assert sha(NEW)==a["output_sha256"]
 keep={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(keep)==107
 assert hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest()==a["protected_107_other_mesh_sha256"]
 topo={}
 for k,v in a["original_derived_existing_meshes"].items():
  o=bpy.data.objects[v["after"]["name"]]
  assert objstate(o)==v["after"] and v["before"]["signature"]!=v["after"]["signature"],k
  assert all(math.isfinite(c) for vv in o.data.vertices for c in vv.co),(k,"nonfinite")
  bm=bmesh.new();bm.from_mesh(o.data)
  topo[k]={"vertices":len(bm.verts),"faces":len(bm.faces),
           "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert topo["dashboard"]["nonmanifold_edges"]==184
 assert topo["spoke"]["nonmanifold_edges"]==1597
 assert topo["rim"]["nonmanifold_edges"]==0
 assert topo["bezel"]["vertices"]>908 and topo["bezel"]["faces"]>1344
 assert all(holes(bpy.data.objects[PARTS["spoke"]]))
 sc=bpy.context.scene
 # Transient QA camera ONLY, no save after inserting camera.
 cam_data=bpy.data.cameras.new("SLOTA_R15_APPROX_DRIVER_EYE_TRANSIENT")
 cam=bpy.data.objects.new("SLOTA_R15_APPROX_DRIVER_EYE_TRANSIENT",cam_data)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 look=Vector((-.24,.19,.797))
 cam.rotation_euler=(look-cam.location).to_track_quat("-Z","Y").to_euler()
 cam_data.type="PERSP";cam_data.lens=28;cam_data.clip_start=.01
 sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(NEW)==a["output_sha256"]
 r={"result":"SLOTA_R15_TRUE_ORIGINAL_SOURCE_BLEND_INDEPENDENT_REOPEN_CYCLES_PASS",
 "car":"daytona365","slot":"A","blender":bpy.app.version_string,
 "pmt_sha256":EXPECTED["pmt"],"import_sha256":EXPECTED["import"],
 "r14_sha256":EXPECTED["r14"],"r15_blend_sha256":sha(NEW),
 "r15_render_sha256":sha(PNG),"render":PNG.name,
 "render_resolution":[720,480],"samples":3,
 "geometry":topo,"protected_other_meshes":107,"native_spoke_holes":8,
 "camera":"APPROXIMATE_NOT_GAME","seven_Spider_views":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0,"no_export":True}
 QA.write_text(json.dumps(r,indent=2))
 print(r["result"],json.dumps({"blend":r["r15_blend_sha256"],"render":r["r15_render_sha256"],"mesh":topo}),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOT_A_R15_MODE")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("SLOT_A_R15_MODE must be build or verify")