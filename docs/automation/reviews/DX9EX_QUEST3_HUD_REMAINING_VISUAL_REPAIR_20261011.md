# 2026-10-11 DX9Ex Quest 3 visual candidates

Tested input build: 9e393cfdc2865e580c0cb2e16b364017afd3b1da (CURRENT_FOCUS/CORRECTNESS).
Current baseline before these changes: bd81283b9a4c2207d42a2b5c573119600b2c024d (DX9Ex Active, Domain, Full Impact all PASS).

Evidence from attached two real OUTRUN_VR_ANALYZE ZIPs:
- rank per-eye projected buildOk 5229 / buildFail 20, but HMD reports car-ordinal 1-5 detached. R62 occasional RANK_MARKER_CLIP owner=SCREEN_HUD marker=0 is not necessarily a vehicle glyph: NaviPub uses the same sub_4BAD20 with four explicitly ScreenHud callers. Do not globally reinterpret those as world markers.
- separate 0x989xx stage-extension six parent hooks were installed but no 'VR P0 STAGE EXTENSION SOURCES:' runtime hit across both sessions. Do not claim the white +TIME is fixed: identify the actual live source before widening.
- central lens object 0x570002 had D3A5 parent WorldBillboard but visual centre still doubled; outer discs via CABE remain good.
- sky splits around stage changes and mission finish; clean independent stereo SkyGlow was active (factor=4) and failure counters 0.

Source candidates:
1. Rank ordinal exact sprani/clip producers have a scoped render semantic DURING the original CALL (old R57 style), not only delayed queue tagging after it. Preserve NaviPub ScreenHud and actual projected anchor gating. Real HMD validation required.
2. Lens central exact original E8 at EXE+0xC993 into DrawObjectAlpha_Internal now scopes the actual core draw as ProjectedScreenEffect2D, independent of the outer CABE. Retain the original camera near 0.05 and parent D3A5 scope. Real HMD validation required.
3. SkyGlow is suppressed ONLY at transient GOAL, TIMEUP, LINK_TIMEUP, GIVEUP, WARP, RESTART states, avoiding transition-only double additive sky layers. Original game world, normal GAME glow, and both eyes' scene geometry untouched. This is a targeted candidate, not proof that split sky vanishes.
4. +TIME original source attribution is still incomplete. No unproved generic alpha/HUD heuristic was added: needs matched HMD trace around exact +TIME onset.

Regression checks: tools/verify_vr_visual_composition_p0.py negative mutations for marker producer-time scope and exact core-call separation. Same test SHA required for CI; RUNTIME_VALIDATION=UNTESTED until user Quest3/VDXR optical check.
