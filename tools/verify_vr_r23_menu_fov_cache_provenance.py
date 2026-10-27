#!/usr/bin/env python3
"""R23 cached menu projection must follow valid live binocular FOV provenance."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

assert 'std::array<XrFovf, 2> cachedMenuSourceFov{};' in SRC
assert 'bool cachedMenuSourceFovValid = false;' in SRC
start=SRC.index('const bool currentMenuLetterbox =')
end=SRC.index('if (cachedMenuProjectionValid)', start)
block=SRC[start:end]
required=(
 'const bool currentMenuViewsValid =',
 'vc >= 2 &&',
 '(vs.viewStateFlags & neededViews) == neededViews',
 'const auto sameFov = [](',
 'std::isfinite(value)',
 'const bool menuFovChanged =',
 'cachedMenuSourceFovValid &&',
 '!sameFov(cachedMenuSourceFov[0], views[0].fov)',
 '!sameFov(cachedMenuSourceFov[1], views[1].fov)',
 'cachedMenuSourceFovValid = false;',
 'currentMenuViewsValid &&',
 'letterboxPolicyChanged || menuFovChanged',
 'cachedMenuSourceFov[0] = views[0].fov;',
 'cachedMenuSourceFov[1] = views[1].fov;',
 'cachedMenuSourceFovValid = true;',
)
for token in required:
    assert token in block, token
assert block.index('currentMenuViewsValid &&') < block.index('R23RenderWorldLockedMenuProjection(')
assert block.index('menuFovChanged') < block.index('R23RenderWorldLockedMenuProjection(')
assert block.index('cachedMenuSourceFov[0] = views[0].fov;') > block.index('R23RenderWorldLockedMenuProjection(')
assert WF.count('tools/verify_vr_r23_menu_fov_cache_provenance.py') == 2

# Destructive controls: stale-FOV reuse or invalid-view refresh must be visible.
bad_fov=block.replace('letterboxPolicyChanged || menuFovChanged', 'letterboxPolicyChanged', 1)
assert bad_fov != block and 'letterboxPolicyChanged || menuFovChanged' not in bad_fov
bad_views=block.replace('                        currentMenuViewsValid &&\n', '', 1)
assert bad_views != block
assert bad_views.index('R23RenderWorldLockedMenuProjection(') >= 0
print('PASS R23 menu cache reprojects on valid binocular FOV changes and rejects new raster from invalid XR views; HMD UNTESTED')
