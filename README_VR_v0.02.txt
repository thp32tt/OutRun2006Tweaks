OutRun 2006 VR v0.02 Beta - Cockpit Release

한국어 안내
- ZIP을 OR2006C2C.EXE가 있는 게임 폴더에 압축 해제합니다.
- VR 운전석 모드는 Start-OutRun-VR.cmd를 실행합니다.
- 정면을 바라본 상태에서 F12를 누르면 VR 시점이 재정렬됩니다.
- v0.02 기본 운전석 높이는 SeatDown=+0.8로 낮췄습니다.
- 차량 떨림 완화를 위해 F0 Render Scope는 기본 ON입니다.
- OR2006C2C.EXE를 직접 실행하면 기존처럼 2D + FFB로 실행됩니다.
- 시작 시 하늘 깜빡임 수정은 포함되어 있으나 Quest 3 실기 최종 확인은 아직 남아 있습니다.

INSTALL
1. Extract all files into the folder that contains OR2006C2C.EXE.
2. Run Start-OutRun-VR.cmd for VR cockpit mode.
3. Run OR2006C2C.EXE directly, or Start-OutRun.cmd and choose 1, for normal 2D + FFB.
4. In VR, press F12 while looking forward to recenter.

v0.02 COCKPIT DEFAULTS
- QuestCockpitV2 cockpit enabled in VR launcher.
- F0 render scope ON. This is the field-tested path that removed vehicle body vibration.
- SeatBack=-0.08, SeatDown=+0.8, SeatRight=0.0.
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
