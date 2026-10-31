OUTRUN 2006 / R26 SAFE DX9EX WHITE SCREEN RECOVERY

The prior NO-MONO test can leave a blank/white frame before the first verified
stereo projection. It also omitted the existing proper DX9Ex launcher.

THIS ZIP RESTORES:
- exact CI-successful R26 game DLL with original independent MONO fallback
- matching x64 OpenXR host from the same successful commit
- original RUN_DX9EX_TEST.cmd plus Run-DX9ExFocusTest.ps1
- correct XR flags, classic Desktop Duplication fallback, logs
- first-run backup, install, launch, and rollback scripts

FIRST RUN:
1. Extract this entire ZIP to an empty directory.
2. Quit OutRun and the old VR host; start Quest / Virtual Desktop / VDXR.
3. Double-click INSTALL_AND_RUN.cmd.
4. When requested, enter the folder containing OR2006C2C.EXE.
5. Prior binaries and runner files are backed up before installation.
6. The original test runner starts the GAME EXE (not the host EXE).
7. For later runs, double-click RUN_INSTALLED_SAFE.cmd in game folder.

RESTORE:
Close the game and VR host and run RESTORE_PREVIOUS.cmd in game folder.

Original game assets and EXE are not redistributed. Existing INI settings
are never overwritten. Optional reference INIs are copied only if missing.

SOURCE:
Original safe mono fallback commit 8ee0bc110425f6bd3f18e2d9d286931c32141f08
Verified Windows game+host test build 41207495346
Artifact 13045081423

NO-MONO OPTIMIZATION IS DISABLED. This is a screen-recovery test.
Quest white-screen recovery must still be confirmed in your real setup.
