#!/usr/bin/env python3
"""R30 real C++ eye-affine cache regression; positive/negative mutations."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
source = SRC.read_text(encoding="utf-8")
start = source.index("        struct R30EyeAffineCache\n")
end = source.index("\n        struct R30XyzrhwState", start)
affine = source[start:end]


def verify_contract(code):
    for token in (
        "static thread_local R30EyeAffineCache cache{};",
        "cache.valid && cache.poseSequence == stereo.poseSequence",
        "cache.angleLeft[0] == stereo.eyeFov[0].angleLeft",
        "cache.angleRight[0] == stereo.eyeFov[0].angleRight",
        "cache.angleLeft[1] == stereo.eyeFov[1].angleLeft",
        "cache.angleRight[1] == stereo.eyeFov[1].angleRight",
        "cache.valid = false;",
        "cache.valid = true;",
        "std::isfinite(scale)",
        "std::isfinite(offset)",
    ):
        assert token in code, f"R30 affine cache contract missing: {token}"
    assert code.index("cache.valid = false;") < code.index("std::tan(")
    assert code.index("cache.valid = true;") > code.index("std::isfinite(offset)")
    assert source.count("R30BuildEyeAffine(state.stereo,") == 1
    assert source.count("R30BuildEyeAffine(stereo,") == 1


verify_contract(affine)
for destructive in (
    affine.replace("cache.valid = true;", "// cache.valid = disabled;"),
    affine.replace("cache.valid = false;", "// invalidation removed;"),
    affine.replace("cache.angleRight[1] == stereo.eyeFov[1].angleRight", "true"),
    affine.replace("cache.poseSequence == stereo.poseSequence", "true"),
):
    try:
        verify_contract(destructive)
    except AssertionError:
        pass
    else:
        raise AssertionError("R30 destructive cache mutation was not rejected")

# Compile the exact extracted C++ implementation, replacing tan with a
# counting wrapper solely in the harness to assert a miss costs 4 trig calls.
compiler = shutil.which("clang++") or shutil.which("g++")
if compiler:
    cxx = r"""
#include <cmath>
#include <cstdint>
#include <limits>
#include <cassert>
#include <algorithm>
namespace OutRunVRRenderer {
  struct EyeFov { float angleLeft, angleRight; };
  struct LatchedStereoFrame { uint32_t poseSequence; EyeFov eyeFov[2]; };
}
static unsigned tanCalls = 0;
float CountedTan(float v) { ++tanCalls; return std::tan(v); }
namespace {
__AFFINE__
}
static void check(const OutRunVRRenderer::LatchedStereoFrame& f) {
 float s[2]{}, o[2]{};
 assert(R30BuildEyeAffine(f, s, o));
 for(int eye=0;eye<2;++eye) {
   const float l0=std::tan(f.eyeFov[0].angleLeft);
   const float l1=std::tan(f.eyeFov[1].angleLeft);
   const float r0=std::tan(f.eyeFov[0].angleRight);
   const float r1=std::tan(f.eyeFov[1].angleRight);
   const float left=.5f*(l0+l1), right=.5f*(r0+r1);
   const float width=std::tan(f.eyeFov[eye].angleRight)-std::tan(f.eyeFov[eye].angleLeft);
   const float refScale=(right-left)/width;
   const float refOffset=(right+left-std::tan(f.eyeFov[eye].angleRight)-std::tan(f.eyeFov[eye].angleLeft))/width;
   assert(std::fabs(s[eye]-refScale)<1e-6f);
   assert(std::fabs(o[eye]-refOffset)<1e-6f);
 }
}
int main() {
 OutRunVRRenderer::LatchedStereoFrame f{33,{{-.85f,.80f},{-.82f,.83f}}};
 check(f); assert(tanCalls==4);
 for(int i=0;i<1000;++i)check(f); assert(tanCalls==4);
 f.eyeFov[1].angleRight=.84f;check(f);assert(tanCalls==8);
 f.poseSequence=34;check(f);assert(tanCalls==12);
 f.eyeFov[0].angleLeft=std::numeric_limits<float>::quiet_NaN();
 float s[2]{},o[2]{};
 assert(!R30BuildEyeAffine(f,s,o));assert(tanCalls==14);
 f.eyeFov[0].angleLeft=-.85f;check(f);assert(tanCalls==18);
 f.eyeFov[0].angleLeft=1.40f;f.eyeFov[0].angleRight=1.401f;
 assert(!R30BuildEyeAffine(f,s,o)); assert(tanCalls==20);
 f.eyeFov[0].angleLeft=-.85f;f.eyeFov[0].angleRight=.80f;
 check(f);assert(tanCalls==24);
 return 0;
}
""".replace("__AFFINE__", affine.replace("std::tan(", "CountedTan("))
    with tempfile.TemporaryDirectory() as td:
        unit = Path(td) / "r30_eye_cache.cpp"
        exe = Path(td) / "r30_eye_cache.exe"
        unit.write_text(cxx, encoding="utf-8")
        subprocess.run([compiler, "-std=c++17", "-O2", str(unit), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print("PASS: C++ eye-FOV cache hit/miss/nonfinite/invalid-width parity + negative mutations")
else:
    # The Win32 game CI still compiles the modified implementation.
    print("PASS: source/negative mutations (C++ fixture unavailable: compiler not in PATH)")
