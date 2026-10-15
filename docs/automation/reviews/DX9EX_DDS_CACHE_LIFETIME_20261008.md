# DX9Ex cross-thread DDS cache lifetime defect — 2026-10-08

Confirmed source-level race before this change:
- `FileDataCache::cacheFile` and preload `cacheFolder` updated `cache`, `lru_list` and `current_cache_size` under `mtx1`; concurrently `getFileData` read and reordered that same cache under unrelated `mtx2`.
- Cached entries were bare `std::vector<uint8_t>` and `getFileData` returned `it->second.data.data()` after its local lock. Preload could evict/reallocate an entry before D3DX consumed those bytes. This is a real mutex mismatch plus source pointer lifetime defect; its manifestation on Quest 3 remains untested.

Repair:
- Cache entries use `shared_ptr<vector<uint8_t>>`; cache preloading and lookup/LRU/budget use one `mtx1`, with no nested lock during `cacheFile`.
- `getFileData` serializes request load with `mtx2`, acquires the cached shared owner under `mtx1` and publishes a raw pointer **only after** attaching the owner to `transientOwner`; D3DX wrappers retain it across fast/native retries. Eviction can unlink the entry but cannot free a still-in-use source buffer.
- `getCacheSize` snapshot is synchronized with `mtx1`.
- `tools/verify_vr_texture_cache_lifetime.py --self-test` enforces 16 ownership invariants and ten deliberate source corruptions; P0/HUD Inspector/DX9Ex CI watch it.

No N100 clone or hardware request. Exact-SHA compile/static gates required before declaring build verification; runtime remains UNTESTED.
