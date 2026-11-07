from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
ED=ROOT/"editable_v5"
README="""Ferrari 365 GTS/4 Daytona | Editable 3D cockpit v5 (PRIVATE)

This package is the real editable GLB derived from the original OutRun 2006 PMT
and the v4 source mesh. It is NOT an AI-generated picture, not a gameplay capture
and NOT a finished OutRun/Quest loader build.

Modeling rework:
 - original separately-stored 3-spoke steering geometry mounted once
 - independent, curved upper dashboard and padded instrument face
 - sculpted tan front seat cushion/backrest pairs, side bolsters and piping
 - raised black leather band inserts, threads, reclining head cushion edges
 - rounded door cards, trim, shifter/knob and dash vent rings
 - previous photo 3D switch hardware and instrument gauge geometry retained

GLB materials:
 - 9 photosource-based base colors
 - 9 tangent-space normal maps in GLB standard normalTexture slots
 - 9 packed ORM maps (Occlusion R, Roughness G, Metallic B) in glTF slots
 - 9 optional height maps embedded as metadata and separately in PNG.
The code confirmed in the GitHub PBR loader branch is NORMAL + ORM, not
independent 3D/volume voxel texture sampling. Height maps are authoring assets
only. Do not confuse glTF KHR_materials_volume with a 3D texture sampler.

Open the GLB in Blender:
 File > Import > glTF 2.0 > Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb
 All standard PBR textures are embedded. PNG files are provided for adjustments.
 There is no need to build or install the OVC into the game for this step.

Known limitations:
 - source seat spatial alignment has not been checked in Quest 3 hardware
 - custom software-preview renderer sorts triangle polygons approximately, so
   it can render broken-looking intersections that are not necessarily in GLB
 - macro photographed shadow geometry was intentionally removed from leather
 - real Blender professional visual/QC/UV cleanup is NOT claimed completed
 - PBR loader on other development branch was inspected, not changed
 - original PMT, Dino, DLL and game install were NOT modified.

Source current private model root:
 /home/chatgpt-runner/work_handoff/daytona365_rework_20261107/editable_v5
Private personal modding derivatives; do not publicly redistribute original assets.
"""
(ED/"README_V5_KO.txt").write_text(README,encoding="utf-8")
files=sorted(ED.glob("*.png"))+sorted(ED.glob("*.jpg"))+[
 ED/"Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb",
 ED/"V5_EDITABLE_MODEL_MANIFEST.json",
 ED/"README_V5_KO.txt"]
assert all(p.exists() for p in files)
archive=ROOT/"Daytona365_EDITABLE_ONLY_PBR_v5_PRIVATE.zip"
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for p in files:z.write(p,"Daytona365_EDITABLE_v5/"+p.name)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 glb=z.read("Daytona365_EDITABLE_v5/Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb")
 sha=hashlib.sha256(glb).hexdigest()
 manifest=json.loads((ED/"V5_EDITABLE_MODEL_MANIFEST.json").read_text())
 assert sha==manifest["sha256"]
 assert not any(n.endswith(".ovc") or "obj_plcar_dayts_pmt.sz" in n for n in z.namelist())
 print(json.dumps({"zip":str(archive),"size":archive.stat().st_size,
 "entries":len(z.namelist()),"glb_sha":sha,"glb_triangles":manifest["triangles"],
 "no_game_binary":True,"zip_verified":True},indent=2))