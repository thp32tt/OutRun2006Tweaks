#!/usr/bin/env python3
"""01061: real game mip-zero BGRA GPU frame -> shared D3D9Ex desktop crop.

Source-link negative regression only. Windows compile, device execution and
Quest3/OpenXR runtime are separate evidence layers.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/native_game_shared_desktop.hpp").read_text(encoding="utf-8")
selector = (root / "src/vr/d3d11/native_game_shared_desktop_source.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(src, header):
    try:
        admit = src.split("D3D11_TEXTURE2D_DESC desc{};", 1)[1].split(
            "// Confirm the real game destination", 1)[0]
        copy = src.split("const bool entire = regionCount == 1u", 1)[1].split(
            "context->End(fence_.Get());", 1)[0]
        fmt = copy.split("const bool exactWholeCopy", 1)[1].split(
            "context->CopySubresourceRegion(", 1)[0]
    except IndexError:
        return False
    checks = (
        "desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB" in admit,
        "desc.Format == DXGI_FORMAT_B8G8R8A8_TYPELESS" in admit,
        "desc.SampleDesc.Count == 1u" in admit,
        "!compatibleColor" in admit,
        "desc.MipLevels, desc.ArraySize" in admit,
        "source->GetDevice(sourceOwner.GetAddressOf())" in admit,
        "cached.Format != desc.Format" in copy,
        "resolvedSource_.Reset();" in copy,
        "desc.MipLevels == 1u" in fmt,
        "desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM" in fmt,
        "if (exactWholeCopy)" in fmt,
        "context->CopyResource(source_.Get(), readySource);" in fmt,
        "const RECT tile = entire" in fmt,
        "static_cast<LONG>(width), static_cast<LONG>(height)" in fmt,
        "context->CopySubresourceRegion(" in copy,
        "source_.Get(), 0u, region.left, region.top, 0u," in copy,
        "readySource, 0u, &region" in copy,
        "mipLevels == 0u || arraySize != 1u" in header,
        "mipLevels == 1u && renderTarget && formatSupportsResolve" in header,
    )
    return all(checks)

assert integrated(bridge, selector)
for needle in (
    "desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",
    "desc.Format == DXGI_FORMAT_B8G8R8A8_TYPELESS",
    "cached.Format != desc.Format",
    "if (exactWholeCopy)",
    "const RECT tile = entire",
    "context->CopySubresourceRegion(",
):
    mutated = bridge.replace(needle, "/* 01061 detached */", 1)
    assert mutated != bridge and not integrated(mutated, selector), needle
for needle in (
    "mipLevels == 0u || arraySize != 1u",
    "mipLevels == 1u && renderTarget && formatSupportsResolve",
):
    mutated = selector.replace(needle, "false /* unproved source layout */", 1)
    assert mutated != selector and not integrated(bridge, mutated), needle
assert "python tools/test_dx11_shared_desktop_source_layout_01061.py" in workflow
assert "tools/dx11_shared_desktop_source_layout_01061.cpp" in workflow
print("PASS 01061 real BGRA mip-zero camera source -> fenced GPU desktop/region handoff")
