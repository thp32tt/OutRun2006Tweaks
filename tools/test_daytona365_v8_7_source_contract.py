#!/usr/bin/env python3
"""Static source contract, explicitly not a Blender runtime/render."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
paths=[
 "blender_daytona365_v8_7_seat_source_contours_underdash.py",
 "verify_daytona365_v8_7_blender.py",
 "render_daytona365_v8_7_actual.py",
 "compare_daytona365_v8_7_actual.py"]
sources={}
for file in paths:
 p=root/file
 assert p.is_file()
 s=p.read_text(encoding="utf-8")
 ast.parse(s,filename=str(p))
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(p),cfile=str(Path(temp)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in s
 assert "bpy.ops.wm.open_mainfile(" not in s
 assert "subprocess" not in s
 sources[file]=s
s=sources[paths[0]]
tokens=[
 "SOURCE_SHA256","assert not DEST.exists()","Daytona365_Cockpit_Blender_PBR_v8_6.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_7.blend",
 "PMT_SEAT_ENVELOPE","PMT_CONSOLE_ENVELOPE",
 "V8_7_GEODESIC_LEATHER_UV","V8_7_Seat_Side_Return_Leather_PBR",
 "V8_7_Knee_And_Footwell_PBR","V8_7_FOOTWELL_METRIC_UV",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "Daytona365_Cockpit_Blender_PBR_v8_7.blend",
 "rear.co=(p.co.x,p.co.y+.054,p.co.z-.004)",
 "rear.co=(p.co.x,p.co.y+.006,p.co.z-.049)",
 "DAYTONA_V8_7_MODEL_SAVED",
 '"render_validation":"UNTESTED"',
 '"original_game_files_modified":False',
 '"Quest3_tested":False']
for t in tokens:
 assert t in s,t
v=sources[paths[1]]
assert 'mesh_count' in v and "side_i" in v
assert 'bpy.data.filepath==str(src)' in v
assert "DAYTONA365_APPROVED_HEAVY_RENDER_HOST" in sources[paths[2]]
assert "changed_RGB_pixels_v86_v87" in sources[paths[3]]
print("DAYTONA_V8_7_SOURCE_CONTRACT_PASS",len(tokens),"assertions; RENDER_VALIDATION=UNTESTED until actual execution")
