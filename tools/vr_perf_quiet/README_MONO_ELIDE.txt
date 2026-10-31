OutRun VR R26 FOCUS PERF MONO-ELISION TEST - 2026-11-01

This package includes Win32 dinput8.dll and matching x64 outrun-vr-host.exe.
It contains focus visual repairs, prior safe perf optimizations, and a change
that REMOVES third mono center Draw/Clear in steady-state DirectGPU stereo.

SAFETY: the original mono shadow stays active only during initial bootstrap,
until at least one verified DirectGPU stereo frame with host-ready publication.
Then R9MonoElisionArmed skips every extra center mono Draw and Clear.
On incomplete stereo frames no new broken frame is published; the host retains
its last valid stereo projection. Three sequential failed frames disarm the
elision and restore warmup shadow, to avoid the prior cold-start white screen.
A device Reset also disarms the optimization. This is not 100% elimination
during cold-start/failure; after normal DirectGPU convergence extra mono = 0.

1. Backup existing dinput8.dll and outrun-vr-host.exe and your INI.
2. Extract the INNER ZIP files directly into the game folder containing
   OR2006C2C.EXE, replacing the two VR binaries.
3. Activate Quest + Virtual Desktop / VDXR and run RUN_VR_PERF_QUIET.cmd.
4. If it asks to isolate an existing d3d9.dll, type YES only if approved.
   The wrapper is backed up and automatically restored on normal exit.
5. Compare GPU frametime and VR clarity on the SAME course.

LOGGING: VR Telemetry=false, host full trace disabled, pixel probe disabled.
Only startup/errors and sparse single-shot mono state logs remain.
QUALITY: OpenXR physical per-eye resolution preserved, MSAA2 unchanged.
Reflection 256, update rate 0.25, vehicle LOD enabled.

Source focus base: 9e26abe; integrated quiet perf base: b1efbe8.
Quest real-world runtime still requires user validation.
