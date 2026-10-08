#!/usr/bin/env python3
from pathlib import Path
import re
import json
from verify_vr_hud_exact_callsite_contract import check as verify_hud_callsite_contract
from verify_vr_hud_dds_loader import verify as verify_dds_loader_contract
from verify_vr_texture_scene_contract import verify as verify_scene_texture_contract
from verify_vr_texture_cache_lifetime import verify as verify_texture_cache_lifetime

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def require(token, source, meaning):
    if token not in source:
        raise SystemExit(f'P0 visual composition drift: {meaning}: missing {token!r}')

def function_body(source, marker):
    start = source.find(marker)
    if start < 0:
        raise SystemExit(f'P0 visual composition drift: missing function {marker!r}')
    brace = source.find('{', start)
    if brace < 0:
        raise SystemExit(f'P0 visual composition drift: missing body for {marker!r}')
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[brace + 1:i]
    raise SystemExit(f'P0 visual composition drift: unterminated body for {marker!r}')

def require_order(source, meaning, *tokens):
    positions = [source.find(token) for token in tokens]
    if min(positions) < 0 or positions != sorted(positions):
        raise SystemExit(
            f'P0 visual composition drift: {meaning}: ordering {tokens} -> {positions}'
        )

ui = read('src/hooks_uiscaling.cpp')
textures = read('src/hooks_textures.cpp')
verify_dds_loader_contract(textures)
verify_scene_texture_contract(textures)
verify_texture_cache_lifetime(textures)
hud = read('src/vr/hud_semantics.hpp')
sem = read('src/vr/game/render_semantics.hpp')
r30 = read('src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp')
graphics = read('src/hooks_graphics.cpp')
overlay = read('src/overlay/hooks_overlay.cpp')
r14 = read('src/vr/d3d9/ex_device_upgrade_r14.cpp')
runner = read('tools/Run-OutRunVRTest.ps1')
pcfast = read('tools/Build-OutRunPCFast.ps1')
binary_contract = read('docs/VR_BINARY_CONTRACT.json')
verify_hud_callsite_contract(ui, json.loads(binary_contract))
hud_inspector_workflow = read('.github/workflows/outrun-exe-hud-inspector.yml')
dx9ex_active_workflow = read('.github/workflows/vr-dx9ex-active.yml')

# P0 exact-SHA validation graph: every source/contract input consumed by this
# verifier must also schedule the HUD Inspector on push/PR, and the Inspector
# must run this verifier itself. CI wiring changes are in turn watched by the
# canonical DX9Ex Active gate so a green visual contract cannot hide behind a
# workflow path-filter gap.
for path in (
    'src/hooks_uiscaling.cpp',
    'src/hooks_textures.cpp',
    'src/vr/hud_semantics.hpp',
    'src/vr/game/render_semantics.hpp',
    'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp',
    'src/hooks_graphics.cpp',
    'src/overlay/hooks_overlay.cpp',
    'src/vr/d3d9/ex_device_upgrade_r14.cpp',
    'tools/Run-OutRunVRTest.ps1',
    'tools/Build-OutRunPCFast.ps1',
    'docs/VR_BINARY_CONTRACT.json',
    'tools/analyze_outrun_exe.py',
    'tools/verify_vr_visual_composition_p0.py',
    'tools/verify_vr_hud_exact_callsite_contract.py',
):
    if hud_inspector_workflow.count(path) < 2:
        raise SystemExit(
            f'P0 visual composition drift: HUD Inspector must watch {path!r} on push and PR'
        )
require('python tools/verify_vr_visual_composition_p0.py',
        hud_inspector_workflow, 'HUD Inspector executes the P0 contract')
require("'.github/workflows/outrun-exe-hud-inspector.yml'",
        dx9ex_active_workflow, 'DX9Ex Active watches HUD Inspector CI wiring')

# P0 F11 fork integration: upstream Dear ImGui DX9 is XYZ+orthographic and
# cannot enter R30's XYZRHW/VS owners. Check explicit per-eye projection and
# scissor ownership, preserving fallback for ordinary game/menu 3D.
def check_f11_xyz_owner(source):
    prepare = function_body(source, 'bool R30PrepareExternalImGuiProjection(')
    draw = function_body(source, 'HRESULT R30TryExternalImGuiIndexed(')
    indexed = function_body(source, 'HRESULT __stdcall DrawIndexedPrimitiveDestR30(')
    world = function_body(source, 'bool R30ConfigureXyzrhwWorldEffect(')
    execute = function_body(source, 'HRESULT R30ExecuteXyzrhwStereo(')
    for token in (
        'ExternalOverlaySemanticDepth == 0',
        'RenderScope::ScreenOverlay2D',
        'D3DFVF_XYZ',
        'D3DFVF_DIFFUSE',
        'D3DFVF_TEX1',
        'GetTransform(D3DTS_PROJECTION',
        'stockProjection._34',
        'stockProjection._44',
        'GetLatchedHeadInverse(',
        'R30BuildHudPlaneCoefficients(state)',
        'projected.m[row][3]',
        'eyeScissors[eye]',
        'FrameHadWorldStereo',
    ):
        require(token, prepare, 'F11 explicitly scoped XYZ/orthographic finite HUD plane')
    for token in (
        'R30CaptureSkyGlowSceneBeforeHud(device)',
        'device->SetTransform(',
        'D3DTS_PROJECTION, &eyeProjection[eye]',
        'device->SetScissorRect(&eyeScissors[eye])',
        'RestoreRightPassState(device,',
        'restoreRaster()',
        'R30ArmSafeFallback()',
        'OutRunVR::StereoFailureRightDrawFailed',
    ):
        require(token, draw, 'F11 eye-specific draw and complete state restoration')
    require_order(draw, 'F11 left/right render ordering',
                  'if (!setEye(0))', 'const HRESULT leftHr = draw();',
                  'rightHr = draw();', 'RestoreRightPassState(device,')
    require('R30TryExternalImGuiIndexed(', indexed,
            'F11 owner must be reached from actual indexed draw')
    require('if (externalImGui != E_NOTIMPL)', indexed,
            'F11 owner result must bypass stock R26')
    require('R30XyzrhwLooksLikeHudPlane(', world,
            'untagged flat RHW=1 world evidence must be checked')
    require('state.worldEvidenceAuthoritative', world,
            'unknown flat world draws must lack authoritative host evidence')
    require('if (state.worldEvidenceAuthoritative)', execute,
            'only authoritative world draws may mark host stereo readiness')
    for token in (
        'R30TotalShadowBudgetBytes',
        'R30ShadowReservedBytes',
        'ExternalOverlaySemanticDepth == 0',
    ):
        require(token, source, 'CPU shadows bounded and external ImGui excluded')

check_f11_xyz_owner(r30)
for path in ("'external/imgui'", "'.gitmodules'"):
    if hud_inspector_workflow.count(path) < 2:
        raise SystemExit(
            f'P0 F11 drift: pinned ImGui dependency missing from Inspector push/PR: {path}')
    require(path, dx9ex_active_workflow, 'DX9Ex Active watches ImGui gitlink')
    require(path, read('.github/workflows/dx9ex-fullsource-impact-review.yml'),
            'fullsource CI watches ImGui gitlink')
require('external/imgui/backends/imgui_impl_dx9.cpp',
        read('cmake.toml'), 'pinned upstream Dear ImGui actually compiles into game')

# Fault injection is six *different* single-step source regressions, not the
# obsolete 1000/5000 unchanged-source static repetitions.
for label, needle in (
    ('broad external scope', 'ExternalOverlaySemanticDepth == 0'),
    ('XYZ vertex gate', 'D3DFVF_XYZ'),
    ('per-eye scissor', 'device->SetScissorRect(&eyeScissors[eye])'),
    ('fixed pose plane', 'R30BuildHudPlaneCoefficients(state)'),
    ('host world authority', 'if (state.worldEvidenceAuthoritative)'),
    ('global shadow budget', 'R30TotalShadowBudgetBytes'),
):
    if needle not in r30:
        raise SystemExit(f'P0 F11 negative setup missing {label}')
    broken = r30.replace(needle, '/* injected ' + label + ' regression */')
    try:
        check_f11_xyz_owner(broken)
    except SystemExit:
        pass
    else:
        raise SystemExit(f'P0 F11 fault injection was not caught: {label}')

# Exact historical producer inventory recovered from upstream + R65-R74/R73-era work.
for token in [
    '0xBB0FB','0xBB133','0xBB16C','0xBB1A5',
    '0xBB21F','0xBB241','0xBB271','0xBB2BC','0xBB2D0',
    '0xE358B','0xE35A3','0xE35CC','0xE35F7',
    '0xE481B','0xE4833','0xE485C','0xE4887',
    '0xEC24C','0xEC277','0xED4D4','0xED7A3',
    '0x460F1','0x463D6','0x46410','0x97BB7','0x97DA7',
    '0xBB796','0x2C808','0x2C9DB',
]:
    require(token, ui, 'historical exact HUD producer inventory')

for token in [
    'HUD_RANK','HUD_GEAR_REV','HUD_TIME_ATTACK','HUD_GOAL_TIME',
    'HUD_RIVAL','HUD_GHOST','WORLD_RIVAL_MARKER','WORLD_HEART',
]:
    require(token, hud, 'semantic baseline family')

# Canonical EXE closure for rank/rival marker producers.
# The source already routes these exact call sites through projected/world
# marker ownership, but the binary contract must also prove each CALL target.
# This prevents a matching source literal from masking canonical-EXE drift.
for contract_id, rva in (
    ('VR-EXE-RANK-MARKER-SPRANI-BB0FB', '0x000BB0FB'),
    ('VR-EXE-RANK-MARKER-SPRANI-BB133', '0x000BB133'),
    ('VR-EXE-RANK-MARKER-SPRANI-BB16C', '0x000BB16C'),
    ('VR-EXE-RANK-MARKER-SPRANI-BB1A5', '0x000BB1A5'),
    ('VR-EXE-RANK-MARKER-CLIP-BB21F', '0x000BB21F'),
    ('VR-EXE-RANK-MARKER-CLIP-BB241', '0x000BB241'),
    ('VR-EXE-RANK-MARKER-CLIP-BB271', '0x000BB271'),
    ('VR-EXE-RANK-MARKER-CLIP-BB2BC', '0x000BB2BC'),
    ('VR-EXE-RANK-MARKER-CLIP-BB2D0', '0x000BB2D0'),
    ('VR-EXE-RIVAL-MARKER-SPRANI-BB796', '0x000BB796'),
    ('VR-EXE-RANK-SUB-SCREEN-HUD-BEB98', '0x000BEB98'),
    ('VR-EXE-RANK-SUB-SCREEN-HUD-BED83', '0x000BED83'),
    ('VR-EXE-RANK-SUB-SCREEN-HUD-BED9E', '0x000BED9E'),
    ('VR-EXE-RANK-SUB-SCREEN-HUD-BEDAE', '0x000BEDAE'),
):
    require(contract_id, binary_contract, 'canonical rank/rival direct-CALL contract')
    require(rva, binary_contract, 'canonical rank/rival direct-CALL RVA')
require('RankMarker_SpraniCalls', ui, 'exact 1st-3rd rank marker sprani producer set')
require('RankMarker_ClipSpriteCalls', ui, 'exact 4th+ rank marker clip producer set')
require('RivalMarker_SpraniCall', ui, 'exact rival marker sprani producer')
require('RankMarkerSubScreenHudCalls', ui, 'exact screen-HUD sub_4BAD20 caller set')

# Canonical EXE closure for option/menu arrow clip producers.
# These exact historical calls were already routed to SCREEN_HUD, but until
# now only their source literals were guarded. Pin the original executable
# CALL bytes too so menu-arrow ownership cannot silently drift to another
# producer while still satisfying the source-only inventory.
for contract_id, rva in (
    ('VR-EXE-OPTION-ARROW-CLIP-E358B', '0x000E358B'),
    ('VR-EXE-OPTION-ARROW-CLIP-E35A3', '0x000E35A3'),
    ('VR-EXE-OPTION-ARROW-CLIP-E35CC', '0x000E35CC'),
    ('VR-EXE-OPTION-ARROW-CLIP-E35F7', '0x000E35F7'),
    ('VR-EXE-OPTION-ARROW-CLIP-E481B', '0x000E481B'),
    ('VR-EXE-OPTION-ARROW-CLIP-E4833', '0x000E4833'),
    ('VR-EXE-OPTION-ARROW-CLIP-E485C', '0x000E485C'),
    ('VR-EXE-OPTION-ARROW-CLIP-E4887', '0x000E4887'),
    ('VR-EXE-OPTION-ARROW-CLIP-EC24C', '0x000EC24C'),
    ('VR-EXE-OPTION-ARROW-CLIP-EC277', '0x000EC277'),
    ('VR-EXE-OPTION-ARROW-CLIP-ED4D4', '0x000ED4D4'),
    ('VR-EXE-OPTION-ARROW-CLIP-ED7A3', '0x000ED7A3'),
):
    require(contract_id, binary_contract, 'canonical option/menu arrow direct-CALL contract')
    require(rva, binary_contract, 'canonical option/menu arrow direct-CALL RVA')
require('OptionArrow_ClipSpriteCalls', ui, 'exact option/menu arrow producer set')
require('ExactScreenHud_putClipSprite', ui, 'option/menu arrow SCREEN_HUD route')

# Canonical executable closure for the DispRank/POSITION HUD family.
# These eight right-side put_clip_sprite producers cover the on-screen rank
# digits/position family that regressed to doubled/head-following in 00519.
# Pin the actual CALL bytes before relying on the ScreenHud wrapper list.
for contract_id, rva in (
    ('VR-EXE-DISPRANK-CLIP-B9F3A', '0x000B9F3A'),
    ('VR-EXE-DISPRANK-CLIP-B9F5E', '0x000B9F5E'),
    ('VR-EXE-DISPRANK-CLIP-B9F81', '0x000B9F81'),
    ('VR-EXE-DISPRANK-CLIP-B9FD0', '0x000B9FD0'),
    ('VR-EXE-DISPRANK-CLIP-B9FFC', '0x000B9FFC'),
    ('VR-EXE-DISPRANK-CLIP-BA01E', '0x000BA01E'),
    ('VR-EXE-DISPRANK-CLIP-BA035', '0x000BA035'),
    ('VR-EXE-DISPRANK-CLIP-BA052', '0x000BA052'),
):
    require(contract_id, binary_contract,
            'canonical DispRank direct-CALL contract')
    require(rva, binary_contract,
            'canonical DispRank direct-CALL RVA')
require('ExactScreenHudRight_ClipSpriteCalls', ui,
        'DispRank right-side ScreenHud producer set')
require('ExactScreenHudRight_putClipSprite', ui,
        'DispRank right-side ScreenHud wrapper')

# Canonical executable closure for the three legacy R65-R74/R73-era
# ScreenHud clip bridges that were restored during the refactor-divergence
# recovery. These source literals previously had no pinned EXE byte contract.
for contract_id, rva in (
    ('VR-EXE-LEGACY-SCREENHUD-CLIP-460F1', '0x000460F1'),
    ('VR-EXE-LEGACY-SCREENHUD-CLIP-463D6', '0x000463D6'),
    ('VR-EXE-LEGACY-SCREENHUD-CLIP-46410', '0x00046410'),
):
    require(contract_id, binary_contract,
            'canonical legacy ScreenHud direct-CALL contract')
    require(rva, binary_contract,
            'canonical legacy ScreenHud direct-CALL RVA')
require('ExactScreenHud_ClipSpriteCalls', ui,
        'legacy ScreenHud clip producer set')
require('ExactScreenHud_putClipSprite', ui,
        'legacy ScreenHud exact producer wrapper')

# Canonical executable closure for the remaining direct SCREEN_HUD clip producers.
# This closes the source-only gap for REV/gear, C2C warning/slipstream,
# Ghost/You/Diff and the pre-result TimeAttack calls. All are exact canonical
# put_clip_sprite CALLs already routed through the dedicated ScreenHud wrappers.
for contract_id, rva in (
    ('VR-EXE-GEAR-REV-CLIP-B9096', '0x000B9096'),
    ('VR-EXE-GEAR-REV-CLIP-B90B3', '0x000B90B3'),
    ('VR-EXE-SLIPSTREAM-CLIP-BD32E', '0x000BD32E'),
    ('VR-EXE-GF-WARNING-CLIP-BD397', '0x000BD397'),
    ('VR-EXE-GF-WARNING-CLIP-BD414', '0x000BD414'),
    ('VR-EXE-GF-WARNING-CLIP-BD472', '0x000BD472'),
    ('VR-EXE-GHOST-CLIP-BDB0E', '0x000BDB0E'),
    ('VR-EXE-GHOST-CLIP-BDB2D', '0x000BDB2D'),
    ('VR-EXE-GHOST-CLIP-BDB4C', '0x000BDB4C'),
    ('VR-EXE-GHOST-CLIP-BDB8E', '0x000BDB8E'),
    ('VR-EXE-TIMEATTACK-CLIP-BE311', '0x000BE311'),
    ('VR-EXE-TIMEATTACK-CLIP-BE343', '0x000BE343'),
    ('VR-EXE-TIMEATTACK-CLIP-BE3E3', '0x000BE3E3'),
    ('VR-EXE-TIMEATTACK-CLIP-BE424', '0x000BE424'),
    ('VR-EXE-TIMEATTACK-CLIP-BE45D', '0x000BE45D'),
):
    require(contract_id, binary_contract,
            'canonical remaining ScreenHud direct-CALL contract')
    require(rva, binary_contract,
            'canonical remaining ScreenHud direct-CALL RVA')
require('ExactScreenHud_ClipSpriteCalls', ui,
        'Ghost/TimeAttack generic ScreenHud producer set')
require('ExactScreenHudRight_ClipSpriteCalls', ui,
        'C2C warning/slipstream right-side ScreenHud producer set')
require('ExactScreenHudLeft_ClipSpriteCalls', ui,
        'REV/gear left-side ScreenHud producer set')
require('ExactScreenHud_putClipSprite', ui,
        'generic exact ScreenHud wrapper')
require('ExactScreenHudRight_putClipSprite', ui,
        'right-side exact ScreenHud wrapper')
require('ExactScreenHudLeft_putClipSprite', ui,
        'left-side exact ScreenHud wrapper')

# Canonical executable closure for TimeAttack/checkpoint/goal/result HUD.
# These 15 right-side put_clip_sprite producers are the historical UIScaling
# handoff restored after the doubled/head-following +TIME/result regression.
# Pin their actual EXE CALL bytes so source-only call lists cannot mask drift.
for contract_id, rva in (
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE5CD', '0x000BE5CD'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE603', '0x000BE603'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE633', '0x000BE633'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE66D', '0x000BE66D'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE690', '0x000BE690'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE6B5', '0x000BE6B5'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE6D5', '0x000BE6D5'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE7E8', '0x000BE7E8'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE802', '0x000BE802'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE81C', '0x000BE81C'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE8D8', '0x000BE8D8'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE915', '0x000BE915'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE94A', '0x000BE94A'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE97A', '0x000BE97A'),
    ('VR-EXE-TIMEATTACK-RESULT-CLIP-BE9A3', '0x000BE9A3'),
):
    require(contract_id, binary_contract,
            'canonical TimeAttack/result direct-CALL contract')
    require(rva, binary_contract,
            'canonical TimeAttack/result direct-CALL RVA')
require('ExactScreenHudRight_ClipSpriteCalls', ui,
        'TimeAttack/result right-side ScreenHud producer set')
require('ExactScreenHudRight_putClipSprite', ui,
        'TimeAttack/result right-side ScreenHud wrapper')

# Canonical disassembly proves 38 direct put_clip_sprite SCREEN_HUD calls.
# Keep those call sites exact and avoid a hot-path runtime stack walk.
for token in [
    '0xB9096','0xB90B3',
    '0xB9F3A','0xB9F5E','0xB9F81','0xB9FD0',
    '0xB9FFC','0xBA01E','0xBA035','0xBA052',
    '0xBD32E','0xBD397','0xBD414','0xBD472',
    '0xBDB0E','0xBDB2D','0xBDB4C','0xBDB8E',
    '0xBE311','0xBE343','0xBE3E3','0xBE424','0xBE45D',
    '0xBE5CD','0xBE603','0xBE633','0xBE66D','0xBE690',
    '0xBE6B5','0xBE6D5','0xBE7E8','0xBE802','0xBE81C',
    '0xBE8D8','0xBE915','0xBE94A','0xBE97A','0xBE9A3',
]:
    require(token, ui, 'canonical SCREEN_HUD put_clip_sprite call site')
require('ExactScreenHudRight_ClipSpriteCalls', ui, 'right-side SCREEN_HUD producer set')
require('ExactScreenHudLeft_ClipSpriteCalls', ui, 'left-side SCREEN_HUD producer set')
require('ExactScreenHudRight_putClipSprite', ui, 'right-side exact producer wrapper')
require('ExactScreenHudLeft_putClipSprite', ui, 'left-side exact producer wrapper')
for token in ['0xBEB98','0xBED83','0xBED9E','0xBEDAE']:
    require(token, ui, 'canonical NaviPub -> sub_4BAD20 SCREEN_HUD call site')
require('RankMarkerSubScreenHudCall', ui, 'NaviPub exact sub_4BAD20 screen ownership predicate')
require('RankMarkerSubSemanticDest', ui, 'sub_4BAD20 caller semantic wrapper')
rank_sprani = function_body(ui, 'static int __cdecl RankMarker_sprani(')
require_order(
    rank_sprani, 'screen-owned sub_4BAD20 must outrank projected/world marker tagging',
    'if (RankMarkerSubScreenHudDepth != 0)',
    'RenderScope::ScreenHud',
    'const bool projected = RankMarkerProjectedInfo.valid'
)
rank_clip = function_body(ui, 'static int __cdecl RankMarker_putClipSprite(')
require_order(
    rank_clip, 'screen-owned 4th+ rank digits must outrank projected/world tagging',
    'const bool screenHud = RankMarkerSubScreenHudDepth != 0;',
    'const bool projected = !screenHud && RankMarkerProjectedInfo.valid;',
    'RenderScope::ScreenHud',
    'RenderScope::ProjectedWorldMarker2D',
    'RenderScope::WorldBillboard',
    'TagAppendedNodes(tailsBefore, scope,'
)
for label, body in (
    ('4th+ multi-digit car mark', rank_clip),
    ('menu/result clip', function_body(ui, 'static int __cdecl ExactScreenHud_putClipSprite(')),
):
    require('TagAppendedNodes(tailsBefore,', body,
            label + ' must tag every emitted sprite sibling')
    require('Game::SpritePriorityCount', body,
            label + ' must trace every priority queue')
rank_group = function_body(ui, 'static int __cdecl RankMarkerSub_dest(')
require_order(
    rank_group, 'old car anchor cannot survive across separate sub_4BAD20 invocations',
    'RankMarkerProjectedInfo = {};',
    '++RankMarkerSubActiveDepth;',
    'RankMarkerSub_hk.call<int>(arg)',
    '--RankMarkerSubActiveDepth;',
    'RankMarkerProjectedInfo = saved;'
)
require('RankMarkerSub_hk = safetyhook::create_inline(',
        ui, 'full original rank function entry now scopes each car')
rival_producer = function_body(ui, 'static int __cdecl RivalMarker_sprani(')
require_order(
    rival_producer, 'rival anchor captured from BB6F5 must be consumed once at BB796',
    'const auto projectedAnchor = RivalMarkerProjectedInfo;',
    'RivalMarkerProjectedInfo = {};',
    'TagAppendedNodes('
)
calc_producer = function_body(ui, 'static void Calc3D2D_dest(')
require('RankMarkerSubScreenHudDepth == 0', calc_producer,
        'NaviPub screen-HUD Calc3D2D must not overwrite world car anchor')

# Four distinct deterministic regressions: do not repeat the same source
# contract 1,000/5,000 times.
def verify_marker_owner(source):
    rank_body = function_body(source, 'static int __cdecl RankMarkerSub_dest(')
    digit_body = function_body(source, 'static int __cdecl RankMarker_putClipSprite(')
    menu_body = function_body(source, 'static int __cdecl ExactScreenHud_putClipSprite(')
    rival_body = function_body(source, 'static int __cdecl RivalMarker_sprani(')
    calc_body = function_body(source, 'static void Calc3D2D_dest(')
    require('RankMarkerProjectedInfo = {};', rank_body,
            'stale vehicle rank anchor at sub entry')
    require('TagAppendedNodes(tailsBefore, scope,', digit_body,
            'missing 4th+ all-node stereo semantic')
    require('TagAppendedNodes(tailsBefore,', menu_body,
            'missing menu all-node stereo semantic')
    require('RivalMarkerProjectedInfo = {};', rival_body,
            'stale rival anchor must be consumed')
    require('RankMarkerSubScreenHudDepth == 0', calc_body,
            'screen HUD overwrote world Calc3D2D')
verify_marker_owner(ui)
for label, token in (
    ('stale rank car', 'RankMarkerProjectedInfo = {};'),
    ('missing 4th+ digit children', 'TagAppendedNodes(tailsBefore, scope,'),
    ('missing menu arrow children', 'TagAppendedNodes(tailsBefore,'),
    ('stale rival car', 'RivalMarkerProjectedInfo = {};'),
):
    # Target each exact function, so mutation of another identical token cannot
    # accidentally make an invalid fixture look valid.
    targets = {
        'stale rank car': 'static int __cdecl RankMarkerSub_dest(',
        'missing 4th+ digit children': 'static int __cdecl RankMarker_putClipSprite(',
        'missing menu arrow children': 'static int __cdecl ExactScreenHud_putClipSprite(',
        'stale rival car': 'static int __cdecl RivalMarker_sprani(',
    }
    target = targets[label]
    start = ui.index(target)
    brace = ui.index('{', start)
    depth = 0
    stop = None
    for j in range(brace, len(ui)):
        if ui[j] == '{':
            depth += 1
        elif ui[j] == '}':
            depth -= 1
            if depth == 0:
                stop = j
                break
    source_body = ui[brace:stop]
    if token not in source_body:
        raise SystemExit('P0 marker negative setup missing ' + label)
    altered = ui[:brace] + source_body.replace(
        token, '/* injected regression */', 1) + ui[stop:]
    try:
        verify_marker_owner(altered)
    except SystemExit:
        pass
    else:
        raise SystemExit('P0 marker injection not caught: ' + label)

# Direct put_sprite_ex/put_sprite_ex2 producers cover the remaining exact semantic families
# (WORLD_HEART, C2C speech/hearts, etc.) without hot-path stack walking.
require('ClassifyDirectVrSpriteCaller', textures, 'direct sprite caller semantic classifier')
require('TagDirectVrSpriteNodes', textures, 'direct sprite node semantic publication')
require('OutRunVRHudSemantics::ClassifyCaller', textures, 'shared canonical semantic map')
require('RenderScope::ScreenHud', textures, 'direct screen-HUD scope')
require('RenderScope::WorldBillboard', textures, 'direct world-billboard scope')
if 'RtlCaptureStackBackTrace' in textures:
    raise SystemExit('P0 visual composition drift: runtime stack-walk HUD classification is forbidden')
direct_put = function_body(textures, 'static int __cdecl put_sprite_ex_dest(')
require_order(
    direct_put, 'put_sprite_ex semantic publication must follow the real producer draw',
    'const int result = put_sprite_ex.call<int>(a1, a2);',
    'TagDirectVrSpriteNodes(vrTailsBefore, returnAddress);',
    'return result;'
)
direct_put2 = function_body(textures, 'static int __cdecl put_sprite_ex2_dest(')
require_order(
    direct_put2, 'put_sprite_ex2 semantic publication must follow the real producer draw',
    'const int result = put_sprite_ex2.call<int>(a1, a2);',
    'TagDirectVrSpriteNodes(vrTailsBefore, returnAddress);',
    'return result;'
)

# 00519 observed projected semantic ownership but zero build attempts: XYZRHW needs an exact route.
require('projectedWorldMarker', r30, 'fixed-function projected marker state')
require('semanticProjectedWorld', r30, 'fixed-function projected marker classifier')
require('R57BuildProjectedMarkerDelta', r30, 'projected marker per-eye delta builder')
require('projectedDeltaX', r30, 'projected marker XYZRHW eye delta')
xy_body = function_body(r30, 'bool R30ConfigureXyzrhwWorldEffect(')
require_order(
    xy_body, 'projected marker must resolve exact payload before generic world classification',
    'if (semanticProjectedWorld)',
    'R57BuildProjectedMarkerDelta(',
    'state.projectedWorldMarker = true;',
    'if (semanticWorld)'
)
xy_transform = function_body(r30, 'bool R30TransformXyzrhwVertices(')
require_order(
    xy_transform, 'projected fixed-function transform must outrank generic world transform',
    'if (state.projectedWorldMarker)',
    'else if (state.worldEffect)'
)

# Lens flare / SceneEffect is exact original-mod ownership, never a broad alpha heuristic.
require('RenderScope::SceneEffect', graphics, 'original Clr_SceneEffect semantic scope')
require('semanticSceneEffect', r30, 'exact SceneEffect classifier input')
require('R44GetOwnedRawOverlayWvp', r30, 'SceneEffect owned WVP evidence')
require('R44ClassifyOwnedOverlayMatrix', r30, 'SceneEffect spatial-vs-flat matrix proof')

# Restored base shadows are exact world geometry at three original-mod call sites.
for token in ['0x69EB4','0x6AC76','0x6B766']:
    require(token, graphics, 'original car-base-shadow call site')
require('ScopedRenderSemantic semantic(', graphics, 'car shadow exact world semantic scope')
require('RenderScope::WorldParticle', graphics, 'car shadow world ownership')

# The three upstream call sites converge on this exact world-space producer.
# Prevent a head-following/duplicated shadow caused by an expired semantic
# scope even when both text tokens still exist elsewhere in the source file.
shadow_draw = function_body(graphics, 'static void __cdecl CalcPeraShadow(')
if not re.search(
    r'OutRunVR::GameSemantic::ScopedRenderSemantic\s+semantic\(\s*'
    r'OutRunVR::GameSemantic::RenderScope::WorldParticle\s*\);\s*'
    r'Game::DrawObjectAlpha_Internal\(\s*a1,\s*'
    r'a4\s*\*\s*Settings::CarBaseShadowOpacity,\s*0,\s*-1\);',
    shadow_draw, re.S,
):
    raise SystemExit('P0 visual composition drift: car shadow draw escaped world-scoped RAII owner')
for contract_id, rva in (
    ('VR-EXE-CAR-BASE-SHADOW-DISPCAR-CALL', '0x00069EB4'),
    ('VR-EXE-CAR-BASE-SHADOW-O2SP-SELECT-CALL', '0x0006AC76'),
    ('VR-EXE-CAR-BASE-SHADOW-C2C-SELECT-CALL', '0x0006B766'),
):
    require(contract_id, binary_contract, 'canonical car-base-shadow direct-CALL contract')
    require(rva, binary_contract, 'canonical car-base-shadow direct-CALL RVA')

# F11/ImGui is external UI. It must render without consuming pending game semantic tokens.
require('ScopedExternalOverlaySemantic semantic(', overlay, 'F11 external semantic guard')
require('RenderScope::ScreenOverlay2D', overlay, 'F11 external overlay scope')
require('ImGui_ImplDX9_RenderDrawData', overlay, 'F11 guarded draw call')

# A token-only check permits an unguarded gameplay draw or a scope that has
# already destructed before ImGui submits. Pin both gameplay and menu branches
# in the original D3DEndScene owner, with the semantic RAII scope inside the
# gameplay branch and immediately enclosing the draw call.
endscene = function_body(overlay, 'static void D3DEndScene(')
if not re.search(
    r'if\s*\(\s*overlayActive\s*&&\s*Game::is_in_game\(\)\s*\)\s*'
    r'\{\s*OutRunVR::GameSemantic::ScopedExternalOverlaySemantic\s+semantic\(\s*'
    r'OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D\s*\);\s*'
    r'ImGui_ImplDX9_RenderDrawData\(ImGui::GetDrawData\(\)\);\s*\}\s*'
    r'else\s*\{\s*ImGui_ImplDX9_RenderDrawData\(ImGui::GetDrawData\(\)\);\s*\}',
    endscene, re.S,
):
    raise SystemExit(
        'P0 visual composition drift: F11 gameplay draw must remain RAII-guarded; menu draw stays unguarded'
    )

# Translated DYNAMIC MANAGED textures must not consume the bounded CPU-shadow pool.
require('R14TrackDirectLockable', r14, 'dynamic direct-lockable MANAGED texture path')
require('D3DUSAGE_DYNAMIC', r14, 'dynamic texture distinction')
create_texture = function_body(r14, 'HRESULT __stdcall CreateTextureCompatDestR14(')
require_order(
    create_texture, 'DYNAMIC MANAGED textures must bypass CPU-shadow allocation',
    '(translatedDesc.Usage & D3DUSAGE_DYNAMIC) != 0',
    'R14TrackDirectLockable(device, *texture)',
    'R14CreateCpuShadow('
)

# Runtime evidence must be valid before launch and the analyzer must ship with the package.
require('OUTRUN_VR_EXE_SEMANTICS_VERIFIED', runner, 'pre-launch EXE semantic identity environment')
require('68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3', runner, 'canonical EXE SHA gate')
launch_markers = [
    '& $game @Arguments',
    'Start-Process -FilePath $game -ArgumentList $gameArgs',
]
launch_positions = [runner.find(marker) for marker in launch_markers]
launch_positions = [pos for pos in launch_positions if pos >= 0]
launch_pos = min(launch_positions) if launch_positions else -1
semantic_pos = runner.find("$env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED='1'")
if launch_pos < 0 or semantic_pos < 0 or semantic_pos >= launch_pos:
    raise SystemExit('P0 visual composition drift: EXE semantic identity must be established before game launch')
require('analyze_outrun_assets.py', pcfast, 'asset analyzer packaged with test build')

# Fail-closed invariants.
require('RenderScope::ScreenOverlay2D', sem, 'generic 2D fallback retained')

# R73 HMD evidence proved these heuristic fixes were not sufficient. Keep them
# out of the P0 candidate: ownership must come from exact producer/disassembly
# evidence, not stage windows or scalar flare tuning.
for forbidden in (
    'R73OutRunTransientHudPresents',
    'R73OutRunTransientHudActive',
    'R72OutRunTransientHudPresents',
    'FlareStereoDepth',
):
    if forbidden in r30:
        fail(f'failed R72/R73 heuristic must stay retired: {forbidden}')

# R73 also proved that UI replacement DDS files larger than the VR LRU budget
# can be valid assets. They must be consumed transiently rather than silently
# falling back to the original texture solely because they are not cacheable.
require('transient-load', textures, 'oversized DDS transient-load path')
require('std::shared_ptr<std::vector<uint8_t>> transientTextureData',
        textures, 'D3DX-call-bounded transient DDS owner')
require('FileData.getFileData(', textures, 'replacement file data lookup')
require('&transientOwner', textures, 'transient owner handoff into file lookup')

# Pin the lifetime fix itself, not just the presence of transient-load symbols.
# For the UI fast-loader fallback, keep the transient owner alive through both
# the attempted fast decoder and any legacy Ex-trampoline retry.
# Each wrapper must own the shared buffer in the same function scope that calls
# D3DX, so an oversized replacement cannot dangle between HandleTexture and the
# actual texture creation call.
for marker, d3dx_call in (
    (
        'static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Custom_dest(',
        'const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom(',
    ),
    (
        'static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Orig_dest(',
        'return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(',
    ),
    (
        'static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Custom_dest(',
        'const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom(',
    ),
    (
        'static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Orig_dest(',
        'return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(',
    ),
    (
        'static HRESULT __stdcall D3DXCreateCubeTextureFromFileInMemoryEx_dest(',
        'return D3DXCreateCubeTextureFromFileInMemoryEx.stdcall<HRESULT>(',
    ),
):
    body = function_body(textures, marker)
    require_order(
        body,
        'transient DDS owner must remain function-scoped through D3DX create',
        'std::shared_ptr<std::vector<uint8_t>> transientTextureData;',
        'if (',
        'HandleTexture(&pSrcData, &SrcDataSize',
        'transientTextureData);',
        d3dx_call,
    )

require('CorroboratesProjectedWorldMarker', sem, 'exact projected marker semantic retained')

# Lens flare P0: R73 HMD proved scalar disparity tuning was not a fix.
# Ownership must come from the canonical sub_40CAE0 producer: EXE+0xCABE
# DrawObjectAlpha call, then pass the same exact semantic through the WVP proof.
require('ProjectedScreenEffect2D', sem, 'exact projected lens semantic')
require('CorroboratesProjectedScreenEffect', sem, 'projected lens semantic predicate')
require('VRLensFlareProjected2D', graphics, 'canonical lens producer hook')
require('Module::exe_ptr(0xCABE)', graphics, 'canonical EXE+0xCABE lens callsite')
require('RenderScope::ProjectedScreenEffect2D', graphics, 'exact lens producer scope')

# Canonical EXE+0xCABE must call the exact projection-scoped producer; merely
# mentioning the scope and CALL-site elsewhere would not protect the effect.
lens_owner = graphics.split('class VRLensFlareProjected2D : public Hook', 1)
if len(lens_owner) != 2:
    raise SystemExit('P0 visual composition drift: exact lens hook owner missing')
lens_owner = lens_owner[1].split('VRLensFlareProjected2D::instance;', 1)[0]
if not re.search(
    r'Memory::VP::InjectHook\(\s*Module::exe_ptr\(0xCABE\),\s*'
    r'DrawObjectAlphaProjected,\s*Memory::HookType::Call\);',
    lens_owner, re.S,
):
    raise SystemExit('P0 visual composition drift: EXE+0xCABE no longer hooks exact lens producer')
lens_draw = function_body(graphics, 'static void __cdecl DrawObjectAlphaProjected(')
if not re.search(
    r'OutRunVR::GameSemantic::ScopedRenderSemantic\s+semantic\(\s*'
    r'OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D\s*\);\s*'
    r'Game::DrawObjectAlpha_Internal\(objectId,\s*alpha,\s*work,\s*flags\);',
    lens_draw, re.S,
):
    raise SystemExit('P0 visual composition drift: lens draw escaped projection-scoped RAII owner')
require('semanticProjectedScreen', r30, 'exact lens scope classifier')
require('CorroboratesProjectedScreenEffect', r30, 'exact lens WVP ownership guard')
require('exactSceneEffect', r30, 'SceneEffect/lens ownership admission')
require_order(
    r30,
    'lens ownership must be semantic before WVP classification',
    'const bool semanticProjectedScreen',
    'if (!semanticHud && !semanticWorld && !semanticSceneEffect',
    'if (semanticProjectedScreen || semanticSceneEffect)',
    'R44GetOwnedRawOverlayWvp(rawWvp)',
    'R44ClassifyOwnedOverlayMatrix(rawWvp)',
)
analyzer = read('tools/analyze_outrun_exe.py')
require('SceneEffectLensProducer_sub_40CAE0', analyzer, 'canonical lens producer window')
require('0x0000CAE0', analyzer, 'lens producer start RVA')
require('0x0000CABE', analyzer, 'lens DrawObjectAlpha anchor RVA')
require('0x0000CF4E', analyzer, 'lens Calc3D2D anchor RVA')
# Canonical byte closure for the NaviPub ScreenHud scaling-state hooks.
# Bytes are taken from HUD Inspector artifact 11501098116 for canonical
# OR2006C2C.EXE SHA-256 68ceb386... and must remain bound to the exact current
# UIScaling mid-hook addresses.
for contract_id, rva in (
    ('VR-EXE-NAVIPUB-GOAL-SCALING-BEA64', '0x000BEA64'),
    ('VR-EXE-NAVIPUB-RIVAL-DISABLE-BEB8E', '0x000BEB8E'),
    ('VR-EXE-NAVIPUB-RIVAL-ENABLE-BEBAF', '0x000BEBAF'),
    ('VR-EXE-NAVIPUB-HEART-DISABLE-BEBE1', '0x000BEBE1'),
    ('VR-EXE-NAVIPUB-HEART-ENABLE-BEBE6', '0x000BEBE6'),
    ('VR-EXE-NAVIPUB-RIVAL-ONLINE-DISABLE-BEC83', '0x000BEC83'),
    ('VR-EXE-NAVIPUB-RIVAL-ONLINE-ENABLE-BEC88', '0x000BEC88'),
    ('VR-EXE-NAVIPUB-C2C-HEART-ENABLE-BECBA', '0x000BECBA'),
    ('VR-EXE-NAVIPUB-C2C-HEART-ENABLE2-BECE0', '0x000BECE0'),
):
    require(contract_id, binary_contract,
            'canonical NaviPub ScreenHud scaling-state contract')
    require(rva, binary_contract,
            'canonical NaviPub ScreenHud scaling-state RVA')

# Canonical byte closure for the ten active Ghost/TimeAttack ScreenHud
# spacing-state hooks. The original four anchors plus the remaining six are
# recovered from the pinned GhostTimeAttackHud window in HUD Inspector evidence.
for contract_id, rva in (
    ('VR-EXE-GHOST-SUB-ADJUST-BDAE8', '0x000BDAE8'),
    ('VR-EXE-GHOST-ADJUST-BDE3A', '0x000BDE3A'),
    ('VR-EXE-GHOST-FORCE-LEFT-BE045', '0x000BE045'),
    ('VR-EXE-GHOST-FORCE-RIGHT2-BE067', '0x000BE067'),
    ('VR-EXE-GHOST-FORCE-LEFT2-BE083', '0x000BE083'),
    ('VR-EXE-GHOST-FORCE-RIGHT-BE0A5', '0x000BE0A5'),
    ('VR-EXE-TIMEATTACK-FORCE-RIGHT-BE4BC', '0x000BE4BC'),
    ('VR-EXE-TIMEATTACK-DISABLE-BE4C1', '0x000BE4C1'),
    ('VR-EXE-TIMEATTACK-FORCE-LEFT-BE4E7', '0x000BE4E7'),
    ('VR-EXE-TIMEATTACK-FORCE-ENABLE-BE575', '0x000BE575'),
):
    require(contract_id, binary_contract,
            'canonical Ghost/TimeAttack ScreenHud spacing contract')
    require(rva, binary_contract,
            'canonical Ghost/TimeAttack ScreenHud spacing RVA')

# Ghost/You/Diff + TimeAttack ScreenHud producer window. These four
# source-level UIScaling spacing hooks are high-value P0 anchors but previously
# lacked a durable canonical disassembly window for exact byte recovery.
require('GhostTimeAttackHud_0xBD900', analyzer,
        'Ghost/TimeAttack canonical producer window')
require('0x000BD900', analyzer, 'Ghost/TimeAttack producer start RVA')
require('0x000BEA40', analyzer, 'Ghost/TimeAttack producer end RVA')
for token in (
    '0x000BDAE8', '0x000BDE3A',
    '0x000BE045', '0x000BE067', '0x000BE083', '0x000BE0A5',
    '0x000BE4BC', '0x000BE4C1', '0x000BE4E7', '0x000BE575',
):
    require(token, analyzer, 'Ghost/TimeAttack canonical anchor RVA')

# NaviPub goal/rival/heart/nav HUD producer window. These screen-HUD
# state-transition anchors are part of the original UIScaling map but did not
# previously have a durable canonical disassembly window in the HUD Inspector.
require('NaviPubHud_0xBEA40', analyzer,
        'NaviPub goal/rival/heart canonical producer window')
require('0x000BEA40', analyzer, 'NaviPub HUD producer start RVA')
require('0x000BEE80', analyzer, 'NaviPub HUD producer end RVA')
for token in (
    '0x000BEA64',
    '0x000BEB8E', '0x000BEBAF',
    '0x000BEBE1', '0x000BEBE6',
    '0x000BEC83', '0x000BEC88',
    '0x000BECBA', '0x000BECE0',
    '0x000BED83', '0x000BED9E', '0x000BEDAE',
):
    require(token, analyzer, 'NaviPub HUD canonical anchor RVA')

require('OutRunStageResultHud_0x97000', analyzer,
        'OutRun stage/result HUD producer window')
for token in (
    '0x000975EE', '0x00097727', '0x000977FB',
    '0x00097BB7', '0x00097DA7',
):
    require(token, analyzer, 'OutRun stage/result canonical producer anchor')

# Canonical executable closure for the common Sumo text-glyph producers.
# Stage/result/YES-NO and other exact ScreenHud text ultimately reaches these
# two put_sprite_ex CALLs. Pin the actual EXE bytes so a source-only wrapper
# list cannot mask a changed call target or displaced producer.
for contract_id, rva in (
    ('VR-EXE-TEXT-GLYPH-PUT-SPRITE-2C808', '0x0002C808'),
    ('VR-EXE-TEXT-GLYPH-PUT-SPRITE-2C9DB', '0x0002C9DB'),
):
    require(contract_id, binary_contract,
            'canonical text glyph direct-CALL contract')
    require(rva, binary_contract,
            'canonical text glyph direct-CALL RVA')
require('TextGlyph_PutSpriteCalls[] = { 0x2C808, 0x2C9DB }', ui,
        'exact text glyph producer set')
require('TextGlyph_putSprite', ui,
        'exact text glyph ScreenHud wrapper')
require('Module::exe_ptr(0x2CFE0)', ui,
        'text glyph wrapper original put_sprite_ex target')

# Canonical executable closure for the OutRun stage/result HUD.
# The three text calls resolve to Sumo_Printf; its exact glyph producers are
# already redirected through TextGlyph_putSprite and registered as ScreenHud.
for contract_id, rva in (
    ('VR-EXE-STAGE-RESULT-TEXT-975EE', '0x000975EE'),
    ('VR-EXE-STAGE-RESULT-TEXT-97727', '0x00097727'),
    ('VR-EXE-STAGE-RESULT-TEXT-977FB', '0x000977FB'),
    ('VR-EXE-STAGE-RESULT-CLIP-97BB7', '0x00097BB7'),
    ('VR-EXE-STAGE-RESULT-CLIP-97DA7', '0x00097DA7'),
):
    require(contract_id, binary_contract,
            'canonical stage/result HUD direct-CALL contract')
    require(rva, binary_contract,
            'canonical stage/result HUD direct-CALL RVA')
require('TextGlyph_PutSpriteCalls[] = { 0x2C808, 0x2C9DB }', ui,
        'stage/result Sumo_Printf glyph route')
require('TextGlyph_putSprite', ui,
        'stage/result text ScreenHud wrapper')
require('ProducerToken::TextGlyphPutSprite', ui,
        'stage/result text producer token')
require('RenderScope::ScreenHud', ui,
        'stage/result text ScreenHud ownership')
for token in ('0x97BB7', '0x97DA7'):
    require(token, ui, 'stage/result clip exact ScreenHud route')
require('ExactScreenHud_putClipSprite', ui,
        'stage/result clip ScreenHud wrapper')


# Exact original producer -> original Sumo_Printf text -> glyph queue ->
# R30 mono/stereo head-lock path. Previously the label's exact ScreenHud
# provenance could still be vetoed by a stale verified-world shader/c64 state,
# and masked sibling sprites from the same glyph call stayed untagged.
# The pinned PE32 manifest already confirms all three stage/result text
# producers target Sumo_Printf (0x2CDD0), and 0x2C808/0x2C9DB target
# put_sprite_ex (0x2CFE0). Do not add broad 0x97000 range heuristics.
def check_time_goal_lens_owner(source_r30, source_ui):
    shader = function_body(source_r30, 'R30ScreenSpaceKind R30ClassifyScreenSpacePass(')
    fixed = function_body(source_r30, 'bool R30ConfigureXyzrhwWorldEffect(')
    glyph = function_body(source_ui, 'static int __cdecl TextGlyph_putSprite(')
    for token in (
        'const bool exactSceneEffect =',
        'RenderScope::SceneEffect',
        'CorroboratesProjectedScreenEffect(',
        'else if (exactSceneEffect)',
        'state.rhwDepthEvidence &&',
        '!R30XyzrhwLooksLikeHudPlane(',
        '!exactSceneEffect)',
    ):
        require(token, fixed, 'EXE-owned lens/scene fixed XYZRHW exact classification')
    require('state.worldEffect = state.rhwDepthEvidence &&\n'
            '                    !R30XyzrhwLooksLikeHudPlane(',
            fixed, 'lens world stereo requires actual exact-reference depth evidence')
    if fixed.index('else if (exactSceneEffect)') > fixed.index('if (!state.worldEffect &&'):
        raise SystemExit('P0 lens XYZRHW exact semantic accepted too late')
    for token in (
        'const bool semanticHud =',
        'if (semanticWorld)',
        'if (semanticHud)',
        'return R30ScreenSpaceKind::PerspectiveHud;',
    ):
        require(token, shader, 'shader HUD/world owner boundary')
    precise_hud = shader[shader.index('if (semanticHud)'):]
    for forbidden in (
        'if (CurrentDrawMatchesVerifiedWorld(device))',
        'if (R28CanRebindVerifiedWorld(',
    ):
        if forbidden in precise_hud:
            raise SystemExit(
                'P0 +TIME/goal semantic ScreenHud wrongly vetoed by world state: ' +
                forbidden)
    # World still has both strict authority gates before the exact HUD branch.
    world_before_hud = shader[shader.index('if (semanticWorld)'):
                               shader.index('if (semanticHud)')]
    for token in (
        'CurrentDrawMatchesVerifiedWorld(device)',
        'R28CanRebindVerifiedWorld(',
    ):
        require(token, world_before_hud, 'world effects must retain verified-world gate')
    require_order(glyph, 'Sumo glyph all-child scope after original put_sprite_ex',
                  'tailsBefore', 'Module::exe_ptr(0x2CFE0)',
                  'const int result = original(args, priority);',
                  'TagAppendedNodes(tailsBefore,',
                  'RenderScope::ScreenHud',
                  'ProducerToken::TextGlyphPutSprite')
    for token in ('Game::SpritePriorityCount', 'TagAppendedNodes(tailsBefore,'):
        require(token, glyph, 'all stage/result +TIME glyph/mask children same HUD')
    for token in (
        '0x000975EE', '0x00097727', '0x000977FB',
        '0x00097BB7', '0x00097DA7',
        '0x0002C808', '0x0002C9DB',
    ):
        require(token, binary_contract, 'original EXE Sumo text/glyph/clip identity')

check_time_goal_lens_owner(r30, ui)

# Four *distinct*, exactly-once fault injections. These do not repeat an
# unchanged-source static audit 1000/5000 times.
def inject_one_function_token(source, signature, token, replacement):
    begin = source.index(signature)
    brace = source.index('{', begin)
    depth = 0
    end = None
    for i in range(brace, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit('P0 lens/HUD injection: malformed function')
    part = source[begin:end]
    if token not in part:
        raise SystemExit('P0 lens/HUD injection setup missing ' + token)
    return source[:begin] + part.replace(token, replacement, 1) + source[end:]

for label, broken_r30, broken_ui in (
    ('missing exact lens fixed semantic',
     inject_one_function_token(
         r30, 'bool R30ConfigureXyzrhwWorldEffect(',
         'else if (exactSceneEffect)', 'else if (false)'), ui),
    ('lens depth evidence bypass',
     inject_one_function_token(
         r30, 'bool R30ConfigureXyzrhwWorldEffect(',
         'state.rhwDepthEvidence &&',
         'true ||'), ui),
    ('time-goal HUD world veto resurrected',
     inject_one_function_token(
         r30, 'R30ScreenSpaceKind R30ClassifyScreenSpacePass(',
         '++R44FlatOverlayClassifications;',
         'if (CurrentDrawMatchesVerifiedWorld(device)) return R30ScreenSpaceKind::None;\n            ++R44FlatOverlayClassifications;'), ui),
    ('stage text glyph siblings untagged',
     r30, inject_one_function_token(
         ui, 'static int __cdecl TextGlyph_putSprite(',
         'TagAppendedNodes(tailsBefore,', '/* injected missing glyph siblings */')),
):
    try:
        check_time_goal_lens_owner(broken_r30, broken_ui)
    except SystemExit:
        pass
    else:
        raise SystemExit('P0 source fault injection unexpectedly passed: ' + label)


print('P0 visual composition static contract: PASS')
