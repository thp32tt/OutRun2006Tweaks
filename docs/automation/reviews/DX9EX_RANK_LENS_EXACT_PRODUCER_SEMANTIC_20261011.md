# DX9Ex exact-source semantic precedence repair — 2026-10-11

Prior visual source candidate commit `bc7b91794f08b556938e7678ded6bcc8ab3a4ba5` and rank-order CI follow-up `35f6ae4f24294fead95372176c9aa502462c4f8b`.

## Original test evidence
In Quest3/VDXR CORRECTNESS source `9e393cfd` the user's 1st–5th vehicle rank remains detached; the game logs had projected renderer counters yet *no* `VR R57 rank Calc3D2D` capture log. Not evidence of a valid **specific ordinal** source. +TIME six 0x989xx wrapper hooks installed but did not log runtime calls; do not assert extension is solved.

## Exact fix
`ScopedRenderSemantic` previously adjusted only CurrentScope. `EffectiveScope` gives an existing queue node `CurrentQueueExactScope` priority; `CurrentProjectedMarker()` separately reads a potentially older queue payload. Any *immediate* original producer draw could therefore still inherit a previous HUD scope and stale projected position even after patch `35f6ae4f`.

Add `ScopedExactProducerSemantic` which:
- executes only if SpriteQueueDepth == 0; never supersedes a currently rendering real SpriteNode
- saves and restores CurrentScope, CurrentQueueExactScope and CurrentQueueProjectedMarker with RAII
- gives exactly the game `RankMarker_sprani` and `RankMarker_putClipSprite` producers their own recovered world point, or NaviPub exact ScreenHud; keeps post-call queue sibling tagging
- gives original central flare source E8 0xC993 an exact ProjectedScreenEffect2D draw owner; outer halo 0xCABE unchanged
- changes no shader constants, pixels, game simulation, HUD scale, sky color, or timer

The existing targeted stereo SkyGlow transition guard remains from bc7b9179 and the previous EXE+0x97C5F OutRun end/result crash guard remains from 4de8dfaa.

Negatives: `tools/verify_vr_visual_composition_p0.py` rejects removal of queue-depth, projected-payload restore, or exact-rank producer override.

**RUNTIME_VALIDATION=UNTESTED**. Test actual Quest3/VDXR rank tracking, lens centre, mission rival/self time, stage transitions, +TIME and OutRun result crash on one exact package SHA. Do not equate pass build with optical success.
