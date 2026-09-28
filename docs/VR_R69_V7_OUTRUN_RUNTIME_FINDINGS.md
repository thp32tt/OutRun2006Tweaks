# R69 V7 OutRun runtime findings

Runtime source tested by user: `92ce3403c6e68fe5c945b88440e5fa7d5d23cd4d` (V6).

## User-visible evidence
- Overall image is washed/white; HUD/menu appear semi-transparent.
- Menu < > remains head-following.
- Car-selection 3D and initial-grid shadow remain incorrect.
- Brief stage-transition sky corruption improved.
- OutRun intermediate remaining-time update is doubled/split.
- OutRun final goal/result presentation is doubled/split.
- Earlier Mission-mode testing did not expose these OutRun-only paths.

## Uploaded analyze evidence
- DirectGPU transport is healthy; no fence-timeout pattern explains these visuals.
- HUD semantic coverage reports 4,858 unknown rows.
- R65 TIME HUD and R66 GOAL TIME HUD producers were not observed in this OutRun session.
- Unknown canonical 2D queue rows appear in STATE_GAME (0x10) and STATE_GOAL (0x13).
- STATE_RESULT (0x16) had no corresponding unknown cluster, so the visible final double is produced during GOAL presentation, not RESULT.

## V7 changes
1. Restore R69 full D3DSBT_ALL SkyGlow state boundary while retaining current cached glow resources/passes. This tests/removes the explicit touched-state experiment as a source of washed color / UI state leakage.
2. Promote only unclassified canonical 2D queue nodes in STATE_GOAL to ScreenHud. Existing exact tags remain authoritative.
3. Add bounded committed-stack raw RVA diagnostics for unknown STATE_GAME / STATE_GOAL sprite events. The intermediate checkpoint overlay remains diagnostic-only until its exact producer is recovered.

## Explicitly unchanged
- Menu arrow ownership.
- Car-selection 3D path.
- Initial-grid shadow policy.
- Stage-transition hold/recovery.
- DirectGPU/R32 host synchronization.
