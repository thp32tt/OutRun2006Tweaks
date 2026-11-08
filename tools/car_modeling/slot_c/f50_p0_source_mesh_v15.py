#!/usr/bin/env python3
"""F50 Slot C P0 v15: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires the exact read-only original PMT and verified first import, then edits the immutable v14 source-derived .blend.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="87cce97c87a15bb657599c5e2457a1c109658d58b65ec5488e8988b6e007c349"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"be562487b4102326f55f022f30bbc534f456df6f3cc8356a6a7430bb352260a7"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"e240a908071264d40aa77e7756bd5c9e87b19742caf46dd1c6a0820ea30ac2f0"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"fcb6a75ea4785b1c5453d362ac64facc98b99a2c7069b09257f2f4396f6dc63c")}
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
 """Edit only the existing original PMT dash/visor triangles to match F50
 photo: long unbroken instrument brow, broad shadow return, low fascia roll."""
 verts=o.data.vertices
 before=[tuple(v.co) for v in verts]
 x0,x1=min(v.co.x for v in verts),max(v.co.x for v in verts)
 y0,y1=min(v.co.y for v in verts),max(v.co.y for v in verts)
 for v in verts:
  u=(v.co.x-x0)/max(1e-9,x1-x0)
  t=(v.co.y-y0)/max(1e-9,y1-y0)
  mask=window(u,.035,.964,.093)*window(t,.045,.954,.080)
  arch=.733-.060*(2*u-1)**2
  # Continuous original dash roll: soften artifact-prone twin spikes.
  brow=math.exp(-((t-arch)/.034)**2)*math.exp(-((u-.5)/.432)**6)
  swept=math.exp(-((t-(arch-.080))/.022)**2)*math.exp(-((u-.5)/.37)**6)
  recess=math.exp(-((t-.484)/.125)**4)*math.exp(-((u-.5)/.31)**6)
  left=math.exp(-(((u-.290)/.125)**2+((t-.565)/.145)**2))
  right=math.exp(-(((u-.710)/.125)**2+((t-.565)/.145)**2))
  seam=math.exp(-((t-.313)/.019)**2)*math.exp(-((u-.5)/.40)**6)
  v.co.z+=mask*(.00171*brow-.00103*swept-.00106*recess+
               .00051*(left+right)+.00068*seam)
 # Genuine source-topology Laplacian, z-only and fade-to-zero at boundaries.
 # This reduces the sawtooth highlights of the inherited original cowl.
 def weight(co):
  u=(co.x-x0)/max(1e-9,x1-x0)
  t=(co.y-y0)/max(1e-9,y1-y0)
  arc=.74-.057*(2*u-1)**2
  w=window(u,.08,.92,.14)*window(t,.30,.82,.16)
  return .17*w*(.25+.75*math.exp(-((t-(arc-.035))/.16)**4))
 smooth_existing_z(o,weight,rounds=3)
 o.data.update()
 moved=sum(math.dist(tuple(v.co),old)>1e-6 for v,old in zip(verts,before))
 depth=max(math.dist(tuple(v.co),old) for v,old in zip(verts,before))
 o["source_edit_scope"]="F50 slot C v15 physical one-piece original dash brow smoothing/raised visor/undercut/gauge return; original PMT topology and object IDs"
 return moved,depth

def sculpt_original_wheel(o):
 """Retain the original F50 PMT 3-spoke object/rim opening topology; round
 original leather rim chord and improve its attached spoke ramps in place."""
 verts=o.data.vertices
 before=[tuple(v.co) for v in verts]
 def sector(ang,center,width):
  d=math.atan2(math.sin(ang-center),math.cos(ang-center))
  return math.exp(-(d/width)**4)
 for v in verts:
  x,y,z=v.co
  r=math.hypot(x,y)
  if r<1e-10:continue
  a=math.atan2(y,x)
  top=sector(a,math.pi/2,.49)
  lower=sector(a,-math.pi/2,.36)
  grip=sector(a,math.pi*.78,.27)+sector(a,math.pi*.22,.27)
  rim=math.exp(-((r-.153)/.022)**4)
  face=window(z,-.015,.023,.009)
  # Raise the center of existing chorded source rim, not a new perfect torus.
  # Keep leather ring thickness by moving the existing radial cross-section.
  dr=(.00235*top+.00113*grip+.00057*lower)*rim*(.45+.55*face)
  pfx=math.exp(-((r-.146)/.013)**2)
  pfout=math.exp(-((r-.168)/.009)**2)
  dz=(.00138*grip*pfx-.00040*grip*pfout+.00066*top*rim)*face
  # Original 9/3 flattened spoke ends: source-formed rolled shoulder.
  wings=math.exp(-((abs(x)-.108)/.037)**4)*math.exp(-((y+.018)/.031)**4)
  lip=math.exp(-((abs(x)-.139)/.011)**2)*math.exp(-((y+.017)/.028)**2)
  lower_web=math.exp(-(x/.039)**4)*math.exp(-((y+.111)/.035)**4)
  web_edge=math.exp(-((abs(x)-.032)/.011)**2)*math.exp(-((y+.114)/.029)**2)
  dz+=(.00209*wings-.00062*lip+.00178*lower_web-.00046*web_edge)*(.18+.82*face)
  # Only source vertices; no spoke-hole bridging or native steering-axis move.
  v.co.x+=dr*x/r;v.co.y+=dr*y/r;v.co.z+=dz
 o.data.update()
 moved=sum(math.dist(tuple(v.co),old)>1e-6 for v,old in zip(verts,before))
 depth=max(math.dist(tuple(v.co),old) for v,old in zip(verts,before))
 o["source_edit_scope"]="F50 slot C v15 native leather rim crown rounding, 10/2 contour, two factory side pressings, six-o-clock web; holes and source pivot preserved"
 return moved,depth

def sculpt_original_hub(o):
 """Original PMT steering hub/collar vertices only, no emblem/badge objects."""
 verts=o.data.vertices
 before=[tuple(v.co) for v in verts]
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 for v in verts:
  x,y,z=v.co
  r=math.hypot(x,y+.019)
  face=window(z,-.003,.0116,.004)
  # F50 source hub: physical circular horn button seat in metal three-spoke boss.
  dish=math.exp(-(r/.021)**6)
  horn_lip=math.exp(-((r-.030)/.0068)**2)
  countersink=math.exp(-((r-.042)/.0068)**2)
  outer=math.exp(-((r-.060)/.010)**2)
  dz=(.00127*dish+.00118*horn_lip-.00079*countersink+.00026*outer)
  for cx,cy in centers:
   d=math.hypot(x-cx,y-cy)
   dz+=-.00052*math.exp(-(d/.0068)**2)+.00022*math.exp(-((d-.013)/.0048)**2)
  v.co.z+=dz*face
 o.data.update()
 moved=sum(math.dist(tuple(v.co),old)>1e-6 for v,old in zip(verts,before))
 depth=max(math.dist(tuple(v.co),old) for v,old in zip(verts,before))
 o["source_edit_scope"]="F50 slot C v15 genuine source horn-button seat/bolt-counterbore geometric depth; not a fabricated badge or material"
 return moved,depth

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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified immutable v14 original-derived Blender input missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==42
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
 scene["geometry_edit_count"]=45
 scene["slot_c_last_geometry_stage"]="F50_P0_V15_ORIGINAL_VISOR_CROWN_RIM_CIRCLE_PHYSICAL_HUB"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V15_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v14_blend_sha256":INPUT_SHA,"new_private_v15_blend_path":str(a.output),
 "new_private_v15_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V15_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v15_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()