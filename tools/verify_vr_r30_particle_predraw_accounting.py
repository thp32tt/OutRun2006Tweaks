#!/usr/bin/env python3
"""WorldParticle DynamicVB pre-LEFT bind failure must not poison fallback frame."""
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

execute=body(SRC, 'HRESULT R30ExecuteXyzrhwStereo(')
required=(
 'const bool* physicalLeftDrawAttempted = nullptr',
 'const bool deferLeftAccounting =',
 'physicalLeftDrawAttempted != nullptr;',
 'const HRESULT leftHr = leftDraw();',
 'const bool leftWasPhysicallyAttempted =',
 '!physicalLeftDrawAttempted || *physicalLeftDrawAttempted;',
 'if (deferLeftAccounting && leftWasPhysicallyAttempted)',
 'if (!leftWasPhysicallyAttempted)',
 'return leftHr;',
 'R29OwnerMarkRightDrawFailed();',
)
for token in required: assert token in execute, token
assert execute.index('const HRESULT leftHr = leftDraw();') < execute.index('if (!leftWasPhysicallyAttempted)')
assert execute.index('if (!leftWasPhysicallyAttempted)') < execute.index('R29OwnerMarkRightDrawFailed();')

particle=SRC[SRC.index('bool physicalDrawAttempted = false;'):SRC.index('auto leftDraw = [&]()', SRC.index('bool physicalDrawAttempted = false;'))]
assert 'const HRESULT bind =' in particle
assert 'if (FAILED(bind)) return bind;' in particle
assert particle.index('if (FAILED(bind)) return bind;') < particle.index('physicalDrawAttempted = true;') < particle.index('R29OwnerCallRawDrawPrimitive(')
assert '"R30/WorldParticle-DynamicVB", false,' in particle
assert '&physicalDrawAttempted);' in particle
assert 'MayUseNativeUpAfterGpuAttempt(' in particle
assert WF.count('tools/verify_vr_r30_particle_predraw_accounting.py') == 2

# A bind failure before the attempt bit is set must remain distinguishable.
bad=SRC.replace('&physicalDrawAttempted);', 'nullptr);', 1)
assert bad != SRC
bad_particle=bad[bad.index('bool physicalDrawAttempted = false;'):bad.index('auto leftDraw = [&]()', bad.index('bool physicalDrawAttempted = false;'))]
assert '&physicalDrawAttempted);' not in bad_particle
print('PASS R30 WorldParticle pre-LEFT stream bind failure delegates without false frame poison; attempted Draw remains fail-closed; HMD UNTESTED')
