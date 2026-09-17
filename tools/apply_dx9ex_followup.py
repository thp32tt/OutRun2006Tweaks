from pathlib import Path


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    found = text.count(old)
    if found < count:
        raise SystemExit(f'{path}: expected {count}, found {found}: {old[:120]!r}')
    p.write_text(text.replace(old, new, count), encoding='utf-8')

# Explicit standard-library ownership + valid fixed-function texture stages.
p = 'src/vr/d3d9/ex_device_upgrade.cpp'
replace(p, '#include <atomic>\n', '#include <algorithm>\n#include <atomic>\n')
replace(p, '#include <vector>\n', '#include <utility>\n#include <vector>\n')
replace(p,
'''            for (DWORD stage = 0; stage < 16; ++stage)\n                if (FAILED(device->SetTexture(stage, nullptr))) ++failures;''',
'''            // Classic D3D9 exposes eight fixed-function texture stages.\n            // Do not count VS sampler aliases (16..19) or invalid pixel stages\n            // as Reset replay failures.\n            for (DWORD stage = 0; stage < 8; ++stage)\n                if (FAILED(device->SetTexture(stage, nullptr))) ++failures;''')

# Keep DirectGPU rejection generation-scoped rather than accidentally process-scoped.
p = 'src/vr/d3d9/stereo_renderer_r32.cpp'
replace(p,
'''            if (!frameId || R32DirectCopyPathRejected ||\n                !R32EnsureDirectResources(device) ||\n                !BackBuffer || !RightEyeSurface)\n                return false;''',
'''            if (!frameId || !R32EnsureDirectResources(device) ||\n                !BackBuffer || !RightEyeSurface)\n                return false;\n            // R32EnsureDirectResources must run before this cached rejection:\n            // host PID/LUID or transport-generation changes invalidate the old\n            // interop identity and clear the rejection automatically.\n            if (R32DirectCopyPathRejected)\n                return false;''')

# R14 now tracks actual mutating level-surface operations and fails closed if the
# compatibility shadow itself cannot be established.
p = 'src/vr/d3d9/ex_device_upgrade_r14.cpp'
replace(p,
'''// Lock/Unlock operation stable while the registry is changed. Any write path\n// which R14 cannot mirror (direct GPU Lock fallback, external GetSurfaceLevel,\n// UpdateSurface or UpdateTexture) permanently retires that texture's shadow\n// instead of allowing stale CPU data to overwrite newer GPU contents.''',
'''// Lock/Unlock operation stable while the registry is changed. Borrowing a\n// level surface is allowed while its mutating entry points are observed; actual\n// external writes (surface LockRect/GetDC, StretchRect, ColorFill, Update*, or\n// mip generation) retire the shadow instead of risking a stale CPU overwrite.''')
replace(p,
'''            if (shadow) shadow->Release();\n            ++R14ShadowCreateFailed;\n            if (!R14FirstFallbackLogged.exchange(true))\n            {\n                spdlog::warn(\n                    "VR R14 EX: lifetime/coherency hooks or CPU shadow unavailable; this MANAGED texture remains on the R13 direct-GPU compatibility path");\n            }\n            return hr;''',
'''            if (shadow) shadow->Release();\n            if (*texture)\n            {\n                (*texture)->Release();\n                *texture = nullptr;\n            }\n            ++R14ShadowCreateFailed;\n            ++OutRunVRD3D9ExUpgrade::ManagedCreateFailures;\n            if (!R14FirstFallbackLogged.exchange(true))\n            {\n                spdlog::error(\n                    "VR R14 EX: MANAGED 2D compatibility shadow/hooks unavailable; resource creation fails closed instead of exposing weaker R13 direct-lock semantics");\n            }\n            return D3DERR_NOTAVAILABLE;''')

print('DX9Ex follow-up hardening applied')
