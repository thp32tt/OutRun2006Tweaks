#!/usr/bin/env python3
"""Guard the shipped DX9Ex launch path against stale slots and silent failures.

Source-level mutation tests are deliberately independent from Quest3/HMD and
do not claim that launching a user's game succeeds on a CI machine.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def check(src):
    selector, gui, runner, workflow = src
    failures = []
    expected = [
        (selector, r'\}\s*elseif\s*\(\$Backend\s*-eq\s*"d3d9"\)\s*\{\s*\$backendPayload', "every non-R84 DX9Ex slot must use the canonical payload"),
        (selector, r'\$src\s*=\s*if\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and\s*\$variant\s*-eq\s*"R84_TEST"\)', "explicit opt-in R84 selection must be present"),
        (selector, r'if\s*\(-not\s*\(Test-Path\s+\$slotPayload\)\)\s*\{\s*throw', "missing R84 payload must fail closed"),
        (selector, r'\$rendererBuildVariant\s*-ne\s*"R84_SPLIT_R33_R32_R31_R30_R29"', "R84 variant must be tied to independently compiled owner"),
        (selector, r'\$sourceSha\s*-ne\s*\(Get-Content\s+\$baselineShaFile', "R84 must reject a different source SHA"),
        (selector, r'R84_TEST host is not the matching exact-SHA host', "R84 must reject a mismatched host"),
        (gui, r'\}\s*elseif\(\$cfg\.Backend -eq \'d3d9\'\)\s*\{.*?\$backendPath', "non-R84 GUI buttons must inspect canonical payload"),
        (gui, r"\$effectivePath=if\(\$cfg\.Backend -eq 'd3d9' -and \$slot -eq 'R84_TEST'\)\s*\{\s*\$slotPath", "R84 GUI button must inspect its dedicated payload"),
        (gui, r"'R84_TEST'=\[ordered\]@\{Backend='d3d9'", "R84 opt-in GUI entry must remain available"),
        (gui, r'(?m)^[ \t]*&[ \t]+\$selector -Backend \$cfg\.Backend -TestProfile \$cfg\.Profile -VariantId \$slot[ \t]*$', "slot preparation must preserve paths with spaces and propagate failures"),
        (gui, r'\$session\.SessionId -eq \$previousSessionId', "selector must reject a reused session ID"),
        (gui, r'\$session\.Backend -ne \$cfg\.Backend', "new manifest backend must match the selected slot"),
        (gui, r'\$session\.TestProfile -ne \$cfg\.Profile', "new manifest profile must match the selected slot"),
        (gui, r'\$session\.VariantId -ne \$slot', "new manifest variant must match the selected slot"),
        (gui, r'\$active\.backend -ne \$cfg\.Backend', "active backend marker must agree with the manifest"),
        (gui, r'\$quotedRunner\s*=\s*\x27"\x27 \+ \$runner \+ \x27"\x27', "PowerShell -File value must be explicitly quoted"),
        (gui, r'Start-Process -FilePath \(Join-Path \$PSHOME \'powershell.exe\'\) -ArgumentList \$launchArgs', "quoted runner must be launched, not the unquoted array"),
        (runner, r"trap\s*\{.*?\$errorFile\s*=\s*Join-Path\s+\$root\s+'OUTRUNVR_LAUNCH_ERROR\.txt'.*?Set-Content\s+-LiteralPath\s+\$errorFile.*?MessageBox\]::Show", "early launcher failures need durable error-path creation, file write and visible dialog"),
        (workflow, r'verify_vr_dx9ex_launch_paths\.py', "negative regression verifier must run in the Active Gate"),
    ]
    for value, pattern, label in expected:
        if not re.search(pattern, value, re.S):
            failures.append(label)
    if re.search(r'\}\s*elseif\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and', selector):
        failures.append("CURRENT_FOCUS-only fallback leaves other protected slots stale")
    if re.search(r'Start-Process powershell -Wait -PassThru -WindowStyle Hidden -ArgumentList \$args', gui):
        failures.append("unquoted and silent hidden backend selector remains")
    return failures

if __name__ == "__main__":
    files = [
        ROOT / "tools/Select-OutRunVRBackend.ps1",
        ROOT / "tools/OutRunVR-Slot-Selector.ps1",
        ROOT / "tools/Run-OutRunVRTest.ps1",
        ROOT / ".github/workflows/vr-dx9ex-active.yml",
    ]
    src = tuple(p.read_text(encoding="utf-8-sig") for p in files)
    assert not check(src), "; ".join(check(src))
    mutations = [
        (0, '} elseif ($Backend -eq "d3d9") {', '} elseif ($Backend -eq "d3d9" -and $variant -eq "CURRENT_FOCUS") {'),
        (0, 'R84_TEST payload missing: $slotPayload', 'R84 payload missing: $slotPayload'),
        (0, '$rendererBuildVariant -ne "R84_SPLIT_R33_R32_R31_R30_R29"', '$rendererBuildVariant -ne "R26"'),
        (0, '$sourceSha -ne (Get-Content $baselineShaFile', '$sourceSha -eq (Get-Content $baselineShaFile'),
        (1, '$quotedRunner = \'"\' + $runner + \'"\'', '$quotedRunner = $runner'),
        (1, '    & $selector -Backend $cfg.Backend', '    # & $selector -Backend $cfg.Backend'),
        (1, "} elseif($cfg.Backend -eq 'd3d9')", "} elseif($slot -eq 'CURRENT_FOCUS')"),
        (1, "$effectivePath=if($cfg.Backend -eq 'd3d9' -and $slot -eq 'R84_TEST')", "$effectivePath=if($cfg.Backend -eq 'd3d9' -and $slot -eq 'CURRENT_FOCUS')"),
        (1, '$session.SessionId -eq $previousSessionId', '$session.SessionId -ne $previousSessionId'),
        (1, '$session.Backend -ne $cfg.Backend', '$session.Backend -eq $cfg.Backend'),
        (1, '$session.TestProfile -ne $cfg.Profile', '$session.TestProfile -eq $cfg.Profile'),
        (1, '$session.VariantId -ne $slot', '$session.VariantId -eq $slot'),
        (1, '$active.backend -ne $cfg.Backend', '$active.backend -eq $cfg.Backend'),
        (2, "OUTRUNVR_LAUNCH_ERROR.txt", "SILENT_FAILURE"),
    ]
    for index, original, mutant in mutations:
        assert original in src[index], f"mutation fixture missing {original}"
        changed = list(src)
        changed[index] = changed[index].replace(original, mutant, 1)
        assert check(changed), f"regression mutation escaped: {original}"
    print(f"DX9Ex launch paths PASS (protected R26 canonical, R84 opt-in fail-close, quoted invocation, visible error, {len(mutations)} destructive mutations)")
