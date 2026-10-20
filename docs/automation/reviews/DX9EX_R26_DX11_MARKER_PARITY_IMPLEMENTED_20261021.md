# DX9Ex R26: apply user-good DX11 marker source defaults (2026-10-21 KST)

Direct user instruction: "모두 적용해봐." Game/runtime source edits expressly authorized for this turn. Scheduled autonomous DX9Ex REVIEW_ONLY policy remains unchanged.

## Baseline and scope

- DX11 reference branch `vr-dx11-native-r71` read SHA `e3f8acd154c49e3455a1f427dbfa32614fd6f9ed`, user reports rank+Rival visually good.
- DX9Ex focus branch R26+HUD remains runtime/default, with native 3440x1440 landscape game source, 2496x2688 XR eye targets, correct 4:3 main/car menu, F11 screen-only path, HUD scale 0.55, original stage sun.
- Older user-good DX11 test ZIP exact SHA / loaded module hash is not yet supplied. DX11 native game full-frame is opt-in (`OUTRUN_DX11_FIRST_GAME_FRAME=1`, plus `OUTRUN_DX11_FULL_GAME_FRAME=1`) and latest 00959 C6 had `RUNTIME_VALIDATION=UNTESTED` for genuine native frame. The good screen may be its retained R57/R62 D3D9Ex game path; do not claim it is native DX11 without artifact proof.

## Material changes (not just a review)

1. `RankDx11ProducerReference=true` (default): original exact `Calc3D2D` 0xBAEE7 or captured x86 E8 0xBAEE2 consumes the output-derived game vehicle view point, **without** the additional R26 raw-input round-trip match or optional `RankMarkerSubActiveDepth` fallback. If false, the earlier guarded R26 round-trip/parent route remains. Exactly the car original E8 remains the source; no global sprite auto-promotion.
2. `RivalDx11NativeRoute=true` (default): do not install either DX9Ex-added rival x86 E8 hook at `0xBB6F0` or `0xBB796`. The stock game rival sprite path, matching the working DX11 branch's lack of custom rival detours, executes. False restores both hooks and previous frozen stereo anchor for A/B. Restart required because hooks are patched only at program initialization.
3. `RankDesktopLift=false` (default): rank 1–3 and 4–6 no longer add the later R26 +32 native-UI-pixel vertical correction on top of the original game positions. False is DX11 reference; true restores lift independently of source/eye pose. Rival never inherits it.
4. `RankDx11ReferenceEyePose=true` and `HudScale=0.55` unchanged. DX11-like HeadInverse / centered-eye IPD / asymmetric FOV correction for rank preserved. Keep R62 fixed-function FVF0x142 dual-eye and R64 Draw→Flush sprite isolation; no blanket world/HUD reclassification, renderer switch, or unrelated changes.

## A/B settings

```ini
[VR]
HudScale = 0.55
RankDx11ReferenceEyePose = true
RankDx11ProducerReference = true
RivalDx11NativeRoute = true
RankDesktopLift = false
```

- Compare exact binary when left/right optical success observed. For isolated regression: `RankDx11ProducerReference=false` changes rank projector only, `RivalDx11NativeRoute=false` restores 2 E8 hooks after restart, `RankDesktopLift=true` restores +32 rank shift.
- Game viewport fixed 3440x1440 (unless user manually changes); XR eye texture remains separate. Main menu/selector optical acceptance must not be regressed.
- Runtime logs: `VR R57 RANK OWNER PROBE`, `VR RANK PHYSICAL PRODUCER`, `VR R62 FIXEDFN KIND0`, `VR R64 D3DX ISOLATE RESTORED`, `VR RIVAL DX11 REFERENCE`. In native rival mode, `VR RIVAL EXACT CALC EDGE` and `VR RIVAL PHYSICAL PRODUCER` should **not** be emitted by disabled call hooks.

## Risk and gates

- Exact 0xBAEE2 lies in shared `sub_4BAD20` reached from several NaviPub callers, so its presence alone does not prove a real world anchor. New rank defaults retain finite recovered-point checks; no arbitrary null/invalid anchors are granted. The user still must check 1–3, 4–6, and rival separately at near/mid/far distance. False positive on NaviPub is possible pending physical per-producer proof.
- DX9Ex-only rival bypass may leave the original sprite without custom depth semantics. This is deliberate DX11 stock-path optical A/B; do **not** mark it fixed based only on matched source shape.
- The older `0cff83cf` stable label does not certify all rank+Rival simultaneously.
- Compile/policy and exact Windows CI required. Until the exact patch binary is run in Quest 3, `RUNTIME_VALIDATION=UNTESTED`.
- This direct-source development change does not enable automatic autonomous editing. No AI points claimed for review/status, duplicate task or untested code.
