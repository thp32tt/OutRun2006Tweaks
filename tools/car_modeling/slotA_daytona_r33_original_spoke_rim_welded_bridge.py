#!/usr/bin/env python3
"""Slot A Daytona R33. Source-native PMT steering spoke/rim contact rework.
Attaches three tapered stamped-metal ends to the existing source-derived
3-spoke mesh. No invented car, independent replacement steering, texture,
material, PMT/OVC export, exterior work, game deployment, or VR changes.
Fail closed unless immutable original game PMT, authentic Blender import,
exact R32 private source and exact LHD Spider research photo all match.
"""
import sys, subprocess, hashlib, math, json, struct
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
NATIVE=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
BASE=R/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v30_r32.blend"
OUT=R/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v31_r33.blend"
PNG=R/"SLOTA_DAYTONA_R33_AFTER_REAL_CYCLES_APPROX_EYE.png"
PREV=R/"SLOTA_DAYTONA_R32_AFTER_REAL_CYCLES_APPROX_EYE.png"
COMP=R/"SLOTA_DAYTONA_R32_R33_REAL_CYCLES_BEFORE_AFTER.jpg"
AUDIT=R/"SLOTA_R33_SOURCE_NATIVE_SPOKE_TO_RIM_BRIDGES_AUDIT.json"
QA=R/"SLOTA_R33_INDEPENDENT_REOPEN_CYCLES.json"
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
SOURCE={
"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"original_blend":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"spider_lhd":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
"r32":"0caafbf7c242ef539ead91c280f147a1d5893802355f8a9c9664a31761d6bc35"
}
SPOKE="V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"
RIM="V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),(-.310,.804,.0068),
(-.290,.804,.0068),(-.269,.804,.0068),(-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for part in iter(lambda:f.read(1048576),b""):h.update(part)
 return h.hexdigest()
def gate():
 for key,p in (("pmt",PMT),("original_blend",NATIVE),("spider_lhd",PHOTO),("r32",BASE)):
  assert p.is_file() and sha(p)==SOURCE[key],("BLOCKED_INPUT_MISSING_OR_SHA_DRIFT",key)
 assert BL.is_file(),"BLOCKED_BLENDER_4_5_15_MISSING"
def matrix(o):return tuple(tuple(round(float(v),9) for v in row) for row in o.matrix_world)
def geo(o):
 h=hashlib.sha256()
 for v in o.data.vertices:
  h.update(struct.pack("<ddd",round(v.co.x,8),round(v.co.y,8),round(v.co.z,8)))
 for poly in o.data.polygons:
  h.update((",".join(map(str,poly.vertices))+":"+str(poly.material_index)+";").encode())
 return h.hexdigest()
def invariant():
 import bpy
 return {
 "all_objects":sorted(bpy.data.objects.keys()),
 "all_mesh_datablocks":sorted(bpy.data.meshes.keys()),
 "all_materials":sorted(bpy.data.materials.keys()),
 "all_images":sorted(bpy.data.images.keys()),
 "all_cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"},
 "all_object_transforms":{o.name:matrix(o) for o in bpy.data.objects},
 "all_mesh_materials":{o.name:tuple(m.name if m else "" for m in o.data.materials) for o in bpy.data.objects if o.type=="MESH"}
 }
def native():
 import bpy
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==NATIVE.resolve()
 gate()
 for n,v in (("object00_group01_material012_a0",13),("object22_group00_material000_a0",61)):
  o=bpy.data.objects.get(n); assert o and o.type=="MESH" and len(o.data.vertices)==v,("BLOCKED_NATIVE_ORIGINAL_MESH",n)
 print("R33_NATIVE_GAME_IMPORT_VERIFIED",sha(NATIVE),flush=True)
def holes_pass():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 bvh=BVHTree.FromObject(bpy.data.objects[SPOKE],bpy.context.evaluated_depsgraph_get())
 def hit(x,z):
  return bvh.ray_cast(Vector((x,-.55,z)),Vector((0,1,0)),1.0)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]
def build():
 import bpy,bmesh
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15")
 assert Path(bpy.data.filepath).resolve()==BASE.resolve(),"BLOCKED_NOT_EXACT_R32_PRIVATE_BASE"
 gate()
 for p in (OUT,AUDIT,QA,PNG,COMP):
  assert not p.exists(),("BLOCKED_IMMUTABLE_R33_OUTPUT_EXISTS",str(p))
 s=bpy.data.objects[SPOKE]; rim=bpy.data.objects[RIM]
 assert s.type=="MESH" and len(s.data.vertices)==9720 and len(s.data.polygons)==17285
 assert s.data.users==1 and rim.type=="MESH" and len(rim.data.vertices)==6144
 assert all(holes_pass()),"BLOCKED_SOURCE_HOLES"
 assert bpy.context.scene.camera and bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
 before=geo(s);oldmat=tuple(m.name for m in s.data.materials)
 protected={o.name:geo(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=SPOKE}
 assert len(protected)==112,("BLOCKED_UNEXPECTED_SOURCE_MESH_COUNT",len(protected))
 inv=invariant()
 src_v=len(s.data.vertices);src_f=len(s.data.polygons)
 # Refer to actual native-source stamped spokes' terminal boundary vertices.
 # New extensions are welded into the SAME original-derived wheel mesh, using
 # native source boundary vertices as four of the eight prism corners.
 # They reach the existing separate factory-style rim's actual inner tube.
 bm=bmesh.new();bm.from_mesh(s.data);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table()
 original=list(bm.verts); boundary={v for e in bm.edges if e.is_boundary for v in e.verts}
 def coord(v):return s.matrix_world@v.co
 def nearest(target,filter_fn,used):
  subset=(v for v in original if v in boundary and v not in used and filter_fn(coord(v)))
  v=min(subset,key=lambda v:(coord(v)-Vector(target)).length,default=None)
  assert v is not None and (coord(v)-Vector(target)).length<.021,("BLOCKED_SOURCE_TIP_NOT_FOUND",target)
  used.add(v);return v
 # Source tip measurements come from the exact R32 native mesh boundary audit.
 # Target Y/Z values are copied from the native perimeter, not invented holes.
 sectors=[
 {"name":"left","filter":lambda p:p.x<-.437 and .770<p.z<.824,
  "roots":[(-.454,-.286,.787),(-.454,-.286,.805),(-.454,-.277,.787),(-.454,-.277,.805)],
  "ends":[(-.5235,-.289,.783),(-.5235,-.289,.802),(-.5235,-.283,.783),(-.5235,-.283,.802)]},
 {"name":"right","filter":lambda p:p.x>-.262 and .770<p.z<.829,
  "roots":[(-.246,-.288,.791),(-.246,-.288,.815),(-.246,-.276,.791),(-.246,-.276,.815)],
  "ends":[(-.1765,-.289,.783),(-.1765,-.289,.802),(-.1765,-.283,.783),(-.1765,-.283,.802)]},
 {"name":"lower","filter":lambda p:p.z<.717 and -.386<p.x<-.314,
  "roots":[(-.364,-.307,.687),(-.336,-.307,.687),(-.364,-.293,.687),(-.336,-.293,.687)],
  "ends":[(-.360,-.291,.617),(-.340,-.291,.617),(-.360,-.284,.617),(-.340,-.284,.617)]}
 ]
 face_counts={};anchors={}
 uvmap=bm.loops.layers.uv.active
 for sec in sectors:
  used=set()
  roots=[nearest(p,sec["filter"],used) for p in sec["roots"]]
  # Four native boundary vertex IDs remain unchanged and source-identifiable.
  orig_ids=[v.index for v in roots]
  targets=[Vector(p) for p in sec["ends"]]
  new=[bm.verts.new(s.matrix_world.inverted()@p) for p in targets]
  # two broad stamped surfaces, two rolled edge surfaces, one buried end cap
  faces=[(roots[0],roots[1],new[1],new[0]),
         (roots[2],new[2],new[3],roots[3]),
         (roots[0],new[0],new[2],roots[2]),
         (roots[1],roots[3],new[3],new[1]),
         (new[0],new[1],new[3],new[2])]
  created=[]
  for loop in faces:
   f=bm.faces.new(loop)
   f.material_index=0
   f.smooth=True
   # Inherit only existing material. This does not generate or bake textures.
   if uvmap:
    for li,l in enumerate(f.loops):
     l[uvmap].uv=((li%2)*.5,((li//2)%2)*.5)
   created.append(f)
  area=sum(f.calc_area() for f in created)
  assert area>.0002,("BLOCKED_DEGENERATE_SOURCE_BRIDGE",sec["name"],area)
  face_counts[sec["name"]]=len(created)
  anchors[sec["name"]]={"original_boundary_vertex_ids":orig_ids,
   "original_boundary_xyz":[list(map(lambda x:round(float(x),6),coord(v))) for v in roots],
   "end_contact_xyz":sec["ends"],"area_m2":round(area,6)}
 bm.normal_update();bm.to_mesh(s.data);bm.free();s.data.update()
 assert len(s.data.vertices)==src_v+12 and len(s.data.polygons)==src_f+15
 assert tuple(m.name for m in s.data.materials)==oldmat
 assert invariant()==inv,"BLOCKED_OBJECT_MATERIAL_CAMERA_OR_SCENE_DRIFT"
 assert {o.name:geo(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=SPOKE}==protected
 assert all(holes_pass()),"BLOCKED_FACTORY_EIGHT_HOLES_OBSTRUCTED"
 assert geo(s)!=before,"BLOCKED_NO_ACTUAL_MESH_CHANGE"
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 report={"slot":"A","car":"daytona365","status":"R33_NEW_NATIVE_SPOKE_TO_RIM_STAMPED_END_GEOMETRY_SAVED",
 "source_PMT":str(PMT),"source_PMT_sha256":SOURCE["pmt"],
 "first_genuine_import":str(NATIVE),"import_blend_sha256":SOURCE["original_blend"],
 "original_import_meshes":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "input_R32_blend_sha256":SOURCE["r32"],"result_R33_blend_sha256":sha(OUT),
 "existing_original_derived_mesh_name":SPOKE,
 "spoke_geometry_sha256_before":before,"spoke_geometry_sha256_after":geo(s),
 "spoke_vertices_before_after":[src_v,len(s.data.vertices)],
 "spoke_faces_before_after":[src_f,len(s.data.polygons)],
 "new_welded_spoke_terminal_quads_per_direction":face_counts,
 "native_source_tip_provenance":anchors,
 "untouched_112_meshes":protected,
 "camera_objects_ID_transforms_materials_unchanged":True,
 "existing_8_native_steering_holes":"PASS",
 "reference_photo_file":str(PHOTO),"reference_spider_lhd_photo_sha256":SOURCE["spider_lhd"],
 "exact_original_game_driver_eye":"UNCALIBRATED","seven_authentic_photo_angles":"INCOMPLETE",
 "hosted_Actions_actual_proprietary_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "native_PMT_OVC_OVC3_export":False,"texture_PBR_modifications":False,
 "vehicle_complete":False,"slot_advance":False,"score_delta":0}
 AUDIT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
 print("R33_REAL_SOURCE_STEERING_NATIVE_BRIDGE_SAVED",sha(OUT),face_counts,flush=True)
def verify():
 import bpy
 from mathutils import Vector
 assert bpy.app.version_string.startswith("4.5.15") and Path(bpy.data.filepath).resolve()==OUT.resolve()
 gate()
 assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
 a=json.loads(AUDIT.read_text(encoding="utf8"))
 assert sha(OUT)==a["result_R33_blend_sha256"]
 s=bpy.data.objects[SPOKE]
 assert len(s.data.vertices)==9732 and len(s.data.polygons)==17300
 assert geo(s)==a["spoke_geometry_sha256_after"]
 assert {o.name:geo(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=SPOKE}==a["untouched_112_meshes"]
 assert all(holes_pass())
 sc=bpy.context.scene
 camera_data=bpy.data.cameras.new("R33_UNSAVED_APPROX_EYE")
 camera=bpy.data.objects.new("R33_UNSAVED_APPROX_EYE",camera_data)
 sc.collection.objects.link(camera)
 camera.location=(-.35,-.92,1.055)
 camera.rotation_euler=(Vector((-.24,.19,.797))-camera.location).to_track_quat("-Z","Y").to_euler()
 camera_data.lens=28;camera_data.clip_start=.01;sc.camera=camera
 sc.render.engine="CYCLES";sc.cycles.device="CPU"
 sc.render.threads_mode="FIXED";sc.render.threads=2
 sc.cycles.samples=3;sc.cycles.use_denoising=True
 sc.render.resolution_x=720;sc.render.resolution_y=480;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
 sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
 bpy.ops.render.render(write_still=True)
 assert PNG.stat().st_size>12000 and sha(OUT)==a["result_R33_blend_sha256"]
 qa={"status":"R33_OFFICIAL_BLENDER_4_5_15_PRIVATE_SOURCE_FRESH_REOPEN_CYCLES_PASS",
 "editable_blend_sha256":sha(OUT),"render_sha256":sha(PNG),"resolution":[720,480],
 "three_attached_native_spoke_to_rim_ends":"SAVED_AND_REOPENED",
 "eight_factory_through_holes":"PASS","other_112_original_meshes":"UNCHANGED",
 "hosted_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED","seven_Spider_photos":"INCOMPLETE",
 "exact_original_game_eye":"UNCALIBRATED","vehicle_complete":False,"score_delta":0}
 QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf8")
 print("R33_FRESH_REOPEN_REAL_CYCLES_PASS",sha(PNG),flush=True)
def compare():
 from PIL import Image
 assert QA.is_file() and PREV.is_file() and PNG.is_file() and not COMP.exists()
 with Image.open(PREV) as p,Image.open(PNG) as q:
  a=p.convert("RGB");b=q.convert("RGB")
  assert a.size==b.size==(720,480)
  pa=a.load();pb=b.load()
  diff=sum(max(abs(pa[x,y][k]-pb[x,y][k]) for k in range(3))>3
    for x in range(720) for y in range(480))
  assert diff>100,("BLOCKED_NO_VISUAL_SOURCE_GEOMETRY_CHANGE",diff)
  out=Image.new("RGB",(1440,480))
  out.paste(a,(0,0));out.paste(b,(720,0));out.save(COMP,quality=94,optimize=True)
 qa=json.loads(QA.read_text())
 qa.update({"r32_vs_r33_pixels_changed_gt3":diff,"compare_sha256":sha(COMP),
  "r32_original_cycles_sha256":sha(PREV)})
 QA.write_text(json.dumps(qa,indent=2),encoding="utf8")
 print("R33_REAL_SOURCE_BEFORE_AFTER",diff,sha(COMP),flush=True)
def run(mode):
 assert BL.is_file()
 scene=NATIVE if mode=="native" else BASE if mode=="build" else OUT
 cmd=[str(BL),"--background",str(scene),"--threads","2","--python",str(Path(__file__).resolve()),"--",mode]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=215)
 print(p.stdout[-15000:],flush=True)
 if p.returncode:print(p.stderr[-4500:],flush=True);raise RuntimeError("BLENDER_R33_"+mode+"_"+str(p.returncode))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode in ("native","build","verify"):
  try:import bpy
  except ImportError:run(mode)
  else:{"native":native,"build":build,"verify":verify}[mode]()
 elif mode=="compare":compare()
 else:raise SystemExit("usage: script.py native|build|verify|compare")