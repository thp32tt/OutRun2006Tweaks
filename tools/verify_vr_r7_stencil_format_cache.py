#!/usr/bin/env python3
"""R7 tracked-depth stencil-format GetDesc cache with lifecycle negative tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"


def verify(source: str) -> None:
    assert "bool TrackedStencilFormatKnown = false;" in source
    assert "bool TrackedStencilFormatHasStencil = false;" in source
    fn = source.split("bool SurfaceHasStencil(IDirect3DSurface9* surface)\n", 1)[1]
    fn = fn.split("\n\t\tbool DepthTestActive(", 1)[0]
    required = (
        "if (!surface) return false;",
        "if (surface == TrackedDepthStencil && TrackedStencilFormatKnown)",
        "return TrackedStencilFormatHasStencil;",
        "if (FAILED(surface->GetDesc(&desc))) return false;",
        "const bool hasStencil = FormatHasStencil(desc.Format);",
        "if (surface == TrackedDepthStencil)",
        "TrackedStencilFormatHasStencil = hasStencil;",
        "TrackedStencilFormatKnown = true;",
        "return hasStencil;",
    )
    for part in required:
        assert part in fn, part
    assert fn.index(required[1]) < fn.index(required[3]) < fn.index(required[6])
    assert fn.index(required[6]) < fn.index(required[7]) < fn.index(required[8])
    assert fn.index(required[3]) < fn.index(required[8])
    reset = source.split("void ReleaseStereoResources()\n", 1)[1]
    reset = reset.split("\n\t\tbool CreateRightDepthForTracked(", 1)[0]
    assert reset.index("TrackedStencilFormatKnown = false;") < reset.index(
        "ReleaseCom(TrackedDepthStencil)")
    binding = source.split("HRESULT __stdcall SetDepthStencilSurfaceDest(", 1)[1]
    binding = binding.split("\n\t\tHRESULT __stdcall QueryIssueDest(", 1)[0]
    assert "const bool changed=TrackedDepthStencil!=surface;" in binding
    assert "if(changed) TrackedStencilFormatKnown=false;" in binding
    assert binding.index("if(changed) TrackedStencilFormatKnown=false;") < binding.index(
        "ReplaceSurfaceRef(TrackedDepthStencil,surface);")



def verify_device_facts(source: str) -> None:
    """Device-scoped COM cache must retain live host LUID and XR sizing checks."""
    def scope(start: str, end: str) -> str:
        return source.split(start, 1)[1].split(end, 1)[0]

    struct = scope("struct DirectTransportDeviceFacts", "D3DSURFACE_DESC BackBufferDesc")
    for token in ("IDirect3DDevice9* device = nullptr;", "LUID gameAdapterLuid{};",
                  "UINT maxTextureWidth = 0;", "UINT maxTextureHeight = 0;",
                  "bool adapterLuidKnown = false;", "bool textureLimitsKnown = false;",
                  "DirectTransportDeviceFacts DirectTransportFacts{};"):
        assert token in struct, token
    binder = scope("void BindDirectTransportFacts(", "D3DSURFACE_DESC BackBufferDesc")
    assert "if (DirectTransportFacts.device != device)" in binder
    assert "DirectTransportFacts = {};" in binder
    assert "DirectTransportFacts.device = device;" in binder
    query = scope("bool QueryGameAdapterLuid(", "bool EnsureDirectInteropProbe(")
    for token in ("if (!device) return false;", "BindDirectTransportFacts(device);",
                  "if (DirectTransportFacts.adapterLuidKnown)",
                  "luid = DirectTransportFacts.gameAdapterLuid;",
                  "device->QueryInterface(__uuidof(IDirect3DDevice9Ex)",
                  "d3dEx->GetAdapterLUID(cp.AdapterOrdinal, &luid)",
                  "ReleaseCom(d3dEx);", "ReleaseCom(base);", "ReleaseCom(deviceEx);",
                  "if (ok)", "DirectTransportFacts.gameAdapterLuid = luid;",
                  "DirectTransportFacts.adapterLuidKnown = true;"):
        assert token in query, token
    assert query.index("BindDirectTransportFacts(device);") < query.index(
        "if (DirectTransportFacts.adapterLuidKnown)") < query.index("device->QueryInterface")
    assert query.index("ReleaseCom(deviceEx);") < query.index(
        "if (ok)") < query.index("DirectTransportFacts.adapterLuidKnown = true;")
    probe = scope("bool EnsureDirectInteropProbe(", "void ReleaseDirectTransportSlots()")
    assert "QueryGameAdapterLuid(device,gameLuid)" in probe
    assert "SharedState->hostAdapterLuidLow==gameLuid.LowPart" in probe
    assert "SharedState->hostAdapterLuidHigh==static_cast<std::uint32_t>(gameLuid.HighPart)" in probe
    assert "SharedState->hostInteropProbeAckToken==DirectInteropProbeToken" in probe
    size = scope("bool DirectTransportTargetSize(", "HRESULT StretchDirectEye(")
    for token in ("SharedState->sequence", "SharedState->recommendedWidth[0]",
                  "SharedState->recommendedHeight[1]", "if (w0 != w1 || h0 != h1) return false;",
                  "BindDirectTransportFacts(device);", "if (!DirectTransportFacts.textureLimitsKnown)",
                  "if (FAILED(device->GetDeviceCaps(&caps))) return false;",
                  "DirectTransportFacts.maxTextureWidth = caps.MaxTextureWidth;",
                  "DirectTransportFacts.maxTextureHeight = caps.MaxTextureHeight;",
                  "DirectTransportFacts.textureLimitsKnown = true;",
                  "published, {DirectTransportFacts.maxTextureWidth,",
                  "DirectTransportFacts.maxTextureHeight});"):
        assert token in size, token
    assert size.index("BindDirectTransportFacts(device);") < size.index(
        "if (!DirectTransportFacts.textureLimitsKnown)") < size.index(
        "device->GetDeviceCaps(&caps)")
    assert size.index("if (FAILED(device->GetDeviceCaps(&caps))) return false;") < size.index(
        "DirectTransportFacts.textureLimitsKnown = true;")
    release = scope("void ReleaseStereoResources()", "bool CreateRightDepthForTracked(")
    assert "DirectTransportFacts = {};" in release
    assert release.index("DirectTransportFacts = {};") < release.index(
        "ReleaseDirectInteropProbe();")
    assert "RetireDirectTransportFramePublications();" in release
    assert "ReleaseDirectTransportSlotObjects();" in release
    reset = scope("HRESULT __stdcall ResetDest(", "constexpr std::uint32_t StereoInstallPending")
    assert "ReleaseStereoResources();" in reset


def verify_device_facts_mutations(source: str) -> None:
    mutations = (
        ("if (DirectTransportFacts.device != device)", "if (false)"),
        ("DirectTransportFacts.device = device;", "DirectTransportFacts.device = nullptr;"),
        ("if (DirectTransportFacts.adapterLuidKnown)", "if (true)"),
        ("luid = DirectTransportFacts.gameAdapterLuid;", "luid = {};"),
        ("d3dEx->GetAdapterLUID(cp.AdapterOrdinal, &luid)", "D3D_OK"),
        ("DirectTransportFacts.gameAdapterLuid = luid;", "DirectTransportFacts.gameAdapterLuid = {};"),
        ("DirectTransportFacts.adapterLuidKnown = true;", "DirectTransportFacts.adapterLuidKnown = false;"),
        ("if (!DirectTransportFacts.textureLimitsKnown)", "if (true)"),
        ("if (FAILED(device->GetDeviceCaps(&caps))) return false;", "if (false) return false;"),
        ("DirectTransportFacts.maxTextureWidth = caps.MaxTextureWidth;", "DirectTransportFacts.maxTextureWidth = 0;"),
        ("DirectTransportFacts.maxTextureHeight = caps.MaxTextureHeight;", "DirectTransportFacts.maxTextureHeight = 0;"),
        ("DirectTransportFacts.textureLimitsKnown = true;", "DirectTransportFacts.textureLimitsKnown = false;"),
        ("// Reset/ResetEx may reuse a COM address for another device.\n            DirectTransportFacts = {};",
         "// Reset invalidation removed"),
    )
    for old, replacement in mutations:
        assert old in source, f"missing fixture: {old}"
        bad = source.replace(old, replacement, 1)
        try:
            verify_device_facts(bad)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"mutation was not rejected: {old}")
    print(f"PASS DirectGPU device-facts per-Present cache: {len(mutations)} negative mutations")

if __name__ == "__main__":
    source = SRC.read_text(encoding="utf-8")
    verify(source)
    verify_device_facts(source)
    verify_device_facts_mutations(source)
    mutations = (
        ("bool TrackedStencilFormatKnown = false;", "bool TrackedStencilFormatKnown = true;"),
        ("bool TrackedStencilFormatHasStencil = false;", "bool TrackedStencilFormatHasStencil = true;"),
        ("if (!surface) return false;", "if (!surface) return true;"),
        ("if (surface == TrackedDepthStencil && TrackedStencilFormatKnown)", "if (TrackedStencilFormatKnown)"),
        ("return TrackedStencilFormatHasStencil;", "return true;"),
        ("if (FAILED(surface->GetDesc(&desc))) return false;", "if (true) return false;"),
        ("const bool hasStencil = FormatHasStencil(desc.Format);", "const bool hasStencil = true;"),
        ("if (surface == TrackedDepthStencil)", "if (surface != TrackedDepthStencil)"),
        ("TrackedStencilFormatHasStencil = hasStencil;", "TrackedStencilFormatHasStencil = false;"),
        ("TrackedStencilFormatKnown = true;", "TrackedStencilFormatKnown = false;"),
        ("// A Reset can recycle a COM address for a different depth format.\n\t\t\tTrackedStencilFormatKnown = false;",
         "// Reset cache invalidation deliberately deleted."),
        ("if(changed) TrackedStencilFormatKnown=false;", "if(changed) (void)0;"),
    )
    count = 0
    for old, new in mutations:
        assert old in source, "missing negative fixture: " + old
        broken = source.replace(old, new, 1)
        try:
            verify(broken)
        except (AssertionError, IndexError, ValueError):
            count += 1
        else:
            raise AssertionError("mutation survived: " + old)
    assert count == len(mutations)
    print(f"PASS DX9Ex R7 stencil GetDesc hot path: {count} negative mutations")
