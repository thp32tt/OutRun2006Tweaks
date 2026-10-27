#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / 'src/vr/d3d9/stereo_renderer_r7.inc').read_text(encoding='utf-8')
wf = (root / '.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')
start = src.index('HRESULT __stdcall SetDepthStencilSurfaceDest(')
end = src.index('HRESULT __stdcall QueryIssueDest(', start)
body = src[start:end]
compat = body.index('if(compatible)')
else_pos = body.index('else', compat)
branch = body[compat:else_pos]
assert 'RightDepthSynchronized=false;' in branch
assert 'RightStencilSynchronized=!FormatHasStencil(leftDesc.Format);' in branch
assert 'CreateRightDepthForTracked(device)' not in branch
assert 'without desynchronizing' not in branch
assert 'content sync invalidated' in branch
assert "'tools/verify_vr_r7_depth_identity_sync.py'" in wf
bad = branch.replace('RightDepthSynchronized=false;', 'RightDepthSynchronized=true;', 1)
assert bad != branch and 'RightDepthSynchronized=false;' not in bad
print('PASS R7 compatible depth allocation reuse invalidates content sync on COM identity change; HMD UNTESTED')
