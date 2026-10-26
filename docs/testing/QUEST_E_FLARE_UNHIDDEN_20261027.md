# Quest E comparison — full original flare and XR eye-source repair

Independent branch vr-d3d9ex-e-xr-rival-flare-20261026 based on D 24d4084e.

1. FULL FLARE RESTORED. Both original 0x570008 CABE draws are executed; the
   previous 'ordinal 2 hidden' early return is removed. The 0x570002 C993
   centre is drawn even with legacy LensFlareCentreEnabled=false. Other
   originals 0x570010/0x57000F/0x570006 never hidden. All keep scoped
   ProjectedScreenEffect2D mono-eye fusion; trace ordinal and source IDs.
   A visible tiny end-of-flare dot is not proven to be a given sprite ID.
2. RIVAL. D's route=true bypassed BB6F0/BB796; E tests the exact original
   projector and sprani hook with direct D3DX pre-drain + source-exit flush
   in its projected source scope. Exact queue tags stay guarded. This is an
   experiment, NOT proof of final stereo correctness.
3. XR EYE. D 3500-ms wait expired at 23:41:23.000, while host v3 was
   ready at 23:41:23.551. E first-device startup waits up to 8000 ms
   for an actual live host PID and matching per-eye OpenXR extents.
   No guessed dimensions and no per-frame wait.
4. MIRROR. D's PreserveAspect=false stretched game/menus on 3440x1440.
   E returns true. If desktop sidebars appear, they require a distinct
   black-mask PC window solution, not stretching the 4:3 menu.
5. GOAL. Real D state=20 TIMEUP is admitted=true and queued HUD had
   HRESULT zero for both eyes but user still saw duplicate/head-follow.
   Those symptoms remain UNRESOLVED; preserve exact source gates and
   investigate final graph as a separate opt-in test.
6. +TIME. No real +TIME event in the most recent D logs, so optical
   outcome cannot be verified and original source/semantic guards remain.
No changes to official focus; TEST and DEBUG built via GitHub Actions.
RUNTIME_VALIDATION=UNTESTED until Quest 3.
