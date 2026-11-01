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
assert 'case GameState::STATE_SYSTEM:' not in front_end
assert 'case GameState::STATE_START:' not in front_end
assert 'case GameState::STATE_SUMO_FE:' in front_end
assert 'case GameState::STATE_GAME:' not in front_end
assert 'bool VrFrontEndNeedsPhysicalTargetMap() noexcept' in ui
physical_owner = ui.split('bool VrFrontEndNeedsPhysicalTargetMap() noexcept', 1)[1].split(
    'bool ResolveVrFrontEndVirtualCanvasScale(', 1)[0]
assert '*Game::current_mode != GameState::STATE_SUMO_FE' in physical_owner
assert 'pOut, vrFrontEndProducer &&\n                        VrFrontEndNeedsPhysicalTargetMap(),' in ui
assert 'pOut, originalFrontEndProducer &&\n                    VrFrontEndNeedsPhysicalTargetMap(),' in ui
assert 'if (!precontained && frontEnd && contained &&\n            VrFrontEndNeedsPhysicalTargetMap())' in ui
assert 'if (Settings::VREnabled && VrFrontEndNeedsPhysicalTargetMap() &&\n            ResolveVrFrontEndVirtualCanvasScale(' in ui
# No Sumo-FE custom/multi route may bypass the same physical-map veto.
assert 'if (!precontained && frontEnd && contained)\n        {' not in ui
assert 'Settings::VREnabled && VrFrontEndPhysicalCanvasState() &&\n            ResolveVrFrontEndVirtualCanvasScale(' not in ui
assert 'const float containScale =' not in ui
assert 'mapped._41 += offsetX;' not in ui
assert 'mapped._42 += offsetY;' not in ui
assert 'scaleX = static_cast<float>(width) / logicalWidth;' in ui
assert 'scaleY = static_cast<float>(height) / logicalHeight;' in ui
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
assert 'VRMenuScale{ "VR", "MenuScale", 0.75f,' in settings
assert 'MenuScale = 0.75' in ini
assert 'ReadMenuScaleOverride(path, candidateMenuScale)' in host
assert host.count('ReadMenuScaleOverride(path, candidateMenuScale)') == 2
assert 'clientGameState, R23ConfiguredMenuScale);' in host
aspect = (root / 'vrhost/src/runtime/menu_content_aspect.hpp').read_text(encoding='utf-8')
assert 'gameState == 0x00u || // SYSTEM / boot-title theater' in aspect
assert 'gameState == 0x0Du || // START / loading theater' in aspect
assert 'gameState == 0x20u;   // STATE_SUMO_FE runtime owner' in aspect
assert 'case 0x20u: // SUMO_FE: title/main/selector share logical canvas' in aspect
assert 'static_assert(IsTopLeftLogicalTheaterState(0x20u));' in aspect
assert 'ownsFrontEndOpticalScale ? menuScale : 1.0f' in aspect
assert 'cachedMenuScale != R23ConfiguredMenuScale' in host

# Verify the ACTUAL menu call path rather than the retired
# R23RenderWorldLockedMenuProjection helper. The live front-end loop submits
# R23RenderTheater(... clientGameState ...), so MenuScale and aspect must be
# consumed inside that function itself.
correlation = host.split('bool R23TheaterFrameMatchesCapture(', 1)[1].split(
    'bool R23RenderTheater(', 1)[0]
for token in (
    'frame.presentationMode != OutRunVR::PresentationTheater',
    'RenderFramePresentInFlight',
    'frame.presentQpc <= 0',
    'c.lastCapturePresentQpc_ <= 0',
    'frame.presentQpc > c.lastCapturePresentQpc_',
    'frequency.QuadPart / 10',
    'c.lastCapturePresentQpc_ - frame.presentQpc <= maxSkewTicks',
):
    assert token in correlation, token
theater = host.split('bool R23RenderTheater(', 1)[1].split(
    'void R23CopyMatchedViews(', 1)[0]
assert 'ResolveMenuOpticalCoverageForState(' in theater
assert 'clientGameState, R23ConfiguredMenuScale)' in theater
assert 'quad.size.width = 2.f * theaterScale;' in theater
assert 'quad.size.height = quad.size.width / aspect;' in theater
assert 'const float theaterScale = !sourceIsSbs &&' in theater
assert 'clientGameState != 0xFFFFFFFFu' in theater
assert 'clientGameState == 0x20u' in theater
assert 'PlanTopLeftLogicalCanvasCrop(' in theater
assert 'R23TheaterFrameMatchesCapture(c, *mirrorFrame)' in theater
assert 'mirrorFrame->backbufferWidth >= 640u' in theater
assert 'mirrorFrame->backbufferHeight >= 480u' in theater
assert 'const float menuPhysicalWidth = mirrorBackbufferExtentValid' in theater
assert 'const float menuPhysicalHeight = mirrorBackbufferExtentValid' in theater
assert 'clientGameState, menuPhysicalWidth, menuPhysicalHeight' in theater
assert 'publishedLogicalCanvasCrop.width' in theater
assert 'publishedLogicalCanvasCrop.height' in theater
assert 'publishedMirrorAspect = publishedLogicalCanvasCrop.aspect;' in theater
assert '[VR TRACE SUMO_FE LOGICAL CANVAS FULL]' in theater
assert 'if (!sourceIsSbs && publishedMirrorApplied &&\n            (clientGameState == 0x04u || clientGameState == 0x09u))' in theater
assert 'clientGameState == 0x20u' not in theater.split(
    'bool authoredFourThreeApplied = false;', 1)[1].split(
    'const auto logicalCanvasCrop =', 1)[0]
assert host.count('R23RenderWorldLockedMenuProjection(') == 1
assert host.count('R23RenderTheater(') >= 3
assert 'HudScale = 0.55' in ini
print('PASS live R23RenderTheater owns MenuScale uniformly; SUMO_FE is not destructively forced to 4:3; HMD UNTESTED')

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
