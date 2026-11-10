#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/projected_lens_inline_source.hpp"
#include "vr/game/stage_edge_cull_projection.hpp"
#include "vr/ui/vr_mirror_aspect_fit.hpp"
#include "vr/game/pmt_node_culling_contract.hpp"
#include "vr_shared.hpp"
#include "vr/game/quest_cockpit_v2_phase0_probe.hpp"
#include "vr/game/quest_cockpit_v2_runtime.hpp"
#include "vr/game/quest_cockpit_v2_seat.hpp"
#include "vr/game/quest_cockpit_v2_turn_yaw.hpp"
#include "vr/game/quest_cockpit_v2_occupant.hpp"
#include "vr/game/quest_cockpit_v2_visibility.hpp"
#include "vr/game/quest_cockpit_v2_native_frame.hpp"
#include "vr/game/quest_cockpit_v2_glass_hook.hpp"
#include "vr/game/reflection_frame_budget.hpp"
#include "vr/game/car_base_shadow_stereo.hpp"
#include "vr/runtime_eligibility.hpp"
#include "vr/d3d9/reset_trace.hpp"
#include <algorithm>
#include <iostream>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <utility>

namespace Settings
{
	Setting<int> SkyGlowFactor{ "Graphics", "SkyGlowFactor", 4,
		"If set above 0, restores the glowing sky/track effect from the console versions. Resolution of the glow effect is "
		"divided by the factor value: use 1 for full resolution, or 4 for quarter-res (same factor as console).", Range<int>{ 0, 16 } };
	Setting<bool> SkyGlowTwoStep{ "Graphics", "SkyGlowTwoStep", true,
		"Reduces aliasing in the sky glow effect by handling the SkyGlowFactor in two steps. "
		"Likely not console-accurate, but can help reduce the aliasing with Factor = 4 or higher." };
	// Defined by src/vr/settings.cpp. Sky glow samples the mono game backbuffer,
	// so it must be suppressed while true stereo is active or the left-eye bloom
	// gets composited into the right eye as a translucent ghost.
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRStereo;
	extern Setting<bool> VRTelemetry;
	extern Setting<bool> VRMirrorFitDesktop;
    extern Setting<bool> VRMirrorPreserveAspect;
    extern Setting<bool> VRAutoRenderResolution;
    extern Setting<int> VRAntiAliasing;
    extern Setting<int> VRStageCullingMode;
    extern Setting<bool> VRLensFlareCentreEnabled;
    extern Setting<float> VRCullingUnionMarginDegrees;
    extern Setting<bool> VRTransparencySupersampling;
	extern Setting<int> VRRenderWidth;
	extern Setting<int> VRRenderHeight;
	extern Setting<bool> VRDisableDesktopVsync;
	extern Setting<bool> VRCockpitFrameProbe;
    extern Setting<bool> VRQuestCockpitV2Enabled,VRQuestCockpitV2FullCar,VRQuestCockpitV2HideDriver,VRQuestCockpitV2RawB0Camera,VRQuestCockpitV2OccupantCorrection,VRQuestCockpitV2F0RenderScope,VRQuestCockpitV2OccupantLod0,VRQuestCockpitV2NativeSeatProfile,VRQuestCockpitV2GlassEnabled,VRQuestCockpitV2GlassHidden,VRQuestCockpitV2PassengerVisible,VRQuestCockpitV2GlassReflectionOff,VRQuestCockpitV2SkyProbe,VRQuestCockpitV2ApkNativeCamera;
    extern Setting<float> VRQuestCockpitV2SeatBack,VRQuestCockpitV2SeatDown,VRQuestCockpitV2SeatRight;
    extern Setting<float> VRQuestCockpitV2GlassBrightness;
	Setting<bool> RestoreXboxBrightness{ "Graphics", "RestoreXboxBrightness", false,
		"Restores the HDR effect from the Xbox releases, brightening up most areas of the game." };

	Setting<bool> UseHiDefCharacters{ "Graphics", "UseHiDefCharacters", true,
		"Forces hi-def versions of Alberto/Jennifer/Clarissa during gameplay." };

	Setting<int> AnisotropicFiltering{ "Graphics", "AnisotropicFiltering", 16,
		"1 - 16, 0 to leave it at games default.", Range<int>{ 0, 16 } };
	Setting<int> ReflectionResolution{ "Graphics", "ReflectionResolution", 512,
		"Resolution used for car reflections, games default is 128x128; 512x512 balances reflection detail and rendering cost.",
		Range<int>{ 0, 8192 } };
	Setting<float> ReflectionUpdateRate{ "Graphics", "ReflectionUpdateRate", 0.5f,
		"How much of the car reflection to redraw each frame: 1.0 redraws all faces every frame, 0.5 spreads it over two frames (games default).", Range<float>{ 0.0f, 1.0f } };
	Setting<bool> TransparencySupersampling{ "Graphics", "TransparencySupersampling", true,
		"Allows game to enable 4x transparency supersampling, heavily reducing aliasing on things like barriers or cloth "
		"around the track edge. For best results use this with \"DX/ANTIALIASING = 2\" inside outrun2006.ini." };
	Setting<bool> ScreenEdgeCullFix{ "Graphics", "ScreenEdgeCullFix", true,
		"Fixes certain stage objects disappearing before they reach edge of screen, when playing at non-4:3 aspect ratio." };
	Setting<bool> DisableVehicleLODs{ "Graphics", "DisableVehicleLODs", true,
		"Disables LODs on vehicles, reducing the ugly pop-in they have." };
	Setting<bool> DisableStageCulling{ "Graphics", "DisableStageCulling", true,
		"Disables culling of certain stage objects, so most distant objects won't obviously pop in to view." };
	Setting<bool> FixZBufferPrecision{ "Graphics", "FixZBufferPrecision", true,
		"Fixes Z-Buffer precision issues, greatly reducing z-fighting and distant object drawing issues "
		"(eg. signs/buildings will have much less pop-in)." };
	Setting<float> CarBaseShadowOpacity{ "Graphics", "CarBaseShadowOpacity", 1.0f,
		"Restores the player car base shadow that was included in other C2C ports. Opacity = 1.0 can help mask some issues "
		"with the stencil shadowing; Xbox C2C uses 0.5, but that makes it very transparent on PC.", Range<float>{ 0.0f, 1.0f } };

	Setting<int> VSync{ "Performance", "VSync", 1,
		"Syncs rendering to your displays refresh rate to reduce screen tearing.",
		{ "Disabled", "Enabled", "Half-refresh-rate" } };

	Setting<bool> WindowedBorderless{ "Window", "WindowedBorderless", true,
		"Forces windowed mode to become borderless. (requires \"DX/WINDOWED = 1\" inside outrun2006.ini)" };
	Setting<int> WindowPositionX{ "Window", "WindowPositionX", 0,
		"Only applied if WindowedBorderless is set to true." };
	Setting<int> WindowPositionY{ "Window", "WindowPositionY", 0,
		"Only applied if WindowedBorderless is set to true." };
	Setting<bool> DisableDPIScaling{ "Window", "DisableDPIScaling", true,
		"Disables DPI scaling on game window, can help fix issues when screen DPI is set above 100%." };
}

class UseHiDefCharacters : public Hook
{
	inline static const char ChrDrGh00_path[] = "Media\\CHR_DR_GH00.bin";
	inline static const char ChrDrGh00_gamepath[] = "\\Media\\CHR_DR_GH00.bin";
	inline static const char ChrDrGh00Usa_path[] = "Media\\CHR_DR_GH00_USA.bin";
	inline static const char ChrDrGh00Usa_gamepath[] = "\\Media\\CHR_DR_GH00_USA.bin";

public:
	std::string_view description() override
	{
		return "UseHiDefCharacters";
	}

	bool validate() override
	{
		return Settings::UseHiDefCharacters;
	}

	void declare_settings() override
	{
		Settings::UseHiDefCharacters.needs_restart();
	}

	bool apply() override
	{
		// Switch Chr\CHR_DR_GH00*.bin usages to read from Media\CHR_DR_GH00*.bin instead, if they exist
		// (Chr\ versions are missing hair anims which Media\ versions fortunately include - Media\ versions are otherwise unused)
		{
			if (std::filesystem::exists(ChrDrGh00_path))
				Game::chrset_info[ChrSet::CHR_DR_GH00].bin_ptr = ChrDrGh00_gamepath;
			if (std::filesystem::exists(ChrDrGh00Usa_path))
				Game::chrset_info[ChrSet::CHR_DR_GH00_USA].bin_ptr = ChrDrGh00Usa_gamepath;
		}

		int* driver_chrsets = Module::exe_ptr<int>(0x2549B0);
		int* heroine_chrsets = Module::exe_ptr<int>(0x2549C8);

		// Switch Alberto CHR_DR_M00 -> CHR_DR_MH00
		driver_chrsets[0] = ChrSet::CHR_DR_MH00;
		Memory::VP::Patch(Module::exe_ptr(0x87F41 + 1), { uint8_t(ChrSet::CHR_DR_MH00) }); // O2SP

		// Switch Jennifer CHR_DR_L00 -> CHR_DR_LH00
		heroine_chrsets[3] = ChrSet::CHR_DR_LH00;
		Memory::VP::Patch(Module::exe_ptr(0x8803A + 1), { uint8_t(ChrSet::CHR_DR_LH00) }); // O2SP

		// Switch Clarissa CHR_DR_G00_* -> CHR_DR_GH00_*
		heroine_chrsets[4] = ChrSet::CHR_DR_GH00; // (game code handles switching heroine_chrsets to USA variant, so we don't need to check RestoreJPClarissa here)

		// Clarissa O2SP code (this is also patched by RestoreJPClarissa, so make sure both set it to same value...)
		Memory::VP::Patch(Module::exe_ptr(0x88044 + 1), { Settings::RestoreJPClarissa ? uint8_t(ChrSet::CHR_DR_GH00) : uint8_t(ChrSet::CHR_DR_GH00_USA) });

		return true;
	}

	static UseHiDefCharacters instance;
};
UseHiDefCharacters UseHiDefCharacters::instance;

// Isolated V2 branch: retire every active legacy driver-seat detour.
// Only the original player-car state call is observed, never modified.
// The original Quest cockpit only permits mode 1 and a proven game-frame
// owner; the latter is still UNOBSERVED on PC and must never be guessed.
static bool IsPlayableCarGameplay() noexcept
{
    if (!Game::current_mode) return false;
    if (*Game::current_mode == STATE_GAME || *Game::current_mode == STATE_GOAL)
        return true;
    return *Game::current_mode == STATE_START &&
        Game::game_start_progress_code && *Game::game_start_progress_code == 65;
}

// Live Quest mode1 player glass hook, no PMT file writes. The player
// producer runs inside 49F3E0, whereas 404901 is an ordinary flush material
// consumer that can run later. Capturing only the current thread-local scope
// would miss deferred entries; broad material-pointer matching would tint
// traffic cars/world. Preserve an exact, bounded original queue identity.
namespace QuestCockpitGlassLive {
struct Token {
    const DrawEntry* entry=nullptr;
    std::uint32_t id=0;
    const CullingNode* node=nullptr;
    std::uint64_t epoch=0;
};
struct QueueCount { int before=-1; DrawBuffer* buffer=nullptr; };
struct Pending {
    float* rgba=nullptr;
    std::array<float,18> saved{};
    std::uint32_t* materialFlags=nullptr;
    std::uint32_t savedMaterialFlags=0;
    std::array<std::uint32_t*,3> layers{};
    std::array<std::uint32_t,3> savedLayers{};
};
inline thread_local std::array<Token,1024> Tokens{};
inline thread_local std::size_t TokenCount=0;
inline thread_local bool TooMany=false;
inline thread_local unsigned PlayerDepth=0;
inline thread_local std::array<Pending,16> PendingStack{};
inline thread_local unsigned PendingDepth=0,OverflowDepth=0;
inline thread_local unsigned LogCount=0;

// Never dereference a guessed register, PMT pointer or game stack address.
// Windows memory may be committed but EXECUTE_ONLY/guarded or unmapped.
static bool Memory(const void* p,std::size_t length,bool write=false) noexcept {
    if(!p || !length)return false;
    MEMORY_BASIC_INFORMATION mbi{};
    if(VirtualQuery(p,&mbi,sizeof(mbi))!=sizeof(mbi) ||
       mbi.State!=MEM_COMMIT || (mbi.Protect&PAGE_GUARD) ||
       (mbi.Protect&PAGE_NOACCESS))return false;
    const auto prot=mbi.Protect&0xFFu;
    bool readable=(prot==PAGE_READONLY||prot==PAGE_READWRITE||
        prot==PAGE_WRITECOPY||prot==PAGE_EXECUTE_READ||
        prot==PAGE_EXECUTE_READWRITE||prot==PAGE_EXECUTE_WRITECOPY);
    bool writable=(prot==PAGE_READWRITE||prot==PAGE_WRITECOPY||
        prot==PAGE_EXECUTE_READWRITE||prot==PAGE_EXECUTE_WRITECOPY);
    const auto paddr=reinterpret_cast<std::uintptr_t>(p);
    const auto base=reinterpret_cast<std::uintptr_t>(mbi.BaseAddress);
    return readable&&(!write||writable)&&paddr>=base&&
        length<=mbi.RegionSize && paddr-base<=mbi.RegionSize-length;
}
static void OnNewNativeFrame() noexcept {
    // This prevents stale queue slot reuse across frames; current material
    // updates must have completed/restored before the next frame.
    TokenCount=0;TooMany=false;
}
static QueueCount CaptureBefore(DrawBuffer* q) noexcept {
    QueueCount out{};
    if(!Memory(q,sizeof(DrawBuffer)))return out;
    const int count=q->NumBuffers_0,limit=q->MaxBuffers_4;
    if(count<0||limit<=0||limit>16384||count>limit)return out;
    out.buffer=q;out.before=count;return out;
}
static void CaptureAfter(const QueueCount& before,std::uint64_t epoch) noexcept {
    if(!epoch||TooMany||before.before<0||!before.buffer||
       !Memory(before.buffer,sizeof(DrawBuffer)))return;
    const DrawBuffer* q=before.buffer;
    const int count=q->NumBuffers_0;
    if(count<before.before||count>q->MaxBuffers_4||count>16384||
       !Memory(q->BufferPtrs_10,
           static_cast<std::size_t>(count)*sizeof(DrawEntry*)))return;
    for(int i=before.before;i<count;++i){
        const DrawEntry* e=q->BufferPtrs_10[i];
        if(!Memory(e,sizeof(DrawEntry)))continue;
        // Original PC DrawEntry is 0x3C; +0x38 is the queued object ID.
        // The cull node pointer and ID detect slot reuse in the same frame.
        std::uint32_t id=0;
        std::memcpy(&id,reinterpret_cast<const char*>(e)+0x38,sizeof(id));
        if(!id||id==0xffffffffu)continue;
        bool seen=false;
        for(std::size_t j=0;j<TokenCount;++j)
            if(Tokens[j].entry==e&&Tokens[j].epoch==epoch){seen=true;break;}
        if(seen)continue;
        if(TokenCount==Tokens.size()){
            TooMany=true;TokenCount=0;return;
        }
        Tokens[TokenCount++]={e,id,e->CullNode_18,epoch};
    }
}
struct PlayerCallback {
    bool admitted=false;
    QueueCount immediate{},after{};
    std::uint64_t epoch=0;
    explicit PlayerCallback(EVWORK_CAR* player) noexcept {
        // 49F3E0 can run during startup before camera/game events exist.
        // Defer ALL Game::camera/pl_car() access until runtime gates pass.
        epoch=OutRunVR::QuestCockpitV2::NativeFrameTrace().ActiveEpoch();
        if(!Settings::VREnabled||!Settings::VRQuestCockpitV2Enabled||
           !player||!epoch||!IsPlayableCarGameplay()||
           OutRunVR::QuestCockpitV2::InSceneEffect())return;
        const auto* camera=Game::camera();
        admitted=player==Game::pl_car()&&camera&&camera->cam_mode_34A==1;
        if(!admitted)return;
        immediate=CaptureBefore(Game::s_ImmDrawBuffer);
        after=CaptureBefore(Game::s_AftDrawBuffer);
        ++PlayerDepth;
    }
    ~PlayerCallback() noexcept {
        if(!admitted)return;
        // Persist exact descriptor pointers only, never borrow the vehicle
        // scope for unrelated draws after the callback unwinds.
        CaptureAfter(immediate,epoch);
        CaptureAfter(after,epoch);
        --PlayerDepth;
    }
    PlayerCallback(const PlayerCallback&)=delete;
    PlayerCallback& operator=(const PlayerCallback&)=delete;
};
static bool HasDeferredOwner(const SafetyHookContext& ctx,
    std::uint64_t epoch) noexcept
{
    if(TooMany||!TokenCount||!epoch)return false;
    // Do NOT scan arbitrary stack words: an old player descriptor can
    // survive there while the renderer is processing a scenery/traffic draw.
    // Deferred admission is fail-closed unless the current entry is still
    // held by one of the original x86 callee-saved live registers.
    const std::uintptr_t liveEntryRegisters[]{ctx.ebx,ctx.edi,ctx.ebp};
    const auto valueInContext=[&](std::uintptr_t addr) noexcept {
        for(auto value:liveEntryRegisters)if(value==addr)return true;
        return false;
    };
    for(std::size_t i=0;i<TokenCount;++i){
        const auto& t=Tokens[i];
        // Hot renderer path: compare three live register values FIRST.
        // VirtualQuery for every historical player queue token on every
        // unrelated stage draw would badly inflate frame time.
        if(t.epoch!=epoch||
           !valueInContext(reinterpret_cast<std::uintptr_t>(t.entry)))
            continue;
        if(!Memory(t.entry,sizeof(DrawEntry))||
           t.node!=t.entry->CullNode_18)continue;
        std::uint32_t currentId=0;
        std::memcpy(&currentId,
            reinterpret_cast<const char*>(t.entry)+0x38,sizeof(currentId));
        if(currentId==t.id)return true;
    }
    return false;
}
static void OnMaterialBefore(SafetyHookContext& ctx) noexcept {
    if(PendingDepth>=PendingStack.size()){
        if(OverflowDepth<1024u)++OverflowDepth;
        return;
    }
    Pending& pending=PendingStack[PendingDepth++];
    pending={};
    // Material calls also happen during loading; never obtain event/camera
    // pointers before original playable-game and verified-frame gates.
    const auto epoch=OutRunVR::QuestCockpitV2::NativeFrameTrace().ActiveEpoch();
    if(!Settings::VREnabled||!Settings::VRQuestCockpitV2Enabled||
       (!Settings::VRQuestCockpitV2GlassEnabled &&
        !Settings::VRQuestCockpitV2GlassHidden &&
        !Settings::VRQuestCockpitV2GlassReflectionOff)||
        !IsPlayableCarGameplay()||
       !epoch||OutRunVR::QuestCockpitV2::InSceneEffect())return;
    const auto* cam=Game::camera();
    if(!cam||cam->cam_mode_34A!=1||!Game::pl_car())return;
    const bool owner=PlayerDepth>0||HasDeferredOwner(ctx,epoch);
    if(!owner)return;
    // PC retail 4048F2/4048F5 material provenance: ESI points to the
    // relocated 0x3C-byte PmtObject; EDX to its indexed 0x58 PmtMaterial.
    // A source mismatch cannot grant material ownership.
    const auto* object=reinterpret_cast<const std::uint32_t*>(ctx.esi);
    const auto* material=reinterpret_cast<const std::uint32_t*>(ctx.edx);
    if(!Memory(object,0x3C)||!Memory(material,0x58))return;
    const auto* materials=reinterpret_cast<const std::uint8_t*>(object[0x34/4]);
    auto* colors=reinterpret_cast<std::uint8_t*>(object[0x38/4]);
    const auto* info=reinterpret_cast<const std::uint8_t*>(object[0x18/4]);
    if(!Memory(info,0x34))return;
    std::uint32_t nMaterials=0,nColors=0;
    std::memcpy(&nMaterials,info+0x2c,4);
    std::memcpy(&nColors,info+0x30,4);
    if(!nMaterials||nMaterials>1024||!nColors||nColors>1024||
       !Memory(materials,static_cast<std::size_t>(nMaterials)*0x58)||
       !Memory(colors,static_cast<std::size_t>(nColors)*0x48))return;
    const auto matptr=reinterpret_cast<std::uintptr_t>(material);
    const auto base=reinterpret_cast<std::uintptr_t>(materials);
    if(matptr<base||matptr-base>=static_cast<std::size_t>(nMaterials)*0x58||
       (matptr-base)%0x58!=0)return;
    const auto ci=material[0],attr=material[1];
    if(ci>=nColors)return;
    // Translate the PMT blend nibbles through the original PC retail
    // table at VA 0x61E784.  The on-device GetRenderState(19/20)
    // *before* 408C80 still belongs to the prior material: never use it
    // as proof for the material being installed.
    const auto* blend=reinterpret_cast<const std::uint32_t*>(
        Module::exe_ptr<std::uint8_t>(0x21E784));
    if(!Memory(blend,16*sizeof(std::uint32_t)))return;
    const unsigned src=(attr>>8)&15u,dst=(attr>>12)&15u;
    const bool selected=OutRunVR::QuestCockpitV2::Glass::Blend(
        attr,blend[src],blend[dst]);
    auto* rgba=reinterpret_cast<float*>(colors+ci*0x48);
    if(!Memory(rgba,16,true))return;
    const bool diffuse=OutRunVR::QuestCockpitV2::Glass::GlassDiffuse(
        rgba[0],rgba[1],rgba[2],rgba[3]);
    bool unique=diffuse&&selected;
    if(unique){
        for(std::uint32_t j=0;j<nMaterials;++j){
            if(materials+j*0x58==reinterpret_cast<const std::uint8_t*>(material))
                continue;
            std::uint32_t other=0;
            std::memcpy(&other,materials+j*0x58,4);
            if(other==ci){unique=false;break;}
        }
    }
    DWORD alphaBlend=FALSE;
    auto* device=Game::D3DDevice_ptr?*Game::D3DDevice_ptr:nullptr;
    const bool alphaPass=device &&
        SUCCEEDED(device->GetRenderState(D3DRS_ALPHABLENDENABLE,&alphaBlend)) &&
        alphaBlend!=FALSE;
    if(!OutRunVR::QuestCockpitV2::Glass::Admit(
        true,true,true,true,true,true,true,owner,alphaPass,
        selected,diffuse,unique))return;
    const bool hide=Settings::VRQuestCockpitV2GlassHidden;
    const bool noReflection=Settings::VRQuestCockpitV2GlassReflectionOff||hide;
    const bool tint=Settings::VRQuestCockpitV2GlassEnabled;
    const float brightness=Settings::VRQuestCockpitV2GlassBrightness.get();
    const float target=hide?0.f:
        OutRunVR::QuestCockpitV2::Glass::AlphaFromBrightness(brightness);
    if(!std::isfinite(target))return;
    if(!hide&&!noReflection&&(!tint||std::fabs(rgba[3]-target)<.00001f))
        return;
    // Original PC 408F90: reflection is NOT just diffuse alpha; material
    // flags bit0 enable specular, fixed shader modes 4/5 bind cubemaps,
    // 409430 layer bits 0x02/0x08/0x80 bind environment texture stages.
    // Patch only the exact material during original 408C80 state install.
    // Device state/cache then contains NON-reflective shader for the draw;
    // restore original data at 404907 before any later material.
    auto* writableMaterial=const_cast<std::uint32_t*>(material);
    if(!Memory(rgba,18*sizeof(float),true))return;
    if(noReflection&&!Memory(writableMaterial,0x58,true))return;
    pending.rgba=rgba;
    std::memcpy(pending.saved.data(),rgba,18*sizeof(float));
    if(noReflection) {
        pending.materialFlags=writableMaterial+1;
        pending.savedMaterialFlags=writableMaterial[1];
        writableMaterial[1]=OutRunVR::QuestCockpitV2::Glass::
            RemoveGlassReflectionFlags(writableMaterial[1]);
        for(std::size_t i=0;i<3;++i) {
            // PmtMaterial layer[i] at +08 + i*0x14, flags at +00.
            auto* layer=writableMaterial+2+i*5;
            pending.layers[i]=layer;
            pending.savedLayers[i]=*layer;
            *layer=OutRunVR::QuestCockpitV2::Glass::
                RemoveGlassReflectionLayer(*layer);
        }
        OutRunVR::QuestCockpitV2::Glass::
            SuppressGlassReflectionColours(rgba,hide);
    }
    if(hide) {
        // One/InvSrcAlpha may otherwise retain RGB; all D3DMATERIAL9
        // diffuse/ambient/specular/emissive become zero. Keep geometry
        // and original material draws, no guessed reflection mesh skip.
        rgba[0]=rgba[1]=rgba[2]=rgba[3]=0.f;
    } else if(tint) {
        rgba[3]=target;
    }
    if(Settings::VRTelemetry&&++LogCount<=24u)
        spdlog::info("VR COCKPIT GLASS LIVE: epoch={} owner={} material={:p} "
            "originalAlpha={:.4f} appliedAlpha={:.4f} hidden={} "
            "reflectionOff={} originalShaderMode={} brightness={:.1f} "
            "restore=after_original_408C80 QuestWindowMesh=UNTESTED",
            epoch,PlayerDepth?"player-callback":"matched-queue",
            static_cast<const void*>(material),pending.saved[3],
            rgba[3],hide,noReflection,(attr>>19)&15u,brightness);
}
static void OnMaterialAfter(SafetyHookContext&) noexcept {
    if(OverflowDepth){--OverflowDepth;return;}
    if(!PendingDepth)return;
    Pending pending=PendingStack[--PendingDepth];
    PendingStack[PendingDepth]={};
    if(pending.materialFlags&&Memory(pending.materialFlags,sizeof(std::uint32_t),true))
        *pending.materialFlags=pending.savedMaterialFlags;
    for(std::size_t i=0;i<pending.layers.size();++i) {
        if(pending.layers[i]&&Memory(pending.layers[i],sizeof(std::uint32_t),true))
            *pending.layers[i]=pending.savedLayers[i];
    }
    if(pending.rgba&&Memory(pending.rgba,18*sizeof(float),true))
        std::memcpy(pending.rgba,pending.saved.data(),18*sizeof(float));
}
} // namespace QuestCockpitGlassLive

class QuestCockpitV2GlassRuntimeHook final : public Hook {
    inline static SafetyHookMid MaterialBefore{},MaterialAfter{};
public:
    std::string_view description() override {
        return "VRQuestCockpitV2GlassRuntimeHook";
    }
    bool validate() override {
        // Hooks install at startup. F11 glass toggle itself is LIVE; it does
        // not require a restart once the experimental cockpit is enabled.
        return Settings::VREnabled&&Settings::VRQuestCockpitV2Enabled;
    }
    bool apply() override {
        constexpr std::array<std::uint8_t,6> sig{
            0x52,0xE8,0x79,0x43,0x00,0x00};
        const auto* p=Module::exe_ptr<std::uint8_t>(0x4901);
        if(!QuestCockpitGlassLive::Memory(p,sig.size())||
           !std::equal(sig.begin(),sig.end(),p)){
            spdlog::warn("VR COCKPIT GLASS: original 404901 PMT call mismatch; no hook");
            return false;
        }
        // At 404901 PUSH EDX; at 404902 CALL 408C80; 404907 is the
        // first instruction after the original material state is consumed.
        auto after=safetyhook::create_mid(Module::exe_ptr(0x4907),
            QuestCockpitGlassLive::OnMaterialAfter);
        if(!after)return false;
        auto before=safetyhook::create_mid(Module::exe_ptr(0x4901),
            QuestCockpitGlassLive::OnMaterialBefore);
        if(!before)return false;
        MaterialAfter=std::move(after);
        MaterialBefore=std::move(before);
        return true;
    }
    static QuestCockpitV2GlassRuntimeHook instance;
};
QuestCockpitV2GlassRuntimeHook QuestCockpitV2GlassRuntimeHook::instance;

// Original retail PC frame-render clock: distinct from Present and XR.
class QuestCockpitV2NativeFrameProbe final : public Hook
{
    static constexpr int FrameEnterRva=0x49050;
    static constexpr int FrameEndRva=0x48E40;
    static constexpr int PlayerCallbackRva=0x9F3E0;
    inline static SafetyHookMid FrameEnterHook{},FrameEndHook{};
    inline static SafetyHookInline PlayerCallbackHook{};
    inline static thread_local bool F0CallbackActive=false;
    static constexpr std::size_t SeatTableCount=30u;
    inline static bool SeatTableCaptured=false;
    inline static bool SeatTablePatched=false;
    inline static std::array<std::array<float,3>,SeatTableCount>
        SeatTableOriginal{};

    static bool CaptureNativeSeatTable() noexcept
    {
        if(SeatTableCaptured)return true;
        constexpr std::size_t kStride=36u;
        constexpr std::size_t kBytes=SeatTableCount*kStride;
        auto* table=Module::exe_ptr<std::uint8_t>(0x418BB0);
        // The original runtime copies PE 0x5BA4E0 to live VA 0x818BB0.
        // Installing this hook before that copy used to capture 30 zeroed
        // records as the "original" fallback, corrupting later restoration.
        const auto* original=Module::exe_ptr<const std::uint8_t>(0x1BA4E0);
        if(!QuestCockpitGlassLive::Memory(original,kBytes))return false;
        for(std::size_t i=0;i<SeatTableCount;++i) {
            if(!QuestCockpitGlassLive::Memory(
                   table+i*kStride,3u*sizeof(float),true))return false;
        }
        if(!OutRunVR::QuestCockpitV2::OriginalModeOneTableInitialized(
               table,kBytes,original,kBytes))return false;
        for(std::size_t i=0;i<SeatTableCount;++i)
            std::memcpy(SeatTableOriginal[i].data(),
                        table+i*kStride,3u*sizeof(float));
        SeatTableCaptured=true;
        return true;
    }

    static bool RestoreNativeSeatProfile() noexcept
    {
        // Failed or partial rollback cannot authorize Quest-native eyes.
        OutRunVR::QuestCockpitV2::NativeSeatCameraTick.Invalidate();
        if(!SeatTableCaptured || !SeatTablePatched)return true;
        constexpr std::size_t kStride=36u;
        auto* table=Module::exe_ptr<std::uint8_t>(0x418BB0);
        // A partial rollback must never be advertised as a clean original
        // camera table. Preflight EVERY row before changing any of them.
        // Keep SeatTablePatched armed when a row is unavailable so a later
        // state transition can retry the original anchors.
        for(std::size_t i=0;i<SeatTableCount;++i) {
            auto* row=table+i*kStride;
            if(!QuestCockpitGlassLive::Memory(row,3u*sizeof(float),true))
                return false;
        }
        for(std::size_t i=0;i<SeatTableCount;++i)
            std::memcpy(table+i*kStride,SeatTableOriginal[i].data(),
                        3u*sizeof(float));
        SeatTablePatched=false;
        return true;
    }

    static bool SyncNativeSeatProfile(bool afterOriginalCameraTick) noexcept
    {
        // 485FE0 CAMERA control runs before 449050 frame rendering. Therefore
        // the mode1 table must already contain the Quest anchors before the
        // next camera tick; a frame-enter/frame-end-only scope is too late.
        if(!CaptureNativeSeatTable()) {
            OutRunVR::QuestCockpitV2::NativeSeatCameraTick.Invalidate();
            return false;
        }
        const bool apkRaceGameState=
            !Settings::VRQuestCockpitV2ApkNativeCamera ||
            (Game::current_mode &&
             OutRunVR::QuestCockpitV2::OriginalQuestGameCameraState(
                static_cast<std::uint32_t>(*Game::current_mode)));
        // Native Quest's state==0x10 camera admission is OFF during
        // menu, START and GOAL. Restore PC view1 anchors there.
        // Original PadSnapshot toggle remains unknown, not fabricated.
        const bool requested=
            Settings::VREnabled && Settings::VRQuestCockpitV2Enabled &&
            Settings::VRQuestCockpitV2NativeSeatProfile && apkRaceGameState;
        if(!requested)
            return RestoreNativeSeatProfile();

        constexpr std::size_t kStride=36u,kProfileStride=0x128u;
        const auto* profiles=Module::exe_ptr<const std::uint8_t>(0x1B0CB8);
        const auto* pointers=Module::exe_ptr<const std::uint8_t>(0x1B2F68);
        if(!QuestCockpitGlassLive::Memory(
               profiles,SeatTableCount*kProfileStride) ||
           !QuestCockpitGlassLive::Memory(
               pointers,SeatTableCount*sizeof(std::uint32_t))) {
            RestoreNativeSeatProfile();
            return false;
        }

        const bool apkNativeCamera=
            Settings::VRQuestCockpitV2ApkNativeCamera.get();
        // Quest 3 physical feedback 2026-11-10: signed F11 offsets
        // CALIBRATE the selected native Quest profile BEFORE stock camera
        // swing, ground clamp and the single +0.32Y/+0.55Z composition.
        // Zero means uncalibrated APK-derived pose. No XR eye offset.
        const float manualBack=Settings::VRQuestCockpitV2SeatBack.get();
        const float manualDown=Settings::VRQuestCockpitV2SeatDown.get();
        const float manualRight=Settings::VRQuestCockpitV2SeatRight.get();
        if(apkNativeCamera) {
            static bool logged=false;
            static float priorBack=0.f,priorDown=0.f,priorRight=0.f;
            if(!logged || manualBack!=priorBack ||
               manualDown!=priorDown || manualRight!=priorRight) {
                logged=true;
                priorBack=manualBack;priorDown=manualDown;priorRight=manualRight;
                spdlog::info(
                    "VR COCKPIT APK SEAT: calibrated back={:.3f} "
                    "down={:.3f} right={:.3f}; native Y/Z exactly once",
                    manualBack,manualDown,manualRight);
            }
        }

        std::array<OutRunVR::QuestCockpitV2::Vec3,SeatTableCount> injected{};
        for(std::size_t i=0;i<SeatTableCount;++i) {
            OutRunVR::QuestCockpitV2::Vec3 profile{};
            OutRunVR::QuestCockpitV2::Vec3 tuned{};
            if(!OutRunVR::QuestCockpitV2::OriginalQuestVrProfileAnchor(
                   pointers,SeatTableCount*sizeof(std::uint32_t),
                   profiles,SeatTableCount*kProfileStride,
                   static_cast<int>(i),profile) ||
               !OutRunVR::QuestCockpitV2::NativeVrProfileInputAnchor(
                   profile,manualBack,manualDown,manualRight,tuned) ||
               (apkNativeCamera
                    ? !OutRunVR::QuestCockpitV2::OriginalQuestModeOneInput(
                          tuned,injected[i])
                    : (injected[i]=tuned,false))) {
                RestoreNativeSeatProfile();
                return false;
            }
        }

        auto* table=Module::exe_ptr<std::uint8_t>(0x418BB0);
        // Compare all 30 original seat inputs before changing anything.
        // An initial game entry or live F11 adjustment cannot share an
        // APK-native eye matrix with a camera that used the previous table.
        bool sameInput=SeatTablePatched;
        for(std::size_t i=0;i<SeatTableCount;++i) {
            const auto* row=table+i*kStride;
            if(!QuestCockpitGlassLive::Memory(row,3u*sizeof(float),true)) {
                RestoreNativeSeatProfile();
                return false;
            }
            static_assert(sizeof(injected[i])==3u*sizeof(float));
            if(std::memcmp(row,&injected[i],3u*sizeof(float))!=0)
                sameInput=false;
        }
        const bool previouslyPatched=SeatTablePatched;
        // Keep the existing admission stable when nothing changed; an
        // unnecessary per-tick false/true would flicker a parallel Draw.
        if(!sameInput)
            OutRunVR::QuestCockpitV2::NativeSeatCameraTick.Invalidate();
        SeatTablePatched=true;
        for(std::size_t i=0;i<SeatTableCount;++i) {
            auto* row=table+i*kStride;
            // Unchanged input requires no guest-memory rewrite.
            if(std::memcmp(row,&injected[i],3u*sizeof(float))!=0)
                std::memcpy(row,&injected[i],3u*sizeof(float));
        }
        OutRunVR::QuestCockpitV2::NativeSeatCameraTick.AfterSeatSync(
            previouslyPatched,sameInput,apkNativeCamera,afterOriginalCameraTick);
        return true;
    }
    static void OnFrameEnter(SafetyHookContext&)
    {
        // Camera control for the next tick reads this persistent live table.
        // Re-sync here only for live F11/tuning changes; startup apply below
        // installs the profile before the first playable camera tick.
        const bool synced=SyncNativeSeatProfile(true);
        if(Settings::VRQuestCockpitV2Enabled &&
           Settings::VRQuestCockpitV2NativeSeatProfile &&
           Game::current_mode &&
           OutRunVR::QuestCockpitV2::OriginalQuestGameCameraState(
               static_cast<std::uint32_t>(*Game::current_mode))) {
            static bool loggedReady=false;
            static unsigned missingCount=0;
            if(synced &&
               OutRunVR::QuestCockpitV2::NativeSeatCameraTick.Ready() &&
               !loggedReady) {
                loggedReady=true;
                spdlog::info("VR COCKPIT SEAT: original 30-car table "
                    "synchronized before native camera tick; "
                    "Quest-native eye admission enabled");
            } else if(!synced && ++missingCount==90u) {
                spdlog::warn("VR COCKPIT SEAT: GAME 90 frames without "
                    "native seat-table sync; original PC camera retained");
            }
        }
        OutRunVR::QuestCockpitV2::NativeFrameTrace().OnFrameEnter(
            OutRunVR::QuestCockpitV2::NextVerifiedNativeEpoch());
        QuestCockpitGlassLive::OnNewNativeFrame();
    }
    static void OnFrameEnd(SafetyHookContext&)
    {
        OutRunVR::QuestCockpitV2::NativeFrameTrace().OnFrameEnd();
    }
    // Bounded on-thread observation before optional F0 staging.
    // Player B0 is the interpolated display basis, F0 is the local
    // body/suspension basis; the native mode1 camera is a distinct producer.
    // This does NOT attribute bounce until these deltas are seen on the HMD.
    static void ProbeCockpitCarMotion(const EVWORK_CAR* player) noexcept
    {
        if(!Settings::VRQuestCockpitV2SkyProbe ||
           !Settings::VRQuestCockpitV2Enabled ||
           !player || player!=Game::pl_car()) return;
        const auto* camera=Game::camera();
        if(!camera || camera->cam_mode_34A!=1) return;
        const float b0Y=player->matrix_B0._42;
        const float f0Y=player->matrix_F0._42;
        const float cameraY=camera->cam_pos_F8.y;
        // Stock PC/Quest mode1 camera yaw uses auxiliary car+0x1FE;
        // the body itself points along car+0x2E. Diagnose this
        // separate original producer without mutating game/VR state.
        const auto bodyWord=static_cast<std::uint16_t>(player->field_2C[1]);
        const auto auxWord=player->field_1FE;
        const auto steerWord=static_cast<std::uint16_t>(player->field_162);
        const float auxBodyDeg=
            OutRunVR::QuestCockpitV2::YawWordDeltaDegrees(auxWord,bodyWord);
        const float cameraLookYaw=camera->cam_ang_128.y;
        // Compare the actually rendered/interpolated player B0 orientation
        // against the actually rendered/interpolated camera look vector.
        // bodyWord/auxWord are simulation-domain values and can legitimately
        // be one phase away on >60 Hz zero-tick frames; this visual-domain
        // pair removes that ambiguity when diagnosing "camera turns first".
        const float b0ForwardX=player->matrix_B0._31;
        const float b0ForwardZ=player->matrix_B0._33;
        const float cameraForwardX=camera->look_pos_104.x-camera->cam_pos_F8.x;
        const float cameraForwardZ=camera->look_pos_104.z-camera->cam_pos_F8.z;
        const float b0ForwardNorm=std::hypot(b0ForwardX,b0ForwardZ);
        const float cameraForwardNorm=std::hypot(cameraForwardX,cameraForwardZ);
        if(!(b0ForwardNorm>1.0e-5f) || !(cameraForwardNorm>1.0e-5f))
            return;
        const float visualCarYaw=std::atan2(b0ForwardX,b0ForwardZ);
        const float visualCameraYaw=std::atan2(cameraForwardX,cameraForwardZ);
        const float visualCarCameraGapDeg=
            OutRunVR::QuestCockpitV2::YawRadiansStepDegrees(
                visualCameraYaw,visualCarYaw);
        const float interpAlpha=Game::g_InterpAlpha
            ? *Game::g_InterpAlpha : 1.0f;
        const float speed=player->field_1C4;
        if(!std::isfinite(b0Y)||!std::isfinite(f0Y)||
           !std::isfinite(cameraY)||!std::isfinite(cameraLookYaw)||
           !std::isfinite(visualCarCameraGapDeg)||
           !std::isfinite(interpAlpha)||!std::isfinite(speed))return;
        static const EVWORK_CAR* lastPlayer=nullptr;
        static float lastB0Y=0.f,lastF0Y=0.f,lastCameraY=0.f;
        static float lastRelativeY=0.f;
        static float maxB0Delta=0.f,maxF0Delta=0.f,maxCameraDelta=0.f;
        static float maxRelativeDelta=0.f;
        static std::uint16_t prevBody=0,prevAux=0;
        static float prevCameraLookYaw=0.f;
        static float prevVisualCarYaw=0.f,prevVisualCameraYaw=0.f;
        static unsigned turnTraceSamples=0,turnTraceQualified=0;
        static float maxBodyYawStep=0.f,maxAuxYawStep=0.f;
        static float maxCameraYawStep=0.f,maxAuxBodyGap=0.f;
        static float maxVisualCarCameraGap=0.f;
        static float maxSteering=0.f;
        static unsigned observations=0;
        if(lastPlayer!=player) {
            lastPlayer=player;observations=0;
            maxB0Delta=maxF0Delta=maxCameraDelta=maxRelativeDelta=0.f;
            lastB0Y=b0Y;lastF0Y=f0Y;lastCameraY=cameraY;
            lastRelativeY=b0Y-cameraY;
            prevBody=bodyWord;prevAux=auxWord;
            prevCameraLookYaw=cameraLookYaw;
            prevVisualCarYaw=visualCarYaw;
            prevVisualCameraYaw=visualCameraYaw;
            turnTraceSamples=turnTraceQualified=0;
            maxBodyYawStep=maxAuxYawStep=maxCameraYawStep=0.f;
            maxAuxBodyGap=maxVisualCarCameraGap=maxSteering=0.f;
        }
        const float bodyStepDeg=
            OutRunVR::QuestCockpitV2::YawWordDeltaDegrees(bodyWord,prevBody);
        const float auxStepDeg=
            OutRunVR::QuestCockpitV2::YawWordDeltaDegrees(auxWord,prevAux);
        const float cameraStepDeg=
            OutRunVR::QuestCockpitV2::YawRadiansStepDegrees(
                cameraLookYaw,prevCameraLookYaw);
        const float visualCarStepDeg=
            OutRunVR::QuestCockpitV2::YawRadiansStepDegrees(
                visualCarYaw,prevVisualCarYaw);
        const float visualCameraStepDeg=
            OutRunVR::QuestCockpitV2::YawRadiansStepDegrees(
                visualCameraYaw,prevVisualCameraYaw);
        maxBodyYawStep=(std::max)(maxBodyYawStep,std::fabs(bodyStepDeg));
        maxAuxYawStep=(std::max)(maxAuxYawStep,std::fabs(auxStepDeg));
        maxCameraYawStep=(std::max)(maxCameraYawStep,std::fabs(cameraStepDeg));
        maxAuxBodyGap=(std::max)(maxAuxBodyGap,std::fabs(auxBodyDeg));
        maxVisualCarCameraGap=(std::max)(
            maxVisualCarCameraGap,std::fabs(visualCarCameraGapDeg));
        maxSteering=(std::max)(maxSteering,std::fabs(
            OutRunVR::QuestCockpitV2::YawWordDeltaDegrees(steerWord,0)));
        const float steeringDeg=
            OutRunVR::QuestCockpitV2::YawWordDeltaDegrees(steerWord,0);
        // Bounded, read-only temporal trace for the user's "camera turns
        // first" report. Sample only meaningful moving steering and decimate
        // to every second qualifying player draw; at most 48 lines per player
        // lifetime, so this cannot become multi-GB per-draw telemetry.
        if(speed>0.00922849774f && std::fabs(steeringDeg)>=0.5f &&
           turnTraceSamples<48u && (++turnTraceQualified&1u)==0u) {
            ++turnTraceSamples;
            spdlog::info(
                "VR CAMERA TURN TRACE: sample={} nativeEpoch={} "
                "interpAlpha={:.4f} steerDeg={:.3f} speed={:.6f} "
                "step[body={:.3f},aux={:.3f},gameCam={:.3f},"
                "renderCar={:.3f},renderLook={:.3f}] "
                "gap[auxBody={:.3f},renderCarCam={:.3f}]",
                turnTraceSamples,
                OutRunVR::QuestCockpitV2::NativeFrameTrace().ActiveEpoch(),
                interpAlpha,steeringDeg,speed,
                bodyStepDeg,auxStepDeg,cameraStepDeg,
                visualCarStepDeg,visualCameraStepDeg,
                auxBodyDeg,visualCarCameraGapDeg);
        }
        prevBody=bodyWord;prevAux=auxWord;
        prevCameraLookYaw=cameraLookYaw;
        prevVisualCarYaw=visualCarYaw;
        prevVisualCameraYaw=visualCameraYaw;
        const float b0Delta=std::fabs(b0Y-lastB0Y);
        const float f0Delta=std::fabs(f0Y-lastF0Y);
        const float cameraDelta=std::fabs(cameraY-lastCameraY);
        const float relativeY=b0Y-cameraY;
        const float relativeDelta=std::fabs(relativeY-lastRelativeY);
        if(relativeDelta>maxRelativeDelta)maxRelativeDelta=relativeDelta;
        if(b0Delta>maxB0Delta)maxB0Delta=b0Delta;
        if(f0Delta>maxF0Delta)maxF0Delta=f0Delta;
        if(cameraDelta>maxCameraDelta)maxCameraDelta=cameraDelta;
        lastB0Y=b0Y;lastF0Y=f0Y;lastCameraY=cameraY;
        lastRelativeY=relativeY;
        if(++observations==90u) {
            spdlog::info(
                "VR CAR MOTION PROBE: samples=90 maxDeltaB0Y={:.5f} "
                "maxDeltaF0Y={:.5f} maxDeltaCameraY={:.5f} "
                "maxDeltaCarMinusCameraY={:.5f} "
                "currentB0Y={:.5f} currentF0Y={:.5f} currentCameraY={:.5f} "
                "f0RenderScope={} (render-only source, not tire physics)",
                maxB0Delta,maxF0Delta,maxCameraDelta,maxRelativeDelta,
                b0Y,f0Y,cameraY,
                Settings::VRQuestCockpitV2F0RenderScope.get());
            spdlog::info(
                "VR CAMERA YAW PROBE: samples=90 "
                "maxBodyYawStepDeg={:.3f} maxAuxYawStepDeg={:.3f} "
                "maxCameraYawStepDeg={:.3f} "
                "maxAuxBodyGapDeg={:.3f} auxMinusBodyDeg={:.3f} "
                "maxVisualCarCameraGapDeg={:.3f} "
                "visualCarCameraGapDeg={:.3f} interpAlpha={:.4f} "
                "maxSteerDeg={:.3f} speed={:.6f} f0RenderScope={}",
                maxBodyYawStep,maxAuxYawStep,maxCameraYawStep,
                maxAuxBodyGap,auxBodyDeg,maxVisualCarCameraGap,
                visualCarCameraGapDeg,interpAlpha,maxSteering,speed,
                Settings::VRQuestCockpitV2F0RenderScope.get());
            observations=0;
            maxB0Delta=maxF0Delta=maxCameraDelta=maxRelativeDelta=0.f;
            maxBodyYawStep=maxAuxYawStep=maxCameraYawStep=0.f;
            maxAuxBodyGap=maxVisualCarCameraGap=maxSteering=0.f;
        }
    }
    static void CallOriginalPlayerWithGlassScope(EVWORK_CAR* player)
    {
        QuestCockpitGlassLive::PlayerCallback scope(player);
        PlayerCallbackHook.ccall<void>(player);
    }
    static void __cdecl OnPlayerCallback(EVWORK_CAR* player)
    {
        using namespace OutRunVR::QuestCockpitV2;
        // Original 0x49F3E0: push ESI; mov ESI,[ESP+8];
        // push ESI; call original 0x46BD30 (player car display).
        // This 1-argument cdecl wrapper ends POP ESI; RET. It is
        // the nearest bounded original player-render scope on PC.
        NativeFrameTrace().OnPlayerCallback();
        ProbeCockpitCarMotion(player);
        // Crash isolation: startup/loading may invoke original 49F3E0
        // before the game camera and XR frame are constructed. Do not
        // dereference either for an OFF / not-yet-gameplay experiment.
        if (!Settings::VREnabled || !Settings::VRQuestCockpitV2Enabled ||
            !Settings::VRQuestCockpitV2F0RenderScope ||
            !NativeOriginalHooksReady.load(std::memory_order_acquire) ||
            !NativeFrameTrace().Active() || !IsPlayableCarGameplay() ||
            !player) {
            CallOriginalPlayerWithGlassScope(player);
            return;
        }
        const EvWorkCamera* camera=Game::camera();
        const auto* xr=OutRunVRRenderer::GetLatchedStereoFrameView();
        const bool admitted=VerifiedPlayerF0CallOwner(
            Settings::VREnabled && Settings::VRQuestCockpitV2Enabled &&
               Settings::VRQuestCockpitV2F0RenderScope,
            player && player==Game::pl_car(),
            NativeFrameTrace().Active(),camera && camera->cam_mode_34A==1,
            xr && xr->valid && xr->poseSequence!=0,
            InSceneEffect(),F0CallbackActive);
        if(!admitted){
            CallOriginalPlayerWithGlassScope(player);
            return;
        }
        // The original Quest computes C from immutable B0/F0 BEFORE
        // substituting F0. The separate native robot draw, if later in
        // the game frame, recomputes C only after F0 is restored.
        // Never mutate simulation work across an end-of-frame boundary.
        Matrix b0{},f0{},C{};
        std::memcpy(b0.data(),&player->matrix_B0,sizeof(Matrix));
        std::memcpy(f0.data(),&player->matrix_F0,sizeof(Matrix));
        if(!ComputeBodyCorrection(b0,f0,C)){
            CallOriginalPlayerWithGlassScope(player);
            return;
        }
        // Reentrancy blocked; both F0 and TLS owner restored in reverse
        // order even if the original synchronous callback throws.
        struct FlagGuard {
            bool& flag;
            explicit FlagGuard(bool& f) noexcept:flag(f){flag=true;}
            ~FlagGuard() noexcept {flag=false;}
        } marker(F0CallbackActive);
        // Original Quest: publish pre-identity B0/F0 correction before F0
        // staging, retain it for original occupant draws nested in this call.
        // Destructor order first restores F0, then clears the saved owner.
        const ScopedPreF0SnapshotData originalMatrices{
            reinterpret_cast<std::uintptr_t>(player),
            NativeFrameTrace().ActiveEpoch(),xr->poseSequence,b0,f0,C
        };
        ScopedPreF0Snapshot preF0Owner(originalMatrices,true);
        ScopedOriginalPlayerF0 scope(
            reinterpret_cast<float*>(&player->matrix_F0),
            preF0Owner.Active());
        static thread_local std::uint32_t trace=0;
        if(Settings::VRCockpitFrameProbe && Settings::VRTelemetry &&
           ++trace<=32u)
            spdlog::info("VR COCKPIT V2 F0: sample={} originalCar=1 "
                "nativeFrame={} xrPose={} identityScoped=1 unwindRestore=1 "
                "QuestFullFrameEquivalence=UNTESTED",
                trace,NativeFrameTrace().ActiveEpoch(),xr->poseSequence);
        CallOriginalPlayerWithGlassScope(player);
    }
    template<std::size_t N>
    static bool MatchOriginalRva(int rva,
        const std::array<std::uint8_t,N>& signature)
    {
        // Reject all other executable builds and any previously detoured
        // entrypoints; never patch an unknown instruction stream.
        const auto* p=Module::exe_ptr<std::uint8_t>(rva);
        MEMORY_BASIC_INFORMATION info{};
        if (!p || VirtualQuery(p,&info,sizeof(info))!=sizeof(info) ||
            info.State!=MEM_COMMIT || (info.Protect & PAGE_GUARD) ||
            (info.Protect & PAGE_NOACCESS) ||
            reinterpret_cast<std::uintptr_t>(p)+N >
                reinterpret_cast<std::uintptr_t>(info.BaseAddress)+info.RegionSize)
            return false;
        return std::equal(signature.begin(),signature.end(),p);
    }
public:
    std::string_view description() override {
        return "QuestCockpitV2NativeFrameProbe";
    }
    bool validate() override {
        return Settings::VREnabled &&
            (Settings::VRCockpitFrameProbe||Settings::VRQuestCockpitV2Enabled);
    }
    bool apply() override {
        // Prologue bytes were extracted from the user's owned canonical PC
        // EXE. All three hook owners must be installed or none remain.
        constexpr std::array<std::uint8_t,24> begin{{
            0xA1,0x14,0x26,0x7D,0x00,0x83,0xEC,0x30,
            0x53,0x56,0x33,0xDB,0x83,0xCE,0xFF,0x3B,
            0xC3,0x75,0x05,0xE8,0xF8,0x5C,0xFC,0xFF
        }};
        constexpr std::array<std::uint8_t,24> end{{
            0x8B,0x0D,0xE8,0x25,0x7D,0x00,0xA1,0xEC,
            0x25,0x7D,0x00,0x3B,0xC1,0x8B,0x0D,
            0xF4,0x25,0x7D,0x00,0x75,0x08,0x3B,0x0D,0x10
        }};
        constexpr std::array<std::uint8_t,24> player{{
            0x56,0x8B,0x74,0x24,0x08,0x56,0xE8,0x45,
            0xC9,0xFC,0xFF,0x68,0xF0,0xE7,0x82,0x00,
            0x56,0xE8,0x5A,0xB2,0xFF,0xFF,0x83,0xC4
        }};
        if (!MatchOriginalRva(FrameEnterRva,begin) ||
            !MatchOriginalRva(FrameEndRva,end) ||
            !MatchOriginalRva(PlayerCallbackRva,player)) {
            spdlog::warn("VR COCKPIT V2 native frame probe unavailable: "
                "original EXE signatures differ; cockpit remains disabled");
            return false;
        }
        auto first=safetyhook::create_mid(
            Module::exe_ptr(FrameEnterRva),OnFrameEnter);
        if(!first)return false;
        auto last=safetyhook::create_mid(
            Module::exe_ptr(FrameEndRva),OnFrameEnd);
        if(!last)return false;
        auto actor=safetyhook::create_inline(
            Module::exe_ptr(PlayerCallbackRva),OnPlayerCallback);
        if(!actor)return false;
        FrameEnterHook=std::move(first);
        FrameEndHook=std::move(last);
        PlayerCallbackHook=std::move(actor);
        OutRunVR::QuestCockpitV2::NativeOriginalHooksReady.store(true,std::memory_order_release);
        if(!SyncNativeSeatProfile(false) &&
           Settings::VRQuestCockpitV2NativeSeatProfile)
            spdlog::info("VR COCKPIT: initial seat table sync deferred; "
                "will retry after original 30-car table initialization");
        return true;
    }
    static QuestCockpitV2NativeFrameProbe instance;
};
QuestCockpitV2NativeFrameProbe QuestCockpitV2NativeFrameProbe::instance;

// Exact original world-sky source owner. r4dius/outrun2-decomp's x86 oracle
// proves 0x4521C0 is race_sky_display(work): one cdecl stack argument, Z off,
// both 0x90-byte sky layers, then Z on. Keep the semantic alive across the
// original function so fixed-function and programmable sky draws cannot be
// confused with pause/menu depth-off content or with the SkyGlow postprocess.
class VrOriginalRaceSkyOwner final : public Hook
{
    static constexpr int RaceSkyDisplayRva = 0x521C0;
    inline static SafetyHookInline RaceSkyDisplayHook{};

    static void __cdecl RaceSkyDisplayDest(void* work)
    {
        OutRunVR::GameSemantic::ScopedExactProducerSemantic sky(
            OutRunVR::GameSemantic::RenderScope::WorldSky);
        RaceSkyDisplayHook.ccall<void>(work);
    }

public:
    std::string_view description() override
    {
        return "VrOriginalRaceSkyOwner4521C0";
    }

    bool validate() override
    {
        return Settings::VREnabled && Settings::VRStereo;
    }

    bool apply() override
    {
        // Canonical emoose v0.1 replacement EXE SHA256:
        // 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3
        // Exact RVA 0x521C0 bytes were re-read from that binary. Fail closed
        // on any other executable or a previously detoured entrypoint.
        constexpr std::array<std::uint8_t,24> signature{{
            0x83,0xEC,0x08,0x53,0x55,0x56,0x57,0xE8,
            0x54,0xF0,0xFB,0xFF,0x50,0xE8,0xBE,0x7D,
            0xFB,0xFF,0xA1,0x60,0xBD,0x89,0x00,0x8B
        }};
        auto* entry=Module::exe_ptr<std::uint8_t>(RaceSkyDisplayRva);
        MEMORY_BASIC_INFORMATION info{};
        if(!entry ||
           VirtualQuery(entry,&info,sizeof(info))!=sizeof(info) ||
           info.State!=MEM_COMMIT || (info.Protect&PAGE_GUARD) ||
           (info.Protect&PAGE_NOACCESS) ||
           reinterpret_cast<std::uintptr_t>(entry)+signature.size() >
             reinterpret_cast<std::uintptr_t>(info.BaseAddress)+info.RegionSize ||
           !std::equal(signature.begin(),signature.end(),entry)) {
            spdlog::warn("VR WORLD SKY: canonical original 4521C0 signature mismatch; exact sky owner disabled");
            return false;
        }
        RaceSkyDisplayHook=safetyhook::create_inline(entry,RaceSkyDisplayDest);
        if(!RaceSkyDisplayHook) {
            spdlog::warn("VR WORLD SKY: failed to hook original 4521C0");
            return false;
        }
        spdlog::info("VR WORLD SKY: exact original 4521C0 owner installed; two sky layers use rotation-only stereo");
        return true;
    }

    static VrOriginalRaceSkyOwner instance;
};
VrOriginalRaceSkyOwner VrOriginalRaceSkyOwner::instance;

// QuestCockpitV2 mode1 camera: keep original game eye/swing/blend, but
// opt-in experimental native Quest 30-profile table delta in camera basis.
// Do not confuse the 30x36 PC camera anchors with the 30x296 VR profiles.
// The rejected full-car B0 camera and stale-pose cache remain retired.
static bool QuestCockpitV2Active(const EvWorkCamera* camera) noexcept {
    return OutRunVR::QuestCockpitV2::TrialEligible(
        Settings::VRQuestCockpitV2Enabled,Settings::VREnabled,
        IsPlayableCarGameplay(),
        camera ? static_cast<std::uint8_t>(camera->cam_mode_34A) : 0xff,
        OutRunVR::QuestCockpitV2::InSceneEffect(), Game::pl_car()!=nullptr)
        && OutRunVR::QuestCockpitV2::NativeOriginalHooksReady.load(
            std::memory_order_acquire);
}
static bool QuestCockpitV2CameraPose(const EvWorkCamera* camera,
    OutRunVR::QuestCockpitV2::SeatPose& result) noexcept {
    if(!QuestCockpitV2Active(camera)||!camera)return false;
    // Quest profile XYZ is now substituted into the live mode-1 input table
    // before original CAMERA control consumes it, so eye_swing/view_blend/
    // ground clamp run normally. The previous post-CalcCameraMatrix delta caused the HMD
    // view to sink toward the floor and amplified camera-direction jitter.
    if(Settings::VRQuestCockpitV2RawB0Camera){
        static bool warned=false;
        if(!warned){
            warned=true;
            spdlog::warn("VR COCKPIT: RawB0Camera is retired; "
                "native profile uses original mode1 camera producer");
        }
    }
    if(Settings::VRQuestCockpitV2NativeSeatProfile)
        return false;

    // Explicit A/B disable keeps the original mode1 anchor. Optional legacy
    // manual tuning remains available only when native-profile injection is
    // disabled, so two camera displacement owners can never stack.
    const float back=Settings::VRQuestCockpitV2SeatBack.get();
    const float down=Settings::VRQuestCockpitV2SeatDown.get();
    const float right=Settings::VRQuestCockpitV2SeatRight.get();
    if(back==0.f&&down==0.f&&right==0.f)return false;
    const OutRunVR::QuestCockpitV2::Vec3 nativeEye{
        camera->cam_pos_F8.x,camera->cam_pos_F8.y,camera->cam_pos_F8.z};
    const OutRunVR::QuestCockpitV2::Vec3 nativeLook{
        camera->look_pos_104.x,camera->look_pos_104.y,camera->look_pos_104.z};
    return OutRunVR::QuestCockpitV2::NativeSeatOffset(
        nativeEye,nativeLook,back,down,right,result);
}
class QuestCockpitV2PlayerCandidateProbe final : public Hook {
    static constexpr int PlayerCarRva=0x69764, RobotRva=0x114E60;
    static constexpr int OriginalDriverDisplayRva=0x879B0;
    inline static SafetyHookMid PlayerHook{};
    inline static SafetyHookInline RobotHook{};
    inline static std::uint64_t TraceCount=0;
    inline static thread_local OutRunVR::QuestCockpitV2::FrameOwner OccupantOwner{};

    static OutRunVR::QuestCockpitV2::OriginalOccupantSlot
    ExactOriginalCockpitOccupant(EvWorkRobot* robot) noexcept {
        using namespace OutRunVR::QuestCockpitV2;
        if(!robot)return OriginalOccupantSlot::None;
        // Original Quest TLS admits BOTH native event slot 362 and 363.
        // Original PC: ROB01 is driver; conditionally active ROB02
        // is passenger. Both use race_robot_driver_display_4879B0.
        // Never assume a missing ROB02 is open or reuse a stale token.
        sEventWork* driver=Game::event(EVENT_ROB01);
        sEventWork* passenger=Game::event(EVENT_ROB02);
        const auto expected=reinterpret_cast<decltype(driver->EventFunc.Disp)>(
            Module::exe_ptr(OriginalDriverDisplayRva));
        const bool d=driver && driver->EventFunc.Disp==expected;
        const bool p=passenger && passenger->EventFunc.Disp==expected;
        return ResolveOriginalCockpitWork(
            reinterpret_cast<std::uintptr_t>(robot),
            d?reinterpret_cast<std::uintptr_t>(
                driver->data<EvWorkRobot>()):0u,d,
            p?reinterpret_cast<std::uintptr_t>(
                passenger->data<EvWorkRobot>()):0u,p);
    }
    // Actual PC: 0x514E60 is the rob_disp_disp trampoline to Draw::disp
    // at 0x514C30. 0x514C10 is a DIFFERENT function. Old V2 targeted
    // 0x514C10 and thus never owned original player model display.
    static bool OriginalRobotDrawSignature() noexcept {
        constexpr std::array<std::uint8_t,25> kOriginal{
            0x8B,0x44,0x24,0x04,0x50,0x8B,0x00,0x8D,0x0C,0x40,
            0xC1,0xE1,0x05,0x81,0xC1,0xD8,0x77,0x85,0x00,
            0xE8,0xB8,0xFD,0xFF,0xFF,0xC3
        };
        const auto* ptr=Module::exe_ptr<std::uint8_t>(RobotRva);
        MEMORY_BASIC_INFORMATION mbi{};
        if(!ptr || VirtualQuery(ptr,&mbi,sizeof(mbi))!=sizeof(mbi) ||
           mbi.State!=MEM_COMMIT || (mbi.Protect&(PAGE_GUARD|PAGE_NOACCESS)))
            return false;
        const auto lo=reinterpret_cast<std::uintptr_t>(ptr);
        const auto hi=reinterpret_cast<std::uintptr_t>(mbi.BaseAddress)+mbi.RegionSize;
        if(lo>hi || hi-lo<kOriginal.size())return false;
        return std::equal(kOriginal.begin(),kOriginal.end(),ptr);
    }
    static void __cdecl RobotDisplay(EvWorkRobot* robot) {
        using namespace OutRunVR::QuestCockpitV2;
        // Nested original draws already see the outer scoped corrected W.
        // Let the original draw run, but never correct/stage it a second time.
        if(OriginalRobotCorrectionActive()) {
            RobotHook.ccall<void>(robot);
            return;
        }
        // Original ROB display runs outside races too. Access to event work,
        // camera, or OpenXR latched frame before game/device initialization
        // is not safe; let original guest render without probing these.
        if (!robot || !Settings::VREnabled ||
            !Settings::VRQuestCockpitV2Enabled ||
            !NativeOriginalHooksReady.load(std::memory_order_acquire) ||
            !NativeFrameTrace().Active() || InSceneEffect() ||
            !IsPlayableCarGameplay()) {
            RobotHook.ccall<void>(robot);
            return;
        }
        const EvWorkCamera* camera=Game::camera();
        if(!camera || camera->cam_mode_34A!=1 || !Game::pl_car()) {
            RobotHook.ccall<void>(robot);
            return;
        }
        const auto* stereo=OutRunVRRenderer::GetLatchedStereoFrameView();
        const auto frameEpoch=NativeFrameTrace().ActiveEpoch();
        const auto slot=ExactOriginalCockpitOccupant(robot);
        const bool racing=Game::current_mode &&
            (*Game::current_mode==STATE_GAME ||
             (*Game::current_mode==STATE_START &&
              Game::game_start_progress_code &&
              *Game::game_start_progress_code==65));
        const auto action=SelectCockpitOccupantRender(
            slot,QuestCockpitV2Active(camera),racing,
            Settings::VRQuestCockpitV2HideDriver,
            Settings::VRQuestCockpitV2PassengerVisible);
        if(action==CockpitOccupantRender::SuppressDriver)return;
        // Quest event 363 is a full occupant: it needs the SAME scoped W*C
        // correction as event 362, not an early exit to an uncorrected
        // passenger matrix. Keep the passenger visible/LOD0 scope alive
        // through both the corrected path and every fail-closed original
        // fallback; never force this scope on NPCs, driver, or GOAL.
        const bool passengerLod0=
            action==CockpitOccupantRender::OriginalPassengerForceVisible;
        ScopedOriginalOccupantLod0 passengerVisible(passengerLod0);
        if(!Settings::VRQuestCockpitV2OccupantCorrection) {
            RobotHook.ccall<void>(robot);
            return;
        }
        const bool exact=slot!=OriginalOccupantSlot::None;
        const bool enabled=Settings::VRQuestCockpitV2OccupantCorrection;
        static thread_local unsigned ownerSamples=0;
        if(enabled && Settings::VRTelemetry && ++ownerSamples<=48u)
            spdlog::info("VR COCKPIT V2 OCCUPANT OWNER: sample={} "
                "eventSlot={} exactOwner={} nativeEpoch={} stereo={} "
                "cam1={} source=PC_514E60",
                ownerSamples,static_cast<unsigned>(slot),exact,frameEpoch,
                stereo&&stereo->valid?stereo->poseSequence:0,
                camera&&camera->cam_mode_34A==1);
        const bool eligible=VerifiedPlayerOccupantScope(
            enabled,
            NativeOriginalHooksReady.load(std::memory_order_acquire),
            frameEpoch!=0,exact,exact,
            camera && camera->cam_mode_34A==1,
            QuestCockpitV2Active(camera),stereo&&stereo->valid &&
                stereo->poseSequence!=0,InSceneEffect());
        if(eligible) {
            const EVWORK_CAR* car=Game::pl_car();
            if(car) {
                FrameInput sample{};
                sample.nativeGameFrame=frameEpoch;
                sample.xrPoseSequence=stereo->poseSequence;
                // OpenXR reference-space generation is not yet published here:
                // still experimental and cannot be called exact Quest parity.
                sample.xrSpaceGeneration=0;
                sample.playerIdentity=reinterpret_cast<std::uintptr_t>(car);
                sample.cameraMode=1;
                sample.optionRequested=true;
                sample.gameplay=true;
                sample.worldPass=true;
                sample.originalPlayerEventVerified=true;
                sample.stereoAndPositionValid=true;
                std::memcpy(sample.matrixB0.data(),&car->matrix_B0,sizeof(Matrix));
                std::memcpy(sample.matrixF0.data(),&car->matrix_F0,sizeof(Matrix));
                // During the original player callback, F0 is intentionally
                // identity. Original Quest occupant rendering must consume
                // the PRE-identity matrix snapshot/C, not recompute from I.
                // Reject cross-player/frame/eye aliases to fail closed.
                const auto* preF0=MatchOriginalPreF0(
                    sample.playerIdentity,frameEpoch,stereo->poseSequence);
                if(preF0) {
                    if(std::memcmp(sample.matrixB0.data(),
                                   preF0->matrixB0.data(),sizeof(Matrix))!=0) {
                        RobotHook.ccall<void>(robot);
                        return;
                    }
                    sample.matrixF0=preF0->matrixF0;
                } else if(ActivePreF0Snapshot) {
                    // An active snapshot with a different owner, frame or
                    // pose must never fall through to identity-derived C.
                    RobotHook.ccall<void>(robot);
                    return;
                }
                if(OccupantOwner.Observe(sample)) {
                    const FrameSnapshot* own=OccupantOwner.Snapshot();
                    Matrix work{},corrected{};
                    static_assert(sizeof(robot->d3dmatrix10)==sizeof(Matrix));
                    std::memcpy(work.data(),&robot->d3dmatrix10,sizeof(Matrix));
                    if(own&&ComposeOccupantModel(work,own->occupantCorrection,corrected)) {
                        // Keep the recursion gate until AFTER scoped work
                        // restoration (reverse destructor order).
                        ScopedOriginalRobotCorrectionOwner correctionOwner(true);
                        if(!correctionOwner.Active()) {
                            RobotHook.ccall<void>(robot);
                            return;
                        }
                        ScopedOriginalRobotWorkMatrix scoped(
                            reinterpret_cast<float*>(&robot->d3dmatrix10),
                            corrected,true);
                        static thread_local unsigned appliedSamples=0;
                        if(Settings::VRTelemetry && ++appliedSamples<=32u)
                            spdlog::info("VR COCKPIT V2 WXC APPLIED: eventSlot={} "
                                "nativeEpoch={} poseSeq={} count={} player={} "
                                "correctedHash={:016X}",
                                static_cast<unsigned>(slot),
                                frameEpoch,stereo->poseSequence,appliedSamples,
                                sample.playerIdentity,
                                MatrixFingerprint(work,corrected));
                        // Parent renderer submits rigid and skinned bones from
                        // the original robot work only in this synchronous call.
                        // Original guest work matrix restored on all C++ exits.
                        // Quest occupant PMT LOD0 is scoped to this verified
                        // original ROB01/ROB02 native draw only; normal V2 OFF.
                        ScopedOriginalOccupantLod0 lod0(
                            Settings::VRQuestCockpitV2OccupantLod0);
                        RobotHook.ccall<void>(robot);
                        return;
                    }
                }
            }
        }
        // No player owner, uncertain eye, menu/goal/effect, unknown executable
        // or invalid B0/F0: exact original rendering unchanged.
        RobotHook.ccall<void>(robot);
    }
    static void PlayerState(SafetyHookContext& ctx) {
        if(!Settings::VREnabled ||
           (!Settings::VRCockpitFrameProbe && !Settings::VRQuestCockpitV2Enabled))
            return;
        const EVWORK_CAR* car=Game::pl_car();
        if(!car || reinterpret_cast<EVWORK_CAR*>(ctx.ebx)!=car)return;
        const EvWorkCamera* cam=Game::camera();
        const auto mode=cam?
            static_cast<std::uint8_t>(cam->cam_mode_34A):0xff;
        if(Settings::VRCockpitFrameProbe){
            OutRunVR::QuestCockpitV2::ThreadProbe().OnPlayerCar(mode);
            OutRunVR::QuestCockpitV2::NativeFrameTrace().OnPlayerCar();
        }
        if(QuestCockpitV2Active(cam) && Settings::VRQuestCockpitV2FullCar)
            ctx.eax=(ctx.eax & ~0x0000C000u)|0x00004000u;
        if(Settings::VRCockpitFrameProbe && Settings::VRTelemetry &&
           ++TraceCount<=32u){
            using namespace OutRunVR::QuestCockpitV2;
            Matrix b0{},f0{},correction{};
            std::memcpy(b0.data(),&car->matrix_B0,sizeof(b0));
            std::memcpy(f0.data(),&car->matrix_F0,sizeof(f0));
            const bool good=ComputeBodyCorrection(b0,f0,correction);
            spdlog::info("VR COCKPIT V2 SAMPLE: count={} mode={} "
                "matrixValid={} hash={:016X} frame={} requested={} "
                "stereoFrameMapping=EXPERIMENTAL",
                TraceCount,mode,good,MatrixFingerprint(b0,f0),
                NativeFrameTrace().ActiveEpoch(),
                Settings::VRQuestCockpitV2Enabled.get());
        }
    }
public:
    std::string_view description() override {return "QuestCockpitV2PlayerCandidateProbe";}
    bool validate() override {
        return Settings::VREnabled &&
            (Settings::VRCockpitFrameProbe || Settings::VRQuestCockpitV2Enabled);
    }
    void declare_settings() override {
        Settings::VRCockpitFrameProbe.needs_restart();
        Settings::VRQuestCockpitV2Enabled.needs_restart();
    }
    bool apply() override {
        auto car=safetyhook::create_mid(Module::exe_ptr(PlayerCarRva),PlayerState);
        if(!car)return false;
        if(!OriginalRobotDrawSignature()) {
            spdlog::warn("QuestCockpitV2: exact PC rob_disp_disp_514E60 signature mismatch; render hooks not installed");
            return false;
        }
        auto robot=safetyhook::create_inline(Module::exe_ptr(RobotRva),RobotDisplay);
        if(!robot)return false; // car RAII rollback
        PlayerHook=std::move(car);RobotHook=std::move(robot);
        return true;
    }
    static QuestCockpitV2PlayerCandidateProbe instance;
};
QuestCockpitV2PlayerCandidateProbe QuestCockpitV2PlayerCandidateProbe::instance;

class RestoreCarBaseShadow : public Hook
{
	static void __cdecl CalcPeraShadow(int a1, int a2, int a3, float a4)
	{
		// These call sites were nullsub_1 calls on PC, so skipping the draw
		// restores exactly what the game did without the shadow.
		if (Settings::CarBaseShadowOpacity <= 0.f ||
			!std::isfinite(a4))
			return;
        float shadowAlpha = 0.f;
        if (!OutRunVR::CarShadowStereo::ValidScaledAlpha(
                a4, Settings::CarBaseShadowOpacity.get(), shadowAlpha))
            return;

		// The selector also invokes this PC nullsub replacement, but
		// pl_car() there is not the selected model (or may be null).
		// Do not borrow a stale gameplay matrix or pass a null matrix.
		// Until the selector's transform owner is proven, omit its shadow.
		if (!IsPlayableCarGameplay())
			return;
		EVWORK_CAR* car = Game::pl_car();
		if (!car)
			return;
		Game::mxPushLoadMatrix(&car->matrix_B0);
		Game::mxTranslate(0.0f, 0.05f, 0.0f);

		// Each original-mod shadow CALL is world geometry, not a HUD sprite.
		// EffectiveScope prefers an old selected SpriteNode's exact ScreenHud
		// to CurrentScope. A nonqueued direct Draw therefore needs a bounded
		// exact owner; it must never overwrite the owner of a live queue draw.
		{
			const auto directWorldScope =
				Settings::VREnabled &&
				!OutRunVR::GameSemantic::QueueRenderActive()
				? OutRunVR::GameSemantic::RenderScope::WorldParticle
				: OutRunVR::GameSemantic::RenderScope::None;
			// The direct producer must not consume an unrelated pending
			// HUD one-shot token or inherit a stale queue-owned scope.
			// Keep the legacy RAII world scope immediately around the draw.
			// This also preserves the original live-queue/desktop fallback.
			OutRunVR::GameSemantic::ScopedExactProducerSemantic directWorld(
				directWorldScope, nullptr, true,
				OutRunVR::GameSemantic::ProducerToken::CarBaseShadow);
			OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
				OutRunVR::GameSemantic::RenderScope::WorldParticle);
			Game::DrawObjectAlpha_Internal(
				a1, shadowAlpha, 0, -1);
		}
		Game::mxPopMatrix();
	}

public:
	std::string_view description() override
	{
		return "RestoreCarBaseShadow";
	}

	bool apply() override
	{
		constexpr int DispCarModel_Common_HookAddr = 0x69EB4;
		constexpr int DispSelCarModel_HookAddr = 0x6AC76; // O2SP car selection
		constexpr int Sumo_DispSelCarModel_HookAddr = 0x6B766; // C2C car selection

		// These three funcs contain nullsub_1 calls which were CalcPeraShadow calls in O2SP / C2CXbox
		// We can't just hook nullsub_1 since a bunch of other nulled out code also calls it, instead we'll rewrite them to call our CalcPeraShadow func
		Memory::VP::InjectHook(Module::exe_ptr(DispCarModel_Common_HookAddr), CalcPeraShadow, Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(DispSelCarModel_HookAddr), CalcPeraShadow, Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(Sumo_DispSelCarModel_HookAddr), CalcPeraShadow, Memory::HookType::Call);

		return true;
	}

	static RestoreCarBaseShadow instance;
};
RestoreCarBaseShadow RestoreCarBaseShadow::instance;

// Canonical SceneEffect/lens producer proof:
//   sub_40CAE0 owns the effect loop,
//   EXE+0xCABE is the single DrawObjectAlpha_Internal producer call,
//   EXE+0xCF4E calls Calc3D2D for its projected anchor.
// Do not infer lens ownership from generic alpha state or tune disparity scalars.
class VRLensFlareProjected2D : public Hook
{
    // Original OR2006C2C.EXE SHA 68ceb386... disassembly:
    // sub_40CAE0 at 0xCF4E projects the light centre (Calc3D2D),
    // then 0xD3A0 loads object 0x570002 and 0xD3A5 calls sub_40C980,
    // which directly forwards to DrawObjectAlpha_Internal. The later
    // outer halo discs use distinct sub_40C9A0 calls at 0xD5F5..0xD796.
    // Prior 0xCABE hook only covered the OUTER sub_40C9A0 path.
    // Correct the central SUN object alone: preserve its world matrix
    // through true per-eye stereo, rather than classifying it as an
    // already-projected flat ScreenHud. Leave every other flare child and
    // original display opacity untouched.
    inline static SafetyHookMid LensCentreEnterHook{};
    inline static SafetyHookMid LensCentreLeaveHook{};
    inline static thread_local unsigned LensCentreDepth = 0;
    // This is the depth at which a non-queue, VR-enabled centre became the
    // owner. Count every D3A5 entry, even when skipped, so each D3AA exit
    // balances its own call without restoring an outer centre prematurely.
    inline static thread_local unsigned LensCentreOwnerDepth = 0;
    inline static thread_local OutRunVR::GameSemantic::RenderScope
        LensCentreSavedScope = OutRunVR::GameSemantic::RenderScope::None;
    inline static thread_local OutRunVR::GameSemantic::ProducerToken
        LensCentreSavedProducer = OutRunVR::GameSemantic::ProducerToken::None;
    inline static thread_local std::uint64_t LensCentreSavedEpoch = 0;
    // r4dius/outrun2-decomp race_course_passes.cpp proves 0x570008 is
    // emitted twice per visible sun-flare sequence: ordinal 1 is an outer
    // flare child and ordinal 2 is the near-centre glow. Preserve the outer
    // child and suppress only the duplicated centre glow in VR.
    inline static thread_local std::uint64_t LensFlareSequence = 0;
    inline static thread_local std::uint64_t LensOuter570008Sequence = 0;
    inline static thread_local unsigned LensOuter570008Ordinal = 0;
    // This serial counts *source wrapper admissions*, not physical GPU draws.
    // A 0x570002 anchor can be absent when original 40CBC0 spread <= 0;
    // never use the last-C993 sequence as a Present or sun-invocation ID.
    inline static thread_local std::uint64_t LensSourceCallSerial = 0;
    inline static std::atomic<std::uint64_t> LensOpaqueFlushSerial{0};
    inline static std::atomic<std::uint64_t> LensOpaquePmtEntrySerial{0};
    static std::uint64_t NextLensSourceCallSerial() noexcept
    {
        if (++LensSourceCallSerial == 0)
            ++LensSourceCallSerial;
        return LensSourceCallSerial;
    }
    static constexpr bool IsOuterLensSource(int id) noexcept
    {
        switch (id)
        {
        case 0x570003: case 0x570004: case 0x570005:
        case 0x570007: case 0x570008: case 0x570009:
        case 0x57000A: case 0x57000B: case 0x57000C:
        case 0x57000D: case 0x57000E:
            return true;
        default:
            return false;
        }
    }

    using LensOpaqueFlushFn = void(__cdecl*)();
    using LensOpaquePmtEntryFn = void(__cdecl*)(const std::uint32_t*);

    static void __cdecl TraceLensOpaquePmtEntry(
        const std::uint32_t* entry)
    {
        using namespace OutRunVR::GameSemantic;
        const auto projectedFlush =
            OutRunVR::ProjectedLens::CurrentInlineFlush;
        OutRunVR::ProjectedLens::InlinePmtReceipt projectedPmt{};
        if (entry && projectedFlush.valid &&
            entry[14] == projectedFlush.objectId &&
            entry[8] == 1u && entry[5] && entry[6] && entry[7])
        {
            projectedPmt = {
                projectedFlush.sourceSerial,
                projectedFlush.sequence,
                projectedFlush.objectId,
                entry[8], entry[5], entry[6], entry[7], true
            };
        }
        OutRunVR::ProjectedLens::ScopedInlinePmt projectedLensPmt(
            projectedPmt);

        const auto axisFlush = CurrentLensAxisOpaqueFlush;
        LensAxisOpaquePmtOwner axisPmt{};
        if (Settings::VREnabled && entry &&
            IsProjectedLensPmtObject(entry[14]) &&
            entry[5] != 0 && entry[6] != 0 && entry[7] != 0)
        {
            // D79B carries the first-570008 source interval. D44B and the
            // inline 405360 flushes are independently exact original call
            // sites, so zero sourceSerial is valid there; PMT identity itself
            // is the physical proof.
            axisPmt = {
                axisFlush.valid ? axisFlush.sourceSerial : 0,
                axisFlush.valid ? axisFlush.sequence : LensFlareSequence,
                reinterpret_cast<std::uintptr_t>(entry),
                entry[14], entry[5], entry[6], entry[7], entry[8], true
            };
        }
        ScopedLensAxisOpaquePmtOwner axisPmtScope(axisPmt);

        const auto flush = CurrentLensOpaqueFlush;
        if (!entry || flush.serial == 0 ||
            !Settings::VREnabled || !Settings::VRTelemetry)
        {
            Module::fn_ptr<LensOpaquePmtEntryFn>(0x4700)(entry);
            return;
        }

        LensOpaquePmtEntryReceipt receipt{};
        receipt.serial = LensOpaquePmtEntrySerial.fetch_add(
            1, std::memory_order_relaxed) + 1;
        if (receipt.serial == 0)
            receipt.serial = LensOpaquePmtEntrySerial.fetch_add(
                1, std::memory_order_relaxed) + 1;
        receipt.flushSerial = flush.serial;
        receipt.flushOrigin = flush.origin;
        receipt.entry = reinterpret_cast<std::uintptr_t>(entry);
        receipt.depthBits = entry[0];
        receipt.matrix = entry[1];
        receipt.paletteCount = entry[2];
        receipt.idHigh = entry[3];
        receipt.resource = entry[4];
        receipt.object = entry[5];
        receipt.node = entry[6];
        receipt.mesh = entry[7];
        receipt.pass = entry[8];
        receipt.colourList = entry[9];
        receipt.colour = entry[10];
        receipt.morphTarget = entry[11];
        receipt.morphWeightBits = entry[12];
        receipt.flags = entry[13];
        receipt.objectId = entry[14];

        ScopedLensOpaquePmtEntry pmtScope(receipt);
        LARGE_INTEGER preQpc{};
        QueryPerformanceCounter(&preQpc);
        spdlog::info(
            "VR TRACE LENS PMT ENTRY FULL: phase=PRE qpc={} thread={} "
            "pmtEntrySerial={} flushSerial={} flushOrigin={} entry=0x{:X} "
            "objectId=0x{:06X} idHigh=0x{:08X} resource=0x{:X} "
            "object=0x{:X} node=0x{:X} mesh=0x{:X} pass={} "
            "matrix={} paletteCount={} depthBits=0x{:08X} flags=0x{:08X} "
            "colourList=0x{:X} colour={} morphTarget=0x{:X} "
            "morphWeightBits=0x{:08X} sourceCallSerial={} sequence={} "
            "sourceObj=0x{:06X} sourceOrdinal={} "
            "authority=EXACT_RETAIL_405890_CALL_404700",
            preQpc.QuadPart, GetCurrentThreadId(), receipt.serial,
            receipt.flushSerial, Name(receipt.flushOrigin), receipt.entry,
            receipt.objectId, receipt.idHigh, receipt.resource,
            receipt.object, receipt.node, receipt.mesh, receipt.pass,
            receipt.matrix, receipt.paletteCount, receipt.depthBits,
            receipt.flags, receipt.colourList, receipt.colour,
            receipt.morphTarget, receipt.morphWeightBits,
            flush.sourceSerial, flush.sequence, flush.objectId,
            static_cast<unsigned>(flush.ordinal));

        Module::fn_ptr<LensOpaquePmtEntryFn>(0x4700)(entry);

        LARGE_INTEGER postQpc{};
        QueryPerformanceCounter(&postQpc);
        spdlog::info(
            "VR TRACE LENS PMT ENTRY FULL: phase=POST qpc={} thread={} "
            "pmtEntrySerial={} flushSerial={} flushOrigin={} entry=0x{:X} "
            "objectId=0x{:06X} pass={} "
            "authority=EXACT_RETAIL_405890_CALL_404700",
            postQpc.QuadPart, GetCurrentThreadId(), receipt.serial,
            receipt.flushSerial, Name(receipt.flushOrigin), receipt.entry,
            receipt.objectId, receipt.pass);
    }

    static std::uint64_t HashOpaquePatchLedger(
        std::uint32_t patchCount) noexcept
    {
        const auto count = std::min<std::uint32_t>(patchCount, 128u);
        const auto* pairs =
            Module::exe_ptr<const std::uint32_t>(0x4995A0);
        std::uint64_t hash = 1469598103934665603ull;
        for (std::uint32_t i = 0; i < count; ++i)
        {
            const std::uint32_t ptr = pairs[i * 2u + 0u];
            const std::uint32_t oldValue = pairs[i * 2u + 1u];
            hash ^= ptr;
            hash *= 1099511628211ull;
            hash ^= oldValue;
            hash *= 1099511628211ull;
        }
        return hash;
    }

    static void TraceLensOpaqueFlush(
        OutRunVR::GameSemantic::LensOpaqueFlushOrigin origin) noexcept
    {
        using namespace OutRunVR::GameSemantic;
        const auto inlineReceipt = CurrentLensOriginalCall;
        const auto deferred = CurrentLensDeferredPhysical;
        const bool exactInlineProjectedLens =
            Settings::VREnabled &&
            origin == LensOpaqueFlushOrigin::Inline405360 &&
            inlineReceipt.sourceSerial != 0 &&
            inlineReceipt.callsite == 1u &&
            OutRunVR::ProjectedLens::IsExactInlineC993Object(
                inlineReceipt.objectId) &&
            !QueueRenderActive() &&
            EffectiveScope() == RenderScope::ProjectedScreenEffect2D;
        OutRunVR::ProjectedLens::ScopedInlineFlush projectedLensFlush(
            { inlineReceipt.sourceSerial,
              inlineReceipt.lastC993Sequence,
              inlineReceipt.objectId,
              exactInlineProjectedLens });
        const bool exactSceneFlush =
            origin == LensOpaqueFlushOrigin::SceneD44B ||
            origin == LensOpaqueFlushOrigin::SceneD79B;
        // Runtime 23:57 + retail decomp prove these two original E8 sites
        // submit only the same screen-space sun family (D44B: 570010/57000F,
        // D79B: the eleven 40C9A0 axis sprites). Own the semantic BEFORE
        // 405890 reloads the entry matrix/c64, otherwise the generic renderer
        // head transform is injected before R30 can build the angular ray.
        ScopedRenderSemantic exactSceneProjectedScope(
            exactSceneFlush
                ? RenderScope::ProjectedScreenEffect2D
                : EffectiveScope());
        const bool exactAxisFlush =
            Settings::VREnabled &&
            deferred.sourceSerial != 0 &&
            deferred.sequence != 0 &&
            deferred.objectId == 0x570008u &&
            deferred.ordinal == 1u;
        ScopedLensAxisOpaqueFlushOwner axisFlushScope(
            { deferred.sourceSerial, deferred.sequence, exactAxisFlush });
        const bool trace = Settings::VREnabled && Settings::VRTelemetry &&
            (exactSceneFlush || inlineReceipt.sourceSerial != 0 ||
             deferred.sourceSerial != 0);

        const auto readU32 = [](std::uintptr_t rva) noexcept {
            return *Module::exe_ptr<const std::uint32_t>(rva);
        };
        const auto prePatchCount = readU32(0x464F14);
        const auto prePatchHash = HashOpaquePatchLedger(prePatchCount);
        const auto preQueue0 = readU32(0x464EF8);
        const auto preQueue1 = readU32(0x464EFC);
        const auto preQueue2 = readU32(0x464F00);
        const auto preFlushFlag = readU32(0x4999B0);

        LensOpaqueFlushReceipt receipt{};
        if (trace)
        {
            receipt.serial = LensOpaqueFlushSerial.fetch_add(
                1, std::memory_order_relaxed) + 1;
            if (receipt.serial == 0)
                receipt.serial = LensOpaqueFlushSerial.fetch_add(
                    1, std::memory_order_relaxed) + 1;
            receipt.origin = origin;
            receipt.sourceSerial = inlineReceipt.sourceSerial != 0
                ? inlineReceipt.sourceSerial : deferred.sourceSerial;
            receipt.sequence = inlineReceipt.sourceSerial != 0
                ? inlineReceipt.lastC993Sequence :
                (deferred.sourceSerial != 0
                    ? deferred.sequence : LensFlareSequence);
            receipt.objectId = inlineReceipt.sourceSerial != 0
                ? inlineReceipt.objectId : deferred.objectId;
            receipt.ordinal = inlineReceipt.sourceSerial != 0
                ? inlineReceipt.ordinal : deferred.ordinal;
            receipt.patchCount = prePatchCount;
            receipt.patchLedgerHash = prePatchHash;
        }

        ScopedLensOpaqueFlush flushScope(receipt);
        if (trace)
        {
            LARGE_INTEGER qpc{};
            QueryPerformanceCounter(&qpc);
            spdlog::info(
                "VR TRACE LENS OPAQUE FLUSH FULL: phase=PRE qpc={} thread={} "
                "flushSerial={} origin={} sequence={} sourceCallSerial={} "
                "sourceObj=0x{:06X} ordinal={} inlineLinked={} deferredCandidate={} "
                "patchCount={} patchHash=0x{:016X} queueCount={} queueCapacity={} "
                "matrixCount={} flushFlag={} scope={} producer={} "
                "queueLayout=EXE_PROVEN_405160_4052C0 opaquePmtIdentity=ENTRY_JOIN_PENDING",
                qpc.QuadPart, GetCurrentThreadId(), receipt.serial,
                Name(origin), receipt.sequence, receipt.sourceSerial,
                receipt.objectId, static_cast<unsigned>(receipt.ordinal),
                inlineReceipt.sourceSerial != 0 ? 1 : 0,
                deferred.sourceSerial != 0 ? 1 : 0,
                prePatchCount,
                static_cast<unsigned long long>(prePatchHash),
                preQueue0, preQueue1, preQueue2, preFlushFlag,
                Name(EffectiveScope()), Name(CurrentRenderProducerToken()));
        }

        Module::fn_ptr<LensOpaqueFlushFn>(0x52C0)();

        if (trace)
        {
            LARGE_INTEGER qpc{};
            QueryPerformanceCounter(&qpc);
            const auto postPatchCount = readU32(0x464F14);
            const auto postPatchHash = HashOpaquePatchLedger(postPatchCount);
            spdlog::info(
                "VR TRACE LENS OPAQUE FLUSH FULL: phase=POST qpc={} thread={} "
                "flushSerial={} origin={} sequence={} sourceCallSerial={} "
                "sourceObj=0x{:06X} ordinal={} patchCountBefore={} patchCountAfter={} "
                "patchHashBefore=0x{:016X} patchHashAfter=0x{:016X} "
                "queueCountAfter={} queueCapacityAfter={} matrixCountAfter={} "
                "flushFlagAfter={} queueLayout=EXE_PROVEN_405160_4052C0 "
                "opaquePmtIdentity=ENTRY_JOIN_AVAILABLE",
                qpc.QuadPart, GetCurrentThreadId(), receipt.serial,
                Name(origin), receipt.sequence, receipt.sourceSerial,
                receipt.objectId, static_cast<unsigned>(receipt.ordinal),
                prePatchCount, postPatchCount,
                static_cast<unsigned long long>(prePatchHash),
                static_cast<unsigned long long>(postPatchHash),
                readU32(0x464EF8), readU32(0x464EFC), readU32(0x464F00),
                readU32(0x4999B0));
        }
    }

    static void __cdecl LensOpaqueFlushInline405360()
    {
        TraceLensOpaqueFlush(
            OutRunVR::GameSemantic::LensOpaqueFlushOrigin::Inline405360);
    }
    static void __cdecl LensOpaqueFlushSceneD44B()
    {
        TraceLensOpaqueFlush(
            OutRunVR::GameSemantic::LensOpaqueFlushOrigin::SceneD44B);
    }
    static void __cdecl LensOpaqueFlushSceneD79B()
    {
        TraceLensOpaqueFlush(
            OutRunVR::GameSemantic::LensOpaqueFlushOrigin::SceneD79B);
    }


    static void LensCentreEnter(safetyhook::Context&)
    {
        // A non-queued original producer must never overwrite a selected
        // SpriteNode's semantic during nested queue processing.
        ++LensCentreDepth;
        if (Settings::VRTelemetry)
            spdlog::info(
                "VR TRACE LENS CENTRE ENTER FULL: depth={} ownerDepth={} vr={} "
                "queueActive={} queueEpoch={} eligible={} preScope={} preProducer={} "
                "preLensEpoch={}",
                LensCentreDepth, LensCentreOwnerDepth,
                Settings::VREnabled ? 1 : 0,
                OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                OutRunVR::GameSemantic::CurrentQueueNodeEpoch(),
                Settings::VREnabled &&
                    !OutRunVR::GameSemantic::QueueRenderActive() &&
                    LensCentreDepth == 1 ? 1 : 0,
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::EffectiveScope()),
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::CurrentRenderProducerToken()),
                OutRunVR::GameSemantic::CurrentLensCentreCallEpoch);
        // Original 0xD3A5/0xD3AA are paired call edges, including nested
        // and disabled-VR paths. An ignored nested queue call must still
        // consume exactly one depth on its matching leave, not pop the
        // active outer sun's saved render scope.
        if (!Settings::VREnabled ||
            OutRunVR::GameSemantic::QueueRenderActive() ||
            LensCentreDepth != 1)
            return;
        LensCentreOwnerDepth = LensCentreDepth;
        LensCentreSavedScope = OutRunVR::GameSemantic::CurrentScope;
        LensCentreSavedProducer = OutRunVR::GameSemantic::CurrentDirectExactProducer;
        LensCentreSavedEpoch = OutRunVR::GameSemantic::CurrentLensCentreCallEpoch;
        auto& next = OutRunVR::GameSemantic::NextLensCentreCallEpoch;
        if (++next == 0)
            ++next;
        OutRunVR::GameSemantic::CurrentLensCentreCallEpoch = next;
        OutRunVR::GameSemantic::CurrentDirectExactProducer =
            OutRunVR::GameSemantic::ProducerToken::LensFlareCentre;
        OutRunVR::GameSemantic::CurrentScope =
            OutRunVR::GameSemantic::RenderScope::WorldBillboard;
        if (Settings::VRTelemetry)
            spdlog::info(
                "VR TRACE LENS CENTRE ACQUIRED FULL: depth={} ownerDepth={} "
                "scope={} producer={} lensEpoch={} savedScope={} savedProducer={} "
                "savedEpoch={}",
                LensCentreDepth, LensCentreOwnerDepth,
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::EffectiveScope()),
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::CurrentRenderProducerToken()),
                OutRunVR::GameSemantic::CurrentLensCentreCallEpoch,
                OutRunVR::GameSemantic::Name(LensCentreSavedScope),
                OutRunVR::GameSemantic::Name(LensCentreSavedProducer),
                LensCentreSavedEpoch);
    }

    static void LensCentreLeave(safetyhook::Context&)
    {
        // A captured render scope must be restored even if VR is disabled
        // during the original draw; gating exit on the current VR setting
        // would leak the central WorldBillboard semantic into later effects.
        if (!LensCentreDepth)
            return;
        const unsigned leaveDepthBefore = LensCentreDepth;
        const bool restoringOwner = LensCentreOwnerDepth == LensCentreDepth;
        const auto leaveScopeBefore =
            OutRunVR::GameSemantic::EffectiveScope();
        const auto leaveProducerBefore =
            OutRunVR::GameSemantic::CurrentRenderProducerToken();
        const auto leaveEpochBefore =
            OutRunVR::GameSemantic::CurrentLensCentreCallEpoch;
        // Only the precise enter which acquired ownership may restore it.
        // Preserve that restore even if VREnabled toggles during the call.
        if (LensCentreOwnerDepth == LensCentreDepth)
        {
            OutRunVR::GameSemantic::CurrentScope = LensCentreSavedScope;
            OutRunVR::GameSemantic::CurrentDirectExactProducer = LensCentreSavedProducer;
            OutRunVR::GameSemantic::CurrentLensCentreCallEpoch = LensCentreSavedEpoch;
            LensCentreSavedProducer = OutRunVR::GameSemantic::ProducerToken::None;
            LensCentreSavedEpoch = 0;
            LensCentreSavedScope =
                OutRunVR::GameSemantic::RenderScope::None;
            LensCentreOwnerDepth = 0;
        }
        --LensCentreDepth;
        if (Settings::VRTelemetry)
            spdlog::info(
                "VR TRACE LENS CENTRE LEAVE FULL: depthBefore={} depthAfter={} "
                "restored={} preScope={} preProducer={} preLensEpoch={} "
                "postScope={} postProducer={} postLensEpoch={} queueActive={} queueEpoch={}",
                leaveDepthBefore, LensCentreDepth, restoringOwner ? 1 : 0,
                OutRunVR::GameSemantic::Name(leaveScopeBefore),
                OutRunVR::GameSemantic::Name(leaveProducerBefore),
                leaveEpochBefore,
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::EffectiveScope()),
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::CurrentRenderProducerToken()),
                OutRunVR::GameSemantic::CurrentLensCentreCallEpoch,
                OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                OutRunVR::GameSemantic::CurrentQueueNodeEpoch());
    }

	static void __cdecl DrawObjectAlphaProjected(
		int objectId, float alpha, void* work, int flags)
	{
        const bool trackedSource = Settings::VREnabled && IsOuterLensSource(objectId);
        const std::uint64_t sourceCallSerial =
            trackedSource ? NextLensSourceCallSerial() : 0;
        const auto resetTrace = trackedSource
            ? OutRunVR::D3D9ResetTrace::Read()
            : OutRunVR::D3D9ResetTrace::Snapshot{};
        unsigned sourceOrdinal = 0;
        // User Quest3 confirmed the "missing" tiny end-of-flare point
        // is NOT explained by hiding this child. Restore BOTH original
        // 0x570008 draws. Preserve their exact scene/projection semantics
        // and log source ordinals for diagnosing eye-space duplication.
        if (Settings::VREnabled && objectId == 0x570008)
        {
            if (LensFlareSequence != 0)
            {
                if (LensOuter570008Sequence != LensFlareSequence)
                {
                    LensOuter570008Sequence = LensFlareSequence;
                    LensOuter570008Ordinal = 0;
                }
                sourceOrdinal = ++LensOuter570008Ordinal;
            }

            // The first original CABE is deferred into a multi-object opaque
            // queue. Close the diagnostic-only ordinal1 interval exactly when
            // the second original CABE enters. This window is NOT object or
            // render-policy authority for any native Draw inside the flush.
            if (sourceOrdinal >= 2)
            {
                const auto deferred =
                    OutRunVR::GameSemantic::CurrentLensDeferredPhysical;
                if (Settings::VRTelemetry && deferred.sourceSerial != 0)
                    spdlog::info(
                        "VR LENS 570008 DEFERRED WINDOW CLOSE: sequence={} "
                        "sourceCallSerial={} ordinal={} reason=SECOND_570008_ENTRY",
                        deferred.sequence, deferred.sourceSerial,
                        static_cast<unsigned>(deferred.ordinal));
                OutRunVR::GameSemantic::ClearLensDeferredPhysical();
            }

            if (Settings::VRTelemetry)
            {
                static std::atomic<std::uint64_t> originalDraws{0};
                const auto n = originalDraws.fetch_add(1, std::memory_order_relaxed) + 1;
                if (n <= 12 || (n & (n - 1)) == 0)
                    spdlog::info(
                        "VR LENS 570008 ORIGINAL BOTH DRAWN: id=0x{:X} ordinal={} sequence={} hits={} alpha={} flags=0x{:X} ambientScope={} spriteQueue={} physicalDraw=UNOBSERVED sourceCallSerial={} anchorKnown={} ordinalMaySpanSunCalls={}",
                        static_cast<unsigned>(objectId), sourceOrdinal,
                        LensFlareSequence, n, alpha,
                        static_cast<unsigned>(flags),
                        static_cast<int>(OutRunVR::GameSemantic::EffectiveScope()),
                        OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                        sourceCallSerial, LensFlareSequence != 0 ? 1 : 0,
                        sourceOrdinal > 2 ? 1 : 0);
            }
        }

        if (trackedSource && Settings::VRTelemetry)
        {
            LARGE_INTEGER sourceEventQpc{};
            QueryPerformanceCounter(&sourceEventQpc);
            const auto deferred =
                OutRunVR::GameSemantic::CurrentLensDeferredPhysical;
            spdlog::info(
                "VR TRACE LENS SOURCE FULL: site=CABE object=0x{:06X} alpha={:.9g} "
                "flags=0x{:08X} work=0x{:X} sourceCallSerial={} sequence={} ordinal={} "
                "scope={} producer={} queueActive={} queueEpoch={} lensCentreEpoch={} "
                "centreDepth={} centreOwnerDepth={} deferredSerial={} "
                "deferredSequence={} deferredObject=0x{:06X} deferredOrdinal={} "
                "resetEpoch={} resetQpc={} resetFlags=0x{:X} resetSnapshotStable={} "
                "sourceEventQpc={} thread={} resetQpcRole=RESET_ENTRY",
                static_cast<unsigned>(objectId), alpha,
                static_cast<unsigned>(flags),
                reinterpret_cast<std::uintptr_t>(work),
                sourceCallSerial, LensFlareSequence, sourceOrdinal,
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::EffectiveScope()),
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::CurrentRenderProducerToken()),
                OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                OutRunVR::GameSemantic::CurrentQueueNodeEpoch(),
                OutRunVR::GameSemantic::CurrentLensCentreCallEpoch,
                LensCentreDepth, LensCentreOwnerDepth,
                deferred.sourceSerial, deferred.sequence,
                deferred.objectId, static_cast<unsigned>(deferred.ordinal),
                resetTrace.resetSerial, resetTrace.qpc, resetTrace.flags,
                resetTrace.readStable ? 1 : 0,
                sourceEventQpc.QuadPart, GetCurrentThreadId());
        }

        // One original 0xCABE call occurs for each source effect object,
        // rather than each of the 4-5 visible flare discs being one surface.
        // Capture bounded per-object evidence to identify the centre-only
        // ghost WITHOUT reclassifying the normal surrounding lens circles.
        // Object/flag logging must not affect alpha, original call count,
        // return value, game matrices or shader state.
        if (Settings::VRTelemetry)
        {
            static std::atomic<std::uint64_t> flareCalls{ 0 };
            const auto hit =
                flareCalls.fetch_add(1, std::memory_order_relaxed) + 1;
            if (hit <= 24 || (hit & (hit - 1)) == 0)
                spdlog::info(
                    "VR P0 FLARE OBJECT: id={} alpha={} flags=0x{:X} calls={} gameState={}",
                    objectId, alpha, static_cast<unsigned>(flags), hit,
                    Game::current_mode ? static_cast<int>(*Game::current_mode) : -1);
        }
		OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
			OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D);
        OutRunVR::GameSemantic::ScopedLensOriginalCall inlineSource(
            {sourceCallSerial, LensFlareSequence,
             static_cast<std::uint32_t>(objectId), 2,
             static_cast<std::uint8_t>(sourceOrdinal)});
		Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);

        // Record only the source-order interval after ordinal1 returns and
        // before ordinal2 enters. Canonical EXE has both an optional inline
        // 405360->4052C0 flush and later scene 4052C0 flushes, so this window
        // remains diagnostic-only and cannot change EffectiveScope or claim
        // one physical 570008/PMT identity.
        if (Settings::VREnabled && objectId == 0x570008 &&
            sourceOrdinal == 1 && sourceCallSerial != 0)
        {
            OutRunVR::GameSemantic::ArmLensDeferredPhysical(
                {sourceCallSerial, LensFlareSequence,
                 static_cast<std::uint32_t>(objectId), 1});
            if (Settings::VRTelemetry)
                spdlog::info(
                    "VR LENS 570008 DEFERRED WINDOW ARM: sequence={} "
                    "sourceCallSerial={} ordinal=1 scope={} "
                    "provenance=SOURCE_ORDER_WINDOW_CANDIDATE",
                    LensFlareSequence, sourceCallSerial,
                    OutRunVR::GameSemantic::Name(
                        OutRunVR::GameSemantic::EffectiveScope()));
        }
	}

    // Original sun pass decomp (r4dius/outrun2-decomp,
    // race_course_passes.cpp::sun_flare_40cbc0) shows that sub_40C980/C993
    // is NOT exclusive to 0x570002. The screen-space sun stack also draws
    // 0x570010, 0x57000F and 0x570006 through the same wrapper while the
    // camera +0x1C0 screen matrix is active. Treating only 0x570002 as a
    // WorldBillboard splits one visual sun into different binocular spaces.
    // Keep this exact C993 callsite narrow by object id; other C993 callers
    // retain the original path.
    static constexpr bool IsProjectedSunScreenObject(int objectId) noexcept
    {
        switch (objectId)
        {
        case 0x570002: // visible sun disc
        case 0x570006: // central glow
        case 0x57000F: // far sun object
        case 0x570010: // visible/occlusion companion
            return true;
        default:
            return false;
        }
    }
    static void __cdecl DrawObjectAlphaCentre(
        int objectId, float alpha, void* work, int flags)
    {
        // Begin one exact sun-flare sequence before any optional C993
        // suppression. The following C9A0 path emits 0x570008 twice.
        if (Settings::VREnabled &&
            static_cast<unsigned>(objectId) == 0x570002u)
        {
            // Fail closed against a stale deferred receipt if the previous
            // source sequence exited abnormally before ordinal2.
            OutRunVR::GameSemantic::ClearLensDeferredPhysical();
            if (++LensFlareSequence == 0)
                ++LensFlareSequence;
            LensOuter570008Sequence = LensFlareSequence;
            LensOuter570008Ordinal = 0;
        }

        // No VR flare/sun child may be hidden as an optical workaround.
        // Even a stale LensFlareCentreEnabled=false INI must preserve the
        // exact original 0x570002 central sun object.

        const bool projectedSun =
            Settings::VREnabled &&
            !OutRunVR::GameSemantic::QueueRenderActive() &&
            IsProjectedSunScreenObject(objectId);
        // This source-only serial does not grant physical render ownership.
        // Keep the protected projected admission as the first exact-ID check
        // so its destructive negative-control test targets the real route.
        const bool trackedSource = Settings::VREnabled &&
            IsProjectedSunScreenObject(objectId);
        const std::uint64_t sourceCallSerial =
            trackedSource ? NextLensSourceCallSerial() : 0;
        const auto resetTrace = trackedSource
            ? OutRunVR::D3D9ResetTrace::Read()
            : OutRunVR::D3D9ResetTrace::Snapshot{};
        if (trackedSource && Settings::VRTelemetry)
        {
            LARGE_INTEGER sourceEventQpc{};
            QueryPerformanceCounter(&sourceEventQpc);
            const auto deferred =
                OutRunVR::GameSemantic::CurrentLensDeferredPhysical;
            spdlog::info(
                "VR TRACE LENS SOURCE FULL: site=C993 object=0x{:06X} alpha={:.9g} "
                "flags=0x{:08X} work=0x{:X} sourceCallSerial={} sequence={} projected={} "
                "scope={} producer={} queueActive={} queueEpoch={} lensCentreEpoch={} "
                "centreDepth={} centreOwnerDepth={} deferredSerial={} "
                "deferredSequence={} deferredObject=0x{:06X} deferredOrdinal={} "
                "resetEpoch={} resetQpc={} resetFlags=0x{:X} resetSnapshotStable={} "
                "sourceEventQpc={} thread={} resetQpcRole=RESET_ENTRY",
                static_cast<unsigned>(objectId), alpha,
                static_cast<unsigned>(flags),
                reinterpret_cast<std::uintptr_t>(work),
                sourceCallSerial, LensFlareSequence, projectedSun ? 1 : 0,
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::EffectiveScope()),
                OutRunVR::GameSemantic::Name(
                    OutRunVR::GameSemantic::CurrentRenderProducerToken()),
                OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                OutRunVR::GameSemantic::CurrentQueueNodeEpoch(),
                OutRunVR::GameSemantic::CurrentLensCentreCallEpoch,
                LensCentreDepth, LensCentreOwnerDepth,
                deferred.sourceSerial, deferred.sequence,
                deferred.objectId, static_cast<unsigned>(deferred.ordinal),
                resetTrace.resetSerial, resetTrace.qpc, resetTrace.flags,
                resetTrace.readStable ? 1 : 0,
                sourceEventQpc.QuadPart, GetCurrentThreadId());
        }
        // 4056D0 prepares the original opaque object and calls 405360.
        // Canonical EXE disassembly proves 405360 can either leave the opaque
        // work pending or, when the game's flush state is armed, call 4052C0
        // before 4056D0 returns. Therefore this wrapper call counter proves
        // source chronology only: it is NOT a native Draw/eye RT receipt and
        // does not distinguish inline versus later opaque submission. The mod
        // SpriteNode/D3DX queue flag is a separate mechanism and remains a
        // control only.
        if (Settings::VREnabled && Settings::VRTelemetry &&
            IsProjectedSunScreenObject(objectId))
        {
            static std::atomic<std::uint64_t> sourceAdmissions{0};
            const auto n = sourceAdmissions.fetch_add(
                1, std::memory_order_relaxed) + 1;
            if (n <= 16 || (n & (n - 1)) == 0)
                spdlog::info(
                    "VR LENS C993 SOURCE ADMISSION: id=0x{:06X} hits={} "
                    "sequence={} projected={} spriteQueue={} sourceCallSerial={} "
                    "ambientScope={} physicalDraw=UNOBSERVED opaqueFlush=UNOBSERVED",
                    static_cast<unsigned>(objectId), n,
                    LensFlareSequence, projectedSun ? 1 : 0,
                    OutRunVR::GameSemantic::QueueRenderActive() ? 1 : 0,
                    sourceCallSerial,
                    static_cast<int>(OutRunVR::GameSemantic::EffectiveScope()));
        }
        if (!projectedSun)
        {
            OutRunVR::GameSemantic::ScopedLensOriginalCall inlineSource(
                {sourceCallSerial, LensFlareSequence,
                 static_cast<std::uint32_t>(objectId), 1});
            Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);
            return;
        }

        if (Settings::VRTelemetry)
        {
            static std::atomic<std::uint64_t> draws{ 0 };
            const auto n = draws.fetch_add(1, std::memory_order_relaxed) + 1;
            if (n <= 24 || (n & (n - 1)) == 0)
                spdlog::info(
                    "VR SUN C993 SCREEN FAMILY: id=0x{:06X} hits={} "
                    "parent={} owner={} queue=0 mode=PROJECTED_SCREEN_EFFECT_2D",
                    static_cast<unsigned>(objectId), n,
                    LensCentreDepth, LensCentreOwnerDepth);
        }

        // C993's four central objects are already projected by the game to
        // one centre-eye screen ray. R84 verifier keeps the legacy spatial
        // route as a fail-closed reference but validates this active mono path.
        // AUTO 01493/01473 follow-through keeps
        // broad GOAL/lifecycle changes out of this optical fix. Keep the exact
        // ProjectedScreenEffect2D
        // scope but clear D3A5's spatial LensFlareCentre token for the actual
        // C993 draw. R30 then uses the existing identical-L/R centre-eye WVP
        // fusion instead of independently reprojecting the same ray through
        // asymmetric eye frusta. CABE outer discs remain on their own path.
        OutRunVR::GameSemantic::ScopedExactProducerSemantic semantic(
            OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D,
            nullptr, true,
            OutRunVR::GameSemantic::ProducerToken::None);
        OutRunVR::GameSemantic::ScopedRenderSemantic sunDrawScope(
            OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D);
        OutRunVR::GameSemantic::ScopedLensOriginalCall inlineSource(
            {sourceCallSerial, LensFlareSequence,
             static_cast<std::uint32_t>(objectId), 1});
        Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);
    }

public:
	std::string_view description() override
	{
		return "VRLensFlareProjected2D";
	}

	bool apply() override
	{
		Memory::VP::InjectHook(
			Module::exe_ptr(0xCABE), DrawObjectAlphaProjected,
			Memory::HookType::Call);
        // Diagnostic-only original opaque queue boundaries. Each site is a
        // verified E8 -> 4052C0 and the wrapper calls 4052C0 exactly once.
        Memory::VP::InjectHook(
            Module::exe_ptr(0x542A), LensOpaqueFlushInline405360,
            Memory::HookType::Call);
        Memory::VP::InjectHook(
            Module::exe_ptr(0xD44B), LensOpaqueFlushSceneD44B,
            Memory::HookType::Call);
        Memory::VP::InjectHook(
            Module::exe_ptr(0xD79B), LensOpaqueFlushSceneD79B,
            Memory::HookType::Call);
        // Exact retail 405890 call edges into 404700: pass 0 and pass 1.
        // The wrapper calls the original exactly once and is inert outside a
        // verified lens-related opaque flush transaction.
        Memory::VP::InjectHook(
            Module::exe_ptr(0x5A41), TraceLensOpaquePmtEntry,
            Memory::HookType::Call);
        Memory::VP::InjectHook(
            Module::exe_ptr(0x5C44), TraceLensOpaquePmtEntry,
            Memory::HookType::Call);
        // Separate verified E8 into the same DrawObjectAlpha_Internal ABI,
        // invoked only by the primary sun's sub_40C980 producer.
        Memory::VP::InjectHook(
            Module::exe_ptr(0xC993), DrawObjectAlphaCentre,
            Memory::HookType::Call);
        // Exact E8 source for central 0x570002 object, not the shared
        // sub_40C980 target. If either enter/leave cannot relocate, retain
        // the unchanged original lens behavior rather than leaking a world
        // semantic beyond this sole object.
        LensCentreEnterHook = safetyhook::create_mid(
            Module::exe_ptr(0xD3A5), LensCentreEnter);
        LensCentreLeaveHook = safetyhook::create_mid(
            Module::exe_ptr(0xD3AA), LensCentreLeave);
        if (!LensCentreEnterHook || !LensCentreLeaveHook)
        {
            LensCentreEnterHook = {};
            LensCentreLeaveHook = {};
            spdlog::warn(
                "VR P0 LENS CENTRE: 0xD3A5/0xD3AA partial hook rolled back; keeping original scene effect");
        }
        else
            spdlog::info(
                "VR P0 LENS CENTRE: 0xD3A5 owner plus exact 0xC993 projected draw scope (outer 0xCABE discs untouched)");
		spdlog::info(
			"VR P0 FLARE: exact EXE+0xCABE producer -> PROJECTED_SCREEN_EFFECT_2D; placement remains WVP-proven");
		return true;
	}

	static VRLensFlareProjected2D instance;
};
VRLensFlareProjected2D VRLensFlareProjected2D::instance;

// Restores the console's lighting dynamic range, which the PC port didn't make
// use of, costing roughly a third of the sun on surfaces facing it.
//
// In the stage data the light diffuse is often authored between 1.00 - 1.64 on
// the original OR2 stages.
// The vertex shader ends on "mad oD0, r0, r2, r1", and oD0 is a colour output,
// which hardware clamps to 0.0 - 1.0. So saturate(N dot L) * material * 1.64 clips 
// at 1.0 and the pixel stage then modulates the texture by 1.0 instead of 1.64.
//
// The console keeps the same value under the clamp by working in a dynamic range
// of 2: the light diffuse is halved into the constant, the ambient half of the
// equation is scaled by CV_R_DRANGE (c16) to match, and the first texture stage
// then doubles the result back with D3DTOP_MODULATE2X. The arcade shader source
// names the constant "reciprocal of dynamic range" and comments the clamp.
//
class RestoreXboxBrightness : public Hook
{
	// (1) Doubling is chosen per shader by a flag holding the bound shader's id.
	// Only id 1, a shader combined from the VsUnit tables, has its lighting halved
	// and so wants doubling back. vsSelectVertexShader binds the shader and returns
	// without ever writing the flag; the one path that does write it is for an entry
	// carrying no shader, which writes zero, so the flag never holds 1.
	//
	// The hook adds the missing write where the shader is bound. esi holds the
	// shader entry there, and its third word is the id.
	static constexpr int SelectVertexShader_IdBranch_Addr = 0x106E9;
	static constexpr int Modulate2xFlag_Addr = 0x49EDD0;
	static constexpr int ShaderEntry_Id = 2;

	inline static SafetyHookMid SelectVertexShader_hook = {};
	static void SelectVertexShader_dest(safetyhook::Context& ctx)
	{
		const uint32_t* entry = reinterpret_cast<const uint32_t*>(ctx.esi);
		if (entry)
			*Module::exe_ptr<uint32_t>(Modulate2xFlag_Addr) = entry[ShaderEntry_Id];
	}

	// (2) The promotion has to be redone for every material. psSetTextureColorOp
	// has its own copy of it but only reaches that when the requested colour op
	// differs from the previous one, and it records the op unpromoted. Two materials
	// that both ask for MODULATE are then identical to that test even when their
	// shader ids differ, so the second inherits the first's MODULATE2X combiner and
	// its intensity_state.
	//
	// Promoting from a hook at the entry, with the in-function copy blanked, makes
	// the op reaching that test the promoted one. A differing shader id then reopens
	// it by itself, while an op that really is unchanged still short circuits and
	// avoids rebuilding the shader every draw.
	static constexpr int PsSetTextureColorOp_Addr = 0xB800;
	static constexpr int PsSetTextureColorOp_Inline_Addr = 0xB832;
	static constexpr int PsSetTextureColorOp_Inline_Size = 29;
	static constexpr int IntensityState_Addr = 0x49EDC8;
	static constexpr uint32_t Op_Modulate = 4;
	static constexpr uint32_t Op_Modulate2x = 5;

	inline static SafetyHookMid PsSetTextureColorOp_hook = {};
	static void PsSetTextureColorOp_dest(safetyhook::Context& ctx)
	{
		// __usercall: eax is the texture stage, edx the requested colour op.
		if (ctx.eax != 0 || !Settings::RestoreXboxBrightness)
			return;

		uint32_t* intensityState = Module::exe_ptr<uint32_t>(IntensityState_Addr);
		*intensityState = 0;

		if (ctx.edx != Op_Modulate)
			return;
		if (*Module::exe_ptr<uint32_t>(Modulate2xFlag_Addr) != 1)
			return;

		ctx.edx = Op_Modulate2x;
		*intensityState = 1;
	}

	// (3) Texture stage 0's MODULATE2X snippet is a copy of the plain MODULATE one
	// in both shader model tables, missing the shift that does the doubling. Stage 1
	// carries it in both. Bits 24 to 27 of a destination token hold the shift, where
	// 1 means _x2. Both tables need patching: a material landing on the untouched
	// one gets the halved light with nothing to double it back.
	static constexpr int Modulate2xShift_ps11_Addr = 0x21EB43;
	static constexpr int Modulate2xShift_ps14_Addr = 0x21EF97;

	// (4) vsSetLightIntensity uploads the halved diffuse and c16 only on the frame
	// the mode turns on, and vsSetDirctinalLight overwrites that same register with
	// the unhalved diffuse every frame after. Dropping the test re-uploads it per
	// material, which runs after the light setup rather than before it.
	static constexpr int IntensityLatch_Addr = 0x10D16;

public:
	std::string_view description() override
	{
		return "RestoreXboxBrightness";
	}

	// Never install the irreversible NOPs or per-material hooks when off.
	// This option changes executable shader code and requires a restart.
	bool validate() override
	{
		return Settings::RestoreXboxBrightness;
	}

	void declare_settings() override
	{
		Settings::RestoreXboxBrightness.needs_restart();
	}

	bool apply() override
	{
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(Modulate2xShift_ps11_Addr), uint8_t(0x81));
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(Modulate2xShift_ps14_Addr), uint8_t(0x81));

		Memory::VP::Nop(Module::exe_ptr(IntensityLatch_Addr), 6);
		Memory::VP::Nop(Module::exe_ptr(PsSetTextureColorOp_Inline_Addr),
			PsSetTextureColorOp_Inline_Size);

		SelectVertexShader_hook = safetyhook::create_mid(
			Module::exe_ptr(SelectVertexShader_IdBranch_Addr), SelectVertexShader_dest);
		PsSetTextureColorOp_hook = safetyhook::create_mid(
			Module::exe_ptr(PsSetTextureColorOp_Addr), PsSetTextureColorOp_dest);

		return SelectVertexShader_hook && PsSetTextureColorOp_hook;
	}

	static RestoreXboxBrightness instance;
};
RestoreXboxBrightness RestoreXboxBrightness::instance;

// Restores the console sky glow, which PC port mostly included but was disabled
// in the code due to various issues.
//
// The effect blooms pixels whose framebuffer alpha beats a per stage baseline,
// alpha being an HDR exposure of 0 to 4.0 rather than opacity. vsSetMaterial
// turns a material's intensity into that exposure, clamp(((intensity + 1) * 0.25)
// * glow_param[1] * 255), so an ordinary material at intensity 0 gives 63, and
// g_GlowParamTable sets the baseline to match.
//
// Five separate things had to be fixed for this to work properly, plus two
// more for quality:
class RestoreSkyGlow : public Hook
{
	static bool SkyGlowAllowed() noexcept
	{
		return Settings::SkyGlowFactor > 0 &&
			!(Settings::VREnabled && Settings::VRStereo);
	}

	// (1) The exposure reaches pixel shader constant c7 alpha, but nothing reads
	// it. Games pixel shaders are assembled by concatenating ps_1_1 snippets looked
	// up by combiner encoding, and entry for the HDR alpha op holds an empty snippet 
	// on PC, so alpha keeps whatever the texture stages left: opaque scenery writes 255 
	// where it should write 63 and the whole stage blooms.
	//
	// A key names an NV2A sum, (b3 * b2) + (b1 * b0), where 0x10 is zero, 0x30 one,
	// 0x14 v0, 0x18 to 0x1B t0 to t3, 0x1C r0, and 0x11 and 0x12 the stage's two
	// constants. SetHDRPostProcessCombiner picks by the draw's alpha reference:
	// 0x1C301010 below 0x80, which is r0 alone and so leaves alpha untouched, and
	// 0x10101230 at 0x80 and above, the second constant on its own. Only the second
	// is the exposure write, so only its entry is redirected and draws that keep
	// their own alpha are unaffected.
	//
	// Its key2 of 0x4C00 carries the one flag nibble set anywhere in either table,
	// AB_CD_MUX, making the result (r0.a >= 0.5) ? exposure : 0 rather than the
	// exposure everywhere. Multiplying by the alpha already in the register gives
	// the same two outcomes for a cutout mask in one instruction.
	static constexpr int AlphaOpTable_ps11_Entry0Snippet = 0x21F248;
	static constexpr int AlphaOpTable_ps14_Entry0Snippet = 0x21F2B8;

	// Alpha shader snippet for ps_1_1
	static inline const uint32_t Snippet_ps11[] = {
		0xFFFF0101, // not copied
		0x00000005, // mul
		0x80080000, // r0.a
		0x80FF0000, // r0.a
		0xA0FF0007, // c7.a
		0x0000FFFF, // end
	};
	// Alpha shader snippet for ps_1_4
	static inline const uint32_t Snippet_ps14[] = {
		0xFFFF0104,
		0x00000005,
		0x80080004, // r4.a
		0x80FF0004, // r4.a
		0xA0FF0007,
		0x0000FFFF,
	};

	// (2) InitRender leaves the alpha test on with D3DCMP_GREATEREQUAL and the
	// opaque class carries a reference of 128. That works while alpha holds texture
	// alpha, opaque texels being 255, but no exposure can reach it, so every opaque
	// draw would fail and vanish.
	//
	// Only the copy psSetPixelShader reasserts is lowered. The 128 in
	// SetDefaultAlphaState is also what SetHDRPostProcessCombiner tests to choose
	// the alpha op, and below 0x80 it installs the no-op, reverting the effect.
	// ApplyAlphaRenderState sets the device reference and picks the op from that
	// same value, then psSetPixelShader runs per material and leaves 1 for the draw.
	static constexpr int AlphaRefCompare_Imm = 0xB027;
	static constexpr int AlphaRefReassert_Imm = 0xB039;

	// (2b) The console uses one reference for every HDR draw, s_HdrState[4], left
	// at 1 by SetHDRPostProcessCombiner, which is what the immediates above now
	// hold. One value serves because its alpha op is a MUX: alpha comes out as the
	// material's exposure or as 0, so 1 always cuts at half texture alpha.
	//
	// The mul standing in for that MUX writes tex_alpha * exposure, a ramp, so 1
	// would cut at almost nothing and every soft alpha edge would draw the fringe
	// it used to clip. Half the exposure puts the cut back where the MUX had it,
	// so a draw carrying the op has its reference set per draw instead.
	static constexpr int PsSetPixelShader_Addr = 0xAF80;
	static constexpr int HdrState_Addr = 0x49BC04;
	static constexpr int ReqPresetPs_Addr = 0x49BC20;
	static constexpr int VsSetMaterial_Exposure_Addr = 0x10F4F;

	// (2c) byte_95AEF4 is bit 8 of a material's first texture attribute, set per
	// material by SetMaterialStructure to mark one that needs its real alpha.
	// psSetPixelShader passes it to ConstructPixelShaderProgram, which then skips
	// stage 4 and emits no exposure op, and picks s_HdrState[1] over [2] for
	// D3DRS_COLORWRITEENABLE, the same mask with the alpha bit cleared. Neither is
	// in the Xbox build, which calls its shader builder with no argument at all
	// and always uses the mask with alpha.
	//
	// The guard covers a case that cannot arise. It stops a blended draw having
	// its alpha replaced by an exposure the blender would then use as srcA, but a
	// blended draw is alpha class 1, and SetHDRPostProcessCombiner gives an HDR
	// enable of 0 the no-op alpha op regardless. Only class 0 carries the exposure
	// op, and class 0 has blending off.
	//
	// What it costs is every material with alpha in its texture, cutouts as well
	// as blends. A hatched road verge is a cutout, so it writes no exposure and
	// shows whatever is behind it, which against sky is the sky's own exposure.
	static constexpr int MaterialKeepsAlpha_Addr = 0x8F56;


	// ConstructPixelShaderProgram's output: the per entry alpha op keys, their
	// second words, and the entry count in the low nibble of the last.
	static constexpr int PsdAlphaOp_Addr = 0x49BC28;
	static constexpr int PsdAlphaOp2_Addr = 0x49BC9C;
	static constexpr int PsdCount_Addr = 0x49BD14;
	static constexpr uint32_t MaxCombinerEntries = 9;

	// The combiner encoding whose table entry is redirected above, so finding it
	// among the emitted entries is what says this shader writes the exposure.
	static constexpr uint32_t ExposureAlphaOp = 0x10101230;
	static constexpr uint32_t ExposureAlphaOp2 = 0x4C00;

	// The exposure op only reaches a shader if ConstructPixelShaderProgram emitted
	// stage 4 carrying it, and three separate things stop that. byte_95AEF4, bit 8
	// of the material's first texture attribute, makes it skip stage 4 outright,
	// which is how a material keeps real alpha for blending. A reference below
	// 0x80 makes SetHDRPostProcessCombiner put the no-op op there instead. And a
	// material whose earlier stages fill all nine entries never reaches stage 4 at
	// all. The emitted list is the one place all three show up, and is what
	// BuildPixelShaderFromCombiners_mb keys its own snippet lookup on.
	static bool ShaderWritesExposure()
	{
		const uint32_t count = *Module::exe_ptr<uint32_t>(PsdCount_Addr) & 0xF;
		const uint32_t* alphaOp = Module::exe_ptr<uint32_t>(PsdAlphaOp_Addr);
		const uint32_t* alphaOp2 = Module::exe_ptr<uint32_t>(PsdAlphaOp2_Addr);

		for (uint32_t i = 0; i < count && i < MaxCombinerEntries; i++)
		{
			if (alphaOp[i] == ExposureAlphaOp && alphaOp2[i] == ExposureAlphaOp2)
				return true;
		}

		return false;
	}

	// The exposure varies per material, so the reference has to follow it rather
	// than sit at a constant. The console alpha op was a MUX, (r0.a >= 0.5) ?
	// exposure : 0, which cut at half alpha whatever the reference was, since
	// everything below the threshold came out at zero. The mul that stands in for
	// it writes tex_alpha * exposure, a ramp rather than a step, so the cut lands
	// wherever reference over exposure falls instead.
	inline static uint32_t MaterialExposure = 1;

	inline static SafetyHookMid Exposure_hook = {};
	static void Exposure_dest(safetyhook::Context& ctx)
	{
		// __ftol2 has just returned it; the game clamps over the next few
		// instructions, with unsigned compares, so a negative conversion lands
		// at 255 rather than 1.
		uint32_t exposure = ctx.eax;
		if (exposure < 1)
			exposure = 1;
		if (exposure > 255)
			exposure = 255;

		MaterialExposure = exposure;
	}

	inline static SafetyHookInline PsSetPixelShader_hook = {};
	static int __stdcall PsSetPixelShader_dest()
	{
		const int result = PsSetPixelShader_hook.stdcall<int>();

		// A preset shader is not built from the combiner tables, so st_psd does not
		// describe it and the patched immediate never applied to it either. The
		// game gives it s_HdrState[3], 8 for the blended class, and overriding
		// that would drop everything below half alpha.
		if (*Module::exe_ptr<uint32_t>(ReqPresetPs_Addr) != 0)
			return result;

		// Zero means the game left the reference alone, so nothing here should
		// touch it either.
		if (*Module::exe_ptr<uint32_t>(HdrState_Addr) == 0)
			return result;

		// A shader without the op keeps the reference the game left it, which the
		// immediates above have already put where the console holds it.
		if (!ShaderWritesExposure())
			return result;

		// Half the exposure, putting the cut where the console's MUX had it.
		DWORD alphaRef = MaterialExposure / 2;
		if (alphaRef < 1)
			alphaRef = 1;

		if (IDirect3DDevice9* device = Game::D3DDevice())
			device->SetRenderState(D3DRS_ALPHAREF, alphaRef);

		return result;
	}

	// (3) D3D9 blends alpha with the colour factors, so the sky's exposure lands as
	// srcA*srcA + dstA*(1 - srcA) instead of srcA.
	//
	// Seeding the frame clear colour with that exposure, E = 0.25 * glow_param[0], 
	// makes that E*E + E*(1 - E), which is E, the blend's fixed point, so it comes 
	// out with right value without needing to override blend modes.
	//
	// Consoles seem to reach E by never clearing alpha and letting it settle across
	// frames, which the DISCARD swap chain used on PC can't do. E also suits pixels 
	// no sky covers: Sky_Disp draws with depth off and transparent scenery writes RGB 
	// only, so on Alaska, which has no skyId0 and shows black, a 0 clear would previously
	// leave a hard edge on surfaces that intersect empty sky parts.
	static constexpr int ClearBuffer_Addr = 0xEC70;
	static constexpr int BackColor_Addr = 0x49BD5C;
	static constexpr int GlowParam0_Addr = 0x4A8C18;

	// (4b) InitFilter tests g_GlowEnabled once at game_init around the whole of the
	// one time setup: the pixel shaders, and scaling vtx_glow2glow_base by
	// g_ScreenMultiplyX and Y. Nothing repeats either, so booting with the effect
	// off left the composite quad at its authored 640x480 and switching it on later
	// drew the glow into that corner with no shaders bound.
	//
	// Dropping the test runs the setup either way, leaving the flag to SceneControl
	// as the per frame switch. D3D_GlowInit_mb tests it itself, so the render
	// targets are still only allocated once the effect is on.
	static constexpr int InitFilter_EnabledCheck_Addr = 0x14CE7;

	// (4) Flag for enabling the glow effect - always set to 0 on PC.
	// (the launcher exe did include a setting for the glow that was hidden, devs
	// likely intended to add an option for it, but guess they ran out of time
	// to implement it fully - to be fair it took us over 2 years to fix too :P)
	static constexpr int GlowEnabled_Addr = 0x55AF09;

	// Addresses for glow texture sizes
	static constexpr int GlowInit_Addr = 0x14C00;
	static constexpr int GlowInit_WidthImm[] = { 0x14C22, 0x14C45, 0x14C69 };
	static constexpr int GlowInit_HeightImm[] = { 0x14C1D, 0x14C40, 0x14C64 };

	// Extract and blur passes both draw a quad spanning 0,0 to the target size,
	// so also have to be updated with the proper texture size.
	static constexpr int ExtractQuad_XY[] = { 0x2236CC, 0x2236EC, 0x223704, 0x223708 };
	static constexpr int BlurQuad_XY[] = { 0x223754, 0x22378C, 0x2237BC, 0x2237C0 };

	// (5) MakeReduceBuff copies the back buffer into the glow buffer with a single
	// StretchRect. Bilinear samples 2x2, so reducing by 4x reads only four of every
	// sixteen pixels, and building edges alias and crawl. Two 2x steps sample all of
	// them, bilinear being an exact box filter at exactly half, and the extra
	// averaging adds the softness the small buffer is meant to provide. Only worth
	// doing when the reduction is more than 2x.
	static constexpr int MakeReduceBuff_Addr = 0x14E50;
	static constexpr int GlowRelease_Addr = 0x14C80;
	static constexpr int RenderCfgGlow_Addr = 0x39FCD5; // tested as (x & 3) == 2
	static constexpr int Step1Tex_Addr = 0x4A8C14;
	static constexpr int LatestTex_Addr = 0x4A8C08;
	static constexpr int GlowAmount_Addr = 0x4A8C40; // glow_param.amount_28

	inline static IDirect3DTexture9* ReduceHalf = nullptr;

	inline static SafetyHookInline MakeReduceBuff_hook = {};
	static void __stdcall MakeReduceBuff_dest()
	{
		// True stereo owns two independent eye images. The stock glow reducer
		// samples D3DBACKBUFFER_TYPE_MONO, which is the left/game backbuffer in
		// the VR renderer; letting this run would bake left-eye scenery into a
		// texture that is later composited into both eyes.
		if (!SkyGlowAllowed())
			return;

		// Checked here rather than in apply so the setting can be changed while the
		// game runs.
		if (!Settings::SkyGlowTwoStep || !ReduceHalf)
		{
			MakeReduceBuff_hook.stdcall();
			return;
		}

		// The conditions the original reduces under.
		if ((*Module::exe_ptr<uint8_t>(RenderCfgGlow_Addr) & 3) != 2)
			return;
		if (*Module::exe_ptr<int>(GlowAmount_Addr) == 0)
			return;

		IDirect3DDevice9* device = Game::D3DDevice();
		IDirect3DTexture9* step1 = *Module::exe_ptr<IDirect3DTexture9*>(Step1Tex_Addr);
		if (!device || !step1)
			return;

		IDirect3DSurface9* back = nullptr;
		IDirect3DSurface9* half = nullptr;
		IDirect3DSurface9* target = nullptr;

		if (SUCCEEDED(device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &back))
			&& SUCCEEDED(ReduceHalf->GetSurfaceLevel(0, &half))
			&& SUCCEEDED(step1->GetSurfaceLevel(0, &target)))
		{
			device->StretchRect(back, nullptr, half, nullptr, D3DTEXF_LINEAR);
			device->StretchRect(half, nullptr, target, nullptr, D3DTEXF_LINEAR);

			*Module::exe_ptr<IDirect3DTexture9*>(LatestTex_Addr) = step1;
		}

		if (target)
			target->Release();
		if (half)
			half->Release();
		if (back)
			back->Release();
	}

	// The intermediate is D3DPOOL_DEFAULT, so it has to be gone before a device
	// reset. D3D_GlowRelease_mb is where the game drops its own glow targets.
	inline static SafetyHookInline GlowRelease_hook = {};
	static void __stdcall GlowRelease_dest()
	{
		if (ReduceHalf)
		{
			ReduceHalf->Release();
			ReduceHalf = nullptr;
		}

		GlowRelease_hook.stdcall();
	}

	// (6) BlurGlowImage offsets its taps by `glow_param[11] / screen width` in texture
	// coordinates, growing by glow_param[12] each pass. Dividing by the live width
	// pins the blur to a fixed count of screen pixels, which covered most of the
	// picture at 640 across and is almost nothing at 3840: the offset stays 0.1
	// buffer texels either way, but the buffer is six times wider so the blur spans
	// six times less of the image, and four taps inside one texel leave bilinear
	// nothing to average.
	// Scaling both by width / 640 holds the texture coordinate offset constant, the 
	// proportion the console blurred at.
	static constexpr int BlurGlowImage_Addr = 0x15630;
	static constexpr int BlurOffset_Addr = 0x4A8C44;     // glow_param[11]
	static constexpr int BlurOffsetStep_Addr = 0x4A8C48; // glow_param[12]

	inline static SafetyHookInline BlurGlowImage_hook = {};
	static void __stdcall BlurGlowImage_dest()
	{
		// Keep the whole post-process chain inert while true stereo is active.
		// This is a second fail-safe behind g_GlowEnabled for paths that can be
		// entered from cached game state during a mode transition.
		if (!SkyGlowAllowed())
			return;

		float* offset = Module::exe_ptr<float>(BlurOffset_Addr);
		float* step = Module::exe_ptr<float>(BlurOffsetStep_Addr);

		const float scale = Game::screen_resolution->x / Game::original_resolution.x;
		const float prevOffset = *offset;
		const float prevStep = *step;

		*offset = prevOffset * scale;
		*step = prevStep * scale;

		{
			OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
				OutRunVR::GameSemantic::RenderScope::SkyGlow);
			BlurGlowImage_hook.stdcall();
		}

		*offset = prevOffset;
		*step = prevStep;
	}

	inline static SafetyHookInline GlowInit_hook = {};
	static void __stdcall GlowInit_dest()
	{
		// The setup runs even with SkyGlowFactor switched off, so the divisor 
		// is floored at 1 rather than taken from a setting that can be 0.
		const int factor = max(1, Settings::SkyGlowFactor.get());

		// Sized here rather than in apply because the render resolution is only
		// known once the game has read its config.
		int w = int(Game::screen_resolution->x) / factor;
		int h = int(Game::screen_resolution->y) / factor;

		// Floor at the size the console ran, so a small window still leaves the blur
		// room to work in.
		if (w < 160)
			w = 160;
		if (h < 120)
			h = 120;

		for (int addr : GlowInit_WidthImm)
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(w));
		for (int addr : GlowInit_HeightImm)
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(h));

		for (const int* quad : { ExtractQuad_XY, BlurQuad_XY })
		{
			Memory::VP::Patch(Module::exe_ptr<float>(quad[0]), float(w));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[1]), float(h));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[2]), float(w));
			Memory::VP::Patch(Module::exe_ptr<float>(quad[3]), float(h));
		}

		spdlog::info("RestoreSkyGlow: glow buffers sized {}x{}", w, h);

		// True-stereo VR owns its own per-eye R30 glow chain. Do not allocate
		// the game's mono glow render targets here: besides wasting a large
		// buffer at 4K, that chain can only sample D3DBACKBUFFER_TYPE_MONO and
		// would later leak left-eye content into the right eye.
		if (Settings::VREnabled && Settings::VRStereo)
		{
			if (ReduceHalf)
			{
				ReduceHalf->Release();
				ReduceHalf = nullptr;
			}
			spdlog::info(
				"RestoreSkyGlow: stock mono buffers skipped in true-stereo VR; R30 owns independent eye buffers factor={}",
				Settings::SkyGlowFactor.get());
			return;
		}

		GlowInit_hook.stdcall();

		// Halfway stage for the reduce, so neither StretchRect does more than a 2x.
		// This runs again after a device reset, so drop any previous one first.
		if (ReduceHalf)
		{
			ReduceHalf->Release();
			ReduceHalf = nullptr;
		}

		if (SkyGlowAllowed() && Settings::SkyGlowFactor > 2)
		{
			if (IDirect3DDevice9* device = Game::D3DDevice())
			{
				uint32_t halfW = uint32_t(Game::screen_resolution->x) / 2;
				uint32_t halfH = uint32_t(Game::screen_resolution->y) / 2;

				if (FAILED(device->CreateTexture(halfW, halfH, 1, D3DUSAGE_RENDERTARGET,
					D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &ReduceHalf, nullptr)))
				{
					ReduceHalf = nullptr;
					spdlog::warn("RestoreSkyGlow: reduce intermediate failed, glow will alias at edges");
				}
			}
		}
	}

	inline static SafetyHookInline ClearBuffer_hook = {};
	static int __cdecl ClearBuffer_dest(int a1)
	{
		// When glow is disabled (including true-stereo VR), preserve the game's
		// original clear alpha exactly. The exposure seed only exists to feed the
		// mono sky-glow extraction pass.
		if (!SkyGlowAllowed())
			return ClearBuffer_hook.ccall<int>(a1);

		uint32_t* backColor = Module::exe_ptr<uint32_t>(BackColor_Addr);
		const uint32_t prevColor = *backColor;

		if (Game::is_in_game() || *Game::current_mode == GameState::STATE_GAMEOVER)
		{
			float exposure = 0.25f * *Module::exe_ptr<float>(GlowParam0_Addr);

			int alpha = int(exposure * 255.0f);
			if (alpha < 0)
				alpha = 0;
			if (alpha > 255)
				alpha = 255;

			*backColor = (prevColor & 0x00FFFFFF) | (uint32_t(alpha) << 24);
		}

		int result = ClearBuffer_hook.ccall<int>(a1);

		// Only the clear needs the exposure in there; leaving it set changes what
		// every later clear starts from, including the menus after a race.
		*backColor = prevColor;

		return result;
	}

public:
	std::string_view description() override
	{
		return "RestoreSkyGlow";
	}

	void declare_settings() override
	{
		// The buffers are sized from the factor, so a change has to resize them.
		// SkyGlowTwoStep is read inside MakeReduceBuff on every call, so nothing
		// needs declaring for it at all.
		Settings::SkyGlowFactor.watch([] { RebuildGlowBuffers(); });
		Settings::VREnabled.watch([] { RebuildGlowBuffers(); });
		Settings::VRStereo.watch([] { RebuildGlowBuffers(); });
	}

	bool apply() override
	{
		// Note: hooks/patches are always applied regardless of INI settings, so they can be changed at runtime
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(GlowEnabled_Addr), uint8_t(SkyGlowAllowed() ? 1 : 0));
		if (Settings::SkyGlowFactor > 0 && !SkyGlowAllowed())
			spdlog::info("VR SKY GLOW: stock mono-backbuffer chain disabled; stereo renderer owns independent left/right glow extraction and blur");

		Memory::VP::Patch(Module::exe_ptr(AlphaOpTable_ps11_Entry0Snippet), uintptr_t(Snippet_ps11));
		Memory::VP::Patch(Module::exe_ptr(AlphaOpTable_ps14_Entry0Snippet), uintptr_t(Snippet_ps14));

		for (int addr : { AlphaRefCompare_Imm, AlphaRefReassert_Imm })
			Memory::VP::Patch(Module::exe_ptr<uint32_t>(addr), uint32_t(1));

		Memory::VP::Patch(Module::exe_ptr(MaterialKeepsAlpha_Addr), { 0x30, 0xC0 }); // and al, 1 -> xor al, al

		// jz over the one time setup, six bytes.
		Memory::VP::Nop(Module::exe_ptr(InitFilter_EnabledCheck_Addr), 6);

		GlowInit_hook = safetyhook::create_inline(Module::exe_ptr(GlowInit_Addr), GlowInit_dest);
		ClearBuffer_hook = safetyhook::create_inline(Module::exe_ptr(ClearBuffer_Addr), ClearBuffer_dest);
		MakeReduceBuff_hook = safetyhook::create_inline(Module::exe_ptr(MakeReduceBuff_Addr), MakeReduceBuff_dest);
		GlowRelease_hook = safetyhook::create_inline(Module::exe_ptr(GlowRelease_Addr), GlowRelease_dest);
		BlurGlowImage_hook = safetyhook::create_inline(Module::exe_ptr(BlurGlowImage_Addr), BlurGlowImage_dest);
		PsSetPixelShader_hook = safetyhook::create_inline(Module::exe_ptr(PsSetPixelShader_Addr), PsSetPixelShader_dest);

		if (!GlowInit_hook || !ClearBuffer_hook || !MakeReduceBuff_hook
			|| !GlowRelease_hook || !BlurGlowImage_hook || !PsSetPixelShader_hook)
			return false;

		// Mid hook rather than inline: vsSetMaterial is __usercall, and the
		// exposure only exists in a register partway through it.
		Exposure_hook = safetyhook::create_mid(Module::exe_ptr(VsSetMaterial_Exposure_Addr), Exposure_dest);

		// Read inside MakeReduceBuff on every call, so nothing to re-do.

		// The buffers are sized from the factor, so a change has to resize them.
		return true;
	}

	// Resizing the glow buffers means tearing down what the old size allocated.
	static void RebuildGlowBuffers()
	{
		// declare_settings runs whether or not the hooks installed, so a change
		// can reach here after apply gave up. The release path calls through
		// these, which would be a jump into nothing.
		if (!GlowInit_hook || !GlowRelease_hook)
			return;

		// Release before patching the enabled byte, so it frees resources if needed
		GlowRelease_dest();
		Memory::VP::Patch(Module::exe_ptr<uint8_t>(GlowEnabled_Addr), uint8_t(SkyGlowAllowed() ? 1 : 0));
		GlowInit_dest();
	}

	static RestoreSkyGlow instance;
};
RestoreSkyGlow RestoreSkyGlow::instance;

class ReflectionResolution : public Hook
{
	inline static std::array<int, 6> ReflectionResolution_Addrs = 
	{
		// Envmap_Init
		0x13B50 + 1,
		0x13BA1 + 1,
		0x13BA6 + 1,
		// D3D_CreateTemporaries
		0x17A69 + 1,
		0x17A88 + 1,
		0x17A8D + 1,
	};

public:
	std::string_view description() override
	{
		return "ReflectionResolution";
	}

	bool validate() override
	{
		return Settings::ReflectionResolution >= 2;
	}

	void declare_settings() override
	{
		Settings::ReflectionResolution.needs_restart();
	}

	bool apply() override
	{
		for (const int& addr : ReflectionResolution_Addrs)
		{
			Memory::VP::Patch(Module::exe_ptr<int>(addr), Settings::ReflectionResolution.get());
		}
		return true;
	}

	static ReflectionResolution instance;
};
ReflectionResolution ReflectionResolution::instance;

// Envmap_RenderToCubeMap redraws part of the car reflection cubemap each frame, picking
// up from the face the previous frame stopped on, so the count it works out is faces for
// this frame rather than an update rate. Vanilla asks for 3 of the 6 faces, completing a
// cubemap every second frame, which was 30 of them a second at the games 60FPS lock.
class ReflectionUpdateRate : public Hook
{
	const static int Envmap_FaceCount_Addr = 0x1447E;

	static constexpr int FacesPerCubemap = 6;

	inline static SafetyHookMid FaceCount_midhook = {};

	static void FaceCount_dest(SafetyHookContext& ctx)
	{
		// Carried between frames so a share that doesn't come to a whole number of
		// faces still averages out. In VR, render cadence can be 72/80/90/120 Hz;
		// normalize the work to elapsed time so 0.5 keeps the original 60 Hz
		// budget (3 faces/frame * 60) instead of scaling GPU cost with HMD Hz.
		static float pendingFaces = 0.0f;
		static LARGE_INTEGER lastCounter{};
		static LARGE_INTEGER frequency{};
		static OutRunVR::ReflectionFrameBudget::AdaptiveFrameCadence frameCadence{};

		float frameScale60 = 1.0f;
		bool frameSpike = false;
		if (Settings::VREnabled && Settings::VRNormalizeReflectionRate)
		{
			if (frequency.QuadPart <= 0)
				QueryPerformanceFrequency(&frequency);
			LARGE_INTEGER now{};
			QueryPerformanceCounter(&now);
			if (lastCounter.QuadPart > 0 && frequency.QuadPart > 0 &&
				now.QuadPart >= lastCounter.QuadPart)
			{
				const double dt = static_cast<double>(now.QuadPart - lastCounter.QuadPart) /
					static_cast<double>(frequency.QuadPart);
				// Avoid a long pause/load screen producing a one-frame cubemap spike.
				// At 120 Hz an over-budget frame can still be well below 18 ms.
				// Use the observed healthy headset cadence as an additional
				// late-frame criterion; preserve the old >18-ms protection.
				frameSpike = frameCadence.Observe(dt);
				frameScale60 = frameSpike ? 0.5f :
					static_cast<float>(std::clamp(dt * 60.0, 0.0, 1.0));
			}
			lastCounter = now;
		}
		else
		{
			lastCounter = {};
			frameCadence.Reset();
		}

		// Quest-inspired bounded render work: one deterministic budget
		// preserves original 60 Hz reflection quality while preventing XR
		// frame misses from triggering a large deferred cubemap redraw.
		const auto budget = OutRunVR::ReflectionFrameBudget::Advance(
			pendingFaces, Settings::ReflectionUpdateRate.get(), frameScale60,
			Settings::VREnabled && Settings::VRNormalizeReflectionRate,
			frameSpike);
		pendingFaces = budget.pendingFaces;
		ctx.eax = budget.faces;
	}

public:
	std::string_view description() override
	{
		return "ReflectionUpdateRate";
	}

	bool apply() override
	{
		Memory::VP::Nop(Module::exe_ptr<uint8_t>(Envmap_FaceCount_Addr), 7);
		FaceCount_midhook = safetyhook::create_mid(Module::exe_ptr(Envmap_FaceCount_Addr), FaceCount_dest);

		return true;
	}

	static ReflectionUpdateRate instance;
};
ReflectionUpdateRate ReflectionUpdateRate::instance;

class DisableDPIScaling : public Hook
{
public:
	std::string_view description() override
	{
		return "DisableDPIScaling";
	}

	bool validate() override
	{
		return Settings::DisableDPIScaling;
	}

	void declare_settings() override
	{
		Settings::DisableDPIScaling.needs_restart();
	}

	bool apply() override
	{
		SetProcessDPIAware();
		return true;
	}

	static DisableDPIScaling instance;
};
DisableDPIScaling DisableDPIScaling::instance;

class ScreenEdgeCullFix : public Hook
{
	const static int CalcBall3D2D_Addr = 0x49E70;

	// Hook CalcBall3D2D to rescale screen-ratio positions back to 4:3 positions that game code expects
	// (fixes objects like cones being culled out before they reach edge of the screen)
	inline static SafetyHookInline dest_orig = {};
	static float __cdecl destination(float a1, Sphere* a2, Sphere* a3)
	{
		float ret = dest_orig.ccall<float>(a1, a2, a3);

		if (!Settings::ScreenEdgeCullFix || !a3 || !Game::screen_resolution)
			return ret;

		// CalcBall3D2D already wrote the game's culling sphere. During
		// VR eye-extent changes, device Reset and minimize the original
		// source viewport can transiently be zero/invalid. Correct both
		// coordinates only after a complete finite 4:3 projection succeeds;
		// otherwise keep the original game's sphere and return value intact.
		const auto mapped = OutRunVrStageCull::CorrectBallProjection(
			a3->f0, a3->f1,
			Game::screen_resolution->x, Game::screen_resolution->y);
		if (mapped.valid)
		{
			a3->f0 = mapped.x;
			a3->f1 = mapped.y;
		}
		return ret;
	}

public:
	std::string_view description() override
	{
		return "ScreenEdgeCullFix";
	}

	bool apply() override
	{
		dest_orig = safetyhook::create_inline(Module::exe_ptr(CalcBall3D2D_Addr), destination);
		return !!dest_orig;
	}

	static ScreenEdgeCullFix instance;
};
ScreenEdgeCullFix ScreenEdgeCullFix::instance;

// VR PMT culling is intentionally attached to the *original visibility
// function's call boundary*, not to the render projection/WVP upload.
// Changing the live projection for an entire BeginScene caused previous visual
// regressions: world rendering and effects inherited a culling-only matrix.
//
// PMT walk:
//   EXE+0x5015 CALL render_node_visible_404b00
//   EXE+0x501D TEST EAX,EAX / JE ...
// Keep the original EAX answer for the VR-wide case, and override it only for
// explicit disable/fail-open. Both hooks are on the same rendering thread.
class DisableStageCulling : public Hook
{
    inline static SafetyHookMid before_visible_hook{};
    inline static SafetyHookMid result_gate_hook{};
    inline static bool signature_mismatch_logged = false;
    inline static bool projection_writable = false;
    inline static bool quest_occupant_lod0_pc_verified = false;
    inline static std::uint64_t scoped_calls = 0;
    inline static std::uint64_t fail_open_calls = 0;
    inline static std::uint64_t first_deferred_report = 0;

    // Canonical OutRun.exe + 0x55D8A0 = game's 0x0095D8A0 projection matrix.
    // Only a scoped CPU PMT visibility invocation ever sees the widened copy.
    static constexpr std::uintptr_t ProjectionRva = 0x0055D8A0u;

    struct SavedProjection
    {
        D3DMATRIX* target = nullptr;
        D3DMATRIX original{};
        bool active = false;
    };
    inline static thread_local SavedProjection saved{};

    static bool VrGameplay() noexcept
    {
        return Settings::VREnabled.get() && Game::current_mode &&
            (*Game::current_mode == GameState::STATE_GAME ||
             *Game::current_mode == GameState::STATE_SMPAUSEMENU) &&
            OutRunVR::RuntimeEligibility::MayInjectStereo();
    }

    static bool ValidateProjectionAddress() noexcept
    {
        D3DMATRIX* p = Module::exe_ptr<D3DMATRIX>(ProjectionRva);
        MEMORY_BASIC_INFORMATION mbi{};
        if (!p || !VirtualQuery(p, &mbi, sizeof(mbi)) ||
            mbi.State != MEM_COMMIT)
            return false;
        const DWORD access = mbi.Protect & 0xFFu;
        if (access != PAGE_READWRITE && access != PAGE_WRITECOPY &&
            access != PAGE_EXECUTE_READWRITE &&
            access != PAGE_EXECUTE_WRITECOPY)
            return false;
        const auto begin = reinterpret_cast<std::uintptr_t>(p);
        const auto regionEnd =
            reinterpret_cast<std::uintptr_t>(mbi.BaseAddress) + mbi.RegionSize;
        return begin <= regionEnd && regionEnd - begin >= sizeof(D3DMATRIX);
    }

    static bool GetWideFov(float& tanHorizontal, float& tanVertical) noexcept
    {
        const auto* frame = OutRunVRRenderer::GetLatchedStereoFrameView();
        if (!frame || !frame->valid || frame->poseSequence == 0)
            return false;
        const float margin = std::clamp(
            Settings::VRCullingUnionMarginDegrees.get(), 0.0f, 15.0f) *
            0.01745329251994329577f;
        float h = 0.0f, v = 0.0f;
        for (int eye = 0; eye < 2; ++eye)
        {
            const auto& fov = frame->eyeFov[eye];
            const float angles[4] = {
                fov.angleLeft, fov.angleRight, fov.angleDown, fov.angleUp
            };
            for (float angle : angles)
                if (!std::isfinite(angle) || std::abs(angle) >= 1.56f)
                    return false;
            if (!(fov.angleLeft < fov.angleRight) ||
                !(fov.angleDown < fov.angleUp))
                return false;
            h = (std::max)(h, (std::max)(std::abs(fov.angleLeft),
                std::abs(fov.angleRight)));
            v = (std::max)(v, (std::max)(std::abs(fov.angleDown),
                std::abs(fov.angleUp)));
        }
        // Symmetric enclosure of both OpenXR asymmetric eye frusta.
        // Conservative when either eye differs; never shrink original FOV.
        h = (std::min)(1.48f, h + margin);
        v = (std::min)(1.48f, v + margin);
        tanHorizontal = std::tan(h);
        tanVertical = std::tan(v);
        return std::isfinite(tanHorizontal) && tanHorizontal > 0.0f &&
            std::isfinite(tanVertical) && tanVertical > 0.0f;
    }

    static void RestoreScopedProjection() noexcept
    {
        if (!saved.active)
            return;
        if (saved.target)
            std::memcpy(saved.target, &saved.original, sizeof(D3DMATRIX));
        saved = {};
    }

    static void BeforeVisible(safetyhook::Context&) noexcept
    {
        // The companion after-call hook always restores the CPU matrix, even
        // when the original game decides this PMT node is invisible.
        RestoreScopedProjection();
        if (!projection_writable || !VrGameplay() ||
            Settings::VRStageCullingMode.get() != 1)
            return;

        float tanH = 0.0f, tanV = 0.0f;
        if (!GetWideFov(tanH, tanV))
            return;
        auto* projection = Module::exe_ptr<D3DMATRIX>(ProjectionRva);
        if (!projection)
            return;
        D3DMATRIX original{};
        std::memcpy(&original, projection, sizeof(original));
        if (!std::isfinite(original._11) || !std::isfinite(original._22) ||
            !std::isfinite(original._34) || !std::isfinite(original._44) ||
            original._11 <= 0.0f || original._22 <= 0.0f ||
            std::abs(original._34) < 0.5f || std::abs(original._44) > 0.5f)
            return; // Not a perspective-world source: never alter it.

        // D3D9 right-handed projection. A culling-only symmetric enclosure
        // lets the game keep its own visibility algorithm and node transforms.
        const float newX = (std::min)(original._11, 1.0f / tanH);
        const float newY = (std::min)(original._22, 1.0f / tanV);
        if (!std::isfinite(newX) || !std::isfinite(newY) ||
            newX <= 0.0f || newY <= 0.0f)
            return;
        saved.target = projection;
        saved.original = original;
        saved.active = true;
        projection->_11 = newX;
        projection->_22 = newY;
        projection->_31 = 0.0f;
        projection->_32 = 0.0f;
        ++scoped_calls;
    }

    static void AfterVisible(safetyhook::Context& ctx) noexcept
    {
        const bool scoped = saved.active;
        RestoreScopedProjection();

        // Original PC 405015 CALL 404B00; 40501D TEST EAX;
        // 405021 MOV EDX,[ESP+0x1C] / 405025 MOV EAX,[ESI+EDX*4+0x28].
        // Force visible and LOD0 only inside exact original player ROB draw.
        // Native mesh[0] existence and queue capacity checks remain intact.
        if(quest_occupant_lod0_pc_verified &&
           (Settings::VRQuestCockpitV2OccupantLod0 ||
            Settings::VRQuestCockpitV2PassengerVisible) &&
           OutRunVR::QuestCockpitV2::OriginalOccupantLod0Active() &&
           !OutRunVR::QuestCockpitV2::InSceneEffect() &&
           ctx.esp != 0) {
            const std::int32_t forcedLod=0;
            std::memcpy(reinterpret_cast<void*>(
                static_cast<std::uintptr_t>(ctx.esp)+0x1Cu),
                &forcedLod,sizeof(forcedLod));
            ctx.eax=1u;
            return;
        }
        const bool vr = VrGameplay();
        const int mode = Settings::VRStageCullingMode.get();
        if (vr && mode == 2)
        {
            ctx.eax = 1u; // TEST EAX,EAX now falls through
            return;
        }
        if (vr && mode == 1)
        {
            // A missing/invalid pose or unsafe projection must never delete
            // scenery in a VR frame. This costs perf only until VR is ready.
            if (!scoped)
            {
                ++fail_open_calls;
                ctx.eax = 1u;
            }
        }
        else if (Settings::DisableStageCulling.get())
        {
            // Original Graphics toggle remains authoritative for legacy and
            // desktop modes without patching code bytes under a live detour.
            ctx.eax = 1u;
        }

        if ((scoped_calls + fail_open_calls) != 0 &&
            ((scoped_calls + fail_open_calls) & 0xFFFFFu) == 0 &&
            first_deferred_report != scoped_calls + fail_open_calls)
        {
            first_deferred_report = scoped_calls + fail_open_calls;
            spdlog::info(
                "VR PMT CULL: scopedWide={} failOpen={} mode={} marginDeg={:.1f}; HMD coverage untested",
                scoped_calls, fail_open_calls, mode,
                Settings::VRCullingUnionMarginDegrees.get());
        }
    }

public:
    std::string_view description() override
    {
        return "DisableStageCulling";
    }

    bool apply() override
    {
        // Relocated TEST/JE must be stock before the mid-hook is installed.
        auto* gate = Module::exe_ptr<std::uint8_t>(
            OutRunVR::PmtNodeCull::ResultTestRva);
        if (!OutRunVR::PmtNodeCull::ResultGateBytesCompatible(
                gate, OutRunVR::PmtNodeCull::OriginalResultGate.size()))
        {
            if (!signature_mismatch_logged)
            {
                signature_mismatch_logged = true;
                spdlog::error(
                    "VR PMT CULL: signature mismatch at 0x{:X}, refusing hooks",
                    static_cast<unsigned>(OutRunVR::PmtNodeCull::ResultTestRva));
            }
            return false;
        }
        const auto* call = Module::exe_ptr<std::uint8_t>(
            OutRunVR::PmtNodeCull::WalkNodeVisibleCallRva);
        if (!call || *call != 0xE8u)
        {
            spdlog::error("VR PMT CULL: expected direct CALL absent at 0x5015");
            return false;
        }

        // The original PC caller carries the LOD local in [ESP+0x1C]
        // only on this exact code version. Never write on mismatched ABI.
        constexpr std::array<std::uint8_t,8> kPostcallOriginal{
            0x83,0xC4,0x08,0x85,0xC0,0x74,0x72,0x8B
        };
        constexpr std::array<std::uint8_t,8> kLodReadOriginal{
            0x8B,0x54,0x24,0x1C,0x8B,0x44,0x96,0x28
        };
        const auto* post=Module::exe_ptr<const std::uint8_t>(0x501Au);
        const auto* lod=Module::exe_ptr<const std::uint8_t>(0x5021u);
        quest_occupant_lod0_pc_verified=
            post && lod &&
            std::equal(kPostcallOriginal.begin(),kPostcallOriginal.end(),post) &&
            std::equal(kLodReadOriginal.begin(),kLodReadOriginal.end(),lod);
        if(Settings::VRQuestCockpitV2OccupantLod0 &&
           !quest_occupant_lod0_pc_verified)
            spdlog::warn("QuestCockpitV2 LOD0 unavailable: original "
                "40501A/405021 PC stack ABI mismatch");
        projection_writable = ValidateProjectionAddress();
        // Install the after-call restore FIRST. If the pre-call hook fails,
        // no source matrix is ever changed.
        result_gate_hook = safetyhook::create_mid(
            Module::exe_ptr(OutRunVR::PmtNodeCull::ResultTestRva),
            AfterVisible);
        if (!result_gate_hook)
            return false;
        before_visible_hook = safetyhook::create_mid(
            Module::exe_ptr(OutRunVR::PmtNodeCull::WalkNodeVisibleCallRva),
            BeforeVisible);
        if (!before_visible_hook)
        {
            result_gate_hook = {};
            return false;
        }
        spdlog::info(
            "VR PMT CULL: native result-gate modes installed; projectionWritable={} (wide FOV scoped to call only)",
            projection_writable);
        return true;
    }

    static DisableStageCulling instance;
};
DisableStageCulling DisableStageCulling::instance;

class DisableVehicleLODs : public Hook
{
	const static int DispOthcar_PatchAddr = 0xAE4E9;
public:
	std::string_view description() override
	{
		return "DisableVehicleLODs";
	}

	void declare_settings() override
	{
		Settings::DisableVehicleLODs.watch([this] { apply(); });
	}

	bool apply() override
	{
		// Patch "eax = car.LodNumber" -> "eax = 0"
		static TogglePatch patch(Module::exe_ptr(DispOthcar_PatchAddr), { 0x90, 0x31, 0xC0 });
		patch.set(Settings::DisableVehicleLODs);

		return true;
	}

	static DisableVehicleLODs instance;
};
DisableVehicleLODs DisableVehicleLODs::instance;

class FixZBufferPrecision : public Hook
{
	const static int CalcCameraMatrix_Addr = 0x84BD0;
	const static int Clr_SceneEffect_Addr = 0xBE70;

	inline static SafetyHookInline CalcCameraMatrix = {};

	static inline bool allow_znear_override = true;

	static void CalcCameraMatrix_dest(EvWorkCamera* camera)
    {
        if (Settings::VREnabled && Settings::VRCockpitFrameProbe && camera)
            OutRunVR::QuestCockpitV2::ThreadProbe().OnCamera(
                static_cast<std::uint8_t>(camera->cam_mode_34A),
                OutRunVRRenderer::IsCullingCameraSyncedNow(),
                OutRunVR::QuestCockpitV2::InSceneEffect());

        // Existing R26 Z precision and 6DoF near-plane are unchanged.
        // The rejected old DriverSeat never displaces the camera in V2.
        if (allow_znear_override && Settings::FixZBufferPrecision) {
            if (Settings::VRPositionalTracking &&
                Settings::VRStereo &&
                OutRunVR::RuntimeEligibility::MayInjectStereo() &&
                IsPlayableCarGameplay()) {
                camera->perspective_znear_BC =
                    OutRunVR::QuestCockpitV2::SafeNearPlane(
                        Settings::VRNearPlane.get(),0.03f,0.50f);
            } else if ((camera->cam_mode_34A==2 || camera->cam_mode_34A==0) &&
                       camera->cam_mode_timer_364==0 &&
                       Game::current_mode &&
                       (*Game::current_mode==STATE_GAME ||
                        *Game::current_mode==STATE_GOAL)) {
                camera->perspective_znear_BC=1.0f;
            } else if (camera->cam_mode_timer_364!=0 ||
                       !Game::current_mode ||
                       *Game::current_mode!=STATE_GAME) {
                camera->perspective_znear_BC=0.1f;
            } else {
                float inCarNear=0.25f;
                const auto* player=Game::pl_car();
                if (player && player->car_kind_11==7) inCarNear=0.2f;
                camera->perspective_znear_BC=inCarNear;
            }
        }
        OutRunVR::QuestCockpitV2::SeatPose pose{};
        const bool seatReady=QuestCockpitV2CameraPose(camera,pose);
        // Native CalcCameraMatrix consumes a temporary body-space seat
        // and leaves original simulation work unchanged on every exit.
        struct ScopedCamera final {
            EvWorkCamera* c;
            D3DVECTOR eye{},look{};
            bool active;
            ScopedCamera(EvWorkCamera* camera,
                OutRunVR::QuestCockpitV2::SeatPose seat,bool enabled)
                :c(camera),active(enabled) {
                if(active){
                    eye=c->cam_pos_F8;look=c->look_pos_104;
                    c->cam_pos_F8={seat.eye.x,seat.eye.y,seat.eye.z};
                    c->look_pos_104={seat.look.x,seat.look.y,seat.look.z};
                }
            }
            ~ScopedCamera() {
                if(active){c->cam_pos_F8=eye;c->look_pos_104=look;}
            }
        } scoped(camera,pose,seatReady);
        CalcCameraMatrix.call(camera);
    }

	// hook Clr_SceneEffect so we can reset camera z-near before screen effects are draw
	inline static SafetyHookInline Clr_SceneEffect = {};
	static void Clr_SceneEffect_dest(int a1)
    {
        const bool previousAllow=allow_znear_override;
        allow_znear_override=false;
        EvWorkCamera* camera=Module::exe_ptr<EvWorkCamera>(0x39FE10);
        const float previousNear=camera->perspective_znear_BC;
        {
            OutRunVR::QuestCockpitV2::ScopedSceneEffect effect;
            camera->perspective_znear_BC=0.05f;
            CalcCameraMatrix_dest(camera);
            OutRunVR::GameSemantic::ScopedRenderSemantic semantic(
                OutRunVR::GameSemantic::RenderScope::SceneEffect);
            Clr_SceneEffect.call(a1);
        }
        camera->perspective_znear_BC=previousNear;
        CalcCameraMatrix_dest(camera);
        allow_znear_override=previousAllow;
    }

public:
	std::string_view description() override
	{
		return "FixZBufferPrecision";
	}

	bool validate() override
    {
        return Settings::FixZBufferPrecision ||
            (Settings::VREnabled && Settings::VRQuestCockpitV2Enabled);
    }

	void declare_settings() override
	{
		Settings::FixZBufferPrecision.needs_restart();
	}

	bool apply() override
	{
		CalcCameraMatrix = safetyhook::create_inline(Module::exe_ptr(CalcCameraMatrix_Addr), CalcCameraMatrix_dest);
		if (!CalcCameraMatrix)
			return false;

		Clr_SceneEffect = safetyhook::create_inline(Module::exe_ptr(Clr_SceneEffect_Addr), Clr_SceneEffect_dest);
		return !!Clr_SceneEffect;
	}

	static FixZBufferPrecision instance;
};
FixZBufferPrecision FixZBufferPrecision::instance;

class TransparencySupersampling : public Hook
{
	const static int DeviceInitHookAddr = 0xEC2F;
	const static int DeviceResetHookAddr = 0x17A20;

	inline static SafetyHookMid dest_hook = {};
	inline static SafetyHookMid deviceReset_hook = {};
	static void destination(safetyhook::Context& ctx)
	{
		static D3DADAPTER_IDENTIFIER9 adapterId = { 0 };

		if (adapterId.VendorId == 0)
		{
			auto* d3d = Game::D3D();
			if (!d3d || !SUCCEEDED(d3d->GetAdapterIdentifier(*Game::D3DAdapterNum, 0, &adapterId)))
				adapterId.VendorId = 0xFFFF;
		}

		if (adapterId.VendorId == 0x10DE) // NVIDIA
		{
			auto* device = Game::D3DDevice();
			spdlog::debug("TransparencySupersampling: enabling NVIDIA SSAA");
			device->SetRenderState(D3DRS_MULTISAMPLEANTIALIAS, TRUE);
			// SSAA support must not silently overwrite the game's cached
			// alpha, blend or line state at device init/Reset.
			device->SetRenderState(D3DRS_MULTISAMPLEMASK, 0xFFFFFFFF);

			// TODO: Allow switching between ATOC/SSAA modes, may give better performance for some?
			// Enabling ATOC here causes graphical issues though.
			// (Intel apparently supports the same ATOC switch, but users have reported issues before, unsure if they were on intel)
			//device->SetRenderState(D3DRS_ADAPTIVETESS_Y, D3DFORMAT(MAKEFOURCC('A', 'T', 'O', 'C')));

			// NVIDIA transparency supersampling. Report driver API result rather
            // than claiming that the actual hardware pixel cost was measured.
			const HRESULT ssaaHr = device->SetRenderState(
                D3DRS_ADAPTIVETESS_Y, D3DFORMAT(MAKEFOURCC('S', 'S', 'A', 'A')));
            char gpuLab[4]{};
            if (GetEnvironmentVariableA("OUTRUN_VR_GPU_PROFILE", gpuLab,
                    static_cast<DWORD>(std::size(gpuLab))) == 1 && gpuLab[0] == '1')
                spdlog::info(
                    "VR GPU LAB SSAA DEVICE: vendor=NVIDIA hr=0x{:08X} driverAccepted={} hardwareCost=UNTESTED",
                    static_cast<unsigned int>(ssaaHr), SUCCEEDED(ssaaHr));
		}

		// TODO: AMD ATOC mode.
		// This causes same graphical issues that the NVIDIA ATOC above gave.
		// Maybe it can be worked into the actual rendering code instead.
#if 0
		else if (adapterId.VendorId == 0x1002) // AMD
		{
			auto* device = Game::D3DDevice();
			spdlog::debug("TransparencySupersampling: enabling AMD ATOC");
			device->SetRenderState(D3DRS_MULTISAMPLEANTIALIAS, TRUE);
			device->SetRenderState(D3DRS_ANTIALIASEDLINEENABLE, TRUE);
			device->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE);
			device->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_SRCALPHA);
			device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
			device->SetRenderState(D3DRS_MULTISAMPLEMASK, 0xFFFFFFFF);

			// AMD ATOC
			device->SetRenderState(D3DRS_POINTSIZE, MAKEFOURCC('A', '2', 'M', '1'));
		}
#endif
	}

public:
	std::string_view description() override
	{
		return "TransparencySupersampling";
	}

	bool validate() override
	{
        // VR.Enabled defaults to true even for plain 2D launches. Do not
        // suppress the original 2D graphics setting unless the selected
        // backend is actually the native DX9Ex VR reference.
        char backend[32]{};
        const DWORD length = GetEnvironmentVariableA(
            "OUTRUN_VR_BACKEND", backend, static_cast<DWORD>(std::size(backend)));
        const bool activeNativeVr = Settings::VREnabled &&
            length > 0 && length < std::size(backend) &&
            lstrcmpiA(backend, "d3d9") == 0;
        const bool eligible = Settings::TransparencySupersampling &&
            (!activeNativeVr || Settings::VRTransparencySupersampling);
        char gpuLab[4]{};
        if (GetEnvironmentVariableA("OUTRUN_VR_GPU_PROFILE", gpuLab,
                static_cast<DWORD>(std::size(gpuLab))) == 1 && gpuLab[0] == '1')
            spdlog::info(
                "VR GPU LAB SSAA GATE: graphics={} vr={} nativeDX9Ex={} eligible={} (device API acceptance tracked separately)",
                Settings::TransparencySupersampling.get(),
                Settings::VRTransparencySupersampling.get(), activeNativeVr, eligible);
        return eligible;
	}

	void declare_settings() override
	{
		Settings::TransparencySupersampling.needs_restart();
        Settings::VRTransparencySupersampling.needs_restart();
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(DeviceInitHookAddr), destination);
		deviceReset_hook = safetyhook::create_mid(Module::exe_ptr(DeviceResetHookAddr), destination);
		return !!dest_hook;
	}

	static TransparencySupersampling instance;
};
TransparencySupersampling TransparencySupersampling::instance;

class WindowedBorderless : public Hook
{
	const static int WinMain_BorderlessWindow_WndStyleExAddr = 0x18175;
	const static int WinMain_BorderlessWindow_WndStyleAddr = 0x1817A;
	const static int Win32_Init_DisableWindowResize_Addr1 = 0xE9E3;
	const static int Win32_Init_DisableWindowResize_Addr2 = 0xEA30;
	const static int Win32_Init_SetWindowPos_Addr = 0xEAA7;

	inline static SafetyHookMid dest_hook = {};
    inline static HWND mirror_backdrop_window = nullptr;

    static LRESULT CALLBACK mirror_backdrop_wndproc(
        HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam)
    {
        if (message == WM_ERASEBKGND)
        {
            RECT client{};
            if (GetClientRect(hwnd, &client))
            {
                FillRect(reinterpret_cast<HDC>(wparam), &client,
                    static_cast<HBRUSH>(GetStockObject(BLACK_BRUSH)));
                return 1;
            }
        }
        return DefWindowProcW(hwnd, message, wparam, lparam);
    }

    static void update_mirror_backdrop(
        const MONITORINFO& monitorInfo, bool needed)
    {
        if (!needed)
        {
            if (mirror_backdrop_window && IsWindow(mirror_backdrop_window))
                ShowWindow(mirror_backdrop_window, SW_HIDE);
            return;
        }

        constexpr wchar_t className[] = L"OutRunVRMirrorBackdrop";
        const HINSTANCE instance = GetModuleHandleW(nullptr);
        WNDCLASSW existing{};
        if (!GetClassInfoW(instance, className, &existing))
        {
            WNDCLASSW wc{};
            wc.lpfnWndProc = mirror_backdrop_wndproc;
            wc.hInstance = instance;
            wc.hbrBackground =
                static_cast<HBRUSH>(GetStockObject(BLACK_BRUSH));
            wc.lpszClassName = className;
            if (!RegisterClassW(&wc) &&
                GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
            {
                spdlog::warn(
                    "VR PC MIRROR: black backdrop class registration failed err={}",
                    GetLastError());
                return;
            }
        }

        if (!mirror_backdrop_window || !IsWindow(mirror_backdrop_window))
        {
            mirror_backdrop_window = CreateWindowExW(
                WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                className, L"", WS_POPUP,
                monitorInfo.rcMonitor.left, monitorInfo.rcMonitor.top,
                monitorInfo.rcMonitor.right - monitorInfo.rcMonitor.left,
                monitorInfo.rcMonitor.bottom - monitorInfo.rcMonitor.top,
                nullptr, nullptr, instance, nullptr);
            if (!mirror_backdrop_window)
            {
                spdlog::warn(
                    "VR PC MIRROR: black backdrop creation failed err={}",
                    GetLastError());
                return;
            }
        }

        const int width =
            monitorInfo.rcMonitor.right - monitorInfo.rcMonitor.left;
        const int height =
            monitorInfo.rcMonitor.bottom - monitorInfo.rcMonitor.top;
        SetWindowPos(mirror_backdrop_window, HWND_TOP,
            monitorInfo.rcMonitor.left, monitorInfo.rcMonitor.top,
            width, height, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        InvalidateRect(mirror_backdrop_window, nullptr, TRUE);
        UpdateWindow(mirror_backdrop_window);
    }

	static void destination(safetyhook::Context& ctx)
	{
		HWND window = HWND(ctx.ebp);
		int x = Settings::WindowPositionX;
		int y = Settings::WindowPositionY;
		int width = Game::screen_resolution->x;
		int height = Game::screen_resolution->y;
        int mirrorSourceWidth = width;
        int mirrorSourceHeight = height;
        if (Settings::VREnabled && Game::D3DPresentParams)
        {
            const auto backbufferWidth =
                static_cast<int>(Game::D3DPresentParams->BackBufferWidth);
            const auto backbufferHeight =
                static_cast<int>(Game::D3DPresentParams->BackBufferHeight);
            if (backbufferWidth >= 640 && backbufferWidth <= 8192 &&
                backbufferHeight >= 480 && backbufferHeight <= 8192)
            {
                mirrorSourceWidth = backbufferWidth;
                mirrorSourceHeight = backbufferHeight;
            }
        }

		// VR may intentionally render a larger internal backbuffer than the PC
		// desktop. Keep that render resolution for the HMD/SBS source, but fit the
		// borderless mirror window to the current monitor so a 3840x2160 render on
		// a 3440x1440 display is scaled instead of extending off-screen.
        // Preserve the VR internal eye backbuffer. Only resize the PC mirror
        // when a valid VR render resolution is explicitly configured.
        const bool vrInternalOverride = Settings::VRRenderWidth >= 640 &&
            Settings::VRRenderHeight >= 480 &&
            static_cast<std::int64_t>(static_cast<int>(Settings::VRRenderWidth)) *
                static_cast<int>(Settings::VRRenderHeight) <= 16777216LL;
        if (Settings::VREnabled &&
            (Settings::VRMirrorFitDesktop || vrInternalOverride || Settings::VRAutoRenderResolution))
		{
			MONITORINFO monitorInfo{};
			monitorInfo.cbSize = sizeof(monitorInfo);
			const HMONITOR monitor = MonitorFromWindow(
				window, MONITOR_DEFAULTTOPRIMARY);
			if (monitor && GetMonitorInfoW(monitor, &monitorInfo))
			{
                const int monitorWidth =
                    monitorInfo.rcMonitor.right - monitorInfo.rcMonitor.left;
                const int monitorHeight =
                    monitorInfo.rcMonitor.bottom - monitorInfo.rcMonitor.top;
                x = monitorInfo.rcMonitor.left;
                y = monitorInfo.rcMonitor.top;
                width = monitorWidth;
                height = monitorHeight;
                // The unified physical source may be portrait 2496x2688
                // while a 3440x1440 desktop mirror is ultrawide. Stretching
                // the HWND to that whole monitor rescales the D3D9Ex Present
                // anisotropically and flattens car/menu sprites vertically.
                // Fit the WINDOW, never the actual game/eye render buffers.
                // Users can opt out for old full-width mirror A/B captures.
                bool mirrorBackdropNeeded = false;
                if (Settings::VRMirrorPreserveAspect) {
                    const auto fit = OutRunVRMirrorAspect::Fit(
                        monitorWidth, monitorHeight,
                        mirrorSourceWidth, mirrorSourceHeight);
                    if (fit.valid) {
                        x += fit.left;
                        y += fit.top;
                        width = fit.width;
                        height = fit.height;
                        mirrorBackdropNeeded =
                            fit.width < monitorWidth ||
                            fit.height < monitorHeight;
                    }
                }
                update_mirror_backdrop(monitorInfo, mirrorBackdropNeeded);
                spdlog::info(
                    "VR PC MIRROR: monitor={}x{} logical={}x{} backbufferSource={}x{} fittedWindow={}x{} origin={},{} preserveAspect={} backdrop={} (OpenXR eyes unchanged)",
                    monitorWidth, monitorHeight,
                    Game::screen_resolution->x, Game::screen_resolution->y,
                    mirrorSourceWidth, mirrorSourceHeight,
                    width, height, x, y,
                    Settings::VRMirrorPreserveAspect.get(),
                    mirrorBackdropNeeded ? 1 : 0);
			}
		}

		SetWindowPos(window, 0, x, y, width, height, 0x40);
	}

public:
	std::string_view description() override
	{
		return "WindowedBorderless";
	}

	bool validate() override
	{
		return Settings::WindowedBorderless;
	}

	void declare_settings() override
	{
		Settings::WindowedBorderless.needs_restart();
		Settings::WindowPositionX.needs_restart();
		Settings::WindowPositionY.needs_restart();
	}

	bool apply() override
	{
		auto* patch_addr = Module::exe_ptr(WinMain_BorderlessWindow_WndStyleExAddr);
		Memory::VP::Patch(patch_addr, uint32_t(0));

		patch_addr = Module::exe_ptr(WinMain_BorderlessWindow_WndStyleAddr);
		Memory::VP::Patch(patch_addr, uint32_t(WS_POPUP));

		patch_addr = Module::exe_ptr(Win32_Init_DisableWindowResize_Addr1);
		Memory::VP::Nop(patch_addr, 6);

		patch_addr = Module::exe_ptr(Win32_Init_DisableWindowResize_Addr2);
		Memory::VP::Nop(patch_addr, 6);

		// replace original SetWindowPos call
		Memory::VP::Nop(Module::exe_ptr(Win32_Init_SetWindowPos_Addr), 0x23);
		dest_hook = safetyhook::create_mid(Module::exe_ptr(Win32_Init_SetWindowPos_Addr), destination);

		return true;
	}

	static WindowedBorderless instance;
};
WindowedBorderless WindowedBorderless::instance;

class AnisotropicFiltering : public Hook
{
	const static int ChangeTexAttribute_HookAddr1 = 0x9AD8;
	const static int ChangeTexAttribute_HookAddr2 = 0x8960;

	inline static SafetyHookMid dest_hook = {};
	static bool PreserveScreenTextureFiltering() noexcept
	{
		if (!Settings::VREnabled.get())
			return false;
		const auto scope = OutRunVR::GameSemantic::EffectiveScope();
		return scope == OutRunVR::GameSemantic::RenderScope::ScreenHud ||
			scope == OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D ||
			scope == OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D ||
			scope == OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D;
	}
	static void destination(safetyhook::Context& ctx)
	{
		if (Settings::AnisotropicFiltering <= 0)
			return;
		const int sampler = ctx.ebp;
		// A prior 3D texture can leave 16x anisotropy on a HUD sampler.
		// Keep 2D MIN/MAG/MIP unmodified while resetting its max level.
		const int anisotropy = PreserveScreenTextureFiltering()
			? 1 : Settings::AnisotropicFiltering.get();
		Game::D3DDevice()->SetSamplerState(sampler,
			D3DSAMP_MAXANISOTROPY, anisotropy);
	}

	// ChangeTexAttribute reads the mip filter from bits 19-20 of the material and
	// passes it straight to D3DSAMP_MIPFILTER, but first rewrites a 3 into a 1:
	// D3DTEXF_ANISOTROPIC is not a legal D3D9 mip filter, and it picks POINT rather
	// than LINEAR to replace it.
	// A material asking for the best filtering therefore gets hard mip transitions, 
	// which shimmer wherever the mip level changes quickly across a surface, thin 
	// geometry seen at an angle most of all.
	const static int MipFilter_HookAddr = 0x9B73;

	inline static SafetyHookMid mip_hook = {};
	static void mip_destination(safetyhook::Context& ctx)
	{
		if (Settings::AnisotropicFiltering <= 0 ||
			PreserveScreenTextureFiltering())
			return;

		// Only upgrade POINT. A material that asked for no mipmapping at all is
		// left alone, since that is a deliberate choice for 2D and UI textures.
		if (ctx.esi == D3DTEXF_POINT)
			ctx.esi = D3DTEXF_LINEAR;
	}

	inline static SafetyHookMid dest_hook2 = {};
	static void destination2(safetyhook::Context& ctx)
	{
		// Checked before the filter is forced below, so 0 really does leave the
		// games filtering untouched rather than only skipping the level.
		if (Settings::AnisotropicFiltering <= 0 ||
			PreserveScreenTextureFiltering())
			return;
		// Only minification needs forced anisotropy for 3D materials.
		// MAGFILTER retains the game's requested value. All ScreenHud and
		// 2D overlays still bypass this hook via PreserveScreenTextureFiltering.
		if (ctx.edi == D3DSAMP_MINFILTER)
			ctx.esi = D3DTEXF_ANISOTROPIC;
	}

public:
	std::string_view description() override
	{
		return "AnisotropicFiltering";
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(ChangeTexAttribute_HookAddr1), destination);
		dest_hook2 = safetyhook::create_mid(Module::exe_ptr(ChangeTexAttribute_HookAddr2), destination2);
		mip_hook = safetyhook::create_mid(Module::exe_ptr(MipFilter_HookAddr), mip_destination);

		return true;
	}

	static AnisotropicFiltering instance;
};
AnisotropicFiltering AnisotropicFiltering::instance;

class VSyncOverride : public Hook
{
	const static int D3DInit_HookAddr = 0xEB66;

	inline static SafetyHookMid dest_hook = {};

	static bool IsNativeD3D9ReferenceLaunch() noexcept
	{
		char backend[32]{};
		const DWORD length = GetEnvironmentVariableA(
			"OUTRUN_VR_BACKEND", backend, static_cast<DWORD>(std::size(backend)));
		return length > 0 && length < std::size(backend) &&
			lstrcmpiA(backend, "d3d9") == 0;
	}

	static void ConfigureReferenceVRMSAA() noexcept
	{
		if (!Settings::VREnabled || !IsNativeD3D9ReferenceLaunch() ||
			!Game::D3D() || !Game::D3DPresentParams || !Game::D3DAdapterNum)
			return;

        auto& params = *Game::D3DPresentParams;
        const int vrMode = Settings::VRAntiAliasing.get();
        if (vrMode == 3)
        {
            // Keep 2D's AA selection unchanged only in explicit Game AA mode.
            spdlog::info("VR DX9Ex AA: using original game/2D type={} quality={}",
                static_cast<int>(params.MultiSampleType), params.MultiSampleQuality);
            return;
        }
        // VR-only modes must not inherit an expensive game NONMASKABLE request.
        // This does not change Game::D3DAntialiasing or saved 2D configuration.
        params.MultiSampleType = D3DMULTISAMPLE_NONE;
        params.MultiSampleQuality = 0;
        if (vrMode == 0)
        {
            spdlog::info("VR DX9Ex AA: Off, independent of 2D game AA");
            return;
        }
        if (vrMode != 1 && vrMode != 2 && vrMode != 4)
        {
            spdlog::warn("VR DX9Ex AA: invalid level {}, using Off", vrMode);
            return;
        }
        if (params.SwapEffect != D3DSWAPEFFECT_DISCARD)
        {
            spdlog::warn("VR DX9Ex AA: swap effect {} disallows MSAA; using Off",
                static_cast<int>(params.SwapEffect));
            return;
        }

		const UINT adapter = static_cast<UINT>(*Game::D3DAdapterNum);
		D3DFORMAT colorFormat = params.BackBufferFormat;
		if (colorFormat == D3DFMT_UNKNOWN)
		{
			D3DDISPLAYMODE mode{};
			if (FAILED(Game::D3D()->GetAdapterDisplayMode(adapter, &mode)))
			{
				spdlog::warn("VR DX9Ex AA: display format unavailable; using Off");
				return;
			}
			colorFormat = mode.Format;
		}

        // 2x never escalates. 4x may fall back to 2x. 8x is
        // opt-in and tries 8x -> 4x -> 2x; unsupported modes fail closed.
        // Preserve mode 3 as "Use Game AA" for existing user INI files.
		const D3DMULTISAMPLE_TYPE candidates[] = {
            D3DMULTISAMPLE_8_SAMPLES,
			D3DMULTISAMPLE_4_SAMPLES,
			D3DMULTISAMPLE_2_SAMPLES
		};
		for (const auto sampleType : candidates)
		{
            if (vrMode == 1 && sampleType != D3DMULTISAMPLE_2_SAMPLES)
                continue;
            if (vrMode == 2 && sampleType == D3DMULTISAMPLE_8_SAMPLES)
                continue;
			DWORD colorQuality = 0;
			if (FAILED(Game::D3D()->CheckDeviceMultiSampleType(
					adapter, D3DDEVTYPE_HAL, colorFormat, params.Windowed,
					sampleType, &colorQuality)) ||
				colorQuality == 0)
				continue;

			DWORD depthQuality = colorQuality;
			if (params.EnableAutoDepthStencil)
			{
				if (FAILED(Game::D3D()->CheckDeviceMultiSampleType(
						adapter, D3DDEVTYPE_HAL, params.AutoDepthStencilFormat,
						params.Windowed, sampleType, &depthQuality)) ||
					depthQuality == 0)
					continue;
			}

			params.MultiSampleType = sampleType;
            // Index zero avoids forcing an adapter's maximum quality tier.
			params.MultiSampleQuality = 0;
			spdlog::info(
				"VR DX9Ex AA: explicit {}x MSAA selected quality={} (colorLevels={} depthLevels={}); replaces ambiguous NONMASKABLE game AA",
				static_cast<int>(sampleType), params.MultiSampleQuality,
				colorQuality, depthQuality);
			return;
		}

		spdlog::warn("VR DX9Ex AA: selected MSAA unsupported; using Off (not game 2D AA)");
	}

	static void destination(safetyhook::Context& ctx)
	{
		ConfigureReferenceVRMSAA();
		if (Settings::VREnabled && Settings::VRDisableDesktopVsync)
		{
			Game::D3DPresentParams->PresentationInterval =
				D3DPRESENT_INTERVAL_IMMEDIATE;
			spdlog::info("VR PRESENT: desktop D3D9 VSync bypass active; OpenXR cadence is owned by the host/runtime");
		}
		else
		{
			Game::D3DPresentParams->PresentationInterval = Settings::VSync;
			if (!Settings::VSync)
				Game::D3DPresentParams->PresentationInterval =
					D3DPRESENT_INTERVAL_IMMEDIATE;
		}

		// DX9Ex reference runs select an explicit multisample type above.
		// Other backends retain the game's original AA presentation parameters.
	}

public:
	std::string_view description() override
	{
		return "VSync";
	}

	bool validate() override
	{
		// The D3D9 reference path also owns the explicit MSAA selection above.
		// CORRECTNESS normally keeps desktop VSync at its default, so without
		// this clause the hook never installed and the runtime silently stayed
		// on the game's NONMASKABLE AA despite the requested 4x/2x policy.
		return Settings::VSync != 1 ||
			(Settings::VREnabled &&
				(Settings::VRDisableDesktopVsync ||
				 IsNativeD3D9ReferenceLaunch()));
	}

	void declare_settings() override
	{
		Settings::VSync.needs_restart();
        Settings::VRAntiAliasing.needs_restart();
	}

	bool apply() override
	{
		dest_hook = safetyhook::create_mid(Module::exe_ptr(D3DInit_HookAddr), destination);

		return true;
	}

	static VSyncOverride instance;
};
VSyncOverride VSyncOverride::instance;
