#include "vr/game/sprite_uv_transaction.hpp"
#include <cmath>
#include <limits>

struct S2 {
    float left_88=.75f,left_A0=.25f,right_90=.5f,right_98=.125f;
    float bottom_84=.25f,bottom_8C=.5f,top_94=.75f,top_9C=1.f;
};
struct S1 {
    float top_4=.25f,left_8=.5f,bottom_C=.75f,right_10=1.f;
    float scaleX=2.f,scaleY=4.f;
};
static bool near(float a,float b){return std::fabs(a-b)<.000001f;}
#define CHECK(expression) do { if (!(expression)) return __LINE__; } while (false)
int main(){
    S2 parent{},mask{};mask.left_88=.125f;
    const S2 parentOriginal=parent,maskOriginal=mask;
    // Reusing the same source objects must not apply UV replacement twice.
    for(int frame=0;frame!=500;++frame) {
        OutRunVR::SpriteUV::ScopedSprArgs2Scale<S2> p,m;
        CHECK(p.Apply(&parent,2.f,4.f));
        CHECK(m.Apply(&mask,3.f,2.f));
        CHECK(near(parent.left_88,.5f));
        CHECK(near(parent.top_94,3.f));
        CHECK(near(mask.left_88,-1.625f));
        CHECK(!p.Apply(&parent,2.f,4.f));
        m.Restore(); p.Restore();
        CHECK(near(parent.top_94,parentOriginal.top_94));
        CHECK(near(mask.left_88,maskOriginal.left_88));
    }
    S1 sprite{};const S1 original=sprite;
    for(int frame=0;frame!=500;++frame) {
        OutRunVR::SpriteUV::ScopedSprArgsScale<S1> tx;
        CHECK(tx.Apply(&sprite,4.f,2.f));
        CHECK(near(sprite.top_4,.5f));
        CHECK(near(sprite.right_10,4.f));
        CHECK(near(sprite.scaleX,.5f));
        CHECK(near(sprite.scaleY,2.f));
        // Destructor also restores on a normal native-call scope exit.
    }
    CHECK(near(sprite.top_4,original.top_4));
    CHECK(near(sprite.scaleX,original.scaleX));
    const float nan=std::numeric_limits<float>::quiet_NaN();
    for(float bad : {0.f,-1.f,nan,std::numeric_limits<float>::infinity()}){
        OutRunVR::SpriteUV::ScopedSprArgsScale<S1> a;
        OutRunVR::SpriteUV::ScopedSprArgs2Scale<S2> b;
        CHECK(!a.Apply(&sprite,bad,1.f));
        CHECK(!b.Apply(&parent,1.f,bad));
    }
    CHECK(near(sprite.top_4,original.top_4));
    S2 broken=parent;broken.top_94=nan;
    {
        OutRunVR::SpriteUV::ScopedSprArgs2Scale<S2> tx;
        CHECK(!tx.Apply(&broken,2.f,2.f));
    }
    CHECK(near(broken.left_88,parentOriginal.left_88));
    S1 tooBig=sprite;tooBig.top_4=std::numeric_limits<float>::max();
    {
        OutRunVR::SpriteUV::ScopedSprArgsScale<S1> tx;
        CHECK(!tx.Apply(&tooBig,2.f,4.f));
        CHECK(near(tooBig.scaleX,original.scaleX));
    }
    // Nested same-input reentry restores the outer call's converted UVs
    // before outer transaction finally returns the unmodified game data.
    {
        OutRunVR::SpriteUV::ScopedSprArgs2Scale<S2> outer;
        CHECK(outer.Apply(&parent,2.f,4.f));
        {
            OutRunVR::SpriteUV::ScopedSprArgs2Scale<S2> nested;
            CHECK(nested.Apply(&parent,2.f,4.f));
            CHECK(near(parent.left_88,0.f));
        }
        CHECK(near(parent.left_88,.5f));
    }
    CHECK(near(parent.left_88,parentOriginal.left_88));
    CHECK(near(parent.bottom_84,parentOriginal.bottom_84));
    CHECK(near(mask.top_9C,maskOriginal.top_9C));
    return 0;
}
