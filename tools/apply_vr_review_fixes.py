from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:160]!r}")
    write(path, text.replace(old, new, 1))


# Preserve the original Pose.v1 field layout exactly. The last 16 bytes of the
# 64-byte runtimeName field are an extension tail: new hosts keep byte 47 NUL,
# so old C-string readers remain compatible while new clients can decode two
# SNORM16 eye quaternions from bytes 48..63 under StereoEyeOrientationValid.
replace_once("src/vr_shared.hpp", "#include <cstdint>\n", "#include <cstddef>\n#include <cstdint>\n")
replace_once(
    "src/vr_shared.hpp",
    '''\tinline constexpr std::uint32_t RenderFrameProtocolVersion = 1;\n''',
    '''\tinline constexpr std::uint32_t RenderFrameProtocolVersion = 1;\n\tinline constexpr std::size_t PackedEyeOrientationOffset = 48;\n\tinline constexpr std::size_t PackedEyeOrientationBytes = 16;\n''',
)
replace_once(
    "src/vr_shared.hpp",
    '''\t\tSharedFov eyeFov[2];\n\t\tfloat eyeOrientation[2][4];\n\t\tchar runtimeName[48];\n\t\tstd::uint32_t reserved[16];\n''',
    '''\t\tSharedFov eyeFov[2];\n\t\tstd::uint32_t recommendedWidth[2];\n\t\tstd::uint32_t recommendedHeight[2];\n\t\tchar runtimeName[64];\n\t\tstd::uint32_t reserved[16];\n''',
)
replace_once(
    "src/vr_shared.hpp",
    '''\tstatic_assert(sizeof(SharedPoseState) == 248);\n\tstatic_assert(sizeof(SharedRenderEye) == 48);\n''',
    '''\tstatic_assert(sizeof(SharedPoseState) == 248);\n\tstatic_assert(offsetof(SharedPoseState, recommendedWidth) == 104);\n\tstatic_assert(offsetof(SharedPoseState, recommendedHeight) == 112);\n\tstatic_assert(offsetof(SharedPoseState, runtimeName) == 120);\n\tstatic_assert(offsetof(SharedPoseState, reserved) == 184);\n\tstatic_assert(PackedEyeOrientationOffset + PackedEyeOrientationBytes == sizeof(SharedPoseState::runtimeName));\n\tstatic_assert(sizeof(SharedRenderEye) == 48);\n''',
)

# Host-side SNORM16 packing and restoration of the original recommended-size fields.
replace_once(
    "vrhost/main_stereo.cpp",
    '''    std::uint32_t FloatBits(float v)\n    {\n        std::uint32_t b = 0;\n        std::memcpy(&b, &v, sizeof(b));\n        return b;\n    }\n''',
    '''    std::uint32_t FloatBits(float v)\n    {\n        std::uint32_t b = 0;\n        std::memcpy(&b, &v, sizeof(b));\n        return b;\n    }\n\n    std::int16_t PackSnorm16(float value)\n    {\n        const float clamped = std::clamp(value, -1.0f, 1.0f);\n        return static_cast<std::int16_t>(std::lround(clamped * 32767.0f));\n    }\n\n    void StorePackedEyeOrientations(char runtimeName[64], const XrQuaternionf eyeOrientation[2])\n    {\n        std::int16_t packed[8]{};\n        for (int eye = 0; eye < 2; ++eye)\n        {\n            const XrQuaternionf q = NormalizeQuaternion(eyeOrientation[eye]);\n            packed[eye * 4 + 0] = PackSnorm16(q.x);\n            packed[eye * 4 + 1] = PackSnorm16(q.y);\n            packed[eye * 4 + 2] = PackSnorm16(q.z);\n            packed[eye * 4 + 3] = PackSnorm16(q.w);\n        }\n        static_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);\n        std::memcpy(runtimeName + OutRunVR::PackedEyeOrientationOffset, packed, sizeof(packed));\n    }\n''',
)
replace_once(
    "vrhost/main_stereo.cpp",
    '''            for (std::uint32_t eye = 0; eye < 2; ++eye)\n            {\n                if (eye < viewCount)\n                {\n                    state_->eyeFov[eye] = {\n                        views[eye].fov.angleLeft, views[eye].fov.angleRight,\n                        views[eye].fov.angleUp, views[eye].fov.angleDown\n                    };\n                }\n            }\n            (void)configs;\n            if(stereoValid)\n            {\n                const XrVector3f left=ToHeadLocal(head.pose,views[0].pose.position),right=ToHeadLocal(head.pose,views[1].pose.position);\n                const XrQuaternionf eq[2]={ToHeadLocalOrientation(head.pose,views[0].pose),ToHeadLocalOrientation(head.pose,views[1].pose)};\n                for(int eye=0;eye<2;++eye){state_->eyeOrientation[eye][0]=eq[eye].x;state_->eyeOrientation[eye][1]=eq[eye].y;state_->eyeOrientation[eye][2]=eq[eye].z;state_->eyeOrientation[eye][3]=eq[eye].w;}\n                state_->reserved[OutRunVR::HostEyeOffsetLeftXIndex] = FloatBits(left.x);\n                state_->reserved[OutRunVR::HostEyeOffsetLeftYIndex] = FloatBits(left.y);\n                state_->reserved[OutRunVR::HostEyeOffsetLeftZIndex] = FloatBits(left.z);\n                state_->reserved[OutRunVR::HostEyeOffsetRightXIndex] = FloatBits(right.x);\n                state_->reserved[OutRunVR::HostEyeOffsetRightYIndex] = FloatBits(right.y);\n                state_->reserved[OutRunVR::HostEyeOffsetRightZIndex] = FloatBits(right.z);\n            }\n            strncpy_s(state_->runtimeName, sizeof(state_->runtimeName),\n                runtime ? runtime : "unknown", _TRUNCATE);\n''',
    '''            for (std::uint32_t eye = 0; eye < 2; ++eye)\n            {\n                state_->recommendedWidth[eye] = configs[eye].recommendedImageRectWidth;\n                state_->recommendedHeight[eye] = configs[eye].recommendedImageRectHeight;\n                if (eye < viewCount)\n                {\n                    state_->eyeFov[eye] = {\n                        views[eye].fov.angleLeft, views[eye].fov.angleRight,\n                        views[eye].fov.angleUp, views[eye].fov.angleDown\n                    };\n                }\n            }\n\n            std::memset(state_->runtimeName, 0, sizeof(state_->runtimeName));\n            strncpy_s(state_->runtimeName, OutRunVR::PackedEyeOrientationOffset,\n                runtime ? runtime : "unknown", _TRUNCATE);\n            if (stereoValid)\n            {\n                const XrVector3f left = ToHeadLocal(head.pose, views[0].pose.position);\n                const XrVector3f right = ToHeadLocal(head.pose, views[1].pose.position);\n                const XrQuaternionf eyeOrientation[2]{\n                    ToHeadLocalOrientation(head.pose, views[0].pose),\n                    ToHeadLocalOrientation(head.pose, views[1].pose)\n                };\n                StorePackedEyeOrientations(state_->runtimeName, eyeOrientation);\n                state_->reserved[OutRunVR::HostEyeOffsetLeftXIndex] = FloatBits(left.x);\n                state_->reserved[OutRunVR::HostEyeOffsetLeftYIndex] = FloatBits(left.y);\n                state_->reserved[OutRunVR::HostEyeOffsetLeftZIndex] = FloatBits(left.z);\n                state_->reserved[OutRunVR::HostEyeOffsetRightXIndex] = FloatBits(right.x);\n                state_->reserved[OutRunVR::HostEyeOffsetRightYIndex] = FloatBits(right.y);\n                state_->reserved[OutRunVR::HostEyeOffsetRightZIndex] = FloatBits(right.z);\n            }\n''',
)

# Client-side decode from the ABI-compatible runtimeName extension tail.
replace_once(
    "src/vr_renderer_probe.cpp",
    '''\t\tfloat FloatFromBits(std::uint32_t bits)\n\t\t{\n\t\t\tfloat value = 0.0f;\n\t\t\tstd::memcpy(&value, &bits, sizeof(value));\n\t\t\treturn value;\n\t\t}\n''',
    '''\t\tfloat FloatFromBits(std::uint32_t bits)\n\t\t{\n\t\t\tfloat value = 0.0f;\n\t\t\tstd::memcpy(&value, &bits, sizeof(value));\n\t\t\treturn value;\n\t\t}\n\n\t\tbool DecodePackedEyeOrientations(const SharedPoseState& snapshot, Quat out[2])\n\t\t{\n\t\t\tstd::int16_t packed[8]{};\n\t\t\tstatic_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);\n\t\t\tstd::memcpy(packed, snapshot.runtimeName + OutRunVR::PackedEyeOrientationOffset, sizeof(packed));\n\t\t\tfor (int eye = 0; eye < 2; ++eye)\n\t\t\t{\n\t\t\t\tQuat q{\n\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 0]) / 32767.0f,\n\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 1]) / 32767.0f,\n\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 2]) / 32767.0f,\n\t\t\t\t\tstatic_cast<float>(packed[eye * 4 + 3]) / 32767.0f\n\t\t\t\t};\n\t\t\t\tif (!QuaternionIsSane(q))\n\t\t\t\t\treturn false;\n\t\t\t\tout[eye] = Normalize(q);\n\t\t\t}\n\t\t\treturn true;\n\t\t}\n''',
)
replace_once(
    "src/vr_renderer_probe.cpp",
    '''\t\t\t\tconst std::uint32_t indexes[2][3] = {\n\t\t\t\t\t{ HostEyeOffsetLeftXIndex, HostEyeOffsetLeftYIndex, HostEyeOffsetLeftZIndex },\n\t\t\t\t\t{ HostEyeOffsetRightXIndex, HostEyeOffsetRightYIndex, HostEyeOffsetRightZIndex }\n\t\t\t\t};\n\t\t\t\tfor (int eye = 0; eye < 2 && pose.stereoValid; ++eye)\n\t\t\t\t{\n\t\t\t\t\tfor (int axis = 0; axis < 3; ++axis)\n\t\t\t\t\t{\n\t\t\t\t\t\tconst float value = FloatFromBits(snapshot.reserved[indexes[eye][axis]]);\n\t\t\t\t\t\tif (!std::isfinite(value) || std::fabs(value) > 0.25f)\n\t\t\t\t\t\t{\n\t\t\t\t\t\t\tpose.stereoValid = false;\n\t\t\t\t\t\t\tbreak;\n\t\t\t\t\t\t}\n\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;\n\t\t\t\t\t}\n\t\t\t\t\tconst Quat eyeQ{ snapshot.eyeOrientation[eye][0], snapshot.eyeOrientation[eye][1],\n\t\t\t\t\t\tsnapshot.eyeOrientation[eye][2], snapshot.eyeOrientation[eye][3] };\n\t\t\t\t\tif (!QuaternionIsSane(eyeQ)) pose.stereoValid = false;\n\t\t\t\t\telse pose.eyeOrientation[eye] = Normalize(eyeQ);\n\t\t\t\t}\n''',
    '''\t\t\t\tQuat eyeOrientation[2]{};\n\t\t\t\tif (!DecodePackedEyeOrientations(snapshot, eyeOrientation))\n\t\t\t\t\tpose.stereoValid = false;\n\t\t\t\tconst std::uint32_t indexes[2][3] = {\n\t\t\t\t\t{ HostEyeOffsetLeftXIndex, HostEyeOffsetLeftYIndex, HostEyeOffsetLeftZIndex },\n\t\t\t\t\t{ HostEyeOffsetRightXIndex, HostEyeOffsetRightYIndex, HostEyeOffsetRightZIndex }\n\t\t\t\t};\n\t\t\t\tfor (int eye = 0; eye < 2 && pose.stereoValid; ++eye)\n\t\t\t\t{\n\t\t\t\t\tfor (int axis = 0; axis < 3; ++axis)\n\t\t\t\t\t{\n\t\t\t\t\t\tconst float value = FloatFromBits(snapshot.reserved[indexes[eye][axis]]);\n\t\t\t\t\t\tif (!std::isfinite(value) || std::fabs(value) > 0.25f)\n\t\t\t\t\t\t{\n\t\t\t\t\t\t\tpose.stereoValid = false;\n\t\t\t\t\t\t\tbreak;\n\t\t\t\t\t\t}\n\t\t\t\t\t\tpose.eyeOffset[eye][axis] = value;\n\t\t\t\t\t}\n\t\t\t\t\tpose.eyeOrientation[eye] = eyeOrientation[eye];\n\t\t\t\t}\n''',
)

# A partial depth clear cannot prove a newly-created right depth surface is fully
# initialized. Keep fail-closed until a successful full-surface Z clear occurs.
replace_once(
    "src/vr_stereo.cpp",
    '''else if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=true;''',
    '''else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0) RightDepthSynchronized = true;''',
)

# Remove obsolete low-word QPC comparison now that Frame.v1 transports int64 QPC.
main = read("vrhost/main_stereo.cpp")
old_qpc = '''    bool QpcLowAtOrAfter(std::uint32_t capture, std::uint32_t present)\n    {\n        if (capture == 0 || present == 0) return false;\n        return static_cast<std::int32_t>(capture - present) >= 0;\n    }\n\n'''
if old_qpc not in main:
    raise RuntimeError("vrhost/main_stereo.cpp: obsolete QpcLowAtOrAfter helper not found")
write("vrhost/main_stereo.cpp", main.replace(old_qpc, "", 1))

# Lock in the backward-compatible Pose.v1 layout and final safety invariants.
checks = {
    "src/vr_shared.hpp": [
        "offsetof(SharedPoseState, recommendedWidth) == 104",
        "offsetof(SharedPoseState, runtimeName) == 120",
        "offsetof(SharedPoseState, reserved) == 184",
        "PackedEyeOrientationOffset = 48",
        "static_assert(sizeof(SharedPoseState) == 248)",
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
    ],
    "src/vr_stereo.cpp": [
        "D3DCLEAR_ZBUFFER) != 0 && count == 0",
        "StereoFailureDepthUnsynchronized",
    ],
}
for path, markers in checks.items():
    text = read(path)
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path}: missing final invariant: {marker}")

print("Pose.v1 ABI and final stereo safety pass applied successfully")
