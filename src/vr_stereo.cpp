#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr_shared.hpp"

// True-stereo renderer for OutRun 2006.
//
// Important invariant: simulation/input/FFB/render queues are NOT replayed.
// Each final D3D9 backbuffer draw is issued twice while all game render state is
// still alive: once into the left SBS half and once into the right. World draws
// derive their two eye matrices from the already head-corrected c64 WVP produced
// by vr_renderer_probe.cpp, so recenter/head tracking has one authoritative path.
// Non-world draws are duplicated unchanged, giving HUD/UI zero disparity.

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
		constexpr std::size_t DrawPrimitiveVtableIndex = 81;
		constexpr std::size_t DrawIndexedPrimitiveVtableIndex = 82;
		constexpr std::size_t DrawPrimitiveUPVtableIndex = 83;
		constexpr std::size_t DrawIndexedPrimitiveUPVtableIndex = 84;
		constexpr UINT WvpRegister = 64;
		constexpr UINT WvpRegisterCount = 4;
		constexpr std::uintptr_t ProjectionRva = 0x0095D8A0u - 0x00400000u;
		constexpr float MatrixEpsilon = 1.0e-3f;
		constexpr LONGLONG HostPoseStaleMs = 250;

		SafetyHookInline ResetHook{};
		SafetyHookInline PresentHook{};
		SafetyHookInline SetRenderTargetHook{};
		SafetyHookInline DrawPrimitiveHook{};
		SafetyHookInline DrawIndexedPrimitiveHook{};
		SafetyHookInline DrawPrimitiveUPHook{};
		SafetyHookInline DrawIndexedPrimitiveUPHook{};

		IDirect3DSurface9* BackbufferIdentity = nullptr; // weak identity, never AddRef-held across Reset
		bool Rt0IsBackbuffer = true;
		std::uint32_t BackbufferWidth = 0;
		std::uint32_t BackbufferHeight = 0;
		std::uint32_t StereoFrame = 0;
		std::uint64_t StereoDraws = 0;
		std::uint64_t StereoWorldDraws = 0;
		std::uint64_t StereoFallbackDraws = 0;
		ULONGLONG LastSummaryMs = 0;
		bool FirstStereoLog = false;

		struct Matrix4
		{
			float m[4][4]{};
		};

		struct StereoSnapshot
		{
			OutRunVR::SharedFov fov[2]{};
			float eyeOffset[2][3]{};
			std::uint32_t sequence = 0;
			bool valid = false;
		};

		bool IsGameDevice(IDirect3DDevice9* device)
		{
			return device && Game::D3DDevice_ptr && *Game::D3DDevice_ptr == device;
		}

		float BitsToFloat(std::uint32_t bits)
		{
			float v = 0.0f;
			std::memcpy(&v, &bits, sizeof(v));
			return v;
		}

		bool Finite(float v) { return std::isfinite(v); }

		bool MatrixFinite(const Matrix4& a)
		{
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					if (!Finite(a.m[r][c])) return false;
			return true;
		}

		Matrix4 Multiply(const Matrix4& a, const Matrix4& b)
		{
			Matrix4 out{};
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					for (int k = 0; k < 4; ++k)
						out.m[r][c] += a.m[r][k] * b.m[k][c];
			return out;
		}

		Matrix4 Transpose(const Matrix4& a)
		{
			Matrix4 out{};
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c)
					out.m[r][c] = a.m[c][r];
			return out;
		}

		bool Invert(const Matrix4& in, Matrix4& out)
		{
			float a[4][8]{};
			for (int r = 0; r < 4; ++r)
			{
				for (int c = 0; c < 4; ++c) a[r][c] = in.m[r][c];
				a[r][r + 4] = 1.0f;
			}
			for (int col = 0; col < 4; ++col)
			{
				int pivot = col;
				for (int r = col + 1; r < 4; ++r)
					if (std::fabs(a[r][col]) > std::fabs(a[pivot][col])) pivot = r;
				if (!Finite(a[pivot][col]) || std::fabs(a[pivot][col]) < 1.0e-8f) return false;
				if (pivot != col)
					for (int c = 0; c < 8; ++c) std::swap(a[pivot][c], a[col][c]);
				const float invPivot = 1.0f / a[col][col];
				for (int c = 0; c < 8; ++c) a[col][c] *= invPivot;
				for (int r = 0; r < 4; ++r)
				{
					if (r == col) continue;
					const float factor = a[r][col];
					for (int c = 0; c < 8; ++c) a[r][c] -= factor * a[col][c];
				}
			}
			for (int r = 0; r < 4; ++r)
				for (int c = 0; c < 4; ++c) out.m[r][c] = a[r][c + 4];
			return MatrixFinite(out);
		}

		Matrix4 Translation(float x, float y, float z)
		{
			Matrix4 out{};
			out.m[0][0] = out.m[1][1] = out.m[2][2] = out.m[3][3] = 1.0f;
			out.m[3][0] = x;
			out.m[3][1] = y;
			out.m[3][2] = z;
			return out;
		}

		bool AffineLike(const Matrix4& a)
		{
			return MatrixFinite(a) && std::fabs(a.m[0][3]) < 0.02f &&
				std::fabs(a.m[1][3]) < 0.02f && std::fabs(a.m[2][3]) < 0.02f &&
				std::fabs(a.m[3][3] - 1.0f) < 0.02f;
		}

		bool BuildEyeProjection(const Matrix4& gameProjection, const OutRunVR::SharedFov& fov, Matrix4& out)
		{
			const float A = gameProjection.m[2][2];
			const float B = gameProjection.m[3][2];
			if (!Finite(A) || !Finite(B) || std::fabs(A) < 1.0e-6f || std::fabs(A + 1.0f) < 1.0e-6f)
				return false;
			const float zn = B / A;
			const float zf = B / (A + 1.0f);
			if (!Finite(zn) || !Finite(zf) || zn <= 0.0f || zf <= zn)
				return false;
			if (!Finite(fov.angleLeft) || !Finite(fov.angleRight) || !Finite(fov.angleUp) || !Finite(fov.angleDown))
				return false;
			const float l = zn * std::tan(fov.angleLeft);
			const float r = zn * std::tan(fov.angleRight);
			const float b = zn * std::tan(fov.angleDown);
			const float t = zn * std::tan(fov.angleUp);
			if (!(l < r) || !(b < t)) return false;

			out = {};
			out.m[0][0] = 2.0f * zn / (r - l);
			out.m[1][1] = 2.0f * zn / (t - b);
			out.m[2][0] = (l + r) / (l - r);
			out.m[2][1] = (t + b) / (b - t);
			out.m[2][2] = zf / (zn - zf);
			out.m[2][3] = -1.0f;
			out.m[3][2] = zn * zf / (zn - zf);
			return MatrixFinite(out);
		}

		bool ReadStereoSnapshot(StereoSnapshot& out)
		{
			HANDLE mapping = OpenFileMappingW(FILE_MAP_READ, FALSE, OutRunVR::SharedMemoryName);
			if (!mapping) return false;
			auto* shared = static_cast<const OutRunVR::SharedPoseState*>(MapViewOfFile(
				mapping, FILE_MAP_READ, 0, 0, sizeof(OutRunVR::SharedPoseState)));
			if (!shared) { CloseHandle(mapping); return false; }

			OutRunVR::SharedPoseState snap{};
			bool stable = false;
			for (int attempt = 0; attempt < 4; ++attempt)
			{
				const std::uint32_t before = shared->sequence;
				if (before & 1u) continue;
				MemoryBarrier();
				std::memcpy(&snap, shared, sizeof(snap));
				MemoryBarrier();
				const std::uint32_t after = shared->sequence;
				if (before == after && !(after & 1u)) { out.sequence = after; stable = true; break; }
			}
			UnmapViewOfFile(shared);
			CloseHandle(mapping);
			if (!stable || snap.magic != OutRunVR::SharedMagic ||
				snap.protocolVersion != OutRunVR::SharedProtocolVersion ||
				snap.structSize != sizeof(OutRunVR::SharedPoseState) || snap.hostPid == 0)
				return false;
			if ((snap.flags & (OutRunVR::HostAlive | OutRunVR::OrientationValid | OutRunVR::StereoViewsValid)) !=
				(OutRunVR::HostAlive | OutRunVR::OrientationValid | OutRunVR::StereoViewsValid))
				return false;

			LARGE_INTEGER now{}, freq{};
			QueryPerformanceCounter(&now);
			QueryPerformanceFrequency(&freq);
			if (freq.QuadPart <= 0 || snap.sampleQpc <= 0 || now.QuadPart < snap.sampleQpc ||
				now.QuadPart - snap.sampleQpc > (freq.QuadPart * HostPoseStaleMs) / 1000)
				return false;

			out.fov[0] = snap.eyeFov[0];
			out.fov[1] = snap.eyeFov[1];
			const std::uint32_t li[3] = { OutRunVR::HostEyeOffsetLeftXIndex, OutRunVR::HostEyeOffsetLeftYIndex, OutRunVR::HostEyeOffsetLeftZIndex };
			const std::uint32_t ri[3] = { OutRunVR::HostEyeOffsetRightXIndex, OutRunVR::HostEyeOffsetRightYIndex, OutRunVR::HostEyeOffsetRightZIndex };
			for (int c = 0; c < 3; ++c)
			{
				out.eyeOffset[0][c] = BitsToFloat(snap.reserved[li[c]]);
				out.eyeOffset[1][c] = BitsToFloat(snap.reserved[ri[c]]);
				if (!Finite(out.eyeOffset[0][c]) || !Finite(out.eyeOffset[1][c])) return false;
			}
			out.valid = true;
			return true;
		}

		OutRunVR::ClientPresentationMode CurrentPresentationMode()
		{
			if (!Game::current_mode) return OutRunVR::PresentationUnknown;
			if (*Game::current_mode == GameState::STATE_GAME) return OutRunVR::PresentationGameplay;
			if (*Game::current_mode == GameState::STATE_START && Game::game_start_progress_code &&
				*Game::game_start_progress_code == 65) return OutRunVR::PresentationGameplay;
			return OutRunVR::PresentationTheater;
		}

		void UpdateBackbufferIdentity(IDirect3DDevice9* device)
		{
			BackbufferIdentity = nullptr;
			BackbufferWidth = BackbufferHeight = 0;
			IDirect3DSurface9* bb = nullptr;
			if (FAILED(device->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &bb)) || !bb) return;
			BackbufferIdentity = bb;
			D3DSURFACE_DESC desc{};
			if (SUCCEEDED(bb->GetDesc(&desc))) { BackbufferWidth = desc.Width; BackbufferHeight = desc.Height; }
			bb->Release(); // weak identity only; never block Reset with our reference
			IDirect3DSurface9* rt = nullptr;
			if (SUCCEEDED(device->GetRenderTarget(0, &rt)) && rt)
			{
				Rt0IsBackbuffer = rt == BackbufferIdentity;
				rt->Release();
			}
			else Rt0IsBackbuffer = true;
		}

		bool MapViewport(const D3DVIEWPORT9& original, int eye, D3DVIEWPORT9& mapped)
		{
			if (!BackbufferWidth || !BackbufferHeight) return false;
			const std::uint32_t half = BackbufferWidth / 2;
			if (!half) return false;
			mapped = original;
			const double scale = static_cast<double>(half) / static_cast<double>(BackbufferWidth);
			mapped.X = eye * half + static_cast<DWORD>(std::floor(original.X * scale));
			mapped.Width = std::max<DWORD>(1, static_cast<DWORD>(std::ceil(original.Width * scale)));
			if (mapped.X + mapped.Width > static_cast<DWORD>((eye + 1) * half))
				mapped.Width = static_cast<DWORD>((eye + 1) * half) - mapped.X;
			return mapped.Width > 0;
		}

		RECT MapScissor(const RECT& original, int eye)
		{
			const LONG half = static_cast<LONG>(BackbufferWidth / 2);
			const double scale = static_cast<double>(half) / static_cast<double>(BackbufferWidth);
			RECT out = original;
			out.left = eye * half + static_cast<LONG>(std::floor(original.left * scale));
			out.right = eye * half + static_cast<LONG>(std::ceil(original.right * scale));
			out.left = std::clamp<LONG>(out.left, eye * half, (eye + 1) * half);
			out.right = std::clamp<LONG>(out.right, out.left, (eye + 1) * half);
			return out;
		}

		bool PrepareEyeMatrices(IDirect3DDevice9* device, const StereoSnapshot& stereo, Matrix4 eyeWvp[2], float savedC64[16])
		{
			if (FAILED(device->GetVertexShaderConstantF(WvpRegister, savedC64, WvpRegisterCount))) return false;
			Matrix4 currentWvpT{};
			std::memcpy(&currentWvpT, savedC64, sizeof(currentWvpT));
			const Matrix4 currentWvp = Transpose(currentWvpT);

			const auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(ProjectionRva);
			if (!projectionPtr) return false;
			Matrix4 projection{};
			std::memcpy(&projection, projectionPtr, sizeof(projection));
			if (!MatrixFinite(currentWvp) || !MatrixFinite(projection)) return false;
			Matrix4 invProjection{};
			if (!Invert(projection, invProjection)) return false;
			const Matrix4 headWorldView = Multiply(currentWvp, invProjection);
			if (!AffineLike(headWorldView)) return false; // conservative 3D/world-draw discriminator

			for (int eye = 0; eye < 2; ++eye)
			{
				Matrix4 eyeProjection{};
				if (!BuildEyeProjection(projection, stereo.fov[eye], eyeProjection)) return false;
				const float scale = Settings::VRWorldScale;
				const Matrix4 eyeInverse = Translation(
					-stereo.eyeOffset[eye][0] * scale,
					-stereo.eyeOffset[eye][1] * scale,
					-stereo.eyeOffset[eye][2] * scale);
				eyeWvp[eye] = Multiply(Multiply(headWorldView, eyeInverse), eyeProjection);
				if (!MatrixFinite(eyeWvp[eye])) return false;
			}
			return true;
		}

		void PublishStereoState(std::uint32_t state, bool duplicated, bool worldDraw)
		{
			HANDLE mapping = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, OutRunVR::SharedMemoryName);
			if (!mapping) return;
			auto* shared = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedPoseState)));
			if (shared && shared->magic == OutRunVR::SharedMagic && shared->protocolVersion == OutRunVR::SharedProtocolVersion)
			{
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared->reserved[OutRunVR::ClientStereoStateIndex]), static_cast<LONG>(state));
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared->reserved[OutRunVR::ClientStereoFrameIndex]), static_cast<LONG>(StereoFrame));
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared->reserved[OutRunVR::ClientStereoBackbufferWidthIndex]), static_cast<LONG>(BackbufferWidth));
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]), static_cast<LONG>(BackbufferHeight));
				if (duplicated || worldDraw)
				{
					LONG bits = shared->reserved[OutRunVR::ClientFlagsIndex];
					bits |= static_cast<LONG>(OutRunVR::ClientStereoActive);
					if (duplicated) bits |= static_cast<LONG>(OutRunVR::ClientStereoDrawDuplicated);
					if (worldDraw) bits |= static_cast<LONG>(OutRunVR::ClientStereoWorldDraw);
					InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared->reserved[OutRunVR::ClientFlagsIndex]), bits);
				}
			}
			if (shared) UnmapViewOfFile(shared);
			CloseHandle(mapping);
		}

		template <typename Call>
		HRESULT StereoDraw(IDirect3DDevice9* device, Call&& originalCall)
		{
			if (!IsGameDevice(device) || !Settings::VRStereo || !Rt0IsBackbuffer ||
				CurrentPresentationMode() != OutRunVR::PresentationGameplay || BackbufferWidth < 2)
				return originalCall();

			StereoSnapshot stereo{};
			if (!ReadStereoSnapshot(stereo))
			{
				++StereoFallbackDraws;
				PublishStereoState(OutRunVR::StereoSbsFallbackMono, false, false);
				return originalCall();
			}

			D3DVIEWPORT9 originalViewport{};
			if (FAILED(device->GetViewport(&originalViewport))) return originalCall();
			DWORD scissorEnabled = FALSE;
			device->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissorEnabled);
			RECT originalScissor{};
			if (scissorEnabled && FAILED(device->GetScissorRect(&originalScissor))) scissorEnabled = FALSE;

			Matrix4 eyeWvp[2]{};
			float savedC64[16]{};
			const bool worldDraw = PrepareEyeMatrices(device, stereo, eyeWvp, savedC64);
			if (worldDraw) ++StereoWorldDraws;

			HRESULT firstFailure = D3D_OK;
			bool duplicated = false;
			for (int eye = 0; eye < 2; ++eye)
			{
				D3DVIEWPORT9 vp{};
				if (!MapViewport(originalViewport, eye, vp)) continue;
				if (FAILED(device->SetViewport(&vp))) continue;
				if (scissorEnabled)
				{
					RECT sr = MapScissor(originalScissor, eye);
					device->SetScissorRect(&sr);
				}
				if (worldDraw)
				{
					const Matrix4 transposed = Transpose(eyeWvp[eye]);
					device->SetVertexShaderConstantF(WvpRegister, &transposed.m[0][0], WvpRegisterCount);
				}
				const HRESULT hr = originalCall();
				duplicated = true;
				if (FAILED(hr) && SUCCEEDED(firstFailure)) firstFailure = hr;
			}

			if (worldDraw) device->SetVertexShaderConstantF(WvpRegister, savedC64, WvpRegisterCount);
			device->SetViewport(&originalViewport);
			if (scissorEnabled) device->SetScissorRect(&originalScissor);

			if (duplicated)
			{
				++StereoDraws;
				PublishStereoState(OutRunVR::StereoSbsActive, true, worldDraw);
				if (!FirstStereoLog)
				{
					FirstStereoLog = true;
					spdlog::info("VR stereo: true SBS draw duplication active; simulation/input/FFB remain single-pass");
				}
				return firstFailure;
			}
			return originalCall();
		}

		HRESULT __stdcall DrawPrimitiveDest(IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT c)
		{
			return StereoDraw(d, [&]() { return DrawPrimitiveHook.stdcall<HRESULT>(d, t, s, c); });
		}
		HRESULT __stdcall DrawIndexedPrimitiveDest(IDirect3DDevice9* d, D3DPRIMITIVETYPE t, INT b, UINT minv, UINT nv, UINT si, UINT pc)
		{
			return StereoDraw(d, [&]() { return DrawIndexedPrimitiveHook.stdcall<HRESULT>(d, t, b, minv, nv, si, pc); });
		}
		HRESULT __stdcall DrawPrimitiveUPDest(IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT pc, const void* data, UINT stride)
		{
			return StereoDraw(d, [&]() { return DrawPrimitiveUPHook.stdcall<HRESULT>(d, t, pc, data, stride); });
		}
		HRESULT __stdcall DrawIndexedPrimitiveUPDest(IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT minv, UINT nv, UINT pc, const void* idx, D3DFORMAT fmt, const void* vtx, UINT stride)
		{
			return StereoDraw(d, [&]() { return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(d, t, minv, nv, pc, idx, fmt, vtx, stride); });
		}

		HRESULT __stdcall SetRenderTargetDest(IDirect3DDevice9* d, DWORD index, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetRenderTargetHook.stdcall<HRESULT>(d, index, surface);
			if (IsGameDevice(d) && index == 0 && SUCCEEDED(hr)) Rt0IsBackbuffer = surface == BackbufferIdentity;
			return hr;
		}

		HRESULT __stdcall ResetDest(IDirect3DDevice9* d, D3DPRESENT_PARAMETERS* pp)
		{
			BackbufferIdentity = nullptr;
			BackbufferWidth = BackbufferHeight = 0;
			Rt0IsBackbuffer = true;
			const HRESULT hr = ResetHook.stdcall<HRESULT>(d, pp);
			if (IsGameDevice(d) && SUCCEEDED(hr)) UpdateBackbufferIdentity(d);
			return hr;
		}

		HRESULT __stdcall PresentDest(IDirect3DDevice9* d, const RECT* src, const RECT* dst, HWND hwnd, const RGNDATA* dirty)
		{
			if (IsGameDevice(d))
			{
				++StereoFrame;
				if (!BackbufferIdentity || !BackbufferWidth) UpdateBackbufferIdentity(d);
				const bool active = Settings::VRStereo && CurrentPresentationMode() == OutRunVR::PresentationGameplay;
				PublishStereoState(active ? OutRunVR::StereoSbsActive : OutRunVR::StereoDisabled, false, false);
				if (Settings::VRTelemetry && GetTickCount64() - LastSummaryMs >= 5000)
				{
					LastSummaryMs = GetTickCount64();
					spdlog::info("VR stereo: frame={} draws={} world={} fallback={} backbuffer={}x{}",
						StereoFrame, StereoDraws, StereoWorldDraws, StereoFallbackDraws, BackbufferWidth, BackbufferHeight);
				}
			}
			return PresentHook.stdcall<HRESULT>(d, src, dst, hwnd, dirty);
		}

		bool Install(IDirect3DDevice9* device)
		{
			void** vtable = *reinterpret_cast<void***>(device);
			if (!vtable) return false;
			UpdateBackbufferIdentity(device);
			ResetHook = safetyhook::create_inline(vtable[ResetVtableIndex], ResetDest);
			PresentHook = safetyhook::create_inline(vtable[PresentVtableIndex], PresentDest);
			SetRenderTargetHook = safetyhook::create_inline(vtable[SetRenderTargetVtableIndex], SetRenderTargetDest);
			DrawPrimitiveHook = safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex], DrawPrimitiveDest);
			DrawIndexedPrimitiveHook = safetyhook::create_inline(vtable[DrawIndexedPrimitiveVtableIndex], DrawIndexedPrimitiveDest);
			DrawPrimitiveUPHook = safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex], DrawPrimitiveUPDest);
			DrawIndexedPrimitiveUPHook = safetyhook::create_inline(vtable[DrawIndexedPrimitiveUPVtableIndex], DrawIndexedPrimitiveUPDest);
			if (!ResetHook || !PresentHook || !SetRenderTargetHook || !DrawPrimitiveHook ||
				!DrawIndexedPrimitiveHook || !DrawPrimitiveUPHook || !DrawIndexedPrimitiveUPHook)
			{
				ResetHook = {}; PresentHook = {}; SetRenderTargetHook = {};
				DrawPrimitiveHook = {}; DrawIndexedPrimitiveHook = {}; DrawPrimitiveUPHook = {}; DrawIndexedPrimitiveUPHook = {};
				return false;
			}
			spdlog::info("VR stereo: D3D9 SBS hooks installed (Reset/Present/RT/Draw*); true stereo armed");
			return true;
		}

		DWORD WINAPI InstallThread(void*)
		{
			for (int i = 0; i < 1200; ++i)
			{
				if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
				{
					if (!Install(*Game::D3DDevice_ptr)) spdlog::error("VR stereo: D3D9 hook installation failed");
					return 0;
				}
				Sleep(100);
			}
			spdlog::warn("VR stereo: D3D9 device did not appear; stereo disabled");
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
			HANDLE thread = CreateThread(nullptr, 0, InstallThread, nullptr, 0, nullptr);
			if (!thread) return false;
			CloseHandle(thread);
			return true;
		}
		static VRStereoHook instance;
	};
	VRStereoHook VRStereoHook::instance;
}
