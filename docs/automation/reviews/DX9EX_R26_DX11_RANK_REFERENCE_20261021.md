# 2026-10-21 — DX11 proven ordinal/rival reference and R26 HUD size

Direct user request. Branch: vr-d3d9ex-focus. Separate automatic DX9Ex lane remains REVIEW_ONLY.

## Comparison

- DX11 `vr-dx11-native-r71` HUD `Settings::VRHudScale=0.55`, packaged `HudScale=0.55`. R26 previously set 0.82; now both set to 0.55.
- DX11 `src/hooks_uiscaling.cpp` R57 default mode 6 scopes rank1-3 and rank4-6 as PROJECTED_WORLD_MARKER_2D and recovers the original `Calc3D2D` projection. It preserves 2D sprite size and adds eye-specific NDC delta from original view-space point.
- DX11 `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` R57 mode6 uses `HeadInverse * inverse(relative-eye/IPD with identity orientation) * per-eye FOV projection`. It does not add eye orientation for ordinal rank.
- R26 DX9Ex reconstructed an additional `exactOrdinalEyeCant` full-eye pose for ordinal only. User Quest3 optics: DX11 reference rank and rival are fully normal; R26 marks depthless. A direct opt-in comparator now defaults to DX11 identity-eye mode while retaining ordinal canted-eye mode as `RankDx11ReferenceEyePose=false` for an explicit future A/B.
- Crucially neither candidate may fabricate a 3D anchor when `Calc3D2D` or queue ownership is invalid. The observed `navipubDepth=1` probe was ScreenHud and does not establish that an exact vehicle marker was rejected. Runtime visual parity remains UNTESTED until fresh Quest3 session.

## Scope

Changed only R26 rank eye-pose selection and HUD default+packaged INI. Rivals, native source/UI 640x480, 1080p virtual HUD canvas, gameplay/world projection, lens, F11 are unchanged.

## Test

Use exact SHA artifact; verify Quest3 1st/2nd/3rd vs 4th/5th/6th and rival at different car distances with slow yaw/pitch, compare with DX11 on same conditions. Check `VR RANK PHYSICAL PRODUCER` projectedValid and eye pose. `RankDx11ReferenceEyePose=false` restores prior R26 ordinal path only on explicit A/B test; restart game for consistent comparison.

No HMD completion claim from source inspection or CI.
