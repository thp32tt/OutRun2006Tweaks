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
assert 'ReadMenuScaleOverride(path, R23ConfiguredMenuScale)' in host
assert host.count('ReadMenuScaleOverride(path, R23ConfiguredMenuScale)') == 2, 'Base + user INI precedence'
assert 'clientGameState, R23ConfiguredMenuScale);' in host
assert 'cachedMenuScale != R23ConfiguredMenuScale' in host, 'Static captured menu must refresh after a scale change'
assert 'HudScale = 0.55' in ini
assert 'PreferD3D9Ex = false' in ini
print('PASS menu/game source split wiring, provider independence, config precedence and static capture invalidation')
