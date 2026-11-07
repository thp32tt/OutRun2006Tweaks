#!/usr/bin/env python3
"""Immutable private editable Daytona v8.6 Blender checkpoint archive.

No source PMT/OVC/DDS/game binaries or original .blend in the ZIP.
The actual original PMT *comparison PNG* is an evidence render only.
"""
import hashlib,json,os,zipfile
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
dest=ROOT/"Daytona365_BLENDER_REWORK_v8_6_PRIVATE.zip"
assert not dest.exists(),"Never overwrite a private archive"
names=[
 "Daytona365_Cockpit_Blender_PBR_v8_6.blend",
 "Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_ORIGINAL_vs_V8_5_vs_V8_6_ACTUAL_CYCLES_PREVIEW_COMPARE.png",
 "DAYTONA_V8_6_BUILD_MANIFEST.json",
 "DAYTONA_V8_6_VERIFIED.json",
 "DAYTONA_V8_6_PREVIEW_RENDER_PROVENANCE.json",
 "DAYTONA_V8_6_COMPARE_PROVENANCE.json",
 "blender_daytona365_v8_6_source_contoured_console_seats.py",
 "verify_daytona365_v8_6_blender.py",
 "render_daytona365_v8_6_actual.py",
 "make_daytona365_v8_6_actual_compare.py",
 "test_daytona365_v8_6_source_contract.py"
]
report=json.loads((W/"DAYTONA_V8_6_BUILD_MANIFEST.json").read_text())
assert report["new_sha256"]=="cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4"
assert hashlib.sha256((W/names[0]).read_bytes()).hexdigest()==report["new_sha256"]
details={}
for name in names:
 p=W/name
 assert p.is_file(),p
 assert p.stat().st_size>0
 assert not name.lower().endswith((".pmt",".ovc",".dds",".exe",".dll"))
 details[name]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
 for name in names:
  archive.write(W/name,arcname="Daytona365_v8_6/"+name)
with zipfile.ZipFile(dest) as archive:
 assert archive.testzip() is None
 assert len(archive.namelist())==len(names)
 assert all(x.startswith("Daytona365_v8_6/") for x in archive.namelist())
meta={
 "status":"DAYTONA_V8_6_EDITABLE_PRIVATE_ZIP_VERIFIED",
 "file":dest.name,
 "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "bytes":dest.stat().st_size,
 "entry_count":len(details),
 "entries":details,
 "render_validation":"PREVIEW_ONLY",
 "full_resolution_matched_cycles":"UNTESTED",
 "game_runtime_ovc_Quest3":"UNTESTED"
}
(ROOT/"DAYTONA_V8_6_PRIVATE_PACKAGE_REPORT.json").write_text(json.dumps(meta,indent=2))
print("DAYTONA_V8_6_PRIVATE_PACKAGE_PASS",json.dumps({k:meta[k] for k in ("file","bytes","sha256","entry_count")}),flush=True)
