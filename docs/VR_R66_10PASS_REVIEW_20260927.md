# VR R66 10-pass source review — 2026-09-27

## Baseline

- Proven HUD lineage base: `10c73daa037b5cc521b42ce7fb3a7cc1820b1921` (R64)
- Production renderer contract: R26/R23 world + R30 HUD/XYZRHW/SkyGlow
- Required build flags:
  - `OUTRUN_VR_SAFE_DRAW_COMPARE=OFF`
  - `OUTRUN_VR_R26_HUD_COMPARE=ON`
  - `OUTRUN_VR_C1_COMPARE=OFF`
  - `OUTRUN_VR_C2_COMPARE=OFF`
- Proven runtime HUD baseline:
  - `OUTRUN_VR_R57_MODE=6`
  - `OUTRUN_VR_HUD_EXPERIMENT_MODE=2`
  - `OUTRUN_VR_HUD_PROBE=0`

## Review passes

1. **Lineage / domain isolation**
   - Compared R64 to the R66 candidate.
   - Changes remain confined to VR source, VR build/test workflows and VR binary-contract documentation.
   - No localization or FFB source merge.

2. **Runtime-mode coherence**
   - R57 mode 6 is now the source default in both HUD producer code and the R26+HUD renderer.
   - The normal selector defaults DX9Ex/DX11/DXVK launches to `R57_06_RANK_PROJECTED_HEAD`.
   - R57_05 remains a unique diagnostic slot instead of being overwritten.
   - Runner mapping for R57_06 keeps semantic mode 2 and R57 mode 6.

3. **HUD semantic ownership / diagnostic isolation**
   - Exact queue ownership defaults to semantic mode 2.
   - HUD probe remains default 0.
   - Diagnostic env=0 remains available as an explicit rollback and no diagnostic probe is promoted to production.

4. **Rival rank + POSITION ownership**
   - 1st–3rd exact sprani callsites preserved.
   - 4th+ exact put_clip_sprite callsites preserved.
   - Mode 6 keeps both families as `ProjectedWorldMarker2D`.
   - DispRank kind-1 and kind-0 producers keep exact `SCREEN_HUD + DispRank` ownership.
   - R64 post-Draw isolate remains restricted to projected-rank or DispRank-owned HUD.

5. **Canonical glyph + option arrows**
   - Canonical glyph callsite `0x2C9DB` preserved.
   - Option-arrow callsites remain limited to the eight reverse-proven callers in `0xE34E0/0xE4770`.
   - Review found that nested producer scope alone repeated the same risk previously seen on 4th+ rank markers.
   - Fixed by directly pinning the one SpriteNode appended by each exact option-arrow `put_clip_sprite` call.
   - No global `put_clip_sprite` promotion.

6. **Final GOAL/TIME**
   - Disassembly reconfirmed `NaviPub_DispTimeAttackGoal` at RVA `0xBEA50`.
   - Exact edges:
     - `0xBEA5A -> 0xBE020`
     - `0xBEA5F -> 0xBE150`
   - Both helpers are argument-free and each has only two callers: TimeAttack2D and Goal.
   - Only the Goal caller edges are redirected; newly appended nodes are pinned `SCREEN_HUD`.
   - Existing 15 TimeAttack2D hooks stay intact.

7. **Lens flare**
   - Exact flare path remains scoped to `0xCABE -> DrawObjectAlpha_Internal`.
   - x86 stack reconstruction confirms the wrapper ABI `(int objectId, float alpha, void* work, int flags)`.
   - R26+HUD production renderer handles only `ProjectedScreenEffect2D` with the asymmetric-FOV affine; no generic alpha heuristic.

8. **Selector shadow / START presentation**
   - Selector-only base-shadow bypass remains restricted to VR + `STATE_SELECTOR`.
   - Shared renderer/stereo presentation predicate remains present.
   - `STATE_START` stays gated by `game_start_progress_code == 65`.
   - No broad state-block or sprite heuristic was introduced.

9. **Build / packaging identity**
   - Found and fixed the dangerous old CMake defaults that still produced R26-only SAFE-DRAW.
   - New CMake default is R26+HUD.
   - Production builders explicitly pin all four comparison flags.
   - C1/C2/safe-only historical jobs explicitly opt out of R26+HUD so defaults cannot leak.
   - Ambiguous `outrun2006-vr-x86` safe-only artifact renamed to:
     `outrun2006-vr-x86-r26-only-diagnostic-DO-NOT-PACKAGE`.
   - PC-fast variant metadata corrected from stale `ACTIVE_FULL_R34` to `ACTIVE_R26_HUD_R66`.
   - DX9Ex active metadata corrected to the same R66 identity.

10. **Fail-closed regression gate / binary contract**
    - Added `tools/verify_vr_proven_baseline.py`.
    - Production Build, PC-fast, OpenXR R26+HUD and DX9Ex active invoke the gate before accepting a build.
    - Built DLLs are also scanned for required R64/R65/R66 markers and reject the R26-only SAFE-DRAW marker.
    - Added canonical EXE byte signatures for:
      - glyph callsite `0x2C9DB`
      - flare callsite `0xCABE`
      - GOAL/TIME edges `0xBEA5A/0xBEA5F`
      - all eight option-arrow callsites.
    - Exact canonical EXE identity remains SHA-256
      `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.

## Build acceptance rule

A production test build is rejected if any of these conditions fail:

- R26+HUD source graph is not selected.
- R57 mode 6 or semantic mode 2 is omitted.
- HUD probe defaults nonzero.
- rank/DispRank/font/option/GOAL-time/flare/selector/START guards disappear.
- any new exact EXE callsite is missing from the binary contract.
- built DLL lacks the proven R64/R65/R66 marker set.
- built DLL contains the R26-only SAFE-DRAW marker.
- package metadata identifies a different renderer variant.

R26-only, C1, C2 and old R20 builds remain available as explicitly named diagnostics only and must not be packaged as the user test build.

## Final build trigger

The post-review guard set was completed through source head
`e56201696ec257310c9791f8d1b08a029c0dbf77`.

The following commit changes documentation only and intentionally carries the
`[pc-build]` token so the exact reviewed tree is rebuilt by the PC-fast runner.
No source, build flag or runtime logic may change after this trigger without a
new review/build cycle.

## Late pass-10 generated-source correction

A final generated-source check found that `CMakeLists.txt` had been corrected to
R26+HUD defaults while the cmkr source `cmake.toml` still declared the old
R26-only SAFE-DRAW defaults. Because workflows intentionally clear `CI` before
configure, cmkr can regenerate CMakeLists and silently restore the old defaults.

Corrected both sources of truth:
- `cmake.toml`: SAFE_DRAW=OFF, R26_HUD=ON
- `CMakeLists.txt`: SAFE_DRAW=OFF, R26_HUD=ON
- `verify_vr_proven_baseline.py` now validates both files.

Any build produced before this correction is not an accepted R66 production
test build.
