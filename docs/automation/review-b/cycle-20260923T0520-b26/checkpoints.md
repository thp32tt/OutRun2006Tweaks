# B26 checkpoints

Target integration: `539fecf218d39cea103da6ccc23f59eb7498185f`
USER_RUNTIME_VERIFIED baseline: `17ad376bfdf7939f0851c0c629e4fa094a84f28a` / CORRECTNESS.
Role B review-only; production/candidate source modified: NO.
Fresh focus: R51 protected semantic ownership/rank producer paths, current-HEAD absence, R30 shadow/SkyGlow performance/state boundaries, candidate divergence and anti-regression falsification.

- CP10 rows=10 fresh=10 carry=0
- CP20 rows=20 fresh=20 carry=0
- CP30 rows=30 fresh=30 carry=0
- CP40 rows=40 fresh=40 carry=0
- CP50 rows=50 fresh=50 carry=0
- CP60 rows=60 fresh=60 carry=0
- CP70 rows=70 fresh=70 carry=0
- CP80 rows=80 fresh=75 carry=5
- CP90 rows=90 fresh=75 carry=15
- CP100 rows=100 fresh=75 carry=25
- CP110 rows=110 fresh=75 carry=35
- CP120 rows=120 fresh=75 carry=45
- CP130 rows=130 fresh=75 carry=55
- CP140 rows=140 fresh=75 carry=65
- CP150 rows=150 fresh=75 carry=75 COMPLETE

Diversity: 15 cross + 15 adversarial + 15 path + 15 regression + 15 performance fresh units; 75 distinct named objectives/paths; outside-current-delta >=25.

## Findings / handoff
R51 screen semantic queue ownership and exact rank-marker WORLD_BILLBOARD tagging remain absent from current integration HEAD. This is evidence augmentation for existing protected/open R51 regression keys, not a new duplicate finding.
Current HEAD and R51 remain diverged at merge-base 4ff3a3f; an old R51 candidate cannot be directly treated as a current C candidate.
R30 CPU shadow avoids draw-time GPU Lock and SkyGlow restores stateblock plus RT/depth/viewport; no new static P0/P1 performance defect promoted. Runtime pacing remains NEED_HMD_TEST.

## exact nextAction
C: construct a fresh candidate from current integration HEAD with explicit R51->candidate and HEAD->candidate BASELINE_DELTA. Preserve R51 world-stereo/frame-stability invariants, restore only proven semantic ownership needed for exact HUD/rank fixes, preserve SkyGlowFactor=1 and TargetRefreshRateHz=0. D independently reviews/integrates/packages.
