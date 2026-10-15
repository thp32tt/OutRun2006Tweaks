#pragma once
// Lazy CPU shadow storage for the shipped R26+HUD VB/IB capture path.
// A shadow is NEVER read unless its independent valid-range map covers the
// requested bytes. The old vector::resize(size) zero-filled up to 16 MiB
// before immediately overwriting the observed game Lock/Unlock range.
// Default-initialized byte arrays avoid that redundant full-buffer write.
#include <cstddef>
#include <cstdint>
#include <memory>

namespace OutRunVR::R30ShadowBytes
{
    class LazyUninitializedBuffer
    {
        std::unique_ptr<std::uint8_t[]> data_;
        std::size_t size_ = 0;
    public:
        std::size_t size() const noexcept { return size_; }
        std::uint8_t* data() noexcept { return data_.get(); }
        const std::uint8_t* data() const noexcept { return data_.get(); }
        void clear() noexcept
        {
            data_.reset();
            size_ = 0;
        }
        void resize(std::size_t size)
        {
            if (size == size_ && data_)
                return; // capture writes reuse the same storage
            if (size == 0)
            {
                clear();
                return;
            }
            // Deliberately no parentheses: default-initialized uint8_t
            // has indeterminate values. Only the separate interval map
            // ever permits the stereo renderer to consume observed bytes.
            std::unique_ptr<std::uint8_t[]> replacement{
                new std::uint8_t[size]};
            data_.swap(replacement);
            size_ = size;
        }
    };
}
