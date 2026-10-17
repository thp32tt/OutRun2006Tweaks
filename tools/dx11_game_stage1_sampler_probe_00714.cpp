#include "../src/vr/d3d11/live_game_stage1_dual_texture.hpp"
#include <cstdio>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    unsigned accepted=0, rejected=0;
    for (unsigned address=0; address<7; ++address)
      for (unsigned min=0; min<5; ++min)
        for (unsigned mag=0; mag<5; ++mag)
          for (unsigned mip=0; mip<4; ++mip) {
            bool expected=address>=1 && address<=5 &&
                (((min==1 || min==2) && (mag==1 || mag==2)) ||
                 (min==3 && (mag==2 || mag==3) && mip==2)) && mip<=2;
            auto good=stage1_game_sampler_supported(address,3,min,mag,mip,0,
                0.0f,min==3?8:1,0);
            if(good!=expected) return 1;
            good ? ++accepted : ++rejected;
          }
    if(accepted==0 || rejected==0) return 2;
    if (!stage1_game_sampler_supported(1,4,2,1,2,2,-2.25f,1,1) ||
        !stage1_game_sampler_supported(5,3,3,3,2,0,0.0f,16,0) ||
        stage1_game_sampler_supported(1,3,3,3,2,0,0.0f,1,0) ||
        stage1_game_sampler_supported(1,3,2,1,0,1,0.0f,1,0) ||
        stage1_game_sampler_supported(1,3,2,1,2,0,16.0f,1,0) ||
        stage1_game_sampler_supported(1,3,2,1,2,0,0.0f,1,2)) return 3;
    std::printf("PASS 00714: %u native sampler modes, %u fail-closed cases\\n",accepted,rejected);
}
