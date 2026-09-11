from pathlib import Path
import re
import subprocess


def read(path):
    return Path(path).read_text(encoding='utf-8')


def write(path, value):
    Path(path).write_text(value, encoding='utf-8')


def replace_once(path, old, new):
    s = read(path)
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, got {count}: {old[:100]!r}')
    write(path, s.replace(old, new, 1))


# Review pass 2: install the V2 legacy compatibility layer only when it can
# actually be active. UniversalWheelProfile owns the same legacy entry points.
replace_once(
    'src/hooks_wheel_input_compat_v2.hpp',
    '''        bool validate() override
        {
            return Settings::WheelInputCompatibility && !Settings::UseNewInput;
        }
''',
    '''        bool validate() override
        {
            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                !Settings::WheelUniversalSetupEnable;
        }
''')

# Review pass 5: GlobalStrength is already part of the force model and every
# DirectInput effect is intentionally created at DI_FFNOMINALMAX. The old
# live-effect-gain updater can therefore never observe a changed gain; remove
# the dead state machine rather than keeping misleading retry/logging code.
ffb_path = 'src/hooks_wheel_ffb.cpp'
s = read(ffb_path)
s = s.replace('            apply_live_effect_gain();\n\n', '', 1)
s = s.replace('            lastEffectGain_ = configured_effect_gain();\n', '', 1)
s = s.replace(
    '''            lastEffectGain_ = 0xFFFFFFFFu;
            nextGainRetryTick_ = 0;
            lastGainErrorLog_ = 0;
''', '', 1)
s = s.replace(
    '''        DWORD lastGainErrorLog_ = 0;
        DWORD lastEffectGain_ = 0xFFFFFFFFu;
        DWORD nextGainRetryTick_ = 0;
''', '', 1)
pattern = re.compile(
    r'''        DWORD configured_effect_gain\(\) const\n        \{.*?\n        \}\n\n        void apply_live_effect_gain\(\)\n        \{.*?\n        \}\n\n(?=        bool create_constant_effect\(\))''',
    re.S)
s, count = pattern.subn('', s, count=1)
if count != 1:
    raise SystemExit(f'{ffb_path}: dead live-gain block match count={count}')
for forbidden in ('apply_live_effect_gain', 'configured_effect_gain', 'lastEffectGain_', 'nextGainRetryTick_', 'lastGainErrorLog_'):
    if forbidden in s:
        raise SystemExit(f'{ffb_path}: stale live-gain symbol remains: {forbidden}')
write(ffb_path, s)

# Strengthen source-only verification so the same two architecture mistakes
# cannot silently return later.
verify_path = 'tools/verify_wheel_ffb_current.py'
v = read(verify_path)
v = v.replace(
    "req(read('src/hooks_wheel_input_compat_v2.hpp'), '!Settings::UseNewInput', 'legacy compatibility hook excluded from new input')\n",
    "compat_v2 = read('src/hooks_wheel_input_compat_v2.hpp')\n"
    "req(compat_v2, 'return Settings::WheelInputCompatibility &&\\n                !Settings::UseNewInput &&\\n                !Settings::WheelUniversalSetupEnable;', 'legacy V2 hook install gate is mutually exclusive')\n",
    1)
anchor = "req(ffb, 'DIPROP_FFGAIN', 'device gain configured separately from effect gain')\n"
if anchor not in v:
    raise SystemExit('verify: DIPROP_FFGAIN anchor missing')
v = v.replace(
    anchor,
    anchor +
    "forbid(ffb, 'apply_live_effect_gain', 'dead live effect-gain updater removed')\n"
    "forbid(ffb, 'configured_effect_gain', 'effect gain fixed nominal at creation')\n"
    "forbid(ffb, 'lastEffectGain_', 'dead live-gain state removed')\n",
    1)
write(verify_path, v)

# Source-only structural validation. This script must never invoke a compiler,
# CMake, MSBuild, or verify_wheel_ffb_math.py.
subprocess.run(['python3', 'tools/verify_wheel_ffb_current.py'], check=True)

# One-shot source-edit helper cleanup. The workflow itself removes this file.
