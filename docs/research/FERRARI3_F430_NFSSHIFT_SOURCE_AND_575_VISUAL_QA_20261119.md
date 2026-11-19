# Ferrari remaining three — new Shift-origin F430 Spider source audit and 575 static eye QA
Date: 2026-11-19 KST

## Purpose and hard gates
This report records **actual new external-source acquisition and bounded geometry inspection**, not an installed model improvement. Preserve donor/default package 13/16 high-quality exact, optional-inclusive 16/16 exact candidate inventory, prior verified source binaries, and normal VR runtime branch.

## Ferrari F430 Spider — a distinct NFS Shift -> MW source (new actual file)
- Original project source listing: https://www.nfs-cars.com/need-for-speed-most-wanted/7/files/view/11244/
- Original distributor credits Alexc12fr for Need for Speed: Most Wanted conversion, EA/SMS for the original Need for Speed: Shift geometry/textures.
- Site direct download (no executable run): https://www.nfs-cars.com/files/download/send/11244/1329220691-F430-Spider.zip
- Retrieved actual ZIP **1,081,152 bytes**, SHA256 `5b22d2bd21cd000e54ed4584705ec2bd9716835d290d0eeb40bf1f8fdc0a7bd4`, `zipfile.testzip() == None` PASS.
- Nested 7z **1,080,657 bytes**. Extracted using the installed 7z archive extractor; no installer, mod loader, game or executable was invoked.
- Original `ADDONS/CARS_REPLACE/RX8/GEOMETRY.BIN` **11,612,160 bytes**, SHA256 `d80e9fa0a2d90e1bfcb8ff61a17035f83acd01da68028f340e3972242d9e4c53`.
- Original `textures.bin` **735,525 bytes**, SHA256 `2404ec6bab635bc17cd9024d1316a445778e74e4fd5e706d55ac996fa6ce08a5`. A texture container exists; individual DDS formats or material mapping **not decoded or visual-tested**.

### Actual bounded native container inspection
- Read-only EA chunk walk supported by publicly documented chunk IDs: `0x80134000` root, `0x80134010` part, `0x00134011` part metadata, `0x80134100` mesh, `0x00134900` descriptor, `0x00134B01` vertex stream, `0x00134B02` submeshes and `0x00134B03` indices.
- **54 complete part containers**, each with matching header, descriptor, vertex and index stream. **0 chunk-boundary errors**.
- Actual part names include `FRX8_BASE_A`, `FRX8_KIT00_BODY_A`, `FRX8_KIT01_BODY_A` … `FRX8_KIT05_BODY_A`; additional LODs `_B` to `_E` are stored independently.
- **Never add all six mutually exclusive body-kit variants or all LOD levels** when estimating one stock car. The selected A-level stock `BASE_A` + `KIT00_*_A` front/rear brakes, tire and driver has **at most approximately 23,541 triangles**, based only on the per-part 16-bit index-stream byte-length / 6. Some streams contain alignment padding, so **this is a conservative upper-bound estimate, not a fully decoded exact triangle count or game draw validation**.
- Above does not exceed the previous optional exact standard F430 Spider **77,979 triangles** or 16M donor **565,172 triangles**. Other quality factors (textures, trim, roof shape, cockpit) are not proven to compensate.
- **Reject as higher-quality default and optional replacement.** No new F430 GLB/OVC4 was produced, no removal of existing candidates, no source binary added to public GitHub. The downloaded original derives from copyrighted commercial game assets; permission to redistribute derived vehicle models has not been verified.

### On-host private raw evidence
N100 authorized home-relative path:
`ferrari_resume_20261119/f430_spider_nfsshift_mw_20261119/`
Reports: `download_probe.json`, `asset_inspect.json`, `geometry_structure_report.json`, `geometry_a_summary.json`. Raw ZIP, nested 7z and source BIN reside solely on N100 in this private test directory.

## Ferrari 575 Superamerica — offline static cockpit visibility investigation
- Input is the **previously created** exact privately gauge-bound GLB SHA256 `07ba422ae28628fb14244cd2bc68ed40c4f022c173c46c2ed799bc2aaddff2b1` (no newly acquired source, no new OVC4 conversion).
- With Blender **5.2.4 LTS** N100 2-thread CLI, the heavyweight Cycles attempt did not complete, no image was produced; that aborted attempt is not a QA PASS.
- The lightweight `BLENDER_WORKBENCH` rendering passed:
  1. Driver-left whole-model view saved `gauge_visual_qa/driver_left_workbench.png`, but the external body/roof occluded the actual dashboard from that arbitrary camera.
  2. Interior-only visibility control (body hidden **for render only**, no exported geometry changes) saved `gauge_visual_qa/interior/left_eye_interior.png` and `cluster_close.png`.
  3. Gauge-only isolation saved `gauge_visual_qa/cluster_only/gauge_cluster_only.png`.
- The GLB scene has **78 mesh objects**, speed needle `ARROW_SPEED` exactly once at Blender world [-0.285382, 0.132986, 0.788789], RPM needle `ARROW_RPM` exactly once at [-0.399135, 0.131489, 0.802759]; these reflect the earlier static correctly encoded native dashboard pivots.
- **Static render caveat:** Workbench treats glass and textured materials as opaque / simplified, and the isolated cluster appears largely flat grey, with the two colored needle meshes not independently visible from the tested viewpoint. Therefore the renders only validate successful parsing, offline scene existence and approximate model hierarchy. They **DO NOT verify** correct in-game dial direction, absence of gauge occlusion or matching viewpoint. Render-only object visibility changes are not baked back into the private GLB/OVC4.
- The existing optional 575 native gauge OVC4 SHA256 `222eca041b07623f7d489c5cb675464f43859939d865ff63e3f26b08df49683b` and owner-private optional package remain **unchanged** and Quest 3 runtime **NOT TESTED**.

## Source search exclusions and next gates
- A high-resolution 328 GTS from 88Cars3D, 3DExport or CAD Browser is paid or has unavailable license/source binaries: not purchased or treated as a proven improvement.
- Several newer Assetto Corsa F430 downloads are F430 **coupe**, Scuderia or Challenge. They are not the required 2005 Spider.
- Newly found Ferrari 575 models often depict the roofed 575M Maranello, rather than the Superamerica's unique rotating glass Revocromico roof. Do not promote without exact body identity and full interior geometry.
- No additional free, rights-verified, exact full-cockpit source beating the current donor quality gate was found.
- Next gate for any source is full original geometry+materials+textures, exact trim/roof, axle and ride-height fitting, independent OVC4 static verification, then **actual Quest 3 driver-eye game visual comparison**.

## End state and AI2 competition
- 16/16 private optional-inclusive exact variant candidates (unchanged).
- 13/16 high-quality exact default models (unchanged).
- No runtime code changes, no extra new installed car or game success claim.
- Latest verified AI2 SSOT cumulative **2871** at commit `df479e420c27ea4222a168941b810315fb17db0c`. This source-only acquisition and recheck is **+0**: 2871 + 0 = 2871. No duplicate points for previous Superamerica/328 conversions, rebase, or QA.
