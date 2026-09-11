from pathlib import Path
import subprocess


def read(path):
    return Path(path).read_text(encoding='utf-8')


def write(path, value):
    Path(path).write_text(value, encoding='utf-8')


def replace_once(path, old, new):
    s = read(path)
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, got {count}: {old[:140]!r}')
    write(path, s.replace(old, new, 1))


# Pass 1 — device identity / setup UI.
# A saved GUID/name should remain visible when unplugged, but must not look like
# a currently connected device. Prefer the actual matched device name when it is
# present and clearly mark stale saved identities when it is not.
replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '''                std::string preview = configuredNameValue;
                if (preview.empty())
                    preview = first_device_name(ffbOnly);
                const std::string configuredGuid = lower_identity(configuredGuidValue);
                auto isSelectedDevice = [&](const DeviceInfo& dev)
                {
                    if (ffbOnly && !dev.ffb)
                        return false;
                    return !configuredGuid.empty()
                        ? dev.guidKey == configuredGuid
                        : dev.name == configuredNameValue;
                };

                if (ImGui::BeginCombo(label, preview.c_str()))
''',
    '''                const std::string configuredGuid = lower_identity(configuredGuidValue);
                auto isSelectedDevice = [&](const DeviceInfo& dev)
                {
                    if (ffbOnly && !dev.ffb)
                        return false;
                    return !configuredGuid.empty()
                        ? dev.guidKey == configuredGuid
                        : dev.name == configuredNameValue;
                };

                std::string preview;
                for (const auto& dev : devices)
                {
                    if (isSelectedDevice(dev))
                    {
                        preview = dev.name;
                        break;
                    }
                }
                if (preview.empty())
                {
                    if (!configuredNameValue.empty())
                        preview = configuredNameValue + " (not connected)";
                    else if (!configuredGuid.empty())
                        preview = "Saved DirectInput device (not connected)";
                    else
                        preview = first_device_name(ffbOnly);
                }

                if (ImGui::BeginCombo(label, preview.c_str()))
''')
replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '            ImGui::TextDisabled("Settings > WheelFFB is hidden; changes on this page apply live. SDL gamepad rumble is suppressed while wheel FFB is enabled.");\n',
    '            ImGui::TextDisabled("Settings > WheelFFB is hidden; changes on this page apply live. Gamepad rumble is suppressed only while DirectInput FFB owns an output device.");\n')

# Pass 2 — hook / mode lifecycle.
# UseNewInput and the legacy stack are mutually exclusive at installation time.
# Inside the legacy stack, Universal vs compatibility/R3 ownership is selected
# at runtime so F11 can enable the universal profile without restarting.
replace_once(
    'src/hooks_wheel_input_compat_v2.hpp',
    '''        bool validate() override
        {
            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                !Settings::WheelUniversalSetupEnable;
        }
''',
    '''        bool validate() override
        {
            // Install with the legacy stack so F11 can switch the universal
            // profile live. active() remains the runtime ownership gate.
            return Settings::WheelInputCompatibility && !Settings::UseNewInput;
        }
''')
replace_once(
    'src/overlay/wheel_setup_ui.cpp',
    '        bool validate() override { return Settings::WheelInputCompatibility && !Settings::UseNewInput && Settings::WheelUniversalSetupEnable; }\n',
    '        // Install with the legacy stack; active() gates live F11 ownership.\n        bool validate() override { return Settings::WheelInputCompatibility && !Settings::UseNewInput; }\n')
replace_once(
    'src/hooks_wheel_r3_menu_dpad.hpp',
    '''            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                !Settings::WheelUniversalSetupEnable &&
                Settings::WheelMenuR3DirectDPad;
''',
    '''            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                Settings::WheelMenuR3DirectDPad;
''')
replace_once(
    'src/hooks_wheel_r3_menu_ab.hpp',
    '''            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                !Settings::WheelUniversalSetupEnable &&
                Settings::WheelMenuR3DirectAB;
''',
    '''            return Settings::WheelInputCompatibility &&
                !Settings::UseNewInput &&
                Settings::WheelMenuR3DirectAB;
''')

# Pass 3 — DirectInput output ownership.
# No behavior change was needed after review; assert that rumble suppression is
# tied to a real initialized FFB owner rather than merely the Enable setting.
ffb = read('src/hooks_wheel_ffb.cpp')
if 'return Settings::WheelFFBEnable && initialized_ && device_ && !panicStopped_;' not in ffb:
    raise SystemExit('FFB ownership invariant missing')
if 'apply_live_effect_gain' in ffb or 'configured_effect_gain' in ffb:
    raise SystemExit('dead live-effect gain path unexpectedly returned')

# Pass 4 — physics state semantics.
# At a stop the estimator keeps its calibrated basis, but there is no valid
# dynamic beta/yaw/front-slip sample. Keep sampleValid false after clearing.
replace_once(
    'src/hooks_wheel_vehicle_dynamics.hpp',
    '''        if (speedNorm <= 0.04f)
        {
            clear_dynamic_state();
            sampleValid_ = calibrated_;
            return;
        }
''',
    '''        if (speedNorm <= 0.04f)
        {
            clear_dynamic_state();
            return;
        }
''')
replace_once(
    'tools/test_wheel_ffb_current.cpp',
    ' d.update(&c,0,0,0);require(d.frontSlip()==0&&d.yawRate()==0,"stop clear");\n',
    ' d.update(&c,0,0,0);require(d.frontSlip()==0&&d.yawRate()==0&&!d.sampleValid(),"stop clear and invalid dynamic sample");\n')

# Pass 5 — maintainability / future CI correctness.
# The dead live-gain log marker was removed from source in the previous pass;
# leaving it in the binary marker list would make the next real build fail for
# the wrong reason. Restore the normal Build trigger now that editing is done.
build_path = '.github/workflows/build.yml'
build = read(build_path)
build = build.replace(
    '''on:
  push:
    paths-ignore:
      - '.github/workflows/source-edit.yml'
  pull_request:
''',
    '''on:
  push:
  pull_request:
''',
    1)
marker = '            "WheelFFB: live GlobalStrength applied to active effects",\n'
if marker not in build:
    raise SystemExit('build marker preimage missing')
build = build.replace(marker, '', 1)
write(build_path, build)

# Keep the structural verifier aligned with live-switchable legacy ownership.
verify_path = 'tools/verify_wheel_ffb_current.py'
v = read(verify_path)
v = v.replace(
    "compat_v2 = read('src/hooks_wheel_input_compat_v2.hpp')\n"
    "req(compat_v2, 'return Settings::WheelInputCompatibility &&\\n                !Settings::UseNewInput &&\\n                !Settings::WheelUniversalSetupEnable;', 'legacy V2 hook install gate is mutually exclusive')\n"
    "req(wheel_ui, '!Settings::UseNewInput && Settings::WheelUniversalSetupEnable', 'universal legacy hook has exclusive install gate')\n",
    "compat_v2 = read('src/hooks_wheel_input_compat_v2.hpp')\n"
    "r3_dpad = read('src/hooks_wheel_r3_menu_dpad.hpp')\n"
    "r3_ab = read('src/hooks_wheel_r3_menu_ab.hpp')\n"
    "req(compat_v2, 'return Settings::WheelInputCompatibility && !Settings::UseNewInput;', 'legacy V2 installed for live universal switching')\n"
    "req(wheel_ui, 'bool validate() override { return Settings::WheelInputCompatibility && !Settings::UseNewInput; }', 'universal legacy hook installed for live switching')\n"
    "req(r3_dpad, '!Settings::UseNewInput &&\\n                Settings::WheelMenuR3DirectDPad;', 'R3 DPad hook can remain dormant under universal ownership')\n"
    "req(r3_ab, '!Settings::UseNewInput &&\\n                Settings::WheelMenuR3DirectAB;', 'R3 AB hook can remain dormant under universal ownership')\n",
    1)
anchor = "req(dyn, 'headingValid_ = false; // The next heading', 'missing samples break derivative baseline')\n"
if anchor not in v:
    raise SystemExit('verifier dynamics anchor missing')
v = v.replace(
    anchor,
    "forbid(dyn, 'sampleValid_ = calibrated_', 'stopped vehicle has no valid dynamic SAT sample')\n" + anchor,
    1)
write(verify_path, v)

# Structural source checks only. Do not call verify_wheel_ffb_math.py, CMake,
# MSBuild, cl.exe, or any compiler in this workflow.
subprocess.run(['python3', 'tools/verify_wheel_ffb_current.py'], check=True)

# Extra source-only assertions covering this review's intended state.
for path in ('src/overlay/wheel_setup_ui.cpp', 'src/hooks_wheel_input_compat_v2.hpp',
             'src/hooks_wheel_r3_menu_dpad.hpp', 'src/hooks_wheel_r3_menu_ab.hpp',
             'src/hooks_wheel_vehicle_dynamics.hpp', 'tools/test_wheel_ffb_current.cpp',
             '.github/workflows/build.yml'):
    data = read(path)
    if data.count('{') != data.count('}'):
        raise SystemExit(f'brace mismatch after review: {path}')

print('FIVE-PASS SOURCE REVIEW FIXES VERIFIED WITHOUT COMPILATION')
