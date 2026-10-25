# Quest APK call-site inventory — 2026-10-25

Source: user-owned Quest native ARM64 ELF, SHA256 fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6.

The exact REA raw function slices were decoded as original AArch64 instructions, including immediate BL targets and register-indirect BLR sites:

| ELF function | BL | BLR |
| --- | ---: | ---: |
| Flush::draw_404700 (0x10B9894) | 22 | not separately counted |
| PcSceneRenderer::render_frame (0x10CBE9C) | 8 | 20 |
| Draw::disp_514c30 (0xD60FD4) | 229 | 23 |

For glass, 13 direct calls lead to Bytes::out_of_view, others to internal renderer and C++ exception helpers; some import names remain unknown. Occupant has 33 distinct direct target addresses. At render_frame 0x10CC718 the target is 0x1233540 (previous frame_render_449050 context, final PLT binding unverified).

These are static call instructions, not runtime executions. Indirect BLR destinations require register and object/vtable provenance. Prior exact XR, camera and character-selection mappings are in QUEST_APK_EXTERNAL_CALL_RESOLUTION_20261025.md.

Status: REVIEW_ONLY, CODE_CHANGE=NO, BUILD=NOT_RUN, RUNTIME_VALIDATION=UNTESTED.