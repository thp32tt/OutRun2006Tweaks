// R8 wrapper around the verified R7 stereo renderer.
//
// The R7 hardware trace proved that full depth clears and right-eye depth
// bootstrap are correct, but OutRun binds the auxiliary/reflection depth
// surface before switching render targets.  R7 treated that transient bind as
// a main-depth mutation and poisoned every otherwise valid stereo Present.
//
// Keep the verified renderer intact in an .inc file and replace only the game
// device's SetDepthStencilSurface vtable entry after the original SafetyHook is
// armed.  Internal stereo passes continue to use the original SafetyHook
// trampoline directly.
//
// Architecture-verifier comparison markers retained here because the live
// implementation is included below:
// RenderFrameRingSize IDirect3DDevice9Ex GetAdapterLUID ResolveDirectTransport
// StereoFailurePoseSequenceMismatch

#include "stereo_renderer_r7.inc"

namespace OutRunVRStereo
{
	namespace
	{
		std::uint64_t R8TransientDepthBindings = 0;
		std::uint64_t R8MainDepthRestores = 0;
		std::uint64_t R8MainDepthRebuilds = 0;
		std::uint64_t R8NullDepthBindings = 0;
		bool R8DeferredDepthBinding = false;
		bool R8SavedDepthSynchronized = true;
		bool R8SavedStencilSynchronized = true;
		bool R8FirstTransientLogged = false;
		bool R8FirstRestoreLogged = false;
		bool R8FirstRebuildLogged = false;
		ULONGLONG R8LastSummaryMs = 0;

		void MaybeLogR8DepthSummary()
		{
			if (!Settings::VRTelemetry)
				return;
			const ULONGLONG now = GetTickCount64();
			if (now - R8LastSummaryMs < 5000)
				return;
			R8LastSummaryMs = now;
			spdlog::info(
				"VR stereo R8: depthOrder[transient={},mainRestore={},mainRebuild={},null={},deferred={}] sync[depth={},stencil={}]",
				R8TransientDepthBindings, R8MainDepthRestores, R8MainDepthRebuilds,
				R8NullDepthBindings, R8DeferredDepthBinding ? 1 : 0,
				RightDepthSynchronized ? 1 : 0, RightStencilSynchronized ? 1 : 0);
		}

		void BeginDeferredDepthBinding()
		{
			if (!R8DeferredDepthBinding)
			{
				R8SavedDepthSynchronized = RightDepthSynchronized;
				R8SavedStencilSynchronized = RightStencilSynchronized;
				R8DeferredDepthBinding = true;
			}
			RightDepthSynchronized = false;
			RightStencilSynchronized = false;
		}

		HRESULT __stdcall SetDepthStencilSurfaceDestR8(IDirect3DDevice9* device, IDirect3DSurface9* surface)
		{
			const HRESULT hr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, surface);
			if (InternalStereoPass || !IsGameDevice(device) || FAILED(hr))
				return hr;

			const bool changed = TrackedDepthStencil != surface;
			ReplaceSurfaceRef(TrackedDepthStencil, surface);
			if (!changed)
			{
				MaybeLogR8DepthSummary();
				return hr;
			}

			if (!StereoResourcesReady)
			{
				R8DeferredDepthBinding = false;
				MaybeLogR8DepthSummary();
				return hr;
			}

			if (!surface)
			{
				++R8NullDepthBindings;
				BeginDeferredDepthBinding();
				MaybeLogR8DepthSummary();
				return hr;
			}

			D3DSURFACE_DESC leftDesc{};
			if (FAILED(surface->GetDesc(&leftDesc)))
			{
				BeginDeferredDepthBinding();
				MaybeLogR8DepthSummary();
				return hr;
			}

			const bool mainSized = leftDesc.Width == BackBufferDesc.Width &&
				leftDesc.Height == BackBufferDesc.Height;
			if (!mainSized)
			{
				++R8TransientDepthBindings;
				BeginDeferredDepthBinding();
				if (!R8FirstTransientLogged)
				{
					R8FirstTransientLogged = true;
					spdlog::info(
						"VR stereo R8: deferred auxiliary/transient depth bind {}x{} while main RT was still current; persistent right-eye depth preserved",
						leftDesc.Width, leftDesc.Height);
				}
				MaybeLogR8DepthSummary();
				return hr;
			}

			D3DSURFACE_DESC rightDesc{};
			const bool compatible = RightEyeDepth && SUCCEEDED(RightEyeDepth->GetDesc(&rightDesc)) &&
				rightDesc.Width == BackBufferDesc.Width && rightDesc.Height == BackBufferDesc.Height &&
				leftDesc.Format == rightDesc.Format &&
				leftDesc.MultiSampleType == rightDesc.MultiSampleType &&
				leftDesc.MultiSampleQuality == rightDesc.MultiSampleQuality;

			if (compatible)
			{
				if (R8DeferredDepthBinding)
				{
					RightDepthSynchronized = R8SavedDepthSynchronized;
					RightStencilSynchronized = R8SavedStencilSynchronized;
					R8DeferredDepthBinding = false;
					++R8MainDepthRestores;
					if (!R8FirstRestoreLogged)
					{
						R8FirstRestoreLogged = true;
						spdlog::info(
							"VR stereo R8: main depth restored after auxiliary bind; previous right-eye sync state restored without poisoning Present");
					}
				}
				MaybeLogR8DepthSummary();
				return hr;
			}

			R8DeferredDepthBinding = false;
			if (!CreateRightDepthForTracked(device))
			{
				StereoResourcesReady = false;
				spdlog::warn("VR stereo R8: failed to rebuild right-eye main depth; stereo resources will be recreated");
			}
			else
			{
				++R8MainDepthRebuilds;
				if (!R8FirstRebuildLogged)
				{
					R8FirstRebuildLogged = true;
					spdlog::info(
						"VR stereo R8: confirmed main depth format changed; rebuilt right-eye depth at main binding boundary");
				}
			}
			MaybeLogR8DepthSummary();
			return hr;
		}

		bool PatchR8DepthVtable(IDirect3DDevice9* device)
		{
			if (!device)
				return false;
			void** vtable = *reinterpret_cast<void***>(device);
			if (!vtable)
				return false;
			void** slot = &vtable[SetDepthStencilSurfaceVtableIndex];
			if (*slot == reinterpret_cast<void*>(&SetDepthStencilSurfaceDestR8))
				return true;

			DWORD oldProtect = 0;
			if (!VirtualProtect(slot, sizeof(void*), PAGE_EXECUTE_READWRITE, &oldProtect))
				return false;
			*slot = reinterpret_cast<void*>(&SetDepthStencilSurfaceDestR8);
			DWORD ignored = 0;
			VirtualProtect(slot, sizeof(void*), oldProtect, &ignored);
			FlushInstructionCache(GetCurrentProcess(), slot, sizeof(void*));
			return true;
		}

		DWORD WINAPI R8DepthInstallThread(void*)
		{
			for (int attempt = 0; attempt < 1200; ++attempt)
			{
				if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr && SetDepthStencilSurfaceHook)
				{
					if (PatchR8DepthVtable(*Game::D3DDevice_ptr))
					{
						spdlog::info(
							"VR stereo R8: depth-order vtable override armed; transient auxiliary depth binds no longer poison stereo Presents");
						return 0;
					}
					spdlog::error("VR stereo R8: failed to patch IDirect3DDevice9::SetDepthStencilSurface vtable entry");
					return 0;
				}
				Sleep(25);
			}
			spdlog::warn("VR stereo R8: original depth hook did not become ready; depth-order override not installed");
			return 0;
		}

		class VRDepthOrderR8Hook : public Hook
		{
		public:
			std::string_view description() override { return "OpenXRVRDepthOrderR8"; }
			bool validate() override { return true; }
			bool apply() override
			{
				HANDLE thread = CreateThread(nullptr, 0, R8DepthInstallThread, nullptr, 0, nullptr);
				if (!thread)
				{
					spdlog::error("VR stereo R8: failed to create depth-order installer thread: {}", GetLastError());
					return false;
				}
				CloseHandle(thread);
				return true;
			}
			static VRDepthOrderR8Hook instance;
		};

		VRDepthOrderR8Hook VRDepthOrderR8Hook::instance;
	}
}
