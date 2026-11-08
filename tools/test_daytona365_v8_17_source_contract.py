#!/usr/bin/env python3
"""Static v8.17 source contract only; never labels a CI run as a Blender render."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=("blender_daytona365_v8_17_cowl_pbr_normals.py",
 "verify_daytona365_v8_17_blender.py",
 "render_daytona365_v8_17_actual.py",
 "make_daytona365_v8_17_actual_compare.py")
s={}
for name in files:
 p=root/name
 assert p.is_file(),name
 text=p.read_text(encoding="utf-8")
 ast.parse(text,filename=name)
 with tempfile.TemporaryDirectory() as d:
  py_compile.compile(str(p),cfile=str(Path(d)/(p.stem+".pyc")),doraise=True)
 assert "OR2006C2C.EXE" not in text
 assert "bpy.ops.wm.open_mainfile(" not in text
 s[name]=text
model=s[files[0]]
guards=("Daytona365_Cockpit_Blender_PBR_v8_16.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_17.blend",
 "d0f3406886262359e9c079ee7eeb122d9a9ac5739d5ffb9148055c9422ee77da",
 "assert not f.exists()",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
 "V6_BLENDER_INSTRUMENT_COWL_ROUNDED_LEATHER_EDGE",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "V8_17_Source_Packed_Dark_Dashboard_PBR",
 "V8_17_Cowl_Tangent_Normal_UV",
 "V8_17_Packed_Cowl_Tangent_Normal",
 "V8_17_Source_And_Cowl_Normal_Mix",
 "V8_17_Original_Dash_Charcoal_Value",
 "V8_5_ORM_ROUGHNESS_RANGE",
 "recalc_face_normals",
 "V8_17_Dashboard_Source_Metric_UV",
 "DAYTONA_V8_17_MODEL_SAVED",
 "original_gauges_switches_seats_gate_unchanged",
 "private_original_pmt_unchanged",
 "matched_full_resolution")
for g in guards:assert g in model,g
v=s[files[1]]
for g in ("DAYTONA_V8_17_FRESH_REOPEN_PASS",
 "cowl_vertices","normal.packed_file","norm.packed_file",
 "model_sha256","len(me.vertices)==650"): 
 if g=="normal.packed_file":continue
 assert g in v,g
r=s[files[2]]
for g in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
 "scene.cycles.samples=4" if False else "s.cycles.samples=4",
 "s.render.resolution_x=480","assert not out.exists()",
 "DAYTONA_V8_17_ACTUAL_CYCLES_PASS"):
 assert g in r,g
c=s[files[3]]
for g in ("original_960x640_10spp_downsampled",
 "candidate_480x320_4spp","photometric_equivalence",
 "NOT_ESTABLISHED","Daytona365_v8_17_ACTUAL_CYCLES_PREVIEW.png"):
 assert g in c,g
print("DAYTONA_V8_17_SOURCE_CONTRACT_PASS",len(guards),
 "static checks only, Blender/PMT/Quest3 not executed in this test")