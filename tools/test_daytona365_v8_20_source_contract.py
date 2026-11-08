#!/usr/bin/env python3
"""Daytona365 v8.20 AST/compile source-only CI; not a Blender/runtime test."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=(
 "blender_daytona365_v8_20_source_footwell_pbr.py",
 "verify_daytona365_v8_20_blender.py",
 "render_daytona365_v8_20_actual.py",
 "make_daytona365_v8_20_actual_compare.py")
texts={}
for name in FILES:
 p=ROOT/name
 assert p.exists(),name
 s=p.read_text(encoding="utf-8")
 ast.parse(s,filename=name)
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in s
 assert "bpy.ops.wm.open_mainfile(" not in s
 texts[name]=s
model,verify,render,compare=[texts[name] for name in FILES]
guards=(
 "Daytona365_Cockpit_Blender_PBR_v8_19_r2.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_20.blend",
 "f018aee762f714f84fc3bec12991e217778d1eade598861511729bf901469300",
 "for p in (DEST,NORMAL,MANIFEST):assert not p.exists()",
 "V6_", "BLENDER_BLACK_FLOOR_MAT",
 "V8_20_Footwell_Metric_Tangent_UV",
 "V8_20_Footwell_Aligned_Normal_UV",
 "V8_20_Source_Packed_Dark_Rubber_Footwell_PBR",
 "V8_20_Source_And_Footwell_Tangent_Normal_Mix",
 "V8_20_Packed_Footwell_Tangent_Normal",
 "FOOTWELL_MAT_PERIMETER_WELT",
 "V7_REAL_BLACK_CARPET_FLOOR",
 "V6_DRIVER_METAL_PEDAL_0",
 "V8_19_L_DASH_DOOR_FORMED_ENDCAP",
 "V8_19_R_DASH_DOOR_FORMED_ENDCAP",
 "NX=19;NY=13",
 "len(new.vertices)==494", "len(new.polygons)==492",
 "bmesh.ops.recalc_face_normals",
 "source_packed_textures", "image.pack()", "img.pack()",
 "native_controls_seats_door_endcaps_and_carpet_unchanged",
 "original_game_modified", "Quest3_tested",
 "bpy.ops.wm.save_as_mainfile(filepath=str(DEST)",
 'sum(o.type=="MESH" for o in bpy.data.objects)==112',
 'sum(o.type=="CURVE" for o in bpy.data.objects)==108',
 "DAYTONA_V8_20_MODEL_SAVED")
for guard in guards:
 assert guard in model,guard
for guard in ("DAYTONA_V8_20_FRESH_REOPEN_PASS",
 "len(me.vertices)==494","len(me.polygons)==492",
 "assert detail.packed_file","assert len(edge.data.splines[0].points)==60",
 "assert hashlib.sha256(p.read_bytes()).hexdigest()",
 "source_controls_seats_v819_door_ends_preserved"):
 assert guard in verify,guard
for guard in ("DAYTONA_V8_20_ACTUAL_CYCLES_PASS",
 "scene.render.resolution_x=480","scene.cycles.samples=4",
 "scene.render.threads=2","assert not out.exists()",
 "PREVIEW_ONLY"):
 assert guard in render,guard
for guard in ("Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 "Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_20_ACTUAL_CYCLES_PREVIEW.png",
 "original_960x640_10spp_downsampled",
 "candidate_480x320_4spp","photometric_equivalence",
 "NOT_ESTABLISHED"):
 assert guard in compare,guard
print("DAYTONA_V8_20_SOURCE_CONTRACT_PASS",len(guards),
 "model guards; AST/compile; physical Blender render audited independently")