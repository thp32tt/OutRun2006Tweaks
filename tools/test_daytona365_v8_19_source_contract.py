#!/usr/bin/env python3
"""Daytona365 v8.19 source-only CI contract: NOT Blender, OVC or Quest validation."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=(
 "blender_daytona365_v8_19_door_endcaps_pbr.py",
 "verify_daytona365_v8_19_blender.py",
 "render_daytona365_v8_19_actual.py",
 "render_daytona365_v8_19_endcap_diagnostic.py",
 "make_daytona365_v8_19_actual_compare.py")
sources={}
for name in files:
 p=root/name
 assert p.is_file(),name
 text=p.read_text(encoding="utf-8")
 ast.parse(text,filename=name)
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(p),cfile=str(Path(temp)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in text,name
 assert "bpy.ops.wm.open_mainfile(" not in text,name
 sources[name]=text
m=sources[files[0]]
guard=(
 "Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_19_r2.blend",
 "bde686212360eb7450697d3f762351eabe19751af54fa3ea58493063fcf72a4a",
 "DAYTONA_V8_19_R2_BUILD_MANIFEST.json",
 "assert not f.exists()",
 "LEATHER_SCULPTED_DOOR",
 "V8_3_",
 "BLACK_DOOR_TOP_CAP",
 "V8_19_",
 "DASH_DOOR_FORMED_ENDCAP",
 "taper=.24+.76*math.sin(math.pi*t)**.7",
 "recalc_face_normals",
 "V8_19_Endcap_Metric_Tangent_UV",
 "V8_19_Endcap_Aligned_Tangent_UV",
 "V8_19_Source_Dash_To_Door_Dark_PBR",
 "V8_19_Packed_Endcap_Tangent_Normal",
 "V8_19_Source_And_Endcap_Tangent_Normal_Mix",
 "V8_5_ORM_ROUGHNESS_RANGE",
 "source_PBR_images",
 "original_game_PMT_untouched",
 "DAYTONA_V8_19_R2_MODEL_SAVED",
 "normsha",
 "new_seam_curves",
 "V8_18_L_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
)
for text in guard:assert text in m,text
verify=sources[files[1]]
for t in ("DAYTONA_V8_19_FRESH_REOPEN_PASS",
          "len(end.vertices)==128","len(top.vertices)==136",
          "len(door.vertices)==465","im.packed_file",
          "source_sha256","model_sha256"):
 assert t in verify,t
render=sources[files[2]]
for t in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
          "scene.cycles.samples=4","scene.render.resolution_x=480",
          "assert not out.exists()","DAYTONA_V8_19_ACTUAL_CYCLES_PASS"):
 assert t in render,t
diagnostic=sources[files[3]]
for t in ("diagnostic_not_original_camera",
          "DAYTONA_V8_19_ENDCAP_DIAGNOSTIC_CYCLES_PASS",
          "scene.cycles.samples=4","V8_19_Door_Endcap_Diagnostic_Camera"):
 assert t in diagnostic,t
comparison=sources[files[4]]
for t in ("original_960x640_10spp_downsampled",
          "candidate_480x320_4spp",
          "photometric_equivalence","NOT_ESTABLISHED",
          "Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png"):
 assert t in comparison,t
print("DAYTONA_V8_19_SOURCE_CONTRACT_PASS",len(guard),
      "static guards only; real Blender render verified independently")