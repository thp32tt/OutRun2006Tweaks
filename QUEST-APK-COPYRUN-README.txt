OutRun2006 Quest APK Cockpit - COPY & RUN

1. Close the game/VR host and extract ALL ZIP contents into your own
   OR2006C2C.EXE folder, preserving QUEST_APK_COPYRUN_PAYLOAD.
2. Double-click RUN-QUEST-APK-COCKPIT.cmd. No installer or manual
   settings change is needed. First launch verifies x86/x64 DLL/host
   hashes, saves the previously installed DLL/host/DXVK/INI and helper
   files, activates DX9Ex and starts the VR cockpit.
3. Use RUN-QUEST-APK-SKY-DIAG.cmd to capture bounded sky/vehicle evidence.
   Use RUN-QUEST-APK-INTERP-OFF.cmd for road-jitter interpolation A/B.
4. RESTORE-QUEST-APK-COCKPIT.cmd restores the original files backed up
   by the first launch. Close the game first.

The ZIP contains NO top-level dinput8.dll, d3d9.dll, VR host,
OutRun2006Tweaks.ini, original game EXE or PMT/car/texture assets.
This avoids changing existing binaries or INI just by unzipping.
Existing OutRun2006Tweaks.user.ini is preserved. The launcher may
temporarily switch away from DXVK to DX9Ex, with a backup available.

This remains a WIP test. Original Quest angle-dependent native view
matrix and player-car F0 render-time vibration are NOT yet HMD-verified.
