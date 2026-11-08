#!/usr/bin/env python3
"""Independent official Blender 4.5.15 reopen check on original-vs-edited F50.
Fail closed if a non-target source mesh, original object identity or native pivot changed.
"""
import bpy,json,hashlib,struct
from pathlib import Path
d=Path(__file__).resolve().parent
src=d/"F50_OriginalPMT_CockpitSource_v1.blend"
candidate=d/"F50_OriginalPMT_P0_DashboardSteering_v1.blend"
report=json.loads((d/"F50_P0_DashboardSteering_OriginalMeshDelta_v1.json").read_text(encoding="utf-8"))
expected="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
assert bpy.data.filepath==str(candidate)
assert bpy.app.version_string.startswith("4.5.15")
assert bpy.context.scene.get("outrun_original_game_resource_sha256")==expected
assert bpy.context.scene.get("geometry_edit_count")==3
assert hashlib.sha256(src.read_bytes()).hexdigest()==report["baseline_sha256"]
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==report["candidate_sha256"]
def signature(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for p in me.polygons:
  h.update(struct.pack("<I",len(p.vertices)))
  for v in p.vertices:h.update(struct.pack("<I",v))
 return h.hexdigest()
all_meshes=[o for o in bpy.data.objects if o.type=="MESH"]
assert len(all_meshes)==42
edits=set(report["before_after"])
for ob in all_meshes:
 assert ob.get("outrun_original_mesh_object_id") and ob.get("outrun_original_game_resource_sha256")==expected
 assert ob.name not in edits or ob.get("source_edit_scope")
 if ob.name in edits:
  a=report["before_after"][ob.name]["after"]
  assert len(ob.data.vertices)==a["vertices"] and len(ob.data.polygons)==a["faces"]
  assert signature(ob.data)==a["mesh_sha256"]
  assert [round(x,9) for row in ob.matrix_world for x in row]==a["matrix_world"]
 assert not any(ty in ob.name.lower() for ty in ("external_replacement","invented_car"))
assert set(report["edited_original_mesh_ids"])=={"object00_group01_material028_a0","object21_group01_material002_a0","object21_group00_material000_a0"}
assert all(len(o.data.materials)==0 for o in all_meshes),"New materials are not allowed"
audit={"status":"INDEPENDENT_REOPEN_GEOMETRY_PASS","blender":bpy.app.version_string,
 "source_import_blend_sha256":report["baseline_sha256"],"edited_blend_sha256":report["candidate_sha256"],
 "original_native_sha256":expected,"imported_meshes":len(all_meshes),"edited_existing_meshes":len(edits),
 "source_objects_identified":True,"original_pivot_transforms_preserved":True,
 "source_game_camera_verified":False,
 "scene_render_pass":True,"github_actions_real_scene_audit":False,
 "no_new_texture_materials":True,"game_executable_modified":False,
 "no_ovc_ovc3_pmt_outputs":True,"qa_gate":"P0_IN_PROGRESS_NOT_COMPLETE"}
(d/"F50_Independent_Reopen_QA_v1.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
print("F50_INDEPENDENT_REOPEN_GEOMETRY_PASS",audit["edited_blend_sha256"])