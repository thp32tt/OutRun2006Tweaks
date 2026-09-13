#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr_shared.hpp"

// Renderer-boundary camera probe for the OpenXR branch.
//
// Why this exists:
// hooks_vr.cpp composes the HMD pose into EvWorkCamera::d3dmatrix140 after
// CalcCameraMatrix. That proves the game-side camera object changed, but not
// that the matrix which reaches Direct3D is the same one. Mature injector-style
// VR mods solve this exact ambiguity by instrumenting the last render boundary,
// rather than continuing to guess at camera math upstream.
//
// This file is deliberately read-only: it never changes a game or D3D matrix.
// It identifies which EvWorkCamera matrix (if any) reaches D3D9 through either
// SetTransform(D3DTS_VIEW) or SetVertexShaderConstantF. Once runtime telemetry
// identifies the real sink we can move the head-pose composition there without
// touching wheel, multi-device or FFB code.

namespace OutRunVRRendererProbe
{
	namespace
	{
		constexpr std::size_t CameraMatrixCount = 7;
		constexpr std::size_t SetTransformVtableIndex = 44;
		constexpr std::size_t SetVertexShaderConstantFVtableIndex = 94;
		constexpr float MatrixEpsilon = 1.0e-4f;
		constexpr ULONGLONG ProbeDurationMs = 30000;

		const char* CameraMatrixNames[CameraMatrixCount] = {
			"d3dmatrix140",
			"d3dmatrix180",
			"cam_matrix_1C0",
			"d3dmatrix200",
			"d3dmatrix240",
			"d3dmatrix280",
			"d3dmatrix2C0",
		};

		SafetyHookInline SetTransformHook{};
		SafetyHookInline SetVertexShaderConstantFHook{};

		HANDLE ProbeMapping = nullptr;
		const SharedPoseState* ProbeSharedState = nullptr;
		ULONGLONG LastMappingAttemptMs = 0;
		ULONGLONG ProbeStartMs = 0;
		ULONGLONG LastSummaryMs = 0;

		std::atomic<std::uint32_t> SeenMask{ 0 };
		std::atomic<std::uint64_t> ViewTransformCalls{ 0 };
		std::atomic<std::uint64_t> VertexConstantCalls{ 0 };
		std::atomic<bool> ProbeExpiredLogged{ false };

		enum class ProbeApi : std::uint32_t
		{
			SetTransform = 0,
			VertexConstants = 1,
		};

		bool EnsureSharedState()
		{
			if (ProbeSharedState)
				return true;

			const ULONGLONG now = GetTickCount64();
			if (now - LastMappingAttemptMs < 1000)
				return false;
			LastMappingAttemptMs = now;

			ProbeMapping = OpenFileMappingW(FILE_MAP_READ, FALSE, SharedMemoryName);
			if (!ProbeMapping)
				return false;

			ProbeSharedState = static_cast<const SharedPoseState*>(MapViewOfFile(
				ProbeMapping, FILE_MAP_READ, 0, 0, sizeof(SharedPoseState)));
			if (!ProbeSharedState)
			{
				CloseHandle(ProbeMapping);
				ProbeMapping = nullptr;
				return false;
			}
			return true;
		}

		bool HostPoseIsLive()
		{
			if (!EnsureSharedState())
				return false;
			if (ProbeSharedState->magic != SharedMagic ||
				ProbeSharedState->protocolVersion != SharedProtocolVersion ||
				ProbeSharedState->structSize != sizeof(SharedPoseState))
				return false;
			return (ProbeSharedState->flags & HostAlive) != 0 &&
				(ProbeSharedState->flags & OrientationValid) != 0 &&
				ProbeSharedState->hostPid != 0;
		}

		bool ProbeWindowIsActive()
		{
			if (!HostPoseIsLive())
			{
				ProbeStartMs = 0;
				ProbeExpiredLogged.store(false, std::memory_order_relaxed);
				return false;
			}

			if (!Game::current_mode || !Game::game_start_progress_code || !Game::is_in_game())
				return false;
			if (!Game::camera())
				return false;

			const ULONGLONG now = GetTickCount64();
			if (!ProbeStartMs)
			{
				ProbeStartMs = now;
				spdlog::info("VR renderer probe: capture window started (30s)");
			}

			if (now - ProbeStartMs <= ProbeDurationMs)
				return true;

			if (!ProbeExpiredLogged.exchange(true, std::memory_order_relaxed))
				spdlog::info("VR renderer probe: capture window finished mask=0x{:08X}", SeenMask.load());
			return false;
		}

		void GetCameraMatrices(EvWorkCamera* cam, const D3DMATRIX* out[CameraMatrixCount])
		{
			out[0] = &cam->d3dmatrix140;
			out[1] = &cam->d3dmatrix180;
			out[2] = &cam->cam_matrix_1C0;
			out[3] = &cam->d3dmatrix200;
			out[4] = &cam->d3dmatrix240;
			out[5] = &cam->d3dmatrix280;
			out[6] = &cam->d3dmatrix2C0;
		}

		bool MatrixNear(const float* candidate, const D3DMATRIX& matrix, bool transposed)
		{
			for (int row = 0; row < 4; ++row)
			{
				for (int col = 0; col < 4; ++col)
				{
					const float a = candidate[row * 4 + col];
					const float b = transposed ? matrix.m[col][row] : matrix.m[row][col];
					if (!std::isfinite(a) || !std::isfinite(b) || std::fabs(a - b) > MatrixEpsilon)
						return false;
				}
			}
			return true;
		}

		void ReportMatch(ProbeApi api, std::size_t matrixIndex, bool transposed, UINT shaderRegister)
		{
			const std::uint32_t apiBase = api == ProbeApi::VertexConstants ? 14u : 0u;
			const std::uint32_t transposeBase = transposed ? 7u : 0u;
			const std::uint32_t bitIndex = apiBase + transposeBase + static_cast<std::uint32_t>(matrixIndex);
			const std::uint32_t bit = 1u << bitIndex;
			const std::uint32_t previous = SeenMask.fetch_or(bit, std::memory_order_relaxed);
			if (previous & bit)
				return;

			const char* apiName = api == ProbeApi::SetTransform
				? "SetTransform(D3DTS_VIEW)"
				: "SetVertexShaderConstantF";
			const char* layoutName = transposed ? "transposed" : "direct";
			const char* trackedMarker = matrixIndex == 0 ? " [TRACKED_VIEW_REACHED_RENDERER]" : "";

			if (api == ProbeApi::VertexConstants)
			{
				spdlog::info("VR renderer probe: {} matched {} at c{} ({}){}",
					apiName, CameraMatrixNames[matrixIndex], shaderRegister, layoutName, trackedMarker);
			}
			else
			{
				spdlog::info("VR renderer probe: {} matched {} ({}){}",
					apiName, CameraMatrixNames[matrixIndex], layoutName, trackedMarker);
			}
		}

		void ProbeMatrix(const float* candidate, ProbeApi api, UINT shaderRegister)
		{
			EvWorkCamera* cam = Game::camera();
			if (!cam || !candidate)
				return;

			const D3DMATRIX* matrices[CameraMatrixCount]{};
			GetCameraMatrices(cam, matrices);
			for (std::size_t i = 0; i < CameraMatrixCount; ++i)
			{
				if (MatrixNear(candidate, *matrices[i], false))
					ReportMatch(api, i, false, shaderRegister);
				if (MatrixNear(candidate, *matrices[i], true))
					ReportMatch(api, i, true, shaderRegister);
			}
		}

		void MaybeLogSummary()
		{
			const ULONGLONG now = GetTickCount64();
			if (now - LastSummaryMs < 1000)
				return;
			LastSummaryMs = now;

			spdlog::info("VR renderer probe: viewSetCalls={} vsConstantCalls={} matchMask=0x{:08X}",
				ViewTransformCalls.load(std::memory_order_relaxed),
				VertexConstantCalls.load(std::memory_order_relaxed),
				SeenMask.load(std::memory_order_relaxed));
		}

		HRESULT __stdcall SetTransformDest(
			IDirect3DDevice9* device, D3DTRANSFORMSTATETYPE state, const D3DMATRIX* matrix)
		{
			if (state == D3DTS_VIEW && matrix && ProbeWindowIsActive())
			{
				ViewTransformCalls.fetch_add(1, std::memory_order_relaxed);
				ProbeMatrix(reinterpret_cast<const float*>(matrix), ProbeApi::SetTransform, 0);
				MaybeLogSummary();
			}
			return SetTransformHook.stdcall<HRESULT>(device, state, matrix);
		}

		HRESULT __stdcall SetVertexShaderConstantFDest(
			IDirect3DDevice9* device, UINT startRegister, const float* constantData, UINT vector4fCount)
		{
			if (constantData && vector4fCount >= 4 && ProbeWindowIsActive())
			{
				VertexConstantCalls.fetch_add(1, std::memory_order_relaxed);

				// A matrix occupies four consecutive float4 registers. Slide by one
				// register so batched uploads are covered too. Cap a pathological
				// upload at the D3D9 vertex constant limit (256 registers).
				const UINT cappedCount = std::min<UINT>(vector4fCount, 256);
				for (UINT offset = 0; offset + 4 <= cappedCount; ++offset)
					ProbeMatrix(constantData + offset * 4, ProbeApi::VertexConstants, startRegister + offset);
				MaybeLogSummary();
			}
			return SetVertexShaderConstantFHook.stdcall<HRESULT>(
				device, startRegister, constantData, vector4fCount);
		}

		bool InstallD3D9Hooks(IDirect3DDevice9* device)
		{
			if (!device)
				return false;

			void** vtable = *reinterpret_cast<void***>(device);
			if (!vtable)
				return false;

			SetTransformHook = safetyhook::create_inline(
				vtable[SetTransformVtableIndex], SetTransformDest);
			SetVertexShaderConstantFHook = safetyhook::create_inline(
				vtable[SetVertexShaderConstantFVtableIndex], SetVertexShaderConstantFDest);

			if (!SetTransformHook || !SetVertexShaderConstantFHook)
			{
				spdlog::error("VR renderer probe: failed to hook D3D9 renderer boundary");
				return false;
			}

			spdlog::info(
				"VR renderer probe: D3D9 hooks installed (SetTransform vtbl[44], SetVertexShaderConstantF vtbl[94])");
			return true;
		}

		DWORD WINAPI RendererProbeInstallThread(void*)
		{
			// Hook registration happens before the game's D3D9 device is guaranteed
			// to exist. Wait off the render thread, install once, then exit.
			for (int attempt = 0; attempt < 1200; ++attempt)
			{
				if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
				{
					InstallD3D9Hooks(*Game::D3DDevice_ptr);
					return 0;
				}
				Sleep(100);
			}

			spdlog::warn("VR renderer probe: D3D9 device did not appear; probe not installed");
			return 0;
		}
	}

	class VRRendererProbeHook : public Hook
	{
	public:
		std::string_view description() override { return "OpenXRVRRendererProbe"; }
		bool validate() override { return true; }

		bool apply() override
		{
			HANDLE thread = CreateThread(nullptr, 0, RendererProbeInstallThread, nullptr, 0, nullptr);
			if (!thread)
			{
				spdlog::error("VR renderer probe: failed to create installer thread: {}", GetLastError());
				return false;
			}
			CloseHandle(thread);
			return true;
		}

		static VRRendererProbeHook instance;
	};

	VRRendererProbeHook VRRendererProbeHook::instance;
}
