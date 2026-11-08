#!/usr/bin/env python3
"""v8.23 source-only AST/compile and required physical guards (not Blender)."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
names=("blender_daytona365_v8_23_spoke_bridges_pbr.py",
 "verify_daytona365_v8_23_blender.py",
 "render_daytona365_v8_23_actual.py",
 "make_daytona365_v8_23_actual_compare.py",
 "render_daytona365_v8_23_spoke_isolated_actual.py",
 "make_daytona365_v8_23_spoke_detail_compare.py")
src={}
for name in names:
 p=ROOT/name
 assert p.exists(),name
 content=p.read_text(encoding="utf-8")
 ast.parse(content,filename=name)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/"test.pyc"),doraise=True)
 assert "OR2006C2C.EXE" not in content
 assert "bpy.ops.wm.open_mainfile(" not in content
 src[name]=content
model,verify,render,compare,detail,detail_compare=[src[n] for n in names]
guards=(
 "Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_23.blend",
 "30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437",
 "for p in (DST,NORMAL,MANIFEST):assert not p.exists()",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB",
 "V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",
 "V6_L_BLENDER_BLACK_FLOOR_MAT",
 "V6_R_BLENDER_BLACK_FLOOR_MAT",
 "V7_3_", "SHORT_CHROME_SPOKE_BRIDGE",
 '"LEFT","RIGHT","LOWER"',
 "STATIONS=14;AROUND=16",
 "len(verts)==224 and len(faces)==210",
 "all(len(e.link_faces)==2 for e in bm.edges)",
 "bmesh.ops.recalc_face_normals",
 "V8_23_Metric_Stamped_Spoke_UV",
 "V8_23_Aligned_Spoke_Tangent_Normal_UV",
 "V8_23_Source_Linked_Brushed_Spoke_Aluminum",
 "V8_23_Packed_Stamped_Spoke_Tangent_Normal",
 "V8_23_Spoke_Analytical_Normal_Map",
 "V8_BrushedMetalNormal",
 "img.pack()",
 "original_game_modified",
 "source_machined_metal_material_retained_procedural_bump",
 "for n,h in signature.items():assert mesh_sha(bpy.data.objects[n])==h,n",
 "bpy.ops.wm.save_as_mainfile(filepath=str(DST)",
 "DAYTONA_V8_23_MODEL_SAVED"
)
for t in guards:assert t in model,t
for t in ("DAYTONA_V8_23_FRESH_REOPEN_PASS",
 "bm.calc_volume(signed=True)",
 "len(mesh.vertices)==224",
 "all(len(e.link_faces)==2 for e in bm.edges)",
 "img.packed_file",
 "native_source_spoke_badge_rim_and_prior_meshes_preserved"):assert t in verify,t
for t in ("DAYTONA_V8_23_ACTUAL_CYCLES_PASS",
 "sc.render.resolution_x=480","sc.cycles.samples=4",
 "sc.render.threads=2","assert not out.exists()",
 "PREVIEW_ONLY"):assert t in render,t
for t in ("Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 "Daytona365_v8_22_r2_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_23_ACTUAL_CYCLES_PREVIEW.png",
 "photometric_equivalence","NOT_ESTABLISHED"):assert t in compare,t
for t in ("V823_TEMPORARY_STUDIO_DETAIL_CAMERA",
 "hide_render","bpy.ops.render.render",
 "TEMPORARY_STUDIO_WHEEL_DETAIL_NOT_ORIGINAL_CAMERA"):assert t in detail,t
for t in ("Daytona365_v8_22_r2_SPOKE_ISOLATED_ACTUAL_CYCLES.png",
 "Daytona365_v8_23_SPOKE_ISOLATED_ACTUAL_CYCLES.png",
 "studio_view_is_not_original_PMT_reference_camera",
 "DAYTONA_V8_23_REAL_SPOKE_DETAIL_COMPARE_PASS"):assert t in detail_compare,t
print("DAYTONA_V8_23_SOURCE_CONTRACT_PASS",len(guards),"model guards and six-file AST/compile, real Blender checked separately")