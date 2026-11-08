#!/usr/bin/env python3
"""Independent fresh-process official Blender 4.5.15 F50 v14 native source QA."""
import bpy,bmesh,struct,hashlib,json,sys,argparse
from pathlib import Path
PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
ORIG="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V13="ef53e2b4be0e80237eb44bdd01695e1bb785e4654abba4bf9f936559ebc3180d"
TARGETS={
 "PMT_F50_object00_group01_material028_a0",
 "PMT_F50_object21_group01_material002_a0",
 "PMT_F50_object21_group00_material000_a0"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_sig(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for f in me.polygons:
  h.update(struct.pack("<I",len(f.vertices)))
  for i in f.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()
def snap():
 result={}
 for o in bpy.data.objects:
  if o.type!="MESH":continue
  bm=bmesh.new();bm.from_mesh(o.data)
  nm=sum(not e.is_manifold for e in bm.edges);bm.free()
  result[o.name]={
   "id":o.get("outrun_original_mesh_object_id"),
   "pmt":o.get("outrun_original_game_resource_sha256"),
   "sha":mesh_sig(o.data),"v":len(o.data.vertices),"f":len(o.data.polygons),
   "nonmanifold":nm,"uv":len(o.data.uv_layers),"materials":len(o.data.materials),
   "smooth":all(p.use_smooth for p in o.data.polygons),
   "matrix":[round(float(v),9) for row in o.matrix_world for v in row]}
 return result
def cam_sig():
 return {o.name:(
  [round(float(v),9) for row in o.matrix_world for v in row],
  o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA"}
def render_local(path):
 sc=bpy.context.scene
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 cam=sc.camera;engine=sc.render.engine;rp=sc.render.filepath
 res=(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage)
 try:
  sc.camera=bpy.data.objects["QA_F50_STEERING_LOCAL_NON_GAME"]
  sc.render.engine="BLENDER_WORKBENCH"
  sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=800,560,100
  sc.render.image_settings.file_format="PNG"
  keep={"PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"}
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in keep
  sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
  assert path.is_file() and path.stat().st_size>10000
  return {"path":str(path),"sha256":sha(path)}
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  sc.camera=cam;sc.render.engine=engine;sc.render.filepath=rp
  sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=res
def run():
 p=argparse.ArgumentParser()
 for k in ("native","original-import","before","after","report","audit","independent-render"):
  p.add_argument("--"+k,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 assert sha(a.native)==PMT and sha(a.original_import)==ORIG and sha(a.before)==V13
 report=json.loads(a.report.read_text(encoding="utf8"))
 assert sha(a.after)==report["new_private_v14_blend_sha256"]
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==42
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
 after=snap();cam_after=cam_sig()
 assert len(after)==42 and all(item["id"] and item["pmt"]==PMT for item in after.values())
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=snap();cam_before=cam_sig()
 assert len(before)==42 and set(before)==set(after) and cam_before==cam_after
 for n in sorted(before):
  b,c=before[n],after[n]
  assert b["id"]==c["id"] and b["pmt"]==c["pmt"]==PMT
  assert b["matrix"]==c["matrix"]
  assert b["uv"]==c["uv"] and b["materials"]==c["materials"]
  assert (b["v"],b["f"],b["nonmanifold"])==(c["v"],c["f"],c["nonmanifold"])
  if n not in TARGETS:assert b==c,("Unexpected source mesh change",n)
  else:
   assert b["sha"]!=c["sha"],n
   d=report["changed_original_source_meshes"][n]
   assert b["sha"]==d["before"]["mesh_sha256"],n
   assert c["sha"]==d["after"]["mesh_sha256"],n
 assert sum(before[n]["sha"]!=after[n]["sha"] for n in before)==3
 assert sum(before[n]["sha"]==after[n]["sha"] for n in before)==39
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert snap()==after and cam_sig()==cam_after
 assert bpy.context.scene.get("geometry_edit_count")==42
 render=render_local(a.independent_render)
 assert sha(a.native)==PMT and sha(a.original_import)==ORIG and sha(a.before)==V13 and sha(a.after)==report["new_private_v14_blend_sha256"]
 assert not a.audit.exists()
 audit={
  "status":"PASS_F50_V14_PRIVATE_ORIGINAL_DERIVED_SCENE_FRESH_REOPEN_INDEPENDENT_RENDER",
  "blender_version":bpy.app.version_string,"native_pmt_sha256":PMT,"original_import_sha256":ORIG,
  "previous_v13_sha256":V13,"v14_sha256":sha(a.after),
  "original_source_meshes":42,"changed_original_meshes":sorted([before[n]["id"] for n in TARGETS]),
  "other_source_meshes_hash_identical":39,
  "geometry_deltas":{before[n]["id"]:{
    "before":[before[n]["v"],before[n]["f"]],"after":[after[n]["v"],after[n]["f"]],
    "nonmanifold_before_after":[before[n]["nonmanifold"],after[n]["nonmanifold"]],
    "mesh_sha_before":before[n]["sha"],"mesh_sha_after":after[n]["sha"]} for n in sorted(TARGETS)},
  "all_original_ids_transforms_cameras_uv_materials_preserved":True,
  "original_readonly_native_PMTSHA_stable":True,
  "independent_render":render,
  "driver_eye_game_camera":"UNVERIFIED","photo_7view_QA":"INCOMPLETE",
  "github_actions_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "complete":False}
 a.audit.write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V14_INDEPENDENT_FRESH_REOPEN_PASS",audit["v14_sha256"],render["sha256"])
if __name__=="__main__":run()