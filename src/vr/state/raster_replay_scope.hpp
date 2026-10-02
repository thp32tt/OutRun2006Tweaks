#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    struct RasterReplayToken
    {
        IDirect3DDevice9* device = nullptr;
        bool outer = false;
        bool stateValid = false;
    };

    void BeginRasterReplay(
        RasterReplayToken& token, IDirect3DDevice9* device) noexcept;
    void EndRasterReplay(RasterReplayToken& token) noexcept;

    class RasterReplayScope final
    {
    public:
        explicit RasterReplayScope(IDirect3DDevice9* device) noexcept
        {
            BeginRasterReplay(token_, device);
        }

        ~RasterReplayScope()
        {
            EndRasterReplay(token_);
        }

        RasterReplayScope(const RasterReplayScope&) = delete;
        RasterReplayScope& operator=(const RasterReplayScope&) = delete;

        bool Valid() const noexcept { return token_.stateValid; }

    private:
        RasterReplayToken token_{};
    };
}
