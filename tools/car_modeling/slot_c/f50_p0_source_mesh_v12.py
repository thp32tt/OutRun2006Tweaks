#!/usr/bin/env python3
"""F50 Slot C P0 v12: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires exact read-only original PMT, original Blender import, prior v9 native-derived .blend hashes.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="33edb2a2b3673847569c9bc321f8442148478e6a996d606fbd3f1bca27a69b9f"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"9ac1da17b864f5777cd58f1e712993bcb4dbb6aa9d5008b25a174bec5b420783"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"394253546d833cdf7eec608cc9d471913c9e82fce54c6c935658bb8152c2fee1"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"ee41fbb2cb9f5d64b68a9537932d508133de32e2251458578230b011c90c4486")}
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
 """F50 original binnacle: sculpt continuous hood shadow lip, twin instrument
 pockets, and outward tapered brows on EXISTING factory source triangles."""
 v=o.data.vertices
 before=[tuple(p.co) for p in v]
 x0,x1=min(p.co.x for p in v),max(p.co.x for p in v)
 y0,y1=min(p.co.y for p in v),max(p.co.y for p in v)
 for p in v:
  u=(p.co.x-x0)/max(1.e-9,x1-x0)
  t=(p.co.y-y0)/max(1.e-9,y1-y0)
  edge=window(u,.016,.984,.085)*window(t,.015,.985,.080)
  brow=.748-.076*(2*u-1)**2
  arch=math.exp(-((t-(brow+.016))/.045)**2)*math.exp(-((u-.5)/.44)**6)
  return_edge=math.exp(-((t-(brow-.078))/.027)**2)
  left=math.exp(-(((u-.342)/.177)**2+((t-.459)/.118)**2))
  right=math.exp(-(((u-.682)/.182)**2+((t-.458)/.117)**2))
  divider=math.exp(-((u-.510)/.062)**2)*math.exp(-((t-.531)/.110)**2)
  shoulders=(math.exp(-((u-.185)/.125)**2)+math.exp(-((u-.815)/.125)**2))*math.exp(-((t-.625)/.15)**2)
  # A 3D formed original F50 dash shell, not decals, bevel-only or a new object.
  gauge_ridge=math.exp(-((t-(brow-.028))/.029)**2)*math.exp(-((u-.5)/.41)**6)
  lower_fascia=math.exp(-((t-.318)/.031)**2)*(math.exp(-((u-.33)/.20)**4)+math.exp(-((u-.68)/.20)**4))
  # Strengthen the source-formed F50 double instrument recess and curved eyebrow.
  p.co.z+=edge*(.00320*arch-.00182*return_edge-.00168*(left+right)+.00137*divider+.00112*shoulders+.00070*gauge_ridge-.00046*lower_fascia)
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(v,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(v,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v12 native dash visor: molded shadow brow, return edge, dual gauge pockets, central divider; original topology preserved"
 return moved,delta

def sculpt_original_wheel(o):
 """Reprofile the ACTUAL source 3-spoke steering rim and pressed arm shoulders
 using photograph-visible structure; preserve native outer seam and wheel pivot."""
 verts=o.data.vertices
 before=[tuple(p.co) for p in verts]
 for p in verts:
  x,y,z=p.co
  r=math.hypot(x,y)
  if r<1e-9:continue
  ang=math.atan2(y,x)
  def sector(a,w):
   d=math.atan2(math.sin(ang-a),math.cos(ang-a))
   return math.exp(-(d/w)**2)
  upper=sector(.78*math.pi,.18)+sector(.22*math.pi,.18)
  bottom=sector(-math.pi/2,.20)
  rim=math.exp(-((r-.153)/.018)**4)
  shoulder=math.exp(-((r-.134)/.020)**2)
  face=window(z,-.014,.023,.011)
  # v12 deepens photo-visible physical 3-spoke pressings on the real original wheel.
  # Existing leather rim's raised 10/2 grip and subtle lower rolled segment.
  dr=(.00204*upper+.00076*bottom)*rim*(.22+.78*face)
  dz=(.00231*upper+.00110*bottom)*rim*(.25+.75*face)
  dz+=.00061*upper*shoulder*face
  # Three native arms: two horizontal metallic shoulders and a continuous
  # six-o'clock web. Do NOT insert, delete or move animation-anchored objects.
  side=math.exp(-((abs(x)-.100)/.036)**4)*math.exp(-((y+.024)/.033)**4)
  fold=math.exp(-((abs(x)-.126)/.011)**2)*math.exp(-((y+.021)/.034)**2)
  low=math.exp(-(x/.027)**4)*math.exp(-((y+.107)/.037)**4)
  lowfold=math.exp(-((abs(x)-.023)/.011)**2)*math.exp(-((y+.113)/.032)**2)
  dz+=(.00294*side-.00069*fold+.00205*low-.00057*lowfold)*(.20+.80*face)
  # Reinforce smooth source-derived spoke-hub transition, without an
  # invented badge or visual texture.
  inner=math.exp(-((r-.063)/.023)**2)*math.exp(-((abs(y)-.030)/.040)**2)
  dz+=.00087*inner*face
  # Roll a leather grip at the 10 and 2 o'clock contact arcs, on factory vertices.
  dz+=.00036*upper*math.exp(-((r-.144)/.010)**2)*face
  p.co.x+=dr*x/r
  p.co.y+=dr*y/r
  p.co.z+=dz
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(verts,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(verts,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v12 photo-shaped factory three-spoke rim, upper grip, lateral pressings, 6-o'clock web, hub transition; no fabricated mesh"
 return moved,delta

def sculpt_original_hub(o):
 """On the factory F50 hub ONLY, relieve the original central cup, six bolt
 lands and stepped rim, never synthesize badge or replace the source part."""
 verts=o.data.vertices
 before=[tuple(p.co) for p in verts]
 centers=[(.048*math.cos(math.radians(a)),-.019+.048*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 for p in verts:
  x,y,z=p.co
  r=math.hypot(x,y+.019)
  dz=(-.00106*math.exp(-(r/.019)**4)
       +.00149*math.exp(-((r-.032)/.008)**2)
       -.00051*math.exp(-((r-.044)/.0055)**2)
       +.00035*math.exp(-((r-.060)/.013)**2))
  for cx,cy in centers:
   dist=math.hypot(x-cx,y-cy)
   dz+=-.00037*math.exp(-(dist/.008)**2)+.00029*math.exp(-((dist-.014)/.005)**2)
  # Six authentic source-surface fastener lands and hub step: geometric only.
  p.co.z+=dz*window(z,-.0027,.012,.0045)
 moved=sum(math.dist(tuple(p.co),old)>1e-6 for p,old in zip(verts,before))
 delta=max(math.dist(tuple(p.co),old) for p,old in zip(verts,before))
 o.data.update()
 o["source_edit_scope"]="F50 Slot C v12 original metal hub circular step/cup and six shallow factory bolt lands; no new geometry objects"
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
 assert scene.get("geometry_edit_count")==33
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
 scene["geometry_edit_count"]=36
 scene["slot_c_last_geometry_stage"]="F50_P0_V12_SOURCE_COWL_TWIN_RECESS_WHEEL_ARM_HUB_COLLAR"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V12_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v11_blend_sha256":INPUT_SHA,"new_private_v12_blend_path":str(a.output),
 "new_private_v12_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V12_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v12_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()