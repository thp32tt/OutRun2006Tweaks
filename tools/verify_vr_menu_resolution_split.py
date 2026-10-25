#!/usr/bin/env python3
"""Source wiring gate for independent menu placement / startup game resolution.

Portable geometry assertions live in menu_content_aspect_smoke.cpp and run
against the production C++ helper. HMD optics remain a separate test.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cfg = (root / 'src/hooks_misc.cpp').read_text(encoding='utf-8')
host = (root / 'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
settings = (root / 'src/vr/settings.cpp').read_text(encoding='utf-8')
ini = (root / 'OutRun2006Tweaks.ini').read_text(encoding='utf-8')
source = cfg.split('void ApplyVrEyeResolutionAfterConfig(', 1)[1].split('class CommandLineArguments', 1)[0]
assert 'Settings::VRPreferD3D9Ex' not in source, 'Resolution must not depend on transport/provider preference'
assert source.index('if (commandLineResolution)') < source.index('if (manualRequested)') < source.index('RequestVRHostStartup()')
assert 'GetTickCount64() - startTick >= 1250ull' in source
assert 'VRMenuScale{ "VR", "MenuScale", 1.0f,' in settings
assert 'MenuScale = 1.00' in ini
assert 'ReadMenuScaleOverride(path, candidateMenuScale)' in host
assert host.count('ReadMenuScaleOverride(path, candidateMenuScale)') == 2, 'Base + user INI precedence'
assert 'clientGameState, R23ConfiguredMenuScale);' in host
assert 'cachedMenuScale != R23ConfiguredMenuScale' in host, 'Static captured menu must refresh after a scale change'
assert 'HudScale = 0.55' in ini
assert 'PreferD3D9Ex = false' in ini
print('PASS menu/game source split wiring, provider independence, config precedence and static capture invalidation')

# Same-owner failed refresh must not publish defaults or a partial config.
owner = host.split('bool R23GameMenuIsLetterboxed(HWND gameWindow) noexcept', 1)[1].split('constexpr ULONGLONG R23PixelIntervalMs', 1)[0]
assert 'const bool sameOwner = gamePid != 0 &&' in owner
assert 'cachedWindow == gameWindow && cachedPid == gamePid;' in owner
assert 'if (!sameOwner)' in owner
assert owner.index('const bool sameOwner') < owner.index('cachedWindow = gameWindow;')
assert owner.index('if (!sameOwner)') < owner.index('R23ConfiguredMenuScale = 1.0f;') < owner.index('OpenProcess(')
assert 'return false;' not in owner
assert owner.index('if (!foundConfig)') < owner.index('R23ConfiguredMenuScale = candidateMenuScale;')
print('PASS same-owner process/path/config failure retains accepted scale; new owner resets')
