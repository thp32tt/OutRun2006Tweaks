#include "../../src/vr/game/quest_cockpit_v2_seat.hpp"
#include "../../src/vr/game/quest_cockpit_v2_apk_xr_pose.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
using namespace OutRunVR::QuestCockpitV2;
static bool near(float a,float b) {return std::fabs(a-b)<1.e-4f;}
int main(){
    // Loading a cockpit hook before the original game has initialized its
    // 30x36 live camera table must NOT snapshot zeroes as original seats.
    constexpr std::size_t stride=36,modelCount=30;
    std::array<std::uint8_t,stride*modelCount> originalSeats{};
    std::array<std::uint8_t,stride*modelCount> liveSeats{};
    for(std::size_t i=0;i<modelCount;++i) {
        const float xyz[3]={-.35f,.6f+float(i)*.01f,-.4f};
        std::memcpy(originalSeats.data()+i*stride,xyz,sizeof(xyz));
    }
    assert(!OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size(),originalSeats.data(),originalSeats.size()));
    liveSeats=originalSeats;
    assert(OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size(),originalSeats.data(),originalSeats.size()));
    // Altering an unrelated original per-car record field leaves XYZ intact.
    liveSeats[17*stride+15]=0x55;
    assert(OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size(),originalSeats.data(),originalSeats.size()));
    // But one changed XYZ byte or one invalid original coordinate must veto
    // the entire backup, not store the 29 plausible records.
    liveSeats[29*stride+4]^=0x01;
    assert(!OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size(),originalSeats.data(),originalSeats.size()));
    liveSeats=originalSeats;
    originalSeats[3*stride+4]=0xff;
    originalSeats[3*stride+5]=0xff;
    originalSeats[3*stride+6]=0xff;
    originalSeats[3*stride+7]=0x7f;
    assert(!OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size(),originalSeats.data(),originalSeats.size()));
    assert(!OriginalModeOneTableInitialized(
        liveSeats.data(),liveSeats.size()-1,originalSeats.data(),originalSeats.size()));
    assert(!OriginalModeOneTableInitialized(
        nullptr,liveSeats.size(),originalSeats.data(),originalSeats.size()));
    // Original 2D6A60 yaw-only XR origin and 2D6B98 dual-eye source math.
    // A live Quest HMD is not required to validate the quaternion/eye
    // algebra and its position recenter invariants.
    constexpr float halfYaw=.25f;
    NativePose worldHead{
        {0.f,std::sin(halfYaw),0.f,std::cos(halfYaw)},
        {10.f,1.6f,20.f}};
    NativePose origin{};
    assert(NativeYawOrigin(worldHead,origin));
    assert(near(origin.q.x,0.f)&&near(origin.q.y,std::sin(halfYaw)));
    assert(near(origin.q.z,0.f)&&near(origin.q.w,std::cos(halfYaw)));
    assert(near(origin.p.x,10.f)&&near(origin.p.y,1.6f));
    NativePose center{};
    assert(NativeInverseOriginCompose(origin,worldHead,center));
    assert(near(center.q.x,0.f)&&near(center.q.y,0.f));
    assert(near(center.q.z,0.f)&&near(center.q.w,1.f));
    assert(near(center.p.x,0.f)&&near(center.p.y,0.f));
    assert(near(center.p.z,0.f));
    NativePose eyeLeft{},eyeRight{};
    assert(NativeStereoEye(origin,worldHead,
        {{0.f,0.f,0.f,1.f},{-.032f,0.f,0.f}},eyeLeft));
    assert(NativeStereoEye(origin,worldHead,
        {{0.f,0.f,0.f,1.f},{.032f,0.f,0.f}},eyeRight));
    assert(near(eyeLeft.p.x,-.032f));
    assert(near(eyeRight.p.x,.032f));
    assert(near(eyeLeft.p.y,0.f)&&near(eyeRight.p.z,0.f));
    assert(near(eyeLeft.q.w,1.f)&&near(eyeRight.q.w,1.f));
    NativePose invalidNative{};
    assert(!NativeYawOrigin({{0,0,0,0},{0,0,0}},invalidNative));
    assert(!NativeStereoEye(origin,worldHead,
        {{0.f,0.f,0.f,1.f},{std::numeric_limits<float>::quiet_NaN(),0,0}},
        invalidNative));
    // Nontrivial binocular XR test: the original source applies one
    // inverse-yaw origin to both eyes, preserving their physical eye
    // separation and head-local rotational relationship. Equal camera
    // source YZ additions must never move either OpenXR eye pose.
    NativePose pitchedHead{
        {0.10f,0.20f,-0.12f,0.968f},
        {4.5f,1.4f,-2.7f}};
    NativePose pitchedOrigin{};
    assert(NativeYawOrigin(pitchedHead,pitchedOrigin));
    NativePose left2{},right2{};
    assert(NativeStereoEye(pitchedOrigin,pitchedHead,
        {{0.f,0.012f,0.f,0.999928f},{-.031f,0.002f,0.004f}},
        left2));
    assert(NativeStereoEye(pitchedOrigin,pitchedHead,
        {{0.f,-.012f,0.f,0.999928f},{.031f,-0.002f,0.004f}},
        right2));
    const float sepX=right2.p.x-left2.p.x;
    const float sepY=right2.p.y-left2.p.y;
    const float sepZ=right2.p.z-left2.p.z;
    assert(std::fabs(std::sqrt(sepX*sepX+sepY*sepY+sepZ*sepZ)
                     -std::sqrt(.062f*.062f+.004f*.004f))<1.e-4f);
    NativePose invalidEye{};
    assert(!NativeStereoEye(pitchedOrigin,pitchedHead,
        {{0.f,0.f,0.f,1.f},{0.f,INFINITY,0.f}},invalidEye));
    // The game view is yaw-recentered, but the PC OpenXR projection
    // space remains LOCAL. Keep original located eye pose for the
    // runtime submission: these are distinct when the yaw origin is
    // non-identity. Transforming both would double-recenter the image.
    NativePose physicalLeft{};
    assert(NativeHeadLocalEye(pitchedHead,
        {{0.f,0.012f,0.f,0.999928f},{-.031f,.002f,.004f}},
        physicalLeft));
    assert(std::fabs(physicalLeft.p.x-left2.p.x)>0.5f);
    NativePose recoveredLocal{};
    assert(NativeInverseOriginCompose(pitchedOrigin,physicalLeft,recoveredLocal));
    assert(near(recoveredLocal.p.x,left2.p.x));
    assert(near(recoveredLocal.p.y,left2.p.y));
    assert(near(recoveredLocal.p.z,left2.p.z));
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
    // Native camera override is state==0x10 only. START=0x0d and
    // GOAL=0x13 must preserve the unpatched PC mode1 camera table.
    assert(!OriginalQuestGameCameraState(0x0du));
    assert(OriginalQuestGameCameraState(0x10u));
    assert(!OriginalQuestGameCameraState(0x13u));
    assert(!OriginalQuestGameCameraState(0x1bu));
    // ARM64 selected profile X/Y/Z is written to x19[64] buffer by
    // 2E1598/2E1650/2E16C4 before the native 2E17F4 YZ addition.
    // Both +.32Y and +.55Z must be present exactly once in the
    // game camera producer input; no additional OpenXR head offset.
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
    // The F11 sliders must also work when APK-native camera composition
    // is ON. Previously that branch skipped NativeVrProfileInputAnchor,
    // so manual offsets were silently ignored after choosing the APK pose.
    // Tuning happens BEFORE the source-proven +0.32Y/+0.55Z pair;
    // zero tuning must reproduce the exact original guest values.
    Vec3 nativeTuned{},nativeComposed{};
    assert(NativeVrProfileInputAnchor(questXYZ[0],0.f,0.f,0.f,nativeTuned));
    assert(OriginalQuestModeOneInput(nativeTuned,nativeComposed));
    assert(near(nativeComposed.x,-.353f));
    assert(near(nativeComposed.y,.947f));
    assert(near(nativeComposed.z,.160f));
    assert(NativeVrProfileInputAnchor(questXYZ[0],.1f,.1f,.05f,nativeTuned));
    assert(OriginalQuestModeOneInput(nativeTuned,nativeComposed));
    assert(near(nativeComposed.x,-.303f));
    assert(near(nativeComposed.y,.847f));
    assert(near(nativeComposed.z,.260f));
    assert(NativeVrProfileInputAnchor(questXYZ[0],.25f,-.38f,-.05f,nativeTuned));
    assert(OriginalQuestModeOneInput(nativeTuned,nativeComposed));
    assert(near(nativeComposed.x,-.403f));
    assert(near(nativeComposed.y,1.327f));
    assert(near(nativeComposed.z,.410f));
    // Physical Quest3 requested modest forward/up movement.
    assert(NativeVrProfileInputAnchor(
        questXYZ[0],-.08f,-.05f,0.f,nativeTuned));
    assert(OriginalQuestModeOneInput(nativeTuned,nativeComposed));
    assert(near(nativeComposed.x,-.353f));
    assert(near(nativeComposed.y,.997f));
    assert(near(nativeComposed.z,.080f));
    const Vec3 priorComposed=nativeComposed;
    assert(!NativeVrProfileInputAnchor(questXYZ[0],-1.3f,0.f,0.f,nativeTuned));
    assert(near(nativeComposed.y,priorComposed.y));
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
