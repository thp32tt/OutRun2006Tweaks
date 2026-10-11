#!/usr/bin/env python3
"""R32 fallback draw cache gate and fail-closed negative-mutation tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
OWNER = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"


def body(text, signature):
    start = text.index(signature)
    begin = text.index("{", start)
    depth = 0
    for pos in range(begin, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[begin:pos + 1]
    raise ValueError("unclosed source function")


def valid(source, owner):
    try:
        hot = body(source, "HRESULT R32LowerFailClosed(")
        cached = body(owner, "bool R29EffectCacheCurrent()")
        oracle = body(owner, "bool TryGetEffectTelemetrySnapshot(")
        steps = (
            "OutRunVR::State::StateBlockTracker::Reliable() &&",
            "R30SupportTryGetEffectTelemetrySnapshot(shadow)",
            "return lowerDraw();",
            "R32ReadEffectSnapshot(device, snapshot)",
            "return lowerDraw();",
            "R30SupportExchangeVertexShaderIdentity(0)",
            "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity)",
        )
        index = -1
        for step in steps:
            index = hot.index(step, index + 1)
        return (
            "R30SupportIsGameDevice(device)" in hot
            and "R32FailClosedZeroDisparityDraws" in hot
            and "if (!R29EffectCacheCurrent())" in oracle
            and all(x in cached for x in (
                "StateBlockTracker::Reliable()",
                "StateBlockTracker::ApplyGeneration()",
                "PresentEpoch",
                "TopLevelDrawSerial()",
            ))
        )
    except (ValueError, IndexError):
        return False


def model(reliable, cached, live):
    if reliable and cached:
        return "lower", 0
    return ("lower" if live else "zero-disparity"), 1


def main():
    source = SOURCE.read_text(encoding="utf-8")
    owner = OWNER.read_text(encoding="utf-8")
    assert valid(source, owner), "R32 cached-effect fallback boundary changed"
    for reliable in (False, True):
        for cached in (False, True):
            for live in (False, True):
                result, reads = model(reliable, cached, live)
                assert (reads == 0) == (reliable and cached)
                assert result == ("zero-disparity" if
                    not (reliable and cached) and not live else "lower")

    mutants = [
        ("unreliable", source.replace(
            "OutRunVR::State::StateBlockTracker::Reliable() &&\n"
            "                R30SupportTryGetEffectTelemetrySnapshot(shadow)",
            "R30SupportTryGetEffectTelemetrySnapshot(shadow)")),
        ("shadow", source.replace(
            "R30SupportTryGetEffectTelemetrySnapshot(shadow)", "false")),
        ("live", source.replace(
            "R32ReadEffectSnapshot(device, snapshot)", "true")),
        ("zero", source.replace(
            "R30SupportExchangeVertexShaderIdentity(0)", "0")),
    ]
    for name, mutant in mutants:
        assert mutant != source and not valid(mutant, owner), name
    corrupt_owner = owner.replace("if (!R29EffectCacheCurrent())", "if (false)")
    assert corrupt_owner != owner and not valid(source, corrupt_owner)
    print("PASS R32 shadow fallback: 8 model cases, 5 negative mutations")


if __name__ == "__main__":
    main()
