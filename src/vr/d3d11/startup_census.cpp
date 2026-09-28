#include "startup_census.hpp"

namespace outrun::vr::dx11
{
    namespace
    {
        DXGI_FORMAT translate_backbuffer_format(D3DFORMAT format) noexcept
        {
            switch (format)
            {
            case D3DFMT_A8R8G8B8:
            case D3DFMT_X8R8G8B8:
                return DXGI_FORMAT_B8G8R8A8_UNORM;
            default:
                return DXGI_FORMAT_UNKNOWN;
            }
        }
    }

    StartupCensus inspect_source_device(IDirect3DDevice9* device) noexcept
    {
        StartupCensus out{};
        if (!device)
            return out;

        D3DDEVICE_CREATION_PARAMETERS creation{};
        if (SUCCEEDED(device->GetCreationParameters(&creation)))
            out.behavior_flags = creation.BehaviorFlags;

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
        out.native_format = translate_backbuffer_format(desc.Format);
        out.multisample = desc.MultiSampleType;
        out.format_supported = out.native_format != DXGI_FORMAT_UNKNOWN;
        out.single_sample = desc.MultiSampleType == D3DMULTISAMPLE_NONE;
        out.native_bootstrap_compatible =
            out.width != 0 && out.height != 0 &&
            out.format_supported && out.single_sample;
        return out;
    }
}
