#!/usr/bin/env python3
"""F50 Slot C P0 v7: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires exact read-only original PMT, original Blender import, prior v6 native-derived .blend hashes.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="bb0c0f5a98709194ec8a1cb15edc9b2f69dc6227515a6b0a96f208cf43cdd827"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"7710ab4cae5f59ab666fd1ed3c85fe2fb9644443d3ae99399ad160f2e6e03fdf"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"05233f8e315bd1fedc0b8dbfd9cefe8f7388a6f5559c740689f519b707b41c53"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"94fde52385dea2af49ce86c8e9023405c6d7944ef8c9511207d105efeb686f2e")}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_sig(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for f in me.polygons:
  h.update(struct.pack("<I",len(f.vertices)))
  for idx in f.vertices:h.update(struct.pack("<I",idx))
 return h.hexdigest()
def snapshot(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
 return {"id":o.get("outrun_original_mesh_object_id"),"pmt":o.get("outrun_original_game_resource_sha256"),
  "mesh_sha256":mesh_sig(o.data),"verts":len(o.data.vertices),"faces":len(o.data.polygons),
  "nonmanifold":nonmanifold,"materials":len(o.data.materials),"uv":len(o.data.uv_layers),
  "matrix":[round(float(a),9) for row in o.matrix_world for a in row]}
def window(value,lo,hi,width):
 return max(0.,min(1.,(value-lo)/width,(hi-value)/width))
def sculpt_original_hood(o):
 """In-place F50 native instrument cowl: reshape source eyebrow, original two-gauge
 recessed surfaces, lower light-blocking lip and raised center divider. No new mesh."""
 vs=o.data.vertices
 xmin,xmax=min(v.co.x for v in vs),max(v.co.x for v in vs)
 ymin,ymax=min(v.co.y for v in vs),max(v.co.y for v in vs)
 moved=0;max_displace=0.
 for v in vs:
  u=(v.co.x-xmin)/max(xmax-xmin,1.e-9)
  t=(v.co.y-ymin)/max(ymax-ymin,1.e-9)
  # Source-native local axis only; shape contours from actual original PMT dash shell.
  # F50 interior photos: elongated visor with darker sunk left cluster and speed arch.
  arch_t=.741-.094*(2*u-1)**2
  main_hood=math.exp(-((t-arch_t)/.070)**2)
  lip=math.exp(-((t-(arch_t-.126))/.039)**2)
  tach_recess=math.exp(-(((u-.338)/.174)**2+((t-.439)/.118)**2))
  speed_recess=math.exp(-(((u-.701)/.187)**2+((t-.441)/.133)**2))
  middle_bridge=math.exp(-((u-.527)/.065)**2)*math.exp(-((t-.472)/.143)**2)
  side_return=(math.exp(-((u-.130)/.077)**2)+math.exp(-((u-.865)/.082)**2))
  dz=(.00295*main_hood+.00118*lip-.00235*tach_recess
      -.00215*speed_recess+.00122*middle_bridge
      +.00072*side_return*main_hood)
  # Seal existing source perimeter: avoid occlusion at native dashboard seams.
  dz*=window(u,.017,.982,.093)*window(t,.019,.985,.091)
  if abs(dz)>1.e-6:
   v.co.z+=dz
   moved+=1
   max_displace=max(max_displace,abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v7 original PMT dashboard: deeper swept dual-instrument visor pockets, defined eyebrow/lip and protected original perimeter"
 return moved,max_displace
def sculpt_original_wheel(o):
 """Follow actual F50 3-arm wheel photo, editing existing original PMT rim/spoke
 vertices only. Improve pressed arm shoulder and upper palm grip surface relief."""
 moved=0;max_displace=0.
 for v in o.data.vertices:
  x,y,z=v.co;r=math.hypot(x,y)
  if r<1.e-8:continue
  ang=math.atan2(y,x)
  def sector(center,width):
   d=math.atan2(math.sin(ang-center),math.cos(ang-center))
   return math.exp(-(d/width)**2)
  palms=sector(.80*math.pi,.17)+sector(.20*math.pi,.17)
  lower=sector(-math.pi/2,.16)
  rim=math.exp(-((r-.1485)/.016)**4)
  interior_shoulder=math.exp(-((r-.133)/.014)**2)
  forward=window(z,-.014,.020,.014)
  # More tactile 10/2 o'clock rim cross-section; no wheel diameter or pivot change.
  dr=(.00134*palms+.00056*lower)*rim*(.41+.59*forward)
  dr+=.00040*palms*interior_shoulder
  dz=(.00188*palms+.00093*lower)*rim*(.30+.70*forward)
  # Broad smooth plate, folded outer edge and lower vertical third spoke.
  horizontal_web=math.exp(-((abs(x)-.093)/.028)**4)*math.exp(-((y+.026)/.028)**4)
  side_ridge=math.exp(-((abs(x)-.116)/.016)**2)*math.exp(-((y+.023)/.025)**2)
  stamped_edge=math.exp(-((abs(x)-.127)/.008)**2)*math.exp(-((y+.023)/.033)**2)
  lower_web=math.exp(-(x/.027)**4)*math.exp(-((y+.100)/.037)**4)
  lower_fold=math.exp(-((abs(x)-.023)/.008)**2)*math.exp(-((y+.108)/.027)**2)
  dz+=(.00138*horizontal_web+.00053*side_ridge-.00051*stamped_edge
       +.00108*lower_web-.00035*lower_fold)*(.28+.72*forward)
  if abs(dr)>1.e-6 or abs(dz)>1.e-6:
   v.co.x+=dr*x/r;v.co.y+=dr*y/r;v.co.z+=dz
   moved+=1;max_displace=max(max_displace,abs(dr),abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v7 native wheel: physically raised arm webs with folded margins, tactile upper 2/10 grips, continuous 6-o'clock spoke"
 return moved,max_displace
def sculpt_original_hub(o):
 """F50 original six-bolt center plate: retain native surface, mildly contour
 mounting collar and countersink seats on existing dense PMT-derived vertices."""
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 moved=0;max_displace=0.
 for v in o.data.vertices:
  x,y,z=v.co
  rr=math.hypot(x,y+.019)
  cap=.00062*math.exp(-(rr/.026)**4)
  cap_lip=.00051*math.exp(-((rr-.029)/.009)**2)
  collar=-.00026*math.exp(-((rr-.043)/.008)**2)
  dz=cap+cap_lip+collar
  for cx,cy in centers:
   d=math.hypot(x-cx,y-cy)
   # Wide feathered fastener pockets; deliberately no deep dent or plate fracture.
   dz-=.00021*math.exp(-(d/.010)**2)
   dz+=.00018*math.exp(-((d-.016)/.008)**2)
  dz*=max(.12,min(1.,(z+.0014)/.0045))
  if abs(dz)>1.e-6:
   v.co.z+=dz;moved+=1;max_displace=max(max_displace,abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v7 source-native hub: smoothed central cup and rimmed six fastener seats, no badge replacement"
 return moved,max_displace
def render(scene,root,tag,cam,visible):
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 prev_camera=scene.camera;eng=scene.render.engine;prev_path=scene.render.filepath
 res=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage)
 try:
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.image_settings.file_format="PNG"
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=800,560,100
  scene.camera=bpy.data.objects[cam]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in visible
  f=Path(str(root)+"_"+tag+".png")
  scene.render.filepath=str(f)
  bpy.ops.render.render(write_still=True)
  assert f.is_file() and f.stat().st_size>10000
  return {"filename":str(f),"sha256":sha(f)}
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  scene.camera=prev_camera;scene.render.engine=eng;scene.render.filepath=prev_path
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=res
def run():
 p=argparse.ArgumentParser()
 for key in ("native","original-import","input","output","report","render-root"):
  p.add_argument("--"+key,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 assert a.native.is_file() and sha(a.native)==PMT_SHA,"BLOCKED_INPUT native PMT provenance mismatch"
 assert a.original_import.is_file() and sha(a.original_import)==IMPORT_SHA,"BLOCKED_INPUT true original import missing"
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified v5-r2 derivative missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==18
 originals={o.name:o for o in bpy.data.objects if o.type=="MESH"}
 assert len(originals)==42 and all(o.get("outrun_original_mesh_object_id") for o in originals.values())
 before={name:snapshot(o) for name,o in originals.items()}
 for name,(source,v,f,expected_sha) in TARGETS.items():
  b=before[name]
  assert (b["id"],b["verts"],b["faces"],b["mesh_sha256"])==(source,v,f,expected_sha),name
  assert b["pmt"]==PMT_SHA
 cameras={o.name:(tuple(round(float(v),9) for row in o.matrix_world for v in row),o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA"}
 views=[
 ("GAUGE","QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"]),
 ("STEERING","QA_F50_STEERING_LOCAL_NON_GAME",["PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"])]
 renders={}
 for label,camera,objects in views:
  renders["before_"+label]=render(scene,a.render_root,"BEFORE_"+label,camera,objects)
 changes={}
 for name,func in zip(TARGETS,(sculpt_original_hood,sculpt_original_wheel,sculpt_original_hub)):
  moved,depth=func(originals[name])
  assert moved>150 and depth>(.0002 if 'group00_material000' in name else .0005),(name,moved,depth)
  changes[name]={"moved_vertices":moved,"max_local_deformation_m":round(depth,8)}
 after={name:snapshot(o) for name,o in originals.items()}
 for name in before:
  b,c=before[name],after[name]
  assert b["id"]==c["id"] and b["pmt"]==c["pmt"]==PMT_SHA
  assert (b["verts"],b["faces"],b["matrix"],b["uv"],b["materials"],b["nonmanifold"])==(c["verts"],c["faces"],c["matrix"],c["uv"],c["materials"],c["nonmanifold"])
  if name not in TARGETS:assert b==c,"Outside original cockpit mesh unexpectedly edited: "+name
  else:assert b["mesh_sha256"]!=c["mesh_sha256"],name
 assert all(cameras[o.name]==(tuple(round(float(v),9) for row in o.matrix_world for v in row),o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA")
 scene["geometry_edit_count"]=21
 scene["slot_c_last_geometry_stage"]="F50_P0_V7_SOURCE_COWL_TWIN_RECESS_WHEEL_ARM_HUB_COLLAR"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V7_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v6_blend_sha256":INPUT_SHA,"new_private_v7_blend_path":str(a.output),
 "new_private_v7_blend_sha256":sha(a.output),
 "original_source_meshes":42,"changed_original_source_meshes":{
  n:{"original_id":before[n]["id"],"before":before[n],"after":after[n],"deformation":changes[n]} for n in TARGETS},
 "untouched_other_original_source_meshes":39,"all_42_original_ids_preserved":True,
 "unchanged_object_camera_transforms":True,"unchanged_UV_materials":True,
 "source_pmt_untouched":True,"source_geometry_nonmanifold_unchanged":True,
 "paired_real_blender_render":renders,
 "photo_reference":"03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg",
 "photo_use":"qualitative morphology only; no game-calibrated driver-eye",
 "full_7_photo_view_match":"INCOMPLETE","native_driver_eye":"UNVERIFIED",
 "github_hosted_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
 "new_car_objects":0,"external_body_wheels_tires_edit":False,
 "created_textures_PBR_normal_maps":False,"game_export_PMT_OVC_OVC3":False,"VR_Model2_Dino_slotA_change":False,
 "complete":False}
 a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V7_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v7_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()