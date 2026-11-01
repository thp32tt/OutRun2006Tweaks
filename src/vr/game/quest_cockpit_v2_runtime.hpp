// Quest APK cockpit V2 core: isolated, engine-independent C++17 implementation.
// Original Quest: mode == 1, paired vehicle B0/F0 matrices, scoped occupant correction.
// No camera patch, persistent game-memory write, wheel input, or render hook here.
// Admission REQUIRES a proven native game-frame owner; Present/pose alone never suffice.
#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <initializer_list>
#include <algorithm>

namespace OutRunVR::QuestCockpitV2 {
using Matrix = std::array<float, 16>;
inline constexpr Matrix Identity = {{
    1.f,0.f,0.f,0.f, 0.f,1.f,0.f,0.f,
    0.f,0.f,1.f,0.f, 0.f,0.f,0.f,1.f
}};

inline bool FiniteAffine(const Matrix& m) noexcept {
    for (float v : m) if (!std::isfinite(v)) return false;
    constexpr float e = 1.0e-5f;
    return std::fabs(m[3])<=e && std::fabs(m[7])<=e &&
           std::fabs(m[11])<=e && std::fabs(m[15]-1.f)<=e;
}

// Independently verified against the Quest ARM64 arithmetic transcription:
// R=-A^T B^T A; t=(I+A^T B D A)tA - A^T B tB; D=diag(1,-1,1).
// This is an OCCUPANT-MODEL correction (det(R)=-1 for rigid inputs).
// It must never be installed into the OpenXR view, head or eye matrix.
inline bool ComputeBodyCorrection(const Matrix& matrixB0,
                                  const Matrix& matrixF0,
                                  Matrix& output) noexcept {
    if (!FiniteAffine(matrixB0) || !FiniteAffine(matrixF0)) return false;
    double a[3][3]{}, b[3][3]{}, m[3][3]{}, u[3][3]{}, c[3][3]{};
    constexpr double d[3]{1.,-1.,1.};
    for (int i=0;i<3;++i)
        for (int j=0;j<3;++j) {
            a[i][j]=matrixB0[4*i+j];
            b[i][j]=matrixF0[4*i+j];
        }
    for (int i=0;i<3;++i)
        for (int j=0;j<3;++j)
            for (int k=0;k<3;++k)
                m[i][j]+=a[k][i]*b[k][j];
    Matrix tmp{};
    for (int i=0;i<3;++i) {
        for (int j=0;j<3;++j) {
            u[i][j]=(i==j?1.0:0.0);
            for (int k=0;k<3;++k) u[i][j]+=m[i][k]*d[k]*a[k][j];
            for (int k=0;k<3;++k)
                for (int p=0;p<3;++p)
                    c[i][j]-=a[k][i]*b[p][k]*a[p][j];
            tmp[4*i+j]=static_cast<float>(c[i][j]);
        }
        double t=0.;
        for (int k=0;k<3;++k) {
            t+=u[i][k]*static_cast<double>(matrixB0[12+k]);
            t-=m[i][k]*static_cast<double>(matrixF0[12+k]);
        }
        tmp[12+i]=static_cast<float>(t);
    }
    tmp[15]=1.f;
    if (!FiniteAffine(tmp)) return false;
    output=tmp;
    return true;
}

struct FrameInput {
    std::uint64_t nativeGameFrame=0; // must come from verified frame_render_449050
    std::uint64_t xrPoseSequence=0;  // same pose for both eyes
    std::uint32_t xrSpaceGeneration=0;
    std::uintptr_t playerIdentity=0;
    std::uint8_t cameraMode=0;
    bool optionRequested=false, gameplay=false, worldPass=false;
    bool originalPlayerEventVerified=false;
    bool stereoAndPositionValid=false;
    bool sceneEffect=false;
    Matrix matrixB0{}, matrixF0{};
};
struct FrameSnapshot {
    std::uint64_t nativeGameFrame=0, xrPoseSequence=0;
    std::uint32_t xrSpaceGeneration=0;
    std::uintptr_t playerIdentity=0;
    Matrix matrixB0{}, matrixF0{}, occupantCorrection{};
};

inline float SafeNearPlane(float request,float minimum,float maximum,
                          float fallback=0.10f) noexcept {
    if (!std::isfinite(request)||!std::isfinite(minimum)||
        !std::isfinite(maximum)||!std::isfinite(fallback)||
        minimum<=0.f||maximum<minimum) return 0.10f;
    const float safeFallback=std::clamp(fallback,minimum,maximum);
    return request>0.f?std::clamp(request,minimum,maximum):safeFallback;
}

// Pure pass ownership: native Clr_SceneEffect must not inherit cockpit scope.
inline thread_local std::uint32_t SceneEffectDepth=0;
class ScopedSceneEffect final {
public:
    ScopedSceneEffect() noexcept {++SceneEffectDepth;}
    ~ScopedSceneEffect() noexcept {--SceneEffectDepth;}
    ScopedSceneEffect(const ScopedSceneEffect&)=delete;
    ScopedSceneEffect& operator=(const ScopedSceneEffect&)=delete;
};
inline bool InSceneEffect() noexcept {return SceneEffectDepth!=0;}

inline bool NativeEligible(const FrameInput& f) noexcept {
    return f.nativeGameFrame!=0 && f.xrPoseSequence!=0 &&
           f.playerIdentity!=0 && f.cameraMode==1 &&
           f.optionRequested && f.gameplay && f.worldPass &&
           f.originalPlayerEventVerified && f.stereoAndPositionValid &&
           !f.sceneEffect;
}

// Any input change inside ONE native render-frame rejects the entire frame.
// No fallback to a cached camera, previous vehicle, PresentEpoch or XR pose.
class FrameOwner final {
    FrameSnapshot snapshot_{};
    bool initialized_=false, admitted_=false, blocked_=false;
public:
    void Reset() noexcept { snapshot_={};initialized_=admitted_=blocked_=false; }
    bool Observe(const FrameInput& f) noexcept {
        const bool newFrame=!initialized_ || f.nativeGameFrame!=snapshot_.nativeGameFrame;
        // Out-of-order callbacks must never rearm a rejected older frame.
        if (initialized_ && f.nativeGameFrame < snapshot_.nativeGameFrame) {
            admitted_=false;
            blocked_=true;
            return false;
        }
        if (newFrame) {
            initialized_=true;admitted_=false;blocked_=false;
            snapshot_={};snapshot_.nativeGameFrame=f.nativeGameFrame;
            if (!NativeEligible(f)) { blocked_=true; return false; }
            Matrix correction{};
            if (!ComputeBodyCorrection(f.matrixB0,f.matrixF0,correction)) {
                blocked_=true;return false;
            }
            snapshot_.xrPoseSequence=f.xrPoseSequence;
            snapshot_.xrSpaceGeneration=f.xrSpaceGeneration;
            snapshot_.playerIdentity=f.playerIdentity;
            snapshot_.matrixB0=f.matrixB0;
            snapshot_.matrixF0=f.matrixF0;
            snapshot_.occupantCorrection=correction;
            admitted_=true;
        } else if (!NativeEligible(f) ||
                   f.xrPoseSequence!=snapshot_.xrPoseSequence ||
                   f.xrSpaceGeneration!=snapshot_.xrSpaceGeneration ||
                   f.playerIdentity!=snapshot_.playerIdentity ||
                   std::memcmp(f.matrixB0.data(),snapshot_.matrixB0.data(),
                               sizeof(Matrix))!=0 ||
                   std::memcmp(f.matrixF0.data(),snapshot_.matrixF0.data(),
                               sizeof(Matrix))!=0) {
            admitted_=false; blocked_=true;
        }
        return admitted_ && !blocked_;
    }
    bool Active() const noexcept {return initialized_ && admitted_ && !blocked_;}
    const FrameSnapshot* Snapshot() const noexcept {
        return Active()? &snapshot_:nullptr;
    }
};

// Scope a COPY of the render-local vehicle matrix. No EVWORK_CAR mutation.
// Not copyable or movable, restoring even on an exception.
class ScopedRenderMatrixF0 final {
    Matrix& scratch_;
    const Matrix old_;
    bool active_;
public:
    ScopedRenderMatrixF0(Matrix& renderLocalF0, bool admitted) noexcept
        : scratch_(renderLocalF0),old_(renderLocalF0),active_(admitted) {
        if (active_) scratch_=Identity;
    }
    ~ScopedRenderMatrixF0() noexcept { if(active_) scratch_=old_; }
    ScopedRenderMatrixF0(const ScopedRenderMatrixF0&)=delete;
    ScopedRenderMatrixF0& operator=(const ScopedRenderMatrixF0&)=delete;
};

inline std::uint64_t MatrixFingerprint(const Matrix& a, const Matrix& b) noexcept {
    // Bounded FNV-1a observation fingerprint, not original asset/matrix logging.
    std::uint64_t h=1469598103934665603ull;
    for (const Matrix* mat : {&a,&b}) {
        for (float x : *mat) {
            std::uint32_t bits=0;std::memcpy(&bits,&x,sizeof(bits));
            for (int i=0;i<4;++i) {h^=(bits>>(i*8))&0xffu;h*=1099511628211ull;}
        }
    }
    return h;
}
} // namespace OutRunVR::QuestCockpitV2
