#!/usr/bin/env python3
"""Slot A Daytona R16: strictly existing original PMT-derived cockpit meshes.
Original resource and imported .blend are read-only provenance witnesses.
Only spatial vertex coordinates of six existing P0 meshes may change.
No object/material/UV/image changes; no game conversion/export/integration.
"""
from pathlib import Path
import bpy, bmesh, math, os, hashlib, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMP=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
OLD=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v13_r15.blend"
NEW=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v14_r16.blend"
OLD_RECORD=ROOT/"SLOT_A_DAYTONA_P0_R15_NATIVE_BEZEL_BROW_STEERING.json"
AUDIT=ROOT/"SLOT_A_DAYTONA_P0_R16_STEERING_DASH_SOURCE_GEOMETRY.json"
QA=ROOT/"SLOTA_R16_INDEPENDENT_REOPEN_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R16_AFTER_REAL_CYCLES_APPROX_EYE.png"
EXPECTED={
 "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "r15":"5da12b72f92ccd07ce20e92bc1d66d79e962b7259d5441d303d369cb3df205b4",
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
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
  [(f.material_index,tuple(f.vertices)) for f in o.data.polygons]
 )).encode()).hexdigest()
def mx(o):return [[round(float(c),9) for c in row] for row in o.matrix_world]
def state(o):
 return {"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "signature":sig(o),"matrix":mx(o),"uv":[x.name for x in o.data.uv_layers],
 "materials":[x.name if x else None for x in o.data.materials]}
def smooth(a,b,v):
 t=max(0.0,min(1.0,(v-a)/(b-a)))
 return t*t*(3.-2.*t)
def holes(o):
 bpy.context.view_layer.update()
 bvh=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return bvh.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def source_gate():
 assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_VERSION"
 for tag,p,h in (("PMT",PMT,EXPECTED["pmt"]),("original imported scene",IMP,EXPECTED["import"]),
 ("R15 existing editable scene",OLD,EXPECTED["r15"]),("Spider LHD photo",PHOTO,EXPECTED["photo"])):
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT_SHA",tag)
 # The immutable original IMPORT scene contains raw object00/object22.
 # The R15 working scene retains linked DERIVATIVE object identities instead.
 # Never mislabel these 6 edited meshes as byte-identical native triangles.
 assert "V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0" in bpy.data.objects
 assert "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0" in bpy.data.objects
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"].data.vertices)==9720
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
def snapshot():
 objs={key:bpy.data.objects[name] for key,name in PARTS.items()}
 assert all(o.type=="MESH" and o.data.users==1 for o in objs.values())
 keep={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
 assert len(keep)==107
 baseline={
 "objects":sorted(bpy.data.objects.keys()),"materials":sorted(bpy.data.materials.keys()),
 "curves":sorted(bpy.data.curves.keys()),
 "images":{im.name:(list(im.size),bool(im.packed_file)) for im in bpy.data.images},
 "cameras":{o.name:mx(o) for o in bpy.data.objects if o.type=="CAMERA"}}
 return objs,keep,baseline
def invariants(objs,keep,baseline):
 assert sorted(bpy.data.objects.keys())==baseline["objects"]
 assert sorted(bpy.data.materials.keys())==baseline["materials"]
 assert sorted(bpy.data.curves.keys())==baseline["curves"]
 assert {im.name:(list(im.size),bool(im.packed_file)) for im in bpy.data.images}==baseline["images"]
 assert {o.name:mx(o) for o in bpy.data.objects if o.type=="CAMERA"}==baseline["cameras"]
 assert {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}==keep
 assert all(holes(objs["spoke"])),"SLOT_A_SOURCE_HOLES_DAMAGED"
def build():
 assert Path(bpy.data.filepath).resolve()==OLD.resolve(),"BLOCKED_INPUT_R15_MUST_BE_OPEN"
 assert not NEW.exists() and not AUDIT.exists(),"IMMUTABLE_OUTPUT_COLLISION"
 source_gate()
 prev=json.loads(OLD_RECORD.read_text())
 assert prev["slot"]=="A" and prev["car"]=="daytona365"
 assert prev["output_sha256"]==EXPECTED["r15"]
 objs,keep,baseline=snapshot()
 before={k:state(o) for k,o in objs.items()}
 for k in PARTS:
  prior=prev["original_derived_existing_meshes"]["brow" if k=="cowl" else k]["after"]
  assert before[k]=={ "name":prior["name"],"vertices":prior["vertices"],
  "faces":prior["faces"],"signature":prior["signature"],
  "matrix":prior["matrix"],"uv":prior["uv"],"materials":prior["materials"]},("R15_ORIGINAL_MESH_MISMATCH",k)
 assert all(holes(objs["spoke"]))
 report={}
 for k,o in objs.items():
  inv=o.matrix_world.inverted()
  moved=0; maximum=0.; total=0.
  for vert in o.data.vertices:
   p=o.matrix_world@vert.co
   dx=dy=dz=0.
   if k=="dashboard":
    # Lower padded fascia transitions to upper gauge housing. Quiet edge relief,
    # photographed dashboard shape, without adding invented new instruments.
    span=smooth(-.622,-.573,p.x)*(1.-smooth(-.126,-.078,p.x))
    height=smooth(.750,.796,p.z)*(1.-smooth(.920,.951,p.z))
    forward=1.-smooth(.178,.236,p.y)
    lobe=math.exp(-((p.x+.351)/.167)**4)
    dz=.0032*span*height*forward*(.45+.55*lobe)
    dy=-.0015*span*height*forward
   elif k=="cowl":
    # Sculpt existing source hood lip into broad arch with stepped front overhang.
    span=smooth(-.625,-.590,p.x)*(1.-smooth(-.111,-.074,p.x))
    lip=1.-smooth(.132,.201,p.y)
    arc=math.exp(-((p.x+.350)/.192)**4)
    low=1.-smooth(.935,.968,p.z)
    high=smooth(.936,.968,p.z)
    dz=-.0034*span*lip*low*(.58+.42*arc)+.0017*span*lip*high*arc
    dy=-.0031*span*lip*(.65+.35*arc)
   elif k=="bezel":
    # Circular pressed ring relief uses existing high-resolution loops, no UV edits.
    front=math.exp(-((p.y-.1485)/.0022)**2)
    shoulder=math.exp(-((p.y-.153)/.0017)**2)
    dy=-.0019*front+.0011*shoulder
    dz=.0007*front*math.tanh((p.z-.823)/.030)
   elif k=="spoke":
    # Eight genuine through-holes remain voids; deepen original stamped-metal
    # toroidal lips and softly roll existing three-spoke arms.
    ds=[math.hypot(p.x-x,p.z-z)/r for x,z,r in HOLES]
    nearest=min(ds)
    safe=smooth(1.045,1.42,nearest)
    lip=max(math.exp(-((d-1.44)/.28)**2) for d in ds)
    left_right=math.exp(-((p.z-.801)/.029)**4)*smooth(.038,.080,abs(p.x+.35))
    lower=math.exp(-((p.z-.737)/.055)**4)*math.exp(-((p.x+.35)/.026)**4)
    facing=math.exp(-((p.y+.287)/.021)**2)
    dy=-.0017*lip*facing+.0012*safe*(left_right+.85*lower)*facing
    dz=-.00045*lip*facing*math.tanh((p.z-.770)/.028)
   elif k=="rim":
    # Reduce visually over-round existing rim, preserve wheel radius/pivot.
    ux=p.x+.35;wz=p.z-.792
    rad=math.hypot(ux,wz)
    if rad>.05:
     cross=rad-.1740
     dr=-.082*cross
     dx=dr*ux/rad;dz=dr*wz/rad
     theta=math.atan2(wz,ux)
     grips=(math.exp(-((theta-.80)/.31)**4)+math.exp(-((theta-2.34)/.31)**4))
     dx+=.00055*grips*ux/rad;dz+=.00055*grips*wz/rad
    dy=-.075*(p.y+.286)
   elif k=="hub":
    # Existing wheel-column shoulder: rolled flange, no extra hub mesh.
    rad=math.hypot(p.x+.350,p.z-.767)
    ring=math.exp(-((p.y+.251)/.011)**2)*smooth(.009,.021,rad)
    if rad>.00001:
     dx=.0013*ring*(p.x+.35)/rad
     dz=.0013*ring*(p.z-.767)/rad
    dy=-.0014*ring
   d=Vector((dx,dy,dz))
   if d.length<.000016:continue
   vert.co=inv@(p+d)
   moved+=1
   maximum=max(maximum,d.length*1000.)
   total+=d.length*1000.
  assert moved>={"dashboard":80,"cowl":250,"bezel":250,"spoke":600,"rim":4500,"hub":20}[k],(k,moved)
  assert maximum<6.0,(k,maximum)
  o.data.update()
  now=state(o)
  assert (now["vertices"],now["faces"])==(before[k]["vertices"],before[k]["faces"])
  assert now["signature"]!=before[k]["signature"]
  for key in ("name","matrix","uv","materials"):assert now[key]==before[k][key]
  report[k]={"before":before[k],"after":now,"moved":moved,
   "max_mm":round(maximum,5),"avg_mm":round(total/moved,5)}
 invariants(objs,keep,baseline)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(NEW),compress=True)
 assert NEW.is_file() and NEW.stat().st_size>1_000_000
 obj={"slot":"A","car":"daytona365","revision":"r16","blender":bpy.app.version_string,
 "original_pmt_path":str(PMT),"original_pmt_sha256":EXPECTED["pmt"],
 "original_import_blend_path":str(IMP),"original_import_sha256":EXPECTED["import"],
 "reference_photo_sha256":EXPECTED["photo"],
 "original_object_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "input_r15_sha256":EXPECTED["r15"],"output_r16_sha256":sha(NEW),
 "source_derived_original_objects":report,
 "unmodified_107_other_mesh_signatures_sha256":hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest(),
 "eight_original_steering_holes":"PASS","transforms_pivots_camera_uv_materials_textures_unchanged":True,
 "external_body_untouched":True,"no_exports_or_game_runtime_changes":True,
 "render_eye":"APPROXIMATE_NOT_GAME","seven_exact_spider_photos":"INCOMPLETE",
 "github_hosted_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"slot_advance":False,"score_change":0}
 AUDIT.write_text(json.dumps(obj,indent=2),encoding="utf-8")
 print("SLOT_A_DAYTONA_R16_ORIGINAL_MESH_EDIT_SAVED",json.dumps({
  "blend_sha256":obj["output_r16_sha256"],"moved":{k:v["moved"] for k,v in report.items()},
  "before_after":{k:[[v["before"]["vertices"],v["before"]["faces"]],[v["after"]["vertices"],v["after"]["faces"]]] for k,v in report.items()}}),flush=True)
def verify():
 assert Path(bpy.data.filepath).resolve()==NEW.resolve(),"BLOCKED_INPUT_R16_REOPEN"
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
 source_gate()
 audit=json.loads(AUDIT.read_text())
 assert sha(NEW)==audit["output_r16_sha256"]
 objs,keep,baseline=snapshot()
 assert all(holes(objs["spoke"]))
 assert hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest()==audit["unmodified_107_other_mesh_signatures_sha256"]
 geometry={}
 for k,o in objs.items():
  assert state(o)==audit["source_derived_original_objects"][k]["after"],k
  bm=bmesh.new();bm.from_mesh(o.data)
  geometry[k]={"vertices":len(bm.verts),"faces":len(bm.faces),
   "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
  bm.free()
 assert geometry["dashboard"]["nonmanifold_edges"]==184
 assert geometry["bezel"]["nonmanifold_edges"]==932
 assert geometry["spoke"]["nonmanifold_edges"]==1597
 assert geometry["rim"]["nonmanifold_edges"]==0
 sc=bpy.context.scene
 # Temporary QA-only camera; never save to disk after adding it.
 camdata=bpy.data.cameras.new("SLOTA_R16_APPROX_EYE_TEMP")
 cam=bpy.data.objects.new("SLOTA_R16_APPROX_EYE_TEMP",camdata)
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
 assert PNG.is_file() and PNG.stat().st_size>12000
 assert sha(NEW)==audit["output_r16_sha256"]
 record={"result":"SLOT_A_R16_REAL_PRIVATE_BLENDER_SEPARATE_PROCESS_REOPEN_CYCLES_PASS",
 "blender":bpy.app.version_string,"slot":"A","car":"daytona365",
 "pmt_sha256":EXPECTED["pmt"],"original_import_sha256":EXPECTED["import"],
 "r15_sha256":EXPECTED["r15"],"r16_blend_sha256":sha(NEW),
 "r16_cycles_sha256":sha(PNG),"render":PNG.name,"resolution":[720,480],"cycles_samples":3,
 "geometry":geometry,"native_holes_open":8,"protected_other_meshes":107,
 "camera":"APPROXIMATE_NOT_GAME","seven_exact_spider_views":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "completed":False,"score_change":0}
 QA.write_text(json.dumps(record,indent=2),encoding="utf-8")
 print(record["result"],json.dumps({"blend_sha256":record["r16_blend_sha256"],"render_sha256":record["r16_cycles_sha256"],"geometry":geometry}),flush=True)
if __name__=="__main__":
 mode=os.environ.get("SLOT_A_R16_MODE")
 if mode=="build":build()
 elif mode=="verify":verify()
 else:raise SystemExit("SLOT_A_R16_MODE must be build or verify")
