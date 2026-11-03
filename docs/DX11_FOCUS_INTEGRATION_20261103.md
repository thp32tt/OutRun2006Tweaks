# DX11 on latest Focus (2026-11-03)

- Focus runtime baseline SHA: `5d68d900deeccc003c4c8bf0e5eb46614eaa3302` (R26+HUD, menus, F11/ESC, FFB, 2D startup isolation, no release polling).
- DX11 source donor SHA: `aa1d87e4bdc4e7b118a8f44838f433416006ed90` (complete identical 198-file native D3D11 engine, GPU transport probe, source-state header).
- 12 native engine CPPs added to Focus game DLL; independent WARP test verifies native transport against Focus common interfaces.
- DX11 donor R30 game-draw observers are NOT YET ported. Focus R30/HUD/lens/menu code remains untouched, so production rendering currently uses the Focus DX9Ex fallback. DX11 native-game rendering requires separate source-scoped bridge integration and runtime validation.
- Candidate branch only; no stable Focus or public release change.
