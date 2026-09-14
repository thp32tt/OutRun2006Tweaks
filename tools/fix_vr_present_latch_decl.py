from pathlib import Path
p = Path('src/vr_renderer_probe.cpp')
s = p.read_text(encoding='utf-8')
old = '\t\tvoid ReusePresentPoseForScene()\n'
new = '\t\tvoid InvalidateVerifiedWvp();\n\n\t\tvoid ReusePresentPoseForScene()\n'
if s.count(old) != 1:
    raise SystemExit(f'expected one ReusePresentPoseForScene, got {s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('added forward declaration')
