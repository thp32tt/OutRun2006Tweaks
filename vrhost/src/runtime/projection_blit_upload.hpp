#pragma once
// CPU/driver upload cache, not a pixel/frame cache. MarkUploaded only after
// successful D3D11 Map/Unmap; reset invalidates both independent eye caches.
namespace OutRunVrProjectionBlit
{
    struct Key
    {
        float uvScaleX = 0.f, uvScaleY = 0.f;
        float uvOffsetX = 0.f, uvOffsetY = 0.f;
        float sdrWhiteScale = 0.f, sourceIsScRgb = 0.f;
    };
    struct Cache
    {
        Key uploaded{};
        bool valid = false;
        bool NeedsUpload(const Key& key) const noexcept
        {
            return !valid ||
                uploaded.uvScaleX != key.uvScaleX ||
                uploaded.uvScaleY != key.uvScaleY ||
                uploaded.uvOffsetX != key.uvOffsetX ||
                uploaded.uvOffsetY != key.uvOffsetY ||
                uploaded.sdrWhiteScale != key.sdrWhiteScale ||
                uploaded.sourceIsScRgb != key.sourceIsScRgb;
        }
        void MarkUploaded(const Key& key) noexcept
        {
            uploaded = key;
            valid = true;
        }
        void Invalidate() noexcept { valid = false; }
    };
}
