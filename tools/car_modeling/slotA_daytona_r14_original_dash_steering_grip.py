#!/usr/bin/env python3
"""Slot A ONLY: original OutRun 2006 Daytona cockpit R14.
In-place edits of six verified R13 source-derived MESH objects. No creation,
replacement model, native export, game install, texturing or outside-car edits.
Build and verify MUST run in separate official Blender 4.5.15 processes.
"""
import bpy, bmesh, hashlib, json, math, os, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(os.environ["SLOT_A_WORK"])
OLD=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v11_r13.blend"
NEW=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v12_r14.blend"
PRIOR=ROOT/"SLOT_A_DAYTONA_P0_R13_ORIGINAL_VISOR_RIM_EDGELOOPS.json"
REPORT=ROOT/"SLOT_A_DAYTONA_P0_R14_NATIVE_DASH_COWL_WHEEL_GRIP.json"
QA=ROOT/"SLOTA_R14_INDEPENDENT_NATIVE_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R14_AFTER_REAL_CYCLES_APPROX_EYE.png"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORTED=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"r13":"e8c63f9a92529c2580bb92e8b511533ac9efab7e89116fc8e40e12d74e347a51",
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
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def sig(ob):
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in ob.data.vertices],
 [(p.material_index,tuple(p.vertices)) for p in ob.data.polygons])).encode()).hexdigest()
def matrix(ob):
 return [[round(float(c),9) for c in row] for row in ob.matrix_world]
def smooth(lo,hi,v):
 t=max(0.,min(1.,(v-lo)/(hi-lo)))
 return t*t*(3.-2.*t)
def holes_open(ob):
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def check_roots():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT official Blender 4.5.15 required"
 for name,p,h in [("original native PMT",PMT,EXPECTED["pmt"]),("original native Blender",IMPORTED,EXPECTED["import"]),("genuine R13",OLD,EXPECTED["r13"]),("original Spider LHD photo",PHOTO,EXPECTED["photo"])]:
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SOURCE_SHA",name,str(p))
 assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert "object00_group01_material012_a0" in {o.name for o in bpy.data.objects} or "V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0" in bpy.data.objects
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
def mesh_state(ob):
 return {"name":ob.name,"verts":len(ob.data.vertices),"faces":len(ob.data.polygons),"signature":sig(ob),
 "matrix":matrix(ob),"uv":[u.name for u in ob.data.uv_layers],
 "materials":[m.name if m else None for m in ob.data.materials]}
def build():
 assert Path(bpy.data.filepath).resolve()==OLD.resolve(),"BLOCKED_INPUT: load genuine R13"
 assert not NEW.exists() and not REPORT.exists(),"immutable R14 output already exists"
 check_roots()
 old=json.loads(PRIOR.read_text())
 assert old["slot"]=="A" and old["car_id"]=="daytona365"
 assert old["output_blend_sha256"]==EXPECTED["r13"]
 assert old["original_native_PMT_sha256"]==EXPECTED["pmt"]
 assert old["verified_original_import_sha256"]==EXPECTED["import"]
 objs={key:bpy.data.objects[name] for key,name in PARTS.items()}
 before={key:mesh_state(ob) for key,ob in objs.items()}
 for key,ob in objs.items():
  prev=old["source_derived_original_mesh_changes"][key]
  assert ob.type=="MESH" and ob.data.users==1
  assert before[key]["signature"]==prev["after_mesh_signature"]
  assert (before[key]["verts"],before[key]["faces"])==(prev["after_vertices"],prev["after_faces"])
 assert all(holes_open(objs["spoke"])),"source spoke through-hole missing"
 protected={ob.name:sig(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in PARTS.values()}
 assert len(protected)==107
 anchors={ob.name:matrix(ob) for ob in bpy.data.objects if ob.type=="CAMERA"}
 original_names=set(bpy.data.objects)
 materials=set(bpy.data.materials)
 curves=set(bpy.data.curves)
 imgs={im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}
 changes={}
 for key,ob in objs.items():
  inv=ob.matrix_world.inverted()
  changed=0;maximum=0.;total=0.
  for vert in ob.data.vertices:
   p=ob.matrix_world@vert.co
   dx=dy=dz=0.
   if key=="dashboard":
    # Source dashboard padded shelf, photo: rolled lip continuous beneath
    # the instrument hood (no disconnected faux pad).
    lateral=smooth(-.665,-.603,p.x)*(1.-smooth(-.106,-.055,p.x))
    height=smooth(.744,.812,p.z)*(1.-smooth(.931,.955,p.z))
    forward=1.-smooth(.193,.231,p.y)
    rise=math.exp(-((p.x+.353)/.202)**4)
    dz=-.0030*lateral*height*forward*(.55+.45*rise)
    dy=-.0026*lateral*height*forward*(.45+.55*rise)
   elif key=="brow":
    # Smooth original-derived instrument visor's front roll and crown.
    lateral=smooth(-.633,-.607,p.x)*(1.-smooth(-.082,-.053,p.x))
    lip=1.-smooth(.132,.176,p.y)
    top=smooth(.925,.949,p.z)
    center=math.exp(-((p.x+.35)/.190)**4)
    dz=.0034*lateral*lip*top*center-.0022*lateral*lip*top*(1.-center)
    dy=-.0035*lateral*lip*(.30+.70*center)
   elif key=="bezel":
    # Existing native-derived metal gauge bezel rolled front relief.
    leading=math.exp(-((p.y-.1560)/.00175)**2)
    back=math.exp(-((p.y-.1504)/.00115)**2)
    dy=-.0013*leading+.00065*back
    dz=.00063*leading*math.tanh((p.z-.825)/.035)
   elif key=="spoke":
    # Press relief into the REAL factory-derived 3-spoke mesh while
    # excluding each of its eight through-holes and their cut edges.
    gap=min(math.hypot(p.x-x,p.z-z)/r for x,z,r in HOLES)
    safe=smooth(1.10,2.0,gap)
    lip=max(math.exp(-((math.hypot(p.x-x,p.z-z)/r-1.75)/.37)**2) for x,z,r in HOLES)
    arms=math.exp(-((p.z-.806)/.024)**4)*smooth(.023,.090,abs(p.x+.35))
    tail=math.exp(-((p.z-.747)/.058)**4)*math.exp(-((p.x+.35)/.026)**4)
    front=math.exp(-((p.y+.285)/.015)**2)
    dy=(-.00155*lip+.00125*safe*(arms+.72*tail))*front
    dz=.00042*safe*arms*front*math.tanh((p.x+.35)/.045)
   elif key=="rim":
    # Real photo: slender round leather-rim silhouette. Retaper existing
    # original-derived ring's tube section, never move its center/pivot.
    rx=p.x+.35; rz=p.z-.792
    r=math.hypot(rx,rz)
    if r>.001:
     taper=-.14*(r-.1740)
     dx=taper*rx/r
     dz=taper*rz/r
    dy=-.12*(p.y+.2860)
   elif key=="hub":
    # Subtle original steering shaft collar taper.
    r=math.hypot(p.x+.35,p.z-.767)
    ridge=math.exp(-((p.y+.246)/.013)**2)*smooth(.006,.019,r)
    if r>.000001:
     dx=.0011*ridge*(p.x+.35)/r
     dz=.0011*ridge*(p.z-.767)/r
    dy=-.00085*ridge
   d=Vector((dx,dy,dz))
   if d.length<.000018:continue
   vert.co=inv@(p+d)
   changed+=1
   maximum=max(maximum,d.length*1000)
   total+=d.length*1000
  ob.data.update()
  assert changed>={"dashboard":85,"brow":160,"bezel":100,"spoke":120,"rim":3500,"hub":20}[key],(key,changed)
  assert maximum<7.0,(key,maximum)
  after=mesh_state(ob)
  assert after["signature"]!=before[key]["signature"]
  for invariant in ("name","verts","faces","matrix","uv","materials"):
   assert after[invariant]==before[key][invariant],(key,invariant)
  changes[key]={"before":before[key],"after":after,"changed_vertices":changed,
                "max_displacement_mm":round(maximum,5),"avg_displacement_mm":round(total/changed,5)}
 assert all(holes_open(objs["spoke"])),"eight source holes must remain physical"
 assert {ob.name:sig(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in PARTS.values()}==protected
 assert set(bpy.data.objects)==original_names and set(bpy.data.materials)==materials and set(bpy.data.curves)==curves
 assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==imgs
 assert {ob.name:matrix(ob) for ob in bpy.data.objects if ob.type=="CAMERA"}==anchors
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(NEW),compress=True)
 assert NEW.stat().st_size>1000000
 record={"result":"SLOTA_R14_GENUINE_ORIGINAL_DASH_VISOR_BEZEL_STEERING_GRIP_SAVED",
 "slot":"A","car_id":"daytona365","official_blender":bpy.app.version_string,
 "original_native_pmt_sha256":EXPECTED["pmt"],"original_import_blend_sha256":EXPECTED["import"],
 "exact_original_spider_photo_sha256":EXPECTED["photo"],"input_r13_sha256":EXPECTED["r13"],
 "source_blend":OLD.name,"output_blend":NEW.name,"output_blend_sha256":sha(NEW),
 "output_blend_bytes":NEW.stat().st_size,
 "original_mesh_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "source_derived_original_objects":changes,
 "protected_other_mesh_count":107,"protected_other_mesh_hash":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
 "original_spoke_eight_BVH_holes":True,"no_new_objects_materials_images_uv_or_cameras":True,
 "no_exterior_or_game_or_texture_or_export":True,
 "camera":"APPROXIMATE_NOT_ORIGINAL_GAME_DRIVER_EYE",
 "exact_spider_7_views":"INCOMPLETE","hosted_private_blend":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"slot_A_advance":False}
 REPORT.write_text(json.dumps(record,indent=2))
 print(record["result"],json.dumps({"sha":record["output_blend_sha256"],
 "moved":{k:v["changed_vertices"] for k,v in changes.items()},
 "max_mm":{k:v["max_displacement_mm"] for k,v in changes.items()}}),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==NEW.resolve(),"BLOCKED_INPUT: independently reopen true R14"
 assert REPORT.exists() and not QA.exists() and not PNG.exists(),"immutable R14 QA evidence"
 check_roots()
 r=json.loads(REPORT.read_text())
 assert r["slot"]=="A" and r["car_id"]=="daytona365"
 assert sha(NEW)==r["output_blend_sha256"]
 unchanged={ob.name:sig(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in PARTS.values()}
 assert len(unchanged)==107 and hashlib.sha256(json.dumps(unchanged,sort_keys=True).encode()).hexdigest()==r["protected_other_mesh_hash"]
 topology={}
 for k,v in r["source_derived_original_objects"].items():
  ob=bpy.data.objects[v["after"]["name"]]
  assert mesh_state(ob)==v["after"] and v["before"]["signature"]!=v["after"]["signature"]
  bm=bmesh.new();bm.from_mesh(ob.data)
  topology[k]={"verts":len(bm.verts),"faces":len(bm.faces),"nonmanifold":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert all(holes_open(bpy.data.objects[PARTS["spoke"]]))
 assert topology["dashboard"]["nonmanifold"]==184
 assert topology["bezel"]["nonmanifold"]==466
 assert topology["spoke"]["nonmanifold"]==1597
 assert topology["rim"]["nonmanifold"]==0
 # Identical approximate eye and Cycles settings to R13 for actual pixel comparison.
 sc=bpy.context.scene
 camdata=bpy.data.cameras.new("SLOTA_R14_TRANSIENT_APPROX_EYE")
 cam=bpy.data.objects.new("SLOTA_R14_TRANSIENT_APPROX_EYE",camdata)
 sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 look=Vector((-.24,.19,.797))
 cam.rotation_euler=(look-cam.location).to_track_quat("-Z","Y").to_euler()
 camdata.type="PERSP";camdata.lens=28;camdata.clip_start=.01
 sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52
 sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.exists() and PNG.stat().st_size>12000
 assert sha(NEW)==r["output_blend_sha256"]
 record={"result":"SLOTA_R14_INDEPENDENT_REAL_ORIGINAL_BLEND_REOPEN_CYCLES_PASS",
 "slot":"A","car_id":"daytona365","blender":bpy.app.version_string,
 "original_native_pmt_sha256":EXPECTED["pmt"],"original_import_blend_sha256":EXPECTED["import"],
 "r13_sha256":EXPECTED["r13"],"r14_sha256":sha(NEW),
 "render_png":PNG.name,"render_sha256":sha(PNG),"resolution":[720,480],
 "camera":"APPROXIMATE_NOT_GAME","object_topology":topology,
 "native_source_holes_open":8,"protected_other_meshes":107,
 "hosted_private_blend":"BLOCKED_INPUT_NOT_TRANSFERRED","full_7_photo_view_qa":"INCOMPLETE",
 "vehicle_complete":False,"score_change":0,"no_native_export_or_game_changes":True}
 QA.write_text(json.dumps(record,indent=2))
 print(record["result"],json.dumps({"scene":record["r14_sha256"],
 "cycles":record["render_sha256"],"topology":topology}),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOT_A_R14_MODE","")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("invalid SLOT_A_R14_MODE; expected build or verify")
