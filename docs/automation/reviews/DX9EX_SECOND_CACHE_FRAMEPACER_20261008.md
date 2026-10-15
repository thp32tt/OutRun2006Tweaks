# 2026-10-08 Second full-source review: cache I/O lock frame hitch

Source-level confirmed **performance cross-effect** after prior race/UAF mitigation:

- Previously `FileDataCache::cacheFile` acquired `mtx1` then opened, sized, allocated, read and inserted a DDS (up to the 64 MiB VR cache cap), all while other cache hits in `getFileData` also needed the same `mtx1`.
- When the preload thread was warming menu/world DDS files, unrelated game/HUD cache hits were blocked behind disk reads. Successful static safety tests could not catch this VR frame-pacing issue.

Repair:
- Separate `cachePopulationMutex` serializes writers and avoids competing allocations/duplicate inserts. The existing `mtx1` only covers cache hits, budget accounting and LRU mutations; actual disk open/read and `shared_ptr<vector>` allocation run outside `mtx1`.
- Eviction before allocation is preserved for the 32-bit process; recheck size/budget and evict again under `mtx1` when publishing. Background cache-hit reads can proceed during the I/O window.
- No new buffers survive beyond the existing shared source-owner contract, and transient DDS remains available for oversized replacements.
- `verify_vr_texture_cache_lifetime.py` adds 5 lock-scope/publish checks and 3 deliberate mutations (13 total), linked from P0/HUD inspector and exact-SHA DX9Ex Active.

Risk note: a game cache *miss* may still wait for background cachePopulationMutex; fully independent asynchronous loads require design-level scheduling rather than simply relaxing all locks.

RUNTIME_VALIDATION=UNTESTED; do not claim proven 90Hz performance improvement before headset benchmark.
