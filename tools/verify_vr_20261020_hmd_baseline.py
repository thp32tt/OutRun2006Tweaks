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
    # C993 is already projected to a centre-eye ray by the game. The exact
    # family clears D3A5's spatial token so R69 mono fusion owns the draw.
    assert 'ProducerToken::None' in center
    assert '!OutRunVR::GameSemantic::QueueRenderActive()' in center
    # Quest E intentionally restores every original sun/flare child: a
    # disabled INI toggle may not hide the C993 centre object.
    assert 'static_cast<unsigned>(objectId) == 0x570002u' in center
    assert '!Settings::VRLensFlareCentreEnabled.get()' not in center
    assert 'VR LENS C993 CENTER HIDDEN:' not in center
    assert center.index('static_cast<unsigned>(objectId) == 0x570002u') < center.index('IsProjectedSunScreenObject(objectId)')
    assert 'Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);' in center

    projected=src.split('static void __cdecl DrawObjectAlphaProjected(',1)[1].split('static void __cdecl DrawObjectAlphaCentre(',1)[0]
    assert 'objectId == 0x570008' in projected
    # Current FULL trace scopes the 570008 source ordinal to one explicit
    # LensFlareSequence. This preserves both original CABE calls while
    # preventing an unanchored cross-sun counter from masquerading as a
    # stable physical-child identity.
    assert 'unsigned sourceOrdinal = 0;' in projected
    assert 'if (LensFlareSequence != 0)' in projected
    assert 'if (LensOuter570008Sequence != LensFlareSequence)' in projected
    assert 'LensOuter570008Sequence = LensFlareSequence;' in projected
    assert 'LensOuter570008Ordinal = 0;' in projected
    assert 'sourceOrdinal = ++LensOuter570008Ordinal;' in projected
    assert 'VR LENS 570008 ORIGINAL BOTH DRAWN:' in projected
    assert 'if (sourceOrdinal == 2)' not in projected
    assert 'Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);' in projected

    assert 'Get-Content $active' in log
    assert "$kv.ContainsKey('gameDllSha256')" in log
    assert "[string]$kv['gameDllSha256']" in log
    assert "if($kv.gameDllSha256)" not in log
    return True

verify(source,settings,collector)
mutations=[
    ('source','case 0x570010:','case 0x570011:'),
    ('source','case 0x57000F:','case 0x570011:'),
    ('source','sourceOrdinal = ++LensOuter570008Ordinal;','sourceOrdinal = LensOuter570008Ordinal;'),
    ('source','static_cast<unsigned>(objectId) == 0x570002u','static_cast<unsigned>(objectId) == 0x570003u'),
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
for old, bad in [('ProducerToken::None', 'ProducerToken::LensFlareCentre'),
                 ('RenderScope::ProjectedScreenEffect2D', 'RenderScope::WorldBillboard')]:
    try:
        verify(prefix + 'static void __cdecl DrawObjectAlphaCentre(' + center.replace(
            old, bad, 1), settings, collector)
    except AssertionError:
        pass
    else:
        raise AssertionError('exact C993 centre mutation escaped: ' + old)
print('PASS VR C993 centre-eye mono fusion + both original 570008 draws preserved; negative controls; HMD UNTESTED')

