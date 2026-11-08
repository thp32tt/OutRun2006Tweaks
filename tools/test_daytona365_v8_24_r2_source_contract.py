#!/usr/bin/env python3
"""v8.24-r2 rigorous source-only contract; separate true Blender evidence required."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
names=("blender_daytona365_v8_24_punched_spoke_holes_r2.py",
"verify_daytona365_v8_24_r2_blender.py",
"render_daytona365_v8_24_r2_actual.py",
"render_daytona365_v8_24_r2_spoke_isolated_actual.py",
"make_daytona365_v8_24_r2_actual_compare.py")
s=[]
for name in names:
 path=root/name;assert path.is_file(),name
 content=path.read_text(encoding="utf-8")
 ast.parse(content,filename=name)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(path),cfile=str(Path(d)/"checked.pyc"),doraise=True)
 assert "OR2006C2C.EXE" not in content
 assert "bpy.ops.wm.open_mainfile(" not in content
 s.append(content)
model,verify,render,studio,compare=s
requirements=(
"Daytona365_Cockpit_Blender_PBR_v8_23.blend",
"Daytona365_Cockpit_Blender_PBR_v8_24_r2.blend",
"58c6404ec595392ab73358ec3b61aea3d971629f87d2d633b73918aaffa041bd",
"assert not DST.exists() and not MANIFEST.exists()",
"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
"DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",
"V8_21_SOURCE_LOWER_GAUGE_SHROUD",
"V6_L_BLENDER_BLACK_FLOOR_MAT",
"V6_R_BLENDER_BLACK_FLOOR_MAT",
"V8_23_Source_Linked_Brushed_Spoke_Aluminum",
"V8_23_Stamped_Spoke_Packed_Tangent_Normal",
"V8_24_Dark_Anodized_Punched_Spoke_Edge_PBR",
"bpy.ops.mesh.primitive_cylinder_add(vertices=32",
"mod.operation=\"DIFFERENCE\";mod.solver=\"EXACT\"",
"bpy.ops.object.modifier_move_up(modifier=mod.name)",
"bpy.ops.object.modifier_apply(modifier=mod.name)",
"R=.00305","for t in (.25,.5,.75)",
"abs(d-R)<.00075",
"len(e.link_faces)==2",
"bmesh.ops.recalc_face_normals",
"assert not hit",
"assert metal_hit",
"me.uv_layers",
"me.materials.append(bore_mat)",
"sum(o.type==\"MESH\" for o in bpy.data.objects)==113",
"sum(o.type==\"CURVE\" for o in bpy.data.objects)==111",
"bpy.ops.wm.save_as_mainfile(filepath=str(DST)",
"source_original_PMT_triangle_copy",
"original_game_modified",
"OVC_created",
"Quest3_tested",
"DAYTONA_V8_24_MODEL_SAVED")
for key in requirements:assert key in model,key
for key in ("DAYTONA_V8_24_R2_FRESH_REOPEN_PASS","all(len(e.link_faces)==2 for e in bm.edges)",
 "bm.calc_volume(signed=True)","not hit","assert hit",
 "im.packed_file","me.materials[1]==bore"):assert key in verify,key
for key in ("DAYTONA_V8_24_R2_ACTUAL_CYCLES_PASS","sc.render.resolution_x=480",
 "sc.cycles.samples=4","sc.render.threads=2","PREVIEW_ONLY"):assert key in render,key
for key in ("DAYTONA_V8_24_R2_ISOLATED_CYCLES_PASS",
 "cam.location=(-.35,-.88,.792)",'cam_data.lens=51',
 'sc.cycles.samples=4',"TEMPORARY_STUDIO_WHEEL_DETAIL_NOT_ORIGINAL_CAMERA"):
 assert key in studio,key
for key in ("Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 "Daytona365_v8_23_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_24_r2_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_v8_23_SPOKE_ISOLATED_ACTUAL_CYCLES.png",
 "Daytona365_v8_24_r2_SPOKE_ISOLATED_ACTUAL_CYCLES.png",
 "photometric_equivalence","NOT_ESTABLISHED","delta_not_fidelity_score"):
 assert key in compare,key
print("DAYTONA_V8_24_R2_SOURCE_CONTRACT_PASS",len(requirements),"guards + AST/compile; real Blender separately verified")