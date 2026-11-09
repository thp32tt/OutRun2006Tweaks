#!/usr/bin/env python3
"""SLOT C F50: driver_controls native source unidentifiable -> BLOCKED.
Next breadth component inner_door: edit ONLY authentic PMT material031 driver-side upper door rail.
NO dashboard/wheel, no new objects/faces/meshes/materials, no export/game integration.
"""
import os,sys,subprocess,json,hashlib,struct,math
from pathlib import Path
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108")
EXE=Path("/home/chatgpt-runner/work_handoff/blender_4_5_15_official_cache/blender-4.5.15-linux-x64/blender")
INPUT=ROOT/"F50_OriginalPMT_CenterConsole_Shaft_v39.blend"
OUTPUT=ROOT/"F50_OriginalPMT_InnerDoor_UpperRail_v40.blend"
BASE=ROOT/"F50_OriginalPMT_CockpitSource_v1.blend"
ORIG=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg")
REPORT=ROOT/"F50_InnerDoor_UpperRail_v40_Receipt.json"
AUDIT=ROOT/"F50_InnerDoor_UpperRail_v40_IndependentReopen.json"
TARGET="PMT_F50_object00_group01_material031_a0"
EXPECTED={INPUT:"724df8bcd079299e8781726b25888243dbdcab7368d7d758f81ba8236666072f",BASE:"d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31",ORIG:"10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1024*1024),b""):h.update(x)
 return h.hexdigest()
if "bpy" not in sys.modules:
 mode=sys.argv[-1]
 assert mode in ("build","audit")
 args=[str(EXE),"-b",str(INPUT if mode=="build" else OUTPUT),"--python",__file__,"--",mode]
 p=subprocess.run(args,capture_output=True,text=True,timeout=150)
 print("OFFICIAL_BLENDER_EXIT",p.returncode,p.stdout[-13000:],p.stderr[-1800:],flush=True)
 sys.exit(p.returncode)
import bpy
from mathutils import Vector
def protect():
 assert bpy.app.version[:3]==(4,5,15)
 for p,v in EXPECTED.items():assert p.is_file() and sha(p)==v,("BLOCKED_SOURCE_SHA",str(p))
 assert PHOTO.is_file()
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==EXPECTED[ORIG]
 m=[o for o in bpy.data.objects if o.type=="MESH"]
 assert len(m)==42,len(m)
 for o in m:assert o.get("outrun_original_game_resource_sha256")==EXPECTED[ORIG],o.name
 assert bpy.data.objects[TARGET].get("outrun_original_mesh_object_id")=="object00_group01_material031_a0"
def sig(o):
 h=hashlib.sha256();mesh=o.data
 for v in mesh.vertices:h.update(struct.pack("<3d",float(v.co.x),float(v.co.y),float(v.co.z)))
 for p in mesh.polygons:
  q=tuple(int(i) for i in p.vertices)
  h.update(struct.pack("<I",len(q)));h.update(struct.pack("<"+"I"*len(q),*q))
 for uv in mesh.uv_layers:
  h.update(uv.name.encode())
  for p in uv.data:h.update(struct.pack("<2d",float(p.uv.x),float(p.uv.y)))
 for mat in mesh.materials:h.update((mat.name if mat else "<null>").encode())
 for row in o.matrix_world:
  for x in row:h.update(struct.pack("<d",float(x)))
 h.update(str(o.get("outrun_original_mesh_object_id")).encode())
 return {"sha256":h.hexdigest(),"v":len(mesh.vertices),"f":len(mesh.polygons)}
def snapshot():return {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH"}
def render(name):
 scene=bpy.context.scene;cam_old=scene.camera
 old=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format)
 states={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 cd=bpy.data.cameras.new("TEMP_F50_INNER_DOOR_V40_"+name);co=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(co)
 co.location=(-1.75,1.04,-.18);co.rotation_euler=(Vector((-.63,.57,-.12))-co.location).to_track_quat("-Z","Y").to_euler();cd.type="ORTHO";cd.ortho_scale=1.8;scene.camera=co
 try:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name!=TARGET
  scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=800;scene.render.resolution_y=720;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format="PNG"
  scene.render.filepath=str(ROOT/("F50_InnerDoor_UpperRail_v40_"+name+".png"))
  bpy.ops.render.render(write_still=True)
  return sha(Path(scene.render.filepath))
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=states[o.name]
  scene.camera=cam_old
  (scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format)=old
  bpy.data.objects.remove(co,do_unlink=True);bpy.data.cameras.remove(cd)
def build():
 protect()
 assert Path(bpy.data.filepath).resolve()==INPUT
 assert not any(p.exists() for p in (OUTPUT,REPORT,AUDIT)),"IMMUTABLE_OUTPUT_EXISTS"
 before=snapshot()
 oldobjects=set(bpy.data.objects)
 bimg=render("BEFORE")
 ob=bpy.data.objects[TARGET];mesh=ob.data
 assert len(mesh.vertices)==66 and len(mesh.polygons)==40
 modified=[];mx=0.0
 for v in mesh.vertices:
  x,y,z=map(float,v.co)
  # Original driver-side (x<0) PMT door upper trim shoulder; do not adjust
  # dashboard, wheel, unrelated body, opposite-side door, or fabricated handle.
  if -.76<x<-.60 and .715<y<.9 and .25<z<.46:
   t=min(1.,max(0.,(y-.705)/.175))
   dx=.027*t
   if dx<.003:continue
   v.co.x=x+dx
   modified.append(v.index)
   mx=max(mx,dx)
 mesh.update()
 assert 4<=len(modified)<=18,("BLOCKED_UNCERTAIN_DOOR_VERTICES",modified)
 assert .018<mx<.03
 after=snapshot()
 assert len(before)==len(after)==42
 assert all(before[n]==after[n] for n in before if n!=TARGET),"UNRELATED_MESH_MUTATED"
 assert before[TARGET]["sha256"]!=after[TARGET]["sha256"]
 assert set(bpy.data.objects)==oldobjects
 assert len(mesh.vertices)==66 and len(mesh.polygons)==40
 bpy.context.scene["slot_c_driver_controls"]="BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL"
 bpy.context.scene["slot_c_inner_door"]="COVERED_PARTIAL_QA_DRIVER_SIDE_UPPER_RAIL; HANDLE_NOT_IDENTIFIED"
 bpy.context.scene["slot_c_v40_input_blend_sha256"]=EXPECTED[INPUT]
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 aimg=render("AFTER")
 record={"status":"SOURCE_PMTC_INNER_DOOR_EDIT_FRESH_REOPEN_PENDING","slot":"C","car":"f50","driver_controls":"BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL","inner_door":"COVERED_PARTIAL_QA_UPPER_RAIL_ONLY","original_native_resource_sha256":EXPECTED[ORIG],"original_import_sha256":EXPECTED[BASE],"input_blend_sha256":EXPECTED[INPUT],"output_blend_sha256":sha(OUTPUT),"output_bytes":OUTPUT.stat().st_size,"edited_native_mesh_id":"object00_group01_material031_a0","before_target":before[TARGET],"after_target":after[TARGET],"moved_existing_vertices":len(modified),"vertex_indices":modified,"max_shift_mm":round(mx*1000,3),"other_41_meshes_identical":True,"no_created_objects":True,"workbench_before_sha256":bimg,"workbench_after_sha256":aimg,"matched_private_photo":PHOTO.name,"private_photo_sha256":sha(PHOTO),"scope":"only driver-side original PMT door inner upper rail; all 42 original object identities retained","door_handle":"BLOCKED_UNIDENTIFIED_NATIVE_SOURCE","car_qa":"NOT_PASS","next":"windshield_frame"}
 REPORT.write_text(json.dumps(record,ensure_ascii=False,indent=2))
 print("F50_INNER_DOOR_REAL_GEOMETRY_EDIT",json.dumps(record,ensure_ascii=False),flush=True)
def audit():
 protect()
 assert Path(bpy.data.filepath).resolve()==OUTPUT
 record=json.loads(REPORT.read_text())
 assert sha(OUTPUT)==record["output_blend_sha256"]
 newer=snapshot()
 bpy.ops.wm.open_mainfile(filepath=str(INPUT))
 protect();older=snapshot()
 assert len(newer)==len(older)==42
 assert all(newer[n]==older[n] for n in newer if n!=TARGET)
 assert newer[TARGET]!=older[TARGET]
 bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
 protect();assert snapshot()==newer
 info={"status":"PASS_OFFICIAL_BLENDER_4_5_15_INDEPENDENT_FRESH_REOPEN","original_pmtsource_sha256":EXPECTED[ORIG],"original_import_sha256":EXPECTED[BASE],"input_blend_sha256":EXPECTED[INPUT],"output_blend_sha256":sha(OUTPUT),"modified_native":"object00_group01_material031_a0","other_41_native_unchanged":True,"driver_controls":"BLOCKED_SOURCE_UNIDENTIFIED","inner_door":"COVERED_PARTIAL_QA","car_qa":"NOT_PASS"}
 AUDIT.write_text(json.dumps(info,indent=2))
 print("F50_INNER_DOOR_INDEPENDENT_AUDIT",json.dumps(info),flush=True)
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode=="build":build()
 elif mode=="audit":audit()
 else:raise SystemExit("MODE_REQUIRED")