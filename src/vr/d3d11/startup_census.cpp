#include "startup_census.hpp"
#include "resource_translation.hpp"

namespace outrun::vr::dx11
{
    StartupCensus inspect_source_device(IDirect3DDevice9* device) noexcept
    {
        StartupCensus out{};
        if (!device)
            return out;

        D3DDEVICE_CREATION_PARAMETERS creation{};
        const bool creationValid =
            SUCCEEDED(device->GetCreationParameters(&creation));
        if (creationValid)
            out.behavior_flags = creation.BehaviorFlags;

        if (creationValid)
        {
            IDirect3D9* d3d = nullptr;
            IDirect3D9Ex* d3dEx = nullptr;
            if (SUCCEEDED(device->GetDirect3D(&d3d)) && d3d &&
                SUCCEEDED(d3d->QueryInterface(
                    __uuidof(IDirect3D9Ex),
                    reinterpret_cast<void**>(&d3dEx))) && d3dEx)
            {
                out.adapter_luid_valid = SUCCEEDED(
                    d3dEx->GetAdapterLUID(
                        creation.AdapterOrdinal, &out.adapter_luid));
            }
            if (d3dEx) d3dEx->Release();
            if (d3d) d3d->Release();
        }

        IDirect3DSurface9* backbuffer = nullptr;
        const HRESULT backHr = device->GetBackBuffer(
            0, 0, D3DBACKBUFFER_TYPE_MONO, &backbuffer);
        if (FAILED(backHr) || !backbuffer)
            return out;

        D3DSURFACE_DESC desc{};
        const HRESULT descHr = backbuffer->GetDesc(&desc);
        backbuffer->Release();
        if (FAILED(descHr))
            return out;

        out.observed = true;
        out.width = desc.Width;
        out.height = desc.Height;
        out.source_format = desc.Format;
        const auto format = translate_resource_format(desc.Format, ResourceRole::Color);
        out.native_format = format.format;
        out.multisample = desc.MultiSampleType;
        out.format_supported = format.exact;
        out.single_sample = desc.MultiSampleType == D3DMULTISAMPLE_NONE;
        out.native_bootstrap_compatible =
            out.width != 0 && out.height != 0 &&
            out.format_supported && out.single_sample;
        return out;
    }
}