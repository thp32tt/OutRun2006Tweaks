#include "../src/vr/d3d11/native_game_pre_draw_depth.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { long x1,y1,x2,y2; };
int main() {
 GameNativeFrameBatch f{};
 f.note_full_depth_clear(1.f);
 assert(f.can_seed_pre_draw_depth(true,true));
 GameNativePreDrawDepth d{};
 const Rect patches[]={{-2,1,3,4},{5,0,7,2}};
 assert(d.record(7,11,13,8,6,0,0,8,6,2,patches,.5f));
 assert(d.count==2&&d.tiles[0].left==0&&d.tiles[0].right==3);
 std::array<float,48> pixels{};
 pixels.fill(f.depth_clear_value(false));
 for(unsigned i=0;i<d.count;++i) {
  const auto& p=d.tiles[i];
  for(auto y=p.top;y<p.bottom;++y)
   for(auto x=p.left;x<p.right;++x)
    pixels[static_cast<std::size_t>(y)*8u+static_cast<std::size_t>(x)]=p.z;
 }
 for(unsigned y=0;y<6;++y)for(unsigned x=0;x<8;++x)
  assert(pixels[y*8+x]==(((x<3&&y>=1&&y<4)||(x>=5&&x<7&&y<2))?.5f:1.f));
 assert(d.replay_ready(7,11,13,8,6));
 assert(!d.replay_ready(8,11,13,8,6));
 assert(!d.replay_ready(7,12,13,8,6));
 assert(!d.replay_ready(7,11,12,8,6));
 const Rect bad[]={{0,0,1,1},{2,2,2,3}};
 auto saved=d;
 assert(!d.record(7,11,13,8,6,0,0,8,6,2,bad,.2f));
 assert(d.count==saved.count);
 assert(!d.record(7,11,13,8,6,0,0,8,6,1,patches,
                  std::numeric_limits<float>::quiet_NaN()));
 assert(!d.record(8,11,13,8,6,0,0,8,6,1,patches,.2f));
 const Rect outside[]={{20,20,23,24}};
 assert(d.record(7,11,13,8,6,0,0,8,6,1,outside,.2f));
 assert(d.count==2);
 d.discard();
 assert(d.count==0);
 // An actual 32-GPU-tile overflow must contain 32 *non-fusible*
 // overwrites. Consecutive equal-depth game pixels now combine exactly.
 for(unsigned i=0;i<33;++i) {
  Rect r={long(i%8),long((i/8)%6),long(i%8+1),long((i/8)%6+1)};
  const float z=(i%2u)? .3f : .6f;
  if(i<32)assert(d.record(7,11,13,8,6,0,0,8,6,1,&r,z));
  else assert(!d.record(7,11,13,8,6,0,0,8,6,1,&r,z));
 }
 assert(d.count==32);
}
