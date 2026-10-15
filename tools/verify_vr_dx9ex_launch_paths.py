#!/usr/bin/env python3
"""Verify the R84-default DX9Ex release path and the protected R26 rollback.

Source mutation tests run without Quest3/HMD; they protect installer routing,
exact-source identity, portable performance invariants, and visible errors.
CI compile/link and HMD correctness remain separate acceptance gates.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def check(src):
    selector, gui, runner, workflow = src
    failures = []
    expected = [
        (selector, r'\$src\s*=\s*if\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and\s*\(\$variant\s*-eq\s*"R26_SAFE"\s*-or\s*\$variant\s*-eq\s*"R84_TEST"\)\)', "R26/R84 optional variants require dedicated payloads"),
        (selector, r'\}\s*elseif\s*\(\$Backend\s*-eq\s*"d3d9"\)\s*\{\s*\$backendPayload', "all ordinary DX9Ex profiles must use main R84 payload"),
        (selector, r'if\s*\(-not\s*\(Test-Path\s+\$slotPayload\)\)\s*\{\s*throw', "absent R26 fallback must fail closed"),
        (selector, r'\$expectedVariant\s*=\s*if\s*\(\$variant\s*-eq\s*"R26_SAFE"\)\s*\{\s*"ACTIVE_R26_R43_R44"\s*\}\s*else\s*\{\s*"R84_SPLIT_R33_R32_R31_R30_R29"', "default and fallback build variants must be distinct"),
        (selector, r'\$sourceSha\s*-ne\s*\(Get-Content\s+\$baselineShaFile', "all variants must use the same source SHA"),
        (selector, r'\$enforceReleaseIdentity\s*=\s*\(Test-Path\s+\$packageInputsFile\)', "released package must enforce main/fallback identity"),
        (selector, r'\$sourceSha\s*-ne\s*\[string\]\$buildInputs\.IntegrationSha', "released variant must match the build manifest exact SHA"),
        (selector, r'\[string\]\$buildInputs\.VariantId\s*-ne\s*"R84_SPLIT_R33_R32_R31_R30_R29"', "released default must be compiled R84"),
        (selector, r'\$rendererCmakeFlags\s*-notmatch\s*\x27OUTRUN_VR_REFACTOR_SPLIT_R30_R29=ON\x27', "R84 must be the fully split owner"),
        (selector, r'\$rendererCmakeFlags\s*-notmatch\s*\x27OUTRUN_VR_R26_HUD_COMPARE=ON\x27', "R26 fallback must retain its shipped HUD owner"),
        (selector, r'DX9Ex selected host is not the matching exact-SHA host', "different OpenXR host hashes must fail closed"),
        (gui, r"'CURRENT_FOCUS'=\[ordered\]@\{Backend='d3d9'.*?Title='MAIN R84", "default GUI entry must identify R84"),
        (gui, r"'R26_SAFE'=\[ordered\]@\{Backend='d3d9'", "explicit R26 safe rollback must be visible"),
        (gui, r"\$effectivePath=if\(\$cfg\.Backend -eq 'd3d9' -and \(\$slot -eq 'R84_TEST' -or \$slot -eq 'R26_SAFE'\)\)", "GUI dedicated R26 and R84 payload gating"),
        (gui, r"\}\s*elseif\(\$cfg\.Backend -eq 'd3d9'\)\s*\{.*?\$backendPath", "other GUI DX9Ex entries use main payload"),
        (gui, r'(?m)^[ \t]*&[ \t]+\$selector -Backend \$cfg\.Backend -TestProfile \$cfg\.Profile -VariantId \$slot[ \t]*$', "GUI installer propagates errors"),
        (gui, r'\$session\.SessionId -eq \$previousSessionId', "stale sessions are rejected"),
        (gui, r'\$session\.VariantId -ne \$slot', "selected variant identity must be checked"),
        (gui, r'\$quotedRunner\s*=\s*\x27"\x27 \+ \$runner \+ \x27"\x27', "quoted launcher path"),
        (gui, r"Start-Process -FilePath \(Join-Path \$PSHOME 'powershell.exe'\) -ArgumentList \$launchArgs", "visible runner must be started"),
        (runner, r"trap\s*\{.*?\$errorFile\s*=\s*Join-Path\s+\$root\s+'OUTRUNVR_LAUNCH_ERROR\.txt'.*?Set-Content\s+-LiteralPath\s+\$errorFile.*?MessageBox\]::Show", "early failures must be visible and logged"),
        (workflow, r"Copy-Item payload/r84/dinput8\.dll \(Join-Path \$backend 'dinput8\.dll'\)", "main package must contain actual R84 DLL"),
        (workflow, r"Copy-Item payload/game/dinput8\.dll \(Join-Path \$r26 'dinput8\.dll'\)", "fallback package must contain protected R26 DLL"),
        (workflow, r"FallbackRendererSlot = 'R26_SAFE'", "package manifest must advertise rollback"),
        (workflow, r"CURRENT_FOCUS installed a non-R84 renderer", "CI must compare default installed renderer variant"),
        (workflow, r"R26_SAFE did not install protected R26\+HUD DLL", "CI must verify rollback DLL bytes"),
        (workflow, r"R84 main restore did not install the refactored R29-R33 DLL", "CI must verify rollback reversal"),
        (workflow, r'verify_vr_dx9ex_launch_paths\.py', "Active CI must run this verifier"),
    ]
    for value, pattern, label in expected:
        if not re.search(pattern, value, re.S):
            failures.append(label)
    if re.search(r'\}\s*elseif\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and', selector):
        failures.append("unsafe restricted canonical fallback")
    if re.search(r'Start-Process powershell -Wait -PassThru -WindowStyle Hidden -ArgumentList \$args', gui):
        failures.append("unquoted/hidden PowerShell launch")
    return failures


def perf_check(root):
    """Protect real code parity, not claims that VR FPS or optics are proven."""
    safe = (root / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8-sig")
    r30 = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
    r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8-sig")
    r33 = (root / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8-sig")
    checks = [
        ("R26 lazy shadow", "R30ShadowBytes::LazyUninitializedBuffer bytes;" in safe),
        ("R84 lazy shadow", "R30ShadowBytes::LazyUninitializedBuffer bytes;" in r30),
        ("R26 source scratch", "WriteOnlyByteScratch source;" in safe),
        ("R84 source scratch", "WriteOnlyByteScratch source;" in r30),
        ("R26 index scratch", "WriteOnlyByteScratch indexSource;" in safe),
        ("R84 index scratch", "WriteOnlyByteScratch indexSource;" in r30),
        ("R26 per-eye scratch", "WriteOnlyByteScratch left;" in safe and "WriteOnlyByteScratch right;" in safe),
        ("R84 per-eye scratch", "WriteOnlyByteScratch left;" in r30 and "WriteOnlyByteScratch right;" in r30),
        ("R84 shadow generation", "R30TryIncrementalShadowCopy" in r30),
        ("R84 bounded indexedUP", "R30IndexedUpBounds::" in r30),
        ("R84 indexed sparse visit", "R30SeedTouchedXyzrhwVertices" in r30),
        ("R84 stereo world", "R30TransformWorldAffineStereo" in r30),
        ("R84 R29 perf cache", "R29" in r29 and "cache" in r29.lower()),
        ("R84 sole dispatcher", "R33" in r33 and "R30" in r33),
    ]
    missing = [name for name, ok in checks if not ok]
    return missing


if __name__ == "__main__":
    files = [
        ROOT / "tools/Select-OutRunVRBackend.ps1",
        ROOT / "tools/OutRunVR-Slot-Selector.ps1",
        ROOT / "tools/Run-OutRunVRTest.ps1",
        ROOT / ".github/workflows/vr-dx9ex-active.yml",
    ]
    src = tuple(p.read_text(encoding="utf-8-sig") for p in files)
    problems = check(src)
    assert not problems, "; ".join(problems)
    mutations = [
        (0, '} elseif ($Backend -eq "d3d9") {', '} elseif ($Backend -eq "d3d9" -and $variant -eq "CURRENT_FOCUS") {'),
        (0, '$variant -eq "R26_SAFE" -or $variant -eq "R84_TEST"', '$variant -eq "R84_TEST"'),
        (0, 'if (-not (Test-Path $slotPayload)) { throw', 'if (-not (Test-Path $slotPayload)) { Write-Warning'),
        (0, '"ACTIVE_R26_R43_R44"', '"NONEXISTENT"'),
        (0, '    } else {\n        "R84_SPLIT_R33_R32_R31_R30_R29"\n    }', '    } else {\n        "NONEXISTENT"\n    }'),
        (0, '$sourceSha -ne (Get-Content $baselineShaFile', '$sourceSha -eq (Get-Content $baselineShaFile'),
        (0, "DX9Ex selected host is not the matching exact-SHA host.", "DX9Ex selected host unverified"),
        (1, "$effectivePath=if($cfg.Backend -eq 'd3d9' -and ($slot -eq 'R84_TEST' -or $slot -eq 'R26_SAFE'))", "$effectivePath=if($slot -eq 'CURRENT_FOCUS')"),
        (1, "'R26_SAFE'=[ordered]", "'NO_ROLLBACK'=[ordered]"),
        (1, '$quotedRunner = \'"\' + $runner + \'"\'', '$quotedRunner = $runner'),
        (1, '    & $selector -Backend $cfg.Backend', '    # & $selector -Backend $cfg.Backend'),
        (1, '$session.SessionId -eq $previousSessionId', '$session.SessionId -ne $previousSessionId'),
        (1, '$session.VariantId -ne $slot', '$session.VariantId -eq $slot'),
        (2, "OUTRUNVR_LAUNCH_ERROR.txt", "SILENT_FAILURE"),
        (3, "Copy-Item payload/r84/dinput8.dll (Join-Path $backend 'dinput8.dll')", "Copy-Item payload/game/dinput8.dll (Join-Path $backend 'dinput8.dll')"),
        (3, "Copy-Item payload/game/dinput8.dll (Join-Path $r26 'dinput8.dll')", "Copy-Item payload/r84/dinput8.dll (Join-Path $r26 'dinput8.dll')"),
        (3, "FallbackRendererSlot = 'R26_SAFE'", "FallbackRendererSlot = 'NONE'"),
    ]
    for index, original, mutant in mutations:
        assert original in src[index], f"mutation fixture missing {original}"
        changed = list(src)
        changed[index] = changed[index].replace(original, mutant, 1)
        assert check(changed), f"mutation escaped: {original}"
    assert not perf_check(ROOT), "; ".join(perf_check(ROOT))
    print(f"DX9Ex R84 MAIN + R26 rollback PASS ({len(mutations)} negative mutations); perf-source evidence PASS; HMD UNTESTED")
