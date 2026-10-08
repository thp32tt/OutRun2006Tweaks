#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path('src/hooks_graphics.cpp')
s = p.read_text(encoding='utf-8')
needle = '''if (Settings::VRPositionalTracking &&\n\t\t\t\tSettings::VRStereo &&\n\t\t\t\tOutRunVR::RuntimeEligibility::MayInjectStereo() &&'''
include = '#include "vr/runtime_eligibility.hpp"'
legacy = 'if (Settings::VREnabled && Settings::VRPositionalTracking &&'
errors = []
if include not in s:
    errors.append('runtime eligibility header missing')
if needle not in s:
    errors.append('near-plane active-stereo eligibility gate missing')
if legacy in s:
    errors.append('legacy VREnabled-only near-plane gate still present')

# Original Clr_SceneEffect (EXE RVA 0xBE70) temporarily sets a 0.05f near
# plane for lens/SceneEffect. A nested SceneEffect entry must retain the
# enclosing caller's 'override disabled' state rather than unconditionally
# turning the gameplay near-plane rewrite back on.
def scene_effect_scope(source):
    marker = 'static void Clr_SceneEffect_dest(int a1)'
    start = source.find(marker)
    if start < 0:
        raise ValueError('Clr_SceneEffect hook missing')
    begin = source.find('{', start)
    depth = 0
    for i in range(begin, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[begin:i + 1]
    raise ValueError('unterminated SceneEffect hook')

def verify_scene_effect_suppression(source):
    scope = scene_effect_scope(source)
    order = (
        'const bool previousAllowZnearOverride = FixZBufferPrecision::allow_znear_override;',
        'FixZBufferPrecision::allow_znear_override = false;',
        'camera->perspective_znear_BC = 0.05f;',
        'CalcCameraMatrix_dest(camera);',
        'Clr_SceneEffect.call(a1);',
        'camera->perspective_znear_BC = prev;',
        'FixZBufferPrecision::allow_znear_override = previousAllowZnearOverride;',
    )
    positions = [scope.find(token) for token in order]
    if min(positions) < 0 or positions != sorted(positions):
        return False
    if 'FixZBufferPrecision::allow_znear_override = true;' in scope:
        return False
    return True

if not verify_scene_effect_suppression(s):
    errors.append('SceneEffect near-plane suppression not restored to caller state')
else:
    # One distinct injected fault: restore-to-true instead of caller state.
    broken = s.replace(
        'FixZBufferPrecision::allow_znear_override = previousAllowZnearOverride;',
        'FixZBufferPrecision::allow_znear_override = true;', 1)
    if verify_scene_effect_suppression(broken):
        errors.append('SceneEffect nested-suppression negative test not detected')

if errors:
    print('VR-NEARPLANE-ACTIVE-GATE-001 RED:', '; '.join(errors))
    sys.exit(1)
print('VR-NEARPLANE-ACTIVE-GATE-001 GREEN')
