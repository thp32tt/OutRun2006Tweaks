---
name: outrun-vr-regression
description: Verify isolated OutRun 2006 VR renderer fixes using GitHub CI, source tests and exact Quest 3 test bundle identity.
---

# Regression / Completion
1. Read AGENTS.md, leased FEATURE_ID and current compiled CMake flags; preserve independent DX11, DXVK, localization and FFB lanes.
2. Make failing regression first, smallest correction second. Run unit verification and affected + domain isolation checks.
3. Build the exact Win32 game DLL, x64 host and package from the same SHA; verify launcher, startup PID and copy contents.
4. Compare protected R26/HUD, menu 4:3, F11/ESC, shadows, rank, +TIME/GOAL, sun and lens against working baselines.
5. Separate STATIC_PASS, WINDOWS_CI_PASS, PACKAGE_PASS, and QUEST3_HMD_PASS; no extrapolation between them.
6. No claimed functional completion from docs-only work, no assumed controller hot-reload.
7. No repeat scoring for retry, review, rollover or the same TASK_ID.
