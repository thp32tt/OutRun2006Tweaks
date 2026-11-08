#!/usr/bin/env python3
"""v8.21-r2 source-only CI. Official Blender save/render audited separately."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=(
 "blender_daytona365_v8_21_source_hub_lower_shroud_r2.py",
 "verify_daytona365_v8_21_r2_blender.py",
 "render_daytona365_v8_21_r2_actual.py",
 "make_daytona365_v8_21_r2_actual_compare.py")
src={}
for name in FILES:
 p=ROOT/name
 assert p.is_file(),name
 content=p.read_text(encoding="utf-8")
 ast.parse(content,filename=name)
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(p),cfile=str(Path(temp)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in content
 assert "bpy.ops.wm.open_mainfile(" not in content
 src[name]=content
model,verify,render,compare=(src[name] for name in FILES)
guards=(
 "Daytona365_Cockpit_Blender_PBR_v8_20.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_21_r2.blend",
 "1c0244e4933b343647de2a8ec19e0ef68660cc9f4607f6208399176dd9380d5d",
 "for p in (DEST,NORMAL,MANIFEST):assert not p.exists()",
 "DAYTONA_V8_21_R2_BUILD_MANIFEST.json",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB",
 "V8_21_Source_Wheel_Hub_Tapered_Shaft",
 "V8_21_Hub_Metric_Tangent_UV",
 "len(new.vertices)==224",
 "len(new.polygons)==210",
 "tip_gap<.06",
 "V8_5_STEERING_SHAFT",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V8_21_Shroud_Metric_Tangent_UV",
 "V8_21_Shroud_Aligned_Tangent_Normal_UV",
 "V8_21_Source_Packed_Lower_Gauge_Shroud_PBR",
 "V8_21_Gauge_Shroud_Packed_Tangent_Normal",
 "V8_21_Source_And_Shroud_Normal_Mix",
 "V8_21_SOURCE_LOWER_GAUGE_SHROUD_WELT",
 "len(me.vertices)==168",
 "len(me.polygons)==162",
 "max_z<metal_min_z",
 "max_z<gauge_min_z",
 "sum(o.type==\"MESH\" for o in bpy.data.objects)==113",
 "sum(o.type==\"CURVE\" for o in bpy.data.objects)==109",
 "bmesh.ops.recalc_face_normals",
 "all_protected_source_mesh_geometry_preserved",
 "original_game_modified",
 "Quest3_tested",
 "DAYTONA_V8_21_MODEL_SAVED",
)
for guard in guards:assert guard in model,guard
for guard in (
 "DAYTONA_V8_21_R2_FRESH_REOPEN_PASS",
 "manifold(shaft.data) and manifold(me)",
 "assert max_z<min_atlas and max_z<min_bezel",
 "assert im.packed_file",
 "len(shaft.data.vertices)==224",
 "len(me.vertices)==168",
 "packed_source_PBR_detail_normal",
):assert guard in verify,guard
for guard in (
 "DAYTONA_V8_21_R2_ACTUAL_CYCLES_PASS",
 "scene.render.resolution_x=480",
 "scene.cycles.samples=4",
 "scene.render.threads=2",
 "assert not out.exists()",
 "PREVIEW_ONLY",
):assert guard in render,guard
for guard in (
 "Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 "Daytona365_v8_20_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_21_r2_ACTUAL_CYCLES_PREVIEW.png",
 "original_960x640_10spp_downsampled",
 "candidate_480x320_4spp",
 "photometric_equivalence",
 "NOT_ESTABLISHED",
):assert guard in compare,guard
print("DAYTONA_V8_21_SOURCE_CONTRACT_PASS",len(guards),
 "model guards AST/compile; independent Blender/Cycles evidence not CI")