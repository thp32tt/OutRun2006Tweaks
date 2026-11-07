#!/usr/bin/env python3
"""Daytona 365 v8.13 source-only static contract. NEVER calls Blender render."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=(
 "blender_daytona365_v8_13_pmt_seven_pleat_packed_normals.py",
 "verify_daytona365_v8_13_blender.py",
 "render_daytona365_v8_13_actual.py",
 "make_daytona365_v8_13_actual_compare.py",
)
txt={}
for file in FILES:
 path=ROOT/file
 assert path.is_file(),file
 code=path.read_text(encoding="utf-8")
 ast.parse(code,filename=str(path))
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(path),cfile=str(Path(temp)/(path.stem+".pyc")),doraise=True)
 txt[file]=code
code=txt[FILES[0]]
markers=(
 "Daytona365_Cockpit_Blender_PBR_v8_12.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_13.blend",
 "03c7e288fad4ecb36952ca2f871e132ee079d9888dea4664d9a97923cd6945c6",
 "assert not DEST.exists()",
 "Daytona365_v8_13_Cushion_Seven_Pleat_Tangent_Normal.png",
 "V8_13_PLEAT_DETAIL_UV_SOURCE",
 "V8_13_PACKED_PLEAT_NORMAL_IMAGE",
 "V8_13_SOURCE_PLUS_PLEAT_TANGENT_NORMAL",
 "V8_13_Geodesic_Seat_Leather_UV",
 "V8_13_Seven_Pleat_Aligned_Normal_UV",
 "OLD_CRESTS","NEW_CRESTS","NEW_GROOVES",
 "len(me.vertices)==2*RING",
 "len(me.polygons)==7736",
 "me.vertices[RING+k]",
 "recalc_face_normals",
 "math.dist",
 "mix.inputs[0].default_value=.36",
 "original_normal",
 "img.pack()",
 "assert img.packed_file",
 "colorspace_settings.name=\"Non-Color\"",
 "V8_5_ORM_ROUGHNESS_RANGE",
 "V8_9_PMT_CHARCOAL_DESATURATION",
 "NORMAL_MAP","BUMP",
 "V8_7_","CUSHION_STITCH_",
 "V5_","SEAT_RECLINED_PADDED_BACK",
 "DAYTONA_V8_13_MODEL_SAVED",
 "original_game_modified",
 "Quest3_tested",
)
for item in markers:assert item in code,item
verify=txt[FILES[1]]
for item in ("DAYTONA_V8_13_FRESH_REOPEN_PASS",
 "im.packed_file","original","len(mesh.vertices)==7738",
 "len(mesh.polygons)==7736","packed_new_tangent_normal",
 "source_tangent_normal_retained","m[\"cushions\"][side]"):
 assert item in verify,item
render=txt[FILES[2]]
for item in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
 "assert not out.exists()","DAYTONA_V8_13_ACTUAL_CYCLES_PREVIEW_PASS",
 "UNTESTED","bpy.ops.render.render(write_still=True)"):
 assert item in render,item
compare=txt[FILES[3]]
for item in ("original_960x640_10spp_downsampled",
 "photometric_equivalence","NOT_ESTABLISHED",
 "Daytona365_v8_13_ACTUAL_CYCLES_PREVIEW.png"):
 assert item in compare,item
for name,c in txt.items():
 assert "bpy.ops.wm.open_mainfile(" not in c,name
 assert "OR2006C2C.EXE" not in c,name
 assert "subprocess" not in c,name
print("DAYTONA_V8_13_SOURCE_CONTRACT_PASS",
 len(markers),"source guards; AST/compile only, not Blender render")