#!/usr/bin/env python3
"""Non-Blender source contract for source-private Daytona v8.5.

Blender execution and image rendering must be recorded separately.
"""
import ast
import py_compile
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
build=root/"blender_daytona365_v8_5_geometry_uv_pbr.py"
verify=root/"verify_daytona365_v8_5_blender.py"
for p in (build,verify):
 assert p.is_file(),p
 ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
source=build.read_text(encoding="utf-8")
check=verify.read_text(encoding="utf-8")
must_include=[
 "Daytona365_Cockpit_Blender_PBR_v8_4.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_5.blend",
 "BASE_SHA256",
 "assert not DEST.exists()",
 "rear.co = (front.co.x, front.co.y+.054, front.co.z-.004)",
 "V8_5_METRIC_UPHOLSTERY_UV",
 "V8_LOW_CENTER_TUNNEL",
 "V8_5_CURVED_COLUMN_COWL",
 "V8_5_STEERING_SHAFT",
 "V8_5_ORM_ROUGHNESS_RANGE",
 'sep.outputs["Green"]',
 'orm.image.colorspace_settings.name=="Non-Color"',
 "DAYTONA_V8_5_MODEL_SAVED",
 '"render_validation":"UNTESTED"',
 '"original_game_files_modified":False',
 '"OVC_created":False'
]
for token in must_include:
 assert token in source,token
assert "rear.y-front.y" in check
assert "packed_pbr_normal_orm_height" in check
assert "full_resolution_cycles_validation" in check
for text in (source,check):
 assert 'bpy.ops.wm.open_mainfile(' not in text
 assert "subprocess" not in text
 assert "OR2006C2C.EXE" not in text
 assert ".ovc" not in text.lower()
print("DAYTONA_V8_5_SOURCE_CONTRACT_PASS",len(must_include),"features; RENDER_VALIDATION=UNTESTED until actual render")
