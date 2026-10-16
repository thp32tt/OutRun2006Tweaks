#pragma once
#include "r30_particle_upload_policy.hpp"
#include <d3d9.h>
#include <cstdint>
#include <cstring>
#include <mutex>

// Actual Win32 D3D9Ex buffer transport for the already-transformed R30 XYZRHW
// scratch. Each eye has DIFFERENT vertex bytes; the optimization is ONE
// DynamicVB Lock+Unlock for both eyes, not a shared mono vertex projection.
// Caller owns a mutex lock across prepare -> left -> right -> restore.
namespace OutRunVR::R30ParticleUpload {
class DualEyeGpuRing final {
public:
    ~DualEyeGpuRing() { invalidate(); }
    DualEyeGpuRing() = default;
    DualEyeGpuRing(const DualEyeGpuRing&) = delete;
    DualEyeGpuRing& operator=(const DualEyeGpuRing&) = delete;

    std::mutex& mutex() noexcept { return mutex_; }
    void invalidate() noexcept {
        if (buffer_) { buffer_->Release(); buffer_ = nullptr; }
        device_ = nullptr;
        writeOffset_ = 0;
        stride_ = 0;
        leftOffset_ = rightOffset_ = 0;
    }
    bool prepare(IDirect3DDevice9* d, const void* left, const void* right,
                 std::uint32_t vertices, std::uint32_t stride) noexcept {
        if (!d || !left || !right || !stride || !vertices ||
            vertices > kMaxPerEyeBytes / stride)
            return false;
        const std::uint32_t eyeBytes = vertices * stride;
        const std::uint32_t total = eyeBytes * 2;
        if (!total || total > kCapacity) return false;
        if (device_ != d) { invalidate(); device_ = d; }
        if (!buffer_) {
            const HRESULT created = d->CreateVertexBuffer(
                kCapacity, D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY, 0,
                D3DPOOL_DEFAULT, &buffer_, nullptr);
            if (FAILED(created) || !buffer_) return false;
            writeOffset_ = 0;
        }
        const std::uint32_t alignment =
            (stride - (writeOffset_ % stride)) % stride;
        const bool discard = writeOffset_ > kCapacity ||
            alignment > kCapacity - writeOffset_ ||
            total > kCapacity - writeOffset_ - alignment;
        const std::uint32_t start = discard ? 0u : writeOffset_ + alignment;
        void* mapped = nullptr;
        if (FAILED(buffer_->Lock(start, total, &mapped,
                discard || start == 0 ? D3DLOCK_DISCARD : D3DLOCK_NOOVERWRITE))
            || !mapped)
            return false;
        std::memcpy(mapped, left, eyeBytes);
        std::memcpy(static_cast<std::uint8_t*>(mapped) + eyeBytes,
                    right, eyeBytes);
        if (FAILED(buffer_->Unlock())) {
            invalidate();
            return false;
        }
        stride_ = stride;
        leftOffset_ = start;
        rightOffset_ = start + eyeBytes;
        writeOffset_ = start + total;
        return true;
    }
    HRESULT bindEye(unsigned eye) noexcept {
        if (!device_ || !buffer_ || eye > 1 || stride_ == 0) return E_FAIL;
        return device_->SetStreamSource(
            0, buffer_, eye == 0 ? leftOffset_ : rightOffset_, stride_);
    }
    // DrawPrimitiveUP clears stream zero even if a VB was previously set.
    // Restore that original API side-effect after the second eye/error.
    bool finishUp() noexcept {
        return device_ && SUCCEEDED(device_->SetStreamSource(0,nullptr,0,0));
    }
private:
    std::mutex mutex_;
    IDirect3DDevice9* device_ = nullptr; // borrowed; VB holds a COM device ref
    IDirect3DVertexBuffer9* buffer_ = nullptr;
    std::uint32_t writeOffset_ = 0, stride_ = 0;
    std::uint32_t leftOffset_ = 0, rightOffset_ = 0;
};
} // namespace OutRunVR::R30ParticleUpload
