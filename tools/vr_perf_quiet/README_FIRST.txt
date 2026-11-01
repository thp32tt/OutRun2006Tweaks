OutRun 2006 Focus+R26 all safe performance optimizations (VR)

1. Extract the full compiled package into your installed game folder
   containing OR2006C2C.EXE. Back up existing DLL and host EXE first.
2. Start Quest/Virtual Desktop/VDXR as your active OpenXR runtime.
3. Double-click RUN_VR_PERF_QUIET.cmd, not the host EXE.
4. If an existing local d3d9.dll blocks D3D9Ex, type YES to isolate
   it temporarily for this game session. It is restored by SHA256 on exit.
5. Test exactly the same course. No full frame trace, no pixel probe,
   VR Telemetry=false. The launcher leaves the original game EXE alone.

SOURCE FOCUS FREEZE: 9e26abe49fc414ae8eeaa9f3bbebe16ab618d385
CHERRY-PICK: 0b39f432, 36d5882d, 6b75e5cb, 73e1bfc5, 8ee0bc11
LOG POLICY: OUTRUN_VR_FULL_TRACE=0; OUTRUN_VR_R23_PIXEL_PROBE=0;
 VR.Telemetry=false. Lightweight errors and startup summaries retained.
QUALITY: OpenXR recommended eye pixels; MSAA2 setting; no game EXE edits.
REFLECTION: 256 pixels, rate 0.25, native vehicle LOD enabled.
EXCLUDED: unconditional third mono backup removal (previously caused
 blank/white frames before a verified stereo source).

Avoid copying this package over an unrelated build without backing up
 dinput8.dll, outrun-vr-host.exe, and INI first. Existing user INI can
 override the package reference INI; the launcher forces key VR settings.
This is an experimental Windows-compiled test, not Quest runtime validated.

MONO GAP REPAIR TEST (2026-11-01):
This R26+HUD branch is NOT the prior unconditional third-mono elimination.
Before a gap, complete independent R9 mono safety render is preserved.
After R30 draws a stereo pair without a mono copy, R9MonoBackupGap=true;
the existing backup is now unrestorable for that Present. Later R9
Draw and partial Clear skip ONLY the unusable third shadow replay, while
real left/right stereo and R13/R9 failure flow remain in place.
A verified full main-target color Clear can re-seed the independent backup.
With VR Telemetry=true, R9's 5-second summary reports gapSkipDraw and
gapSkipClear counters. Default Telemetry=false keeps logs quiet.
This source contract and Windows binary compile are CI checked, but real
Quest HMD visual correctness and GPU frame-time gains require user testing.
