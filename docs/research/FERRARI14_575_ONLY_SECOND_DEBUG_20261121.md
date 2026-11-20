# Ferrari14 second-pass regression debugging — 2026-11-21 KST

## Input evidence / exact revisions
- User's broken stereo image and uploaded `FERRARI13_LOGS_20261120T162046931Z.zip`, `OutRun_vr_1.zip`, `FERRARI13_RUN_20261120T161837806Z.log` were re-opened; the actual broken runtime was old Ferrari13 DLL SHA256 `313d9925...` and host `9ecc80a9...`, with explicit `PreferD3D9Ex=false`, `DirectGpuOnly=false`, `FollowGameResolution=true`, `FrameCadenceMode=0`. The host's OpenXR target 90Hz was not met during the game: observed frame interval ~35–37ms, xrEndFrame ~23–27ms and repeated capture-frame-history-miss / present-in-flight, while Desktop Duplication was in use.
- Current recovery source: pinned normal Quest core based on `5eb417782179c0c944ac2c28fc04a223b0b130fa`, code correction commit `72c97346681f934915333719d2068fc4c74489b9` on `vr-ferrari14-stereo-recovery-normal-20261121`. **No normal VR stereo core or host source changes**.

## Second-pass real faults / insufficiencies

1. Previous A/B launch `-VR.ExternalFerrariTest=true` activated *all* installed external Ferrari slots 0–29, while also enabling special F50. This does **not isolate** the first known-good one-car test and prevents attributing visual failure to a single new sidecar.
2. The V4 loader checked only `modelMinLocalY`/static ground clearance. Original OVC4 CRC/PBR tests do **not** check actual cockpit-eye intersection or player-world camera alignment.
3. Existing PBR external vertex shader uses VS c0/c4/c8 matrices while verified game stereo c64 lineage uses a separate per-eye gate. The fixed-function diagnostic forces the well-established `SetTransform(VIEW/PROJECTION)` path so the normal stereo renderer can replace each eye's transforms, bypassing PBR while stereo is investigated.
4. The broken runtime passed `-VR.Telemetry=false`; existing `VR QUEST FERRARI EXTERNAL` instrumented route was therefore silent, so old logs do **not** establish selected car ID, external vs stock draw ownership, matrix rotation, per-eye result or offending face/mesh.

## Newly verified model bounds and what they do not show

Independently parsed actual private 575 Superamerica OVC SHA256 `16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71` on the limited N100 home workspace. Source geometry: X **-1.045525..+1.045528m**, Y **~0..+1.200004m**, Z **-2.270146..+2.270146m**, i.e. **2.091m wide, 1.200m high, 4.540m long**. Exactly 78 groups and 57,786 triangles. It is **not wildly scaled 10x or 100x**. The screenshot's large opaque foreground must still be explained by actual camera-relative pose, orientation, model's cockpit surface/roof and/or depth draw order; do not blindly alter dimensions or F11 seat settings.

## Actual source corrections (not yet HMD-proven)
- New portable `external_car_selection.hpp`: canonical retail ID aliases 15..27 → base 0..12, 29 →14, exact 28 preserved. `MatchesFerrariSelection` is fail-closed for IDs >=30 and invalid filter values.
- New settings `VR.ExternalFerrariTestCarId=-1..29` (legacy -1 all); new explicit **575-only A/B launcher selects ID 5**, which also admits tuned 20 via canonical mapping. **F50 special sidecar OFF**. All others stay stock.
- Guard **both** `PrepareF50External` and `DrawPreparedF50External` with the same canonical-car gate so a stale prepared ticket cannot replace the original car after the selected slot changes.
- `VR.ExternalFerrariDiag` adds bounded diagnostics: max four pre-draw sidecar rejects, eight replacement route/mesh receipts, four world-origin/forward/native-view/projection input matrices. The regular A/B launcher keeps diagnostic OFF; `RUN-FERRARI14-575-TRACE.cmd` explicitly enables it for short focused runs.
- Portable C++ `external_car_selection_test.cpp` exhaustively compares all observed 0..29 and requested 0..29 pairs, disallowed selection values, and tuned/base alias consistency. First new CI failed because this **test file lacked `<initializer_list>` include**; corrected at `7dd155e6`. Re-run Ferrari14 Normal-Core Stereo Recovery Gate **SUCCESS** at commit `7dd155e6`; latest source additions are bounded diagnostic prints only.

## Required acceptance (not fulfilled by C++ tests)

- GitHub Windows x86 Release Build and HUD CI for exact `72c97346...` must pass before a new DLL/patch is delivered; check artifact SHA and pack only the matched normal v0.03 x64 host. A prior 9b749fad binary is **not** interchangeable with this new selector implementation.
- Use separate Ferrari14 private TEST GAME folder, never the known-good v0.03 directory. First launch baseline car OFF, then same 575 with fixed-function ON, then only if needed the bounded matrix log launcher. Compare left/right Quest3 output, FPS, actual directReady, camera relative to transformed vehicle.
- No third-party OVC binary is to be committed publicly. The previously private 575 OVC remains on the user's copy.
- Static CI does not prove live eye rendering. No regression is declared fixed until the user's headset test confirms correct stereo, unobstructed cockpit and stable FPS.

## AI score
This is further debugging and derivative isolation on already-scored normal-VR Ferrari14 loader. Actual new accepted HMD performance is unknown. **No additional score attributed to repeated validation or re-reporting**; any distinct future implementation score must consult `thp32tt/ai-dev-lab@main/AI_SCOREBOARD.md` and have a unique validated outcome.
