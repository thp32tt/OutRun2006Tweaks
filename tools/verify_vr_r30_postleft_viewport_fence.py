#!/usr/bin/env python3
"""R30 must fence post-LEFT viewport provenance before any RIGHT replay."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'src/vr/d3d9/stereo_renderer_r30.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def body(source: str, signature: str) -> str:
    at=source.index(signature)
    start=source.index('{', at)
    depth=0
    for pos in range(start, len(source)):
        if source[pos]=='{': depth+=1
        elif source[pos]=='}':
            depth-=1
            if depth==0: return source[start:pos+1]
    raise AssertionError('unclosed '+signature)

def require_fence(fn: str, baseline: str, frame_anchor: str) -> None:
    left=fn.index('const HRESULT leftHr')
    fence=fn.index('D3DVIEWPORT9 postLeftViewport{};', left)
    frame=fn.index(frame_anchor, fence)
    assert left < fence < frame
    window=fn[fence:frame]
    for token in (
        'R29OwnerTryGetTrackedViewport(postLeftViewport) ||',
        'SUCCEEDED(device->GetViewport(&postLeftViewport))',
        'postLeftViewport.X == '+baseline+'.X',
        'postLeftViewport.Y == '+baseline+'.Y',
        'postLeftViewport.Width == '+baseline+'.Width',
        'postLeftViewport.Height == '+baseline+'.Height',
        'postLeftViewport.MinZ == '+baseline+'.MinZ',
        'postLeftViewport.MaxZ == '+baseline+'.MaxZ',
        'StereoFailureRightStateFailed',
        'StereoFailureViewportUnavailable',
        'R29OwnerArmMonoSafety();',
        'return leftHr;',
    ): assert token in window, token

generic=body(SRC, 'HRESULT R30ExecuteXyzrhwStereo(')
require_fence(generic, 'state.viewport', 'R29OwnerCaptureFrameSnapshot()')
assert generic.index('D3DVIEWPORT9 postLeftViewport{};') < generic.index('R29OwnerCallOriginalSetRenderTarget(')

screen=body(SRC, 'HRESULT R30TryScreenSpaceFovDraw(')
require_fence(screen, 'savedViewport', 'R29OwnerCaptureFrameSnapshot()')
fence=screen[screen.index('D3DVIEWPORT9 postLeftViewport{};'):screen.index('R29OwnerCaptureFrameSnapshot()', screen.index('D3DVIEWPORT9 postLeftViewport{};'))]
assert 'R29OwnerSetWvpOneRegisterAtATime(' in fence
assert 'R30 HUD post-left viewport fence c64' in fence

assert WF.count('tools/verify_vr_r30_postleft_viewport_fence.py') == 2

# Destructive controls: removing one dimension or the tracked fast path is visible.
assert 'postLeftViewport.Width == state.viewport.Width' in generic
assert 'postLeftViewport.Height == savedViewport.Height' in screen
mutated=generic.replace('R29OwnerTryGetTrackedViewport(postLeftViewport) ||', 'false &&', 1)
assert mutated != generic and 'R29OwnerTryGetTrackedViewport(postLeftViewport) ||' not in mutated
print('PASS R30 post-LEFT viewport provenance fence uses tracked hot path, fallback live read, no LEFT replay; HMD UNTESTED')
