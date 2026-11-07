#!/usr/bin/env python3
"""Package only private editable Daytona v8.5 Blender checkpoint and real evidence.

No original game PMT/DDS/OVC/EXE or other car source files.
"""
import hashlib,json,os,zipfile
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
zip_path=root/"Daytona365_BLENDER_REWORK_v8_5_PRIVATE.zip"
assert not zip_path.exists(),"Do not overwrite prior private package"
names=[
 "Daytona365_Cockpit_Blender_PBR_v8_5.blend",
 "Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_ORIGINAL_vs_V8_5_ACTUAL_PREVIEW_COMPARE.png",
 "DAYTONA_V8_5_BUILD_MANIFEST.json",
 "DAYTONA_V8_5_VERIFIED.json",
 "DAYTONA_V8_5_PREVIEW_RENDER_PROVENANCE.json",
 "DAYTONA_V8_5_COMPARE_PROVENANCE.json",
 "blender_daytona365_v8_5_geometry_uv_pbr.py",
 "verify_daytona365_v8_5_blender.py",
 "render_daytona365_v8_5_actual.py",
 "make_daytona365_v8_5_actual_compare.py",
]
for name in names:
 assert (w/name).is_file(),name
assert hashlib.sha256((w/names[0]).read_bytes()).hexdigest()=="bac28640d88c745b5f276b1ecb5c2ae730e54660fb9526432aeb8c09be390ef8"
details={}
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 for name in names:
  p=w/name
  z.write(p,arcname="Daytona365_v8_5/"+name)
  details[name]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(names)
 assert not any(x.lower().endswith((".ovc",".pmt",".dds",".exe",".dll")) for x in z.namelist())
meta={"status":"PRIVATE_EDITABLE_CHECKPOINT_ZIP_VERIFIED",
"file":zip_path.name,"size":zip_path.stat().st_size,
"sha256":hashlib.sha256(zip_path.read_bytes()).hexdigest(),
"entries":details,"render_validation":"PREVIEW_ONLY",
"full_resolution_cycles":"UNTESTED","game_runtime":"UNTESTED"}
(root/"DAYTONA_V8_5_PRIVATE_PACKAGE_REPORT.json").write_text(
 json.dumps(meta,indent=2),encoding="utf-8")
print("DAYTONA_V8_5_PRIVATE_ZIP_PASS",json.dumps({"file":meta["file"],"bytes":meta["size"],"sha256":meta["sha256"],"entry_count":len(details)}),flush=True)
