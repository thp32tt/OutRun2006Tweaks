#!/usr/bin/env python3
"""R23 menu quad must not depend on a cached projection/FOV pair.

XrCompositionLayerQuad is an object in LOCAL space; OpenXR projects it for the
current two eye views. The previous projection-layer menu needed a cached pair
of FOV-specific rasters. Keeping that gate on the quad would incorrectly hide
or freeze the menu during valid FOV/recenter changes.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

start=SRC.index('const std::uint32_t clientGameState = shared.GameState();')
end=SRC.index('QueryPerformanceCounter(&re);', start)
block=SRC[start:end]

required=(
    'if (capture.available &&',
    'R23RenderTheater(',
    'compositor, viewSpace, localSpace,',
    'fs.predictedDisplayTime, quad, false',
    'cachedMenuProjectionValid = false;',
    'cachedMenuSourceFovValid = false;',
    'menu-local-fixed-quad-fresh',
    'menu-local-fixed-quad-cached',
)
for token in required:
    assert token in block, token

# FOV bookkeeping may remain for diagnostics/legacy review, but it must not
# gate or publish the active quad.
quad_call=block.index('R23RenderTheater(')
quad_if=block.rfind('if (capture.available &&', 0, quad_call)
assert quad_if >= 0
quad_gate=block[quad_if:quad_call]
assert 'currentMenuViewsValid &&' not in quad_gate
assert 'menuFovChanged' not in quad_gate
assert 'letterboxPolicyChanged' not in quad_gate
assert 'R23RenderWorldLockedMenuProjection(' not in block
assert 'cachedMenuSourceFov[0] = views[0].fov;' not in block
assert 'cachedMenuSourceFov[1] = views[1].fov;' not in block
assert 'cachedMenuSourceFovValid = true;' not in block

# The active policy workflow must keep this transition guard wired.
assert WF.count('tools/verify_vr_r23_menu_fov_cache_provenance.py') == 2

# Destructive controls.
mutations=(
    ('if (capture.available &&\n                        R23RenderTheater(',
     'if (capture.available && currentMenuViewsValid &&\n                        R23RenderTheater('),
    ('R23RenderTheater(', 'R23RenderWorldLockedMenuProjection('),
    ('cachedMenuSourceFovValid = false;', 'cachedMenuSourceFovValid = true;'),
)
for old,bad in mutations:
    assert old in SRC
    altered=SRC.replace(old,bad,1)
    astart=altered.index('const std::uint32_t clientGameState = shared.GameState();')
    aend=altered.index('QueryPerformanceCounter(&re);',astart)
    ablock=altered[astart:aend]
    escaped=True
    try:
        acall=ablock.index('R23RenderTheater(')
        agate=ablock[ablock.rfind('if (capture.available &&',0,acall):acall]
        assert 'currentMenuViewsValid &&' not in agate
        assert 'R23RenderWorldLockedMenuProjection(' not in ablock
        assert 'cachedMenuSourceFovValid = true;' not in ablock
    except (AssertionError,ValueError):
        escaped=False
    assert not escaped, 'unsafe FOV-cache mutation escaped: '+old

print('PASS R23 LOCAL menu quad is independent of cached projection/FOV raster provenance; HMD UNTESTED')
