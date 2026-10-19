#!/usr/bin/env python3
"""Self-hosted PC Fast: verify a complete first-run DX9Ex package contract.

This is a source-level contract; passing does not prove a Windows binary
was actually compiled or a Quest3/VDXR visual test passed.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
build=(R/"tools/Build-OutRunPCFast.ps1").read_text(encoding="utf-8")
selector=(R/"tools/Select-OutRunVRBackend.ps1").read_text(encoding="utf-8")
runner=(R/"tools/Run-OutRunVRTest.ps1").read_text(encoding="utf-8")
start=(R/"tools/START_DX9EX_PC_FAST.cmd").read_text(encoding="utf-8")
workflow=(R/".github/workflows/vr-pc-fast-build.yml").read_text(encoding="utf-8")
def check(b,s,r,cmd):
    for token in ('START_DX9EX_PC_FAST.cmd', 'Select-OutRunVRBackend.ps1',
                  'Run-OutRunVRTest.ps1','SOURCE_SHA.txt','BUILD_INPUTS.json',
                  'SHA256SUMS.txt','dinput8.dll','outrun-vr-host.exe'):
        assert token in b, ("PC FAST package item missing",token)
    assert 'CURRENT_VR_SESSION.json' not in b.split("$runtimeFiles = @(",1)[1].split(")",1)[0]
    assert "PC_FAST_INCREMENTAL_NOT_FINAL_CI" in b
    assert "ValidationClass = 'PC_FAST_INCREMENTAL_NOT_FINAL_CI'" in b
    for token in ("$activeMissing = !(Test-Path -LiteralPath $active)",
                  "$currentMissing = !(Test-Path -LiteralPath $current)",
                  "if(-not ($activeMissing -and $currentMissing))",
                  "if(!(Test-Path $game))",
                  "if($running){throw",
                  "& $selector -Backend d3d9 -TestProfile $TestProfile -VariantId CURRENT_FOCUS",
                  "if(-not $? -or !(Test-Path -LiteralPath $active)"):
        assert token in r, ("first-run safety missing",token)
    assert r.index("if(!(Test-Path $game))") < r.index("$activeMissing =")
    for token in ("$isPcFastPackage", "ACTIVE_FULL_R34",
                  "R51-PC-FAST-v2-R26HUD-ON",
                  "PC_FAST_INCREMENTAL_NOT_FINAL_CI",
                  "$rendererCmakeFlags -ne [string]$buildInputs.CMakeFlags",
                  "OUTRUN_VR_SAFE_DRAW_COMPARE=OFF", 
                  "OUTRUN_VR_R26_HUD_COMPARE=ON"):
        assert token in s, ("package/selector contract missing",token)
    assert s.index("$isPcFastPackage = $false") < s.index("if ($isPcFastPackage)")
    for token in ('if not exist "OR2006C2C.EXE"',
                  'if not exist "backends\\d3d9\\dinput8.dll"',
                  'if not exist "backends\\d3d9\\outrun-vr-host.exe"',
                  'Run-OutRunVRTest.ps1'):
        assert token in cmd, ("starter guard missing",token)
    assert workflow.count("runs-on: [self-hosted, Windows, X64, outrun-pc]") == 1
    assert "contains(github.event.head_commit.message, '[pc-build]')" in workflow
    return True
check(build,selector,runner,start)
for source,old,new in (
    ("runner","if(-not ($activeMissing -and $currentMissing))",
     "if($activeMissing -or $currentMissing)"),
    ("runner","-VariantId CURRENT_FOCUS","-VariantId R26_SAFE"),
    ("selector","R51-PC-FAST-v2-R26HUD-ON","R51-PC-FAST-v3"),
    ("selector","$rendererCmakeFlags -ne [string]$buildInputs.CMakeFlags",
     "$rendererCmakeFlags -eq [string]$buildInputs.CMakeFlags"),
    ("build","'START_DX9EX_PC_FAST.cmd',","'Run-OutRunVRTest.cmd',"),
    ("start",'if not exist "OR2006C2C.EXE"','if exist "OR2006C2C.EXE"')):
    items=dict(build=build,selector=selector,runner=runner,start=start)
    assert old in items[source], old
    items[source]=items[source].replace(old,new,1)
    try:check(items["build"],items["selector"],items["runner"],items["start"])
    except (AssertionError,ValueError):pass
    else:raise AssertionError("PC fast mutation survived: "+source+" "+old)
print("PASS PC Fast DX9Ex single-command launcher, source identity, first-run safety, and six negative mutations")
