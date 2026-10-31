#pragma once
#include <cstdint>
#include <cstring>

namespace OutRunVR::ProjectedLens
{
    // The 2026-10-31 Quest trace proves these two C993 objects are submitted
    // synchronously through the original 405360 -> 4052C0 -> 405890 -> 404700
    // path while their source wrapper is still on the stack. 0x57000F/010 are
    // deferred SceneD44B objects in that run and must not inherit this owner.
    constexpr bool IsExactInlineC993Object(std::uint32_t objectId) noexcept
    {
        return objectId == 0x570002u || objectId == 0x570006u;
    }

    struct InlineFlushReceipt
    {
        std::uint64_t sourceSerial = 0;
        std::uint64_t sequence = 0;
        std::uint32_t objectId = 0;
        bool valid = false;
    };
    inline thread_local InlineFlushReceipt CurrentInlineFlush{};

    class ScopedInlineFlush final
    {
        InlineFlushReceipt previous_{};
    public:
        explicit ScopedInlineFlush(InlineFlushReceipt receipt) noexcept
            : previous_(CurrentInlineFlush)
        {
            CurrentInlineFlush = receipt;
        }
        ~ScopedInlineFlush() noexcept
        {
            CurrentInlineFlush = previous_;
        }
        ScopedInlineFlush(const ScopedInlineFlush&) = delete;
        ScopedInlineFlush& operator=(const ScopedInlineFlush&) = delete;
    };

    struct InlinePmtReceipt
    {
        std::uint64_t sourceSerial = 0;
        std::uint64_t sequence = 0;
        std::uint32_t objectId = 0;
        std::uint32_t pass = 0;
        std::uintptr_t object = 0;
        std::uintptr_t node = 0;
        std::uintptr_t mesh = 0;
        bool valid = false;
    };
    inline thread_local InlinePmtReceipt CurrentInlinePmt{};

    class ScopedInlinePmt final
    {
        InlinePmtReceipt previous_{};
    public:
        explicit ScopedInlinePmt(InlinePmtReceipt receipt) noexcept
            : previous_(CurrentInlinePmt)
        {
            CurrentInlinePmt = receipt;
        }
        ~ScopedInlinePmt() noexcept
        {
            CurrentInlinePmt = previous_;
        }
        ScopedInlinePmt(const ScopedInlinePmt&) = delete;
        ScopedInlinePmt& operator=(const ScopedInlinePmt&) = delete;
    };

    struct RawWvpStamp
    {
        std::uint64_t sourceSerial = 0;
        std::uint64_t sequence = 0;
        std::uint32_t objectId = 0;
        std::uint8_t callsite = 0;
        std::uint64_t writtenDraw = 0;
        std::uint64_t poseEpoch = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        bool cameraSynced = false;
        bool valid = false;
    };

    struct RawWvpSnapshot
    {
        float raw[16]{};
        RawWvpStamp stamp{};

        void Reset() noexcept
        {
            stamp = {};
        }
        bool Valid() const noexcept
        {
            return stamp.valid;
        }
    };

    constexpr bool SameInlinePmt(
        const InlinePmtReceipt& a, const InlinePmtReceipt& b) noexcept
    {
        return a.valid && b.valid &&
            a.sourceSerial != 0 && a.sourceSerial == b.sourceSerial &&
            a.sequence != 0 && a.sequence == b.sequence &&
            IsExactInlineC993Object(a.objectId) &&
            a.objectId == b.objectId &&
            a.pass == 1u && b.pass == 1u &&
            a.object != 0 && a.object == b.object &&
            a.node != 0 && a.node == b.node &&
            a.mesh != 0 && a.mesh == b.mesh;
    }

    // A recorded raw WVP may be used only by the same exact synchronous C993
    // source and exact original PMT. Generic SceneEffect age/shader proximity
    // and live GPU c64 are deliberately insufficient.
    constexpr bool OwnsRawWvp(
        const RawWvpStamp& raw,
        const InlinePmtReceipt& pmt,
        std::uint64_t currentSourceSerial,
        std::uint64_t currentSequence,
        std::uint32_t currentObject,
        std::uint8_t currentCallsite,
        std::uint64_t currentPoseEpoch,
        std::uint64_t currentDraw,
        std::uintptr_t currentShader,
        std::uint64_t currentShaderEpoch) noexcept
    {
        return raw.valid && pmt.valid &&
            IsExactInlineC993Object(currentObject) &&
            currentCallsite == 1u &&
            currentSourceSerial != 0 &&
            currentSourceSerial == raw.sourceSerial &&
            currentSourceSerial == pmt.sourceSerial &&
            currentSequence != 0 &&
            currentSequence == raw.sequence &&
            currentSequence == pmt.sequence &&
            currentObject == raw.objectId &&
            currentObject == pmt.objectId &&
            raw.callsite == 1u &&
            pmt.pass == 1u &&
            pmt.object != 0 && pmt.node != 0 && pmt.mesh != 0 &&
            currentPoseEpoch != 0 &&
            currentPoseEpoch == raw.poseEpoch &&
            currentDraw > raw.writtenDraw &&
            currentDraw - raw.writtenDraw <= 128u &&
            currentShader != 0 && currentShader == raw.shader &&
            currentShaderEpoch != 0 &&
            currentShaderEpoch == raw.shaderEpoch;
    }

    constexpr InlinePmtReceipt TestPmt(std::uint32_t objectId) noexcept
    {
        return { 11u, 7u, objectId, 1u, 0x100u, 0x200u, 0x300u, true };
    }
    static_assert(IsExactInlineC993Object(0x570002u));
    static_assert(IsExactInlineC993Object(0x570006u));
    static_assert(!IsExactInlineC993Object(0x57000Fu));
    static_assert(!IsExactInlineC993Object(0x570010u));
    static_assert(OwnsRawWvp(
        {11u,7u,0x570002u,1u,50u,9u,0x400u,3u,true,true},
        TestPmt(0x570002u),
        11u,7u,0x570002u,1u,9u,51u,0x400u,3u));
    static_assert(OwnsRawWvp(
        {12u,8u,0x570006u,1u,70u,10u,0x500u,4u,true,true},
        {12u,8u,0x570006u,1u,0x110u,0x210u,0x310u,true},
        12u,8u,0x570006u,1u,10u,71u,0x500u,4u));
    static_assert(!OwnsRawWvp(
        {11u,7u,0x570002u,1u,50u,9u,0x400u,3u,true,true},
        TestPmt(0x570002u),
        13u,7u,0x570002u,1u,9u,51u,0x400u,3u),
        "a previous C993 source serial must never be borrowed");
    static_assert(!OwnsRawWvp(
        {11u,7u,0x570002u,1u,50u,9u,0x400u,3u,true,true},
        TestPmt(0x570006u),
        11u,7u,0x570002u,1u,9u,51u,0x400u,3u),
        "another C993 material must never borrow the sun-disc matrix");
}
