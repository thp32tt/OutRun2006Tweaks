# DX9Ex 16G follow-up implementation — 2026-10-22

Source log: 16.57 GiB OutRun2006Tweaks.log previously archived in docs/evidence/DX9EX_16G_LOG_ANALYSIS_20261022.md.

Implemented/retained for this test package:
- CABE projected lens flare: retain the R69 exact ProjectedScreenEffect2D same-source dual-eye path already committed from the 16G provenance.
- Rival marker: retain stock/DX11-equivalent BB6F0 + BB796 path with RivalDx11NativeRoute=true; the capture itself contained no rival event, so this is Git-history regression recovery rather than a claim from the 16G runtime trace.
- Ordinal rank 1..5: retain exact BAEE2 source capture and projected marker path. The 16G capture proves valid Calc3D2D anchor and stereo-capable physical route; HMD optical correctness remains untested.
- GOAL/result progress: no geometry rewrite. The 16G capture showed bounded LEFT/RIGHT S_OK with projectionRestored=true; duplicate optical output therefore requires HMD-correlated transform/geometry evidence rather than another blind GPU-route rewrite.
- +TIME: no coordinate rewrite. The 16G capture did not observe its exact producer, so modifying it from this dataset would be speculative.
- F11: fix a source-confirmed telemetry format defect. The format previously hard-coded mode=FOV_ONLY_SCREEN2D while still passing a dynamic mode argument, shifting all following scissor and HRESULT fields. It now uses mode={} so the log reflects the actual FINITE_WORLD_LOCK_065/FOV_ONLY_FAILSAFE branch and correct L/R scissor + HRESULT values.

Validation before package build:
- tools/verify_vr_f11_probe_telemetry.py PASS
- tools/verify_vr_rank_dx11_reference.py PASS
- tools/verify_vr_dx9ex_launch_paths.py PASS
- tools/verify_vr_20261020_hmd_baseline.py PASS
- Quest3/VDXR runtime validation remains UNTESTED.
