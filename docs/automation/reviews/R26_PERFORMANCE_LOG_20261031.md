# R26 user log review 2026-10-31
TASK_ID: USER-DX9EX-PERF-REFLECTION256-20261031
Branch: perf/r26-copy-math-aa-20261028
Base: e10927a2d9e832d1e292cb5086f96233c1d85381
Input: R26_PERF_COPY_MATH_AA2_TEST-20261031-001223.zip
Host build marker: 6b75e5cbd70f; pipeline gameBuild unknown. User reports no visible screen faults, no large subjective performance improvement. Not a full visual acceptance matrix or controlled FPS benchmark.
42 pipeline interval records with actualFinal=projection-direct-r32-fast:
commitAvgMaxP95 p95 range 0.003–0.0049ms; render p95 0.739–1.096ms; xrEndFrame p95 2.0228–23.6633ms. CPU-call elapsed times, not GPU timestamp timings. Interval totals xr16675/fresh16218/cached201; intervals can contain other routes, not a pure gameplay FPS denominator.
90Hz runtime period 11.1111ms. Lower-Present at 00:17:09 avg8.768ms max26.430ms with952.5 draws/Present. This is consistent with wait/backpressure or expensive rendering, not proof of one GPU bottleneck.
Applied user request: reflection512->256 in INI + command-line launcher + packaging notes + profile checker. Each reflection face pixel area is one-quarter; total frame cost reduction unknown. MSAA2/culling8/diagnostics unchanged.
Next candidates: combine four contiguous WVP constant uploads into one only after partial-failure restoration tests; investigate per-draw world epoch rebind and redundant state calls with stateblock/reset invalidation; particle/water lower-resolution rendering needs confirmed pass identity and depth/stereo composition validation. No speculative draw deletion.
Validation: profile checker required; CI triggered by commit. New256 profile runtime UNTESTED. tested source strictly6b75e5cbd70f. No mainline merge.
