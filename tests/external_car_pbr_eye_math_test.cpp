#include "../src/vr/game/external_car_pbr_eye_math.hpp"
#include <cassert>
#include <cmath>
#include <limits>

int main() {
    using OutRunVR::DinoSidecar::ExternalPbrEyeConstants;
    float eye[4]{};
    const float left[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, -2,-3,-4,1
    };
    const float right[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, -2.064,-3,-4,1
    };
    assert(ExternalPbrEyeConstants(left,1.f,eye));
    assert(eye[0]==2.f && eye[1]==3.f && eye[2]==4.f && eye[3]==1.f);
    assert(ExternalPbrEyeConstants(right,0.f,eye));
    assert(std::abs(eye[0]-2.064f)<0.0001f);
    assert(eye[3]==0.f);
    const float rotated[16]{
        0,1,0,0, -1,0,0,0, 0,0,1,0, 5,-7,-2,1
    };
    assert(ExternalPbrEyeConstants(rotated,1.f,eye));
    assert(eye[0]==7.f && eye[1]==5.f && eye[2]==2.f && eye[3]==1.f);
    // Nonuniform scale plus shear: transform the recovered eye back to
    // view space; it must map to the camera origin for both eyes.
    const float affine[16]{2,.25f,0,0, 0,3,.5f,0, 0,0,4,0, -4,-9,-16,1};
    assert(ExternalPbrEyeConstants(affine,1.f,eye));
    for(unsigned col=0;col<3;++col){
        float p=affine[12+col];
        for(unsigned row=0;row<3;++row)p+=eye[row]*affine[4*row+col];
        assert(std::abs(p)<0.00001f);
    }
    float singular[16]{1,0,0,0, 1,0,0,0, 0,0,1,0, 0,0,0,1};
    assert(!ExternalPbrEyeConstants(singular,1.f,eye));
    float projective[16]{1,0,0,.5f, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    assert(!ExternalPbrEyeConstants(projective,1.f,eye));
    float invalid[16]{};
    for(int i=0;i<16;++i)invalid[i]=left[i];
    invalid[4]=std::numeric_limits<float>::quiet_NaN();
    assert(!ExternalPbrEyeConstants(invalid,0.f,eye));
    assert(!ExternalPbrEyeConstants(left,
        std::numeric_limits<float>::infinity(),eye));
    assert(!ExternalPbrEyeConstants(nullptr,1.f,eye));
    assert(!ExternalPbrEyeConstants(left,1.f,nullptr));
}
