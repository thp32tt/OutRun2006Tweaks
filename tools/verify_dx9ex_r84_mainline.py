#!/usr/bin/env python3
"""Fail-closed DX9Ex R84 *mainline* ownership contract.

R84 is the normal option-free source/configure/build/test path. An explicitly
requested R26/C1/C2 variant is diagnostic/rollback only. This proves selected
source/build profiles and CI packaging, NOT Quest3 optical/runtime correctness.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
TOML = ROOT / "cmake.toml"
ACTIVE = ROOT / ".github/workflows/vr-dx9ex-active.yml"
LAUNCH = ROOT / "tools/START_DX9EX_TEST.cmd"
SELECT = ROOT / "tools/Select-OutRunVRBackend.ps1"
OPENXR = ROOT / ".github/workflows/vr-openxr.yml"
MATRIX = ROOT / ".github/workflows/vr-unified-backends.yml"
IMPACT = ROOT / ".github/workflows/dx9ex-fullsource-impact-review.yml"
HUD_INSPECTOR = ROOT / ".github/workflows/outrun-exe-hud-inspector.yml"

_SPLITS = (
    "OUTRUN_VR_REFACTOR_SPLIT_R33_R32",
    "OUTRUN_VR_REFACTOR_SPLIT_R32_R31",
    "OUTRUN_VR_REFACTOR_SPLIT_R31_R30",
    "OUTRUN_VR_REFACTOR_SPLIT_R30_R29",
)
_COMPARISONS = (
    "OUTRUN_VR_SAFE_DRAW_COMPARE",
    "OUTRUN_VR_R26_HUD_COMPARE",
    "OUTRUN_VR_C1_COMPARE",
    "OUTRUN_VR_C2_COMPARE",
)


def check(cmake: str, toml: str, ci: str, launcher: str, select: str,
          openxr: str, manual: str, impact: str, hud_inspector: str) -> None:
    # cmkr is a source, CMakeLists the generated build owner. A build without
    # overrides must compile all five independent R29-R33 game TUs.
    for source in (cmake, toml):
        assert re.search(
            r'option\(OUTRUN_VR_SAFE_DRAW_COMPARE\s+"[^"]+"\s+OFF\)',
            source), "historical R26 safe owner cannot be default"
        assert re.search(
            r'set\(OUTRUN_VR_R84_MAIN_DEFAULT\s+ON\)', source), (
                "R84 must be the option-free mainline")
        defaults = source.split(
            "set(OUTRUN_VR_R84_MAIN_DEFAULT ON)", 1)[1].split(
            "option(OUTRUN_VR_REFACTOR_SPLIT_R33_R32", 1)[0]
        for compare in _COMPARISONS:
            assert compare in defaults, "explicit fallback not isolated: " + compare
        assert "set(OUTRUN_VR_R84_MAIN_DEFAULT OFF)" in defaults, (
            "comparison mode must disable all four owners on fresh configure")
        for split in _SPLITS:
            assert re.search(
                rf'option\({split}\s+"[^"]+"\s+\$\{{OUTRUN_VR_R84_MAIN_DEFAULT\}}\)',
                source), "R84 split default missing: " + split
            assert f"add_compile_definitions({split}=1)" in source
        for tu in ("r29", "r30", "r31", "r32"):
            name = f"src/vr/d3d9/stereo_renderer_{tu}.cpp"
            # Each independently compiled owner is emitted only by a gated
            # FALSE override. The main R33 dispatcher is final owner.
            assert re.search(
                rf'{re.escape(name)}\s+PROPERTIES HEADER_FILE_ONLY FALSE\)',
                source), "R84 independent compile guard lost: " + tu
        assert "src/vr/d3d9/stereo_renderer_r33.cpp" in source
        assert 'option(OUTRUN_VR_R26_HUD_COMPARE ' in source
        assert "OUTRUN_VR_R84_MAIN_DEFAULT" in source
    # cmake.toml regeneration must not silently restore old default flags.
    for prefix in ("OUTRUN_VR_SAFE_DRAW_COMPARE",) + _SPLITS:
        c_option = re.search(rf'^option\({prefix}[^\n]*$', cmake, re.M)
        t_option = re.search(rf'^option\({prefix}[^\n]*$', toml, re.M)
        assert c_option and t_option and c_option.group() == t_option.group(), (
            "CMakeLists and cmkr generated defaults drift: " + prefix)

    # Windows test CI MUST configure the main DLL without -D overrides.
    section = ci.split(
        "- name: Configure Win32 R84 MAIN from option-free CMake", 1)[1].split(
        "- name: Apply VC2022 dependency workarounds for full-chain gate", 1)[0]
    assert re.search(
        r'^\s+cmake -S \. -B build-full-chain -G "Visual Studio 17 2022" -A Win32\s*$',
        section, re.M), "main Windows game configure must be option-free"
    assert "R84_MAIN" not in section or "option-free" in section
    for split in _SPLITS:
        assert f"'{split}:BOOL=ON'" in section, (
            "Windows CMakeCache lacks live R84 owner assertion: " + split)
    for compare in _COMPARISONS:
        assert f"'{compare}:BOOL=OFF'" in section, (
            "Windows CMakeCache lacks disabled fallback assertion: " + compare)
    fallback = ci.split(
        "- name: Configure Win32 R26_SAFE fallback (explicit comparison)", 1)[1].split(
        "- name: Apply VC2022 dependency workarounds", 1)[0]
    assert "-DOUTRUN_VR_R26_HUD_COMPARE=ON" in fallback
    for split in _SPLITS:
        assert f"'{split}:BOOL=OFF'" in fallback

    assert "needs: [host, game, full-chain-compile]" in ci
    assert "name: dx9ex-r84-independent-full-chain-game" in ci
    assert "name: dx9ex-active-game" in ci
    assert "Copy-Item payload/r84/dinput8.dll (Join-Path $backend 'dinput8.dll')" in ci
    assert "Copy-Item payload/game/dinput8.dll (Join-Path $r26 'dinput8.dll')" in ci
    assert "Set-Content stage-r84-chain/MAINLINE_BUILD_MODE.txt 'R84_DEFAULT_CMAKE_OPTIONS'" in ci
    assert "Copy-Item payload/r84/MAINLINE_BUILD_MODE.txt (Join-Path $backend 'MAINLINE_BUILD_MODE.txt')" in ci
    assert "DefaultBuildMode = 'R84_DEFAULT_CMAKE_OPTIONS'" in ci
    assert "R26_SAFE did not install protected R26+HUD DLL" in ci
    assert "R84 main restore did not install the refactored R29-R33 DLL" in ci
    assert "run: python tools/verify_dx9ex_r84_mainline.py" in ci
    assert "VariantId = 'R84_SPLIT_R33_R32_R31_R30_R29'" in ci

    assert "CURRENT_FOCUS" in launcher and "R84" in launcher
    assert re.search(
        r'\$src = if \(\$Backend -eq "d3d9" -and \(\$variant -eq "R26_SAFE" -or \$variant -eq "R84_TEST"\)\)',
        select), "only explicit fallback may route away from R84 main"
    assert 'elseif ($Backend -eq "d3d9")' in select and "$backendPayload" in select
    assert "R84_SPLIT_R33_R32_R31_R30_R29" in select
    assert "ACTIVE_R26_R43_R44" in select

    # Remaining build/test entrypoints must agree: no R26 production graph
    # behind an apparently option-free cmake invocation.
    assert "cmake -S . -B build-vr-game -G" in openxr
    assert "- name: Verify regenerated R84 MAIN independent game graph" in openxr
    assert "- name: Verify Win32 R84 MAIN x86 binary identity" in openxr
    assert "OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=ON" in openxr
    assert "R26 fallback compiled into R84 MAIN" in openxr
    assert "VR R33 DISPATCH: final Reset/Present/DirectGPU/draw physical ownership READY" in openxr
    assert "P3_R84_MAIN" in manual and "P3_FULL_R34" not in manual
    assert re.search(r'- variant: P3_R84_MAIN\s+flags: ""', manual)
    assert "name: dx9ex-game-P3_R84_MAIN" in manual
    # All required code-review and HUD diagnostics now analyze the same R84
    # independent owner as the tested package; R26 is only an explicit control.
    impact_config = impact.split(
        "- name: Configure exact R84 MAIN game for MSVC static analysis", 1)[1].split(
        "- name: Apply same dependency compatibility fixes as DX9Ex Active", 1)[0]
    assert re.search(
        r'cmake -S \. -B build-analysis -G "Visual Studio 17 2022" -A Win32 -DCMAKE_CXX_FLAGS=/analyze\s*$',
        impact_config, re.M)
    assert "-DOUTRUN_VR_" not in impact_config
    inspector_config = hud_inspector.split(
        "- name: Configure Win32 R84 MAIN HUD Inspector DLL", 1)[1].split(
        "- name: Apply VC2022 dependency workarounds", 1)[0]
    assert re.search(
        r'cmake -S \. -B build-game -G "Visual Studio 17 2022" -A Win32\s*$',
        inspector_config, re.M)
    assert "-DOUTRUN_VR_" not in inspector_config
    for split in _SPLITS:
        assert f"'{split}:BOOL=ON'" in impact_config
        assert f"'{split}:BOOL=ON'" in inspector_config
    assert "Set-Content stage/VARIANT_ID.txt 'R84_SPLIT_R33_R32_R31_R30_R29'" in hud_inspector

    for trigger in (".github/workflows/vr-openxr.yml",
                    ".github/workflows/vr-unified-backends.yml",
                    ".github/workflows/dx9ex-fullsource-impact-review.yml",
                    ".github/workflows/outrun-exe-hud-inspector.yml",
                    "tools/verify_dx9ex_r84_mainline.py"):
        assert trigger in ci, "mainline CI misses build contract change: " + trigger


def main() -> None:
    originals = [
        CMAKE.read_text(encoding="utf-8-sig"),
        TOML.read_text(encoding="utf-8-sig"),
        ACTIVE.read_text(encoding="utf-8-sig"),
        LAUNCH.read_text(encoding="utf-8-sig"),
        SELECT.read_text(encoding="utf-8-sig"),
        OPENXR.read_text(encoding="utf-8-sig"),
        MATRIX.read_text(encoding="utf-8-sig"),
        IMPACT.read_text(encoding="utf-8-sig"),
        HUD_INSPECTOR.read_text(encoding="utf-8-sig"),
    ]
    check(*originals)
    mutations = [
        (0, 'historical stereo fallback" OFF', 'historical stereo fallback" ON'),
        (1, 'historical stereo fallback" OFF', 'historical stereo fallback" ON'),
        (0, "set(OUTRUN_VR_R84_MAIN_DEFAULT ON)", "set(OUTRUN_VR_R84_MAIN_DEFAULT OFF)"),
        (1, "set(OUTRUN_VR_R84_MAIN_DEFAULT ON)", "set(OUTRUN_VR_R84_MAIN_DEFAULT OFF)"),
        (0, 'Compile R29 separately from R30" ${OUTRUN_VR_R84_MAIN_DEFAULT}', 'Compile R29 separately from R30" OFF'),
        (2, 'cmake -S . -B build-full-chain -G "Visual Studio 17 2022" -A Win32', 'cmake -S . -B build-full-chain -G "Visual Studio 17 2022" -A Win32 -DOUTRUN_VR_R26_HUD_COMPARE=ON'),
        (2, "'OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=ON'", "'OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=OFF'"),
        (2, "Copy-Item payload/r84/dinput8.dll (Join-Path $backend 'dinput8.dll')", "Copy-Item payload/game/dinput8.dll (Join-Path $backend 'dinput8.dll')"),
        (2, "Copy-Item payload/game/dinput8.dll (Join-Path $r26 'dinput8.dll')", "Copy-Item payload/r84/dinput8.dll (Join-Path $r26 'dinput8.dll')"),
        (2, "DefaultBuildMode = 'R84_DEFAULT_CMAKE_OPTIONS'", "DefaultBuildMode = 'UNVERIFIED'"),
        (4, '$variant -eq "R26_SAFE" -or $variant -eq "R84_TEST"', '$variant -eq "R84_TEST"'),
        (5, "Verify regenerated R84 MAIN independent game graph", "Verify regenerated R26 safe production source graph"),
        (5, "OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=ON", "OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=OFF"),
        (6, 'P3_R84_MAIN', 'P3_FULL_R34'),
        (7, 'cmake -S . -B build-analysis -G "Visual Studio 17 2022" -A Win32 -DCMAKE_CXX_FLAGS=/analyze',
            'cmake -S . -B build-analysis -G "Visual Studio 17 2022" -A Win32 -DOUTRUN_VR_R26_HUD_COMPARE=ON -DCMAKE_CXX_FLAGS=/analyze'),
        (8, 'cmake -S . -B build-game -G "Visual Studio 17 2022" -A Win32\n',
            'cmake -S . -B build-game -G "Visual Studio 17 2022" -A Win32 -DOUTRUN_VR_SAFE_DRAW_COMPARE=ON\n'),
    ]
    for idx, old, new in mutations:
        assert old in originals[idx], "missing negative fixture: " + old
        altered = list(originals)
        altered[idx] = altered[idx].replace(old, new, 1)
        try:
            check(*altered)
        except (AssertionError, IndexError):
            continue
        raise AssertionError("mainline regression escaped: " + old)
    print(f"DX9Ex R84 DEFAULT MAINLINE PASS ({len(mutations)} destructive checks); "
          "R26-safe fallback explicit; Quest3/VDXR HMD UNTESTED")


if __name__ == "__main__":
    main()
