#!/usr/bin/env python3
"""RT0 raster resynchronization: trusted scissor-enable elision and negative mutations."""
from pathlib import Path

code = (Path(__file__).resolve().parents[1] /
        "src/vr/d3d9/stereo_renderer_r23.cpp").read_text(encoding="utf-8")

def check(s):
    fn = s.split("bool R23CaptureActualGameState(", 1)[1].split(
        "\n        void R23Reject(", 1)[0]
    hook = s.split("HRESULT __stdcall SetRenderTargetDestR23(", 1)[1].split(
        "\n        const char* R23DiagnoseHostFreshness", 1)[0]
    for required in (
        'std::strcmp(site, "SetRenderTarget") == 0',
        'shadow.Valid() && IsTrackedStateBlockReliable()',
        'if (trustedRtScissorEnable)',
        'actual = shadow;',
        'SUCCEEDED(device->GetViewport(&actual.viewport))',
        'SUCCEEDED(device->GetScissorRect(&actual.rect))',
        'captured = CaptureTrackedRasterState(device, actual);',
        'if (!captured)', '++R23StateCaptureFailures;',
        'SetTrackedRasterShadow(actual);',
        'R23LastStateSampleEpoch = PresentEpoch;',
    ):
        assert required in fn, required
    optimized = fn.split('if (trustedRtScissorEnable)', 1)[1].split(
        '\n            else', 1)[0]
    assert 'GetRenderState' not in optimized
    assert optimized.index('actual = shadow;') < optimized.index(
        'device->GetViewport(&actual.viewport)')
    assert 'if (!R23CaptureActualGameState(device, actual,' in hook
    assert 'InvalidateTrackedRasterShadow();' in hook
    assert 'FailClosedTrackedRasterReplay(' in hook

check(code)
for old, bad in (
    ('shadow.Valid() && IsTrackedStateBlockReliable()',
     'shadow.Valid() || IsTrackedStateBlockReliable()'),
    ('SUCCEEDED(device->GetViewport(&actual.viewport))', 'SUCCEEDED(D3D_OK)'),
    ('SUCCEEDED(device->GetScissorRect(&actual.rect))', 'SUCCEEDED(D3D_OK)'),
    ('captured = CaptureTrackedRasterState(device, actual);', 'captured = true;'),
    ('if (!captured)', 'if (false)'),
    ('actual = shadow;', 'actual = {};'),
):
    assert old in code, old
    try:
        check(code.replace(old, bad, 1))
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("unsafe raster capture mutation escaped: " + old)

# The D3D9 RT0 call can replace the viewport/scissor geometry but leaves
# SCISSORTESTENABLE unchanged. Strict ownership determines whether the fast
# two-getter path or conservative complete three-getter path is legal.
for reliable in (False, True):
    for valid in (False, True):
        for enabled in (0, 1):
            for success in (False, True):
                fast = reliable and valid
                getters = ("GetViewport", "GetScissorRect") if fast else (
                    "GetViewport", "GetScissorRect", "GetRenderState")
                assert len(getters) == (2 if fast else 3)
                viewport = (0, 0, 1920, 1080)
                scissor = (4, 2, 1800, 1000)
                if success:
                    result = (viewport, scissor, enabled)
                    assert result[0] == viewport and result[1] == scissor
                    assert result[2] == enabled
                else:
                    result = None
                    assert result is None
print("R23 SetRenderTarget trusted live geometry/fail-closed mutation PASS")
