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


policy = require(
    "src/vr/d3d9/r32_policy.hpp",
    "RearmMonoSafetyEpoch",
    "ForceZeroDisparity",
    "ProducerFenceBudgetMs = 2",
    "PendingFenceDecision",
    "ClassifyPendingFence",
)

r32 = require(
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    '#include "stereo_renderer_r31.cpp"',
    "R32ResetR22Hook",
    "reinterpret_cast<void*>(&ResetDestR22)",
    "R32ResetAfterGameReset",
    "R32InvalidateResetCaches",
    "R29MonoSafetyThroughEpoch = OutRunVR::R32::RearmMonoSafetyEpoch",
    "R32EffectIsFragileLive",
    "draw is forced to stock-WVP zero disparity",
    "R32SetWvpBatch",
    "OutRunWvpRegisterCount",
    "R32WaitProducerFence",
    "QueryPerformanceCounter",
    "Budget starts before the FLUSH request",
    "R32ProducerFencePending",
    "R32DrainPendingProducerFence",
    "timed-out producer EVENT remains pending",
    "R32DirectIdentityMatches",
    "VR R32 PERF 5s",
    "VR R32 REVIEW2",
)
if "R32ResetR13Hook" in r32:
    raise SystemExit("R32 must no longer install a competing ResetDestR13 hook")
if "R22ShadowState = {};" in r32[r32.find("void R32ResetAfterGameReset"):]:
    raise SystemExit("R32 successful Reset post-processing must preserve R22's freshly primed viewport/scissor shadow")

r33 = require(
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    '#include "stereo_renderer_r32.cpp"',
    "R31OwnedResult R33TryFastWorld",
    "R31OwnedResult R33TryHud",
    "R31ObserveDraw(device)",
    "R32LowerFailClosed",
    "R31DiscardUnreliableDrawCaches();",
    "changing one tracked render state cannot",
    "R30DrawPrimitiveR29Hook",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "R33 -> R32 -> R22",
    "top-level telemetry counted once",
)
if "const HRESULT hr = ResetDestR22" in r33:
    raise SystemExit("R33 must not bypass the corrected R32 Reset lifecycle")

require(
    "vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp",
    "R32SharedSlotCache",
    "R32OpenSharedSlot",
    "R32InactiveEye",
    "R32SafeTimeoutPreserves",
    "queued copy cannot mutate SafeFrameId image identity",
    "EnsureSafeFrameR32",
)

host_direct = require(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    "CanFastSubmit",
    "ProjectionMatchesSnapshot",
    "ArmConsumptionFence",
    "D3D11_ASYNC_GETDATA_DONOTFLUSH",
    "flushIssued",
    "deferred until actual direct-ring slot pressure",
    "PublishCompletedFrame",
    "AckedFrame",
    "AckedGeneration",
    "R32 direct PERF 5s",
    "verified incoming DirectGPU projection submitted once",
    "OutRunVrR26RecenterHardening::EndFrame",
)
# Flush remains permitted only in the slot-pressure escalation block. Reject the
# old unconditional End(query)+Flush() sequence.
if "Context->End(pending.fence);\n        OutRunVrFinalTest::Context->Flush();" in host_direct:
    raise SystemExit("R32 host must not Flush every direct frame")

require(
    "vrhost/src/main_r23.cpp",
    "R23DirectHoldState",
    "R23StageDirectHold",
    "grace projection no longer samples ACK-reusable producer slots",
    "srv[0] = R23DirectHold.srv[0]",
)

require(
    "src/vr/d3d9/ex_device_upgrade_r14.cpp",
    "singleLevelTexture",
    "entry.gpu->GetLevelCount() <= 1",
)

require(
    "vrhost/tests/r32_policy_smoke.cpp",
    "RearmMonoSafetyEpoch(1) == 3",
    "EffectSnapshotDecision::ForceZeroDisparity",
    "ProducerFenceBudgetMs <= 2",
    "PendingFenceDecision::BlockReuse",
    "PendingFenceDecision::QueryError",
)

cmake = require(
    "cmake.toml",
    "R33/R14 keep the validated",
    "stereo_renderer_r31.cpp",
    "stereo_renderer_r32.cpp",
    "PROPERTIES HEADER_FILE_ONLY TRUE",
)
included_start = cmake.find("set(OUTRUN_VR_INCLUDED_IMPL_TUS")
included_end = cmake.find(
    "set_source_files_properties(${OUTRUN_VR_INCLUDED_IMPL_TUS}",
    included_start)
final_start = cmake.find("set(OUTRUN_VR_FINAL_TUS", included_end)
final_end = cmake.find("foreach(_vr_source", final_start)
if min(included_start, included_end, final_start, final_end) < 0:
    raise SystemExit("could not locate list-based VR source ownership blocks")
header_section = cmake[included_start:included_end]
final_section = cmake[final_start:final_end]
if "stereo_renderer_r31.cpp" not in header_section or \
        "stereo_renderer_r32.cpp" not in header_section:
    raise SystemExit("R31/R32 must be include-only implementation TUs")
if "stereo_renderer_r33.cpp" in header_section:
    raise SystemExit("R33 final TU must not be include-only")
if "stereo_renderer_r33.cpp" not in final_section or \
        "ex_device_upgrade_r14.cpp" not in final_section or \
        "outrun_renderer_r29.cpp" not in final_section:
    raise SystemExit("final VR wrapper TU list is incomplete")

generated = require(
    "CMakeLists.txt",
    "set(OUTRUN_VR_INCLUDED_IMPL_TUS",
    "set(OUTRUN_VR_FINAL_TUS",
    "stereo_renderer_r33.cpp",
    "ex_device_upgrade_r14.cpp",
    "outrun_renderer_r29.cpp",
)
for source in (
    "src/vr/d3d9/stereo_renderer_r31.cpp",
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    "src/vr/d3d9/ex_device_upgrade_r14.cpp",
    "src/vr/game/outrun_renderer_r29.cpp",
):
    if source not in generated:
        raise SystemExit(f"generated CMakeLists is stale: missing {source}")

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

print("R32/R33 review-2 consolidation verification passed")
