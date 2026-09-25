# Korean Text + Graphics Test Build — 2026-09-26

## Canonical source
- Branch: `korean-localization-clean`
- Runtime source SHA: `60b0aeae9bbb8b386df7137c11d7bb39aba83e6c`
- GitHub Actions build run: `36199273761`
- Runtime artifact id: `10890929129`
- Runtime artifact digest: `sha256:823534a8e69e2f5ff9cc6a125dd53358454ae6520c5e6c43b92c3d33d172660a`

## Runtime text test
- `localization/text/runtime_ko.tsv`: 1,355 translated rows.
- `KoreanTextOverlayTest=true`.
- `KoreanTrace=true`.
- `KoreanProofTextOverride=false`.
- `KoreanK3Trace=false`.
- Stock text resolver is tracked without replacing non-render consumers.
- Matching `sprPrintf` / `Sumo_Printf` output is hidden with a layout-preserving surrogate.
- Korean UTF-8 is redrawn through the existing D3D9 ImGui overlay.
- `%d` / `%s` formatting is applied from the original x86 call arguments.
- Windows font preference: `malgun.ttf`, `malgunsl.ttf`, `gulim.ttc`, `batang.ttc`, then `segoeui.ttf`.

## Graphics included
Source package:
`OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B21v3_QA_Test.zip`

SHA-256:
`c566a79e47faaf788380da73fc6ec6bd23639e75c1f26c65d58e061067a07284`

- 32 reviewed DDS assets in package.
- 28 retained localized candidates.
- 4 QA-failed assets are reset to the original DDS, not shipped as Korean candidates.
- Source-faithful policy remains mandatory.

## Combined test package
`OutRun2_Korean_Text_GFX_Test_20260926_60b0aeae.zip`

SHA-256:
`3aa850066c61eac5762c036b91ef6fe9211c7bdf3097b0ea9eecd71f25cc9437`

Contents verified:
- `dinput8.dll`: 4,521,472 bytes.
- `runtime_ko.tsv`: 1,355 rows.
- 32 DDS files under `textures/load/`.
- `OutRun2006Tweaks.ini` with runtime Korean test enabled.
- Test README and graphics QA report.

## Mandatory in-game gates
1. English text must not remain double-drawn under Korean text.
2. Korean glyphs must remain inside the original text region / sprite cell.
3. Any spill, clipping, overlap, broken glyph, or unrelated artwork damage is a failure.
4. Check 4:3 and widescreen positioning.
5. Check long messages, explicit line breaks, `%d` values, and `%s` names/button labels.
6. The four reset-to-original graphics are expected to remain English until reworked.
7. Keep `OutRun2006Tweaks.log` and screenshots for every failure.

## Status
- CI build: PASS.
- Package assembly/checksum: PASS.
- In-game runtime validation: PENDING USER TEST.
- Final release readiness: NOT YET; this remains an experimental localization test build.
