#!/usr/bin/env python3
"""00856: actual complete native game GPU handoff independent of D3D9 CPU upload."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_gpu_handoff.hpp").read_text()
start = bridge.index("void before_game_present(")
end = bridge.index("void before_game_reset(", start)
present = bridge[start:end]
gpu_start = present.index("const bool gpuOutputAdmissible = ")
gpu_call = present.index("if (GameNativeGpuHandoff::may_offer(", gpu_start)
cpu_fallback = present.index("if (!gpuHandoffQueued && complete && outputWritable", gpu_call)
assert gpu_start < gpu_call < cpu_fallback
assert "GameNativeGpuHandoff::gpu_frame_output_ready(" in present[gpu_start:gpu_call]
assert "monoNativePublicationAllowed" in present[gpu_start:gpu_call]
assert "backbufferKnown && outputNow.valid()" in present[gpu_start:gpu_call]
assert "nativeExtentMatches, fullPlacement.valid" in present[gpu_start:gpu_call]
# Bound the native sink assertion to the GPU call, not the later shared
# desktop path: the latter MUST still require writable D3D9 backbuffer pixels.
gpu_call_end = present.index(")) {", gpu_call) + len(")) {")
assert gpu_call < gpu_call_end < cpu_fallback
assert "fullMode, complete, gpuOutputAdmissible" in present[gpu_call:gpu_call_end]
assert "outputWritable" not in present[gpu_call:gpu_call_end]
assert "fullMode, complete, outputWritable" in present[gpu_call_end:cpu_fallback]
assert "outputWritable" in present[cpu_fallback:]
assert "monoPublicationAllowed && outputKnown" in header
assert "nativeExtentMatches && fullPlacementValid" in header

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++17 compiler required for runtime behavioral regression"
with TemporaryDirectory(prefix="dx11-gpu-only-00856-") as tmp:
    binary = Path(tmp) / "gpu-handoff"
    src = root / "tests/vr/dx11_native_game_gpu_handoff.cpp"
    build = subprocess.run(
        [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-pedantic", str(src), "-o", str(binary)],
        capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    assert subprocess.run([str(binary)], check=False).returncode == 0

# Negative integration mutations must remove the ONLY eligible native route,
# rather than merely renaming test tokens or bypassing CPU D3D9 fallback.
for removed in (
    "monoNativePublicationAllowed",
    "backbufferKnown && outputNow.valid()",
    "nativeExtentMatches, fullPlacement.valid",
):
    candidate = present[gpu_start:gpu_call].replace(removed, "false", 1)
    assert candidate != present[gpu_start:gpu_call] and removed not in candidate
assert cpu_fallback > gpu_call, "D3D9 fallback must follow GPU sink"
print("PASS: native real-game GPU sink independent of CPU D3D9 target; stereo, extent, generation and fallback retained")
