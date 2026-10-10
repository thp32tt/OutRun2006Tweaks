# DX9Ex result-stage screen crash: two real minidumps (2026-10-10 KST)

## Exact optical regression and minidump evidence

- Tested user-provided DX9Ex executable SHA: `9e393cfdc2865e580c0cb2e16b364017afd3b1da`, profile CURRENT_FOCUS/CORRECTNESS.
- `OR2006C2C.EXE.20261010233304.zip` and `OR2006C2C.EXE.20261010233550.zip`: identical faulting EXE RVA `0x00097C5F`, exception `0xC0000096` (privileged instruction).
- Both minidumps contain overwritten live EXE code: an E9 rel32 detour at `0x00097C57` and another E9 rel32 detour at `0x00097C5C` (the `+5` leave hook).
- `0x00097C5F` is byte 4 of the latter detour, inside its relative displacement. Reading that byte as an x86 instruction yields an invalid/privileged instruction; the two minidumps have different displacement bytes but exactly the same EIP.
- The result-stage text producer at `0x97C57` is one of 19 original direct E8 calls to `0xB9200`. In the current code the `SafetyHookMid` at `rva+5` corrupts an original control-flow continuation in that window.

## Bounded source repair

`src/hooks_uiscaling.cpp` retains the original 19-call identity allowlist but declines BOTH enter and leave midhooks for this one unsafe parent (`0x97C57`). It leaves the actual E8 and original text fully intact, does not force or suppress game drawing, and does not change the two original GOAL helper calls `0xBEA5A` / `0xBEA5F`.

Why skip both: allowing the Enter-only hook would leave `ResultTextDepth` and `CurrentScope` sticky through unrelated world/sky passes. Remaining 18 result-stage parents still capture immediate ScreenHud semantic and appended SpriteNode children with normal balanced entry/exit.

The existing `tools/verify_vr_visual_composition_p0.py` now requires that the exclusion precede both hook installs and includes a negative mutation that removes it.

## Acceptance gates

1. **Build / source checks:** exact-SHA Win32 x86 game DLL, x64 host, `verify_vr_visual_composition_p0.py`, Domain Isolation and Full Source Impact. Check existing independent R29/R31 StateBlock verifier failure separately.
2. **Quest3/VDXR:** reproduce OutRun 5-stage result roll-up repeatedly and confirm no `EXE+0x97C5F` crash. Confirm no newly head-locked sky, +TIME or mission rival/self times, and preserve original result contents. This fix does not prove the result text is stereo-correct: the unsafe parent's HUD semantic is currently deliberately unowned.
3. **Subsequent full repair:** replace this one parent with a safe verified E8-call wrapper having the exact original ABI and an RAII source scope; never reinstall an unsafe `rva+5` midhook at `0x97C5C`.

**RUNTIME_VALIDATION=UNTESTED** for this new candidate. This is a source-level crash regression repair, not proof of headset success.
