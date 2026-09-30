#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVRStereo
{
    void FlushPendingStateBlockResync(IDirect3DDevice9* device) noexcept;
    void DiscardUnreliableDrawCaches() noexcept;
    bool LiveShaderMatches(
        IDirect3DDevice9* device, std::uintptr_t shader) noexcept;
    void ObserveDispatchDraw(IDirect3DDevice9* device) noexcept;
    void NoteDispatchUnstable() noexcept;
    void NoteDispatchFragile() noexcept;
    void NoteDispatchFastWorld() noexcept;
    void NoteDispatchHud() noexcept;
    void NoteDispatchFallback() noexcept;
}
