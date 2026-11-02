#include "../../src/vr/game/quest_cockpit_v2_occupant.hpp"
#include "../../docs/research/quest_cockpit_v2_occupant_model_compose_20261026.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
#include <random>
using namespace OutRunVR::QuestCockpitV2;
int main() {
    const Matrix eye=Identity;
    assert(VerifiedPlayerOccupantScope(true,true,true,true,true,true,true,true,false));
    for(int i=0;i<9;++i){
        bool flags[9]{true,true,true,true,true,true,true,true,false};
        flags[i]=i==8?true:false;
        assert(!VerifiedPlayerOccupantScope(flags[0],flags[1],flags[2],
            flags[3],flags[4],flags[5],flags[6],flags[7],flags[8]));
    }
    // Non-commuting 4x4 matrices and actual original research comparator.
    std::mt19937 rng(0x514e60u);
    std::uniform_real_distribution<float> u(-1.f,1.f);
    for(int n=0;n<1200;++n) {
        Matrix w=eye,c=eye,expected{},got{};
        for(int k=0;k<16;++k){w[k]=u(rng);c[k]=u(rng);}
        w[3]=w[7]=w[11]=0.f;w[15]=1.f;
        c[3]=c[7]=c[11]=0.f;c[15]=1.f;
        assert(quest_cockpit_research::ComposeOccupantModelRightCorrection(
            w,c,expected));
        assert(ComposeOccupantModel(w,c,got));
        for(int k=0;k<16;++k)
            assert(std::fabs(expected[k]-got[k])<1.e-5f);
        Matrix work=w;
        {ScopedOriginalRobotWorkMatrix scope(work.data(),got,true);
            assert(scope.Active());
            assert(std::memcmp(work.data(),got.data(),sizeof(Matrix))==0);
        }
        assert(work==w);
        try {
            ScopedOriginalRobotWorkMatrix scope(work.data(),got,true);
            throw 47;
        }catch(int){}
        assert(work==w);
        {ScopedOriginalRobotWorkMatrix scope(work.data(),got,false);
            assert(!scope.Active());}
        assert(work==w);
        auto invalid=c;invalid[0]=std::numeric_limits<float>::quiet_NaN();
        const auto before=got;
        assert(!ComposeOccupantModel(w,invalid,got));assert(got==before);
    }
    Matrix translated=eye;translated[12]=7.f;
    Matrix reflection=eye;reflection[5]=-1.f;
    Matrix out{};
    assert(ComposeOccupantModel(translated,reflection,out));
    assert(out[13]==0.f&&out[12]==7.f&&out[5]==-1.f);
}