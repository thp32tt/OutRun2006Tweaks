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
        (selector, r'\$src\s*=\s*if\s*\(\$Backend\s*-eq\s*"d3d9"\)\s*\{\s*\$backendPayload', "all DX9Ex slots must use the canonical payload"),
        (gui, r'\$effectivePath=if\(\$cfg\.Backend -eq \'d3d9\'\)\s*\{\s*#.*?\s*\$backendPath', "GUI buttons must inspect canonical payload"),
        (gui, r'(?m)^[ \\t]*&[ \\t]+\\$selector -Backend \\$cfg\\.Backend -TestProfile \\$cfg\\.Profile -VariantId \\$slot[ \\t]* "slot preparation must preserve paths with spaces and propagate failures"),
        (gui, r'\\$session\\.SessionId -eq \\$previousSessionId', "selector must reject a reused session ID"),
        (gui, r'\\$session\\.Backend -ne \\$cfg\\.Backend', "new manifest backend must match the selected slot"),
        (gui, r'\\$session\\.TestProfile -ne \\$cfg\\.Profile', "new manifest profile must match the selected slot"),
        (gui, r'\\$session\\.VariantId -ne \\$slot', "new manifest variant must match the selected slot"),
        (gui, r'\\$active\\.backend -ne \\$cfg\\.Backend', "active backend marker must agree with the manifest"),
        (gui, r'\$quotedRunner\s*=\s*\x27"\x27 \+ \$runner \+ \x27"\x27', "PowerShell -File value must be explicitly quoted"),
        (gui, r'Start-Process -FilePath \(Join-Path \$PSHOME \'powershell.exe\'\) -ArgumentList \$launchArgs', "quoted runner must be launched, not the unquoted array"),
        (runner, r'trap\s*\{.*?OUTRUNVR_LAUNCH_ERROR\.txt.*?MessageBox\]::Show', "early launcher failures need a durable error and visible dialog"),
        (workflow, r'verify_vr_dx9ex_launch_paths\.py', "negative regression verifier must run in the Active Gate"),
    ]
    for value, pattern, label in expected:
        if not re.search(pattern, value, re.S):
            failures.append(label)
    if re.search(r'\$src\s*=\s*if\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and', selector):
        failures.append("CURRENT_FOCUS-only fallback leaves other slots stale")
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
        (0, '$src = if ($Backend -eq "d3d9") {', '$src = if ($Backend -eq "d3d9" -and $variant -eq "CURRENT_FOCUS") {'),
        (1, '$quotedRunner = \'"\' + $runner + \'"\'', '$quotedRunner = $runner'),
        (1, '    & $selector -Backend $cfg.Backend', '    # & $selector -Backend $cfg.Backend'),
        (1, "$effectivePath=if($cfg.Backend -eq 'd3d9')", "$effectivePath=if($slot -eq 'CURRENT_FOCUS')"),
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
    print("DX9Ex launch paths PASS (canonical slots, quoted invocation, visible error, ten destructive mutations)")
, "slot preparation must preserve paths with spaces and propagate failures"),
        (gui, r'\$quotedRunner\s*=\s*\x27"\x27 \+ \$runner \+ \x27"\x27', "PowerShell -File value must be explicitly quoted"),
        (gui, r'Start-Process -FilePath \(Join-Path \$PSHOME \'powershell.exe\'\) -ArgumentList \$launchArgs', "quoted runner must be launched, not the unquoted array"),
        (runner, r'trap\s*\{.*?OUTRUNVR_LAUNCH_ERROR\.txt.*?MessageBox\]::Show', "early launcher failures need a durable error and visible dialog"),
        (workflow, r'verify_vr_dx9ex_launch_paths\.py', "negative regression verifier must run in the Active Gate"),
    ]
    for value, pattern, label in expected:
        if not re.search(pattern, value, re.S):
            failures.append(label)
    if re.search(r'\$src\s*=\s*if\s*\(\$Backend\s*-eq\s*"d3d9"\s*-and', selector):
        failures.append("CURRENT_FOCUS-only fallback leaves other slots stale")
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
        (0, '$src = if ($Backend -eq "d3d9") {', '$src = if ($Backend -eq "d3d9" -and $variant -eq "CURRENT_FOCUS") {'),
        (1, '$quotedRunner = \'"\' + $runner + \'"\'', '$quotedRunner = $runner'),
        (1, '    & $selector -Backend $cfg.Backend', '    # & $selector -Backend $cfg.Backend'),
        (1, "$effectivePath=if($cfg.Backend -eq 'd3d9')", "$effectivePath=if($slot -eq 'CURRENT_FOCUS')"),
        (2, "OUTRUNVR_LAUNCH_ERROR.txt", "SILENT_FAILURE"),
    ]
    for index, original, mutant in mutations:
        assert original in src[index], f"mutation fixture missing {original}"
        changed = list(src)
        changed[index] = changed[index].replace(original, mutant, 1)
        assert check(changed), f"regression mutation escaped: {original}"
    print("DX9Ex launch paths PASS (canonical slots, quoted invocation, visible error, five destructive mutations)")
