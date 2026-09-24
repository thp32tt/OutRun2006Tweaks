from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PREFIXES = (
    "src/vr/",
    "vrhost/",
    "docs/VR_",
    "docs/automation/",
    "reverse/semantics.json",
    ".github/workflows/vr-",
)

FORBIDDEN_EXACT = {
    "VR_OPENXR.md",
    "AGENTS.md",
    "src/vr_shared.hpp",
    "tools/Build-OutRunPCFast.ps1",
    "tools/Collect-OutRunVRLogs.cmd",
    "tools/Collect-OutRunVRLogs.ps1",
    "tools/OutRunVR-Backend-Selector.cmd",
    "tools/OutRunVR-Backend-Selector.ps1",
    "tools/OutRunVR-TestProfiles.ps1",
    "tools/RUN_DX9EX_TEST.cmd",
    "tools/Run-DX9ExFocusTest.ps1",
    "tools/Run-OutRunVRTest.cmd",
    "tools/Run-OutRunVRTest.ps1",
    "tools/Select-OutRunVRBackend.cmd",
    "tools/Select-OutRunVRBackend.ps1",
    "tools/Test-OutRunVRTestPolicy.ps1",
    "tools/Test-VRAutodevCoordination.ps1",
    "tools/Test-VRRegressionKnowledge.ps1",
}

TEXT_CONTRACTS = {
    "CMakeLists.txt": (
        "src/vr/",
        "vrhost/",
        "OUTRUN_VR_",
        "OpenXR",
        "D3D9Ex",
    ),
    "cmake.toml": (
        "src/vr/",
        "vrhost/",
        "OUTRUN_VR_",
        "OpenXR",
        "D3D9Ex",
    ),
    "OutRun2006Tweaks.ini": (
        "[VR]",
        "PreferD3D9Ex",
        "OpenXR",
        "DirectGpuOnly",
    ),
}

violations = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(".git/"):
        continue
    if rel in FORBIDDEN_EXACT or any(rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        violations.append(f"forbidden VR path: {rel}")

for rel, tokens in TEXT_CONTRACTS.items():
    path = ROOT / rel
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in tokens:
        if token in text:
            violations.append(f"forbidden VR build/runtime token in {rel}: {token}")

if violations:
    raise SystemExit("STANDALONE FFB SCOPE FAILED\n" + "\n".join(violations))

print("OK: standalone FFB branch contains no VR source/build/runtime paths")
