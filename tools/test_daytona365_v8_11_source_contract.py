#!/usr/bin/env python3
"""Static source contract only; not a Blender rendering or original PMT fidelity test."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
names=("blender_daytona365_v8_11_crown_dark_conformal_piping.py",
 "verify_daytona365_v8_11_blender.py",
 "render_daytona365_v8_11_actual.py",
 "make_daytona365_v8_11_actual_compare.py")
txt={}
for n in names:
 p=root/n
 assert p.is_file(),n
 t=p.read_text(encoding="utf-8")
 ast.parse(t,filename=n)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/(p.stem+".pyc")),doraise=True)
 txt[n]=t
s=txt[names[0]]
must=(
 "Daytona365_Cockpit_Blender_PBR_v8_10.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_11.blend",
 "ab60744f37c93f4db079a9be79b7df09f3d99006fc332e4a9f98e21b92acbb74",
 "assert not DEST.exists()",
 "V8_3_",
 "V8_11_Source_Charcoal_Seat_Edge_PBR",
 "V8_11_HEADREST_SURFACE_GEODESIC_UV",
 "V8_11_CROWN_GEODESIC_UV",
 "len(m.vertices)==242",
 "len(m.polygons)==222",
 "PMT017",
 "V8_LOW_CENTER_TUNNEL",
 "V8_9_",
 "V8_5_ORM_ROUGHNESS_RANGE",
 "V8_9_PMT_CHARCOAL_DESATURATION",
 "bmesh.ops.recalc_face_normals",
 "DAYTONA_V8_11_MODEL_SAVED",
 '"original_game_files_modified":False',
 '"Quest3_tested":False',
 '"render_validation":"UNTESTED"')
for key in must:
 assert key in s,key
v=txt[names[1]]
for key in ("DAYTONA_V8_11_FRESH_REOPEN_PASS","len(m.vertices)==242",
 "V8_11_CROWN_GEODESIC_UV","packed_file","len(tunnel.data.vertices)==78"):
 assert key in v,key
r=txt[names[2]]
assert 'DAYTONA365_APPROVED_HEAVY_RENDER_HOST' in r
assert 'DAYTONA_V8_11_ACTUAL_CYCLES_PREVIEW_PASS' in r
c=txt[names[3]]
assert 'original_960x640_10spp_downsampled' in c
assert 'photometric_equivalence' in c
for name,t in txt.items():
 assert 'OR2006C2C.EXE' not in t,name
 assert 'bpy.ops.wm.open_mainfile(' not in t,name
 assert 'subprocess' not in t,name
print("DAYTONA_V8_11_SOURCE_CONTRACT_PASS",len(must),"guards AST/compile; no Blender render claim")