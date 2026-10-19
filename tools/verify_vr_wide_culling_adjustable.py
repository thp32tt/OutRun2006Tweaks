#!/usr/bin/env python3
"""2026-10-20 HMD: VR PMT wide margin is editable while keeping stereo source."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
settings=(r/'src/vr/settings.cpp').read_text(encoding='utf-8')
profiles=(r/'tools/OutRunVR-TestProfiles.ps1').read_text(encoding='utf-8')
source=(r/'src/hooks_graphics.cpp').read_text(encoding='utf-8')
def check(s,p,c):
    assert 'VRCullingUnionMarginDegrees{ "VR", "CullingUnionMarginDegrees", 8.0f,' in s
    assert 'Can be tuned in F11.' in s
    assert "-CullingUnionMarginDegrees=4.0" not in p
    assert "-CullingUnionMarginDegrees=8.0" not in p
    assert 'Settings::VRCullingUnionMarginDegrees.get()' in c
    owner=c.split('class DisableStageCulling : public Hook',1)[1].split('class WindowedBorderless',1)[0]
    for marker in (
        'Settings::VRStageCullingMode.get() != 1',
        'Settings::VRCullingUnionMarginDegrees.get(), 0.0f, 15.0f)',
        'const float newX = (std::min)(original._11, 1.0f / tanH);',
        'const float newY = (std::min)(original._22, 1.0f / tanV);',
        'RestoreScopedProjection();',
        'ctx.eax = 1u;',
    ): assert marker in owner, marker
    assert 'projection->_11 = newX;' in owner
    assert 'projection->_22 = newY;' in owner
    assert 'if (vr && mode == 2)' in owner
check(settings,profiles,source)
for typ,old,bad in (
    ('settings','"CullingUnionMarginDegrees", 8.0f,','"CullingUnionMarginDegrees", 4.0f,'),
    ('profiles','# the user must be able to tune VR PMT wide-FOV margin in F11.',
     "-CullingUnionMarginDegrees=8.0 # F11 no longer free"),
    ('source','const float newX = (std::min)(original._11, 1.0f / tanH);',
     'const float newX = 1.0f / tanH;'),
    ('source','RestoreScopedProjection();','// RestoreScopedProjection();'),
):
    parts=dict(settings=settings,profiles=profiles,source=source)
    assert old in parts[typ]
    parts[typ]=parts[typ].replace(old,bad,1)
    try:check(parts['settings'],parts['profiles'],parts['source'])
    except (AssertionError,ValueError):pass
    else:raise AssertionError('wide cull mutant escaped '+typ+old)
from math import tan, radians
for baseDeg in (35.,46.,60.):
    original=1/tan(radians(baseDeg))
    enlarged=1/tan(radians(min(85,baseDeg+8)))
    assert min(original,enlarged)<=original and enlarged>0
print('PASS PMT VR wide 8deg default, F11 writable, scoped projection restore, 4 destructive controls')
