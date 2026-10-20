#!/usr/bin/env python3
"""DX9Ex default release contract: R26+HUD; R84 explicit A/B only.

Legacy filename is kept because the exact-SHA workflows invoke it. This is a
source/policy gate, not Windows compile, Quest3 HMD or FPS validation.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "cmake": "CMakeLists.txt",
    "toml": "cmake.toml",
    "ci": ".github/workflows/vr-dx9ex-active.yml",
    "launch": "tools/START_DX9EX_TEST.cmd",
    "selector": "tools/Select-OutRunVRBackend.ps1",
    "gui": "tools/OutRunVR-Slot-Selector.ps1",
    "pc": "tools/Build-OutRunPCFast.ps1",
    "pcworkflow": ".github/workflows/vr-pc-fast-build.yml",
    "openxr": ".github/workflows/vr-openxr.yml",
    "matrix": ".github/workflows/vr-unified-backends.yml",
    "impact": ".github/workflows/dx9ex-fullsource-impact-review.yml",
    "inspector": ".github/workflows/outrun-exe-hud-inspector.yml",
    "queue": "docs/VR_WORK_QUEUE.json",
    "state": "docs/VR_AUTODEV_STATE.json",
    "agents": "AGENTS.md",
}
SPLITS = ("R33_R32", "R32_R31", "R31_R30", "R30_R29")
R26 = "ACTIVE_R26_R43_R44"
R84 = "R84_SPLIT_R33_R32_R31_R30_R29"


def check(data):
    for key in ("cmake", "toml"):
        src = data[key]
        assert "set(OUTRUN_VR_R26_HUD_DEFAULT ON)" in src, key
        assert "OUTRUN_VR_R26_HUD_DEFAULT})" in src, key
        assert "set(OUTRUN_VR_R84_MAIN_DEFAULT ON)" in src, key
        assert "if(OUTRUN_VR_SAFE_DRAW_COMPARE OR OUTRUN_VR_R26_HUD_COMPARE OR" in src, key
        assert "set(OUTRUN_VR_R84_MAIN_DEFAULT OFF)" in src, key
        assert "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp" in src, key
        for suffix in SPLITS:
            assert "OUTRUN_VR_REFACTOR_SPLIT_" + suffix in src, key
            assert "OUTRUN_VR_R84_MAIN_DEFAULT})" in src, key
    for opt in ("OUTRUN_VR_R26_HUD_COMPARE",) + tuple("OUTRUN_VR_REFACTOR_SPLIT_" + s for s in SPLITS):
        m = re.compile(r"^option\(" + opt + r"[^\n]*$", re.M)
        a = m.search(data["cmake"])
        b = m.search(data["toml"])
        assert a and b and a.group(0) == b.group(0), ("cmake/cmkr drift", opt)

    ci = data["ci"]
    assert re.search(r'cmake -S \. -B build-game -G "Visual Studio 17 2022" -A Win32\s*$', ci, re.M)
    assert "OUTRUN_VR_R26_HUD_COMPARE:BOOL=ON" in ci
    assert "Configure Win32 R84 explicit independent comparison" in ci
    assert 'cmake -S . -B build-full-chain -G "Visual Studio 17 2022" -A Win32 -DOUTRUN_VR_R26_HUD_COMPARE=OFF' in ci
    assert "Set-Content stage-r84-chain/MAINLINE_BUILD_MODE.txt 'R84_EXPLICIT_COMPARISON'" in ci
    assert "Copy-Item payload/game/dinput8.dll (Join-Path $backend 'dinput8.dll')" in ci
    assert "Copy-Item payload/r84/dinput8.dll (Join-Path $r84 'dinput8.dll')" in ci
    assert "Copy-Item payload/game/dinput8.dll (Join-Path $r26 'dinput8.dll')" in ci
    assert "DefaultBuildMode = 'R26_HUD_DEFAULT_CMAKE_OPTIONS'" in ci
    assert "FallbackRendererSlot = 'R84_TEST'" in ci
    assert "CURRENT_FOCUS installed a non-R26+HUD renderer" in ci
    assert "R26+HUD main restore did not install the default R26+HUD DLL" in ci
    assert "verify_vr_dx9ex_launch_paths.py" in ci
    assert "verify_dx9ex_r84_mainline.py" in ci

    selector = data["selector"]
    assert "$defaultVariant = switch ($Backend)" in selector and '"d3d9"      { "CURRENT_FOCUS" }' in selector
    assert "if ($isPcFastPackage)" in selector
    assert "'ACTIVE_R26_R43_R44'" in selector and "'R84_SPLIT_R33_R32_R31_R30_R29'" in selector
    assert "R26HUD-PC-FAST-v3-EXACT-SHA" in selector
    assert "PC Fast game DLL SHA256 mismatch" in selector
    assert "$rendererCmakeFlags -notmatch 'OUTRUN_VR_R26_HUD_COMPARE=ON'" in selector
    assert "$rendererCmakeFlags -notmatch 'OUTRUN_VR_REFACTOR_SPLIT_R30_R29=ON'" in selector
    assert "R26+HUD" in data["launch"] and "CURRENT_FOCUS" in data["launch"]
    assert "Title='MAIN R26+HUD" in data["gui"]
    assert "Title='R84 TEST" in data["gui"]

    assert "ref: \${{ github.sha }}" in data["pcworkflow"]
    assert "-ExpectedSha $expectedSha" in data["pcworkflow"]
    for marker in ("PC Fast WRONG CHECKOUT", "PC FAST SOURCE GRAPH VERIFIED",
                   "PC FAST COMPILED R26 DLL SHA256", "GAME_DLL_SHA256.txt",
                   "R26HUD-PC-FAST-v3-EXACT-SHA", "RendererSourceOwner",
                   "OUTRUN_VR_REFACTOR_SPLIT_R30_R29=OFF"):
        assert marker in data["pc"], marker

    assert 'cmake -S . -B build-vr-game -G "Visual Studio 17 2022" -A Win32 -DOUTRUN_VR_R26_HUD_COMPARE=OFF' in data["openxr"]
    assert 'variant: P3_R84_MAIN' in data["matrix"]
    assert 'flags: "-DOUTRUN_VR_R26_HUD_COMPARE=OFF"' in data["matrix"]
    for key in ("impact", "inspector"):
        assert "'OUTRUN_VR_R26_HUD_COMPARE:BOOL=ON'" in data[key], key
        for suffix in SPLITS:
            assert "'OUTRUN_VR_REFACTOR_SPLIT_" + suffix + ":BOOL=OFF'" in data[key], key
    assert "Set-Content stage/VARIANT_ID.txt 'ACTIVE_R26_R43_R44'" in data["inspector"]
    for key in ("queue", "state"):
        policy = json.loads(data[key])["policy"]
        assert policy["dx9exR26HudMainline"]["mainRenderer"] == "R26_WORLD_R30_HUD_SKYGLOW", key
        assert policy["dx9exR26HudMainline"]["testBuild"] == "DX9EX_ACTIVE_CURRENT_FOCUS_R26_HUD", key
        assert policy["dx9exR26HudMainline"]["r84"] == "EXPLICIT_R84_TEST_ONLY", key
    assert "R26+HUD IS DX9EX DEFAULT" in data["agents"]


def main():
    originals = {key: (ROOT / path).read_text(encoding="utf-8-sig") for key,path in PATHS.items()}
    check(originals)
    mutations = [
        ("cmake", "set(OUTRUN_VR_R26_HUD_DEFAULT ON)", "set(OUTRUN_VR_R26_HUD_DEFAULT OFF)"),
        ("toml", "set(OUTRUN_VR_R26_HUD_DEFAULT ON)", "set(OUTRUN_VR_R26_HUD_DEFAULT OFF)"),
        ("ci", "Copy-Item payload/game/dinput8.dll (Join-Path $backend 'dinput8.dll')",
         "Copy-Item payload/r84/dinput8.dll (Join-Path $backend 'dinput8.dll')"),
        ("ci", "DefaultBuildMode = 'R26_HUD_DEFAULT_CMAKE_OPTIONS'", "DefaultBuildMode = 'R84_DEFAULT_CMAKE_OPTIONS'"),
        ("ci", "FallbackRendererSlot = 'R84_TEST'", "FallbackRendererSlot = 'R26_SAFE'"),
        ("selector", "R26HUD-PC-FAST-v3-EXACT-SHA", "UNVERIFIED"),
        ("gui", "Title='MAIN R26+HUD", "Title='MAIN R84"),
        ("pcworkflow", "ref: \${{ github.sha }}", "ref: vr-d3d9ex-focus"),
        ("pc", "PC FAST SOURCE GRAPH VERIFIED", "UNTESTED"),
        ("inspector", "'OUTRUN_VR_R26_HUD_COMPARE:BOOL=ON'", "'OUTRUN_VR_R26_HUD_COMPARE:BOOL=OFF'"),
        ("queue", '"mainRenderer": "R26_WORLD_R30_HUD_SKYGLOW"', '"mainRenderer": "R84"'),
    ]
    for key,old,new in mutations:
        assert old in originals[key], ("missing negative control", key, old)
        d = dict(originals)
        d[key] = d[key].replace(old,new,1)
        try:
            check(d)
        except (AssertionError, ValueError, KeyError):
            pass
        else:
            raise AssertionError("negative control survived " + key + " " + old)
    print("PASS R26+HUD default + R84 explicit A/B, PC Fast exact DLL owner, 11 destructive controls; HMD UNTESTED")

if __name__ == "__main__":
    main()
