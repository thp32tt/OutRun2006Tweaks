#!/usr/bin/env python3
"""HMD 0cff83cf baseline: scope-only lens-center removal + PC Fast log collector.
Static source tests do not assert Quest3 optical success.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'src/hooks_graphics.cpp').read_text(encoding='utf-8')
settings=(root/'src/vr/settings.cpp').read_text(encoding='utf-8')
collector=(root/'tools/Collect-OutRunVRLogs.ps1').read_text(encoding='utf-8')
def verify(src,setting,log):
    assert 'VRLensFlareCentreEnabled{ "VR", "LensFlareCentreEnabled", false,' in setting
    assert 'extern Setting<bool> VRLensFlareCentreEnabled;' in src
    assert 'Module::exe_ptr(0xC993), DrawObjectAlphaCentre' in src
    assert 'Module::exe_ptr(0xCABE), DrawObjectAlphaProjected' in src
    center=src.split('static void __cdecl DrawObjectAlphaCentre(',1)[1].split('public:',1)[0]
    assert 'objectId == 0x570002\n            ?' in center
    assert 'if (Settings::VREnabled && objectId == 0x570002 &&' in center
    assert 'VR LENS C993 CENTER HIDDEN:' in center
    assert 'LensCentreOwnerDepth == LensCentreDepth' in center
    assert '!OutRunVR::GameSemantic::QueueRenderActive()' in center
    assert '!Settings::VRLensFlareCentreEnabled.get()' in center
    assert center.index('if (Settings::VREnabled && objectId == 0x570002 &&') < center.index('ScopedExactProducerSemantic')
    assert center.index('if (Settings::VREnabled && objectId == 0x570002 &&') < center.index('Game::DrawObjectAlpha_Internal(')
    assert 'Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);' in center
    assert 'Get-Content $active' in log
    assert "$kv.ContainsKey('gameDllSha256')" in log
    assert "[string]$kv['gameDllSha256']" in log
    assert "if($kv.gameDllSha256)" not in log
    return True
verify(source,settings,collector)
for fname,old,bad in [
    ('source','objectId == 0x570002','objectId >= 0'),
    ('source','!Settings::VRLensFlareCentreEnabled.get()','Settings::VRLensFlareCentreEnabled.get()'),
    ('source','if (Settings::VREnabled && objectId == 0x570002 &&','if (objectId == 0x570002 &&'),
    ('settings','"LensFlareCentreEnabled", false,','"LensFlareCentreEnabled", true,'),
    ('collector',"$kv.ContainsKey('gameDllSha256')","$kv.gameDllSha256")]:
    values=dict(source=source,settings=settings,collector=collector)
    assert old in values[fname],old
    values[fname]=values[fname].replace(old,bad,1)
    try:verify(values['source'],values['settings'],values['collector'])
    except (AssertionError,ValueError): pass
    else:raise AssertionError('mutation escaped '+fname+' '+old)
print('PASS VR C993 exact object center hide independent of D3A5 parent, outer CABE and desktop retained, 5 negative controls')
