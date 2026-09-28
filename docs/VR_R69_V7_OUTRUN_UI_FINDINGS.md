# R69 V7 OutRun UI runtime findings

Runtime source tested by user: `92ce3403c6e68fe5c945b88440e5fa7d5d23cd4d`.

Observed in HMD:
- overall image soft/washed/white;
- HUD/menu appear translucent;
- menu `< >` remains doubled/head-following;
- OutRun checkpoint remaining-time update is split;
- final OutRun result UI is split;
- selector-car 3D and start-grid shadow remain broken;
- stage-transition sky improved.

Runtime ZIP evidence:
- DirectGPU transport stable; no stereo failure/fence-timeout explanation.
- existing `VR R66 OPTION ARROW`, `VR R65 TIME HUD` and `VR R66 GOAL TIME HUD` hooks recorded zero hits in this OutRun session.
- sprite `0x3004A` was observed from exact `put_clip_sprite` caller RVAs `0x460F1`, `0x463D6`, `0x46410`.
- canonical text glyph tagging remained active.
- CORRECTNESS launched with `SkyGlowFactor=1`, while the experimental renderer ignored it and forced working factor 2.

V7 changes:
1. Restore requested SkyGlow factor, so CORRECTNESS uses factor 1.
2. Composite stereo SkyGlow at the first HUD boundary, before HUD/menu draw, not additively over completed UI.
3. Tag the three runtime-proven OutRun arrow callsites, protected by exact arrow asset IDs.
4. Add `R69_V7_UIFIX`: HUD experiment mode 4 promotes only generic SpriteNode ScreenOverlay2D to the finite HUD plane; exact rank/flare/world owners retain priority.
5. Preserve R68 three-present stage hold.

Not claimed fixed by this candidate:
- selector-car 3D rendering;
- start-grid shadow corruption.
Those remain separate world/effect defects and should not be mixed into this UI candidate until V7 HMD evidence is collected.
