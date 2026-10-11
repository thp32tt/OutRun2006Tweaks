# OutRun VR - GPU Performance Lab (independent test package)

Separate CI artifact OutRun2-VR-GPU-DIAGNOSTIC-<SHA>.zip. Does not replace normal DX9Ex ZIP.
Extract into the game folder with original OR2006C2C.EXE and launch OutRunVR-GPU-Lab.cmd.
Choose A/B/C/D/E or select each field separately, choose WATERFRONT/SAND_SPRAY/DENSE_BUILDINGS,
then click GPU 측정 시작 / 게임 실행. No manual environment variable entry needed.
Game log and RUN_OVERRIDES.txt contain exact settings. Upload auto-collected OutRun2_VR_ANALYZE_*.zip.

A = baseline transparency ON/reflection 1024/SkyGlow 4/culling OFF.
B = A + culling ON; C = B + transparency SSAA OFF; D = C + reflection 512.
E = B + SkyGlow 0 for isolated bloom diagnosis.
Diagnostic always ON in the special GUI: asynchronous GPU D3D9 timestamps, sparse alpha
/depth/stencil/pixel shader state, R32 Draw and triangle workload, CPU/QPC/XR pacing,
optional nvidia-smi GPU utilization, memory and temperature (1s).
These are not an exact water pass, shader occupancy, pixel overdraw or actual GPU utilization from timestamps.
Test identical scene/refresh/render resolution. Compare normal non-profiling build for measurement overhead.
Quest 3 / VDXR runtime verification remains UNTESTED.