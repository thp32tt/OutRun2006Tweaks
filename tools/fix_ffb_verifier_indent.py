from pathlib import Path

path = Path('tools/verify_wheel_ffb_current.py')
text = path.read_text(encoding='utf-8')
old = "constantEffectPolar_ = false;\\n            prevConstantLevel_ = 0;\\n            lastConstantWriteTick_ = 0;"
new = "constantEffectPolar_ = false;\\n                    prevConstantLevel_ = 0;\\n                    lastConstantWriteTick_ = 0;"
if old not in text:
    raise SystemExit('old CARTESIAN cache verifier pattern not found')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Updated CARTESIAN cache verifier for nested validated fallback')
