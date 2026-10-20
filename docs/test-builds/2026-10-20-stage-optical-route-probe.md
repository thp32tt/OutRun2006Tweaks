# 2026-10-20 +TIME Optical Route Probe (diagnostic only)
Candidate branch: vr-d3d9ex-candidate/stage-optical-probe-20261020
Protected HMD-stable: 0cff83cf509c; branch vr-d3d9ex-stable-20261020-0cff83cf unchanged.
Use exact-SHA DX9Ex Active Validation test ZIP, normally START_DX9EX_TEST.cmd (do not install over the stable backup).
At runtime use F11 [VR] or OutRun2006Tweaks.ini [VR]:
StageOpticalProbeMode=0 Off: unchanged R84 (default).
1 Native: exact +TIME original one Draw, likely one eye (diagnostic only).
2 FiniteHud: current R84 2.50 game-unit HUD plane.
3 ZeroDisparity: identical left-eye source clip in both D3D9 eye targets; canted XR views still can differ, so diagnostic only.
4 Hidden: suppress exact +TIME GPU Draw to isolate source.
StageOpticalProbeTarget=0 All, 1 Direct numeric/text only, 2 Queued sprani only.
Test Hidden separately with target 1/2 to identify sprite versus digits; test 0/2/3 with Quest3 eye fusion, yaw 15 degrees and 10 cm translation. Log VR STAGE OPTICAL PROBE (Telemetry=true), compare same user scene, return mode 0 afterward. Other HUD, GOAL, 4/5 rank, rival, sky and F11 remain protected. Runtime validation=UNTESTED until user exact-build optical test. Native/Hidden modes intentionally break +TIME display, never leave active as normal gameplay.
