#!/usr/bin/env python3
"""Static feature bundle contract; runtime is deliberately not inferred."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/vr-r84-feature-00591.yml"
FEATURE = ROOT / "docs/automation/runs/CONVERSION-DX9EX-00591.json"

def verify(text: str) -> None:
    jobs = {
        "r84-local": (),
        "r84-win32": ("r84-local",),
        "r84-host": ("r84-win32",),
        "r84-baseline-game": ("r84-win32",),
        "r84-bundle": ("r84-win32", "r84-host", "r84-baseline-game"),
    }
    headers = list(re.finditer(r"^  (r84-[a-z-]+):\s*$", text, re.M))
    blocks = {
        m.group(1): text[m.end():headers[i + 1].start()
                         if i + 1 < len(headers) else len(text)]
        for i, m in enumerate(headers)
    }
    assert set(blocks) == set(jobs), "feature job inventory drift"
    for name, requirements in jobs.items():
        block = blocks[name]
        if requirements:
            if len(requirements) > 1:
                assert "needs: [" + ", ".join(requirements) + "]" in block, name
            else:
                assert "needs: " + requirements[0] in block, name
    for source in ("stereo_renderer_r29.cpp", "stereo_renderer_r30.cpp",
                   "stereo_renderer_r31.cpp", "stereo_renderer_r32.cpp",
                   "stereo_renderer_r33.cpp"):
        assert (ROOT / "src/vr/d3d9" / source).exists(), source
    for flag in (
        "-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=ON",
        "-DOUTRUN_VR_REFACTOR_SPLIT_R32_R31=ON",
        "-DOUTRUN_VR_REFACTOR_SPLIT_R31_R30=ON",
        "-DOUTRUN_VR_REFACTOR_SPLIT_R30_R29=ON",
    ):
        assert flag in blocks["r84-win32"], flag
        assert flag in blocks["r84-bundle"], "manifest missing: " + flag
    for payload in ("r84-full-chain", "r84-host-x64", "r84-baseline-game"):
        assert "name: " + payload in text, payload
    for path in (
        "backends/d3d9/dinput8.dll",
        "backends/d3d9/outrun-vr-host.exe",
        "reference/dinput8-R26-baseline.dll",
        "FEATURE_MANIFEST.json",
        "SOURCE_SHA.txt", "SHA256SUMS.txt",
        "Collect-OutRunVRLogs.ps1", "OutRunVR-Slot-Selector.cmd",
    ):
        assert path in blocks["r84-bundle"], path
    for term in (
        "RuntimeValidation = 'UNTESTED'",
        "SourceSha = $env:GITHUB_SHA",
        "Assert-PeMachine",
        "0x014c", "0x8664", "mixed SHA",
        "Get-FileHash", "Compress-Archive",
        "Expand-Archive", "if-no-files-found: error",
    ):
        assert term in blocks["r84-bundle"], term
    assert "python3 tools/verify_vr_r29_owner_api_seam.py" in blocks["r84-local"]
    assert "python3 tools/verify_vr_r30_support_api_seam.py" in blocks["r84-local"]
    assert "python3 tools/verify_vr_r84_feature_bundle.py" in blocks["r84-local"]
    assert '"runtime_validation": "UNTESTED"' in FEATURE.read_text(encoding="utf-8")
    assert "$" + "{{ github.sha }}" in blocks["r84-bundle"]

def main():
    original = WORKFLOW.read_text(encoding="utf-8")
    verify(original)
    for missing in (
        "Assert-PeMachine", "Collect-OutRunVRLogs.ps1",
        "-DOUTRUN_VR_REFACTOR_SPLIT_R30_R29=ON",
        "RuntimeValidation = 'UNTESTED'", "r84-host-x64",
    ):
        altered = original.replace(missing, "NEGATIVE_MUTATION", 1)
        assert altered != original, missing
        try:
            verify(altered)
        except AssertionError:
            pass
        else:
            raise AssertionError("incomplete bundle not detected: " + missing)
    print("R84 bundle contract PASS (5 negative mutations; Win32/HMD untested)")

if __name__ == "__main__":
    main()
