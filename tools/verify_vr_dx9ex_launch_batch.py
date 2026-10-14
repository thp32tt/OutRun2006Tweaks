#!/usr/bin/env python3
"""DX9Ex shipped launch must be visible and observe real OpenXR host."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CMD=(ROOT/'tools/START_DX9EX_TEST.cmd').read_text(encoding='utf-8-sig')
PS=(ROOT/'tools/Run-OutRunVRTest.ps1').read_text(encoding='utf-8-sig')
GUI=(ROOT/'tools/OutRunVR-Slot-Selector.ps1').read_text(encoding='utf-8-sig')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8-sig')

def check(c,p,g,w):
    for s in ('pushd "%~dp0"','OR2006C2C.EXE',
              'backends\\d3d9\\dinput8.dll','backends\\d3d9\\outrun-vr-host.exe',
              'where powershell.exe','-Backend d3d9','-VariantId CURRENT_FOCUS',
              'Run-OutRunVRTest.ps1','if errorlevel 1','pause >nul','exit /b %result%'):
        assert s in c, 'CMD launch contract missing: '+s
    for s in ('Set-Location -LiteralPath $root',
              "Get-Process -Name 'outrun-vr-host'",
              'HOST_NEVER_STARTED','HOST_DISAPPEARED_DURING_GAME',
              'DX9EX_LAUNCH_HEALTH.txt','OUTRUNVR_LAUNCH_ERROR.txt',
              'runtimeValidation=UNTESTED','exit 5',
              'gameExitCode=$gameExitCode',"'GAME_NONZERO_EXIT'",
              'if($gameExitCode -ne 0){','exit 7'):
        assert s in p, 'OpenXR host check missing: '+s
    start=g.split('function Start-Slot(',1)[1].split('$form=New-Object',1)[0]
    assert '-WindowStyle Hidden' not in start, 'hidden child masks launch errors'
    for s in ('START_DX9EX_TEST.cmd','DX9EX_TEST_LAUNCH_CONTRACT.md',
              'if ($launchers.Count -ne 2','verify_vr_dx9ex_launch_batch.py'):
        assert s in w, 'package release gate missing: '+s

if __name__ == '__main__':
    check(CMD,PS,GUI,WF)
    mutants=[
       ('no quoted cwd',CMD.replace('pushd "%~dp0"','rem no working directory',1),PS,GUI,WF),
       ('missing original EXE preflight',CMD.replace('OR2006C2C.EXE','OTHER.EXE'),PS,GUI,WF),
       ('missing host payload',CMD.replace('backends\\d3d9\\outrun-vr-host.exe','missing.exe'),PS,GUI,WF),
       ('missing host lifecycle',CMD,PS.replace('HOST_NEVER_STARTED','HOST_UNKNOWN'),GUI,WF),
       ('silenced game failure',CMD,PS.replace('exit 7','exit 0'),GUI,WF),
       ('erased failure health',CMD,PS.replace("'GAME_NONZERO_EXIT'","'PROCESS_OBSERVED_NOT_HMD_VERIFIED'"),GUI,WF),
       ('hidden runner',CMD,PS,GUI.replace('-WindowStyle Normal','-WindowStyle Hidden',1),WF),
       ('missing packaged entry',CMD,PS,GUI,WF.replace('if ($launchers.Count -ne 2','if ($launchers.Count -ne 1',1)),
    ]
    for name,c,p,g,w in mutants:
        try:check(c,p,g,w)
        except AssertionError:continue
        raise AssertionError('negative mutation survived: '+name)
    print('PASS DX9Ex visible batch, real OpenXR host health and six mutations; HMD UNTESTED')
