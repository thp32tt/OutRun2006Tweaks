#!/usr/bin/env python3
"""Private editable Daytona v8.7 archive: no original PMT/DDS/OVC/exe binaries."""
import hashlib,json,os,zipfile
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
zip_path=root/"Daytona365_BLENDER_REWORK_v8_7_PRIVATE.zip"
assert not zip_path.exists(),"Never overwrite the private checkpoint ZIP"
names=[
 "Daytona365_Cockpit_Blender_PBR_v8_7.blend",
 "Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png",
 "Daytona365_ORIGINAL_vs_V8_6_vs_V8_7_ACTUAL_CYCLES_PREVIEW_COMPARE.png",
 "DAYTONA_V8_7_BUILD_MANIFEST.json",
 "DAYTONA_V8_7_VERIFIED.json",
 "DAYTONA_V8_7_PREVIEW_RENDER_PROVENANCE.json",
 "DAYTONA_V8_7_COMPARE_PROVENANCE.json",
 "blender_daytona365_v8_7_seat_source_contours_underdash.py",
 "verify_daytona365_v8_7_blender.py",
 "render_daytona365_v8_7_actual.py",
 "compare_daytona365_v8_7_actual.py",
 "test_daytona365_v8_7_source_contract.py"]
build=json.loads((w/"DAYTONA_V8_7_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256((w/names[0]).read_bytes()).hexdigest()==build["new_sha256"]
details={}
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 for n in names:
  p=w/n
  assert p.is_file(),n
  assert not n.lower().endswith((".pmt",".dds",".ovc",".dll",".exe"))
  z.write(p,arcname="Daytona365_v8_7/"+n)
  details[n]={"bytes":p.stat().st_size,
              "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(names)
 assert all(n.startswith("Daytona365_v8_7/") for n in z.namelist())
report={
 "status":"DAYTONA_V8_7_PRIVATE_EDITABLE_PACKAGE_VERIFIED",
 "file":zip_path.name,"size":zip_path.stat().st_size,
 "sha256":hashlib.sha256(zip_path.read_bytes()).hexdigest(),
 "files":details,"count":len(names),
 "render_validation":"PREVIEW_ONLY",
 "full_resolution":"UNTESTED","game_runtime":"UNTESTED"}
(root/"DAYTONA_V8_7_PRIVATE_PACKAGE_REPORT.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_7_PRIVATE_PACKAGE_PASS",json.dumps({k:report[k] for k in ("file","size","sha256","count")}),flush=True)
