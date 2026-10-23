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
if errors:
    print('VR-NEARPLANE-ACTIVE-GATE-001 RED:', '; '.join(errors))
    sys.exit(1)
print('VR-NEARPLANE-ACTIVE-GATE-001 GREEN')
