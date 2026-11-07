#!/usr/bin/env python3
"""Non-Blender contract; Blender execution and actual rendering are separate."""
import ast,py_compile,tempfile
from pathlib import Path
r=Path(__file__).resolve().parent
names=("blender_daytona365_v8_6_source_contoured_console_seats.py",
       "verify_daytona365_v8_6_blender.py",
       "render_daytona365_v8_6_actual.py",
       "make_daytona365_v8_6_actual_compare.py")
texts={}
for name in names:
 path=r/name
 assert path.is_file(),name
 s=path.read_text(encoding="utf-8")
 ast.parse(s,filename=str(path))
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(path),cfile=str(Path(tmp)/(path.stem+".pyc")),doraise=True)
 texts[name]=s
s=texts[names[0]]
required=(
 "Daytona365_Cockpit_Blender_PBR_v8_5.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_6.blend",
 "SOURCE_SHA256",
 "assert not DEST.exists()",
 "PMT_CENTER_STACK_BOUNDS",
 "PMT_CONSOLE_BOUNDS",
 "object00_group01_material016_a0",
 "object00_group01_material018",
 "V8_6_METRIC_TANGENT_UV",
 "V8_LOW_CENTER_TUNNEL",
 "V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING",
 "V8_2_CONTINUOUS_LOWER_DASH_LIP",
 "V8_6_DOOR_METRIC_UV",
 "V8_6_Source_Measured_Console_Grain",
 "V8_6_Soft_Door_Card_Leather",
 "V8_5_METRIC_UPHOLSTERY_UV",
 "back.co=(point.co.x,point.co.y+.054,point.co.z-.004)",
 "DAYTONA_V8_6_MODEL_SAVED",
 '"render_validation":"UNTESTED"',
 '"original_game_files_modified":False',
 '"Quest3_tested":False'
)
for token in required:
 assert token in s,token
assert "len(tunnel.data.vertices)==54" in texts[names[1]]
assert "shader.inputs[\"Normal\"].is_linked" in texts[names[1]]
assert "DAYTONA365_APPROVED_HEAVY_RENDER_HOST" in texts[names[2]]
assert "original_960x640_10spp_downsampled" in texts[names[3]]
for t in texts.values():
 assert "bpy.ops.wm.open_mainfile(" not in t
 assert "OR2006C2C.EXE" not in t
 assert "subprocess" not in t
print("DAYTONA_V8_6_SOURCE_CONTRACT_PASS",len(required),"material checks; actual Blender/render separately")
