#!/usr/bin/env python3
"""Source-only v8.10 static contract; never claim Blender render from CI alone."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=("blender_daytona365_v8_10_pmt_dark_doors_wheel_normals.py",
 "verify_daytona365_v8_10_blender.py",
 "render_daytona365_v8_10_actual.py",
 "make_daytona365_v8_10_actual_compare.py")
texts={}
for file in files:
 p=root/file
 assert p.is_file(),file
 t=p.read_text(encoding="utf-8")
 ast.parse(t,filename=file)
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(p),cfile=str(Path(temp)/(p.stem+".pyc")),doraise=True)
 texts[file]=t
s=texts[files[0]]
keys=("Daytona365_Cockpit_Blender_PBR_v8_9.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_10.blend",
 "bfd91e5e29d796e708918298678305172ec21fff958122d2eed72118303ca9c2",
 "assert not DEST.exists()",
 '"V5_"+side',"V8_10_DOOR_GEODESIC_UV",
 "V8_10_Source_Charcoal_Door_Leather_PBR",
 "V8_10_Source_Charcoal_Door_Lower_PBR",
 "V8_10_Source_Ebonized_Steering_Rim_PBR",
 "V8_10_PMT_DARK_SOURCE_BASECOLOR",
 "V8_5_ORM_ROUGHNESS_RANGE",
 "NORMAL_MAP","BUMP","TEX_IMAGE",
 "recalc_face_normals","math.dist",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "DAYTONA_V8_10_MODEL_SAVED",
 '"original_game_files_modified":False',
 '"Quest3_tested":False',
 '"render_validation":"UNTESTED"')
for k in keys:assert k in s,k
v=texts[files[1]]
for k in ("len(me.vertices)==465","len(me.polygons)==840",
 "V8_10_DOOR_GEODESIC_UV","packed_file","camera.name",
 "DAYTONA_V8_10_FRESH_REOPEN_PASS"):assert k in v,k
render=texts[files[2]]
assert 'DAYTONA365_APPROVED_HEAVY_RENDER_HOST' in render
assert 'DAYTONA_V8_10_ACTUAL_CYCLES_PREVIEW_PASS' in render
compare=texts[files[3]]
assert 'original_960x640_10spp_downsampled' in compare
assert 'NOT_ESTABLISHED' in compare
for k,t in texts.items():
 assert 'bpy.ops.wm.open_mainfile(' not in t,k
 assert 'OR2006C2C.EXE' not in t,k
 assert 'subprocess' not in t,k
print("DAYTONA_V8_10_SOURCE_CONTRACT_PASS",len(keys),
 "guards; AST/compile/static only, not Blender render")