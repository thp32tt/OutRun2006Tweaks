#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <shellapi.h>
#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include <imgui.h>
#include <backends/imgui_impl_win32.h>
#include <backends/imgui_impl_dx9.h>
#include "overlay.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/core/r23_eye_extent_api.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace Settings
{
	Setting<bool> OverlayEnabled{ "Overlay", "Enabled", true,
		"Enables the OutRun2006Tweaks overlay." };
	Setting<bool> WindowedHideMouseCursor{ "Window", "WindowedHideMouseCursor", true,
		"Hides mouse cursor while game window is active." };
}

bool overlayInited = false;
bool overlayActive = false;

struct CUSTOMVERTEX
{
	FLOAT x, y, z, rhw;
	D3DCOLOR color;
};
#define CUSTOMFVF (D3DFVF_XYZRHW | D3DFVF_DIFFUSE)

IDirect3DVertexBuffer9* LetterboxVertex = nullptr;
// The menu bars are a source-backbuffer-sized GPU buffer, not a fixed game
// resolution. Game resolution changes can occur before the next temporary
// resource Reset callback, so never replay geometry from the previous size.
IDirect3DDevice9* LetterboxRasterDevice = nullptr; // borrowed, never AddRef
float LetterboxRasterWidth = 0.0f;
float LetterboxRasterHeight = 0.0f;

void CreateLetterboxVertex()
{
	// The menu is authored for a 4:3 source. Draw side bars only when the
	// current source backbuffer is wider; 4:3 and portrait XR/mirror sources
	// have no valid left/right bar geometry. A Reset may invalidate all of the
	// previous dimensions and the old vertex buffer.
	if (LetterboxVertex)
	{
		LetterboxVertex->Release();
		LetterboxVertex = nullptr;
	}
	LetterboxRasterDevice = nullptr;
	LetterboxRasterWidth = 0.0f;
	LetterboxRasterHeight = 0.0f;
	IDirect3DDevice9* d3ddev = Game::D3DDevice();
	if (!d3ddev || !Game::screen_resolution)
		return;

	const float sourceWidth = float(Game::screen_resolution->x);
	const float sourceHeight = float(Game::screen_resolution->y);
	if (!std::isfinite(sourceWidth) || !std::isfinite(sourceHeight) ||
		sourceWidth < 1.0f || sourceHeight < 1.0f)
		return;
	const float contentWidth = sourceHeight * (4.0f / 3.0f);
	if (!std::isfinite(contentWidth))
		return;
	// No GPU bars are needed for a 4:3/portrait source. Cache that successful
	// empty result, but defer caching a widescreen size/device until its VB
	// has actually been created, locked, filled and unlocked. Otherwise a
	// transient D3D9Ex Reset allocation failure permanently hides menu bars.
	if (sourceWidth <= contentWidth)
	{
		LetterboxRasterDevice = d3ddev;
		LetterboxRasterWidth = sourceWidth;
		LetterboxRasterHeight = sourceHeight;
		return;
	}
	const float borderWidth = (sourceWidth - contentWidth) * 0.5f + 0.5f;
	if (!std::isfinite(borderWidth) || borderWidth >= sourceWidth * 0.5f)
		return;
	const float screenWidth = sourceWidth + 0.5f;
	const float screenHeight = sourceHeight + 0.5f;
	CUSTOMVERTEX vertices[]
	{
		{ -0.5f, -0.5f, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ borderWidth, -0.5f, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ -0.5f, screenHeight, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ borderWidth, screenHeight, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ (screenWidth - borderWidth), -0.5f, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ screenWidth, -0.5f, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ (screenWidth - borderWidth), screenHeight, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) },
		{ screenWidth, screenHeight, 0.0f, 1.0f, D3DCOLOR_XRGB(0, 0, 0) }
	};

	IDirect3DVertexBuffer9* candidate = nullptr;
	if (FAILED(d3ddev->CreateVertexBuffer(sizeof(vertices), 0, CUSTOMFVF,
		// D3D9Ex rejects D3DPOOL_MANAGED. DEFAULT works on classic D3D9
		// and Ex; the game's temporary-resource release hook owns Reset.
		D3DPOOL_DEFAULT, &candidate, nullptr)) || !candidate)
		return;
	void* mapped = nullptr;
	if (FAILED(candidate->Lock(0, 0, &mapped, 0)) || !mapped)
	{
		candidate->Release();
		return;
	}
	memcpy(mapped, vertices, sizeof(vertices));
	if (FAILED(candidate->Unlock()))
	{
		candidate->Release();
		return;
	}
	LetterboxVertex = candidate;
	// Only completed buffers are cached. Create/Lock/Unlock failures leave
	// the cache empty, so the next valid same-size menu frame can retry.
	LetterboxRasterDevice = d3ddev;
	LetterboxRasterWidth = sourceWidth;
	LetterboxRasterHeight = sourceHeight;
}

class D3DHooks : public Hook
{
	inline static SafetyHookMid midhook_d3dinit{};
	static void D3DInit(SafetyHookContext& ctx)
	{
		if (ctx.eax == 0)
			return; // InitDirectX returned false

		CreateLetterboxVertex();

		if (Settings::OverlayEnabled)
		{
			Overlay::init_imgui();

			// Setup Platform/Renderer backends
			ImGui_ImplWin32_Init(Game::GameHwnd());
			ImGui_ImplDX9_Init(Game::D3DDevice());

			overlayInited = true;
		}
	}

	inline static SafetyHookMid midhook_d3dendscene{};
	static void D3DEndScene(SafetyHookContext& ctx)
	{
		// A live source resolution switch (e.g. 21:9 -> 4:3 -> 16:9)
		// does not necessarily pass through the game's temporary resource
		// Reset hooks. Recreate menu bars once on an actual size/device change;
		// never draw an old widescreen rectangle during a portrait/invalid
		// publication gap. Gameplay without forced bars avoids this work.
		IDirect3DDevice9* currentDevice = Game::D3DDevice();
		const auto* currentSize = Game::screen_resolution;
		const bool validSource = currentDevice && currentSize &&
			std::isfinite(currentSize->x) && std::isfinite(currentSize->y) &&
			currentSize->x >= 1.0f && currentSize->y >= 1.0f;
		if (Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 &&
			(!Game::is_in_game() || Settings::UILetterboxing == 2) &&
			validSource &&
			(currentDevice != LetterboxRasterDevice ||
			 currentSize->x != LetterboxRasterWidth ||
			 currentSize->y != LetterboxRasterHeight))
			CreateLetterboxVertex();

		if (Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex &&
			validSource && currentDevice == LetterboxRasterDevice &&
			currentSize->x == LetterboxRasterWidth &&
			currentSize->y == LetterboxRasterHeight)
		{
			IDirect3DDevice9* d3ddev = Game::D3DDevice();

			// Only show letterboxing if not in game, or UILetterboxing is 2.
			// The game can leave scissor/stencil clipping enabled after its last
			// menu draw. Do not let that clip the 4:3 sidebars, and restore the
			// exact game state before ImGui or the next scene. Missing GetRenderState
			// evidence skips only the sidebars, never the F11 overlay below.
			DWORD prevScissorTest = FALSE;
			DWORD prevStencilEnable = FALSE;
			DWORD prevAlphaTest = FALSE;
			DWORD prevColorWrite = 0;
			DWORD prevFogEnable = FALSE;
			DWORD prevFillMode = D3DFILL_SOLID;
			DWORD prevClipPlaneEnable = 0;
			// The game's last menu pass may leave a centred 4:3 viewport.
			// Scissor/stencil overrides cannot make the side rails visible
			// outside that viewport. Capture it before drawing any opaque bars.
			D3DVIEWPORT9 previousViewport{};
			D3DVIEWPORT9 barViewport{};
			bool overrideViewport = false;
			const bool validViewportSize =
				currentSize->x <= 16384.0f && currentSize->y <= 16384.0f &&
				std::floor(currentSize->x) == currentSize->x &&
				std::floor(currentSize->y) == currentSize->y;
			bool clipStateReady =
				(!Game::is_in_game() || Settings::UILetterboxing == 2) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_SCISSORTESTENABLE, &prevScissorTest)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_STENCILENABLE, &prevStencilEnable)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_ALPHATESTENABLE, &prevAlphaTest)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_COLORWRITEENABLE, &prevColorWrite)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_FOGENABLE, &prevFogEnable)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_FILLMODE, &prevFillMode)) &&
				SUCCEEDED(d3ddev->GetRenderState(D3DRS_CLIPPLANEENABLE, &prevClipPlaneEnable)) &&
				validViewportSize &&
				SUCCEEDED(d3ddev->GetViewport(&previousViewport));
			if (clipStateReady)
			{
				barViewport = previousViewport; // Keep the game's Z range.
				barViewport.X = 0;
				barViewport.Y = 0;
				barViewport.Width = static_cast<DWORD>(currentSize->x);
				barViewport.Height = static_cast<DWORD>(currentSize->y);
				overrideViewport =
					previousViewport.X != barViewport.X ||
					previousViewport.Y != barViewport.Y ||
					previousViewport.Width != barViewport.Width ||
					previousViewport.Height != barViewport.Height;
				// A failed full-viewport transition must not draw clipped bars,
				// and must never prevent the following F11 ImGui frame.
				if (overrideViewport)
					clipStateReady = SUCCEEDED(d3ddev->SetViewport(&barViewport));
			}
			if (clipStateReady)
			{
				// This runs after SceneControl has finished, so anything left set here carries
				// into the next frame. The game's material layer keeps its own copies of device
				// state (st_prevTexIdx, texture_color_op and friends) and skips reapplying a
				// state it believes is already set, so every change below has to be put back.
				DWORD prevCullMode = D3DCULL_CCW;
				DWORD prevAlphaBlend = FALSE;
				DWORD prevZEnable = D3DZB_TRUE;
				DWORD prevLighting = TRUE;
				DWORD prevColorOp = D3DTOP_MODULATE;
				DWORD prevAlphaOp = D3DTOP_SELECTARG1;
				// Fixed-function FVF is a separate restorable input mode from
				// custom vertex declarations. Save both before drawing sidebars.
				DWORD prevFVF = 0;
				const bool hadFixedFVF =
					SUCCEEDED(d3ddev->GetFVF(&prevFVF)) && prevFVF != 0;
				UINT prevStreamOffset = 0;
				UINT prevStreamStride = 0;

				IDirect3DBaseTexture9* prevTexture = nullptr;
				IDirect3DVertexShader9* prevVertexShader = nullptr;
				IDirect3DPixelShader9* prevPixelShader = nullptr;
				IDirect3DVertexDeclaration9* prevVertexDecl = nullptr;
				IDirect3DVertexBuffer9* prevStreamData = nullptr;

				d3ddev->GetRenderState(D3DRS_CULLMODE, &prevCullMode);
				d3ddev->GetRenderState(D3DRS_ALPHABLENDENABLE, &prevAlphaBlend);
				d3ddev->GetRenderState(D3DRS_ZENABLE, &prevZEnable);
				d3ddev->GetRenderState(D3DRS_LIGHTING, &prevLighting);
				d3ddev->GetTextureStageState(0, D3DTSS_COLOROP, &prevColorOp);
				d3ddev->GetTextureStageState(0, D3DTSS_ALPHAOP, &prevAlphaOp);
				d3ddev->GetTexture(0, &prevTexture);
				d3ddev->GetVertexShader(&prevVertexShader);
				d3ddev->GetPixelShader(&prevPixelShader);
				d3ddev->GetVertexDeclaration(&prevVertexDecl);
				d3ddev->GetStreamSource(0, &prevStreamData, &prevStreamOffset, &prevStreamStride);

				// The opaque bars must not inherit the last sprite's stencil,
				// scissor, alpha test or disabled colour channels. A prior alpha
				// compare can discard even the XRGB-black sidebars; a zero colour
				// mask makes both triangles invisible. Restore every state below.
				d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);
				d3ddev->SetRenderState(D3DRS_STENCILENABLE, FALSE);
				d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);
				d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE,
					D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |
					D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA);
				// Fixed-function black rails must be solid and fog-free even when
				// the previous world pass left wireframe or coloured fog enabled.
				// The two values are restored with the other captured scene states.
				d3ddev->SetRenderState(D3DRS_FOGENABLE, FALSE);
				d3ddev->SetRenderState(D3DRS_FILLMODE, D3DFILL_SOLID);
				d3ddev->SetRenderState(D3DRS_CLIPPLANEENABLE, 0);
				// Borders get culled without this
				d3ddev->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);

				// A shader left bound by the scene would shade the borders instead of the
				// fixed-function path, and would ignore the stage state set up below
				d3ddev->SetVertexShader(nullptr);
				d3ddev->SetPixelShader(nullptr);

				// Seems these SetRenderState/SetTexture calls are needed for DGVoodoo to render letterbox while imgui is active
				// DXVK/D3D9 seem to work fine without them
				{
					// Set render states
					d3ddev->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
					d3ddev->SetRenderState(D3DRS_ZENABLE, D3DZB_FALSE);
					d3ddev->SetRenderState(D3DRS_LIGHTING, FALSE);

					// Set texture stage states to avoid any texture influence
					d3ddev->SetTexture(0, NULL);
					d3ddev->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_DISABLE);
					d3ddev->SetTextureStageState(0, D3DTSS_ALPHAOP, D3DTOP_DISABLE);
				}

				// Set FVF and stream source
				d3ddev->SetFVF(CUSTOMFVF);
				d3ddev->SetStreamSource(0, LetterboxVertex, 0, sizeof(CUSTOMVERTEX));

				// Draw left border
				d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);

				// Draw right border
				d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);

				// Restore before all subsequent game/ImGui draws; a latched mask
				// from the previous scene must neither clip the bars nor be lost.
				d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, prevScissorTest);
				d3ddev->SetRenderState(D3DRS_STENCILENABLE, prevStencilEnable);
				d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, prevAlphaTest);
				d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE, prevColorWrite);
				d3ddev->SetRenderState(D3DRS_FOGENABLE, prevFogEnable);
				d3ddev->SetRenderState(D3DRS_FILLMODE, prevFillMode);
				d3ddev->SetRenderState(D3DRS_CLIPPLANEENABLE, prevClipPlaneEnable);
				d3ddev->SetRenderState(D3DRS_CULLMODE, prevCullMode);
				d3ddev->SetRenderState(D3DRS_ALPHABLENDENABLE, prevAlphaBlend);
				d3ddev->SetRenderState(D3DRS_ZENABLE, prevZEnable);
				d3ddev->SetRenderState(D3DRS_LIGHTING, prevLighting);
				d3ddev->SetTextureStageState(0, D3DTSS_COLOROP, prevColorOp);
				d3ddev->SetTextureStageState(0, D3DTSS_ALPHAOP, prevAlphaOp);

				// A Get on a resource adds a reference, so each one is released once it's
				// back on the device. Restore the actual preceding vertex input:
				// setting a null vertex declaration does NOT restore a previous
				// fixed-function FVF on D3D9Ex. Keep custom declarations intact.
				d3ddev->SetTexture(0, prevTexture);
				if (prevTexture)
					prevTexture->Release();

				d3ddev->SetVertexShader(prevVertexShader);
				if (prevVertexShader)
					prevVertexShader->Release();

				d3ddev->SetPixelShader(prevPixelShader);
				if (prevPixelShader)
					prevPixelShader->Release();

				if (hadFixedFVF)
					d3ddev->SetFVF(prevFVF);
				else
					d3ddev->SetVertexDeclaration(prevVertexDecl);
				if (prevVertexDecl)
					prevVertexDecl->Release();

				d3ddev->SetStreamSource(0, prevStreamData, prevStreamOffset, prevStreamStride);
				if (prevStreamData)
					prevStreamData->Release();
				// Restore exact X/Y/width/height and Z range for next game pass.
				if (overrideViewport)
					d3ddev->SetViewport(&previousViewport);
			}
		}

		if (overlayInited)
		{
			// ImGui draws into the desktop-sized D3D9 backbuffer before the
			// asymmetric portrait XR eye transfer. A source-aspect-sized font
			// is visually reduced by that transfer. When the F11 shell is open
			// in actual VR gameplay, create larger glyphs *at rasterisation*;
			// never bitmap-upscale ImGui's existing font atlas. Keep the game
			// sprite HUD, menu, native 2D desktop UI and world passes untouched.
			float vrFontMultiplier = 1.0f;
			if (overlayActive && Game::is_vr_gameplay_presentation() &&
				Game::screen_resolution &&
				Game::screen_resolution->x > 0 &&
				Game::screen_resolution->y > 0)
			{
				// A short-lived XR publication gap is not an instruction to
				// shrink the already-rasterised F11 shell to desktop density.
				// Keep the last finite VR atlas until BOTH eye extents can be
				// sampled again. Outside gameplay/F11 the 1.0 default above
				// still restores the desktop font on the next EndScene.
				vrFontMultiplier = std::clamp(
					Overlay::VrFontMultiplier, 1.0f, 3.0f);
				std::uint32_t lw = 0, lh = 0, rw = 0, rh = 0;
				if (OutRunVRStereo::R23TryGetPublishedEyeExtent(0, lw, lh) &&
					OutRunVRStereo::R23TryGetPublishedEyeExtent(1, rw, rh) &&
					lw >= 640u && lh >= 480u && rw >= 640u && rh >= 480u &&
					// Eye extents are published separately during a VDXR resize.
					// Never mix one new eye with one stale eye to rebuild the
					// full Segoe/DX9 atlas. Retain the last VR atlas until both
					// dimensions converge; this is a transient frame, not a
					// real source/eye aspect change.
					std::fabs(static_cast<float>(lw) - static_cast<float>(rw)) <=
						0.10f * static_cast<float>((std::max)(lw, rw)) &&
					std::fabs(static_cast<float>(lh) - static_cast<float>(rh)) <=
						0.10f * static_cast<float>((std::max)(lh, rh)))
				{
					const float sourceAspect = static_cast<float>(
						Game::screen_resolution->x) /
						static_cast<float>(Game::screen_resolution->y);
					const float eyeAspect =
						0.5f * (static_cast<float>(lw) / lh +
							static_cast<float>(rw) / rh);
					// Preserve source-space glyph pixels when a lower-height
					// mirror is expanded to a taller XR eye. Aspect correction
					// alone misses 1080p/768p source -> 2688p eye cases.
					// This is F11-only atlas raster density, not a change to
					// the game's HUD projection or desktop ImGui scaling.
					const float eyePixelScale =
						(0.5f * (static_cast<float>(lh) + static_cast<float>(rh))) /
						static_cast<float>(Game::screen_resolution->y);
					const float factor =
						(std::max)(sourceAspect / eyeAspect, eyePixelScale);
					if (std::isfinite(factor) && factor > 0.0f)
					{
						const float stepped = std::clamp(
							std::ceil(factor * 4.0f) * 0.25f, 1.0f, 3.0f);
						const float previous = std::clamp(
							Overlay::VrFontMultiplier, 1.0f, 3.0f);
						// A rounded-up bucket changes at every quarter-aspect
						// boundary. Tiny VDXR source/eye extent oscillations at
						// that boundary otherwise rebuild Segoe UI + the entire
						// DX9 font texture every other EndScene (a frame stall).
						// Use a symmetric 0.03 aspect dead band while the F11
						// shell is open; real resize/recenter changes still
						// cross the band and update the atlas immediately.
						constexpr float kFontAspectHysteresis = 0.03f;
						if (stepped > previous &&
							factor <= previous + kFontAspectHysteresis)
							vrFontMultiplier = previous;
						else if (stepped < previous &&
							factor >= previous - 0.25f - kFontAspectHysteresis &&
							factor > 1.0f)
							vrFontMultiplier = previous;
						else
							vrFontMultiplier = stepped;
					}
				}
			}
			// Quantised quarter-steps prevent continuous atlas churn when the
			// OpenXR host updates aspect hints or the window is reset/resized.
			// Reset and menu/desktop transitions return to the original atlas.
			if (Overlay::VrFontMultiplier != vrFontMultiplier)
			{
				Overlay::VrFontMultiplier = vrFontMultiplier;
				Overlay::FontsDirty = true;
			}
			// A new atlas needs a new font texture. Dropping the device objects
			// here leaves ImGui_ImplDX9_NewFrame to build them again below, and
			// happens between frames where changing the atlas is safe.
			if (Overlay::FontsDirty)
			{
				Overlay::rebuild_fonts();
				ImGui_ImplDX9_InvalidateDeviceObjects();
			}

			ImGui_ImplDX9_NewFrame();
			ImGui_ImplWin32_NewFrame();
			overlayActive = Overlay::render();
			ImGui::Render();

			// In gameplay the VR draw hooks own main-backbuffer 2D placement.
			// The F11 Tweaks shell is external ImGui UI, not a game sprite producer:
			// give it explicit SCREEN_OVERLAY_2D ownership so R30 applies the
			// established binocular common-ray/FOV correction. Keep front-end/menu
			// rendering untouched, where the user-observed overlay is already correct.
			if (overlayActive && Game::is_vr_gameplay_presentation())
			{
				OutRunVR::GameSemantic::ScopedExternalOverlaySemantic semantic(
					OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D);
				ImGui_ImplDX9_RenderDrawData(ImGui::GetDrawData());
			}
			else
			{
				ImGui_ImplDX9_RenderDrawData(ImGui::GetDrawData());
			}
		}
	}

	inline static SafetyHookMid midhook_d3dTemporariesRelease{};
	static void D3DTemporariesRelease(SafetyHookContext& ctx)
	{
		if (overlayInited)
			ImGui_ImplDX9_InvalidateDeviceObjects();

		if (LetterboxVertex)
		{
			LetterboxVertex->Release();
			LetterboxVertex = nullptr;
		}
		LetterboxRasterDevice = nullptr;
		LetterboxRasterWidth = 0.0f;
		LetterboxRasterHeight = 0.0f;
	}

	inline static SafetyHookMid midhook_d3dTemporariesCreate{};
	static void D3DTemporariesCreate(SafetyHookContext& ctx)
	{
		if (overlayInited)
			ImGui_ImplDX9_CreateDeviceObjects();

		CreateLetterboxVertex();
	}

public:
	std::string_view description() override
	{
		return "D3DHooks";
	}

	bool validate() override
	{
		return true;
	}

	void declare_settings() override
	{
		Settings::OverlayEnabled.needs_restart();
		Settings::OverlayEnabled.hidden(true);
	}

	bool apply() override
	{
		constexpr int InitDirectX_CallerResult_Addr = 0x1775E;
		constexpr int Direct3D_EndScene_CallerAddr = 0x17D4E;
		constexpr int D3D_ReleaseTemporaries_Addr = 0x17970;
		constexpr int D3D_CreateTemporaries_Addr = 0x17A20;

		midhook_d3dinit = safetyhook::create_mid(Module::exe_ptr(InitDirectX_CallerResult_Addr), D3DInit);
		midhook_d3dendscene = safetyhook::create_mid(Module::exe_ptr(Direct3D_EndScene_CallerAddr), D3DEndScene);

		midhook_d3dTemporariesRelease = safetyhook::create_mid(Module::exe_ptr(D3D_ReleaseTemporaries_Addr), D3DTemporariesRelease);
		midhook_d3dTemporariesCreate = safetyhook::create_mid(Module::exe_ptr(D3D_CreateTemporaries_Addr), D3DTemporariesCreate);

		Overlay::init();

		return !!midhook_d3dinit && !!midhook_d3dendscene;
	}

	static D3DHooks instance;
};
D3DHooks D3DHooks::instance;

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

class WndprocHook : public Hook
{
	const static int WndProc_Addr = 0x17F90;

	inline static SafetyHookInline dest_orig = {};
	static LRESULT __stdcall destination(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
	{
		// The gameplay window hides its cursor, but the F11 ImGui shell must
		// restore a visible pointer even after an activation/focus transition.
		if (overlayActive && msg == WM_SETCURSOR && LOWORD(lParam) == HTCLIENT)
		{
			SetCursor(LoadCursorA(nullptr, IDC_ARROW));
			return TRUE;
		}
		if (ImGui_ImplWin32_WndProcHandler(hwnd, msg, wParam, lParam))
			return 1;

		if (Settings::WindowedHideMouseCursor && !overlayActive)
		{
			if (msg == WM_SETFOCUS || (msg == WM_ACTIVATE && LOWORD(wParam) != WA_INACTIVE))
			{
				ShowCursor(false);
			}
		}

		if (msg == WM_ERASEBKGND) // erase window to white during device reset
		{
			RECT rect;
			GetClientRect(hwnd, &rect);
			HBRUSH brush = CreateSolidBrush(RGB(0xFF, 0xFF, 0xFF));
			FillRect((HDC)wParam, &rect, brush);
			DeleteObject(brush);
			return 1;
		}

		// Other message handling
		return dest_orig.stdcall<LRESULT>(hwnd, msg, wParam, lParam);
	}

public:
	std::string_view description() override
	{
		return "WndprocHook";
	}

	bool validate() override
	{
		return true;
	}

	bool apply() override
	{
		dest_orig = safetyhook::create_inline(Module::exe_ptr(WndProc_Addr), destination);
		return !!dest_orig;
	}

	static WndprocHook instance;
};
WndprocHook WndprocHook::instance;
