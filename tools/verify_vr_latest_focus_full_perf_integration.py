#!/usr/bin/env python3
"""Gate merged latest focus visual patches, preexisting R26 GPU performance and stereo-only transactional recovery."""
from pathlib import Path
import configparser
root=Path(__file__).resolve().parents[1]
read=lambda name: (root/name).read_text(encoding="utf-8")
r30=read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
r9=read("src/vr/d3d9/stereo_renderer.cpp")
r23=read("vrhost/src/main_r23.cpp")
host=read("vrhost/src/main.cpp")
aspect=read("vrhost/src/runtime/menu_content_aspect.hpp")
ini=read("OutRun2006Tweaks.ini")
settings=read("src/vr/settings.cpp")
launch=read("tools/vr_perf_quiet/Run-VRPerfQuiet.ps1")
assert "const bool outerFlareObject =" in r30
assert "outerFlareObject ? false : recordedCameraSynced;" in r30
assert "const std::uint32_t projectedObjectId =" in r30
assert "R23TheaterFrameMatchesCapture(" in r23
assert "publishedLogicalCanvasCrop" in r23
assert "ShouldCropFallbackTitleMenu(" in r23
assert "ResolveMenuOpticalCoverageForState(" in r23
assert "PlanTopLeftLogicalCanvasCrop(" in aspect
assert "Setting<float> VRMenuScale{ \"VR\", \"MenuScale\", 0.75f" in settings
assert "MenuScale = 0.75" in ini
assert "'-MenuScale=0.75'" in launch and "'-MenuScale=1.00'" not in launch
assert "bool PreparePendingDirectStereoSource(" in host
assert "bool AcceptPendingDirectStereoSource()" in host
assert "directPendingReady_ = true;" in host
assert "matchedStereoDirect || GetTickCount64()-lastStereoMatchMs<=StereoGraceMs" in host
assert "R9FrameMonoPolicyLatched = true;" in r9
assert "R9NoMonoForActiveVr()" in r9
assert "R9StereoOnlySavedDraws" in r9
ini_cfg=configparser.ConfigParser(interpolation=None)
ini_cfg.read(root/"OutRun2006Tweaks.ini",encoding="utf-8")
assert ini_cfg.getint("Graphics","ReflectionResolution")==256
assert abs(ini_cfg.getfloat("Graphics","ReflectionUpdateRate")-0.25)<0.00001
assert ini_cfg.getint("VR","AntiAliasing")==2
assert ini_cfg.getboolean("VR","CullingUnionFov")
assert not ini_cfg.getboolean("Graphics","TransparencySupersampling")
assert not ini_cfg.getboolean("VR","Telemetry")
assert "'-DirectGpuOnly=true'" in launch
print("PASS latest focus lens+front-end assets and full R26 GPU performance values retained")
print("PASS transactional stereo-only last-good host and game-frame safety preserved")
print("PASS launcher does not override latest focus menu optical size 0.75")
print("RUNTIME_QUEST_HMD_UNTESTED")
