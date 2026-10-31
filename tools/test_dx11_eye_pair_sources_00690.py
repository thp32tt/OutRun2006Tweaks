#!/usr/bin/env python3
"""DX11 live stereo source identity and immutable shared-ring output regression."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
source = (ROOT / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text(encoding="utf-8")
probe = ROOT / "tools/dx11_game_eye_pair_sources_probe_00690.cpp"
# Do not accept an isolated helper that is never used by the live native eye pair.
required = [
    '#include "native_game_eye_pair_sources.hpp"',
    "source->QueryInterface(",
    "for (std::size_t n = 0; n < slots_.size(); ++n)",
    "native_game_eye_local_render_target_admitted(",
    "D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX",
    "D3D11_RESOURCE_MISC_SHARED_NTHANDLE",
    "native_game_eye_pair_sources_admitted(",
    "context->CopyResource(entry.eye[0].Get(), left_source);",
    "context->CopyResource(entry.eye[1].Get(), right_source);",
]
for marker in required:
    assert marker in source, f"producer source link lost: {marker}"
assert source.index("native_game_eye_local_render_target_admitted(") < source.index(
    "context->CopyResource(entry.eye[0].Get(), left_source);"
), "shared or non-render-target source must fail before GPU copy"
assert source.index("native_game_eye_pair_sources_admitted(") < source.index(
    "context->CopyResource(entry.eye[0].Get(), left_source);"
), "unsafe GPU copy scheduled before canonical source ownership validation"
assert source.index("context->CopyResource(entry.eye[0].Get(), left_source);") < source.index(
    "context->CopyResource(entry.eye[1].Get(), right_source);"
), "left/right native eye order changed"
# Positive/negative compile-time cases cover independent eyes, same-resource
# aliases, any other ring slot, and partially initialized output allocations.
with tempfile.TemporaryDirectory(prefix="dx11_eye_00690_") as temp:
    executable = Path(temp) / "eye_pair_probe"
    subprocess.run(
        ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
         "-Werror", "-pedantic", str(probe), "-o", str(executable)],
        check=True,
    )
    subprocess.run([str(executable)], check=True)
print("DX11 native stereo eye pair source lineage: PASS (portable/static, HMD UNTESTED)")
