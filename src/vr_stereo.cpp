#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
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
// matching RIGHT-eye render target while all renderer state is still alive.
//
// vr_renderer_probe.cpp remains the single head-tracking/recenter authority.
// This file reads the c64 WVP that probe already uploaded, removes only the game
// projection, appends the OpenXR per-eye position, and installs the OpenXR
// asymmetric per-eye FOV. HUD/non-world draws are duplicated unchanged to the
// two full-size eye surfaces, so screen-space UI does not get cut in half.
//
// At Present both full-size eye surfaces are resolved and drawn side-by-side to
// the real backbuffer. The x64 host crops that SBS transport and submits it as
// XrCompositionLayerProjection.

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
		constexpr std::uintptr_t OutRunWorldViewRva = 0x0095DB20u - 0x00400000u;
		constexpr LONGLONG HostPoseStaleMs = 250;

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
		LARGE_INTEGER QpcFrequency{};

		IDirect3DSurface9* BackBuffer = nullptr;
		IDirect3DSurface9* TrackedRenderTarget = nullptr;
		IDirect3DSurface9* TrackedDepthStencil = nullptr;
		IDirect3DSurface9* RightEyeSurface = nullptr;
		IDirect3DSurface9* RightEyeDepth = nullptr;
		IDirect3DTexture9* LeftResolveTexture = nullptr;
		IDirect3DSurface9* LeftResolveSurface = nullptr;
		IDirect3DTexture9* RightResolveTexture = nullptr;
		IDirect3DSurface9* RightResolveSurface = nullptr;
		IDirect3DVertexShader9* CurrentVertexShader = nullptr; // weak; device owns state ref

		D3DSURFACE_DESC BackBufferDesc{};
		bool StereoResourcesReady = false;
		bool InternalStereoPass = false;
		bool FrameHadDuplicatedDraw = false;
		bool FrameHadWorldStereo = false;
		bool FrameRightDrawFailed = false;
		std::uint32_t StereoFrameCounter = 0;
		ULONGLONG LastSummaryMs = 0;
		std::uint64_t DuplicatedDraws = 0;
		std::uint64_t WorldStereoDraws = 0;
		std::uint64_t NonWorldDuplicatedDraws = 0;
		std::uint64_t StereoComposeSuccess = 0;
		std::uint64_t StereoComposeFailure = 0;
		bool FirstStereoActiveLogged = false;
		bool FirstWorldStereoLogged = false;

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

		bool Rigidish(const D3DMATRIX& m)
		{
			if (!MatrixFinite(m) || std::fabs(m._14) > 0.1f || std::fabs(m._24) > 0.1f ||
				std::fabs(m._34) > 0.1f || std::fabs(m._44 - 1.0f) > 0.15f)
				return false;
			const float rows[3][3] = {
				{m._11, m._12, m._13}, {m._21, m._22, m._23}, {m._31, m._32, m._33}
			};
			for (int r = 0; r < 3; ++r)
			{
				float len = 0.0f;
				for (int c = 0; c < 3; ++c) len += rows[r][c] * rows[r][c];
				if (!std::isfinite(len) || std::fabs(len - 1.0f) > 0.30f)
					return false;
			}
			for (int a = 0; a < 3; ++a)
				for (int b = a + 1; b < 3; ++b)
				{
					float dot = 0.0f;
					for (int c = 0; c < 3; ++c) dot += rows[a][c] * rows[b][c];
					if (std::fabs(dot) > 0.20f)
						return false;
				}
			return true;
		}

		float FloatFromBits(std::uint32_t bits)
		{
			float value = 0.0f;
			std::memcpy(&value, &bits, sizeof(value));
			return value;
		}

		struct StereoSnapshot
		{
			OutRunVR::SharedFov fov[2]{};
			float eyeOffset[2][3]{};
		};

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
			QueryPerformanceFrequency(&QpcFrequency);
			return true;
		}

		bool FovValid(const OutRunVR::SharedFov& fov)
		{
			const float limit = 1.56f;
			return std::isfinite(fov.angleLeft) && std::isfinite(fov.angleRight) &&
				std::isfinite(fov.angleUp) && std::isfinite(fov.angleDown) &&
				fov.angleLeft > -limit && fov.angleRight < limit &&
				fov.angleDown > -limit && fov.angleUp < limit &&
				fov.angleRight > fov.angleLeft + 0.05f &&
				fov.angleUp > fov.angleDown + 0.05f;
		}

		bool ReadStereoSnapshot(StereoSnapshot& out)
		{
			if (!EnsureSharedState())
				return false;
			if (QpcFrequency.QuadPart <= 0)
				QueryPerformanceFrequency(&QpcFrequency);
			OutRunVR::SharedPoseState snapshot{};
			bool stable = false;
			for (int attempt = 0; attempt < 4; ++attempt)
			{
				const std::uint32_t before = SharedState->sequence;
				if (before & 1u)
					continue;
				MemoryBarrier();
				std::memcpy(&snapshot, SharedState, sizeof(snapshot));
				MemoryBarrier();
				const std::uint32_t after = SharedState->sequence;
				if (before == after && !(after & 1u))
				{
					stable = true;
					break;
				}
			}
			if (!stable || snapshot.magic != OutRunVR::SharedMagic ||
				snapshot.protocolVersion != OutRunVR::SharedProtocolVersion ||
				snapshot.structSize != sizeof(snapshot) ||
				(snapshot.flags & (OutRunVR::HostAlive | OutRunVR::StereoViewsValid)) !=
					(OutRunVR::HostAlive | OutRunVR::StereoViewsValid))
				return false;
			LARGE_INTEGER now{};
			QueryPerformanceCounter(&now);
			if (snapshot.sampleQpc <= 0 || QpcFrequency.QuadPart <= 0)
				return false;
			const LONGLONG age = now.QuadPart - snapshot.sampleQpc;
			if (age < 0 || age > (QpcFrequency.QuadPart * HostPoseStaleMs) / 1000)
				return false;
			out.fov[0] = snapshot.eyeFov[0];
			out.fov[1] = snapshot.eyeFov[1];
			if (!FovValid(out.fov[0]) || !FovValid(out.fov[1]))
				return false;
			const std::uint32_t indexes[2][3] = {
				{ OutRunVR::HostEyeOffsetLeftXIndex, OutRunVR::HostEyeOffsetLeftYIndex, OutRunVR::HostEyeOffsetLeftZIndex },
				{ OutRunVR::HostEyeOffsetRightXIndex, OutRunVR::HostEyeOffsetRightYIndex, OutRunVR::HostEyeOffsetRightZIndex }
			};
			for (int eye = 0; eye < 2; ++eye)
				for (int axis = 0; axis < 3; ++axis)
				{
					out.eyeOffset[eye][axis] = FloatFromBits(snapshot.reserved[indexes[eye][axis]]);
					if (!std::isfinite(out.eyeOffset[eye][axis]) || std::fabs(out.eyeOffset[eye][axis]) > 0.25f)
						return false;
				}
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

		bool ReadRendererMatrices(D3DMATRIX& projection, D3DMATRIX& worldView)
		{
			if (!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX)) ||
				!ImageContainsRange(OutRunWorldViewRva, sizeof(D3DMATRIX)))
				return false;
			const auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
			const auto* worldViewPtr = Module::exe_ptr<D3DMATRIX>(OutRunWorldViewRva);
			if (!IsReadableRange(projectionPtr, sizeof(D3DMATRIX)) ||
				!IsReadableRange(worldViewPtr, sizeof(D3DMATRIX)))
				return false;
			std::memcpy(&projection, projectionPtr, sizeof(projection));
			std::memcpy(&worldView, worldViewPtr, sizeof(worldView));
			return MatrixFinite(projection) && MatrixFinite(worldView) &&
				std::fabs(projection._34 + 1.0f) < 0.25f && std::fabs(projection._44) < 0.25f;
		}

		struct DrawStereoState
		{
			float originalConstants[16]{};
			float eyeConstants[2][16]{};
			bool worldStereo = false;
		};

		bool BuildEyeConstants(IDirect3DDevice9* device, const StereoSnapshot& stereo, DrawStereoState& state)
		{
			if (!CurrentVertexShader)
				return false;
			if (FAILED(device->GetVertexShaderConstantF(OutRunWvpRegister,
				state.originalConstants, OutRunWvpRegisterCount)))
				return false;
			D3DMATRIX projection{};
			D3DMATRIX worldView{};
			if (!ReadRendererMatrices(projection, worldView))
				return false;
			D3DMATRIX uploadedT{};
			std::memcpy(&uploadedT, state.originalConstants, sizeof(uploadedT));
			const D3DMATRIX currentWvp = TransposeMatrix(uploadedT);
			D3DMATRIX invProjection{};
			D3DMATRIX invWorldView{};
			if (!InvertMatrix(projection, invProjection) || !InvertMatrix(worldView, invWorldView))
				return false;
			// currentWvp already contains the mono renderer-probe head correction.
			const D3DMATRIX correctedWorldView = MultiplyMatrix(currentWvp, invProjection);
			const D3DMATRIX headDelta = MultiplyMatrix(invWorldView, correctedWorldView);
			if (!Rigidish(headDelta))
				return false;

			for (int eye = 0; eye < 2; ++eye)
			{
				D3DMATRIX eyeInverse = IdentityMatrix();
				eyeInverse._41 = -stereo.eyeOffset[eye][0] * Settings::VRWorldScale;
				eyeInverse._42 = -stereo.eyeOffset[eye][1] * Settings::VRWorldScale;
				eyeInverse._43 = -stereo.eyeOffset[eye][2] * Settings::VRWorldScale;
				const D3DMATRIX eyeProjection = ProjectionFromFov(projection, stereo.fov[eye]);
				const D3DMATRIX eyeWvp = MultiplyMatrix(
					MultiplyMatrix(correctedWorldView, eyeInverse), eyeProjection);
				if (!MatrixFinite(eyeWvp))
					return false;
				const D3DMATRIX eyeWvpT = TransposeMatrix(eyeWvp);
				std::memcpy(state.eyeConstants[eye], &eyeWvpT, sizeof(eyeWvpT));
			}
			state.worldStereo = true;
			return true;
		}

		bool SetWvpOneRegisterAtATime(IDirect3DDevice9* device, const float* constants)
		{
			// The mono renderer hook only recognizes a candidate when c64..c67 are
			// present in one call. Four 1-register writes deliberately pass through
			// unchanged, avoiding a second hook on SetVertexShaderConstantF.
			for (UINT reg = 0; reg < OutRunWvpRegisterCount; ++reg)
				if (FAILED(device->SetVertexShaderConstantF(
					OutRunWvpRegister + reg, constants + reg * 4, 1)))
					return false;
			return true;
		}

		bool StereoWanted()
		{
			if (!Settings::VRStereo || !GameplayActive())
				return false;
			return Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;
		}

		bool TargetIsBackBuffer()
		{
			return BackBuffer && TrackedRenderTarget && TrackedRenderTarget == BackBuffer;
		}

		void ReleaseStereoResources()
		{
			StereoResourcesReady = false;
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

		bool EnsureStereoResources(IDirect3DDevice9* device)
		{
			if (!device)
				return false;
			IDirect3DSurface9* newBackBuffer = nullptr;
			if (FAILED(device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &newBackBuffer)) || !newBackBuffer)
				return false;
			D3DSURFACE_DESC desc{};
			newBackBuffer->GetDesc(&desc);
			if (StereoResourcesReady && BackBuffer && newBackBuffer == BackBuffer &&
				desc.Width == BackBufferDesc.Width && desc.Height == BackBufferDesc.Height &&
				desc.Format == BackBufferDesc.Format && desc.MultiSampleType == BackBufferDesc.MultiSampleType)
			{
				newBackBuffer->Release();
				return true;
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
			if (SUCCEEDED(device->GetDepthStencilSurface(&currentDepth)) && currentDepth)
				TrackedDepthStencil = currentDepth;

			if (FAILED(device->CreateRenderTarget(desc.Width, desc.Height, desc.Format,
				desc.MultiSampleType, desc.MultiSampleQuality, FALSE, &RightEyeSurface, nullptr)))
			{
				ReleaseStereoResources();
				return false;
			}
			if (TrackedDepthStencil)
			{
				D3DSURFACE_DESC depthDesc{};
				TrackedDepthStencil->GetDesc(&depthDesc);
				if (FAILED(device->CreateDepthStencilSurface(desc.Width, desc.Height, depthDesc.Format,
					depthDesc.MultiSampleType, depthDesc.MultiSampleQuality, FALSE,
					&RightEyeDepth, nullptr)))
				{
					ReleaseStereoResources();
					return false;
				}
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

			InternalStereoPass = true;
			SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
			else
				device->SetDepthStencilSurface(RightEyeDepth);
			ClearHook.stdcall<HRESULT>(device, 0u, static_cast<const D3DRECT*>(nullptr),
				D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL,
				D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0u);
			if (TrackedRenderTarget)
				SetRenderTargetHook.stdcall<HRESULT>(device, 0u, TrackedRenderTarget);
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, TrackedDepthStencil);
			else
				device->SetDepthStencilSurface(TrackedDepthStencil);
			InternalStereoPass = false;

			StereoResourcesReady = true;
			spdlog::info("VR stereo: full-size eye surfaces ready {}x{} format={} msaa={} quality={}",
				desc.Width, desc.Height, static_cast<int>(desc.Format),
				static_cast<int>(desc.MultiSampleType), desc.MultiSampleQuality);
			return true;
		}

		void PublishStereoState(std::uint32_t state, bool worldStereo)
		{
			if (!EnsureSharedState())
				return;
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),
				static_cast<LONG>(state));
			if (state == OutRunVR::StereoSbsActive)
			{
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoFrameIndex]),
					static_cast<LONG>(++StereoFrameCounter));
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferWidthIndex]),
					static_cast<LONG>(BackBufferDesc.Width));
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]),
					static_cast<LONG>(BackBufferDesc.Height));
				LONG bits = static_cast<LONG>(OutRunVR::ClientStereoActive | OutRunVR::ClientStereoDrawDuplicated);
				if (worldStereo)
					bits |= static_cast<LONG>(OutRunVR::ClientStereoWorldDraw);
				InterlockedOr(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]), bits);
			}
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
			stateBlock->Capture();
			IDirect3DSurface9* savedRt = nullptr;
			IDirect3DSurface9* savedDepth = nullptr;
			device->GetRenderTarget(0, &savedRt);
			device->GetDepthStencilSurface(&savedDepth);
			D3DVIEWPORT9 savedViewport{};
			device->GetViewport(&savedViewport);
			const std::uint32_t savedClientFlags = SharedState
				? SharedState->reserved[OutRunVR::ClientFlagsIndex] : 0;

			bool success = false;
			InternalStereoPass = true;
			do
			{
				if (FAILED(SetRenderTargetHook.stdcall<HRESULT>(device, 0u, BackBuffer))) break;
				if (SetDepthStencilSurfaceHook)
					SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, static_cast<IDirect3DSurface9*>(nullptr));
				else
					device->SetDepthStencilSurface(nullptr);
				if (FAILED(device->BeginScene())) break;
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
				device->SetViewport(&full);
				device->Clear(0, nullptr, D3DCLEAR_TARGET, D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0);
				const bool leftOk = DrawTextureHalf(device, LeftResolveTexture, false);
				const bool rightOk = DrawTextureHalf(device, RightResolveTexture, true);
				device->SetTexture(0, nullptr);
				const HRESULT endHr = device->EndScene();
				success = leftOk && rightOk && SUCCEEDED(endHr);
			} while (false);
			InternalStereoPass = false;

			stateBlock->Apply();
			stateBlock->Release();
			if (savedRt)
			{
				SetRenderTargetHook.stdcall<HRESULT>(device, 0u, savedRt);
				savedRt->Release();
			}
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth);
			else
				device->SetDepthStencilSurface(savedDepth);
			if (savedDepth) savedDepth->Release();
			device->SetViewport(&savedViewport);

			// The extra D3D BeginScene/EndScene is compositor-only. Preserve the
			// real game scene's client telemetry after vr_renderer_probe observes it.
			if (SharedState)
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientFlagsIndex]),
					static_cast<LONG>(savedClientFlags));
			return success;
		}

		bool PrepareDuplicatedDraw(IDirect3DDevice9* device, DrawStereoState& draw)
		{
			if (InternalStereoPass || !StereoWanted() || !TargetIsBackBuffer() ||
				!EnsureStereoResources(device))
				return false;
			StereoSnapshot stereo{};
			if (!ReadStereoSnapshot(stereo))
				return false;
			BuildEyeConstants(device, stereo, draw);
			return true;
		}

		template <typename DrawCall>
		HRESULT ExecuteStereoDraw(IDirect3DDevice9* device, DrawCall&& drawCall)
		{
			DrawStereoState draw{};
			if (!PrepareDuplicatedDraw(device, draw))
				return drawCall();

			if (draw.worldStereo && !SetWvpOneRegisterAtATime(device, draw.eyeConstants[0]))
				return drawCall();
			const HRESULT leftHr = drawCall();
			if (FAILED(leftHr))
			{
				if (draw.worldStereo)
					SetWvpOneRegisterAtATime(device, draw.originalConstants);
				return leftHr;
			}

			IDirect3DSurface9* savedRt = TrackedRenderTarget;
			IDirect3DSurface9* savedDepth = TrackedDepthStencil;
			InternalStereoPass = true;
			HRESULT rightHr = SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
			if (SUCCEEDED(rightHr))
			{
				if (SetDepthStencilSurfaceHook)
					rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
				else
					rightHr = device->SetDepthStencilSurface(RightEyeDepth);
			}
			if (SUCCEEDED(rightHr) && draw.worldStereo)
				rightHr = SetWvpOneRegisterAtATime(device, draw.eyeConstants[1]) ? D3D_OK : E_FAIL;
			if (SUCCEEDED(rightHr))
				rightHr = drawCall();
			if (savedRt)
				SetRenderTargetHook.stdcall<HRESULT>(device, 0u, savedRt);
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth);
			else
				device->SetDepthStencilSurface(savedDepth);
			if (draw.worldStereo)
				SetWvpOneRegisterAtATime(device, draw.originalConstants);
			InternalStereoPass = false;

			FrameHadDuplicatedDraw = true;
			++DuplicatedDraws;
			if (draw.worldStereo)
			{
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
			if (FAILED(rightHr))
				FrameRightDrawFailed = true;
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
			StereoSnapshot snapshot{};
			const bool duplicate = !InternalStereoPass && StereoWanted() && TargetIsBackBuffer() &&
				EnsureStereoResources(device) && ReadStereoSnapshot(snapshot);
			const HRESULT leftHr = ClearHook.stdcall<HRESULT>(device, count, rects, flags, color, z, stencil);
			if (!duplicate || FAILED(leftHr))
				return leftHr;

			IDirect3DSurface9* savedRt = TrackedRenderTarget;
			IDirect3DSurface9* savedDepth = TrackedDepthStencil;
			InternalStereoPass = true;
			SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
			else
				device->SetDepthStencilSurface(RightEyeDepth);
			ClearHook.stdcall<HRESULT>(device, count, rects, flags, color, z, stencil);
			if (savedRt)
				SetRenderTargetHook.stdcall<HRESULT>(device, 0u, savedRt);
			if (SetDepthStencilSurfaceHook)
				SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, savedDepth);
			else
				device->SetDepthStencilSurface(savedDepth);
			InternalStereoPass = false;
			return leftHr;
		}

		HRESULT __stdcall SetRenderTargetDest(IDirect3DDevice9* device, DWORD index, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetRenderTargetHook.stdcall<HRESULT>(device, index, surface);
			if (!InternalStereoPass && IsGameDevice(device) && index == 0 && SUCCEEDED(hr))
				ReplaceSurfaceRef(TrackedRenderTarget, surface);
			return hr;
		}

		HRESULT __stdcall SetDepthStencilSurfaceDest(IDirect3DDevice9* device, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface);
			if (!InternalStereoPass && IsGameDevice(device) && SUCCEEDED(hr))
				ReplaceSurfaceRef(TrackedDepthStencil, surface);
			return hr;
		}

		HRESULT __stdcall SetVertexShaderDest(IDirect3DDevice9* device, IDirect3DVertexShader9* shader)
		{
			const HRESULT hr = SetVertexShaderHook.stdcall<HRESULT>(device, shader);
			if (!InternalStereoPass && IsGameDevice(device) && SUCCEEDED(hr))
				CurrentVertexShader = shader;
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
			spdlog::info("VR stereo: draws={} world={} ui/effect={} composeOk={} composeFail={} rightFail={}",
				DuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws,
				StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0);
		}

		HRESULT __stdcall PresentDest(IDirect3DDevice9* device, const RECT* sourceRect,
			const RECT* destRect, HWND destWindowOverride, const RGNDATA* dirtyRegion)
		{
			if (!IsGameDevice(device))
				return PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);

			if (StereoWanted() && FrameHadWorldStereo && FrameHadDuplicatedDraw && !FrameRightDrawFailed &&
				EnsureStereoResources(device))
			{
				if (ComposeSbs(device))
				{
					++StereoComposeSuccess;
					PublishStereoState(OutRunVR::StereoSbsActive, true);
					if (!FirstStereoActiveLogged)
					{
						FirstStereoActiveLogged = true;
						spdlog::info("VR stereo: SBS transport active; x64 host can submit XrCompositionLayerProjection");
					}
				}
				else
				{
					++StereoComposeFailure;
					PublishStereoState(OutRunVR::StereoSbsFallbackMono, false);
				}
			}
			else
				PublishStereoState(StereoWanted() ? OutRunVR::StereoSbsFallbackMono : OutRunVR::StereoDisabled, false);

			MaybeLogSummary();
			const HRESULT hr = PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);
			FrameHadDuplicatedDraw = false;
			FrameHadWorldStereo = false;
			FrameRightDrawFailed = false;
			return hr;
		}

		HRESULT __stdcall ResetDest(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)
		{
			if (!IsGameDevice(device))
				return ResetHook.stdcall<HRESULT>(device, params);
			ReleaseStereoResources();
			CurrentVertexShader = nullptr;
			const HRESULT hr = ResetHook.stdcall<HRESULT>(device, params);
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
				CurrentVertexShader = shader;
				shader->Release();
			}
			EnsureSharedState();
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
