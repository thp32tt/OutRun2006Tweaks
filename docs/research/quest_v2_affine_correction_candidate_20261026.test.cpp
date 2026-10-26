#include "quest_v2_affine_correction_candidate_20261026.hpp"
#include <array>
#include <cmath>
#include <cassert>
#include <iostream>
#include <iomanip>
#include <random>
#include <algorithm>
namespace quest_research {
std::array<float,16> body_correction_from_guest_matrices(
 const std::array<float,16>&, const std::array<float,16>&);
}
int main(){
  using namespace quest_cockpit_research;
  std::mt19937 rng(20261026);
  std::uniform_real_distribution<float> uni(-2.0f,2.0f);
  double worst=0.0, worstRel=0.0;
  int tested=0;
  for (int i=0; i<2000; ++i) {
    AffineMatrix a{},b{},got{};
    for (auto* m: {&a,&b}) {
      for(int k=0;k<16;++k)(*m)[k]=uni(rng);
      (*m)[3]=(*m)[7]=(*m)[11]=0.0f;
      (*m)[15]=1.0f;
    }
    assert(ComputeQuestBodyCorrectionAffine(a,b,got));
    auto ref=quest_research::body_correction_from_guest_matrices(a,b);
    for (int k=0;k<16;++k) {
      const double delta=std::abs(double(ref[k])-double(got[k]));
      const double rel=delta/(1.0+std::abs(double(ref[k])));
      worst=std::max(worst,delta);
      worstRel=std::max(worstRel,rel);
      assert(rel < 0.00001); // reference uses native arm64 fused floats
    }
    ++tested;
  }
  AffineMatrix identity{}; for(int i=0;i<16;i+=5)identity[i]=1;
  AffineMatrix got{};
  assert(ComputeQuestBodyCorrectionAffine(identity,identity,got));
  for(int i: {0,5,10}) assert(got[i]==-1.0f);
  assert(got[15]==1.0f);
  auto bad=identity;bad[3]=0.4f;
  AffineMatrix kept=identity;
  assert(!ComputeQuestBodyCorrectionAffine(bad,identity,kept));
  assert(kept==identity);
  bad=identity;bad[7]=std::nanf("");
  assert(!ComputeQuestBodyCorrectionAffine(bad,identity,kept));
  std::cout<<std::setprecision(10)<<"PASS 2000 random affine tests, max_abs="<<worst
           <<" max_relative="<<worstRel<<" rejects_validated=2\n";
}