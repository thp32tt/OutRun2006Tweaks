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
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:180]!r}")
    write(path, text.replace(old, new, 1))


replace_once(
    "src/vr_stereo.cpp",
    "\t\tbool RightDepthSynchronized = true;\n",
    "\t\tbool RightDepthSynchronized = true;\n\t\tbool LastHostRenderEligible = false;\n",
)

replace_once(
    "src/vr_stereo.cpp",
    '''\t\tbool StereoWanted()\n\t\t{\n\t\t\tif (!Settings::VRStereo || !GameplayActive() || !HostRenderEligible())\n\t\t\t\treturn false;\n\t\t\treturn Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;\n\t\t}\n''',
    '''\t\tbool StereoWanted()\n\t\t{\n\t\t\tconst bool hostEligible = HostRenderEligible();\n\t\t\tif (hostEligible && !LastHostRenderEligible && TrackedDepthStencil)\n\t\t\t{\n\t\t\t\t// The left/game depth may have advanced while OpenXR asked us not to\n\t\t\t\t// render. Require the next full duplicated Z clear before reusing the\n\t\t\t\t// right-eye depth surface.\n\t\t\t\tRightDepthSynchronized = false;\n\t\t\t}\n\t\t\tLastHostRenderEligible = hostEligible;\n\t\t\tif (!Settings::VRStereo || !GameplayActive() || !hostEligible)\n\t\t\t\treturn false;\n\t\t\treturn Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;\n\t\t}\n''',
)

replace_once(
    "src/vr_stereo.cpp",
    "\t\t\tVertexShaderSerial.store(0, std::memory_order_release);\n",
    "\t\t\tVertexShaderSerial.store(0, std::memory_order_release);\n\t\t\tLastHostRenderEligible = false;\n",
)

stereo = read("src/vr_stereo.cpp")
for marker in (
    "LastHostRenderEligible",
    "The left/game depth may have advanced while OpenXR asked us not to",
    "RightDepthSynchronized = false;",
):
    if marker not in stereo:
        raise RuntimeError(f"resume-depth invariant missing: {marker}")

print("render resume now requires right-depth resynchronization")
