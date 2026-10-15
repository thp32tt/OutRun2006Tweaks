# Second 30-minute full-source review: optional Windows API failure paths

MSVC `/analyze` first-party diagnostics:
- `src/hooks_misc.cpp`: `WSAStartup` result was ignored, yet an optional UPnP thread was started regardless. Now log nonzero result and skip optional UPnP without disrupting original game network owner.
- `src/hooks_wheel_ffb.cpp`: `GetProcAddress(GetModuleHandleA("kernel32.dll"), ...)` could receive a null module handle. Now guard HMODULE before resolving optional ExitProcess hook.
- `tools/verify_vr_win32_cross_domain_safety.py`: add two exact source guards and two negative mutations.
- CI integration: `.github/workflows/vr-dx9ex-active.yml` previously watched only selected `src/` files. A change in common wheel/network/core code could alter the DX9Ex binary without running canonical host/game/full-chain gates. Replace narrow VR-folder entry with `src/**` to include all compiled source edits, retaining other non-src path filters.

These are fail-safe edge cases, not known causes of the prior user 00519 HUD visuals. Runtime validation UNTESTED.
