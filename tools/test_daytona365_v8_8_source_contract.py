#!/usr/bin/env python3
"""Static source contract only: not a substitute for actual official Blender render."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
names=("blender_daytona365_v8_8_pmt_console_pbr.py",
 "verify_daytona365_v8_8_blender.py","render_daytona365_v8_8_actual.py",
 "make_daytona365_v8_8_actual_compare.py")
texts={}
for name in names:
 p=root/name
 assert p.is_file(),name
 t=p.read_text(encoding="utf-8")
 ast.parse(t,filename=name)
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
 texts[name]=t
s=texts[names[0]]
required=(
 'Daytona365_Cockpit_Blender_PBR_v8_7.blend',
 'Daytona365_Cockpit_Blender_PBR_v8_8.blend',
 'e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3',
 'assert not DEST.exists()',
 'PMT_CONSOLE_BOUNDS',
 'PMT_SEAT_BOUNDS',
 'V8_7_GEODESIC_LEATHER_UV',
 'V8_8_PMT_Console_Matte_Grain',
 'V8_8_METRIC_CONSOLE_UV',
 'V8_8_Source_Seat_Less_Saturated_Leather',
 'V8_8_Seat_Side_Return_Leather',
 'V8_5_ORM_ROUGHNESS_RANGE',
 'V8_8_SOURCE_BASECOLOR_ATTENUATION',
 'len(stations)==13',
 'V8_LOW_CENTER_TUNNEL',
 'DAYTONA_V8_8_MODEL_SAVED',
 'original_game_files_modified',
 '"Quest3_tested":False',
 '"render_validation":"UNTESTED"',
)
for token in required:
 assert token in s,token
v=texts[names[1]]
for token in ('len(tunnel.data.vertices)==78','V8_7_GEODESIC_LEATHER_UV',
              'bpy.context.scene.camera.name','packed_source_pbr_orm_normal_bump'):
 assert token in v,token
r=texts[names[2]]
assert 'DAYTONA365_APPROVED_HEAVY_RENDER_HOST' in r
assert '"preview"' in r and '"matched"' in r
c=texts[names[3]]
assert 'original_960x640_10spp_downsampled' in c
for name,t in texts.items():
 assert 'bpy.ops.wm.open_mainfile(' not in t,name
 assert 'OR2006C2C.EXE' not in t,name
 assert 'subprocess' not in t,name
print("DAYTONA_V8_8_SOURCE_CONTRACT_PASS",len(required),"v8.8 material checks; no render claim")