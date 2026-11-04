#include "vr/game/dino_mode1_fullcar_swap.hpp"
#include <cassert>
int main() {
 using OutRunVR::DinoMode1::SelectReplacement;
 assert(SelectReplacement(true,true,true,true,true,0,1));
 for(int m: {0,2,3,15,-1}) assert(!SelectReplacement(true,true,true,true,true,m,1));
 for(int camera: {0,2,3}) assert(!SelectReplacement(true,true,true,true,true,0,camera));
 assert(!SelectReplacement(false,true,true,true,true,0,1));
 assert(!SelectReplacement(true,false,true,true,true,0,1));
 assert(!SelectReplacement(true,true,false,true,true,0,1));
 assert(!SelectReplacement(true,true,true,false,true,0,1));
 assert(!SelectReplacement(true,true,true,true,false,0,1));
 return 0;
}
