#!/usr/bin/env python3
"""v8.16 CI static source contract; DOES NOT claim Blender execution/render."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=("blender_daytona365_v8_16_backrest_wings_packed_normals.py",
 "verify_daytona365_v8_16_blender.py",
 "render_daytona365_v8_16_actual.py",
 "make_daytona365_v8_16_actual_compare.py")
sources={}
for name in files:
 p=root/name;assert p.is_file(),name
 text=p.read_text(encoding="utf-8")
 ast.parse(text,filename=name)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in text
 assert "bpy.ops.wm.open_mainfile(" not in text
 sources[name]=text
model=sources[files[0]]
guard=(
"Daytona365_Cockpit_Blender_PBR_v8_15.blend",
"Daytona365_Cockpit_Blender_PBR_v8_16.blend",
"19728e96bb3b09ea92138cb4201218ac4479cdfaa7b624e375587fc0ef872006",
"assert not p.exists()",
"V8_9_Source_Charcoal_Seat_PBR",
"V8_9_Source_Charcoal_Seat_Side_PBR",
"V8_16_PMT017_Backrest_Source_Charcoal_PBR",
"V8_16_Backrest_Metric_Tangent_UV",
"V8_16_Aligned_Wing_Tangent_Normal_UV",
"V8_16_Original_And_Wing_Normal_Mix",
"V8_16_Packed_Wing_Normal",
"V8_5_ORM_ROUGHNESS_RANGE",
"recalc_face_normals",
"newseams.append",
"original_game_files_modified",
"Quest3_tested",
"OVC_created",
"DAYTONA_V8_16_MODEL_SAVED",
)
for k in guard:assert k in model,k
verify=sources[files[1]]
for k in ("DAYTONA_V8_16_FRESH_REOPEN_PASS","len(me.vertices)==8614",
 "me.materials[0]==mat","normal.packed_file","source_sha256"):
 assert k in verify,k
render=sources[files[2]]
for k in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST","scene.cycles.samples=4",
 "scene.render.resolution_x=480","assert not out.exists()",
 "DAYTONA_V8_16_ACTUAL_CYCLES_PASS"):
 assert k in render,k
comparison=sources[files[3]]
for k in ("original_960x640_10spp_downsampled",
"candidate_480x320_4spp","photometric_equivalence",
"NOT_ESTABLISHED","Daytona365_v8_16_ACTUAL_CYCLES_PREVIEW.png"):
 assert k in comparison,k
print("DAYTONA_V8_16_SOURCE_CONTRACT_PASS",len(guard),
 "static guard keys; no Blender or in-game execution claimed")