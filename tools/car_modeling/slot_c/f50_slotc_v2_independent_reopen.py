#!/usr/bin/env python3
"""Independent Blender 4.5.15 source-versus-v2 checkpoint QA. No save or game export."""
import bpy,hashlib,json,struct,sys
from pathlib import Path
import argparse
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snap():
 def sh(m):
  h=hashlib.sha256()
  for v in m.vertices:h.update(struct.pack("<3f",*v.co))
  for f in m.polygons:
   h.update(struct.pack("<I",len(f.vertices)))
   for i in f.vertices:h.update(struct.pack("<I",i))
  return h.hexdigest()
 return {o.name:{"hash":sh(o.data),"v":len(o.data.vertices),"f":len(o.data.polygons),
          "sourceid":o.get("outrun_original_mesh_object_id"),
          "world":[round(v,9) for row in o.matrix_world for v in row],
          "mats":len(o.data.materials)} for o in bpy.data.objects if o.type=="MESH"}
def cameras():
 return {o.name:([round(v,9) for row in o.matrix_world for v in row],
                 o.data.type,o.data.lens) for o in bpy.data.objects if o.type=="CAMERA"}
p=argparse.ArgumentParser()
for x in ("source-native","original-blend","baseline","candidate","delta","audit"):p.add_argument("--"+x,required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert bpy.app.version[:3]==(4,5,15)
assert digest(a.source_native)=="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
assert digest(a.original_blend)=="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
assert digest(a.baseline)=="b7289f9ec1d772f9beca1c785f63c3536e8c501aee8a9a5710b2b086b7152e6d"
report=json.loads(a.delta.read_text())
assert str(Path(bpy.data.filepath).resolve())==str(a.candidate.resolve())
assert digest(a.candidate)==report["output_blend_sha256"]
assert bpy.context.scene.get("geometry_edit_count")==6
after=snap(); cams_after=cameras()
assert len(after)==42
bpy.ops.wm.open_mainfile(filepath=str(a.baseline))
before=snap();cams_before=cameras()
assert len(before)==42 and before.keys()==after.keys() and cams_after==cams_before
changed=[n for n in before if before[n]["hash"]!=after[n]["hash"]]
expected=set(report["mesh_delta"].keys())
assert set(changed)==expected,(changed,expected)
for name in before:
 assert before[name]["sourceid"]==after[name]["sourceid"]
 assert before[name]["world"]==after[name]["world"]
 assert before[name]["mats"]==after[name]["mats"]==0
 if name not in expected:assert before[name]==after[name]
 else:
  rec=report["mesh_delta"][name]
  assert after[name]["hash"]==rec["after"]["mesh_sha256"]
  assert (after[name]["v"],after[name]["f"])==(rec["after"]["vertices"],rec["after"]["faces"])
  assert after[name]["v"]>before[name]["v"] and after[name]["f"]>before[name]["f"]
assert all((a.candidate.parent/("F50_SlotC_P0_v2_"+s+"_QA_NON_GAME.png")).stat().st_size>3000 for s in ("GAUGE","STEERING"))
bpy.ops.wm.open_mainfile(filepath=str(a.candidate))
assert snap()==after, "Independent reloaded final checkpoint not identical"
assert digest(a.source_native)=="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
audit={"status":"SLOT_C_F50_V2_REAL_PRIVATE_SCENE_INDEPENDENT_REOPEN_PASS",
       "blender":bpy.app.version_string,"pmtsz_sha":digest(a.source_native),
       "original_import_sha":digest(a.original_blend),"baseline_sha":digest(a.baseline),
       "v2_sha":digest(a.candidate),"original_meshes":42,
       "modified_source_mesh_ids":[after[n]["sourceid"] for n in changed],
       "unchanged_source_meshes":39,"camera_objects_unchanged":True,
       "native_game_driver_eye_verified":False,
       "github_actions_real_scene":False,
       "7_photo_view_QA":"UNTESTED",
       "all_materials_unchanged":True,
       "no_converted_exports":True,
       "24h_window_not_complete":True,
       "completed":False}
assert not a.audit.exists()
a.audit.write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf8")
print("SLOT_C_F50_V2_INDEPENDENT_REOPEN_PASS",audit["v2_sha"],audit["modified_source_mesh_ids"])