#!/usr/bin/env python3
"""F50 Slot C P0 v6: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires exact read-only original PMT, original Blender import, prior v4 .blend hashes.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="f2cd5ac7b41f67b0c7278b52eff8edf444a4d2a4e62c324371a6711190642e43"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"ba2dbe6871cf47750dd373926e1f9a661623b5d5e6f3217d8b51c7cd9be764f3"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"c51ddd8efca87030274a67f27d1f9518eb468151f0f953d56f65110c9c82d4c7"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"aa06aea5b9d56890fe6cc7fd0a8ee2cc225fb5a4e2124c9b6b8bad09fd06af01")}
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
 """F50's source cockpit cowl: form continuous raised eyebrow, asymmetric twin-dial recess
 and sharp lower return directly from existing game-derived manifold vertices."""
 vs=o.data.vertices
 xmin,xmax=min(v.co.x for v in vs),max(v.co.x for v in vs)
 ymin,ymax=min(v.co.y for v in vs),max(v.co.y for v in vs)
 moved=0;maximum=0.
 for v in vs:
  u=(v.co.x-xmin)/max(xmax-xmin,1e-9)
  t=(v.co.y-ymin)/max(ymax-ymin,1e-9)
  # The real F50 has a dark deeply hooded instrument panel and taut asymmetric brow,
  # not a generic symmetric double-gauge pod. Dimensions are qualitative/photo-guided.
  visor_center=.73-.085*(2*u-1)**2
  arch=math.exp(-((t-visor_center)/.090)**2)
  upper_lip=math.exp(-((t-(visor_center-.105))/.043)**2)
  rev_well=math.exp(-(((u-.355)/.205)**2+((t-.445)/.148)**2))
  speed_well=math.exp(-(((u-.710)/.169)**2+((t-.443)/.153)**2))
  middle_rib=math.exp(-((u-.528)/.063)**2)*math.exp(-((t-.455)/.164)**2)
  side_roll=math.exp(-((u-.145)/.095)**2)+math.exp(-((u-.875)/.095)**2)
  # Three-dimensional relief of the source hood (z), rather than a flat color/normal trick.
  dz=(.00345*arch+.00162*upper_lip-.00315*rev_well-.00265*speed_well
       +.00117*middle_rib+.00087*side_roll*arch)
  edge=window(u,.012,.988,.090)*window(t,.020,.984,.095)
  dz*=edge
  if abs(dz)>1.e-6:
   v.co.z+=dz;moved+=1;maximum=max(maximum,abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v6 genuine source visor: deeper separate tach/speed wells, sculpted upper dash eyebrow and formed inner return; no instrument decals"
 return moved,maximum
def sculpt_original_wheel(o):
 """Retain original F50 three-spoke topology and pivot; add photograph-guided
 physical palm swells, rim shoulder and pronounced stamped spoke web contours."""
 moved=0;max_delta=0.
 for v in o.data.vertices:
  x,y,z=v.co
  r=math.hypot(x,y)
  if r<1.e-8:continue
  a=math.atan2(y,x)
  def sector(theta,width):
   d=math.atan2(math.sin(a-theta),math.cos(a-theta))
   return math.exp(-(d/width)**2)
  palms=sector(.80*math.pi,.165)+sector(.20*math.pi,.165)
  six=sector(-math.pi/2,.135)
  outer=math.exp(-((r-.148)/.017)**4)
  fore=window(z,-.014,.019,.013)
  shoulder=math.exp(-((r-.131)/.017)**2)
  # Existing three-spoke web left/right with raised central ribs.
  bar=math.exp(-((abs(x)-.089)/.034)**4)*math.exp(-((y+.024)/.027)**4)
  outer_seam=math.exp(-((abs(x)-.123)/.009)**2)*math.exp(-((y+.020)/.027)**2)
  lower_web=math.exp(-((x/.030)**4))*math.exp(-((y+.102)/.037)**4)
  lower_edge=math.exp(-((abs(x)-.024)/.009)**2)*math.exp(-((y+.103)/.033)**2)
  radial=(.00185*palms+.00070*six)*outer*(.55+.45*fore)
  radial+=.00048*palms*shoulder
  dz=(.00245*palms+.00103*six)*outer*(.35+.65*fore)
  dz+=(.00170*bar-.00056*outer_seam+.00120*lower_web-.00044*lower_edge)*(.26+.74*fore)
  if abs(dz)>1e-6 or abs(radial)>1e-6:
   v.co.x+=radial*x/r;v.co.y+=radial*y/r;v.co.z+=dz
   moved+=1;max_delta=max(max_delta,abs(dz),abs(radial))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v6 actual source three-spoke: continuous stamped arm ribs and lowered edge seams, fuller 10/2 palm grips and six-o-clock rim thickness"
 return moved,max_delta
def sculpt_original_hub(o):
 """Shape native six-bolt steering center without sharp sculpt artifacts:
 low domed cap and six broad counterbore reliefs on existing hub vertices."""
 bolts=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 moved=0;max_delta=0.
 for v in o.data.vertices:
  x,y,z=v.co
  radius=math.hypot(x,y+.019)
  dome=.00091*math.exp(-((radius)/.030)**4)
  shoulder=.00068*math.exp(-((radius-.030)/.0085)**2)
  collar=-.00037*math.exp(-((radius-.040)/.008)**2)
  relief=dome+shoulder+collar
  for cx,cy in bolts:
   rr=math.hypot(x-cx,y-cy)
   # Wide and shallow: prevent rejected v5-style inverted fastener craters.
   relief-=.00036*math.exp(-((rr)/.0090)**2)
   relief+=.00023*math.exp(-((rr-.015)/.0080)**2)
  fore=max(.15,min(1.,(z+.0015)/.0045))
  dz=relief*fore
  if abs(dz)>1e-6:
   v.co.z+=dz;moved+=1;max_delta=max(max_delta,abs(dz))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v6 original hub: broad center cap surface, raised collar, shallow six-bolt counterbore relief; no badges or textures"
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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified v5-r2 derivative missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==15
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
 scene["geometry_edit_count"]=18
 scene["slot_c_last_geometry_stage"]="F50_P0_V6_ORIGINAL_TACH_BROW_THREESPOKE_HUB_PROFILE"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V6_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v5r2_blend_sha256":INPUT_SHA,"new_private_v6_blend_path":str(a.output),
 "new_private_v6_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V6_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v6_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()