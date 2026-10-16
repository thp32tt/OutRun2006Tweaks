#include "quest_pcvr/vr_core.hpp"
#include <cmath>
#include <limits>
#include <iostream>
using namespace quest_pcvr;
#define VERIFY(x) do { if (!(x)) { std::cerr << "FAIL: " #x " line " << __LINE__ << "\n"; return 1; } } while(false)
int main() {
    StereoViews v{};
    for(auto& e:v.eyes) e.fov={-0.4f,0.4f,-0.4f,0.4f};
    VERIFY(sphere_in_stereo(v,{0,0,-2},0.1f)==Visibility::Visible);
    VERIFY(sphere_in_stereo(v,{50,0,-2},0.1f)==Visibility::Culled);
    VERIFY(sphere_in_stereo(v,{0,0,2},0.1f)==Visibility::Culled);
    VERIFY(sphere_in_stereo(v,{0,0,-0.02f},0.05f)==Visibility::Visible);
    v.eyes[1].pose.position={1.5f,0,0};
    VERIFY(sphere_in_stereo(v,{1.5f,0,-2},0.1f)==Visibility::Visible);
    v.eyes[1].pose.position={0,0,0};
    const float yaw=0.35f;
    v.eyes[1].pose.orientation={0.f,std::sin(yaw*0.5f),0.f,std::cos(yaw*0.5f)};
    VERIFY(sphere_in_stereo(v,{-0.65f,0,-2},0.05f)==Visibility::Visible);
    VERIFY(sphere_in_stereo(v,{std::numeric_limits<float>::quiet_NaN(),0,-2},0.1f)==Visibility::Unknown);
    VERIFY(should_render(Visibility::Unknown));
    v.eyes[1].pose.orientation={0,0,0,0};
    VERIFY(sphere_in_stereo(v,{50,0,-2},0.1f)==Visibility::Unknown);
    v.eyes[1].pose.orientation={0,0,0,1};
    FrameSubmission f{};
    f.generation=9; f.frame_id=31; f.pose_sample_id=45; f.predicted_display_time_ns=567;
    f.eyes[0]={9,31,45,101}; f.eyes[1]={9,31,45,102};
    VERIFY(valid_stereo_submission(f));
    f.eyes[1].generation=8; VERIFY(!valid_stereo_submission(f));
    f.eyes[1].generation=9; f.eyes[1].pose_sample_id=46;
    VERIFY(!valid_stereo_submission(f));
    f.eyes[1].pose_sample_id=45; f.eyes[1].target_identity=101;
    VERIFY(!valid_stereo_submission(f));
    f.eyes[1].target_identity=102; f.eyes[1].frame_id=30;
    VERIFY(!valid_stereo_submission(f));
    f.eyes[1].frame_id=31; VERIFY(valid_stereo_submission(f));
    std::cout << "quest_pcvr_core: 15 checks PASS\n";
    return 0;
}
