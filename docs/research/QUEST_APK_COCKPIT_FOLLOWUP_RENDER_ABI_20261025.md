# Quest APK cockpit / glass recovery — follow-up cross-check (2026-10-25)

## Provenance
User-owned Quest APK native binary; same SHA256 as prior work: `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. This follow-up is research-only: no gameplay source change, build or HMD runtime confirmation.

## New results
1. The original ARM64 `Flush::draw_404700` reads `DrawEntry+0x20 == 1` and `DrawEntry+0x34 & 2` before the blend-state and diffuse-alpha tests. The independently reconstructed public PC `PmtDraw` / `DrawEntry` type identifies **+0x20 as the blended pass** and **+0x34 as flags**. The separate Quest-specific bit1 producer is *not identified*, and neither field by itself proves windshield geometry. Reference: https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/pc_pmt_records.hpp
2. In the public PC queue reconstruction, blended nodes (`PmtNode.flags & 2`) are drawn with `e.pass = 1`; normal queue creation assigns bit0 for mirror/cull handling. Quest's bit1 requires its own write/xref trace. Reference: https://github.com/r4dius/outrun2-decomp/blob/main/src/platform/pc_render_flush.cpp
3. A bounded virtual FP register calculation for ELF `PcSceneRenderer::render_frame` (`0x10CBF6C..0x10CC2FC`) with **both 4x4 input matrices set to identity** yields `diag(-1,-1,-1,+1)` as the separate cockpit body-correction matrix. This is a synthetic instruction-path result, not an observed HMD or real game frame; the algebraic formula and real input semantics require further verification.
4. Independent PC `race_camera_view_switch_484a40` C++ reconstruction provides a readable comparison for the otherwise oversized and warning-bearing Quest Ghidra camera-switch pseudo-C. It is PC-origin, not literal Quest source. Reference: https://github.com/r4dius/outrun2-decomp/blob/main/src/driving/pc_race_camera.cpp

## Remaining proof obligations
Quest queue bit1 writer, identity and polygons of front/side window, actual car render ownership, numerical matrix order and conventions, hand/driver bones and HMD runtime behavior. No original-author source recovery claim. The desired deliverable is a behaviorally equivalent C++ implementation under test.

Status: REVIEW_ONLY; CODE_CHANGE=NO; BUILD=NOT_RUN; RUNTIME_VALIDATION=UNTESTED.