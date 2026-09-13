#define XR_USE_PLATFORM_WIN32
#define XR_USE_GRAPHICS_API_D3D11

#include <Windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "vr_shared.hpp"

namespace
{
	void CheckXr(XrResult result, const char* what)
	{
		if (XR_FAILED(result))
			throw std::runtime_error(std::string(what) + " failed, XrResult=" + std::to_string(result));
	}

	void CheckHr(HRESULT hr, const char* what)
	{
		if (FAILED(hr))
			throw std::runtime_error(std::string(what) + " failed, HRESULT=" + std::to_string(static_cast<long>(hr)));
	}

	bool HasExtension(const char* wanted)
	{
		std::uint32_t count = 0;
		CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, 0, &count, nullptr),
			"xrEnumerateInstanceExtensionProperties(count)");

		std::vector<XrExtensionProperties> extensions(count);
		for (auto& ext : extensions)
			ext = { XR_TYPE_EXTENSION_PROPERTIES };
		CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, count, &count, extensions.data()),
			"xrEnumerateInstanceExtensionProperties(list)");

		for (const auto& ext : extensions)
			if (std::strcmp(ext.extensionName, wanted) == 0)
				return true;
		return false;
	}

	bool SameLuid(const LUID& a, const LUID& b)
	{
		return a.LowPart == b.LowPart && a.HighPart == b.HighPart;
	}

	IDXGIAdapter1* FindAdapter(const LUID& wanted)
	{
		IDXGIFactory1* factory = nullptr;
		CheckHr(CreateDXGIFactory1(__uuidof(IDXGIFactory1), reinterpret_cast<void**>(&factory)),
			"CreateDXGIFactory1");

		IDXGIAdapter1* match = nullptr;
		for (UINT i = 0;; ++i)
		{
			IDXGIAdapter1* adapter = nullptr;
			if (factory->EnumAdapters1(i, &adapter) == DXGI_ERROR_NOT_FOUND)
				break;

			DXGI_ADAPTER_DESC1 desc{};
			adapter->GetDesc1(&desc);
			if (SameLuid(desc.AdapterLuid, wanted))
			{
				match = adapter;
				break;
			}
			adapter->Release();
		}

		factory->Release();
		if (!match)
			throw std::runtime_error("OpenXR runtime D3D11 adapter was not found");
		return match;
	}

	struct D3DObjects
	{
		ID3D11Device* device = nullptr;
		ID3D11DeviceContext* context = nullptr;

		~D3DObjects()
		{
			if (context)
				context->Release();
			if (device)
				device->Release();
		}
	};

	D3DObjects CreateD3D11Device(const XrGraphicsRequirementsD3D11KHR& requirements)
	{
		IDXGIAdapter1* adapter = FindAdapter(requirements.adapterLuid);

		const std::array<D3D_FEATURE_LEVEL, 7> allLevels{
			D3D_FEATURE_LEVEL_12_1,
			D3D_FEATURE_LEVEL_12_0,
			D3D_FEATURE_LEVEL_11_1,
			D3D_FEATURE_LEVEL_11_0,
			D3D_FEATURE_LEVEL_10_1,
			D3D_FEATURE_LEVEL_10_0,
			D3D_FEATURE_LEVEL_9_3,
		};
		std::vector<D3D_FEATURE_LEVEL> levels;
		for (const auto level : allLevels)
			if (level >= requirements.minFeatureLevel)
				levels.push_back(level);
		if (levels.empty())
			levels.push_back(requirements.minFeatureLevel);

		D3DObjects out;
		D3D_FEATURE_LEVEL selected{};
		const HRESULT hr = D3D11CreateDevice(
			adapter,
			D3D_DRIVER_TYPE_UNKNOWN,
			nullptr,
			D3D11_CREATE_DEVICE_BGRA_SUPPORT,
			levels.data(),
			static_cast<UINT>(levels.size()),
			D3D11_SDK_VERSION,
			&out.device,
			&selected,
			&out.context);
		adapter->Release();
		CheckHr(hr, "D3D11CreateDevice");
		return out;
	}

	class SharedWriter
	{
	public:
		SharedWriter()
		{
			mapping_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
				0, static_cast<DWORD>(sizeof(OutRunVR::SharedPoseState)), OutRunVR::SharedMemoryName);
			if (!mapping_)
				throw std::runtime_error("CreateFileMappingW failed: " + std::to_string(GetLastError()));

			state_ = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(
				mapping_, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedPoseState)));
			if (!state_)
				throw std::runtime_error("MapViewOfFile failed: " + std::to_string(GetLastError()));

			if (state_->magic != OutRunVR::SharedMagic ||
				state_->protocolVersion != OutRunVR::SharedProtocolVersion ||
				state_->structSize != sizeof(OutRunVR::SharedPoseState))
			{
				std::memset(state_, 0, sizeof(*state_));
				state_->magic = OutRunVR::SharedMagic;
				state_->protocolVersion = OutRunVR::SharedProtocolVersion;
				state_->structSize = sizeof(OutRunVR::SharedPoseState);
			}
		}

		~SharedWriter()
		{
			if (state_)
			{
				BeginWrite();
				state_->flags = 0;
				state_->hostPid = 0;
				EndWrite();
				UnmapViewOfFile(state_);
			}
			if (mapping_)
				CloseHandle(mapping_);
		}

		void Write(const XrSpaceLocation& headLocation,
			const std::array<XrView, 2>& views,
			std::uint32_t viewCount,
			const std::array<XrViewConfigurationView, 2>& configs,
			XrSessionState sessionState,
			const char* runtimeName)
		{
			LARGE_INTEGER qpc{};
			QueryPerformanceCounter(&qpc);

			std::uint32_t flags = OutRunVR::HostAlive;
			if (headLocation.locationFlags & XR_SPACE_LOCATION_ORIENTATION_VALID_BIT)
				flags |= OutRunVR::OrientationValid;
			if (headLocation.locationFlags & XR_SPACE_LOCATION_POSITION_VALID_BIT)
				flags |= OutRunVR::PositionValid;
			if (sessionState == XR_SESSION_STATE_VISIBLE || sessionState == XR_SESSION_STATE_FOCUSED)
				flags |= OutRunVR::SessionVisible;
			if (sessionState == XR_SESSION_STATE_FOCUSED)
				flags |= OutRunVR::SessionFocused;

			BeginWrite();
			state_->hostPid = GetCurrentProcessId();
			state_->flags = flags;
			state_->heartbeat += 1;
			state_->sampleQpc = qpc.QuadPart;

			state_->orientation[0] = headLocation.pose.orientation.x;
			state_->orientation[1] = headLocation.pose.orientation.y;
			state_->orientation[2] = headLocation.pose.orientation.z;
			state_->orientation[3] = headLocation.pose.orientation.w;
			state_->position[0] = headLocation.pose.position.x;
			state_->position[1] = headLocation.pose.position.y;
			state_->position[2] = headLocation.pose.position.z;

			for (std::uint32_t eye = 0; eye < 2; ++eye)
			{
				if (eye < viewCount)
				{
					state_->eyeFov[eye].angleLeft = views[eye].fov.angleLeft;
					state_->eyeFov[eye].angleRight = views[eye].fov.angleRight;
					state_->eyeFov[eye].angleUp = views[eye].fov.angleUp;
					state_->eyeFov[eye].angleDown = views[eye].fov.angleDown;
				}
				state_->recommendedWidth[eye] = configs[eye].recommendedImageRectWidth;
				state_->recommendedHeight[eye] = configs[eye].recommendedImageRectHeight;
			}

			strncpy_s(state_->runtimeName, sizeof(state_->runtimeName),
				runtimeName ? runtimeName : "unknown", _TRUNCATE);
			EndWrite();
		}

	private:
		void BeginWrite()
		{
			LONG sequence = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
			if ((sequence & 1) == 0)
				InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
			MemoryBarrier();
		}

		void EndWrite()
		{
			MemoryBarrier();
			LONG sequence = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
			if (sequence & 1)
				InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
		}

		HANDLE mapping_ = nullptr;
		OutRunVR::SharedPoseState* state_ = nullptr;
	};

	XrEnvironmentBlendMode ChooseBlendMode(XrInstance instance, XrSystemId systemId)
	{
		std::uint32_t count = 0;
		CheckXr(xrEnumerateEnvironmentBlendModes(instance, systemId,
			XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, 0, &count, nullptr),
			"xrEnumerateEnvironmentBlendModes(count)");
		if (!count)
			throw std::runtime_error("OpenXR runtime returned no environment blend modes");

		std::vector<XrEnvironmentBlendMode> modes(count);
		CheckXr(xrEnumerateEnvironmentBlendModes(instance, systemId,
			XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, count, &count, modes.data()),
			"xrEnumerateEnvironmentBlendModes(list)");

		for (const auto mode : modes)
			if (mode == XR_ENVIRONMENT_BLEND_MODE_OPAQUE)
				return mode;
		return modes.front();
	}

	bool ParseRuntimeOverride(int argc, char** argv)
	{
		for (int i = 1; i + 1 < argc; ++i)
		{
			if (std::strcmp(argv[i], "--runtime-json") == 0)
			{
				if (!SetEnvironmentVariableA("XR_RUNTIME_JSON", argv[i + 1]))
					throw std::runtime_error("failed to set XR_RUNTIME_JSON");
				std::cout << "XR_RUNTIME_JSON=" << argv[i + 1] << "\n";
				return true;
			}
		}
		return false;
	}
}

int main(int argc, char** argv)
{
	try
	{
		ParseRuntimeOverride(argc, argv);

		if (!HasExtension(XR_KHR_D3D11_ENABLE_EXTENSION_NAME))
			throw std::runtime_error("active OpenXR runtime does not expose XR_KHR_D3D11_enable");

		const char* extensions[] = { XR_KHR_D3D11_ENABLE_EXTENSION_NAME };
		XrInstanceCreateInfo instanceInfo{ XR_TYPE_INSTANCE_CREATE_INFO };
		strncpy_s(instanceInfo.applicationInfo.applicationName,
			sizeof(instanceInfo.applicationInfo.applicationName), "OutRun 2006 VR", _TRUNCATE);
		instanceInfo.applicationInfo.applicationVersion = 1;
		strncpy_s(instanceInfo.applicationInfo.engineName,
			sizeof(instanceInfo.applicationInfo.engineName), "OutRun2006Tweaks", _TRUNCATE);
		instanceInfo.applicationInfo.engineVersion = 1;
		instanceInfo.applicationInfo.apiVersion = XR_CURRENT_API_VERSION;
		instanceInfo.enabledExtensionCount = 1;
		instanceInfo.enabledExtensionNames = extensions;

		XrInstance instance = XR_NULL_HANDLE;
		CheckXr(xrCreateInstance(&instanceInfo, &instance), "xrCreateInstance");

		XrInstanceProperties instanceProperties{ XR_TYPE_INSTANCE_PROPERTIES };
		CheckXr(xrGetInstanceProperties(instance, &instanceProperties), "xrGetInstanceProperties");
		std::cout << "OpenXR runtime: " << instanceProperties.runtimeName << " "
			<< XR_VERSION_MAJOR(instanceProperties.runtimeVersion) << "."
			<< XR_VERSION_MINOR(instanceProperties.runtimeVersion) << "."
			<< XR_VERSION_PATCH(instanceProperties.runtimeVersion) << "\n";

		XrSystemGetInfo systemInfo{ XR_TYPE_SYSTEM_GET_INFO };
		systemInfo.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
		XrSystemId systemId = XR_NULL_SYSTEM_ID;
		CheckXr(xrGetSystem(instance, &systemInfo, &systemId), "xrGetSystem");

		PFN_xrGetD3D11GraphicsRequirementsKHR getD3D11Requirements = nullptr;
		CheckXr(xrGetInstanceProcAddr(instance, "xrGetD3D11GraphicsRequirementsKHR",
			reinterpret_cast<PFN_xrVoidFunction*>(&getD3D11Requirements)),
			"xrGetInstanceProcAddr(xrGetD3D11GraphicsRequirementsKHR)");
		if (!getD3D11Requirements)
			throw std::runtime_error("xrGetD3D11GraphicsRequirementsKHR is null");

		XrGraphicsRequirementsD3D11KHR requirements{ XR_TYPE_GRAPHICS_REQUIREMENTS_D3D11_KHR };
		CheckXr(getD3D11Requirements(instance, systemId, &requirements),
			"xrGetD3D11GraphicsRequirementsKHR");
		D3DObjects d3d = CreateD3D11Device(requirements);

		XrGraphicsBindingD3D11KHR graphicsBinding{ XR_TYPE_GRAPHICS_BINDING_D3D11_KHR };
		graphicsBinding.device = d3d.device;
		XrSessionCreateInfo sessionInfo{ XR_TYPE_SESSION_CREATE_INFO };
		sessionInfo.next = &graphicsBinding;
		sessionInfo.systemId = systemId;

		XrSession session = XR_NULL_HANDLE;
		CheckXr(xrCreateSession(instance, &sessionInfo, &session), "xrCreateSession");

		XrPosef identityPose{};
		identityPose.orientation.w = 1.0f;

		XrReferenceSpaceCreateInfo localInfo{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
		localInfo.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL;
		localInfo.poseInReferenceSpace = identityPose;
		XrSpace localSpace = XR_NULL_HANDLE;
		CheckXr(xrCreateReferenceSpace(session, &localInfo, &localSpace),
			"xrCreateReferenceSpace(LOCAL)");

		XrReferenceSpaceCreateInfo viewInfo{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
		viewInfo.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_VIEW;
		viewInfo.poseInReferenceSpace = identityPose;
		XrSpace viewSpace = XR_NULL_HANDLE;
		CheckXr(xrCreateReferenceSpace(session, &viewInfo, &viewSpace),
			"xrCreateReferenceSpace(VIEW)");

		std::uint32_t configCount = 0;
		CheckXr(xrEnumerateViewConfigurationViews(instance, systemId,
			XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, 0, &configCount, nullptr),
			"xrEnumerateViewConfigurationViews(count)");
		if (configCount < 2)
			throw std::runtime_error("OpenXR runtime did not expose two stereo views");

		std::vector<XrViewConfigurationView> configVector(configCount);
		for (auto& config : configVector)
			config = { XR_TYPE_VIEW_CONFIGURATION_VIEW };
		CheckXr(xrEnumerateViewConfigurationViews(instance, systemId,
			XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, configCount, &configCount, configVector.data()),
			"xrEnumerateViewConfigurationViews(list)");

		std::array<XrViewConfigurationView, 2> configs{ configVector[0], configVector[1] };
		const XrEnvironmentBlendMode blendMode = ChooseBlendMode(instance, systemId);
		SharedWriter shared;

		bool exitRequested = false;
		bool sessionRunning = false;
		XrSessionState sessionState = XR_SESSION_STATE_UNKNOWN;

		std::cout << "Pose bridge running. Start OutRun 2006 with [VR] Enabled=true.\n";
		std::cout << "F10 recenters head tracking in game. Ctrl+C closes this host.\n";

		while (!exitRequested)
		{
			XrEventDataBuffer event{ XR_TYPE_EVENT_DATA_BUFFER };
			while (xrPollEvent(instance, &event) == XR_SUCCESS)
			{
				if (event.type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED)
				{
					const auto* changed = reinterpret_cast<const XrEventDataSessionStateChanged*>(&event);
					sessionState = changed->state;

					if (sessionState == XR_SESSION_STATE_READY && !sessionRunning)
					{
						XrSessionBeginInfo beginInfo{ XR_TYPE_SESSION_BEGIN_INFO };
						beginInfo.primaryViewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
						CheckXr(xrBeginSession(session, &beginInfo), "xrBeginSession");
						sessionRunning = true;
					}
					else if (sessionState == XR_SESSION_STATE_STOPPING && sessionRunning)
					{
						CheckXr(xrEndSession(session), "xrEndSession");
						sessionRunning = false;
					}
					else if (sessionState == XR_SESSION_STATE_EXITING ||
						sessionState == XR_SESSION_STATE_LOSS_PENDING)
					{
						exitRequested = true;
					}
				}

				event = { XR_TYPE_EVENT_DATA_BUFFER };
			}

			if (exitRequested)
				break;
			if (!sessionRunning)
			{
				Sleep(10);
				continue;
			}

			XrFrameWaitInfo waitInfo{ XR_TYPE_FRAME_WAIT_INFO };
			XrFrameState frameState{ XR_TYPE_FRAME_STATE };
			CheckXr(xrWaitFrame(session, &waitInfo, &frameState), "xrWaitFrame");

			XrFrameBeginInfo frameBegin{ XR_TYPE_FRAME_BEGIN_INFO };
			CheckXr(xrBeginFrame(session, &frameBegin), "xrBeginFrame");

			XrSpaceLocation headLocation{ XR_TYPE_SPACE_LOCATION };
			CheckXr(xrLocateSpace(viewSpace, localSpace, frameState.predictedDisplayTime, &headLocation),
				"xrLocateSpace(VIEW->LOCAL)");

			std::array<XrView, 2> views{};
			for (auto& view : views)
				view = { XR_TYPE_VIEW };
			XrViewState viewState{ XR_TYPE_VIEW_STATE };
			XrViewLocateInfo locateInfo{ XR_TYPE_VIEW_LOCATE_INFO };
			locateInfo.viewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
			locateInfo.displayTime = frameState.predictedDisplayTime;
			locateInfo.space = localSpace;
			std::uint32_t viewCount = 0;
			CheckXr(xrLocateViews(session, &locateInfo, &viewState,
				static_cast<std::uint32_t>(views.size()), &viewCount, views.data()),
				"xrLocateViews");

			shared.Write(headLocation, views, viewCount, configs, sessionState,
				instanceProperties.runtimeName);

			// Milestone 1 owns a real OpenXR session and supplies predicted HMD
			// tracking, but does not submit the game's D3D9 images yet. The next
			// milestone replaces this zero-layer end frame with stereo projection
			// layers backed by the x86 bridge's left/right render targets.
			XrFrameEndInfo frameEnd{ XR_TYPE_FRAME_END_INFO };
			frameEnd.displayTime = frameState.predictedDisplayTime;
			frameEnd.environmentBlendMode = blendMode;
			frameEnd.layerCount = 0;
			frameEnd.layers = nullptr;
			CheckXr(xrEndFrame(session, &frameEnd), "xrEndFrame");
		}

		if (viewSpace != XR_NULL_HANDLE)
			xrDestroySpace(viewSpace);
		if (localSpace != XR_NULL_HANDLE)
			xrDestroySpace(localSpace);
		if (session != XR_NULL_HANDLE)
			xrDestroySession(session);
		if (instance != XR_NULL_HANDLE)
			xrDestroyInstance(instance);
		return 0;
	}
	catch (const std::exception& e)
	{
		std::cerr << "OutRun VR host error: " << e.what() << "\n";
		return 1;
	}
}
