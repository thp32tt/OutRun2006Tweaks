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

// Final-render head-pose injector for OutRun 2006.
//
// The first OpenXR camera implementation applied the HMD transform to
// EvWorkCamera::d3dmatrix140 after CalcCameraMatrix. Runtime telemetry proved
// that this object changed, but the headset image did not. The missing piece
// was the renderer sink.
//
// Kim2091/Remix-Wrappers contains an independently reverse-engineered OR2006
// D3D9 path. It establishes that the game does not upload a standalone View
// matrix to the vertex shader. Immediately before DrawIndexedPrimitive it
// builds:
//
//   0x0095DB20  WorldView = World * View
//   0x0095D8A0  Projection
//   VS c64..c67 = Transpose(WorldView * Projection)
//
// with the live camera View at 0x0095D860. That same analysis identifies the
// render camera/projection as D3DXMatrixLookAtRH / D3DXMatrixPerspectiveFovRH.
// OpenXR is also right-handed with -Z forward, so this final-render path keeps
// the OpenXR quaternion in its RH basis instead of applying the older LH
// reflection used by the initial camera-object experiment.
//
// We verify the c64 relation at runtime and, only when it matches, replace it
// with:
//
//   Transpose(WorldView * HeadInverse * Projection)
//
// for the default row-vector composition order. The alternate order is also
// supported by recovering World from WorldView and View. If the expected
// relationship does not match the running binary, the upload is left untouched
// (fail closed). Wheel, multi-device and FFB paths are not involved.

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRAutoEnableWhenHostPresent;
	extern Setting<bool> VRHeadTracking;
	extern Setting<bool> VRPositionalTracking;
	extern Setting<float> VRWorldScale;
	extern Setting<float> VRRotationScale;
	extern Setting<int> VRMatrixOrder;
	extern Setting<bool> VRTelemetry;
}

namespace OutRunVRRenderer
{
	namespace
	{
		struct Vec3 { float x, y, z; };
		struct Quat { float x, y, z, w; };
		struct PoseSample
		{
			Quat orientation{ 0.0f, 0.0f, 0.0f, 1.0f };
			Vec3 position{ 0.0f, 0.0f, 0.0f };
			bool positionValid = false;
			std::uint32_t hostPid = 0;
			std::uint32_t sequence = 0;
		};

		constexpr std::size_t CameraMatrixCount = 7;
		constexpr std::size_t SetTransformVtableIndex = 44;
		constexpr std::size_t SetVertexShaderConstantFVtableIndex = 94;
		constexpr UINT OutRunWvpRegister = 64;
		constexpr UINT OutRunWvpRegisterCount = 4;

		// The external reverse-engineering uses absolute addresses for the stock
		// 0x00400000 image base. Store RVAs so ASLR/rebasing remains safe here.
		constexpr std::uintptr_t OutRunViewRva = 0x0095D860u - 0x00400000u;
		constexpr std::uintptr_t OutRunProjectionRva = 0x0095D8A0u - 0x00400000u;
		constexpr std::uintptr_t OutRunWorldViewRva = 0x0095DB20u - 0x00400000u;

		constexpr float Pi = 3.14159265358979323846f;
		constexpr float CameraProbeEpsilon = 1.0e-4f;
		constexpr float WvpVerifyAbsoluteEpsilon = 0.05f;
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

		HANDLE SharedMapping = nullptr;
		const SharedPoseState* SharedState = nullptr;
		LARGE_INTEGER QpcFrequency{};
		ULONGLONG LastMappingAttemptMs = 0;
		ULONGLONG ProbeStartMs = 0;
		ULONGLONG LastSummaryMs = 0;

		Quat CenterOrientation{ 0.0f, 0.0f, 0.0f, 1.0f };
		Vec3 CenterPosition{ 0.0f, 0.0f, 0.0f };
		bool CenterValid = false;
		std::uint32_t CenterHostPid = 0;
		std::uint32_t LastPoseSequence = 0;
		D3DMATRIX CachedHeadInverse{};
		bool CachedHeadInverseValid = false;
		bool RecenterWasDown = false;

		std::atomic<std::uint32_t> SeenMask{ 0 };
		std::atomic<std::uint64_t> ViewTransformCalls{ 0 };
		std::atomic<std::uint64_t> VertexConstantCalls{ 0 };
		std::atomic<std::uint64_t> WvpCandidateCalls{ 0 };
		std::atomic<std::uint64_t> WvpVerifiedCalls{ 0 };
		std::atomic<std::uint64_t> WvpInjectedCalls{ 0 };
		std::atomic<std::uint64_t> WvpRejectedCalls{ 0 };
		std::atomic<bool> ProbeExpiredLogged{ false };
		std::atomic<bool> FirstVerifiedLogged{ false };
		std::atomic<bool> FirstInjectedLogged{ false };
		std::atomic<bool> FirstRejectedLogged{ false };

		enum class ProbeApi : std::uint32_t
		{
			SetTransform = 0,
			VertexConstants = 1,
		};

		Quat Normalize(Quat q)
		{
			const float lengthSq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
			if (lengthSq <= 1.0e-12f)
				return { 0.0f, 0.0f, 0.0f, 1.0f };
			const float invLength = 1.0f / std::sqrt(lengthSq);
			return { q.x * invLength, q.y * invLength, q.z * invLength, q.w * invLength };
		}

		Quat Conjugate(const Quat& q) { return { -q.x, -q.y, -q.z, q.w }; }

		Quat MultiplyRaw(const Quat& a, const Quat& b)
		{
			return {
				a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
				a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
				a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
				a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z
			};
		}

		Quat Multiply(const Quat& a, const Quat& b)
		{
			return Normalize(MultiplyRaw(a, b));
		}

		Quat AxisAngle(float x, float y, float z, float radians)
		{
			const float half = radians * 0.5f;
			const float s = std::sin(half);
			return Normalize({ x * s, y * s, z * s, std::cos(half) });
		}

		Quat ScaleRotation(Quat q, float scale)
		{
			q = Normalize(q);
			if (q.w < 0.0f)
				q = { -q.x, -q.y, -q.z, -q.w };

			const float w = std::clamp(q.w, -1.0f, 1.0f);
			const float angle = 2.0f * std::acos(w);
			const float sinHalf = std::sqrt(std::max(0.0f, 1.0f - w * w));
			if (sinHalf < 1.0e-6f || angle < 1.0e-6f)
				return { 0.0f, 0.0f, 0.0f, 1.0f };
			return AxisAngle(q.x / sinHalf, q.y / sinHalf, q.z / sinHalf, angle * scale);
		}

		Vec3 RotateVector(const Quat& qIn, const Vec3& v)
		{
			const Quat q = Normalize(qIn);
			const Quat p{ v.x, v.y, v.z, 0.0f };
			const Quat r = MultiplyRaw(MultiplyRaw(q, p), Conjugate(q));
			return { r.x, r.y, r.z };
		}

		D3DMATRIX IdentityMatrix()
		{
			D3DMATRIX out{};
			out._11 = out._22 = out._33 = out._44 = 1.0f;
			return out;
		}

		D3DMATRIX MatrixFromPose(const Quat& qIn, const Vec3& position)
		{
			const Quat q = Normalize(qIn);
			const float xx = q.x * q.x, yy = q.y * q.y, zz = q.z * q.z;
			const float xy = q.x * q.y, xz = q.x * q.z, yz = q.y * q.z;
			const float xw = q.x * q.w, yw = q.y * q.w, zw = q.z * q.w;

			D3DMATRIX out = IdentityMatrix();
			out._11 = 1.0f - 2.0f * (yy + zz);
			out._12 = 2.0f * (xy + zw);
			out._13 = 2.0f * (xz - yw);
			out._21 = 2.0f * (xy - zw);
			out._22 = 1.0f - 2.0f * (xx + zz);
			out._23 = 2.0f * (yz + xw);
			out._31 = 2.0f * (xz + yw);
			out._32 = 2.0f * (yz - xw);
			out._33 = 1.0f - 2.0f * (xx + yy);
			out._41 = position.x;
			out._42 = position.y;
			out._43 = position.z;
			return out;
		}

		D3DMATRIX MultiplyMatrix(const D3DMATRIX& a, const D3DMATRIX& b)
		{
			D3DMATRIX out{};
			for (int row = 0; row < 4; ++row)
				for (int col = 0; col < 4; ++col)
					for (int k = 0; k < 4; ++k)
						out.m[row][col] += a.m[row][k] * b.m[k][col];
			return out;
		}

		D3DMATRIX TransposeMatrix(const D3DMATRIX& m)
		{
			D3DMATRIX out{};
			for (int row = 0; row < 4; ++row)
				for (int col = 0; col < 4; ++col)
					out.m[row][col] = m.m[col][row];
			return out;
		}

		D3DMATRIX InverseRigid(const D3DMATRIX& m)
		{
			D3DMATRIX out = IdentityMatrix();
			out._11 = m._11; out._12 = m._21; out._13 = m._31;
			out._21 = m._12; out._22 = m._22; out._23 = m._32;
			out._31 = m._13; out._32 = m._23; out._33 = m._33;
			out._41 = -(m._41 * out._11 + m._42 * out._21 + m._43 * out._31);
			out._42 = -(m._41 * out._12 + m._42 * out._22 + m._43 * out._32);
			out._43 = -(m._41 * out._13 + m._42 * out._23 + m._43 * out._33);
			return out;
		}

		bool MatrixNear(const float* candidate, const D3DMATRIX& matrix, bool transposed, float epsilon)
		{
			for (int row = 0; row < 4; ++row)
			{
				for (int col = 0; col < 4; ++col)
				{
					const float a = candidate[row * 4 + col];
					const float b = transposed ? matrix.m[col][row] : matrix.m[row][col];
					if (!std::isfinite(a) || !std::isfinite(b) || std::fabs(a - b) > epsilon)
						return false;
				}
			}
			return true;
		}

		bool EnsureSharedState()
		{
			if (SharedState)
				return true;

			const ULONGLONG now = GetTickCount64();
			if (now - LastMappingAttemptMs < 1000)
				return false;
			LastMappingAttemptMs = now;

			SharedMapping = OpenFileMappingW(FILE_MAP_READ, FALSE, SharedMemoryName);
			if (!SharedMapping)
				return false;

			SharedState = static_cast<const SharedPoseState*>(MapViewOfFile(
				SharedMapping, FILE_MAP_READ, 0, 0, sizeof(SharedPoseState)));
			if (!SharedState)
			{
				CloseHandle(SharedMapping);
				SharedMapping = nullptr;
				return false;
			}

			QueryPerformanceFrequency(&QpcFrequency);
			return true;
		}

		bool ReadHostPose(PoseSample& pose)
		{
			if (!EnsureSharedState())
				return false;

			SharedPoseState snapshot{};
			bool stable = false;
			for (int attempt = 0; attempt < 4; ++attempt)
			{
				const std::uint32_t seqBefore = SharedState->sequence;
				if (seqBefore & 1u)
					continue;
				MemoryBarrier();
				std::memcpy(&snapshot, SharedState, sizeof(snapshot));
				MemoryBarrier();
				const std::uint32_t seqAfter = SharedState->sequence;
				if (seqBefore == seqAfter && !(seqAfter & 1u))
				{
					stable = true;
					pose.sequence = seqAfter;
					break;
				}
			}

			if (!stable || snapshot.magic != SharedMagic ||
				snapshot.protocolVersion != SharedProtocolVersion ||
				snapshot.structSize != sizeof(SharedPoseState))
				return false;

			if ((snapshot.flags & HostAlive) == 0 ||
				(snapshot.flags & OrientationValid) == 0 || snapshot.hostPid == 0)
				return false;

			LARGE_INTEGER now{};
			QueryPerformanceCounter(&now);
			if (QpcFrequency.QuadPart > 0 && snapshot.sampleQpc > 0 &&
				(now.QuadPart - snapshot.sampleQpc) > (QpcFrequency.QuadPart * 2))
				return false;

			// OpenXR and OR2006's actual render camera are both RH with -Z forward.
			pose.orientation = Normalize({
				snapshot.orientation[0], snapshot.orientation[1],
				snapshot.orientation[2], snapshot.orientation[3]
			});
			pose.position = { snapshot.position[0], snapshot.position[1], snapshot.position[2] };
			pose.positionValid = (snapshot.flags & PositionValid) != 0;
			pose.hostPid = snapshot.hostPid;
			return true;
		}

		bool RendererRecenterPressed()
		{
			const bool isDown = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
			const bool pressed = isDown && !RecenterWasDown;
			RecenterWasDown = isDown;
			return pressed;
		}

		bool GetHeadInverse(D3DMATRIX& headInverse)
		{
			PoseSample sample{};
			const bool haveHostPose = ReadHostPose(sample);
			if (!haveHostPose)
			{
				CenterValid = false;
				CenterHostPid = 0;
				CachedHeadInverseValid = false;
				return false;
			}

			const bool autoEnabled = Settings::VRAutoEnableWhenHostPresent;
			const bool trackingEnabled = Settings::VRHeadTracking || autoEnabled;
			if (!(Settings::VREnabled || autoEnabled) || !trackingEnabled)
				return false;

			const bool recenter = RendererRecenterPressed();
			if (CachedHeadInverseValid && !recenter && sample.sequence == LastPoseSequence &&
				CenterHostPid == sample.hostPid)
			{
				headInverse = CachedHeadInverse;
				return true;
			}

			if (!CenterValid || CenterHostPid != sample.hostPid || recenter)
			{
				CenterOrientation = sample.orientation;
				CenterPosition = sample.position;
				CenterHostPid = sample.hostPid;
				CenterValid = true;
			}

			const Quat invCenter = Conjugate(Normalize(CenterOrientation));
			Quat relativeOrientation = Multiply(invCenter, sample.orientation);
			Vec3 relativePosition{ 0.0f, 0.0f, 0.0f };
			if (Settings::VRPositionalTracking && sample.positionValid)
			{
				const Vec3 delta{
					sample.position.x - CenterPosition.x,
					sample.position.y - CenterPosition.y,
					sample.position.z - CenterPosition.z
				};
				relativePosition = RotateVector(invCenter, delta);
				relativePosition.x *= Settings::VRWorldScale;
				relativePosition.y *= Settings::VRWorldScale;
				relativePosition.z *= Settings::VRWorldScale;
			}

			relativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);
			CachedHeadInverse = InverseRigid(MatrixFromPose(relativeOrientation, relativePosition));
			CachedHeadInverseValid = true;
			LastPoseSequence = sample.sequence;
			headInverse = CachedHeadInverse;
			return true;
		}

		bool GameRendererIsActive()
		{
			return Game::current_mode && Game::game_start_progress_code && Game::is_in_game();
		}

		bool ProbeWindowIsActive()
		{
			if (!GameRendererIsActive())
				return false;

			PoseSample pose{};
			if (!ReadHostPose(pose))
			{
				ProbeStartMs = 0;
				ProbeExpiredLogged.store(false, std::memory_order_relaxed);
				return false;
			}

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
				spdlog::info("VR renderer probe: {} matched {} at c{} ({}){}",
					apiName, CameraMatrixNames[matrixIndex], shaderRegister, layoutName, trackedMarker);
			else
				spdlog::info("VR renderer probe: {} matched {} ({}){}",
					apiName, CameraMatrixNames[matrixIndex], layoutName, trackedMarker);
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
				if (MatrixNear(candidate, *matrices[i], false, CameraProbeEpsilon))
					ReportMatch(api, i, false, shaderRegister);
				if (MatrixNear(candidate, *matrices[i], true, CameraProbeEpsilon))
					ReportMatch(api, i, true, shaderRegister);
			}
		}

		bool TryInjectOutRunWvp(
			UINT startRegister, const float* constantData, UINT vector4fCount,
			float* patchedData)
		{
			if (!constantData || !patchedData || vector4fCount == 0 || vector4fCount > 256)
				return false;
			if (startRegister > OutRunWvpRegister ||
				startRegister + vector4fCount < OutRunWvpRegister + OutRunWvpRegisterCount)
				return false;
			if (!GameRendererIsActive())
				return false;

			WvpCandidateCalls.fetch_add(1, std::memory_order_relaxed);

			const D3DMATRIX* view = Module::exe_ptr<D3DMATRIX>(OutRunViewRva);
			const D3DMATRIX* projection = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
			const D3DMATRIX* worldView = Module::exe_ptr<D3DMATRIX>(OutRunWorldViewRva);
			if (!view || !projection || !worldView)
				return false;

			const UINT wvpOffsetRegisters = OutRunWvpRegister - startRegister;
			const float* uploadedWvp = constantData + wvpOffsetRegisters * 4;

			// Fail closed unless the external OR2006 renderer mapping is true for
			// this exact draw on this exact executable.
			const D3DMATRIX expectedWvp = MultiplyMatrix(*worldView, *projection);
			if (!MatrixNear(uploadedWvp, expectedWvp, true, WvpVerifyAbsoluteEpsilon))
			{
				WvpRejectedCalls.fetch_add(1, std::memory_order_relaxed);
				if (!FirstRejectedLogged.exchange(true, std::memory_order_relaxed))
					spdlog::info("VR renderer inject: first c64 upload did not match Transpose(WorldView*Proj); leaving unmatched draws untouched");
				return false;
			}

			WvpVerifiedCalls.fetch_add(1, std::memory_order_relaxed);
			if (!FirstVerifiedLogged.exchange(true, std::memory_order_relaxed))
				spdlog::info("VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)");

			D3DMATRIX headInverse{};
			if (!GetHeadInverse(headInverse))
				return false;

			D3DMATRIX correctedWvp{};
			if (Settings::VRMatrixOrder == 0)
			{
				correctedWvp = MultiplyMatrix(MultiplyMatrix(*worldView, headInverse), *projection);
			}
			else
			{
				// WorldView = World * View -> World = WorldView * inverse(View).
				const D3DMATRIX world = MultiplyMatrix(*worldView, InverseRigid(*view));
				correctedWvp = MultiplyMatrix(
					MultiplyMatrix(MultiplyMatrix(world, headInverse), *view), *projection);
			}

			std::memcpy(patchedData, constantData, sizeof(float) * vector4fCount * 4);
			const D3DMATRIX transposed = TransposeMatrix(correctedWvp);
			std::memcpy(patchedData + wvpOffsetRegisters * 4, &transposed, sizeof(transposed));

			WvpInjectedCalls.fetch_add(1, std::memory_order_relaxed);
			if (!FirstInjectedLogged.exchange(true, std::memory_order_relaxed))
				spdlog::info("VR renderer inject: HEAD TRACKING ACTIVE at VS c64 render boundary");
			return true;
		}

		void MaybeLogSummary()
		{
			if (!Settings::VRTelemetry)
				return;

			const ULONGLONG now = GetTickCount64();
			if (now - LastSummaryMs < 1000)
				return;
			LastSummaryMs = now;

			spdlog::info(
				"VR renderer: viewSet={} vsConst={} c64Candidate={} verified={} injected={} rejected={} matchMask=0x{:08X}",
				ViewTransformCalls.load(std::memory_order_relaxed),
				VertexConstantCalls.load(std::memory_order_relaxed),
				WvpCandidateCalls.load(std::memory_order_relaxed),
				WvpVerifiedCalls.load(std::memory_order_relaxed),
				WvpInjectedCalls.load(std::memory_order_relaxed),
				WvpRejectedCalls.load(std::memory_order_relaxed),
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
			const bool probe = constantData && vector4fCount >= 4 && ProbeWindowIsActive();
			if (probe)
			{
				VertexConstantCalls.fetch_add(1, std::memory_order_relaxed);
				const UINT cappedCount = std::min<UINT>(vector4fCount, 256);
				for (UINT offset = 0; offset + 4 <= cappedCount; ++offset)
					ProbeMatrix(constantData + offset * 4, ProbeApi::VertexConstants, startRegister + offset);
			}

			float patchedData[256 * 4];
			const bool injected = TryInjectOutRunWvp(
				startRegister, constantData, vector4fCount, patchedData);
			MaybeLogSummary();

			return SetVertexShaderConstantFHook.stdcall<HRESULT>(
				device, startRegister, injected ? patchedData : constantData, vector4fCount);
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
				spdlog::error("VR renderer: failed to hook D3D9 renderer boundary");
				return false;
			}

			spdlog::info(
				"VR renderer: D3D9 hooks installed; OR2006 c64 WVP verification/injection armed (vtbl 44/94)");
			return true;
		}

		DWORD WINAPI RendererInstallThread(void*)
		{
			for (int attempt = 0; attempt < 1200; ++attempt)
			{
				if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
				{
					InstallD3D9Hooks(*Game::D3DDevice_ptr);
					return 0;
				}
				Sleep(100);
			}

			spdlog::warn("VR renderer: D3D9 device did not appear; renderer hook not installed");
			return 0;
		}
	}

	class VRRendererHook : public Hook
	{
	public:
		std::string_view description() override { return "OpenXRVRRenderer"; }
		bool validate() override { return true; }

		bool apply() override
		{
			HANDLE thread = CreateThread(nullptr, 0, RendererInstallThread, nullptr, 0, nullptr);
			if (!thread)
			{
				spdlog::error("VR renderer: failed to create installer thread: {}", GetLastError());
				return false;
			}
			CloseHandle(thread);
			return true;
		}

		static VRRendererHook instance;
	};

	VRRendererHook VRRendererHook::instance;
}
