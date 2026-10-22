#!/usr/bin/env python3
"""Structural negative regression: live-game shared GPU copy and fallback.

D3D11 Windows build and game/Quest 3 runtime checks are separate.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
code = (root / "src/vr/d3d11/native_game_shared_desktop.hpp").read_text(encoding="utf-8")
helpers = (root / "src/vr/d3d11/native_game_gpu_output_preserve.hpp").read_text(encoding="utf-8")

def correct(s):
    start = s.find("class NativeSharedDesktopBridge final")
    end = s.find("private:", start)
    if min(start, end) < 0:
        return False
    part = s[start:end]
    tokens = (
        "ScopedNativeGameGpuTransferInputs shaderInputs(context, source_.Get());",
        "ScopedNativeGameGpuTransferOutputs scopedOutputs(context);",
        "context->CopyResource(source_.Get(), readySource);",
        "context->End(fence_.Get());",
        "context->Flush();",
        "if (status == S_FALSE) return false;",
        "pending_ = false;",
        "if (FAILED(device->GetDeviceRemovedReason())) {",
        "Microsoft::WRL::ComPtr<IDirect3DSurface9> sharedSurface;",
        "if (FAILED(game->StretchRect("
    )
    positions = [part.find(x) for x in tokens]
    return (all(p >= 0 for p in positions) and positions == sorted(positions)
        and "faulted_ = true;\n            return false;\n        }\n"
            "        Microsoft::WRL::ComPtr<IDirect3DSurface9> sharedSurface;" in part
        and all(s in helpers for s in (
            "VSGetShaderResources", "PSGetShaderResources", "GSGetShaderResources",
            "HSGetShaderResources", "DSGetShaderResources", "CSGetShaderResources",
            "resource == destination_", "set(stage, slot, &empty);",
            "set(entry.stage, entry.slot, &entry.view);")))

assert correct(code)
for token in (
    "ScopedNativeGameGpuTransferInputs shaderInputs(context, source_.Get());",
    "ScopedNativeGameGpuTransferOutputs scopedOutputs(context);",
    "if (FAILED(device->GetDeviceRemovedReason())) {",
):
    assert not correct(code.replace(token, "/* removed step */", 1)), token
print("PASS native desktop shader resource transfer and removed-device fallback")
