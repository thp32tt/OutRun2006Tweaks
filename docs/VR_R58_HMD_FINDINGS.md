# R58 HMD findings — 2026-09-26

## Source HMD observations

The R57 01..10 matrix was tested on the NIGHTLY-R57-UNIFIED package.

- 01: HUD remains stereo-split; no improvement.
- 02: HUD remains stereo-split; no improvement.
- 03: ordinary/base HUD becomes a single stable image; other target defects unchanged.
- 04: 1st-3rd rival markers become smaller and stop following the head, but do not stay precisely on the cars.
- 05: 1st-3rd have correct placement looking forward, but head rotation moves them off the cars.
- 06: 1st-3rd remain attached to the cars while the head moves. This is the first correct vehicle-tracking result.
- 07: same head-motion failure as 05.
- 08: same ordinary-HUD improvement as 03; 4th+ target unchanged.
- 09: ordinary HUD stable; 1st-3rd split again.
- 10: ordinary HUD stable; 1st-3rd split and have no vehicle-rank depth.

## Runtime evidence

First projected-marker deltas:
- R57-05: view=(-4.6345,-1.9828,-109.4547), L=(0.22603,0.20417), R=(-0.25964,0.20417)
- R57-06: view=(-4.6406,-1.9777,-109.4443), L=(0.19721,0.17248), R=(-0.28847,0.17248)
- R57-07: view=(-4.6406,-1.9822,-109.4465), L=(0.22601,0.20416), R=(-0.25967,0.20416)
- R57-08: no projected-marker delta was consumed.
- R57-09/10 calculate the IPD-only delta, but intentionally do not apply it visually.

All tested relevant draws are dominated by the fixed-function XYZRHW path. Shader screen-space counters remain zero, so c64/WVP shader work is not the next priority for these defects.

## Conclusions

1. R57-06 falsifies the old assumption that the CPU-projected BAD20 anchor already includes the live head camera. The projected marker requires headInverse + relative-eye inverse + per-eye FOV projection.
2. R57-04 proves treating a rival marker as HUD can remove head following, but destroys correct world attachment/depth. Rival markers must remain projected-world objects.
3. R57-08 is the key 4th+ failure: BAD20 4th+ put_clip calls are visible in HUD tracing, yet no ProjectedWorldMarker2D reaches the R30 owner. R58 must bypass nested semantic propagation and tag the final digit SpriteNode directly.
4. R57-03 proves the finite recentered HUD plane is the correct generic HUD transform. Zero-disparity variants 01/02 are insufficient on the asymmetric OpenXR eye projection.
5. The visible 6th/6 POSITION did not respond even though the known DispRank callsites execute and are statically identified as HUD_RANK. The next test must suppress those producers completely. If the visible element remains, DispRank is not its presentation owner and further coordinate tweaks there are wasted work.

## R58 matrix

- 01: confirmed BAD20 1st-3rd head-inverse path only.
- 02: BAD20 4th+ final-node direct ProjectedWorldMarker2D tag.
- 03: BB3D6 -> BB550 sibling family.
- 04: BB6F0 -> BB796 sibling family.
- 05: BBB85 -> BBC5A sibling family.
- 06: BBDC5 -> BC2E5/BC346 sibling family.
- 07: all projected families together.
- 08: suppress all known DispRank producers.
- 09: direct-tag final DispRank nodes as SCREEN_HUD using configured HudScale.
- 10: same direct ownership with forced 35% finite HUD plane.

Production vr-d3d9ex-focus remains unchanged until HMD validation.
