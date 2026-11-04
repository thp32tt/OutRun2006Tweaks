#include "../../src/vr/game/quest_cockpit_v2_seat.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
using namespace OutRunVR::QuestCockpitV2;
static bool near(float a,float b) {return std::fabs(a-b)<1.e-4f;}
int main(){
    std::array<std::uint8_t,30u*36u> table{};
    for(int i=0;i<30;++i){
        const float v[3]{float((i%15)*-0.01f-0.35f),
                         float(0.9f+(i%15)*0.02f),
                         float((i%15)*-0.02f-0.3f)};
        std::memcpy(table.data()+i*36,v,sizeof(v));
    }
    Vec3 a{-99,0,0},b{};
    for(int i=0;i<15;++i){
        assert(OriginalModeOneAnchor(table.data(),table.size(),i,a));
        assert(OriginalModeOneAnchor(table.data(),table.size(),i+15,b));
        assert(near(a.x,b.x)&&near(a.y,b.y)&&near(a.z,b.z));
    }
    assert(!OriginalModeOneAnchor(table.data(),table.size(),-1,a));
    assert(!OriginalModeOneAnchor(table.data(),table.size(),30,a));
    assert(!OriginalModeOneAnchor(table.data(),table.size()-1,0,a));
    assert(!OriginalModeOneAnchor(nullptr,table.size(),0,a));
    Matrix car=Identity;car[12]=10.f;car[13]=20.f;car[14]=30.f;
    SeatPose p{};
    assert(SeatPoseFromCar(car,{-0.35f,0.99f,-0.345f},p));
    assert(near(p.eye.x,9.65f)&&near(p.eye.y,20.99f)&&
           near(p.eye.z,29.655f));
    assert(near(p.look.z,30.655f));
    Matrix rotate=Identity;
    // 90 deg yaw about Y in a D3D row-vector matrix.
    rotate[0]=0;rotate[2]=-1;rotate[8]=1;rotate[10]=0;
    assert(SeatPoseFromCar(rotate,{-0.35f,1.0f,-0.345f},p));
    assert(near(p.eye.x,-0.345f)&&near(p.eye.y,1.f)&&near(p.eye.z,0.35f));
    assert(near(p.look.x,0.655f));
    auto before=p;
    rotate[4]=std::numeric_limits<float>::quiet_NaN();
    assert(!SeatPoseFromCar(rotate,{0,0,0},p));
    assert(near(before.eye.x,p.eye.x));
    SeatPose offset{};
    assert(NativeSeatOffset({0,1,0},{0,1,10},.35f,.18f,0,offset));
    assert(near(offset.eye.z,-.35f)&&near(offset.eye.y,.82f));
    assert(near(offset.look.z,9.65f)&&near(offset.look.y,.82f));
    assert(NativeSeatOffset({3,1,4},{13,1,4},.35f,.18f,.1f,offset));
    assert(near(offset.eye.x,2.65f)&&near(offset.eye.z,3.9f));
    const auto beforeOffset=offset;
    assert(!NativeSeatOffset({0,0,0},{0,0,0},.35f,.18f,0,offset));
    assert(near(offset.eye.x,beforeOffset.eye.x));
    assert(!NativeSeatOffset({0,0,0},{0,0,1},3.f,.18f,0,offset));

    // Quest native run_game::$_2 30-way guest profile addresses must be
    // checked. This is NOT 15 copies of the old view1 camera table.
    constexpr std::size_t kStride=0x128u,kCount=30u;
    const std::array<Vec3,kCount> questXYZ{{
        {-.353f,.627f,-.390f},{-.331f,.688f,-.258f},
        {-.357f,.635f,-.396f},{-.319f,.673f,-.244f},
        {-.345f,.773f,-.019f},{-.325f,.698f,-.472f},
        {-.330f,.620f,-.400f},{-.365f,.679f,-.442f},
        {-.351f,.674f,-.458f},{-.331f,.766f,.035f},
        {-.353f,.650f,-.340f},{-.320f,.640f,-.340f},
        {-.351f,.750f,-.458f},{-.351f,.770f,.000f},
        {-.351f,.674f,-.025f},{-.353f,.627f,-.450f},
        {-.331f,.688f,-.258f},{-.357f,.635f,-.396f},
        {-.319f,.673f,-.244f},{-.345f,.773f,-.050f},
        {-.325f,.698f,-.472f},{-.330f,.620f,-.400f},
        {-.365f,.679f,-.350f},{-.351f,.674f,-.458f},
        {-.331f,.766f,.035f},{-.353f,.650f,-.340f},
        {-.320f,.640f,-.340f},{-.351f,.720f,-.410f},
        {-.351f,.770f,.000f},{-.351f,.750f,-.025f}
    }};
    std::array<std::uint8_t,kCount*kStride> records{};
    std::array<std::uint8_t,kCount*4u> guestPointers{};
    for(std::size_t i=0;i<kCount;++i) {
        const std::uint32_t va=0x5b0cb8u+std::uint32_t(i*kStride);
        std::memcpy(guestPointers.data()+4u*i,&va,4u);
        std::memcpy(records.data()+i*kStride+0x4cu,
                    &questXYZ[i],sizeof(Vec3));
    }
    Vec3 fetched{};
    for(int i=0;i<30;++i) {
        assert(OriginalQuestVrProfileAnchor(guestPointers.data(),
            guestPointers.size(),records.data(),records.size(),i,fetched));
        assert(near(fetched.x,questXYZ[std::size_t(i)].x));
        assert(near(fetched.y,questXYZ[std::size_t(i)].y));
        assert(near(fetched.z,questXYZ[std::size_t(i)].z));
    }
    assert(!near(questXYZ[0].z,questXYZ[15].z));
    assert(!near(questXYZ[7].z,questXYZ[22].z));
    assert(!near(questXYZ[12].y,questXYZ[27].y));
    const Vec3 oldFetch=fetched;
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size(),records.data(),records.size(),-1,fetched));
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size(),records.data(),records.size(),30,fetched));
    assert(!OriginalQuestVrProfileAnchor(nullptr,
        guestPointers.size(),records.data(),records.size(),0,fetched));
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size()-1,records.data(),records.size(),0,fetched));
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size(),records.data(),records.size()-1,0,fetched));
    assert(near(fetched.z,oldFetch.z));
    const std::uint32_t corrupt=0u;
    std::memcpy(guestPointers.data()+4u*29u,&corrupt,4u);
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size(),records.data(),records.size(),29,fetched));
    records[0x4cu+4u]=0xff; records[0x4cu+5u]=0xff;
    records[0x4cu+6u]=0xff; records[0x4cu+7u]=0x7f;
    assert(!OriginalQuestVrProfileAnchor(guestPointers.data(),
        guestPointers.size(),records.data(),records.size(),0,fetched));
    // Runtime now injects Quest XYZ at the original mode1 producer input,
    // so the game's own swing/blend/ground clamp consumes it before XR.
    // Original ARM64 2E17F4 callback adds a fixed Y/Z pair to the
    // 30-entry profile before native view1; never to OpenXR eye matrices.
    Vec3 exactQuestInput{};
    assert(OriginalQuestModeOneInput(questXYZ[0],exactQuestInput));
    assert(near(exactQuestInput.x,-.353f));
    assert(near(exactQuestInput.y,.947f));
    assert(near(exactQuestInput.z,.160f));
    assert(OriginalQuestModeOneInput(questXYZ[15],exactQuestInput));
    assert(near(exactQuestInput.y,.947f));
    assert(near(exactQuestInput.z,.100f));
    assert(!OriginalQuestModeOneInput(
        {0.f,std::numeric_limits<float>::quiet_NaN(),0.f},
        exactQuestInput));
    assert(near(exactQuestInput.z,.100f));
    Vec3 inputAnchor{};
    assert(NativeVrProfileInputAnchor(
        questXYZ[0],0.f,0.f,0.f,inputAnchor));
    assert(near(inputAnchor.x,questXYZ[0].x));
    assert(near(inputAnchor.y,questXYZ[0].y));
    assert(near(inputAnchor.z,questXYZ[0].z));
    assert(NativeVrProfileInputAnchor(
        questXYZ[0],.1f,.1f,.05f,inputAnchor));
    assert(near(inputAnchor.x,-.303f));
    assert(near(inputAnchor.y,.527f));
    assert(near(inputAnchor.z,-.290f));
    // Previously the F11 range could not cross zero and the cockpit eye
    // was trapped below the dashboard. Negative down must raise it.
    assert(NativeVrProfileInputAnchor(
        questXYZ[0],.25f,-.38f,-.05f,inputAnchor));
    assert(near(inputAnchor.x,-.403f));
    assert(near(inputAnchor.y,1.007f));
    assert(near(inputAnchor.z,-.140f));
    assert(NativeVrProfileInputAnchor(
        questXYZ[0],-.25f,.25f,0.f,inputAnchor));
    assert(near(inputAnchor.y,.377f));
    assert(near(inputAnchor.z,-.640f));
    const Vec3 inputBefore=inputAnchor;
    assert(!NativeVrProfileInputAnchor(
        questXYZ[0],-1.3f,0.f,0.f,inputAnchor));
    assert(!NativeVrProfileInputAnchor(
        questXYZ[0],0.f,-1.1f,0.f,inputAnchor));
    assert(near(inputAnchor.x,inputBefore.x));

    // No raw B0 is used: the source view1 camera remains the same and
    // only its profile delta is applied ONCE, atomically to eye and look.
    SeatPose profilePose{};
    assert(NativeVrProfilePose({0.f,.99f,0.f},{0.f,.99f,10.f},
        {-.353f,.99f,-.345f},questXYZ[0],
        0.f,0.f,0.f,profilePose));
    assert(near(profilePose.eye.x,0.f));
    assert(near(profilePose.eye.y,.627f));
    assert(near(profilePose.eye.z,-.045f));
    assert(near(profilePose.look.y,.627f));
    assert(near(profilePose.look.z,9.955f));
    const auto profileBefore=profilePose;
    assert(!NativeVrProfilePose({0.f,.99f,0.f},{0.f,.99f,0.f},
        {-.353f,.99f,-.345f},questXYZ[0],0.f,0.f,0.f,profilePose));
    assert(near(profilePose.eye.y,profileBefore.eye.y));
    // A 90-degree yaw rotates X/Z seat delta; no extra translated car B0.
    assert(NativeVrProfilePose({10.f,1.f,20.f},{20.f,1.f,20.f},
        {0.f,1.f,0.f},{-.2f,.7f,-.4f},
        0.f,0.f,0.f,profilePose));
    assert(near(profilePose.eye.x,9.6f));
    assert(near(profilePose.eye.y,.7f));
    assert(near(profilePose.eye.z,20.2f));
    assert(near(profilePose.look.x,19.6f));
    // User back/down/right remain optional on TOP of native Quest seat.
    assert(NativeVrProfilePose({0.f,.99f,0.f},{0.f,.99f,10.f},
        {-.353f,.99f,-.345f},questXYZ[0],
        .1f,.1f,.05f,profilePose));
    assert(near(profilePose.eye.x,.05f));
    assert(near(profilePose.eye.y,.527f));
    assert(near(profilePose.eye.z,-.145f));
    assert(!NativeVrProfilePose({0.f,.99f,0.f},{0.f,.99f,10.f},
        {-.353f,.99f,-.345f},questXYZ[0],
        -1.3f,0.f,0.f,profilePose));
    assert(!NativeVrProfilePose({0.f,.99f,0.f},{0.f,.99f,10.f},
        {-.353f,.99f,-.345f},
        {-.353f,std::numeric_limits<float>::quiet_NaN(),-.345f},
        0.f,0.f,0.f,profilePose));
    assert(near(profilePose.eye.y,.527f));
    assert(TrialEligible(true,true,true,1,false,true));
    assert(!TrialEligible(true,true,true,2,false,true));
    assert(!TrialEligible(true,true,true,1,true,true));
    assert(!TrialEligible(true,true,true,1,false,false));
}
