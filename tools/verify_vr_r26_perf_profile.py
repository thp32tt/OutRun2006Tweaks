from pathlib import Path
import configparser
r=Path(__file__).resolve().parents[1]
p=configparser.ConfigParser(strict=True,interpolation=None);p.read(r/'OutRun2006Tweaks.ini',encoding='utf-8')
assert p.getint('Graphics','ReflectionResolution')==256
assert p.getint('VR','AntiAliasing')==2
assert p.getfloat('VR','CullingUnionMarginDegrees')==8
assert p.getboolean('Graphics','DisableStageCulling')
assert p.getboolean('VR','CullingUnionFov')
assert not p.getboolean('VR','TransparencySupersampling')
assert not p.getboolean('Graphics','TransparencySupersampling')
s=(r/'tools/Run-DX9ExFocusTest.ps1').read_text()
for value in ['-Graphics.ReflectionResolution=256','-VR.TransparencySupersampling=false','-Graphics.TransparencySupersampling=false','-AntiAliasing=2','-CullingUnionMarginDegrees=8.0']:
 assert value in s,value
s=(r/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
assert s.count('scratch.left, scratch.right, scratch.restoredView')==4
assert 'R30CopySparseVertexShadow(vb, streamOffset, stride,' in s
s=(r/'src/vr/d3d9/stereo_renderer_r7.inc').read_text()
assert 'const auto* eyeMath = R26CachedEyeMath(projection, stereo);' in s
print('PASS reflection256/transparencyOff/MSAA2/culling8 and production integration')
