#!/usr/bin/env python3
from pathlib import Path
import ast,py_compile,tempfile
ROOT=Path(__file__).resolve().parent
files=[
 "blender_daytona_v8_shape_rework.py",
 "blender_daytona_v8_1_cleanup.py",
 "blender_daytona_v8_2_polish.py",
 "blender_daytona_v8_3_structure.py",
 "blender_daytona_v8_4_fine_cleanup.py",
 "verify_daytona_v8_4_blender.py",
]
for f in files:
 p=ROOT/f
 if not p.is_file():
  alt=ROOT/f.replace("blender_daytona_","blender_daytona365_").replace("verify_daytona_","verify_daytona365_")
  p=alt
 assert p.is_file(),p
 py_compile.compile(str(p),doraise=True)
 ast.parse(p.read_text())
texts={}
for f in files:
 p=ROOT/f if (ROOT/f).exists() else ROOT/f.replace("blender_daytona_","blender_daytona365_").replace("verify_daytona_","verify_daytona365_")
 texts[f]=p.read_text()
assert "V8_L_CLASSIC_PADDED_CUSHION" in texts["verify_daytona_v8_4_blender.py"]
assert "V8_4_SLIM_STEERING_COWL" in texts["verify_daytona_v8_4_blender.py"]
assert "V8_2_CONTINUOUS_LOWER_DASH_LIP" in texts["verify_daytona_v8_4_blender.py"]
assert "normal_bump_maps_connected" in texts["verify_daytona_v8_4_blender.py"]
assert "seat_rails_and_mounts" in texts["blender_daytona_v8_3_structure.py"]
assert "steering_column_slimmed" in texts["blender_daytona_v8_4_fine_cleanup.py"]
assert "center_tunnel_compacted" in texts["blender_daytona_v8_2_polish.py"]
for f,t in texts.items():
 low=t.lower()
 assert "obj_plcar_dayts_pmt.sz" not in low
 assert ".ovc" not in low
print("DAYTONA_V8_SOURCE_CONTRACT_PASS",len(files),"scripts")