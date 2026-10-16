#pragma once
#include "quest_pcvr/vr_core.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace quest_pcvr {
enum class EffectKind : std::uint8_t { Unknown, Smoke, Dust, Gravel, WaterSpray, WaterSurface, Glass, Flare };

struct ParticleDraw {
    FrameSubmission frame{};
    EffectKind kind{EffectKind::Unknown};
    std::uint64_t producer_token{};
    std::uint64_t material_token{};
    std::uint64_t state_serial{};
    std::uint64_t target_serial{};
    std::uint64_t draw_sequence{};
    const void* vertices{};
    std::uint32_t vertex_count{};
    std::uint32_t vertex_stride{};
    bool world_space{};
    bool alpha_blend{};
    bool depth_write_disabled{};
    bool verified_producer{};
};

struct ParticleGpuSlice {
    std::uint32_t byte_offset{};
    std::uint32_t vertex_count{};
    std::uint32_t vertex_stride{};
};
class IParticleGpu {
public:
    virtual ~IParticleGpu() = default;
    virtual bool uploadOnce(const void* bytes, std::uint32_t byte_count,
                            std::uint32_t stride, std::uint64_t resource_generation,
                            ParticleGpuSlice& out) noexcept = 0;
    virtual bool drawEye(unsigned eye_index, const FrameSubmission& frame,
                         const ParticleGpuSlice& slice, std::uint64_t material_token) noexcept = 0;
};
enum class ParticleResult : std::uint8_t {
    NeedsOriginal, // safe fallback: no visible raster output was attempted
    Submitted,     // both eyes rendered; no simulation or effect updates repeated
    FrameInvalid   // partial output may exist: NEVER replay original draws
};
struct ParticleStats {
    std::uint64_t batches{};
    std::uint64_t original_draws_covered{};
    std::uint64_t uploads{};
    std::uint64_t bytes_uploaded{};
    std::uint64_t physical_eye_draws{};
    std::uint64_t rejected_groups{};
    std::uint64_t failed_uploads{};
    std::uint64_t invalid_frames{};
};
class ParticleStereoBatcher final {
public:
    explicit ParticleStereoBatcher(bool enabled = false) noexcept : enabled_(enabled) {}
    void enable(bool yes) noexcept { enabled_ = yes; }
    bool enabled() const noexcept { return enabled_; }
    ParticleResult submit(const ParticleDraw* adjacent, std::size_t count,
                          IParticleGpu& gpu);
    const ParticleStats& stats() const noexcept { return stats_; }
    void resetStats() noexcept { stats_ = {}; }
private:
    static constexpr std::size_t kMaxBatchBytes = 2u * 1024u * 1024u;
    bool enabled_ = false;
    std::vector<std::uint8_t> staging_{};
    ParticleStats stats_{};
};
bool eligible_for_optional_half_resolution(EffectKind kind, bool verified_producer) noexcept;
} // namespace quest_pcvr
