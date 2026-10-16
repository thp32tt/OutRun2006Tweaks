#include "quest_pcvr/particle_stereo.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <vector>
using namespace quest_pcvr;
#define CK(x) do { if(!(x)){std::cerr<<"fail " #x " line "<<__LINE__<<"\n";return 1;} }while(0)
struct Mock:IParticleGpu {
 int uploads=0,eyes=0;bool failUpload=false,failRight=false;
 std::vector<unsigned char> bytes; std::vector<std::uint64_t> targets;
 bool uploadOnce(const void*p,std::uint32_t n,std::uint32_t stride,std::uint64_t,ParticleGpuSlice&s) noexcept override {
  ++uploads;if(failUpload)return false;
  const auto*b=static_cast<const unsigned char*>(p);bytes.assign(b,b+n);
  s={0,n/stride,stride};return true;
 }
 bool drawEye(unsigned i,const FrameSubmission&f,const ParticleGpuSlice&,std::uint64_t) noexcept override {
  ++eyes;targets.push_back(f.eyes[i].target_identity);return !failRight||i==0;
 }
};
ParticleDraw draw(const void*vertices,unsigned sequence) {
 ParticleDraw d{}; d.frame.generation=1;d.frame.frame_id=2;d.frame.pose_sample_id=3;
 d.frame.predicted_display_time_ns=4;d.frame.eyes={EyeImageStamp{1,2,3,50},EyeImageStamp{1,2,3,51}};
 d.kind=EffectKind::Smoke;d.producer_token=5;d.material_token=6;
 d.state_serial=7;d.target_serial=8;d.draw_sequence=sequence;d.vertices=vertices;
 d.vertex_count=3;d.vertex_stride=16;d.world_space=true;d.alpha_blend=true;
 d.depth_write_disabled=true;d.verified_producer=true;return d;
}
int main(){
 std::array<unsigned char,48>a{},b{};a.fill(0x10);b.fill(0x80);
 ParticleDraw ds[]={draw(a.data(),10),draw(b.data(),11)};
 Mock gpu;ParticleStereoBatcher batch;
 CK(batch.submit(ds,2,gpu)==ParticleResult::NeedsOriginal&&gpu.uploads==0);
 batch.enable(true);CK(batch.submit(ds,2,gpu)==ParticleResult::Submitted);
 CK(gpu.uploads==1&&gpu.eyes==2&&gpu.targets[0]==50&&gpu.targets[1]==51);
 CK(gpu.bytes.size()==96&&std::memcmp(gpu.bytes.data(),a.data(),48)==0);
 CK(std::memcmp(gpu.bytes.data()+48,b.data(),48)==0);
 CK(batch.stats().original_draws_covered==2&&batch.stats().bytes_uploaded==96);
 Mock reject;ds[1].state_serial=9;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal&&reject.uploads==0);
 ds[1].state_serial=7;ds[1].material_token=9;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[1].material_token=6;ds[1].draw_sequence=14;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[1].draw_sequence=11;ds[1].kind=EffectKind::Glass;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[1].kind=EffectKind::Smoke;ds[1].verified_producer=false;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[1].verified_producer=true;ds[1].frame.eyes[1].target_identity=50;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[1].frame.eyes[1].target_identity=51;ds[0].vertex_count=200000;
 CK(batch.submit(ds,2,reject)==ParticleResult::NeedsOriginal);
 ds[0].vertex_count=3;
 Mock uploadFail;uploadFail.failUpload=true;
 CK(batch.submit(ds,2,uploadFail)==ParticleResult::NeedsOriginal&&uploadFail.eyes==0);
 Mock eyeFail;eyeFail.failRight=true;
 CK(batch.submit(ds,2,eyeFail)==ParticleResult::FrameInvalid&&eyeFail.eyes==2);
 CK(eligible_for_optional_half_resolution(EffectKind::Smoke,true));
 CK(!eligible_for_optional_half_resolution(EffectKind::Glass,true));
 CK(!eligible_for_optional_half_resolution(EffectKind::WaterSurface,true));
 CK(!eligible_for_optional_half_resolution(EffectKind::WaterSpray,true));
 CK(!eligible_for_optional_half_resolution(EffectKind::Dust,false));
 std::cout<<"particle batching PASS\n";
}
