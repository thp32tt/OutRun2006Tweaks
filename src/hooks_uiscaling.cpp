#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/hud_command_batch.hpp"
#include "vr/game/goal_result_parent_provenance.hpp"
#include "vr/game/sprite_queue_tail_proof.hpp"
#include "vr/game/rank_marker_fraction.hpp"
#include "vr/hud_semantics.hpp"
#include "vr/ui/ui_side_spacing.hpp"
#include "vr/ui/menu_quad_transform.hpp"
#include "vr/ui/multi_sprite_contain_scale.hpp"
#include "vr/ui/frontend_affine_contain.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <optional>

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

namespace
{
    constexpr float CenterMultiSpriteAxis(
    	float pixel, float axisScale, float containScale,
    	float screenExtent, float originalExtent) noexcept
    {
    	return (pixel / axisScale) * containScale +
    		(screenExtent - originalExtent * containScale) * 0.5f;
    }

    // Deterministic Win32 compile-time coordinate regressions: native 4:3,
    // 16:9, 21:9 and portrait XR (including top/bottom Y letterbox).
    static_assert(CenterMultiSpriteAxis(640.0f, 2.0f, 2.0f, 1280.0f, 640.0f) == 640.0f);
    static_assert(CenterMultiSpriteAxis(960.0f, 3.0f, 2.25f, 1920.0f, 640.0f) == 960.0f);
    static_assert(CenterMultiSpriteAxis(1280.0f, 4.0f, 2.25f, 2560.0f, 640.0f) == 1280.0f);
    static_assert(CenterMultiSpriteAxis(0.0f, 2.5f, 1.25f, 1200.0f, 480.0f) == 300.0f);
    static_assert(CenterMultiSpriteAxis(1200.0f, 2.5f, 1.25f, 1200.0f, 480.0f) == 900.0f);


    // A rotation-only D3DXMatrixTransformation2D call can legitimately omit
    // both optional scale/translation vectors. The old (scale || translate)
    // prerequisite skipped whole-matrix containment for such menu/car-select
    // sprites and left the already rotated art anisotropically stretched.
    // Keep identity/unsupported states, gameplay HUD and F11 unchanged.
    constexpr bool NeedsFrontEndAffineContain(
        bool exactFrontEnd, bool containedMode,
        bool hasScale, bool hasTranslation, bool hasScaleCenter,
        bool hasRotationCenter, float scaleRotation, float rotation) noexcept
    {
        return exactFrontEnd && containedMode &&
            (hasScale || hasTranslation || rotation != 0.0f) &&
            (hasScaleCenter || hasRotationCenter ||
             scaleRotation != 0.0f || rotation != 0.0f);
    }

    static_assert(NeedsFrontEndAffineContain(
        true, true, false, false, false, false, 0, 1.5707963f),
        "Rotation-only title sprites must use full affine containment");
    static_assert(NeedsFrontEndAffineContain(
        true, true, false, false, false, true, 0, 0.35f),
        "Pivoted rotation-only vehicle sprites must retain source aspect");
    static_assert(NeedsFrontEndAffineContain(
        true, true, true, false, true, false, 0, 0),
        "Pivoted scale-only sprites must retain source aspect");
    static_assert(NeedsFrontEndAffineContain(
        true, true, false, true, false, true, 0, 0),
        "Translation with an authored pivot retains the old transform path");
    static_assert(!NeedsFrontEndAffineContain(
        true, true, false, false, true, true, 0, 0),
        "Unused centres alone cannot justify rewriting an identity matrix");
    static_assert(!NeedsFrontEndAffineContain(
        true, true, false, false, true, false, 0.75f, 0),
        "Scale rotation without a scale vector is not an authored transform");
    static_assert(!NeedsFrontEndAffineContain(
        false, true, false, false, false, false, 0, 1),
        "Never transform gameplay HUD/GOAL/+TIME through the front end");
    static_assert(!NeedsFrontEndAffineContain(
        true, false, false, false, false, false, 0, 1),
        "Vanilla must preserve the original menu matrix");

    // The six +TIME caller tails are snapshots, not owned queue pointers.
    // Validate both boundaries against the live chain before dereferencing
    // any old tail (which may have been freed by a nested queue rebuild).
    template<class Node>
    constexpr Node* StageFirstAppendedNode(
        Node* root, Node* oldTail, Node* newTail, unsigned bound) noexcept
    {
        // All exact GOAL/rank/+TIME owners share the SAME production queue
        // reachability proof, including the stack-proven B9200 glyph family.
        return OutRunVR::SpriteQueue::FirstVerifiedAppendedNode(
            root, oldTail, newTail, bound);
    }

    struct StageTailFixture { StageTailFixture* next_0 = nullptr; };
    constexpr bool TestStageFirstAppendedNode() noexcept
    {
        StageTailFixture root{}, first{}, old{}, newest{}, stale{};
        root.next_0 = &first;
        first.next_0 = &old;
        old.next_0 = &newest;
        return StageFirstAppendedNode(&root, &old, &newest, 4) == &newest &&
            StageFirstAppendedNode<StageTailFixture>(
                &root, nullptr, &newest, 4) == &first &&
            StageFirstAppendedNode(&root, &stale, &newest, 4) == nullptr &&
            StageFirstAppendedNode(&root, &old, &old, 4) == nullptr &&
            StageFirstAppendedNode(&root, &old, &newest, 2) == nullptr &&
            StageFirstAppendedNode(&root, &old, &newest, 3) == &newest;
    }
    static_assert(TestStageFirstAppendedNode(),
        "+TIME must not read or relabel a stale source queue tail");

    // Multi-child rank and GOAL producers can append several queue nodes.
    // Retain both live siblings without consulting a detached old tail.
    constexpr bool TestExactRankGoalSiblingTailProof() noexcept
    {
        StageTailFixture root{}, old{}, first{}, second{}, stale{};
        root.next_0 = &old;
        old.next_0 = &first;
        first.next_0 = &second;
        if (StageFirstAppendedNode(&root, &old, &second, 4) != &first ||
            StageFirstAppendedNode(&root, &stale, &second, 4))
            return false;
        // A nested producer replaced the original priority-list chain.
        root.next_0 = &first;
        return StageFirstAppendedNode(&root, &old, &second, 3) == nullptr &&
            StageFirstAppendedNode<StageTailFixture>(
                &root, nullptr, &second, 3) == &first;
    }
    static_assert(TestExactRankGoalSiblingTailProof(),
        "Exact GOAL/rank producers must not tag a rebuilt foreign queue");

    // Compose the matrix AFTER D3DX applies scaling/rotation pivots.
    // Changing only pScaling/pTranslation uses a different pivot basis and
    // distorts rotated menu art at portrait and ultrawide aspect ratios.
    struct UiMatrix2DRows { float m11, m12, m21, m22, tx, ty; };
    constexpr UiMatrix2DRows ContainUiMatrixRows(
        UiMatrix2DRows m, float sx, float sy,
        float shiftX, float shiftY) noexcept
    {
        return {m.m11 * sx, m.m12 * sy,
            m.m21 * sx, m.m22 * sy,
            m.tx * sx + shiftX, m.ty * sy + shiftY};
    }
    // Rotation, translation and native 4:3 identity: actual source-header
    // compile-time regressions, not telemetry or a string-only verifier.
    static_assert(ContainUiMatrixRows(
        {0, 4, -4, 0, 48, 80}, 1, 0.5f, 0, 120).m12 == 2);
    static_assert(ContainUiMatrixRows(
        {0, 4, -4, 0, 48, 80}, 1, 0.5f, 0, 120).m21 == -4);
    static_assert(ContainUiMatrixRows(
        {0, 4, -4, 0, 48, 80}, 1, 0.5f, 0, 120).ty == 160);
    static_assert(ContainUiMatrixRows(
        {2, 0, 0, 2, 16, 20}, 1, 1, 0, 0).tx == 16);

}

// The exact D3DX sprite hook is declared below the original +TIME source.
// Split any proven previous batch BEFORE the original direct glyph obtains
// ScreenHud ownership, not after its Draw may have submitted old triangles.
static void FlushD3DXBeforeDirectStageSource() noexcept;
static void FlushD3DXAtDirectStageSourceExit() noexcept;
static void FlushD3DXBeforeDirectGoalSource() noexcept;
static void FlushD3DXAtDirectGoalSourceExit() noexcept;

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
	// Only exact driving peripheral producers may opt in to VR edge layout.
	// Keep GOAL/+TIME, C2C controls, speech, and unknown text on old HUD paths.
	inline static thread_local bool OutRunHudPeripheralText = false;
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
    // Two user minidumps (23:33:04 and 23:35:50 KST, exact test SHA
    // 9e393cfd) both faulted with 0xC0000096 at EXE+0x97C5F.
    // The installed SafetyHookMid at 0x97C57 + 5 = 0x97C5C overwrote
    // bytes 0x97C5C..0x97C60 with E9 rel32, and 0x97C5F lies INSIDE
    // that jump displacement. The original result branch can arrive at
    // 0x97C5F, so this is not a safe midhook placement. Keep the
    // original 0x97C57 E8 CALL completely unmodified until a verified
    // CALL-ABI wrapper can replace this parent without a post-CALL detour.
    // All nineteen result text E8 parents must remain untouched until a
    // verified ABI-safe wrapper exists: minidumps EIP 0x97C5F / 0x97E75.
    static constexpr int ResultTextUnsafeReturnRva = 0x97C57;

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
    // R57/R62 Quest3 known-good calls the original Calc3D2D from
    // EXE+0xBAEE2. Source 9e393cfd/b913ef69 logged rank glyphs but no
    // exact Calc3D2D event, causing world-marker projection to remain zero.
    // Bind this exact CALL edge, rather than relying on _ReturnAddress()
    // from the shared 0x49940 inline trampoline alone.
    inline static thread_local bool RankMarkerExactCalcEdge = false;

	// D3DXMatrixTransformation2D hook allows us to change draw_sprite_custom
	static inline SafetyHookInline D3DXMatrixTransformation2D = {};
	static int __stdcall D3DXMatrixTransformation2D_dest(D3DMATRIX* pOut, D3DXVECTOR2* pScalingCenter, float pScalingRotation,
		D3DXVECTOR2* pScaling, D3DXVECTOR2* pRotationCenter, float Rotation, D3DXVECTOR2* pTranslation)
	{
		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		// D3DX treats these input vectors as read-only. The game may reuse
		// the same source sprite matrix across menu/car-selection draws;
		// do not accumulate our aspect correction in the caller's storage.
		D3DXVECTOR2 localScaling{};
		D3DXVECTOR2 localTranslation{};
		D3DXVECTOR2* forwardedScaling = pScaling;
		D3DXVECTOR2* forwardedTranslation = pTranslation;


        // Complete 2D composition is required when the game supplies a
        // non-origin scale/rotation pivot. Only title/menu/car-selection
        // producers take this path; other visual owners remain unchanged.
        const bool frontEndPivot = NeedsFrontEndAffineContain(
            Game::current_mode &&
                (*Game::current_mode == GameState::STATE_TITLE ||
                 *Game::current_mode == GameState::STATE_MENU ||
                 *Game::current_mode == GameState::STATE_SELECTOR ||
                 *Game::current_mode == GameState::STATE_SELEXIT ||
                 *Game::current_mode == GameState::STATE_SELRESET),
            mode == ScalingMode::KeepCentered ||
                mode == ScalingMode::OnlineArcade,
            pScaling != nullptr, pTranslation != nullptr,
            pScalingCenter != nullptr, pRotationCenter != nullptr,
            pScalingRotation, Rotation);
		// D3DX allows optional 2D scaling/translation inputs. During resolution
		// or device reset the game scale may also be invalid. Preserve input
		// values and forward the original call when reprojection is unsafe.
        if (!frontEndPivot && (mode == ScalingMode::KeepCentered ||
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
                std::isfinite(Game::screen_resolution->y) &&
                std::isfinite(Game::original_resolution.x) &&
                std::isfinite(Game::original_resolution.y))
			{
				const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(
                    sx, sy, Game::screen_resolution->x,
                    Game::screen_resolution->y, Game::original_resolution.x,
                    Game::original_resolution.y);
				const float xScale = affine.ScaleX(pScaling->x);
				const float yScale = affine.ScaleY(pScaling->y);
				const float centeredX = affine.MapX(pTranslation->x);
                const float centeredY = affine.MapY(pTranslation->y);
                // Complete the finite check before mutating any in/out argument.
				if (affine.valid && std::isfinite(xScale) && std::isfinite(yScale) &&
				    std::isfinite(centeredX) && std::isfinite(centeredY))
				{
					// Publish both derived vectors only after every component is
					// finite. The game's original vectors remain byte-for-byte stable.
					localScaling.x = xScale;
					localScaling.y = yScale;
					localTranslation.x = centeredX;
					localTranslation.y = centeredY;
					forwardedScaling = &localScaling;
					forwardedTranslation = &localTranslation;
				}
			}
		}


        // D3DX accepts independent nullable scale/translation vectors.
        // The full-vector path above is deliberately unchanged. In title/menu
        // and car selection, one absent vector used to bypass 4:3 containment
        // entirely: preserve the supplied input, treat the missing one as the
        // documented identity (scale=1, translation=0), then stage BOTH output
        // vectors so only these partial front-end draws gain containment.
        // Never widen this path into gameplay HUD, GOAL/+TIME, F11 or pause.
        const bool partialFrontEndMenu = Game::current_mode &&
            (*Game::current_mode == GameState::STATE_TITLE ||
             *Game::current_mode == GameState::STATE_MENU ||
             *Game::current_mode == GameState::STATE_SELECTOR ||
             *Game::current_mode == GameState::STATE_SELEXIT ||
             *Game::current_mode == GameState::STATE_SELRESET);
        if (!frontEndPivot && partialFrontEndMenu &&
            (mode == ScalingMode::KeepCentered ||
             mode == ScalingMode::OnlineArcade) &&
            ((pScaling == nullptr) != (pTranslation == nullptr)) &&
            Game::screen_scale && Game::screen_resolution)
        {
            const float sourceSx = Game::screen_scale->x;
            const float sourceSy = Game::screen_scale->y;
            const float srcWidth = Game::original_resolution.x;
            const float srcHeight = Game::original_resolution.y;
            const float dstWidth = Game::screen_resolution->x;
            const float dstHeight = Game::screen_resolution->y;
            const float inputSx = pScaling ? pScaling->x : 1.0f;
            const float inputSy = pScaling ? pScaling->y : 1.0f;
            const float inputTx = pTranslation ? pTranslation->x : 0.0f;
            const float inputTy = pTranslation ? pTranslation->y : 0.0f;
            if (std::isfinite(sourceSx) && std::isfinite(sourceSy) &&
                sourceSx > 1.0e-6f && sourceSy > 1.0e-6f &&
                std::isfinite(srcWidth) && std::isfinite(srcHeight) &&
                srcWidth > 0.0f && srcHeight > 0.0f &&
                std::isfinite(dstWidth) && std::isfinite(dstHeight) &&
                dstWidth > 0.0f && dstHeight > 0.0f &&
                std::isfinite(inputSx) && std::isfinite(inputSy) &&
                std::isfinite(inputTx) && std::isfinite(inputTy))
            {
                const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(
                    sourceSx, sourceSy, dstWidth, dstHeight,
                    srcWidth, srcHeight);
                const float nextSx = affine.ScaleX(inputSx);
                const float nextSy = affine.ScaleY(inputSy);
                const float nextTx = affine.MapX(inputTx);
                const float nextTy = affine.MapY(inputTy);
                if (affine.valid && std::isfinite(nextSx) && std::isfinite(nextSy) &&
                    std::isfinite(nextTx) && std::isfinite(nextTy))
                {
                    localScaling.x = nextSx;
                    localScaling.y = nextSy;
                    localTranslation.x = nextTx;
                    localTranslation.y = nextTy;
                    forwardedScaling = (&localScaling);
                    forwardedTranslation = (&localTranslation);
                }
            }
        }

        const int result = D3DXMatrixTransformation2D.stdcall<int>(
            pOut, pScalingCenter, pScalingRotation,
            forwardedScaling, pRotationCenter, Rotation, forwardedTranslation);
        if (frontEndPivot && result && pOut &&
            Game::screen_scale && Game::screen_resolution)
        {
            const float sx = Game::screen_scale->x;
            const float sy = Game::screen_scale->y;
            const float width = Game::screen_resolution->x;
            const float height = Game::screen_resolution->y;
            const float sourceWidth = Game::original_resolution.x;
            const float sourceHeight = Game::original_resolution.y;
            if (std::isfinite(sx) && std::isfinite(sy) &&
                std::isfinite(width) && std::isfinite(height) &&
                std::isfinite(sourceWidth) && std::isfinite(sourceHeight) &&
                sx > 1.0e-6f && sy > 1.0e-6f &&
                width > 0.0f && height > 0.0f &&
                sourceWidth > 0.0f && sourceHeight > 0.0f)
            {
                const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(
                    sx, sy, width, height, sourceWidth, sourceHeight);
                const float ratioX = affine.ratioX;
                const float ratioY = affine.ratioY;
                const float offsetX = affine.offsetX;
                const float offsetY = affine.offsetY;
                const UiMatrix2DRows raw{pOut->_11, pOut->_12,
                    pOut->_21, pOut->_22, pOut->_41, pOut->_42};
                const auto mapped = ContainUiMatrixRows(
                    raw, ratioX, ratioY, offsetX, offsetY);
                // Publish the entire corrected sprite matrix atomically;
                // unknown/projective or non-finite states retain the original.
                if (affine.valid && std::isfinite(mapped.m11) && std::isfinite(mapped.m12) &&
                    std::isfinite(mapped.m21) && std::isfinite(mapped.m22) &&
                    std::isfinite(mapped.tx) && std::isfinite(mapped.ty) &&
                    pOut->_44 == 1.0f && pOut->_14 == 0.0f &&
                    pOut->_24 == 0.0f)
                {
                    pOut->_11 = mapped.m11;
                    pOut->_12 = mapped.m12;
                    pOut->_21 = mapped.m21;
                    pOut->_22 = mapped.m22;
                    pOut->_41 = mapped.tx;
                    pOut->_42 = mapped.ty;
                }
            }
        }
        return result;
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
             !std::isfinite(Game::screen_resolution->y) ||
             !std::isfinite(Game::original_resolution.x) ||
             !std::isfinite(Game::original_resolution.y)))
			return;

		D3DSURFACE_DESC v25{};
		const HRESULT descHr =
			a1->d3dtexture_ptr_C->GetLevelDesc(0, &v25);
		if (FAILED(descHr) || v25.Width == 0 || v25.Height == 0)
			return;
		// Validate and stage the entire original game menu/car-selection quad.
		// A failed eye/reset transform must not publish half of a quad into
		// the shared game vertex stream or submit non-finite screen vertices.
		auto* device = Game::D3DDevice();
		if (!device)
			return;
		std::array<float, 28> quad{};

		float v21 = 0.50999999 / (double)v25.Width;
		float v22 = 0.50999999 / (double)v25.Height;

		D3DMATRIX pM;
		memcpy(&pM, &a1->mtx_14, sizeof(pM));

		D3DXVECTOR4 vec;

		D3DXVECTOR4 topLeft{ 0 };
		D3DXVECTOR4 bottomLeft{ 0 };
		D3DXVECTOR4 topRight{ 0 };
		D3DXVECTOR4 bottomRight{ 0 };

        // Apply one aspect map to all four source-transformed corners.
        // Vanilla front-end X has its own scale; preserve the historical
        // gameplay/GOAL fallback and existing 4:3 contained menu modes.
        const bool contained =
            mode == ScalingMode::KeepCentered ||
            mode == ScalingMode::OnlineArcade;
        const bool vanillaFrontEnd =
            mode == ScalingMode::Vanilla && Game::current_mode &&
            (*Game::current_mode == GameState::STATE_TITLE ||
             *Game::current_mode == GameState::STATE_MENU ||
             *Game::current_mode == GameState::STATE_SELECTOR ||
             *Game::current_mode == GameState::STATE_SELEXIT ||
             *Game::current_mode == GameState::STATE_SELRESET);
        const auto quadMap = OutRunVrMenuQuad::BuildPixelMap(
            contained, vanillaFrontEnd, screenScaleX, screenScaleY,
            Game::screen_resolution ? Game::screen_resolution->x : 0.0f,
            Game::screen_resolution ? Game::screen_resolution->y : 0.0f,
            Game::original_resolution.x, Game::original_resolution.y);
        if (!quadMap.valid)
            return;

        // X and Y must use the SAME viewport-bounded map for the entire
        // authored quad. The previous independent Y formula could still
        // use stale screen_scale and clip bottom-right on Reset/resize.
        // Non-contained/Vanilla mode retains its original screenScaleY.

		// TopLeft
		vec.x = a1->TopLeft_54.x;
		vec.y = a1->TopLeft_54.y;
		vec.z = a1->TopLeft_54.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&topLeft, &vec, &pM);

		quad[1] = OutRunVrMenuQuad::ProjectY(quadMap, topLeft.y);
		quad[2] = topLeft.z;
		quad[3] = 1.0;
		quad[4] = a1->color_4;
		quad[5] = v21 + a1->top_9C;
		quad[6] = -v22 + a1->left_A0;

		// BottomLeft
		vec.x = a1->BottomLeft_60.x;
		vec.y = a1->BottomLeft_60.y;
		vec.z = a1->BottomLeft_60.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&bottomLeft, &vec, &pM);

		quad[8] = OutRunVrMenuQuad::ProjectY(quadMap, bottomLeft.y);
		quad[9] = bottomLeft.z;
		quad[0xA] = 1.0;
		quad[0xB] = a1->color_4;
		quad[0xC] = v21 + a1->top_94;
		quad[0xD] = v22 + a1->right_98;

		// TopRight
		vec.x = a1->TopRight_6C.x;
		vec.y = a1->TopRight_6C.y;
		vec.z = a1->TopRight_6C.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&topRight, &vec, &pM);

		quad[0xF] = OutRunVrMenuQuad::ProjectY(quadMap, topRight.y);
		quad[0x10] = topRight.z;
		quad[0x11] = 1.0;
		quad[0x12] = a1->color_4;
		quad[0x13] = -v21 + a1->bottom_84;
		quad[0x14] = -v22 + a1->left_88;

		// BottomRight
		vec.x = a1->BottomRight_78.x;
		vec.y = a1->BottomRight_78.y;
		vec.z = a1->BottomRight_78.z;
		vec.w = 1.0;
		Game::D3DXVec4Transform(&bottomRight, &vec, &pM);

		quad[0x16] = OutRunVrMenuQuad::ProjectY(quadMap, bottomRight.y);
		quad[0x17] = bottomRight.z;
		quad[0x18] = 1.0;
		quad[0x19] = a1->color_4;
		quad[0x1A] = -v21 + a1->bottom_8C;
		quad[0x1B] = v22 + a1->right_90;

        quad[0] = OutRunVrMenuQuad::ProjectX(quadMap, topLeft.x);
        quad[7] = OutRunVrMenuQuad::ProjectX(quadMap, bottomLeft.x);
        quad[0xE] = OutRunVrMenuQuad::ProjectX(quadMap, topRight.x);
        quad[0x15] = OutRunVrMenuQuad::ProjectX(quadMap, bottomRight.x);

		// Validate every transformed vertex/UV before publishing anything.
		// Keep packed diffuse color bits as-is: its float representation may
		// legally look like NaN, but it is a D3DCOLOR, not a coordinate.
		for (std::size_t i = 0; i < 4; ++i)
		{
			const std::size_t base = i * 7;
			if (!std::isfinite(quad[base]) ||
				!std::isfinite(quad[base + 1]) ||
				!std::isfinite(quad[base + 2]) ||
				!std::isfinite(quad[base + 5]) ||
				!std::isfinite(quad[base + 6]))
				return;
		}
		std::copy(quad.begin(), quad.end(), g_spriteVertexStream);
		device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2u, g_spriteVertexStream, 0x1Cu);
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
        if ((ordinalReturnSite || ordinalProducerScope ||
             RankMarkerExactCalcEdge) &&
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
                spdlog::info(
                    "VR R57 EXACT CALC EDGE: originalE8=0xBAEE2 hooked={} "
                    "markerValid={} NaviPubDepth={}",
                    RankMarkerExactCalcEdge ? 1 : 0,
                    RankMarkerProjectedInfo.valid ? 1 : 0,
                    RankMarkerSubScreenHudDepth);
            }
        }
		else if (returnAddress == Module::exe_ptr(0xBB6F5))
			recoverViewPoint(RivalMarkerProjectedInfo, false);

		// TODO: OnlineArcade mode needs to add position here

		ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());

		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			out->x = (out->x / Game::screen_scale->y) * Game::screen_scale->x;
	};

    // Exact source CALL wrapper for canonical original E8 0xBAEE2->0x49940.
    // Input/output ABI mirrors original Calc3D2D (void __cdecl, two floats,
    // two D3DVECTOR pointers). All graphics and UI scaling continue through
    // the same shared Calc3D2D_dest; the flag binds ONLY this rank parent.
    static void __cdecl Calc3D2D_OrdinalExactCall(
        float a1, float a2, D3DVECTOR* in, D3DVECTOR* out)
    {
        const bool previous = RankMarkerExactCalcEdge;
        RankMarkerExactCalcEdge = true;
        Calc3D2D_dest(a1, a2, in, out);
        RankMarkerExactCalcEdge = previous;
    }

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

			// Preserve ordinary HUD fast tagging; exact rank/GOAL/+TIME
            // producers can rebuild the queue, so prove old/new tail
            // reachability before dereferencing the old tail.
            SpriteNode* node = nullptr;
            if (producer == OutRunVR::GameSemantic::ProducerToken::StageExtensionTime ||
                producer == OutRunVR::GameSemantic::ProducerToken::OutRunStagePrintf ||
                producer == OutRunVR::GameSemantic::ProducerToken::ResultProgress ||
                // Original B9200 GOAL text can rebuild a priority list:
                // oldTail->next_0 is not safe unless oldTail is still linked.
                producer == OutRunVR::GameSemantic::ProducerToken::ResultTextB9200 ||
                producer == OutRunVR::GameSemantic::ProducerToken::GoalTimeHelper ||
                producer == OutRunVR::GameSemantic::ProducerToken::GoalTime020 ||
                producer == OutRunVR::GameSemantic::ProducerToken::GoalTime150 ||
                producer == OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani ||
                producer == OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite ||
                producer == OutRunVR::GameSemantic::ProducerToken::RivalMarkerSprani)
            {
                node = StageFirstAppendedNode(
                    root, before[prio], tailAfter, Game::SpriteNodeMax);
            }
            else
            {
                // O(1) path only for the non-rebuilding ordinary HUD.
                node = before[prio]
                    ? before[prio]->next_0 : root->next_0;
            }
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
		const bool previousPeripheral = OutRunHudPeripheralText;
		OutRunHudTextScreenHud = previous ||
			semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud;
		// Producer-callsite whitelist, not position-only inference: the
		// generic OutRunHudText token also includes protected GOAL and other
		// screen HUD. Preserve those sibling glyphs and their queue scopes.
		// BA9D0 can reenter through an unclassified helper while an
		// exact driving-HUD parent owns the glyph group. Keep that parent's
		// peripheral identity for the nested call, then restore it at exit.
		// A classified non-peripheral HUD (including GOAL), or world marker,
		// must NEVER borrow a parent's edge-anchor entitlement.
		OutRunHudPeripheralText =
			(semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud &&
			 (OutRunVRHudSemantics::InRange(caller, 0x0B9000, 0x0B9200) || // gear/REV
			  OutRunVRHudSemantics::InRange(caller, 0x0B9E00, 0x0BA100) || // rank
			  OutRunVRHudSemantics::InRange(caller, 0x0BE300, 0x0BEA40))) || // time attack
			(previousPeripheral &&
			 semantic.space == OutRunVRHudSemantics::SpacePolicy::Unknown);
        // BA9D0 may rasterize immediately before its exact clip/sprani
        // children enter the SpriteNode queue. Unify ownership without
        // widening GOAL/+TIME/unknown callers or changing desktop fallback.
        {
            std::optional<OutRunVR::GameSemantic::ScopedExactProducerSemantic>
                directHudOwner;
            if (Settings::VREnabled &&
                semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud)
            {
                const auto token = OutRunHudPeripheralText
                    ? OutRunVR::GameSemantic::ProducerToken::OutRunHudPeripheralText
                    : OutRunVR::GameSemantic::ProducerToken::OutRunHudText;
                // This original exact HUD call may emit a synchronous
                // glyph Draw before any SpriteNode is queued. A pending
                // world/marker Draw from the preceding producer must not
                // steal its scope. The RAII owner preserves and restores
                // that token; a live SpriteNode queue still takes priority.
                directHudOwner.emplace(
                    OutRunVR::GameSemantic::RenderScope::ScreenHud,
                    nullptr, true, token);
            }
            OutRunHudTextProducerHook.call(
                glyphSet, x, y, text, a4, alpha);
        }
		OutRunHudPeripheralText = previousPeripheral;
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
			OutRunHudPeripheralText
				? OutRunVR::GameSemantic::ProducerToken::OutRunHudPeripheralText
				: OutRunVR::GameSemantic::ProducerToken::OutRunHudText);
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
			OutRunHudPeripheralText
				? OutRunVR::GameSemantic::ProducerToken::OutRunHudPeripheralText
				: OutRunVR::GameSemantic::ProducerToken::OutRunHudText);
		return result;
	}

	// R71 synchronous stage/checkpoint/result Sumo_Printf CALL producer.
	// Keep exact parent lifetime, then tag every appended SpriteNode.
	inline static SafetyHookMid OutRunStagePrintfEnterHooks[3]{};
	inline static SafetyHookMid OutRunStagePrintfLeaveHooks[3]{};
	inline static thread_local unsigned OutRunStagePrintfDepth = 0;
	inline static thread_local std::optional<
		OutRunVR::GameSemantic::ScopedExactProducerSemantic>
		OutRunStagePrintfDirectDrawOwner;
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
        // Each of the three exact 0x97xxx Sumo_Printf result producers can
        // rasterize before its SpriteNodes exist. A prior world/rank
        // NextDrawScope wins over CurrentScope unless we isolate it here.
        // Record the SAME provenance as the subsequently tagged children so
        // the raw game c64 / ScreenHud GPU route cannot borrow a prior owner.
        // An active queue node remains authoritative, and RAII restores the
        // pending token, projection anchor and source on exit / VR toggle.
        if (Settings::VREnabled)
        {
            // The three proven Sumo_Printf GOAL result parents may emit
            // D3DXSprite::Draw work as well as queue SpriteNodes. Submit
            // any homogeneous outgoing batch under its OLD producer before
            // accepting the result text's ScreenHud owner.
            if (!OutRunVR::GameSemantic::QueueRenderActive())
                FlushD3DXBeforeDirectGoalSource();
            OutRunStagePrintfDirectDrawOwner.emplace(
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                nullptr, true,
                OutRunVR::GameSemantic::ProducerToken::OutRunStagePrintf);
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
        // D3DX can defer the record/stage glyph draw beyond its original
        // Sumo_Printf E8. Drain only this exact homogeneous live source
        // before RAII restores the previous world/queue identity. Mixed or
        // foreign batches keep the game's original End/Flush behavior.
        FlushD3DXAtDirectGoalSourceExit();
        // Unwind on exit even if VR mode toggles during the parent E8 call.
        OutRunStagePrintfDirectDrawOwner.reset();
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
    inline static thread_local std::optional<
        OutRunVR::GameSemantic::ScopedExactProducerSemantic>
        ResultProgressDirectDrawOwner;
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
        // 0x97BE4/0x97DEC submit synchronous animated digits plus queued
        // siblings. Shield stale world Draws; reentrant live queues retain
        // their semantic authority, and old pending state is restored.
        if (Settings::VREnabled)
        {
            // An existing homogeneous D3DX buffer belongs to its outgoing
            // producer. Split it BEFORE the exact 0-99% progress E8 takes
            // ScreenHud ownership. The SpriteNode queue has its own boundary.
            if (!OutRunVR::GameSemantic::QueueRenderActive())
                FlushD3DXBeforeDirectGoalSource();
            ResultProgressDirectDrawOwner.emplace(
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                nullptr, true,
                OutRunVR::GameSemantic::ProducerToken::ResultProgress);
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
        // D3DXSprite::Draw can defer submission past this original E8.
        // Submit only a proven homogeneous ResultProgress batch while its
        // exact source is live, before restoring the previous semantic.
        // Unknown/mixed buffers retain native D3DX End/Flush behavior.
        FlushD3DXAtDirectGoalSourceExit();
        ResultProgressDirectDrawOwner.reset();
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
    // Bracket both immediate numeric glyph draws and the original sprite
    // producer. A previous queue node's ScreenHud/World scope must not
    // override the current exact +TIME source when it rasterizes directly.
    inline static thread_local std::optional<
        OutRunVR::GameSemantic::ScopedExactProducerSemantic>
        StageExtensionDirectDrawOwner;

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
        if (Settings::VREnabled &&
            OutRunVR::GameSemantic::SpriteQueueDepth == 0)
        {
            // Immediate +TIME numerals must not consume a prior queued
            // world's pending Draw token. Shield it until this original
            // E8 caller returns, and carry the exact same source identity
            // as the separately tagged deferred sprani/number siblings.
            // ScopedExactProducerSemantic restores the previous scope,
            // pending Draw and direct producer on every return path.
            // Unlike a queued node, the original numeric +TIME E8 can
            // submit D3DX work synchronously. Any *proven* preexisting
            // homogeneous batch belongs to the outgoing producer; flush it
            // before the new ScreenHud scope can relabel its GPU submission.
            FlushD3DXBeforeDirectStageSource();
            StageExtensionDirectDrawOwner.emplace(
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                nullptr, true,
                OutRunVR::GameSemantic::ProducerToken::StageExtensionTime);
        }
    }

    static void StageExtensionLeave(safetyhook::Context&)
    {
        if (!StageExtensionDepth || --StageExtensionDepth != 0)
            return;
        TagAppendedNodes(StageExtensionBefore,
            OutRunVR::GameSemantic::RenderScope::ScreenHud,
            OutRunVR::GameSemantic::ProducerToken::StageExtensionTime);
        // D3DX Draw can defer triangles beyond the original numeric CALL.
        // Close only a still-homogeneous +TIME batch while the exact direct
        // source is alive, before restoring the previous shader/HUD owner.
        // Failed/unknown/mixed batches retain normal D3DX End behavior.
        FlushD3DXAtDirectStageSourceExit();
        // Always restore the exact direct-draw queue cursor/anchor even if
        // VR enablement changes inside the original +TIME E8 call.
        StageExtensionDirectDrawOwner.reset();
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
        // The two original GOAL E8 helper calls are independent title/time
        // outputs. The same exact token must cover both synchronous glyph
        // Draws and deferred sibling SpriteNodes; never deduplicate them.
        const auto producer = helperRva == 0xBE020
            ? OutRunVR::GameSemantic::ProducerToken::GoalTime020
            : (helperRva == 0xBE150
                ? OutRunVR::GameSemantic::ProducerToken::GoalTime150
                : OutRunVR::GameSemantic::ProducerToken::GoalTimeHelper);
        // An old world/GOAL pending Draw must not steal the current exact
        // time/title glyph. Active SpriteNode queue ownership outranks us.
        std::optional<OutRunVR::GameSemantic::ScopedExactProducerSemantic>
            goalDirectDrawOwner;
        // Split a tracked previous-owner D3DX batch before GOAL takes
        // producer ownership; submit this helper's exact remaining batch
        // before its original scope is restored. Queued sprites remain
        // tagged separately by the existing SpriteNode path.
        const bool directGoal = Settings::VREnabled &&
            !OutRunVR::GameSemantic::QueueRenderActive();
        if (directGoal)
            FlushD3DXBeforeDirectGoalSource();
        if (Settings::VREnabled)
            goalDirectDrawOwner.emplace(
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                nullptr, true, producer);
        original();
        if (directGoal)
            FlushD3DXAtDirectGoalSourceExit();
        goalDirectDrawOwner.reset();
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

		// Freeze this vehicle's exact Calc3D2D anchor before the original
		// sprani call can nest another producer or mutate thread-local state.
		// Both the synchronous draw and every queued sibling use this snapshot.
		const auto projectedAnchor = RankMarkerProjectedInfo;
		OutRunVR::GameSemantic::RenderScope scope{};
		const OutRunVR::GameSemantic::ProjectedMarkerInfo* marker = nullptr;
		if (RankMarkerSubScreenHudDepth != 0)
		{
			scope = OutRunVR::GameSemantic::RenderScope::ScreenHud;
		}
		else
		{
			const bool projected = projectedAnchor.valid;
			scope = projected
				? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
				: OutRunVR::GameSemantic::RenderScope::WorldBillboard;
			marker = projected ? &projectedAnchor : nullptr;
		}

        // Scope the actual original draw AFTER determining NaviPub vs
        // vehicle owner; this preserves the historical precedence contract.
        // Post-call SpriteNode tagging remains necessary for queued siblings.
        int result = 0;
        {
            OutRunVR::GameSemantic::ScopedExactProducerSemantic producerScope(
                scope, marker, Settings::VREnabled,
                OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani);
            result = Game::sprani_play_ae_auth_alpha(
                spriteId, x + RankMarkerFracX, y + RankMarkerFracY,
                a4, a5, alpha);
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
		// Preserve the same per-car anchor through direct draw and post-call
		// queue tagging, even if a nested producer updates the live TLS state.
		const auto projectedAnchor = RankMarkerProjectedInfo;
        // Snapshot this vehicle's fractional screen position before the
        // original producer can reenter and change its thread-local owner.
        const float frozenFractionX = RankMarkerFracX;
        const float frozenFractionY = RankMarkerFracY;
		const bool screenHud = RankMarkerSubScreenHudDepth != 0;
		const bool projected = !screenHud && projectedAnchor.valid;
		const auto scope = screenHud
			? OutRunVR::GameSemantic::RenderScope::ScreenHud
			: (projected
				? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
				: OutRunVR::GameSemantic::RenderScope::WorldBillboard);
        int result = 0;
        {
            OutRunVR::GameSemantic::ScopedExactProducerSemantic producerScope(
                scope, projected ? &projectedAnchor : nullptr, Settings::VREnabled,
                OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite);
            result = Game::put_clip_sprite(
                xstnum, x, y, flags, priority, color);
        }

		// put_clip_sprite normally queues one glyph. If an animation/mask
		// expands it to sibling nodes (even at another priority), every child
		// needs the original fractional offset and the same spatial owner.
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			SpriteNode* tailAfter = root ? root->tail_4 : nullptr;
			if (!root || !tailAfter || tailAfter == tailsBefore[prio])
				continue;
			// The original clip producer can rebuild this priority list.
			// The old tail is a snapshot, NOT owned memory: prove it is
			// still reachable from the live root before touching siblings.
			// Restore every proven kind-0/1 child's original Calc3D2D
			// fraction, then register the SAME live children below.
			OutRunVR::RankMarker::RestoreAppendedRankFractions(
				root, tailsBefore[prio], tailAfter, Game::SpriteNodeMax,
				frozenFractionX, frozenFractionY);
		}
		TagAppendedNodes(tailsBefore, scope,
			OutRunVR::GameSemantic::ProducerToken::RankMarkerClipSprite,
			projected ? &projectedAnchor : nullptr);
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

	static int ExactScreenHud_putClipSpriteOwned(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color,
		OutRunVR::GameSemantic::ProducerToken producer)
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
			OutRunVR::GameSemantic::RenderScope::ScreenHud, producer);
		return result;
	}

	static int __cdecl ExactScreenHud_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		return ExactScreenHud_putClipSpriteOwned(xstnum, x, y, flags,
			priority, color,
			OutRunVR::GameSemantic::ProducerToken::ExactScreenHudClipSprite);
	}

	// Exact original ESC arrow E8 sources may synchronously submit D3DX
	// triangles before SpriteNodes are appended/tagged. Isolate only these
	// pause-state calls: deferred nodes keep the existing exact queue owner,
	// while direct Draw observes the same producer and R84 eye transform.
	static int __cdecl PauseOptionArrow_putClipSprite(
		int xstnum, int x, int y, uint32_t flags,
		float priority, uint32_t color)
	{
		if (!Settings::VREnabled || !Game::current_mode ||
			*Game::current_mode != GameState::STATE_SMPAUSEMENU)
			return ExactScreenHud_putClipSprite(
				xstnum, x, y, flags, priority, color);
        // Exact pause arrows may defer their physical D3DX GPU draw beyond
        // this original E8. Never relabel other ScreenHud/menu clips.
        if (!OutRunVR::GameSemantic::QueueRenderActive())
            FlushD3DXBeforeDirectGoalSource();
        OutRunVR::GameSemantic::ScopedExactProducerSemantic directArrowOwner(
            OutRunVR::GameSemantic::RenderScope::ScreenHud, nullptr, true,
            OutRunVR::GameSemantic::ProducerToken::PauseOptionArrow);
        const int result = ExactScreenHud_putClipSpriteOwned(
            xstnum, x, y, flags, priority, color,
            OutRunVR::GameSemantic::ProducerToken::PauseOptionArrow);
        FlushD3DXAtDirectGoalSourceExit();
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

		// The original exact 0xBB796 rival CALL may draw immediately before
		// queueing animated siblings. Consume the preceding 0xBB6F5 anchor
		// once and use it for BOTH source-time and queued draw ownership.
		// Keep the game's original coordinates, alpha and sprite calls intact.
		const auto projectedAnchor = RivalMarkerProjectedInfo;
		RivalMarkerProjectedInfo = {};
		const bool projected = projectedAnchor.valid;
		const auto scope = projected
			? OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D
			: OutRunVR::GameSemantic::RenderScope::WorldBillboard;
		int result = 0;
		{
			OutRunVR::GameSemantic::ScopedExactProducerSemantic producerScope(
                scope, projected ? &projectedAnchor : nullptr, Settings::VREnabled,
                OutRunVR::GameSemantic::ProducerToken::RivalMarkerSprani);
			result = Game::sprani_play_ae_auth_alpha(
				spriteId, x, y, a4, a5, alpha);
		}
		// The prior HMD-accepted queued rival nodes retain exactly the same
		// scope and anchor, with no widening to generic world/HUD sprites.
		TagAppendedNodes(before, scope,
			OutRunVR::GameSemantic::ProducerToken::RivalMarkerSprani,
			projected ? &projectedAnchor : nullptr);
		return result;
	}

    // 2026-10-11 Quest3 dumps proved that hooking any of the nineteen
    // original GOAL B9200 E8 return sites can corrupt a legal branch target.
    // Recover the source from its exact return address on the call stack of
    // the ALREADY installed 0x2C808/0x2C9DB glyph wrapper instead.
    // Unknown/FPO-unwind-failed frames use the original glyph path.
    static bool IsOriginalB9200GoalGlyph() noexcept
    {
        if (!Settings::VREnabled || !Game::current_mode ||
            *Game::current_mode != GameState::STATE_GOAL)
            return false;
        void* frames[24]{};
        const USHORT count = RtlCaptureStackBackTrace(
            0, static_cast<ULONG>(std::size(frames)), frames, nullptr);
        const auto base = reinterpret_cast<std::uintptr_t>(Module::exe_ptr(0));
        for (USHORT i = 0; i < count; ++i)
            if (OutRunVR::GoalResult::IsOriginalB9200ParentReturn(
                    base, reinterpret_cast<std::uintptr_t>(frames[i])))
                return true;
        return false;
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
        // Source verification happens BEFORE the original game allocates
        // nodes or submits direct glyphs. A verified B9200 caller must
        // survive into R84's queued SpriteNode and GPU-eye plane; unrelated
        // HUD/GOAL helpers keep the old TextGlyphPutSprite provenance.
        const bool exactGoalResult = IsOriginalB9200GoalGlyph();
        std::optional<OutRunVR::GameSemantic::ScopedExactProducerSemantic>
            directResultOwner;
        if (exactGoalResult && !OutRunVR::GameSemantic::QueueRenderActive())
            directResultOwner.emplace(
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                nullptr, true,
                OutRunVR::GameSemantic::ProducerToken::ResultTextB9200);
		auto original = reinterpret_cast<TextGlyphPutSpriteFn>(
			Module::exe_ptr(0x2CFE0));
		const int result = original(args, priority);
        if (exactGoalResult)
        {
            TagAppendedNodes(tailsBefore,
                OutRunVR::GameSemantic::RenderScope::ScreenHud,
                OutRunVR::GameSemantic::ProducerToken::ResultTextB9200);
        }
        else
        {
            // The untouched +TIME, stage Sumo_Printf, ordinary HUD and
            // all unknown callers use the exact preexisting sprite route.
		    TagAppendedNodes(tailsBefore,
			    OutRunVR::GameSemantic::RenderScope::ScreenHud,
			    OutRunVR::GameSemantic::ProducerToken::TextGlyphPutSprite);
        }
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
			// In portrait XR the original height-based padding goes negative:
			// sy*640 can exceed the eye width (e.g. 2944 > 2064). Use
			// the SAME min-axis containment as the sprite renderer so only
			// a genuine free horizontal side rail can move OnlineArcade HUD.
			if (!Game::screen_scale || !Game::screen_resolution ||
				!std::isfinite(Game::screen_resolution->x) ||
				!std::isfinite(Game::screen_scale->x) ||
				!std::isfinite(Game::screen_scale->y) ||
				Game::screen_scale->x <= 1.0e-6f ||
				Game::screen_scale->y <= 1.0e-6f)
				return;
			const float spacing = OutRunVrUiAspect::ContainedSidePaddingPixels(
				Game::screen_resolution->x, Game::original_resolution.x,
				Game::screen_scale->x, Game::screen_scale->y);
			if (!std::isfinite(spacing))
				return;

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
	// The original custom-matrix multi-sprite producers submit four vertices
	// already scaled in screen pixels. Old centre hooks adjusted only X: on a
	// portrait XR eye, screen_scale.y > screen_scale.x, so Y retained the
	// stretched scale and the menu quad lost its native 4:3 proportions.
	// Use the same contain scale/centering for BOTH axes, exclusively for
	// KeepCentered/OnlineArcade UI sprites (never world, Vanilla or F11).
	static void CenterMultiSpriteQuad(float* vertices, int stride) noexcept
	{
		if (!vertices || !Game::screen_scale || !Game::screen_resolution)
			return;
		const float sx = Game::screen_scale->x;
		const float sy = Game::screen_scale->y;
		const float width = Game::screen_resolution->x;
		const float height = Game::screen_resolution->y;
		const float originalWidth = Game::original_resolution.x;
		const float originalHeight = Game::original_resolution.y;
		if (!std::isfinite(sx) || !std::isfinite(sy) ||
			!std::isfinite(width) || !std::isfinite(height) ||
			!std::isfinite(originalWidth) || !std::isfinite(originalHeight) ||
			sx <= 1.0e-6f || sy <= 1.0e-6f ||
			width <= 0.0f || height <= 0.0f ||
			originalWidth <= 0.0f || originalHeight <= 0.0f)
			return;

		// A uniformly scaled native quad is already centered and aspect-
		// correct. Preserve its original vertex bits rather than dividing and
		// multiplying every corner on desktop 4:3 and unchanged Reset sizes.
		// Rounded or nonuniform target sizes must still use the contain path.
		if (sx == sy && originalWidth * sx == width &&
			originalHeight * sy == height)
			return;

		// Original menu screen_scale can remain stale after a live Reset.
		// The three 9/11/13-stride paths must all fit the live backbuffer.
		const float contain = OutRunVrUiAspect::BoundedMultiSpriteContainScale(
			sx, sy, width, height, originalWidth, originalHeight);
		if (!(contain > 0.0f))
			return;
		float transformedX[4]{};
		float transformedY[4]{};
		// All-or-nothing: reject a nonfinite vertex or overflow before
		// modifying the original stream; device-loss continuations remain safe.
		for (int i = 0; i < 4; ++i)
		{
			const float x = vertices[i * stride];
			const float y = vertices[i * stride + 1];
			if (!std::isfinite(x) || !std::isfinite(y))
				return;
			transformedX[i] = CenterMultiSpriteAxis(
				x, sx, contain, width, originalWidth);
			transformedY[i] = CenterMultiSpriteAxis(
				y, sy, contain, height, originalHeight);
			if (!std::isfinite(transformedX[i]) ||
				!std::isfinite(transformedY[i]))
				return;
		}
		for (int i = 0; i < 4; ++i)
		{
			vertices[i * stride] = transformedX[i];
			vertices[i * stride + 1] = transformedY[i];
		}
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite(safetyhook::Context& ctx)
	{
		const ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 9);
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite2_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite2(safetyhook::Context& ctx)
	{
		const ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 11);
	}

	static inline SafetyHookMid draw_sprite_custom_matrix_multi_CenterSprite3_hk{};
	static void draw_sprite_custom_matrix_multi_CenterSprite3(safetyhook::Context& ctx)
	{
		const ScalingMode mode = ScalingMode(Settings::UIScalingMode.get());
		if (mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade)
			CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 13);
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

		// The producer's integer/float X is in original UI coordinates.
		// Never apply a negative "widescreen" rail on a portrait XR eye:
		// it otherwise pushes the right speed/gear/goal groups inward and
		// defeats the exact R30 peripheral visibility/scale gates.
		if (!value || !Game::screen_scale || !Game::screen_resolution ||
			!std::isfinite(Game::screen_resolution->x) ||
			!std::isfinite(Game::screen_scale->x) ||
			!std::isfinite(Game::screen_scale->y) ||
			Game::screen_scale->x <= 1.0e-6f ||
			Game::screen_scale->y <= 1.0e-6f)
			return;
		float spacing = OutRunVrUiAspect::ContainedSidePaddingPixels(
			Game::screen_resolution->x, Game::original_resolution.x,
			Game::screen_scale->x, Game::screen_scale->y);
		spacing /= Game::screen_scale->x;
		if (!std::isfinite(spacing))
			return;

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
        if (Calc3D2D_hk)
        {
            Memory::VP::InjectHook(
                Module::exe_ptr(0xBAEE2), Calc3D2D_OrdinalExactCall,
                Memory::HookType::Call);
            spdlog::info(
                "VR R57 KNOWN-GOOD SOURCE: exact 0xBAEE2 original rank "
                "Calc3D2D E8 edge installed (R57_06/R62)");
        }
        else
            spdlog::error(
                "VR R57 exact rank E8 left stock: original Calc3D2D "
                "trampoline unavailable");
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
				Module::exe_ptr(addr), PauseOptionArrow_putClipSprite,
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

        // Exact source RVA comparison against 2026-10-11 user minidump:
        // first result crash EIP 0x97C5F = inside old E9 displacement from
        // EXE+0x97C5C (post-CALL after original E8 at 0x97C57).
        // second crash EIP 0x97E75 = inside another E9 displacement from
        // EXE+0x97E72 (post-CALL after original E8 at 0x97E6D).
        // The fault moved only because we disabled 0x97C57; the 18
        // remaining rva+5 detours have the SAME unsafe overlap condition.
        // An original branch can land inside a five-byte hook displacement.
        // Do not reinstall ANY of the 19 B9200 parent enter/leave midhooks.
        // Preserve all stock E8 calls and their result graph/digit content.
        // The dedicated result-progress / two GOAL helper sources below
        // are separate, still covered; safe B9200 caller wrappers require
        // confirmed original call ABI before another optical attempt.
        spdlog::warn(
            "VR P0 RESULT CRASH GUARD 20261011: 19 B9200 original E8 "
            "calls unmodified, all rva+5 midhooks disabled "
            "(minidump EIPs 0x97C5F and 0x97E75); "
            "stock result graph preserved, stereo correction still pending");

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

namespace DX9ExD3DXSpriteLifetime
{
    // ID3DXSprite can outlive the game's global pointer during device loss.
    // Do not dereference a retained vtable unless the actual live game
    // sprite is still exactly the object whose Begin/Draws we observed.
    constexpr bool CanFlush(const void* candidate, const void* tracked,
        const void* live) noexcept
    {
        return candidate != nullptr && candidate == tracked &&
            candidate == live;
    }

    // OnLostDevice/OnResetDevice may be invoked on the OLD sprite after
    // 0x55B218 has already been cleared/replaced. The old tracked object
    // must still revoke its deferred +TIME/GOAL ownership.
    constexpr bool OwnsLifecycle(const void* callback, const void* tracked,
        const void* live) noexcept
    {
        return callback != nullptr &&
            (callback == tracked || callback == live);
    }

    // D3DXSprite::Draw is a CPU-side registration: a later game Flush/End
    // can rasterize it after its original +TIME caller or SpriteNode queue
    // has returned. Rebind ONLY an exclusively observed exact-owner batch
    // on the unchanged live sprite, and never while another queue is active.
    constexpr bool CanRestoreDeferredResultOwner(
        bool batchActive, bool queueActive, bool homogeneous,
        unsigned pendingDraws, bool exactLiveSprite,
        OutRunVR::GameSemantic::RenderScope scope,
        OutRunVR::GameSemantic::ProducerToken producer) noexcept
    {
        // Source-proven B9200 glyphs may use R84's finite eye plane only
        // DURING their actual direct/queued GPU owner. Their independent
        // D3DXSprite deferred-batch/Flush lifetime was never proven; do not
        // restore that owner after the original glyph call exits. Keep the
        // existing negative C++ static_assert for this exact source.
        return batchActive && !queueActive && homogeneous &&
            pendingDraws != 0u && exactLiveSprite &&
            producer != OutRunVR::GameSemantic::ProducerToken::ResultTextB9200 &&
            (OutRunVR::GameSemantic::CanReprojectFiniteResultHudPlane(
                 scope, producer) ||
             (scope == OutRunVR::GameSemantic::RenderScope::ScreenHud &&
              producer == OutRunVR::GameSemantic::ProducerToken::PauseOptionArrow));
    }

    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;

    // D3DXSprite may implicitly submit the PREVIOUS texture batch as soon
    // as the next unrelated Draw arrives. Drain only a proven outgoing exact
    // +TIME/GOAL batch *before* the new Draw can trigger that submission.
    // This is one flush per exact owner transition, never one per sprite.
    constexpr bool CanDrainDeferredResultBeforeForeignDraw(
        bool batchActive, bool queueActive, bool homogeneous,
        unsigned pendingDraws, bool exactLiveSprite,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope incomingScope, ProducerToken incomingProducer) noexcept
    {
        return CanRestoreDeferredResultOwner(
            batchActive, queueActive, homogeneous, pendingDraws,
            exactLiveSprite, pendingScope, pendingProducer) &&
            (pendingScope != incomingScope ||
             pendingProducer != incomingProducer);
    }
    static_assert(CanDrainDeferredResultBeforeForeignDraw(
        true,false,true,2,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::None,ProducerToken::None));
    static_assert(CanDrainDeferredResultBeforeForeignDraw(
        true,false,true,1,true,RenderScope::ScreenHud,
        ProducerToken::GoalTime150,
        RenderScope::ScreenHud,ProducerToken::GoalTime020));
    static_assert(!CanDrainDeferredResultBeforeForeignDraw(
        true,false,true,2,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud,ProducerToken::StageExtensionTime));
    static_assert(!CanDrainDeferredResultBeforeForeignDraw(
        true,true,true,2,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::None,ProducerToken::None));
    static_assert(!CanDrainDeferredResultBeforeForeignDraw(
        true,false,false,2,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::None,ProducerToken::None));
    static_assert(!CanDrainDeferredResultBeforeForeignDraw(
        true,false,true,2,false,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::None,ProducerToken::None));
    static_assert(CanRestoreDeferredResultOwner(
        true,false,true,3,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime));
    static_assert(CanRestoreDeferredResultOwner(
        true,false,true,1,true,RenderScope::ScreenHud,
        ProducerToken::GoalTime020));
    static_assert(!CanRestoreDeferredResultOwner(
        true,true,true,1,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime)); // live queue owns its own token
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,false,2,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime)); // unrelated triangles mixed
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,true,0,true,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime)); // no queued Draw
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,true,2,false,RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime)); // replaced/lost sprite
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,true,2,true,RenderScope::ScreenHud,
        ProducerToken::ResultTextB9200)); // unverified result parent
    static_assert(CanRestoreDeferredResultOwner(
        true,false,true,2,true,RenderScope::ScreenHud,
        ProducerToken::PauseOptionArrow));
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,true,2,true,RenderScope::ScreenHud,
        ProducerToken::ExactScreenHudClipSprite));
    static_assert(!CanRestoreDeferredResultOwner(
        true,false,true,2,true,RenderScope::WorldBillboard,
        ProducerToken::StageExtensionTime)); // world must remain spatial

    // Compile-time positive and negative tests for real pointer identity,
    // including global replacement/null during a pending GPU batch.
    inline constexpr unsigned char OldSprite = 1;
    inline constexpr unsigned char NewSprite = 2;
    inline constexpr unsigned char ForeignSprite = 3;
    static_assert(CanFlush(&OldSprite, &OldSprite, &OldSprite));
    static_assert(!CanFlush(&OldSprite, &OldSprite, &NewSprite));
    static_assert(!CanFlush(&NewSprite, &OldSprite, &NewSprite));
    static_assert(!CanFlush(&ForeignSprite, &OldSprite, &NewSprite));
    static_assert(!CanFlush(nullptr, &OldSprite, &OldSprite));
    static_assert(!CanFlush(&OldSprite, nullptr, &OldSprite));
    static_assert(OwnsLifecycle(&OldSprite, &OldSprite, nullptr));
    static_assert(OwnsLifecycle(&OldSprite, &OldSprite, &NewSprite));
    static_assert(OwnsLifecycle(&NewSprite, &OldSprite, &NewSprite));
    static_assert(!OwnsLifecycle(&ForeignSprite, &OldSprite, &NewSprite));
    static_assert(!OwnsLifecycle(nullptr, &OldSprite, &NewSprite));
}

class VRProjectedD3DXSpriteIsolationR64 : public Hook
{
    inline static SafetyHookInline Begin_hk{};
    inline static SafetyHookInline Draw_hk{};
    inline static SafetyHookInline Flush_hk{};
    inline static SafetyHookInline End_hk{};
    inline static SafetyHookInline LostDevice_hk{};
    inline static SafetyHookInline ResetDevice_hk{};
    inline static std::atomic<std::uint64_t> Flushes{ 0 };
    inline static std::atomic<std::uint64_t> Failures{ 0 };
    inline static std::atomic<std::uint64_t> StageFlushes{ 0 };
    inline static std::atomic<std::uint64_t> StageFallbacks{ 0 };
    inline static std::atomic<std::uint64_t> GoalFlushes{ 0 };
    inline static std::atomic<std::uint64_t> GoalFallbacks{ 0 };

    // A D3DXSprite::Draw may queue triangles until Flush/End. A source-call
    // scope is NOT sufficient ownership for a deferred GPU Draw. We only
    // isolate +TIME on a known, single-owner active Begin/Draw batch, never
    // reassign an unknown pre-hook/mixed buffer to ScreenHud.
    // Single coherent Quest-style HUD command ledger. The live original
    // ID3DXSprite is still authoritative for physical draw/Flush/End.
    inline static thread_local OutRunVR::HudCommandBatch::Ledger HudBatch{};

    static bool IsExactSprite(void* self) noexcept
    {
        return self && self == *Module::exe_ptr<void*>(0x55B218);
    }

    static bool StageOwner(
        OutRunVR::GameSemantic::RenderScope scope,
        OutRunVR::GameSemantic::ProducerToken source) noexcept
    {
        return scope == OutRunVR::GameSemantic::RenderScope::ScreenHud &&
            source == OutRunVR::GameSemantic::ProducerToken::StageExtensionTime;
    }

    // GOAL finish-time helpers, progress sprites and the three verified
    // Sumo_Printf result parents enqueue D3DX triangles beyond their E8.
    // Scope only those existing hooked sources, never arbitrary white/alpha
    // draws or the unsafe nineteen B9200 result return-hook family.
    static bool GoalOwner(
        OutRunVR::GameSemantic::RenderScope scope,
        OutRunVR::GameSemantic::ProducerToken source) noexcept
    {
        using namespace OutRunVR::GameSemantic;
        return scope == RenderScope::ScreenHud &&
            (source == ProducerToken::GoalTime020 ||
             source == ProducerToken::GoalTime150 ||
             source == ProducerToken::ResultProgress ||
             source == ProducerToken::OutRunStagePrintf ||
             source == ProducerToken::PauseOptionArrow);
    }

    static void ForgetBatch() noexcept { HudBatch.forget(); }

    static HRESULT __stdcall BeginDest(void* self, DWORD flags)
    {
        // A re-entrant Begin on an already-active ID3DXSprite fails with
        // INVALIDCALL; it does NOT close the previous Begin/Draw batch.
        // Keep its exact +TIME/GOAL provenance for the eventual Flush/End.
        const bool existingBatch =
            HudBatch.active && self == HudBatch.sprite && IsExactSprite(self);
        const HRESULT hr = Begin_hk.stdcall<HRESULT>(self, flags);
        if (IsExactSprite(self))
        {
            if (FAILED(hr) && existingBatch)
                return hr;
            HudBatch.begin(self, SUCCEEDED(hr));
        }
        return hr;
    }

    static HRESULT __stdcall FlushDest(void* self)
    {
        using namespace OutRunVR::GameSemantic;
        // The game's normal Flush is allowed to occur after the original
        // +TIME/GOAL source leaves. Recover the proven producer for the
        // physical GPU draw, not merely the earlier CPU Draw registration.
        // Unknown, mixed, foreign, Reset, and live-queue batches remain
        // untouched. ScopedExactProducerSemantic restores every prior scope
        // (including a pending marker) even when the game Flush fails.
        const bool restore = DX9ExD3DXSpriteLifetime::CanRestoreDeferredResultOwner(
            HudBatch.active, QueueRenderActive(), HudBatch.homogeneous,
            HudBatch.drawCount,
            DX9ExD3DXSpriteLifetime::CanFlush(
                self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218)),
            HudBatch.scope, HudBatch.producer);
        HRESULT hr;
        {
            ScopedExactProducerSemantic owned(
                restore ? HudBatch.scope : RenderScope::None, nullptr, restore,
                restore ? HudBatch.producer : ProducerToken::None);
            hr = Flush_hk.stdcall<HRESULT>(self);
        }
        if (self == HudBatch.sprite)
        {
            if (SUCCEEDED(hr))
            {
                // An explicit game Flush physically consumes the current
                // D3DX batch. A queue-exit boundary from the previous +TIME
                // or GOAL Draw cannot authorize the *next* producer's Draw.
                // Its first successful exact-owner Draw will re-arm normally.
                HudBatch.onFlushSuccess();
            }
            else
            {
                // A failed flush is not proof that the old draw buffer was
                // submitted. Preserve the game HRESULT and cease promotion.
                HudBatch.onFlushFailure();
            }
        }
        return hr;
    }

    static HRESULT __stdcall EndDest(void* self)
    {
        using namespace OutRunVR::GameSemantic;
        // ID3DXSprite::End may be the first physical submission when neither
        // a source-exit nor a queue boundary was able to flush safely.
        // Preserve the exact homogeneous producer only until End returns;
        // the native HRESULT and normal batch teardown are unchanged.
        const bool restore = DX9ExD3DXSpriteLifetime::CanRestoreDeferredResultOwner(
            HudBatch.active, QueueRenderActive(), HudBatch.homogeneous,
            HudBatch.drawCount,
            DX9ExD3DXSpriteLifetime::CanFlush(
                self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218)),
            HudBatch.scope, HudBatch.producer);
        HRESULT hr;
        {
            ScopedExactProducerSemantic owned(
                restore ? HudBatch.scope : RenderScope::None, nullptr, restore,
                restore ? HudBatch.producer : ProducerToken::None);
            hr = End_hk.stdcall<HRESULT>(self);
        }
        if (self == HudBatch.sprite)
        {
            HudBatch.end();
        }
        return hr;
    }

    // ID3DXSprite slots 12/13 invalidate its internal GPU batch across a
    // D3D9 Reset. OnLostDevice can fail or arrive without a successful End;
    // neither event proves the prior Draws were submitted. Never let stale
    // +TIME/GOAL ownership trigger a Flush after the device changes.
    static void InvalidateForDeviceLifecycle(bool wasTrackedOrExactGameSprite) noexcept
    {
        // The original OnLost/OnReset may replace the global sprite pointer.
        // The callback's object can still be the old tracked batch owner even
        // when 0x55B218 has already become null or a new sprite instance.
        if (!wasTrackedOrExactGameSprite)
            return;
        HudBatch.invalidate();
    }

    static HRESULT __stdcall LostDeviceDest(void* self)
    {
        const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(
            self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218));
        const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);
        InvalidateForDeviceLifecycle(ownsBatch);
        return hr;
    }

    static HRESULT __stdcall ResetDeviceDest(void* self)
    {
        const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(
            self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218));
        const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);
        InvalidateForDeviceLifecycle(ownsBatch);
        return hr;
    }

    static bool FlushTracked(void* self) noexcept
    {
        // Queue-end used to call this with HudBatch.sprite directly. A silent
        // sprite replacement (or global cleared before OnLostDevice) made
        // that old pointer potentially freed: never read its vtable.
        void* liveSprite = *Module::exe_ptr<void*>(0x55B218);
        if (!HudBatch.active ||
            !DX9ExD3DXSpriteLifetime::CanFlush(
                self, HudBatch.sprite, liveSprite))
        {
            if (self && self == HudBatch.sprite && self != liveSprite)
                InvalidateForDeviceLifecycle(true);
            return false;
        }
        void** vtable = *reinterpret_cast<void***>(self);
        if (!vtable || !vtable[10])
            return false;
        using FlushFn = HRESULT(__stdcall*)(void*);
        return SUCCEEDED(reinterpret_cast<FlushFn>(vtable[10])(self));
    }

public:
    // Direct +TIME numeric glyphs do not pass through QueueNode. D3DX may
    // submit the previous Draw batch while the first new glyph is queued.
    // Split only a complete, homogeneous, already-tracked batch with the
    // currently live outgoing scope+producer. Never flush an unknown batch
    // or broaden HUD ownership; the existing fail-closed path remains.
    static void BeforeDirectStageSource() noexcept
    {
        using namespace OutRunVR::GameSemantic;
        if (QueueRenderActive())
            return;
        HudBatch.boundaryReady = false;
        void* sprite = *Module::exe_ptr<void*>(0x55B218);
        if (!HudBatch.active || sprite != HudBatch.sprite || HudBatch.drawCount == 0)
            return;
        if (!CanFlushD3DXPreQueueStageBatch(
                false, true, HudBatch.homogeneous,
                HudBatch.scope, HudBatch.producer,
                EffectiveScope(), CurrentRenderProducerToken()) ||
            !FlushTracked(sprite))
        {
            StageFallbacks.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        StageFlushes.fetch_add(1, std::memory_order_relaxed);
    }

    // The E8 parent can return without an intervening D3DX Draw flush
    // (including reentrant draw and internal texture batching). Keep the
    // exact semantic alive through the final GPU submission. This is not a
    // global Flush: an unknown, mixed, foreign or queued batch is untouched.
    static void AfterDirectStageSource() noexcept
    {
        using namespace OutRunVR::GameSemantic;
        void* sprite = *Module::exe_ptr<void*>(0x55B218);
        if (!CanFlushD3DXDirectStageAtExit(
                QueueRenderActive(), HudBatch.active,
                sprite != nullptr && sprite == HudBatch.sprite,
                HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope, HudBatch.producer,
                EffectiveScope(), CurrentRenderProducerToken()))
            return;
        if (FlushTracked(sprite))
            StageFlushes.fetch_add(1, std::memory_order_relaxed);
        else
        {
            HudBatch.boundaryReady = false;
            StageFallbacks.fetch_add(1, std::memory_order_relaxed);
        }
    }

    // GOAL print helpers 0xBE020 and 0xBE150 can submit direct D3DX
    // triangles outside SpriteNode dispatch. Never relabel an existing
    // unknown, mixed or unrelated buffer with the incoming GOAL token.
    static void BeforeDirectGoalSource() noexcept
    {
        using namespace OutRunVR::GameSemantic;
        if (QueueRenderActive())
            return;
        HudBatch.boundaryReady = false;
        void* sprite = *Module::exe_ptr<void*>(0x55B218);
        if (!HudBatch.active || sprite != HudBatch.sprite || HudBatch.drawCount == 0)
            return;
        if (!CanFlushD3DXPreQueueStageBatch(
                false, true, HudBatch.homogeneous, HudBatch.scope, HudBatch.producer,
                EffectiveScope(), CurrentRenderProducerToken()) ||
            !FlushTracked(sprite))
        {
            GoalFallbacks.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        GoalFlushes.fetch_add(1, std::memory_order_relaxed);
    }

    static void AfterDirectGoalSource() noexcept
    {
        using namespace OutRunVR::GameSemantic;
        void* sprite = *Module::exe_ptr<void*>(0x55B218);
        if (!CanFlushD3DXDirectGoalAtExit(
                QueueRenderActive(), HudBatch.active,
                sprite != nullptr && sprite == HudBatch.sprite,
                HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope,
                HudBatch.producer, EffectiveScope(),
                CurrentRenderProducerToken()))
            return;
        if (FlushTracked(sprite))
            GoalFlushes.fetch_add(1, std::memory_order_relaxed);
        else
        {
            HudBatch.boundaryReady = false;
            GoalFallbacks.fetch_add(1, std::memory_order_relaxed);
        }
    }

    // Called BEFORE SelectSpriteQueueNode replaces the outgoing producer.
    // Any prior homogeneous batch flushes under its ORIGINAL queue owner;
    // only then may the incoming +TIME owner start a separate batch.
    static void BeforeQueueNode(const void* nextNode) noexcept
    {
        using namespace OutRunVR::GameSemantic;
        ProducerToken nextProducer = ProducerToken::None;
        const auto nextScope =
            PeekSpriteNodeScope(nextNode, RenderScope::None, &nextProducer);

        // A direct numeric +TIME/GOAL D3DX Draw may still be outstanding
        // when the very first unrelated queued SpriteNode is selected.
        // Here QueueRenderActive() is false, so the existing outgoing queue
        // transition check cannot see the earlier source. Submit that
        // *proven* batch with its saved owner before changing queue context.
        // Native End remains authoritative for unknown/mixed/failed batches.
        void* firstQueueSprite = *Module::exe_ptr<void*>(0x55B218);
        if (CanDrainDirectResultBeforeFirstQueueNode(
                QueueRenderActive(), HudBatch.active,
                DX9ExD3DXSpriteLifetime::CanFlush(
                    firstQueueSprite, HudBatch.sprite, firstQueueSprite),
                HudBatch.drawCount, HudBatch.homogeneous,
                HudBatch.scope, HudBatch.producer, nextScope, nextProducer))
        {
            const auto outgoingScope = HudBatch.scope;
            const auto outgoingProducer = HudBatch.producer;
            const bool wasStage = StageOwner(outgoingScope, outgoingProducer);
            bool flushed = false;
            {
                ScopedExactProducerSemantic outgoingBatch(
                    outgoingScope, nullptr, true, outgoingProducer);
                flushed = FlushTracked(firstQueueSprite);
            }
            if (flushed)
            {
                (wasStage ? StageFlushes : GoalFlushes).fetch_add(
                    1, std::memory_order_relaxed);
            }
            else
            {
                // Failed Flush and any lost vtable/live-object proof cannot
                // authorize a later optical owner. Preserve original End
                // but withdraw our batch identity until the next Begin.
                HudBatch.active = false;
                ForgetBatch();
                HudBatch.boundaryReady = false;
                (wasStage ? StageFallbacks : GoalFallbacks).fetch_add(
                    1, std::memory_order_relaxed);
            }
        }
        const bool enteringStage = StageOwner(nextScope, nextProducer);
        const bool leavingStage = QueueRenderActive() &&
            StageOwner(EffectiveScope(), CurrentRenderProducerToken());
        const bool enteringGoal = GoalOwner(nextScope, nextProducer);
        const bool leavingGoal = QueueRenderActive() &&
            GoalOwner(EffectiveScope(), CurrentRenderProducerToken());
        // A pair of GOAL E8 helpers have different source tokens even
        // though both are ScreenHud. The outgoing GPU batch must be
        // submitted before the queue selects the new helper.
        const bool goalBoundary =
            (enteringGoal != leavingGoal) ||
            (enteringGoal && leavingGoal &&
             nextProducer != CurrentRenderProducerToken());
        if (enteringStage == leavingStage && !goalBoundary)
            return;

        void* sprite = *Module::exe_ptr<void*>(0x55B218);
        if (!HudBatch.active || sprite != HudBatch.sprite)
        {
            HudBatch.boundaryReady = false;
            return;
        }
        if (HudBatch.drawCount != 0)
        {
            // Before SelectSpriteQueueNode, a homogeneous PRE-QUEUE
            // direct buffer can still be submitted with its OLD scope.
            // The old unconditional !QueueRenderActive() guard missed this
            // first +TIME edge and let later End outlive ScreenHud source.
            // Mixed, unknown prehook and mismatched buffers still fail closed;
            // ordinary first-queue GOAL/unrelated entries keep the old rule.
            if (!CanFlushD3DXPreQueueStageBatch(
                    // A first GOAL SpriteNode is also a valid queue transition:
                    // drain a proven prior direct batch under its OLD owner
                    // before selecting the GOAL source, exactly as for +TIME.
                    QueueRenderActive(), enteringStage || enteringGoal,
                    HudBatch.homogeneous,
                    HudBatch.scope, HudBatch.producer,
                    EffectiveScope(), CurrentRenderProducerToken()) ||
                !FlushTracked(sprite))
            {
                HudBatch.boundaryReady = false;
                StageFallbacks.fetch_add(1, std::memory_order_relaxed);
                return;
            }
            StageFlushes.fetch_add(1, std::memory_order_relaxed);
        }
        HudBatch.boundaryReady = enteringStage || enteringGoal;
    }

    static void BeforeQueueEnd() noexcept
    {
        using namespace OutRunVR::GameSemantic;
        if (HudBatch.boundaryReady && QueueRenderActive() &&
            (StageOwner(EffectiveScope(), CurrentRenderProducerToken()) ||
             GoalOwner(EffectiveScope(), CurrentRenderProducerToken())) &&
            HudBatch.drawCount != 0 && HudBatch.homogeneous &&
            HudBatch.scope == EffectiveScope() &&
            HudBatch.producer == CurrentRenderProducerToken())
        {
            if (FlushTracked(HudBatch.sprite))
                StageFlushes.fetch_add(1, std::memory_order_relaxed);
            else
                StageFallbacks.fetch_add(1, std::memory_order_relaxed);
        }
        HudBatch.boundaryReady = false;
    }

private:
    static HRESULT __stdcall DrawDest(
        void* self, IDirect3DTexture9* texture, const RECT* rect,
        const D3DVECTOR* center, const D3DVECTOR* pos, D3DCOLOR color)
    {
        // On a texture/provenance change the native Draw may internally
        // flush the earlier exact +TIME/GOAL batch BEFORE we can tag this
        // incoming Draw. Separate it under its original GPU owner now.
        // Queued, mixed and foreign buffers remain untouched/fail-closed.
        if (DX9ExD3DXSpriteLifetime::CanDrainDeferredResultBeforeForeignDraw(
                HudBatch.active, OutRunVR::GameSemantic::QueueRenderActive(),
                HudBatch.homogeneous,
                HudBatch.drawCount,
                DX9ExD3DXSpriteLifetime::CanFlush(
                    self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218)),
                HudBatch.scope, HudBatch.producer,
                OutRunVR::GameSemantic::EffectiveScope(),
                OutRunVR::GameSemantic::CurrentRenderProducerToken()))
        {
            const bool wasStage = StageOwner(HudBatch.scope, HudBatch.producer);
            // The incoming foreign producer is already the current scope,
            // but FlushTracked physically submits the PREVIOUS +TIME/GOAL
            // triangles. Restore that proven homogeneous GPU-batch owner
            // across the native Flush, including a reentrant FlushDest.
            // The RAII guard restores the incoming producer and pending
            // one-shot token before the new Draw enters D3DX.
            const auto outgoingScope = HudBatch.scope;
            const auto outgoingProducer = HudBatch.producer;
            bool flushed = false;
            {
                OutRunVR::GameSemantic::ScopedExactProducerSemantic outgoingBatch(
                    outgoingScope, nullptr, true, outgoingProducer);
                flushed = FlushTracked(self);
            }
            if (flushed)
            {
                (wasStage ? StageFlushes : GoalFlushes).fetch_add(
                    1, std::memory_order_relaxed);
            }
            else
            {
                HudBatch.boundaryReady = false;
                (wasStage ? StageFallbacks : GoalFallbacks).fetch_add(
                    1, std::memory_order_relaxed);
            }
        }
        const HRESULT hr = Draw_hk.stdcall<HRESULT>(
            self, texture, rect, center, pos, color);
        if (FAILED(hr))
        {
            // D3DX can have submitted part of the pending batch before a
            // failed Draw. Its GPU ownership is now unknown: never submit
            // stale +TIME/GOAL provenance under a later queue/source scope.
            // Preserve the game's HRESULT and its original Flush/End path.
            if (self && self == HudBatch.sprite)
            {
                HudBatch.active = false;
                HudBatch.boundaryReady = false;
                ForgetBatch();
            }
            return hr;
        }
        if (!self)
            return hr;

        using namespace OutRunVR::GameSemantic;
        const auto scope = EffectiveScope();
        const auto source = CurrentRenderProducerToken();
        if (self == HudBatch.sprite)
            HudBatch.recordDraw(scope, source);

        // +TIME is a complete producer batch, not one GPU submission per
        // sprite. The first node/source entry splits the previous producer;
        // BeforeQueueNode and BeforeQueueEnd submit queued +TIME under its
        // exact ScreenHud owner. StageExtensionLeave submits direct numeric
        // glyphs before restoring that caller's owner. Do NOT flush every
        // D3DX Draw: it both defeats native D3DX texture batching and inserts
        // avoidable driver submissions during the stage transition.
        // A mixed/unknown batch remains on the game's normal End path.
        const bool exactStage = StageOwner(scope, source) && HudBatch.homogeneous;
        // A new D3DX Begin after SelectSpriteQueueNode resets the previous
        // stage boundary. Only the first successful, clean, exact-owner Draw
        // may re-arm the queue-exit GPU submission (never every Draw Flush).
        if (exactStage && CanArmD3DXQueueStageAfterDraw(
                QueueRenderActive(), HudBatch.active, self == HudBatch.sprite,
                HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope, HudBatch.producer,
                scope, source))
            HudBatch.boundaryReady = true;
        if (exactStage)
            return hr;

        // GOAL direct sources retain the proven eager/parent-exit behavior.
        // Queued exact GOAL sources are submitted once on owner transition
        // or queue end; uncertain/mixed buffers keep the old fallback.
        const bool queuedStageIsolated =
            QueueRenderActive() && HudBatch.boundaryReady;
        const bool directStageIsolated =
            !QueueRenderActive() && HudBatch.drawCount == 1u;
        const bool exactGoal = GoalOwner(scope, source) && HudBatch.homogeneous;
        // D3DX Begin may occur after SelectSpriteQueueNode and clear the
        // earlier queue boundary. The first clean GOAL Draw must rearm it
        // before the existing eager, source-owned GPU Flush. Without this,
        // the 0-99% progress and both GOAL glyph helpers can survive until
        // an unrelated End/batch with no original producer scope.
        if (exactGoal && CanArmD3DXQueueGoalAfterDraw(
                QueueRenderActive(), HudBatch.active, self == HudBatch.sprite,
                HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope, HudBatch.producer,
                scope, source))
            HudBatch.boundaryReady = true;
        // The queued original GOAL progress, both finish-time helpers and
        // three verified Sumo_Printf parents share the same exact GPU owner
        // until the NEXT queue node or queue end. Keep their D3DX Draw batch
        // intact: the two existing queue boundaries submit under the outgoing
        // owner before SelectSpriteQueueNode / EndSpriteQueueRender.
        // Direct GOAL continues using the proven per-Draw/parent-exit path;
        // mixed/unarmed batches retain the existing fail-closed fallback.
        if (CanDeferD3DXQueueGoalBatch(
                QueueRenderActive(), HudBatch.active,
                self == HudBatch.sprite, HudBatch.boundaryReady,
                HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope,
                HudBatch.producer, scope, source))
            return hr;
        if ((queuedStageIsolated || directStageIsolated ||
                (QueueRenderActive() && HudBatch.boundaryReady)) &&
            HudBatch.active && self == HudBatch.sprite &&
            exactGoal &&
            HudBatch.scope == scope && HudBatch.producer == source)
        {
            if (FlushTracked(self))
            {
                const auto n = GoalFlushes.fetch_add(
                    1, std::memory_order_relaxed) + 1;
                if ((n & (n - 1)) == 0)
                    spdlog::info(
                        "VR P0 GOAL D3DX batch: exact {} submission; flushes={} fallback={}",
                        queuedStageIsolated ? "queued" : "direct",
                        n, GoalFallbacks.load(std::memory_order_relaxed));
            }
            else
            {
                HudBatch.boundaryReady = false;
                GoalFallbacks.fetch_add(1, std::memory_order_relaxed);
            }
            return hr;
        }

        // Preserve HMD-verified R64 rank isolation unchanged in scope.
        if (!QueueRenderActive())
            return hr;
        const auto* marker = CurrentProjectedMarker();
        const auto queuedSource = CurrentQueueProducerToken();
        const bool projectedRank =
            CorroboratesProjectedWorldMarker(scope) && marker && marker->valid &&
            (queuedSource == ProducerToken::RankMarkerSprani ||
             queuedSource == ProducerToken::RankMarkerClipSprite);
        const bool dispRankHud =
            CorroboratesHud(scope) &&
            (queuedSource == ProducerToken::DispRankFirst ||
             queuedSource == ProducerToken::DispRankClipSprite);
        if (!projectedRank && !dispRankHud)
            return hr;

        void** vtable = *reinterpret_cast<void***>(self);
        if (!vtable || !vtable[10])
            return hr;
        using FlushFn = HRESULT(__stdcall*)(void*);
        const HRESULT flushHr = reinterpret_cast<FlushFn>(vtable[10])(self);
        const auto count = Flushes.fetch_add(
            1, std::memory_order_relaxed) + 1;
        if (FAILED(flushHr))
            Failures.fetch_add(1, std::memory_order_relaxed);
        if ((count & (count - 1)) == 0)
            spdlog::info(
                "VR R64 D3DX ISOLATE RESTORED: owner={} producer={} flushes={} failures={} markerValid={}",
                projectedRank ? "projected-rank" : "disprank-hud",
                Name(queuedSource), count,
                Failures.load(std::memory_order_relaxed),
                marker && marker->valid ? 1 : 0);
        return hr;
    }

    static DWORD WINAPI InstallThread(void*)
    {
        for (int attempt = 0; attempt < 7200; ++attempt)
        {
            void* sprite = *Module::exe_ptr<void*>(0x55B218);
            if (sprite)
            {
                void** vtable = *reinterpret_cast<void***>(sprite);
                if (vtable && vtable[8] && vtable[9] &&
                    vtable[10] && vtable[11] &&
                    vtable[12] && vtable[13])
                {
                    const auto disabled =
                        safetyhook::InlineHook::StartDisabled;
                    Begin_hk = safetyhook::create_inline(
                        vtable[8], reinterpret_cast<void*>(&BeginDest), disabled);
                    Draw_hk = safetyhook::create_inline(
                        vtable[9], reinterpret_cast<void*>(&DrawDest), disabled);
                    Flush_hk = safetyhook::create_inline(
                        vtable[10], reinterpret_cast<void*>(&FlushDest), disabled);
                    End_hk = safetyhook::create_inline(
                        vtable[11], reinterpret_cast<void*>(&EndDest), disabled);
                    LostDevice_hk = safetyhook::create_inline(
                        vtable[12], reinterpret_cast<void*>(&LostDeviceDest), disabled);
                    ResetDevice_hk = safetyhook::create_inline(
                        vtable[13], reinterpret_cast<void*>(&ResetDeviceDest), disabled);
                    if (Begin_hk && Draw_hk && Flush_hk && End_hk &&
                        LostDevice_hk && ResetDevice_hk &&
                        Begin_hk.enable().has_value() &&
                        Flush_hk.enable().has_value() &&
                        End_hk.enable().has_value() &&
                        Draw_hk.enable().has_value() &&
                        LostDevice_hk.enable().has_value() &&
                        ResetDevice_hk.enable().has_value())
                    {
                        spdlog::info(
                            "VR R64 D3DX: +TIME/GOAL batch ownership plus device-loss/reset invalidation and original rank isolate; unknown/mixed batches fail closed");
                        return 0;
                    }
                    // Tear down all trampolines on a partial hook install;
                    // lifecycle invalidation must never run in isolation.
                    ResetDevice_hk = {};
                    LostDevice_hk = {};
                    Draw_hk = {};
                    End_hk = {};
                    Flush_hk = {};
                    Begin_hk = {};
                }
            }
            Sleep(25);
        }
        spdlog::warn(
            "VR R64 D3DX: exact sprite batch/lifecycle hook set unavailable; original no-flush behavior retained");
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

static void FlushD3DXBeforeDirectStageSource() noexcept
{
    VRProjectedD3DXSpriteIsolationR64::BeforeDirectStageSource();
}

static void FlushD3DXAtDirectStageSourceExit() noexcept
{
    VRProjectedD3DXSpriteIsolationR64::AfterDirectStageSource();
}

static void FlushD3DXBeforeDirectGoalSource() noexcept
{
    VRProjectedD3DXSpriteIsolationR64::BeforeDirectGoalSource();
}

static void FlushD3DXAtDirectGoalSourceExit() noexcept
{
    VRProjectedD3DXSpriteIsolationR64::AfterDirectGoalSource();
}

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
        const void* node = reinterpret_cast<const void*>(ctx.edi);
        VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);
		OutRunVR::GameSemantic::SelectSpriteQueueNode(node);
	}

	static void QueueEnd(SafetyHookContext&)
	{
        VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();
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