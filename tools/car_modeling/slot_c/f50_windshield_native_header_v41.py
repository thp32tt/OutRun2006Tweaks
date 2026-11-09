#!/usr/bin/env python3
"""SLOT=C F50 breadth-first: driver_controls BLOCKED (no native stalk/pedal identification).
NEXT windshield_frame: reshape ONLY 13 original PMT windshield header/A-pillar outer-border vertices.
No wheels, dash, steering, glass, exterior body, new mesh, PBR, conversion, or game install.
"""
import sys,subprocess,hashlib,struct,json,math
from pathlib import Path
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108")
EXE=Path("/home/chatgpt-runner/work_handoff/blender_4_5_15_official_cache/blender-4.5.15-linux-x64/blender")
INPUT=ROOT/"F50_OriginalPMT_InnerDoor_UpperRail_v40.blend"
OUTPUT=ROOT/"F50_OriginalPMT_Windshield_Header_Apillar_v41.blend"
BASE=ROOT/"F50_OriginalPMT_CockpitSource_v1.blend"
ORIG=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/03_F50/REF16_interior_1_b0df0e6809.jpg")
REPORT=ROOT/"F50_Windshield_Header_Apillar_v41_Receipt.json"
AUDIT=ROOT/"F50_Windshield_Header_Apillar_v41_IndependentReopen.json"
TARGET="PMT_F50_object00_group00_material000_a0"
EXPECTED={INPUT:"03b96b1eb2293c151c60133919380055fa8393372b0acbf18045edf25faa949a",BASE:"d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31",ORIG:"10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"}
UPPER=[28,30,32,34,36,38,40,43,45,47,49]
LOWER=[27,50]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
if "bpy" not in sys.modules:
 mode=sys.argv[-1]
 if mode not in ("build","audit"):raise SystemExit("expected build/audit")
 p=subprocess.run([str(EXE),"-b",str(INPUT if mode=="build" else OUTPUT),"--python",__file__,"--",mode],capture_output=True,text=True,timeout=170)
 print("OFFICIAL_BLENDER_EXIT",p.returncode,p.stdout[-14000:],p.stderr[-1000:],flush=True)
 sys.exit(p.returncode)
import bpy
from mathutils import Vector
def protect():
 assert bpy.app.version[:3]==(4,5,15)
 for p,v in EXPECTED.items():assert p.is_file() and sha(p)==v,("BLOCKED_INPUT_SHA",p)
 assert PHOTO.is_file()
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==EXPECTED[ORIG]
 ms=[o for o in bpy.data.objects if o.type=="MESH"]
 assert len(ms)==42,len(ms)
 for ob in ms:assert ob.get("outrun_original_game_resource_sha256")==EXPECTED[ORIG],ob.name
 assert bpy.data.objects[TARGET].get("outrun_original_mesh_object_id")=="object00_group00_material000_a0"
def sig(o):
 h=hashlib.sha256();m=o.data
 for v in m.vertices:h.update(struct.pack("<3d",*map(float,v.co)))
 for p in m.polygons:
  ids=tuple(int(i) for i in p.vertices)
  h.update(struct.pack("<I",len(ids)));h.update(struct.pack("<"+"I"*len(ids),*ids))
 for uv in m.uv_layers:
  h.update(uv.name.encode())
  for p in uv.data:h.update(struct.pack("<2d",*map(float,p.uv)))
 for mat in m.materials:h.update((mat.name if mat else "<null>").encode())
 for row in o.matrix_world:
  for x in row:h.update(struct.pack("<d",float(x)))
 h.update(str(o.get("outrun_original_mesh_object_id")).encode())
 return {"sha256":h.hexdigest(),"v":len(m.vertices),"f":len(m.polygons)}
def snapshot():return {o.name:sig(o) for o in bpy.data.objects if o.type=="MESH"}
def render(stem):
 s=bpy.context.scene;oldcam=s.camera
 old=(s.render.engine,s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format)
 oldstate={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 ca=bpy.data.cameras.new("TEMP_F50_WIND_FRAME_V41_"+stem)
 co=bpy.data.objects.new(ca.name,ca);s.collection.objects.link(co)
 co.location=(-1.45,1.42,.27)
 co.rotation_euler=(Vector((0,.88,-.49))-co.location).to_track_quat("-Z","Y").to_euler()
 ca.type="ORTHO";ca.ortho_scale=1.65;s.camera=co
 try:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name!=TARGET
  s.render.engine="BLENDER_WORKBENCH";s.render.resolution_x=760;s.render.resolution_y=600;s.render.resolution_percentage=100
  s.render.image_settings.file_format="PNG"
  s.render.filepath=str(ROOT/("F50_Windshield_Header_Apillar_v41_"+stem+".png"))
  bpy.ops.render.render(write_still=True)
  return sha(Path(s.render.filepath))
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=oldstate[o.name]
  s.camera=oldcam
  (s.render.engine,s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.filepath,s.render.image_settings.file_format)=old
  bpy.data.objects.remove(co,do_unlink=True);bpy.data.cameras.remove(ca)
def build():
 protect()
 assert Path(bpy.data.filepath).resolve()==INPUT
 assert not any(p.exists() for p in (OUTPUT,REPORT,AUDIT)),"IMMUTABLE_OUTPUT_ALREADY_EXISTS"
 before=snapshot();oldobjs=set(bpy.data.objects)
 ob=bpy.data.objects[TARGET];me=ob.data
 assert len(me.vertices)==68 and len(me.polygons)==56
 before_png=render("BEFORE")
 moves={}
 for idx in UPPER:
  v=me.vertices[idx];x,y,z=map(float,v.co)
  # Raise/deepen the EXISTING outer header border only; the PMT glass
  # inner border and matching transparent windshield are untouched.
  dy=0.018; dz=0.009
  dx=math.copysign(0.006*min(1.0,abs(x)/.53),x) if abs(x)>0.001 else 0.0
  v.co=(x+dx,y+dy,z+dz)
  moves[idx]=[dx,dy,dz]
 for idx in LOWER:
  v=me.vertices[idx];x,y,z=map(float,v.co)
  dx=math.copysign(0.014,x);dz=0.006
  v.co=(x+dx,y,z+dz)
  moves[idx]=[dx,0.0,dz]
 me.update();after=snapshot()
 assert set(bpy.data.objects)==oldobjs
 assert len(before)==len(after)==42 and all(before[n]==after[n] for n in before if n!=TARGET),"OUT_OF_SCOPE_MESH_CHANGED"
 assert before[TARGET]["sha256"]!=after[TARGET]["sha256"]
 assert len(me.vertices)==68 and len(me.polygons)==56
 assert len(moves)==13 and max(math.sqrt(sum(x*x for x in a)) for a in moves.values())<.024
 bpy.context.scene["slot_c_driver_controls"]="BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL"
 bpy.context.scene["slot_c_windshield_frame"]="COVERED_PARTIAL_QA_NATIVE_HEADER_AND_APILLAR_OUTER_BORDER"
 bpy.context.scene["slot_c_v41_input_blend_sha256"]=EXPECTED[INPUT]
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 after_png=render("AFTER")
 rec={"status":"SOURCE_NATIVE_WINDSHIELD_FRAME_EDIT_REOPEN_PENDING","slot":"C","car_id":"f50","target_requested":"driver_controls","driver_controls":"BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL","fallback_component":"windshield_frame","windshield_frame":"COVERED_PARTIAL_QA_HEADER_AND_APILLAR_ONLY","original_game_pmt_sha256":EXPECTED[ORIG],"original_import_blend_sha256":EXPECTED[BASE],"input_blend_sha256":EXPECTED[INPUT],"output_blend_sha256":sha(OUTPUT),"output_bytes":OUTPUT.stat().st_size,"native_mesh_id":"object00_group00_material000_a0","before_target":before[TARGET],"after_target":after[TARGET],"modified_original_vertices":sorted(moves),"vertex_move_m":{str(k):[round(x,6) for x in moves[k]] for k in sorted(moves)},"max_shift_mm":round(max(math.sqrt(sum(x*x for x in a)) for a in moves.values())*1000,3),"other_41_original_meshes_unchanged":True,"new_objects_or_materials":0,"glass_005_unchanged":True,"before_png_sha256":before_png,"after_png_sha256":after_png,"private_photo_name":PHOTO.name,"private_photo_sha256":sha(PHOTO),"photo_comparison":"interior top surround and A pillar; NOT calibrated driver-eye","limitations":"original upper glass seal remains unchanged; visible full cockpit and seven-view QA pending","vehicle_final_qa":"NOT_PASS","next":"visible_seat"}
 REPORT.write_text(json.dumps(rec,indent=2,ensure_ascii=False))
 print("SLOT_C_F50_V41_SOURCE_GEOMETRY",json.dumps({k:rec[k] for k in ("native_mesh_id","modified_original_vertices","max_shift_mm","output_blend_sha256","other_41_original_meshes_unchanged","next")}),flush=True)
def audit():
 protect();assert Path(bpy.data.filepath).resolve()==OUTPUT
 rec=json.loads(REPORT.read_text());assert sha(OUTPUT)==rec["output_blend_sha256"]
 final=snapshot()
 bpy.ops.wm.open_mainfile(filepath=str(INPUT));protect();previous=snapshot()
 assert len(final)==len(previous)==42
 assert all(final[k]==previous[k] for k in previous if k!=TARGET)
 assert final[TARGET]!=previous[TARGET]
 bpy.ops.wm.open_mainfile(filepath=str(OUTPUT));protect();assert snapshot()==final
 out={"status":"PASS_OFFICIAL_BLENDER_4_5_15_INDEPENDENT_FRESH_REOPEN","source_pmt_sha256":EXPECTED[ORIG],"original_import_sha256":EXPECTED[BASE],"input_sha256":EXPECTED[INPUT],"output_sha256":sha(OUTPUT),"native_mesh_id":"object00_group00_material000_a0","changed_existing_vertex_count":13,"other_41_meshes_identical":True,"driver_controls":"BLOCKED","windshield_frame":"COVERED_PARTIAL_QA","vehicle_qa":"NOT_PASS","next":"visible_seat"}
 AUDIT.write_text(json.dumps(out,indent=2))
 print("SLOT_C_F50_V41_REOPEN",json.dumps(out),flush=True)
if __name__=="__main__":
 m=sys.argv[-1]
 if m=="build":build()
 elif m=="audit":audit()
 else:raise SystemExit("MODE_REQUIRED")
