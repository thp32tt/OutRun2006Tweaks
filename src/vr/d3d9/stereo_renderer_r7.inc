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
#include "vr/game/disasm_render_contract.hpp"
#include "vr_shared.hpp"
#include "vr/core/d3d9_draw_state.hpp"
#include "vr/d3d11/runtime_census.hpp"

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
	extern Setting<float> VRWorldScale;
	extern Setting<float> VRStereoDepth;
	extern Setting<bool> VRTelemetry;
}

#ifndef OUTRUN_VR_BUILD_SHA
#define OUTRUN_VR_BUILD_SHA "unknown"
#endif

namespace OutRunVRStereo
{
	namespace
	{
		constexpr std::size_t ResetVtableIndex = 16;
		constexpr std::size_t PresentVtableIndex = 17;
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
		constexpr UINT OutRunWvpRegister =
			static_cast<UINT>(OutRunVR::DisasmContract::WvpVsRegister);
		constexpr UINT OutRunWvpRegisterCount =
			static_cast<UINT>(OutRunVR::DisasmContract::WvpVsRegisterCount);
		constexpr std::uintptr_t OutRunProjectionRva =
			OutRunVR::DisasmContract::ProjectionRva;
		constexpr float VerifiedWvpEpsilon = 1.0e-4f;

		SafetyHookInline ResetHook{};
		SafetyHookInline PresentHook{};
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

		HANDLE SharedMapping = nullptr;
		OutRunVR::SharedPoseState* SharedState = nullptr;
		HANDLE RenderFrameMapping = nullptr;
		OutRunVR::SharedRenderFrameRing* RenderFrameRing = nullptr;
		std::uint32_t RenderFrameRunGeneration = 0;
		bool RenderFrameRingClaimed = false;

		IDirect3DSurface9* BackBuffer = nullptr;
		IDirect3DSurface9* TrackedRenderTarget = nullptr;
		IDirect3DSurface9* TrackedDepthStencil = nullptr;
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
		bool DirectInteropVerified = false;

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
		// R67 stage-boundary guard: game Present still proceeds, but no new
		// OpenXR transport metadata is published for one mixed transition frame.
		bool R67HoldPreviousProjectionThisPresent = false;
		OutRunVR::StereoFailureReason FrameFailureReason = OutRunVR::StereoFailureNone;
		std::uint32_t FrameStereoPoseSequence = 0;
		OutRunVRRenderer::LatchedStereoFrame FrameStereoMetadata{};
		std::uint32_t StereoFrameCounter = 0;
		bool RightDepthSynchronized = true;
		bool RightStencilSynchronized = true;
		bool LastStereoWanted = false;
		bool FramePoseMismatchLogged = false;
		std::uint64_t PresentEpoch = 1;
		std::uint64_t LastMainDepthClearEpoch = 0;
		DWORD LastMainDepthClearFlags = 0;
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