OutRun2006 Quest APK Cockpit - COPY & RUN (R26, NO EXTERNAL MODEL)

Use ONLY the GitHub Actions artifact named:
  OutRun2-QuestCockpitV2-COPY-RUN-<40-character-source-SHA>
Do NOT extract the similarly named GENERAL test ZIP into an existing game
folder when the goal is a no-overwrite, single-click installation.

This cockpit test renders the original in-game Ferrari car and driver-seat
camera. It does NOT load Dino GLB, replacement meshes or external textures.

1. Close the game/VR host and extract ALL ZIP contents into your own
   OR2006C2C.EXE folder, preserving QUEST_APK_COPYRUN_PAYLOAD.
2. Double-click RUN-QUEST-APK-COCKPIT.cmd. No installer or manual
   settings change is needed. First launch verifies x86/x64 DLL/host
   hashes, saves the previously installed DLL/host/DXVK/INI and helper
   files, activates DX9Ex and starts the VR cockpit.
3. Use RUN-QUEST-APK-SKY-DIAG.cmd to capture bounded sky/vehicle evidence.
   Use RUN-QUEST-APK-INTERP-OFF.cmd for road-jitter interpolation A/B.
4. RESTORE-QUEST-APK-COCKPIT.cmd restores the files backed up by the
   current test cycle. Close the game first. A successful restore archives
   that baseline under QUEST_APK_COPYRUN_BACKUP_HISTORY, so a later test
   creates a fresh backup instead of reusing an old pre-restore snapshot.

The ZIP contains NO top-level dinput8.dll, d3d9.dll, VR host,
OutRun2006Tweaks.ini, original game EXE or PMT/car/texture assets.
This avoids changing existing binaries or INI just by unzipping.
Existing OutRun2006Tweaks.user.ini is preserved. The launcher may
temporarily switch away from DXVK to DX9Ex, with a backup available.

This remains a WIP test. Original Quest angle-dependent native view
matrix and player-car F0 render-time vibration are NOT yet HMD-verified.

TEST AND APK COMPARISON (2026-11-05):
- Keep original view1 (in-car) selected. The native Quest 30-car profile
  and verified game-state guard remain in use; no EXE or APK asset patch.
- QuestCockpitV2ApkNativeCamera=true is the APK-parity path. Saved F11
  QuestCockpitV2SeatBack/SeatDown/SeatRight values are intentionally ignored
  there so an old manual SeatDown cannot raise/lower the native Quest seat.
  The original 30-car profile and exactly one source Y/Z composition remain.
  Manual seat tuning is only for the explicit ApkNativeCamera=false comparison.
- If road bounce/sky flicker persists, use the two included A/B scripts
  without changing the original game files. These remain unresolved
  visual comparisons until captured on a Quest 3 headset.
- Zip extraction by itself does not replace dinput8.dll, DXVK, INI,
  executable, car models or textures. First launch saves old installed
  files under QUEST_APK_COPYRUN_ORIGINAL_BACKUP before activating the test.
- The dedicated ZIP is a developer HMD test artifact; successful Windows
  compilation does not prove APK-equivalent camera or stereo behavior.
