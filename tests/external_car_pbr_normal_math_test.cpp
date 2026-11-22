#include "../src/vr/game/external_car_pbr_normal_math.hpp"
#include <cassert>
#include <cmath>
#include <limits>

int main() {
    using OutRunVR::DinoSidecar::ExternalCarPbrNormalMatrix;
    float output[12]{};
    const float identity[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, 1,2,3,1
    };
    assert(ExternalCarPbrNormalMatrix(identity,output));
    assert(output[0]==1.f && output[5]==1.f && output[10]==1.f);
    const float nonuniform[16]{
        2,0,0,0, 0,3,0,0, 0,0,4,0, 9,8,7,1
    };
    assert(ExternalCarPbrNormalMatrix(nonuniform,output));
    assert(output[0]==0.5f);
    assert(std::abs(output[5]-1.f/3.f)<0.000001f);
    assert(output[10]==0.25f);
    assert(output[3]==0.f && output[7]==0.f && output[11]==0.f);
    const float mirrored[16]{
        -2,0,0,0, 0,3,0,0, 0,0,4,0, 0,0,0,1
    };
    assert(ExternalCarPbrNormalMatrix(mirrored,output));
    assert(output[0]==-0.5f && output[10]==0.25f);
    float singular[16]{};
    for(int n=0;n<16;++n)singular[n]=identity[n];
    singular[0]=0.f;
    assert(!ExternalCarPbrNormalMatrix(singular,output));
    singular[0]=std::numeric_limits<float>::quiet_NaN();
    assert(!ExternalCarPbrNormalMatrix(singular,output));
    assert(!ExternalCarPbrNormalMatrix(nullptr,output));
    assert(!ExternalCarPbrNormalMatrix(identity,nullptr));
}
