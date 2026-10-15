# HUD nightly 2026-10-09 source and delivery record

User requested same-night HUD/screen-composition test build. Authenticated source `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`, base `fe428cb8de0fc7027c20f66111c6ed75962155e2`; TASK_ID `DX9EX-HUD-NIGHT-GOAL-TRACE-AND-PACKAGE-20261009`.

The latest source already retains restored R62 4/5 FVF0x142 marker path, R64 6/6 per-sprite Draw/Flush isolation, exact 0xBEA5A/0xBEA5F GOAL helper A/B, original D3D9/host state parity, F11 user-reported normal and screen-state provenance. Known **HMD-unresolved**: +TIME transient, GOAL-before-restart translucent time, lens centre and certain menu arrows. Do not globally classify translucent sprites as ScreenHud or remove either GOAL helper.

**One source-proven defect fixed:** R30 pre-restart draw-form and early-gate diagnostics used process-lifetime atomic masks. Following the first GOAL, a second GOAL within the same game executable never emitted any route evidence. New source resets both bounded atomic masks only on an actual GOAL/TIMEUP/LINK_TIMEUP transition observed from gameplay, never on every frame/draw. Four independent negative tests in visual verifier. This is a diagnostic fix, not an HMD-verified optical fix.

**Package issue fixed:** Windows package manifest previously advertised only CONTROL/CORRECTNESS/PERFORMANCE although GUI supports B_HUD / HUD_SCREEN, HUD_MENU and C_FLARE / HUD_WORLD. Add actual profiles to manifest and a practical HUD tester guide included in the zip. The existing CORRECTNESS profile remains default, no material game/host renderer policy change.

Validation policy: exact new material SHA DX9Ex Active Win32 game + host + R33 full-chain + zip, Domain Isolation, EXE HUD Inspector; no 1000/5000 HUD static repeats. RUNTIME_VALIDATION=UNTESTED.
