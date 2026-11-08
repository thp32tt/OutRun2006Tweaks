#!/usr/bin/env python3
"""v8.18 R2 source-only static CI; actual Blender/Cycles validated separately."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=("blender_daytona365_v8_18_native_switch_surround_pbr.py",
 "verify_daytona365_v8_18_blender.py",
 "render_daytona365_v8_18_actual.py",
 "make_daytona365_v8_18_actual_compare.py")
text={}
for name in FILES:
 p=ROOT/name
 assert p.is_file(),name
 s=p.read_text(encoding="utf-8")
 ast.parse(s,filename=name)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in s
 assert "bpy.ops.wm.open_mainfile(" not in s
 text[name]=s
model=text[FILES[0]]
guards=(
"Daytona365_Cockpit_Blender_PBR_v8_17.blend",
"Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend",
"fcbe1755599de7a67af43bf7497f8889a756cb5e529efc031ccb1279e3abf1c7",
"for p in (DEST,NORMAL,MANIFEST):assert not p.exists()",
"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING",
"V8_18_Source_BlackLeather_SwitchSurround_PBR",
"V8_18_Surround_Metric_Tangent_UV",
"V8_18_Surround_Aligned_Normal_UV",
"V8_18_Packed_Surround_Tangent_Normal",
"V8_18_Source_And_Surround_Tangent_Normal_Mix",
"new_3D_seam_curve_count",
"source_switch_bounds_m",
"len(me.vertices)==1885",
"len(me.polygons)==3584",
"stack_faces>300",
"sculpted>110",
"len(mesh.vertices)==104",
"len(mesh.polygons)==98",
"recalc_face_normals",
"min(abs(v.co.x) for o in rails.values()",
"max(v.co.z for v in bottom.data.vertices)<bank_bnd",
"sum(o.type==\"MESH\" for o in bpy.data.objects)==110",
"sum(o.type==\"CURVE\" for o in bpy.data.objects)==102",
"assert all(math.isfinite",
"original_game_modified",
"Quest3_tested",
"DAYTONA_V8_18_R2_MODEL_SAVED")
for k in guards:assert k in model,k
verify=text[FILES[1]]
for k in ("DAYTONA_V8_18_FRESH_REOPEN_PASS",
"three_closed_source_switchbank_surround_meshes",
"len(me.vertices)==104","sill.materials[0]==mat",
"im.packed_file"):
 assert k in verify,k
render=text[FILES[2]]
for k in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
"scene.render.resolution_x=480","scene.cycles.samples=4",
"assert not out.exists()","DAYTONA_V8_18_ACTUAL_CYCLES_PASS"):
 assert k in render,k
compare=text[FILES[3]]
for k in ("Daytona365_v8_18_r2_ACTUAL_CYCLES_PREVIEW.png",
"original_960x640_10spp_downsampled",
"candidate_480x320_4spp","photometric_equivalence",
"NOT_ESTABLISHED"):
 assert k in compare,k
print("DAYTONA_V8_18_SOURCE_CONTRACT_PASS",len(guards),
 "AST/compile source-only guards, actual Blender verification separate")