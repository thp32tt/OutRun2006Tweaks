from pathlib import Path


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    found = text.count(old)
    if found < count:
        raise SystemExit(f'{path}: expected {count}, found {found}: {old[:140]!r}')
    p.write_text(text.replace(old, new, count), encoding='utf-8')

# CheckDeviceState failures that cannot be recovered by Reset should look like
# classic driver-internal failure rather than creating an endless lost/reset loop.
p = 'src/vr/d3d9/ex_device_upgrade.cpp'
replace(p,
'''            else if (state == D3DERR_DEVICELOST)\n                translated = D3DERR_DEVICELOST;\n            else if (FAILED(state))\n                translated = D3DERR_DEVICELOST;''',
'''            else if (state == D3DERR_DEVICELOST)\n                translated = D3DERR_DEVICELOST;\n            else if (state == D3DERR_DEVICEHUNG ||\n                state == D3DERR_DEVICEREMOVED)\n                translated = D3DERR_DRIVERINTERNALERROR;\n            else if (FAILED(state))\n                translated = D3DERR_DRIVERINTERNALERROR;''')

# Public bridge used by the final Present chain. Positive 9Ex presentation
# statuses must not leak to a legacy game that expects the classic lost-device
# contract.
p = 'src/vr/d3d9/r13_bridge.hpp'
replace(p,
'''    bool ResetCompatDevice(IDirect3DDevice9* device,\n        D3DPRESENT_PARAMETERS* params, HRESULT& result) noexcept;\n    void DisarmLegacyResetHook() noexcept;''',
'''    bool ResetCompatDevice(IDirect3DDevice9* device,\n        D3DPRESENT_PARAMETERS* params, HRESULT& result) noexcept;\n    HRESULT NormalizeLegacyPresentResult(\n        IDirect3DDevice9* device, HRESULT result) noexcept;\n    void DisarmLegacyResetHook() noexcept;''')

p = 'src/vr/d3d9/ex_device_upgrade_r13.cpp'
anchor = '''    bool ResetCompatDevice(IDirect3DDevice9* device,\n        D3DPRESENT_PARAMETERS* params, HRESULT& result) noexcept\n'''
impl = r'''    HRESULT NormalizeLegacyPresentResult(
        IDirect3DDevice9* device, HRESULT result) noexcept
    {
        if (!OutRunVRD3D9ExUpgrade::IsCompatDevice(device))
            return result;
        if (result == S_PRESENT_MODE_CHANGED)
            return D3DERR_DEVICELOST;
        if (result == S_PRESENT_OCCLUDED)
        {
            return OutRunVRD3D9ExUpgrade::CompatWindowed.load(
                std::memory_order_acquire)
                ? D3D_OK : D3DERR_DEVICELOST;
        }
        return result;
    }

'''
replace(p, anchor, impl + anchor)

# Normalize before R9 decides whether a frame was successfully presented, so
# shared VR metadata cannot claim success for a legacy-visible lost Present.
p = 'src/vr/d3d9/stereo_renderer.cpp'
replace(p,
'''\t\t\tconst HRESULT hr = PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);\n\t\t\tif (composedStereo && SUCCEEDED(hr) && !FrameStereoIncomplete)''',
'''\t\t\tconst HRESULT rawPresentHr = PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);\n\t\t\tconst HRESULT hr = OutRunVRD3D9ExUpgradeR13::NormalizeLegacyPresentResult(\n\t\t\t\tdevice, rawPresentHr);\n\t\t\tif (composedStereo && SUCCEEDED(hr) && !FrameStereoIncomplete)''')

print('Legacy D3D9 Present contract patch applied')
