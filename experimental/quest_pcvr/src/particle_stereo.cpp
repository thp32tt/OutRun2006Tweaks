#include "quest_pcvr/particle_stereo.hpp"
#include <cstring>
#include <limits>

namespace quest_pcvr {
namespace {
bool safe_kind(EffectKind kind) noexcept {
    return kind == EffectKind::Smoke || kind == EffectKind::Dust ||
           kind == EffectKind::Gravel || kind == EffectKind::WaterSpray;
}
bool equal_frame(const FrameSubmission& a, const FrameSubmission& b) noexcept {
    if (a.generation != b.generation || a.frame_id != b.frame_id ||
        a.pose_sample_id != b.pose_sample_id ||
        a.predicted_display_time_ns != b.predicted_display_time_ns) return false;
    for (unsigned i = 0; i != 2; ++i) {
        if (a.eyes[i].generation != b.eyes[i].generation ||
            a.eyes[i].frame_id != b.eyes[i].frame_id ||
            a.eyes[i].pose_sample_id != b.eyes[i].pose_sample_id ||
            a.eyes[i].target_identity != b.eyes[i].target_identity) return false;
    }
    return true;
}
bool valid_draw(const ParticleDraw& d) noexcept {
    return d.verified_producer && safe_kind(d.kind) && d.producer_token != 0 &&
           d.material_token != 0 && d.state_serial != 0 &&
           d.target_serial != 0 && d.draw_sequence != 0 &&
           d.world_space && d.alpha_blend && d.depth_write_disabled &&
           d.vertices != nullptr && d.vertex_count >= 3 &&
           d.vertex_count % 3 == 0 && d.vertex_stride >= 12 &&
           d.vertex_stride <= 256 && valid_stereo_submission(d.frame);
}
bool compatible(const ParticleDraw& a, const ParticleDraw& b) noexcept {
    return a.kind == b.kind && a.producer_token == b.producer_token &&
           a.material_token == b.material_token &&
           a.state_serial == b.state_serial && a.target_serial == b.target_serial &&
           a.vertex_stride == b.vertex_stride &&
           a.draw_sequence != std::numeric_limits<std::uint64_t>::max() &&
           b.draw_sequence == a.draw_sequence + 1 && equal_frame(a.frame, b.frame);
}
}
ParticleResult ParticleStereoBatcher::submit(const ParticleDraw* adjacent,
                                             std::size_t count, IParticleGpu& gpu) {
    if (!enabled_ || !adjacent || count == 0 || count > 512) {
        ++stats_.rejected_groups;
        return ParticleResult::NeedsOriginal;
    }
    std::size_t total = 0;
    for (std::size_t i = 0; i < count; ++i) {
        const auto& d = adjacent[i];
        if (!valid_draw(d) || (i && !compatible(adjacent[i-1], d))) {
            ++stats_.rejected_groups;
            return ParticleResult::NeedsOriginal;
        }
        const std::size_t bytes = std::size_t(d.vertex_count) * d.vertex_stride;
        if (bytes > kMaxBatchBytes - total) {
            ++stats_.rejected_groups;
            return ParticleResult::NeedsOriginal;
        }
        total += bytes;
    }
    try { staging_.resize(total); }
    catch (...) { ++stats_.rejected_groups; return ParticleResult::NeedsOriginal; }
    std::size_t offset = 0;
    for (std::size_t i = 0; i < count; ++i) {
        const std::size_t bytes = std::size_t(adjacent[i].vertex_count) * adjacent[i].vertex_stride;
        std::memcpy(staging_.data() + offset, adjacent[i].vertices, bytes);
        offset += bytes;
    }
    ParticleGpuSlice slice{};
    if (!gpu.uploadOnce(staging_.data(), static_cast<std::uint32_t>(total),
                        adjacent[0].vertex_stride, adjacent[0].frame.generation, slice)) {
        ++stats_.failed_uploads;
        return ParticleResult::NeedsOriginal;
    }
    const auto expected_count = static_cast<std::uint32_t>(total / adjacent[0].vertex_stride);
    if (slice.vertex_count != expected_count || slice.vertex_stride != adjacent[0].vertex_stride) {
        ++stats_.invalid_frames;
        return ParticleResult::FrameInvalid;
    }
    ++stats_.uploads;
    stats_.bytes_uploaded += total;
    for (unsigned eye = 0; eye != 2; ++eye) {
        ++stats_.physical_eye_draws;
        if (!gpu.drawEye(eye, adjacent[0].frame, slice, adjacent[0].material_token)) {
            ++stats_.invalid_frames;
            return ParticleResult::FrameInvalid;
        }
    }
    ++stats_.batches;
    stats_.original_draws_covered += count;
    return ParticleResult::Submitted;
}
bool eligible_for_optional_half_resolution(EffectKind kind, bool verified) noexcept {
    return verified && (kind == EffectKind::Smoke || kind == EffectKind::Dust);
}
} // namespace quest_pcvr
