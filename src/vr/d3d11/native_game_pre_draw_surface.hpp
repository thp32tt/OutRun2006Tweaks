#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
// A real D3D9 UpdateSurface/StretchRect can change the game backbuffer
// between its full Clear and first native Draw. Capture current color
// while the original game owns it, then seed the first native SM3/FVF
// frame. Opt-in CPU-staged compatibility only, NOT GPU-only XR transport.
struct GameNativePreDrawSurface {
    static constexpr std::uint64_t kMaxPixels = 16ull*1024ull*1024ull;
    std::uintptr_t owner{}, target{};
    std::uint32_t width{}, height{}, format{};
    std::vector<std::uint8_t> pixels;
    [[nodiscard]] static constexpr bool capture_allowed(
        bool seeded, bool contiguous, bool beforeFirstDraw,
        bool pending, bool cpuWriteOpen,
        bool authenticatedCpuFinish = false) noexcept {
        // An open CPU/GDI write is NOT a valid native snapshot. Only its
        // matching, successful UnlockRect/ReleaseDC may capture the full
        // current D3D9 color, before any native Draw has been admitted.
        return seeded && contiguous && beforeFirstDraw && !pending &&
            (!cpuWriteOpen || authenticatedCpuFinish);
    }
    [[nodiscard]] static constexpr bool size_allowed(
        std::uint32_t w, std::uint32_t h) noexcept {
        return w && h && std::uint64_t(w)*h<=kMaxPixels;
    }
    // The backbuffer's actual D3D9 desc is authoritative before any native
    // render target has been created. Reject mismatched source extent/format
    // and unbounded CPU staging even on a cold menu frame or after Reset.
    [[nodiscard]] static constexpr bool source_matches_canonical(
        std::uint32_t w, std::uint32_t h, std::uint32_t fmt,
        std::uint32_t canonicalW, std::uint32_t canonicalH,
        std::uint32_t canonicalFmt) noexcept {
        return fmt != 0u && size_allowed(w,h) &&
            w == canonicalW && h == canonicalH && fmt == canonicalFmt;
    }
    // Before the first source Draw, the native frame target may be 0x0 or
    // retain a previous resolution. The later SM3/FVF Draw verifies the
    // staged snapshot against the newly allocated target. Post-Draw copies
    // must match its CURRENT dimensions before touching native GPU pixels.
    [[nodiscard]] static constexpr bool capture_extent_allowed(
        bool preDrawCopy, bool postDrawCopy,
        std::uint32_t w, std::uint32_t h,
        std::uint32_t nativeW, std::uint32_t nativeH) noexcept {
        return size_allowed(w,h) &&
            (preDrawCopy || (postDrawCopy &&
                             w == nativeW && h == nativeH));
    }
    [[nodiscard]] bool active() const noexcept { return owner!=0u; }
    // Called only AFTER a successful, source-authenticated full D3D9 RT0
    // ColorFill has been admitted for native replay. Foreign game cameras
    // cannot retire the staged real main backbuffer CPU/GDI color.
    void discard_if_canonical_full_write(std::uintptr_t device,
                                         std::uintptr_t surface) noexcept {
        if (owner != 0u && target != 0u && owner == device &&
            target == surface) discard();
    }
    void discard() noexcept {
        owner=target=0u; width=height=format=0u; pixels.clear();
    }
    [[nodiscard]] bool matches(std::uintptr_t device, std::uintptr_t surface,
        std::uint32_t w, std::uint32_t h,
        std::uint32_t fmt) const noexcept {
        return owner && target && owner==device && target==surface &&
            width==w && height==h && format==fmt && size_allowed(w,h) &&
            pixels.size()==static_cast<std::size_t>(w)*h*4u;
    }
    // An authenticated D3D9 source backbuffer readback is disposable once
    // the native first-Draw seed owns its pixels. Exchange its allocation
    // with the previous seed instead of allocating and recopying a complete
    // 1080p/1440p frame on every menu/car/race CPU/GDI surface mutation.
    // Validation precedes the noexcept swap; failed captures keep the seed.
    [[nodiscard]] bool record_consuming(std::uintptr_t device, std::uintptr_t surface,
        std::uint32_t w, std::uint32_t h, std::uint32_t fmt,
        std::vector<std::uint8_t>& source) noexcept {
        if (!device || !surface || !fmt || !size_allowed(w,h) ||
            &source == &pixels ||
            source.size()!=static_cast<std::size_t>(w)*h*4u) return false;
        pixels.swap(source);
        owner=device; target=surface; width=w; height=h; format=fmt;
        return true;
    }
    // Existing record() callers are copy-preserving, whether their vector
    // happens to be const or mutable. Only the authenticated game-readback
    // observer opts into consuming its disposable staging allocation.
    // Read-only source snapshots retain the previous deep-copy semantics.
    [[nodiscard]] bool record(std::uintptr_t device, std::uintptr_t surface,
        std::uint32_t w, std::uint32_t h, std::uint32_t fmt,
        const std::vector<std::uint8_t>& source) noexcept {
        if (!device || !surface || !fmt || !size_allowed(w,h) ||
            source.size()!=static_cast<std::size_t>(w)*h*4u) return false;
        try {
            std::vector<std::uint8_t> stable(source);
            pixels.swap(stable);
            owner=device; target=surface; width=w; height=h; format=fmt;
            return true;
        } catch (...) { discard(); return false; }
    }
};
}