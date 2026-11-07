#!/usr/bin/env python3
"""Source AST/compile/contract only; real Blender and Cycles are separate."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
filenames=[
 "blender_daytona365_v8_9_headrest_charcoal_pleats.py",
 "verify_daytona365_v8_9_blender.py",
 "render_daytona365_v8_9_actual.py",
 "make_daytona365_v8_9_actual_compare.py"]
files={}
for name in filenames:
 p=ROOT/name
 assert p.is_file(),name
 source=p.read_text(encoding="utf-8")
 ast.parse(source,filename=name)
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
 files[name]=source
main=files[filenames[0]]
for token in (
 'Daytona365_Cockpit_Blender_PBR_v8_8.blend',
 'Daytona365_Cockpit_Blender_PBR_v8_9.blend',
 '6859ead3070525e9a55e7b6946ba10d0050ff85825ce1074f8e3a2255ef48c60',
 'assert not DEST.exists()',
 'headrest_rings',
 'V8_9_METRIC_HEADREST_UV',
 'V8_9_RESCULPTED_GEODESIC_UV',
 'V8_9_PMT_CHARCOAL_DESATURATION',
 'V8_8_SOURCE_BASECOLOR_ATTENUATION',
 'V8_9_Source_Charcoal_Seat_PBR',
 'V8_9_Source_Charcoal_Seat_Side_PBR',
 'V8_9_Source_Charcoal_Headrest_PBR',
 'V8_5_ORM_ROUGHNESS_RANGE',
 'packed_file',
 'source_packed_pbr_basecolor_normal_orm_height',
 'original_game_files_modified',
 'Quest3_tested',
 'DAYTONA_V8_9_MODEL_SAVED'):
 assert token in main,token
ver=files[filenames[1]]
for token in ('len(h.data.vertices)==7*4',
 'len(tunnel.data.vertices)==78',
 'v8_9.blend',
 'V8_9_RESCULPTED_GEODESIC_UV',
 'source_packed_pbr_basecolor_normal_orm_height_retained'):
 assert token in ver,token
render=files[filenames[2]]
assert 'DAYTONA365_APPROVED_HEAVY_RENDER_HOST' in render
assert 'ACTUAL_BLENDER_CYCLES_RENDERED' in render
compare=files[filenames[3]]
assert 'original_960x640_10spp_downsampled' in compare
for name,contents in files.items():
 assert 'bpy.ops.wm.open_mainfile(' not in contents,name
 assert 'subprocess' not in contents,name
 assert 'OR2006C2C.EXE' not in contents,name
print("DAYTONA_V8_9_SOURCE_CONTRACT_PASS",len(files),"scripts; Blender/render not inferred")