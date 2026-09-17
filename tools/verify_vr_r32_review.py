from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"R32/R33 verification missing file: {rel}")
    return path.read_text(encoding="utf-8")


def require(rel: str, *markers: str) -> str:
    data = load(rel)
    for marker in markers:
        if marker not in data:
            raise SystemExit(f"R32/R33 invariant missing: {rel} :: {marker}")
    return data


require(
    "src/vr/d3d9/r32_policy.hpp",
    "RearmMonoSafetyEpoch",
    "ForceZeroDisparity",
    "ProducerFenceBudgetMs = 2",
)
require(
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    '#include "stereo_renderer_r31.cpp"',
    "R32ResetAfterGameReset",
    "R29MonoSafetyThroughEpoch = OutRunVR::R32::RearmMonoSafetyEpoch",
    "R32EffectIsFragileLive",
    "draw is forced to stock-WVP zero disparity",
    "R32SetWvpBatch",
    "OutRunWvpRegisterCount",
    "R32WaitProducerFence",
    "D3DGETDATA_FLUSH",
    "ProducerFenceBudgetMs",
    "R32DirectIdentityMatches",
    "VR R32 PERF 5s",
    "VR R32 REVIEW",
)
require(
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    '#include "stereo_renderer_r32.cpp"',
    "R31ObserveDraw(device)",
    "R32TryFastWorld",
    "R32TryHud",
    "R32LowerFailClosed",
    "R30DrawPrimitiveR29Hook",
    "top-level draw telemetry is counted exactly once",
)

require(
    "vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp",
    "R32SharedSlotCache",
    "R32OpenSharedSlot",
    "R32InactiveEye",
    "R32SafeTimeoutPreserves",
    "queued copy cannot mutate SafeFrameId image identity",
    "EnsureSafeFrameR32",
)
require(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    "CanFastSubmit",
    "ProjectionMatchesSnapshot",
    "ArmConsumptionFence",
    "D3D11_ASYNC_GETDATA_DONOTFLUSH",
    "PublishCompletedFrame",
    "verified incoming DirectGPU projection submitted once",
    "redundant SafeEye copy + second projection removed",
    "OutRunVrR26RecenterHardening::EndFrame",
)
require(
    "vrhost/tests/r32_policy_smoke.cpp",
    "RearmMonoSafetyEpoch(1) == 3",
    "EffectSnapshotDecision::ForceZeroDisparity",
    "ProducerFenceBudgetMs <= 2",
)

cmake = require(
    "cmake.toml",
    "R33/R14 keep the validated",
    "stereo_renderer_r31.cpp",
    "stereo_renderer_r32.cpp",
    "PROPERTIES HEADER_FILE_ONLY TRUE",
)
vr_start = cmake.find(
    "set_source_files_properties(\n    src/vr/d3d9/ex_device_upgrade.cpp")
vr_end = cmake.find("PROPERTIES HEADER_FILE_ONLY TRUE", vr_start)
if vr_start < 0 or vr_end < 0:
    raise SystemExit("could not locate VR HEADER_FILE_ONLY ownership block")
header_section = cmake[vr_start:vr_end]
if "stereo_renderer_r31.cpp" not in header_section or \
        "stereo_renderer_r32.cpp" not in header_section:
    raise SystemExit("R31/R32 must be include-only implementation TUs")
if "stereo_renderer_r33.cpp" in header_section:
    raise SystemExit("R33 final TU must remain independently compiled")

host_cmake = require(
    "vrhost/CMakeLists.txt",
    "d3d9ex_direct_passthrough_r32.hpp",
    "r32_direct_submit.hpp",
    "outrun-vr-r32-policy-smoke",
)
if host_cmake.find("d3d9ex_direct_passthrough_r32.hpp") > \
        host_cmake.find("r22_runtime_hardening.hpp"):
    raise SystemExit("R32 SafeEye A/B override must precede R22/R23/R24")
if host_cmake.find("r32_direct_submit.hpp") < \
        host_cmake.find("r26_recenter_hardening.hpp"):
    raise SystemExit("R32 direct submit must be final xrEndFrame owner after R26")

print("R32/R33 review consolidation verification passed")
