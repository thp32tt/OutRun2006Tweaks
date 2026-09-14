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

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr_shared.hpp"

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
	extern Setting<float> VRWorldScale;
	extern Setting<bool> VRTelemetry;
}

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
		constexpr std::size_t SetVertexShaderVtableIndex = 92;
		constexpr UINT OutRunWvpRegister = 64;
		constexpr UINT OutRunWvpRegisterCount = 4;
		constexpr std::uintptr_t OutRunProjectionRva = 0x0095D8A0u - 0x00400000u;
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
		SafetyHookInline SetVertexShaderHook{};

		HANDLE SharedMapping = nullptr;
		OutRunVR::SharedPoseState* SharedState = nullptr;
		HANDLE RenderFrameMapping = nullptr;
		OutRunVR::SharedRenderFrameState* RenderFrameState = nullptr;

		IDirect3DSurface9* BackBuffer = nullptr;
		IDirect3DSurface9* TrackedRenderTarget = nullptr;
		IDirect3DSurface9* TrackedDepthStencil = nullptr;
		IDirect3DSurface9* RightEyeSurface = nullptr;
		IDirect3DSurface9* RightEyeDepth = nullptr;
		IDirect3DTexture9* LeftResolveTexture = nullptr;
		IDirect3DSurface9* LeftResolveSurface = nullptr;
		IDirect3DTexture9* RightResolveTexture = nullptr;
		IDirect3DSurface9* RightResolveSurface = nullptr;

		D3DSURFACE_DESC BackBufferDesc{};
		bool StereoResourcesReady = false;
		bool InternalStereoPass = false;
		std::array<bool, 3> AuxRenderTargetActive{};

		std::atomic<std::uintptr_t> CurrentVertexShaderIdentity{ 0 };
		std::atomic<std::uint64_t> VertexShaderSerial{ 0 };

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

		ULONGLONG LastSummaryMs = 0;
		std::uint64_t DuplicatedDraws = 0;
		std::uint64_t WorldStereoDraws = 0;
		std::uint64_t NonWorldDuplicatedDraws = 0;
		std::uint64_t StereoComposeSuccess = 0;
		std::uint64_t StereoComposeFailure = 0;
		std::uint64_t MrtRejectedDraws = 0;
		std::uint64_t RestoreFailures = 0;
		bool FirstStereoActiveLogged = false;
		bool FirstWorldStereoLogged = false;
		bool FirstRestoreFailureLogged = false;
		bool FirstMrtRejectLogged = false;

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

		bool GameplayActive()
		{
			if (!Game::current_mode)
				return false;
			if (*Game::current_mode == GameState::STATE_GAME)
				return true;
			return *Game::current_mode == GameState::STATE_START &&
				Game::game_start_progress_code && *Game::game_start_progress_code == 65;
		}

		bool StereoWanted()
		{
			if (!Settings::VRStereo || !GameplayActive())
				return false;
			return Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;
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
			// Matches Khronos OpenXR-SDK xr_linear.h GRAPHICS_D3D projection
			// layout (-Z forward, +Y up, D3D [0,1] depth).
			out._11 = 2.0f / width;
			out._22 = 2.0f / height;
			out._31 = (tanRight + tanLeft) / width;
			out._32 = (tanUp + tanDown) / height;
			// Preserve OutRun's exact near/far/depth mapping.
			out._33 = base._33;
			out._34 = base._34;
			out._43 = base._43;
			out._44 = base._44;
			return out;
		}

		bool ReadProjection(D3DMATRIX& projection)
		{
			if (!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX)))
				return false;
			const auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
			if (!IsReadableRange(projectionPtr, sizeof(D3DMATRIX)))
				return false;
			std::memcpy(&projection, projectionPtr, sizeof(projection));
			return MatrixFinite(projection) &&
				std::fabs(projection._34 + 1.0f) < 0.25f && std::fabs(projection._44) < 0.25f;
		}

		bool GetInverseProjection(const D3DMATRIX& projection, D3DMATRIX& inverse)
		{
			if (!ProjectionInverseValid || std::memcmp(&projection, &CachedProjection, sizeof(projection)) != 0)
			{
				D3DMATRIX candidate{};
				if (!InvertMatrix(projection, candidate))
					return false;
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
				return SharedState->magic == OutRunVR::SharedMagic &&
					SharedState->protocolVersion == OutRunVR::SharedProtocolVersion &&
					SharedState->structSize == sizeof(OutRunVR::SharedPoseState);
			SharedMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
				0, static_cast<DWORD>(sizeof(OutRunVR::SharedPoseState)), OutRunVR::SharedMemoryName);
			if (!SharedMapping)
				return false;
			const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;
			SharedState = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(
				SharedMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedPoseState)));
			if (!SharedState)
			{
				CloseHandle(SharedMapping);
				SharedMapping = nullptr;
				return false;
			}
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

		bool EnsureRenderFrameState()
		{
			if (RenderFrameState) return RenderFrameState->magic==OutRunVR::RenderFrameMagic && RenderFrameState->protocolVersion==OutRunVR::RenderFrameProtocolVersion && RenderFrameState->structSize==sizeof(OutRunVR::SharedRenderFrameState);
			RenderFrameMapping=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameState)),OutRunVR::RenderFrameMemoryName); if(!RenderFrameMapping)return false;
			const bool existed=GetLastError()==ERROR_ALREADY_EXISTS; RenderFrameState=static_cast<OutRunVR::SharedRenderFrameState*>(MapViewOfFile(RenderFrameMapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(OutRunVR::SharedRenderFrameState))); if(!RenderFrameState)return false;
			if(!existed){std::memset(RenderFrameState,0,sizeof(*RenderFrameState));RenderFrameState->protocolVersion=OutRunVR::RenderFrameProtocolVersion;RenderFrameState->structSize=sizeof(*RenderFrameState);MemoryBarrier();RenderFrameState->magic=OutRunVR::RenderFrameMagic;}
			return RenderFrameState->magic==OutRunVR::RenderFrameMagic && RenderFrameState->protocolVersion==OutRunVR::RenderFrameProtocolVersion && RenderFrameState->structSize==sizeof(*RenderFrameState);
		}
		void PoisonFrame(OutRunVR::StereoFailureReason reason){FrameStereoIncomplete=true;if(FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=reason;}

		struct DrawStereoState
		{
			float originalConstants[16]{};
			float eyeConstants[2][16]{};
			bool worldStereo = false;
			std::uint32_t poseSequence = 0;
			OutRunVRRenderer::LatchedStereoFrame stereoFrame{};
		};

		bool BuildEyeConstants(IDirect3DDevice9* device,
			const OutRunVRRenderer::LatchedStereoFrame& stereo, DrawStereoState& state)
		{
			std::uintptr_t shaderIdentity = 0;
			std::uint64_t shaderSerial = 0;
			if (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))
				return false;

			if (FAILED(device->GetVertexShaderConstantF(OutRunWvpRegister,
				state.originalConstants, OutRunWvpRegisterCount)))
				return false;

			float verifiedConstants[16]{};
			std::uint32_t verifiedGeneration = 0;
			std::uint32_t verifiedPoseSequence = 0;
			std::uintptr_t verifiedShaderIdentity = 0;
			std::uint64_t verifiedShaderSerial = 0;
			if (!OutRunVRRenderer::GetLastVerifiedWvp(verifiedConstants, verifiedGeneration,
				verifiedPoseSequence, verifiedShaderIdentity, verifiedShaderSerial))
				return false;
			if (verifiedGeneration == 0 || verifiedPoseSequence != stereo.poseSequence ||
				verifiedShaderIdentity != shaderIdentity || verifiedShaderSerial != shaderSerial ||
				!FloatArrayNear(state.originalConstants, verifiedConstants, 16, VerifiedWvpEpsilon))
				return false;

			D3DMATRIX projection{};
			D3DMATRIX invProjection{};
			if (!ReadProjection(projection) || !GetInverseProjection(projection, invProjection))
				return false;

			D3DMATRIX uploadedT{};
			std::memcpy(&uploadedT, state.originalConstants, sizeof(uploadedT));
			const D3DMATRIX currentWvp = TransposeMatrix(uploadedT);
			const D3DMATRIX correctedWorldView = MultiplyMatrix(currentWvp, invProjection);
			if (!MatrixFinite(correctedWorldView))
				return false;

			for (int eye = 0; eye < 2; ++eye)
			{
				const D3DMATRIX eyePose = MatrixFromQuaternionTranslation(stereo.eyeOrientation[eye], stereo.eyeOffset[eye], Settings::VRWorldScale);
				const D3DMATRIX eyeInverse = InverseRigid(eyePose);
				const D3DMATRIX eyeProjection = ProjectionFromFov(projection, stereo.eyeFov[eye]);
				const D3DMATRIX eyeWvp = MultiplyMatrix(
					MultiplyMatrix(correctedWorldView, eyeInverse), eyeProjection);
				if (!MatrixFinite(eyeWvp))
					return false;
				const D3DMATRIX eyeWvpT = TransposeMatrix(eyeWvp);
				std::memcpy(state.eyeConstants[eye], &eyeWvpT, sizeof(eyeWvpT));
			}

			state.worldStereo = true;
			state.poseSequence = stereo.poseSequence;
			return true;
		}

		bool SetWvpOneRegisterAtATime(IDirect3DDevice9* device, const float* constants)
		{
			// The mono renderer hook only recognizes a candidate when c64..c67 are
			// present in one call. Four 1-register writes deliberately pass through
			// unchanged, avoiding a second head transform.
			for (UINT reg = 0; reg < OutRunWvpRegisterCount; ++reg)
				if (FAILED(device->SetVertexShaderConstantF(
					OutRunWvpRegister + reg, constants + reg * 4, 1)))
					return false;
			return true;
		}

		bool FormatHasStencil(D3DFORMAT format)
		{
			switch (format)
			{
			case D3DFMT_D15S1:
			case D3DFMT_D24S8:
			case D3DFMT_D24X4S4:
			case D3DFMT_D24FS8:
				return true;
			default:
				return false;
			}
		}

		void ReleaseStereoResources()
		{
			StereoResourcesReady = false;
			ProjectionInverseValid = false;
			ReleaseCom(RightEyeSurface);
			ReleaseCom(RightEyeDepth);
			ReleaseCom(LeftResolveSurface);
			ReleaseCom(LeftResolveTexture);
			ReleaseCom(RightResolveSurface);
			ReleaseCom(RightResolveTexture);
			ReleaseCom(BackBuffer);
			ReleaseCom(TrackedRenderTarget);
			ReleaseCom(TrackedDepthStencil);
			BackBufferDesc = {};
		}

		bool CreateRightDepthForTracked(IDirect3DDevice9* device)
		{
			ReleaseCom(RightEyeDepth);
			RightDepthSynchronized = TrackedDepthStencil == nullptr;
			if (!TrackedDepthStencil)
				return true;

			D3DSURFACE_DESC depthDesc{};
			if (FAILED(TrackedDepthStencil->GetDesc(&depthDesc)))
				return false;
			return SUCCEEDED(device->CreateDepthStencilSurface(
				BackBufferDesc.Width, BackBufferDesc.Height, depthDesc.Format,
				depthDesc.MultiSampleType, depthDesc.MultiSampleQuality, FALSE,
				&RightEyeDepth, nullptr));
		}

		bool InitializeAuxRenderTargetState(IDirect3DDevice9* device)
		{
			for (DWORD index = 1; index <= 3; ++index)
			{
				IDirect3DSurface9* surface = nullptr;
				const HRESULT hr = device->GetRenderTarget(index, &surface);
				AuxRenderTargetActive[index - 1] = SUCCEEDED(hr) && surface != nullptr;
				if (surface)
					surface->Release();
			}
			return true;
		}

		bool EnsureStereoResources(IDirect3DDevice9* device)
		{
			if (!device)
				return false;
			if (StereoResourcesReady && BackBuffer && RightEyeSurface &&
				LeftResolveSurface && RightResolveSurface)
				return true;

			IDirect3DSurface9* newBackBuffer = nullptr;
			if (FAILED(device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &newBackBuffer)) || !newBackBuffer)
				return false;
			D3DSURFACE_DESC desc{};
			if (FAILED(newBackBuffer->GetDesc(&desc)))
			{
				newBackBuffer->Release();
				return false;
			}

			ReleaseStereoResources();
			BackBuffer = newBackBuffer;
			BackBufferDesc = desc;

			IDirect3DSurface9* currentRt = nullptr;
			if (SUCCEEDED(device->GetRenderTarget(0, &currentRt)) && currentRt)
				TrackedRenderTarget = currentRt;
			else
				ReplaceSurfaceRef(TrackedRenderTarget, BackBuffer);
			IDirect3DSurface9* currentDepth = nullptr;
			const HRESULT depthStateHr = device->GetDepthStencilSurface(&currentDepth);
			if (SUCCEEDED(depthStateHr) && currentDepth)
				TrackedDepthStencil = currentDepth;
			else if (depthStateHr == D3DERR_NOTFOUND)
				TrackedDepthStencil = nullptr;
			InitializeAuxRenderTargetState(device);

			if (FAILED(device->CreateRenderTarget(desc.Width, desc.Height, desc.Format,
				desc.MultiSampleType, desc.MultiSampleQuality, FALSE, &RightEyeSurface, nullptr)) ||
				!CreateRightDepthForTracked(device))
			{
				ReleaseStereoResources();
				return false;
			}

			if (FAILED(device->CreateTexture(desc.Width, desc.Height, 1, D3DUSAGE_RENDERTARGET,
				desc.Format, D3DPOOL_DEFAULT, &LeftResolveTexture, nullptr)) ||
				FAILED(LeftResolveTexture->GetSurfaceLevel(0, &LeftResolveSurface)) ||
				FAILED(device->CreateTexture(desc.Width, desc.Height, 1, D3DUSAGE_RENDERTARGET,
					desc.Format, D3DPOOL_DEFAULT, &RightResolveTexture, nullptr)) ||
				FAILED(RightResolveTexture->GetSurfaceLevel(0, &RightResolveSurface)))
			{
				ReleaseStereoResources();
				return false;
			}

			D3DVIEWPORT9 savedViewport{};
			if (FAILED(device->GetViewport(&savedViewport)))
			{
				ReleaseStereoResources();
				return false;
			}

			bool initOk = true;
			{
				InternalPassScope guard;
				if (FAILED(SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface)))
					initOk = false;
				if (initOk)
				{
					const HRESULT depthHr = SetDepthStencilSurfaceHook
						? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth)
						: device->SetDepthStencilSurface(RightEyeDepth);
					if (FAILED(depthHr)) initOk = false;
				}
				if (initOk && FAILED(device->SetViewport(&savedViewport)))
					initOk = false;

				DWORD clearFlags = D3DCLEAR_TARGET;
				if (RightEyeDepth)
				{
					D3DSURFACE_DESC depthDesc{};
					if (FAILED(RightEyeDepth->GetDesc(&depthDesc)))
						initOk = false;
					else
					{
						clearFlags |= D3DCLEAR_ZBUFFER;
						if (FormatHasStencil(depthDesc.Format))
							clearFlags |= D3DCLEAR_STENCIL;
					}
				}
				if (initOk && FAILED(ClearHook.stdcall<HRESULT>(device, 0u,
					static_cast<const D3DRECT*>(nullptr), clearFlags,
					D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0u)))
					initOk = false;

				if (TrackedRenderTarget && FAILED(SetRenderTargetHook.stdcall<HRESULT>(
					device, 0u, TrackedRenderTarget)))
					initOk = false;
				const HRESULT restoreDepthHr = SetDepthStencilSurfaceHook
					? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, TrackedDepthStencil)
					: device->SetDepthStencilSurface(TrackedDepthStencil);
				if (FAILED(restoreDepthHr)) initOk = false;
				if (FAILED(device->SetViewport(&savedViewport))) initOk = false;
			}

			if (!initOk)
			{
				ReleaseStereoResources();
				return false;
			}

			StereoResourcesReady = true;
			spdlog::info("VR stereo: full-size eye surfaces ready {}x{} format={} msaa={} quality={}",
				desc.Width, desc.Height, static_cast<int>(desc.Format),
				static_cast<int>(desc.MultiSampleType), desc.MultiSampleQuality);
			return true;
		}

		void NoteRestoreFailure(const char* what)
		{
			FrameRightDrawFailed = true;
			PoisonFrame(OutRunVR::StereoFailureRestoreFailed);
			++RestoreFailures;
			if (!FirstRestoreFailureLogged)
			{
				FirstRestoreFailureLogged = true;
				spdlog::warn("VR stereo: renderer state restore failed at {}; frame forced to mono fallback", what);
			}
		}

		bool RestoreRightPassState(IDirect3DDevice9* device, IDirect3DSurface9* savedRt,
			IDirect3DSurface9* savedDepth, const D3DVIEWPORT9& savedViewport,
			const float* originalConstants, bool restoreWvp)
		{
			bool ok = true;
			if (savedRt && FAILED(SetRenderTargetHook.stdcall<HRESULT>(device, 0u, savedRt))) ok = false;
			const HRESULT depthHr = SetDepthStencilSurfaceHook
				? SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth)
				: device->SetDepthStencilSurface(savedDepth);
			if (FAILED(depthHr)) ok = false;
			if (FAILED(device->SetViewport(&savedViewport))) ok = false;
			if (restoreWvp && !SetWvpOneRegisterAtATime(device, originalConstants)) ok = false;
			return ok;
		}

		std::uint32_t NextStereoFrameId()
		{
			if (++StereoFrameCounter == 0)
				++StereoFrameCounter;
			return StereoFrameCounter;
		}

		void PublishStereoState(std::uint32_t state, bool worldStereo,
			std::uint32_t poseSequence, std::uint32_t frameId,
			std::uint32_t presentQpcLow)
		{
			if (!EnsureSharedState())
				return;

			// Frame=0 is the client-side publication guard. The host refuses frame 0,
			// so it cannot accept fields while this packet is being rewritten.
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]), 0);
			const LONG stereoBits=static_cast<LONG>(OutRunVR::ClientStereoActive|OutRunVR::ClientStereoWorldDraw|OutRunVR::ClientStereoDrawDuplicated);
			InterlockedAnd(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]), ~stereoBits);

			if (state != OutRunVR::StereoSbsActive || poseSequence == 0 || frameId == 0 || presentQpcLow == 0)
			{
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence), 0);
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoPresentQpcLowIndex]), 0);
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),
					static_cast<LONG>(state));
				return;
			}

			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence),
				static_cast<LONG>(poseSequence));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoPresentQpcLowIndex]),
				static_cast<LONG>(presentQpcLow));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]),
				static_cast<LONG>(BackBufferDesc.Height));
			LONG bits = static_cast<LONG>(OutRunVR::ClientStereoActive | OutRunVR::ClientStereoDrawDuplicated);
			if (worldStereo)
				bits |= static_cast<LONG>(OutRunVR::ClientStereoWorldDraw);
			InterlockedOr(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]), bits);
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),
				static_cast<LONG>(OutRunVR::StereoSbsActive));
			MemoryBarrier();
			// Publish last: non-zero frame means all metadata above is coherent.
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]),
				static_cast<LONG>(frameId));
		}

		void PublishRenderFrame(std::uint32_t state,std::uint32_t frameId,std::uint32_t sourcePoseSequence,std::int64_t presentQpc,OutRunVR::StereoFailureReason failureReason,const OutRunVRRenderer::LatchedStereoFrame* stereo)
		{
			if(!EnsureRenderFrameState())return; LONG seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));if((seq&1)==0)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));MemoryBarrier();
			RenderFrameState->clientPid=GetCurrentProcessId();RenderFrameState->state=state;RenderFrameState->frameId=frameId;RenderFrameState->sourcePoseSequence=sourcePoseSequence;RenderFrameState->presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;RenderFrameState->flags=0;RenderFrameState->failureReason=static_cast<std::uint32_t>(failureReason);RenderFrameState->backbufferWidth=BackBufferDesc.Width;RenderFrameState->backbufferHeight=BackBufferDesc.Height;RenderFrameState->presentQpc=presentQpc;std::memset(RenderFrameState->eye,0,sizeof(RenderFrameState->eye));
			if(state==OutRunVR::StereoSbsActive&&stereo&&stereo->valid&&frameId){RenderFrameState->flags=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;for(int eye=0;eye<2;++eye){std::memcpy(RenderFrameState->eye[eye].orientation,stereo->effectiveEyeOrientation[eye],sizeof(RenderFrameState->eye[eye].orientation));std::memcpy(RenderFrameState->eye[eye].position,stereo->effectiveEyePosition[eye],sizeof(RenderFrameState->eye[eye].position));RenderFrameState->eye[eye].fov=stereo->eyeFov[eye];}}
			MemoryBarrier();seq=InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));if(seq&1)InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameState->sequence));
		}

		struct ScreenVertex
		{
			float x, y, z, rhw;
			float u, v;
		};

		bool DrawTextureHalf(IDirect3DDevice9* device, IDirect3DTexture9* texture, bool right)
		{
			if (!texture || !BackBufferDesc.Width || !BackBufferDesc.Height)
				return false;
			const float x0 = right ? static_cast<float>(BackBufferDesc.Width / 2) : 0.0f;
			const float x1 = right ? static_cast<float>(BackBufferDesc.Width) : static_cast<float>(BackBufferDesc.Width / 2);
			const float y0 = 0.0f;
			const float y1 = static_cast<float>(BackBufferDesc.Height);
			const ScreenVertex vertices[4] = {
				{x0 - 0.5f, y0 - 0.5f, 0.0f, 1.0f, 0.0f, 0.0f},
				{x1 - 0.5f, y0 - 0.5f, 0.0f, 1.0f, 1.0f, 0.0f},
				{x0 - 0.5f, y1 - 0.5f, 0.0f, 1.0f, 0.0f, 1.0f},
				{x1 - 0.5f, y1 - 0.5f, 0.0f, 1.0f, 1.0f, 1.0f},
			};
			if (FAILED(device->SetTexture(0, texture)))
				return false;
			return SUCCEEDED(device->DrawPrimitiveUP(
				D3DPT_TRIANGLESTRIP, 2, vertices, static_cast<UINT>(sizeof(ScreenVertex))));
		}

		bool ComposeSbs(IDirect3DDevice9* device)
		{
			if (!StereoResourcesReady || !BackBuffer || !RightEyeSurface ||
				!LeftResolveSurface || !RightResolveSurface)
				return false;
			if (FAILED(device->StretchRect(BackBuffer, nullptr, LeftResolveSurface, nullptr, D3DTEXF_NONE)) ||
				FAILED(device->StretchRect(RightEyeSurface, nullptr, RightResolveSurface, nullptr, D3DTEXF_NONE)))
				return false;

			IDirect3DStateBlock9* stateBlock = nullptr;
			if (FAILED(device->CreateStateBlock(D3DSBT_ALL, &stateBlock)) || !stateBlock)
				return false;

			IDirect3DSurface9* savedRt = nullptr;
			IDirect3DSurface9* savedDepth = nullptr;
			D3DVIEWPORT9 savedViewport{};
			const HRESULT rtHr = device->GetRenderTarget(0, &savedRt);
			const HRESULT depthHr = device->GetDepthStencilSurface(&savedDepth);
			const HRESULT viewportHr = device->GetViewport(&savedViewport);
			const bool depthOk = SUCCEEDED(depthHr) || depthHr == D3DERR_NOTFOUND;
			if (FAILED(rtHr) || !savedRt || !depthOk || FAILED(viewportHr))
			{
				if (savedRt) savedRt->Release();
				if (savedDepth) savedDepth->Release();
				stateBlock->Release();
				return false;
			}

			bool success = false;
			bool beganScene = false;
			{
				InternalPassScope guard;
				if (SUCCEEDED(SetRenderTargetHook.stdcall<HRESULT>(device, 0u, BackBuffer)) &&
					SUCCEEDED(SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, static_cast<IDirect3DSurface9*>(nullptr))) &&
					SUCCEEDED(device->BeginScene()))
				{
					beganScene = true;
					device->SetVertexShader(nullptr);
					device->SetPixelShader(nullptr);
					device->SetFVF(D3DFVF_XYZRHW | D3DFVF_TEX1);
					device->SetRenderState(D3DRS_ZENABLE, FALSE);
					device->SetRenderState(D3DRS_ZWRITEENABLE, FALSE);
					device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
					device->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);
					device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
					device->SetRenderState(D3DRS_LIGHTING, FALSE);
					device->SetRenderState(D3DRS_FOGENABLE, FALSE);
					device->SetRenderState(D3DRS_STENCILENABLE, FALSE);
					device->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);
					device->SetRenderState(D3DRS_SRGBWRITEENABLE, FALSE);
					device->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
					device->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TEXTURE);
					device->SetTextureStageState(0, D3DTSS_ALPHAOP, D3DTOP_SELECTARG1);
					device->SetTextureStageState(0, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
					device->SetTextureStageState(0, D3DTSS_TEXCOORDINDEX, 0);
					device->SetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
					device->SetTextureStageState(1, D3DTSS_COLOROP, D3DTOP_DISABLE);
					device->SetSamplerState(0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
					device->SetSamplerState(0, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
					device->SetSamplerState(0, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
					device->SetSamplerState(0, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
					device->SetSamplerState(0, D3DSAMP_SRGBTEXTURE, FALSE);
					D3DVIEWPORT9 full{ 0, 0, BackBufferDesc.Width, BackBufferDesc.Height, 0.0f, 1.0f };
					const bool stateOk = SUCCEEDED(device->SetViewport(&full)) &&
						SUCCEEDED(device->Clear(0, nullptr, D3DCLEAR_TARGET, D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0));
					const bool leftOk = stateOk && DrawTextureHalf(device, LeftResolveTexture, false);
					const bool rightOk = leftOk && DrawTextureHalf(device, RightResolveTexture, true);
					device->SetTexture(0, nullptr);
					const HRESULT endHr = device->EndScene();
					beganScene = false;
					success = leftOk && rightOk && SUCCEEDED(endHr);
				}
				if (beganScene)
					device->EndScene();
			}

			const HRESULT applyHr = stateBlock->Apply();
			stateBlock->Release();
			bool restoreOk = SUCCEEDED(applyHr);
			if (FAILED(SetRenderTargetHook.stdcall<HRESULT>(device, 0u, savedRt))) restoreOk = false;
			if (FAILED(SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth))) restoreOk = false;
			if (FAILED(device->SetViewport(&savedViewport))) restoreOk = false;
			savedRt->Release();
			if (savedDepth) savedDepth->Release();
			return success && restoreOk;
		}

		bool PrepareDuplicatedDraw(IDirect3DDevice9* device, DrawStereoState& draw)
		{
			if (InternalStereoPass || !StereoWanted() || !TargetIsBackBuffer()) return false;
			if (AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);++MrtRejectedDraws;if(!FirstMrtRejectLogged){FirstMrtRejectLogged=true;spdlog::info("VR stereo: auxiliary MRT active; current Present is marked incomplete");}return false;}
			if(!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);return false;}
			if(TrackedDepthStencil&&!RightDepthSynchronized){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}
			OutRunVRRenderer::LatchedStereoFrame stereo{};if(!OutRunVRRenderer::GetLatchedStereoFrame(stereo)){PoisonFrame(OutRunVR::StereoFailureMissingLatchedPose);return false;}
			draw.stereoFrame=stereo;BuildEyeConstants(device,stereo,draw);return true;
		}

		template <typename DrawCall>
		HRESULT ExecuteStereoDraw(IDirect3DDevice9* device, DrawCall&& drawCall)
		{
			DrawStereoState draw{};
			if (!PrepareDuplicatedDraw(device, draw))
				return drawCall();

			D3DVIEWPORT9 savedViewport{};
			if(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return drawCall();}
			if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.eyeConstants[0])){const bool rolledBack=SetWvpOneRegisterAtATime(device,draw.originalConstants);PoisonFrame(OutRunVR::StereoFailureLeftWvpUploadFailed);if(!rolledBack)NoteRestoreFailure("left-eye c64 rollback");return drawCall();}

			const HRESULT leftHr = drawCall();
			if(FAILED(leftHr)){PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.originalConstants))NoteRestoreFailure("left draw c64");return leftHr;}

			IDirect3DSurface9* savedRt = TrackedRenderTarget;
			IDirect3DSurface9* savedDepth = TrackedDepthStencil;
			HRESULT rightHr = D3D_OK;
			bool restoreOk = true;
			{
				InternalPassScope guard;
				rightHr = SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
				if (SUCCEEDED(rightHr))
					rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
				if (SUCCEEDED(rightHr))
					rightHr = device->SetViewport(&savedViewport);
				if (SUCCEEDED(rightHr) && draw.worldStereo)
					rightHr = SetWvpOneRegisterAtATime(device, draw.eyeConstants[1]) ? D3D_OK : E_FAIL;
				if (SUCCEEDED(rightHr))
					rightHr = drawCall();

				restoreOk = RestoreRightPassState(device, savedRt, savedDepth,
					savedViewport, draw.originalConstants, draw.worldStereo);
			}

			FrameHadDuplicatedDraw = true;
			++DuplicatedDraws;
			if (draw.worldStereo)
			{
				if(FrameStereoPoseSequence==0){FrameStereoPoseSequence=draw.poseSequence;FrameStereoMetadata=draw.stereoFrame;}
				else if(FrameStereoPoseSequence!=draw.poseSequence){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);spdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");}
				FrameHadWorldStereo = true;
				++WorldStereoDraws;
				if (!FirstWorldStereoLogged)
				{
					FirstWorldStereoLogged = true;
					spdlog::info("VR stereo: TRUE GEOMETRY STEREO active; per-eye c64 + OpenXR asymmetric FOV confirmed");
				}
			}
			else
				++NonWorldDuplicatedDraws;

			if(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(draw.worldStereo?OutRunVR::StereoFailureRightWvpUploadFailed:OutRunVR::StereoFailureRightDrawFailed);}
			if (!restoreOk)
				NoteRestoreFailure("right-eye draw");
			return leftHr;
		}

		HRESULT __stdcall DrawPrimitiveDest(IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
			UINT startVertex, UINT primitiveCount)
		{
			auto call = [&]() { return DrawPrimitiveHook.stdcall<HRESULT>(device, type, startVertex, primitiveCount); };
			return ExecuteStereoDraw(device, call);
		}

		HRESULT __stdcall DrawIndexedPrimitiveDest(IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
			INT baseVertexIndex, UINT minVertexIndex, UINT numVertices, UINT startIndex, UINT primitiveCount)
		{
			auto call = [&]() { return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
				baseVertexIndex, minVertexIndex, numVertices, startIndex, primitiveCount); };
			return ExecuteStereoDraw(device, call);
		}

		HRESULT __stdcall DrawPrimitiveUPDest(IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
			UINT primitiveCount, const void* data, UINT stride)
		{
			if (InternalStereoPass)
				return DrawPrimitiveUPHook.stdcall<HRESULT>(device, type, primitiveCount, data, stride);
			auto call = [&]() { return DrawPrimitiveUPHook.stdcall<HRESULT>(device, type, primitiveCount, data, stride); };
			return ExecuteStereoDraw(device, call);
		}

		HRESULT __stdcall DrawIndexedPrimitiveUPDest(IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
			UINT minVertexIndex, UINT numVertices, UINT primitiveCount, const void* indexData,
			D3DFORMAT indexFormat, const void* vertexData, UINT stride)
		{
			auto call = [&]() { return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
				minVertexIndex, numVertices, primitiveCount, indexData, indexFormat, vertexData, stride); };
			return ExecuteStereoDraw(device, call);
		}

		HRESULT __stdcall ClearDest(IDirect3DDevice9* device, DWORD count, const D3DRECT* rects,
			DWORD flags, D3DCOLOR color, float z, DWORD stencil)
		{
			const bool candidate=!InternalStereoPass&&StereoWanted()&&TargetIsBackBuffer();bool duplicate=candidate;
			if(duplicate&&AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);duplicate=false;}
			if(duplicate&&!EnsureStereoResources(device)){PoisonFrame(OutRunVR::StereoFailureResourceUnavailable);duplicate=false;}
			const HRESULT leftHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);if(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);return leftHr;}
			D3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}
			IDirect3DSurface9* savedRt=TrackedRenderTarget;IDirect3DSurface9* savedDepth=TrackedDepthStencil;HRESULT rightHr=D3D_OK;bool restoreOk=true;{
				InternalPassScope guard;rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);if(SUCCEEDED(rightHr))rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);if(SUCCEEDED(rightHr))rightHr=device->SetViewport(&savedViewport);if(SUCCEEDED(rightHr))rightHr=ClearHook.stdcall<HRESULT>(device,count,rects,flags,color,z,stencil);restoreOk=RestoreRightPassState(device,savedRt,savedDepth,savedViewport,nullptr,false);}
			if(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0) RightDepthSynchronized = true;if(!restoreOk)NoteRestoreFailure("right-eye clear");return leftHr;
		}

		HRESULT __stdcall SetRenderTargetDest(IDirect3DDevice9* device, DWORD index, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);
			if (!InternalStereoPass && IsGameDevice(device) && SUCCEEDED(hr))
			{
				if (index == 0)
				{
					ReplaceSurfaceRef(TrackedRenderTarget, surface);
				}
				else if (index >= 1 && index <= 3)
					AuxRenderTargetActive[index - 1] = surface != nullptr;
			}
			return hr;
		}

		HRESULT __stdcall SetDepthStencilSurfaceDest(IDirect3DDevice9* device, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface);
			if (!InternalStereoPass && IsGameDevice(device) && SUCCEEDED(hr))
			{
				const bool changed=TrackedDepthStencil!=surface;ReplaceSurfaceRef(TrackedDepthStencil,surface);if(changed){if(StereoWanted()&&TargetIsBackBuffer())PoisonFrame(OutRunVR::StereoFailureDepthStateChanged);if(StereoResourcesReady&&!CreateRightDepthForTracked(device))StereoResourcesReady=false;}
			}
			return hr;
		}

		HRESULT __stdcall SetVertexShaderDest(IDirect3DDevice9* device, IDirect3DVertexShader9* shader)
		{
			const HRESULT hr = SetVertexShaderHook.stdcall<HRESULT>(device, shader);
			if (!InternalStereoPass && IsGameDevice(device) && SUCCEEDED(hr))
			{
				const std::uintptr_t next=reinterpret_cast<std::uintptr_t>(shader);const std::uintptr_t previous=CurrentVertexShaderIdentity.load(std::memory_order_acquire);if(next!=previous){CurrentVertexShaderIdentity.store(next,std::memory_order_release);std::uint64_t serial=VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel)+1;if(serial==0)VertexShaderSerial.fetch_add(1,std::memory_order_acq_rel);}
			}
			return hr;
		}

		void MaybeLogSummary()
		{
			if (!Settings::VRTelemetry)
				return;
			const ULONGLONG now = GetTickCount64();
			if (now - LastSummaryMs < 5000)
				return;
			LastSummaryMs = now;
			spdlog::info("VR stereo: draws={} world={} ui/effect={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseSeq={}",
				DuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws,
				StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,
				MrtRejectedDraws, RestoreFailures, FrameStereoPoseSequence);
		}

		HRESULT __stdcall PresentDest(IDirect3DDevice9* device,const RECT* sourceRect,const RECT* destRect,HWND destWindowOverride,const RGNDATA* dirtyRegion)
		{
			if(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;
			if(stereoRequested&&FrameHadWorldStereo&&FrameHadDuplicatedDraw&&!FrameRightDrawFailed&&!FrameStereoIncomplete&&FrameStereoPoseSequence&&FrameStereoMetadata.valid&&EnsureStereoResources(device)){if(ComposeSbs(device)){++StereoComposeSuccess;composedStereo=true;pendingPoseSequence=FrameStereoPoseSequence;}else{++StereoComposeFailure;PoisonFrame(OutRunVR::StereoFailureComposeFailed);}}
			MaybeLogSummary();LARGE_INTEGER presentStart{};QueryPerformanceCounter(&presentStart);const HRESULT hr=PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);
			if(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){const std::uint32_t frameId=NextStereoFrameId();std::uint32_t low=static_cast<std::uint32_t>(presentStart.QuadPart);if(!low)low=1;PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId,low);PublishRenderFrame(OutRunVR::StereoSbsActive,frameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: SBS transport active; exact effective eye pose published in Frame.v1");}}
			else{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=OutRunVR::StereoFailurePresentFailed;const std::uint32_t fallback=stereoRequested?OutRunVR::StereoSbsFallbackMono:OutRunVR::StereoDisabled;PublishStereoState(fallback,false,0,0,0);PublishRenderFrame(fallback,0,0,presentStart.QuadPart,FrameFailureReason,nullptr);}
			FrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;
		}

		HRESULT __stdcall ResetDest(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)
		{
			if (!IsGameDevice(device))
				return ResetHook.stdcall<HRESULT>(device, params);
			ReleaseStereoResources();
			AuxRenderTargetActive = {};
			CurrentVertexShaderIdentity.store(0, std::memory_order_release);
			VertexShaderSerial.store(0, std::memory_order_release);
			FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState(OutRunVR::StereoDisabled,false,0,0,0);PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,OutRunVR::StereoFailureNone,nullptr);const HRESULT hr=ResetHook.stdcall<HRESULT>(device,params);
			if (SUCCEEDED(hr))
				EnsureStereoResources(device);
			return hr;
		}

		bool InstallStereoHooks(IDirect3DDevice9* device)
		{
			if (!device)
				return false;
			void** vtable = *reinterpret_cast<void***>(device);
			if (!vtable)
				return false;

			ResetHook = safetyhook::create_inline(vtable[ResetVtableIndex], ResetDest);
			PresentHook = safetyhook::create_inline(vtable[PresentVtableIndex], PresentDest);
			SetRenderTargetHook = safetyhook::create_inline(vtable[SetRenderTargetVtableIndex], SetRenderTargetDest);
			SetDepthStencilSurfaceHook = safetyhook::create_inline(
				vtable[SetDepthStencilSurfaceVtableIndex], SetDepthStencilSurfaceDest);
			ClearHook = safetyhook::create_inline(vtable[ClearVtableIndex], ClearDest);
			DrawPrimitiveHook = safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex], DrawPrimitiveDest);
			DrawIndexedPrimitiveHook = safetyhook::create_inline(
				vtable[DrawIndexedPrimitiveVtableIndex], DrawIndexedPrimitiveDest);
			DrawPrimitiveUPHook = safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex], DrawPrimitiveUPDest);
			DrawIndexedPrimitiveUPHook = safetyhook::create_inline(
				vtable[DrawIndexedPrimitiveUPVtableIndex], DrawIndexedPrimitiveUPDest);
			SetVertexShaderHook = safetyhook::create_inline(vtable[SetVertexShaderVtableIndex], SetVertexShaderDest);

			if (!ResetHook || !PresentHook || !SetRenderTargetHook || !SetDepthStencilSurfaceHook ||
				!ClearHook || !DrawPrimitiveHook || !DrawIndexedPrimitiveHook ||
				!DrawPrimitiveUPHook || !DrawIndexedPrimitiveUPHook || !SetVertexShaderHook)
			{
				spdlog::error("VR stereo: failed to install one or more D3D9 hooks");
				return false;
			}

			IDirect3DVertexShader9* shader = nullptr;
			if (SUCCEEDED(device->GetVertexShader(&shader)) && shader)
			{
				CurrentVertexShaderIdentity.store(reinterpret_cast<std::uintptr_t>(shader), std::memory_order_release);
				VertexShaderSerial.store(1, std::memory_order_release);
				shader->Release();
			}
			InitializeAuxRenderTargetState(device);
			EnsureSharedState();
			EnsureRenderFrameState();
			EnsureStereoResources(device);
			spdlog::info("VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS)");
			return true;
		}

		DWORD WINAPI StereoInstallThread(void*)
		{
			Sleep(250);
			for (int attempt = 0; attempt < 1200; ++attempt)
			{
				if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
				{
					if (!InstallStereoHooks(*Game::D3DDevice_ptr))
						spdlog::error("VR stereo: renderer hook installation failed");
					return 0;
				}
				Sleep(100);
			}
			spdlog::warn("VR stereo: D3D9 device did not appear; stereo hooks not installed");
			return 0;
		}
	}

	bool IsInternalStereoPassActive()
	{
		return InternalStereoPass;
	}

	bool GetCurrentShaderEpoch(std::uintptr_t& shaderIdentity, std::uint64_t& serial)
	{
		for (int attempt = 0; attempt < 3; ++attempt)
		{
			const std::uint64_t before = VertexShaderSerial.load(std::memory_order_acquire);
			const std::uintptr_t identity = CurrentVertexShaderIdentity.load(std::memory_order_acquire);
			const std::uint64_t after = VertexShaderSerial.load(std::memory_order_acquire);
			if (before == after)
			{
				shaderIdentity = identity;
				serial = after;
				return identity != 0 && after != 0;
			}
		}
		shaderIdentity = 0;
		serial = 0;
		return false;
	}

	class VRStereoHook : public Hook
	{
	public:
		std::string_view description() override { return "OpenXRVRStereo"; }
		bool validate() override { return true; }
		bool apply() override
		{
			HANDLE thread = CreateThread(nullptr, 0, StereoInstallThread, nullptr, 0, nullptr);
			if (!thread)
			{
				spdlog::error("VR stereo: failed to create installer thread: {}", GetLastError());
				return false;
			}
			CloseHandle(thread);
			return true;
		}
		static VRStereoHook instance;
	};

	VRStereoHook VRStereoHook::instance;
}
