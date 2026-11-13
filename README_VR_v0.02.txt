OutRun 2006 VR v0.02 Beta - Cockpit Release

INSTALL
1. Extract all files into the folder that contains OR2006C2C.EXE.
2. Run Start-OutRun-VR.cmd for VR cockpit mode.
3. Run OR2006C2C.EXE directly, or Start-OutRun.cmd and choose 1, for normal 2D + FFB.
4. In VR, press F12 while looking forward to recenter.

v0.02 COCKPIT DEFAULTS
- QuestCockpitV2 cockpit enabled in VR launcher.
- F0 render scope ON. This is the field-tested path that removed vehicle body vibration.
- SeatBack=-0.08, SeatDown=+0.05, SeatRight=0.0.
- Native Quest 30-car seat profile and APK-mode camera input path enabled.
- Driver hidden, passenger retained, original full car retained.
- Cockpit glass reflection suppression enabled.
- Normal release logging/telemetry disabled for performance.

STARTUP SKY
The exact original 0x4521C0 programmable sky is pinned to one deterministic
rotation-only stereo basis to prevent native/fallback mode changes observed in
the previous HMD logs. This code/CI fix is included in v0.02. Quest 3 visual
confirmation of complete startup-flicker removal is still pending at release time.

CRASH HARDENING
- Crash handler is installed before settings and VR hook initialization.
- Inaccessible/missing user INI checks use nonthrowing filesystem paths.
- CrashDumps directory creation is fail-safe.
- Missing normal runtime log no longer invalidates crash ZIP creation.
- Partial minidumps are rejected.
- Crash signatures distinguish main EXE faults from other loaded modules using
  MEM_IMAGE AllocationBase rather than raw address ordering.

This is a fan-made beta mod. Keep a backup of your game folder.
