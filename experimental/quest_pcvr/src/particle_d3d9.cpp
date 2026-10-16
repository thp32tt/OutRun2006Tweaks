#ifdef _WIN32
#include "quest_pcvr/particle_d3d9.hpp"
#include <cstring>

namespace quest_pcvr {
ParticleD3D9Gpu::ParticleD3D9Gpu(IDirect3DDevice9* d, IParticleD3D9EyeBinder& b) noexcept
    : device_(d), binder_(b) {}
ParticleD3D9Gpu::~ParticleD3D9Gpu() { invalidate(); }
void ParticleD3D9Gpu::invalidate() noexcept {
    if (buffer_) { buffer_->Release(); buffer_ = nullptr; }
    generation_ = 0;
    offset_ = 0;
}
bool ParticleD3D9Gpu::uploadOnce(const void* bytes, std::uint32_t byte_count,
                                std::uint32_t stride, std::uint64_t generation,
                                ParticleGpuSlice& out) noexcept {
    out = {};
    if (!device_ || !bytes || !stride || !generation ||
        byte_count == 0 || byte_count > kCapacity || byte_count % stride != 0)
        return false;
    if (generation_ != generation) invalidate();
    if (!buffer_) {
        const HRESULT hr = device_->CreateVertexBuffer(kCapacity,
            D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY, 0, D3DPOOL_DEFAULT,
            &buffer_, nullptr);
        if (FAILED(hr) || !buffer_) return false;
        offset_ = 0;
        generation_ = generation;
    }
    const std::uint32_t alignment = (stride - (offset_ % stride)) % stride;
    const bool discard = offset_ == 0 || byte_count > kCapacity - offset_ ||
                         alignment > kCapacity - offset_ - byte_count;
    const std::uint32_t at = discard ? 0u : offset_ + alignment;
    void* mapped = nullptr;
    const HRESULT hr = buffer_->Lock(at, byte_count, &mapped,
                                     discard ? D3DLOCK_DISCARD : D3DLOCK_NOOVERWRITE);
    if (FAILED(hr) || !mapped) return false;
    std::memcpy(mapped, bytes, byte_count);
    if (FAILED(buffer_->Unlock())) return false;
    offset_ = at + byte_count;
    out = {at, byte_count / stride, stride};
    return true;
}
bool ParticleD3D9Gpu::drawEye(unsigned eye, const FrameSubmission& frame,
                             const ParticleGpuSlice& slice,
                             std::uint64_t /*material_token*/) noexcept {
    if (!device_ || !buffer_ || eye > 1 || frame.generation != generation_ ||
        slice.vertex_count < 3 || slice.vertex_count % 3 || !slice.vertex_stride ||
        slice.byte_offset >= kCapacity ||
        std::uint64_t(slice.byte_offset) +
            std::uint64_t(slice.vertex_count) * slice.vertex_stride > kCapacity)
        return false;
    IDirect3DVertexBuffer9* previous = nullptr;
    UINT old_offset = 0, old_stride = 0;
    if (FAILED(device_->GetStreamSource(0, &previous, &old_offset, &old_stride)))
        return false;
    const bool bound = binder_.beginEye(eye, frame);
    bool drawn = false;
    if (bound && SUCCEEDED(device_->SetStreamSource(0, buffer_, slice.byte_offset, slice.vertex_stride))) {
        drawn = SUCCEEDED(device_->DrawPrimitive(D3DPT_TRIANGLELIST, 0, slice.vertex_count/3));
    }
    const bool restored = SUCCEEDED(device_->SetStreamSource(0, previous, old_offset, old_stride));
    if (previous) previous->Release();
    const bool eyeRestored = binder_.endEye();
    return bound && drawn && restored && eyeRestored;
}
} // namespace quest_pcvr
#endif
