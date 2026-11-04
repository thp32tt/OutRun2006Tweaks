# Dino 246 GTS V15 R2 vehicle selection inflater crash mitigation

User's game EXE (SHA256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3) raised a write access violation 0xC0000005 at 0x0043C030. Memory dump opcode is 88 06, an 8-bit write during DEFLATE decoding. This occurred at vehicle selection, before any VR frame was recorded.

The user's unmodified Dino PMT (SHA256 1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284) inflates to 739,216B, whereas v15 R1 inflated to 2,161,528B. An output buffer capacity violation is a plausible cause, but the hard game allocator limit has **not** been proven.

R2 performs topology-aware tube row decimation on high-density rings, controls, trims and stitching; original 70 groups and all 19 new, distinct 128x128 BC1 textures remain. Model: 21,100 vertices, 38,992 triangles; model payload SHA256 3ea734229c9e0745d103e854ce949e5e24289a52987773712601837f591de282. The resulting fully textured PMT inflates to 1,881,432B, versus 2,161,528B R1; budget saving 280,096B. R2 local manifest SHA256 04fb781657c42273bae8a3e18f9d5682dfbdb86d62b32defef76eb8c851b4a41.

Guard refuses PMT output with uncompressed size >= 1,900,000B **before writing game assets**. Threshold is conservative/experimental, not a guaranteed game limit.

Validation: actual R2 model decoded, 70 material groups, 19 material indexes, 38,992 in-bound triangles; indices safely reindexed during tube decimation; no duplicate surviving tube triangles. Synthetic original-game PMT patch on N100: V15_R2_SAFE_BUDGET_STRUCTURAL_PASS, original 739,216B raw, R2 1,881,432B, 60 texture slots including preserved original 41, 104 object0 materials.

User installation: first run R1 RESTORE-DINO-COCKPIT-V15.cmd to restore exact backup; leave .dino-v12-original.bak untouched; then extract R2 and install. Do not overwrite an unrecognized mod. Separate test branch; OutRun main / DX11 / DXVK branches unchanged.

RUNTIME_VALIDATION=UNTESTED. The user must verify real game/HMD; lowering below the hypothesized cap does not establish crash resolution.
