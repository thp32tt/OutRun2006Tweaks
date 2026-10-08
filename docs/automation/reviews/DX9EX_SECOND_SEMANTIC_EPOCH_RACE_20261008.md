# DX9Ex second full-source review: cross-thread semantic epoch race

The exact HUD sprite producer previously reserved `SpriteNodeSemanticNextSerial` before taking the registry mutex. If preempted, render queue's unlocked serial cutoff could advance to that reserved number. The subsequent node tag inserted after queue start was then deleted as stale at queue end, even if it belonged to the next frame. Loss of exact ScreenHud/WorldBillboard/Projected ownership can fall back to generic ScreenOverlay2D; this is a source-proven interleaving, not a claim that a user HMD symptom was reproduced.

Fix `src/vr/game/render_semantics.hpp`: issue producer serial **inside** the registry lock; snapshot the cutoff **under the same lock** in both eager Begin and active lazy Select. Lock released before node Consume. Extend existing `verify_vr_cross_thread_semantic_registry.py` with 3 ordering contracts and 3 negative lock-removal injections. Runtime validation UNTESTED.
