#!/usr/bin/env python3
"""Source-only QA for Ferrari16 slot A Daytona P0 original-derived Blender editing.

This is NOT a real-scene Blender/model QA pass. Real N100 private source file
hash, edited .blend save, independent fresh-open, and photo review are separate.
"""
from pathlib import Path
import ast,py_compile,tempfile
ROOT=Path(__file__).resolve().parent
files=("slotA_daytona_source_mesh_p0_r2.py",
       "slotA_verify_daytona_p0_r2.py",
       "slotA_render_driver_eye_r2.py")
text={}
for name in files:
 p=ROOT/name
 assert p.is_file(),name
 source=p.read_text(encoding="utf-8")
 ast.parse(source,filename=str(p))
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/"test.pyc"),doraise=True)
 text[name]=source
b,v,r=[text[name] for name in files]
guards=(
"obj_plcar_dayts_pmt.sz",
"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend",
"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend",
"30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437",
"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v1_r2.blend",
"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0",
"dashboard_n>=160",
"post_verts>61 and post_faces>31",
"badge_clearance=fade(.059,.084,math.hypot(p.x+.35,p.z-.792))",
"bmesh.ops.subdivide_edges",
"bmesh.ops.recalc_face_normals",
"all_protected",
"images_before",
"materials_before",
"curves_before",
"original_names",
"assert not OUT.exists() and not REP.exists()",
"bpy.ops.wm.save_as_mainfile",
"GLB_exported",
"OVC3_OVC_PMT_converted",
"game_runtime_changed",
"next_car_change_allowed")
for key in guards:assert key in b,key
for key in ("SLOTA_DAYTONA_P0_FRESH_REOPEN_PASS",
 "original_game_resource_sha256","original_import_blend_sha256",
 "source_dashboard_original_local_signature_matched",
 "qa_24hour","NOT_COMPLETED"):
 assert key in v,key
for key in ("SLOTA_DAYTONA_REAL_CYCLES_PREVIEW_PASS",
 "APPROX_LEFT_HAND_DRIVER_EYE_NOT_GAME_CAMERA",
 "new_blend_saved_during_render","samples"):
 assert key in r,key
for path in (b,v,r):
 for bad in ("bpy.ops.export_scene","bpy.ops.export_mesh",
 "bpy.ops.wm.read_factory_settings","bpy.ops.mesh.primitive_",
 "bpy.data.objects.new('CAR","bpy.ops.object.convert"):
  assert bad not in path,bad
print("SLOTA_DAYTONA_P0_SOURCE_CONTRACT_PASS",len(guards),"guards AST/compile; production real Blender verified separately")
# Subsequent r3 material rework is independently source-audited; private .blend
# and real Ferrari PMT are intentionally NOT in public GitHub Actions checkout.
r3path=ROOT/"slotA_daytona_p0_geometry_r3.py"
assert r3path.is_file()
r3=r3path.read_text(encoding="utf-8")
ast.parse(r3,filename=str(r3path))
with tempfile.TemporaryDirectory() as d:
 py_compile.compile(str(r3path),cfile=str(Path(d)/"r3.pyc"),doraise=True)
for guard in (
 "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v1_r2.blend",
 "0d388f558563c2e9a92c483d6e0bfa6260a357b078d3145b87b4d2e7e7433b30",
 "obj_plcar_dayts_pmt.sz",
 "f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend",
 "92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB",
 "assert not OUTPUT.exists() and not REPORT.exists()",
 "protected_original_meshes_unchanged",
 "original_object_ids_preserved",
 "bpy.ops.wm.save_as_mainfile",
 "PARTIAL_VARIANT_UNVERIFIED",
 "NEEDS_VISUAL_QA",
 "completed_24h",
):
 assert guard in r3,guard
for bad in ("bpy.ops.export_scene","bpy.ops.export_mesh",
 "bpy.ops.wm.read_factory_settings","bpy.ops.mesh.primitive_",
 "bpy.ops.object.convert", "bpy.data.objects.new("):
 assert bad not in r3,bad
print("SLOTA_DAYTONA_P0_R3_SOURCE_CONTRACT_PASS", "AST/compile and original-source/no-export guards only; private real-scene QA separate")
