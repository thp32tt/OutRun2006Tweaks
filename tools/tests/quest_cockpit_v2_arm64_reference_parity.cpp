// Independent APK ARM64 FMADD transcription vs active QuestCockpitV2 code.
// Original 240-assignment research file is included verbatim for comparison,
// but no game assets, EXE or APK binary are linked into this smoke test.
#include "../../docs/research/quest_cockpit_body_correction_reconstructed_20261025.cpp"
#include "../../src/vr/game/quest_cockpit_v2_runtime.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <random>

using OutRunVR::QuestCockpitV2::Matrix;
using OutRunVR::QuestCockpitV2::Identity;
using OutRunVR::QuestCockpitV2::ComputeBodyCorrection;

static Matrix Rotate(const float pitch,const float yaw,const float roll,
                     const float tx,const float ty,const float tz) {
    const float cp=std::cos(pitch),sp=std::sin(pitch);
    const float cy=std::cos(yaw),sy=std::sin(yaw);
    const float cr=std::cos(roll),sr=std::sin(roll);
    Matrix m=Identity;
    // Proper rotation Rz * Ry * Rx, row-vector storage.
    m[0]=cr*cy;    m[1]=sr*cp+cr*sy*sp;   m[2]=sr*sp-cr*sy*cp;
    m[4]=-sr*cy;   m[5]=cr*cp-sr*sy*sp;   m[6]=cr*sp+sr*sy*cp;
    m[8]=sy;       m[9]=-cy*sp;           m[10]=cy*cp;
    m[12]=tx;m[13]=ty;m[14]=tz;
    return m;
}
int main() {
    std::mt19937 mt{0x51AEC24u};
    std::uniform_real_distribution<float> rad{-3.0f,3.0f};
    std::uniform_real_distribution<float> pos{-4.0f,4.0f};
    for(int n=0;n<1500;++n) {
        const Matrix a=Rotate(rad(mt),rad(mt),rad(mt),pos(mt),pos(mt),pos(mt));
        const Matrix b=Rotate(rad(mt),rad(mt),rad(mt),pos(mt),pos(mt),pos(mt));
        Matrix actual{};
        assert(ComputeBodyCorrection(a,b,actual));
        const Matrix reference=quest_research::body_correction_from_guest_matrices(a,b);
        for(int k=0;k<16;++k) {
            assert(std::isfinite(reference[k]));
            assert(std::fabs(actual[k]-reference[k])<=0.0015f);
        }
        // Destination must not be overwritten on invalid matrix.
        Matrix corrupted=a;
        corrupted[15]=0.f;
        const auto saved=actual;
        assert(!ComputeBodyCorrection(corrupted,b,actual));
        assert(actual==saved);
    }
}
