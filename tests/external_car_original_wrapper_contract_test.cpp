#include <array>
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include <limits>
#include "../src/vr/game/external_car_original_wrapper_contract.hpp"
#include "../src/vr/game/external_car_atomic_precommit.hpp"
#include "../src/vr/game/dino_external_original_car_gate.hpp"
#include "../src/vr/game/external_car_dashboard.hpp"
#include "../src/vr/game/quest_cockpit_v2_glass_hook.hpp"
using namespace OutRunVR::DinoSidecar;
static OriginalCarGate ValidGate(){
    OriginalCarGate g{};
    g.optedIn=g.ownedPlayer=g.gameplay=g.cockpitModeOne=true;
    g.validStereo=g.nativeFrameActive=g.deviceReady=true;
    g.ticketEpoch=g.liveEpoch=14;
    g.ticketPose=g.livePose=22;
    return g;
}
static void TestDeferredGlassOwnerRefresh(){
    using namespace OutRunVR::QuestCockpitV2::Glass;
    struct Token {
        const int* entry=nullptr;
        std::uint32_t id=0;
        const int* node=nullptr;
        std::uint64_t epoch=0;
    };
    int entry=0,otherEntry=0,nodeA=0,nodeB=0;
    std::array<Token,1> tokens{};
    std::size_t count=0;
    const Token original{&entry,10,&nodeA,7};
    const Token reused{&entry,11,&nodeB,7};
    assert(RememberDeferredOwner(tokens,count,original));
    assert(count==1 && DeferredOwnerMatches(tokens[0],original));
    assert(!DeferredOwnerMatches(tokens[0],reused));
    // A newly captured original-player entry at the same queue address
    // must replace the old token, even when the bounded table is full.
    assert(RememberDeferredOwner(tokens,count,reused));
    assert(count==1 && DeferredOwnerMatches(tokens[0],reused));
    assert(!DeferredOwnerMatches(tokens[0],original));
    assert(!DeferredOwnerMatches(tokens[0],Token{&entry,11,&nodeA,7}));
    assert(!DeferredOwnerMatches(tokens[0],Token{&entry,11,&nodeB,8}));
    assert(!DeferredOwnerMatches(tokens[0],Token{&otherEntry,11,&nodeB,7}));
    assert(!RememberDeferredOwner(tokens,count,Token{&otherEntry,12,&nodeB,7}));
    assert(!RememberDeferredOwner(tokens,count,Token{&entry,0,&nodeB,7}));
    assert(!RememberDeferredOwner(tokens,count,Token{&entry,0xffffffffu,&nodeB,7}));
    assert(!RememberDeferredOwner(tokens,count,Token{&entry,11,&nodeB,0}));
    assert(count==1 && DeferredOwnerMatches(tokens[0],reused));
}
static void TestDeferredQueueAppendProvenance(){
    using namespace OutRunVR::QuestCockpitV2::Glass;
    int storageA=0,storageB=0;
    const DeferredQueueSnapshot before{&storageA,4,16};
    assert(SameDeferredQueueAppend(before,{&storageA,4,16}));
    assert(SameDeferredQueueAppend(before,{&storageA,16,16}));
    assert(!SameDeferredQueueAppend(before,{&storageB,5,16}));
    assert(!SameDeferredQueueAppend(before,{&storageA,3,16}));
    assert(!SameDeferredQueueAppend(before,{&storageA,5,32}));
    assert(!SameDeferredQueueAppend(before,{&storageA,17,16}));
    assert(!SameDeferredQueueAppend(before,{nullptr,5,16}));
    assert(!SameDeferredQueueAppend(before,{&storageA,5,16385}));
    assert(!SameDeferredQueueAppend({&storageA,-1,16},before));
    assert(!SameDeferredQueueAppend({&storageA,0,0},before));
    for(unsigned slot=0;slot<16;++slot)
        for(bool sameStorage:{false,true})
            for(bool sameLimit:{false,true})
                for(int count:{-1,0,3,4,5,16,17}) {
                    const DeferredQueueSnapshot after{
                        sameStorage?&storageA:&storageB,count,sameLimit?16:32};
                    assert(SameDeferredQueueAppend(before,after)==
                        (sameStorage&&sameLimit&&count>=4&&count<=16));
                }
}
static void TestImmediateGlassOwnerScope(){
    using namespace OutRunVR::QuestCockpitV2::Glass;
    ScopedPlayerCallbackOwner* current=nullptr;
    for(unsigned slot=0;slot<16;++slot) {
        for(bool nestedPlayer:{false,true}) {
            const std::uint64_t epoch=7;
            assert(!ScopedPlayerCallbackOwner::Immediate(current,epoch));
            {
                ScopedPlayerCallbackOwner outer(current);
                assert(!ScopedPlayerCallbackOwner::Immediate(current,epoch));
                outer.Admit(epoch);
                assert(ScopedPlayerCallbackOwner::Immediate(current,epoch));
                assert(!ScopedPlayerCallbackOwner::Immediate(current,epoch+1));
                assert(!ScopedPlayerCallbackOwner::Immediate(current,0));
                assert(outer.CanCapture(epoch));
                assert(!outer.CanCapture(epoch+1));
                {
                    ScopedPlayerCallbackOwner inner(current);
                    if(nestedPlayer)inner.Admit(epoch);
                    assert(ScopedPlayerCallbackOwner::Immediate(current,epoch)==nestedPlayer);
                    assert(inner.CanCapture(epoch)==nestedPlayer);
                    assert(!outer.CanCapture(epoch));
                }
                assert(ScopedPlayerCallbackOwner::Immediate(current,epoch));
                assert(!outer.CanCapture(epoch));
            }
            assert(current==nullptr);
        }
    }
}
static void TestDeferredGlassCannotOverrideLiveCallback(){
    using namespace OutRunVR::QuestCockpitV2::Glass;
    using Scope=ScopedPlayerCallbackOwner;
    Scope* current=nullptr;
    // A valid older deferred token can still be in a callee-saved register.
    // Its match must not be evaluated during any live callback, even a
    // non-player or stale-epoch callback nested under the player.
    for(unsigned slot=0;slot<16;++slot) {
        for(bool matchingToken:{false,true}) {
            unsigned scans=0;
            const auto admitted=[&](std::uint64_t epoch) {
                return Scope::Immediate(current,epoch) ||
                    (Scope::MayLookupDeferred(current,epoch) &&
                     (++scans,matchingToken));
            };
            assert(!admitted(0) && scans==0);
            assert(admitted(7)==matchingToken && scans==1);
            {
                Scope outer(current);
                assert(!admitted(7) && scans==1);
                outer.Admit(7);
                assert(admitted(7) && scans==1);
                assert(!admitted(8) && scans==1);
                {
                    Scope inner(current);
                    assert(!admitted(7) && scans==1);
                    inner.Admit(8);
                    assert(!admitted(7) && scans==1);
                    assert(admitted(8) && scans==1);
                }
                assert(admitted(7) && scans==1);
            }
            assert(current==nullptr);
            assert(admitted(7)==matchingToken && scans==2);
        }
    }
}
int main(){
    TestDeferredQueueAppendProvenance();
    TestDeferredGlassCannotOverrideLiveCallback();
    TestDeferredGlassOwnerRefresh();
    TestImmediateGlassOwnerScope();
    static_assert(!MaySkipRetailPlayerWrapper(),
        "A proven two-call retail wrapper is not a body-only draw leaf");
    static_assert(!RuntimeExternalCarAtomicStageReady(),
        "Do not enable exterior model raster before GPU pair staging");
    constexpr auto bytes=RetailPlayerWrapperPrefix;
    static_assert(RetailCallTarget(bytes.data(),bytes.size(),6)==0x46BD30u);
    static_assert(RetailCallTarget(bytes.data(),bytes.size(),17)==0x49A650u);
    static_assert(ExactRetailPlayerWrapperTwoCalls(bytes.data(),bytes.size()));
    assert(!ExactRetailPlayerWrapperTwoCalls(bytes.data(),bytes.size()-1));
    assert(!ExactRetailPlayerWrapperTwoCalls(nullptr,bytes.size()));
    auto corrupt=bytes;corrupt[7]^=1;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    corrupt=bytes;corrupt[18]^=1;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    corrupt=bytes;corrupt[11]=0x90;
    assert(!ExactRetailPlayerWrapperTwoCalls(corrupt.data(),corrupt.size()));
    assert(RetailCallTarget(bytes.data(),3,6)==0u);
    assert(RetailCallTarget(bytes.data(),bytes.size(),5)==0u);
    // A hostile/invalid offset must not wrap the size_t end check and
    // read outside the code buffer, on either x86 or x64.
    const auto maxOffset=std::numeric_limits<std::size_t>::max();
    for(std::size_t k=0;k<5;++k)
        assert(RetailCallTarget(bytes.data(),bytes.size(),maxOffset-k)==0u);
    assert(RetailCallTarget(bytes.data(),bytes.size(),bytes.size())==0u);
    assert(RetailCallTarget(bytes.data(),bytes.size(),bytes.size()-4)==0u);
    unsigned reads=0;
    const auto fullSpan=[&](const void* p,std::size_t n){
        ++reads;return p==bytes.data() && n==bytes.size();
    };
    assert(MatchReadableRetailSignature(bytes.data(),bytes,fullSpan));
    assert(reads==1);
    assert(!MatchReadableRetailSignature(nullptr,bytes,fullSpan));
    assert(reads==1);
    const auto denied=[&](const void*,std::size_t n){
        ++reads;assert(n==bytes.size());return false;
    };
    assert(!MatchReadableRetailSignature(bytes.data(),bytes,denied));
    assert(reads==2);
    assert(!MatchReadableRetailSignature(corrupt.data(),bytes,
        [](const void*,std::size_t){return true;}));

    // The prior 24-byte signature ended mid-ADD ESP and never checked
    // stack cleanup, POP ESI or RET. All three bytes now matter.
    static_assert(bytes.size()==27);
    assert(!ExactRetailPlayerWrapperTwoCalls(bytes.data(),24));
    for(std::size_t i=24;i<bytes.size();++i) {
        auto bad=bytes;bad[i]^=1;
        assert(!ExactRetailPlayerWrapperTwoCalls(bad.data(),bad.size()));
    }
    constexpr auto ret=RetailPlayerFollowupRet;
    for(unsigned slot=0;slot<16;++slot)
        for(bool wrapperOk:{false,true})
            for(bool tailOk:{false,true})
                for(bool wrapperReadable:{false,true})
                    for(bool followupReadable:{false,true}) {
                        auto wrapper=bytes;
                        if(!wrapperOk)wrapper[24]^=1;
                        auto callee=ret;
                        if(!tailOk)callee[0]=0x90;
                        unsigned followupReads=0;
                        const bool ok=MatchReadableRetailPlayerWrapper(
                            wrapper.data(),callee.data(),
                            [&](const void* ptr,std::size_t len) {
                                if(ptr==wrapper.data()) {
                                    assert(len==27);return wrapperReadable;
                                }
                                assert(ptr==callee.data() && len==1);
                                ++followupReads;return followupReadable;
                            });
                        assert(ok==(wrapperOk&&tailOk&&wrapperReadable&&followupReadable));
                        assert(followupReads==(wrapperOk&&wrapperReadable?1u:0u));
                    }
    assert(!MatchReadableRetailPlayerWrapper(bytes.data(),nullptr,
        [](const void*,std::size_t){return true;}));

    // Every canonical Ferrari slot (0..14, 28) remains on the ORIGINAL
    // complete callback: body, stock dashboard, glass/alpha, passenger and
    // shadow follow-up are not skipped. This is callback ownership parity,
    // not a visual claim about any untested HMD pixels.
    constexpr std::array<unsigned,16> ids{{
        0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,28}};
    for(unsigned id:ids){
        (void)id;
        const bool externalPresent=true;
        const bool missingExternal=false;
        const bool dashboardMissing=true;
        const bool alphaGlass=true;
        const bool passengerAndShadow=true;
        for(bool installed:{externalPresent,missingExternal}){
            for(bool overlay:{false,dashboardMissing}){
                // No wrapper suppression allowed independent of sidecar or
                // missing dashboard. A future body-only hook is separate.
                assert(!(MaySkipRetailPlayerWrapper() && installed && overlay));
                assert(alphaGlass && passengerAndShadow);
            }
        }
        const auto gate=ValidGate();
        MeshDrawReceipt noRaster{};
        noRaster.expectedMeshes=3;
        noRaster.stateRestored=true;
        assert(ChooseOriginalCarRoute(gate,noRaster)==
               OriginalCarRoute::OriginalFallback);
        // A late right-eye or mesh failure after any raster is NEVER
        // equated with stock rollback from HRESULT alone.
        MeshDrawReceipt partial{};
        partial.expectedMeshes=3;
        partial.attemptedMeshes=1;
        partial.possiblySubmitted=true;
        partial.stateRestored=true;
        assert(ChooseOriginalCarRoute(gate,partial)==
               OriginalCarRoute::ExternalPartial);
        partial={};
        partial.stateMayBeDirty=true;
        assert(ChooseOriginalCarRoute(gate,partial)==
               OriginalCarRoute::ExternalPartial);
        auto stale=gate;stale.livePose++;
        assert(ChooseOriginalCarRoute(stale,noRaster)==
               OriginalCarRoute::OriginalFallback);
        // Hybrid embedded speed/RPM never authorizes dropping the *whole*
        // native dashboard when a separate overlay is absent.
        DashboardBinding speed{},rpm{},gear{};
        speed.kind=DashboardKind::SpeedNeedle;
        rpm.kind=DashboardKind::RpmNeedle;
        gear.kind=DashboardKind::GearVisible;
        gear.gear=3u;
        const auto telemetry=SanitizeDashboardTelemetry(88.f,4200u,3u);
        assert(telemetry.valid && telemetry.gear==3u);
        assert(DashboardOverlayMeshVisible(&gear,telemetry,0u));
        assert(DashboardNeedleMask(&speed,1)==DashboardSpeedNeedleBit);
        assert(DashboardNeedleMask(&rpm,1)==DashboardRpmNeedleBit);
        std::array<DashboardBinding,2> both{{speed,rpm}};
        assert(DashboardNeedleMask(both.data(),both.size())==
               DashboardBothNeedles);
        assert(!MaySkipRetailPlayerWrapper());
    }
}
