#include "../../src/vr/game/quest_cockpit_v2_occupant.hpp"
#include <cassert>
#include <cmath>
#include <limits>
#include <random>
using namespace OutRunVR::QuestCockpitV2;
int main(){
    assert(VerifiedDriverWorkOwner(0x7A1234,0x7A1234));
    assert(!VerifiedDriverWorkOwner(0,0));
    assert(!VerifiedDriverWorkOwner(0x7A1234,0x7A12AC));
    assert(OriginalOccupantPreviewEligible(true,true,true,true,true,false));
    assert(!OriginalOccupantPreviewEligible(true,true,true,true,false,false));
    assert(!OriginalOccupantPreviewEligible(true,true,true,false,true,false));
    assert(!OriginalOccupantPreviewEligible(true,true,true,true,true,true));
    Matrix W=Identity,C=Identity,out{},wrong{};
    W[12]=3;W[13]=4;W[14]=5;
    C[0]=-1;C[5]=-1;C[10]=-1;
    assert(OriginalOccupantRightCompose(W,C,out));
    assert(out[12]==-3 && out[13]==-4 && out[14]==-5);
    // The opposite C * W keeps translation positive. Noncommuting witness.
    for(int i=0;i<4;++i)for(int j=0;j<4;++j)
        for(int k=0;k<4;++k)
            wrong[i*4+j]+=C[i*4+k]*W[k*4+j];
    assert(wrong[12]==3 && wrong[13]==4 && wrong[14]==5);
    assert(out[12]!=wrong[12]);
    std::mt19937 gen{0x126362};
    std::uniform_real_distribution<float> v{-2,2};
    for(int i=0;i<1000;++i) {
        Matrix a=Identity,b=Identity,o{};
        for(int r=0;r<3;++r)for(int c=0;c<3;++c){
            a[r*4+c]=v(gen);b[r*4+c]=v(gen);
        }
        for(int k=0;k<3;++k){a[12+k]=v(gen);b[12+k]=v(gen);}
        assert(OriginalOccupantRightCompose(a,b,o));
        for(int r=0;r<4;++r)for(int c=0;c<4;++c){
            double expected=0;
            for(int k=0;k<4;++k)expected+=double(a[r*4+k])*b[k*4+c];
            assert(std::fabs(o[4*r+c]-expected)<0.00003);
        }
        Matrix invalid=a;invalid[0]=std::numeric_limits<float>::quiet_NaN();
        const Matrix saved=o;
        assert(!OriginalOccupantRightCompose(invalid,b,o));
        assert(o==saved);
    }
}
