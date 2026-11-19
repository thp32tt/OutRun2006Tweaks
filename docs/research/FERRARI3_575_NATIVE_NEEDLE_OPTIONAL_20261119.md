# Ferrari 575 Superamerica exact native speed/RPM optional QA — 2026-11-19 KST

## Scope and non-regression gate
An **optional private exact Ferrari 575 Superamerica OVRCABH4** was generated with 2 native speed/RPM mesh bindings. This is not a new high-poly source and is not promoted into the 16-car high-quality default: 51,444-triangle exact car still has lower geometry count than 200,071-triangle 575M donor. Real Quest 3 visuals and needle direction/angle calibration remain **UNTESTED**. Default high-quality exact package stays **13/16** and optional-inclusive exact inventory stays **16/16**.

## Verified source and authored changes
- Original exact Ferrari Superamerica GLB: 4,899,840 bytes; SHA256 765e89af297a5823aa751c89835c1de97a75e6eac1e746dd38c17b8b629f46a4. Source is an external Assetto Garage model; no public redistribution license independently confirmed.
- Donor full 575M GLB: 200,071 triangles; 79 images; 45 anonymous materials in a *single mesh with 104 primitives*. Source body geometry cannot be safely split by unverified materials; donor-to-exact alignment also differs in height. No speculative visual merge was performed because it could create duplicated body/glass and z-fighting.
- Exact GLB has 78 named meshes and native child needle mesh nodes ARROW_SPEED / ARROW_RPM whose parents unfortunately share identical names. Renamed only their nonmesh parent aliases, preserving child mesh names and existing node transforms. Native bindings resolve child mesh node origins and signed axes through existing game-local transform.
- Previously documented malformed UV accessor 137, index 2031 corrected from [638.5, -20721] to [11.5, -8]. Independent binary comparison: exactly 6 differing bytes in the old versus newly authored BIN chunk, all within the one VEC2 UV. Original mesh indices, 51,444 triangles, 43 images, 30 materials and geometry buffers are unchanged.
- Derived private GLB 4,899,864 bytes, SHA256 07ba422ae28628fb14244cd2bc68ed40c4f022c173c46c2ed799bc2aaddff2b1.
- Explicit provisional binding ranges: speed 0..320, RPM 0..10000, angle sweep 0..260 degrees. **Not calibrated against actual gauges in-game.**

## Actual native conversion and independent checks
Existing local native conversion code: external_superamerica_exact_dxt_20261117/ferrari_batch_converter.py.
Isolated N100 source/QA workspace: ferrari_resume_20261119/575_exact_native_binded_20261119; Blender 5.2.4 Python NumPy and isolated Pillow.
- Strict source audit: 1 READY; 0 BLOCKED; 2 unique dashboard node bindings.
- Convert: PASS. Native second-pass verify: PASS.
- New OVC4 bytes: 7,157,147; SHA256 222eca041b07623f7d489c5cb675464f43859939d865ff63e3f26b08df49683b.
- Header, independent parser, geometry totals, CRC32, all DDS sections, PBR extension, trailer boundaries PASS.
- 78 groups, 56,323 vertices, 51,444 triangles, 30 materials, 16 normal-map materials.
- Native speed binding group 37; pivot approx [-0.286601,0.785295,-0.251297]; rotation axis [0,0,-1].
- Native RPM binding group 38; pivot approx [-0.400354,0.799265,-0.249801]; rotation axis [0,0,-1].
- No static failures. **No actual game or Quest3 runtime success claimed.**

## Optional private installer package
- File: FERRARI575_EXACT_NATIVE_GAUGES_OPTIONAL_PRIVATE_20261119.zip.
- ZIP size 7,164,780 bytes; SHA256 50665bcdec1c65ad0cd57c68508687111cafafe2b62770bd68b8d8a0117a80ce. 5/5 ZIP members CRC PASS.
- Includes ExternalCars/car_id_05.ovc, APPLY-575-EXACT-NATIVE.ps1, RESTORE-575-PREVIOUS.ps1, README_FIRST.txt, independent_validation.json.
- Windows installer defaults VERIFY-ONLY. Optional install requires -Install and -AllowLowerDetail and a valid game root with OR2006C2C.EXE; backs up the previous car_id_05.ovc and checks new SHA; rollback script refuses unexpected target modifications. **Not Windows-integration tested**.
- User private Google Drive upload independently confirmed: folder OutRun2006_Private_Model_Tests, target ZIP verified size 7,164,780 and file owner-only permission (shared=false). No public binary uploaded to GitHub.

## Extra source discovery rejection
- 328 GTS: a full-cockpit exact commercial option exists at https://88cars3d.com/product/ferrari-328-gts-3d-model/ but not free and not acquired; no new proven source surpasses the existing exact optional OVC4.
- 575: recent 575M Maranello downloads describe the Superamerica only in generic history, not as proven distinct rotating-roof mesh. Not an exact replacement.
- F430: Challenge, Scuderia and F430 coupe downloads are not Spider. Paid exact Spider models were not purchased; the previously inspected CadNav F430 F1 Spider import is visibly damaged/untextured, rejected.

## Distinct normal-base integration branch
The normal VR base was separately rebuilt in thp32tt/OutRun2006Tweaks@vr-ferrari16-v4-rebased-normal-20261119 (scoreboard commit df479e420c27ea4222a168941b810315fb17db0c). No claim that this optional OVC was installed or runtime-tested against that new branch. The old working normal VR setup is unchanged.

## Competition score
GitHub SSOT confirmed latest AI2 2871 (separate normal-base rebuild). This optional static gauge binding has not had actual VR gauge calibration, so score change +0; do not rescore earlier exact 575 conversion or the separate normal-base runtime task.
