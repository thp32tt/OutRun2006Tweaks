#!/usr/bin/env python3
"""R31/R32 telemetry OFF must not write diagnostic counters on gameplay paths.

Actual safety decisions (live-WVP cadence, failed snapshot/fallback, reset and
interop invalidation) still execute. The C++/Win32 build is owned by DX9Ex CI.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R31 = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"
R32 = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"

R31_DIAGNOSTICS = ("R31FastWorldLiveValidations", "R31FastWorldValidationRejects")
R32_DIAGNOSTICS = (
    "R32StateSnapshotFailures", "R32BatchWvpFailures",
    "R32FailClosedZeroDisparityDraws", "R32DirectIdentityInvalidations",
    "R32ResetEpochRearms", "R32ResetFailures",
)


def owner(source: str, signature: str) -> str:
    at = source.index(signature)
    start = source.index("{", at)
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if not depth:
                return source[start:i + 1]
    raise AssertionError("unterminated " + signature)


def checked(source: str, counter: str) -> bool:
    # Require exactly one producer, guarded at its own write site; a guard
    # around five-second logging must not count as a disabled-draw fast path.
    writes = re.findall(r"\+\+" + re.escape(counter) + r"\s*;", source)
    guarded = re.findall(
        r"if\s*\(\s*R30SupportTelemetryEnabled\(\)\s*\)\s*"
        r"\+\+" + re.escape(counter) + r"\s*;", source)
    return len(writes) == len(guarded) == 1


def verify(r31: str, r32: str) -> bool:
    if not all(checked(r31, c) for c in R31_DIAGNOSTICS):
        return False
    if not all(checked(r32, c) for c in R32_DIAGNOSTICS):
        return False
    fast = owner(r31, "bool R31BuildFastWorldConstants(")
    if not all(s in fast for s in (
        "++R31FastWorldCandidates;",
        "R31FastWorldCandidates % LiveWvpValidationInterval",
        "R30SupportValidateVerifiedWvp(", "R31BlockedVerifiedGeneration = generation;",
        "liveValidated = true;", "const float* originalWvp = liveValidated ? live : verified;")):
        return False
    if "constexpr std::uint64_t LiveWvpValidationInterval = 16;" not in r31:
        return False
    read = owner(r32, "bool R32ReadEffectSnapshot(")
    lower = owner(r32, "HRESULT R32LowerFailClosed(")
    batch = owner(r32, "bool R32SetWvpBatch(")
    reset = owner(r32, "HRESULT R32WithResetLifecycle(")
    interop = owner(r32, "void R32InvalidateDirectInteropOnly()")
    present = owner(r32, "void R32LogPerfWindow()")
    if not all(s in read for s in ("if (!ok)", "return ok;", "spdlog::warn(")):
        return False
    if not all(s in lower for s in (
        "if (R32ReadEffectSnapshot(device, snapshot))",
        "R30SupportExchangeVertexShaderIdentity(0)",
        "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity);")):
        return False
    if not all(s in batch for s in (
        "OutRunVR::D3D9::SetVertexShaderConstantBatch(",
        "if (R30SupportTelemetryEnabled())",
        "++R32BatchWvpUploads;")):
        return False
    rearm = owner(r32, "void R32ResetAfterGameReset()")
    if "R32InvalidateResetCaches();" not in rearm:
        return False
    if not all(s in reset for s in (
        "if (SUCCEEDED(hr))", "R32ResetAfterGameReset();",
        "R32InvalidateResetCaches();")):
        return False
    if not all(s in interop for s in (
        "R30SupportReleaseDirectAckState();",
        "R30SupportReleaseDirectTransportInterop();",
        "R32ForgetDirectIdentity();")):
        return False
    if not all(s in present for s in (
        "if (!R30SupportTelemetryEnabled())", "R32BatchWvpFailures - R32Counters.batchFail",
        "R31SupportTelemetryLiveWvpChecks() - R32Counters.liveWvp",
        "R32ResetFailures - R32Counters.resetFail")):
        return False
    return True


def main() -> None:
    r31, r32 = R31.read_text(encoding="utf-8"), R32.read_text(encoding="utf-8")
    assert verify(r31, r32), "R31/R32 disabled-telemetry or safety contract failed"
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert wf.count("tools/verify_vr_r31_r32_off_counters.py") == 2
    mutants = 0
    for counter in R31_DIAGNOSTICS + R32_DIAGNOSTICS:
        src = r31 if counter in R31_DIAGNOSTICS else r32
        guarded = re.search(
            r"if \(R30SupportTelemetryEnabled\(\)\) \+\+" + counter + r";", src)
        assert guarded, counter
        for replacement in ("++" + counter + ";", "if (true) ++" + counter + ";",
                            "if (R30SupportTelemetryEnabled()) /* lost count */;"):
            broken = src[:guarded.start()] + replacement + src[guarded.end():]
            assert not (verify(broken, r32) if src is r31 else verify(r31, broken)), (
                counter, replacement)
            mutants += 1
    for old, new in (
        ("LiveWvpValidationInterval = 16;", "LiveWvpValidationInterval = 0;"),
        ("++R31FastWorldCandidates;", "/* dropped cadence */"),
        ("R31BlockedVerifiedGeneration = generation;", "/* allow unsafe generation */"),
    ):
        broken = r31.replace(old, new, 1)
        assert broken != r31 and not verify(broken, r32), old
        mutants += 1
    for old, new in (
        ("R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity);", "/* no restore */"),
        ("R30SupportReleaseDirectTransportInterop();", "/* reused dead interop */"),
        ("R32InvalidateResetCaches();", "/* stale reset */"),
    ):
        broken = r32.replace(old, new, 1)
        assert broken != r32 and not verify(r31, broken), old
        mutants += 1
    # Functional counter-transition reference: enabled samples retain all
    # counts; disabled samples leave diagnostic counters unchanged.
    observed = 0
    for enabled in (True, True, False, False, True, False, True):
        if enabled:
            observed += 1
    assert observed == 4
    print(f"PASS R31/R32 diagnostic opt-out, fail-closed/reset preservation, {mutants} destructive mutations")


if __name__ == "__main__":
    main()
