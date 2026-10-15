# CONVERSION-DX9EX-00549 — DDS cache source splice recovery

- Event: CONVERSION-DX9EX-00549-E002; rollover 2; ATTEMPT=1/3 unchanged.
- Confirmed base GitHub HEAD: `8c6bd34c034a1097b12b366b0833dd623e18b515`.
- Previous `00548` is COMPLETE_BUILD_VERIFIED and is not repeated; `00549` had no prior run file at this base.
- Direct source diff of `c0cf0852df0921a09c7f92ba11e1182ba7642806` exposed an invalid C++ paste: `cacheFolder` lost its directory-iterator loop/closing brace, `cacheFile` was spliced onto an incomplete token, and an orphaned error-message tail remained after its closing brace.
- Restore `cacheFolder`'s original scan and regular-file dispatch; remove only the orphaned tail. Preserve `cacheFile`'s recently introduced short cache-lock / background I/O / shared-owner behavior.
- Harden `verify_vr_texture_cache_lifetime.py`: assert preloader traversal, sibling function boundaries, clean end of `cacheFile`; four new negative mutations cover directory-loop loss and an injected post-function orphan (17 total).
- Static source checks are not equivalent to hosted compiler success or HMD runtime validation. RUNTIME_VALIDATION=UNTESTED.
