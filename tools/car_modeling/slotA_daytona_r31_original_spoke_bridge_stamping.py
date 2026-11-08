#!/usr/bin/env python3
"""Slot A Daytona R31. ONLY edit six existing PMT-derived cockpit meshes.
Correct the three pre-existing spoke-to-rim bridge shapes to broad, thin
three-spoke metal pressings. Geometry/provenance only; no new mesh, material,
image, model, native conversion/export, game/VR runtime or slot C changes.
The private licensed original and edited blend stay on authorized N100.
"""
from pathlib import Path
import hashlib, json, math, subprocess, sys
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
NATIVE=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v28_r30.blend"
OUT=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v29_r31.blend"
AUDIT=ROOT/"SLOTA_R31_SOURCE_BRIDGE_DASH_COWL_AUDIT.json"
QA=ROOT/"SLOTA_R31_FRESH_REOPEN_REAL_CYCLES.json"
RENDER=ROOT/"SLOTA_DAYTONA_R31_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMPARE=ROOT/"SLOTA_DAYTONA_R30_R31_ACTUAL_CYCLES_BEFORE_AFTER.jpg"
PREV=ROOT/"SLOTA_DAYTONA_R30_AFTER_REAL_CYCLES_APPROX_EYE.png"
BLENDER=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
HASH={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"base":"beed6f9e1cc11706e21e361c22754ddc4ed2aba581087c66009dd08202f7a6fb",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
"upper":"V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
"cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"left":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
"right":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
"lower":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for ch in iter(lambda:f.read(1024*1024),b""):h.update(ch)
 return h.hexdigest()
def check_inputs():
 for key,p in (("pmt",PMT),("import",NATIVE),("base",BASE),("photo",PHOTO)):
  if not p.is_file() or sha(p)!=HASH[key]:
   raise RuntimeError("BLOCKED_INPUT_SHA: "+key+" "+str(p))
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def mat(o):
 return [[round(float(v),9) for v in row] for row in o.matrix_world]
def geo_sig(o):
 h=hashlib.sha256()
 for v in o.data.vertices:
  h.update(("%.7f,%.7f,%.7f;"%(v.co.x,v.co.y,v.co.z)).encode())
 for p in o.data.polygons:h.update((str(tuple(p.vertices))+":"+str(p.material_index)+";").encode())
 return h.hexdigest()
def uv_sig(o):
 return hashlib.sha256(repr([(l.name,[(round(u.uv.x,8),round(u.uv.y,8)) for u in l.data]) for l in o.data.uv_layers]).encode()).hexdigest()
def snapshot(o):
 return {"name":o.name,"verts":len(o.data.vertices),"faces":len(o.data.polygons),
 "geometry_sha256":geo_sig(o),"uv_sha256":uv_sig(o),"world_matrix":mat(o),
 "materials":[m.name if m else None for m in o.data.materials],
 "hide_render":bool(o.hide_render)}
def inventory():
 import bpy
 return {"objects":sorted(bpy.data.objects.keys()),"mesh_data":sorted(bpy.data.meshes.keys()),
 "materials":sorted(bpy.data.materials.keys()),"curves":sorted(bpy.data.curves.keys()),
 "images":{a.name:(tuple(a.size),bool(a.packed_file),a.filepath) for a in bpy.data.images},
 "camera":{o.name:mat(o) for o in bpy.data.objects if o.type=="CAMERA"}}
def holes():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 bvh=BVHTree.FromObject(bpy.data.objects[NAMES["spoke"]],bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return bvh.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
 return [(not hit(x,z)) and hit(x+1.6*r,z) for x,z,r in HOLES]
def bridge_profile(o,kind):
 # Five inherited mesh cross-sections, each with existing front/back quads.
 from collections import defaultdict
 sections=defaultdict(list)
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  key=round((p.z if kind=="lower" else p.x),5)
  sections[key].append(p)
 assert len(sections)==5,("SOURCE_BRIDGE_STATIONS",kind,len(sections))
 profile={}
 for key,coords in sections.items():
  vals=[p.x if kind=="lower" else p.z for p in coords]
  mid=(min(vals)+max(vals))/2.
  half=(max(vals)-min(vals))/2.
  assert half>.002,("SOURCE_BRIDGE_WIDTH",kind,key,half)
  profile[key]=(mid,half)
 return profile
def bridge_delta(kind,p,profile):
 from mathutils import Vector
 x,y,z=p
 if kind=="lower":
  key=round(z,5);a,b=profile[key]
  t=(z-.6205)/(.6975-.6205)
  assert -.001<=t<=1.001
  target_half=.0115+.0035*smooth(0.,1.,t)
  target_x=-.350+(x-a)/b*target_half
  target_z=z-.0030*(1.-t)**3
  target_y=y-.0009-.00085*math.sin(math.pi*t)
  return Vector((target_x-x,target_y-y,target_z-z))
 key=round(x,5);a,b=profile[key]
 t=((x+.5215)/(.077) if kind=="left" else (-.1785-x)/(.077))
 assert -.001<=t<=1.001
 target_half=.0115+.0035*smooth(0.,1.,t)
 target_z=a+(z-a)/b*target_half
 target_x=x+(-.003 if kind=="left" else .003)*(1.-t)**3
 target_y=y-.0009-.00085*math.sin(math.pi*t)
 return Vector((target_x-x,target_y-y,target_z-z))
def source_delta(kind,p):
 from mathutils import Vector
 x,y,z=p; dx=dy=dz=0.
 if kind=="spoke":
  # Reshape existing native-source plate pressing at the three bridge junctions.
  # Keep factory punch holes open; do not add any bridge or punch geometry.
  clearance=min(math.hypot(x-hx,z-hz)/r for hx,hz,r in HOLES)
  safe=smooth(1.75,3.25,clearance)
  arm=max(smooth(.087,.112,abs(x+.35))*math.exp(-((z-.791)/.033)**4),
          smooth(.084,.112,.791-z)*math.exp(-((x+.35)/.028)**4))
  dy=-.00145*arm*safe
 elif kind=="cowl":
  # Subtle raised dash eyebrow along the EXISTING native-guided shroud.
  width=math.exp(-((x+.35)/.255)**4)
  front=1-smooth(.193,.311,y)
  dz=.00285*width*front
  dy=-.00075*width*front
 elif kind=="upper":
  width=math.exp(-((x+.35)/.31)**4)
  front=1-smooth(.198,.355,y)
  ridge=smooth(.938,.986,z)
  dz=.00220*width*front*ridge
  dy=-.00070*width*front*ridge
 return Vector((dx,dy,dz))
def topology(o):
 import bmesh
 bm=bmesh.new();bm.from_mesh(o.data)
 val=sum(not e.is_manifold for e in bm.edges);bm.free()
 return val
def origin():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==NATIVE.resolve()
 check_inputs()
 for name,n in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(name)
  assert o and o.type=="MESH" and len(o.data.vertices)==n,("ORIGINAL_NATIVE_OBJECT_MISMATCH",name)
 print("R31_ORIGINAL_IMPORTED_PMT_OBJECTS_VERIFIED",flush=True)
def build():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==BASE.resolve(),"BLOCKED_WRONG_SCENE"
 check_inputs()
 assert all(not p.exists() for p in (OUT,AUDIT,QA,RENDER,COMPARE)), "BLOCKED_IMMUTABLE_OUTPUT_COLLISION"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
 assert len(bpy.data.objects[NAMES["spoke"]].data.vertices)==9720
 assert all(holes()),"BLOCKED_FACTORY_SPOKE_HOLES"
 before_inventory=inventory()
 other={o.name:geo_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(other)==107,("ORIGINAL_DERIVED_MESH_COUNT",len(other))
 report={}
 for kind,name in NAMES.items():
  o=bpy.data.objects[name]
  assert o.type=="MESH" and o.data.users==1
  s0=snapshot(o);topo0=topology(o);inv=o.matrix_world.inverted()
  prof=bridge_profile(o,kind) if kind in ("left","right","lower") else None
  moved=0;max_change=0.;sum_change=0.
  for v in o.data.vertices:
   w=o.matrix_world@v.co
   d=bridge_delta(kind,w,prof) if prof is not None else source_delta(kind,w)
   if d.length<.000008:continue
   v.co=inv@(w+d)
   moved+=1;max_change=max(max_change,d.length);sum_change+=d.length
  o.data.update()
  s1=snapshot(o)
  assert moved>=({"upper":80,"cowl":500,"spoke":150,"left":20,"right":20,"lower":20}[kind]),("BLOCKED_NOT_ENOUGH_GEOMETRY",kind,moved)
  assert max_change<.013,("BLOCKED_DANGEROUS_DISPLACEMENT",kind,max_change)
  for key in ("name","verts","faces","uv_sha256","world_matrix","materials","hide_render"):
   assert s0[key]==s1[key],("BLOCKED_INVARIANT",kind,key)
  assert s0["geometry_sha256"]!=s1["geometry_sha256"]
  assert topology(o)==topo0,("BLOCKED_TOPOLOGY_DAMAGE",kind)
  report[kind]={"before":s0,"after":s1,"moved":moved,"maximum_move_m":round(max_change,8),
                 "mean_move_m":round(sum_change/moved,8),"nonmanifold_edges_preexisting":topo0}
 assert inventory()==before_inventory,"BLOCKED_CAMERA_OR_OBJECT_INVENTORY_CHANGE"
 assert {o.name:geo_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}==other
 assert all(holes()),"BLOCKED_SOURCE_HOLE_OCCLUSION"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 assert OUT.stat().st_size>1000000
 data={"status":"SLOTA_R31_SOURCE_STEERING_BRIDGE_AND_DASH_GEOMETRY_SAVED",
 "slot":"A","car":"daytona365","PMT":str(PMT),"PMT_sha256":HASH["pmt"],
 "original_import_sha256":HASH["import"],"original_import_meshes":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "r30_input_sha256":HASH["base"],"r31_private_output_blend_sha256":sha(OUT),
 "reference_Spider_LHD_photo_sha256":HASH["photo"],"edited_original_derived_meshes":report,
 "other_107_original_derived_mesh_signatures_sha256":hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest(),
 "factory_eight_through_holes":"PASS","source_topology_UV_material_pivots_camera_unchanged":True,
 "no_new_objects_no_external_Body_or_car_no_texture_no_exports":True,
 "exact_game_eye":"NOT_CALIBRATED","seven_photo_views":"INCOMPLETE",
 "GitHub_Actions_private_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"slot_advance":False,"score_change":0}
 AUDIT.write_text(json.dumps(data,indent=2),encoding="utf8")
 print("SLOTA_R31_SOURCE_BUILD_PASS",json.dumps({"sha":sha(OUT),"moved":{k:v["moved"] for k,v in report.items()}}),flush=True)
def verify():
 import bpy
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==OUT.resolve()
 check_inputs()
 assert AUDIT.is_file() and not QA.exists() and not RENDER.exists()
 a=json.loads(AUDIT.read_text())
 assert sha(OUT)==a["r31_private_output_blend_sha256"]
 other={o.name:geo_sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
 assert len(other)==107
 assert hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest()==a["other_107_original_derived_mesh_signatures_sha256"]
 assert all(holes())
 for k,record in a["edited_original_derived_meshes"].items():
  o=bpy.data.objects[record["after"]["name"]]
  assert snapshot(o)==record["after"],("BLOCKED_FRESH_REOPEN_MESH",k)
  assert topology(o)==record["nonmanifold_edges_preexisting"]
 # Temporary camera only, never save into the proprietary edited scene.
 sc=bpy.context.scene
 cd=bpy.data.cameras.new("R31_TRANSIENT_APPROX_EYE")
 cam=bpy.data.objects.new("R31_TRANSIENT_APPROX_EYE",cd);sc.collection.objects.link(cam)
 cam.location=(-.35,-.92,1.055)
 cam.rotation_euler=(Vector((-.24,.19,.797))-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.lens=28;cd.clip_start=.01;sc.camera=cam
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480
 sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(RENDER)
 bpy.ops.render.render(write_still=True)
 assert RENDER.is_file() and RENDER.stat().st_size>12000
 assert sha(OUT)==a["r31_private_output_blend_sha256"]
 qa={"status":"R31_OFFICIAL_BLENDER_4_5_15_REAL_PRIVATE_SCENE_FRESH_REOPEN_CYCLES_PASS",
 "blend_sha256":sha(OUT),"png_sha256":sha(RENDER),"render":[720,480,3],
 "edited_mesh_count":len(NAMES),"unchanged_other_mesh_count":107,
 "eight_native_holes":"PASS","original_nonmanifold_not_yet_fixed":True,
 "game_driver_eye":"NOT_CALIBRATED","seven_Spider_photos":"INCOMPLETE",
 "GitHub_Actions_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"score_change":0}
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R31_PRIVATE_FRESH_REOPEN_CYCLES_PASS",json.dumps(qa),flush=True)
def compare():
 from PIL import Image
 assert PREV.is_file() and RENDER.is_file() and QA.is_file()
 with Image.open(PREV) as ip,Image.open(RENDER) as iq:
  a=ip.convert("RGB");b=iq.convert("RGB")
  assert a.size==b.size==(720,480)
  a_pix,b_pix=a.load(),b.load()
  changed=sum(1 for y in range(480) for x in range(720) if max(abs(a_pix[x,y][c]-b_pix[x,y][c]) for c in range(3))>3)
  assert changed>500,("INSUFFICIENT_VISUAL_GEOMETRY",changed)
  combined=Image.new("RGB",(1440,480))
  combined.paste(a,(0,0));combined.paste(b,(720,0))
  combined.save(COMPARE,quality=93,optimize=True)
 qa=json.loads(QA.read_text())
 qa.update({"r30_vs_r31_gt3_RGB_pixels":changed,"r30_png_sha256":sha(PREV),
 "r31_png_sha256":sha(RENDER),"side_by_side_sha256":sha(COMPARE)})
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("SLOTA_R31_ACTUAL_CYCLES_BEFORE_AFTER_PASS",changed,sha(COMPARE),flush=True)
def call_blender(mode):
 assert BLENDER.is_file(),"BLOCKED_OFFICIAL_BLENDER_MISSING"
 scene=NATIVE if mode=="origin" else (BASE if mode=="build" else OUT)
 p=subprocess.run([str(BLENDER),"--background",str(scene),"--threads","2",
  "--python",str(Path(__file__).resolve()),"--",mode],capture_output=True,text=True,timeout=210)
 print(p.stdout[-26000:],flush=True)
 if p.stderr:print("STDERR",p.stderr[-2500:],flush=True)
 if p.returncode:raise RuntimeError("BLENDER_FAILED_%s_%s"%(mode,p.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("origin","build","verify"):
  try:import bpy
  except ImportError:call_blender(mode)
  else:{"origin":origin,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("use origin/build/verify/compare")
