#!/usr/bin/env python3
"""Protect portrait VDXR -> ultrawide PC mirror pixel aspect, HMD unchanged."""
from pathlib import Path
from math import isclose
r=Path(__file__).resolve().parents[1]
cpp=(r/'src/hooks_graphics.cpp').read_text(encoding='utf-8')
header=(r/'src/vr/ui/vr_mirror_aspect_fit.hpp').read_text(encoding='utf-8')
settings=(r/'src/vr/settings.cpp').read_text(encoding='utf-8')
def check(c,h,s):
    assert 'VRMirrorPreserveAspect{ "VR", "MirrorPreserveAspect", true,' in s
    assert '#include "vr/ui/vr_mirror_aspect_fit.hpp"' in c
    owner=c.split('class WindowedBorderless : public Hook',1)[1].split('bool validate() override',1)[0]
    assert 'if (Settings::VRMirrorPreserveAspect)' in owner
    assert 'OutRunVRMirrorAspect::Fit(' in owner
    assert 'x += fit.left;' in owner and 'y += fit.top;' in owner
    assert 'width = fit.width;' in owner and 'height = fit.height;' in owner
    assert 'SetWindowPos(window, 0, x, y, width, height, 0x40);' in owner
    assert 'Game::screen_resolution->x =' not in owner
    assert 'Game::screen_resolution->y =' not in owner
    assert 'GetMonitorInfoW(monitor, &monitorInfo)' in owner
    for needle in (
        'const double scale = (std::min)(x, y);',
        'std::round(sourceW * scale)',
        'std::round(sourceH * scale)',
        '(monitorW - width) / 2',
        '(monitorH - height) / 2',
    ): assert needle in h, needle
check(cpp,header,settings)
for src,old,bad in (
    ('cpp','if (Settings::VRMirrorPreserveAspect)','if (false)'),
    ('cpp','width = fit.width;','width = monitorWidth;'),
    ('header','const double scale = (std::min)(x, y);',
     'const double scale = (std::max)(x, y);'),
    ('header','(monitorW - width) / 2','0'),
    ('settings','"MirrorPreserveAspect", true,','"MirrorPreserveAspect", false,')):
    d=dict(cpp=cpp,header=header,settings=settings)
    assert old in d[src]
    d[src]=d[src].replace(old,bad,1)
    try:check(d['cpp'],d['header'],d['settings'])
    except (AssertionError,ValueError): pass
    else:raise AssertionError('escaped mirror aspect mutation '+old)
def fit(mw,mh,sw,sh):
    scale=min(mw/sw,mh/sh)
    w=max(1,min(mw,round(sw*scale)))
    h=max(1,min(mh,round(sh*scale)))
    return ((mw-w)//2,(mh-h)//2,w,h)
for monitor in [(3440,1440),(1920,1080),(2560,1440)]:
    for source in [(2496,2688),(3440,1440),(1920,1080)]:
        x,y,w,h=fit(*monitor,*source)
        assert x>=0 and y>=0 and w<=monitor[0] and h<=monitor[1]
        assert abs(w/h-source[0]/source[1])<=max(1/h,1/w)*2
assert fit(3440,1440,2496,2688)==(1051,0,1337,1440)
print('PASS portrait XRender -> desktop source-preserving mirror fit; source/eye unchanged; five destructive controls')
