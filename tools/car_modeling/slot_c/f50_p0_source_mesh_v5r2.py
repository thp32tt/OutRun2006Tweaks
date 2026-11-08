#!/usr/bin/env python3
"""F50 Slot C P0 v5r2: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires exact read-only original PMT, original Blender import, prior v4 .blend hashes.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="870ad1663837eabd391e6436c957b7f47b4c75868db9a4b448fc8d1d64bde8c8"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"f92ccb471c839c73399f46039180cd68cbe6817bfc9171cc42961db55b694226"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"b8f13ce582e5df8df58c01c0f59c29d8d5133e6cd336b74c4fdf036114e08dc4"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"dd60689b8c3f43a2b4519e81d77468ccdfefdd5508612db72250f723489afc26")}
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
 """Reprofile BOTH native original visor gauge pockets, kept inside existing source envelope."""
 vs=o.data.vertices
 xmin,xmax=min(v.co.x for v in vs),max(v.co.x for v in vs)
 ymin,ymax=min(v.co.y for v in vs),max(v.co.y for v in vs)
 moved=0;max_delta=0.
 for v in vs:
  u=(v.co.x-xmin)/max(xmax-xmin,1e-9)
  t=(v.co.y-ymin)/max(ymax-ymin,1e-9)
  arch=math.exp(-((t-(.71-.12*(2*u-1)**2))/.075)**2)
  left=math.exp(-(((u-.34)/.20)**4+((t-.43)/.17)**4))
  right=math.exp(-(((u-.70)/.20)**4+((t-.43)/.17)**4))
  inner_lip=math.exp(-((t-.28)/.075)**2)*math.exp(-((u-.52)/.42)**4)
  shoulder=math.exp(-((u-.13)/.08)**2)+math.exp(-((u-.87)/.08)**2)
  # Shield underside pockets and dual shoulder rises, not fabricated instrument faces.
  delta=.0018*arch-.0017*left-.0019*right+.0011*inner_lip+.0008*shoulder*arch
  guard=window(u,.02,.98,.095)*window(t,.04,.97,.095)
  dz=delta*guard
  if abs(dz)>1.0e-6:
   v.co.z+=dz;max_delta=max(max_delta,abs(dz));moved+=1
 o.data.update()
 o["source_edit_scope"]="F50 P0 v5r2 native instrument brow: two sculpted gauge recesses, continuous visor arch and inner lip in original material028 mesh"
 return moved,max_delta
def sculpt_original_wheel(o):
 """Reprofile photo-matched native 3-spoke arm transitions, rim palm thickness and thumb rests."""
 moved=0;max_delta=0.
 for v in o.data.vertices:
  x,y,z=v.co
  r=math.hypot(x,y)
  if r<1.e-8:continue
  ang=math.atan2(y,x)
  def grip(g):
   wrapped=math.atan2(math.sin(ang-g),math.cos(ang-g))
   return math.exp(-((wrapped)/.19)**2)
  upper=grip(.81*math.pi)+grip(.19*math.pi)
  base=grip(-math.pi/2)
  rim=math.exp(-((r-.147)/.018)**4)
  front=window(z,-.013,.019,.013)
  # Palm ergonomics: hand-contoured grippy cross section in the ALREADY imported wheel.
  radial=(.0017*upper+.00065*base)*rim*(.45+.55*front)
  dz=(.0020*upper+.0009*base)*rim*(.28+.72*front)
  # Existing lateral spoke roots: raised central rib with descending stamped margins.
  side=math.exp(-((abs(x)-.104)/.031)**4)*math.exp(-((y+.015)/.033)**4)
  lateral_outer=math.exp(-((abs(x)-.128)/.013)**2)*math.exp(-((y+.006)/.033)**2)
  lower=math.exp(-((x)/.027)**4)*math.exp(-((y+.105)/.034)**4)
  dz+=.0016*side*front+.00072*lower*front
  # Move original spoke-tip material toward original surrounding rim by <= 0.8mm.
  radial+=.00075*lateral_outer*(.2+.8*front)
  if abs(dz)>1e-6 or abs(radial)>1e-6:
   v.co.x+=radial*x/r
   v.co.y+=radial*y/r
   v.co.z+=dz
   moved+=1;max_delta=max(max_delta,abs(dz),abs(radial))
 for f in o.data.polygons:f.use_smooth=True
 o.data.update()
 o["source_edit_scope"]="F50 P0 v5r2 original wheel: two sculpted photo-matched thumb grips, rim leather thickening, 3-spoke root relief and tip contour"
 return moved,max_delta
def sculpt_original_hub(o):
 """Corrected v5r2: preserve smooth native original plate; very subtle six-fastener and cap relief."""
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 moved=0;max_delta=0
 for v in o.data.vertices:
  x,y,z=v.co
  radius=math.hypot(x,y+.019)
  # Broad, low amplitude analog shape: no tight quartic sharp dents / distorted alloy facets.
  cap=.00036*math.exp(-((radius)/.026)**2)
  ring=.00042*math.exp(-((radius-.027)/.009)**2)
  groove=-.00020*math.exp(-((radius-.038)/.011)**2)
  dz=cap+ring+groove
  for cx,cy in centers:
   rr=math.hypot(x-cx,y-cy)
   dz-=.00024*math.exp(-((rr)/.011)**2)
   dz+=.00014*math.exp(-((rr-.016)/.010)**2)
  front=max(.10,min(1.,(z+.0015)/.004))
  dz*=front
  if abs(dz)>1e-6:
   v.co.z+=dz
   moved+=1;max_delta=max(max_delta,abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 P0 v5r2 original hub: smooth subtle center cap/annular shoulder and six low-profile native fastener impressions"
 return moved,max_delta
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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified v4 derivative missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==12
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
 scene["geometry_edit_count"]=15
 scene["slot_c_last_geometry_stage"]="F50_P0_V5R2_NATIVE_BROW_THREE_SPOKE_HUB_CUPS"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V5R2_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v4_blend_sha256":INPUT_SHA,"new_private_v5_blend_path":str(a.output),
 "new_private_v5_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V5R2_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v5_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()