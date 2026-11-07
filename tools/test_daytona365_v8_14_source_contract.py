#!/usr/bin/env python3
"""v8.14 source-only CI: AST/compile/static provenance, never a Blender render."""
import ast,py_compile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
names=("blender_daytona365_v8_14_pmt_shifter_deck_pbr.py",
       "verify_daytona365_v8_14_blender.py",
       "render_daytona365_v8_14_actual.py",
       "make_daytona365_v8_14_actual_compare.py")
source={}
for n in names:
 p=ROOT/n
 assert p.is_file(),n
 s=p.read_text(encoding="utf-8")
 ast.parse(s,filename=n)
 with tempfile.TemporaryDirectory() as tmp:
  py_compile.compile(str(p),cfile=str(Path(tmp)/(p.stem+".pyc")),doraise=True)
 source[n]=s
build=source[names[0]]
keys=(
 "Daytona365_Cockpit_Blender_PBR_v8_13.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_14.blend",
 "130accf3db850df025c836c0364d5a8dfebcf6001a88e61d19135b4331499cc7",
 "assert not DEST.exists()",
 "V8_1_COMPACT_SHIFTER_LEATHER_DECK",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "PMT018","stations","len(stations)==10","len(mesh.vertices)==100",
 "len(mesh.polygons)==92","V8_14_PMT018_DECK_METRIC_TANGENT_UV",
 "recalc_face_normals","V8_14_PMT018_Shifter_Deck_Grain_Source_PBR",
 "V8_14_PMT018_SOURCE_DARK_LEATHER",
 "V8_5_ORM_ROUGHNESS_RANGE","NORMAL_MAP","BUMP","TEX_IMAGE",
 "packed_file","Non-Color","len(mesh.uv_layers.active.data)",
 "gate_before==","knob_before==","v813_seat_channels_preserved",
 "original_game_files_modified","Quest3_tested","OVC_created",
 "DAYTONA_V8_14_MODEL_SAVED",
)
for key in keys:assert key in build,key
verify=source[names[1]]
for key in ("DAYTONA_V8_14_FRESH_REOPEN_PASS","mesh_count",
 "len(o.data.vertices)==100","len(o.data.polygons)==92",
 "all(i.packed_file","sum(o.type==\"CURVE\" for o in bpy.data.objects)==94",
 "gate.data.materials[0].name==\"Chrome\""):assert key in verify,key
render=source[names[2]]
for key in ("assert not output.exists()","DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
 "scene.render.resolution_x=480","scene.cycles.samples=4",
 "DAYTONA_V8_14_ACTUAL_CYCLES_PASS"):assert key in render,key
compare=source[names[3]]
for key in ("original_960x640_10spp_downsampled",
 "photometric_equivalence","NOT_ESTABLISHED",
 "Daytona365_v8_14_ACTUAL_CYCLES_PREVIEW.png",
 "attribution_note"):assert key in compare,key
for name,s in source.items():
 assert "bpy.ops.wm.open_mainfile(" not in s,name
 assert "OR2006C2C.EXE" not in s,name
 assert "subprocess" not in s,name
print("DAYTONA_V8_14_SOURCE_CONTRACT_PASS",len(keys),
      "guards; AST/compile/static only; real Blender validation separate")
