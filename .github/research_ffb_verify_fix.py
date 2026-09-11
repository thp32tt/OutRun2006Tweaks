from pathlib import Path

# The research patch renames the final pre-response composition stage.
p = Path('tools/verify_wheel_ffb_current.py')
text = p.read_text(encoding='utf-8')
old = "req(ffb, 'const LONG level = baseSteeringLevel + vibrationLevel;', 'fallback vibration uses only remaining output headroom')"
new = "req(ffb, 'const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;', 'fallback vibration uses only remaining output headroom before wheel response correction')"
if text.count(old) != 1:
    raise SystemExit(f'expected one legacy headroom verifier, found {text.count(old)}')
p.write_text(text.replace(old, new), encoding='utf-8', newline='\n')

# GCC/libstdc++ sets failbit when std::ws reaches EOF. Do not reject an otherwise
# valid numeric token merely because whitespace consumption reached EOF; only
# require that there is no non-whitespace tail after the parsed float.
p = Path('src/wheel_ffb_math.hpp')
text = p.read_text(encoding='utf-8')
old = """            valueStream >> value;\n            valueStream >> std::ws;\n            if (!valueStream || !valueStream.eof() || !std::isfinite(value) ||\n                value < 0.0f || value > 1.0f)\n                return false;\n"""
new = """            if (!(valueStream >> value) || !std::isfinite(value) ||\n                value < 0.0f || value > 1.0f)\n                return false;\n            valueStream >> std::ws;\n            if (!valueStream.eof())\n                return false;\n"""
if text.count(old) != 1:
    raise SystemExit(f'expected one response LUT token parser, found {text.count(old)}')
p.write_text(text.replace(old, new), encoding='utf-8', newline='\n')
print('updated verifier and made response LUT token parsing portable')
