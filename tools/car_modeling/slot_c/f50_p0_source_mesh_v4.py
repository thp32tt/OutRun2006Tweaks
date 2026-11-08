#!/usr/bin/env python3
"""Slot C Ferrari F50 v4: edit native PMT-derived dashboard/wheel/hub meshes IN PLACE.
Input: immutable original PMT + exact original-import .blend + exact v3r2 edited .blend.
Output: private Blender scene, source-mesh report, paired diagnostic renders. NO game export.
"""
import bpy, bmesh, hashlib, struct, json, math, sys, argparse
from pathlib import Path

PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="46f7e420e10701d410137114a15bd86598c05db01fbe51e83ced719803447438"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",1378,1888,"c2212eef2413ca5010d6b95738e2df6287afb76a502c143a8f194f9e00799814"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",3460,6624,"a4cffad3f941547afc0ca8121962a17b8a26c7a31902f95a967279c12cb5177f"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"d970f0ccfa0ba2ff50530053bdb1a7032ece22916a28d9c9a57a2a197b439be5")
}

def sha(p):
 return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def mesh_sha(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for face in me.polygons:
  h.update(struct.pack("<I",len(face.vertices)))
  for i in face.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()

def snapshot(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 nm=sum(not e.is_manifold for e in bm.edges);bm.free()
 return dict(original_id=o.get("outrun_original_mesh_object_id"),
  source_sha=o.get("outrun_original_game_resource_sha256"),verts=len(o.data.vertices),
  faces=len(o.data.polygons),geometry_sha=mesh_sha(o.data),
  nonmanifold_edges=nm,uv=len(o.data.uv_layers),materials=len(o.data.materials),
  matrix=[round(float(v),9) for row in o.matrix_world for v in row],
  native_index=o.get("outrun_original_pmt_object_index"))

def subdivide_derived(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
 bm.to_mesh(o.data);bm.free();o.data.update()

def refined_cowl(o):
 # Original native hood shell, NOT a new replacement hood. Resample native edges.
 subdivide_derived(o)
 vs=o.data.vertices
 xmin,xmax=min(v.co.x for v in vs),max(v.co.x for v in vs)
 ymin,ymax=min(v.co.y for v in vs),max(v.co.y for v in vs)
 zmin,zmax=min(v.co.z for v in vs),max(v.co.z for v in vs)
 moved=0; maxdelta=0.
 for v in vs:
  x=(v.co.x-xmin)/max(1.e-8,xmax-xmin)
  t=(v.co.y-ymin)/max(1.e-8,ymax-ymin)
  u=(x-0.5)*2.
  # F50 arch: taut upper padded visor; smooth shoulders falling toward both sides.
  brow=math.exp(-((t-(0.75-0.12*u*u))/0.14)**2)
  shoulders=(math.exp(-((x-.20)/.15)**2)+math.exp(-((x-.80)/.15)**2))
  swept=math.exp(-((t-.48)/.19)**2)
  center_recess=math.exp(-((u)/.53)**4)*math.exp(-((t-.40)/.14)**2)
  dz=.0026*brow*(1-.27*u*u)+.0018*shoulders*swept-.0013*center_recess
  # Avoid touching thin perimeter seam along the source bottom edge.
  dz*=max(0.,min(1.,(t-.025)/.12))
  if abs(dz)>1e-6:
   v.co.z+=dz;moved+=1;maxdelta=max(maxdelta,abs(dz))
 for f in o.data.polygons:f.use_smooth=True
 o.data.update()
 o["source_edit_scope"]="F50 v4 original group01 material028: resampled native topology, sculpted continuous dashboard brow and shoulder returns"
 return moved,maxdelta,((xmin,xmax),(ymin,ymax),(zmin,zmax))

def refined_wheel(o):
 # 3-spoke rim/spokes remain the original PMT object21 mesh, same local pivot.
 subdivide_derived(o)
 moved=0;maxdelta=0.
 for v in o.data.vertices:
  x,y,z=v.co;r=math.hypot(x,y)
  if r<1.e-7:continue
  a=math.atan2(y,x)
  def angular(a,b):
   d=math.atan2(math.sin(a-b),math.cos(a-b))
   return math.exp(-(d/.23)**2)
  upper=angular(a,math.pi*.80)+angular(a,math.pi*.20)
  lower=angular(a,-math.pi/2)
  band=math.exp(-((r-.146)/.019)**2)
  front=max(.05,min(1.,(z+.012)/.022))
  # Refine actual leather rim cross section, upper thumb supports & 6-o'clock pad.
  dr=band*(.0013*upper+.00045*lower)
  dz=band*(.0023*upper+.0008*lower)*front
  # Pressed original horizontal two-spoke relief & lower third-spoke bulge.
  side=math.exp(-((abs(x)-.072)/.035)**2)*math.exp(-((y+.021)/.022)**2)
  bottom=math.exp(-((x)/.023)**2)*math.exp(-((y+.092)/.030)**2)
  dz+=.0012*side*(1 if z>=0 else .2)+.0010*bottom*(1 if z>=0 else .2)
  if abs(dz)>1e-6 or abs(dr)>1e-6:
   v.co.x+=dr*x/r;v.co.y+=dr*y/r;v.co.z+=dz
   moved+=1;maxdelta=max(maxdelta,abs(dr),abs(dz))
 for f in o.data.polygons:f.use_smooth=True
 o.data.update()
 o["source_edit_scope"]="F50 v4 original object21 group01 material002: denser leather rim and original 3-spoke cross-section, no new mesh object"
 return moved,maxdelta,None

def refined_hub(o):
 # Existing original hub has been tessellated in v3r2. Reuse those very vertices.
 moved=0;maxdelta=0.
 fasteners=[(.048*math.cos(math.radians(d)),-.019+.048*math.sin(math.radians(d))) for d in (30,90,150,210,270,330)]
 for v in o.data.vertices:
  x,y,z=v.co
  rc=math.hypot(x,y+.019)
  # Preserve outside edge/rig; mild central cap and annular recessed join.
  dz=.00085*math.exp(-(rc/.022)**4)-.00065*math.exp(-((rc-.036)/.007)**2)
  for fx,fy in fasteners:
   rr=math.hypot(x-fx,y-fy)
   dz-=.00042*math.exp(-((rr)/.0072)**2)
   dz+=.00028*math.exp(-((rr-.0115)/.0048)**2)
  dz*=1 if z>=0 else .10
  if abs(dz)>1e-6:
   v.co.z+=dz;moved+=1;maxdelta=max(maxdelta,abs(dz))
 for f in o.data.polygons:f.use_smooth=True
 o.data.update()
 o["source_edit_scope"]="F50 v4 original object21 group00 material000: native cap/fastener inset and ring relief without new part or materials"
 return moved,maxdelta,None

def render_diag(scene,root,tag,cam,keep):
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 prev_cam=scene.camera;prev_engine=scene.render.engine;prev_path=scene.render.filepath
 prev_res=scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage
 try:
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=800,560,100
  scene.render.image_settings.file_format="PNG"
  scene.camera=bpy.data.objects[cam]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in keep
  path=str(root)+"_"+tag+".png"
  scene.render.filepath=path;bpy.ops.render.render(write_still=True)
  assert Path(path).is_file() and Path(path).stat().st_size>10000
  return path,sha(path)
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  scene.camera=prev_cam;scene.render.engine=prev_engine;scene.render.filepath=prev_path
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=prev_res

def run():
 ap=argparse.ArgumentParser()
 for key in ("native","original-import","input","output","report","render-root"):
  ap.add_argument("--"+key,required=True,type=Path)
 a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 assert a.native.is_file() and sha(a.native)==PMT_SHA,"BLOCKED_INPUT native PMT SHA mismatch"
 assert a.original_import.is_file() and sha(a.original_import)==IMPORT_SHA,"BLOCKED_INPUT source-derived original scene missing"
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT v3r2 scene SHA mismatch"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 assert not a.output.exists() and not a.report.exists(),"Never replace immutable prior checkpoints"
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==9
 objs={o.name:o for o in bpy.data.objects if o.type=="MESH"}
 assert len(objs)==42 and all(o.get("outrun_original_mesh_object_id") for o in objs.values())
 before={n:snapshot(o) for n,o in objs.items()}
 for n,(source_id,v,f,sh) in TARGETS.items():
  b=before[n]
  assert (b["original_id"],b["verts"],b["faces"],b["geometry_sha"])==(source_id,v,f,sh),n
  assert b["source_sha"]==PMT_SHA
 assert all(o.data.materials.__len__()==0 for o in objs.values())
 cam_states={o.name:tuple(round(float(v),9) for row in o.matrix_world for v in row) for o in bpy.data.objects if o.type=="CAMERA"}
 previews={}
 views=[("GAUGE","QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"]),
        ("STEERING","QA_F50_STEERING_LOCAL_NON_GAME",["PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"])]
 for label,cam,keep in views:previews["before_"+label]=render_diag(scene,a.render_root,"BEFORE_"+label,cam,keep)
 changes={}
 for name,fn in zip(TARGETS,(refined_cowl,refined_wheel,refined_hub)):
  count,delta,bounds=fn(objs[name])
  assert count>60 and delta>.0002,(name,count,delta)
  changes[name]={"moved_vertices":count,"max_abs_delta":round(delta,8),"source_bounds_before":bounds}
 after={n:snapshot(o) for n,o in objs.items()}
 for n in before:
  b,c=before[n],after[n]
  assert b["original_id"]==c["original_id"] and b["source_sha"]==c["source_sha"]==PMT_SHA
  assert b["matrix"]==c["matrix"] and b["uv"]==c["uv"] and b["materials"]==c["materials"]
  if n not in TARGETS:assert b==c,"Unexpected other original mesh changed: "+n
  else:assert b["geometry_sha"]!=c["geometry_sha"]
 assert after["PMT_F50_object00_group01_material028_a0"]["verts"]>before["PMT_F50_object00_group01_material028_a0"]["verts"]
 assert after["PMT_F50_object21_group01_material002_a0"]["verts"]>before["PMT_F50_object21_group01_material002_a0"]["verts"]
 assert after["PMT_F50_object21_group00_material000_a0"]["verts"]==before["PMT_F50_object21_group00_material000_a0"]["verts"]
 assert after["PMT_F50_object00_group01_material028_a0"]["nonmanifold_edges"]==0
 assert after["PMT_F50_object21_group00_material000_a0"]["nonmanifold_edges"]==0
 assert all(tuple(round(float(v),9) for row in o.matrix_world for v in row)==cam_states[o.name] for o in bpy.data.objects if o.type=="CAMERA")
 scene["geometry_edit_count"]=12
 scene["slot_c_last_geometry_stage"]="F50_P0_V4_NATIVE_COWL_WHEEL_HUB_TESSELLATION"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,cam,keep in views:previews["after_"+label]=render_diag(scene,a.render_root,"AFTER_"+label,cam,keep)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"status":"F50_SLOT_C_V4_REAL_NATIVE_GEOMETRY_SAVED_INDEPENDENT_QA_PENDING",
  "blender":bpy.app.version_string,"source_car":"Ferrari F50",
  "original_pmt_path":str(a.native),"original_pmt_sha256":PMT_SHA,
  "original_import_blend_sha256":IMPORT_SHA,"input_blend_sha256":INPUT_SHA,
  "private_output_blend":str(a.output),"private_output_sha256":sha(a.output),
  "original_source_mesh_count":42,"modified_original_meshes":{
    n:{"original_id":before[n]["original_id"],"before":before[n],"after":after[n],**changes[n]} for n in TARGETS},
  "untouched_other_original_meshes":39,"original_object_transforms_unchanged":True,
  "original_camera_transforms_unchanged":True,"original_game_file_unchanged":True,
  "diagnostic_renders":previews,"photo_reference":"03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg",
  "photo_reference_status":"MORPHOLOGY_ONLY_UNCALIBRATED",
  "game_driver_eye":"UNVERIFIED","seven_photo_views":"INCOMPLETE",
  "github_hosted_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "created_pmt_ovc_ovc3_glb_game_package":False,"created_material_texture_normal_PBR":False,
  "changed_exterior_Dino_Model2_or_slotA":False,"complete":False}
 a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V4_ORIGINAL_SCENE_SAVED",report["private_output_sha256"],[(n,after[n]["verts"],after[n]["faces"]) for n in TARGETS])
if __name__=="__main__":run()