# Second 30-minute review: bounded high-resolution wait

`src/hooks_framerate.cpp::Snooze::PreciseSleep` previously treated a non-null waitable timer handle as proof that `SetWaitableTimerEx` successfully armed it, then called `WaitForSingleObject(Timer, INFINITE)`. A failed timer arm or invalid handle therefore could hang the render thread permanently. This is a source-proven unbounded failure path, not an observed user's Quest3 crash.

Patch checks `SetWaitableTimerEx`, bounds `WaitForSingleObject` to the requested QPC sleep slice (1–1000ms plus scheduler tolerance), breaks on failed/timeout return into existing QPC fallback spin, and retains normal timer behavior when successful.

The Win32 cross-domain verifier adds 3 contracts and 3 injected-source failures (13 total). CI source and Win32 active build tests should be run on the material SHA; runtime remains UNTESTED.
