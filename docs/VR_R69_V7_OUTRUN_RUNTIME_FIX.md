# R69 V7 OutRun runtime correction

Source checkpoint: `06b801dd9e0f8dd2544b1296132547ca59959011`

Evidence: V6 HMD session in OutRun mode.

## Correctness fixes

1. SkyGlow state isolation
   - Restore full `D3DSBT_ALL` state-block barrier used by the known P5/P3 correctness path.
   - Keep resource caching and dead-pass removal.
   - Restore configured `SkyGlowFactor` instead of forcing factor=2. The captured V6 config requested factor=4.

2. Menu arrows
   - Existing 12 arrow owners had zero runtime hits in the reported menu.
   - V6 HUD trace observed sprite 0x3004A from exact call edges:
     - 0x460F1
     - 0x463D6
     - 0x46410
   - These are added to the existing queue-node SCREEN_HUD pinning path.

3. OutRun checkpoint HUD
   - Exact direct `put_sprite_ex2` edge 0x2D5A0 / sprite 0x3000B appeared only as short bursts around OutRun checkpoint transitions in the captured session.
   - Pin the produced queue node to SCREEN_HUD.

4. OutRun result HUD
   - Result phase mode=20, stage=13 exposed exact direct edges:
     - put_sprite_ex: 0x2D26C, 0x2D2EC (sprite 0x30001)
     - put_clip_sprite: 0x97BB7, 0x97DA7 (sprite 0x30002)
   - Pin only nodes produced from these exact edges to SCREEN_HUD.

## Deliberately unchanged
- Initial-grid shadow classification.
- Car-selection 3D rendering.
- Generic 0x28E81 put_sprite_ex2 path.
- R29/R34 renderer policy.
- DirectGPU/R32 transport.

Those remain separate issues and are not widened by this correction.

Status: TEST_ONLY_NOT_FOR_INTEGRATION until HMD validation.
