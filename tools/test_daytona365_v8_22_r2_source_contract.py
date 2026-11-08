#!/usr/bin/env python3
"""Ferrari Daytona v8.22 AST/compile source-only CI, not a Blender render."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=("blender_daytona365_v8_22_shifter_boot_pbr_r2.py",
 "verify_daytona365_v8_22_r2_blender.py",
 "render_daytona365_v8_22_r2_actual.py",
 "make_daytona365_v8_22_r2_actual_compare.py")
s={}
for name in FILES:
 p=ROOT/name
 assert p.is_file(),name
 source=p.read_text(encoding="utf-8")
 ast.parse(source,filename=name)
 with tempfile.TemporaryDirectory() as t:
  py_compile.compile(str(p),cfile=str(Path(t)/"test.pyc"),doraise=True)
 assert "OR2006C2C.EXE" not in source
 assert "bpy.ops.wm.open_mainfile" not in source
 s[name]=source
build,verify,render,compare=[s[p] for p in FILES]
guards=(
 "Daytona365_Cockpit_Blender_PBR_v8_21_r2.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend",
 "411cf351d76fcb21413a340c0ff4dbc3994a881c52c56fdc83919d29b4aac110",
 "assert not p.exists()",
 "V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",
 "len(boot.data.vertices)==60",
 "len(boot.data.polygons)==84",
 "RINGS=14; SIDES=24",
 "len(xyz)==672",
 "len(faces)==672",
 "all(len(e.link_faces)==2 for e in bm.edges)",
 "V8_22_Shifter_Metric_Leather_UV",
 "V8_22_Shifter_Aligned_Normal_UV",
 "V8_22_Shifter_Boot_Packed_Tangent_Normal",
 "V8_22_Source_Packed_Shifter_Boot_Black_Leather_PBR",
 "V8_22_Source_And_Shifter_Normal_Mix",
 "V8_22_",
 "SHIFTER_BOOT_SEAM",
 "LEFT",
 "RIGHT",
 "V5_MANUAL_SHIFTER_CHROME_SHAFT",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V6_L_BLENDER_BLACK_FLOOR_MAT",
 "V6_R_BLENDER_BLACK_FLOOR_MAT",
 "V8_L_CLASSIC_PADDED_CUSHION",
 "V8_R_CLASSIC_PADDED_CUSHION",
 "bmesh.ops.recalc_face_normals",
 "img.pack()",
 "node.image.packed_file",
 "sum(o.type==\"MESH\" for o in bpy.data.objects)==113",
 "sum(o.type==\"CURVE\" for o in bpy.data.objects)==111",
 "bpy.ops.wm.save_as_mainfile(filepath=str(OUT)",
 "original_game_modified",
 "Quest3_tested",
 "DAYTONA_V8_22_MODEL_SAVED")
for g in guards: assert g in build,g
for g in ("DAYTONA_V8_22_FRESH_REOPEN_PASS",
 "signed_volume=bm.calc_volume(signed=True)",
 "len(mesh.vertices)==672",
 "all(len(e.link_faces)==2 for e in bm.edges)",
 "assert im.packed_file",
 "mesh.materials[0]==mat"):assert g in verify,g
for g in ("DAYTONA_V8_22_ACTUAL_CYCLES_PASS",
 "sc.render.resolution_x=480","sc.cycles.samples=4",
 "sc.render.threads=2","assert not out.exists()",
 "PREVIEW_ONLY"):assert g in render,g
for g in ("Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 "Daytona365_v8_21_r2_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_22_r2_ACTUAL_CYCLES_PREVIEW.png",
 "photometric_equivalence","NOT_ESTABLISHED",
 "delta_not_fidelity_score"):assert g in compare,g
print("DAYTONA_V8_22_SOURCE_CONTRACT_PASS",len(guards),"guards + AST/compile; real Cycles audited separately")