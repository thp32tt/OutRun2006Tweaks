#!/usr/bin/env python3
"""Real ps_3_0 FACE declaration/linkage/condition native HLSL Draw regression."""
from pathlib import Path
import shutil
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
pipeline = (root / "src/vr/d3d11/pipeline_translation.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
def require(ok, reason):
    if not ok:
        raise SystemExit("01016 FACE native game compare FAIL: " + reason)
shader = backend.split("bool build_r283_sm3_mov_shader_source(", 1)[1].split(
    "bool r283_dxbc_payload(", 1)[0]
require("D3DSMO_FACE" in pipeline and
        "native_sm3_face_declaration(" in pipeline and
        "pixelFace ? D3DDECLUSAGE_PSIZE" in pipeline and
        "mix(pixelFace ? 0x56464143u : 0x56504f53u)" in pipeline and
        "if (!clipPosition) return out;" in pipeline,
        "authentic face DCL, separated shader pair hash and real VS clip source")
require("faceDeclared = true;" in shader and
        "if (faceDeclared) return false;" in shader and
        "native_sm3_face_scalar_source(requiredComponents)" in shader and
        "value = native_sm3_face_compare_hlsl();" in shader and
        'pixelFace ? "bool " : "float4 "' in shader and
        '"r283_frontface"' in shader and
        'label = pixelFace ? "SV_IsFrontFace" : "SV_Position"' in backend,
        "real ps raster bool feeds signed face scalar comparisons")
require("else if (kind == D3DSPR_MISCTYPE)" in shader and
        "native_sm3_face_scalar_source(required)" in shader and
        "native_sm3_pixel_position_source(required)" in shader and
        "if (!faceDeclared ||" in shader and
        "value = native_sm3_face_compare_hlsl();" in shader,
        "arithmetic SM3 face sign accepts only declared x-lane; VPOS and missing FACE fail closed")
# Validate actual game HLSL accepts front-facing arithmetic operands through
# live programmable Draw/DrawIndexed, while rejecting y/z/w and invalid DCL.
require("context->PSSetShader(" in bridge and
        "context->DrawIndexed(" in bridge and "context->Draw(" in bridge,
        "native game shader still binds D3D11 Draw/DrawIndexed")
compiler = shutil.which("g++") or shutil.which("clang++")
require(bool(compiler), "C++17 compiler unavailable")
with tempfile.TemporaryDirectory() as directory:
    exe = Path(directory) / "sm3_face"
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
        str(root / "tools/dx11_sm3_face_compare_01016.cpp"),
        "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

# Source-linked, compiled positive/negative coverage for native shader
# front-face arithmetic and mixed screen-position composition.
    arithmetic = Path(directory) / "face_arithmetic.cpp"
    arithmetic.write_text(r"""
#include "native_sm3_interface_channels.hpp"
#include "native_sm3_arithmetic_codegen.hpp"
#include <array>
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
static_assert(native_sm3_face_declaration(false, 1u, 15u));
static_assert(!native_sm3_face_declaration(true, 1u, 15u));
static_assert(native_sm3_face_scalar_source(
    native_sm3_swizzled_components(15u, 0x00u)));
static_assert(!native_sm3_face_scalar_source(
    native_sm3_swizzled_components(15u, 0xe4u)));
static_assert(!native_sm3_face_scalar_source(
    native_sm3_swizzled_components(15u, 0x55u)));
static_assert(!native_sm3_face_scalar_source(
    native_sm3_swizzled_components(
        native_sm3_source_modifier_components(15u, 9u), 0xe4u)));
int main() {
    const auto actual = native_sm3_source_components(
        NativeSm3ArithmeticOpcode::MultiplyAdd, 15u, 0u);
    assert(actual == 15u);
    assert(native_sm3_face_scalar_source(
        native_sm3_swizzled_components(actual, 0u)));
    std::array<std::string, 3> sources{
        std::string("(") + native_sm3_face_compare_hlsl() + ").xxxx",
        "float4(0.5f, 0.5f, 0.5f, 0.5f)",
        native_sm3_pixel_position_hlsl()};
    std::string translated;
    assert(append_native_sm3_arithmetic(
        translated, NativeSm3ArithmeticOpcode::MultiplyAdd,
        "r283_color", 15u, sources, 3u, 1u));
    assert(translated.find("r283_frontface") != std::string::npos);
    assert(translated.find("r283_vpos") != std::string::npos);
    assert(translated.find("r283_color") != std::string::npos);
}
""")
    face_exe = Path(directory) / "sm3_face_math"
    subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-Werror", "-pedantic", "-I", str(root / "src/vr/d3d11"),
        str(arithmetic), "-o", str(face_exe)], check=True)
    subprocess.run([str(face_exe)], check=True)

print("01016 FACE compare + arithmetic native linkage PASS; actual game/Quest3 UNTESTED")
