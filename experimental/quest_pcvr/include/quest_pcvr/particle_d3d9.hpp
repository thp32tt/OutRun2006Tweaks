#pragma once
#ifdef _WIN32
#include "quest_pcvr/particle_stereo.hpp"
#include <d3d9.h>

namespace quest_pcvr {
// The scene owner binds per-eye render target, WVP/pose, alpha/depth/stencil
// state and restores them. The callbacks never update game simulation.
class IParticleD3D9EyeBinder {
public:
    virtual ~IParticleD3D9EyeBinder() = default;
    virtual bool beginEye(unsigned eye, const FrameSubmission& frame) noexcept = 0;
    // Must restore original state even when beginEye failed.
    virtual bool endEye() noexcept = 0;
};

class ParticleD3D9Gpu final : public IParticleGpu {
public:
    ParticleD3D9Gpu(IDirect3DDevice9* device, IParticleD3D9EyeBinder& binder) noexcept;
    ~ParticleD3D9Gpu() override;
    ParticleD3D9Gpu(const ParticleD3D9Gpu&) = delete;
    ParticleD3D9Gpu& operator=(const ParticleD3D9Gpu&) = delete;
    // Required before Reset/ResetEx/device replacement.
    void invalidate() noexcept;
    bool uploadOnce(const void* bytes, std::uint32_t byte_count, std::uint32_t stride,
                    std::uint64_t resource_generation, ParticleGpuSlice& out) noexcept override;
    bool drawEye(unsigned eye, const FrameSubmission& frame,
                 const ParticleGpuSlice& slice, std::uint64_t material_token) noexcept override;
private:
    IDirect3DDevice9* device_{}; // borrowed, caller invalidates before destruction
    IParticleD3D9EyeBinder& binder_;
    IDirect3DVertexBuffer9* buffer_{};
    std::uint64_t generation_{};
    std::uint32_t offset_{};
    static constexpr std::uint32_t kCapacity = 2u * 1024u * 1024u;
};
} // namespace quest_pcvr
#endif
