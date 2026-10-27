#!/usr/bin/env python3
"""R62 failed LEFT projection setup must not masquerade as a physical LEFT draw."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def body(source: str, signature: str) -> str:
    at=source.index(signature)
    start=source.index('{',at)
    depth=0
    for pos in range(start,len(source)):
        if source[pos]=='{': depth+=1
        elif source[pos]=='}':
            depth-=1
            if depth==0: return source[start:pos+1]
    raise AssertionError('unclosed '+signature)

def check(source: str) -> bool:
    try:
        helper=body(source,'HRESULT R30ExecuteXyzrhwStereo(')
        r62=body(source,'HRESULT R62TryFixedFunctionSpriteStereo(')
        assert 'const bool* physicalLeftDrawAttempted = nullptr' in helper
        assert 'const bool deferLeftAccounting =' in helper
        assert 'physicalLeftDrawAttempted != nullptr;' in helper
        assert 'const bool leftWasPhysicallyAttempted =' in helper
        assert '!physicalLeftDrawAttempted || *physicalLeftDrawAttempted;' in helper
        fail=helper.index('if (FAILED(leftHr))')
        no_draw=helper.index('if (!leftWasPhysicallyAttempted)',fail)
        poison=helper.index('R9Poison(OutRunVR::StereoFailureLeftDrawFailed',no_draw)
        assert fail < no_draw < poison
        assert 'return leftHr;' in helper[no_draw:poison]
        assert 'drawAttempted[eye] = true;' in r62
        call=r62.index('const HRESULT hr = R30ExecuteXyzrhwStereo(')
        assert '&drawAttempted[0]);' in r62[call:call+700]
        fallback=r62.index('if (!drawAttempted[0] && FAILED(projectionSetHr[0]))')
        assert fallback > call
        assert 'return restored ? E_NOTIMPL : E_FAIL;' in r62[fallback:fallback+500]
        return True
    except (AssertionError, ValueError):
        return False

assert WF.count('tools/verify_vr_r62_predraw_projection_fallback.py') == 2
assert check(SRC)
for label,old,new in (
    ('drop attempt pointer','&drawAttempted[0]);','nullptr);'),
    ('fake left attempt','!physicalLeftDrawAttempted || *physicalLeftDrawAttempted','true'),
    ('block original fallback','return restored ? E_NOTIMPL : E_FAIL;','return E_FAIL;'),
):
    assert old in SRC,label
    assert not check(SRC.replace(old,new,1)), 'mutation escaped: '+label
print('PASS R62 pre-LEFT projection failure stays non-physical and delegates original draw after successful restore; HMD UNTESTED')
