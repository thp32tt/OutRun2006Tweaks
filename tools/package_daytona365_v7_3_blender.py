"""Create ONLY private editable Daytona v7.3 Blender artifact archive."""
from pathlib import Path
import hashlib,json,zipfile
root=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
edit=root/"blender_v7"
blend=edit/"Daytona365_Cockpit_Blender_PBR_v7_3.blend"
qa=json.loads((edit/"DAYTONA_V7_3_VERIFIED.json").read_text())
assert qa["sha256"]==hashlib.sha256(blend.read_bytes()).hexdigest()
readme="""Ferrari 365 GTS/4 Daytona — Blender actual rework v7.3
Personal/private 3D modeling WIP. No game install, no OVC, no DLL, no original PMT.

GOAL: supplied generated-image reference classic Daytona tan leather, black dash,
walnut 3-spoke wheel, smooth and anatomically plausible seats.

Real changes: removed 67 overlapping old objects; rebuilt both seat cushions and
backs as continuous meshes, with integrated padded horizontal pleats; corrected
the long steering column so it begins below the instrument cluster; fixed
v6 floor mats that were accidentally vertical, added grounded black carpet and
under-dash lower face; rebuilt nine pedal rubber ribs; replaced faceted visible
wheel rim with one true smooth walnut torus while leaving source rim hidden;
added photo palette BaseColor/normal/ORM/height textures and connected them
to actual Blender shader nodes. Original wheel spoke geometry and logo retained.

Open:
 Daytona365_Cockpit_Blender_PBR_v7_3.blend  in Blender 4.5 or newer.
Packed PBR images require no external files; individual PNGs included for edits.
Preview is a real Blender Cycles render from the editable model, not an AI image.
Normal/ORM/height are editable Blender materials, but independent 3D volume
texture sampling or game runtime compatibility has not been proven.
No actual Quest3/VDXR gameplay check performed, game/loader untouched.

Reference material note: tan grain sample is taken from the image generated
in this chat. Black and walnut are palette-matched procedurally after their
micro-crop transport failed, not a literal photo projected onto a mesh.
This is still NOT photorealistic finished work: remaining seat joints,
accurate Ferrari original component geometry, dashboard underparts and
high-resolution custom UV atlases need further modeling.

SHA256 (blend): """+qa["sha256"]+"\n"
(edit/"README_DAYTONA_BLENDER_V7_3.txt").write_text(readme)
files=[
blend,
edit/"DAYTONA_V7_3_VERIFIED.json",
edit/"DAYTONA_V7_3_BUILD_MANIFEST.json",
edit/"DAYTONA_V7_2_BUILD_MANIFEST.json",
edit/"DAYTONA_V7_1_BUILD_MANIFEST.json",
edit/"Daytona365_v7_3_ACTUAL_CYCLES_CABIN.png",
edit/"README_DAYTONA_BLENDER_V7_3.txt"]
files+=sorted((edit/"textures").glob("*.png"))
files.append(edit/"textures/V7_MATERIAL_MANIFEST.json")
assert all(p.is_file() for p in files)
out=root/"Daytona365_BLENDER_TARGET_REWORK_v7_3_PRIVATE.zip"
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for p in files:
  z.write(p,"Daytona365_Blender_v7_3/"+str(p.relative_to(edit)))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 content=z.read("Daytona365_Blender_v7_3/"+blend.name)
 assert hashlib.sha256(content).hexdigest()==qa["sha256"]
 assert all(not n.endswith((".ovc",".exe",".dll",".sz")) for n in z.namelist())
 print(json.dumps({"archive":str(out),"size_bytes":out.stat().st_size,
 "entries":len(z.namelist()),"blend_sha256":qa["sha256"],
 "zip_verify":"PASS","no_game_binary":True},indent=2))