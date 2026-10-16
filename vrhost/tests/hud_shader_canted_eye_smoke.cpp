// Native R84 shader ScreenHud optical plane input contract.
// The actual renderer calls HudShaderEyes::Build before generating BOTH
// shader c64 eye constants; this same pure C++ source runs in host CI.
#include "vr/d3d9/hud_shader_eye_pose.hpp"
#include <cmath>
#include <limits>

namespace {
bool Near(float a, float b, float tolerance = 0.0003f) {
    return std::isfinite(a) && std::isfinite(b) &&
        std::fabs(a-b) < tolerance;
}
float YawSignal(const float (&q)[4]) {
    // Y rotation of a forward-looking sample ray. Distinct canted eyes
    // must not collapse into the identity pair of the historical R84 HUD.
    return 2.0f * (q[3]*q[1] + q[0]*q[2]);
}
bool Unchanged(const OutRunVR::HudShaderEyes::PosePair& pair) {
    for (const auto& eye : pair.offset)
        for (const float value : eye)
            if (value != 17.0f) return false;
    for (const auto& eye : pair.orientation)
        for (const float value : eye)
            if (value != 19.0f) return false;
    return true;
}
void Sentinel(OutRunVR::HudShaderEyes::PosePair& pair) {
    for (auto& eye : pair.offset) for (float& v : eye) v=17.0f;
    for (auto& eye : pair.orientation) for (float& v : eye) v=19.0f;
}
}
int main() {
    using OutRunVR::HudShaderEyes::Build;
    using OutRunVR::HudShaderEyes::PosePair;
    const float cant = 0.13f;
    float eyeOffsets[2][3]{
        {123.0f-0.032f, 8.0f, -4.0f},
        {123.0f+0.032f, 8.0f, -4.0f}};
    const float eyes[2][4]{
        {0.0f, -std::sin(cant), 0.0f, std::cos(cant)},
        {0.0f, std::sin(cant), 0.0f, std::cos(cant)}};
    PosePair result{};
    if (!Build(eyeOffsets, eyes, 1.0f, result)) return 1;
    if (!Near(result.offset[0][0],-0.032f,0.001f) ||
        !Near(result.offset[1][0],0.032f,0.001f) ||
        !Near(result.offset[0][1],0.0f) ||
        !Near(result.offset[1][2],0.0f) ||
        !(YawSignal(result.orientation[0]) < -0.1f) ||
        !(YawSignal(result.orientation[1]) > 0.1f)) return 2;
    const float parallel[2][4]{{0,0,0,1}, {0,0,0,1}};
    if (!Build(eyeOffsets, parallel, 0.5f, result) ||
        !Near(YawSignal(result.orientation[0]),0.0f) ||
        !Near(YawSignal(result.orientation[1]),0.0f)) return 3;
    // A distant valid origin can overflow a float midpoint if averaged
    // before widening, but still has a finite bilateral relative offset.
    eyeOffsets[0][0] = std::numeric_limits<float>::max();
    eyeOffsets[1][0] = std::numeric_limits<float>::max();
    if (!Build(eyeOffsets, parallel, 1.0f, result) ||
        !Near(result.offset[0][0],0.0f) ||
        !Near(result.offset[1][0],0.0f)) return 4;
    eyeOffsets[0][0] = -0.032f;
    eyeOffsets[1][0] = 0.032f;
    Sentinel(result);
    const float invalidRight[2][4]{{0,0,0,1},{0,0,0,0}};
    if (Build(eyeOffsets, invalidRight, 1.0f, result) ||
        Build(eyeOffsets, eyes, 0.0f, result) ||
        Build(eyeOffsets, eyes, -1.0f, result) ||
        Build(eyeOffsets, eyes, std::numeric_limits<float>::infinity(), result) ||
        !Unchanged(result)) return 5;
    eyeOffsets[1][2] = std::numeric_limits<float>::quiet_NaN();
    if (Build(eyeOffsets, eyes, 1.0f, result) || !Unchanged(result))
        return 6;
    return 0;
}
