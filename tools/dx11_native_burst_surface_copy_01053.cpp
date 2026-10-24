// Live menu -> car selection -> race CPU/GDI full-backbuffer burst replay.
// A readback is full-sized even if UpdateSurface/StretchRect dirtied 1 pixel.
#include "../src/vr/d3d11/native_game_surface_replay_budget.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
#include <algorithm>
#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceReplayBudget;
int main() {
    using B = GameNativeSurfaceReplayBudget;
    static_assert(B::full_readback_bytes(1920,1080) == 8294400u);
    static_assert(B::full_readback_bytes(3440,1440) == 19814400u);
    static_assert(B::full_readback_bytes(0,1080) == 0u);
    static_assert(B::full_readback_bytes(65536,65536) == 0u);
    B live{};
    // More than eight genuine 1080p backbuffer edits can precede first
    // native Draw. Every edit gets a fresh canonical full-image snapshot.
    for (std::uint32_t i=0; i<32u; ++i) {
        assert(live.admits(1920,1080));
        live.note_success(1920,1080);
    }
    assert(live.operations == 32u);
    assert(!live.admits(1920,1080)); // full readback bandwidth exhausted
    const auto fixedCount = live.operations, fixedBytes = live.bytes;
    live.note_success(1920,1080);
    assert(live.operations == fixedCount && live.bytes == fixedBytes);
    // Present, Reset and authenticated new full Clear begin a fresh source
    // epoch. The original fallback never requires a native snapshot.
    live.reset();
    assert(live.operations == 0u && live.bytes == 0u);
    for (std::uint32_t i=0u; i<8u; ++i) {
        assert(live.admits(3840,2160));
        live.note_success(3840,2160);
    }
    assert(!live.admits(3840,2160));
    live.reset();
    assert(live.admits(3440,1440)); // resolution Reset and cold first Draw
    live.note_success(3440,1440);
    assert(live.admits(1920,1080)); // budget uses each actual source extent
    assert(!live.admits(65536,65536));
    B runaway{};
    for (std::uint32_t i=0u;i<B::kMaxOperations;++i) {
        assert(runaway.admits(1,1));
        runaway.note_success(1,1);
    }
    assert(!runaway.admits(1,1)); // reject pathological repeated tiny reads

    // 01054: The SAME live bridge calls preDrawSurface.record_consuming() with the
    // mutable GameNativeSurfaceReplayPixels, so overload selection recycles
    // full-screen 1080p CPU/GDI/StretchRect snapshots before first DX11 Draw.
    using S = outrun::vr::dx11::live_game_frame::GameNativePreDrawSurface;
    constexpr std::uintptr_t owner=0x101u, surface=0x202u;
    S nativeFirstDrawSeed{};
    B sourceBudget{};
    std::vector<std::uint8_t> readback;
    const std::size_t fullBytes=std::size_t{1920}*1080u*4u;
    const std::uint8_t* allocationA=nullptr;
    const std::uint8_t* allocationB=nullptr;
    for (std::uint32_t i=1u; i<=20u; ++i) {
        assert(sourceBudget.admits(1920,1080));
        readback.resize(fullBytes);
        std::fill(readback.begin(),readback.end(),static_cast<std::uint8_t>(i));
        const auto* candidate=readback.data();
        if (i==1u) allocationA=candidate;
        if (i==2u) allocationB=candidate;
        if (i==3u) assert(candidate==allocationA);
        assert(nativeFirstDrawSeed.record_consuming(owner,surface,1920,1080,21u,readback));
        sourceBudget.note_success(1920,1080);
        assert(nativeFirstDrawSeed.matches(owner,surface,1920,1080,21u));
        assert(nativeFirstDrawSeed.pixels.data()==candidate);
        assert(nativeFirstDrawSeed.pixels.front()==i);
        assert(nativeFirstDrawSeed.pixels.back()==i);
        if (i==2u) assert(readback.data()==allocationA);
        if (i==3u) assert(readback.data()==allocationB);
    }
    assert(sourceBudget.operations==20u);
    assert(nativeFirstDrawSeed.pixels.front()==20u);
    // Rejected foreign, truncated or aliasing sources cannot corrupt the
    // previously seeded native frame; D3D9 game fallback remains unchanged.
    const auto* stable=nativeFirstDrawSeed.pixels.data();
    std::vector<std::uint8_t> malformed(1u,13u);
    assert(!nativeFirstDrawSeed.record_consuming(owner,surface,1920,1080,21u,malformed));
    assert(!nativeFirstDrawSeed.record_consuming(owner,surface,1920,1080,21u,
                                                 nativeFirstDrawSeed.pixels));
    assert(nativeFirstDrawSeed.pixels.data()==stable);
    assert(nativeFirstDrawSeed.pixels.front()==20u);
    assert(!nativeFirstDrawSeed.matches(owner+1u,surface,1920,1080,21u));
    // Real cold start / Reset may change dimensions before the first Draw.
    readback.resize(std::size_t{3440}*1440u*4u);
    std::fill(readback.begin(),readback.end(),91u);
    const auto* resizedData=readback.data();
    assert(nativeFirstDrawSeed.record_consuming(owner,surface,3440,1440,22u,readback));
    assert(nativeFirstDrawSeed.pixels.data()==resizedData);
    assert(nativeFirstDrawSeed.matches(owner,surface,3440,1440,22u));
    assert(!nativeFirstDrawSeed.matches(owner,surface,1920,1080,21u));
    // Preserve const-source callers: they retain an independent deep copy.
    const std::vector<std::uint8_t> immutable(16u,33u);
    const auto* constPtr=immutable.data();
    assert(nativeFirstDrawSeed.record(owner,surface,2,2,21u,immutable));
    assert(immutable.data()==constPtr && immutable.front()==33u);
    assert(nativeFirstDrawSeed.pixels.data()!=constPtr);
    assert(nativeFirstDrawSeed.pixels==immutable);
    nativeFirstDrawSeed.discard();
    assert(!nativeFirstDrawSeed.active());
}