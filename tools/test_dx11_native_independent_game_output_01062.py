#!/usr/bin/env python3
"""01062 GPU-only game-frame resolution decoupling source-link regressions."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
gpu = (root / "src/vr/d3d11/native_game_gpu_handoff.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(b, h):
    try:
        segment = b.split("// Authenticate the producer's actual GPU resource", 1)[1].split(
            "// Optional real GPU-only desktop presentation", 1)[0]
        native = h.split("independent_gpu_frame_ready(", 1)[1].split(
            "// Disallow partial game Draw coverage", 1)[0]
    except IndexError:
        return False
    return all((
        "nativeColorOwner.Get() == s.backend.device()" in segment,
        "DXGI_FORMAT_B8G8R8A8_TYPELESS" in segment,
        "nativeColorDesc.SampleDesc.Count == 1u" in segment,
        "nativeColorDesc.MipLevels == 1u" in segment,
        "independent_gpu_frame_ready(" in segment,
        "bb.Width, bb.Height, surfaceWidth, surfaceHeight" in segment,
        "nativeColorDesc.Width, nativeColorDesc.Height" in segment,
        "nativeWidth == textureWidth" in native,
        "nativeHeight == textureHeight" in native,
        "monoPublicationAllowed && gameOutputKnown" in native,
        "const bool outputWritable = monoNativePublicationAllowed &&" in b,
        "nativeExtentMatches &&" in b,
        "nativeGpuDesktopPublished = s.sharedDesktop.try_present(" in b,
        "if (!gpuHandoffQueued && sharedDesktopAllowed &&" in b,
    ))
assert integrated(bridge, gpu)
for needle in ("nativeColorOwner.Get() == s.backend.device()",
               "DXGI_FORMAT_B8G8R8A8_TYPELESS",
               "nativeColorDesc.SampleDesc.Count == 1u",
               "independent_gpu_frame_ready(",
               "bb.Width, bb.Height, surfaceWidth, surfaceHeight",
               "nativeColorDesc.Width, nativeColorDesc.Height"):
    # Repeated geometry arguments can occur in other D3D9/CPU branches.
    # Mutate ONLY the actual GPU-sink producer handoff under test.
    prefix, block_and_after = bridge.split(
        "// Authenticate the producer's actual GPU resource", 1)
    block, suffix = block_and_after.split(
        "// Optional real GPU-only desktop presentation", 1)
    assert needle in block, needle
    broken = (prefix + "// Authenticate the producer's actual GPU resource" +
              block.replace(needle, "/* detached native GPU source */", 1) +
              "// Optional real GPU-only desktop presentation" + suffix)
    assert broken != bridge and not integrated(broken, gpu), needle
for needle in ("nativeWidth == textureWidth",
               "nativeHeight == textureHeight",
               "monoPublicationAllowed && gameOutputKnown"):
    broken = gpu.replace(needle, "false /* detached geometry */", 1)
    assert broken != gpu and not integrated(bridge, broken), needle
assert "tests/vr/dx11_native_independent_game_output_01062.cpp" in workflow
assert "python tools/test_dx11_native_independent_game_output_01062.py" in workflow
print("PASS 01062 independent native GPU sink dimensions with original D3D9 fallback")
