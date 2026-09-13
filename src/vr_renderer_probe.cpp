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

// Authoritative renderer-side OpenXR head-pose injector for OutRun 2006.
//
// Kim2091/Remix-Wrappers independently reverse-engineered the relevant PC
// renderer path:
//   0x0095DB20  WorldView = World * View
//   0x0095D8A0  Projection
//   VS c64..c67 = Transpose(WorldView * Projection)
// with the live View at 0x0095D860. The game camera is right-handed and uses
// D3DXMatrixLookAtRH / D3DXMatrixPerspectiveFovRH, matching OpenXR's RH basis.
//
// We therefore leave gameplay camera state untouched and patch only a c64 upload
// that first proves the expected WVP relationship for the running executable.
// The OpenXR pose is latched once at BeginScene so every draw in one D3D9 scene
// uses exactly the same HMD transform. Unknown executable layouts fail closed.

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

		constexpr std::size_t BeginSceneVtableIndex = 41;
		constexpr std::size_t SetVertexShaderConstantFVtableIndex = 94;
		constexpr UINT OutRunWvpRegister = 64;
		constexpr UINT OutRunWvpRegisterCount = 4;

		// Stock 0x00400000 image-base addresses expressed as RVAs for ASLR safety.
		constexpr std::uintptr_t OutRunViewRva = 0x0095D860u - 0x00400000u;
		constexpr std::uintptr_t OutRunProjectionRva = 0x0095D8A0u - 0x00400000u;
		constexpr std::uintptr_t OutRunWorldViewRva = 0x0095DB20u - 0x00400000u;

		constexpr float Pi = 3.14159265358979323846f;
		constexpr float WvpVerifyAbsoluteEpsilon = 0.05f;
		constexpr LONGLONG HostPoseStaleMs = 250;

		SafetyHookInline BeginSceneHook{};
		SafetyHookInline SetVertexShaderConstantFHook{};

		HANDLE SharedMapping = nullptr;
		SharedPoseState* SharedState = nullptr;
		LARGE_INTEGER QpcFrequency{};

		Quat CenterOrientation{ 0.0f, 0.0f, 0.0f, 1.0f };
		Vec3 CenterPosition{ 0.0f, 0.0f, 0.0f };
		bool CenterValid = false;
		std::uint32_t CenterHostPid = 0;
		bool RecenterWasDown = false;
		bool AutoEnableLogged = false;

		D3DMATRIX LatchedHeadInverse{};
		bool LatchedHeadInverseValid = false;
		std::uint32_t LatchedTelemetryFlags = ClientHookAlive;
		float LatchedRelativeAngleDeg = 0.0f;
		std::uint32_t LatchedPoseSequence = 0;

		ULONGLONG LastSummaryMs = 0;
		std::atomic<std::uint64_t> BeginSceneCalls{ 0 };
		std::atomic<std::uint64_t> VertexConstantCalls{ 0 };
		std::atomic<std::uint64_t> WvpCandidateCalls{ 0 };
		std::atomic<std::uint64_t> WvpVerifiedCalls{ 0 };
		std::atomic<std::uint64_t> WvpInjectedCalls{ 0 };
		std::atomic<std::uint64_t> WvpRejectedCalls{ 0 };
		std::atomic<std::uint64_t> UnsafeAddressRejects{ 0 };
		std::atomic<bool> FirstVerifiedLogged{ false };
		std::atomic<bool> FirstInjectedLogged{ false };
		std::atomic<bool> FirstRejectedLogged{ false };
		std::atomic<bool> FirstUnsafeAddressLogged{ false };

		Quat Normalize(Quat q)
		{
			const float lengthSq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
			if (!std::isfinite(lengthSq) || lengthSq <= 1.0e-12f)
				return { 0.0f, 0.0f, 0.0f, 1.0f };
			const float invLength = 1.0f / std::sqrt(lengthSq);
			return { q.x * invLength, q.y * invLength, q.z * invLength, q.w * invLength };
		}

		bool QuaternionIsSane(const Quat& q)
		{
			if (!std::isfinite(q.x) || !std::isfinite(q.y) ||
				!std::isfinite(q.z) || !std::isfinite(q.w))
				return false;
			const float lengthSq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
			return std::isfinite(lengthSq) && lengthSq > 0.25f && lengthSq < 4.0f;
		}

		bool VectorIsFinite(const Vec3& v)
		{
			return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
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

		bool MatrixFinite(const D3DMATRIX& matrix)
		{
			for (int row = 0; row < 4; ++row)
				for (int col = 0; col < 4; ++col)
					if (!std::isfinite(matrix.m[row][col]))
						return false;
			return true;
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

		bool IsReadableRange(const void* address, std::size_t size)
		{
			if (!address || size == 0)
				return false;

			const auto begin = reinterpret_cast<std::uintptr_t>(address);
			if (begin + size < begin)
				return false;

			MEMORY_BASIC_INFORMATION info{};
			if (VirtualQuery(address, &info, sizeof(info)) != sizeof(info))
				return false;
			if (info.State != MEM_COMMIT || (info.Protect & PAGE_GUARD) ||
				(info.Protect & PAGE_NOACCESS))
				return false;

			const auto regionBegin = reinterpret_cast<std::uintptr_t>(info.BaseAddress);
			const auto regionEnd = regionBegin + info.RegionSize;
			return begin >= regionBegin && begin + size <= regionEnd;
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

		bool ReadImageMatrix(std::uintptr_t rva, D3DMATRIX& out)
		{
			if (!ImageContainsRange(rva, sizeof(out)))
				return false;
			const void* source = reinterpret_cast<const void*>(
				reinterpret_cast<std::uintptr_t>(Module::ExeHandle) + rva);
			if (!IsReadableRange(source, sizeof(out)))
				return false;
			std::memcpy(&out, source, sizeof(out));
			return MatrixFinite(out);
		}

		bool EnsureSharedState()
		{
			if (SharedState)
				return true;

			SharedMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
				0, static_cast<DWORD>(sizeof(SharedPoseState)), SharedMemoryName);
			if (!SharedMapping)
				return false;

			SharedState = static_cast<SharedPoseState*>(MapViewOfFile(
				SharedMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SharedPoseState)));
			if (!SharedState)
			{
				CloseHandle(SharedMapping);
				SharedMapping = nullptr;
				return false;
			}

			if (SharedState->magic != SharedMagic ||
				SharedState->protocolVersion != SharedProtocolVersion ||
				SharedState->structSize != sizeof(SharedPoseState))
			{
				std::memset(SharedState, 0, sizeof(SharedPoseState));
				SharedState->magic = SharedMagic;
				SharedState->protocolVersion = SharedProtocolVersion;
				SharedState->structSize = sizeof(SharedPoseState);
			}

			QueryPerformanceFrequency(&QpcFrequency);
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientPid),
				static_cast<LONG>(GetCurrentProcessId()));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientFlagsIndex]),
				static_cast<LONG>(ClientHookAlive));
			spdlog::info("VR renderer: shared pose bridge ready (protocol {}, client pid={})",
				SharedProtocolVersion, GetCurrentProcessId());
			return true;
		}

		void PublishClientTelemetry(std::uint32_t flags, float relativeAngleDeg)
		{
			if (!EnsureSharedState())
				return;

			std::uint32_t angleBits = 0;
			static_assert(sizeof(angleBits) == sizeof(relativeAngleDeg));
			std::memcpy(&angleBits, &relativeAngleDeg, sizeof(angleBits));
			InterlockedIncrement(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientHeartbeatIndex]));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientFlagsIndex]),
				static_cast<LONG>(flags));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientLastAngleBitsIndex]),
				static_cast<LONG>(angleBits));
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
			if (QpcFrequency.QuadPart <= 0 || snapshot.sampleQpc <= 0)
				return false;
			const LONGLONG ageTicks = now.QuadPart - snapshot.sampleQpc;
			const LONGLONG maxAgeTicks = (QpcFrequency.QuadPart * HostPoseStaleMs) / 1000;
			if (ageTicks < 0 || ageTicks > maxAgeTicks)
				return false;

			const Quat rawOrientation{
				snapshot.orientation[0], snapshot.orientation[1],
				snapshot.orientation[2], snapshot.orientation[3]
			};
			if (!QuaternionIsSane(rawOrientation))
				return false;

			pose.orientation = Normalize(rawOrientation);
			pose.position = { snapshot.position[0], snapshot.position[1], snapshot.position[2] };
			pose.positionValid = (snapshot.flags & PositionValid) != 0 && VectorIsFinite(pose.position);
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

		bool GameRendererIsActive()
		{
			return Game::current_mode && Game::game_start_progress_code && Game::is_in_game();
		}

		void ResetLatchedPose()
		{
			LatchedHeadInverseValid = false;
			LatchedTelemetryFlags = ClientHookAlive;
			LatchedRelativeAngleDeg = 0.0f;
			LatchedPoseSequence = 0;
		}

		void LatchFramePose()
		{
			BeginSceneCalls.fetch_add(1, std::memory_order_relaxed);
			ResetLatchedPose();

			if (!GameRendererIsActive())
				return;

			PoseSample sample{};
			if (!ReadHostPose(sample))
			{
				CenterValid = false;
				CenterHostPid = 0;
				PublishClientTelemetry(ClientHookAlive, 0.0f);
				return;
			}

			LatchedTelemetryFlags |= ClientHostPoseValid;
			const bool autoEnabled = Settings::VRAutoEnableWhenHostPresent;
			const bool trackingEnabled = Settings::VRHeadTracking || autoEnabled;
			const bool enabled = (Settings::VREnabled || autoEnabled) && trackingEnabled;
			if (autoEnabled && (!Settings::VREnabled || !Settings::VRHeadTracking))
			{
				LatchedTelemetryFlags |= ClientAutoEnabled;
				if (!AutoEnableLogged)
				{
					spdlog::info("VR renderer: live host pose auto-enabled renderer-side head tracking");
					AutoEnableLogged = true;
				}
			}

			if (!enabled)
			{
				PublishClientTelemetry(LatchedTelemetryFlags, 0.0f);
				return;
			}

			const bool recenter = RendererRecenterPressed();
			if (!CenterValid || CenterHostPid != sample.hostPid || recenter)
			{
				CenterOrientation = sample.orientation;
				CenterPosition = sample.position;
				CenterHostPid = sample.hostPid;
				CenterValid = true;
				if (recenter)
					spdlog::info("VR renderer: recentered HMD pose (F10)");
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
			LatchedHeadInverse = InverseRigid(MatrixFromPose(relativeOrientation, relativePosition));
			LatchedHeadInverseValid = MatrixFinite(LatchedHeadInverse);
			LatchedPoseSequence = sample.sequence;

			const float w = std::clamp(std::fabs(relativeOrientation.w), 0.0f, 1.0f);
			LatchedRelativeAngleDeg = 2.0f * std::acos(w) * (180.0f / Pi);
			if (!LatchedHeadInverseValid)
				PublishClientTelemetry(LatchedTelemetryFlags, 0.0f);
		}

		bool TryInjectOutRunWvp(
			UINT startRegister, const float* constantData, UINT vector4fCount,
			float* patchedData)
		{
			if (!constantData || !patchedData || vector4fCount == 0 || vector4fCount > 256)
				return false;
			if (startRegister > OutRunWvpRegister)
				return false;
			const UINT wvpOffsetRegisters = OutRunWvpRegister - startRegister;
			if (vector4fCount < wvpOffsetRegisters + OutRunWvpRegisterCount)
				return false;
			if (!GameRendererIsActive())
				return false;

			WvpCandidateCalls.fetch_add(1, std::memory_order_relaxed);

			D3DMATRIX view{};
			D3DMATRIX projection{};
			D3DMATRIX worldView{};
			if (!ReadImageMatrix(OutRunViewRva, view) ||
				!ReadImageMatrix(OutRunProjectionRva, projection) ||
				!ReadImageMatrix(OutRunWorldViewRva, worldView))
			{
				UnsafeAddressRejects.fetch_add(1, std::memory_order_relaxed);
				if (!FirstUnsafeAddressLogged.exchange(true, std::memory_order_relaxed))
					spdlog::warn("VR renderer inject: OutRun renderer globals are not safely readable; injection disabled for this draw");
				return false;
			}

			const float* uploadedWvp = constantData + wvpOffsetRegisters * 4;
			const D3DMATRIX expectedWvp = MultiplyMatrix(worldView, projection);
			if (!MatrixNear(uploadedWvp, expectedWvp, true, WvpVerifyAbsoluteEpsilon))
			{
				WvpRejectedCalls.fetch_add(1, std::memory_order_relaxed);
				if (!FirstRejectedLogged.exchange(true, std::memory_order_relaxed))
					spdlog::info("VR renderer inject: first c64 upload did not match Transpose(WorldView*Proj); unmatched draws stay untouched");
				return false;
			}

			WvpVerifiedCalls.fetch_add(1, std::memory_order_relaxed);
			if (!FirstVerifiedLogged.exchange(true, std::memory_order_relaxed))
				spdlog::info("VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)");

			std::uint32_t telemetryFlags = LatchedTelemetryFlags | ClientRendererWvpVerified;
			if (!LatchedHeadInverseValid)
			{
				PublishClientTelemetry(telemetryFlags, 0.0f);
				return false;
			}

			D3DMATRIX correctedWvp{};
			if (Settings::VRMatrixOrder == 0)
			{
				correctedWvp = MultiplyMatrix(MultiplyMatrix(worldView, LatchedHeadInverse), projection);
			}
			else
			{
				// WorldView = World * View -> World = WorldView * inverse(View).
				const D3DMATRIX world = MultiplyMatrix(worldView, InverseRigid(view));
				correctedWvp = MultiplyMatrix(
					MultiplyMatrix(MultiplyMatrix(world, LatchedHeadInverse), view), projection);
			}
			if (!MatrixFinite(correctedWvp))
			{
				PublishClientTelemetry(telemetryFlags, 0.0f);
				return false;
			}

			std::memcpy(patchedData, constantData, sizeof(float) * vector4fCount * 4);
			const D3DMATRIX transposed = TransposeMatrix(correctedWvp);
			std::memcpy(patchedData + wvpOffsetRegisters * 4, &transposed, sizeof(transposed));

			WvpInjectedCalls.fetch_add(1, std::memory_order_relaxed);
			telemetryFlags |= ClientRendererPoseInjected | ClientPoseApplied;
			PublishClientTelemetry(telemetryFlags, LatchedRelativeAngleDeg);
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
				"VR renderer: beginScene={} vsConst={} c64Candidate={} verified={} injected={} rejected={} unsafe={} latchedSeq={}",
				BeginSceneCalls.load(std::memory_order_relaxed),
				VertexConstantCalls.load(std::memory_order_relaxed),
				WvpCandidateCalls.load(std::memory_order_relaxed),
				WvpVerifiedCalls.load(std::memory_order_relaxed),
				WvpInjectedCalls.load(std::memory_order_relaxed),
				WvpRejectedCalls.load(std::memory_order_relaxed),
				UnsafeAddressRejects.load(std::memory_order_relaxed),
				LatchedPoseSequence);
		}

		HRESULT __stdcall BeginSceneDest(IDirect3DDevice9* device)
		{
			LatchFramePose();
			MaybeLogSummary();
			return BeginSceneHook.stdcall<HRESULT>(device);
		}

		HRESULT __stdcall SetVertexShaderConstantFDest(
			IDirect3DDevice9* device, UINT startRegister, const float* constantData, UINT vector4fCount)
		{
			VertexConstantCalls.fetch_add(1, std::memory_order_relaxed);
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

			BeginSceneHook = safetyhook::create_inline(vtable[BeginSceneVtableIndex], BeginSceneDest);
			SetVertexShaderConstantFHook = safetyhook::create_inline(
				vtable[SetVertexShaderConstantFVtableIndex], SetVertexShaderConstantFDest);

			if (!BeginSceneHook || !SetVertexShaderConstantFHook)
			{
				BeginSceneHook = {};
				SetVertexShaderConstantFHook = {};
				spdlog::error("VR renderer: failed to hook D3D9 renderer boundary");
				return false;
			}

			EnsureSharedState();
			spdlog::info("VR renderer: D3D9 hooks installed; frame-latched c64 WVP injection armed (vtbl 41/94)");
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
