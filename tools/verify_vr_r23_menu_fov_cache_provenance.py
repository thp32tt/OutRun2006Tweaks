#!/usr/bin/env python3
"""R23 LOCAL menu quad must not depend on cached projection/FOV raster provenance."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def menu_block(text: str) -> str:
    start=text.index('const std::uint32_t clientGameState = shared.GameState();')
    end=text.index('QueryPerformanceCounter(&re);',start)
    return text[start:end]

def verify_block(block: str) -> None:
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

    call=block.index('R23RenderTheater(')
    gate_start=block.rfind('if (capture.available &&',0,call)
    assert gate_start >= 0
    gate=block[gate_start:call]
    assert 'currentMenuViewsValid &&' not in gate
    assert 'menuFovChanged' not in gate
    assert 'letterboxPolicyChanged' not in gate
    assert 'R23RenderWorldLockedMenuProjection(' not in block
    assert 'cachedMenuSourceFov[0] = views[0].fov;' not in block
    assert 'cachedMenuSourceFov[1] = views[1].fov;' not in block
    assert 'cachedMenuSourceFovValid = true;' not in block

block=menu_block(SRC)
verify_block(block)
assert WF.count('tools/verify_vr_r23_menu_fov_cache_provenance.py') == 2

# Destructive mutations are applied only to the actual menu branch, never to
# helper function declarations elsewhere in the TU.
mutations=(
    ('if (capture.available &&\n                        R23RenderTheater(',
     'if (capture.available && currentMenuViewsValid &&\n                        R23RenderTheater('),
    ('R23RenderTheater(', 'R23RenderWorldLockedMenuProjection('),
    ('cachedMenuSourceFovValid = false;', 'cachedMenuSourceFovValid = true;'),
)
for old,bad in mutations:
    assert old in block, 'mutation fixture missing: '+old
    altered=block.replace(old,bad,1)
    try:
        verify_block(altered)
    except (AssertionError,ValueError):
        continue
    raise AssertionError('unsafe FOV-cache mutation escaped: '+old)

print('PASS R23 LOCAL menu quad is independent of cached projection/FOV raster provenance; 3 destructive mutants; HMD UNTESTED')
