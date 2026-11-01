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

QUIET MONO-GAP PERFORMANCE PROBE:
This experimental binary keeps EXACTLY the previous focused mono-gap repair.
With VR.Telemetry=false, it writes one short aggregate line every 10 seconds
while stereo is active: VR R26 MONO-GAP SAMPLE. Values are per interval:
monoActual: real third-pass backups; gapSkipDraw: eliminated third passes;
gapSkipClear: eliminated invalid-shadow partial clears; gapFrames:
frames where mono history became invalid; gapFramesWithoutLaterSkip:
gap frames where no subsequent R9 draw could be eliminated. The
candidateSkipSharePct is NOT a GPU frame-time or FPS estimate.
No full per-draw trace, no GPU readback, no new RT, no fidelity changes.
After a same-course gameplay test, compare GPU frame time and send the small
OutRun2006Tweaks.log. Do not change the VR Telemetry setting for this probe.

STEREO-ONLY / LAST GOOD DirectGPU TEST — 2026-11-01
This experimental R26+HUD branch removes the third independent mono
backup in VERIFIED DirectGPU headset gameplay only. It DOES NOT remove
the original game's normal 2D/offscreen Draws or theater/menu rendering.
R20 initial color/depth seed no longer requires a dedicated mono RT or
mono depth: right-eye baseline is built and validated using the original
main-depth generation and current Present's full depth/stencil clear.
R13 side-effecting unsafe Draws continue exactly once on the real target;
incomplete frames are never advertised as active stereo.
After a verified DirectGPU frame was published, failed/incomplete frames
preserve the last-good VR publication until the next valid pair; Reset,
host disconnection and leaving VR invalidate this proof.
No automatic fallback to partial/unsynchronized mono headset frames.
This is a TEST build only. Quest3 HMD visual/boot behavior is unverified.
If blank/white/one-eye display appears, restore the previous safe
R26 gap-repair build and provide logs. Keep DirectGpuOnly=true.

OPENXR LAST-GOOD HOST CHANGE: a verified DirectGPU stereo pair is copied to
host-private D3D11 snapshot textures; while the same gameplay presentation
and XR session remain valid, host keeps presenting that pair until another
verified pair is ready. Reset/session/reference-space/presentation changes
invalidate matching. SBS/DesktopDuplication still uses its old 250ms grace.
This can temporarily freeze head-motion parallax during prolonged game stalls;
for experimental use only, not yet validated for comfort on Quest.

R26+HUD STEREO-ONLY TRANSACTIONAL SAFETY REPAIR (2026-11-01)
- R9 latches the DirectGPU no-mono decision on the first main Clear of
  each Present; fast host-ready toggles cannot mix 2-eye and 3-eye
  histories inside one frame. Both Reset paths explicitly disarm latch.
- OpenXR never copies directly into the displayed last-good snapshots:
  candidate left/right textures are GPU-copied and fenced separately;
  the EXACT frame metadata must be rechecked before pointer swap.
  Copy timeout, allocation failure or metadata mismatch keep the
  previously committed stereo frame unchanged.
- Host uses the 250ms stereo grace for SBS; only actually accepted
  DirectGPU stereo pairs use the longer last-good hold.
- Explicit game ResetEx-disabled/zero publication invalidates old
  host matched source, preventing stale old-generation VR projection.
- Candidate snapshot textures are reused through two-buffer swapping
  when dimensions/format stay stable, avoiding repeated allocations.
- Source/Windows CI tests do NOT prove Quest HMD visual comfort.
  First test cautiously, keep prior R26 safety build for rollback.

FINAL SAFETY CONTRACT ADDENDUM:
The game cannot prove that the host has accepted a DirectGPU frame merely
because producer Present and publication succeeded. No game-side boolean
is treated as authoritative 'last-good'; the game suppresses bad mono packet
publication only while a stereo-only DirectGPU Present is active. The host
commits its own fence-verified and metadata-verified stereo candidate and
holds the only authoritative last-good pair. A lastGoodHeld counter in the
game log means suppressed fallback publication, NOT confirmed host display.
