#include "../../src/vr/game/hud_native_source_transaction.hpp"
#define CHECK(x) do { if (!(x)) return __LINE__; } while(false)
int main()
{
    using namespace OutRunVR::HudNativeSource;
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    using OutRunVR::GameSemantic::PhysicalDrawCommand;
    int first=1, second=2;
    SourceStamp q{true,RenderScope::ScreenHud,ProducerToken::OutRunHudText,
        &first,3,5,0x1234,7,9};
    // Real physical command mapping: same-node passes, foreign glyphs,
    // changed queue, missing exact token/pose/shader are rejected.
    PhysicalDrawCommand cmd{};
    cmd.scope = RenderScope::ScreenHud;
    cmd.producer = ProducerToken::OutRunHudText;
    cmd.queued = true;
    cmd.queueNode = &first;
    cmd.queueEpoch = 3;
    CHECK(SameSourceAfterNativeUpload(q,
        StampPhysicalCommand(cmd,5,0x1234,7,9)));
    cmd.queueNode = &second;
    CHECK(!SameSourceAfterNativeUpload(q,
        StampPhysicalCommand(cmd,5,0x1234,7,9)));
    cmd.queueNode = &first; cmd.queueEpoch++;
    CHECK(!SameSourceAfterNativeUpload(q,
        StampPhysicalCommand(cmd,5,0x1234,7,9)));
    cmd.queueEpoch = 3; cmd.producer = ProducerToken::None;
    CHECK(!IsExactHudSource(StampPhysicalCommand(cmd,5,0x1234,7,9)));
    cmd.producer = ProducerToken::OutRunHudText;
    CHECK(!IsExactHudSource(StampPhysicalCommand(cmd,0,0x1234,7,9)));
    CHECK(!IsExactHudSource(StampPhysicalCommand(cmd,5,0x1234,0,9)));
    CHECK(IsExactHudSource(q));
    CHECK(SameSourceAfterNativeUpload(q,q));
    SourceStamp changed=q;
    changed.node=&second;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.nodeEpoch++;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.producer=ProducerToken::StageExtensionTime;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.scope=RenderScope::ScreenOverlay2D;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.queueActive=false; changed.node=nullptr;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.poseEpoch++;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.shaderEpoch++;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.shader=0x5678;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.drawSerial++;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    changed=q; changed.producer=ProducerToken::None;
    CHECK(!SameSourceAfterNativeUpload(q,changed));
    CHECK(!SameSourceAfterNativeUpload(changed,q));
    SourceStamp direct{false,RenderScope::ScreenHud,
        ProducerToken::OutRunHudPeripheralText,nullptr,0,5,0x1234,7,9};
    PhysicalDrawCommand directCmd{};
    directCmd.scope = RenderScope::ScreenHud;
    directCmd.producer = ProducerToken::OutRunHudPeripheralText;
    CHECK(SameSourceAfterNativeUpload(direct,
        StampPhysicalCommand(directCmd,5,0x1234,7,9)));
    directCmd.scope = RenderScope::WorldBillboard;
    CHECK(!SameSourceAfterNativeUpload(direct,
        StampPhysicalCommand(directCmd,5,0x1234,7,9)));
    CHECK(IsExactHudSource(direct));
    CHECK(SameSourceAfterNativeUpload(direct,direct));
    changed=direct; changed.producer=ProducerToken::OutRunHudText;
    CHECK(!SameSourceAfterNativeUpload(direct,changed));
    changed=direct; changed.queueActive=true; changed.node=&first;
    changed.nodeEpoch=4;
    CHECK(!SameSourceAfterNativeUpload(direct,changed));
    SourceStamp world{false,RenderScope::WorldBillboard,
        ProducerToken::LensFlareCentre,nullptr,0,5,0x1234,7,9};
    SourceStamp unknown{};
    CHECK(SameSourceAfterNativeUpload(world,unknown));
    CHECK(SameSourceAfterNativeUpload(unknown,world));
    CHECK(SameSourceAfterNativeUpload(unknown,unknown));
    // Mutation/negative regressions across all source identity axes.
    for(int i=1;i<=1000;++i)
    {
        changed=q;
        switch(i%5)
        {
            case 0: changed.node=&second; break;
            case 1: changed.nodeEpoch+=i; break;
            case 2: changed.shaderEpoch+=i; break;
            case 3: changed.drawSerial+=i; break;
            case 4: changed.poseEpoch+=i; break;
        }
        CHECK(!SameSourceAfterNativeUpload(q,changed));
    }
    return 0;
}
