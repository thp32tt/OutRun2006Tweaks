#!/usr/bin/env python3
"""v8.12 source-only CI contract: checks code, not Blender or game runtime."""
import ast,py_compile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
files=("blender_daytona365_v8_12_original_shell_exposed_lip_pbr.py",
 "verify_daytona365_v8_12_blender.py",
 "render_daytona365_v8_12_actual.py",
 "make_daytona365_v8_12_actual_compare.py")
texts={}
for name in files:
 path=root/name
 assert path.is_file(),name
 source=path.read_text(encoding="utf-8")
 ast.parse(source,filename=name)
 with tempfile.TemporaryDirectory() as temp:
  py_compile.compile(str(path),cfile=str(Path(temp)/(path.stem+".pyc")),doraise=True)
 texts[name]=source
build=texts[files[0]]
keys=("Daytona365_Cockpit_Blender_PBR_v8_11.blend",
 "Daytona365_Cockpit_Blender_PBR_v8_12.blend",
 "f53ecaf68bea214831dd706baf79e12ab36d9c253febfe8b5bf367c1d13f9cb1",
 "assert not DEST.exists()","V5_","SEAT_RECLINED_PADDED_BACK",
 "TanLeather","V8_12_Source_Charcoal_Original_V5_Back_Return_PBR",
 "V8_11_Source_Dark_Headrest_Return_PBR","V8_5_ORM_ROUGHNESS_RANGE",
 "V8_9_PMT_CHARCOAL_DESATURATION",
 "NORMAL_MAP","BUMP","TEX_IMAGE","packed_file",
 "recalc_face_normals","mesh.uv_layers.active","len(mesh.vertices)==1617",
 "PMT017_z_max","not ob.hide_render",
 "original_game_files_modified","Quest3_tested",
 "DAYTONA_V8_12_MODEL_SAVED")
for key in keys:assert key in build,key
verify=texts[files[1]]
for key in ("FRESH_REOPEN_PASS","len(ob.data.vertices)==1617",
 "len(ob.data.polygons)==3072","all(i.packed_file","UVMap",
 "V8_11_CROWN_GEODESIC_UV","V8_10_DOOR_GEODESIC_UV"):
 assert key in verify,key
rend=texts[files[2]]
for key in ("DAYTONA365_APPROVED_HEAVY_RENDER_HOST",
 "assert not output.exists()","DAYTONA_V8_12_ACTUAL_CYCLES_PREVIEW_PASS"):
 assert key in rend,key
comp=texts[files[3]]
for key in ("original_960x640_10spp_downsampled",
 "photometric_equivalence","NOT_ESTABLISHED","Daytona365_v8_12_ACTUAL_CYCLES_PREVIEW.png"):
 assert key in comp,key
for name,source in texts.items():
 assert "bpy.ops.wm.open_mainfile(" not in source,name
 assert "OR2006C2C.EXE" not in source,name
 assert "subprocess" not in source,name
print("DAYTONA_V8_12_SOURCE_CONTRACT_PASS",
 len(keys),"guards; AST/compile/static only, not Blender render")