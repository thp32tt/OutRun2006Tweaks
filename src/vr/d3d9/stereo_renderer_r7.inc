#include "../game/external_car_stereo_receipt.hpp"
#include "../game/external_car_atomic_precommit.hpp"
#include "../game/external_car_pbr_stereo_scope.hpp"
#include "../game/external_car_pbr_eye_math.hpp"
#include "../game/external_car_eye_transform_proof.hpp"
#include "depth_clear_replay_stamp.hpp"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <mutex>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr_shared.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/quest_cockpit_v2_passenger_event.hpp"
#include "vr/ipc/frame_pacing_diagnostics.hpp"
#include "vr/ipc/xr_eye_extent.hpp"
#include "vr/ui/vr_mirror_aspect_fit.hpp"
#include "vr/state/state_block_tracker.hpp"
#include "vr/d3d9/direct_gpu_hold_policy.hpp"

// True-stereo D3D9 renderer.
//
// Simulation, input, timers, native FFB and OutRun's render queue are never
// replayed. For draws targeting the real game backbuffer, the normal draw is
// turned into the LEFT eye and the same D3D draw is repeated once into a
// matching full-size RIGHT-eye render target while all renderer state is alive.
//
// vr_renderer_probe.cpp remains the single head-tracking/recenter authority and
// latches one immutable head/FOV/IPD packet per successful game BeginScene. This
// file consumes that packet for every draw in the scene; it never re-samples the
// x64 host on a per-draw basis.
//
// World geometry is promoted to per-eye projection only when its live c64..c67
// values exactly correspond to a renderer-probe-verified OutRun WVP upload AND
// the current vertex-shader epoch is the same epoch that performed that upload.
// HUD/effect draws therefore fall back to identical zero-disparity duplication.
//
// At Present both full-size eye surfaces are resolved and drawn side-by-side to
// the real backbuffer. The x64 host crops that SBS transport and submits it as
// XrCompositionLayerProjection using the exact host pose sequence published by
// this renderer. Stereo metadata is published only after the real D3D9 Present
// succeeds, so Desktop Duplication can never pair a new pose with an older frame.

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRAutoEnableWhenHostPresent;
	extern Setting<bool> VRStereo;
	extern Setting<bool> VRDirectGpuOnly;
    extern Setting<int> VRHmdlessDebugMode;
	extern Setting<float> VRWorldScale;
	extern Setting<float> VRStereoDepth;
	extern Setting<bool> VRTelemetry;
    extern Setting<bool> VRQuestCockpitV2Enabled;
    extern Setting<bool> VRQuestCockpitV2SkyProbe;
    extern Setting<bool> VRExternalFerrariTest;
    extern Setting<bool> VRF50ExternalModel;
}

#ifndef OUTRUN_VR_BUILD_SHA
#define OUTRUN_VR_BUILD_SHA "unknown"
#endif

namespace OutRunVRRenderer
{
    bool GetQuestNativeEyeInverse(float outMatrix[16],
        int eye,std::uint32_t& poseSequence) noexcept;
    bool GetQuestNativeEyeInversePair(float outMatrices[2][16],
        std::uint32_t& poseSequence) noexcept;
}

namespace OutRunVRStereo
{
	namespace
	{
		constexpr std::size_t ResetVtableIndex = 16;
        constexpr std::size_t CreateAdditionalSwapChainVtableIndex = 13;
        constexpr std::size_t SwapChainPresentVtableIndex = 3;
		constexpr std::size_t PresentVtableIndex = 17;
		constexpr std::size_t PresentExVtableIndex = 121;
        constexpr std::size_t ResetExVtableIndex = 132;
		constexpr std::size_t CreateDepthStencilSurfaceVtableIndex = 29;
		constexpr std::size_t CreateDepthStencilSurfaceExVtableIndex = 131;
		constexpr std::size_t UpdateSurfaceVtableIndex = 30;
		constexpr std::size_t StretchRectVtableIndex = 34;
		constexpr std::size_t ColorFillVtableIndex = 35;
		constexpr std::size_t SetRenderTargetVtableIndex = 37;
		constexpr std::size_t SetDepthStencilSurfaceVtableIndex = 39;
		constexpr std::size_t ClearVtableIndex = 43;
		constexpr std::size_t DrawPrimitiveVtableIndex = 81;
		constexpr std::size_t DrawIndexedPrimitiveVtableIndex = 82;
		constexpr std::size_t DrawPrimitiveUPVtableIndex = 83;
		constexpr std::size_t DrawIndexedPrimitiveUPVtableIndex = 84;
		constexpr std::size_t SetRenderStateVtableIndex = 57;
		constexpr std::size_t SetVertexShaderVtableIndex = 92;
		constexpr std::size_t CreateQueryVtableIndex = 118;
		constexpr std::size_t QueryIssueVtableIndex = 6;
		constexpr UINT OutRunWvpRegister = 64;
		constexpr UINT OutRunWvpRegisterCount = 4;
		constexpr std::uintptr_t OutRunProjectionRva = 0x0095D8A0u - 0x00400000u;
		constexpr float VerifiedWvpEpsilon = 1.0e-4f;

		SafetyHookInline ResetHook{};
		SafetyHookInline PresentHook{};
		SafetyHookInline CandidatePresentExHook{};
        bool R7CandidatePresentBoundaryCovered=false;
        SafetyHookInline CandidateResetExHook{};
        bool R7CandidateResetBoundaryCovered=false;
        thread_local unsigned R7CandidateResetInFlight=0;
        using R7DirectResetTransportOwnerFn=void(*)() noexcept;
        std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetTransportOwner{nullptr};
        std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetBaselineOwner{nullptr};
        std::atomic<R7DirectResetTransportOwnerFn> R7DirectResetRasterOwner{nullptr};
        using R7DirectResetLifecycleOwnerFn=void(*)(bool,HRESULT) noexcept;
        std::atomic<R7DirectResetLifecycleOwnerFn> R7DirectResetLifecycleOwner{nullptr};
        SafetyHookInline CandidateSwapChainPresentHook{},CandidateAdditionalSwapChainHook{};
        void* R7CandidateSwapChainPresentTarget=nullptr;
        bool R7CandidateAdditionalChainSeen=false;
		SafetyHookInline CreateDepthRetentionHook{};
		SafetyHookInline CreateDepthRetentionExHook{};
		SafetyHookInline UpdateSurfaceHook{};
		SafetyHookInline StretchRectHook{};
		SafetyHookInline ColorFillHook{};
		SafetyHookInline SetRenderTargetHook{};
		SafetyHookInline SetDepthStencilSurfaceHook{};
		SafetyHookInline ClearHook{};
		SafetyHookInline DrawPrimitiveHook{};
		SafetyHookInline DrawIndexedPrimitiveHook{};
		SafetyHookInline DrawPrimitiveUPHook{};
		SafetyHookInline DrawIndexedPrimitiveUPHook{};
		SafetyHookInline SetRenderStateHook{};
		SafetyHookInline SetVertexShaderHook{};
		SafetyHookInline CreateQueryHook{};
		SafetyHookInline QueryIssueHook{};
		std::atomic<std::uint64_t> R7VisualReceiptSerial{0};

		HANDLE SharedMapping = nullptr;
		OutRunVR::SharedPoseState* SharedState = nullptr;
		HANDLE RenderFrameMapping = nullptr;
		OutRunVR::SharedRenderFrameRing* RenderFrameRing = nullptr;
		std::uint32_t RenderFrameRunGeneration = 0;
		bool RenderFrameRingClaimed = false;

		IDirect3DSurface9* BackBuffer = nullptr;
		IDirect3DSurface9* TrackedRenderTarget = nullptr;
		IDirect3DSurface9* TrackedDepthStencil = nullptr;
		// Immutable for the lifetime of this retained D3D9 surface.
		bool TrackedStencilFormatKnown = false;
		bool TrackedStencilFormatHasStencil = false;
		IDirect3DSurface9* RightEyeSurface = nullptr;
		IDirect3DSurface9* RightEyeDepth = nullptr;
		IDirect3DTexture9* LeftResolveTexture = nullptr;
		IDirect3DSurface9* LeftResolveSurface = nullptr;
		IDirect3DTexture9* RightResolveTexture = nullptr;
		IDirect3DSurface9* RightResolveSurface = nullptr;

		struct DirectTransportSlot
		{
			IDirect3DTexture9* leftTexture = nullptr;
			IDirect3DSurface9* leftSurface = nullptr;
			IDirect3DTexture9* rightTexture = nullptr;
			IDirect3DSurface9* rightSurface = nullptr;
			IDirect3DQuery9* fence = nullptr;
			HANDLE leftHandle = nullptr;
			HANDLE rightHandle = nullptr;
			std::uint32_t frameId = 0;
			bool producerPending = false;
			std::uint32_t pendingFrameId = 0;
			// True only after the producer fence completed and this slot was
			// advertised to the host. Unpublished timed-out slots need no ACK.
			bool published = false;
		};

		std::array<DirectTransportSlot, OutRunVR::RenderFrameRingSize> DirectTransportSlots{};
		IDirect3DTexture9* DirectInteropProbeTexture = nullptr;
		IDirect3DSurface9* DirectInteropProbeSurface = nullptr;
		IDirect3DQuery9* DirectInteropProbeFence = nullptr;
		HANDLE DirectInteropProbeHandle = nullptr;
		std::uint32_t DirectInteropProbeToken = 0;
		std::uint32_t ActiveDirectTransportSlot = 0;
		D3DFORMAT DirectTransportFormat = D3DFMT_UNKNOWN;
		std::uint32_t DirectTransportGeneration = 0;
		std::uint32_t DirectTransportWidth = 0;
		std::uint32_t DirectTransportHeight = 0;
		bool DirectTransportResourcesReady = false;
        OutRunVR::EyeExtent::Generation DirectEyeExtentGeneration{};
		bool DirectInteropVerified = false;
        // D3D9Ex device adapter identity and caps are immutable until device
        // replacement. Do not re-query COM for each DirectGPU Present.
        struct DirectTransportDeviceFacts
        {
            IDirect3DDevice9* device = nullptr; // non-owning; reset clears it
            LUID gameAdapterLuid{};
            UINT maxTextureWidth = 0;
            UINT maxTextureHeight = 0;
            bool adapterLuidKnown = false;
            bool textureLimitsKnown = false;
        };
        DirectTransportDeviceFacts DirectTransportFacts{};

        void BindDirectTransportFacts(IDirect3DDevice9* device) noexcept
        {
            if (DirectTransportFacts.device != device)
            {
                DirectTransportFacts = {};
                DirectTransportFacts.device = device;
            }
        }

		D3DSURFACE_DESC BackBufferDesc{};
		bool StereoResourcesReady = false;
		thread_local bool InternalStereoPass = false;
		std::array<bool, 3> AuxRenderTargetActive{};

		std::atomic<std::uintptr_t> CurrentVertexShaderIdentity{ 0 };
		std::atomic<std::uint64_t> VertexShaderSerial{ 0 };
		std::array<DWORD, 256> TrackedRenderStateValue{};
		std::array<bool, 256> TrackedRenderStateValid{};
		std::array<std::uint8_t, 256> TrackedRenderStateReads{};
		std::uint64_t TrackedRenderStateCacheHits = 0;
		std::uint64_t TrackedRenderStateLiveValidations = 0;
		std::uint64_t TrackedRenderStateMismatches = 0;
		std::atomic<int> ActiveOcclusionQueries{ 0 };
		std::atomic<bool> OcclusionQueryTrackingUnavailable{ false };
		std::atomic<bool> StereoBaseCallbacksArmed{ false };

		D3DMATRIX CachedProjection{};
		D3DMATRIX CachedInverseProjection{};
		bool ProjectionInverseValid = false;

		bool FrameHadDuplicatedDraw = false;
		bool FrameHadWorldStereo = false;
		bool FrameRightDrawFailed = false;
		bool FrameStereoIncomplete = false;
		OutRunVR::StereoFailureReason FrameFailureReason = OutRunVR::StereoFailureNone;
		std::uint32_t FrameStereoPoseSequence = 0;
		OutRunVRRenderer::LatchedStereoFrame FrameStereoMetadata{};
		std::uint32_t StereoFrameCounter = 0;
		bool RightDepthSynchronized = true;
		bool RightStencilSynchronized = true;
		bool LastStereoWanted = false;
		bool FramePoseMismatchLogged = false;
		std::uint64_t PresentEpoch = 1;
        std::uint64_t ExternalAtomicReplayEpoch=0;
		OutRunVR::DepthClearReplayStamp LastMainDepthClearStamp{};
		float LastMainDepthClearZ = 1.0f;
		DWORD LastMainDepthClearStencil = 0;
		D3DSURFACE_DESC LastMainDepthClearDesc{};

		ULONGLONG LastSummaryMs = 0;
		std::uint64_t DuplicatedDraws = 0;
		std::uint64_t WorldStereoDraws = 0;
		std::uint64_t NonWorldDuplicatedDraws = 0;
		std::uint64_t StereoComposeSuccess = 0;
		std::uint64_t StereoComposeFailure = 0;
		std::uint64_t MrtRejectedDraws = 0;
		std::uint64_t RestoreFailures = 0;
		std::uint64_t WorldClassificationFailures = 0;
		std::uint64_t OffscreenVerifiedWorldDraws = 0;
		std::uint64_t PoseSequenceMismatchFrames = 0;
		std::uint64_t MultiBeginScenePresents = 0;
		std::uint64_t MaxBeginScenesPerPresent = 0;
		std::uint64_t LastBeginSceneCountAtPresent = 0;
		std::uint64_t FixedFunctionNonWorldDraws = 0;
		std::uint64_t FixedFunctionWorldStereoDraws = 0;
		std::uint64_t FixedFunctionSkyRotationOnlyDraws = 0;
        // Diagnostic only: the original 4521C0 sky may use a
        // programmable c64 WVP rather than fixed-function XYZ.
        // This is NOT exact sky source ownership.
        std::uint64_t ProgrammableDepthOffWorldDraws = 0;
        std::uint64_t ProgrammableNonSkyDepthOffWorldDraws = 0;
        std::uint64_t ProgrammableExactWorldSkyDraws = 0;
        // Per-sky-draw mode coherence, not a generic depth-off heuristic.
        std::uint64_t ProgrammableSkyNativeViewDraws = 0;
        std::uint64_t ProgrammableSkyFallbackViewDraws = 0;
        std::uint64_t ProgrammableSkyMixedEyeDraws = 0;
        std::uint64_t ProgrammableSkyViewModeSwitches = 0;
        bool ProgrammableSkyLastModeKnown = false;
        bool ProgrammableSkyLastNative = false;
        // Quest XrRig::locate accepts the two eyes as one frame. Keep the
        // Windows native-vs-fallback decision equally frame-atomic: fixed and
        // programmable world draws in one Present reuse the first resolution.
        using QuestNativeEyePairMatrices = float[2][16];
        struct QuestNativePairPresentLatch {
            std::uint64_t presentEpoch = 0;
            std::uint32_t poseSequence = 0;
            bool resolved = false;
            bool available = false;
            QuestNativeEyePairMatrices matrices{};
            std::uint32_t headPoseSequence = 0;
            bool headResolved = false;
            bool headAvailable = false;
            D3DMATRIX headInverse{};
        };
        QuestNativePairPresentLatch QuestNativePairLatch{};
		bool FirstFixedFunctionWorldLogged = false;
		bool FirstFixedFunctionSkyRotationLogged = false;
		std::uint64_t OcclusionQueriesCreated = 0;
		std::uint64_t OcclusionQueryBegins = 0;
		std::uint64_t OcclusionQueryEnds = 0;
		std::uint64_t OcclusionStereoRejects = 0;
		std::uint64_t DirectTransportFrames = 0;
		std::uint64_t DirectTransportFallbacks = 0;
		std::uint64_t DirectTransportFenceTimeouts = 0;
		std::uint64_t DirectTransportRingBackpressure = 0;
		std::uint64_t DirectInteropProbeFailures = 0;
		std::uint64_t FullMainDepthClears = 0;
		std::uint64_t DepthBootstrapAttempts = 0;
		std::uint64_t DepthBootstrapSuccesses = 0;
		std::array<std::uint64_t, 32> FailureCounts{};
		bool FirstStereoActiveLogged = false;
		bool FirstWorldStereoLogged = false;
		bool FirstRestoreFailureLogged = false;
		bool FirstMrtRejectLogged = false;
		bool FirstOffscreenWorldLogged = false;
		bool FirstClassificationFailureLogged = false;
		bool FirstOcclusionRejectLogged = false;
		bool FirstOcclusionTrackingUnavailableLogged = false;
		bool FirstDirectTransportLogged = false;
		bool FirstDirectFallbackLogged = false;
		bool FirstDirectOnlyNoFrameLogged = false;
		bool FirstDirectDeferredLogged = false;
		bool FirstD3D9ExUnavailableLogged = false;
		bool FirstAdapterMismatchLogged = false;
		bool FirstInteropVerifiedLogged = false;
		bool FirstMainDepthReuseLogged = false;
		bool FirstMainClearLogged = false;
		bool FirstDepthBootstrapLogged = false;
		bool FirstDeferredResourceInitLogged = false;

		template <typename T>
		void ReleaseCom(T*& value)
		{
			if (value)
			{
				value->Release();
				value = nullptr;
			}
		}

		void ReplaceSurfaceRef(IDirect3DSurface9*& slot, IDirect3DSurface9* value)
		{
			if (value)
				value->AddRef();
			ReleaseCom(slot);
			slot = value;
		}

		struct InternalPassScope
		{
			bool previous = false;
			InternalPassScope() : previous(InternalStereoPass) { InternalStereoPass = true; }
			~InternalPassScope() { InternalStereoPass = previous; }
		};

		bool IsGameDevice(IDirect3DDevice9* device)
		{
			return device && Game::D3DDevice_ptr && *Game::D3DDevice_ptr == device;
		}

		bool FormatHasStencil(D3DFORMAT format);

		bool GameplayActive()
		{
			if (!Game::current_mode)
				return false;

			// Keep the original GAME/GOAL/TIMEUP/pause and WARP/RESTART
			// allowances, but never produce stereo for host mono Theater.
			// R45 host/game presentation parity: is_in_game() includes
			// TRYAGAIN and OUTRUNMILES, but both are mono Theater frames in
			// CurrentPresentationMode() and the OpenXR host. A stereo SBS
			// result buffer displayed inside one Theater quad makes the entire
			// screen binocularly doubled. Reject those exact Theater states
			// before the old gameplay/stage transition allowlist.
			// GOAL/TIMEUP and the established START/WARP/RESTART policies
			// remain unchanged.
			if (!Game::is_vr_gameplay_presentation())
				return false;
			if (Game::is_in_game())
				return true;

			// C2 finish-transition parity: is_in_game() excludes GIVEUP
			// and LINK_TIMEUP even though the shared host presentation owner
			// treats both as true-stereo Gameplay. Before this repair the host
			// waited for a stereo packet that the game's R7 StereoWanted()
			// refused to produce. That can expose mono/head-locked fallback
			// during the time/result transition immediately BEFORE TRYAGAIN.
			// Only restore exact host-allowed transition states; START remains
			// gated by the original game_start_progress_code == 65 rule.
			// The already-correct TRYAGAIN/OUTRUNMILES Theater remains excluded
			// by is_vr_gameplay_presentation() above.
			switch (*Game::current_mode)
			{
			case GameState::STATE_WARP:
			case GameState::STATE_RESTART:
			case GameState::STATE_GIVEUP:
			case GameState::STATE_LINK_TIMEUP:
				return true;
			default:
				return false;
			}
		}

		bool HostRenderEligible()
		{
            // Synthetic pose is latched inside the game renderer. Do not
            // impersonate the x64 OpenXR host or alter the shared-memory ABI.
            if (Settings::VRHmdlessDebugMode != 0)
                return true;
			if (!SharedState || SharedState->magic != OutRunVR::SharedMagic ||
				SharedState->protocolVersion != OutRunVR::SharedProtocolVersion ||
				SharedState->structSize != sizeof(OutRunVR::SharedPoseState))
				return false;
			const std::uint32_t flags = SharedState->flags;

			// Game-side stereo source generation is gated only by hard host
			// liveness/visibility. XrFrameState::shouldRender is transient compositor
			// advice to the x64 host; using it here used to zero the SBS frame metadata
			// and tear down the eye source for several Presents even though the host
			// heartbeat/session remained healthy. The host still decides independently
			// whether a given OpenXR frame submits a layer.
			return (flags & OutRunVR::HostAlive) != 0 &&
				(flags & OutRunVR::SessionVisible) != 0;
		}

		bool HostDirectTransportSupported()
		{
            if (Settings::VRHmdlessDebugMode != 0)
                return false;
			return SharedState && (SharedState->flags & OutRunVR::HostDirectGpuTransport) != 0;
		}

		bool HostDirectTransportReady()
		{
            if (Settings::VRHmdlessDebugMode != 0)
                return false;
			return SharedState && (SharedState->flags & OutRunVR::HostDirectGpuReady) != 0;
		}

		bool StereoWanted()
		{
			const bool hostEligible = HostRenderEligible();
			const bool wanted = Settings::VRStereo && GameplayActive() && hostEligible &&
				(Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent);
			if (wanted && !LastStereoWanted && TrackedDepthStencil)
			{
				RightDepthSynchronized = false;
				D3DSURFACE_DESC d{};
				if (SUCCEEDED(TrackedDepthStencil->GetDesc(&d)) && FormatHasStencil(d.Format))
					RightStencilSynchronized = false;
			}
			LastStereoWanted = wanted;
			return wanted;
		}

		bool AnyAuxRenderTargetActive()
		{
			return AuxRenderTargetActive[0] || AuxRenderTargetActive[1] || AuxRenderTargetActive[2];
		}

		bool TargetIsBackBuffer()
		{
			return BackBuffer && TrackedRenderTarget && TrackedRenderTarget == BackBuffer;
		}

		bool IsReadableRange(const void* address, std::size_t size)
		{
			if (!address || !size)
				return false;
			MEMORY_BASIC_INFORMATION info{};
			if (VirtualQuery(address, &info, sizeof(info)) != sizeof(info))
				return false;
			if (info.State != MEM_COMMIT || (info.Protect & PAGE_GUARD) || (info.Protect & PAGE_NOACCESS))
				return false;
			const auto begin = reinterpret_cast<std::uintptr_t>(address);
			const auto regionBegin = reinterpret_cast<std::uintptr_t>(info.BaseAddress);
			const auto regionEnd = regionBegin + info.RegionSize;
			return begin >= regionBegin && begin + size >= begin && begin + size <= regionEnd;
		}

		bool ImageContainsRange(std::uintptr_t rva, std::size_t size)
		{
			const auto base = reinterpret_cast<std::uintptr_t>(Module::ExeHandle);
			if (!base || !IsReadableRange(reinterpret_cast<const void*>(base), sizeof(IMAGE_DOS_HEADER)))
				return false;
			const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
			if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 0x100000)
				return false;
			const auto ntAddress = base + static_cast<std::uintptr_t>(dos->e_lfanew);
			if (!IsReadableRange(reinterpret_cast<const void*>(ntAddress), sizeof(IMAGE_NT_HEADERS)))
				return false;
			const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(ntAddress);
			if (nt->Signature != IMAGE_NT_SIGNATURE)
				return false;
			const std::size_t imageSize = nt->OptionalHeader.SizeOfImage;
			return rva <= imageSize && size <= imageSize - rva;
		}

		bool MatrixFinite(const D3DMATRIX& matrix)
		{
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					if (!std::isfinite(matrix.m[r][c]))
						return false;
			return true;
		}

		D3DMATRIX IdentityMatrix()
		{
			D3DMATRIX out{};
			out._11 = out._22 = out._33 = out._44 = 1.0f;
			return out;
		}

		D3DMATRIX MatrixFromQuaternionTranslation(const float qIn[4], const float position[3], float positionScale)
		{
			float x=qIn[0],y=qIn[1],z=qIn[2],w=qIn[3]; const float lenSq=x*x+y*y+z*z+w*w;
			if (!std::isfinite(lenSq)||lenSq<=1.0e-12f) return IdentityMatrix(); const float inv=1.0f/std::sqrt(lenSq); x*=inv;y*=inv;z*=inv;w*=inv;
			D3DMATRIX out=IdentityMatrix(); const float xx=x*x,yy=y*y,zz=z*z,xy=x*y,xz=x*z,yz=y*z,xw=x*w,yw=y*w,zw=z*w;
			out._11=1-2*(yy+zz);out._12=2*(xy+zw);out._13=2*(xz-yw);out._21=2*(xy-zw);out._22=1-2*(xx+zz);out._23=2*(yz+xw);
			out._31=2*(xz+yw);out._32=2*(yz-xw);out._33=1-2*(xx+yy);out._41=position[0]*positionScale;out._42=position[1]*positionScale;out._43=position[2]*positionScale; return out;
		}
		D3DMATRIX InverseRigid(const D3DMATRIX& m)
		{
			D3DMATRIX out=IdentityMatrix(); out._11=m._11;out._12=m._21;out._13=m._31;out._21=m._12;out._22=m._22;out._23=m._32;out._31=m._13;out._32=m._23;out._33=m._33;
			out._41=-(m._41*out._11+m._42*out._21+m._43*out._31);out._42=-(m._41*out._12+m._42*out._22+m._43*out._32);out._43=-(m._41*out._13+m._42*out._23+m._43*out._33); return out;
		}

		D3DMATRIX MultiplyMatrix(const D3DMATRIX& a, const D3DMATRIX& b)
		{
			D3DMATRIX out{};
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					for (int k = 0; k < 4; ++k)
						out.m[r][c] += a.m[r][k] * b.m[k][c];
			return out;
		}

		D3DMATRIX TransposeMatrix(const D3DMATRIX& in)
		{
			D3DMATRIX out{};
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					out.m[r][c] = in.m[c][r];
			return out;
		}

		bool InvertMatrix(const D3DMATRIX& in, D3DMATRIX& out)
		{
			float a[4][8]{};
			for (int r = 0; r < 4; ++r)
			{
				for (int c = 0; c < 4; ++c)
					a[r][c] = in.m[r][c];
				a[r][4 + r] = 1.0f;
			}
			for (int col = 0; col < 4; ++col)
			{
				int pivot = col;
				float pivotAbs = std::fabs(a[pivot][col]);
				for (int r = col + 1; r < 4; ++r)
				{
					const float candidate = std::fabs(a[r][col]);
					if (candidate > pivotAbs)
					{
						pivot = r;
						pivotAbs = candidate;
					}
				}
				if (!std::isfinite(pivotAbs) || pivotAbs < 1.0e-8f)
					return false;
				if (pivot != col)
					for (int c = 0; c < 8; ++c)
						std::swap(a[pivot][c], a[col][c]);
				const float divisor = a[col][col];
				for (int c = 0; c < 8; ++c)
					a[col][c] /= divisor;
				for (int r = 0; r < 4; ++r)
				{
					if (r == col)
						continue;
					const float factor = a[r][col];
					for (int c = 0; c < 8; ++c)
						a[r][c] -= factor * a[col][c];
				}
			}
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					out.m[r][c] = a[r][c + 4];
			return MatrixFinite(out);
		}

		bool FloatArrayNear(const float* a, const float* b, std::size_t count, float epsilon)
		{
			if (!a || !b)
				return false;
			for (std::size_t i = 0; i < count; ++i)
				if (!std::isfinite(a[i]) || !std::isfinite(b[i]) || std::fabs(a[i] - b[i]) > epsilon)
					return false;
			return true;
		}

		D3DMATRIX ProjectionFromFov(const D3DMATRIX& base, const OutRunVR::SharedFov& fov)
		{
			const float tanLeft = std::tan(fov.angleLeft);
			const float tanRight = std::tan(fov.angleRight);
			const float tanUp = std::tan(fov.angleUp);
			const float tanDown = std::tan(fov.angleDown);
			const float width = tanRight - tanLeft;
			const float height = tanUp - tanDown;
			D3DMATRIX out{};
			out._11 = 2.0f / width;
			out._22 = 2.0f / height;
			out._31 = (tanRight + tanLeft) / width;
			out._32 = (tanUp + tanDown) / height;
			out._33 = base._33;
			out._34 = base._34;
			out._43 = base._43;
			out._44 = base._44;
			return out;
		}

		bool ReadProjection(D3DMATRIX& projection)
		{
			float rendererProjection[16]{};
			if (OutRunVRRenderer::GetRendererBaseProjection(rendererProjection))
				std::memcpy(&projection, rendererProjection, sizeof(projection));
			else
			{
				if (!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX))) return false;
				const auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
				if (!IsReadableRange(projectionPtr, sizeof(D3DMATRIX))) return false;
				std::memcpy(&projection, projectionPtr, sizeof(projection));
			}
			return MatrixFinite(projection) && std::fabs(projection._34 + 1.0f) < 0.25f && std::fabs(projection._44) < 0.25f;
		}

		bool GetInverseProjection(const D3DMATRIX& projection, D3DMATRIX& inverse)
		{
			if (!ProjectionInverseValid || std::memcmp(&projection, &CachedProjection, sizeof(projection)) != 0)
			{
				D3DMATRIX candidate{};
				if (!InvertMatrix(projection, candidate)) return false;
				CachedProjection = projection;
				CachedInverseProjection = candidate;
				ProjectionInverseValid = true;
			}
			inverse = CachedInverseProjection;
			return true;
		}

		bool EnsureSharedState()
		{
			if (SharedState)
				return SharedState->magic == OutRunVR::SharedMagic && SharedState->protocolVersion == OutRunVR::SharedProtocolVersion && SharedState->structSize == sizeof(OutRunVR::SharedPoseState);
			SharedMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, static_cast<DWORD>(sizeof(OutRunVR::SharedPoseState)), OutRunVR::SharedMemoryName);
			if (!SharedMapping) return false;
			const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;
			SharedState = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(SharedMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedPoseState)));
			if (!SharedState) { CloseHandle(SharedMapping); SharedMapping = nullptr; return false; }
			if (!existed)
			{
				std::memset(SharedState, 0, sizeof(*SharedState));
				SharedState->protocolVersion = OutRunVR::SharedProtocolVersion;
				SharedState->structSize = sizeof(*SharedState);
				MemoryBarrier();
				SharedState->magic = OutRunVR::SharedMagic;
			}
			return true;
		}

		std::uint32_t MakeRenderFrameRunGeneration() noexcept
		{
			LARGE_INTEGER qpc{};
			QueryPerformanceCounter(&qpc);
			std::uint32_t generation =
				static_cast<std::uint32_t>(qpc.LowPart) ^
				static_cast<std::uint32_t>(qpc.HighPart) ^
				GetCurrentProcessId() ^
				GetTickCount() ^
				0x52554E47u; // 'RUNG'
			if (!generation)
				generation = 1;
			return generation;
		}

		bool ClaimRenderFrameRingForCurrentRun() noexcept
		{
			if (!RenderFrameRing)
				return false;
			const bool headerValid =
				RenderFrameRing->magic == OutRunVR::RenderFrameMagic &&
				RenderFrameRing->protocolVersion == OutRunVR::RenderFrameProtocolVersion &&
				RenderFrameRing->structSize == sizeof(OutRunVR::SharedRenderFrameRing) &&
				RenderFrameRing->slotCount == OutRunVR::RenderFrameRingSize;
			if (!headerValid)
				return false;

			const std::uint32_t self = GetCurrentProcessId();
			if (!RenderFrameRunGeneration)
				RenderFrameRunGeneration = MakeRenderFrameRunGeneration();

			if (RenderFrameRingClaimed)
				return RenderFrameRing->clientPid == self &&
					RenderFrameRing->reserved0 == RenderFrameRunGeneration;

			// The host may keep Frame.v2 mapped across a fast game restart.
			// Claim a new run generation under the ring seqlock and invalidate
			// every old slot before publishing any frame from this process.
			LONG ringSeq = InterlockedIncrement(
				reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			if ((ringSeq & 1) == 0)
				ringSeq = InterlockedIncrement(
					reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			MemoryBarrier();

			RenderFrameRing->clientPid = self;
			RenderFrameRing->reserved0 = RenderFrameRunGeneration;
			RenderFrameRing->latestSlot = 0;
			for (auto& slot : RenderFrameRing->slots)
			{
				std::memset(&slot, 0, sizeof(slot));
				slot.protocolVersion = OutRunVR::RenderFrameProtocolVersion;
				slot.structSize = sizeof(slot);
				slot.clientPid = self;
				slot.reserved[OutRunVR::RenderFrameRunGenerationIndex] =
					RenderFrameRunGeneration;
				MemoryBarrier();
				slot.magic = OutRunVR::RenderFrameMagic;
			}

			MemoryBarrier();
			ringSeq = InterlockedIncrement(
				reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			if (ringSeq & 1)
				InterlockedIncrement(
					reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));

			// The legacy R7 DirectGPU fallback has only a global frame ACK and no
			// transport generation. If the host keeps SharedPose mapped across a fast
			// game restart, an old high ACK could otherwise make the new run's frame
			// IDs (which restart at 1) look consumed before the host ever samples them.
			if (EnsureSharedState())
				InterlockedExchange(
					reinterpret_cast<volatile LONG*>(&SharedState->hostDirectConsumedFrameId),
					0);

			RenderFrameRingClaimed = true;
			spdlog::info(
				"VR Frame.v2: claimed run identity pid={} generation=0x{:08x}; stale slots and legacy DirectGPU ACK from previous game runs invalidated",
				self, RenderFrameRunGeneration);
			return true;
		}

		bool EnsureRenderFrameState()
		{
			if (RenderFrameRing)
				return ClaimRenderFrameRingForCurrentRun();

			RenderFrameMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameRing)), OutRunVR::RenderFrameMemoryName);
			if (!RenderFrameMapping) return false;
			const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;
			RenderFrameRing = static_cast<OutRunVR::SharedRenderFrameRing*>(MapViewOfFile(RenderFrameMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedRenderFrameRing)));
			if (!RenderFrameRing) return false;
			if (!existed)
			{
				std::memset(RenderFrameRing, 0, sizeof(*RenderFrameRing));
				RenderFrameRing->protocolVersion = OutRunVR::RenderFrameProtocolVersion;
				RenderFrameRing->structSize = sizeof(*RenderFrameRing);
				RenderFrameRing->slotCount = OutRunVR::RenderFrameRingSize;
				for (auto& slot : RenderFrameRing->slots)
				{
					slot.protocolVersion = OutRunVR::RenderFrameProtocolVersion;
					slot.structSize = sizeof(slot);
					slot.magic = OutRunVR::RenderFrameMagic;
				}
				MemoryBarrier();
				RenderFrameRing->magic = OutRunVR::RenderFrameMagic;
			}
			return ClaimRenderFrameRingForCurrentRun();
		}

		void PoisonFrame(OutRunVR::StereoFailureReason reason)
		{
			FrameStereoIncomplete = true;
			if (FrameFailureReason == OutRunVR::StereoFailureNone)
			{
				FrameFailureReason = reason;
				const auto index = static_cast<std::size_t>(reason);
				if (index < FailureCounts.size()) ++FailureCounts[index];
			}
		}

		bool ReadTrackedRenderState(IDirect3DDevice9* device,
			D3DRENDERSTATETYPE state, DWORD& out) noexcept;

        const QuestNativeEyePairMatrices* GetQuestNativeEyePairForPresent(
            std::uint32_t poseSequence) noexcept
        {
            if(poseSequence==0)return nullptr;
            if(QuestNativePairLatch.presentEpoch!=PresentEpoch) {
                QuestNativePairLatch={};
                QuestNativePairLatch.presentEpoch=PresentEpoch;
            }
            if(QuestNativePairLatch.resolved) {
                if(QuestNativePairLatch.poseSequence!=poseSequence ||
                   !QuestNativePairLatch.available)
                    return nullptr;
                return &QuestNativePairLatch.matrices;
            }

            QuestNativePairLatch.resolved=true;
            QuestNativePairLatch.poseSequence=poseSequence;
            QuestNativeEyePairMatrices pair{};
            std::uint32_t nativePoseSequence=0;
            QuestNativePairLatch.available=
                OutRunVRRenderer::GetQuestNativeEyeInversePair(
                    pair,nativePoseSequence) &&
                nativePoseSequence==poseSequence;
            if(!QuestNativePairLatch.available)
                return nullptr;
            std::memcpy(QuestNativePairLatch.matrices,pair,sizeof(pair));
            return &QuestNativePairLatch.matrices;
        }

        const D3DMATRIX* GetQuestHeadInverseForPresent(
            std::uint32_t poseSequence) noexcept
        {
            if(poseSequence==0)return nullptr;
            if(QuestNativePairLatch.presentEpoch!=PresentEpoch) {
                QuestNativePairLatch={};
                QuestNativePairLatch.presentEpoch=PresentEpoch;
            }
            if(QuestNativePairLatch.headResolved) {
                if(QuestNativePairLatch.headPoseSequence!=poseSequence ||
                   !QuestNativePairLatch.headAvailable)
                    return nullptr;
                return &QuestNativePairLatch.headInverse;
            }
            QuestNativePairLatch.headResolved=true;
            QuestNativePairLatch.headPoseSequence=poseSequence;
            float headBytes[16]{};
            std::uint32_t headPoseSequence=0;
            QuestNativePairLatch.headAvailable=
                OutRunVRRenderer::GetLatchedHeadInverse(
                    headBytes,headPoseSequence) &&
                headPoseSequence==poseSequence;
            if(!QuestNativePairLatch.headAvailable)
                return nullptr;
            std::memcpy(&QuestNativePairLatch.headInverse,headBytes,
                        sizeof(QuestNativePairLatch.headInverse));
            return MatrixFinite(QuestNativePairLatch.headInverse)
                ? &QuestNativePairLatch.headInverse : nullptr;
        }

		enum class EyeBuildResult { NonWorld, WorldStereo, FatalError };
		struct DrawStereoState
		{
			float originalConstants[16]{};
			float eyeConstants[2][16]{};
            float originalPbrView[16]{},originalPbrProjection[16]{};
            float originalPbrEye[4]{};
			D3DMATRIX fixedOriginalView{};
			D3DMATRIX fixedOriginalProjection{};
			D3DMATRIX fixedEyeView[2]{};
			D3DMATRIX fixedEyeProjection[2]{};
			bool worldStereo = false;
			bool fixedFunctionWorld = false;
            bool externalPbrWorld = false;
			bool fixedFunctionRotationOnly = false;
			std::uint32_t poseSequence = 0;
			OutRunVRRenderer::LatchedStereoFrame stereoFrame{};
		};

		EyeBuildResult BuildEyeConstants(IDirect3DDevice9* device, const OutRunVRRenderer::LatchedStereoFrame& stereo, DrawStereoState& state)
		{
			const std::uintptr_t trackedShader =
				CurrentVertexShaderIdentity.load(std::memory_order_acquire);
			const auto* externalPbr =
                OutRunVR::DinoSidecar::ActiveExternalStereoMesh ?
                OutRunVR::DinoSidecar::ActiveExternalPbrStereo : nullptr;
			if (trackedShader == 0 || externalPbr)
			{
				// R13/R29 intentionally masks the tracked identity to zero for
				// shader-based zero-disparity effects. Confirm the real D3D9
				// binding before treating this as a genuine fixed-function draw.
				IDirect3DVertexShader9* boundShader = nullptr;
				const HRESULT boundHr = device->GetVertexShader(&boundShader);
				if (FAILED(boundHr))
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}
				const bool shaderIdentityOk=externalPbr ?
                    boundShader==externalPbr->vertex : boundShader==nullptr;
                if(boundShader)boundShader->Release();
                if(!shaderIdentityOk)
                    return externalPbr ? EyeBuildResult::FatalError :
                        EyeBuildResult::NonWorld;
                if(externalPbr) {
                    IDirect3DPixelShader9* boundPixel=nullptr;
                    const HRESULT pixelHr=device->GetPixelShader(&boundPixel);
                    const bool pixelOk=SUCCEEDED(pixelHr) &&
                        boundPixel==externalPbr->pixel;
                    if(boundPixel)boundPixel->Release();
                    if(!pixelOk)return EyeBuildResult::FatalError;
                }

				DWORD fvf = 0;
				if (FAILED(device->GetFVF(&fvf)) || fvf == 0)
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}

				const DWORD positionType = fvf & D3DFVF_POSITION_MASK;
				switch (positionType)
				{
				case D3DFVF_XYZ:
				case D3DFVF_XYZB1:
				case D3DFVF_XYZB2:
				case D3DFVF_XYZB3:
				case D3DFVF_XYZB4:
				case D3DFVF_XYZB5:
					break;
				default:
					// XYZRHW and unknown/clip-space formats are screen-space
					// or otherwise already transformed; keep zero disparity.
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}

				if (FAILED(device->GetTransform(
						D3DTS_VIEW, &state.fixedOriginalView)) ||
					FAILED(device->GetTransform(
						D3DTS_PROJECTION, &state.fixedOriginalProjection)))
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}

				const auto projectionClass =
					OutRunVR::PassPolicy::ClassifyProjectionSignature(
						state.fixedOriginalProjection._34,
						state.fixedOriginalProjection._44);
				if (projectionClass !=
					OutRunVR::PassPolicy::ProjectionClass::Perspective3D)
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}

				// R84 regression: a paused ESC/option/menu D3DXSprite can
				// bind fixed-function XYZ, perspective projection and disable
				// depth, exactly like the heuristic SkyRotationOnly signature.
				// R26's dedicated source-owned 2D path must win first; when
				// its original-c64/eye proof is missing, preserve a single
				// original UI draw rather than misroute the fallback as 3D sky.
				// SkyGlow here means the *post-process* blur, not the original
				// world sky sphere. Untagged genuine sky keeps the original
				// rotation-only path; F11/rank/world shadow stay separate.
				if (OutRunVR::GameSemantic::CapturePhysicalDrawCommand()
				        .DeniesGenericWorldFallback())
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}
				// Car-select and other theater/menu previews also use
				// fixed-function perspective XYZ. They are not VR world geometry
				// and must not receive the headset inverse/eye transforms.
				DWORD zEnable = D3DZB_TRUE;
				if (!ReadTrackedRenderState(device, D3DRS_ZENABLE, zEnable))
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}
				const auto physicalDraw =
					OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
				const bool exactWorldSky =
					physicalDraw.scope ==
					OutRunVR::GameSemantic::RenderScope::WorldSky;
				const auto fixedPolicy =
					OutRunVR::PassPolicy::ClassifyFixedFunctionStereo(
						projectionClass, GameplayActive(),
						zEnable != D3DZB_FALSE);
				if (fixedPolicy ==
					OutRunVR::PassPolicy::FixedFunctionStereoPolicy::NonWorld)
				{
					++FixedFunctionNonWorldDraws;
					return EyeBuildResult::NonWorld;
				}
				const bool rotationOnly =
					exactWorldSky ||
					fixedPolicy ==
					OutRunVR::PassPolicy::FixedFunctionStereoPolicy::SkyRotationOnly;

				if (stereo.poseSequence == 0 ||
					!MatrixFinite(state.fixedOriginalView) ||
					!MatrixFinite(state.fixedOriginalProjection))
					return EyeBuildResult::FatalError;

				// Original 4521C0 shader sky already uses a fixed head/eye
                // fallback; fixed-function rotation-only sky must use the
                // SAME basis for both original layers. Previously this
                // branch switched to Quest native eye pairs at race start,
                // making sky layers appear doubled/counter-rotated.
                // Non-sky world still uses native Quest eye pairs.
                const auto* fixedNativeEyePair=rotationOnly ? nullptr :
                    GetQuestNativeEyePairForPresent(stereo.poseSequence);
                D3DMATRIX fallbackHeadRotation{};
                const D3DMATRIX* appliedHeadInverse=nullptr;
                if(!fixedNativeEyePair) {
                    const auto* headInverse=
                        GetQuestHeadInverseForPresent(stereo.poseSequence);
                    if(!headInverse)return EyeBuildResult::FatalError;
                    appliedHeadInverse=headInverse;
                    if(rotationOnly) {
                        fallbackHeadRotation=*headInverse;
                        fallbackHeadRotation._41=0.f;
                        fallbackHeadRotation._42=0.f;
                        fallbackHeadRotation._43=0.f;
                        appliedHeadInverse=&fallbackHeadRotation;
                    }
                }

				for (int eye = 0; eye < 2; ++eye)
				{
					float eyeOffset[3]{
						stereo.eyeOffset[eye][0],
						stereo.eyeOffset[eye][1],
						stereo.eyeOffset[eye][2]
					};
					if (rotationOnly)
						eyeOffset[0] = eyeOffset[1] = eyeOffset[2] = 0.0f;
					const D3DMATRIX eyePose =
						MatrixFromQuaternionTranslation(
							stereo.eyeOrientation[eye], eyeOffset,
							Settings::VRWorldScale * Settings::VRStereoDepth);
					const D3DMATRIX eyeInverse = InverseRigid(eyePose);
					// Native Quest 2D6B98..2D6BFC directly computes:
                    // view_matrix(compose(inverse(yawOrigin),XrEyePose)).
                    // Mode1 only; menus and all other renderer owners retain
                    // the preexisting headInverse * localEyeInverse route.
                    if(fixedNativeEyePair) {
                        D3DMATRIX nativeView{};
                        std::memcpy(&nativeView,(*fixedNativeEyePair)[eye],
                                    sizeof(nativeView));
                        if(!MatrixFinite(nativeView))
                            return EyeBuildResult::FatalError;
                        // Original sky rotation-only contract: never move the
                        // sky sphere with headset translation or virtual IPD.
                        // Before this correction Quest mode1 bypassed the
                        // rotationOnly translation masking above, making the
                        // sky layer move as the headset position changed.
                        if(rotationOnly) {
                            nativeView._41=0.f;
                            nativeView._42=0.f;
                            nativeView._43=0.f;
                        }
                        state.fixedEyeView[eye]=MultiplyMatrix(
                            state.fixedOriginalView,nativeView);
                    } else {
                        state.fixedEyeView[eye] =
                            MultiplyMatrix(
                                MultiplyMatrix(
                                    state.fixedOriginalView,
                                    *appliedHeadInverse),
                                eyeInverse);
                    }
					state.fixedEyeProjection[eye] =
						ProjectionFromFov(
							state.fixedOriginalProjection,
							stereo.eyeFov[eye]);
					if (!MatrixFinite(state.fixedEyeView[eye]) ||
						!MatrixFinite(state.fixedEyeProjection[eye]))
						return EyeBuildResult::FatalError;
				}

				state.fixedFunctionWorld = true;
                if(externalPbr) {
                    // Save the original c4/c8 and pixel c1 before issuing
                    // either eye: D3D9's SetTransform never updates custom VS.
                    if(FAILED(device->GetVertexShaderConstantF(
                           4,state.originalPbrView,4)) ||
                       FAILED(device->GetVertexShaderConstantF(
                           8,state.originalPbrProjection,4)) ||
                       FAILED(device->GetPixelShaderConstantF(
                           1,state.originalPbrEye,1)))
                        return EyeBuildResult::FatalError;
                    state.externalPbrWorld=true;
                }
				state.fixedFunctionRotationOnly = rotationOnly;
				state.worldStereo = true;
				state.poseSequence = stereo.poseSequence;
				if (rotationOnly)
				{
					++FixedFunctionSkyRotationOnlyDraws;
                    if(Settings::VRQuestCockpitV2SkyProbe &&
                       (FixedFunctionSkyRotationOnlyDraws<=12u ||
                        FixedFunctionSkyRotationOnlyDraws%180u==0u))
                        spdlog::info(
                            "VR SKY COHERENT BASIS: fixedSkyCount={} "
                            "exactWorldSky={} nativePairUsed={} "
                            "poseSequence={} rotationOnly=1",
                            FixedFunctionSkyRotationOnlyDraws,exactWorldSky,
                            fixedNativeEyePair!=nullptr,stereo.poseSequence);
					if (!FirstFixedFunctionSkyRotationLogged)
					{
						FirstFixedFunctionSkyRotationLogged = true;
						spdlog::info(
							"VR SKY ROTATION: exact 4521C0 or depth-off fixed-function sky keeps headset rotation/FOV but removes head/IPD translation");
					}
				}
				else
				{
					++FixedFunctionWorldStereoDraws;
					if (!FirstFixedFunctionWorldLogged)
					{
						FirstFixedFunctionWorldLogged = true;
						spdlog::info(
							"VR FIXEDFN WORLD: depth-tested perspective XYZ receives latched head inverse + eye-local IPD/FOV");
					}
				}
				return EyeBuildResult::WorldStereo;
			}

			float verifiedConstants[16]{};
			std::uint32_t verifiedGeneration = 0, verifiedPoseSequence = 0;
			std::uintptr_t verifiedShaderIdentity = 0;
			std::uint64_t verifiedShaderSerial = 0;
			if (!OutRunVRRenderer::GetLastVerifiedWvp(verifiedConstants, verifiedGeneration, verifiedPoseSequence, verifiedShaderIdentity, verifiedShaderSerial)) return EyeBuildResult::NonWorld;
			std::uintptr_t shaderIdentity = 0; std::uint64_t shaderSerial = 0;
			if (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial)) return EyeBuildResult::FatalError;
			if (verifiedShaderIdentity != shaderIdentity || verifiedShaderSerial != shaderSerial) return EyeBuildResult::NonWorld;
			if (verifiedGeneration == 0 || verifiedPoseSequence != stereo.poseSequence) return EyeBuildResult::FatalError;
			if (FAILED(device->GetVertexShaderConstantF(OutRunWvpRegister, state.originalConstants, OutRunWvpRegisterCount))) return EyeBuildResult::FatalError;
			if (!FloatArrayNear(state.originalConstants, verifiedConstants, 16, VerifiedWvpEpsilon)) return EyeBuildResult::FatalError;
			D3DMATRIX projection{}, invProjection{};
			if (!ReadProjection(projection) || !GetInverseProjection(projection, invProjection)) return EyeBuildResult::FatalError;
			D3DMATRIX uploadedT{}; std::memcpy(&uploadedT, state.originalConstants, sizeof(uploadedT));
			const D3DMATRIX currentWvp = TransposeMatrix(uploadedT);
			const D3DMATRIX correctedWorldView = MultiplyMatrix(currentWvp, invProjection);
			if (!MatrixFinite(correctedWorldView)) return EyeBuildResult::FatalError;
            const auto physicalDraw =
                OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
			const bool exactWorldSky =
                physicalDraw.scope ==
				OutRunVR::GameSemantic::RenderScope::WorldSky;
            bool exactSkyNativeEye[2]{false,false};
            // Exact original 0x4521C0 sky must use one deterministic
            // rotation-only basis for the whole race. Hardware logs showed
            // native-eye availability changing across Presents at race start
            // (and occasionally later), causing the two original sky layers
            // to alternate between native and fallback transforms. The
            // fallback already carries the latched head rotation plus each
            // OpenXR eye orientation with all translation removed, so keep it
            // as the sole exact-sky path. Non-sky programmable world draws
            // still use the Quest native eye pair when available.
            const auto* programmableNativeEyePair=
                exactWorldSky ? nullptr :
                GetQuestNativeEyePairForPresent(stereo.poseSequence);
            const D3DMATRIX* programmableHeadInverse=nullptr;
            if(programmableNativeEyePair || exactWorldSky) {
                programmableHeadInverse=
                    GetQuestHeadInverseForPresent(stereo.poseSequence);
                if(!programmableHeadInverse)
                    return EyeBuildResult::FatalError;
            }
			for (int eye = 0; eye < 2; ++eye)
			{
				const D3DMATRIX eyePose = MatrixFromQuaternionTranslation(stereo.eyeOrientation[eye], stereo.eyeOffset[eye], Settings::VRWorldScale * Settings::VRStereoDepth);
				D3DMATRIX eyeInverse = InverseRigid(eyePose);
                if(programmableNativeEyePair) {
                    if(exactWorldSky)exactSkyNativeEye[eye]=true;
                    D3DMATRIX nativeFullView{};
                    std::memcpy(&nativeFullView,
                                (*programmableNativeEyePair)[eye],
                                sizeof(nativeFullView));
                    if(!MatrixFinite(nativeFullView))
                        return EyeBuildResult::FatalError;
                    // This shader c64 source ALREADY contains the head
                    // inverse. Compensate its head transform before applying
                    // the exact Quest full-eye view, or headset motion would
                    // be applied twice to programmable world passes.
                    // For exact original 4521C0 sky, the replacement target
                    // keeps orientation only: no headset-position parallax
                    // and no per-eye IPD translation. Inverse(headInverse)
                    // still cancels the full transform already baked into c64.
                    if(exactWorldSky) {
                        nativeFullView._41=0.f;
                        nativeFullView._42=0.f;
                        nativeFullView._43=0.f;
                    }
                    eyeInverse=MultiplyMatrix(
                        InverseRigid(*programmableHeadInverse),nativeFullView);
                    if(!MatrixFinite(eyeInverse))
                        return EyeBuildResult::FatalError;
                } else if(exactWorldSky) {
                    D3DMATRIX rotationOnly=*programmableHeadInverse;
                    rotationOnly._41=0.f;
                    rotationOnly._42=0.f;
                    rotationOnly._43=0.f;
                    // Match the fixed-function 4521C0 fallback exactly:
                    // keep each OpenXR eye's orientation/cant, but remove
                    // positional IPD and headset translation. The old shader
                    // fallback omitted local eye orientation entirely, so the
                    // two original sky layers could disagree until the native
                    // Quest eye pair became available.
                    const float skyEyeOffset[3]{0.f,0.f,0.f};
                    const D3DMATRIX skyEyePose=
                        MatrixFromQuaternionTranslation(
                            stereo.eyeOrientation[eye],skyEyeOffset,
                            Settings::VRWorldScale *
                                Settings::VRStereoDepth);
                    const D3DMATRIX skyEyeInverse=InverseRigid(skyEyePose);
                    eyeInverse=MultiplyMatrix(
                        MultiplyMatrix(
                            InverseRigid(*programmableHeadInverse),rotationOnly),
                        skyEyeInverse);
                    if(!MatrixFinite(eyeInverse))
                        return EyeBuildResult::FatalError;
                }
				const D3DMATRIX eyeProjection = ProjectionFromFov(projection, stereo.eyeFov[eye]);
				const D3DMATRIX eyeWvp = MultiplyMatrix(MultiplyMatrix(correctedWorldView, eyeInverse), eyeProjection);
				if (!MatrixFinite(eyeWvp)) return EyeBuildResult::FatalError;
				const D3DMATRIX eyeWvpT = TransposeMatrix(eyeWvp); std::memcpy(state.eyeConstants[eye], &eyeWvpT, sizeof(eyeWvpT));
			}

            if (Settings::VRQuestCockpitV2SkyProbe) {
                if(exactWorldSky) {
                    ++ProgrammableExactWorldSkyDraws;
                    if(exactSkyNativeEye[0]!=exactSkyNativeEye[1]) {
                        ++ProgrammableSkyMixedEyeDraws;
                    } else {
                        const bool native=exactSkyNativeEye[0];
                        if(native)++ProgrammableSkyNativeViewDraws;
                        else ++ProgrammableSkyFallbackViewDraws;
                        if(ProgrammableSkyLastModeKnown &&
                           ProgrammableSkyLastNative!=native)
                            ++ProgrammableSkyViewModeSwitches;
                        ProgrammableSkyLastModeKnown=true;
                        ProgrammableSkyLastNative=native;
                    }
                }
                DWORD depth=D3DZB_TRUE;
                if(ReadTrackedRenderState(device,D3DRS_ZENABLE,depth) &&
                   depth==D3DZB_FALSE) {
                    ++ProgrammableDepthOffWorldDraws;
                    if(!exactWorldSky) {
                        const auto count=++ProgrammableNonSkyDepthOffWorldDraws;
                        if(count<=24u || count%180u==0u)
                            spdlog::info(
                                "VR SKY NONEXACT DEPTH-OFF: count={} "
                                "scope={} producer={} queued={} "
                                "shader=0x{:X} shaderSerial={} "
                                "worldViewT={:.4f},{:.4f},{:.4f} "
                                "projection34={:.4f} projection44={:.4f}",
                                count,
                                static_cast<unsigned>(physicalDraw.scope),
                                static_cast<unsigned>(physicalDraw.producer),
                                physicalDraw.queued,
                                shaderIdentity,shaderSerial,
                                correctedWorldView._41,
                                correctedWorldView._42,
                                correctedWorldView._43,
                                projection._34,projection._44);
                    }
                }
            }
            state.worldStereo = true; state.poseSequence = stereo.poseSequence; return EyeBuildResult::WorldStereo;
		}

		void InvalidateTrackedRenderStates() noexcept
		{
			TrackedRenderStateValid.fill(false);
			TrackedRenderStateReads.fill(0);
		}

		bool ReadTrackedRenderState(IDirect3DDevice9* device,
			D3DRENDERSTATETYPE state, DWORD& out) noexcept
		{
			const auto index = static_cast<std::size_t>(state);
			if (!device || index >= TrackedRenderStateValue.size())
				return false;
			if (TrackedRenderStateValid[index])
			{
				auto& reads = TrackedRenderStateReads[index];
				// R13's effect draw guard reads five tracked states per draw.
				// A proven R22/R31 setter + StateBlock Apply/recording chain
				// invalidates these values at every mutating boundary: repeated
				// 16-draw D3D9 GetRenderState probes are then pure driver churn.
				// Preserve periodic live sampling whenever coverage is lost,
				// recording is underway or an internal eye pass is active.
				const bool trusted = OutRunVR::State::StateBlockTracker::Reliable() &&
					!OutRunVR::State::StateBlockTracker::Recording() &&
					!InternalStereoPass;
				if (trusted || ++reads < 16)
				{
					++TrackedRenderStateCacheHits;
					out = TrackedRenderStateValue[index];
					return true;
				}
				reads = 0;
			}
			DWORD live = 0;
			if (FAILED(device->GetRenderState(state, &live)))
			{
				if (!TrackedRenderStateValid[index])
					return false;
				out = TrackedRenderStateValue[index];
				return true;
			}
			++TrackedRenderStateLiveValidations;
			if (TrackedRenderStateValid[index] &&
				TrackedRenderStateValue[index] != live)
				++TrackedRenderStateMismatches;
			TrackedRenderStateValue[index] = live;
			TrackedRenderStateValid[index] = true;
			out = live;
			return true;
		}

		void PrimeTrackedRenderStates(IDirect3DDevice9* device) noexcept
		{
			InvalidateTrackedRenderStates();
			if (!device) return;
			constexpr D3DRENDERSTATETYPE states[] = {
				D3DRS_ZENABLE, D3DRS_ZWRITEENABLE,
				D3DRS_ALPHABLENDENABLE, D3DRS_ALPHATESTENABLE,
				D3DRS_CULLMODE, D3DRS_COLORWRITEENABLE,
				D3DRS_STENCILENABLE, D3DRS_STENCILWRITEMASK,
				D3DRS_STENCILFAIL, D3DRS_STENCILZFAIL,
				D3DRS_STENCILPASS, D3DRS_TWOSIDEDSTENCILMODE,
				D3DRS_CCW_STENCILFAIL, D3DRS_CCW_STENCILZFAIL,
				D3DRS_CCW_STENCILPASS
			};
			for (const auto state : states)
			{
				const auto index = static_cast<std::size_t>(state);
				DWORD value = 0;
				if (index < TrackedRenderStateValue.size() &&
					SUCCEEDED(device->GetRenderState(state, &value)))
				{
					TrackedRenderStateValue[index] = value;
					TrackedRenderStateValid[index] = true;
				}
			}
		}

		HRESULT __stdcall SetRenderStateDest(IDirect3DDevice9* device,
			D3DRENDERSTATETYPE state, DWORD value)
		{
			const HRESULT hr = SetRenderStateHook.stdcall<HRESULT>(
				device, state, value);
			const auto index = static_cast<std::size_t>(state);
			if (SUCCEEDED(hr) && !InternalStereoPass && IsGameDevice(device) &&
				index < TrackedRenderStateValue.size())
			{
				TrackedRenderStateValue[index] = value;
				TrackedRenderStateValid[index] = true;
				TrackedRenderStateReads[index] = 0;
			}
			return hr;
		}

		bool CurrentDrawMatchesVerifiedWorld(IDirect3DDevice9* device)
		{
			(void)device;
			float verified[16]{}, current[16]{};
			std::uint32_t generation = 0, poseSequence = 0;
			std::uintptr_t verifiedShader = 0, currentShader = 0, writeShader = 0;
			std::uint64_t verifiedSerial = 0, currentSerial = 0;
			std::uint64_t writeSerial = 0, writeDrawSerial = 0, writeShaderSerial = 0;
			if (!OutRunVRRenderer::GetLastVerifiedWvp(
					verified, generation, poseSequence,
					verifiedShader, verifiedSerial) ||
				generation == 0 || poseSequence == 0)
				return false;
			if (!GetCurrentShaderEpoch(currentShader, currentSerial) ||
				currentShader != verifiedShader || currentSerial != verifiedSerial)
				return false;
			if (!OutRunVRRenderer::GetLastGameWvpWrite(
					current, writeSerial, writeDrawSerial,
					writeShader, writeShaderSerial) ||
				writeShader != currentShader || writeShaderSerial != currentSerial)
				return false;
			return FloatArrayNear(current, verified, 16, VerifiedWvpEpsilon);
		}

		bool SetWvpOneRegisterAtATime(IDirect3DDevice9* device, const float* constants)
		{
			for (UINT reg = 0; reg < OutRunWvpRegisterCount; ++reg)
				if (FAILED(device->SetVertexShaderConstantF(OutRunWvpRegister + reg, constants + reg * 4, 1))) return false;
			return true;
		}

		// Upload may stop on failure; rollback must attempt every original register.
		bool RestoreWvpOneRegisterAtATime(IDirect3DDevice9* device, const float* constants)
		{
			return OutRunVR::DinoSidecar::RestoreStereoWvpRegisters(
				OutRunWvpRegisterCount, [&](unsigned reg) {
					return SUCCEEDED(device->SetVertexShaderConstantF(
						OutRunWvpRegister + reg, constants + reg * 4, 1));
				});
		}

        // The PBR VS consumes c4/c8 directly (not D3DTS_VIEW/PROJECTION).
        // Its pixel shader also requires the matching per-eye camera position.
        bool SetExternalPbrEyeConstants(IDirect3DDevice9* device,
            const DrawStereoState& draw,int eye)
        {
            if(!device || !draw.externalPbrWorld || eye<0 || eye>1)
                return false;
            const auto& view=draw.fixedEyeView[eye];
            const auto& projection=draw.fixedEyeProjection[eye];
            float camera[4]{};
            if(!OutRunVR::DinoSidecar::ExternalPbrEyeConstants(
                    &view.m[0][0],draw.originalPbrEye[3],camera))
                return false;
            return SUCCEEDED(device->SetVertexShaderConstantF(
                    4,&view.m[0][0],4)) &&
                SUCCEEDED(device->SetVertexShaderConstantF(
                    8,&projection.m[0][0],4)) &&
                SUCCEEDED(device->SetPixelShaderConstantF(1,camera,1));
        }

        bool RestoreExternalPbrConstants(IDirect3DDevice9* device,
            const DrawStereoState& draw)
        {
            if(!device || !draw.externalPbrWorld)return false;
            // Always attempt all three restorations, even if one fails.
            // A failed restoration quarantines the current external frame.
            const bool viewOk=SUCCEEDED(device->SetVertexShaderConstantF(
                4,draw.originalPbrView,4));
            const bool projOk=SUCCEEDED(device->SetVertexShaderConstantF(
                8,draw.originalPbrProjection,4));
            const bool eyeOk=SUCCEEDED(device->SetPixelShaderConstantF(
                1,draw.originalPbrEye,1));
            return viewOk && projOk && eyeOk;
        }

		bool SetFixedFunctionEyeTransforms(IDirect3DDevice9* device,
			const DrawStereoState& draw, int eye)
		{
			return device && eye >= 0 && eye < 2 &&
				SUCCEEDED(device->SetTransform(
					D3DTS_VIEW, &draw.fixedEyeView[eye])) &&
				SUCCEEDED(device->SetTransform(
					D3DTS_PROJECTION, &draw.fixedEyeProjection[eye]));
		}

		bool RestoreFixedFunctionTransforms(IDirect3DDevice9* device,
			const DrawStereoState& draw)
		{
			if(!device)return false;
			return OutRunVR::DinoSidecar::RestoreExternalStereoTransformPair(
				[&]() { return SUCCEEDED(device->SetTransform(
					D3DTS_VIEW, &draw.fixedOriginalView)); },
				[&]() { return SUCCEEDED(device->SetTransform(
					D3DTS_PROJECTION, &draw.fixedOriginalProjection)); });
		}

		bool FormatHasStencil(D3DFORMAT format)
		{
			switch (format) { case D3DFMT_D15S1: case D3DFMT_D24S8: case D3DFMT_D24X4S4: case D3DFMT_D24FS8: return true; default: return false; }
		}
		bool SurfaceHasStencil(IDirect3DSurface9* surface)
		{
			if (!surface) return false;
			// Every repeated stereo draw shares the tracked depth surface. Skip
			// its COM GetDesc after the first successful format probe only.
			if (surface == TrackedDepthStencil && TrackedStencilFormatKnown)
				return TrackedStencilFormatHasStencil;
			D3DSURFACE_DESC desc{};
			if (FAILED(surface->GetDesc(&desc))) return false;
			const bool hasStencil = FormatHasStencil(desc.Format);
			if (surface == TrackedDepthStencil)
			{
				TrackedStencilFormatHasStencil = hasStencil;
				TrackedStencilFormatKnown = true;
			}
			return hasStencil;
		}
		bool DepthTestActive(IDirect3DDevice9* device) { if (!device || !TrackedDepthStencil) return false; DWORD enabled=D3DZB_TRUE; if (!ReadTrackedRenderState(device,D3DRS_ZENABLE,enabled)) return true; return enabled!=D3DZB_FALSE; }
		bool StencilTestActive(IDirect3DDevice9* device) { if (!device || !SurfaceHasStencil(TrackedDepthStencil)) return false; DWORD enabled=FALSE; if (!ReadTrackedRenderState(device,D3DRS_STENCILENABLE,enabled)) return true; return enabled!=FALSE; }
		bool LeftDrawMayWriteDepth(IDirect3DDevice9* device) { if(!device||!TrackedDepthStencil)return false;DWORD zEnable=D3DZB_TRUE,zWrite=TRUE;if(!ReadTrackedRenderState(device,D3DRS_ZENABLE,zEnable)||!ReadTrackedRenderState(device,D3DRS_ZWRITEENABLE,zWrite))return true;return zEnable!=D3DZB_FALSE&&zWrite!=FALSE; }
		bool LeftDrawMayWriteStencil(IDirect3DDevice9* device)
		{
			if(!device||!SurfaceHasStencil(TrackedDepthStencil))return false;DWORD enabled=FALSE,writeMask=0;if(!ReadTrackedRenderState(device,D3DRS_STENCILENABLE,enabled)||!ReadTrackedRenderState(device,D3DRS_STENCILWRITEMASK,writeMask))return true;if(!enabled||writeMask==0)return false;DWORD fail=D3DSTENCILOP_KEEP,zfail=D3DSTENCILOP_KEEP,pass=D3DSTENCILOP_KEEP;if(!ReadTrackedRenderState(device,D3DRS_STENCILFAIL,fail)||!ReadTrackedRenderState(device,D3DRS_STENCILZFAIL,zfail)||!ReadTrackedRenderState(device,D3DRS_STENCILPASS,pass))return true;if(fail!=D3DSTENCILOP_KEEP||zfail!=D3DSTENCILOP_KEEP||pass!=D3DSTENCILOP_KEEP)return true;DWORD twoSided=FALSE;if(!ReadTrackedRenderState(device,D3DRS_TWOSIDEDSTENCILMODE,twoSided))return true;if(!twoSided)return false;DWORD cFail=D3DSTENCILOP_KEEP,cZFail=D3DSTENCILOP_KEEP,cPass=D3DSTENCILOP_KEEP;if(!ReadTrackedRenderState(device,D3DRS_CCW_STENCILFAIL,cFail)||!ReadTrackedRenderState(device,D3DRS_CCW_STENCILZFAIL,cZFail)||!ReadTrackedRenderState(device,D3DRS_CCW_STENCILPASS,cPass))return true;return cFail!=D3DSTENCILOP_KEEP||cZFail!=D3DSTENCILOP_KEEP||cPass!=D3DSTENCILOP_KEEP;
		}
		void InvalidateRightDepthStencilIfLeftMayWrite(IDirect3DDevice9* device) { if(RightDepthSynchronized&&LeftDrawMayWriteDepth(device))RightDepthSynchronized=false;if(RightStencilSynchronized&&LeftDrawMayWriteStencil(device))RightStencilSynchronized=false; }
        // A recent full clear can be replayed only until the next potential
        // LEFT depth/stencil write. Keep the no-receipt hot path free of
        // render-state probes. Internal RIGHT replay must not revoke LEFT.
        void RevokeDepthClearReplayBeforeLeftDraw(IDirect3DDevice9* device,
            bool mirrorCandidate=false)
        {
            // R29 raw wrappers also enter here, including internal routes.
            // Any unmirrored physical draw may change color or depth.
            if(ExternalAtomicReplayEpoch && !mirrorCandidate && IsGameDevice(device))
                ExternalAtomicReplayEpoch=0;
            if(InternalStereoPass || !LastMainDepthClearStamp.Current(PresentEpoch) ||
                !IsGameDevice(device))return;
            DWORD writes=0;
            if((LastMainDepthClearStamp.flags&D3DCLEAR_ZBUFFER) &&
                LeftDrawMayWriteDepth(device))writes|=D3DCLEAR_ZBUFFER;
            if((LastMainDepthClearStamp.flags&D3DCLEAR_STENCIL) &&
                LeftDrawMayWriteStencil(device))writes|=D3DCLEAR_STENCIL;
            LastMainDepthClearStamp.OnPotentialWrite(writes);
        }
        // Direct stock fallbacks bypass the R7 detour. Retire the inactive
        // pair before the physical write, even on a failed driver call.
        template<class Call>
        HRESULT R7ExecuteUnmirroredGameRaster(IDirect3DDevice9* device,
            Call&& call,bool clear=false,DWORD flags=0) noexcept
        {
            if(IsGameDevice(device)){
                if(clear){
                    ExternalAtomicReplayEpoch=0;
                    LastMainDepthClearStamp.OnPotentialWrite(flags&(D3DCLEAR_ZBUFFER|D3DCLEAR_STENCIL));
                }else{
                    RevokeDepthClearReplayBeforeLeftDraw(device);
                }
            }
            return call();
        }
		bool ViewportCoversStereoBackbuffer(IDirect3DDevice9* device) { if(!device||!BackBufferDesc.Width||!BackBufferDesc.Height)return false;D3DVIEWPORT9 viewport{};if(FAILED(device->GetViewport(&viewport)))return false;return viewport.X==0&&viewport.Y==0&&viewport.Width==BackBufferDesc.Width&&viewport.Height==BackBufferDesc.Height; }
		bool ClearCoversStereoBackbuffer(IDirect3DDevice9* device,DWORD count,const D3DRECT* rects)
		{
			if(!ViewportCoversStereoBackbuffer(device))return false;
			if(count==0)return true;
			if(!rects)return false;
			for(DWORD i=0;i<count;++i)
			{
				const auto&r=rects[i];
				if(r.x1<=0&&r.y1<=0&&r.x2>=static_cast<LONG>(BackBufferDesc.Width)&&r.y2>=static_cast<LONG>(BackBufferDesc.Height))return true;
			}
			// Review 01514: a full depth/stencil clear split into exactly
			// two contiguous full-height or full-width bands is still
			// whole-surface. Avoid an unbounded/general rectangle-union
			// algorithm on the 120-Hz Draw/Clear path; reject other tilings.
			if(count==2)
			{
				const auto&a=rects[0],&c=rects[1];
				const LONG width=static_cast<LONG>(BackBufferDesc.Width);
				const LONG height=static_cast<LONG>(BackBufferDesc.Height);
				const bool validA=a.x2>a.x1&&a.y2>a.y1;
				const bool validC=c.x2>c.x1&&c.y2>c.y1;
				if(validA&&validC)
				{
					const bool fullHeight=a.y1<=0&&c.y1<=0&&
						a.y2>=height&&c.y2>=height;
					const bool fullWidth=a.x1<=0&&c.x1<=0&&
						a.x2>=width&&c.x2>=width;
					if(fullHeight&&
						((a.x1<=0&&c.x2>=width&&a.x2>=c.x1)||
						 (c.x1<=0&&a.x2>=width&&c.x2>=a.x1)))return true;
					if(fullWidth&&
						((a.y1<=0&&c.y2>=height&&a.y2>=c.y1)||
						 (c.y1<=0&&a.y2>=height&&c.y2>=a.y1)))return true;
				}
			}
			return false;
		}
		bool DepthDescMatches(const D3DSURFACE_DESC&a,const D3DSURFACE_DESC&b)
		{
			return a.Width==b.Width&&a.Height==b.Height&&a.Format==b.Format&&a.MultiSampleType==b.MultiSampleType&&a.MultiSampleQuality==b.MultiSampleQuality;
		}
		void RecordFullMainDepthClear(IDirect3DDevice9*device,DWORD count,const D3DRECT*rects,DWORD flags,float z,DWORD stencil)
		{
			const DWORD depthFlags=flags&(D3DCLEAR_ZBUFFER|D3DCLEAR_STENCIL);
			if(!depthFlags||!TargetIsBackBuffer()||!TrackedDepthStencil||!ClearCoversStereoBackbuffer(device,count,rects))return;
			D3DSURFACE_DESC desc{};if(FAILED(TrackedDepthStencil->GetDesc(&desc)))return;
			LastMainDepthClearStamp.Record(PresentEpoch,depthFlags);LastMainDepthClearZ=z;LastMainDepthClearStencil=stencil;LastMainDepthClearDesc=desc;++FullMainDepthClears;
			if(!FirstMainClearLogged){FirstMainClearLogged=true;spdlog::info("VR stereo: full main depth clear observed count={} flags=0x{:x} z={} stencil={} epoch={}",count,static_cast<unsigned>(depthFlags),z,stencil,PresentEpoch);}
		}

		void RetireDirectInteropProbePublication() noexcept
		{
			if(SharedState&&SharedState->magic==OutRunVR::SharedMagic){InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeToken),0);InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeHandle),0);}
		}

		void ReleaseDirectInteropProbe() noexcept
		{
			RetireDirectInteropProbePublication();
			ReleaseCom(DirectInteropProbeFence);ReleaseCom(DirectInteropProbeSurface);ReleaseCom(DirectInteropProbeTexture);DirectInteropProbeHandle=nullptr;DirectInteropProbeToken=0;DirectInteropVerified=false;
		}

		void ReleaseDirectTransportSlotObjects() noexcept
		{
			for(auto&slot:DirectTransportSlots){ReleaseCom(slot.fence);ReleaseCom(slot.leftSurface);ReleaseCom(slot.leftTexture);ReleaseCom(slot.rightSurface);ReleaseCom(slot.rightTexture);slot={};}
		}

		void RetireDirectTransportFramePublications() noexcept
		{
			if(!RenderFrameRing||!RenderFrameRingClaimed||
				RenderFrameRing->clientPid!=GetCurrentProcessId()||
				RenderFrameRing->reserved0!=RenderFrameRunGeneration)return;

			LONG ringSeq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			if((ringSeq&1)==0)ringSeq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			MemoryBarrier();
			for(auto&frame:RenderFrameRing->slots)
			{
				LONG seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));
				if((seq&1)==0)seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));
				MemoryBarrier();
				if(frame.reserved[OutRunVR::RenderFrameRunGenerationIndex]==RenderFrameRunGeneration&&
					(frame.flags&OutRunVR::RenderFrameDirectGpuTransport)!=0)
				{
					frame.frameId=0;
					frame.flags&=~OutRunVR::RenderFrameDirectGpuTransport;
					frame.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectRightHandleIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectWidthIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectHeightIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectFormatIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex]=0;
					frame.reserved[OutRunVR::RenderFrameDirectSlotIndex]=0;
				}
				MemoryBarrier();
				seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));
				if(seq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));
			}
			MemoryBarrier();
			ringSeq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
			if(ringSeq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
		}


        // D3D9 Discard surfaces lose contents when unbound, even if the
        // exact pointer is restored. Descriptors do not expose Discard.
        // Record provenance on the COM resource itself, not a recyclable
        // pointer in a process-lifetime map. Zero is explicit non-discard;
        // automatic depth proof is scoped to the Create/Reset generation.
        constexpr GUID R7DepthRetentionGuid{0x04e376c5,0x69df,0x43ad,{0xa0,0xd2,0x73,0x18,0x7e,0x11,0x75,0x9b}};
        std::uint64_t R7AutomaticDepthGeneration=1;
        void R7ForgetAutomaticDepthProof() noexcept
        {
            if(++R7AutomaticDepthGeneration==0)++R7AutomaticDepthGeneration;
        }
        void R7MarkDepthRetention(IDirect3DSurface9* surface,std::uint64_t proof) noexcept
        {
            if(surface)surface->SetPrivateData(R7DepthRetentionGuid,&proof,
                static_cast<DWORD>(sizeof(proof)),0);
        }
        bool R7ReadDepthRetention(IDirect3DSurface9* surface,std::uint64_t& proof) noexcept
        {
            DWORD size=static_cast<DWORD>(sizeof(proof));
            return surface&&SUCCEEDED(surface->GetPrivateData(R7DepthRetentionGuid,&proof,&size))&&
                size==sizeof(proof);
        }
        bool R7DepthRetentionProven(IDirect3DSurface9* surface) noexcept
        {
            std::uint64_t proof=0;
            return R7ReadDepthRetention(surface,proof)&&
                (proof==0||proof==R7AutomaticDepthGeneration);
        }
        // A fresh classic Create/Reset can establish automatic identity.
        // ResetEx preserves state/resources, so only an existing resource tag
        // from the preceding generation can prove retained automatic depth.
        // Never certify an arbitrary post-ResetEx binding from PP alone.
        void R7CaptureAutomaticDepth(IDirect3DDevice9* device,std::uint64_t previous) noexcept
        {
            const auto generation=R7AutomaticDepthGeneration;
            if(!device||device->GetNumberOfSwapChains()!=1||previous==generation)return;
            IDirect3DSwapChain9* chain=nullptr;
            D3DPRESENT_PARAMETERS pp{};
            const bool safe=SUCCEEDED(device->GetSwapChain(0,&chain))&&chain&&
                SUCCEEDED(chain->GetPresentParameters(&pp))&&pp.EnableAutoDepthStencil&&
                !(pp.Flags&D3DPRESENTFLAG_DISCARD_DEPTHSTENCIL);
            ReleaseCom(chain);
            if(!safe||R7AutomaticDepthGeneration!=generation)return;
            IDirect3DSurface9* depth=nullptr;
            if(SUCCEEDED(device->GetDepthStencilSurface(&depth))&&depth){
                std::uint64_t tag=0;
                const bool retained=!previous||(R7ReadDepthRetention(depth,tag)&&tag==previous);
                if(retained&&R7AutomaticDepthGeneration==generation)
                    R7MarkDepthRetention(depth,generation);
            }
            ReleaseCom(depth);
        }
        void R7CaptureFreshAutomaticDepth(IDirect3DDevice9* device) noexcept
        {
            R7CaptureAutomaticDepth(device,0);
        }
        void R7RevalidateRetainedAutomaticDepth(IDirect3DDevice9* device,std::uint64_t previous) noexcept
        {
            if(previous)R7CaptureAutomaticDepth(device,previous);
        }
        // Base and Ex creation can delegate to each other inside the driver.
        // Only the outer API contract may prove retention; never let a nested
        // FALSE call mark a surface returned by an outer discard/failure call.
        thread_local unsigned R7DepthCreationNesting=0;
        struct R7DepthCreationScope {
            bool outer;
            R7DepthCreationScope() noexcept:outer(R7DepthCreationNesting++==0){}
            ~R7DepthCreationScope(){--R7DepthCreationNesting;}
        };
        HRESULT __stdcall CreateDepthRetentionDest(IDirect3DDevice9* device,
            UINT width,UINT height,D3DFORMAT format,D3DMULTISAMPLE_TYPE samples,
            DWORD quality,BOOL discard,IDirect3DSurface9** out,HANDLE* shared)
        {
            R7DepthCreationScope scope;
            const HRESULT hr=CreateDepthRetentionHook.stdcall<HRESULT>(device,
                width,height,format,samples,quality,discard,out,shared);
            if(scope.outer&&SUCCEEDED(hr)&&!discard&&!shared&&out&&*out&&
                StereoBaseCallbacksArmed.load(std::memory_order_acquire)&&IsGameDevice(device))
                R7MarkDepthRetention(*out,0);
            return hr;
        }
        HRESULT __stdcall CreateDepthRetentionExDest(IDirect3DDevice9Ex* device,
            UINT width,UINT height,D3DFORMAT format,D3DMULTISAMPLE_TYPE samples,
            DWORD quality,BOOL discard,IDirect3DSurface9** out,HANDLE* shared,DWORD usage)
        {
            R7DepthCreationScope scope;
            const HRESULT hr=CreateDepthRetentionExHook.stdcall<HRESULT>(device,
                width,height,format,samples,quality,discard,out,shared,usage);
            if(scope.outer&&SUCCEEDED(hr)&&!discard&&!shared&&out&&*out&&
                StereoBaseCallbacksArmed.load(std::memory_order_acquire)&&IsGameDevice(device))
                R7MarkDepthRetention(*out,0);
            return hr;
        }

        // EXT16-011 A1: an inactive, renderer-owned pair. Allocation never
        // binds, clears, copies or publishes a live eye. Depth contents are
        // deliberately undefined until a future scene replay seeds them.
        struct R7AtomicCandidatePair
        {
            struct Eye {
                IDirect3DSurface9* color=nullptr;
                IDirect3DSurface9* depth=nullptr;
            };
            Eye eyes[2]{};
            // Both attachments belong to the same eye/epoch. A matching depth
            // alone cannot identify a color target with equivalent scene pixels.
            IDirect3DSurface9* provenLiveColor[2]{};
            IDirect3DSurface9* provenLiveDepth[2]{}; // borrowed from tracked live owners, same replay epoch only
            IDirect3DDevice9* device=nullptr; // non-owning; Reset retires pair
            D3DSURFACE_DESC colorDesc{},depthDesc{};
            UINT simultaneousTargets=0;
            std::uint64_t generation=1;
            R7AtomicCandidatePair()=default;
            R7AtomicCandidatePair(const R7AtomicCandidatePair&)=delete;
            R7AtomicCandidatePair& operator=(const R7AtomicCandidatePair&)=delete;
            ~R7AtomicCandidatePair(){ Reset(); }
            void Reset() noexcept {
                for(auto& eye:eyes){ReleaseCom(eye.depth);ReleaseCom(eye.color);}
                device=nullptr;colorDesc={};depthDesc={};simultaneousTargets=0;
                provenLiveColor[0]=provenLiveColor[1]=nullptr;
                provenLiveDepth[0]=provenLiveDepth[1]=nullptr;
                if(++generation==0)++generation;
            }
            static bool Same(const D3DSURFACE_DESC& a,const D3DSURFACE_DESC& b) noexcept {
                return a.Width==b.Width && a.Height==b.Height && a.Format==b.Format &&
                    a.MultiSampleType==b.MultiSampleType &&
                    a.MultiSampleQuality==b.MultiSampleQuality;
            }
            bool Ensure(IDirect3DDevice9* d,IDirect3DSurface9* lc,IDirect3DSurface9* ld,
                IDirect3DSurface9* rc,IDirect3DSurface9* rd,const D3DVIEWPORT9& vp) noexcept {
                if(device && device!=d)Reset();
                // A driver call can synchronously retire this pair (ResetEx).
                // Stop before dereferencing the next borrowed live attachment.
                const auto descriptorGeneration=generation;
                D3DSURFACE_DESC c{},z{},otherC{},otherZ{};
                if(!d||!lc||!ld||!rc||!rd||lc==rc||ld==rd||
                    FAILED(lc->GetDesc(&c))||generation!=descriptorGeneration||
                    FAILED(ld->GetDesc(&z))||generation!=descriptorGeneration||
                    FAILED(rc->GetDesc(&otherC))||generation!=descriptorGeneration||
                    FAILED(rd->GetDesc(&otherZ))||generation!=descriptorGeneration||
                    !Same(c,otherC)||!Same(z,otherZ)||!c.Width||!c.Height||
                    z.Width<c.Width||z.Height<c.Height||
                    c.MultiSampleType!=z.MultiSampleType||
                    c.MultiSampleQuality!=z.MultiSampleQuality||
                    !vp.Width||!vp.Height||vp.X>=c.Width||vp.Y>=c.Height||
                    vp.Width>c.Width-vp.X||vp.Height>c.Height-vp.Y) {
                    // Do not retire resources owned by a newer transaction.
                    if(generation==descriptorGeneration)Reset();
                    return false;
                }
                if(device==d && Same(colorDesc,c)&&Same(depthDesc,z)&&
                    eyes[0].color&&eyes[0].depth&&eyes[1].color&&eyes[1].depth)return true;
                Reset();
                const auto allocationGeneration=generation;
                // Cache the immutable device limit with the allocation.
                // Unknown/unsupported caps cannot establish RT isolation.
                D3DCAPS9 caps{};
                if(FAILED(d->GetDeviceCaps(&caps))||generation!=allocationGeneration||
                    !caps.NumSimultaneousRTs||caps.NumSimultaneousRTs>4)return false;
                R7AtomicCandidatePair pending;
                for(auto& eye:pending.eyes){
                    if(FAILED(d->CreateRenderTarget(c.Width,c.Height,c.Format,
                        c.MultiSampleType,c.MultiSampleQuality,FALSE,&eye.color,nullptr))||
                        !eye.color||generation!=allocationGeneration||
                        FAILED(d->CreateDepthStencilSurface(z.Width,z.Height,z.Format,
                        z.MultiSampleType,z.MultiSampleQuality,FALSE,&eye.depth,nullptr))||
                        !eye.depth||generation!=allocationGeneration)return false;
                    D3DSURFACE_DESC actualC{},actualZ{};
                    if(FAILED(eye.color->GetDesc(&actualC))||generation!=allocationGeneration||
                        FAILED(eye.depth->GetDesc(&actualZ))||generation!=allocationGeneration||
                        !Same(c,actualC)||!Same(z,actualZ))return false;
                }
                // A reset during a successful allocation must not repopulate
                // the retired cache with pre-reset resources. Pending owns all
                // partial allocations and releases them on every failure.
                if(generation!=allocationGeneration)return false;
                for(unsigned i=0;i<2;++i){
                    eyes[i]=pending.eyes[i];pending.eyes[i]={};
                }
                device=d;colorDesc=c;depthDesc=z;simultaneousTargets=caps.NumSimultaneousRTs;
                return true; // allocated only; never a raster/publication proof
            }
        };
        R7AtomicCandidatePair ExternalAtomicCandidates{};
        std::uint64_t ExternalAtomicAllocationAttemptEpoch=0;
        // Physical presentation may not advance the stock PresentEpoch.
        std::uint64_t R7CandidateBoundarySerial=0;

        // Resolve the implicit chain's actual Present entrypoint each seed.
        // Reset can replace the chain. Never assume a cached COM pointer or
        // a different implementation is covered by an existing inline hook.
        void* R7GetImplicitChainPresentTarget(IDirect3DDevice9* device) noexcept
        {
            if(!device||device->GetNumberOfSwapChains()!=1)return nullptr;
            IDirect3DSwapChain9* chain=nullptr;
            void* target=nullptr;
            if(SUCCEEDED(device->GetSwapChain(0,&chain))&&chain){
                void** table=*reinterpret_cast<void***>(chain);
                target=table?table[SwapChainPresentVtableIndex]:nullptr;
                for(unsigned slot=0;target&&slot<10;++slot)
                    if(slot!=SwapChainPresentVtableIndex&&target==table[slot])target=nullptr;
                // Ex exposes the inherited Present on its own interface.
                // A distinct target or ambiguous QI must not escape coverage.
                IDirect3DSwapChain9Ex* ex=nullptr;
                const HRESULT qi=chain->QueryInterface(__uuidof(IDirect3DSwapChain9Ex),
                    reinterpret_cast<void**>(&ex));
                if(SUCCEEDED(qi)&&ex){
                    void** exTable=*reinterpret_cast<void***>(ex);
                    if(!exTable||exTable[SwapChainPresentVtableIndex]!=target)target=nullptr;
                    for(unsigned slot=0;target&&slot<13;++slot)
                        if(slot!=SwapChainPresentVtableIndex&&target==exTable[slot])target=nullptr;
                }else if(qi!=E_NOINTERFACE||ex)target=nullptr;
                ReleaseCom(ex);
            }
            ReleaseCom(chain);
            return target;
        }

        bool R7CandidateSwapChainCovered(IDirect3DDevice9* device) noexcept
        {
            return !R7CandidateAdditionalChainSeen&&R7CandidateSwapChainPresentTarget&&
                R7GetImplicitChainPresentTarget(device)==R7CandidateSwapChainPresentTarget;
        }

        // An additional chain may have an entirely different vtable.
        // Retire the current receipt before the driver can create it; once
        // one has been exposed, keep candidate staging disabled for this
        // device lifetime until a multi-chain owner is implemented.
        HRESULT __stdcall R7CandidateAdditionalSwapChainDest(IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params,IDirect3DSwapChain9** out)
        {
            if(StereoBaseCallbacksArmed.load(std::memory_order_acquire)&&IsGameDevice(device)){
                ++R7CandidateBoundarySerial;
                ExternalAtomicReplayEpoch=0;
                ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
                R7CandidateAdditionalChainSeen=true;
            }
            return CandidateAdditionalSwapChainHook.stdcall<HRESULT>(device,params,out);
        }

        // Device Present may delegate here, or the game may call the chain
        // directly. Do not notify the host or advance the stock epoch twice.
        HRESULT __stdcall R7CandidateSwapChainPresentDest(IDirect3DSwapChain9* chain,
            const RECT* sourceRect,const RECT* destRect,HWND window,
            const RGNDATA* dirty,DWORD flags)
        {
            if(StereoBaseCallbacksArmed.load(std::memory_order_acquire)){
                IDirect3DDevice9* owner=nullptr;
                const bool known=chain&&SUCCEEDED(chain->GetDevice(&owner))&&owner;
                if(!known||IsGameDevice(owner)){
                    ++R7CandidateBoundarySerial;
                    ExternalAtomicReplayEpoch=0;
                    ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
                }
                ReleaseCom(owner);
            }
            return CandidateSwapChainPresentHook.stdcall<HRESULT>(chain,sourceRect,destRect,
                window,dirty,flags);
        }

        void ReleaseStereoResources();
        void R9RetireDirectResetResources() noexcept;

        // Both classic Reset owners may physically enter ResetEx. Keep the
        // host's reset event single-owner for the entire synchronous call.
        thread_local unsigned R7ResetNotificationDepth=0;
        struct R7ResetNotificationScope
        {
            const bool outermost;
            bool notified=false;
            R7ResetNotificationScope() noexcept
                : outermost(R7ResetNotificationDepth++==0) {}
            ~R7ResetNotificationScope(){--R7ResetNotificationDepth;}
            R7ResetNotificationScope(const R7ResetNotificationScope&)=delete;
            R7ResetNotificationScope& operator=(const R7ResetNotificationScope&)=delete;
            void Notify()
            {
                if(outermost&&!notified){
                    notified=true;
                    OutRunVRRenderer::NotifyGameReset();
                }
            }
        };
        void R7RetireDirectResetFrameIdentity();

        // R13's normal reset path retires core attachments before calling
        // ResetEx. A direct call can still reach the driver with the old
        // backbuffer, right eye and shared transport generation retained.
        // Release these before the physical reset; next verified frame must
        // initialize against the actual post-reset attachments, not the cache.
        bool R7RetireDirectResetCore() noexcept
        {
            const bool hasCore=StereoResourcesReady||BackBuffer||TrackedRenderTarget||
                TrackedDepthStencil||RightEyeSurface||RightEyeDepth||
                LeftResolveSurface||RightResolveSurface||DirectTransportResourcesReady;
            if(!hasCore)return false;
            ReleaseStereoResources();
            InvalidateTrackedRenderStates();
            FrameHadDuplicatedDraw=false;
            FrameHadWorldStereo=false;
            FrameStereoPoseSequence=0;
            FrameStereoMetadata={};
            PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);
            return true;
        }

        // Direct ResetEx bypasses the classic Reset/R13 resource retirement.
        // Retire any still-owned R7 core attachments as well as inactive
        // candidates. The layered classic owners keep their own lifecycle.
        HRESULT __stdcall R7CandidateResetExDest(IDirect3DDevice9Ex* device,
            D3DPRESENT_PARAMETERS* params,D3DDISPLAYMODEEX* fullscreen)
        {
            if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)||!IsGameDevice(device))
                return CandidateResetExHook.stdcall<HRESULT>(device,params,fullscreen);
            ++R7CandidateResetInFlight;
            R7ResetNotificationScope notification;
            const auto previousDepthGeneration=R7AutomaticDepthGeneration;
            // R33 is a separate translation unit in the normal R84 build.
            // Invalidate its borrowed raster/depth caches on both sides of
            // the physical call; callbacks during ResetEx may refill them.
            const auto retireRaster=R7DirectResetRasterOwner.load(std::memory_order_acquire);
            if(retireRaster)retireRaster();
            const auto lifecycle=R7DirectResetLifecycleOwner.load(std::memory_order_acquire);
            if(lifecycle)lifecycle(true,D3D_OK);
            ExternalAtomicReplayEpoch=0;
            ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
            R7ForgetAutomaticDepthProof();
            // R9 holds independent COM references even if R7 has no core.
            R9RetireDirectResetResources();
            // Close the upper baseline before the driver can replace attachments.
            if(const auto retire=R7DirectResetBaselineOwner.load(std::memory_order_acquire))
                retire();
            // The installed R13 overlay owns its ACK mapping independently.
            if(const auto retire=R7DirectResetTransportOwner.load(std::memory_order_acquire))
                retire();
            if(!R7RetireDirectResetCore())ExternalAtomicCandidates.Reset();
            // The classic owners already retired the host/frame identity.
            // Direct ResetEx must do the same even with no core resources.
            if(notification.outermost){
                notification.Notify();
                R7RetireDirectResetFrameIdentity();
            }
            // ReleaseStereoResources also clears the allocation attempt epoch.
            ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
            const HRESULT hr=CandidateResetExHook.stdcall<HRESULT>(device,params,fullscreen);
            // A nested classic owner can reset the epoch and re-capture an
            // automatic surface. ResetEx does not prove fresh depth identity.
            ExternalAtomicReplayEpoch=0;
            ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
            R7ForgetAutomaticDepthProof();
            if(retireRaster)retireRaster();
            if(lifecycle)lifecycle(false,hr);
            if(notification.outermost&&SUCCEEDED(hr))
                R7RevalidateRetainedAutomaticDepth(device,previousDepthGeneration);
            --R7CandidateResetInFlight;
            return hr;
        }

        // Direct PresentEx can bypass the R7/R9 Present epoch owner.
        // Retire the candidate BEFORE the driver sees the present, even on
        // failure, and do not create another candidate in that same epoch.
        // Do not advance the stock epoch or notify the host a second time:
        // base Present may itself call PresentEx.
        HRESULT __stdcall R7CandidatePresentExDest(IDirect3DDevice9Ex* device,
            const RECT* sourceRect,const RECT* destRect,HWND window,
            const RGNDATA* dirty,DWORD flags)
        {
            if(StereoBaseCallbacksArmed.load(std::memory_order_acquire)&&IsGameDevice(device)){
                ++R7CandidateBoundarySerial;
                ExternalAtomicReplayEpoch=0;
                ExternalAtomicAllocationAttemptEpoch=PresentEpoch;
            }
            return CandidatePresentExHook.stdcall<HRESULT>(device,sourceRect,destRect,
                window,dirty,flags);
        }


        enum class R7CandidateSeedResult { Unavailable, Seeded, DirtyRestore };

        // Capture actual attachments, not just the hook's shadow. No clear
        // until all candidate attachment setters succeed.
        template<class BindColor,class BindDepth,class ClearEye>
        R7CandidateSeedResult R7SeedInactivePair(R7AtomicCandidatePair& pair,
            IDirect3DDevice9* d,IDirect3DSurface9* expectedRt,
            IDirect3DSurface9* expectedDepth,BindColor bindColor,
            BindDepth bindDepth,ClearEye clearEye,unsigned firstEye=0,unsigned eyeCount=2,
            bool requireFullViewport=true) noexcept
        {
            if(firstEye>=2||!eyeCount||eyeCount>2-firstEye||
                !d||pair.device!=d||!expectedRt||!expectedDepth||
                !pair.eyes[0].color||!pair.eyes[0].depth||
                !pair.eyes[1].color||!pair.eyes[1].depth)
                return R7CandidateSeedResult::Unavailable;
            const auto generation=pair.generation;
            const auto boundary=R7CandidateBoundarySerial;
            auto current=[&](){return pair.generation==generation&&pair.device==d;};
            auto rasterCurrent=[&](){return current()&&R7CandidateBoundarySerial==boundary;};
            IDirect3DSurface9* rt=nullptr;
            IDirect3DSurface9* depth=nullptr;
            D3DVIEWPORT9 viewport{};
            RECT scissor{};
            const bool captured=SUCCEEDED(d->GetRenderTarget(0,&rt))&&rt==expectedRt&&
                SUCCEEDED(d->GetDepthStencilSurface(&depth))&&depth==expectedDepth&&
                SUCCEEDED(d->GetViewport(&viewport))&&SUCCEEDED(d->GetScissorRect(&scissor))&&
                viewport.Width&&viewport.Height&&viewport.X<pair.colorDesc.Width&&
                viewport.Y<pair.colorDesc.Height&&
                viewport.Width<=pair.colorDesc.Width-viewport.X&&
                viewport.Height<=pair.colorDesc.Height-viewport.Y&&
                (!requireFullViewport||(viewport.X==0&&viewport.Y==0&&
                 viewport.Width==pair.colorDesc.Width&&viewport.Height==pair.colorDesc.Height));
            if(!captured){ReleaseCom(depth);ReleaseCom(rt);return R7CandidateSeedResult::Unavailable;}
            // The shadow MRT flags are not a physical binding proof. Leaving
            // any auxiliary target attached would let the replay write into
            // the live scene, even though RT0 and depth are private.
            bool isolated=pair.simultaneousTargets>=1&&pair.simultaneousTargets<=4;
            for(UINT slot=1;isolated&&slot<pair.simultaneousTargets;++slot){
                IDirect3DSurface9* aux=nullptr;
                const HRESULT hr=d->GetRenderTarget(slot,&aux);
                isolated=!aux&&(SUCCEEDED(hr)||hr==D3DERR_NOTFOUND);
                ReleaseCom(aux);
            }
            if(!isolated||!rasterCurrent()){ReleaseCom(depth);ReleaseCom(rt);return R7CandidateSeedResult::Unavailable;}
            bool seeded=true;
            for(unsigned i=firstEye;i<firstEye+eyeCount;++i){
                const auto& eye=pair.eyes[i];
                if(!rasterCurrent()||FAILED(bindDepth(nullptr))||!rasterCurrent()||
                    FAILED(bindColor(eye.color))||!rasterCurrent()||
                    FAILED(bindDepth(eye.depth))||!rasterCurrent()||
                    FAILED(d->SetViewport(&viewport))||!rasterCurrent()||
                    FAILED(d->SetScissorRect(&scissor))||!rasterCurrent()||FAILED(clearEye())||!rasterCurrent()){
                    seeded=false;break;
                }
            }
            // Never short-circuit recovery, including after a failed setter.
            bool restored=true;
            // A reset/retirement invalidates saved attachment ownership.
            // Do not bind old-generation objects into a replacement device.
            if(!current()||FAILED(bindDepth(nullptr)))restored=false;
            if(!current()||FAILED(bindColor(rt)))restored=false;
            if(!current()||FAILED(bindDepth(depth)))restored=false;
            if(!current()||FAILED(d->SetViewport(&viewport)))restored=false;
            if(!current()||FAILED(d->SetScissorRect(&scissor)))restored=false;
            if(!current())restored=false;
            ReleaseCom(depth);ReleaseCom(rt);
            if(!restored)return R7CandidateSeedResult::DirtyRestore;
            return seeded?R7CandidateSeedResult::Seeded:R7CandidateSeedResult::Unavailable;
        }

        // A successful seed is ONLY the initial clear, not the current scene
        // depth or a publication receipt. Later world draws must be replayed.
        R7CandidateSeedResult R7BeginExternalAtomicResourceTransaction(IDirect3DDevice9* device,
            const D3DVIEWPORT9& viewport,DWORD flags,D3DCOLOR color,float z,DWORD stencil) noexcept
        {
            if(!R7CandidatePresentBoundaryCovered||!R7CandidateResetBoundaryCovered||
                R7CandidateResetInFlight||ExternalAtomicAllocationAttemptEpoch==PresentEpoch)return R7CandidateSeedResult::Unavailable;
            const auto epoch=PresentEpoch;
            const auto boundary=R7CandidateBoundarySerial;
            ExternalAtomicAllocationAttemptEpoch=epoch;
            if(!R7CandidateSwapChainCovered(device))return R7CandidateSeedResult::Unavailable;
            // RightEyeDepth is exclusively created by R7 with Discard=FALSE.
            // For game-owned LEFT depth, no unbind without creation proof.
            auto* const lc=TrackedRenderTarget;
            auto* const ld=TrackedDepthStencil;
            auto* const rc=RightEyeSurface;
            auto* const rd=RightEyeDepth;
            if(!R7DepthRetentionProven(ld)||R7CandidateBoundarySerial!=boundary||PresentEpoch!=epoch)
                return R7CandidateSeedResult::Unavailable;
            if(!ExternalAtomicCandidates.Ensure(device,lc,ld,rc,rd,viewport))
                return R7CandidateSeedResult::Unavailable;
            if(FormatHasStencil(ExternalAtomicCandidates.depthDesc.Format)&&
                !(flags&D3DCLEAR_STENCIL))return R7CandidateSeedResult::Unavailable;
            // Recheck ownership after allocation: it can call into the driver.
            auto current=[&](){return PresentEpoch==epoch&&!R7CandidateResetInFlight&&
                TrackedRenderTarget==lc&&TrackedDepthStencil==ld&&
                RightEyeSurface==rc&&RightEyeDepth==rd&&R7DepthRetentionProven(ld)&&
                R7CandidateBoundarySerial==boundary&&PresentEpoch==epoch;};
            if(!current())return R7CandidateSeedResult::Unavailable;
            const auto generation=ExternalAtomicCandidates.generation;
            InternalPassScope guard;
            const auto result=R7SeedInactivePair(ExternalAtomicCandidates,device,
                lc,ld,
                [&](IDirect3DSurface9* s){return SetRenderTargetHook.stdcall<HRESULT>(device,0u,s);},
                [&](IDirect3DSurface9* s){return SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,s);},
                [&](){return ClearHook.stdcall<HRESULT>(device,0u,static_cast<const D3DRECT*>(nullptr),flags,color,z,stencil);});
            if(result==R7CandidateSeedResult::Seeded){
                if(ExternalAtomicCandidates.generation!=generation||!current()){
                    ExternalAtomicReplayEpoch=0;
                    return R7CandidateSeedResult::Unavailable;
                }
                ExternalAtomicCandidates.provenLiveColor[0]=lc;
                ExternalAtomicCandidates.provenLiveColor[1]=rc;
                ExternalAtomicCandidates.provenLiveDepth[0]=ld;
                ExternalAtomicCandidates.provenLiveDepth[1]=rd;
                ExternalAtomicReplayEpoch=epoch;
            }
            if(result==R7CandidateSeedResult::DirtyRestore)ExternalAtomicCandidates.Reset();
            return result;
        }

        // Replay one physical draw while its exact eye transforms and shaders are bound.
        // UP callers must isolate input state via R7ReplayInactiveDraw.
        // A missing route invalidates the seed; this is NOT a complete scene
        // receipt until every physical owner is covered.
        template<class DrawCall>
        R7CandidateSeedResult R7ReplayInactiveEye(IDirect3DDevice9* device,
            unsigned eye,IDirect3DSurface9* liveColor,IDirect3DSurface9* liveDepth,
            DrawCall& drawCall) noexcept
        {
            if(ExternalAtomicReplayEpoch!=PresentEpoch)
                return R7CandidateSeedResult::Unavailable;
            if(eye>=2||!liveColor||!liveDepth||
                liveColor!=ExternalAtomicCandidates.provenLiveColor[eye]||
                liveDepth!=ExternalAtomicCandidates.provenLiveDepth[eye]){
                ExternalAtomicReplayEpoch=0;
                return R7CandidateSeedResult::Unavailable;
            }
            const auto epoch=PresentEpoch;
            const auto boundary=R7CandidateBoundarySerial;
            const auto generation=ExternalAtomicCandidates.generation;
            InternalPassScope guard;
            const auto result=R7SeedInactivePair(ExternalAtomicCandidates,device,
                liveColor,liveDepth,
                [&](IDirect3DSurface9* s){return SetRenderTargetHook.stdcall<HRESULT>(device,0u,s);},
                [&](IDirect3DSurface9* s){return SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,s);},
                [&](){return drawCall();},eye,1,false);
            if(result!=R7CandidateSeedResult::Seeded){
                ExternalAtomicReplayEpoch=0;
                return result;
            }
            if(PresentEpoch!=epoch||ExternalAtomicReplayEpoch!=epoch||R7CandidateBoundarySerial!=boundary||
                ExternalAtomicCandidates.generation!=generation||
                liveColor!=(eye==0?TrackedRenderTarget:RightEyeSurface)||
                liveDepth!=(eye==0?TrackedDepthStencil:RightEyeDepth)){
                ExternalAtomicReplayEpoch=0;
                return R7CandidateSeedResult::Unavailable;
            }
            return result;
        }

        // Copy/fill methods write explicit surfaces without a draw or Clear.
        // Mirror only operations with proven candidate color provenance; never
        // use StretchRect as a scene-depth reconstruction mechanism.
        template<class Write>
        HRESULT R7ExecuteAtomicSurfaceWrite(IDirect3DDevice9* device,
            IDirect3DSurface9* source,IDirect3DSurface9* destination,
            bool fill,Write&& write) noexcept
        {
            if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)||
                !IsGameDevice(device))
                return write(source,destination);
            if(destination&&destination==TrackedDepthStencil)
                LastMainDepthClearStamp.Invalidate();
            const bool active=ExternalAtomicReplayEpoch!=0&&ExternalAtomicReplayEpoch==PresentEpoch;
            if(!active)return write(source,destination);
            auto& pair=ExternalAtomicCandidates;
            auto eyeFor=[&](IDirect3DSurface9* s){
                if(!s)return -1;
                if(s==BackBuffer)return 0;
                if(s==RightEyeSurface)return 1;
                return -1;
            };
            const auto generation=pair.generation;
            const auto epoch=PresentEpoch;
            const auto boundary=R7CandidateBoundarySerial;
            const int dstEye=eyeFor(destination);
            const int srcEye=eyeFor(source);
            auto current=[&](){return pair.generation==generation&&pair.device==device&&
                PresentEpoch==epoch&&ExternalAtomicReplayEpoch==epoch&&
                R7CandidateBoundarySerial==boundary;};
            auto liveMatches=[&](int eye,IDirect3DSurface9* surface){
                return eye>=0&&pair.provenLiveColor[eye]==surface&&eyeFor(surface)==eye;
            };
            const bool protectedDepth=destination&&
                (destination==TrackedDepthStencil||destination==RightEyeDepth);
            const bool privateWrite=destination&&
                (destination==pair.eyes[0].color||destination==pair.eyes[1].color||
                 destination==pair.eyes[0].depth||destination==pair.eyes[1].depth);
            if(protectedDepth||privateWrite)ExternalAtomicReplayEpoch=0;
            // Preserve the original operation and HRESULT exactly once. The
            // private replay cannot change bindings, viewport or input state.
            const HRESULT hr=write(source,destination);
            if(dstEye<0)return hr;
            if(FAILED(hr)||!current()||FrameStereoIncomplete||FrameRightDrawFailed||
                !liveMatches(dstEye,destination)||!pair.eyes[dstEye].color||
                (!fill&&(!liveMatches(srcEye,source)||!pair.eyes[srcEye].color))){
                ExternalAtomicReplayEpoch=0;
                return hr;
            }
            if(FAILED(write(fill?nullptr:pair.eyes[srcEye].color,pair.eyes[dstEye].color))||
                !current()||!liveMatches(dstEye,destination)||(!fill&&!liveMatches(srcEye,source)))
                ExternalAtomicReplayEpoch=0;
            return hr;
        }

        HRESULT __stdcall StretchRectDest(IDirect3DDevice9* device,
            IDirect3DSurface9* source,const RECT* sourceRect,
            IDirect3DSurface9* destination,const RECT* destinationRect,
            D3DTEXTUREFILTERTYPE filter)
        {
            return R7ExecuteAtomicSurfaceWrite(device,source,destination,false,
                [&](IDirect3DSurface9* s,IDirect3DSurface9* d){
                    return StretchRectHook.stdcall<HRESULT>(device,s,sourceRect,d,destinationRect,filter);
                });
        }

        HRESULT __stdcall ColorFillDest(IDirect3DDevice9* device,
            IDirect3DSurface9* destination,const RECT* rect,D3DCOLOR color)
        {
            return R7ExecuteAtomicSurfaceWrite(device,nullptr,destination,true,
                [&](IDirect3DSurface9*,IDirect3DSurface9* d){
                    return ColorFillHook.stdcall<HRESULT>(device,d,rect,color);
                });
        }

        // UpdateSurface can upload CPU pixels straight into a live color
        // attachment, bypassing raster, Clear and StretchRect. Its system-memory
        // source may itself be a readback of stock pixels; never assume it is
        // equivalent to a future externally staged candidate. Retire the
        // receipt before the original call, including on ambiguous failures.
        HRESULT __stdcall UpdateSurfaceDest(IDirect3DDevice9* device,
            IDirect3DSurface9* source,const RECT* sourceRect,
            IDirect3DSurface9* destination,const POINT* destinationPoint)
        {
            if(StereoBaseCallbacksArmed.load(std::memory_order_acquire)&&
                IsGameDevice(device)&&destination)
            {
                if(destination==TrackedDepthStencil)
                    LastMainDepthClearStamp.Invalidate();
                const auto& pair=ExternalAtomicCandidates;
                if(destination==BackBuffer||destination==RightEyeSurface||
                    destination==TrackedDepthStencil||destination==RightEyeDepth||
                    destination==pair.eyes[0].color||destination==pair.eyes[1].color||
                    destination==pair.eyes[0].depth||destination==pair.eyes[1].depth)
                    ExternalAtomicReplayEpoch=0;
            }
            return UpdateSurfaceHook.stdcall<HRESULT>(device,source,sourceRect,
                destination,destinationPoint);
        }

		void ReleaseStereoResources()
		{
            ExternalAtomicCandidates.Reset();
            ExternalAtomicReplayEpoch=0;
            ExternalAtomicAllocationAttemptEpoch=0;
			// A Reset can recycle a COM address for a different depth format.
			TrackedStencilFormatKnown = false;
			LastMainDepthClearStamp.Invalidate();
            // Reset/ResetEx may reuse a COM address for another device.
            DirectTransportFacts = {};
			StereoResourcesReady=false;
			RetireDirectTransportFramePublications();
			DirectTransportResourcesReady=false;
            DirectTransportWidth=0;DirectTransportHeight=0;
            DirectEyeExtentGeneration.Reset();
			ReleaseDirectTransportSlotObjects();
			ReleaseDirectInteropProbe();
			DirectTransportFormat=D3DFMT_UNKNOWN;ProjectionInverseValid=false;ReleaseCom(RightEyeSurface);ReleaseCom(RightEyeDepth);ReleaseCom(LeftResolveSurface);ReleaseCom(LeftResolveTexture);ReleaseCom(RightResolveSurface);ReleaseCom(RightResolveTexture);ReleaseCom(BackBuffer);ReleaseCom(TrackedRenderTarget);ReleaseCom(TrackedDepthStencil);RightDepthSynchronized=true;RightStencilSynchronized=true;BackBufferDesc={};
		}
		bool CreateRightDepthForTracked(IDirect3DDevice9* device)
		{
			ReleaseCom(RightEyeDepth);RightDepthSynchronized=TrackedDepthStencil==nullptr;RightStencilSynchronized=true;if(!TrackedDepthStencil)return true;D3DSURFACE_DESC depthDesc{};if(FAILED(TrackedDepthStencil->GetDesc(&depthDesc)))return false;RightStencilSynchronized=!FormatHasStencil(depthDesc.Format);return SUCCEEDED(device->CreateDepthStencilSurface(BackBufferDesc.Width,BackBufferDesc.Height,depthDesc.Format,depthDesc.MultiSampleType,depthDesc.MultiSampleQuality,FALSE,&RightEyeDepth,nullptr));
		}
		bool InitializeAuxRenderTargetState(IDirect3DDevice9* device){for(DWORD index=1;index<=3;++index){IDirect3DSurface9*surface=nullptr;const HRESULT hr=device->GetRenderTarget(index,&surface);AuxRenderTargetActive[index-1]=SUCCEEDED(hr)&&surface!=nullptr;if(surface)surface->Release();}return true;}
		D3DFORMAT ChooseDirectTransportFormat(D3DFORMAT source){switch(source){case D3DFMT_A2B10G10R10:return D3DFMT_A2B10G10R10;case D3DFMT_A16B16G16R16F:return D3DFMT_A16B16G16R16F;case D3DFMT_A8R8G8B8:return D3DFMT_A8R8G8B8;default:return D3DFMT_A8R8G8B8;}}
		bool CanConvertForDirectTransport(IDirect3DDevice9* device,D3DFORMAT source,D3DFORMAT target){if(!device)return false;if(source==target)return true;D3DDEVICE_CREATION_PARAMETERS cp{};if(FAILED(device->GetCreationParameters(&cp)))return false;IDirect3D9*d3d=nullptr;if(FAILED(device->GetDirect3D(&d3d))||!d3d)return false;const HRESULT hr=d3d->CheckDeviceFormatConversion(cp.AdapterOrdinal,cp.DeviceType,source,target);d3d->Release();return SUCCEEDED(hr);}
		bool FrameIdAtOrAfter(std::uint32_t candidate,std::uint32_t reference){return reference==0||static_cast<std::int32_t>(candidate-reference)>=0;}
		// Initial interop verification may need FLUSH to submit the probe query.
// The production DirectGPU post-Present path has already submitted commands:
// repeatedly forcing D3DGETDATA_FLUSH on that 1 ms grace path risks extra
// driver submission/stalls. Callers select the policy explicitly, while every
// unresolved/failed query remains unpublishable and ring-owned.
bool WaitForEventQuery(IDirect3DQuery9* query, ULONGLONG timeoutMs,
    DWORD dataFlags = D3DGETDATA_FLUSH)
{
    if (!query) return false;
    const ULONGLONG deadline = GetTickCount64() + timeoutMs;
    for (;;)
    {
        const HRESULT ready = query->GetData(nullptr, 0, dataFlags);
        if (ready == S_OK) return true;
        if (ready != S_FALSE) return false;
        if (GetTickCount64() >= deadline) return false;
        Sleep(0);
    }
}

		bool QueryGameAdapterLuid(IDirect3DDevice9* device,LUID& luid)
        {
            if (!device) return false;
            BindDirectTransportFacts(device);
            if (DirectTransportFacts.adapterLuidKnown)
            {
                luid = DirectTransportFacts.gameAdapterLuid;
                return true;
            }
            IDirect3DDevice9Ex* deviceEx = nullptr;
            if (FAILED(device->QueryInterface(__uuidof(IDirect3DDevice9Ex),
                    reinterpret_cast<void**>(&deviceEx))) || !deviceEx)
            {
                if (!FirstD3D9ExUnavailableLogged)
                {
                    FirstD3D9ExUnavailableLogged = true;
                    spdlog::warn("VR direct transport: game device is not D3D9Ex; zero-copy disabled, SBS/Desktop Duplication remains active");
                }
                return false;
            }
            D3DDEVICE_CREATION_PARAMETERS cp{};
            IDirect3D9* base = nullptr;
            IDirect3D9Ex* d3dEx = nullptr;
            const bool ok =
                SUCCEEDED(deviceEx->GetCreationParameters(&cp)) &&
                SUCCEEDED(deviceEx->GetDirect3D(&base)) && base &&
                SUCCEEDED(base->QueryInterface(__uuidof(IDirect3D9Ex),
                    reinterpret_cast<void**>(&d3dEx))) && d3dEx &&
                SUCCEEDED(d3dEx->GetAdapterLUID(cp.AdapterOrdinal, &luid));
            ReleaseCom(d3dEx);
            ReleaseCom(base);
            ReleaseCom(deviceEx);
            // Never cache failed queries; retry only the unresolved part.
            if (ok)
            {
                DirectTransportFacts.gameAdapterLuid = luid;
                DirectTransportFacts.adapterLuidKnown = true;
            }
            return ok;
        }
		bool EnsureDirectInteropProbe(IDirect3DDevice9* device)
		{
			if(!HostDirectTransportSupported()||!EnsureSharedState()||(SharedState->flags&OutRunVR::HostAdapterLuidValid)==0)return false;LUID gameLuid{};if(!QueryGameAdapterLuid(device,gameLuid))return false;InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientAdapterLuidLow),static_cast<LONG>(gameLuid.LowPart));InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientAdapterLuidHigh),static_cast<LONG>(gameLuid.HighPart));const bool adapterMatches=SharedState->hostAdapterLuidLow==gameLuid.LowPart&&SharedState->hostAdapterLuidHigh==static_cast<std::uint32_t>(gameLuid.HighPart);if(!adapterMatches){if(!FirstAdapterMismatchLogged){FirstAdapterMismatchLogged=true;spdlog::warn("VR direct transport: OpenXR D3D11 adapter LUID does not match the game D3D9Ex adapter; forcing SBS fallback");}return false;}if(DirectInteropProbeToken&&SharedState->hostInteropProbeAckToken==DirectInteropProbeToken){DirectInteropVerified=true;if(!FirstInteropVerifiedLogged){FirstInteropVerifiedLogged=true;spdlog::info("VR direct transport: D3D9Ex -> D3D11 shared-resource probe verified on the OpenXR adapter");}return true;}if(!DirectInteropProbeTexture){HANDLE handle=nullptr;if(FAILED(device->CreateTexture(1,1,1,D3DUSAGE_RENDERTARGET,D3DFMT_A8R8G8B8,D3DPOOL_DEFAULT,&DirectInteropProbeTexture,&handle))||!DirectInteropProbeTexture||!handle||FAILED(DirectInteropProbeTexture->GetSurfaceLevel(0,&DirectInteropProbeSurface))||FAILED(device->ColorFill(DirectInteropProbeSurface,nullptr,D3DCOLOR_ARGB(0xFF,0x7B,0x7B,0x7B)))||FAILED(device->CreateQuery(D3DQUERYTYPE_EVENT,&DirectInteropProbeFence))||!DirectInteropProbeFence||FAILED(DirectInteropProbeFence->Issue(D3DISSUE_END))||!WaitForEventQuery(DirectInteropProbeFence,50)){++DirectInteropProbeFailures;ReleaseDirectInteropProbe();return false;}DirectInteropProbeHandle=handle;DirectInteropProbeToken=static_cast<std::uint32_t>(GetTickCount())^GetCurrentProcessId()^0x4F525652u;if(!DirectInteropProbeToken)DirectInteropProbeToken=1;InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->hostInteropProbeAckToken),0);InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeHandle),static_cast<LONG>(reinterpret_cast<std::uintptr_t>(DirectInteropProbeHandle)));InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeToken),static_cast<LONG>(DirectInteropProbeToken));}return false;
		}
		void ReleaseDirectTransportSlots(){RetireDirectTransportFramePublications();DirectTransportResourcesReady=false;DirectTransportWidth=0;DirectTransportHeight=0;DirectEyeExtentGeneration.Reset();ReleaseDirectTransportSlotObjects();}
		bool DirectTransportTargetSize(IDirect3DDevice9* device,UINT& width,UINT& height)
        {
            width = 0; height = 0;
            if (!device || !SharedState || SharedState->magic != OutRunVR::SharedMagic ||
                SharedState->protocolVersion != OutRunVR::SharedProtocolVersion ||
                SharedState->structSize != sizeof(OutRunVR::SharedPoseState))
                return false;
            OutRunVR::EyeExtent::Size published{};
            bool stable = false;
            for (int attempt = 0; attempt < 4; ++attempt)
            {
                const std::uint32_t before = SharedState->sequence;
                if (before & 1u) continue;
                MemoryBarrier();
                const auto w0 = SharedState->recommendedWidth[0];
                const auto h0 = SharedState->recommendedHeight[0];
                const auto w1 = SharedState->recommendedWidth[1];
                const auto h1 = SharedState->recommendedHeight[1];
                MemoryBarrier();
                const std::uint32_t after = SharedState->sequence;
                if (before != after || (after & 1u)) continue;
                // Host must publish both equal array-slice extents atomically.
                if (w0 != w1 || h0 != h1) return false;
                published = {w0, h0};
                stable = true;
                break;
            }
            if (!stable)
            {
                // Retain current valid allocation on transient seqlock contention.
                published = {DirectTransportWidth, DirectTransportHeight};
            }
            BindDirectTransportFacts(device);
            if (!DirectTransportFacts.textureLimitsKnown)
            {
                D3DCAPS9 caps{};
                if (FAILED(device->GetDeviceCaps(&caps))) return false;
                DirectTransportFacts.maxTextureWidth = caps.MaxTextureWidth;
                DirectTransportFacts.maxTextureHeight = caps.MaxTextureHeight;
                DirectTransportFacts.textureLimitsKnown = true;
            }
            const auto exact = OutRunVR::EyeExtent::ResolveGame(
                published, {DirectTransportFacts.maxTextureWidth,
                            DirectTransportFacts.maxTextureHeight});
            if (!OutRunVR::EyeExtent::Valid(exact)) return false;
            width = exact.width;
            height = exact.height;
            return true;
        }
		HRESULT StretchDirectEye(IDirect3DDevice9* device,IDirect3DSurface9* source,IDirect3DSurface9* target)
		{
			if(!device||!source||!target)return D3DERR_INVALIDCALL;HRESULT hr=device->StretchRect(source,nullptr,target,nullptr,D3DTEXF_LINEAR);if(FAILED(hr))hr=device->StretchRect(source,nullptr,target,nullptr,D3DTEXF_NONE);return hr;
		}
		bool EnsureDirectTransportResources(IDirect3DDevice9* device)
		{
			if(!device||!BackBufferDesc.Width||!BackBufferDesc.Height||!EnsureRenderFrameState()||!EnsureDirectInteropProbe(device))return false;UINT targetWidth=0,targetHeight=0;if(!DirectTransportTargetSize(device,targetWidth,targetHeight))return false;if(DirectTransportResourcesReady&&DirectEyeExtentGeneration.Matches({targetWidth,targetHeight})&&DirectTransportWidth==targetWidth&&DirectTransportHeight==targetHeight)return true;if(DirectTransportResourcesReady)ReleaseDirectTransportSlots();DirectTransportFormat=ChooseDirectTransportFormat(BackBufferDesc.Format);if(!CanConvertForDirectTransport(device,BackBufferDesc.Format,DirectTransportFormat))return false;for(auto&slot:DirectTransportSlots){HANDLE leftHandle=nullptr,rightHandle=nullptr;const HRESULT leftHr=device->CreateTexture(targetWidth,targetHeight,1,D3DUSAGE_RENDERTARGET,DirectTransportFormat,D3DPOOL_DEFAULT,&slot.leftTexture,&leftHandle);const HRESULT rightHr=SUCCEEDED(leftHr)?device->CreateTexture(targetWidth,targetHeight,1,D3DUSAGE_RENDERTARGET,DirectTransportFormat,D3DPOOL_DEFAULT,&slot.rightTexture,&rightHandle):E_FAIL;if(FAILED(leftHr)||FAILED(rightHr)||!leftHandle||!rightHandle||FAILED(slot.leftTexture->GetSurfaceLevel(0,&slot.leftSurface))||FAILED(slot.rightTexture->GetSurfaceLevel(0,&slot.rightSurface))||FAILED(device->CreateQuery(D3DQUERYTYPE_EVENT,&slot.fence))||!slot.fence){ReleaseDirectTransportSlots();return false;}slot.leftHandle=leftHandle;slot.rightHandle=rightHandle;}DirectTransportWidth=targetWidth;DirectTransportHeight=targetHeight;DirectEyeExtentGeneration.Commit({targetWidth,targetHeight});if(!DirectTransportGeneration)DirectTransportGeneration=RenderFrameRunGeneration;if(++DirectTransportGeneration==0)++DirectTransportGeneration;DirectTransportResourcesReady=true;spdlog::info("VR stereo: verified 4-slot D3D9Ex shared eye ring ready {}x{} from desktop {}x{} (VDXR/OpenXR recommended) format={} generation={}",DirectTransportWidth,DirectTransportHeight,BackBufferDesc.Width,BackBufferDesc.Height,static_cast<int>(DirectTransportFormat),DirectTransportGeneration);return true;
		}
		bool ResolveDirectTransport(IDirect3DDevice9* device,std::uint32_t frameId)
		{
			if(!frameId||!EnsureDirectTransportResources(device)||!BackBuffer||!RightEyeSurface)return false;
			const std::uint32_t consumed=SharedState?SharedState->hostDirectConsumedFrameId:0;
			const std::uint32_t preferred=(frameId-1u)%OutRunVR::RenderFrameRingSize;
			std::uint32_t selected=OutRunVR::RenderFrameRingSize;

			// Search every ring slot. A slow query must not stall the game thread
			// or block an otherwise free slot.
			for(std::uint32_t offset=0;offset<OutRunVR::RenderFrameRingSize;++offset)
			{
				const std::uint32_t index=(preferred+offset)%OutRunVR::RenderFrameRingSize;
				auto&slot=DirectTransportSlots[index];

				if(slot.producerPending)
				{
					const HRESULT ready=slot.fence?slot.fence->GetData(nullptr,0,0):E_FAIL;
					if(ready==S_OK)
					{
						slot.producerPending=false;
						slot.pendingFrameId=0;
						// A frame whose fence missed its publication window was
						// never visible to the host, so reclaim it without ACK.
						if(!slot.published)slot.frameId=0;
					}
					else if(ready==S_FALSE)
					{
						continue;
					}
					else
					{
						slot.producerPending=false;
						slot.pendingFrameId=0;
						slot.frameId=0;
						slot.published=false;
					}
				}

				// Published images are immutable until the host ACKs their frame.
				if(slot.published&&slot.frameId&&!FrameIdAtOrAfter(consumed,slot.frameId))
					continue;
				if(slot.published&&slot.frameId&&FrameIdAtOrAfter(consumed,slot.frameId))
				{
					slot.frameId=0;
					slot.published=false;
				}
				selected=index;
				break;
			}

			if(selected>=OutRunVR::RenderFrameRingSize)
			{
				++DirectTransportRingBackpressure;
				return false;
			}

			auto&slot=DirectTransportSlots[selected];
			{
				InternalPassScope guard;
				if(FAILED(StretchDirectEye(device,BackBuffer,slot.leftSurface))||
					FAILED(StretchDirectEye(device,RightEyeSurface,slot.rightSurface))||
					FAILED(slot.fence->Issue(D3DISSUE_END)))return false;
			}
			slot.producerPending=true;
			slot.pendingFrameId=frameId;
			slot.frameId=frameId;
			slot.published=false;
			ActiveDirectTransportSlot=selected;
			return true;
		}

		bool DirectTransportFrameReadyAfterPresent(std::uint32_t frameId)
		{
			if(!frameId||ActiveDirectTransportSlot>=DirectTransportSlots.size())return false;
			auto&slot=DirectTransportSlots[ActiveDirectTransportSlot];
			if(slot.frameId!=frameId||slot.pendingFrameId!=frameId||!slot.fence)return false;

			// Present has already flushed the frame. Allow at most 1 ms of bounded
			// completion grace here; the old 4 ms pre-Present wait consumed a large
			// part of a 90/120 Hz frame budget and was visible as VD hitching.
			// Present already submitted both StretchRect copies and the EVENT.
// Never inject an extra FLUSH while waiting for the producer completion.
if(WaitForEventQuery(slot.fence,1,0u))
			{
				slot.producerPending=false;
				slot.pendingFrameId=0;
				slot.published=true;
				return true;
			}

			++DirectTransportFenceTimeouts;
			// Any unresolved EVENT stays quarantined here. Do not issue a second
			// GetData or clear producer ownership after the bounded wait: the next
			// ring scan is the single owner that distinguishes S_OK, S_FALSE, and
			// hard errors. This keeps an unproven shared slot immutable and lets
			// R13/R32 fail-closed rejection handle hard query failures.
			return false;
		}

		// Capture real LEFT attachments before retiring or allocating anything.
		// A failed getter is not evidence of the default RT or no depth surface.
		bool CaptureStereoInitState(IDirect3DDevice9* device,
			IDirect3DSurface9*& back, IDirect3DSurface9*& rt,
			IDirect3DSurface9*& depth, D3DSURFACE_DESC& desc,
			D3DVIEWPORT9& viewport)
		{
			const auto fail = [&]() {
				ReleaseCom(depth);
				ReleaseCom(rt);
				ReleaseCom(back);
				return false;
			};
			if (FAILED(device->GetBackBuffer(0,0,D3DBACKBUFFER_TYPE_MONO,&back)) ||
				!back || FAILED(back->GetDesc(&desc)))
				return fail();
			if (FAILED(device->GetRenderTarget(0,&rt)) || !rt)
				return fail();
			const HRESULT depthHr = device->GetDepthStencilSurface(&depth);
			if (depthHr == D3DERR_NOTFOUND)
			{
				if (depth)
					return fail();
			}
			else if (FAILED(depthHr) || !depth)
				return fail();
			if (FAILED(device->GetViewport(&viewport)))
				return fail();
			return true;
		}

		bool EnsureStereoResources(IDirect3DDevice9* device)
		{
			if (!device) return false;
			if (StereoResourcesReady && BackBuffer && RightEyeSurface &&
				LeftResolveSurface && RightResolveSurface) return true;
			IDirect3DSurface9* newBackBuffer=nullptr;
			IDirect3DSurface9* currentRt=nullptr;
			IDirect3DSurface9* currentDepth=nullptr;
			D3DSURFACE_DESC desc{};
			D3DVIEWPORT9 savedViewport{};
			if (!CaptureStereoInitState(device,newBackBuffer,currentRt,
				currentDepth,desc,savedViewport)) return false;
			ReleaseStereoResources();
			BackBuffer=newBackBuffer;
			BackBufferDesc=desc;
			TrackedRenderTarget=currentRt;
			TrackedDepthStencil=currentDepth;
			InitializeAuxRenderTargetState(device);
			if (FAILED(device->CreateRenderTarget(desc.Width,desc.Height,desc.Format,
				desc.MultiSampleType,desc.MultiSampleQuality,FALSE,&RightEyeSurface,nullptr)) ||
				!CreateRightDepthForTracked(device)) {ReleaseStereoResources();return false;}
			if (FAILED(device->CreateTexture(desc.Width,desc.Height,1,D3DUSAGE_RENDERTARGET,
				desc.Format,D3DPOOL_DEFAULT,&LeftResolveTexture,nullptr)) ||
				FAILED(LeftResolveTexture->GetSurfaceLevel(0,&LeftResolveSurface)) ||
				FAILED(device->CreateTexture(desc.Width,desc.Height,1,D3DUSAGE_RENDERTARGET,
				desc.Format,D3DPOOL_DEFAULT,&RightResolveTexture,nullptr)) ||
				FAILED(RightResolveTexture->GetSurfaceLevel(0,&RightResolveSurface))) {
				ReleaseStereoResources();return false;
			}
			// 01515: a newly allocated RIGHT color/depth surface must have
			// every pixel initialized even if the game has a cropped viewport.
			// Change only the one-time allocation clear, then restore the
			// caller's exact viewport below (no extra steady-state GPU work).
			D3DVIEWPORT9 initViewport=savedViewport;
			initViewport.X=0;initViewport.Y=0;
			initViewport.Width=desc.Width;initViewport.Height=desc.Height;
			bool initOk=true;{InternalPassScope guard;if(FAILED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface)))initOk=false;if(initOk){const HRESULT depthHr=SetDepthStencilSurfaceHook?SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth):device->SetDepthStencilSurface(RightEyeDepth);if(FAILED(depthHr))initOk=false;}if(initOk&&FAILED(device->SetViewport(&initViewport)))initOk=false;DWORD clearFlags=D3DCLEAR_TARGET;if(RightEyeDepth){D3DSURFACE_DESC depthDesc{};if(FAILED(RightEyeDepth->GetDesc(&depthDesc)))initOk=false;else{clearFlags|=D3DCLEAR_ZBUFFER;if(FormatHasStencil(depthDesc.Format))clearFlags|=D3DCLEAR_STENCIL;}}if(initOk&&FAILED(ClearHook.stdcall<HRESULT>(device,0u,static_cast<const D3DRECT*>(nullptr),clearFlags,D3DCOLOR_XRGB(0,0,0),1.0f,0u)))initOk=false;if(TrackedRenderTarget&&FAILED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,TrackedRenderTarget)))initOk=false;const HRESULT restoreDepthHr=SetDepthStencilSurfaceHook?SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,TrackedDepthStencil):device->SetDepthStencilSurface(TrackedDepthStencil);if(FAILED(restoreDepthHr))initOk=false;if(FAILED(device->SetViewport(&savedViewport)))initOk=false;}if(!initOk){ReleaseStereoResources();return false;}StereoResourcesReady=true;spdlog::info("VR stereo: full-size eye surfaces ready {}x{} format={} msaa={} quality={}",desc.Width,desc.Height,static_cast<int>(desc.Format),static_cast<int>(desc.MultiSampleType),desc.MultiSampleQuality);return true;
		}

		void NoteRestoreFailure(const char* what){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailureRestoreFailed);++RestoreFailures;if(!FirstRestoreFailureLogged){FirstRestoreFailureLogged=true;spdlog::warn("VR stereo: renderer state restore failed at {}; frame forced to mono fallback",what);}}
        // Candidate UP draws must not expose D3D9's input-unbind side effects.
        // The physical live draw alone owns those effects, even on the right eye.
        template<class DrawCall>
        R7CandidateSeedResult R7ReplayInactiveDraw(IDirect3DDevice9* device,
            unsigned eye,IDirect3DSurface9* color,IDirect3DSurface9* depth,
            DrawCall& drawCall,bool up,bool indexedUp) noexcept
        {
            bool inputRestoreFailed=false;
            auto candidateDraw=[&]() -> HRESULT {
                if(!up)return drawCall();
                IDirect3DVertexBuffer9* vb=nullptr;
                IDirect3DIndexBuffer9* ib=nullptr;
                UINT offset=0,stride=0;
                // UP draws clear stream zero (and the index binding for
                // indexed UP). Do not restore pre-reset COM objects into a
                // retired device generation, even if the draw returned S_OK.
                const auto generation=ExternalAtomicCandidates.generation;
                const auto boundary=R7CandidateBoundarySerial;
                auto current=[&](){return ExternalAtomicCandidates.generation==generation&&
                    ExternalAtomicCandidates.device==device;};
                auto rasterCurrent=[&](){return current()&&R7CandidateBoundarySerial==boundary;};
                const bool captured=SUCCEEDED(device->GetStreamSource(0,&vb,&offset,&stride))&&
                    rasterCurrent()&&(!indexedUp||SUCCEEDED(device->GetIndices(&ib)))&&
                    rasterCurrent();
                if(!captured){ReleaseCom(ib);ReleaseCom(vb);return E_FAIL;}
                const HRESULT hr=drawCall();
                // A Present alone interrupts raster but does not invalidate
                // saved input ownership. Still restore on that boundary.
                // Check again between independent recovery operations.
                if(!current()||FAILED(device->SetStreamSource(0,vb,vb?offset:0u,vb?stride:0u)))
                    inputRestoreFailed=true;
                if(indexedUp&&(!current()||FAILED(device->SetIndices(ib))))
                    inputRestoreFailed=true;
                if(!current())inputRestoreFailed=true;
                ReleaseCom(ib);ReleaseCom(vb);
                return inputRestoreFailed?E_FAIL:hr;
            };
            const auto result=R7ReplayInactiveEye(device,eye,color,depth,candidateDraw);
            if(inputRestoreFailed||result!=R7CandidateSeedResult::Seeded)
                ExternalAtomicReplayEpoch=0;
            return inputRestoreFailed?R7CandidateSeedResult::DirtyRestore:result;
        }
        // Raw R29/R30 owners already selected the eye and shader state.
        // InternalStereoPass alone cannot identify the eye or mono backup.
        template<class DrawCall>
        HRESULT R7ExecuteRawCandidateVb(IDirect3DDevice9* device,DrawCall&& drawCall,
            bool up=false,bool indexedUp=false,DWORD clearFlags=0) noexcept
        {
            if(!IsGameDevice(device)||ExternalAtomicReplayEpoch!=PresentEpoch){
                RevokeDepthClearReplayBeforeLeftDraw(device);
                return drawCall();
            }
            IDirect3DSurface9* rt=nullptr;
            IDirect3DSurface9* depth=nullptr;
            int eye=-1;
            if(!FrameStereoIncomplete&&!FrameRightDrawFailed&&
                !AnyAuxRenderTargetActive()&&
                !OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire)&&
                ActiveOcclusionQueries.load(std::memory_order_acquire)==0&&
                !OutRunVR::DinoSidecar::ActiveExternalStereoMesh&&
                TargetIsBackBuffer()&&
                SUCCEEDED(device->GetRenderTarget(0,&rt))&&rt&&
                SUCCEEDED(device->GetDepthStencilSurface(&depth))&&depth){
                if(rt==TrackedRenderTarget&&depth==TrackedDepthStencil)eye=0;
                else if(rt==RightEyeSurface&&depth==RightEyeDepth)eye=1;
            }
            RevokeDepthClearReplayBeforeLeftDraw(device,eye>=0);
            // Internal Clear may write LEFT depth regardless of the current
            // depth/stencil render-state write masks. Only proven RIGHT
            // attachment identity exempts the previous LEFT clear receipt.
            if(clearFlags&&eye!=1)
                LastMainDepthClearStamp.OnPotentialWrite(clearFlags&(D3DCLEAR_ZBUFFER|D3DCLEAR_STENCIL));
            if(eye>=0){
                const auto result=R7ReplayInactiveDraw(device,
                    static_cast<unsigned>(eye),rt,depth,drawCall,up,indexedUp);
                ReleaseCom(depth);ReleaseCom(rt);
                if(result!=R7CandidateSeedResult::Seeded)ExternalAtomicReplayEpoch=0;
                if(result==R7CandidateSeedResult::DirtyRestore){
                    ExternalAtomicReplayEpoch=0;
                    LastMainDepthClearStamp.Invalidate();
                    RightDepthSynchronized=false;RightStencilSynchronized=false;
                    NoteRestoreFailure("external inactive raw replay");
                    return E_FAIL; // attachment restoration not proven
                }
            }else{
                ReleaseCom(depth);ReleaseCom(rt);
            }
            const HRESULT hr=drawCall();
            if(FAILED(hr))ExternalAtomicReplayEpoch=0;
            return hr;
        }

		bool RestoreRightPassState(IDirect3DDevice9* device,IDirect3DSurface9* savedRt,IDirect3DSurface9* savedDepth,const D3DVIEWPORT9& savedViewport,const float* originalConstants,bool restoreWvp){bool ok=true;if(savedRt&&FAILED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,savedRt)))ok=false;const HRESULT depthHr=SetDepthStencilSurfaceHook?SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,savedDepth):device->SetDepthStencilSurface(savedDepth);if(FAILED(depthHr))ok=false;if(FAILED(device->SetViewport(&savedViewport)))ok=false;if(restoreWvp&&!RestoreWvpOneRegisterAtATime(device,originalConstants))ok=false;return ok;}
		bool TryBootstrapRightDepthFromRecentClear(IDirect3DDevice9*device,
			bool* restoreFailed=nullptr)
		{
			if(restoreFailed)*restoreFailed=false;
			++DepthBootstrapAttempts;
			if(!device||!RightEyeSurface||!RightEyeDepth||!TrackedRenderTarget||!TrackedDepthStencil||!LastMainDepthClearStamp.Current(PresentEpoch))return false;
			D3DSURFACE_DESC leftDesc{},rightDesc{};if(FAILED(TrackedDepthStencil->GetDesc(&leftDesc))||FAILED(RightEyeDepth->GetDesc(&rightDesc)))return false;
			if(!DepthDescMatches(leftDesc,rightDesc)||!DepthDescMatches(leftDesc,LastMainDepthClearDesc))return false;
			DWORD replayFlags=0;if(!RightDepthSynchronized&&(LastMainDepthClearStamp.flags&D3DCLEAR_ZBUFFER))replayFlags|=D3DCLEAR_ZBUFFER;if(!RightStencilSynchronized&&(LastMainDepthClearStamp.flags&D3DCLEAR_STENCIL)&&FormatHasStencil(leftDesc.Format))replayFlags|=D3DCLEAR_STENCIL;if(!replayFlags)return false;
			D3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport)))return false;
			// 01513: Clear(count=0) covers only the active viewport. Never
			// certify whole-surface RIGHT depth/stencil sync from a cropped
			// replay. Preserve the original viewport and fail closed instead
			// of adding GPU Clears or altering an already-live depth buffer.
			if(savedViewport.X!=0||savedViewport.Y!=0||
				savedViewport.Width!=BackBufferDesc.Width||
				savedViewport.Height!=BackBufferDesc.Height)return false;
			// Mirror the bootstrap while the actual RIGHT attachments are bound.
            // An unavailable candidate may fall back to the stock clear, but
            // dirty candidate restoration must not write to an unknown target.
            IDirect3DSurface9* savedRt=TrackedRenderTarget,*savedDepth=TrackedDepthStencil;
            HRESULT clearHr=E_FAIL;
            bool restoreOk=true,candidateDirty=false;
            {
                InternalPassScope guard;
                if(SUCCEEDED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface))&&
                    SUCCEEDED(SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth))&&
                    SUCCEEDED(device->SetViewport(&savedViewport))){
                    auto clearRight=[&](){return ClearHook.stdcall<HRESULT>(device,0u,
                        static_cast<const D3DRECT*>(nullptr),replayFlags,0,
                        LastMainDepthClearZ,LastMainDepthClearStencil);};
                    if(ExternalAtomicReplayEpoch&&ExternalAtomicReplayEpoch==PresentEpoch){
                        const auto replay=R7ReplayInactiveEye(device,1,RightEyeSurface,RightEyeDepth,clearRight);
                        candidateDirty=replay==R7CandidateSeedResult::DirtyRestore;
                        if(replay!=R7CandidateSeedResult::Seeded)ExternalAtomicReplayEpoch=0;
                    }
                    if(!candidateDirty)clearHr=clearRight();
                }
                // Always attempt outer recovery, even after candidate failure.
                restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);
            }
            if(FAILED(clearHr)||!restoreOk||candidateDirty)ExternalAtomicReplayEpoch=0;
            if(candidateDirty)restoreOk=false;
            // A failed restore is not an ordinary unavailable depth replay.
			// The live device may still target RIGHT; never certify this frame
			// or retry the clear from the same now-untrusted receipt.
			if(!restoreOk){
				if(restoreFailed)*restoreFailed=true;
				RightDepthSynchronized=false;RightStencilSynchronized=false;
				LastMainDepthClearStamp.Invalidate();
				NoteRestoreFailure("right-eye depth bootstrap");
				return false;
			}
			if(FAILED(clearHr))return false;
			if(replayFlags&D3DCLEAR_ZBUFFER)RightDepthSynchronized=true;
			if(replayFlags&D3DCLEAR_STENCIL)RightStencilSynchronized=true;
			++DepthBootstrapSuccesses;
			if(!FirstDepthBootstrapLogged){
				FirstDepthBootstrapLogged=true;
				spdlog::info("VR stereo: bootstrapped right-eye depth from same-Present full main clear flags=0x{:x} epoch={}",static_cast<unsigned>(replayFlags),PresentEpoch);
			}
			return true;
		}
		std::uint32_t NextStereoFrameId(){if(++StereoFrameCounter==0)++StereoFrameCounter;return StereoFrameCounter;}

		void PublishStereoState(std::uint32_t state,bool worldStereo,std::uint32_t poseSequence,std::uint32_t frameId)
		{
			if(!EnsureSharedState())return;InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]),0);const LONG stereoBits=static_cast<LONG>(OutRunVR::ClientStereoActive|OutRunVR::ClientStereoWorldDraw|OutRunVR::ClientStereoDrawDuplicated);InterlockedAnd(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]),~stereoBits);InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferWidthIndex]),static_cast<LONG>(BackBufferDesc.Width));InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]),static_cast<LONG>(BackBufferDesc.Height));if(state!=OutRunVR::StereoSbsActive||poseSequence==0||frameId==0){InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence),0);InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),static_cast<LONG>(state));return;}InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence),static_cast<LONG>(poseSequence));LONG bits=static_cast<LONG>(OutRunVR::ClientStereoActive|OutRunVR::ClientStereoDrawDuplicated);if(worldStereo)bits|=static_cast<LONG>(OutRunVR::ClientStereoWorldDraw);InterlockedOr(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]),bits);InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),static_cast<LONG>(OutRunVR::StereoSbsActive));MemoryBarrier();InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]),static_cast<LONG>(frameId));
		}

        void WriteGameMirrorClientRect(
            OutRunVR::SharedRenderFrameState& frame) noexcept
        {
            if (!Game::D3DPresentParams ||
                !Game::D3DPresentParams->hDeviceWindow)
                return;
            const HWND window = Game::D3DPresentParams->hDeviceWindow;
            if (!IsWindow(window))
                return;
            RECT client{};
            if (!GetClientRect(window, &client))
                return;
            POINT tl{client.left, client.top};
            POINT br{client.right, client.bottom};
            if (!ClientToScreen(window, &tl) ||
                !ClientToScreen(window, &br) ||
                br.x <= tl.x || br.y <= tl.y)
                return;
            const std::int32_t left = static_cast<std::int32_t>(tl.x);
            const std::int32_t top = static_cast<std::int32_t>(tl.y);
            const std::uint32_t width =
                static_cast<std::uint32_t>(br.x - tl.x);
            const std::uint32_t height =
                static_cast<std::uint32_t>(br.y - tl.y);
            std::uint32_t leftBits = 0, topBits = 0;
            static_assert(sizeof(leftBits) == sizeof(left));
            static_assert(sizeof(topBits) == sizeof(top));
            std::memcpy(&leftBits, &left, sizeof(leftBits));
            std::memcpy(&topBits, &top, sizeof(topBits));
            frame.reserved[OutRunVR::RenderFrameMirrorLeftIndex] = leftBits;
            frame.reserved[OutRunVR::RenderFrameMirrorTopIndex] = topBits;
            frame.reserved[OutRunVR::RenderFrameMirrorWidthIndex] = width;
            frame.reserved[OutRunVR::RenderFrameMirrorHeightIndex] = height;
        }

		void WriteGameBuildTag(OutRunVR::SharedRenderFrameState& frame)
		{
			char tag[12]{};
			const char* source = OUTRUN_VR_BUILD_SHA;
			for (std::size_t i = 0; i < sizeof(tag) && source[i]; ++i)
				tag[i] = source[i];
			std::memcpy(
				&frame.reserved[OutRunVR::RenderFrameGameBuildTag0Index],
				tag, sizeof(tag));
		}

		void PublishRenderFrame(std::uint32_t state,std::uint32_t frameId,std::uint32_t sourcePoseSequence,std::int64_t presentQpc,OutRunVR::StereoFailureReason failureReason,const OutRunVRRenderer::LatchedStereoFrame* stereo,bool presentInFlight=false,bool directTransport=false)
		{
			if(!EnsureRenderFrameState())return;const std::uint32_t slotIndex=frameId?(frameId-1u)%OutRunVR::RenderFrameRingSize:(RenderFrameRing->latestSlot+1u)%OutRunVR::RenderFrameRingSize;auto&frame=RenderFrameRing->slots[slotIndex];LONG seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));if((seq&1)==0)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));MemoryBarrier();frame.magic=OutRunVR::RenderFrameMagic;frame.protocolVersion=OutRunVR::RenderFrameProtocolVersion;frame.structSize=sizeof(frame);frame.clientPid=GetCurrentProcessId();frame.state=state;frame.frameId=frameId;frame.sourcePoseSequence=sourcePoseSequence;frame.presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;frame.flags=presentInFlight?OutRunVR::RenderFramePresentInFlight:0;frame.failureReason=static_cast<std::uint32_t>(failureReason);const bool directSizedFrame=directTransport&&DirectTransportResourcesReady&&DirectTransportWidth&&DirectTransportHeight;frame.backbufferWidth=directSizedFrame?DirectTransportWidth:BackBufferDesc.Width;frame.backbufferHeight=directSizedFrame?DirectTransportHeight:BackBufferDesc.Height;frame.presentQpc=presentQpc;std::memset(frame.eye,0,sizeof(frame.eye));std::memset(frame.reserved,0,sizeof(frame.reserved));frame.reserved[OutRunVR::RenderFrameRunGenerationIndex]=RenderFrameRunGeneration;WriteGameBuildTag(frame);WriteGameMirrorClientRect(frame);frame.reserved[OutRunVR::RenderFrameCadenceRequestIndex]=OutRunVRRenderer::GetActiveCadenceRequestId();if(OutRunVR::Pacing::Enabled()&&!presentInFlight&&frameId){LARGE_INTEGER published{};QueryPerformanceCounter(&published);OutRunVR::Pacing::StampPublished(frame,published.QuadPart,false);}if(directTransport&&DirectTransportResourcesReady&&ActiveDirectTransportSlot<DirectTransportSlots.size()){const auto&transport=DirectTransportSlots[ActiveDirectTransportSlot];if(transport.leftHandle&&transport.rightHandle&&transport.frameId==frameId){frame.flags|=OutRunVR::RenderFrameDirectGpuTransport;frame.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex]=static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(transport.leftHandle));frame.reserved[OutRunVR::RenderFrameDirectRightHandleIndex]=static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(transport.rightHandle));frame.reserved[OutRunVR::RenderFrameDirectWidthIndex]=DirectTransportWidth;frame.reserved[OutRunVR::RenderFrameDirectHeightIndex]=DirectTransportHeight;frame.reserved[OutRunVR::RenderFrameDirectFormatIndex]=static_cast<std::uint32_t>(DirectTransportFormat);frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex]=DirectTransportGeneration;frame.reserved[OutRunVR::RenderFrameDirectSlotIndex]=ActiveDirectTransportSlot;}}if(!presentInFlight&&state==OutRunVR::StereoSbsActive&&stereo&&stereo->valid&&frameId){const std::uint32_t transportFlag=frame.flags&OutRunVR::RenderFrameDirectGpuTransport;frame.flags=transportFlag|OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;for(int eye=0;eye<2;++eye){std::memcpy(frame.eye[eye].orientation,stereo->effectiveEyeOrientation[eye],sizeof(frame.eye[eye].orientation));std::memcpy(frame.eye[eye].position,stereo->effectiveEyePosition[eye],sizeof(frame.eye[eye].position));frame.eye[eye].fov=stereo->eyeFov[eye];}}MemoryBarrier();seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));if(seq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));LONG ringSeq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));if((ringSeq&1)==0)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));MemoryBarrier();RenderFrameRing->clientPid=GetCurrentProcessId();RenderFrameRing->latestSlot=slotIndex;MemoryBarrier();ringSeq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));if(ringSeq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));
		}

        void R7RetireDirectResetFrameIdentity()
        {
            // Do not reuse the pre-reset pose or certify a frame spanning reset.
            // Ex can retain D3D state: do not invent a fresh viewport/depth proof.
            if(++PresentEpoch==0)PresentEpoch=1;
            QuestNativePairLatch={};
            LastMainDepthClearStamp.Invalidate();
            LastMainDepthClearZ=1.0f;
            LastMainDepthClearStencil=0;
            LastMainDepthClearDesc={};
            LastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();
            InvalidateTrackedRenderStates();
            FrameHadDuplicatedDraw=false;
            FrameHadWorldStereo=false;
            FrameRightDrawFailed=false;
            FrameStereoPoseSequence=0;
            FrameStereoMetadata={};
            FramePoseMismatchLogged=false;
            PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);
            PublishStereoState(OutRunVR::StereoDisabled,false,0,0);
            PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,
                OutRunVR::StereoFailureResourceUnavailable,nullptr);
        }

		struct ScreenVertex{float x,y,z,rhw;float u,v;};
		bool DrawTextureHalf(IDirect3DDevice9* device,IDirect3DTexture9* texture,bool right){if(!texture||!BackBufferDesc.Width||!BackBufferDesc.Height)return false;const float x0=right?static_cast<float>(BackBufferDesc.Width/2):0.0f;const float x1=right?static_cast<float>(BackBufferDesc.Width):static_cast<float>(BackBufferDesc.Width/2);const float y0=0.0f,y1=static_cast<float>(BackBufferDesc.Height);const ScreenVertex vertices[4]={{x0-0.5f,y0-0.5f,0.0f,1.0f,0.0f,0.0f},{x1-0.5f,y0-0.5f,0.0f,1.0f,1.0f,0.0f},{x0-0.5f,y1-0.5f,0.0f,1.0f,0.0f,1.0f},{x1-0.5f,y1-0.5f,0.0f,1.0f,1.0f,1.0f}};if(FAILED(device->SetTexture(0,texture)))return false;return SUCCEEDED(device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP,2,vertices,static_cast<UINT>(sizeof(ScreenVertex))));}
		bool ComposeSbs(IDirect3DDevice9* device)
		{
			if(!StereoResourcesReady||!BackBuffer||!RightEyeSurface||!LeftResolveSurface||!RightResolveSurface)return false;
			if(FAILED(device->StretchRect(BackBuffer,nullptr,LeftResolveSurface,nullptr,D3DTEXF_NONE))||FAILED(device->StretchRect(RightEyeSurface,nullptr,RightResolveSurface,nullptr,D3DTEXF_NONE)))return false;
			IDirect3DStateBlock9*stateBlock=nullptr;
			if(FAILED(device->CreateStateBlock(D3DSBT_ALL,&stateBlock))||!stateBlock){if(stateBlock)stateBlock->Release();return false;}
			IDirect3DSurface9*savedRt=nullptr,*savedDepth=nullptr;D3DVIEWPORT9 savedViewport{};
			const HRESULT rtHr=device->GetRenderTarget(0,&savedRt),depthHr=device->GetDepthStencilSurface(&savedDepth),viewportHr=device->GetViewport(&savedViewport);
			const bool depthOk=SUCCEEDED(depthHr)||depthHr==D3DERR_NOTFOUND;
			if(FAILED(rtHr)||!savedRt||!depthOk||FAILED(viewportHr)){if(savedRt)savedRt->Release();if(savedDepth)savedDepth->Release();stateBlock->Release();return false;}
			bool success=false,beganScene=false;
			{InternalPassScope guard;if(SUCCEEDED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,BackBuffer))&&SUCCEEDED(SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,static_cast<IDirect3DSurface9*>(nullptr)))&&SUCCEEDED(device->BeginScene())){beganScene=true;bool setupOk=true;
				// Preserve every state submission, but do not publish stereo if any
				// setup HRESULT fails: the original SBS pixels are not proven (01511).
				setupOk = SUCCEEDED(device->SetVertexShader(nullptr)) && setupOk;
				setupOk = SUCCEEDED(device->SetPixelShader(nullptr)) && setupOk;
				setupOk = SUCCEEDED(device->SetFVF(D3DFVF_XYZRHW|D3DFVF_TEX1)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_ZENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_ZWRITEENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_ALPHABLENDENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_ALPHATESTENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_CULLMODE,D3DCULL_NONE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_LIGHTING,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_FOGENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_STENCILENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_SCISSORTESTENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetRenderState(D3DRS_SRGBWRITEENABLE,FALSE)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_COLOROP,D3DTOP_SELECTARG1)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_COLORARG1,D3DTA_TEXTURE)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_ALPHAOP,D3DTOP_SELECTARG1)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_ALPHAARG1,D3DTA_TEXTURE)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_TEXCOORDINDEX,0)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(0,D3DTSS_TEXTURETRANSFORMFLAGS,D3DTTFF_DISABLE)) && setupOk;
				setupOk = SUCCEEDED(device->SetTextureStageState(1,D3DTSS_COLOROP,D3DTOP_DISABLE)) && setupOk;
				setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_MINFILTER,D3DTEXF_LINEAR)) && setupOk;
				setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR)) && setupOk;
				setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_ADDRESSU,D3DTADDRESS_CLAMP)) && setupOk;
				setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_ADDRESSV,D3DTADDRESS_CLAMP)) && setupOk;
				setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE)) && setupOk;;D3DVIEWPORT9 full{0,0,BackBufferDesc.Width,BackBufferDesc.Height,0.0f,1.0f};const bool stateOk=setupOk&&SUCCEEDED(device->SetViewport(&full))&&SUCCEEDED(device->Clear(0,nullptr,D3DCLEAR_TARGET,D3DCOLOR_XRGB(0,0,0),1.0f,0));const bool leftOk=stateOk&&DrawTextureHalf(device,LeftResolveTexture,false);const bool rightOk=leftOk&&DrawTextureHalf(device,RightResolveTexture,true);device->SetTexture(0,nullptr);const HRESULT endHr=device->EndScene();beganScene=false;success=leftOk&&rightOk&&SUCCEEDED(endHr);}if(beganScene)device->EndScene();}
			const HRESULT applyHr=stateBlock->Apply();stateBlock->Release();bool restoreOk=SUCCEEDED(applyHr);
			if(FAILED(SetRenderTargetHook.stdcall<HRESULT>(device,0u,savedRt)))restoreOk=false;
			if(FAILED(SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,savedDepth)))restoreOk=false;
			if(FAILED(device->SetViewport(&savedViewport)))restoreOk=false;
			savedRt->Release();if(savedDepth)savedDepth->Release();
			if(!restoreOk)NoteRestoreFailure("SBS composition state restore");
			return success&&restoreOk;
		}

		bool PrepareDuplicatedDraw(IDirect3DDevice9* device,DrawStereoState& draw,
			bool& bootstrapRestoreFailed)
		{
			bootstrapRestoreFailed=false;
			if(InternalStereoPass||!StereoWanted()||!TargetIsBackBuffer())return false;if(OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire)){PoisonFrame(OutRunVR::StereoFailureOcclusionQueryActive);++OcclusionStereoRejects;if(!FirstOcclusionTrackingUnavailableLogged){FirstOcclusionTrackingUnavailableLogged=true;spdlog::error("VR stereo: occlusion-query Issue tracking unavailable; stereo duplication fails closed to single-execution mono until tracking recovers");}return false;}if(AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);++MrtRejectedDraws;if(!FirstMrtRejectLogged){FirstMrtRejectLogged=true;spdlog::info("VR stereo: auxiliary MRT active; current Present is marked incomplete");}return false;}if(ActiveOcclusionQueries.load(std::memory_order_acquire)>0){++OcclusionStereoRejects;if(!FirstOcclusionRejectLogged){FirstOcclusionRejectLogged=true;spdlog::info("VR stereo: active D3D9 occlusion query kept single-eye; query result is shared without invalidating the stereo Present");}return false;}if(!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);return false;}if(TrackedDepthStencil&&(!RightDepthSynchronized||!RightStencilSynchronized)){TryBootstrapRightDepthFromRecentClear(device,&bootstrapRestoreFailed);if(bootstrapRestoreFailed)return false;}if(TrackedDepthStencil&&!RightDepthSynchronized&&DepthTestActive(device)){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}if(TrackedDepthStencil&&!RightStencilSynchronized&&StencilTestActive(device)){PoisonFrame(OutRunVR::StereoFailureStencilUnsynchronized);return false;}OutRunVRRenderer::LatchedStereoFrame stereo{};if(!OutRunVRRenderer::GetLatchedStereoFrame(stereo)){PoisonFrame(OutRunVR::StereoFailureMissingLatchedPose);return false;}draw.stereoFrame=stereo;const EyeBuildResult classification=BuildEyeConstants(device,stereo,draw);if(classification==EyeBuildResult::FatalError){++WorldClassificationFailures;PoisonFrame(OutRunVR::StereoFailureWorldClassificationFailed);if(!FirstClassificationFailureLogged){FirstClassificationFailureLogged=true;spdlog::warn("VR stereo: verified world draw could not be classified/transformed safely; frame forced to mono fallback");}return false;}return true;
		}

		struct R7VisualTraceContext
		{
			OutRunVR::GameSemantic::PhysicalDrawCommand command{};
			OutRunVR::GameSemantic::LensOriginalCallReceipt lensInline{};
			OutRunVR::GameSemantic::LensDeferredPhysicalReceipt lensDeferred{};
			OutRunVR::GameSemantic::LensOpaqueFlushReceipt lensOpaque{};
			OutRunVR::GameSemantic::LensOpaquePmtEntryReceipt lensPmt{};
			const char* family="OTHER";
			bool enabled=false;
			bool lens=false;
		};

		const char* R7VisualTraceFamily(
			OutRunVR::GameSemantic::ProducerToken producer) noexcept
		{
			using OutRunVR::GameSemantic::ProducerToken;
			switch(producer)
			{
			case ProducerToken::StageExtensionTime:return "PLUS_TIME";
			case ProducerToken::ResultProgress:return "GOAL_PERCENT";
			case ProducerToken::ResultTextB9200:return "GOAL_TEXT";
			case ProducerToken::GoalTime020:
			case ProducerToken::GoalTime150:return "GOAL_TIME";
			case ProducerToken::OutRunStagePrintf:return "GOAL_STAGE_PRINTF";
			default:return "RESULT_OTHER";
			}
		}

		R7VisualTraceContext R7CaptureVisualTrace() noexcept
		{
			using namespace OutRunVR::GameSemantic;
			R7VisualTraceContext trace{};
			trace.command=CapturePhysicalDrawCommand();
			trace.lensInline=CurrentLensOriginalCall;
			trace.lensDeferred=CurrentLensDeferredPhysical;
			trace.lensOpaque=CurrentLensOpaqueFlush;
			trace.lensPmt=CurrentLensOpaquePmtEntry;
			trace.lens=
				trace.command.producer==ProducerToken::LensFlareCentre||
				trace.lensPmt.serial!=0||
				trace.lensOpaque.serial!=0||
				trace.lensInline.sourceSerial!=0||
				trace.lensDeferred.sourceSerial!=0||
				trace.command.scope==RenderScope::ProjectedScreenEffect2D||
				trace.command.scope==RenderScope::SceneEffect;
			trace.family=trace.lens?"LENS":R7VisualTraceFamily(trace.command.producer);
			trace.enabled=Settings::VRTelemetry&&
				(trace.lens||trace.command.IsExactFiniteResultHud());
			return trace;
		}

		void R7TraceVisualEyes(
			const R7VisualTraceContext& trace,const char* route,
			bool prepared,bool worldStereo,bool fixedFunctionWorld,
			std::uint32_t poseSequence,bool leftAttempted,HRESULT leftHr,
			bool rightAttempted,HRESULT rightHr,
			OutRunVR::StereoFailureReason rightFailure,bool restoreOk,
			OutRunVR::StereoFailureReason failureBefore,
			OutRunVR::StereoFailureReason failureAfter) noexcept
		{
			if(!trace.enabled)return;
			const bool exactPmtEntry=trace.lensPmt.serial!=0;
			const bool inlineLinked=trace.lensInline.sourceSerial!=0;
			const bool deferredCandidate=!inlineLinked&&
				trace.lensDeferred.sourceSerial!=0;
			LARGE_INTEGER qpc{};QueryPerformanceCounter(&qpc);
			const auto receiptSerial=R7VisualReceiptSerial.fetch_add(
				1,std::memory_order_relaxed)+1;
			spdlog::info(
				"VR TRACE R7 VISUAL EYES FULL: qpc={} r7Serial={} family={} route={} "
				"producer={} scope={} queued={} node=0x{:X} epoch={} prepared={} "
				"worldStereo={} fixedFunctionWorld={} pose={} "
				"leftAttempted={} left=0x{:08X} rightAttempted={} right=0x{:08X} "
				"rightFailure={} restore={} failureBefore={} failureAfter={} "
				"frameIncomplete={} rightFailed={} sourceCallSerial={} sequence={} "
				"sourceObj=0x{:06X} sourceSite={} ordinal={} windowAnchorSerial={} "
				"windowAnchorSequence={} windowAnchorObj=0x{:06X} "
				"windowAnchorOrdinal={} sourceAuthority={} opaqueFlushSerial={} "
				"opaqueFlushOrigin={} opaquePatchCount={} opaquePatchHash=0x{:016X} "
				"pmtEntrySerial={} pmtObjectId=0x{:06X} pmtObject=0x{:X} "
				"pmtNode=0x{:X} pmtMesh=0x{:X} pmtPass={} pmtFlags=0x{:08X} "
				"opaquePmtIdentity={}",
				qpc.QuadPart,receiptSerial,trace.family,
				route?route:"UNKNOWN",
				OutRunVR::GameSemantic::Name(trace.command.producer),
				OutRunVR::GameSemantic::Name(trace.command.scope),
				trace.command.queued?1:0,
				reinterpret_cast<std::uintptr_t>(trace.command.queueNode),
				trace.command.queueEpoch,prepared?1:0,worldStereo?1:0,
				fixedFunctionWorld?1:0,poseSequence,
				leftAttempted?1:0,static_cast<unsigned>(leftHr),
				rightAttempted?1:0,static_cast<unsigned>(rightHr),
				static_cast<unsigned>(rightFailure),restoreOk?1:0,
				static_cast<unsigned>(failureBefore),
				static_cast<unsigned>(failureAfter),
				FrameStereoIncomplete?1:0,FrameRightDrawFailed?1:0,
				inlineLinked?trace.lensInline.sourceSerial:0,
				inlineLinked?trace.lensInline.lastC993Sequence:
					(deferredCandidate?trace.lensDeferred.sequence:0),
				inlineLinked?trace.lensInline.objectId:
					(deferredCandidate?trace.lensDeferred.objectId:0),
				inlineLinked?static_cast<unsigned>(trace.lensInline.callsite):0,
				inlineLinked?static_cast<unsigned>(trace.lensInline.ordinal):0,
				deferredCandidate?trace.lensDeferred.sourceSerial:0,
				deferredCandidate?trace.lensDeferred.sequence:0,
				deferredCandidate?trace.lensDeferred.objectId:0,
				deferredCandidate?
					static_cast<unsigned>(trace.lensDeferred.ordinal):0,
				trace.lens?
					(exactPmtEntry?"EXACT_RETAIL_405890_404700_PMT_ENTRY":
						(inlineLinked?"INLINE_CALL_STACK_ONLY":
							(deferredCandidate?"DEFERRED_WINDOW_CANDIDATE":
								"UNOWNED_PHYSICAL"))):
					"EXACT_RESULT_PRODUCER",
				trace.lensOpaque.serial,
				OutRunVR::GameSemantic::Name(trace.lensOpaque.origin),
				trace.lensOpaque.patchCount,
				static_cast<unsigned long long>(
					trace.lensOpaque.patchLedgerHash),
				trace.lensPmt.serial,trace.lensPmt.objectId,
				trace.lensPmt.object,trace.lensPmt.node,
				trace.lensPmt.mesh,trace.lensPmt.pass,trace.lensPmt.flags,
				trace.lensPmt.serial!=0?"EXACT_405890_404700_ENTRY":
					(trace.lens?"UNVERIFIED":"NOT_APPLICABLE"));
		}

		template <typename DrawCall>
		HRESULT ExecuteStereoDraw(IDirect3DDevice9* device,DrawCall&& drawCall,bool candidateVb=false,
            bool up=false,bool indexedUp=false)
		{
			const auto visualTrace=R7CaptureVisualTrace();
			const auto failureAtEntry=FrameFailureReason;
			if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)||!IsGameDevice(device))
			{
                if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh) {
                    OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                    return E_FAIL;
                }
				RevokeDepthClearReplayBeforeLeftDraw(device);
				const HRESULT hr=drawCall();
				R7TraceVisualEyes(visualTrace,"BASE_BYPASS_SINGLE",false,false,false,0,
					true,hr,false,E_PENDING,OutRunVR::StereoFailureNone,true,
					failureAtEntry,FrameFailureReason);
				return hr;
			}
			if(StereoWanted()&&!TargetIsBackBuffer())
			{
                if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh) {
                    OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                    return E_FAIL;
                }
				if(CurrentDrawMatchesVerifiedWorld(device))
				{
					++OffscreenVerifiedWorldDraws;
					if(!FirstOffscreenWorldLogged)
					{
						FirstOffscreenWorldLogged=true;
						D3DSURFACE_DESC rtDesc{},depthDesc{};
						const bool rtOk=TrackedRenderTarget&&SUCCEEDED(TrackedRenderTarget->GetDesc(&rtDesc));
						const bool depthOk=TrackedDepthStencil&&SUCCEEDED(TrackedDepthStencil->GetDesc(&depthDesc));
						spdlog::info("VR stereo: verified auxiliary/offscreen world pass kept mono; stereo backbuffer remains eligible. rt={}x{} fmt={} msaa={} depthFmt={} depthMsaa={}",rtOk?rtDesc.Width:0u,rtOk?rtDesc.Height:0u,rtOk?static_cast<int>(rtDesc.Format):-1,rtOk?static_cast<int>(rtDesc.MultiSampleType):-1,depthOk?static_cast<int>(depthDesc.Format):-1,depthOk?static_cast<int>(depthDesc.MultiSampleType):-1);
					}
				}
				RevokeDepthClearReplayBeforeLeftDraw(device);
				const HRESULT hr=drawCall();
				R7TraceVisualEyes(visualTrace,"OFFSCREEN_SINGLE",false,false,false,0,
					true,hr,false,E_PENDING,OutRunVR::StereoFailureNone,true,
					failureAtEntry,FrameFailureReason);
				return hr;
			}

			// EXT16-007 fail-closed until the WHOLE vehicle can be staged in
			// isolated L/R color+depth and committed as one pair. R7 currently
			// writes LEFT live before RIGHT; neither HRESULT nor a late stereo
			// receipt can undo LEFT pixels if RIGHT subsequently fails.
			// Reject before the FIRST external DIP so the original 49F3E0
			// callback can draw the complete stock car in this same frame.
			if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh &&
			   !OutRunVR::DinoSidecar::MaySubmitExternalCarLiveEye()) {
				OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
				return E_FAIL;
			}
			DrawStereoState draw{};
			bool bootstrapRestoreFailed=false;
			if(!PrepareDuplicatedDraw(device,draw,bootstrapRestoreFailed))
			{
				if(bootstrapRestoreFailed){
					OutRunVR::DinoSidecar::RecordExternalPreRasterRollback(false);
					return E_FAIL; // no raw LEFT fallback on an unproven target
				}
                // A failed PBR classification is NOT permission for a mono
                // fallback DIP; no pixels have been submitted yet.
                if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh) {
                    OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                    return E_FAIL;
                }
				if(StereoWanted()&&TargetIsBackBuffer())
					InvalidateRightDepthStencilIfLeftMayWrite(device);
				RevokeDepthClearReplayBeforeLeftDraw(device);
				const HRESULT hr=drawCall();
				R7TraceVisualEyes(visualTrace,"PREPARE_REJECT_SINGLE",false,false,false,0,
					true,hr,false,E_PENDING,OutRunVR::StereoFailureNone,true,
					failureAtEntry,FrameFailureReason);
				return hr;
			}

            // The fixed-function diagnostic also needs an actual stereo
            // world owner. Never silently submit a mono external mesh.
            if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh &&
               (!draw.worldStereo || !draw.fixedFunctionWorld)) {
                OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                return E_FAIL;
            }
			// A programmable PBR DIP must have a proven world eye-pair.
            // Classification as NonWorld is not an acceptable mono draw.
            if(OutRunVR::DinoSidecar::ActiveExternalPbrStereo &&
               !draw.externalPbrWorld) {
                OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                return E_FAIL;
            }
			D3DVIEWPORT9 savedViewport{};
			if(FAILED(device->GetViewport(&savedViewport)))
			{
				InvalidateRightDepthStencilIfLeftMayWrite(device);
				PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);
                if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh) {
                    OutRunVR::DinoSidecar::ProveExternalNoPhysicalDraw();
                    return E_FAIL;
                }
				RevokeDepthClearReplayBeforeLeftDraw(device);
				const HRESULT hr=drawCall();
				R7TraceVisualEyes(visualTrace,"VIEWPORT_REJECT_SINGLE",true,
					draw.worldStereo,draw.fixedFunctionWorld,draw.poseSequence,
					true,hr,false,E_PENDING,OutRunVR::StereoFailureNone,true,
					failureAtEntry,FrameFailureReason);
				return hr;
			}
			if(draw.worldStereo)
			{
				bool leftEyeOk=false;
				{
					InternalPassScope guard;
					leftEyeOk=draw.externalPbrWorld ?
                        SetExternalPbrEyeConstants(device,draw,0) :
                        (draw.fixedFunctionWorld ?
                        SetFixedFunctionEyeTransforms(device,draw,0) :
                        SetWvpOneRegisterAtATime(device,draw.eyeConstants[0]));
				}
				if(!leftEyeOk)
				{
					bool rolledBack=false;
					{
						InternalPassScope guard;
						rolledBack=draw.externalPbrWorld ?
                            RestoreExternalPbrConstants(device,draw) :
                            (draw.fixedFunctionWorld ?
                            RestoreFixedFunctionTransforms(device,draw) :
                            RestoreWvpOneRegisterAtATime(device,draw.originalConstants));
					}
					InvalidateRightDepthStencilIfLeftMayWrite(device);
					PoisonFrame(OutRunVR::StereoFailureLeftWvpUploadFailed);
					if(!rolledBack)
						NoteRestoreFailure(draw.fixedFunctionWorld?
							"left-eye fixed-function rollback":"left-eye c64 rollback");
					if(OutRunVR::DinoSidecar::ActiveExternalStereoMesh) {
                        // Partial GPU constant upload requires rollback proof.
                        OutRunVR::DinoSidecar::RecordExternalPreRasterRollback(rolledBack);
                        return E_FAIL;
                    }
					RevokeDepthClearReplayBeforeLeftDraw(device);
					const HRESULT hr=drawCall();
                    // Partial LEFT-eye transform upload can fail during
                    // original transform rollback. An absent pair report
                    // would otherwise misclassify this as a safe soft retry.
                    OutRunVR::DinoSidecar::RecordExternalStereoMeshPair(
                        SUCCEEDED(hr),false,rolledBack,draw.poseSequence,
                        false,false,!rolledBack);
					R7TraceVisualEyes(visualTrace,"LEFT_WVP_REJECT_SINGLE",true,
						draw.worldStereo,draw.fixedFunctionWorld,draw.poseSequence,
						true,hr,false,E_PENDING,OutRunVR::StereoFailureNone,rolledBack,
						failureAtEntry,FrameFailureReason);
					return hr;
				}
			}
            // Candidate replay only on the regular two-eye physical path. All
            // fallback draws above use the invalidating raw boundary.
            const bool mirrorCandidate=candidateVb && !InternalStereoPass &&
                !FrameStereoIncomplete && !FrameRightDrawFailed &&
                !OutRunVR::DinoSidecar::ActiveExternalStereoMesh &&
                ExternalAtomicReplayEpoch==PresentEpoch;
            RevokeDepthClearReplayBeforeLeftDraw(device,mirrorCandidate);
            if(mirrorCandidate){
                const auto replay=R7ReplayInactiveDraw(device,0,TrackedRenderTarget,
                    TrackedDepthStencil,drawCall,up,indexedUp);
                if(replay==R7CandidateSeedResult::DirtyRestore){
                    if(draw.worldStereo){
                        InternalPassScope guard;
                        if(draw.externalPbrWorld)RestoreExternalPbrConstants(device,draw);
                        else if(draw.fixedFunctionWorld)RestoreFixedFunctionTransforms(device,draw);
                        else RestoreWvpOneRegisterAtATime(device,draw.originalConstants);
                    }
                    RightDepthSynchronized=false;RightStencilSynchronized=false;
                    LastMainDepthClearStamp.Invalidate();
                    NoteRestoreFailure("external inactive left replay");
                    return E_FAIL;
                }
            }
			const HRESULT leftHr=drawCall();
			if(FAILED(leftHr))
			{
                ExternalAtomicReplayEpoch=0;
				InvalidateRightDepthStencilIfLeftMayWrite(device);
				PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);
				bool restored=true;
				if(draw.worldStereo)
				{
					restored=false;
					{
						InternalPassScope guard;
						restored=draw.externalPbrWorld ?
                            RestoreExternalPbrConstants(device,draw) :
                            (draw.fixedFunctionWorld ?
                            RestoreFixedFunctionTransforms(device,draw) :
                            RestoreWvpOneRegisterAtATime(device,draw.originalConstants));
					}
					if(!restored)
						NoteRestoreFailure(draw.fixedFunctionWorld?
							"left draw fixed-function transforms":"left draw c64");
				}
                OutRunVR::DinoSidecar::RecordExternalStereoMeshPair(
                    false,false,restored,draw.poseSequence,false,false,!restored);
				R7TraceVisualEyes(visualTrace,"LEFT_DRAW_FAILURE",true,
					draw.worldStereo,draw.fixedFunctionWorld,draw.poseSequence,
					true,leftHr,false,E_PENDING,OutRunVR::StereoFailureNone,restored,
					failureAtEntry,FrameFailureReason);
				return leftHr;
			}
			IDirect3DSurface9*savedRt=TrackedRenderTarget,*savedDepth=TrackedDepthStencil;
			HRESULT rightHr=D3D_OK;
			OutRunVR::StereoFailureReason rightFailure=OutRunVR::StereoFailureRightStateFailed;
			bool restoreOk=true;
			bool rightDrawAttempted=false;
			{
				InternalPassScope guard;
				rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);
				if(SUCCEEDED(rightHr))
					rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);
				if(SUCCEEDED(rightHr))
					rightHr=device->SetViewport(&savedViewport);
				if(SUCCEEDED(rightHr)&&draw.worldStereo)
				{
					const bool eyeOk=draw.externalPbrWorld ?
                        SetExternalPbrEyeConstants(device,draw,1) :
                        (draw.fixedFunctionWorld ?
                        SetFixedFunctionEyeTransforms(device,draw,1) :
                        SetWvpOneRegisterAtATime(device,draw.eyeConstants[1]));
					if(!eyeOk)
					{
						rightFailure=OutRunVR::StereoFailureRightWvpUploadFailed;
						rightHr=E_FAIL;
					}
				}
                if(SUCCEEDED(rightHr)&&mirrorCandidate&&ExternalAtomicReplayEpoch==PresentEpoch){
                    const auto replay=R7ReplayInactiveDraw(device,1,RightEyeSurface,RightEyeDepth,
                        drawCall,up,indexedUp);
                    if(replay==R7CandidateSeedResult::DirtyRestore){
                        rightFailure=OutRunVR::StereoFailureRestoreFailed;
                        rightHr=E_FAIL;
                        LastMainDepthClearStamp.Invalidate();
                        RightDepthSynchronized=false;RightStencilSynchronized=false;
                        NoteRestoreFailure("external inactive right replay");
                    }
                }
				if(SUCCEEDED(rightHr))
				{
					rightFailure=OutRunVR::StereoFailureRightDrawFailed;
					rightDrawAttempted=true;
					rightHr=drawCall();
				}
				restoreOk=RestoreRightPassState(device,savedRt,savedDepth,
					savedViewport,draw.originalConstants,
					draw.worldStereo&&!draw.fixedFunctionWorld);
				if(draw.externalPbrWorld) {
                    if(!RestoreExternalPbrConstants(device,draw))restoreOk=false;
                } else if(draw.fixedFunctionWorld &&
                          !RestoreFixedFunctionTransforms(device,draw))
                    restoreOk=false;
			}
			if(FAILED(rightHr)||!restoreOk)ExternalAtomicReplayEpoch=0;
			FrameHadDuplicatedDraw=true;
			++DuplicatedDraws;
			if(draw.worldStereo)
			{
				if(FrameStereoPoseSequence==0)
				{
					FrameStereoPoseSequence=draw.poseSequence;
					FrameStereoMetadata=draw.stereoFrame;
				}
				else if(FrameStereoPoseSequence!=draw.poseSequence)
				{
					FrameRightDrawFailed=true;
					PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);
					if(!FramePoseMismatchLogged)
					{
						FramePoseMismatchLogged=true;
						++PoseSequenceMismatchFrames;
						spdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");
					}
				}
				FrameHadWorldStereo=true;
				++WorldStereoDraws;
				if(!FirstWorldStereoLogged)
				{
					FirstWorldStereoLogged=true;
					spdlog::info("VR stereo: TRUE GEOMETRY STEREO active; per-eye c64 + OpenXR asymmetric FOV confirmed");
				}
			}
			else
				++NonWorldDuplicatedDraws;
			if(FAILED(rightHr))
			{
				FrameRightDrawFailed=true;
				InvalidateRightDepthStencilIfLeftMayWrite(device);
				PoisonFrame(rightFailure);
			}
			if(!restoreOk)
			{
				InvalidateRightDepthStencilIfLeftMayWrite(device);
				NoteRestoreFailure("right-eye draw");
			}
            // Stereo routing alone is not evidence of binocular geometry:
            // identical LEFT/RIGHT view+projection pairs render mono twice.
            // Evaluate the 16-float matrices only for an active external DIP.
            const bool externalDistinctEyes=
                draw.worldStereo && draw.fixedFunctionWorld &&
                OutRunVR::DinoSidecar::ActiveExternalStereoMesh != nullptr &&
                sizeof(D3DMATRIX)==16u*sizeof(float) &&
                OutRunVR::DinoSidecar::DistinctFiniteExternalEyeTransforms(
                    reinterpret_cast<const float*>(&draw.fixedEyeView[0]),
                    reinterpret_cast<const float*>(&draw.fixedEyeView[1]),
                    reinterpret_cast<const float*>(&draw.fixedEyeProjection[0]),
                    reinterpret_cast<const float*>(&draw.fixedEyeProjection[1]));
			OutRunVR::DinoSidecar::RecordExternalStereoMeshPair(
                SUCCEEDED(leftHr),rightDrawAttempted&&SUCCEEDED(rightHr),
                restoreOk&&!FrameStereoIncomplete&&
                    FrameFailureReason==OutRunVR::StereoFailureNone,
                draw.poseSequence,externalDistinctEyes,
                FAILED(rightHr),!restoreOk); // physical D3D and restore evidence
            R7TraceVisualEyes(visualTrace,"STEREO_PAIR",true,
				draw.worldStereo,draw.fixedFunctionWorld,draw.poseSequence,
				true,leftHr,rightDrawAttempted,rightHr,rightFailure,restoreOk,
				failureAtEntry,FrameFailureReason);
			// Keep v0.03's normal game HRESULT, but external mesh
            // calls must not propagate LEFT S_OK after RIGHT/restore failure.
            return OutRunVR::DinoSidecar::CanCompleteExternalStereoDraw(
                SUCCEEDED(leftHr),
                OutRunVR::DinoSidecar::ActiveExternalStereoMesh)
                ? leftHr : E_FAIL;
		}

		HRESULT __stdcall DrawPrimitiveDest(IDirect3DDevice9*device,D3DPRIMITIVETYPE type,UINT startVertex,UINT primitiveCount){auto call=[&](){return DrawPrimitiveHook.stdcall<HRESULT>(device,type,startVertex,primitiveCount);};return ExecuteStereoDraw(device,call,true);}
		HRESULT __stdcall DrawIndexedPrimitiveDest(IDirect3DDevice9*device,D3DPRIMITIVETYPE type,INT baseVertexIndex,UINT minVertexIndex,UINT numVertices,UINT startIndex,UINT primitiveCount)
		{
			const auto pmt=OutRunVR::GameSemantic::CurrentLensOpaquePmtEntry;
			if(Settings::VRTelemetry&&pmt.serial!=0)
			{
				static std::atomic<std::uint64_t> pmtDipSerial{0};
				const auto dipSerial=pmtDipSerial.fetch_add(
					1,std::memory_order_relaxed)+1;
				LARGE_INTEGER qpc{};QueryPerformanceCounter(&qpc);
				spdlog::info(
					"VR TRACE LENS PMT DIP FULL: qpc={} dipSerial={} "
					"pmtEntrySerial={} flushSerial={} flushOrigin={} "
					"objectId=0x{:06X} target570008={} object=0x{:X} "
					"node=0x{:X} mesh=0x{:X} pass={} flags=0x{:08X} "
					"type={} baseVertex={} minVertex={} numVertices={} "
					"startIndex={} primitiveCount={} "
					"authority=EXACT_404700_NATIVE_DIP",
					qpc.QuadPart,dipSerial,pmt.serial,pmt.flushSerial,
					OutRunVR::GameSemantic::Name(pmt.flushOrigin),
					pmt.objectId,pmt.objectId==0x570008u?1:0,
					pmt.object,pmt.node,pmt.mesh,pmt.pass,pmt.flags,
					static_cast<unsigned>(type),baseVertexIndex,minVertexIndex,
					numVertices,startIndex,primitiveCount);
			}
			const bool passengerDip=
				OutRunVR::QuestCockpitV2::ExactPassengerRenderActive();
			auto call=[&](){return DrawIndexedPrimitiveHook.stdcall<HRESULT>(
				device,type,baseVertexIndex,minVertexIndex,numVertices,startIndex,
				primitiveCount);};
			const HRESULT result=ExecuteStereoDraw(device,call,true);
			if(passengerDip)
			{
				static const bool diagEnabled=[]() noexcept {
					char value[8]{};
					const DWORD n=GetEnvironmentVariableA(
						"OUTRUN_VR_PASSENGER_DIAG",value,
						static_cast<DWORD>(sizeof(value)));
					return n==1u&&value[0]=='1';
				}();
				if(diagEnabled)
				{
					static thread_local std::uint64_t passengerDipSerial=0;
					const auto serial=++passengerDipSerial;
					if(serial<=32u||serial%180u==0u)
						spdlog::info(
							"VR PASSENGER NATIVE DIP: count={} hr=0x{:08X} "
							"type={} baseVertex={} minVertex={} numVertices={} "
							"startIndex={} primitiveCount={} scope={} "
							"producer={} authority=D3D9_DIP_VTABLE_82",
							serial,static_cast<std::uint32_t>(result),
							static_cast<unsigned>(type),baseVertexIndex,
							minVertexIndex,numVertices,startIndex,primitiveCount,
							OutRunVR::GameSemantic::Name(
								OutRunVR::GameSemantic::EffectiveScope()),
							OutRunVR::GameSemantic::Name(
								OutRunVR::GameSemantic::CurrentRenderProducerToken()));
				}
			}
			return result;
		}
        HRESULT __stdcall DrawPrimitiveUPDest(IDirect3DDevice9*device,D3DPRIMITIVETYPE type,UINT primitiveCount,const void*data,UINT stride)
        {
            auto call=[&](){return DrawPrimitiveUPHook.stdcall<HRESULT>(device,type,primitiveCount,data,stride);};
            if(InternalStereoPass&&!OutRunVR::DinoSidecar::ActiveExternalStereoMesh)
                return R7ExecuteRawCandidateVb(device,call,true);
            return ExecuteStereoDraw(device,call,true,true);
        }
        HRESULT __stdcall DrawIndexedPrimitiveUPDest(IDirect3DDevice9*device,D3DPRIMITIVETYPE type,UINT minVertexIndex,UINT numVertices,UINT primitiveCount,const void*indexData,D3DFORMAT indexFormat,const void*vertexData,UINT stride)
        {
            auto call=[&](){return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device,type,minVertexIndex,numVertices,primitiveCount,indexData,indexFormat,vertexData,stride);};
            if(InternalStereoPass&&!OutRunVR::DinoSidecar::ActiveExternalStereoMesh)
                return R7ExecuteRawCandidateVb(device,call,true,true);
            return ExecuteStereoDraw(device,call,true,true,true);
        }

		HRESULT __stdcall ClearDest(IDirect3DDevice9*device,DWORD count,const D3DRECT*rects,DWORD flags,D3DCOLOR color,float z,DWORD stencil)
		{
			if(!IsGameDevice(device))
                return ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);
            if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)){
                ExternalAtomicReplayEpoch=0;
                return ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);
            }
            if(InternalStereoPass){
                auto call=[&](){return ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);};
                return R7ExecuteRawCandidateVb(device,call,false,false,flags);
            }
            // A subsequent eligible Clear must update the existing isolated pair.
            // Never reseed from a partial/color-only clear or discard a valid
            // scene solely because the game clears its depth between passes.
            LastMainDepthClearStamp.OnPotentialWrite(flags&(D3DCLEAR_ZBUFFER|D3DCLEAR_STENCIL));
            const bool candidate=StereoWanted()&&TargetIsBackBuffer();
            bool duplicate=candidate;
            if(duplicate&&AnyAuxRenderTargetActive()){
                PoisonFrame(OutRunVR::StereoFailureMrtActive);duplicate=false;
            }
            if(duplicate&&!EnsureStereoResources(device)){
                PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);duplicate=false;
            }
            if(!duplicate||FrameStereoIncomplete||FrameRightDrawFailed)
                ExternalAtomicReplayEpoch=0;
            auto clearCall=[&](){return ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);};
            if(ExternalAtomicReplayEpoch==PresentEpoch){
                const auto replay=R7ReplayInactiveEye(device,0,TrackedRenderTarget,TrackedDepthStencil,clearCall);
                if(replay!=R7CandidateSeedResult::Seeded)ExternalAtomicReplayEpoch=0;
                if(replay==R7CandidateSeedResult::DirtyRestore){
                    RightDepthSynchronized=false;RightStencilSynchronized=false;
                    LastMainDepthClearStamp.Invalidate();
                    NoteRestoreFailure("external inactive LEFT clear");
                    return E_FAIL;
                }
            }
            const HRESULT leftHr=clearCall();
            if(SUCCEEDED(leftHr))RecordFullMainDepthClear(device,count,rects,flags,z,stencil);
            if(!duplicate||FAILED(leftHr)){
                ExternalAtomicReplayEpoch=0;
                if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);
                if(SUCCEEDED(leftHr)&&candidate){
                    if(flags&D3DCLEAR_ZBUFFER)RightDepthSynchronized=false;
                    if((flags&D3DCLEAR_STENCIL)&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;
                }
                return leftHr;
            }
            D3DVIEWPORT9 savedViewport{};
            if(FAILED(device->GetViewport(&savedViewport))){
                ExternalAtomicReplayEpoch=0;
                if(flags&D3DCLEAR_ZBUFFER)RightDepthSynchronized=false;
                if((flags&D3DCLEAR_STENCIL)&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;
                PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;
            }
            IDirect3DSurface9* savedRt=TrackedRenderTarget,*savedDepth=TrackedDepthStencil;
            HRESULT rightHr=D3D_OK;
            bool restoreOk=true,candidateDirty=false;
            {
                InternalPassScope guard;
                rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);
                if(SUCCEEDED(rightHr))rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);
                if(SUCCEEDED(rightHr))rightHr=device->SetViewport(&savedViewport);
                if(SUCCEEDED(rightHr)&&ExternalAtomicReplayEpoch==PresentEpoch){
                    const auto replay=R7ReplayInactiveEye(device,1,RightEyeSurface,RightEyeDepth,clearCall);
                    if(replay!=R7CandidateSeedResult::Seeded)ExternalAtomicReplayEpoch=0;
                    candidateDirty=replay==R7CandidateSeedResult::DirtyRestore;
                }
                if(SUCCEEDED(rightHr)&&!candidateDirty)rightHr=clearCall();
                restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);
            }
            if(FAILED(rightHr)||!restoreOk||candidateDirty)ExternalAtomicReplayEpoch=0;
            // A dirty RT/depth/viewport restore invalidates attachment identity,
            // even when the requested Clear only wrote color. Do not certify
            // full coverage or replay the saved LEFT depth receipt afterwards.
            if(!restoreOk||candidateDirty){
                RightDepthSynchronized=false;
                RightStencilSynchronized=false;
                LastMainDepthClearStamp.Invalidate();
                NoteRestoreFailure("right-eye clear");
                return E_FAIL;
            }
            if(FAILED(rightHr)){FrameRightDrawFailed=true;if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if(ClearCoversStereoBackbuffer(device,count,rects)){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=true;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=true;
                if(ExternalAtomicReplayEpoch!=PresentEpoch&&!FrameStereoIncomplete&&!FrameRightDrawFailed&&
                    (flags&(D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER))==(D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER)&&
                    (Settings::VRExternalFerrariTest||Settings::VRF50ExternalModel))
                {
                    const auto seed=R7BeginExternalAtomicResourceTransaction(device,savedViewport,flags,color,z,stencil);
                    if(seed==R7CandidateSeedResult::DirtyRestore){
                        RightDepthSynchronized=false;RightStencilSynchronized=false;
                        LastMainDepthClearStamp.Invalidate();
                        NoteRestoreFailure("external inactive-pair seed");
                        return E_FAIL;
                    }
                }
            }return leftHr;
		}

		HRESULT __stdcall SetRenderTargetDest(IDirect3DDevice9*device,DWORD index,IDirect3DSurface9*surface){const HRESULT hr=SetRenderTargetHook.stdcall<HRESULT>(device,index,surface);if(!InternalStereoPass&&IsGameDevice(device)&&SUCCEEDED(hr)){if(index==0){if(TrackedRenderTarget!=surface)ExternalAtomicReplayEpoch=0;ReplaceSurfaceRef(TrackedRenderTarget,surface);}else if(index>=1&&index<=3){if(surface)ExternalAtomicReplayEpoch=0;AuxRenderTargetActive[index-1]=surface!=nullptr;}}return hr;}
		HRESULT __stdcall SetDepthStencilSurfaceDest(IDirect3DDevice9*device,IDirect3DSurface9*surface)
		{
			const HRESULT hr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,surface);
			if(!InternalStereoPass&&IsGameDevice(device)&&SUCCEEDED(hr))
			{
				const bool changed=TrackedDepthStencil!=surface;
                if(changed)ExternalAtomicReplayEpoch=0;
				LastMainDepthClearStamp.OnBindingChange(changed);
				if(changed) TrackedStencilFormatKnown=false;
				ReplaceSurfaceRef(TrackedDepthStencil,surface);
				if(changed&&StereoResourcesReady&&TargetIsBackBuffer())
				{
					if(!surface)
					{
						ReleaseCom(RightEyeDepth);
						RightDepthSynchronized=true;
						RightStencilSynchronized=true;
					}
					else
					{
						D3DSURFACE_DESC leftDesc{},rightDesc{};
						const bool compatible=RightEyeDepth&&
							SUCCEEDED(surface->GetDesc(&leftDesc))&&
							SUCCEEDED(RightEyeDepth->GetDesc(&rightDesc))&&
							leftDesc.Width==BackBufferDesc.Width&&leftDesc.Height==BackBufferDesc.Height&&
							rightDesc.Width==BackBufferDesc.Width&&rightDesc.Height==BackBufferDesc.Height&&
							leftDesc.Format==rightDesc.Format&&
							leftDesc.MultiSampleType==rightDesc.MultiSampleType&&
							leftDesc.MultiSampleQuality==rightDesc.MultiSampleQuality;
						if(compatible)
						{
							// Descriptor compatibility proves only that the existing RIGHT
							// allocation can be reused. A different LEFT COM surface has
							// independent contents, so the previous synchronization proof
							// must not survive this identity transition (review 01512).
							RightDepthSynchronized=false;
							RightStencilSynchronized=!FormatHasStencil(leftDesc.Format);
							if(!FirstMainDepthReuseLogged)
							{
								FirstMainDepthReuseLogged=true;
								spdlog::info("VR stereo: compatible main depth identity changed; reusing right-eye allocation with content sync invalidated");
							}
						}
						else
						{
							if(FrameHadDuplicatedDraw||FrameHadWorldStereo)
								PoisonFrame(OutRunVR::StereoFailureDepthStateChanged);
							if(!CreateRightDepthForTracked(device))
								StereoResourcesReady=false;
						}
					}
				}
			}
			return hr;
		}

		HRESULT __stdcall QueryIssueDest(IDirect3DQuery9*query,DWORD issueFlags){const HRESULT hr=QueryIssueHook.stdcall<HRESULT>(query,issueFlags);if(FAILED(hr)||!query||query->GetType()!=D3DQUERYTYPE_OCCLUSION)return hr;IDirect3DDevice9*queryDevice=nullptr;if(FAILED(query->GetDevice(&queryDevice))||!queryDevice)return hr;const bool gameQuery=IsGameDevice(queryDevice);queryDevice->Release();if(!gameQuery)return hr;if((issueFlags&D3DISSUE_BEGIN)!=0){ActiveOcclusionQueries.fetch_add(1,std::memory_order_acq_rel);++OcclusionQueryBegins;}if((issueFlags&D3DISSUE_END)!=0){int current=ActiveOcclusionQueries.load(std::memory_order_acquire);while(current>0&&!ActiveOcclusionQueries.compare_exchange_weak(current,current-1,std::memory_order_acq_rel,std::memory_order_acquire)){}++OcclusionQueryEnds;}return hr;}
		HRESULT __stdcall CreateQueryDest(IDirect3DDevice9*device,D3DQUERYTYPE type,IDirect3DQuery9**query){const HRESULT hr=CreateQueryHook.stdcall<HRESULT>(device,type,query);if(!IsGameDevice(device)||FAILED(hr)||type!=D3DQUERYTYPE_OCCLUSION||!query||!*query)return hr;++OcclusionQueriesCreated;if(!QueryIssueHook){void**queryVtable=*reinterpret_cast<void***>(*query);if(queryVtable)QueryIssueHook=safetyhook::create_inline(queryVtable[QueryIssueVtableIndex],QueryIssueDest);if(QueryIssueHook){OcclusionQueryTrackingUnavailable.store(false,std::memory_order_release);spdlog::info("VR stereo: occlusion-query Issue hook armed; active query draws remain single-eye without invalidating stereo frames");}else{OcclusionQueryTrackingUnavailable.store(true,std::memory_order_release);spdlog::error("VR stereo: failed to hook IDirect3DQuery9::Issue; stereo duplication disabled fail-closed for query safety");}}return hr;}
		HRESULT __stdcall SetVertexShaderDest(IDirect3DDevice9*device,IDirect3DVertexShader9*shader){const HRESULT hr=SetVertexShaderHook.stdcall<HRESULT>(device,shader);if(!InternalStereoPass&&IsGameDevice(device)&&SUCCEEDED(hr)){const std::uintptr_t next=reinterpret_cast<std::uintptr_t>(shader),previous=CurrentVertexShaderIdentity.load(std::memory_order_acquire);if(next!=previous){CurrentVertexShaderIdentity.store(next,std::memory_order_release);std::uint64_t serial=VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel)+1;if(serial==0)VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel);}}return hr;}

		void MaybeLogSummary()
		{
			if(!Settings::VRTelemetry)return;const ULONGLONG now=GetTickCount64();if(now-LastSummaryMs<5000)return;LastSummaryMs=now;const DWORD gamePid=GetCurrentProcessId();const DWORD hostPid=SharedState?SharedState->hostPid:0;spdlog::info("VR identity: gameBuild={} gamePid={} hostPid={} runKey={}-{}",OUTRUN_VR_BUILD_SHA,gamePid,hostPid,hostPid,gamePid);spdlog::info("VR stereo: draws={} world={} ui/effect={} fixedFn={} fixedFnWorld={} offscreenWorld={} classifyFail={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseMismatchFrames={} multiBeginPresent={} maxBeginPerPresent={} poseSeq={} direct[frames={},fallbacks={},fenceTimeout={}] occ[created={},begin={},end={},active={},reject={}] depthSync[fullClear={},bootstrapTry={},bootstrapOk={}] failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={},rightState={},rightWvp={},rightDraw={},restore={},compose={},present={},depthState={},poseMismatch={},offscreen={},occlusion={}]",DuplicatedDraws,WorldStereoDraws,NonWorldDuplicatedDraws,FixedFunctionNonWorldDraws,FixedFunctionWorldStereoDraws,OffscreenVerifiedWorldDraws,WorldClassificationFailures,StereoComposeSuccess,StereoComposeFailure,FrameRightDrawFailed?1:0,MrtRejectedDraws,RestoreFailures,PoseSequenceMismatchFrames,MultiBeginScenePresents,MaxBeginScenesPerPresent,FrameStereoPoseSequence,DirectTransportFrames,DirectTransportFallbacks,DirectTransportFenceTimeouts,OcclusionQueriesCreated,OcclusionQueryBegins,OcclusionQueryEnds,ActiveOcclusionQueries.load(std::memory_order_acquire),OcclusionStereoRejects,FullMainDepthClears,DepthBootstrapAttempts,DepthBootstrapSuccesses,FailureCounts[OutRunVR::StereoFailureMissingLatchedPose],FailureCounts[OutRunVR::StereoFailureResourceUnavailable],FailureCounts[OutRunVR::StereoFailureMrtActive],FailureCounts[OutRunVR::StereoFailureViewportUnavailable],FailureCounts[OutRunVR::StereoFailureWorldClassificationFailed],FailureCounts[OutRunVR::StereoFailureDepthUnsynchronized],FailureCounts[OutRunVR::StereoFailureStencilUnsynchronized],FailureCounts[OutRunVR::StereoFailureClearFailed],FailureCounts[OutRunVR::StereoFailureRightStateFailed],FailureCounts[OutRunVR::StereoFailureRightWvpUploadFailed],FailureCounts[OutRunVR::StereoFailureRightDrawFailed],FailureCounts[OutRunVR::StereoFailureRestoreFailed],FailureCounts[OutRunVR::StereoFailureComposeFailed],FailureCounts[OutRunVR::StereoFailurePresentFailed],FailureCounts[OutRunVR::StereoFailureDepthStateChanged],FailureCounts[OutRunVR::StereoFailurePoseSequenceMismatch],FailureCounts[OutRunVR::StereoFailureOffscreenWorld],FailureCounts[OutRunVR::StereoFailureOcclusionQueryActive]);
		}

		// Original 4521C0 sky ownership has not yet been attested in this
        // rendering lane. Count only fixed-function sky-like classifications
        // and stereo failure transitions. This is a bounded A/B discriminator,
        // not a generic per-draw logger; no game GPU state is modified.
        void MaybeLogCockpitSkyProbe(bool requested,bool composed,
            bool direct,HRESULT presentHr) noexcept
        {
            if (!Settings::VRQuestCockpitV2Enabled ||
                !Settings::VRQuestCockpitV2SkyProbe) return;
            static std::uint32_t frames=0,skyFrames=0,badFrames=0;
            static std::uint32_t rightFailures=0,poisoned=0,depthMissing=0;
            static std::uint64_t lastSky=0,windowSky=0,windowWorld=0,windowShaderDepthOff=0;
            static std::uint64_t windowShaderNonSkyDepthOff=0;
            static std::uint64_t windowExact=0,windowNative=0,
                windowFallback=0,windowMixed=0,windowSwitches=0;
            static std::uint64_t totalPresent=0;
            static bool sawRequested=false,sawComposed=false,sawDirect=false;
            ++frames;
            ++totalPresent;
            sawRequested |= requested;
            sawComposed |= composed;
            sawDirect |= direct;
            if(FixedFunctionSkyRotationOnlyDraws>lastSky) ++skyFrames;
            lastSky=FixedFunctionSkyRotationOnlyDraws;
            if(FrameStereoIncomplete) ++badFrames;
            if(FrameRightDrawFailed) ++rightFailures;
            if(FrameFailureReason!=OutRunVR::StereoFailureNone) ++poisoned;
            if(!RightDepthSynchronized) ++depthMissing;
            if(frames>=90) {
                spdlog::info(
                    "VR SKY PROBE: present={} samples={} skyLikeFrames={} "
                    "skyLikeDraws={} otherFixedWorldDraws={} shaderDepthOffWorldDraws={} "
                    "shaderNonSkyDepthOffDraws={} shaderExactSkyDraws={} shaderSkyNative={} "
                    "shaderSkyFallback={} shaderSkyMixedEyes={} "
                    "shaderSkyModeSwitches={} incomplete={} "
                    "rightFailed={} poisoned={} depthUnsynced={} "
                    "requested={} composed={} direct={} lastFailure={} presentHr={}",
                    totalPresent,frames,skyFrames,
                    FixedFunctionSkyRotationOnlyDraws-windowSky,
                    FixedFunctionWorldStereoDraws-windowWorld,
                    ProgrammableDepthOffWorldDraws-windowShaderDepthOff,
                    ProgrammableNonSkyDepthOffWorldDraws-windowShaderNonSkyDepthOff,
                    ProgrammableExactWorldSkyDraws-windowExact,
                    ProgrammableSkyNativeViewDraws-windowNative,
                    ProgrammableSkyFallbackViewDraws-windowFallback,
                    ProgrammableSkyMixedEyeDraws-windowMixed,
                    ProgrammableSkyViewModeSwitches-windowSwitches,
                    badFrames,rightFailures,poisoned,depthMissing,
                    sawRequested,sawComposed,sawDirect,
                    static_cast<unsigned>(FrameFailureReason),
                    static_cast<unsigned>(presentHr));
                frames=skyFrames=badFrames=0;
                rightFailures=poisoned=depthMissing=0;
                sawRequested=sawComposed=sawDirect=false;
                windowSky=FixedFunctionSkyRotationOnlyDraws;
                windowWorld=FixedFunctionWorldStereoDraws;
                windowShaderDepthOff=ProgrammableDepthOffWorldDraws;
                windowShaderNonSkyDepthOff=ProgrammableNonSkyDepthOffWorldDraws;
                windowExact=ProgrammableExactWorldSkyDraws;
                windowNative=ProgrammableSkyNativeViewDraws;
                windowFallback=ProgrammableSkyFallbackViewDraws;
                windowMixed=ProgrammableSkyMixedEyeDraws;
                windowSwitches=ProgrammableSkyViewModeSwitches;
            }
        }

        HRESULT __stdcall PresentDest(IDirect3DDevice9*device,const RECT*sourceRect,const RECT*destRect,HWND destWindowOverride,const RGNDATA*dirtyRegion)
		{
			if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)||!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);
			const std::uint64_t beginNow=OutRunVRRenderer::GetBeginSceneCallCount(),beginDelta=beginNow>=LastBeginSceneCountAtPresent?beginNow-LastBeginSceneCountAtPresent:0;LastBeginSceneCountAtPresent=beginNow;if(GameplayActive()){if(beginDelta>1)++MultiBeginScenePresents;MaxBeginScenesPerPresent=std::max(MaxBeginScenesPerPresent,beginDelta);}

			const bool stereoRequested=StereoWanted();
			const std::uint32_t pendingFrameId=stereoRequested?NextStereoFrameId():0;
			const bool stereoFrameEligible=
				stereoRequested&&FrameHadWorldStereo&&FrameHadDuplicatedDraw&&
				!FrameRightDrawFailed&&!FrameStereoIncomplete&&
				FrameStereoPoseSequence&&FrameStereoMetadata.valid&&
				EnsureStereoResources(device);

			bool composedStereo=false;
			bool directTransport=false;
			bool directOnlyHold=false;
			std::uint32_t pendingPoseSequence=0;

			auto markDirectOnlyHold=[&]()
			{
				if(directOnlyHold)return;
				directOnlyHold=true;
				++DirectTransportFallbacks;
				if(!FirstDirectDeferredLogged)
				{
					FirstDirectDeferredLogged=true;
					spdlog::warn("VR DIRECT-ONLY: shared-eye frame deferred without blocking; incomplete handles are never published and OpenXR reuses the last safe projection");
				}
			};

			if(stereoFrameEligible)
			{
				if(HostDirectTransportReady())
					directTransport=ResolveDirectTransport(device,pendingFrameId);

				if(directTransport)
				{
					composedStereo=true;
					pendingPoseSequence=FrameStereoPoseSequence;
					if(!FirstDirectTransportLogged)
					{
						FirstDirectTransportLogged=true;
						spdlog::info("VR stereo: 4-slot direct GPU transport uses bounded post-Present completion; source eye={}x{}",BackBufferDesc.Width,BackBufferDesc.Height);
					}
				}
				else if(Settings::VRDirectGpuOnly && Settings::VRHmdlessDebugMode == 0)
				{
					markDirectOnlyHold();
				}
				else if(ComposeSbs(device))
				{
					++StereoComposeSuccess;
					composedStereo=true;
					pendingPoseSequence=FrameStereoPoseSequence;
					++DirectTransportFallbacks;
					if(!FirstDirectFallbackLogged)
					{
						FirstDirectFallbackLogged=true;
						spdlog::warn("VR stereo: direct transport not ready; keeping SBS/Desktop Duplication fallback");
					}
				}
				else
				{
					++StereoComposeFailure;
					PoisonFrame(OutRunVR::StereoFailureComposeFailed);
				}
			}

			MaybeLogSummary();
			LARGE_INTEGER presentStart{};
			QueryPerformanceCounter(&presentStart);

			// Never advertise DirectGPU handles before their event query completes.
			// The classic path keeps its existing pre-Present correlation marker.
			if(OutRunVR::DirectGpuHold::PublishPrePresentMono(
					stereoRequested,directTransport,directOnlyHold))
				PublishRenderFrame(OutRunVR::StereoSbsFallbackMono,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,FrameFailureReason,nullptr,true,false);

			const HRESULT hr=PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);

			if(directTransport)
			{
				if(SUCCEEDED(hr)&&DirectTransportFrameReadyAfterPresent(pendingFrameId))
				{
					++DirectTransportFrames;
				}
				else
				{
					directTransport=false;
					composedStereo=false;
					markDirectOnlyHold();
				}
			}

			if(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete)
			{
				PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,pendingFrameId);
				PublishRenderFrame(OutRunVR::StereoSbsActive,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata,false,directTransport);
				if(!FirstStereoActiveLogged)
				{
					FirstStereoActiveLogged=true;
					spdlog::info("VR stereo: TRUE STEREO active; transport={} sourceEye={}x{} PC={}",directTransport?"verified D3D9Ex->D3D11 ring":"SBS Desktop Duplication",BackBufferDesc.Width,BackBufferDesc.Height,(directTransport&&HostDirectTransportReady())?"left-eye mirror":"SBS fallback");
				}
			}
			else if(!(directOnlyHold&&stereoFrameEligible&&SUCCEEDED(hr)))
			{
				if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)PoisonFrame(OutRunVR::StereoFailurePresentFailed);
				const std::uint32_t fallback=stereoRequested?OutRunVR::StereoSbsFallbackMono:OutRunVR::StereoDisabled;
				PublishStereoState(fallback,false,0,0);
				PublishRenderFrame(fallback,0,0,presentStart.QuadPart,FrameFailureReason,nullptr);
			}
			// A transient DirectGPU miss in direct-only mode deliberately leaves the
			// previous valid stereo metadata intact. The host already owns/reuses the
			// last released OpenXR projection, avoiding a black/corrupt mode flip.

			OutRunVRRenderer::NotifyGamePresent();
			OutRunVR::Pacing::GamePresentComplete();
            MaybeLogCockpitSkyProbe(stereoRequested,composedStereo,
                directTransport,hr);
			FrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FramePoseMismatchLogged=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};ExternalAtomicReplayEpoch=0;if(++PresentEpoch==0)PresentEpoch=1;return hr;
		}

		HRESULT __stdcall ResetDest(IDirect3DDevice9*device,D3DPRESENT_PARAMETERS*params){if(!StereoBaseCallbacksArmed.load(std::memory_order_acquire)||!IsGameDevice(device))return ResetHook.stdcall<HRESULT>(device,params);R7ResetNotificationScope notification;const auto previousDepthGeneration=R7AutomaticDepthGeneration;InvalidateTrackedRenderStates();notification.Notify();R7ForgetAutomaticDepthProof();ReleaseStereoResources();AuxRenderTargetActive={};ActiveOcclusionQueries.store(0,std::memory_order_release);CurrentVertexShaderIdentity.store(0,std::memory_order_release);VertexShaderSerial.store(0,std::memory_order_release);LastStereoWanted=false;RightStencilSynchronized=true;FramePoseMismatchLogged=false;FirstMainDepthReuseLogged=false;FirstMainClearLogged=false;FirstDepthBootstrapLogged=false;PresentEpoch=1;QuestNativePairLatch={};LastMainDepthClearStamp.Invalidate();LastMainDepthClearZ=1.0f;LastMainDepthClearStencil=0;LastMainDepthClearDesc={};LastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState(OutRunVR::StereoDisabled,false,0,0);PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,OutRunVR::StereoFailureNone,nullptr);HRESULT hr=D3DERR_INVALIDCALL;if(OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device)){if(!OutRunVRD3D9ExUpgradeR13::ResetCompatDevice(device,params,hr)){spdlog::error("VR stereo: promoted D3D9Ex device lost ResetEx fallback ownership");return D3DERR_INVALIDCALL;}if(notification.outermost&&SUCCEEDED(hr))R7RevalidateRetainedAutomaticDepth(device,previousDepthGeneration);}else {hr=ResetHook.stdcall<HRESULT>(device,params);if(SUCCEEDED(hr))R7CaptureFreshAutomaticDepth(device);}if(SUCCEEDED(hr)){PrimeTrackedRenderStates(device);EnsureStereoResources(device);}return hr;}

		constexpr std::uint32_t StereoInstallPending = 0;
		constexpr std::uint32_t StereoInstallReady = 1;
		constexpr std::uint32_t StereoInstallFailed = 2;
		std::atomic<std::uint32_t> StereoInstallState{StereoInstallPending};
		std::atomic<IDirect3DDevice9*> StereoInstalledDevice{nullptr};
		std::mutex StereoInstallMutex;

		void RollbackStereoHooks() noexcept
		{
			StereoBaseCallbacksArmed.store(false, std::memory_order_release);
			QueryIssueHook = {};
			CreateQueryHook = {};
			SetVertexShaderHook = {};
			SetRenderStateHook = {};
			DrawIndexedPrimitiveUPHook = {};
			DrawPrimitiveUPHook = {};
			DrawIndexedPrimitiveHook = {};
			DrawPrimitiveHook = {};
			ClearHook = {};
			SetDepthStencilSurfaceHook = {};
			ColorFillHook = {};
			StretchRectHook = {};
			UpdateSurfaceHook = {};
			CreateDepthRetentionExHook = {};
			CreateDepthRetentionHook = {};
			SetRenderTargetHook = {};
			R7CandidatePresentBoundaryCovered=false;
			CandidatePresentExHook = {};
            R7CandidateResetBoundaryCovered=false;
            CandidateResetExHook={};
            R7CandidateSwapChainPresentTarget=nullptr;
            R7CandidateAdditionalChainSeen=false;
            CandidateAdditionalSwapChainHook={};
            CandidateSwapChainPresentHook={};
			PresentHook = {};
			ResetHook = {};
			StereoInstalledDevice.store(nullptr, std::memory_order_release);
		}

		bool InstallStereoHooks(IDirect3DDevice9*device,bool freshDevice=false)
		{
			std::lock_guard<std::mutex> installLock(StereoInstallMutex);
			if(StereoInstallState.load(std::memory_order_acquire)==StereoInstallReady)
				return StereoInstalledDevice.load(std::memory_order_acquire)==device;
			if(!device)
			{
				StereoInstallState.store(StereoInstallFailed,std::memory_order_release);
				return false;
			}
			void**vtable=*reinterpret_cast<void***>(device);
			if(!vtable)
			{
				StereoInstallState.store(StereoInstallFailed,std::memory_order_release);
				return false;
			}
			StereoInstallState.store(StereoInstallPending,std::memory_order_release);
			StereoBaseCallbacksArmed.store(false,std::memory_order_release);
			const auto disabled=safetyhook::InlineHook::StartDisabled;
			ResetHook=safetyhook::create_inline(vtable[ResetVtableIndex],ResetDest,disabled);
			PresentHook=safetyhook::create_inline(vtable[PresentVtableIndex],PresentDest,disabled);
			UpdateSurfaceHook=safetyhook::create_inline(vtable[UpdateSurfaceVtableIndex],UpdateSurfaceDest,disabled);
			StretchRectHook=safetyhook::create_inline(vtable[StretchRectVtableIndex],StretchRectDest,disabled);
			ColorFillHook=safetyhook::create_inline(vtable[ColorFillVtableIndex],ColorFillDest,disabled);
			SetRenderTargetHook=safetyhook::create_inline(vtable[SetRenderTargetVtableIndex],SetRenderTargetDest,disabled);
			SetDepthStencilSurfaceHook=safetyhook::create_inline(vtable[SetDepthStencilSurfaceVtableIndex],SetDepthStencilSurfaceDest,disabled);
			ClearHook=safetyhook::create_inline(vtable[ClearVtableIndex],ClearDest,disabled);
			DrawPrimitiveHook=safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex],DrawPrimitiveDest,disabled);
			DrawIndexedPrimitiveHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveVtableIndex],DrawIndexedPrimitiveDest,disabled);
			DrawPrimitiveUPHook=safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex],DrawPrimitiveUPDest,disabled);
			DrawIndexedPrimitiveUPHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveUPVtableIndex],DrawIndexedPrimitiveUPDest,disabled);
			SetRenderStateHook=safetyhook::create_inline(vtable[SetRenderStateVtableIndex],SetRenderStateDest,disabled);
			SetVertexShaderHook=safetyhook::create_inline(vtable[SetVertexShaderVtableIndex],SetVertexShaderDest,disabled);
			CreateQueryHook=safetyhook::create_inline(vtable[CreateQueryVtableIndex],CreateQueryDest,disabled);
			if(!ResetHook||!PresentHook||!UpdateSurfaceHook||!StretchRectHook||!ColorFillHook||!SetRenderTargetHook||!SetDepthStencilSurfaceHook||!ClearHook||!DrawPrimitiveHook||!DrawIndexedPrimitiveHook||!DrawPrimitiveUPHook||!DrawIndexedPrimitiveUPHook||!SetRenderStateHook||!SetVertexShaderHook||!CreateQueryHook)
			{
				RollbackStereoHooks();
				StereoInstallState.store(StereoInstallFailed,std::memory_order_release);
				spdlog::error("VR stereo: D3D9 hook transaction was partial; all base hooks rolled back immediately");
				return false;
			}
			SafetyHookInline*baseHooks[]{&UpdateSurfaceHook,&StretchRectHook,&ColorFillHook,&SetRenderTargetHook,&SetDepthStencilSurfaceHook,&SetRenderStateHook,&SetVertexShaderHook,&CreateQueryHook,&ClearHook,&DrawPrimitiveHook,&DrawIndexedPrimitiveHook,&DrawPrimitiveUPHook,&DrawIndexedPrimitiveUPHook,&PresentHook,&ResetHook};
			for(auto*hook:baseHooks)
			{
				if(!hook->enable().has_value())
				{
					RollbackStereoHooks();
					StereoInstallState.store(StereoInstallFailed,std::memory_order_release);
					spdlog::error("VR stereo: disabled-first D3D9 hook transaction could not be enabled completely; callbacks remain disarmed");
					return false;
				}
			}
            // Candidate provenance is optional: failure must not disable
            // the established stock stereo renderer. No new hook in v0.03 mode.
            if(Settings::VRExternalFerrariTest||Settings::VRF50ExternalModel){
                CreateDepthRetentionHook=safetyhook::create_inline(
                    vtable[CreateDepthStencilSurfaceVtableIndex],CreateDepthRetentionDest,disabled);
                if(CreateDepthRetentionHook&&!CreateDepthRetentionHook.enable().has_value())
                    CreateDepthRetentionHook={};
                // Query the real Ex interface before indexing its extended
                // vtable. If identity/target is ambiguous, leave it unhooked.
                IDirect3DDevice9Ex* ex=nullptr;
                const HRESULT exQuery=device->QueryInterface(
                    __uuidof(IDirect3DDevice9Ex),reinterpret_cast<void**>(&ex));
                if(CreateDepthRetentionHook&&SUCCEEDED(exQuery)&&
                    ex&&static_cast<IDirect3DDevice9*>(ex)==device){
                    void** exTable=*reinterpret_cast<void***>(ex);
                    if(exTable&&exTable[CreateDepthStencilSurfaceExVtableIndex]&&
                        exTable[CreateDepthStencilSurfaceExVtableIndex]!=vtable[CreateDepthStencilSurfaceVtableIndex]){
                        CreateDepthRetentionExHook=safetyhook::create_inline(
                            exTable[CreateDepthStencilSurfaceExVtableIndex],CreateDepthRetentionExDest,disabled);
                        if(CreateDepthRetentionExHook&&!CreateDepthRetentionExHook.enable().has_value())
                            CreateDepthRetentionExHook={};
                    }
                }
                // With only a base hook on an Ex device, a direct Ex call
                // could delegate into base and impersonate the outer API.
                // Retire the base hook too unless classic D3D9 is confirmed.
                if(!CreateDepthRetentionExHook&&(exQuery!=E_NOINTERFACE||ex))
                    CreateDepthRetentionHook={};
                // Classic devices have only base Present; Ex must also own
                // the direct entrypoint. If optional installation fails, the
                // established renderer continues but candidate seeding stops.
                R7CandidatePresentBoundaryCovered=exQuery==E_NOINTERFACE&&!ex;
                if(SUCCEEDED(exQuery)&&ex&&static_cast<IDirect3DDevice9*>(ex)==device){
                    void** exTable=*reinterpret_cast<void***>(ex);
                    void* target=exTable?exTable[PresentExVtableIndex]:nullptr;
                    // Reject shared entrypoints with incompatible signatures.
                    for(unsigned slot=0;target&&slot<119;++slot)
                        if(target==vtable[slot])target=nullptr;
                    if(target&&target!=exTable[CreateDepthStencilSurfaceExVtableIndex]){
                        CandidatePresentExHook=safetyhook::create_inline(
                            target,R7CandidatePresentExDest,disabled);
                        if(CandidatePresentExHook&&!CandidatePresentExHook.enable().has_value())
                            CandidatePresentExHook={};
                        R7CandidatePresentBoundaryCovered=static_cast<bool>(CandidatePresentExHook);
                    }
                }
                R7CandidateResetBoundaryCovered=exQuery==E_NOINTERFACE&&!ex;
                if(SUCCEEDED(exQuery)&&ex&&static_cast<IDirect3DDevice9*>(ex)==device){
                    void** exTable=*reinterpret_cast<void***>(ex);
                    void* target=exTable?exTable[ResetExVtableIndex]:nullptr;
                    // Reject ABI aliases with any other base/Ex entrypoint.
                    for(unsigned slot=0;target&&slot<134;++slot)
                        if(slot!=ResetExVtableIndex&&target==exTable[slot])target=nullptr;
                    if(target){
                        CandidateResetExHook=safetyhook::create_inline(
                            target,R7CandidateResetExDest,disabled);
                        if(CandidateResetExHook&&!CandidateResetExHook.enable().has_value())
                            CandidateResetExHook={};
                        R7CandidateResetBoundaryCovered=static_cast<bool>(CandidateResetExHook);
                    }
                }
                ReleaseCom(ex);
                void* chainTarget=R7GetImplicitChainPresentTarget(device);
                void* additionalTarget=vtable[CreateAdditionalSwapChainVtableIndex];
                // Device and chain callbacks have different ABI signatures.
                for(unsigned slot=0;slot<119;++slot){
                    if(chainTarget&&chainTarget==vtable[slot])chainTarget=nullptr;
                    if(slot!=CreateAdditionalSwapChainVtableIndex&&additionalTarget==vtable[slot])
                        additionalTarget=nullptr;
                }
                if(chainTarget&&additionalTarget){
                    CandidateSwapChainPresentHook=safetyhook::create_inline(
                        chainTarget,R7CandidateSwapChainPresentDest,disabled);
                    CandidateAdditionalSwapChainHook=safetyhook::create_inline(
                        additionalTarget,R7CandidateAdditionalSwapChainDest,disabled);
                    if(CandidateSwapChainPresentHook&&CandidateAdditionalSwapChainHook&&
                        CandidateSwapChainPresentHook.enable().has_value()&&
                        CandidateAdditionalSwapChainHook.enable().has_value())
                        R7CandidateSwapChainPresentTarget=chainTarget;
                    else{
                        CandidateAdditionalSwapChainHook={};
                        CandidateSwapChainPresentHook={};
                    }
                }
                if(freshDevice)R7CaptureFreshAutomaticDepth(device);
            }
			IDirect3DVertexShader9*shader=nullptr;
			if(SUCCEEDED(device->GetVertexShader(&shader))&&shader)
			{
				CurrentVertexShaderIdentity.store(reinterpret_cast<std::uintptr_t>(shader),std::memory_order_release);
				VertexShaderSerial.store(1,std::memory_order_release);
				shader->Release();
			}
			PrimeTrackedRenderStates(device);
			IDirect3DQuery9*queryProbe=nullptr;
			if(SUCCEEDED(device->CreateQuery(D3DQUERYTYPE_OCCLUSION,&queryProbe))&&queryProbe)queryProbe->Release();
			InitializeAuxRenderTargetState(device);
			LastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();
			EnsureSharedState();
			EnsureRenderFrameState();
			// Resource creation is intentionally deferred beyond CreateDevice exposure.
			// D3D9Ex still installs Reset/Present ownership synchronously, but private
			// eye/backbuffer resources are first created only by the final R23 Present
			// owner after a successful real game Present.
			StereoInstalledDevice.store(device,std::memory_order_release);
			StereoBaseCallbacksArmed.store(true,std::memory_order_release);
			StereoInstallState.store(StereoInstallReady,std::memory_order_release);
			spdlog::info("VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/RenderState/VS/CreateQuery); disabled-first callbacks armed atomically at the behavior boundary; R42 render-state shadow validates every 16 reads and c64 world checks use game upload shadow");
			return true;
		}

		DWORD WINAPI StereoInstallThread(void*)
		{
			// D3D9Ex devices are installed synchronously on their CreateDevice
			// caller thread. This worker remains only for the classic D3D9 path and
			// exits before touching a synchronously installed promoted device.
			for(int attempt=0;attempt<1200;++attempt)
			{
				if(StereoInstallState.load(std::memory_order_acquire)==StereoInstallReady)
					return 0;
				if(Game::D3DDevice_ptr&&*Game::D3DDevice_ptr)
				{
					if(!InstallStereoHooks(*Game::D3DDevice_ptr))
						spdlog::error("VR stereo: classic-path renderer hook installation failed closed");
					return 0;
				}
				Sleep(100);
			}
			StereoInstallState.store(StereoInstallFailed,std::memory_order_release);
			spdlog::warn("VR stereo: D3D9 device did not appear; stereo hooks not installed");
			return 0;
		}

	}

    void R7SetDirectResetRasterOwner(void(*owner)() noexcept) noexcept
    {
        R7DirectResetRasterOwner.store(owner,std::memory_order_release);
    }

    void R7SetDirectResetLifecycleOwner(void(*owner)(bool,HRESULT) noexcept) noexcept
    {
        R7DirectResetLifecycleOwner.store(owner,std::memory_order_release);
    }

	bool InstallStereoHooksSynchronously(IDirect3DDevice9* device) noexcept
	{
		const bool installed=InstallStereoHooks(device,true);
		if(installed)
			spdlog::info("VR stereo: synchronous CreateDevice-thread base hook handoff READY; promoted D3D9Ex device exposed only after Reset ownership transferred");
		return installed;
	}

	bool IsInternalStereoPassActive(){return InternalStereoPass;}
	bool GetCurrentShaderEpoch(std::uintptr_t&shaderIdentity,std::uint64_t&serial){for(int attempt=0;attempt<3;++attempt){const std::uint64_t before=VertexShaderSerial.load(std::memory_order_acquire);const std::uintptr_t identity=CurrentVertexShaderIdentity.load(std::memory_order_acquire);const std::uint64_t after=VertexShaderSerial.load(std::memory_order_acquire);if(before==after){shaderIdentity=identity;serial=after;return identity!=0&&after!=0;}}shaderIdentity=0;serial=0;return false;}
	class VRStereoHook:public Hook
	{
	public:
		std::string_view description() override{return "OpenXRVRStereo";}
		bool validate() override{return true;}
		bool apply() override{HANDLE thread=CreateThread(nullptr,0,StereoInstallThread,nullptr,0,nullptr);if(!thread){StereoInstallState.store(StereoInstallFailed,std::memory_order_release);spdlog::error("VR stereo: failed to create installer thread: {}",GetLastError());return false;}CloseHandle(thread);return true;}
		static VRStereoHook instance;
	};
	VRStereoHook VRStereoHook::instance;
}
