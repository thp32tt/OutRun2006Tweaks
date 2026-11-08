#!/usr/bin/env python3
"""SLOT=C Ferrari F50 original PMT center_console dispatch #2.
Source-derived gear-selector SHAFT ONLY (PMT object20/group00/material001);
no new objects/materials, no dashboard/steering or any other native mesh edits.
"""
import bpy,bmesh,math,json,hashlib,struct,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotC_f50_source_audit_20261108")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
IMPORT=ROOT/"F50_OriginalPMT_CockpitSource_v1.blend"
PARENT=ROOT/"F50_OriginalPMT_CenterConsole_Shifter_v38.blend"
OUT=ROOT/"F50_OriginalPMT_CenterConsole_Shaft_v39.blend"
REPORT=ROOT/"F50_CenterConsole_Shaft_v39_Receipt.json"
AUDIT=ROOT/"F50_CenterConsole_Shaft_v39_IndependentReopen.json"
REF=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/03_F50/REF12_1995_ferrari_f50_transmission_2_1c36328e4.jpg")
SOURCES={
 PMT:"10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab",
 IMPORT:"d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31",
 PARENT:"8e9081c15a071e2b2edde4f44dc529470ac08d9f34a8e4516a93b8926e933ec2"}
PART="PMT_F50_object20_group00_material001_a0"
KNOB="PMT_F50_object20_group00_material000_a0"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as fi:
  for chunk in iter(lambda:fi.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def protect():
 assert bpy.app.version[:3]==(4,5,15), "OFFICIAL_BLENDER_REQUIRED"
 for p,value in SOURCES.items():assert p.is_file() and sha(p)==value,("BLOCKED_INPUT_SHA",str(p))
 assert REF.is_file(),"BLOCKED_F50_PHOTO"
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==SOURCES[PMT]
 meshes=[o for o in bpy.data.objects if o.type=="MESH"]
 assert len(meshes)==42,len(meshes)
 for o in meshes:
  assert o.get("outrun_original_game_resource_sha256")==SOURCES[PMT],o.name
 assert bpy.data.objects[PART].get("outrun_original_mesh_object_id")=="object20_group00_material001_a0"
 assert bpy.data.objects[KNOB].get("outrun_original_mesh_object_id")=="object20_group00_material000_a0"
def fingerprint(o):
 h=hashlib.sha256();m=o.data
 for v in m.vertices:h.update(struct.pack("<3d",*map(float,v.co)))
 for p in m.polygons:
  vals=tuple(int(i) for i in p.vertices)
  h.update(struct.pack("<I",len(vals)));h.update(struct.pack("<"+"I"*len(vals),*vals))
 for uv in m.uv_layers:
  h.update(uv.name.encode())
  for a in uv.data:h.update(struct.pack("<2d",float(a.uv.x),float(a.uv.y)))
 for mat in m.materials:h.update((mat.name if mat else "<null>").encode())
 for row in o.matrix_world:
  for x in row:h.update(struct.pack("<d",float(x)))
 h.update(str(o.get("outrun_original_mesh_object_id")).encode())
 return {"sha256":h.hexdigest(),"verts":len(m.vertices),"faces":len(m.polygons)}
def snap():return {o.name:fingerprint(o) for o in bpy.data.objects if o.type=="MESH"}
def cam_sig():return {o.name:([list(row) for row in o.matrix_world],o.data.lens) for o in bpy.data.objects if o.type=="CAMERA"}
def render(label):
 scene=bpy.context.scene
 keepcam=scene.camera
 old=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format)
 states={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 cd=bpy.data.cameras.new("TEMP_SHIFT_V39_"+label);c=bpy.data.objects.new("TEMP_SHIFT_V39_"+label,cd)
 scene.collection.objects.link(c);scene.camera=c
 c.location=(.28,.22,.33);c.rotation_euler=(Vector((0,.06,0))-c.location).to_track_quat("-Z","Y").to_euler()
 cd.type="ORTHO";cd.ortho_scale=.24
 try:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in (PART,KNOB)
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format="PNG"
  scene.render.filepath=str(ROOT/("F50_CenterConsole_Shaft_v39_"+label+".png"))
  bpy.ops.render.render(write_still=True)
  return sha(Path(scene.render.filepath))
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=states[o.name]
  scene.camera=keepcam
  scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format=old
  bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(cd)
def source_edit():
 ob=bpy.data.objects[PART];m=ob.data
 assert len(m.vertices)==12 and len(m.polygons)==6,("SOURCE_SHAFT_UNEXPECTED",len(m.vertices),len(m.polygons))
 original=[(v.co.x,v.co.y,v.co.z) for v in m.vertices]
 assert min(p[1] for p in original)>=-1.e-6
 assert abs(max(p[1] for p in original)-.08769)<.00005
 # Original triangle shaft is exactly three duplicated source side panels.
 cross=sorted({(round(p[0],5),round(p[2],5)) for p in original})
 assert len(cross)==3,cross
 cx=sum(p[0] for p in cross)/3.
 cz=sum(p[1] for p in cross)/3.
 assert abs(cx)<.002 and abs(cz)<.004
 bm=bmesh.new();bm.from_mesh(m)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=4,use_grid_fill=True)
 moved=0;mx=0.;rmins=[];rmaxs=[]
 for v in bm.verts:
  x,y,z=float(v.co.x),float(v.co.y),float(v.co.z)
  vx=x-cx;vz=z-cz;r=math.hypot(vx,vz)
  if r<.0002:
   bm.free();raise AssertionError("BLOCKED_INTERIOR_DEGENERATE_SHAFT_SAMPLE")
  t=max(0.,min(1.,y/.08769))
  # The original shaft is tri-sided; reprofile genuine source surface as a slim
  # circle using its own 3D perimeter and existing axial range, without new part.
  rdesired=.00525-.00030*t
  scale=rdesired/r
  xx=cx+vx*scale;zz=cz+vz*scale
  delta=math.hypot(xx-x,zz-z)
  if delta>1.e-7:
   v.co.x=xx;v.co.z=zz;moved+=1;mx=max(mx,delta)
 bm.to_mesh(m);bm.free();m.update()
 assert moved>70 and mx>.0004 and mx<.007,(moved,mx)
 assert len(m.vertices)>100 and len(m.polygons)>80,(len(m.vertices),len(m.polygons))
 return {"original_verts":12,"original_faces":6,"new_verts":len(m.vertices),"new_faces":len(m.polygons),"moved_vertices":moved,"max_displacement_mm":round(mx*1000.,5),"cross_section":"PMT original triangular shaft surface -> cylindrically reprofiled (source-face subdivision 4 cuts)","source_side_panels_preserved":3,"new_objects":0,"original_rod_span_y":[round(min(p[1] for p in original),6),round(max(p[1] for p in original),6)]}
def build():
 protect()
 assert Path(bpy.data.filepath).resolve()==PARENT
 assert not any(p.exists() for p in (OUT,REPORT,AUDIT))
 before=snap();cam_before=cam_sig()
 image_before=render("BEFORE")
 geom=source_edit();after=snap()
 assert set(before)==set(after) and len(after)==42
 assert all(before[name]==after[name] for name in before if name!=PART), "UNRELATED_GEOMETRY_MUTATED"
 assert before[PART]["sha256"]!=after[PART]["sha256"]
 assert cam_sig()==cam_before
 bpy.context.scene["slot_c_center_console_dispatch_2"]="NATIVE_SHIFTER_SHAFT_V39_SOURCE_DERIVED"
 bpy.context.scene["slot_c_center_console_coverage"]="COVERED_PARTIAL_QA_KNOB_SHAFT; H_GATE_BLOCKED"
 bpy.context.scene["slot_c_v39_input_blend_sha256"]=SOURCES[PARENT]
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
 image_after=render("AFTER")
 report={"status":"SOURCE_PMTC_ENTER_CONSOLE_SHAFT_REAL_EDIT_REOPEN_PENDING","slot":"C","car":"f50","part":"center_console","native_object":"object20_group00_material001_a0","input":SOURCES[PARENT],"original_pmt":SOURCES[PMT],"original_import":SOURCES[IMPORT],"output":sha(OUT),"output_bytes":OUT.stat().st_size,"before_part":before[PART],"after_part":after[PART],"geometry":geom,"41_other_source_meshes_unchanged":True,"render_before":image_before,"render_after":image_after,"reference_filename":REF.name,"reference_photo_sha256":sha(REF),"h_gate":"BLOCKED_SOURCE_NOT_IDENTIFIED","whole_car_qa":"NOT_PASS","next":"driver_controls","score":"no_claim_pending_decision"}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print("SLOT_C_F50_SHAFT_SOURCE_CHANGED",json.dumps(report),flush=True)
def audit():
 protect()
 assert Path(bpy.data.filepath).resolve()==OUT
 assert REPORT.exists() and sha(OUT)==json.loads(REPORT.read_text())["output"]
 after=snap()
 bpy.ops.wm.open_mainfile(filepath=str(PARENT))
 protect();before=snap()
 assert len(before)==len(after)==42
 assert all(before[name]==after[name] for name in before if name!=PART)
 assert before[PART]!=after[PART]
 bpy.ops.wm.open_mainfile(filepath=str(OUT))
 protect();assert snap()==after
 result={"status":"PASS_BLENDER_4_5_15_INDEPENDENT_REOPEN","pmtsource_sha":SOURCES[PMT],"original_import_sha":SOURCES[IMPORT],"input_sha":SOURCES[PARENT],"output_sha":sha(OUT),"modified_original_object":"object20_group00_material001_a0","other_41_original_meshes_unchanged":True,"driver_eye":"NOT_VERIFIED","car_qa":"NOT_PASS","h_gate":"BLOCKED_UNIDENTIFIED"}
 AUDIT.write_text(json.dumps(result,indent=2))
 print("SLOT_C_F50_SHAFT_FRESH_REOPEN_PASS",json.dumps(result))
if __name__=="__main__":
 mode=sys.argv[-1]
 if mode=="build":build()
 elif mode=="audit":audit()
 else:raise SystemExit("MODE_REQUIRED")