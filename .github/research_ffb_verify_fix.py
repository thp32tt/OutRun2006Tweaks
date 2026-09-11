from pathlib import Path

p = Path('tools/verify_wheel_ffb_current.py')
text = p.read_text(encoding='utf-8')
old = "req(ffb, 'const LONG level = baseSteeringLevel + vibrationLevel;', 'fallback vibration uses only remaining output headroom')"
new = "req(ffb, 'const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;', 'fallback vibration uses only remaining output headroom before wheel response correction')"
if text.count(old) != 1:
    raise SystemExit(f'expected one legacy headroom verifier, found {text.count(old)}')
p.write_text(text.replace(old, new), encoding='utf-8', newline='\n')
print('updated fallback-headroom verifier for the pre-response output stage')
