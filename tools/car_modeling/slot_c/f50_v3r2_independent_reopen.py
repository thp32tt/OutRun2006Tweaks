#!/usr/bin/env python3
"""Private original-derived F50 v3r2 independent fresh process Blender QA (read-only .blends)."""
import bpy,hashlib,json,struct,sys,argparse
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_sig(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for p in me.polygons:
  h.update(struct.pack("<I",len(p.vertices)))
  for idx in p.vertices:h.update(struct.pack("<I",idx))
 return h.hexdigest()
def all_snapshots():
 return {o.name:{
 "sha":mesh_sig(o.data),"original_id":o.get("outrun_original_mesh_object_id"),
 "source_pmt_sha":o.get("outrun_original_game_resource_sha256"),
 "v":len(o.data.vertices),"f":len(o.data.polygons),
 "uv":len(o.data.uv_layers),"materials":len(o.data.materials),
 "matrix_world":[round(float(v),9) for row in o.matrix_world for v in row],
 "all_smooth":all(f.use_smooth for f in o.data.polygons),
 } for o in bpy.data.objects if o.type=="MESH"}
def cameras():
 return {o.name:(
 tuple(round(float(v),9) for row in o.matrix_world for v in row),
 o.data.type,float(o.data.lens)) for o in bpy.data.objects if o.type=="CAMERA"}
def run():
 p=argparse.ArgumentParser()
 for x in ("native","original-import","before","after","delta","output-audit"):
  p.add_argument("--"+x,type=Path,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15)
 assert sha(a.native)=="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
 assert sha(a.original_import)=="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
 assert sha(a.before)=="381326a1b3bfbe598bd744abc19c53aeb6140895fe9e9a095f677ecf49defb53"
 report=json.loads(a.delta.read_text())
 assert sha(a.after)==report["after_blend_sha256"]
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==9
 after=all_snapshots()
 cams_after=cameras()
 assert len(after)==42
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=all_snapshots()
 cams_before=cameras()
 assert len(before)==42 and set(before)==set(after)
 assert cams_after==cams_before
 targets=set(report["before_after"].keys())
 changed=[]
 for name in before:
  b,c=before[name],after[name]
  assert b["original_id"]==c["original_id"]
  assert b["source_pmt_sha"]==c["source_pmt_sha"]=="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
  assert b["matrix_world"]==c["matrix_world"]
  assert b["materials"]==c["materials"]==0
  assert b["uv"]==c["uv"]
  if name not in targets:assert b==c,name
  else:
   assert b["sha"]!=c["sha"],name
   d=report["before_after"][name]
   assert b["sha"]==d["before"]["mesh_sha256"]
   assert c["sha"]==d["after"]["mesh_sha256"]
   assert (c["v"],c["f"])==(d["after"]["verts"],d["after"]["faces"])
   changed.append(name)
 assert len(changed)==3 and len(before)-len(changed)==39
 assert len([n for n in after if "NEW" in n or "GLB" in n])==0
 assert set(changed)=={
  "PMT_F50_object00_group01_material028_a0",
  "PMT_F50_object21_group01_material002_a0",
  "PMT_F50_object21_group00_material000_a0"}
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert all_snapshots()==after
 assert sha(a.native)=="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
 for n in ("F50_SlotC_P0_v3_r2_GAUGE_QA_NON_GAME.png","F50_SlotC_P0_v3_r2_STEERING_QA_NON_GAME.png"):
  assert (a.after.parent/n).stat().st_size>10000
 assert not a.output_audit.exists()
 audit={
  "status":"REAL_SCENE_F50_SLOTC_V3R2_INDEPENDENT_REOPEN_PASS_NOT_COMPLETE",
  "source_car":"Ferrari F50","blender":bpy.app.version_string,
  "native_resource_sha256":sha(a.native),"original_import_sha256":sha(a.original_import),
  "previous_v2_sha256":sha(a.before),"new_v3_r2_sha256":sha(a.after),
  "source_meshes":42,"changed_original_meshes":[after[n]["original_id"] for n in changed],
  "untouched_source_meshes":39,"source_to_candidate_transform_equal":True,
  "diagnostic_camera_equal":True,"no_new_materials_uv_channels":True,
  "no_game_exports":True,"source_unchanged":True,"no_model_glb_replacement":True,
  "driver_eye_game_camera":"UNVERIFIED","photo_7_views":"UNTESTED",
  "github_actions_real_private_scene":"BLOCKED_PRIVATE_BLEND_NOT_DELIVERED",
  "24h_window":"NOT_EXPIRED","complete":False}
 a.output_audit.write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOT_C_V3R2_REOPEN_42_OF_42_PASS",sha(a.after),[after[n]["original_id"] for n in changed])
if __name__=="__main__":run()