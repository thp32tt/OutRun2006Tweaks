#include "live_game_sm3_user_clip.hpp"
#include <cassert>
#include <limits>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    std::array<std::array<float, 4>, 6> planes{};
    planes[0] = {{1.0f, 0.0f, 0.0f, -0.5f}};
    planes[5] = {{0.0f, -1.0f, 0.0f, 0.4f}};
    NativeSm3UserClip clip{};
    assert(native_sm3_user_clip_admission(0x21u, 6u, planes, clip));
    assert(clip.active && clip.constants[0] == 1.0f &&
           clip.constants[3] == -0.5f && clip.constants[23] == 0.4f);
    assert(clip.constants[24] == 1.0f && clip.constants[29] == 1.0f &&
           clip.constants[25] == 0.0f);
    assert(!native_sm3_user_clip_admission(0x20u, 5u, planes, clip));
    assert(!clip.active);
    planes[5][1] = std::numeric_limits<float>::quiet_NaN();
    assert(!native_sm3_user_clip_admission(0x20u, 6u, planes, clip));
    planes[5][1] = -1.0f;
    assert(native_sm3_user_clip_admission(0u, 0u, planes, clip) &&
           !clip.active);
    std::string vs =
        "struct R283Input { float4 r0 : POSITION0; };\n"
        "struct R283Output {\n"
        "    float4 r7 : SV_Position;\n"
        "    float4 r2 : TEXCOORD0;\n"
        "};\nR283Output main(R283Input input) {\n"
        "    R283Output output = (R283Output)0;\n"
        "    output.r7 = input.r0;\n"
        "    return output;\n}\n";
    assert(append_native_sm3_user_clip(vs, true));
    assert(vs.find("SV_ClipDistance0") != std::string::npos);
    assert(vs.find("SV_ClipDistance1") != std::string::npos);
    assert(vs.find("dot(output.r7, r283_clipPlanes[5])") != std::string::npos);
    assert(vs.find("register(b4)") != std::string::npos);
    assert(!append_native_sm3_user_clip(vs, true));
    std::string unsupported = "float4 main() : SV_Target0 {return 0;}";
    assert(!append_native_sm3_user_clip(unsupported, true));
    return 0;
}
