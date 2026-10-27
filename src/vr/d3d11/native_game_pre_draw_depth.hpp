#pragma once
#include "native_game_source_mutation.hpp"
#include <array>
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Original D3D9 whole-Z Clear -> partial Z region(s) -> first native Z Draw.
// Native GPU depth is only allocated on the first real game Draw.
struct GameNativePreDrawDepth {
    struct Tile { std::int64_t left{}, top{}, right{}, bottom{}; float z{}; };
    static constexpr std::uint32_t kCapacity=32u;
    // One original D3D9 Clear may contain more source rectangles than the
    // bounded GPU replay ledger. Fully hidden older depth writes are retired
    // while preserving the final per-pixel Z value and source order.
    static constexpr std::uint32_t kMaxSourceRects=
        GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects;
    std::array<Tile,kCapacity> tiles{};
    std::uintptr_t device{},backbuffer{},depth{};
    std::uint32_t count{};
    constexpr void discard() noexcept { device=backbuffer=depth=0u;count=0u; }
    [[nodiscard]] constexpr bool replay_ready(
        std::uintptr_t owner,std::uintptr_t rt,std::uintptr_t ds,
        std::uint32_t w,std::uint32_t h) const noexcept {
        if(!count)return true;
        if(count>kCapacity||!owner||!rt||!ds||owner!=device||
           rt!=backbuffer||ds!=depth||!w||!h||w>0x7fffffffu||h>0x7fffffffu)
            return false;
        for(std::uint32_t i=0;i<count;++i){
            const auto& p=tiles[i];
            if(p.left<0||p.top<0||p.right<=p.left||p.bottom<=p.top||
               p.right>w||p.bottom>h||!(p.z>=0.f&&p.z<=1.f))return false;
        }
        return true;
    }
    template<class Rect>
    [[nodiscard]] constexpr bool record(
        std::uintptr_t owner,std::uintptr_t rt,std::uintptr_t ds,
        std::uint32_t w,std::uint32_t h,
        std::uint32_t vx,std::uint32_t vy,std::uint32_t vw,std::uint32_t vh,
        std::uint32_t n,const Rect* rects,float z) noexcept {
        if(!owner||!rt||!ds||!(z>=0.f&&z<=1.f)||
           n>kMaxSourceRects||(n&&!rects)||
           (count&&!replay_ready(owner,rt,ds,w,h)))return false;
        auto staged=*this; // Entire original D3D9 call commits or none.
        for(std::uint32_t i=0;i<(n?n:1u);++i){
            // D3DRECT source LONG may be negative: never cast to UINT.
            const std::int64_t l=n?std::int64_t(rects[i].x1):vx;
            const std::int64_t t=n?std::int64_t(rects[i].y1):vy;
            const std::int64_t r=n?std::int64_t(rects[i].x2):std::int64_t(vx)+vw;
            const std::int64_t b=n?std::int64_t(rects[i].y2):std::int64_t(vy)+vh;
            GameNativeSourceMutation::TargetClearRect out{};
            const auto kind=GameNativeSourceMutation::classify_target_clear_rect(
                l,t,r,b,vx,vy,vw,vh,w,h,out);
            if(kind==GameNativeSourceMutation::TargetClearClip::Invalid)return false;
            if(kind==GameNativeSourceMutation::TargetClearClip::Empty)continue;
            const Tile next{out.left,out.top,out.right,out.bottom,z};
            const auto covers=[](const Tile& outer,const Tile& inner) constexpr {
                return outer.left<=inner.left && outer.top<=inner.top &&
                    outer.right>=inner.right && outer.bottom>=inner.bottom;
            };
            // An immediate prior write of the identical Z already owns all
            // these pixels. Never elide an earlier same-Z tile across an
            // intervening different-Z writer.
            if(staged.count && staged.tiles[staged.count-1u].z==z &&
               covers(staged.tiles[staged.count-1u],next))continue;
            // A later opaque D3D9 Z Clear replaces *every* entirely covered
            // previous tile, including differently-valued Z and intervening
            // source writes. Reject capacity BEFORE mutating the transaction.
            std::uint32_t retained=0u;
            for(std::uint32_t j=0u;j<staged.count;++j)
                if(!covers(next,staged.tiles[j]))++retained;
            if(retained>=kCapacity)return false;
            std::uint32_t output=0u;
            for(std::uint32_t j=0u;j<staged.count;++j) {
                const Tile prior=staged.tiles[j];
                if(!covers(next,prior))staged.tiles[output++]=prior;
            }
            staged.count=output;
            if(staged.count==kCapacity)return false;
            if(!staged.count){staged.device=owner;staged.backbuffer=rt;staged.depth=ds;}
            staged.tiles[staged.count++]=next;
        }
        *this=staged;
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
