#!/usr/bin/env python3
"""Daytona v8.15 source AST/compile/static guards; not Blender/runtime validation."""
import ast,py_compile,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
files=("blender_daytona365_v8_15_pmt_bolster_apron_pbr.py",
 "verify_daytona365_v8_15_blender.py",
 "render_daytona365_v8_15_actual.py",
 "make_daytona365_v8_15_actual_compare.py")
texts={}
for name in files:
 p=R/name
 assert p.is_file(),name
 source=p.read_text(encoding="utf-8")
 ast.parse(source,filename=name)
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
 texts[name]=source
build=texts[files[0]]
keys=(
 "Daytona365_Cockpit_Blender_PBR_v8_14.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_15.blend",
 "6de017b7f62b60a8484eef1b5eb8c851db037bd2ab88b1d09a79259b91702c77",
 "assert not DST.exists()","PMT_SEAT",
 "V8_15_Source_PMT017_Outer_Bolster_Packed_PBR",
 "V8_15_CROWN_BOLSTER_APRON_METRIC_UV",
 "V8_13_Seven_Pleat_Aligned_Normal_UV",
 "V8_13_Source_Sculpted_Charcoal_Cushion_PBR",
 "V8_9_Source_Charcoal_Seat_Side_PBR",
 "recalc_face_normals","source_packed_PBR","outer_faces",
 "len(seams)==12","len(me.vertices)==2*RING",
 "len(me.polygons)==7736","bmesh.ops.recalc_face_normals",
 "all(math.isfinite","original_game_files_modified",
 "Quest3_tested","OVC_created","game_runtime",
 "DAYTONA_V8_15_MODEL_SAVED")
for key in keys:assert key in build,key
verify=texts[files[1]]
for key in ("DAYTONA_V8_15_FRESH_REOPEN_PASS",
 "len(me.vertices)==7738","len(me.polygons)==7736",
 "sum(face.material_index==2","me.uv_layers.active.name",
 "all(q.packed_file",
 "sum(o.type==\"MESH\" for o in bpy.data.objects)==106",
 "sum(o.type==\"CURVE\" for o in bpy.data.objects)==94"):
 assert key in verify,key
render=texts[files[2]]
for key in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
 "assert not dest.exists()","scene.cycles.samples=4",
 "scene.render.resolution_x=480",
 "DAYTONA_V8_15_ACTUAL_CYCLES_PASS"):
 assert key in render,key
compare=texts[files[3]]
for key in ("photometric_equivalence","NOT_ESTABLISHED",
 "original_960x640_10spp_downsampled",
 "Daytona365_v8_15_ACTUAL_CYCLES_PREVIEW.png",
 "roi_difference_is_not_quality_score"):
 assert key in compare,key
for name,s in texts.items():
 assert "OR2006C2C.EXE" not in s,name
 assert "subprocess" not in s,name
 assert "bpy.ops.wm.open_mainfile(" not in s,name
print("DAYTONA_V8_15_SOURCE_CONTRACT_PASS",len(keys),
 "source guards; AST/compile only, not Blender render or Quest3")
