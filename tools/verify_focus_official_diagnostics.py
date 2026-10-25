#!/usr/bin/env python3
"""Check the real accepted package variants can reach TEST and DEBUG branches."""
from pathlib import Path
import re
r=Path(__file__).resolve().parents[1]
s=(r/'tools/Run-FocusOfficialTest.ps1').read_text()
accepted=re.search(r"\$variant -notin @\(([^)]*)\)",s).group(1)
variants=re.findall(r"'([^']+)'",accepted)
selector=re.search(r"\$debugMode = \$variant -eq '([^']+)'",s).group(1)
actual={v:v==selector for v in variants}
assert actual=={'R26_FOCUS_OFFICIAL_TEST':False,'R26_FOCUS_OFFICIAL_DEBUG':True},actual
for x in ('SOURCE_SHA.txt','BINARY_IDENTITY.json',"'-AutoRenderResolution=true'","'-FollowGameResolution=false'","'-UnifiedEyeMenuSource=false'","'-AntiAliasing=0'","'-Hud1080pReference=true'","'-HudScale=0.55'"):
 assert x in s,x
assert "Get-FileHash" in s
print('PASS official TEST/DEBUG reachability, XR/HUD arguments and captured binary identity')
