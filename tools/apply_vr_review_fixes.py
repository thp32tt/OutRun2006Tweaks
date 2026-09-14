from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one match for {old[:120]!r}")
    write(path, text.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str, flags=0) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one regex match for {pattern[:120]!r}, got {count}")
    write(path, updated)


# ---------------------------------------------------------------------------
# Pose.v1: restore the exact original semantic layout and offsets.
# Eye orientation uses runtimeName[48..63] as an extension tail. New hosts keep
# the first 48 bytes NUL-terminated, so legacy C-string readers remain safe.
# ---------------------------------------------------------------------------
shared = read("src/vr_shared.hpp")
if "#include <cstddef>" not in shared:
    shared = shared.replace("#include <cstdint>\n", "#include <cstddef>\n#include <cstdint>\n", 1)

shared = shared.replace(
    "    inline constexpr std::uint32_t RenderFrameProtocolVersion = 1;\n",
    "    inline constexpr std::uint32_t RenderFrameProtocolVersion = 1;\n"
    "    inline constexpr std::size_t PackedEyeOrientationOffset = 48;\n"
    "    inline constexpr std::size_t PackedEyeOrientationBytes = 16;\n",
    1,
)

old_layout = (
    "        SharedFov eyeFov[2];\n"
    "        float eyeOrientation[2][4];\n"
    "        char runtimeName[48];\n"
    "        std::uint32_t reserved[16];\n"
)
new_layout = (
    "        SharedFov eyeFov[2];\n"
    "        std::uint32_t recommendedWidth[2];\n"
    "        std::uint32_t recommendedHeight[2];\n"
    "        char runtimeName[64];\n"
    "        std::uint32_t reserved[16];\n"
)
if old_layout not in shared:
    raise RuntimeError("src/vr_shared.hpp: modified Pose.v1 layout not found")
shared = shared.replace(old_layout, new_layout, 1)

old_asserts = (
    "    static_assert(sizeof(SharedPoseState) == 248);\n"
    "    static_assert(sizeof(SharedRenderEye) == 48);\n"
)
new_asserts = (
    "    static_assert(sizeof(SharedPoseState) == 248);\n"
    "    static_assert(offsetof(SharedPoseState, recommendedWidth) == 104);\n"
    "    static_assert(offsetof(SharedPoseState, recommendedHeight) == 112);\n"
    "    static_assert(offsetof(SharedPoseState, runtimeName) == 120);\n"
    "    static_assert(offsetof(SharedPoseState, reserved) == 184);\n"
    "    static_assert(PackedEyeOrientationOffset + PackedEyeOrientationBytes == 64);\n"
    "    static_assert(sizeof(SharedRenderEye) == 48);\n"
)
if old_asserts not in shared:
    raise RuntimeError("src/vr_shared.hpp: Pose.v1 static assert block not found")
shared = shared.replace(old_asserts, new_asserts, 1)
write("src/vr_shared.hpp", shared)


# ---------------------------------------------------------------------------
# Host: pack per-eye relative orientation as two SNORM16 quaternions and restore
# original recommended eye-size publication.
# ---------------------------------------------------------------------------
host = read("vrhost/main_stereo.cpp")
float_bits = '''    std::uint32_t FloatBits(float v)
    {
        std::uint32_t b = 0;
        std::memcpy(&b, &v, sizeof(b));
        return b;
    }
'''
pack_helpers = float_bits + '''
    std::int16_t PackSnorm16(float value)
    {
        const float clamped = std::clamp(value, -1.0f, 1.0f);
        return static_cast<std::int16_t>(std::lround(clamped * 32767.0f));
    }

    void StorePackedEyeOrientations(char runtimeName[64], const XrQuaternionf eyeOrientation[2])
    {
        std::int16_t packed[8]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            const XrQuaternionf q = NormalizeQuaternion(eyeOrientation[eye]);
            packed[eye * 4 + 0] = PackSnorm16(q.x);
            packed[eye * 4 + 1] = PackSnorm16(q.y);
            packed[eye * 4 + 2] = PackSnorm16(q.z);
            packed[eye * 4 + 3] = PackSnorm16(q.w);
        }
        static_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);
        std::memcpy(runtimeName + OutRunVR::PackedEyeOrientationOffset, packed, sizeof(packed));
    }
'''
if "StorePackedEyeOrientations" not in host:
    if host.count(float_bits) != 1:
        raise RuntimeError("vrhost/main_stereo.cpp: FloatBits helper not uniquely found")
    host = host.replace(float_bits, pack_helpers, 1)

write_block_pattern = re.compile(
    r'''            for \(std::uint32_t eye = 0; eye < 2; \+\+eye\)\n'''
    r'''            \{\n'''
    r'''                if \(eye < viewCount\)\n'''
    r'''                \{\n'''
    r'''                    state_->eyeFov\[eye\] = \{\n'''
    r'''                        views\[eye\]\.fov\.angleLeft, views\[eye\]\.fov\.angleRight,\n'''
    r'''                        views\[eye\]\.fov\.angleUp, views\[eye\]\.fov\.angleDown\n'''
    r'''                    \};\n'''
    r'''                \}\n'''
    r'''            \}\n'''
    r'''            \(void\)configs;\n'''
    r'''            if\(stereoValid\)\n'''
    r'''            \{\n'''
    r'''                const XrVector3f left=ToHeadLocal\(head\.pose,views\[0\]\.pose\.position\),right=ToHeadLocal\(head\.pose,views\[1\]\.pose\.position\);\n'''
    r'''                const XrQuaternionf eq\[2\]=\{ToHeadLocalOrientation\(head\.pose,views\[0\]\.pose\),ToHeadLocalOrientation\(head\.pose,views\[1\]\.pose\)\};\n'''
    r'''                for\(int eye=0;eye<2;\+\+eye\)\{state_->eyeOrientation\[eye\]\[0\]=eq\[eye\]\.x;state_->eyeOrientation\[eye\]\[1\]=eq\[eye\]\.y;state_->eyeOrientation\[eye\]\[2\]=eq\[eye\]\.z;state_->eyeOrientation\[eye\]\[3\]=eq\[eye\]\.w;\}\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetLeftXIndex\] = FloatBits\(left\.x\);\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetLeftYIndex\] = FloatBits\(left\.y\);\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetLeftZIndex\] = FloatBits\(left\.z\);\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetRightXIndex\] = FloatBits\(right\.x\);\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetRightYIndex\] = FloatBits\(right\.y\);\n'''
    r'''                state_->reserved\[OutRunVR::HostEyeOffsetRightZIndex\] = FloatBits\(right\.z\);\n'''
    r'''            \}\n'''
    r'''            strncpy_s\(state_->runtimeName, sizeof\(state_->runtimeName\),\n'''
    r'''                runtime \? runtime : "unknown", _TRUNCATE\);\n'''
)
write_block = '''            for (std::uint32_t eye = 0; eye < 2; ++eye)
            {
                state_->recommendedWidth[eye] = configs[eye].recommendedImageRectWidth;
                state_->recommendedHeight[eye] = configs[eye].recommendedImageRectHeight;
                if (eye < viewCount)
                {
                    state_->eyeFov[eye] = {
                        views[eye].fov.angleLeft, views[eye].fov.angleRight,
                        views[eye].fov.angleUp, views[eye].fov.angleDown
                    };
                }
            }

            std::memset(state_->runtimeName, 0, sizeof(state_->runtimeName));
            strncpy_s(state_->runtimeName, OutRunVR::PackedEyeOrientationOffset,
                runtime ? runtime : "unknown", _TRUNCATE);
            if (stereoValid)
            {
                const XrVector3f left = ToHeadLocal(head.pose, views[0].pose.position);
                const XrVector3f right = ToHeadLocal(head.pose, views[1].pose.position);
                const XrQuaternionf eyeOrientation[2]{
                    ToHeadLocalOrientation(head.pose, views[0].pose),
                    ToHeadLocalOrientation(head.pose, views[1].pose)
                };
                StorePackedEyeOrientations(state_->runtimeName, eyeOrientation);
                state_->reserved[OutRunVR::HostEyeOffsetLeftXIndex] = FloatBits(left.x);
                state_->reserved[OutRunVR::HostEyeOffsetLeftYIndex] = FloatBits(left.y);
                state_->reserved[OutRunVR::HostEyeOffsetLeftZIndex] = FloatBits(left.z);
                state_->reserved[OutRunVR::HostEyeOffsetRightXIndex] = FloatBits(right.x);
                state_->reserved[OutRunVR::HostEyeOffsetRightYIndex] = FloatBits(right.y);
                state_->reserved[OutRunVR::HostEyeOffsetRightZIndex] = FloatBits(right.z);
            }
'''
host, count = write_block_pattern.subn(write_block, host, count=1)
if count != 1:
    raise RuntimeError(f"vrhost/main_stereo.cpp: SharedWriter old eye block match count={count}")

qpc_low = '''    bool QpcLowAtOrAfter(std::uint32_t capture, std::uint32_t present)
    {
        if (capture == 0 || present == 0) return false;
        return static_cast<std::int32_t>(capture - present) >= 0;
    }

'''
if qpc_low in host:
    host = host.replace(qpc_low, "", 1)
write("vrhost/main_stereo.cpp", host)


# ---------------------------------------------------------------------------
# x86 pose reader: decode packed eye quaternions from the compatible tail.
# ---------------------------------------------------------------------------
renderer = read("src/vr_renderer_probe.cpp")
float_from_bits = '''\t\tfloat FloatFromBits(std::uint32_t bits)
\t\t{
\t\t\tfloat value = 0.0f;
\t\t\tstd::memcpy(&value, &bits, sizeof(value));
\t\t\treturn value;
\t\t}
'''
decode_helper = float_from_bits + '''
\t\tbool DecodePackedEyeOrientations(const SharedPoseState& snapshot, Quat out[2])
\t\t{
\t\t\tstd::int16_t packed[8]{};
\t\t\tstatic_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);
\t\t\tstd::memcpy(packed,
\t\t\t\tsnapshot.runtimeName + OutRunVR::PackedEyeOrientationOffset,
\t\t\t\tsizeof(packed));
\t\t\tfor (int eye = 0; eye < 2; ++eye)
\t\t\t{
\t\t\t\tQuat q{
\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 0]) / 32767.0f,
\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 1]) / 32767.0f,
\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 2]) / 32767.0f,
\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 3]) / 32767.0f
\t\t\t\t};
\t\t\t\tif (!QuaternionIsSane(q))
\t\t\t\t\treturn false;
\t\t\t\tout[eye] = Normalize(q);
\t\t\t}
\t\t\treturn true;
\t\t}
'''
if "DecodePackedEyeOrientations" not in renderer:
    if renderer.count(float_from_bits) != 1:
        raise RuntimeError("src/vr_renderer_probe.cpp: FloatFromBits helper not uniquely found")
    renderer = renderer.replace(float_from_bits, decode_helper, 1)

old_eye_decode = '''\t\t\t\tconst std::uint32_t indexes[2][3] = {
\t\t\t\t\t{ HostEyeOffsetLeftXIndex, HostEyeOffsetLeftYIndex, HostEyeOffsetLeftZIndex },
\t\t\t\t\t{ HostEyeOffsetRightXIndex, HostEyeOffsetRightYIndex, HostEyeOffsetRightZIndex }
\t\t\t\t};
\t\t\t\tfor (int eye = 0; eye < 2 && pose.stereoValid; ++eye)
\t\t\t\t{
\t\t\t\t\tfor (int axis = 0; axis < 3; ++axis)
\t\t\t\t\t{
\t\t\t\t\t\tconst float value = FloatFromBits(snapshot.reserved[indexes[eye][axis]]);
\t\t\t\t\t\tif (!std::isfinite(value) || std::fabs(value) > 0.25f)
\t\t\t\t\t\t{
\t\t\t\t\t\t\tpose.stereoValid = false;
\t\t\t\t\t\t\tbreak;
\t\t\t\t\t\t}
\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;
\t\t\t\t\t}
\t\t\t\t\tconst Quat eyeQ{ snapshot.eyeOrientation[eye][0], snapshot.eyeOrientation[eye][1],
\t\t\t\t\t\tsnapshot.eyeOrientation[eye][2], snapshot.eyeOrientation[eye][3] };
\t\t\t\t\tif (!QuaternionIsSane(eyeQ)) pose.stereoValid = false;
\t\t\t\t\telse pose.eyeOrientation[eye] = Normalize(eyeQ);
\t\t\t\t}
'''
new_eye_decode = '''\t\t\t\tQuat eyeOrientation[2]{};
\t\t\t\tif (!DecodePackedEyeOrientations(snapshot, eyeOrientation))
\t\t\t\t\tpose.stereoValid = false;
\t\t\t\tconst std::uint32_t indexes[2][3] = {
\t\t\t\t\t{ HostEyeOffsetLeftXIndex, HostEyeOffsetLeftYIndex, HostEyeOffsetLeftZIndex },
\t\t\t\t\t{ HostEyeOffsetRightXIndex, HostEyeOffsetRightYIndex, HostEyeOffsetRightZIndex }
\t\t\t\t};
\t\t\t\tfor (int eye = 0; eye < 2 && pose.stereoValid; ++eye)
\t\t\t\t{
\t\t\t\t\tfor (int axis = 0; axis < 3; ++axis)
\t\t\t\t\t{
\t\t\t\t\t\tconst float value = FloatFromBits(snapshot.reserved[indexes[eye][axis]]);
\t\t\t\t\t\tif (!std::isfinite(value) || std::fabs(value) > 0.25f)
\t\t\t\t\t\t{
\t\t\t\t\t\t\tpose.stereoValid = false;
\t\t\t\t\t\t\tbreak;
\t\t\t\t\t\t}
\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;
\t\t\t\t\t}
\t\t\t\t\tpose.eyeOrientation[eye] = eyeOrientation[eye];
\t\t\t\t}
'''
if renderer.count(old_eye_decode) != 1:
    raise RuntimeError("src/vr_renderer_probe.cpp: old eye orientation decode block not found")
renderer = renderer.replace(old_eye_decode, new_eye_decode, 1)
write("src/vr_renderer_probe.cpp", renderer)


# ---------------------------------------------------------------------------
# Right-eye depth is considered synchronized only by a full-surface Z clear.
# ---------------------------------------------------------------------------
stereo = read("src/vr_stereo.cpp")
old_depth = "else if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=true;"
if old_depth in stereo:
    stereo = stereo.replace(
        old_depth,
        "else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0) RightDepthSynchronized = true;",
        1,
    )
elif "D3DCLEAR_ZBUFFER) != 0 && count == 0" not in stereo:
    raise RuntimeError("src/vr_stereo.cpp: right-depth synchronization marker not found")
write("src/vr_stereo.cpp", stereo)


# Final invariants.
required = {
    "src/vr_shared.hpp": [
        "static_assert(sizeof(SharedPoseState) == 248)",
        "offsetof(SharedPoseState, recommendedWidth) == 104",
        "offsetof(SharedPoseState, recommendedHeight) == 112",
        "offsetof(SharedPoseState, runtimeName) == 120",
        "offsetof(SharedPoseState, reserved) == 184",
        "PackedEyeOrientationOffset = 48",
        "recommendedWidth[2]",
        "runtimeName[64]",
    ],
    "vrhost/main_stereo.cpp": [
        "StorePackedEyeOrientations",
        "recommendedImageRectWidth",
        "QpcAtOrAfter",
    ],
    "src/vr_renderer_probe.cpp": [
        "DecodePackedEyeOrientations",
        "PackedEyeOrientationOffset",
        "delta.x * Settings::VRWorldScale",
        "sample.eyeOffset[eye][0] * Settings::VRWorldScale",
    ],
    "src/vr_stereo.cpp": [
        "D3DCLEAR_ZBUFFER) != 0 && count == 0",
        "StereoFailureDepthUnsynchronized",
    ],
}
for path, markers in required.items():
    text = read(path)
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path}: missing final invariant: {marker}")

print("Pose.v1 ABI and final stereo safety pass applied successfully")
