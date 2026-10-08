# Second full-source DX9Ex audit: rank producer multi-node coverage

The canonical rank sprani producer (`0xBB0FB/0xBB133/0xBB16C/0xBB1A5` original EXE CALLs) previously tagged only the last appended SpriteNode per priority. The same source uses a bounded `TagAppendedNodes` linked-list helper for rival sprites. If a rank animation enqueued more than one node, earlier siblings had no exact world/HUD semantic and inherited generic ScreenOverlay2D, potentially contributing to doubled/misplaced rank markers. This is a **latent multi-node coverage gap**, not proof that normal 1st/2nd/3rd nodes are actually multiple.

The original helper is moved ahead of rank wrapper and reused with the same rank scope and projected-marker payload for *all* nodes appended during this exact call. Existing guard `Game::SpriteNodeMax` retained. No EXE hook address or other HUD category changed. Source contract now requires the all-node bridge. Runtime UNTESTED.
