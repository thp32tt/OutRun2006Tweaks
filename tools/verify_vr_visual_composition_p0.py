#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def require(token, source, meaning):
    if token not in source:
        raise SystemExit(f'P0 visual composition drift: {meaning}: missing {token!r}')

ui = read('src/hooks_uiscaling.cpp')
textures = read('src/hooks_textures.cpp')
hud = read('src/vr/hud_semantics.hpp')
sem = read('src/vr/game/render_semantics.hpp')
r30 = read('src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp')
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
    '0x4BE5CD','0x4BE603','0x4BE633','0x4BE66D','0x4BE690',
    '0x4BE6B5','0x4BE6D5','0x4BE8D8','0x4BE915','0x4BE94A',
    '0x4BE97A','0x4BE9A3','0x4BE7E8','0x4BE802','0x4BE81C',
]:
    require(token, ui, 'historical exact HUD producer inventory')

for token in [
    'HUD_RANK','HUD_GEAR_REV','HUD_TIME_ATTACK','HUD_GOAL_TIME',
    'HUD_RIVAL','HUD_GHOST','WORLD_RIVAL_MARKER','WORLD_HEART',
]:
    require(token, hud, 'semantic baseline family')

# Fixed-function sprite producers must consume the same canonical semantic map.
require('ClassifyVrSpriteProducer', textures, 'common sprite producer semantic classifier')
require('TagAppendedVrSemanticNodes', textures, 'common sprite producer node tagging')
require('OutRunVRHudSemantics::ClassifyCaller', textures, 'canonical HUD semantic map consumption')
require('RenderScope::ScreenHud', textures, 'fixed-function screen HUD mapping')
require('RenderScope::WorldBillboard', textures, 'fixed-function world billboard mapping')

# 00519 observed projected semantic ownership but zero build attempts: XYZRHW needs an exact route.
require('projectedWorldMarker', r30, 'fixed-function projected marker state')
require('semanticProjectedWorld', r30, 'fixed-function projected marker classifier')
require('R57BuildProjectedMarkerDelta', r30, 'projected marker per-eye delta builder')
require('projectedDeltaX', r30, 'projected marker XYZRHW eye delta')

# Translated DYNAMIC MANAGED textures must not consume the bounded CPU-shadow pool.
require('R14TrackDirectLockable', r14, 'dynamic direct-lockable MANAGED texture path')
require('D3DUSAGE_DYNAMIC', r14, 'dynamic texture distinction')

# Runtime evidence must be valid before launch and the analyzer must ship with the package.
require('OUTRUN_VR_EXE_SEMANTICS_VERIFIED', runner, 'pre-launch EXE semantic identity environment')
require('68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3', runner, 'canonical EXE SHA gate')
require('analyze_outrun_assets.py', pcfast, 'asset analyzer packaged with test build')

# Fail-closed invariants.
require('RenderScope::ScreenOverlay2D', sem, 'generic 2D fallback retained')
require('CorroboratesProjectedWorldMarker', sem, 'exact projected marker semantic retained')

print('P0 visual composition static contract: PASS')
