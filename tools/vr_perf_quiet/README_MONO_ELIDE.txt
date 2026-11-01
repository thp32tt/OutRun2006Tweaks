OutRun VR R26 FOCUS MONO-ELISION 512 TEST - 2026-11-01

This build keeps the current visual-quality profile while applying the stronger
verified DirectGPU mono-elision path.

STEADY STATE:
- LEFT and RIGHT stereo rendering remain unchanged.
- After one complete host-ready DirectGPU stereo frame, the redundant third
  center-mono Draw/Clear path is disabled.
- Existing narrow mono-gap skip remains active during bootstrap.

SAFETY:
- Cold start retains the independent mono recovery shadow.
- Incomplete stereo after elision does not replace the last verified host frame.
- Three consecutive bad frames disarm elision and restore bootstrap mono.
- Device Reset also disarms elision.

QUALITY PROFILE:
- ReflectionResolution = 512
- ReflectionUpdateRate = 0.25
- DisableVehicleLODs = true (full-detail vehicles)
- MSAA2 unchanged
- Transparency supersampling off
- Existing culling and R26 copy/math optimizations retained
- SkyGlow forced off by quiet launcher

LOGGING:
A sparse 10-second line "VR R26 MONO-ELIDE SAMPLE" reports monoActual,
gapSkipDraw and monoElidedDraw. candidateSkipSharePct is Draw-count share,
not a direct FPS/GPU-time estimate.

Run RUN_VR_PERF_QUIET.cmd on the same course used for prior comparison.
Quest/HMD runtime performance still requires real-device validation.
