#pragma once
// Exact game D3DX output matrix provenance, not a global menu-mode guess.
// The two paths must never both contain the same already transformed quad.
#include <array>
#include <cmath>
#include <cstddef>
namespace OutRunVrMenuQuad {
struct MatrixRecord {
    std::array<float,16> matrix{};
    float sx=0.f, sy=0.f, width=0.f, height=0.f;
    int mode=-1;
    bool valid=false;
};
class ContainedMatrixLedger {
    std::array<MatrixRecord,16> entries_{};
    std::size_t next_=0;
    static bool Admissible(const std::array<float,16>& matrix,
        int mode,float sx,float sy,float width,float height) noexcept {
        if ((mode!=1 && mode!=2) || !std::isfinite(sx) ||
            !std::isfinite(sy) || !std::isfinite(width) ||
            !std::isfinite(height) || sx<=1.e-6f ||
            sy<=1.e-6f || width<=0.f || height<=0.f) return false;
        for(float f:matrix) if(!std::isfinite(f)) return false;
        return true;
    }
public:
    bool Remember(const std::array<float,16>& matrix,int mode,
        float sx,float sy,float width,float height) noexcept {
        if(!Admissible(matrix,mode,sx,sy,width,height))return false;
        entries_[next_++ % entries_.size()] =
            {matrix,sx,sy,width,height,mode,true};
        return true;
    }
    bool Contains(const std::array<float,16>& matrix,int mode,
        float sx,float sy,float width,float height) const noexcept {
        if(!Admissible(matrix,mode,sx,sy,width,height))return false;
        for(const auto& e:entries_)
            if(e.valid && e.mode==mode && e.sx==sx && e.sy==sy &&
               e.width==width && e.height==height &&
               e.matrix==matrix) return true;
        return false;
    }
};
inline thread_local ContainedMatrixLedger ContainedMatrices{};
}
