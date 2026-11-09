# Original Quest APK / PC view1 camera yaw code comparison, 2026-11-10 KST

## User physical feedback
In PCVR camera mode1 while turning, camera yaw can precede vehicle-body yaw, reminiscent of third-person chase view. Quest APK reportedly did not show this discrepancy to the same extent. This is distinct from F0 player-body vertical bounce.

## Independently verified native sources
- PC decomp `r4dius/outrun2-decomp/src/driving/pc_race_camera.cpp`: original `race_camera_yaw_483110` uses mode 0 OR 1 and reads body car +0x2E, auxiliary heading car +0x1FE, steering +0x162, speed +0x1C4, and camera transition +0x346/+0x348. In moving gameplay, cockpit camera yaw is NOT necessarily equal to body yaw. `race_camera_car_matrices_484810` builds camera +0x200/+0x240 using that source and +0x280 using body heading.
- Original user's Quest APK ARM64 core private N100 ELF `apk/_static_out/liboutrun_quest_core.so`: SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`, size 21,959,856. ARM64 `race_camera_yaw_483110` at 0x1190B30 (1840 bytes) reads view at [x0,#842], +0x1FE auxiliary at [x19,#510], body +0x2E at [x19,#46], steering +0x162 at [x19,#354]. Branch at 0x1190B80 handles both view 0 and 1. `race_camera_car_matrices_484810` at 0x1191260 calls same yaw source at 0x11914F0 / 0x1191688.
- The Quest-native `run_game::$_2` additionally has conditional angle-dependent per-eye inverse pose and view matrix path 0x2E1B00..0x2E1D18 involving sincosf/atan2f. Capture flags and actual physical Quest HMD activation are not established; the PCVR path is NOT proven equivalent.

## Diagnostic addition
- `RUN-QUEST-APK-SKY-DIAG.cmd` now includes bounded `VR CAMERA YAW PROBE` every 90 original car callback samples. It reports body vs auxiliary heading divergence, native camera look-yaw step and steering. Word and radian wraparound are unit tested.
- Log straight/high-speed left bend/high-speed right bend at the same F0 setting. Aggregate max changes alone cannot prove exact temporal phase; confirming a genuine camera lead needs time-aligned per-frame traces or paired Quest and PC capture.
- No change to original simulation, car orientation, head yaw/recenter or mode1 render matrices. Do not force body-locked yaw without physical Quest source-parity evidence. The user's turning symptom is NOT claimed fixed by this diagnostic-only change.
