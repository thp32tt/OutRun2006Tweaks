# Quest3 R26+HUD A/B/C GOAL experiment (2026-10-26)

All three are runnable TEST+DEBUG GitHub Actions packages. Each includes x86 dinput8.dll, x64 host, START_HERE.cmd, PS runner, INI. Use only ONE at a time, restore backups and capture DX9EX_LOGS zip. RUNTIME_VALIDATION=UNTESTED.

- A: exact SHA 456642108a4c0bd86c337bc14ead561b3c376cdc. +TIME live ticket fix, established official baseline. GitHub Actions https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40299176367
- B: exact SHA bda6b12078528265a8157d842a7c825883fb629c. A plus guarded inner GOAL progress and full-graph parent queue-epoch admission. GitHub Actions https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40307057617
- C: this branch exact SHA printed in SOURCE_SHA.txt. B plus isolated single-child rebuilt-empty-root GOAL fallback. Requires original 0x979E0 full parent, unchanged queue epoch, oldRoot sentinel empty, different live newRoot, only one terminal new child, and protects newer exact tags by entry serial. It NEVER touches generic sprite draws, rank, rival, +TIME or 2D resolution. This is a conditional HMD experiment, not a confirmed final-graph fix.

Controls: stable root/empty root, detached old tail, multiple siblings, cyclic tail, non-GOAL/VR-off, changed queue epoch, original native calls and existing StageExtension ticket. Compare final graph only, check GOAL 0-99 and rival as regressions; do not infer "two-eye pass" from CI compile. Keep DriverSeatView=false, HudScale=0.55, MSAA=2, CullingUnionMarginDegrees=8.0.
