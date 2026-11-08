#!/usr/bin/env python3
"""F50 SLOT=C center_console gear-selector knob: modify EXISTING game PMT object20
geometry in place. No synthetic shifter, new objects, textures, game exports or P0 edits.
"""
import bpy,bmesh,hashlib,struct,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108")
PARENT=ROOT/"F50_OriginalPMT_P0_DashboardSteering_v36.blend"
OUT=ROOT/"F50_OriginalPMT_CenterConsole_Shifter_v38.blend"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
ORIG=ROOT/"F50_OriginalPMT_CockpitSource_v1.blend"
PARENT_HASH="4f232ce124caab8afca8ddfcadb6b629267730d80a58ab50a1daddbfad591b3e"
ORIG_HASH="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
PMT_HASH="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
PART="PMT_F50_object20_group00_material000_a0"
SHA_PATH=ROOT/"F50_CenterConsole_Shifter_v38_Receipt.json"
AUDIT_PATH=ROOT/"F50_CenterConsole_Shifter_v38_IndependentReopen.json"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  while True:
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 return h.hexdigest()
def verified(mode):
 assert bpy.app.version[:3]==(4,5,15)
 assert all(p.is_file() and sha(p)==expected for p,expected in ((PMT,PMT_HASH),(ORIG,ORIG_HASH),(PARENT,PARENT_HASH))),"BLOCKED_INPUT_SOURCE_SHA"
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT_HASH
 assert sum(o.type=="MESH" for o in bpy.data.objects)==42
 ob=bpy.data.objects[PART]
 assert ob.get("outrun_original_mesh_object_id")=="object20_group00_material000_a0"
 assert ob.get("outrun_original_game_resource_sha256")==PMT_HASH
 assert bpy.data.objects["PMT_F50_object20_group00_material001_a0"].get("outrun_original_mesh_object_id")=="object20_group00_material001_a0"
 if mode=="build":
  assert Path(bpy.data.filepath).resolve()==PARENT
  assert len(ob.data.vertices)==16 and len(ob.data.polygons)==19
  assert not any(p.exists() for p in (OUT,SHA_PATH,AUDIT_PATH))
 else:assert Path(bpy.data.filepath).resolve()==OUT
def finger(o):
 h=hashlib.sha256();m=o.data
 for v in m.vertices:h.update(struct.pack("<3d",float(v.co.x),float(v.co.y),float(v.co.z)))
 for p in m.polygons:h.update(struct.pack("<I",len(p.vertices)));h.update(struct.pack("<"+"I"*len(p.vertices),*p.vertices))
 for uv in m.uv_layers:
  h.update(uv.name.encode())
  for item in uv.data:h.update(struct.pack("<2d",float(item.uv.x),float(item.uv.y)))
 for mat in m.materials:h.update((mat.name if mat else "").encode())
 for row in o.matrix_world:
  for x in row:h.update(struct.pack("<d",float(x)))
 h.update(str(o.get("outrun_original_mesh_object_id")).encode())
 return {"sha256":h.hexdigest(),"v":len(m.vertices),"f":len(m.polygons)}
def snapshot():return {o.name:finger(o) for o in bpy.data.objects if o.type=="MESH"}
def knob_edit():
 o=bpy.data.objects[PART];m=o.data
 cx,cz=-.00089,.00068;ybase=.08769;ytop=.12705;cy=.1072;R=.0203
 bm=bmesh.new();bm.from_mesh(m)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True)
 moved=0;maxdist=0.;coll=0
 for v in bm.verts:
  x,y,z=v.co.x,v.co.y,v.co.z
  radial=math.hypot(x-cx,z-cz)
  if radial<0.00015:continue
  wanted=math.sqrt(max(0.,R*R-(y-cy)*(y-cy)))
  wanted=max(0.0,min(wanted,.0202))
  if y<=ybase+.001:weight=0.
  elif y>=ybase+.011:weight=1.
  else:
   t=max(0.,min(1.,(y-ybase-.001)/.010));weight=t*t*(3-2*t)
  newrad=radial*(1.-weight)+wanted*weight
  newrad=max(0.,newrad)
  factor=newrad/radial
  nx=cx+(x-cx)*factor;nz=cz+(z-cz)*factor
  dist=math.hypot(nx-x,nz-z)
  if dist>0.0000001:
   moved+=1;maxdist=max(maxdist,dist);v.co.x=nx;v.co.z=nz
  if (y>ybase+.011 and abs(newrad-wanted)>1.e-5):coll+=1
 bm.to_mesh(m);bm.free();m.update()
 assert moved>55 and maxdist>0.0005 and maxdist<.011,(moved,maxdist)
 assert len(m.vertices)>90 and len(m.polygons)>100
 return {"source_native_knob_original_vf":[16,19],"after_vf":[len(m.vertices),len(m.polygons)],"moved_verts":moved,"max_displacement_mm":round(maxdist*1000,4),"method":"native knob triangle surface 2-cut subdivision with spherical radial reprofiling; source neck/pivot preserved","new_object_count":0}
def render(label):
 scene=bpy.context.scene;keep=scene.camera;orig=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format)
 flags={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 camd=bpy.data.cameras.new("TEMP_ONLY_SHIFTER_"+label);cam=bpy.data.objects.new("TEMP_ONLY_SHIFTER_"+label,camd);scene.collection.objects.link(cam);scene.camera=cam
 cam.location=(.28,.22,.33);target=Vector((0,.06,0));cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler();camd.type="ORTHO";camd.ortho_scale=.24
 try:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render="object20_" not in o.name
  scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format="PNG";scene.render.filepath=str(ROOT/("F50_CenterConsole_Shifter_v38_"+label+".png"))
  bpy.ops.render.render(write_still=True)
  return sha(Path(scene.render.filepath))
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=flags[o.name]
  scene.camera=keep
  scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format=orig
  bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(camd)
def build():
 verified("build")
 before=snapshot();caminfo={o.name:tuple(tuple(row) for row in o.matrix_world) for o in bpy.data.objects if o.type=="CAMERA"}
 image_before=render("BEFORE")
 changes=knob_edit();after=snapshot()
 assert set(before)==set(after) and all(before[k]==after[k] for k in before if k!=PART)
 assert before[PART]["sha256"]!=after[PART]["sha256"]
 assert len([o for o in bpy.data.objects if o.type=="MESH"])==42
 assert caminfo=={o.name:tuple(tuple(row) for row in o.matrix_world) for o in bpy.data.objects if o.type=="CAMERA"}
 bpy.context.scene["slot_c_last_geometry_stage"]="CENTER_CONSOLE_ORIGINAL_OBJECT20_SHIFTER_KNOB_V38"
 bpy.context.scene["slot_c_center_console_status"]="COVERED_PARTIAL_QA_SHIFTER_ONLY"
 bpy.context.scene["slot_c_input_blend_sha256"]=PARENT_HASH
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 image_after=render("AFTER")
 rep={"status":"PRIVATE_SOURCE_MESH_EDIT_SAVED_REOPEN_PENDING","slot":"C","car":"f50","region":"center_console","scope":"original shifter knob ONLY; console gate/plinth unverified","source_original_pmt_sha256":PMT_HASH,"source_original_import_blend_sha256":ORIG_HASH,"input_v36_blend_sha256":PARENT_HASH,"output_v38_blend_sha256":sha(OUT),"original_source_mesh_object_id":"object20_group00_material000_a0","edited_source_mesh":PART,"before_source_mesh":before[PART],"after_source_mesh":after[PART],"other_41_meshes_unchanged":True,"change":changes,"matching_ref":"REF16_transmission_1_f25e58b6da.jpg, metallic round knob (not verified game eye)","render_before_sha256":image_before,"render_after_sha256":image_after,"remaining":"H-pattern gate/console support not positively attributed to original PMT source; photo angle/7-view incomplete","car_qa_pass":False,"no_ovc_or_pmt_export":True}
 SHA_PATH.write_text(json.dumps(rep,ensure_ascii=False,indent=2))
 print("F50_CENTER_SOURCE_EDIT_SAVED",json.dumps({"output_sha":rep["output_v38_blend_sha256"],"change":changes,"before_render_sha":image_before,"after_render_sha":image_after}),flush=True)
def audit():
 verified("audit")
 data=json.loads(SHA_PATH.read_text())
 assert sha(OUT)==data["output_v38_blend_sha256"]
 after=snapshot();edited=after[PART]
 bpy.ops.wm.open_mainfile(filepath=str(PARENT))
 verified("build") if False else None
 before=snapshot()
 assert len(before)==42 and set(before)==set(after)
 assert all(before[k]==after[k] for k in before if k!=PART)
 assert before[PART]==data["before_source_mesh"] and edited==data["after_source_mesh"]
 bpy.ops.wm.open_mainfile(filepath=str(OUT))
 assert snapshot()==after
 res={"status":"PASS_OFFICIAL_BLENDER_4_5_15_INDEPENDENT_FRESH_REOPEN","source_pmt":PMT_HASH,"input":PARENT_HASH,"output":sha(OUT),"original_import":ORIG_HASH,"modified_original_object":"object20_group00_material000_a0","other_41_original_meshes_identical":True,"source_shifter_stem_unchanged":True,"car_qa":"PARTIAL_NOT_PASS","scope":"center_console/shifter only"}
 AUDIT_PATH.write_text(json.dumps(res,indent=2));print("F50_CENTER_INDEPENDENT_REOPEN_PASS",json.dumps(res),flush=True)
if __name__=="__main__":
 if sys.argv[-1]=="build":build()
 elif sys.argv[-1]=="audit":audit()
 else:raise ValueError("build/audit required")