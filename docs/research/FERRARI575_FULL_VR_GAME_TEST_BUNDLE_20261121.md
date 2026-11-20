# Ferrari 575 Superamerica HQ gauge hybrid — Ferrari13 V4 full Quest3 game-test bundle (2026-11-21 KST)

## Real bundled deliverable

- Private full test ZIP: `FERRARI14_VR_575_HYBRID_PRIVATE_TEST_20261121.zip`, **607,873,984 bytes**.
- ZIP SHA256: `32b7d2b10a44ee0d5230d38a34a16e83117c54aae331cd1ac7bf1aa6ac1a0327`.
- Stored owner-only in the existing Google Drive private test folder, Drive file ID `1ON4ooc_-dEu0_HTtrGc1upBDE_02e9zC`, observed provider URL `https://drive.google.com/file/d/1ON4ooc_-dEu0_HTtrGc1upBDE_02e9zC/view?usp=drivesdk`. Google Drive metadata size matched, `shared=false`. No public link permission created.
- Parent: `FERRARI13_VR_RECOVERY_MATCHED_HOST_20261119.zip` (599,715,065 bytes; SHA256 `1d3c7cb394392615a461bc315fcd8aeac274ad581bcb32cd29ea1be6260d8d3e`) containing **13 original exact-body test models, 13 dashboard overlays, V4 DLL and matched x64 OpenXR host**.
- Added **575 Superamerica** native OVC4: `FERRARI575_PAYLOAD/car_id_05.ovc`, **8,194,803 bytes**, SHA256 `16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71`, unique 57,786 triangles and native speed/RPM binding.
- **Artifact validation:** ZIP all entries CRC PASS; **48/48** parent Ferrari13 ZIP entries were independently byte-for-byte compared with no changes; **7** added entries and **55** total; model OVC SHA matches; V4 runtime `dinput8.dll` SHA256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e`; launcher explicitly includes `-VR.ExternalFerrariTest=true`; original game `OR2006C2C.EXE` is **not included**.
- New bundle files: `START-FERRARI575-VR.cmd`, `VERIFY-FERRARI575-VR.cmd`, `FERRARI575_RUN.ps1`, `RESTORE-FERRARI575.ps1`, `FERRARI575_PAYLOAD/car_id_05.ovc`, `README_575_GAME_TEST_KO.txt`, `FERRARI575_MODEL_STATUS.json`.
- Launcher: hash-checks model + bundled runtime source DLL and parent manifest before doing anything; verify-only mode modifies nothing; Start installs 575 slot **ID 05** with independent previous sidecar backup and existing Ferrari13 base installed by its own SHA/backup installer; launches existing Ferrari13 recovery V4 runtime with the experimental model. Restore script verifies installed OVC SHA before revert.
- User steps: **make a separate copy of the legitimate game folder first**, unzip entire ZIP into that copy, close other game and host processes, run `VERIFY-FERRARI575-VR.cmd` optionally, then `START-FERRARI575-VR.cmd`; select **575 Superamerica**, enter driving stage, camera 1. If white screen persists, `COLLECT-FERRARI13-LOGS.cmd` saves diagnostics.

## Critical limitations

- This is a **launch-capable test archive** for the user's licensed local game, **not a shipped, proven-working VR release**. Original executable/game files must already be present. Actual Windows and Quest 3 launch were **NOT performed** in this task.
- Crucially **the parent Ferrari13 V4 runtime exhibited a white screen on user hardware** during the prior 2026-11-19 test: menu Present ran but stereo frame publication stayed zero. A later attempt with matched host and D3D9 classic recovery was **not user-validated**. The new ZIP **preserves** that parent runtime and therefore may encounter the same failure. Do not imply the 575 model change repaired startup or that the 14th car visually loads.
- The separate normal Quest cockpit v0.03 release branch, reported to render normally by the user, was **NOT modified**. No unsupported drop-in mixing with v0.03 normal DLL; it may not contain the V4 external model loader.
- 575 hybrid was Blender/GLB/OVC4 statically checked, but Blender driver-eye Workbench renders still show possible dashboard occlusion, and in-game needle calibration is pending.
- Because third-party rights are unverified, deliverable stays owner-private in Drive, no derived vehicle bytes were publicly committed.

## Score/accounting

This is deployment packaging and re-verification of the **already scored** run `FERRARI575-EXACT-HQCLUSTER-HYBRID-OVC4-20261121-16C15B9B`; no new model conversion, new source, corrected VR runtime, or user-confirmed Quest3 rendering. **New scoring +0**, no duplicated independent achievement.
