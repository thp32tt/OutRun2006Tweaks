from pathlib import Path

p = Path('src/hooks_wheel_ffb.cpp')
t = p.read_text(encoding='utf-8')
old = '''            if ((object->dwType & DIDFT_FFACTUATOR) != 0 && self->actuatorAxes_.size() < 2)\n                self->actuatorAxes_.push_back(object->dwOfs);\n'''
new = '''            if ((object->dwType & DIDFT_FFACTUATOR) != 0)\n            {\n                const DWORD offset = object->dwOfs;\n                if (std::find(self->actuatorAxes_.begin(), self->actuatorAxes_.end(), offset) ==\n                    self->actuatorAxes_.end())\n                {\n                    self->actuatorAxes_.push_back(offset);\n                }\n            }\n'''
if t.count(old) != 1:
    raise SystemExit(f'expected one capped actuator enumeration, found {t.count(old)}')
t = t.replace(old, new, 1)
p.write_bytes(t.replace('\n', '\r\n').encode('utf-8'))

v = Path('tools/verify_wheel_ffb_current.py')
s = v.read_text(encoding='utf-8')
needle = "req(ffb, 'for (const DWORD detectedAxis : actuatorAxes_)', 'ConstantForce probes every enumerated actuator axis after canonical X')\n"
extra = needle + "forbid(ffb, 'actuatorAxes_.size() < 2', 'FFB actuator enumeration is not arbitrarily capped at two objects')\n"
if s.count(needle) != 1:
    raise SystemExit('all-actuator verifier marker missing')
s = s.replace(needle, extra, 1)
v.write_bytes(s.replace('\n', '\r\n').encode('utf-8'))
print('Removed two-actuator enumeration cap and deduplicated offsets')
