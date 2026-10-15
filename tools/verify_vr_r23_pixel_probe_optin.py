#!/usr/bin/env python3
"""DX9Ex host: diagnostics cannot consume GPU work on normal production XR ticks."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "vrhost/src/main_r23.cpp"
METHODS = (
    "TryConsume(ID3D11DeviceContext* context)",
    "NoteFinalSubmission()",
    "ScheduleSource(StereoCompositor& c)",
    "ScheduleProjection(StereoCompositor& c, std::uint32_t image)",
    "ScheduleTheater(StereoCompositor& c, std::uint32_t image)",
)


def function(code: str, signature: str) -> str:
    start = code.index(signature)
    opened = code.index("{", start)
    level = 0
    for i in range(opened, len(code)):
        if code[i] == "{":
            level += 1
        elif code[i] == "}":
            level -= 1
            if level == 0:
                return code[opened:i + 1]
    raise ValueError("Unterminated C++ function " + signature)


def verify(code: str) -> None:
    policy = function(code, "bool R23PixelDiagnosticsEnabled() noexcept")
    assert 'std::getenv("OUTRUN_VR_R23_PIXEL_PROBE")' in policy
    assert "static const bool enabled" in policy, "no per-XR-tick getenv"
    assert "return value != nullptr &&" in policy, "must default off"
    for enabled_value in ('"1"', '"true"', '"TRUE"'):
        assert enabled_value in policy, "explicit opt-in lost " + enabled_value
    for signature in METHODS:
        body = function(code, "void " + signature)
        guard = "if (!R23PixelDiagnosticsEnabled()) return;"
        assert guard in body, "missing production GPU-work guard: " + signature
        assert body.index(guard) < min(
            (body.find(token) for token in (
                "ConsumeSource(context)", "ConsumeProjection(context)",
                "ConsumeTheater(context)", "GetTickCount64()",
                "LastSubmittedLayer.load(",
            ) if token in body),
            default=len(body)), "guard must precede GPU work: " + signature
    for required in (
        "R23Pixels.TryConsume(c.context_);",
        "R23Pixels.ScheduleSource(c);",
        "R23Pixels.ScheduleProjection(c, image);",
        "R23Pixels.ScheduleTheater(c, image);",
        "R23Pixels.NoteFinalSubmission();",
        "CopySubresourceRegion(sourceStage,",
        "CopySubresourceRegion(projectionStage,",
        "CopySubresourceRegion(theaterStage,",
    ):
        assert required in code, "opt-in functionality regressed: " + required


if __name__ == "__main__":
    code = SOURCE.read_text(encoding="utf-8")
    verify(code)
    mutants = (
        ('std::getenv("OUTRUN_VR_R23_PIXEL_PROBE")', 'std::getenv("OUTRUN_VR_UNUSED")'),
        ("static const bool enabled", "const bool enabled"),
        ("return value != nullptr &&", "return value == nullptr ||"),
        *(
            ("void " + method + "\n        {\n            if (!R23PixelDiagnosticsEnabled()) return;",
             "void " + method + "\n        {\n            /* missing performance guard */")
            for method in METHODS
        ),
    )
    for good, bad in mutants:
        assert good in code, "ineffective negative mutation: " + good
        try:
            verify(code.replace(good, bad, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("opt-in regression escaped: " + good)
    print(f"PASS DX9Ex host pixel diagnostic opt-in: zero default GPU/map probes, {len(mutants)} negative mutations")
