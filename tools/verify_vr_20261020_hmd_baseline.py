#!/usr/bin/env python3
"""Current R26 lens-family regression contract.
Static source tests do not assert Quest3 optical success.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'src/hooks_graphics.cpp').read_text(encoding='utf-8')
settings=(root/'src/vr/settings.cpp').read_text(encoding='utf-8')
collector=(root/'tools/Collect-OutRunVRLogs.ps1').read_text(encoding='utf-8')

def verify(src,setting,log):
    assert 'VRLensFlareCentreEnabled{ "VR", "LensFlareCentreEnabled", true,' in setting
    assert 'extern Setting<bool> VRLensFlareCentreEnabled;' in src
    assert 'Module::exe_ptr(0xC993), DrawObjectAlphaCentre' in src
    assert 'Module::exe_ptr(0xCABE), DrawObjectAlphaProjected' in src

    center=src.split('static void __cdecl DrawObjectAlphaCentre(',1)[1].split('public:',1)[0]
    for obj in ('0x570002','0x570006','0x57000F','0x570010'):
        assert f'case {obj}:' in src
    assert 'static constexpr bool IsProjectedSunScreenObject' in src
    assert 'IsProjectedSunScreenObject(objectId)' in center
    assert 'RenderScope::ProjectedScreenEffect2D' in center
    assert ('ScopedExactProducerSemantic semantic(\n'
            '            OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D,') in center
    # The already-integrated C993 ray correction identifies the exact
    # centre producer; reverting it to None loses the narrow ray owner.
    assert 'ProducerToken::LensFlareCentre' in center
    assert '!OutRunVR::GameSemantic::QueueRenderActive()' in center
    assert 'if (Settings::VREnabled && objectId == 0x570002 &&' in center
    assert '!Settings::VRLensFlareCentreEnabled.get()' in center
    assert 'VR LENS C993 CENTER HIDDEN:' in center
    assert center.index('if (Settings::VREnabled && objectId == 0x570002 &&') < center.index('IsProjectedSunScreenObject(objectId)')
    assert 'Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);' in center

    projected=src.split('static void __cdecl DrawObjectAlphaProjected(',1)[1].split('static void __cdecl DrawObjectAlphaCentre(',1)[0]
    assert 'objectId == 0x570008' in projected
    assert 'ordinal <= 2' in projected
    assert 'VR LENS 570008 CHILD HIDDEN:' in projected
    assert 'sun 0x570002 and non-570008 outer discs preserved' in projected

    assert 'Get-Content $active' in log
    assert "$kv.ContainsKey('gameDllSha256')" in log
    assert "[string]$kv['gameDllSha256']" in log
    assert "if($kv.gameDllSha256)" not in log
    return True

verify(source,settings,collector)
mutations=[
    ('source','case 0x570010:','case 0x570011:'),
    ('source','case 0x57000F:','case 0x570011:'),
    ('source','ordinal <= 2','ordinal == 2'),
    ('source','!Settings::VRLensFlareCentreEnabled.get()','Settings::VRLensFlareCentreEnabled.get()'),
    ('settings','"LensFlareCentreEnabled", true,','"LensFlareCentreEnabled", false,'),
    ('collector',"$kv.ContainsKey('gameDllSha256')","$kv.gameDllSha256"),
]
for fname,old,bad in mutations:
    values=dict(source=source,settings=settings,collector=collector)
    assert old in values[fname],old
    values[fname]=values[fname].replace(old,bad,1)
    try:
        verify(values['source'],values['settings'],values['collector'])
    except (AssertionError,ValueError):
        pass
    else:
        raise AssertionError('mutation escaped '+fname+' '+old)

# Mutate the C993 owner, not an earlier occurrence in the parent hook.
prefix, center = source.split('static void __cdecl DrawObjectAlphaCentre(', 1)
for old, bad in [('ProducerToken::LensFlareCentre', 'ProducerToken::None'),
                 ('RenderScope::ProjectedScreenEffect2D', 'RenderScope::WorldBillboard')]:
    try:
        verify(prefix + 'static void __cdecl DrawObjectAlphaCentre(' + center.replace(
            old, bad, 1), settings, collector)
    except AssertionError:
        pass
    else:
        raise AssertionError('exact C993 centre mutation escaped: ' + old)
print('PASS VR projected sun family 570002/570006/57000F/570010 + both 570008 child suppression; 8 negative controls; HMD UNTESTED')

