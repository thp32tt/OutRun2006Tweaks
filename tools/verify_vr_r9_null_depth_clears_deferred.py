#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / 'src/vr/d3d9/stereo_renderer.cpp').read_text(encoding='utf-8')
wf = (root / '.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')
start = cpp.index('HRESULT __stdcall SetDepthStencilSurfaceDestR9(')
end = cpp.index('HRESULT __stdcall SetRenderTargetDestR9(', start)
body = cpp[start:end]
n = body.index('if (!surface)')
m = body.index('if ((!R9MainDepthKnown', n)
null_branch = body[n:m]
assert 'R9DeferredDepth = false;' in null_branch
assert 'ReleaseCom(R9DeferredDepthIdentity);' in null_branch
assert null_branch.index('R9DeferredDepth = false;') < null_branch.index('return hr;')
assert null_branch.index('ReleaseCom(R9DeferredDepthIdentity);') < null_branch.index('return hr;')
mirror_start = cpp.index('bool R9CurrentDepthCanMirror()')
mirror_end = cpp.index('void R9LogFirstFailure', mirror_start)
mirror = cpp[mirror_start:mirror_end]
assert 'if (!TrackedDepthStencil)' in mirror
assert 'return true;' in mirror
assert "'tools/verify_vr_r9_null_depth_clears_deferred.py'" in wf
print('PASS R9 null-depth clears stale deferred-depth state; HMD UNTESTED')
