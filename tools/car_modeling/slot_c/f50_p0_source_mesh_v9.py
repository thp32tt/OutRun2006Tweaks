#!/usr/bin/env python3
"""F50 Slot C P0 v9: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires exact read-only original PMT, original Blender import, prior v6 native-derived .blend hashes.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="6895c0e155a823000303b8da4262d4539e131b07cf47e377a82c9316a97e4cea"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"074a723b0e2229f798f35e5c3c579f79461967d9e75312e8ba32f9508dbeaeb1"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"9315df69e58229abb81756b5746f3eca6500aaa86d8ab4f9805786b5fc25dcaa"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"ec15f701fcdf2c2756437c37416ce33d0507af07de08dd74bd1f41b45b28c05c")}
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
 """Photo-guided actual F50 instrument hood: continuously swept eyebrow,
 twin shallow gauge recesses and original lower light-blocking return."""
 v=o.data.vertices
 before=[tuple(p.co) for p in v]
 x0,x1=min(p.co.x for p in v),max(p.co.x for p in v)
 y0,y1=min(p.co.y for p in v),max(p.co.y for p in v)
 def uv(co):return (float((co.x-x0)/(x1-x0)),float((co.y-y0)/(y1-y0)))
 def gate(co):
  u,t=uv(co)
  return window(u,.018,.983,.093)*window(t,.018,.984,.091)
 smooth_existing_z(o,lambda co:.18*gate(co),2)
 for p in v:
  u,t=uv(p.co);arch=.745-.087*(2*u-1)**2
  upper=math.exp(-((t-(arch+.018))/.046)**2)*math.exp(-((u-.50)/.42)**6)
  return_lip=math.exp(-((t-(arch-.079))/.037)**2)
  left=math.exp(-(((u-.34)/.172)**2+((t-.449)/.13)**2))
  right=math.exp(-(((u-.69)/.181)**2+((t-.448)/.133)**2))
  center=math.exp(-((u-.52)/.064)**2)*math.exp(-((t-.53)/.115)**2)
  dz=(.00345*upper-.00215*return_lip-.00150*left
      -.00142*right+.00102*center)
  p.co.z+=dz*gate(p.co)
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(v,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(v,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v9 real original dashboard brow and gauge visor: smooth continuous upper sweep and lower molded instrument lip, no new object"
 return moved,delta

def sculpt_original_wheel(o):
 """Only original imported F50 3-spoke source wheel: stamped arm relief,
 smooth center pressing and shallow rim palm grip. Original radius/pivot kept."""
 v=o.data.vertices
 before=[tuple(p.co) for p in v]
 def w(co):
  r=math.hypot(co.x,co.y)
  return .23*window(r,.030,.141,.024)*window(co.z,-.014,.021,.008)
 smooth_existing_z(o,w,3)
 for p in v:
  x,y,z=p.co;r=math.hypot(x,y)
  if r<1e-8:continue
  ang=math.atan2(y,x)
  def sector(a,w):
   d=math.atan2(math.sin(ang-a),math.cos(ang-a))
   return math.exp(-(d/w)**2)
  palm=(sector(.79*math.pi,.17)+sector(.21*math.pi,.17))
  rim=math.exp(-((r-.153)/.016)**4)
  front=window(z,-.014,.022,.010)
  dr=.00116*palm*rim*(.22+.78*front)
  dz=.00184*palm*rim*(.18+.82*front)
  side=math.exp(-((abs(x)-.103)/.027)**4)*math.exp(-((y+.027)/.025)**4)
  side_fold=math.exp(-((abs(x)-.123)/.011)**2)*math.exp(-((y+.021)/.022)**2)
  lower=math.exp(-(x/.025)**4)*math.exp(-((y+.106)/.033)**4)
  lower_fold=math.exp(-((abs(x)-.022)/.009)**2)*math.exp(-((y+.102)/.026)**2)
  dz+=(.00200*side-.00048*side_fold+.00195*lower-.00044*lower_fold)*front
  pressing=math.exp(-(r/.059)**6)*window(z,-.008,.022,.009)
  dz+=.16*(.0085-z)*pressing
  p.co.x+=dr*x/r;p.co.y+=dr*y/r;p.co.z+=dz
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(v,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(v,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v9 genuine native 3-spoke wheel: smoother center pressing/rolled metal web edges and upper grip; preserve original 8 open boundary loops"
 return moved,delta

def sculpt_original_hub(o):
 """Existing native F50 six-fastener hub: original cup and bolt collar relief."""
 v=o.data.vertices
 before=[tuple(p.co) for p in v]
 smooth_existing_z(o,lambda co:.18*window(math.hypot(co.x,co.y+.019),0,.078,.018),2)
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 for p in v:
  x,y,z=p.co;rr=math.hypot(x,y+.019)
  dz=(-.00095*math.exp(-(rr/.019)**4)
       +.00115*math.exp(-((rr-.030)/.009)**2)
       -.00070*math.exp(-((rr-.041)/.005)**2)
       +.00039*math.exp(-((rr-.064)/.013)**2))
  for cx,cy in centers:
   d=math.hypot(x-cx,y-cy)
   dz-=.00036*math.exp(-(d/.009)**2)
   dz+=.00026*math.exp(-((d-.015)/.006)**2)
  p.co.z+=dz*window(z,-.0027,.011,.0045)
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(v,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(v,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v9 original metal hub: radially curved recessed cup and raised six-bolt source surface, no texture or replacement object"
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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified v5-r2 derivative missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==24
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
 scene["geometry_edit_count"]=27
 scene["slot_c_last_geometry_stage"]="F50_P0_V9_SOURCE_COWL_TWIN_RECESS_WHEEL_ARM_HUB_COLLAR"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V9_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v8_blend_sha256":INPUT_SHA,"new_private_v9_blend_path":str(a.output),
 "new_private_v9_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V9_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v9_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()