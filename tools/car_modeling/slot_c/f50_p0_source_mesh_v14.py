#!/usr/bin/env python3
"""F50 Slot C P0 v14: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires the exact read-only original PMT and verified first import, then edits the immutable v13 source-derived .blend.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="ef53e2b4be0e80237eb44bdd01695e1bb785e4654abba4bf9f936559ebc3180d"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"a0d6213dad3ca609eb074b7b2903c5aec2a3291845503bfc467fda7450826169"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"c4294f4adbedc292b9d08b820ca244027ffb92e80db6e4274e75a6996ec50478"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"5a143c5d7e077ee262b98dd15ed653583f06b7685230a89776b9438f49c586a3")}
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

def smooth_existing_z(o,weight,rounds=2):
 """Smooth pre-existing source mesh z along authentic edges, never add geometry."""
 me=o.data
 adj=[[] for v in me.vertices]
 for e in me.edges:
  a,b=e.vertices
  adj[a].append(b);adj[b].append(a)
 for _ in range(rounds):
  old=[float(v.co.z) for v in me.vertices]
  new={}
  for i,v in enumerate(me.vertices):
   w=weight(v.co)
   if w>1.e-5 and adj[i]:
    new[i]=old[i]+w*(sum(old[j] for j in adj[i])/len(adj[i])-old[i])
  for i,z in new.items():me.vertices[i].co.z=z
 me.update()

def sculpt_original_hood(o):
 """Reform ONLY the inherited F50 original instrument-panel mesh into the
  wide, single continuous dark instrument hood seen in the exact-model photo.
  Keep its source triangles, identifiers, UV, boundaries and dash location."""
 verts=o.data.vertices;before=[tuple(v.co) for v in verts]
 x0,x1=min(v.co.x for v in verts),max(v.co.x for v in verts)
 y0,y1=min(v.co.y for v in verts),max(v.co.y for v in verts)
 for v in verts:
  u=(v.co.x-x0)/max(1e-9,x1-x0)
  t=(v.co.y-y0)/max(1e-9,y1-y0)
  mask=window(u,.034,.966,.100)*window(t,.046,.955,.084)
  # The F50 has ONE continuous gauge-hood crown over a wide oval panel,
  # not two separately manufactured round binnacles.
  crown_t=.737-.058*(2*u-1)**2
  crown=math.exp(-((t-crown_t)/.032)**2)*math.exp(-((u-.50)/.43)**6)
  shadow_return=math.exp(-((t-(crown_t-.083))/.022)**2)*math.exp(-((u-.5)/.385)**6)
  gauge_field=math.exp(-((t-.485)/.111)**4)*math.exp(-((u-.5)/.315)**6)
  shoulder=(math.exp(-((u-.188)/.128)**2)+math.exp(-((u-.812)/.128)**2))*math.exp(-((t-.642)/.123)**2)
  center_control=math.exp(-((u-.50)/.078)**2)*math.exp(-((t-.56)/.107)**2)
  lower_return=math.exp(-((t-.316)/.019)**2)*math.exp(-((u-.5)/.41)**6)
  # Actual vertex displacement: physically shaped lip, undercut and molded return.
  v.co.z+=mask*(.00216*crown-.00125*shadow_return-.00126*gauge_field
               +.00074*shoulder+.00036*center_control+.00066*lower_return)
 def weight(co):
  u=(co.x-x0)/max(1e-9,x1-x0)
  t=(co.y-y0)/max(1e-9,y1-y0)
  return .10*window(u,.10,.90,.18)*window(t,.31,.80,.15)
 smooth_existing_z(o,weight,rounds=2)
 o.data.update()
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(verts,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(verts,before))
 o["source_edit_scope"]="F50 C v14 factory PMT molded one-piece oval instrument visor/crown, interior shade undercut and fascia return; original polygon mesh"
 return moved,delta

def sculpt_original_wheel(o):
 """Physically soften the native three-spoke F50 MOMO rim and pressings;
 never create a substitute wheel or change source wheel-space pivots."""
 verts=o.data.vertices;before=[tuple(v.co) for v in verts]
 def sector(a,ang,w):
  d=math.atan2(math.sin(ang-a),math.cos(ang-a))
  return math.exp(-(d/w)**2)
 for p in verts:
  x,y,z=p.co;r=math.hypot(x,y)
  if r<1e-10:continue
  a=math.atan2(y,x)
  ten_two=sector(math.pi*.78,a,.23)+sector(math.pi*.22,a,.23)
  lower=sector(-math.pi/2,a,.22)
  # Existing source rim is faceted: nudge vertices on its original rim
  # radially toward the round F50 wheel profile, retaining native seam.
  rim=math.exp(-((r-.153)/.019)**4)
  face=window(z,-.015,.024,.009)
  dr=.19*(.1575-r)*rim*(.18+.82*face)
  dr+=.00138*ten_two*rim*face + .00048*lower*rim*face
  bulge=math.exp(-((r-.147)/.012)**2)
  outer=math.exp(-((r-.165)/.010)**2)
  dz=ten_two*(.00156*bulge-.00038*outer)*face
  dz+=.00089*lower*rim*face
  # Flattened metal horizontal 9/3 arms and broader continuous 6 o'clock web;
  # native openings remain open and the hub anchor stays stationary.
  arm=math.exp(-((abs(x)-.104)/.036)**4)*math.exp(-((y+.018)/.029)**4)
  edge_roll=math.exp(-((abs(x)-.137)/.010)**2)*math.exp(-((y+.019)/.025)**2)
  lower_web=math.exp(-(x/.037)**4)*math.exp(-((y+.103)/.038)**4)
  web_edges=math.exp(-((abs(x)-.030)/.009)**2)*math.exp(-((y+.108)/.028)**2)
  dz+=(.00244*arm-.00055*edge_roll+.00170*lower_web-.00047*web_edges)*(.20+.80*face)
  # Source-formed 3-spoke inner shoulders from hub into rim.
  root=math.exp(-((r-.072)/.025)**2)*math.exp(-((abs(y)-.028)/.045)**2)
  dz+=.00072*root*face
  p.co.x+=dr*x/r;p.co.y+=dr*y/r;p.co.z+=dz
 o.data.update()
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(verts,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(verts,before))
 o["source_edit_scope"]="F50 C v14 original MOMO 3-spoke ring radial rounding, 10/2 grip, 9/3 pressed arms and lower web; source holes and animation pivot retained"
 return moved,delta

def sculpt_original_hub(o):
 """Use only original hub vertices to shape OEM round horn-button seat,
 rolled counterbore and six fastener lands: no texture or emblem insertion."""
 verts=o.data.vertices;before=[tuple(v.co) for v in verts]
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 for p in verts:
  x,y,z=p.co;r=math.hypot(x,y+.019)
  face=window(z,-.003,.012,.0043)
  horn=math.exp(-(r/.0205)**6)
  outer_seat=math.exp(-((r-.0285)/.0065)**2)
  counterbore=math.exp(-((r-.042)/.006)**2)
  shoulder=math.exp(-((r-.059)/.009)**2)
  dz=(.00111*horn+.00104*outer_seat-.00068*counterbore+.00037*shoulder)
  for cx,cy in centers:
   d=math.hypot(x-cx,y-cy)
   dz+=-.00042*math.exp(-(d/.0065)**2)+.00025*math.exp(-((d-.0125)/.0045)**2)
  p.co.z+=dz*face
 o.data.update()
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(verts,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(verts,before))
 o["source_edit_scope"]="F50 C v14 actual original hub horn-seat elevation, six counterbored fastener land relief, no invented badge"
 return moved,delta

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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified v9 original-derived Blender input missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==39
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
 scene["geometry_edit_count"]=42
 scene["slot_c_last_geometry_stage"]="F50_P0_V14_ORIGINAL_COWL_OVAL_VISOR_SPOKE_WEB_HUB_STEP"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V14_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v13_blend_sha256":INPUT_SHA,"new_private_v14_blend_path":str(a.output),
 "new_private_v14_blend_sha256":sha(a.output),
 "original_source_meshes":42,"changed_original_source_meshes":{
  n:{"original_id":before[n]["id"],"before":before[n],"after":after[n],"deformation":changes[n]} for n in TARGETS},
 "untouched_other_original_source_meshes":39,"all_42_original_ids_preserved":True,
 "unchanged_object_camera_transforms":True,"unchanged_UV_materials":True,
 "source_pmt_untouched":True,"source_geometry_nonmanifold_unchanged":True,
 "paired_real_blender_render":renders,
 "photo_reference":["03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg","03_F50/01_interior.jpg","03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg"],
 "photo_use":"qualitative morphology only; no game-calibrated driver-eye",
 "full_7_photo_view_match":"INCOMPLETE","native_driver_eye":"UNVERIFIED",
 "github_hosted_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
 "new_car_objects":0,"external_body_wheels_tires_edit":False,
 "created_textures_PBR_normal_maps":False,"game_export_PMT_OVC_OVC3":False,"VR_Model2_Dino_slotA_change":False,
 "complete":False}
 a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V14_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v14_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()