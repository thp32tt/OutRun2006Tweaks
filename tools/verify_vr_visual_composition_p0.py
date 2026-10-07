#!/usr/bin/env python3
from pathlib import Path

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
hud = read('src/vr/hud_semantics.hpp')
sem = read('src/vr/game/render_semantics.hpp')
r30 = read('src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp')
graphics = read('src/hooks_graphics.cpp')
overlay = read('src/overlay/hooks_overlay.cpp')
r14 = read('src/vr/d3d9/ex_device_upgrade_r14.cpp')
runner = read('tools/Run-OutRunVRTest.ps1')
pcfast = read('tools/Build-OutRunPCFast.ps1')

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

# F11/ImGui is external UI. It must render without consuming pending game semantic tokens.
require('ScopedExternalOverlaySemantic semantic(', overlay, 'F11 external semantic guard')
require('RenderScope::ScreenOverlay2D', overlay, 'F11 external overlay scope')
require('ImGui_ImplDX9_RenderDrawData', overlay, 'F11 guarded draw call')

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
launch_pos = runner.find('& $game @Arguments')
semantic_pos = runner.find("$env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED='1'")
if launch_pos < 0 or semantic_pos < 0 or semantic_pos >= launch_pos:
    raise SystemExit('P0 visual composition drift: EXE semantic identity must be established before game launch')
require('analyze_outrun_assets.py', pcfast, 'asset analyzer packaged with test build')

# Fail-closed invariants.
require('RenderScope::ScreenOverlay2D', sem, 'generic 2D fallback retained')
require('CorroboratesProjectedWorldMarker', sem, 'exact projected marker semantic retained')

print('P0 visual composition static contract: PASS')
