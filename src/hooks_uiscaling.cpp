#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/hud_semantics.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace Settings
{
	extern Setting<bool> VREnabled;
    extern Setting<bool> VRTelemetry;
	Setting<int> UIScalingMode{ "Graphics", "UIScalingMode", 1,
		"Adjusts the UI scaling applied by the game.",
		{ "Vanilla, stretches to screen ratio", "Scaled UI, no stretching (Outrun Online Arcade)",
		  "Centered 4:3 UI" } };
	Setting<int> UILetterboxing{ "Graphics", "UILetterboxing", 1,
		"Adds 4:3 letterboxing to game menus, to address graphical issues outside of the menus 4:3 display. "
		"Only used when UIScalingMode isn't set to Vanilla.",
		{ "Disable all letterboxing", "Letterbox menus only, disabled when in-game",
		  "Always letterbox (only use with Centered 4:3 UI)" } };
}

enum class ScalingMode
{
	Vanilla,
	OnlineArcade,
	KeepCentered,
	Other
};

#define SCREEN_ONE_THIRD 213
#define SCREEN_TWO_THIRD 426

class UIScaling : public Hook
{
	const static int D3DXMatrixTransformation2D_Addr = 0x39400;
	const static int draw_sprite_custom_matrix_mid_Addr = 0x2A556;
	const static int Calc3D2D_Addr = 0x49940;

	const static int NaviPub_Disp_SpriteScaleEnable_Addr = 0xBEB31;
	const static int NaviPub_Disp_SpriteScaleEnable2_Addr = 0xBEDBE;
	const static int NaviPub_Disp_SpriteScaleDisable_Addr = 0xBEDE0;
	const static int NaviPub_Disp_SpriteScaleDisable2_Addr = 0xBEE21;
	const static int drawFootage_caller_Addr = 0x293F3;
	const static int draw_sprite_custom_matrix_multi__case2_Addr = 0x2B1E2;
	const static int draw_sprite_custom_matrix_multi__case3_Addr = 0x2B53E;
	const static int draw_sprite_custom_matrix_multi__case4_Addr = 0x2BB2F;

	// sub_4BAD20 draws the 1st/2nd/3rd position markers above rival cars. It
	// projects the car position to screen, then rounds it down to a whole pixel
	// of the game's 640x480 coordinate space. That space is stretched to fill
	// the display, so a single pixel of it spans several real ones and the
	// marker visibly steps as it moves.
	//
	// RankMarker_Truncate is the address just past both cvttss2si, where the
	// values from before the rounding are still on the stack at these offsets.
	const static int RankMarker_Truncate = 0xBB046;
	const static int RankMarker_StackX = 0x40;
	const static int RankMarker_StackY = 0x44;

	// Addresses of the draw calls sub_4BAD20 makes. sprani_play_ae_auth_alpha
	// and put_clip_sprite are both used throughout the game, so each call site
	// is redirected on its own rather than hooking either function.
	static constexpr int RankMarker_SpraniCalls[] = { 0xBB0FB, 0xBB133, 0xBB16C, 0xBB1A5 };
	static constexpr int RankMarker_ClipSpriteCalls[] = { 0xBB21F, 0xBB241, 0xBB271, 0xBB2BC, 0xBB2D0 };
	static constexpr int OptionArrow_ClipSpriteCalls[] = {
		0xE358B, 0xE35A3, 0xE35CC, 0xE35F7,
		0xE481B, 0xE4833, 0xE485C, 0xE4887,
		0xEC24C, 0xEC277, 0xED4D4, 0xED7A3
	};
	static constexpr int ExactScreenHud_ClipSpriteCalls[] = {
		// Existing R65-R74/R73-era menu/result/control bridges.
		0x460F1, 0x463D6, 0x46410, 0x97BB7, 0x97DA7,
		// Canonical EXE direct calls proven SCREEN_HUD by the static HUD map.
		0xBDB0E, 0xBDB2D, 0xBDB4C, 0xBDB8E,
		0xBE311, 0xBE343, 0xBE3E3, 0xBE424, 0xBE45D
	};
	static constexpr int ExactScreenHudRight_ClipSpriteCalls[] = {
		// DispRank.
		0xB9F3A, 0xB9F5E, 0xB9F81, 0xB9FD0,
		0xB9FFC, 0xBA01E, 0xBA035, 0xBA052,
		// C2C warnings / slipstream.
		0xBD32E, 0xBD397, 0xBD414, 0xBD472,
		// TimeAttack/result records: preserve the original right-side spacing.
		0xBE5CD, 0xBE603, 0xBE633, 0xBE66D, 0xBE690,
		0xBE6B5, 0xBE6D5, 0xBE7E8, 0xBE802, 0xBE81C,
		0xBE8D8, 0xBE915, 0xBE94A, 0xBE97A, 0xBE9A3
	};
	static constexpr int ExactScreenHudLeft_ClipSpriteCalls[] = {
		// REV/gear calls proven by the canonical EXE HUD map.
		0xB9096, 0xB90B3
	};
	// Canonical NaviPub calls into sub_4BAD20 are screen HUD, even though the
	// same subroutine is also used for vehicle-attached world rank markers.
	static constexpr int RankMarkerSubScreenHudCalls[] = {
		0xBEB98, 0xBED83, 0xBED9E, 0xBEDAE
	};
	inline static thread_local unsigned RankMarkerSubScreenHudDepth = 0;
	// Restored R70 exact producer bridge. The historic BA9D0 text function
	// queues both a direct clip and sprani child at canonical E8 sites. User
	// 5868 runtime hudtrace saw 255 unknown BA... sprani rows. Only explicitly
	// ScreenHud-classified parents may tag these child sprites as ScreenHud.
	static inline SafetyHookInline OutRunHudTextProducerHook{};
	inline static thread_local bool OutRunHudTextScreenHud = false;
	static constexpr int OutRunHudTextProducerRva = 0xBA9D0;
	static constexpr int OutRunHudTextClipCallRva = 0xBAAA0;
	static constexpr int OutRunHudTextSpraniCallRva = 0xBAAEA;
	static constexpr int RivalMarker_SpraniCall = 0xBB796;
	static constexpr int TextGlyph_PutSpriteCalls[] = { 0x2C808, 0x2C9DB };
	// Canonical EXE Inspector verified first DispRank kind-1 CALL E8->0x29530.
	// This producer is separate from the eight following kind-0 clip sprites.
	static constexpr int DispRankFirstSpraniCall = 0xB9DA6;
	// The original result screen emits a progress/percentage sprite through
	// two separate calls to 0x2D200. Both had their own exact ownership in
	// the historically validated R74 producer map (canonical EXE SHA pinned).
	// Original R71 3 E8 edges all CALL Sumo_Printf 0x2CDD0; glyph/mask
	// siblings may be queued across priorities without lower glyph tags.
	static constexpr int OutRunStagePrintfCalls[] = {
		0x975EE, 0x97727, 0x977FB
	};
	// Canonical EXE original 0x97xxx source disassembly identified
    // 19 distinct E8 direct calls to sub_4B9200. The 93% GOAL screenshot
    // displays oversized result digits while the separate progress-bar E8
    // calls remain 0x97BE4/0x97DEC -> 0x2D200. Restore the MISSING exact
    // sibling HUD owner at source, never by promoting all generic 2D draws.
    // This group is wholly inside the original 0x97000..0x98000 result
    // presentation code, not world decals or the final static GOAL helpers.
    // The original EXE stage-extension animation uses 0x989xx sprani
    // E8 calls (two explicit 0x2C00B4/B5 sprite identifiers plus a
    // 0x2C006C child), NOT the 0x97xxx result-progress print calls.
    // Own only these three original producers, never general alpha or
    // the completed GOAL display. Confirmed EXE SHA 68ceb386...
    static constexpr int StageExtensionSpraniCalls[] = {
        0x9898E, 0x98A36, 0x98AC6
    };
    // Full original 0x98000 disassembly (SHA-pinned), beyond the sprani:
    // the FIRST original time-extension path calls 0x4973C0 twice and
    // 0x4974E0 once at these precise E8 parents. These are reused text/
    // number print helpers, not the sprani animation itself. If unowned,
    // they can render +TIME as generic head-locked overlay even while
    // the three sprite decorations above are correct.
    static constexpr int StageExtensionPrintCalls[] = {
        0x989AD, 0x98A10, 0x98A89
    };
    static constexpr int ResultTextB9200Calls[] = {
        0x973AF, 0x97422, 0x974D0, 0x97544,
        0x97664, 0x97675, 0x9769E, 0x976B2, 0x976F4,
        0x9784F, 0x9787D, 0x9788E, 0x978B4, 0x978C8, 0x978EC,
        0x97C31, 0x97C57, 0x97E47, 0x97E6D
    };

    static constexpr int ResultProgressCallA = 0x97BE4;
	static constexpr int ResultProgressCallB = 0x97DEC;
	// The GOAL time panel also calls two sprite-producing helpers directly.
	static constexpr int GoalTimeHelperCallA = 0xBEA5A;
	static constexpr int GoalTimeHelperCallB = 0xBEA5F;

	inline static thread_local
		OutRunVR::GameSemantic::ProjectedMarkerInfo RankMarkerProjectedInfo{};
	inline static thread_local
		OutRunVR::GameSemantic::ProjectedMarkerInfo RivalMarkerProjectedInfo{};
	// Calc3D2D is a producer-local datum, not a sticky "last car" cache.
	// Rank state belongs to exactly one sub_4BAD20 invocation; rival state
	// belongs to the next exact 0xBB796 producer and is consumed once.
	inline static thread_local unsigned RankMarkerSubActiveDepth = 0;

	// D3DXMatrixTransformation2D hook allows us to change draw_sprite_custom
	static inline SafetyHookInline D3DXMatrixTransformation2D = {};
	static int __stdcall D3DXMatrixTransformation2D_dest(D3DMATRIX* pOut, D3DXVECTOR2* pScalingCenter, float pScalingRotation,
		D3DXVECTOR2* pScaling, D3DXVECTOR2* pRotationCenter, float Rotation, D3DXVECTOR2* pTranslation)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());

		// D3DX allows optional 2D scaling/translation inputs. During resolution
		// or device reset the game scale may also be invalid. Preserve input
		// values and forward the original call when reprojection is unsafe.
		if ((mode == ScalingMode::KeepCentered ||
		     mode == ScalingMode::OnlineArcade) &&
		    pScaling && pTranslation &&
		    Game::screen_scale && Game::screen_resolution)
		{
			const float sx = Game::screen_scale->x;
			const float sy = Game::screen_scale->y;
			if (std::isfinite(sx) && std::isfinite(sy) &&
			    sx > 1.0e-6f && sy > 1.0e-6f &&
			    std::isfinite(pScaling->x) &&
			    std::isfinite(pScaling->y) &&
			    std::isfinite(pTranslation->x) &&
			    std::isfinite(pTranslation->y) &&
			    std::isfinite(Game::screen_resolution->x) &&
			    std::isfinite(Game::original_resolution.x))
			{
				const float scale = min(sx, sy);
				const float xScale = (pScaling->x / sx) * scale;
				const float yScale = (pScaling->y / sy) * scale;
				const float centeredX =
				    (pTranslation->x / sx) * scale +
				    (Game::screen_resolution->x -
				     Game::original_resolution.x * scale) / 2;
				const float centeredY = (pTranslation->y / sy) * scale;
				// Complete the finite check before mutating any in/out argument.
				if (std::isfinite(xScale) && std::isfinite(yScale) &&
				    std::isfinite(centeredX) && std::isfinite(centeredY))
				{
					pScaling->x = xScale;
					pScaling->y = yScale;
					pTranslation->x = centeredX;
					pTranslation->y = centeredY;
				}
			}
		}

		return D3DXMatrixTransformation2D.stdcall<int>(pOut, pScalingCenter, pScalingRotation, pScaling, pRotationCenter, Rotation, pTranslation);
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_hk = {};
	static void __cdecl draw_sprite_custom_matrix_mid(safetyhook::Context& ctx)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());

		float* g_spriteVertexStream = Module::exe_ptr<float>(0x58B868);
		SPRARGS2* a1 = (SPRARGS2*)ctx.ebx;

		// This midhook owns only the custom sprite draw. During texture
		// teardown/reset, keep the game's original continuation intact but
		// never dereference an absent texture or compute UVs from an invalid
		// mip descriptor. No screen-vertex buffer must be touched on failure.
		if (!g_spriteVertexStream || !a1 || !a1->d3dtexture_ptr_C ||
			!Game::screen_scale)
			return;
		const float screenScaleX = Game::screen_scale->x;
		const float screenScaleY = Game::screen_scale->y;
		if (!std::isfinite(screenScaleX) ||
			!std::isfinite(screenScaleY) ||
			screenScaleX <= 0.0f || screenScaleY <= 0.0f)
			return;
		if ((mode == ScalingMode::KeepCentered ||
			 mode == ScalingMode::OnlineArcade) &&
			(!Game::screen_resolution ||
			 !std::isfinite(Game::screen_resolution->x) ||
			 !std::isfinite(Game::original_resolution.x)))
			return;

		D3DSURFACE_DESC v25{};
		const HRESULT descHr =
			a1->d3dtexture_ptr_C->GetLevelDesc(0, &v25);
		if (FAILED(descHr) || v25.Width == 0 || v25.Height == 0)
			return;
		float v21 = 0.50999999 / (double)v25.Width;
		float v22 = 0.50999999 / (double)v25.Height;

		D3DMATRIX pM;
		memcpy(&pM, &a1->mtx_14, sizeof(pM));

		D3DXVECTOR4 vec;

		D3DXVECTOR4 topLeft{ 0 };
		D3DXVECTOR4 bottomLeft{ 0 };
		D3DXVECTOR4 topRight{ 0 };
		D3DXVECTOR4 bottomRight{ 0 };

		float scaleY = screenScaleY;

		// Multiply by the smallest scale factor
		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			scaleY = min(screenScaleX, screenScaleY);

		// TopLeft
		vec.x = a1->TopLeft_54.x;
		vec.y = a1->TopLeft_54.y;
		vec.z = a1->TopLeft_54.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&topLeft, &vec, &pM);

		g_spriteVertexStream[1] = scaleY * topLeft.y + 0.5;
		g_spriteVertexStream[2] = topLeft.z;
		g_spriteVertexStream[3] = 1.0;
		g_spriteVertexStream[4] = a1->color_4;
		g_spriteVertexStream[5] = v21 + a1->top_9C;
		g_spriteVertexStream[6] = -v22 + a1->left_A0;

		// BottomLeft
		vec.x = a1->BottomLeft_60.x;
		vec.y = a1->BottomLeft_60.y;
		vec.z = a1->BottomLeft_60.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&bottomLeft, &vec, &pM);

		g_spriteVertexStream[8] = scaleY * bottomLeft.y + 0.5;
		g_spriteVertexStream[9] = bottomLeft.z;
		g_spriteVertexStream[0xA] = 1.0;
		g_spriteVertexStream[0xB] = a1->color_4;
		g_spriteVertexStream[0xC] = v21 + a1->top_94;
		g_spriteVertexStream[0xD] = v22 + a1->right_98;

		// TopRight
		vec.x = a1->TopRight_6C.x;
		vec.y = a1->TopRight_6C.y;
		vec.z = a1->TopRight_6C.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&topRight, &vec, &pM);

		g_spriteVertexStream[0xF] = scaleY * topRight.y + 0.5;
		g_spriteVertexStream[0x10] = topRight.z;
		g_spriteVertexStream[0x11] = 1.0;
		g_spriteVertexStream[0x12] = a1->color_4;
		g_spriteVertexStream[0x13] = -v21 + a1->bottom_84;
		g_spriteVertexStream[0x14] = -v22 + a1->left_88;

		// BottomRight
		vec.x = a1->BottomRight_78.x;
		vec.y = a1->BottomRight_78.y;
		vec.z = a1->BottomRight_78.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&bottomRight, &vec, &pM);

		g_spriteVertexStream[0x16] = scaleY * bottomRight.y + 0.5;
		g_spriteVertexStream[0x17] = bottomRight.z;
		g_spriteVertexStream[0x18] = 1.0;
		g_spriteVertexStream[0x19] = a1->color_4;
		g_spriteVertexStream[0x1A] = -v21 + a1->bottom_8C;
		g_spriteVertexStream[0x1B] = v22 + a1->right_90;

		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
		{
			float add = (Game::screen_resolution->x - (Game::original_resolution.x * scaleY)) / 2;

			g_spriteVertexStream[0] = (scaleY * topLeft.x) + add;
			g_spriteVertexStream[7] = (scaleY * bottomLeft.x) + add;
			g_spriteVertexStream[0xE] = (scaleY * topRight.x) + add;
			g_spriteVertexStream[0x15] = (scaleY * bottomRight.x) + add;
		}
		else // if (mode == Mode::Vanilla)
		{
			g_spriteVertexStream[0] = (screenScaleY * topLeft.x);
			g_spriteVertexStream[7] = (screenScaleY * bottomLeft.x);
			g_spriteVertexStream[0xE] = (screenScaleY * topRight.x);
			g_spriteVertexStream[0x15] = (screenScaleY * bottomRight.x);
		}

		// Game seems to add these, half-pixel offset?
		g_spriteVertexStream[0] += 0.5f;
		g_spriteVertexStream[7] += 0.5f;
		g_spriteVertexStream[0xE] += 0.5f;
		g_spriteVertexStream[0x15] += 0.5f;

		Game::D3DDevice()->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2u, g_spriteVertexStream, 0x1Cu);
	}

	// Adjust positions of sprites in 3d space (eg 1st/2nd/etc markers)
	static inline SafetyHookInline Calc3D2D_hk = {};
	static void Calc3D2D_dest(float a1, float a2, D3DVECTOR* in, D3DVECTOR* out)
	{
		// Capture the game's actual pre-projection view-space input before
		// Calc3D2D can alias/overwrite its output. The inverse-screen recovery
		// below is a fallback, not the sole source of ordinal rank depth.
		const D3DVECTOR originalInput = in ? *in : D3DVECTOR{};
		const bool finiteInput = in &&
			std::isfinite(originalInput.x) &&
			std::isfinite(originalInput.y) &&
			std::isfinite(originalInput.z);
		Calc3D2D_hk.call(a1, a2, in, out);

		// Exact rank/rival producers flatten a real game-view point into the
		// 640x480 sprite space before queueing. Recover that view-space point at
		// only the two proven Calc3D2D callsites so R30 can reproject it per eye.
		const void* returnAddress = _ReturnAddress();
		auto recoverViewPoint =
			[&](OutRunVR::GameSemantic::ProjectedMarkerInfo& info,
				bool exactOrdinalRank)
		{
			info = {};
			// For ordinal rank only, accept the raw input if it reprojections
			// to the original game's resulting 2D point. This checks the
			// coordinate space rather than guessing it from the function name.
			// The user's correctly attached OutRun rival stays on its old path.
			if (exactOrdinalRank && finiteInput && out &&
				std::isfinite(out->x) && std::isfinite(out->y) &&
				std::isfinite(a1) && std::isfinite(a2) &&
				originalInput.z < -1.0e-6f)
			{
				const float projectedX =
					originalInput.x * a1 / (-originalInput.z);
				const float projectedY =
					originalInput.y * a2 / (-originalInput.z);
				if (std::isfinite(projectedX) &&
					std::isfinite(projectedY) &&
					std::fabs(projectedX - out->x) <=
						std::fmax(0.25f, std::fabs(out->x) * 0.002f) &&
					std::fabs(projectedY - out->y) <=
						std::fmax(0.25f, std::fabs(out->y) * 0.002f))
				{
					info.viewX = originalInput.x;
					info.viewY = originalInput.y;
					info.viewZ = originalInput.z;
					info.valid = true;
					return;
				}
			}
			if (!out || !std::isfinite(out->x) ||
				!std::isfinite(out->y) || !std::isfinite(out->z) ||
				!std::isfinite(a1) || !std::isfinite(a2) ||
				std::fabs(a1) <= 1.0e-6f ||
				std::fabs(a2) <= 1.0e-6f ||
				std::fabs(out->z) <= 1.0e-6f)
				return;
			info.viewZ = out->z;
			info.viewX = out->x * (-out->z) / a1;
			info.viewY = out->y * (-out->z) / a2;
			// Finite game outputs can overflow while unprojecting. Never
			// publish a poisoned per-eye rank/rival marker anchor.
			if (!std::isfinite(info.viewX) ||
				!std::isfinite(info.viewY))
			{
				info = {};
				return;
			}
			info.valid = true;
		};

        // The game's callsite 0xBAEE7 is definitive; the exact hooked
        // sub_4BAD20 lifetime is a second, independently verified authority.
        // Some x86 inline-hook return-address paths differ even though the
        // call occurs inside this sole vehicle-rank producer. Previously a
        // return-site miss silently sent all rank sprites down the detached
        // WorldBillboard fallback. Never use the parent lifetime for NaviPub
        // ScreenHud children and never alter the working rival 0xBB6F5 path.
        const bool ordinalReturnSite =
            returnAddress == Module::exe_ptr(0xBAEE7);
        const bool ordinalProducerScope = RankMarkerSubActiveDepth != 0;
        if ((ordinalReturnSite || ordinalProducerScope) &&
            RankMarkerSubScreenHudDepth == 0)
        {
            recoverViewPoint(RankMarkerProjectedInfo, true);
            static thread_local bool loggedOrdinalCalc = false;
            if (!loggedOrdinalCalc)
            {
                loggedOrdinalCalc = true;
                spdlog::info(
                    "VR R57 rank Calc3D2D: ordinal capture valid={} inputFinite={} "
                    "screenZ={} sourceZ={} originalSite={} parentScope={}",
                    RankMarkerProjectedInfo.valid, finiteInput,
                    out ? out->z : 0.0f, originalInput.z,
                    ordinalReturnSite ? 1 : 0,
                    ordinalProducerScope ? 1 : 0);
            }
        }
		else if (returnAddress == Module::exe_ptr(0xBB6F5))
			recoverViewPoint(RivalMarkerProjectedInfo, false);

		// TODO: OnlineArcade mode needs to add position here

		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());

		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			out->x = (out->x / Game::screen_scale->y) * Game::screen_scale->x;
	};

	// The fraction of a pixel sub_4BAD20 discarded when it rounded the marker
	// position down, for the draws below to add back.
	inline static thread_local float RankMarkerFracX = 0.0f;
	inline static thread_local float RankMarkerFracY = 0.0f;

	static inline SafetyHookMid RankMarker_Truncate_hk{};
	static void RankMarker_Truncate_dest(safetyhook::Context& ctx)
	{
		const float x = *reinterpret_cast<const float*>(ctx.esp + RankMarker_StackX);
		const float y = *reinterpret_cast<const float*>(ctx.esp + RankMarker_StackY);

		// esi and ebp hold the rounded position. Keeping the difference instead
		// of the exact position lets every draw apply it, whatever offset from
		// the marker that draw sits at.
		// A broken/transitioning Calc3D2D producer can expose non-finite
		// stack coordinates at this exact rank-marker truncate hook. Do not
		// forward a NaN/Inf fractional offset to every queued sibling glyph.
		// Valid original subpixel correction is intentionally unchanged.
		if (!std::isfinite(x) || !std::isfinite(y))
		{
			RankMarkerFracX = RankMarkerFracY = 0.0f;
			return;
		}
		const float fracX = (x + 320.0f) - float(int(ctx.esi));
		const float fracY = ((240.0f - y) - 32.0f) - float(int(ctx.ebp));
		if (!std::isfinite(fracX) || !std::isfinite(fracY))
		{
			RankMarkerFracX = RankMarkerFracY = 0.0f;
			return;
		}
		RankMarkerFracX = fracX;
		RankMarkerFracY = fracY;
	}

	// The original sub_4BAD20 owns exactly one rank producer group, including
	// all 1st-3rd sprites and 4th+ clip digits. Scope its captured projection
	// to the whole invocation instead of reusing the preceding vehicle's anchor.
	static inline SafetyHookInline RankMarkerSub_hk{};
	static int __cdecl RankMarkerSub_dest(std::uint32_t arg)
	{
		const auto saved = RankMarkerProjectedInfo;
		const float savedFractionX = RankMarkerFracX;
		const float savedFractionY = RankMarkerFracY;
		RankMarkerProjectedInfo = {};
		RankMarkerFracX = RankMarkerFracY = 0.0f;
		++RankMarkerSubActiveDepth;
		const int result = RankMarkerSub_hk.call<int>(arg);
		--RankMarkerSubActiveDepth;
		RankMarkerProjectedInfo = saved;
		RankMarkerFracX = savedFractionX;
		RankMarkerFracY = savedFractionY;
		return result;
	}

	using RankMarkerSubFn = int(__cdecl*)(std::uint32_t);
	static int __cdecl RankMarkerSubSemanticDest(std::uint32_t arg)
	{
		struct ScreenHudScope
		{
			ScreenHudScope() noexcept { ++RankMarkerSubScreenHudDepth; }
			~ScreenHudScope() { --RankMarkerSubScreenHudDepth; }
		} scope;
		auto original = reinterpret_cast<RankMarkerSubFn>(Module::exe_ptr(0xBAD20));
		return original(arg);
	}

	// 1st, 2nd and 3rd are each a single sprite, and this call takes its
	// position as floats, so the discarded fraction goes straight back on.
	static void TagAppendedNodes(
		const std::array<SpriteNode*, Game::SpritePriorityCount>& before,
		OutRunVR::GameSemantic::RenderScope scope,
		OutRunVR::GameSemantic::ProducerToken producer =
			OutRunVR::GameSemantic::ProducerToken::None,
		const OutRunVR::GameSemantic::ProjectedMarkerInfo* projectedMarker =
			nullptr)
	{
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			SpriteNode* tailAfter = root ? root->tail_4 : nullptr;
			if (!root || !tailAfter || tailAfter == before[prio])
				continue;

			SpriteNode* node = before[prio]
				? before[prio]->next_0 : root->next_0;
			for (unsigned guard = 0; node && guard < Game::SpriteNodeMax; ++guard)
			{
				OutRunVR::GameSemantic::RegisterSpriteNodeScope(
					node, scope, producer, projectedMarker);
				if (node == tailAfter)
					break;
				node = node->next_0;
			}
		}
	}


	// Exact FUN_004BA9D0 caller identity is lost after the child E8 CALLs.
	// Restore the historical source-map bridge, but persist semantics on the
	// actual newly queued sprite nodes, not in retired ScopedProducerSemantic.
	static std::uint32_t OutRunHudTextCallerRva(const void* address) noexcept
	{
		const auto base = reinterpret_cast<std::uintptr_t>(Module::ExeHandle);
		const auto value = reinterpret_cast<std::uintptr_t>(address);
		if (!base || value < base + 5 || value - base > 0xFFFFFFFFu)
			return 0;
		return static_cast<std::uint32_t>(value - base - 5);
	}
	static void __cdecl OutRunHudTextProducer_dest(
		int glyphSet, int x, int y, const char* text, int a4, float alpha)
	{
		const auto caller = OutRunHudTextCallerRva(_ReturnAddress());
		const auto semantic = OutRunVRHudSemantics::ClassifyCaller(caller);
		const bool previous = OutRunHudTextScreenHud;
		OutRunHudTextScreenHud = previous ||
			semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud;
		OutRunHudTextProducerHook.call(
			glyphSet, x, y, text, a4, alpha);
		OutRunHudTextScreenHud = previous;
	}
	static int __cdecl OutRunHudText_clip(
		int sprite, int x, int y, std::uint32_t flags,
		float priority, std::uint32_t color)
	{
		if (!OutRunHudTextScreenHud)
			return Game::put_clip_sprite(
				sprite, x, y, flags, priority, color);
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int p = 0; p < Game::SpritePriorityCount; ++p)
		{
			SpriteNode* root = Game::sprite_prio_root[p];
			before[p] = root ? root->tail_4 : nullptr;
		}
		const int result = Game::put_clip_sprite(
			sprite, x, y, flags, priority, color);
		TagAppendedNodes(before,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::OutRunHudText);
		return result;
	}
	static int __cdecl OutRunHudText_sprani(
		std::uint32_t spriteId, float x, float y, int a4, int a5, float alpha)
	{
		if (!OutRunHudTextScreenHud)
			return Game::sprani_play_ae_auth_alpha(
				spriteId, x, y, a4, a5, alpha);
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int p = 0; p < Game::SpritePriorityCount; ++p)
		{
			SpriteNode* root = Game::sprite_prio_root[p];
			before[p] = root ? root->tail_4 : nullptr;
		}
		const int result = Game::sprani_play_ae_auth_alpha(
			spriteId, x, y, a4, a5, alpha);
		TagAppendedNodes(before,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::OutRunHudText);
		return result;
	}

	// R71 synchronous stage/checkpoint/result Sumo_Printf CALL producer.
	// Keep exact parent lifetime, then tag every appended SpriteNode.
	inline static SafetyHookMid OutRunStagePrintfEnterHooks[3]{};
	inline static SafetyHookMid OutRunStagePrintfLeaveHooks[3]{};
	inline static thread_local unsigned OutRunStagePrintfDepth = 0;
	inline static thread_local
		std::array<SpriteNode*, Game::SpritePriorityCount> OutRunStagePrintfBefore{};
	static void OutRunStagePrintfEnter(safetyhook::Context&)
	{
		if (OutRunStagePrintfDepth++ != 0)
			return;
		for (int p = 0; p < Game::SpritePriorityCount; ++p)
		{
			SpriteNode* root = Game::sprite_prio_root[p];
			OutRunStagePrintfBefore[p] = root ? root->tail_4 : nullptr;
		}
	}
    inline static thread_local std::uint64_t OutRunStagePrintfCompleted = 0;
	static void OutRunStagePrintfLeave(safetyhook::Context&)
	{
		if (!OutRunStagePrintfDepth || --OutRunStagePrintfDepth != 0)
			return;
        unsigned changedPriorities = 0;
        if (Settings::VRTelemetry)
        {
            for (int p = 0; p < Game::SpritePriorityCount; ++p)
            {
                SpriteNode* root = Game::sprite_prio_root[p];
                SpriteNode* after = root ? root->tail_4 : nullptr;
                if (after && after != OutRunStagePrintfBefore[p])
                    ++changedPriorities;
            }
        }
		TagAppendedNodes(OutRunStagePrintfBefore,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::OutRunStagePrintf);
        const auto hit = ++OutRunStagePrintfCompleted;
        if (Settings::VRTelemetry && (hit & (hit - 1u)) == 0)
        {
            spdlog::info(
                "VR P0 STAGE PRINT SOURCE: calls={} priorities={} gameState={} mode={} exactScope=SCREEN_HUD",
                hit, changedPriorities,
                Game::current_mode ? static_cast<int>(*Game::current_mode) : -1,
                Game::game_mode ? *Game::game_mode : -1);
        }
		OutRunStagePrintfBefore = {};
	}

	// R74 exact result-progress CALL boundaries: the parent 0x2D200 creates
	// queued SpriteNodes, so lower glyph/put_clip hooks do not capture every
	// sibling or animated percentage component. Snapshot the parent CALL,
	// then tag only its newly appended nodes, never a global result queue.
	inline static SafetyHookMid ResultProgressEnterA{};
	inline static SafetyHookMid ResultProgressLeaveA{};
	inline static SafetyHookMid ResultProgressEnterB{};
	inline static SafetyHookMid ResultProgressLeaveB{};
	inline static thread_local unsigned ResultProgressDepth = 0;
    // These are diagnostic counters only. The original E8->0x2D200
    // result-progress producer remains fully original and every child stays
    // on its existing exact-node ScreenHud route.
    inline static thread_local std::uint64_t ResultProgressCompletedCalls = 0;
	inline static thread_local
		std::array<SpriteNode*, Game::SpritePriorityCount> ResultProgressTailsBefore{};
	static void ResultProgressEnter(safetyhook::Context&)
	{
		if (ResultProgressDepth++ != 0)
			return;
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			ResultProgressTailsBefore[prio] = root ? root->tail_4 : nullptr;
		}
	}
	static void ResultProgressLeave(safetyhook::Context&)
	{
		if (!ResultProgressDepth || --ResultProgressDepth != 0)
			return;
        // Preserve original producer-before/new-child boundaries, counting
        // only priorities where the exact call appended at least one node.
        // The screenshot at result 93% identifies the unfinished animation;
        // it cannot by itself reveal which E8 made the large record glyph.
        // This bounded trace distinguishes a live progress producer from an
        // early generic-screen-overlay fallback without altering pixels.
        unsigned changedPriorities = 0;
        if (Settings::VRTelemetry)
        {
            for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
            {
                SpriteNode* root = Game::sprite_prio_root[prio];
                SpriteNode* after = root ? root->tail_4 : nullptr;
                if (after && after != ResultProgressTailsBefore[prio])
                    ++changedPriorities;
            }
        }
		TagAppendedNodes(ResultProgressTailsBefore,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::ResultProgress);
        const std::uint64_t hits = ++ResultProgressCompletedCalls;
        if (Settings::VRTelemetry && (hits & (hits - 1u)) == 0)
        {
            spdlog::info(
                "VR P0 RESULT PROGRESS SOURCE: completedCalls={} changedPriorities={} state={} mode={} exactScope=SCREEN_HUD",
                hits, changedPriorities,
                Game::current_mode ? static_cast<int>(*Game::current_mode) : -1,
                Game::game_mode ? *Game::game_mode : -1);
        }
		ResultProgressTailsBefore = {};
	}

    inline static SafetyHookMid StageExtensionEnterHooks[
        std::size(StageExtensionSpraniCalls)]{};
    inline static SafetyHookMid StageExtensionLeaveHooks[
        std::size(StageExtensionSpraniCalls)]{};
    inline static SafetyHookMid StageExtensionPrintEnterHooks[
        std::size(StageExtensionPrintCalls)]{};
    inline static SafetyHookMid StageExtensionPrintLeaveHooks[
        std::size(StageExtensionPrintCalls)]{};
    inline static thread_local unsigned StageExtensionDepth = 0;
    inline static thread_local OutRunVR::GameSemantic::RenderScope
        StageExtensionSavedScope = OutRunVR::GameSemantic::RenderScope::None;
    inline static thread_local std::array<SpriteNode*, Game::SpritePriorityCount>
        StageExtensionBefore{};
    inline static thread_local std::uint64_t StageExtensionCompleted = 0;

    static void StageExtensionEnter(safetyhook::Context&)
    {
        if (StageExtensionDepth++ != 0)
            return;
        for (int p = 0; p < Game::SpritePriorityCount; ++p)
        {
            SpriteNode* root = Game::sprite_prio_root[p];
            StageExtensionBefore[p] = root ? root->tail_4 : nullptr;
        }
        // The six original source E8 CALLs can synchronously draw text as
        // well as enqueue sprites. Post-call node tags only cover the latter.
        // Scope only this exact source call, never the shared text renderer.
        StageExtensionSavedScope = OutRunVR::GameSemantic::CurrentScope;
        if (Settings::VREnabled)
            OutRunVR::GameSemantic::CurrentScope =
                OutRunVR::GameSemantic::RenderScope::ScreenHud;
    }

    static void StageExtensionLeave(safetyhook::Context&)
    {
        if (!StageExtensionDepth || --StageExtensionDepth != 0)
            return;
        TagAppendedNodes(StageExtensionBefore,
            OutRunVR::GameSemantic::RenderScope::ScreenHud,
            OutRunVR::GameSemantic::ProducerToken::StageExtensionTime);
        // Always unwind even if VR enablement changes during the call.
        OutRunVR::GameSemantic::CurrentScope = StageExtensionSavedScope;
        StageExtensionSavedScope =
            OutRunVR::GameSemantic::RenderScope::None;
        const auto hit = ++StageExtensionCompleted;
        if (Settings::VRTelemetry && (hit & (hit - 1u)) == 0)
            spdlog::info(
                "VR P0 STAGE EXTENSION SOURCES: calls={} gameState={} mode={} exactScope=SCREEN_HUD",
                hit,
                Game::current_mode ? static_cast<int>(*Game::current_mode) : -1,
                Game::game_mode ? *Game::game_mode : -1);
        StageExtensionBefore = {};
    }

    // The original GOAL animations print the large white record and
    // intermediate stage text through *19* EXE 0x97xxx E8 calls into
    // sub_4B9200, not just the two 0x2D200 progress percentage calls.
    // No shared-function detour: bracket ONLY the exact original E8
    // parents, so a completed GOAL or another screen cannot inherit tags.
    inline static SafetyHookMid ResultTextEnterHooks[
        std::size(ResultTextB9200Calls)]{};
    inline static SafetyHookMid ResultTextLeaveHooks[
        std::size(ResultTextB9200Calls)]{};
    inline static thread_local unsigned ResultTextDepth = 0;
    inline static thread_local OutRunVR::GameSemantic::RenderScope
        ResultTextSavedScope = OutRunVR::GameSemantic::RenderScope::None;
    inline static thread_local std::array<SpriteNode*, Game::SpritePriorityCount>
        ResultTextBefore{};
    inline static thread_local std::uint64_t ResultTextCompleted = 0;

    static void ResultTextEnter(safetyhook::Context&)
    {
        if (ResultTextDepth++ != 0)
            return;
        for (int p = 0; p < Game::SpritePriorityCount; ++p)
        {
            SpriteNode* root = Game::sprite_prio_root[p];
            ResultTextBefore[p] = root ? root->tail_4 : nullptr;
        }
        // Exact 19 B9200 parent calls also need source-time ownership for
        // immediate graphics, independent of later queued-node provenance.
        ResultTextSavedScope = OutRunVR::GameSemantic::CurrentScope;
        if (Settings::VREnabled)
            OutRunVR::GameSemantic::CurrentScope =
                OutRunVR::GameSemantic::RenderScope::ScreenHud;
    }

    static void ResultTextLeave(safetyhook::Context&)
    {
        if (!ResultTextDepth || --ResultTextDepth != 0)
            return;
        TagAppendedNodes(ResultTextBefore,
            OutRunVR::GameSemantic::RenderScope::ScreenHud,
            OutRunVR::GameSemantic::ProducerToken::ResultTextB9200);
        // Restore the exact previous scope without relying on a live VR flag.
        OutRunVR::GameSemantic::CurrentScope = ResultTextSavedScope;
        ResultTextSavedScope =
            OutRunVR::GameSemantic::RenderScope::None;
        const auto hit = ++ResultTextCompleted;
        if (Settings::VRTelemetry && (hit & (hit - 1u)) == 0)
            spdlog::info(
                "VR P0 RESULT TEXT B9200: calls={} state={} mode={} exactScope=SCREEN_HUD",
                hit,
                Game::current_mode ? static_cast<int>(*Game::current_mode) : -1,
                Game::game_mode ? *Game::game_mode : -1);
        ResultTextBefore = {};
    }

	// R74 original GOAL helpers have the verified zero-argument void ABI.
	// Preserve the original call, then tag all its newly queued siblings.
	using GoalTimeHelperFn = void(__cdecl*)();
	static void GoalTime_TagHelper(int helperRva)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			before[prio] = root ? root->tail_4 : nullptr;
		}
		// Current R84 queue authority has no ScopedProducerSemantic class.
		// The original helper is synchronous; tag its appended nodes after it
		// returns, preserving the exact parent producer identity.
		auto original = reinterpret_cast<GoalTimeHelperFn>(
			Module::exe_ptr(helperRva));
		original();
		// Both original GOAL helpers are required and intentional. The
		// user's screen evidence suggests different visible components
		// (course/stage name and recorded time), NOT two redundant calls
		// rendering one time glyph. Exact component-to-address mapping remains
		// unproven until original function disassembly or a matching HMD trace.
		// Always execute EACH original exactly once and keep all siblings.
		// Distinct producer tokens are diagnostic only: do not suppress,
		// merge or deduplicate either helper, even if both draw white/alpha.
		const auto producer = helperRva == 0xBE020
			? OutRunVR::GameSemantic::ProducerToken::GoalTime020
			: (helperRva == 0xBE150
				? OutRunVR::GameSemantic::ProducerToken::GoalTime150
				: OutRunVR::GameSemantic::ProducerToken::GoalTimeHelper);
		TagAppendedNodes(before,
			OutRunVR::GameSemantic::RenderScope::ScreenHud, producer);
	}
	static void __cdecl GoalTime_Help020() { GoalTime_TagHelper(0xBE020); }
	static void __cdecl GoalTime_Help150() { GoalTime_TagHelper(0xBE150); }

	static int __cdecl RankMarker_sprani(uint32_t spriteId, float x, float y, int a4, int a5, float alpha)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> tailsBefore{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			tailsBefore[prio] = root ? root->tail_4 : nullptr;
		}

		const int result = Game::sprani_play_ae_auth_alpha(
			spriteId, x + RankMarkerFracX, y + RankMarkerFracY, a4, a5, alpha);

		OutRunVR::GameSemantic::RenderScope scope{};
		const OutRunVR::GameSemantic::ProjectedMarkerInfo* marker = nullptr;
		if (RankMarkerSubScreenHudDepth != 0)
		{
			scope = OutRunVR::GameSemantic::RenderScope::ScreenHud;
		}
		else
		{
			const bool projected = RankMarkerProjectedInfo.valid;
			scope = projected
				? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
				: OutRunVR::GameSemantic::RenderScope::WorldBillboard;
			marker = projected ? &RankMarkerProjectedInfo : nullptr;
		}

		// These four exact producer callsites own the vehicle-relative rank
		// markers. Prefer the recovered Calc3D2D anchor; retain the current
		// strict WorldBillboard path as a fail-soft fallback if capture is absent.
		// A sprani producer normally emits one sprite, but can queue an
		// animated or masked sibling. Every node appended by this exact CALL
		// belongs to the same rank marker, not just the final priority tail.
		TagAppendedNodes(tailsBefore, scope,
			OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani, marker);
		return result;
	}

	// 4th place onward is spelled out from digit sprites drawn by
	// put_clip_sprite, which takes its position as int. It converts that to
	// float when filling in the sprite it queues, so the fraction goes back on
	// there instead.
	static int __cdecl RankMarker_putClipSprite(
		int xstnum, int x, int y, uint32_t flags, float priority, uint32_t color)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> tailsBefore{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			tailsBefore[prio] = root ? root->tail_4 : nullptr;
		}
		const int result =
			Game::put_clip_sprite(xstnum, x, y, flags, priority, color);

		const bool screenHud = RankMarkerSubScreenHudDepth != 0;
		const bool projected = !screenHud && RankMarkerProjectedInfo.valid;
		const auto scope = screenHud
			? OutRunVR::GameSemantic::RenderScope::ScreenHud
			: (projected
				? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
				: OutRunVR::GameSemantic::RenderScope::WorldBillboard);
		// put_clip_sprite normally queues one glyph. If an animation/mask
		// expands it to sibling nodes (even at another priority), every child
		// needs the original fractional offset and the same spatial owner.
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			SpriteNode* tailAfter = root ? root->tail_4 : nullptr;
			if (!root || !tailAfter || tailAfter == tailsBefore[prio])
				continue;
			SpriteNode* node = tailsBefore[prio]
				? tailsBefore[prio]->next_0 : root->next_0;
			for (unsigned guard = 0; node && guard < Game::SpriteNodeMax; ++guard)
			{
				// Only kind_C==0 stores SPRARGS at args_10. The original
				// clip producer had modified a single SPRARGS tail; a sibling
				// emitted through put_sprite_ex2 owns args2_58 instead.
				if (node->kind_C == 0)
				{
					node->args_10.float24 += RankMarkerFracX;
					node->args_10.float28 += RankMarkerFracY;
				}
				if (node == tailAfter)
					break;
				node = node->next_0;
			}
		}
		TagAppendedNodes(tailsBefore, scope,
			OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite,
			projected ? &RankMarkerProjectedInfo : nullptr);
		return result;
	}

	using DispRankFirstSpraniFn = int(__cdecl*)(uint32_t, float, float, int, int);
	static int __cdecl DispRankFirst_sprani(
		uint32_t spriteId, float x, float y, int a4, int a5)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			before[prio] = root ? root->tail_4 : nullptr;
		}
		auto original = reinterpret_cast<DispRankFirstSpraniFn>(
			Module::exe_ptr(0x29530));
		const int result = original(spriteId, x, y, a4, a5);
		// Keep the original first position (kind_C=1) and any animated
		// siblings on the same finite ScreenHud plane as eight kind-0 clips.
		TagAppendedNodes(before,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::DispRankFirst);
		return result;
	}

	static int __cdecl ExactScreenHud_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> tailsBefore{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			tailsBefore[prio] = root ? root->tail_4 : nullptr;
		}
		const int result = Game::put_clip_sprite(
			xstnum, x, y, flags, priority, color);
		// All exact-address menu arrows, position HUD and result glyph
		// siblings are SCREEN_HUD; tagging only tail_4 left earlier
		// siblings head-locked by the generic fallback path.
		TagAppendedNodes(tailsBefore,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::ExactScreenHudClipSprite);
		return result;
	}

	static int __cdecl RivalMarker_sprani(
		uint32_t spriteId, float x, float y, int a4, int a5, float alpha)
	{
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			before[prio] = root ? root->tail_4 : nullptr;
		}

		const int result = Game::sprani_play_ae_auth_alpha(
			spriteId, x, y, a4, a5, alpha);
		// R71 HMD evidence binds this exact 0xBB796 producer to the
		// vehicle-relative rival marker. Reuse its proven Calc3D2D anchor when
		// available; fail softly to the current strict WorldBillboard route.
		const auto projectedAnchor = RivalMarkerProjectedInfo;
		// Only the first marker from the matching 0xBB6F5 Calc3D2D producer
		// can consume this anchor. No subsequent vehicle or frame may inherit it.
		RivalMarkerProjectedInfo = {};
		const bool projected = projectedAnchor.valid;
		TagAppendedNodes(
			before,
			projected
				? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
				: OutRunVR::GameSemantic::RenderScope::WorldBillboard,
			OutRunVR::GameSemantic::ProducerToken::RivalMarkerSprani,
			projected ? &projectedAnchor : nullptr);
		return result;
	}

	using TextGlyphPutSpriteFn = int(__cdecl*)(SPRARGS*, float);
	static int __cdecl TextGlyph_putSprite(SPRARGS* args, float priority)
	{
		// The canonical original EXE's 0x2C808 / 0x2C9DB
		// glyph-generation CALLs both reach put_sprite_ex at 0x2CFE0.
		// Sumo_Printf (including stage/result 0x975EE / 0x97727 /
		// 0x977FB) can emit a group, not just the final priority tail.
		std::array<SpriteNode*, Game::SpritePriorityCount> tailsBefore{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			tailsBefore[prio] = root ? root->tail_4 : nullptr;
		}
		auto original = reinterpret_cast<TextGlyphPutSpriteFn>(
			Module::exe_ptr(0x2CFE0));
		const int result = original(args, priority);
		// Tag all original-produced glyph/mask children as ScreenHud;
		// otherwise an untagged sibling bypasses the R30 head-recentered
		// HUD owner and doubles at +TIME / checkpoint / goal/result.
		TagAppendedNodes(tailsBefore,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::TextGlyphPutSprite);
		return result;
	}

	enum SpriteScaleType
	{
		Disabled = 0,
		DetectEdges = 1,
		ForceLeft = 2,
		ForceRight = 3
	};

	static inline SpriteScaleType ScalingType = SpriteScaleType::Disabled;

	static inline SafetyHookMid drawFootage{};
	static void drawFootage_dest(safetyhook::Context& ctx)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode == ScalingMode::OnlineArcade && ScalingType != SpriteScaleType::Disabled)
		{
			float spacing = -((Game::screen_scale->y * Game::original_resolution.x) - Game::screen_resolution->x) / 2;

			// Space out the UI elements if they're on the sides of the screen
			float* m = *Module::exe_ptr<float*>(0x49B564);
			float x = m[12];

			float add = 0;
			if (ScalingType == SpriteScaleType::ForceLeft || ScalingType == SpriteScaleType::DetectEdges && x < SCREEN_ONE_THIRD)
				add = -(spacing / Game::screen_scale->x);
			if (ScalingType == SpriteScaleType::ForceRight || ScalingType == SpriteScaleType::DetectEdges && x >= SCREEN_TWO_THIRD)
				add = (spacing / Game::screen_scale->x);

			m[12] = x + add;
		}
	}
	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite(safetyhook::Context& ctx)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode != ScalingMode::KeepCentered && mode != ScalingMode::OnlineArcade)
			return;

		float* vtxStream = (float*)(ctx.ecx);

		float scale = min(Game::screen_scale->x, Game::screen_scale->y);
		float centering = (Game::screen_resolution->x - (Game::original_resolution.x * scale)) / 2;

		float x1 = vtxStream[0];
		float x2 = vtxStream[9];
		float x3 = vtxStream[18];
		float x4 = vtxStream[27];

		vtxStream[0] = ((vtxStream[0] / Game::screen_scale->x) * scale) + centering;
		vtxStream[9] = ((vtxStream[9] / Game::screen_scale->x) * scale) + centering;
		vtxStream[18] = ((vtxStream[18] / Game::screen_scale->x) * scale) + centering;
		vtxStream[27] = ((vtxStream[27] / Game::screen_scale->x) * scale) + centering;
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite2_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite2(safetyhook::Context& ctx)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode != ScalingMode::KeepCentered && mode != ScalingMode::OnlineArcade)
			return;

		float* vtxStream = (float*)(ctx.esp + 0x80);

		float scale = min(Game::screen_scale->x, Game::screen_scale->y);
		float centering = (Game::screen_resolution->x - (Game::original_resolution.x * scale)) / 2;

		float x1 = vtxStream[0];
		float x2 = vtxStream[11];
		float x3 = vtxStream[22];
		float x4 = vtxStream[33];

		vtxStream[0] = ((vtxStream[0] / Game::screen_scale->x) * scale) + centering;
		vtxStream[11] = ((vtxStream[11] / Game::screen_scale->x) * scale) + centering;
		vtxStream[22] = ((vtxStream[22] / Game::screen_scale->x) * scale) + centering;
		vtxStream[33] = ((vtxStream[33] / Game::screen_scale->x) * scale) + centering;
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite3_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite3(safetyhook::Context& ctx)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode != ScalingMode::KeepCentered && mode != ScalingMode::OnlineArcade)
			return;

		float* vtxStream = (float*)(ctx.edx);

		float scale = min(Game::screen_scale->x, Game::screen_scale->y);
		float centering = (Game::screen_resolution->x - (Game::original_resolution.x * scale)) / 2;

		float x1 = vtxStream[0];
		float x2 = vtxStream[13];
		float x3 = vtxStream[26];
		float x4 = vtxStream[39];

		vtxStream[0] = ((vtxStream[0] / Game::screen_scale->x) * scale) + centering;
		vtxStream[13] = ((vtxStream[13] / Game::screen_scale->x) * scale) + centering;
		vtxStream[26] = ((vtxStream[26] / Game::screen_scale->x) * scale) + centering;
		vtxStream[39] = ((vtxStream[39] / Game::screen_scale->x) * scale) + centering;
	}

	static void SpriteSpacingEnable(safetyhook::Context& ctx)
	{
		ScalingType = SpriteScaleType::DetectEdges;
	}
	static void SpriteSpacingDisable(safetyhook::Context& ctx)
	{
		ScalingType = SpriteScaleType::Disabled;
	}
	static void SpriteSpacingForceLeft(safetyhook::Context& ctx)
	{
		ScalingType = SpriteScaleType::ForceLeft;
	}
	static void SpriteSpacingForceRight(safetyhook::Context& ctx)
	{
		ScalingType = SpriteScaleType::ForceRight;
	}

	// NaviPub_Disp
	static inline SafetyHookMid NaviPub_Disp_SpriteSpacingEnable_hk{};
	static inline SafetyHookMid NaviPub_Disp_SpriteSpacingEnable2_hk{};

	static inline SafetyHookMid NaviPub_Disp_SpriteSpacingDisable_hk{};
	static inline SafetyHookMid NaviPub_Disp_SpriteSpacingDisable2_hk{};

	// dispMarkerCheck
	static inline SafetyHookMid dispMarkerCheck_SpriteScalingDisable_hk{};

	// DispTimeAttack2D
	static inline SafetyHookMid DispTimeAttack2D_SpriteScalingForceRight_hk{};
	static inline SafetyHookMid DispTimeAttack2D_SpriteScalingForceLeft_hk{};
	static inline SafetyHookMid DispTimeAttack2D_SpriteScalingDisable_hk{};
	static inline SafetyHookMid DispTimeAttack2D_SpriteScalingForceEnable_hk{};

	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk2{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk3{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk4{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk5{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk6{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk7{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk8{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk9{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk10{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk11{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk12{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk13{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk14{};
	static inline SafetyHookMid DispTimeAttack2D_put_scroll_AdjustPosition_hk15{};

	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk1{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk2{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk3{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk4{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk5{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk6{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk7{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk8{};
	static inline SafetyHookMid DispRank_put_scroll_AdjustPosition_hk9{};

	static inline SafetyHookMid DispGearPosition_put_scroll_AdjustPosition_hk1{};
	static inline SafetyHookMid DispGearPosition_put_scroll_AdjustPosition_hk2{};
	static inline SafetyHookMid DispGearPosition_put_scroll_AdjustPosition_hk3{};

	template <typename T>
	static void AddSpriteSpacing(T* value, bool left)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode != ScalingMode::OnlineArcade)
			return;

		float spacing = -((Game::screen_scale->y * Game::original_resolution.x) - Game::screen_resolution->x) / 2;
		spacing = spacing / Game::screen_scale->x;

		// round our spacing value to nearest if this is integer, fixes REV indicator light being slightly offset
		if constexpr (std::is_integral_v<T>)
			spacing = std::round(spacing);

		if(left)
			*value = T(float(*value) - spacing);
		else
			*value = T(float(*value) + spacing);
	}

	static void put_scroll_AdjustPositionRight(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((int*)(ctx.esp + 4), false);
	}
	static void TimeRecord_AdjustPositionAndHud(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((int*)(ctx.esp + 4), false);
		OutRunVR::GameSemantic::ArmNextDraw(
			OutRunVR::GameSemantic::RenderScope::ScreenHud);
	}
	static void put_scroll_AdjustPositionLeft(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((int*)(ctx.esp + 4), true);
	}

	static int __cdecl ExactScreenHudRight_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		AddSpriteSpacing(&x, false);
		return ExactScreenHud_putClipSprite(
			xstnum, x, y, flags, priority, color);
	}

	// R64 exact 6th/6 kind-0 source. Unlike generic C2C/time/right
	// clips, these eight canonical DispRank E8 edges are the only source
	// eligible for the HMD-proven post-ID3DXSprite::Draw Flush isolate.
	static bool IsExactDispRankRightClipRva(int rva) noexcept
	{
		switch (rva)
		{
		case 0xB9F3A: case 0xB9F5E: case 0xB9F81:
		case 0xB9FD0: case 0xB9FFC: case 0xBA01E:
		case 0xBA035: case 0xBA052:
			return true;
		default:
			return false;
		}
	}

	static int __cdecl DispRankRight_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		// Preserve the same upstream right-side aspect/online spacing
		// and exact all-sibling queued HUD tagging as the retired generic
		// right wrapper; only its source identity differs.
		AddSpriteSpacing(&x, false);
		std::array<SpriteNode*, Game::SpritePriorityCount> before{};
		for (int p = 0; p < Game::SpritePriorityCount; ++p)
		{
			SpriteNode* root = Game::sprite_prio_root[p];
			before[p] = root ? root->tail_4 : nullptr;
		}
		const int result = Game::put_clip_sprite(
			xstnum, x, y, flags, priority, color);
		TagAppendedNodes(before,
			OutRunVR::GameSemantic::RenderScope::ScreenHud,
			OutRunVR::GameSemantic::ProducerToken::DispRankClipSprite);
		return result;
	}

	static int __cdecl ExactScreenHudLeft_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		AddSpriteSpacing(&x, true);
		return ExactScreenHud_putClipSprite(
			xstnum, x, y, flags, priority, color);
	}

	// PutGhostGapInfo
	static inline SafetyHookMid PutGhostGapInfo_AdjustPosition_hk{};
	static void PutGhostGapInfo_AdjustPosition(safetyhook::Context& ctx)
	{
		bool left = false;
		int* val = (int*)&ctx.ebp;
		if (*val == 102)
			left = true;

		AddSpriteSpacing(val, left);
	};

	// Fix position of the "Ghost/You/Diff" sprites shown with ghost car info
	// Online arcade doesn't seem to adjust this, maybe was left broken in that? (it's needed for 21:9 at least...)
	static inline SafetyHookMid PutGhostGapInfo_sub_AdjustPosition_hk{};
	static void PutGhostGapInfo_sub_AdjustPosition(safetyhook::Context& ctx)
	{
		bool left = false;
		float* val = &ctx.xmm0.f32[0];
		if (*val == 4.0f)
			left = true;

		AddSpriteSpacing(val, left);
	}

	// DispGhostGap
	static inline SafetyHookMid DispGhostGap_ForceLeft_hk{};
	static inline SafetyHookMid DispGhostGap_ForceLeft2_hk{};
	static inline SafetyHookMid DispGhostGap_ForceRight_hk{};
	static inline SafetyHookMid DispGhostGap_ForceRight2_hk{};

	// NaviPub_DispTimeAttackGoal
	static inline SafetyHookMid NaviPub_DispTimeAttackGoal_DisableScaling_hk{};

	// Heart totals
	static inline SafetyHookMid NaviPub_Disp_HeartDisableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_HeartEnableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_C2CHeartDisableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_C2CHeartEnableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_C2CHeartEnableScaling2_hk{};

	static inline SafetyHookMid NaviPub_Disp_C2CFruitDisableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_C2CFruitEnableScaling_hk{};

	static inline SafetyHookMid NaviPub_Disp_RivalDisableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_RivalEnableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_RivalOnlineDisableScaling_hk{};
	static inline SafetyHookMid NaviPub_Disp_RivalOnlineEnableScaling_hk{};

	static inline SafetyHookMid ctrl_icon_work_AdjustPosition_hk{};
	static void ctrl_icon_work_AdjustPosition(safetyhook::Context& ctx)
	{
		AddSpriteSpacing(&ctx.xmm0.f32[0], false);
	}

	static inline SafetyHookMid ctrl_icon_work_AdjustPosition2_hk{};
	static inline SafetyHookMid set_icon_work_AdjustPosition_hk{};
	static void ctrl_icon_work_AdjustPosition2(safetyhook::Context& ctx)
	{
		AddSpriteSpacing(&ctx.xmm0.f32[0], false);

		*(float*)(ctx.esp) = ctx.xmm0.f32[0];
	}

	static inline SafetyHookMid DispTempHeartNum_AdjustPosition_hk{};
	static void DispTempHeartNum_AdjustPosition(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((int*)(ctx.esp), false);
	}

	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk1{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk2{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk3{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk4{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk5{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk6{};
	static inline SafetyHookMid C2CSpeechBubble_AdjustPositionESP0_hk7{};

	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk1{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk2{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk3{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk4{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk5{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk6{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk7{};
	static inline SafetyHookMid C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk1{};
	static inline SafetyHookMid C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk2{};
	static inline SafetyHookMid C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk3{};
	static inline SafetyHookMid C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk4{};

	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk8{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk9{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk10{};

	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk11{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk12{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk13{};
	static inline SafetyHookMid C2CSpeechBubbleGF_AdjustPositionESP0_hk14{};

	static inline SafetyHookMid C2CDontLoseGF_AdjustPosition_hk1{};
	static inline SafetyHookMid C2CDontLoseGF_AdjustPosition_hk2{};
	static inline SafetyHookMid C2CDontLoseGF_AdjustPosition_hk3{};
	static inline SafetyHookMid C2CTestSlipstream_AdjustPosition_hk{};

	static void C2CSpeechBubble_AdjustPositionESP0(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((float*)(ctx.esp), false);
	}

	static void C2CSpeechBubble_AdjustPositionESP4(safetyhook::Context& ctx)
	{
		AddSpriteSpacing((float*)(ctx.esp + 4), false);
	}

public:
	std::string_view description() override
	{
		return "UIScaling";
	}

	bool validate() override
	{
		return Settings::UIScalingMode > 0;
	}

	void declare_settings() override
	{
		Settings::UIScalingMode.needs_restart([] {
			// apply() nops 0x293 bytes of the original sprite path, so mode 0 can't
			// be returned to. 1 and 2 only change what the hooks read.
			return (Settings::UIScalingMode.startup_value() == 0) != (Settings::UIScalingMode.get() == 0);
		});
	}

	bool apply() override
	{
		Memory::VP::Nop(Module::exe_ptr(draw_sprite_custom_matrix_mid_Addr), 0x293);

		draw_sprite_custom_matrix_hk = safetyhook::create_mid(Module::exe_ptr(draw_sprite_custom_matrix_mid_Addr), draw_sprite_custom_matrix_mid);

		// D3DXMatrixTransformation2D hook allows us to change draw_sprite_custom
		D3DXMatrixTransformation2D = safetyhook::create_inline(Module::exe_ptr(D3DXMatrixTransformation2D_Addr), D3DXMatrixTransformation2D_dest);

		Calc3D2D_hk = safetyhook::create_inline(Module::exe_ptr(Calc3D2D_Addr), Calc3D2D_dest);
		// 5868 runtime/old R70 evidence: FUN_004BA9D0's two proven E8
		// children lost their parent HUD identity. Do not install a broad
		// sprani/clip hook; intercept only these two canonical CALL sites.
		OutRunHudTextProducerHook = safetyhook::create_inline(
			Module::exe_ptr(OutRunHudTextProducerRva),
			OutRunHudTextProducer_dest);
		if (OutRunHudTextProducerHook)
		{
			Memory::VP::InjectHook(Module::exe_ptr(OutRunHudTextClipCallRva),
				OutRunHudText_clip, Memory::HookType::Call);
			Memory::VP::InjectHook(Module::exe_ptr(OutRunHudTextSpraniCallRva),
				OutRunHudText_sprani, Memory::HookType::Call);
			spdlog::info(
				"VR P0: original BA9D0 HUD text producer and its two exact child CALLs restored");
		}
		else
			spdlog::error(
				"VR P0: BA9D0 producer hook unavailable; child CALLs left original");
		RankMarkerSub_hk = safetyhook::create_inline(
			Module::exe_ptr(0xBAD20), RankMarkerSub_dest);

		RankMarker_Truncate_hk = safetyhook::create_mid(Module::exe_ptr(RankMarker_Truncate), RankMarker_Truncate_dest);
		for (int addr : RankMarkerSubScreenHudCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr), RankMarkerSubSemanticDest,
				Memory::HookType::Call);
		for (int addr : RankMarker_SpraniCalls)
			Memory::VP::InjectHook(Module::exe_ptr(addr), RankMarker_sprani, Memory::HookType::Call);
		for (int addr : RankMarker_ClipSpriteCalls)
			Memory::VP::InjectHook(Module::exe_ptr(addr), RankMarker_putClipSprite, Memory::HookType::Call);
		for (int addr : OptionArrow_ClipSpriteCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr), ExactScreenHud_putClipSprite,
				Memory::HookType::Call);
		for (int addr : ExactScreenHud_ClipSpriteCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr), ExactScreenHud_putClipSprite,
				Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(DispRankFirstSpraniCall),
			DispRankFirst_sprani, Memory::HookType::Call);
		for (int addr : ExactScreenHudRight_ClipSpriteCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr),
				IsExactDispRankRightClipRva(addr)
					? DispRankRight_putClipSprite
					: ExactScreenHudRight_putClipSprite,
				Memory::HookType::Call);
		for (int addr : ExactScreenHudLeft_ClipSpriteCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr), ExactScreenHudLeft_putClipSprite,
				Memory::HookType::Call);
		Memory::VP::InjectHook(
			Module::exe_ptr(RivalMarker_SpraniCall),
			RivalMarker_sprani, Memory::HookType::Call);
		for (int addr : TextGlyph_PutSpriteCalls)
			Memory::VP::InjectHook(
				Module::exe_ptr(addr), TextGlyph_putSprite,
				Memory::HookType::Call);
		// Exact canonical original x86 CALLs: 0x975EE/0x97727/0x977FB
		// -> 0x2CDD0. Scope only the producer CALL duration, never
		// globally hook Sumo_Printf or classify unproven game sprites.
		bool stageHookOk = true;
		for (int i = 0; i < 3; ++i)
		{
			OutRunStagePrintfEnterHooks[i] = safetyhook::create_mid(
				Module::exe_ptr(OutRunStagePrintfCalls[i]),
				OutRunStagePrintfEnter);
			OutRunStagePrintfLeaveHooks[i] = safetyhook::create_mid(
				Module::exe_ptr(OutRunStagePrintfCalls[i] + 5),
				OutRunStagePrintfLeave);
			stageHookOk = stageHookOk &&
				OutRunStagePrintfEnterHooks[i] && OutRunStagePrintfLeaveHooks[i];
		}
		if (!stageHookOk)
		{
			for (int i = 0; i < 3; ++i)
			{
				OutRunStagePrintfEnterHooks[i] = {};
				OutRunStagePrintfLeaveHooks[i] = {};
			}
			spdlog::error("VR P0: stage Sumo_Printf producer partial install rolled back");
		}
		// Original R74 exact CALL window has already been byte-fingerprinted:
		// result 0x97BE4/0x97DEC E8 -> 0x2D200, and GOAL helpers
		// 0xBEA5A -> 0xBE020 / 0xBEA5F -> 0xBE150.
		// Bracket the two result calls without hooking the shared 0x2D200.
		ResultProgressEnterA = safetyhook::create_mid(
			Module::exe_ptr(ResultProgressCallA), ResultProgressEnter);
		ResultProgressLeaveA = safetyhook::create_mid(
			Module::exe_ptr(ResultProgressCallA + 5), ResultProgressLeave);
		ResultProgressEnterB = safetyhook::create_mid(
			Module::exe_ptr(ResultProgressCallB), ResultProgressEnter);
		ResultProgressLeaveB = safetyhook::create_mid(
			Module::exe_ptr(ResultProgressCallB + 5), ResultProgressLeave);
		if (!ResultProgressEnterA || !ResultProgressLeaveA ||
			!ResultProgressEnterB || !ResultProgressLeaveB)
		{
			// A half-installed producer boundary can leave the following
			// result's SpriteNode semantic attached to the wrong call.
			// Keep original game CALLs intact and disable this repair atomically.
			ResultProgressEnterA = {};
			ResultProgressLeaveA = {};
			ResultProgressEnterB = {};
			ResultProgressLeaveB = {};
			spdlog::error(
				"VR P0 RESULT: exact R74 producer midhooks incomplete; all rolled back");
		}
        // The original +TIME transition emits BOTH decorated sprani AND
        // its 0x973C0/0x974E0 number/text helpers, each from a distinct
        // canonical 0x989xx E8. Atomic install/rollback across ALL SIX
        // original source parents; tag only the newly queued siblings.
        bool stageExtensionOk = true;
        for (unsigned i = 0; i < std::size(StageExtensionSpraniCalls); ++i)
        {
            const int rva = StageExtensionSpraniCalls[i];
            StageExtensionEnterHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva), StageExtensionEnter);
            StageExtensionLeaveHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva + 5), StageExtensionLeave);
            stageExtensionOk = stageExtensionOk &&
                StageExtensionEnterHooks[i] && StageExtensionLeaveHooks[i];
        }
        for (unsigned i = 0; i < std::size(StageExtensionPrintCalls); ++i)
        {
            const int rva = StageExtensionPrintCalls[i];
            StageExtensionPrintEnterHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva), StageExtensionEnter);
            StageExtensionPrintLeaveHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva + 5), StageExtensionLeave);
            stageExtensionOk = stageExtensionOk &&
                StageExtensionPrintEnterHooks[i] &&
                StageExtensionPrintLeaveHooks[i];
        }
        if (!stageExtensionOk)
        {
            for (unsigned i = 0; i < std::size(StageExtensionSpraniCalls); ++i)
            {
                StageExtensionEnterHooks[i] = {};
                StageExtensionLeaveHooks[i] = {};
            }
            for (unsigned i = 0; i < std::size(StageExtensionPrintCalls); ++i)
            {
                StageExtensionPrintEnterHooks[i] = {};
                StageExtensionPrintLeaveHooks[i] = {};
            }
            spdlog::warn(
                "VR P0 +TIME: incomplete 0x989xx sprani/print parent hook; rolled back all six");
        }
        else
            spdlog::info(
                "VR P0 +TIME: 3 original sprani + 3 print E8 parents -> SCREEN_HUD (game animation unchanged)");

        // Inline E8 parent hooks are installed atomically; a partially
        // bracketed result print sequence could tag only half the large
        // record digits and cause an eye-to-eye double image.
        bool resultTextOk = true;
        for (unsigned i = 0; i < std::size(ResultTextB9200Calls); ++i)
        {
            const int rva = ResultTextB9200Calls[i];
            ResultTextEnterHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva), ResultTextEnter);
            ResultTextLeaveHooks[i] = safetyhook::create_mid(
                Module::exe_ptr(rva + 5), ResultTextLeave);
            resultTextOk = resultTextOk &&
                ResultTextEnterHooks[i] && ResultTextLeaveHooks[i];
        }
        if (!resultTextOk)
        {
            for (unsigned i = 0; i < std::size(ResultTextB9200Calls); ++i)
            {
                ResultTextEnterHooks[i] = {};
                ResultTextLeaveHooks[i] = {};
            }
            spdlog::error(
                "VR P0 RESULT TEXT: exact B9200 print parent midhooks incomplete; rolled back");
        }
        else
            spdlog::info(
                "VR P0 RESULT TEXT: 19 original result/stage B9200 parent CALLs -> SCREEN_HUD");

		// The two GOAL CALLs are adjacent, so preserve the original function
		// signatures and redirect only their individually proven E8 edges.
		Memory::VP::InjectHook(Module::exe_ptr(GoalTimeHelperCallA),
			GoalTime_Help020, Memory::HookType::Call);
		Memory::VP::InjectHook(Module::exe_ptr(GoalTimeHelperCallB),
			GoalTime_Help150, Memory::HookType::Call);
		spdlog::info(
			"VR P0 GOAL/RESULT: exact result-progress and two GOAL helper producer owners restored (HMD validation pending)");

		spdlog::info(
			"VR HUD RESTORE: exact option arrows/result clips/text glyphs -> SCREEN_HUD; rank/rival markers -> PROJECTED_WORLD_MARKER_2D when Calc3D2D anchor is valid, WORLD_BILLBOARD fallback otherwise");

		NaviPub_Disp_SpriteSpacingEnable_hk = safetyhook::create_mid(Module::exe_ptr(NaviPub_Disp_SpriteScaleEnable_Addr), SpriteSpacingEnable);
		NaviPub_Disp_SpriteSpacingEnable2_hk = safetyhook::create_mid(Module::exe_ptr(NaviPub_Disp_SpriteScaleEnable2_Addr), SpriteSpacingEnable);
		NaviPub_Disp_SpriteSpacingDisable_hk = safetyhook::create_mid(Module::exe_ptr(NaviPub_Disp_SpriteScaleDisable_Addr), SpriteSpacingDisable);
		NaviPub_Disp_SpriteSpacingDisable2_hk = safetyhook::create_mid(Module::exe_ptr(NaviPub_Disp_SpriteScaleDisable2_Addr), SpriteSpacingDisable);
		NaviPub_Disp_HeartDisableScaling_hk = safetyhook::create_mid((void*)0x4BEBE1, SpriteSpacingDisable);
		NaviPub_Disp_HeartEnableScaling_hk = safetyhook::create_mid((void*)0x4BEBE6, SpriteSpacingEnable);

		NaviPub_Disp_C2CHeartDisableScaling_hk = safetyhook::create_mid((void*)0x481B76, SpriteSpacingDisable);
		NaviPub_Disp_C2CHeartEnableScaling_hk = safetyhook::create_mid((void*)0x4BECBA, SpriteSpacingEnable);
		NaviPub_Disp_C2CHeartEnableScaling2_hk = safetyhook::create_mid((void*)0x4BECE0, SpriteSpacingEnable);

		NaviPub_Disp_C2CFruitDisableScaling_hk = safetyhook::create_mid((void*)0x481A86, SpriteSpacingDisable);
		NaviPub_Disp_C2CFruitEnableScaling_hk = safetyhook::create_mid((void*)0x481A8B, SpriteSpacingEnable);

		NaviPub_Disp_RivalDisableScaling_hk = safetyhook::create_mid((void*)0x4BEB8E, SpriteSpacingDisable);
		NaviPub_Disp_RivalEnableScaling_hk = safetyhook::create_mid((void*)0x4BEBAF, SpriteSpacingEnable);
		NaviPub_Disp_RivalOnlineDisableScaling_hk = safetyhook::create_mid((void*)0x4BEC83, SpriteSpacingDisable);
		NaviPub_Disp_RivalOnlineEnableScaling_hk = safetyhook::create_mid((void*)0x4BEC88, SpriteSpacingEnable);

		// dispMarkerCheck is called by all three rival-marker functions, hopefully can fix them all
		dispMarkerCheck_SpriteScalingDisable_hk = safetyhook::create_mid((void*)0x4BA0E0, SpriteSpacingDisable);

		drawFootage = safetyhook::create_mid(Module::exe_ptr(drawFootage_caller_Addr), drawFootage_dest);

		// Hook the DrawPrimitiveUP call inside the three custom_matrix_multi cases so we can fix up X position
		// (except case3 doesn't point to the scaled-position-array for some reason, so we have to hook slightly earlier)
		draw_sprite_custom_matrix_multi_CenterSprite_hk = safetyhook::create_mid(Module::exe_ptr(draw_sprite_custom_matrix_multi__case2_Addr), draw_sprite_custom_matrix_multi_CenterSprite);
		draw_sprite_custom_matrix_multi_CenterSprite2_hk = safetyhook::create_mid(Module::exe_ptr(draw_sprite_custom_matrix_multi__case3_Addr), draw_sprite_custom_matrix_multi_CenterSprite2);
		draw_sprite_custom_matrix_multi_CenterSprite3_hk = safetyhook::create_mid(Module::exe_ptr(draw_sprite_custom_matrix_multi__case4_Addr), draw_sprite_custom_matrix_multi_CenterSprite3);

		// Fixes for the time displays in time attack mode
		DispTimeAttack2D_SpriteScalingForceRight_hk = safetyhook::create_mid((void*)0x4BE4BC, SpriteSpacingForceRight);
		DispTimeAttack2D_SpriteScalingDisable_hk = safetyhook::create_mid((void*)0x4BE4C1, SpriteSpacingDisable);
		DispTimeAttack2D_SpriteScalingForceLeft_hk = safetyhook::create_mid((void*)0x4BE4E7, SpriteSpacingForceLeft);
		DispTimeAttack2D_SpriteScalingForceEnable_hk = safetyhook::create_mid((void*)0x4BE575, SpriteSpacingEnable);


























		// REV indicator


		DispGearPosition_put_scroll_AdjustPosition_hk3 = safetyhook::create_mid((void*)0x4B90F6, put_scroll_AdjustPositionLeft);

		// Fix ghost car info text positions
		PutGhostGapInfo_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDE3A, PutGhostGapInfo_AdjustPosition);
		DispGhostGap_ForceLeft_hk = safetyhook::create_mid((void*)0x4BE045, SpriteSpacingForceLeft);
		DispGhostGap_ForceLeft2_hk = safetyhook::create_mid((void*)0x4BE083, SpriteSpacingForceLeft);
		DispGhostGap_ForceRight_hk = safetyhook::create_mid((void*)0x4BE0A5, SpriteSpacingForceRight);
		DispGhostGap_ForceRight2_hk = safetyhook::create_mid((void*)0x4BE067, SpriteSpacingForceRight);

		PutGhostGapInfo_sub_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDAE8, PutGhostGapInfo_sub_AdjustPosition);

		NaviPub_DispTimeAttackGoal_DisableScaling_hk = safetyhook::create_mid((void*)0x4BEA64, SpriteSpacingDisable);

		// adjusts the girlfriend request speech bubble
		ctrl_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460D40, ctrl_icon_work_AdjustPosition);
		ctrl_icon_work_AdjustPosition2_hk = safetyhook::create_mid((void*)0x460FBC, ctrl_icon_work_AdjustPosition2);
		set_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460A21, ctrl_icon_work_AdjustPosition2); // set_icon_work can use same logic as ctrl_icon_work_AdjustPosition2

		// "-" text when negative heart score
		DispTempHeartNum_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BBA89, DispTempHeartNum_AdjustPosition);

		// C2C-specific speech bubbles
		C2CSpeechBubble_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x496AC7, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x496B14, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x496B39, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x496B94, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x496BE1, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x496C10, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubble_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x496C6A, C2CSpeechBubble_AdjustPositionESP0);

		C2CSpeechBubbleGF_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FCDC1, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FCDEA, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FCEB0, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FCED9, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x4FCF22, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x4FCF4F, C2CSpeechBubble_AdjustPositionESP0);

		// unsure if this has any effect...
		C2CSpeechBubbleGF_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x4FE8B1, C2CSpeechBubble_AdjustPositionESP0);

		// 4FD1A9 seemed related but no effect?
		C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FD60C, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FD591, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FD5CD, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FD652, C2CSpeechBubble_AdjustPositionESP0);

		// ranking emoji position
		C2CSpeechBubbleGF_AdjustPositionESP0_hk8 = safetyhook::create_mid((void*)0x4FC84E, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk9 = safetyhook::create_mid((void*)0x4FC882, C2CSpeechBubble_AdjustPositionESP0);

		// "rank: aaa" position
		C2CSpeechBubbleGF_AdjustPositionESP0_hk10 = safetyhook::create_mid((void*)0x4FC8B4, C2CSpeechBubble_AdjustPositionESP0);

		// speech bubble initial position
		C2CSpeechBubbleGF_AdjustPositionESP0_hk11 = safetyhook::create_mid((void*)0x4FC9EB, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk12 = safetyhook::create_mid((void*)0x4FCA1E, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk13 = safetyhook::create_mid((void*)0x4FCA51, C2CSpeechBubble_AdjustPositionESP0);
		C2CSpeechBubbleGF_AdjustPositionESP0_hk14 = safetyhook::create_mid((void*)0x4FCB20, C2CSpeechBubble_AdjustPositionESP4);

		// "don't lose your girlfriend" UI sprites




		// "test your slipstream" rival text


		return true;
	}
	static UIScaling instance;
};

UIScaling UIScaling::instance;

// R64 source restoration. The original user's HMD R64 test showed 6th/6
// single and HudScale effective only after the exact D3DXSprite Draw/Flush
// isolation existed. R62 already restores the FVF0x142 *GPU* draw owner;
// that alone does not force distinct queued D3DXSprite items to become
// distinct DrawIndexedPrimitive calls. Keep batch isolation strictly on
// screen-projected rank markers or the DispRank-specific kind0/kind1
// original callsites; never flush unrelated menu, GOAL, +TIME or HUD sprites.
class VRProjectedD3DXSpriteIsolationR64 : public Hook
{
	inline static SafetyHookInline Draw_hk{};
	inline static std::atomic<std::uint64_t> Flushes{ 0 };
	inline static std::atomic<std::uint64_t> Failures{ 0 };

	static HRESULT __stdcall DrawDest(
		void* self, IDirect3DTexture9* texture, const RECT* rect,
		const D3DVECTOR* center, const D3DVECTOR* pos, D3DCOLOR color)
	{
		const HRESULT hr = Draw_hk.stdcall<HRESULT>(
			self, texture, rect, center, pos, color);
		if (FAILED(hr) || !self ||
			!OutRunVR::GameSemantic::QueueRenderActive())
			return hr;

		const auto scope = OutRunVR::GameSemantic::EffectiveScope();
		const auto* marker =
			OutRunVR::GameSemantic::CurrentProjectedMarker();
		const auto source =
			OutRunVR::GameSemantic::CurrentQueueProducerToken();
		// Modern R84 also uses ProjectedWorldMarker2D for the rival-car
		// icon, which was already HMD-correct and must NOT receive an
		// unrelated new Flush. R64's old broad projected scope was
		// primarily the car rank 1..5 owner; here prove the exact original
		// rank E8 source to avoid widening the restored old batch policy.
		const bool projectedRank =
			OutRunVR::GameSemantic::CorroboratesProjectedWorldMarker(
				scope) && marker && marker->valid &&
			(source ==
				OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani ||
				source ==
				OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite);
		const bool dispRankHud =
			OutRunVR::GameSemantic::CorroboratesHud(scope) &&
			(source ==
				OutRunVR::GameSemantic::ProducerToken::DispRankFirst ||
				source ==
				OutRunVR::GameSemantic::ProducerToken::DispRankClipSprite);
		if (!projectedRank && !dispRankHud)
			return hr;

		void** vtable = *reinterpret_cast<void***>(self);
		if (!vtable || !vtable[10])
			return hr;

		using FlushFn = HRESULT(__stdcall*)(void*);
		const HRESULT flushHr =
			reinterpret_cast<FlushFn>(vtable[10])(self);
		const auto count = Flushes.fetch_add(
			1, std::memory_order_relaxed) + 1;
		if (FAILED(flushHr))
			Failures.fetch_add(1, std::memory_order_relaxed);
		if ((count & (count - 1)) == 0)
			spdlog::info(
				"VR R64 D3DX ISOLATE RESTORED: owner={} producer={} flushes={} failures={} markerValid={}",
				projectedRank ? "projected-rank" : "disprank-hud",
				OutRunVR::GameSemantic::Name(source),
				count, Failures.load(std::memory_order_relaxed),
				marker && marker->valid ? 1 : 0);
		return hr;
	}

	static DWORD WINAPI InstallThread(void*)
	{
		// This is the original HMD-verified R64 D3DXSprite pointer/ABI and
		// method layout on the canonical replacement EXE, not a global
		// ID3DXSprite trampoline for unrelated assets.
		for (int attempt = 0; attempt < 7200; ++attempt)
		{
			void* sprite = *Module::exe_ptr<void*>(0x55B218);
			if (sprite)
			{
				void** vtable = *reinterpret_cast<void***>(sprite);
				if (vtable && vtable[9] && vtable[10])
				{
					const auto disabled =
						safetyhook::InlineHook::StartDisabled;
					Draw_hk = safetyhook::create_inline(
						vtable[9], reinterpret_cast<void*>(&DrawDest),
						disabled);
					if (Draw_hk && Draw_hk.enable().has_value())
					{
						spdlog::info(
							"VR R64 D3DX ISOLATE RESTORED: only projected rank + exact DispRank kind0/kind1 post-Draw Flush; result/+TIME and generic HUD excluded");
						return 0;
					}
					Draw_hk = {};
				}
			}
			Sleep(25);
		}
		spdlog::warn(
			"VR R64 D3DX ISOLATE: exact ID3DXSprite Draw hook unavailable; original no-flush behavior retained");
		return 0;
	}

public:
	std::string_view description() override
	{
		return "VRProjectedD3DXSpriteIsolationR64";
	}
	bool validate() override
	{
		return Settings::VREnabled.get();
	}
	bool apply() override
	{
		HANDLE thread = CreateThread(
			nullptr, 0, InstallThread, nullptr, 0, nullptr);
		if (!thread)
			return false;
		CloseHandle(thread);
		return true;
	}
	static VRProjectedD3DXSpriteIsolationR64 instance;
};
VRProjectedD3DXSpriteIsolationR64
	VRProjectedD3DXSpriteIsolationR64::instance;

// VR semantic bridge for the game's canonical queued 2D renderer.
// Canonical replacement EXE SHA256:
// 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3
// Static reverse analysis proves:
//   RVA 0x2D734 = queue-entry context only; DO NOT hook this address,
//   RVA 0x2D762 = per-node iteration with EDI = SpriteNode*,
//   RVA 0x2DCB4 = common epilogue.
// Runtime crash signatures at EXE+0x2D738 and EXE+0x2D73E proved that a
// SafetyHookMid at 0x2D734 can resume inside the relocated prologue.
// Queue scope therefore starts lazily at the first real node (0x2D762).
// This is deliberately semantic, not a draw-state heuristic. The queue hook
// selects an explicit tag when present. Untagged nodes use SCREEN_OVERLAY_2D:
    // asymmetric-FOV alignment only, never finite HUD-plane/world-lock. Exact
    // producer/call-site evidence may register SCREEN_HUD or WORLD_BILLBOARD.
class VRHudQueueSemanticBridge : public Hook
{
	inline static SafetyHookMid QueueNode_hk{};
	inline static SafetyHookMid QueueEnd_hk{};

	static void QueueNode(SafetyHookContext& ctx)
	{
		OutRunVR::GameSemantic::SelectSpriteQueueNode(
			reinterpret_cast<const void*>(ctx.edi));
	}

	static void QueueEnd(SafetyHookContext&)
	{
		OutRunVR::GameSemantic::EndSpriteQueueRender();
	}

public:
	std::string_view description() override
	{
		return "VRHudQueueSemanticBridge";
	}

	bool validate() override
	{
		return Settings::VREnabled.get();
	}

	bool apply() override
	{
		QueueNode_hk = safetyhook::create_mid(
			Module::exe_ptr(0x2D762), QueueNode);
		QueueEnd_hk = safetyhook::create_mid(
			Module::exe_ptr(0x2DCB4), QueueEnd);

		const bool ok = QueueNode_hk && QueueEnd_hk;
		if (!ok)
		{
			// The semantic bridge is all-or-nothing. Never leave a partial
			// queue hook alive after a failed install.
			QueueNode_hk = {};
			QueueEnd_hk = {};
		}
		if (ok)
		{
			spdlog::info(
				"VR HUD SEMANTIC R50: sprite queue node 0x2D762 selects explicit tags; untagged nodes use SCREEN_OVERLAY_2D FOV-only alignment; unsafe 0x2D734 entry hook is forbidden; original-mod tagged rival nodes remain WORLD_BILLBOARD");
		}
		else
		{
			spdlog::error(
				"VR HUD SEMANTIC: failed to install canonical sprite-queue ownership hooks; semantic HUD promotion disabled");
		}
		return ok;
	}

	static VRHudQueueSemanticBridge instance;
};
VRHudQueueSemanticBridge VRHudQueueSemanticBridge::instance;
