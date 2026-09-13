#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr_shared.hpp"

namespace Settings
{
	Setting<bool> VREnabled{ "VR", "Enabled", true,
		"Enables the experimental OpenXR VR camera bridge. The dedicated vr-openxr branch defaults this on." };
	Setting<bool> VRAutoEnableWhenHostPresent{ "VR", "AutoEnableWhenHostPresent", true,
		"Automatically applies head tracking whenever outrun-vr-host.exe is supplying a valid pose. This also overrides an old Enabled=false user setting." };
	Setting<bool> VRHeadTracking{ "VR", "HeadTracking", true,
		"Applies the OpenXR HMD orientation to the rendered camera without changing gameplay camera state." };
	Setting<bool> VRPositionalTracking{ "VR", "PositionalTracking", false,
		"Also applies HMD X/Y/Z movement. Experimental; keep disabled until rotation tracking is verified." };
	Setting<float> VRWorldScale{ "VR", "WorldScale", 1.0f,
		"Game-world units per metre of OpenXR head movement.", Range<float>{ 0.1f, 10.0f } };
	Setting<float> VRRotationScale{ "VR", "RotationScale", 1.0f,
		"Scales HMD rotation around the recentered forward direction.", Range<float>{ 0.0f, 2.0f } };
	Setting<int> VRMatrixOrder{ "VR", "MatrixOrder", 0,
		"Camera-matrix composition order. Default matches the expected D3D9 row-vector convention.",
		{ "GameView * HeadInverse", "HeadInverse * GameView" } };
	Setting<bool> VRTelemetry{ "VR", "Telemetry", true,
		"Logs one head-tracking diagnostic line per second while VR is active." };
	Setting<bool> VRDebugPose{ "VR", "DebugPose", false,
		"Uses the manual debug angles below when no OpenXR host pose is available." };
	Setting<float> VRDebugPitch{ "VR", "DebugPitch", 0.0f,
		"Manual pitch in degrees for VR camera diagnostics.", Range<float>{ -90.0f, 90.0f } };
	Setting<float> VRDebugYaw{ "VR", "DebugYaw", 0.0f,
		"Manual yaw in degrees for VR camera diagnostics.", Range<float>{ -180.0f, 180.0f } };
	Setting<float> VRDebugRoll{ "VR", "DebugRoll", 0.0f,
		"Manual roll in degrees for VR camera diagnostics.", Range<float>{ -90.0f, 90.0f } };
}

namespace OutRunVR
{
	namespace
	{
		struct Vec3 { float x, y, z; };
		struct Quat { float x, y, z, w; };
		struct PoseSample
		{
			Quat orientation{ 0.0f, 0.0f, 0.0f, 1.0f };
			Vec3 position{ 0.0f, 0.0f, 0.0f };
			bool orientationValid = false;
			bool positionValid = false;
			std::uint32_t hostPid = 0;
		};

		HANDLE SharedMapping = nullptr;
		SharedPoseState* SharedState = nullptr;
		LARGE_INTEGER QpcFrequency{};
		bool SharedInitAttempted = false;
		bool HostWasConnected = false;
		std::uint32_t LastHostPid = 0;

		Quat CenterOrientation{ 0.0f, 0.0f, 0.0f, 1.0f };
		Vec3 CenterPosition{ 0.0f, 0.0f, 0.0f };
		bool CenterValid = false;
		bool AutoEnableLogged = false;
		ULONGLONG LastTrackingLogMs = 0;

		constexpr float Pi = 3.14159265358979323846f;

		float DegToRad(float degrees) { return degrees * (Pi / 180.0f); }

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

		Quat DebugEuler(float pitch, float yaw, float roll)
		{
			const Quat qYaw = AxisAngle(0.0f, 1.0f, 0.0f, yaw);
			const Quat qPitch = AxisAngle(1.0f, 0.0f, 0.0f, pitch);
			const Quat qRoll = AxisAngle(0.0f, 0.0f, 1.0f, roll);
			return Multiply(Multiply(qYaw, qPitch), qRoll);
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

		bool EnsureSharedMemory()
		{
			if (SharedState)
				return true;
			if (SharedInitAttempted)
				return false;

			SharedInitAttempted = true;
			QueryPerformanceFrequency(&QpcFrequency);
			SharedMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
				0, static_cast<DWORD>(sizeof(SharedPoseState)), SharedMemoryName);
			if (!SharedMapping)
			{
				spdlog::error("VR: CreateFileMappingW failed: {}", GetLastError());
				return false;
			}

			SharedState = static_cast<SharedPoseState*>(MapViewOfFile(
				SharedMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SharedPoseState)));
			if (!SharedState)
			{
				spdlog::error("VR: MapViewOfFile failed: {}", GetLastError());
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

			SharedState->clientPid = GetCurrentProcessId();
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientFlagsIndex]),
				static_cast<LONG>(ClientHookAlive));
			spdlog::info("VR: shared pose bridge ready (protocol {}, client pid={})",
				SharedProtocolVersion, GetCurrentProcessId());
			return true;
		}

		void PublishClientTelemetry(std::uint32_t flags, float relativeAngleDeg)
		{
			if (!SharedState)
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
			if (!EnsureSharedMemory())
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
					break;
				}
			}

			if (!stable || snapshot.magic != SharedMagic ||
				snapshot.protocolVersion != SharedProtocolVersion ||
				snapshot.structSize != sizeof(SharedPoseState))
				return false;

			const bool alive = (snapshot.flags & HostAlive) != 0 && snapshot.hostPid != 0;
			if (!alive)
			{
				if (HostWasConnected)
					spdlog::warn("VR: OpenXR host disconnected; flat camera restored");
				HostWasConnected = false;
				CenterValid = false;
				LastHostPid = 0;
				return false;
			}

			LARGE_INTEGER now{};
			QueryPerformanceCounter(&now);
			if (QpcFrequency.QuadPart > 0 && snapshot.sampleQpc > 0 &&
				(now.QuadPart - snapshot.sampleQpc) > (QpcFrequency.QuadPart * 2))
			{
				if (HostWasConnected)
					spdlog::warn("VR: OpenXR host heartbeat is stale; ignoring pose");
				HostWasConnected = false;
				CenterValid = false;
				return false;
			}

			if (!HostWasConnected || LastHostPid != snapshot.hostPid)
			{
				spdlog::info("VR: OpenXR host connected (pid={}, runtime={})",
					snapshot.hostPid, snapshot.runtimeName[0] ? snapshot.runtimeName : "unknown");
				CenterValid = false;
			}
			HostWasConnected = true;
			LastHostPid = snapshot.hostPid;

			pose.hostPid = snapshot.hostPid;
			pose.orientationValid = (snapshot.flags & OrientationValid) != 0;
			pose.positionValid = (snapshot.flags & PositionValid) != 0;

			// OpenXR: right handed, -Z forward. Reflect Z into the D3D9 game's
			// left-handed basis. B * R * B maps quaternion (x,y,z,w) to (-x,-y,z,w).
			pose.orientation = Normalize({
				-snapshot.orientation[0], -snapshot.orientation[1],
				snapshot.orientation[2], snapshot.orientation[3]
			});
			pose.position = { snapshot.position[0], snapshot.position[1], -snapshot.position[2] };
			return pose.orientationValid;
		}

		bool RecenterPressed()
		{
			static bool wasDown = false;
			const bool isDown = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
			const bool pressed = isDown && !wasDown;
			wasDown = isDown;
			return pressed;
		}

		void ApplyPose(EvWorkCamera* cam)
		{
			if (!cam || !Settings::VRHeadTracking || !Game::is_in_game())
				return;

			PoseSample sample{};
			const bool haveHostPose = ReadHostPose(sample);
			const bool autoEnabled = haveHostPose && Settings::VRAutoEnableWhenHostPresent;
			const bool enabled = Settings::VREnabled || autoEnabled;

			std::uint32_t telemetryFlags = ClientHookAlive;
			if (haveHostPose)
				telemetryFlags |= ClientHostPoseValid;
			if (autoEnabled && !Settings::VREnabled)
				telemetryFlags |= ClientAutoEnabled;

			if (!enabled)
			{
				PublishClientTelemetry(telemetryFlags, 0.0f);
				return;
			}

			if (autoEnabled && !Settings::VREnabled && !AutoEnableLogged)
			{
				spdlog::info("VR: valid host pose detected; AutoEnableWhenHostPresent is overriding legacy Enabled=false");
				AutoEnableLogged = true;
			}

			Quat relativeOrientation{ 0.0f, 0.0f, 0.0f, 1.0f };
			Vec3 relativePosition{ 0.0f, 0.0f, 0.0f };

			if (haveHostPose)
			{
				const bool recenter = RecenterPressed();
				if (!CenterValid || recenter)
				{
					CenterOrientation = sample.orientation;
					CenterPosition = sample.position;
					CenterValid = true;
					if (recenter)
						spdlog::info("VR: recentered HMD pose (F10)");
				}

				const Quat invCenter = Conjugate(Normalize(CenterOrientation));
				relativeOrientation = Multiply(invCenter, sample.orientation);
				if (Settings::VRPositionalTracking && sample.positionValid)
				{
					const Vec3 delta{
						sample.position.x - CenterPosition.x,
						sample.position.y - CenterPosition.y,
						sample.position.z - CenterPosition.z
					};
					relativePosition = RotateVector(invCenter, delta);
				}
			}
			else if (Settings::VRDebugPose && Settings::VREnabled)
			{
				relativeOrientation = DebugEuler(
					DegToRad(Settings::VRDebugPitch),
					DegToRad(Settings::VRDebugYaw),
					DegToRad(Settings::VRDebugRoll));
			}
			else
			{
				PublishClientTelemetry(telemetryFlags, 0.0f);
				return;
			}

			relativeOrientation = ScaleRotation(relativeOrientation, Settings::VRRotationScale);
			relativePosition.x *= Settings::VRWorldScale;
			relativePosition.y *= Settings::VRWorldScale;
			relativePosition.z *= Settings::VRWorldScale;

			const float w = std::clamp(std::fabs(relativeOrientation.w), 0.0f, 1.0f);
			const float relativeAngleDeg = 2.0f * std::acos(w) * (180.0f / Pi);
			const D3DMATRIX before = cam->d3dmatrix140;
			const D3DMATRIX headInverse = InverseRigid(MatrixFromPose(relativeOrientation, relativePosition));

			// CalcCameraMatrix has already produced the normal game view. Modifying
			// only d3dmatrix140 means HMD motion never feeds back into OutRun's
			// cam_pos_F8/look_pos_104/cam_ang_128 or its interpolation cache.
			if (Settings::VRMatrixOrder == 0)
				cam->d3dmatrix140 = MultiplyMatrix(cam->d3dmatrix140, headInverse);
			else
				cam->d3dmatrix140 = MultiplyMatrix(headInverse, cam->d3dmatrix140);

			telemetryFlags |= ClientPoseApplied;
			PublishClientTelemetry(telemetryFlags, relativeAngleDeg);

			if (Settings::VRTelemetry)
			{
				const ULONGLONG nowMs = GetTickCount64();
				if (nowMs - LastTrackingLogMs >= 1000)
				{
					LastTrackingLogMs = nowMs;
					const float matrixDelta =
						std::fabs(cam->d3dmatrix140._11 - before._11) +
						std::fabs(cam->d3dmatrix140._12 - before._12) +
						std::fabs(cam->d3dmatrix140._13 - before._13) +
						std::fabs(cam->d3dmatrix140._21 - before._21) +
						std::fabs(cam->d3dmatrix140._22 - before._22) +
						std::fabs(cam->d3dmatrix140._23 - before._23);
					spdlog::info(
						"VR: tracking applied host={} angle={:.2f}deg matrixDelta={:.5f} order={} q=({:.3f},{:.3f},{:.3f},{:.3f})",
						sample.hostPid, relativeAngleDeg, matrixDelta, Settings::VRMatrixOrder.get(),
						relativeOrientation.x, relativeOrientation.y, relativeOrientation.z, relativeOrientation.w);
				}
			}
		}
	}

	class VRHeadTrackingHook : public Hook
	{
		inline static SafetyHookInline CalcCameraMatrixHook{};

		static void __cdecl CalcCameraMatrixDest(EvWorkCamera* cam)
		{
			CalcCameraMatrixHook.ccall(cam);
			ApplyPose(cam);
		}

	public:
		std::string_view description() override { return "OpenXRVRHeadTracking"; }
		bool validate() override { return true; }

		bool apply() override
		{
			// Register the x86 client as soon as the DLL loads, rather than waiting
			// until a race and an enabled camera setting. The x64 host can now prove
			// that the game-side bridge is present and can detect when the game exits.
			EnsureSharedMemory();

			CalcCameraMatrixHook = safetyhook::create_inline(
				Module::exe_ptr(GameAddr::CalcCameraMatrix), CalcCameraMatrixDest);
			if (!CalcCameraMatrixHook)
			{
				spdlog::error("VR: failed to hook CalcCameraMatrix");
				return false;
			}
			spdlog::info("VR: CalcCameraMatrix head-tracking hook installed (auto-enable with live host is ON)");
			return true;
		}

		static VRHeadTrackingHook instance;
	};

	VRHeadTrackingHook VRHeadTrackingHook::instance;
}
