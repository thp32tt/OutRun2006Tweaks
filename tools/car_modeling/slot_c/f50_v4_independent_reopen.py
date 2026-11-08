#!/usr/bin/env python3
"""Ferrari F50 v4 exact-source independent Blender reopen/mesh audit. Only private .blend inputs."""
import bpy,bmesh,hashlib,struct,json,sys,argparse
from pathlib import Path
NATIVE="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
BASE="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V3="46f7e420e10701d410137114a15bd86598c05db01fbe51e83ced719803447438"
TARGETS={
 "PMT_F50_object00_group01_material028_a0",
 "PMT_F50_object21_group01_material002_a0",
 "PMT_F50_object21_group00_material000_a0"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sig(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for p in me.polygons:
  h.update(struct.pack("<I",len(p.vertices)))
  for i in p.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()
def snapshots():
 ret={}
 for o in bpy.data.objects:
  if o.type!="MESH":continue
  bm=bmesh.new();bm.from_mesh(o.data);nm=sum(not e.is_manifold for e in bm.edges);bm.free()
  ret[o.name]={"source_id":o.get("outrun_original_mesh_object_id"),"pmt":o.get("outrun_original_game_resource_sha256"),
   "sha":sig(o.data),"v":len(o.data.vertices),"f":len(o.data.polygons),
   "nonmanifold":nm,"uv":len(o.data.uv_layers),"materials":len(o.data.materials),
   "matrix":[round(float(v),9) for row in o.matrix_world for v in row]}
 return ret
def cams():
 return {o.name:(tuple(round(float(v),9) for row in o.matrix_world for v in row),
  o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA"}
def independently_render(root):
 sc=bpy.context.scene
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 ec=sc.render.engine;cam=sc.camera;rp=sc.render.filepath;res=(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage)
 try:
  sc.render.engine="BLENDER_WORKBENCH"
  sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=800,560,100
  sc.camera=bpy.data.objects["QA_F50_STEERING_LOCAL_NON_GAME"]
  kept={"PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"}
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in kept
  sc.render.image_settings.file_format="PNG"
  sc.render.filepath=str(root)+".png"
  bpy.ops.render.render(write_still=True)
  return {"path":str(root)+".png","sha256":sha(str(root)+".png")}
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  sc.render.engine=ec;sc.camera=cam;sc.render.filepath=rp
  sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=res

def run():
 pa=argparse.ArgumentParser()
 for k in ("native","original-import","before","after","delta","audit","render-root"):
  pa.add_argument("--"+k,required=True,type=Path)
 a=pa.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15)
 assert sha(a.native)==NATIVE and sha(a.original_import)==BASE and sha(a.before)==V3
 d=json.loads(a.delta.read_text(encoding="utf8"))
 assert sha(a.after)==d["private_output_sha256"] and Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert not a.audit.exists()
 after=snapshots();c_after=cams()
 assert len(after)==42 and bpy.context.scene.get("geometry_edit_count")==12
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=snapshots();c_before=cams()
 assert len(before)==42 and set(before)==set(after) and c_before==c_after
 for n in before:
  b,t=before[n],after[n]
  assert b["source_id"]==t["source_id"] and b["pmt"]==t["pmt"]==NATIVE
  assert b["matrix"]==t["matrix"] and b["uv"]==t["uv"] and b["materials"]==t["materials"]
  if n not in TARGETS:assert b==t,"Other car geometry changed: "+n
  else:
   assert b["sha"]!=t["sha"],"Expected real material geometry delta: "+n
   q=d["modified_original_meshes"][n]
   assert b["sha"]==q["before"]["geometry_sha"] and t["sha"]==q["after"]["geometry_sha"]
   assert b["v"]==q["before"]["verts"] and t["v"]==q["after"]["verts"]
   assert b["f"]==q["before"]["faces"] and t["f"]==q["after"]["faces"]
 assert after["PMT_F50_object00_group01_material028_a0"]["nonmanifold"]==0
 assert after["PMT_F50_object21_group00_material000_a0"]["nonmanifold"]==0
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert snapshots()==after and cams()==c_after and bpy.context.scene.get("geometry_edit_count")==12
 out=independently_render(a.render_root)
 assert sha(a.native)==NATIVE and sha(a.original_import)==BASE and sha(a.before)==V3 and sha(a.after)==d["private_output_sha256"]
 audit={"status":"F50_SLOTC_V4_REAL_ORIGINAL_SCENE_INDEPENDENT_FRESH_REOPEN_PASS",
  "blender":bpy.app.version_string,"native_pmt_sha256":NATIVE,
  "original_import_sha256":BASE,"previous_blend_sha256":V3,"v4_blend_sha256":sha(a.after),
  "original_source_meshes":42,"modified_meshes":[before[n]["source_id"] for n in sorted(TARGETS)],
  "unchanged_original_meshes":39,
  "mesh_dimensions":{n:{"before":[before[n]["v"],before[n]["f"]],"after":[after[n]["v"],after[n]["f"]],
   "nonmanifold_before":before[n]["nonmanifold"],"nonmanifold_after":after[n]["nonmanifold"]} for n in sorted(TARGETS)},
  "untouched_other_39_bytewise_geom_hashes":True,
  "camera_matrix_unchanged":True,"object_matrix_unchanged":True,"uv_channels_preserved":True,
  "materials_preserved":True,"original_resource_unchanged":True,
  "independent_reopen_render":out,
  "photo_7view":"INCOMPLETE","game_driver_eye":"UNVERIFIED",
  "github_actions_private_original_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "vehicle_complete":False}
 a.audit.write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V4_FRESH_REOPEN_42_OF_42_PASS",audit["v4_blend_sha256"],audit["independent_reopen_render"])
if __name__=="__main__":run()