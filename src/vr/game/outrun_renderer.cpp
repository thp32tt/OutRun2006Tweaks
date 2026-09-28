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
#include "input_manager.hpp"
#include "vr_shared.hpp"
#include "vr/ipc/host_pose_v3.hpp"
#include "vr/ipc/cadence_v1.hpp"
#include "vr/ipc/recenter_request.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/disasm_render_contract.hpp"

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
// The final shader upload remains the authoritative visual transform. A small
// render-phase camera-state sync mirrors the same pose into cam_pos/look only
// between BeginScene and EndScene so culling/billboards/flares that consult the
// live camera can follow head motion without feeding VR values back into the
// physics tick. The sync is restored before EndScene calls the original D3D9
// function. This intentionally does not claim to fix culling that happens before
// BeginScene; that boundary still needs runtime visibility testing.
//
// Stereo eye FOV/IPD are latched from the SAME immutable host snapshot as the
// head pose once per successful game BeginScene. Protocol v3 is the primary
// source; the proven v2 bridge remains a same-frame fallback until transport v3
// fully replaces the legacy frame ring.

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRAutoEnableWhenHostPresent;
	extern Setting<bool> VRHeadTracking;
	extern Setting<bool> VRPositionalTracking;
	extern Setting<bool> VRCullingCameraSync;
	extern Setting<bool> VRCullingUnionFov;
	extern Setting<float> VRCullingUnionMarginDegrees;
	extern Setting<float> VRWorldScale;
	extern Setting<float> VRRotationScale;
	extern Setting<int> VRMatrixOrder;
	extern Setting<bool> VRTelemetry;
	extern Setting<bool> UseNewInput;
	extern Setting<int> VRFrameCadenceMode;
	extern Setting<float> VRFrameCadenceTimeoutMs;
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
			std::uint32_t referenceSpaceGeneration = 0;
			bool stereoValid = false;
			SharedFov eyeFov[2]{};
			float eyeOffset[2][3]{};
			Quat eyeOrientation[2]{
				{ 0.0f, 0.0f, 0.0f, 1.0f },
				{ 0.0f, 0.0f, 0.0f, 1.0f }
			};
		};

		constexpr std::size_t BeginSceneVtableIndex = 41;
		constexpr std::size_t EndSceneVtableIndex = 42;
		constexpr std::size_t SetVertexShaderConstantFVtableIndex = 94;
		constexpr UINT OutRunWvpRegister =
			static_cast<UINT>(OutRunVR::DisasmContract::WvpVsRegister);
		constexpr UINT OutRunWvpRegisterCount =
			static_cast<UINT>(OutRunVR::DisasmContract::WvpVsRegisterCount);

		// Recovered EXE addresses are centralized in the backend-neutral contract.
		constexpr std::uintptr_t OutRunViewRva =
			OutRunVR::DisasmContract::ViewRva;
		constexpr std::uintptr_t OutRunProjectionRva =
			OutRunVR::DisasmContract::ProjectionRva;
		constexpr std::uintptr_t OutRunWorldViewRva =
			OutRunVR::DisasmContract::WorldViewRva;

		constexpr float Pi = 3.14159265358979323846f;
		constexpr float WvpVerifyAbsoluteEpsilon = 0.05f;
		constexpr LONGLONG HostPoseStaleMs = 250;

		SafetyHookInline BeginSceneHook{};
		SafetyHookInline EndSceneHook{};
		SafetyHookInline SetVertexShaderConstantFHook{};

		constexpr std::uint32_t RendererInstallPending = 0;
		constexpr std::uint32_t RendererInstallReady = 1;
		constexpr std::uint32_t RendererInstallFailed = 2;
		std::atomic<std::uint32_t> RendererInstallState{RendererInstallPending};
		std::atomic<bool> RendererInjectionAllowed{true};

		HANDLE SharedMapping = nullptr;
		SharedPoseState* SharedState = nullptr;
		LARGE_INTEGER QpcFrequency{};
		OutRunVR::IpcV3::HostPoseV3Source V3PoseSource{};

		HANDLE CadenceHostMapping = nullptr;
		const OutRunVR::CadenceV1::HostState* CadenceHostState = nullptr;
		HANDLE CadenceClientMapping = nullptr;
		OutRunVR::CadenceV1::ClientState* CadenceClientState = nullptr;
		HANDLE CadenceRequestEvent = nullptr;
		HANDLE CadencePresentedEvent = nullptr;
		std::atomic<std::uint32_t> ActiveCadenceRequestId{0};
		std::atomic<bool> CadencePacingActive{false};
		std::uint32_t CadenceAcceptedRequestId = 0;
		std::uint32_t CadencePresentedRequestId = 0;
		std::uint32_t CadenceTimedOutRequestId = 0;
		std::uint32_t CadenceTimeoutCount = 0;
		std::uint32_t CadenceLastWaitUs = 0;
		std::int64_t CadenceAcceptedQpc = 0;
		std::int64_t CadencePresentedQpc = 0;
		bool FirstCadenceAcceptedLogged = false;
		bool FirstCadenceTimeoutLogged = false;

		const D3DMATRIX* RendererView = nullptr;
		const D3DMATRIX* RendererProjection = nullptr;
		const D3DMATRIX* RendererWorldView = nullptr;
		bool RendererGlobalsChecked = false;
		bool RendererGlobalsValid = false;

		Quat CenterOrientation{ 0.0f, 0.0f, 0.0f, 1.0f };
		Vec3 CenterPosition{ 0.0f, 0.0f, 0.0f };
		bool CenterValid = false;
		bool CenterPositionValid = false;
		std::uint32_t CenterHostPid = 0;
		std::uint32_t CenterReferenceSpaceGeneration = 0;
		bool RecenterWasDown = false;
		bool PendingRendererRecenter = false;
		LONG LastPublishedRecenterRequest = 0;
		bool AutoEnableLogged = false;

		D3DMATRIX LatchedHeadInverse{};
		bool LatchedHeadInverseValid = false;
		LatchedStereoFrame LatchedStereo{};
		std::uint32_t FrameTelemetryFlags = ClientHookAlive;
		float LatchedRelativeAngleDeg = 0.0f;
		std::uint32_t LatchedPoseSequence = 0;
		bool PresentPoseLocked = false;
		bool LastPoseSourceV3 = false;

		float LastVerifiedWvp[16]{};
		bool LastVerifiedWvpValid = false;
		std::uint32_t LastVerifiedWvpGeneration = 0;
		std::uint32_t LastVerifiedWvpPoseSequence = 0;
		std::uintptr_t LastVerifiedShaderIdentity = 0;
		std::uint64_t LastVerifiedShaderSerial = 0;

		float LastGameWvpWrite[16]{};
		float LastRawGameWvpWrite[16]{};
		bool LastGameWvpWriteValid = false;
		std::uint64_t LastGameWvpWriteSerial = 0;
		std::uint64_t LastGameWvpTopLevelDrawSerial = 0;
		std::uintptr_t LastGameWvpShaderIdentity = 0;
		std::uint64_t LastGameWvpShaderSerial = 0;
		OutRunVR::GameSemantic::RenderScope LastGameWvpSemanticScope =
			OutRunVR::GameSemantic::RenderScope::None;
		std::uint64_t LastGameWvpQueueNodeEpoch = 0;
		const void* LastGameWvpQueueNode = nullptr;

		D3DVECTOR CullingCameraSavedPos{};
		D3DVECTOR CullingCameraSavedLook{};
		EvWorkCamera* CullingCameraObject = nullptr;
		bool CullingCameraOverridden = false;
		D3DMATRIX CullingProjectionSaved{};
		bool CullingProjectionOverridden = false;

		ULONGLONG LastSummaryMs = 0;
		std::uint64_t BeginSceneCalls = 0;
		std::uint64_t WvpCandidateCalls = 0;
		std::uint64_t WvpVerifiedCalls = 0;
		std::uint64_t WvpPreparedCalls = 0;
		std::uint64_t WvpUploadSucceededCalls = 0;
		std::uint64_t WvpUploadFailedCalls = 0;
		std::uint64_t WvpRejectedCalls = 0;
		std::uint64_t SemanticOverlayBypassCalls = 0;
		std::uint64_t UnsafeAddressRejects = 0;
		std::uint64_t ReusedPoseSceneCalls = 0;
		std::uint64_t V3PoseReads = 0;
		std::uint64_t V2PoseFallbacks = 0;
		bool FirstVerifiedLogged = false;
		bool FirstInjectedLogged = false;
		bool FirstRejectedLogged = false;
		bool FirstUnsafeAddressLogged = false;
		bool FirstUploadFailedLogged = false;
		bool FirstSemanticOverlayBypassLogged = false;
		bool CullingUnionFovDeferredLogged = false;
		bool FirstV3PoseLogged = false;
		bool FirstV2FallbackLogged = false;

		bool IsGameDevice(IDirect3DDevice9* device)
		{
			return device && Game::D3DDevice_ptr && *Game::D3DDevice_ptr == device;
		}

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

		bool FovValid(const SharedFov& fov)
		{
			constexpr float limit = 1.56f;
			return std::isfinite(fov.angleLeft) && std::isfinite(fov.angleRight) &&
				std::isfinite(fov.angleUp) && std::isfinite(fov.angleDown) &&
				fov.angleLeft > -limit && fov.angleRight < limit &&
				fov.angleDown > -limit && fov.angleUp < limit &&
				fov.angleRight > fov.angleLeft + 0.05f &&
				fov.angleUp > fov.angleDown + 0.05f;
		}

		float FloatFromBits(std::uint32_t bits)
		{
			float value = 0.0f;
			std::memcpy(&value, &bits, sizeof(value));
			return value;
		}

		bool DecodePackedEyeOrientations(const SharedPoseState& snapshot, Quat out[2])
		{
			std::int16_t packed[8]{};
			static_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);
			std::memcpy(packed,
				snapshot.runtimeName + OutRunVR::PackedEyeOrientationOffset,
				sizeof(packed));
			for (int eye = 0; eye < 2; ++eye)
			{
				Quat q{
					static_cast<float>(packed[eye * 4 + 0]) / 32767.0f,
					static_cast<float>(packed[eye * 4 + 1]) / 32767.0f,
					static_cast<float>(packed[eye * 4 + 2]) / 32767.0f,
					static_cast<float>(packed[eye * 4 + 3]) / 32767.0f
				};
				if (!QuaternionIsSane(q))
					return false;
				out[eye] = Normalize(q);
			}
			return true;
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

		Quat YawOnly(const Quat& orientation)
		{
			const Vec3 forward = RotateVector(orientation, { 0.0f, 0.0f, -1.0f });
			if (!VectorIsFinite(forward))
				return { 0.0f, 0.0f, 0.0f, 1.0f };
			const float planarSq = forward.x * forward.x + forward.z * forward.z;
			if (planarSq <= 1.0e-8f)
				return { 0.0f, 0.0f, 0.0f, 1.0f };
			const float yaw = std::atan2(-forward.x, -forward.z);
			return AxisAngle(0.0f, 1.0f, 0.0f, yaw);
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

		D3DMATRIX ProjectionFromFov(const D3DMATRIX& base, const SharedFov& fov)
		{
			const float tanLeft = std::tan(fov.angleLeft), tanRight = std::tan(fov.angleRight);
			const float tanUp = std::tan(fov.angleUp), tanDown = std::tan(fov.angleDown);
			const float width = tanRight - tanLeft, height = tanUp - tanDown;
			D3DMATRIX out{};
			out._11 = 2.0f / width; out._22 = 2.0f / height;
			out._31 = (tanRight + tanLeft) / width; out._32 = (tanUp + tanDown) / height;
			out._33 = base._33; out._34 = base._34; out._43 = base._43; out._44 = base._44;
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

		bool IsWritableRange(void* address, std::size_t size)
		{
			if (!address || size == 0) return false;
			MEMORY_BASIC_INFORMATION info{};
			if (VirtualQuery(address, &info, sizeof(info)) != sizeof(info) || info.State != MEM_COMMIT ||
				(info.Protect & PAGE_GUARD) || (info.Protect & PAGE_NOACCESS)) return false;
			const DWORD protect = info.Protect & 0xFFu;
			const bool writable = protect == PAGE_READWRITE || protect == PAGE_WRITECOPY ||
				protect == PAGE_EXECUTE_READWRITE || protect == PAGE_EXECUTE_WRITECOPY;
			if (!writable) return false;
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

		bool ValidateRendererGlobals()
		{
			if (RendererGlobalsChecked)
				return RendererGlobalsValid;
			RendererGlobalsChecked = true;

			if (!ImageContainsRange(OutRunViewRva, sizeof(D3DMATRIX)) ||
				!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX)) ||
				!ImageContainsRange(OutRunWorldViewRva, sizeof(D3DMATRIX)))
				return false;

			RendererView = Module::exe_ptr<D3DMATRIX>(OutRunViewRva);
			RendererProjection = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
			RendererWorldView = Module::exe_ptr<D3DMATRIX>(OutRunWorldViewRva);
			if (!IsReadableRange(RendererView, sizeof(D3DMATRIX)) ||
				!IsReadableRange(RendererProjection, sizeof(D3DMATRIX)) ||
				!IsReadableRange(RendererWorldView, sizeof(D3DMATRIX)))
			{
				RendererView = nullptr;
				RendererProjection = nullptr;
				RendererWorldView = nullptr;
				return false;
			}

			RendererGlobalsValid = true;
			return true;
		}

		bool ReadRendererMatrices(D3DMATRIX& view, D3DMATRIX& projection, D3DMATRIX& worldView)
		{
			if (!ValidateRendererGlobals())
				return false;
			std::memcpy(&view, RendererView, sizeof(view));
			if (CullingProjectionOverridden) projection = CullingProjectionSaved;
			else std::memcpy(&projection, RendererProjection, sizeof(projection));
			std::memcpy(&worldView, RendererWorldView, sizeof(worldView));
			return MatrixFinite(view) && MatrixFinite(projection) && MatrixFinite(worldView);
		}

		bool SharedHeaderValid()
		{
			return SharedState && SharedState->magic == SharedMagic &&
				SharedState->protocolVersion == SharedProtocolVersion &&
				SharedState->structSize == sizeof(SharedPoseState);
		}

		bool EnsureSharedState()
		{
			if (SharedState)
			{
				if (!SharedHeaderValid())
					return false;
				if (QpcFrequency.QuadPart <= 0)
					QueryPerformanceFrequency(&QpcFrequency);
				InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientPid),
					static_cast<LONG>(GetCurrentProcessId()));
				return true;
			}

			SharedMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
				0, static_cast<DWORD>(sizeof(SharedPoseState)), SharedMemoryName);
			if (!SharedMapping)
				return false;
			const bool mappingAlreadyExisted = GetLastError() == ERROR_ALREADY_EXISTS;

			SharedState = static_cast<SharedPoseState*>(MapViewOfFile(
				SharedMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SharedPoseState)));
			if (!SharedState)
			{
				CloseHandle(SharedMapping);
				SharedMapping = nullptr;
				return false;
			}

			// Creator-only initialization. magic is published last, so an attaching
			// process never treats a partially initialized header as ready.
			if (!mappingAlreadyExisted)
			{
				std::memset(SharedState, 0, sizeof(SharedPoseState));
				SharedState->protocolVersion = SharedProtocolVersion;
				SharedState->structSize = sizeof(SharedPoseState);
				MemoryBarrier();
				SharedState->magic = SharedMagic;
			}
			else if (!SharedHeaderValid())
			{
				// The host may still be publishing a newly-created mapping. Never
				// memset somebody else's mapping; simply retry on a later frame.
				return false;
			}

			QueryPerformanceFrequency(&QpcFrequency);
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientPid),
				static_cast<LONG>(GetCurrentProcessId()));
			spdlog::info("VR renderer: shared pose bridge ready (protocol {}, client pid={})",
				SharedProtocolVersion, GetCurrentProcessId());
			return true;
		}

		ClientPresentationMode CurrentPresentationMode()
		{
			// R65: renderer and D3D9 stereo must make the same presentation
			// decision. In particular, STATE_START is not gameplay until the
			// proven progress==65 stereo-ready boundary.
			if (!Game::current_mode)
				return PresentationUnknown;
			return Game::is_vr_gameplay_presentation()
				? PresentationGameplay : PresentationTheater;
		}

		void PublishClientTelemetry(std::uint32_t flags, float relativeAngleDeg)
		{
			if (!EnsureSharedState())
				return;

			std::uint32_t angleBits = 0;
			static_assert(sizeof(angleBits) == sizeof(relativeAngleDeg));
			std::memcpy(&angleBits, &relativeAngleDeg, sizeof(angleBits));
			const std::uint32_t presentation = static_cast<std::uint32_t>(CurrentPresentationMode());
			const std::uint32_t gameState = Game::current_mode
				? static_cast<std::uint32_t>(*Game::current_mode) : 0xFFFFFFFFu;

			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientPid),
				static_cast<LONG>(GetCurrentProcessId()));
			InterlockedIncrement(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientHeartbeatIndex]));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientFlagsIndex]),
				static_cast<LONG>(flags));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientLastAngleBitsIndex]),
				static_cast<LONG>(angleBits));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientPresentationModeIndex]),
				static_cast<LONG>(presentation));
			InterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[ClientGameStateIndex]),
				static_cast<LONG>(gameState));
		}

		bool ReadHostPose(PoseSample& pose)
		{
			OutRunVR::IpcV3::HostPoseSnapshot v3{};
			if (V3PoseSource.Read(v3))
			{
				const std::uint32_t legacySequence = static_cast<std::uint32_t>(v3.poseId & 0xFFFFFFFFu);
				if (legacySequence != 0)
				{
					pose = {};
					pose.sequence = legacySequence;
					pose.hostPid = v3.hostPid;
					pose.referenceSpaceGeneration = v3.referenceSpaceGeneration;
					pose.orientation = {
						v3.headOrientation[0], v3.headOrientation[1],
						v3.headOrientation[2], v3.headOrientation[3]
					};
					pose.position = {
						v3.headPositionMeters[0], v3.headPositionMeters[1], v3.headPositionMeters[2]
					};
					pose.positionValid = v3.positionValid;
					pose.stereoValid = v3.stereoValid;
					if (pose.stereoValid)
					{
						for (int eye = 0; eye < 2; ++eye)
						{
							pose.eyeFov[eye] = {
								v3.eyes[eye].fov.angleLeft,
								v3.eyes[eye].fov.angleRight,
								v3.eyes[eye].fov.angleUp,
								v3.eyes[eye].fov.angleDown
							};
							for (int axis = 0; axis < 3; ++axis)
								pose.eyeOffset[eye][axis] = v3.eyes[eye].positionMeters[axis];
							pose.eyeOrientation[eye] = {
								v3.eyes[eye].orientation[0], v3.eyes[eye].orientation[1],
								v3.eyes[eye].orientation[2], v3.eyes[eye].orientation[3]
							};
						}
					}
					LastPoseSourceV3 = true;
					++V3PoseReads;
					if (!FirstV3PoseLogged)
					{
						FirstV3PoseLogged = true;
						spdlog::info("VR renderer: protocol v3 pose is PRIMARY; legacy v2 remains automatic fallback");
					}
					return true;
				}
			}

			LastPoseSourceV3 = false;
			++V2PoseFallbacks;
			if (!FirstV2FallbackLogged && V3PoseReads != 0)
			{
				FirstV2FallbackLogged = true;
				spdlog::warn("VR renderer: protocol v3 pose unavailable/stale; falling back to legacy v2 pose without dropping the frame");
			}

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