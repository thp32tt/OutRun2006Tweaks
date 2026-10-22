# DX9Ex 16G log actionable test build — 2026-10-22

- REQUEST=DIRECT_USER_LOG_ANALYZE_FIX_AND_BUILD
- TARGET_BRANCH=vr-d3d9ex-focus
- SOURCE_HEAD_BEFORE_BUILD_TRIGGER=ca7532be35d1a96a28ed6fd86aea0b126f4e4ff0
- FOCUS_BUILD=R26+HUD / PC Fast
- RUNTIME_VALIDATION=UNTESTED

## Log-supported cumulative fixes included

1. **Exact CABE projected flare**
   - 16.57 GiB log plus source comparison showed the exact projected flare had diverged from the known-good DX11 R69 centre-eye path.
   - Current R26 restores exact `ProjectedScreenEffect2D` same-original-WVP L/R fusion only for the verified CABE semantic owner.
   - Static verifier: `verify_dx9ex_r26_projected_flare_fusion.py` PASS.

2. **Rival marker regression isolation**
   - The 16G capture contains no exact rival event, so no runtime claim is made from that capture.
   - Git history proves rival was already HMD-correct before ordinal rank 1–5 work and later force-installed R26 detours violated the recorded DX11-native default.
   - Current default `RivalDx11NativeRoute=true` retains stock `0xBB6F0` projector + `0xBB796` sprite call. Legacy R26 rival detours remain A/B-only.
   - Static verifier: `verify_vr_rank_dx11_reference.py` PASS.

3. **SkyGlow post-HUD capture boundary**
   - Review of the same visual path identified reduced-resource replacement after a clean pre-HUD capture as a stale-generation hazard.
   - Current R26 invalidates the capture epoch when reduced resources are replaced and skips optional glow if screen content has already drawn and no clean capture remains.
   - Static verifier: `verify_vr_skyglow_capture_boundary.py` PASS.

## Deliberately not guessed from this log

- GOAL result-progress: bilateral physical trace shows LEFT=S_OK and RIGHT=S_OK with restore complete; this log does not justify suppressing an eye or changing draw count.
- +TIME: no exact producer occurrence in the captured interval; no new speculative +TIME patch.
- C993 centre: source-owned raw world WVP was not proven in this capture and prior hide-only testing did not remove the doubled central light; no suppression regression.
- F11: 3,136 focused draw events report failure=0 and the later F11 world-lock/size correction remains intact.

## Pre-build static gate at ca7532be

PASS:
- `tools/verify_dx9ex_r26_projected_flare_fusion.py`
- `tools/verify_vr_rank_dx11_reference.py`
- `tools/verify_vr_skyglow_capture_boundary.py`
- `tools/verify_vr_dx9ex_launch_paths.py`
- `tools/verify_vr_r30_screen_hud_finite_plane.py`
- `tools/verify_vr_r26_result_hud_pose.py`
- `tools/verify_vr_20261020_hmd_baseline.py`
- `tools/verify_vr_projected_marker_anchor.py`
- `tools/verify_vr_driver_seat_basis_stability.py`
- `tools/verify_vr_pc_fast_package_contract.py`

The following commit is intentionally a PC Fast build trigger for the cumulative source state; the document itself has no runtime effect.
