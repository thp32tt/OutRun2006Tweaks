#!/usr/bin/env python3
"""Source wiring gate for independent front-end menu/UI coordinates and physical XR target."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cfg = (root / 'src/hooks_misc.cpp').read_text(encoding='utf-8')
ex = (root / 'src/vr/d3d9/ex_device_upgrade.cpp').read_text(encoding='utf-8')
host = (root / 'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
ui = (root / 'src/hooks_uiscaling.cpp').read_text(encoding='utf-8')
game = (root / 'src/game.hpp').read_text(encoding='utf-8')
settings = (root / 'src/vr/settings.cpp').read_text(encoding='utf-8')
ini = (root / 'OutRun2006Tweaks.ini').read_text(encoding='utf-8')
source = cfg.split('void ApplyVrEyeResolutionAfterConfig(', 1)[1].split('class CommandLineArguments', 1)[0]

# Game/menu logical coordinates are never replaced by the XR eye size.
assert 'Game::screen_resolution->x = 1920;' in source
assert 'Game::screen_resolution->y = 1080;' in source
assert 'VR R26 LOGICAL SOURCE LOCK:' in source
assert 'GetTickCount64()' not in source and 'Sleep(' not in source
assert 'physical D3D9Ex target will use live OpenXR eye extent at CreateDevice' in source
assert 'explicit game/UI resolution' in source
assert 'OutRunVR::RequestVRHostStartup();' in source
assert 'VRAutoRenderResolution{ "VR", "AutoRenderResolution", true,' in settings
assert 'VRFollowGameResolution{ "VR", "FollowGameResolution", false,' in settings
assert 'AutoRenderResolution = true' in ini
assert 'FollowGameResolution = false' in ini
front_end = ui.split('bool VrFrontEndPhysicalCanvasState() noexcept', 1)[1].split(
    'bool ResolveVrFrontEndVirtualCanvasScale(', 1)[0]
assert 'STATE_SUMO_FE = 0x20' in game
assert 'case GameState::STATE_SUMO_FE:' in front_end
assert 'case GameState::STATE_GAME:' not in front_end
assert 'MapVrFrontEndMatrixToPhysical(' in ui
assert 'VR TRACE FRONTEND VIRTUAL CANVAS:' in ui

# CreateDevice owns the physical XR render target and must not publish it back
# into the original game's logical UI resolution global.
resolver = ex.split('OutRunVR::EyeExtent::Size ReadyXrEyeSizeAtCreateDevice(',1)[1].split(
    'Direct3DCreate9Fn OriginalDirect3DCreate9',1)[0]
assert 'ResolveStartupForLiveHost' in resolver
assert 'ResolveGame' in resolver
assert 'GameResolutionExplicitOnCommandLine' not in resolver
assert 'Game::screen_resolution->x = static_cast<int>(xrSize.width)' not in ex
assert 'Game::screen_resolution->y = static_cast<int>(xrSize.height)' not in ex

# Menu optical placement remains a host-side 4:3/scale policy, independent
# from physical XR render-target dimensions.
assert 'VRMenuScale{ "VR", "MenuScale", 1.0f,' in settings
assert 'MenuScale = 1.00' in ini
assert 'ReadMenuScaleOverride(path, candidateMenuScale)' in host
assert host.count('ReadMenuScaleOverride(path, candidateMenuScale)') == 2
assert 'clientGameState, R23ConfiguredMenuScale);' in host
assert 'cachedMenuScale != R23ConfiguredMenuScale' in host
assert 'HudScale = 0.55' in ini
print('PASS menu logical coordinates / host 4:3 placement / physical XR target are independent; HMD UNTESTED')

# Same-owner failed refresh must not publish defaults or a partial config.
owner = host.split('bool R23GameMenuIsLetterboxed(HWND gameWindow) noexcept', 1)[1].split(
    'constexpr ULONGLONG R23PixelIntervalMs', 1)[0]
assert 'const bool sameOwner = gamePid != 0 &&' in owner
assert 'cachedWindow == gameWindow && cachedPid == gamePid;' in owner
assert 'if (!sameOwner)' in owner
assert owner.index('const bool sameOwner') < owner.index('cachedWindow = gameWindow;')
assert owner.index('if (!sameOwner)') < owner.index('R23ConfiguredMenuScale = 1.0f;') < owner.index('OpenProcess(')
assert 'return false;' not in owner
assert owner.index('if (!foundConfig)') < owner.index('R23ConfiguredMenuScale = candidateMenuScale;')
print('PASS same-owner menu config failure retains accepted optical scale; new owner resets')
