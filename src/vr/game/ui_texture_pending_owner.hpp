#pragma once
// Each native get_texture -> put_sprite_ex2 lookup belongs to the calling
// game thread. A global pointer/texture-id pair could be replaced by an
// unrelated loading/UI producer between the original get and sprite call.
namespace OutRunVR::UiTexture
{
    struct PendingLookup final
    {
        void* texture = nullptr;
        int textureId = 0;
        void* maskTexture = nullptr;
        int maskTextureId = 0;

        void Advance(void* nativeTexture, int id, bool eligible) noexcept
        {
            // Preserve the exact old 2-slot lookup order. A following
            // get_texture turns the previous UI source into the mask source.
            maskTexture = texture;
            maskTextureId = textureId;
            texture = eligible && nativeTexture ? nativeTexture : nullptr;
            textureId = texture ? id : 0;
        }

        void Clear() noexcept
        {
            texture = nullptr;
            textureId = 0;
            maskTexture = nullptr;
            maskTextureId = 0;
        }
    };

    // Header-inline TLS is one instance per producer thread throughout the
    // x86 DLL, without allocating or locking in native sprite hot paths.
    inline thread_local PendingLookup CurrentLookup{};
}