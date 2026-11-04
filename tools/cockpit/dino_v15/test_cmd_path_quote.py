#!/usr/bin/env python3
"""Windows CRT regression: avoid ending quoted path parameters with backslash."""
from pathlib import Path
ROOT = Path(__file__).parent
def argv(s):
    args=[];i=0
    while i<len(s):
        while i<len(s) and s[i].isspace():i+=1
        if i>=len(s):break
        out=[];inside=False
        while i<len(s):
            if s[i].isspace() and not inside:break
            if s[i]=="\\":
                n=0
                while i<len(s) and s[i]=="\\":i+=1;n+=1
                if i<len(s) and s[i]=='"':
                    out.extend("\\"*(n//2))
                    if n%2:out.append('"')
                    else:inside=not inside
                    i+=1
                else:out.extend("\\"*n)
                continue
            if s[i]=='"':inside=not inside;i+=1;continue
            out.append(s[i]);i+=1
        args.append("".join(out))
        while i<len(s) and s[i].isspace():i+=1
    return args
install=(ROOT/"INSTALL-DINO-COCKPIT-V15.cmd").read_text()
restore=(ROOT/"RESTORE-DINO-COCKPIT-V15.cmd").read_text()
for source in (install,restore):
    assert 'set "GAME_ROOT=%~dp0."' in source
    assert 'set "GAME_ROOT=%~1\\."' in source
    assert '--game "%GAME_ROOT%"' in source
assert '--textures-dir "%~dp0."' in install
for root in ["I:\\game\\OutRun_vr\\","I:\\game\\OutRun vr\\"]:
    args=argv(f'"DinoCockpitV15.exe" install --game "{root}." --payload "{root}Dino246_Cockpit_LHD_v15.dcm" --textures-dir "{root}."')
    assert args==["DinoCockpitV15.exe","install","--game",root+".","--payload",root+"Dino246_Cockpit_LHD_v15.dcm","--textures-dir",root+"."]
    restore_args=argv(f'"DinoCockpitV15.exe" restore --game "{root}."')
    assert restore_args==["DinoCockpitV15.exe","restore","--game",root+"."]
    bad=argv(f'"DinoCockpitV15.exe" install --game "{root}" --payload "{root}Dino246_Cockpit_LHD_v15.dcm"')
    assert "--payload" not in bad
print("DINO_V15_WINDOWS_ARGV_PATHFIX_REGRESSION_PASS")
