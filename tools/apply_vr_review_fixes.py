from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


def normalize_literal_indent(path: str) -> int:
    text = read(path)
    pattern = re.compile(r"(?m)^(?:\\t)+")
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += match.group(0).count("\\t")
        return "\t" * match.group(0).count("\\t")

    fixed = pattern.sub(repl, text)
    if fixed != text:
        write(path, fixed)
    return count


# The previous generator pass left a few line-leading literal "\\t" tokens.
# Normalize only indentation prefixes so string literals and documentation are untouched.
for source in (
    "src/vr_shared.hpp",
    "src/hooks_vr.cpp",
    "src/vr_renderer_probe.cpp",
    "src/vr_stereo.cpp",
    "vrhost/main_stereo.cpp",
):
    normalized = normalize_literal_indent(source)
    if normalized:
        print(f"normalized {normalized} literal indent tokens in {source}")


# Frame.v1 must describe the exact virtual eye pose that produced the SBS image.
# Head translation and IPD therefore use the same VRWorldScale as the D3D9 camera.
replace_once(
    "src/vr_renderer_probe.cpp",
    '''\t\t\t\tconst Quat effectiveHeadOrientation = Multiply(Normalize(CenterOrientation), relativeOrientation);\n\t\t\t\tVec3 effectiveHeadPosition = sample.position;\n\t\t\t\tif (!Settings::VRPositionalTracking || !sample.positionValid) effectiveHeadPosition = CenterPositionValid ? CenterPosition : sample.position;\n\t\t\t\tfor (int eye = 0; eye < 2; ++eye)\n\t\t\t\t{\n\t\t\t\t\tconst Quat eyeOrientation = sample.eyeOrientation[eye];\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][0]=eyeOrientation.x; LatchedStereo.eyeOrientation[eye][1]=eyeOrientation.y;\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][2]=eyeOrientation.z; LatchedStereo.eyeOrientation[eye][3]=eyeOrientation.w;\n\t\t\t\t\tconst Quat effectiveEyeOrientation = Multiply(effectiveHeadOrientation, eyeOrientation);\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][0]=effectiveEyeOrientation.x; LatchedStereo.effectiveEyeOrientation[eye][1]=effectiveEyeOrientation.y;\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][2]=effectiveEyeOrientation.z; LatchedStereo.effectiveEyeOrientation[eye][3]=effectiveEyeOrientation.w;\n\t\t\t\t\tconst Vec3 localEye{sample.eyeOffset[eye][0], sample.eyeOffset[eye][1], sample.eyeOffset[eye][2]};\n\t\t\t\t\tconst Vec3 worldEye = RotateVector(effectiveHeadOrientation, localEye);\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][0]=effectiveHeadPosition.x+worldEye.x;\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][1]=effectiveHeadPosition.y+worldEye.y;\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][2]=effectiveHeadPosition.z+worldEye.z;\n\t\t\t\t}\n''',
    '''\t\t\t\tconst Quat effectiveHeadOrientation = Normalize(\n\t\t\t\t\tMultiply(Normalize(CenterOrientation), relativeOrientation));\n\t\t\t\tVec3 effectiveHeadPosition = CenterPositionValid ? CenterPosition : sample.position;\n\t\t\t\tif (Settings::VRPositionalTracking && sample.positionValid && CenterPositionValid)\n\t\t\t\t{\n\t\t\t\t\tconst Vec3 delta{\n\t\t\t\t\t\tsample.position.x - CenterPosition.x,\n\t\t\t\t\t\tsample.position.y - CenterPosition.y,\n\t\t\t\t\t\tsample.position.z - CenterPosition.z\n\t\t\t\t\t};\n\t\t\t\t\teffectiveHeadPosition = {\n\t\t\t\t\t\tCenterPosition.x + delta.x * Settings::VRWorldScale,\n\t\t\t\t\t\tCenterPosition.y + delta.y * Settings::VRWorldScale,\n\t\t\t\t\t\tCenterPosition.z + delta.z * Settings::VRWorldScale\n\t\t\t\t\t};\n\t\t\t\t}\n\t\t\t\tfor (int eye = 0; eye < 2; ++eye)\n\t\t\t\t{\n\t\t\t\t\tconst Quat eyeOrientation = sample.eyeOrientation[eye];\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][0] = eyeOrientation.x;\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][1] = eyeOrientation.y;\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][2] = eyeOrientation.z;\n\t\t\t\t\tLatchedStereo.eyeOrientation[eye][3] = eyeOrientation.w;\n\n\t\t\t\t\tconst Quat effectiveEyeOrientation = Normalize(\n\t\t\t\t\t\tMultiply(effectiveHeadOrientation, eyeOrientation));\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][0] = effectiveEyeOrientation.x;\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][1] = effectiveEyeOrientation.y;\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][2] = effectiveEyeOrientation.z;\n\t\t\t\t\tLatchedStereo.effectiveEyeOrientation[eye][3] = effectiveEyeOrientation.w;\n\n\t\t\t\t\tconst Vec3 localEye{\n\t\t\t\t\t\tsample.eyeOffset[eye][0] * Settings::VRWorldScale,\n\t\t\t\t\t\tsample.eyeOffset[eye][1] * Settings::VRWorldScale,\n\t\t\t\t\t\tsample.eyeOffset[eye][2] * Settings::VRWorldScale\n\t\t\t\t\t};\n\t\t\t\t\tconst Vec3 worldEye = RotateVector(effectiveHeadOrientation, localEye);\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][0] = effectiveHeadPosition.x + worldEye.x;\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][1] = effectiveHeadPosition.y + worldEye.y;\n\t\t\t\t\tLatchedStereo.effectiveEyePosition[eye][2] = effectiveHeadPosition.z + worldEye.z;\n\t\t\t\t}\n''',
)


# Remove the old duplicate capture initializer. BindCaptureOutput() is now the
# single output/monitor/duplication setup path, including HWND recreation.
host = read("vrhost/main_stereo.cpp")
legacy_start = host.find("        bool InitializeLegacyCaptureRemoved()")
legacy_end = host.find("        CaptureStatus Capture(", legacy_start)
if legacy_start < 0 or legacy_end < 0:
    raise RuntimeError("vrhost/main_stereo.cpp: legacy capture initializer boundary not found")
host = host[:legacy_start] + host[legacy_end:]
write("vrhost/main_stereo.cpp", host)


# Keep the safety-critical frame publication code readable and preserve exact
# markers used by both reviewers and CI.
stereo = read("src/vr_stereo.cpp")
if "\\t" in "\n".join(line[:16] for line in stereo.splitlines()):
    raise RuntimeError("src/vr_stereo.cpp: literal indentation tokens remain")

required = {
    "src/vr_renderer_probe.cpp": [
        "effectiveHeadPosition",
        "delta.x * Settings::VRWorldScale",
        "sample.eyeOffset[eye][0] * Settings::VRWorldScale",
        "VRCullingUnionFov",
    ],
    "src/vr_stereo.cpp": [
        "StereoFailureDepthUnsynchronized",
        "FrameStereoIncomplete",
        "PublishRenderFrame",
        "presentStart.QuadPart",
        "RightDepthSynchronized",
    ],
    "vrhost/main_stereo.cpp": [
        "RenderFrameReader",
        "QpcAtOrAfter",
        "BindCaptureOutput",
        "pendingReferenceSpaceChangeTime",
        "HostTimings",
    ],
    "src/vr_shared.hpp": [
        "static_assert(sizeof(SharedPoseState) == 248)",
        "static_assert(sizeof(SharedRenderFrameState) == 256)",
        "StereoEyeOrientationValid",
        "RenderFrameEffectivePoseValid",
    ],
}
for path, markers in required.items():
    text = read(path)
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path}: required marker missing after cleanup: {marker}")

print("VR final cleanup patch applied successfully")
