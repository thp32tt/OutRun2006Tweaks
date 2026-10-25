#!/usr/bin/env python3
"""01067: D3D9 FVF world clipping is connected to live native Draw/DrawIndexed."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(r/"src/vr/d3d11/live_game_fixed_clip.hpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
def connected(s,k):
    return all((
        '#include "live_game_fixed_clip.hpp"' in s,
        'GetRenderState(D3DRS_CLIPPLANEENABLE, &clipPlanes)' in s,
        'game->GetClipPlane(slot, fixedClip.world[slot].data())' in s,
        'native_game_fixed_clip_mask_admitted(' in s,
        'native_game_fixed_clip_distances(' in s,
        'fixedClip, capture, output)' in s,
        'layout, transforms, fixedClip, capture, vertices)' in s,
        'SV_ClipDistance0' in s,'SV_ClipDistance1' in s,
        'o.clip0 = v.clip0; o.clip1 = v.clip1;' in s,
        'CreateInputLayout(elements, 7,' in s,
        'static_assert(sizeof(NativeVertex) == 96u' in s,
        'std::copy_n(distances.begin() + 4u, 4u, v.clip1);' in s,
        'transformed[c] += p[k] * world[k][c];' in k,
        'distance += transformed[k] * planes.world[i][k];' in k,
        'out.fill(1.0f);' in k
    ))
assert connected(b,h)
for x in ('SV_ClipDistance0','SV_ClipDistance1',
          'game->GetClipPlane(slot, fixedClip.world[slot].data())',
          'std::copy_n(distances.begin() + 4u, 4u, v.clip1);'):
    m=b.replace(x,'/* removed source link */')
    assert m!=b and not connected(m,h),x
for x in ('out.fill(1.0f);','transformed[c] += p[k] * world[k][c];'):
    m=h.replace(x,'/* lost world clip math */')
    assert m!=h and not connected(b,m),x
assert 'tests/vr/dx11_live_fixed_clip_01067.cpp' in w
assert 'python tools/test_dx11_live_fixed_clip_01067.py' in w
print("PASS 01067 FVF native world-space clip GPU integration/mutation")
