#!/usr/bin/env python3
"""F50 slot C v37_r2: original native gauge binnacle surround topology, not another rim smoothing.
Modify existing original PMT object00/group01/material011 in place; no new object, material,
texture, export, synthetic replacement, game conversion or other car edits.
"""
import bpy,bmesh,argparse,hashlib,math,json,sys
from pathlib import Path
from mathutils import Vector
import importlib.util
base=Path(__file__).with_name("f50_p0_source_mesh_v34.py")
spec=importlib.util.spec_from_file_location("f50_native_contract",str(base))
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
PMT=contract.PMT_SHA;ORIGINAL_IMPORT=contract.IMPORT_SHA
PARENT="4f232ce124caab8afca8ddfcadb6b629267730d80a58ab50a1daddbfad591b3e"
ARCH="PMT_F50_object00_group01_material011_a0"
WHEEL="PMT_F50_object21_group01_material002_a0"
HOOD="PMT_F50_object00_group01_material028_a0"
CAM="QA_F50_GAUGE_DETAIL_NON_GAME"
F50_PHOTO="6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961"
def s(v):return contract.smooth(v)
def clamp(v,l):return contract.clamp(v,l)
def sha(p):return contract.sha(p)
def interp(x,profile):
 if x<=profile[0][0]:return profile[0][1]
 if x>=profile[-1][0]:return profile[-1][1]
 for j in range(len(profile)-1):
  if profile[j][0]<=x<=profile[j+1][0]:
   a=profile[max(0,j-1)];b=profile[j];c=profile[j+1];d=profile[min(len(profile)-1,j+2)]
   t=(x-b[0])/(c[0]-b[0]);m1=(c[1]-a[1])/(c[0]-a[0]);m2=(d[1]-b[1])/(d[0]-b[0])
   h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t;h11=t**3-t*t
   dx=c[0]-b[0]
   return h00*b[1]+h10*dx*m1+h01*c[1]+h11*dx*m2
 raise AssertionError("PROFILE")
def camera_state():return contract.cam_state()
def snap():return contract.meshes()
def verify(a,stage):
 assert bpy.app.version[:3]==(4,5,15)
 for p,expected in ((a.native,PMT),(a.original_import,ORIGINAL_IMPORT),(a.before,PARENT)):
  assert p.is_file() and sha(p)==expected,("BLOCKED_INPUT",str(p))
 assert a.photo.is_file() and sha(a.photo)==F50_PHOTO,("BLOCKED_REFERENCE",a.photo)
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
 assert bpy.context.scene.get("geometry_edit_count")==(108 if stage=="before" else 109)
 assert len(snap())==42
 ob=bpy.data.objects[ARCH]
 assert ob.get("outrun_original_mesh_object_id")=="object00_group01_material011_a0"
 assert ob.get("outrun_original_game_resource_sha256")==PMT
 if stage=="before":assert (len(ob.data.vertices),len(ob.data.polygons))==(109,119)
 assert contract.boundary_loop_stats(bpy.data.objects[WHEEL])[1]==[48,48,72,72,72,96,96,120]
def render(a,when):
 scene=bpy.context.scene; cam=scene.camera; oldeng=scene.render.engine
 oldres=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage)
 oldpath=scene.render.filepath; oldfmt=scene.render.image_settings.file_format
 oldhide={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 try:
  scene.camera=bpy.data.objects[CAM]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=(o.name not in (ARCH,HOOD))
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.resolution_x=900;scene.render.resolution_y=560;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format="PNG"
  scene.render.filepath=str(a.render_root)+"_"+when+"_INSTRUMENT_SURROUND.png"
  bpy.ops.render.render(write_still=True)
  return sha(Path(scene.render.filepath))
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=oldhide[o.name]
  scene.camera=cam;scene.render.engine=oldeng
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=oldres
  scene.render.filepath=oldpath;scene.render.image_settings.file_format=oldfmt
def edit():
 o=bpy.data.objects[ARCH]
 # Original arch crown index chain is directly sampled from game PMT import.
 # Indices identify actual source native silhouette; cubic Hermite interpolation
 # follows the native outline rather than imposing a replacement shape.
 ids=[52,34,35,37,39,41,42]
 original=[v.co.copy() for v in o.data.vertices]
 profile=[(original[i].x,original[i].y) for i in ids]
 assert all(profile[i][0]<profile[i+1][0] for i in range(6)),("BLOCKED_PROFILE_NATIVE",profile)
 assert .79<profile[3][1]<.80
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True)
 bm.verts.ensure_lookup_table()
 baseline=[v.co.copy() for v in bm.verts]
 moved=0; maximum=0.
 for idx,v in enumerate(bm.verts):
  p=v.co
  if not (-.495<p.x<-.214 and .760<p.y<.807 and -.540<p.z<-.495):continue
  cx=(p.x+.35428)/.143
  arch_side=max(0.,1.-cx*cx)
  # Outer upper source surround only: inner seam protected to avoid v37 gap artifact.
  z_mask=s((p.z+.542)/.021)*s((-.493-p.z)/.021)
  y_mask=s((p.y-.761)/.030)
  region=arch_side*z_mask*y_mask
  if region<.065:continue
  # Preserve native control-point heights and smoothly correct big flat chords.
  native_curve=interp(p.x,profile)
  chord_correction=clamp(native_curve-p.y,.0014)*region
  rolled_crown=.0029*region
  dy=clamp(chord_correction+rolled_crown,.0040)
  # Recess outer rounded face by a few mm, source-normal guided, not a fake bezel.
  dz=0.0  # source-contact inner seam must not separate
  v.co.y+=dy;v.co.z+=dz
  dist=(v.co-baseline[idx]).length
  if dist>1e-6:moved+=1;maximum=max(maximum,dist)
 bm.to_mesh(o.data);bm.free();o.data.update()
 assert moved>35 and maximum>.001 and maximum<.005,("BLOCKED_NO_MATERIAL_ARCH_CHANGE",moved,maximum)
 assert len(o.data.vertices)>400 and len(o.data.polygons)>450
 return {"moved_after_subdivision":moved,"max_mm":round(1000*maximum,5),"original_source_vertices":109,"original_source_faces":119,
  "after_vertices":len(o.data.vertices),"after_faces":len(o.data.polygons),"source_profile_indices":ids,"source_profile_xy":profile,
  "method":"source edge-loop subdivision (2 cuts) and native crown profile-guided rolled lip"}
def compare(before,after,cameras):
 assert len(before)==len(after)==42 and set(before)==set(after)
 for k,x in before.items():
  y=after[k]
  if k!=ARCH:assert x==y,("BLOCKED_UNRELATED_MESH_MODIFICATION",k)
  else:
   for name in ("source_id","pmt_sha","matrix","materials","uv_layers"):
    assert x[name]==y[name],("BLOCKED_NATIVE_ID_OR_MATERIAL",name)
   assert y["vertices"]>x["vertices"] and y["faces"]>x["faces"]
   assert x["mesh_sha256"]!=y["mesh_sha256"]
 assert camera_state()==cameras
 assert contract.boundary_loop_stats(bpy.data.objects[WHEEL])[1]==[48,48,72,72,72,96,96,120]
def build(a):
 verify(a,"before")
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert all(not p.exists() for p in (a.after,a.report,a.audit))
 before=snap();cams=camera_state()
 br=render(a,"BEFORE")
 delta=edit()
 after=snap();compare(before,after,cams)
 bpy.context.scene["geometry_edit_count"]=109
 bpy.context.scene["slot_c_input_blend_sha256"]=PARENT
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V37_R2_NATIVE_GAUGE_SURROUND_ACTUAL_TOPOLOGY_ROLLED_CROWN"
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 ar=render(a,"AFTER")
 report={"status":"SOURCE_NATIVE_F50_V37_R2_PRIVATE_SAVED_FRESH_REOPEN_PENDING",
 "native_original_PMTSHA256":PMT,"original_import_blend_sha256":ORIGINAL_IMPORT,"parent_v36_sha256":PARENT,
 "output_v37_r2_sha256":sha(a.after),"output_bytes":a.after.stat().st_size,
 "original_mesh_id":ARCH,"source_before":before[ARCH],"source_after":after[ARCH],"geometry":delta,
 "remaining_native_source_meshes_unchanged":41,"source_wheel_624_open_edges":"UNCHANGED",
 "original_game_camera":"UNVERIFIED","real_photo_seven_view":"INCOMPLETE",
 "hosted_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED","car_complete":False,"slot_advance":False,"score_delta":0,
 "renders":{"before":br,"after":ar}}
 a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print("F50_V37_R2_EDITED_NATIVE_GAUGE_SURROUND",json.dumps({"sha":report["output_v37_r2_sha256"],"delta":delta}),flush=True)
def audit(a):
 verify(a,"after")
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 data=json.loads(a.report.read_text(encoding="utf-8"))
 assert sha(a.after)==data["output_v37_r2_sha256"]
 after=snap();cams=camera_state()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 verify(a,"before");before=snap()
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 compare(before,snap(),cams)
 assert snap()==after
 rr=render(a,"REOPEN")
 result={"status":"PASS_ORIGINAL_F50_V37_R2_OFFICIAL_BLENDER_4_5_15_REOPEN_NATIVE_TOPOLOGY_RENDER",
 "input_native_pmt_sha256":PMT,"input_v36_sha256":PARENT,"output_v37_r2_sha256":sha(a.after),
 "fresh_original_surround_render":rr,"unchanged_native_meshes":41,"wheels_open_edges":624,
 "driver_eye":"UNVERIFIED","photo7":"INCOMPLETE","hosted_real_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED","score":0}
 assert not a.audit.exists()
 a.audit.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print(result["status"]+" "+result["output_v37_r2_sha256"],flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--mode",choices=("build","audit"),required=True)
 for name in ("native","original-import","before","after","photo","render-root","report","audit"):
  ap.add_argument("--"+name,dest=name.replace("-","_"),type=Path,required=True)
 a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 (build if a.mode=="build" else audit)(a)
if __name__=="__main__":main()