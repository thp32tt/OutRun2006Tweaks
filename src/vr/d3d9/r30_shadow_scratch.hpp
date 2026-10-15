#pragma once
// CPU scratch for shipped R26+HUD stereo VB/IB shadow readback and indexed-UP
// rebasing. Unlike CPU *shadow* storage this is temporary write-only staging:
// each consumer must overwrite the WHOLE logical [0,size) before reading it.
// No allocation or resize event proves that a byte came from the game.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <memory>

namespace OutRunVR::R30ScratchBytes
{
    class WriteOnlyByteScratch final
    {
        std::unique_ptr<std::uint8_t[]> data_;
        std::size_t size_ = 0;
        std::size_t capacity_ = 0;
    public:
        WriteOnlyByteScratch() = default;
        WriteOnlyByteScratch(const WriteOnlyByteScratch&) = delete;
        WriteOnlyByteScratch& operator=(const WriteOnlyByteScratch&) = delete;
        std::uint8_t* data() noexcept { return data_.get(); }
        const std::uint8_t* data() const noexcept { return data_.get(); }
        std::size_t size() const noexcept { return size_; }
        std::size_t capacity() const noexcept { return capacity_; }

        // Destructive on growth: old content is intentionally not copied.
        // Both R30Copy*Shadow paths and the UP index-rebase loop overwrite
        // every requested byte before consumption. Allocation exceptions are
        // handled by the caller's existing E_NOTIMPL/original-draw fallback.
        void resize(std::size_t requested)
        {
            if (requested <= capacity_)
            {
                size_ = requested;
                return;
            }
            // Like vector capacity growth, avoid O(N^2) reallocations on
            // slowly increasing primitive sizes. These callers already
            // bound requests by the D3D buffer/index admission gates.
            const std::size_t growth = capacity_ + capacity_ / 2u;
            const std::size_t next = (std::max)(requested, growth);
            std::unique_ptr<std::uint8_t[]> replacement{new std::uint8_t[next]};
            data_.swap(replacement);
            capacity_ = next;
            size_ = requested;
        }
        void clear() noexcept
        {
            data_.reset();
            size_ = 0;
            capacity_ = 0;
        }
    };
}
