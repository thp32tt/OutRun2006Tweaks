#!/usr/bin/env python3
"""Source-level negative/positive contract for +TIME-only optical probe."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
def r(f): return (p/f).read_text(encoding='utf-8')
h=r('src/vr/game/stage_extension_optical_probe.hpp')
x=r('src/vr/d3d9/stereo_renderer_r30.cpp')
y=r('src/vr/d3d9/stereo_renderer_r33.cpp')
s=r('src/vr/settings.cpp')
assert '"StageOpticalProbeMode", 0,' in s
assert '"StageOpticalProbeTarget", 0,' in s
for tok in ['IsExactFiniteResultHud','StageExtensionTime','c.queueNode!=nullptr','ResultProgress','RankMarkerClipSprite','Mode::Off']:
 assert tok in h,tok
assert y.count('R33StageOpticalDirect(')==5
assert 'if (!rasterReady) return false;' in y
assert x.count('Mode::ZeroDisparity')==2
assert x.count('StageOpticalProbe::Selected(')==2
assert 'state.stageExtensionClipFromGameNdc[1] =' in x
assert 'std::memcpy(eyeConstants[1], eyeConstants[0],' in x
print('PASS +TIME opt-in four draw APIs, fixedfn/shader eye clips, negative other-producer cases')
