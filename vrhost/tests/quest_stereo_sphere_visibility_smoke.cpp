#include "vr/game/quest_stereo_sphere_visibility.hpp"
#include <array>
#include <cmath>
#include <limits>

using namespace OutRunVR::QuestStereoCull;

int main()
{
    std::array<Frustum, 2> f{};
    if (!Build(-.7f, .6f, -.6f, .7f, .05f, 200.f, f[0]) ||
        !Build(-.6f, .7f, -.6f, .7f, .05f, 200.f, f[1]))
        return 1;
    // A sphere visible only to the second eye must survive.
    if (!EitherEyeVisible(f,
            {{{-100.f, 0.f, 5.f}, {0.f, 0.f, 5.f}}}, .3f))
        return 2;
    if (EitherEyeVisible(f,
            {{{-100.f, 0.f, 5.f}, {100.f, 0.f, 5.f}}}, .3f))
        return 3;
    if (!Visible(f[0], {0.f, 0.f, 5.f}, .3f) ||
        !Visible(f[1], {0.f, 0.f, 5.f}, .3f))
        return 4;
    if (EitherEyeVisible(f,
            {{{0.f, 0.f, -10.f}, {0.f, 0.f, -10.f}}}, .3f))
        return 5;
    if (!EitherEyeVisible(f,
            {{{0.f, 0.f, 0.f}, {0.f, 0.f, 0.f}}}, .01f))
        return 6;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    if (!EitherEyeVisible(f,
            {{{nan, 0.f, 5.f}, {nan, 0.f, 5.f}}}, .3f))
        return 7;
    const auto before = f[0];
    if (Build(.8f, -.8f, -.6f, .6f, .05f, 200.f, f[0]) ||
        f[0].left != before.left)
        return 8;
    if (Build(nan, .6f, -.6f, .7f, .05f, 200.f, f[0]) ||
        f[0].left != before.left)
        return 9;
    if (!Build(-.7f, .6f, -.6f, .7f, .05f, 200.f, f[0]))
        return 10;
    // True native stereo head translation (2 eye origins) rather than
    // the old single 4:3 game camera or screen X/Y projection.
    std::array<EyeBasis,2> eyes{};
    eyes[0].origin={-.032f,0.f,0.f};
    eyes[1].origin={.032f,0.f,0.f};
    if (!EitherEyeWorldVisible(f,eyes,{0.f,0.f,5.f},.3f))
        return 11;
    if (EitherEyeWorldVisible(f,eyes,{100.f,0.f,5.f},.3f))
        return 12;
    EyeSpaceSphere projected{};
    if (!ToEyeSpace(eyes[1],{.032f,0.f,5.f},projected) ||
        std::fabs(projected.right)>1e-4f ||
        std::fabs(projected.depth-5.f)>1e-4f)
        return 13;
    // A broken view matrix (including flipped eye handedness) must
    // *retain* stage geometry until another coherent XR pose arrives.
    eyes[1].right={-1.f,0.f,0.f};
    if (ToEyeSpace(eyes[1],{0.f,0.f,5.f},projected))
        return 14;
    if (!EitherEyeWorldVisible(f,eyes,{100.f,0.f,5.f},.3f))
        return 15;
    eyes[1]=EyeBasis{};
    if (!EitherEyeWorldVisible(f,eyes,{0.f,0.f,5.f},.3f))
        return 16;
    return 0;
}