# R69 EXP_ALL_V3 — 100-unit diversified review

Reviewed source checkpoint: `f19745bf88bbab6dc765f326148cb557f3984631`

Method: 10 categories × 10 distinct questions. Re-reading the same path with the same question does not count. At least three units per category try to falsify the design rather than confirm it.

## A. Build graph / ownership / binary contract (1–10)
1. Exactly one active D3D9 stereo owner for the selected R26+HUD build — PASS.
2. Included implementation TUs remain HEADER_FILE_ONLY — PASS.
3. Final wrapper TUs compile normally — PASS.
4. Game target remains Win32/x86 compatible — PASS.
5. Host CMake rejects non-x64 configuration — PASS.
6. C++20 requirement is consistent on both sides — PASS.
7. Forced runtime include chain still places R32 after lower hardening layers — PASS.
8. No duplicate hook body introduced by V3 — PASS.
9. cmake.toml and generated CMakeLists retain matching VR owner logic — PASS.
10. Release host still emits PDB for post-failure diagnosis — PASS.

## B. IPC / ABI / identity / wraparound (11–20)
11. Frame.v2 state remains 256 bytes — PASS.
12. Frame ring ABI remains size-asserted — PASS.
13. Direct ACK state remains size/version/magic checked — PASS.
14. x86↔x64 wire fields avoid pointer-sized types — PASS.
15. Direct slot is range checked — PASS.
16. Direct generation must be non-zero — PASS.
17. Producer run generation is validated — PASS.
18. Width/height must match frame backbuffer dimensions — PASS.
19. 32-bit frame newest-order uses signed delta and is wrap-safe inside <2^31 active distance — PASS.
20. Old-run ACK cannot be published into a new run identity — PASS.

## C. XYZRHW shadow ownership / memory scope (21–30)
21. V3 does not auto-shadow every VB after the first XYZRHW draw — PASS.
22. V3 does not auto-shadow every IB after the first XYZRHW draw — PASS.
23. Explicit fixed-function XYZRHW VB can be registered at creation — PASS.
24. Untracked VB Lock fast-rejects through Bloom — PASS.
25. Untracked IB Lock fast-rejects through Bloom — PASS.
26. Untracked Unlock also fast-rejects — PASS.
27. Untracked Release also fast-rejects — PASS.
28. Registry insert/erase increments generation, invalidating thread-local known-miss cache — PASS.
29. Full rollback clears maps/Bloom and increments generation — PASS.
30. Long-session tracked release rebuilds Bloom to avoid stale-bit saturation — PASS.

## D. XYZRHW concurrency / rare ordering (31–40)
31. Registry map access is mutex protected — PASS.
32. Per-shadow byte/range state is mutex protected — PASS.
33. Telemetry counters are atomic — PASS.
34. Hot diagnostic counter increments use relaxed ordering — PASS.
35. First shadow log flags are atomic exchange — PASS.
36. Thread-local lookup cache cannot keep a stale negative after generation change — PASS.
37. Bloom false positive only causes an extra lookup — PASS.
38. Bloom false negative is not expected after completed registration — PASS WITH RACE NOTE F1.
39. Static/existing XYZRHW VB that predates creation hook can fail open rather than GPU-read stall — SAFE/EXPECTED.
40. Indexed XYZRHW IB has no creation-time semantic and can miss its first draw until a later CPU Lock — RESIDUAL TEST ITEM.

## E. SkyGlow correctness / state isolation (41–50)
41. VR SkyGlow working factor remains fixed at 2 — PASS.
42. Normal 2D path is not globally downscaled by this setting — PASS.
43. Cached reduced/temp surfaces are released on resource reset — PASS.
44. Dead vertical blur execution is absent; remaining “vertical” occurrence is comment/FOV math only — PASS.
45. FVF state is captured/restored — PASS.
46. Custom vertex declaration path is captured only when FVF is not active — PASS.
47. Stream0 is restored after DrawPrimitiveUP side effect — PASS.
48. Cull/scissor are forced safe for fullscreen passes and restored — PASS.
49. Depth/RT/viewport/shader/texture/sampler/blend/color-write/PS-c0 touched state is restored — PASS.
50. SkyGlow failure is nonfatal to Present and records failure telemetry — PASS.

## F. DirectGPU zero-copy / producer lifetime (51–60)
51. Direct resource metadata is validated before use — PASS.
52. Descriptor cache is keyed by slot/handle/generation — PASS.
53. Zero-copy fresh projection samples the shared SRV rather than host-eye copy — PASS.
54. Successful projection is followed by R32 asynchronous EVENT consumption fence — PASS.
55. Producer ACK is published only after EVENT completion — PASS.
56. Same-frame cached XR ticks reuse released projection rather than re-sampling shared slot — PASS.
57. Failed fresh projection arms a separate deferred EVENT — PASS.
58. Failed referenced frame is marked processed so it is not sampled again behind an older fence — PASS.
59. Latest-frame skip path refuses immediate ACK when deferred reference is pending — PASS.
60. Deferred query objects are explicitly released on normal/exception host shutdown — PASS.

## G. DirectGPU failure / recovery / generation changes (61–70)
61. Deferred EVENT GetData uses DONOTFLUSH — PASS.
62. EVENT query failure fails closed rather than unsafe ACK — PASS.
63. Producer run change prevents old ACK publication — PASS.
64. Generation change can replace stale deferred state — PASS.
65. Same live slot with unresolved older reference is rejected — PASS.
66. R32 generation fault blocks fast-submit for a bad generation — PASS.
67. R32 DestroySession releases normal pending ACK queries — PASS.
68. Legacy SafeEye timeout now uses QPC rather than coarse GetTickCount64 — PASS.
69. Legacy SafeEye synchronous budget is 2000 µs — PASS.
70. Repeated deferred CreateQuery failure can permanently poison slots within one generation — FINDING F2.

## H. Reset / device loss / OpenXR ordering (71–80)
71. SkyGlow resources are released before D3D9 Reset — PASS.
72. No retained SkyGlow state block crosses Reset — PASS.
73. Shadow capture is disarmed at reset — PASS.
74. COM Release path removes tracked shadow registry entries — PASS.
75. Producer D3D9 fence protects publication readiness — PASS.
76. R32 polling occurs before deciding new fast submit — PASS.
77. Projection source is unbound after D3D11 draw path — PASS.
78. Successful visible projection can complete pending recenter — PASS.
79. Black-screen guard keeps zero-layer/fallback handling in the chain — PASS.
80. Session teardown goes through R32 pending-query cleanup plus compositor shutdown — PASS.

## I. Performance / worst-case frame-time (81–90)
81. Untracked world Lock avoids shadow memcpy — PASS.
82. Untracked world Lock avoids registry mutex in the normal Bloom-negative case — PASS.
83. Untracked world Unlock/Release also avoid registry mutex — PASS.
84. Shadow counters do not impose seq_cst increments — PASS.
85. SkyGlow telemetry caches QueryPerformanceFrequency — PASS.
86. Production HUD trace remains telemetry-gated — PASS.
87. Direct descriptor GetDesc repetition remains cached — PASS.
88. Normal R32 path does not synchronously wait for GPU completion — PASS.
89. Legacy fallback still contains Flush; 2 ms polling cap cannot bound driver cost inside Flush itself — RESIDUAL PERF RISK.
90. Explicit SkyGlow touched-state save/restore still has many Get*/Set* calls and must be A/B measured against D3DSBT_ALL — RESIDUAL PERF TEST.

## J. CI / reproducibility / test packaging (91–100)
91. V3 branch is a workflow trigger — PASS.
92. EXP_ALL_V3 is a distinct matrix candidate — PASS.
93. Source SHA is stamped in the package — PASS.
94. Package receives SHA256SUMS — PASS.
95. Candidate is marked TEST_ONLY_NOT_FOR_INTEGRATION — PASS.
96. Matrix fail-fast is disabled so one experiment does not hide the rest — PASS.
97. Shader smoke is built/run — PASS.
98. R32 policy and Direct ACK identity smokes are built/run — PASS.
99. Protocol/core/host-state/conversion/pose smokes are built/run — PASS.
100. Test order selects EXP_ALL_V3 first and keeps older isolated candidates for diagnosis — PASS.

# New findings

## F1 — Bloom publication ordering race
Severity: P1 hardening / multithreaded correctness.

Current registration order under the registry mutex is:
`map.emplace(buffer) -> Bloom.fetch_or(bit) -> generation++`.

The vtable Lock hook does not take the registry mutex when the Bloom bit is absent. With a genuinely multithreaded D3D9 workload, another thread can Lock the just-registered buffer in the small window after `emplace` but before `fetch_or`, causing that CPU write to be missed.

Recommended fix: publish the Bloom bit before map insertion/visibility. A transient false positive is safe: Lock will enter the registry mutex and wait for registration; a false negative can lose bytes.

## F2 — Deferred EVENT CreateQuery failure can poison a live generation
Severity: P1 resilience.

If `CreateQuery(D3D11_QUERY_EVENT)` fails, the slot becomes `armed=true, poisoned=true` with no query. Polling intentionally skips it. A later different frame reusing the same slot in the same run/generation also fails closed. Repeated failures can eventually pin all four producer slots until transport generation changes.

Recommended fix: on query creation failure, mark the DirectGPU generation faulted/disabled and route to cached/classic fallback, or introduce a bounded query-recreation recovery policy. Do not ACK the referenced frame unsafely.

# Residual runtime checks
- Newly created indexed XYZRHW IB first-draw fail-open.
- Cost of global vtable detours after Bloom fast reject.
- P5 vs V3 frame-time P95/P99 in the same heavy scene.
- Explicit SkyGlow state save/restore vs state-block A/B.
- Frequency of legacy SafeEye fallback/Flush under real VDXR load.

Result: 100/100 diversified review units completed. Two new actionable findings (F1, F2). No new P0 visual/lifetime defect found in the normal success path.
