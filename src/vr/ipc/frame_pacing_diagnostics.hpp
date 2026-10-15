#pragma once
// Optional frame-identity-linked CPU/QPC diagnostics. Frame.v2 ABI is unchanged.
// This data never authorizes frame selection, a GPU fence, or an XR submit.
#include "vr/ipc/protocol.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <cstring>
namespace OutRunVR::Pacing
{
    inline constexpr std::uint32_t BeginLo = 12, BeginHi = 13;
    inline constexpr std::uint32_t PublishLo = 14, PublishHi = 15;
    inline bool Enabled() noexcept
    {
        static const bool on = [] {
            const char* v = std::getenv("OUTRUN_VR_PACING_DIAGNOSTICS");
            return v && (std::strcmp(v, "1") == 0 ||
                std::strcmp(v, "true") == 0 || std::strcmp(v, "on") == 0);
        }();
        return on;
    }
    inline std::atomic<std::int64_t> firstGameBeginQpc{0};
    inline void GameBegin(std::int64_t qpc) noexcept
    {
        if (!Enabled() || qpc <= 0) return;
        std::int64_t empty = 0;
        firstGameBeginQpc.compare_exchange_strong(empty, qpc, std::memory_order_relaxed);
    }
    inline void GamePresentComplete() noexcept
    {
        if (Enabled()) firstGameBeginQpc.store(0, std::memory_order_relaxed);
    }
    inline void StoreQpc(SharedRenderFrameState& frame, std::uint32_t lo,
        std::int64_t qpc) noexcept
    {
        const auto bits = qpc > 0 ? static_cast<std::uint64_t>(qpc) : 0ull;
        frame.reserved[lo] = static_cast<std::uint32_t>(bits);
        frame.reserved[lo + 1] = static_cast<std::uint32_t>(bits >> 32);
    }
    inline std::int64_t ReadQpc(const SharedRenderFrameState& frame,
        std::uint32_t lo) noexcept
    {
        const auto bits = static_cast<std::uint64_t>(frame.reserved[lo]) |
            (static_cast<std::uint64_t>(frame.reserved[lo + 1]) << 32);
        return bits <= 0x7fffffffffffffffull ?
            static_cast<std::int64_t>(bits) : 0;
    }
    inline void StampPublished(SharedRenderFrameState& frame,
        std::int64_t publishQpc, bool inFlight) noexcept
    {
        if (!Enabled() || inFlight || frame.frameId == 0) return;
        const auto begin = firstGameBeginQpc.load(std::memory_order_relaxed);
        if (begin <= 0 || frame.presentQpc < begin ||
            publishQpc < frame.presentQpc) return;
        StoreQpc(frame, BeginLo, begin);
        StoreQpc(frame, PublishLo, publishQpc);
    }
    inline double DurationMs(std::int64_t begin, std::int64_t end,
        std::int64_t qpcHz) noexcept
    {
        // -1 is missing/invalid; never turn it into a claimed 0-ms stage.
        if (begin <= 0 || end < begin || qpcHz <= 0) return -1.0;
        const auto elapsed = end - begin;
        if (elapsed > qpcHz * 10) return -1.0;
        return static_cast<double>(elapsed) * 1000.0 /
            static_cast<double>(qpcHz);
    }
    inline bool IsNewer(std::uint32_t oldId, std::uint32_t newId) noexcept
    {
        const std::uint32_t delta = newId - oldId;
        return oldId == 0 || (delta != 0 && delta < 0x80000000u);
    }
    struct Sample
    {
        std::uint64_t xrTick{};
        std::uint32_t frameId{};
        std::uint32_t runGeneration{};
        bool cached{};
        double gameRenderMs{-1.0};
        double gamePresentMs{-1.0};
        double presentToConsumeMs{-1.0};
        double hostCaptureMs{-1.0};
        double hostCopyMs{-1.0};
        double hostRenderMs{-1.0};
        double xrWaitMs{-1.0};
        double xrEndMs{-1.0};
    };
    class Buffer
    {
        std::array<Sample, 256> entries_{};
        std::size_t start_{}, count_{};
        std::uint32_t lastId_{}, lastGeneration_{};
        std::uint64_t dropped_{};
        bool enabled_;
    public:
        explicit Buffer(bool enabled = Enabled()) noexcept : enabled_(enabled) {}
        bool Push(const Sample& sample) noexcept
        {
            if (!enabled_) return false;
            if (!sample.frameId || !sample.runGeneration) return false;
            if (lastGeneration_ == sample.runGeneration)
            {
                if (!sample.cached && !IsNewer(lastId_, sample.frameId))
                    return false;
                if (sample.cached && sample.frameId != lastId_)
                    return false;
            }
            else if (sample.cached)
                return false;
            if (count_ == entries_.size())
            {
                start_ = (start_ + 1) % entries_.size();
                --count_;
                ++dropped_;
            }
            entries_[(start_ + count_) % entries_.size()] = sample;
            ++count_;
            lastId_ = sample.frameId;
            lastGeneration_ = sample.runGeneration;
            return true;
        }
        template<class Sink> void Drain(Sink&& sink)
        {
            while (count_)
            {
                sink(entries_[start_]);
                start_ = (start_ + 1) % entries_.size();
                --count_;
            }
        }
        std::size_t Size() const noexcept { return count_; }
        std::uint64_t Dropped() const noexcept { return dropped_; }
    };
}
