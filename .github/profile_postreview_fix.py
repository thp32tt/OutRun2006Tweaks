from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected one match, found {count}: {old[:120]!r}")
    write(rel, text.replace(old, new, 1))


# 1) A generated NUL byte in the FFB profile-name reset would make the C++
# source invalid. Keep an ordinary C++ '\\0' escape in the source file.
wheel_ui = read("src/overlay/wheel_setup_ui.cpp")
if "\x00" not in wheel_ui:
    raise SystemExit("expected generated NUL byte was not found")
write("src/overlay/wheel_setup_ui.cpp", wheel_ui.replace("\x00", r"\0"))

# 2) A per-wheel profile must follow the physical wheel's FFB output identity.
# The separate FFB feel profiles still deliberately exclude this identity.
replace_once(
    "src/wheel_profile_store.hpp",
    '#include "plugin.hpp"\n\n',
    '#include "plugin.hpp"\n\nnamespace Settings\n{\n    extern Setting<std::string> WheelFFBDeviceName;\n    extern Setting<std::string> WheelFFBDeviceGuid;\n}\n\n')

replace_once(
    "src/wheel_profile_store.hpp",
    '''    struct InputOptionsSnapshot\n    {\n        std::string inputBackend;\n        std::string steeringDeadZone;\n        std::string bypassSensitivity;\n    };''',
    '''    struct InputOptionsSnapshot\n    {\n        std::string inputBackend;\n        std::string steeringDeadZone;\n        std::string bypassSensitivity;\n        std::string ffbDeviceName;\n        std::string ffbDeviceGuid;\n    };''')

replace_once(
    "src/wheel_profile_store.hpp",
    '''            Settings::InputBackend.to_string(),\n            Settings::SteeringDeadZone.to_string(),\n            Settings::BypassGameSensitivity.to_string(),\n        };''',
    '''            Settings::InputBackend.to_string(),\n            Settings::SteeringDeadZone.to_string(),\n            Settings::BypassGameSensitivity.to_string(),\n            Settings::WheelFFBDeviceName.to_string(),\n            Settings::WheelFFBDeviceGuid.to_string(),\n        };''')

replace_once(
    "src/wheel_profile_store.hpp",
    '''        Settings::InputBackend.set_from_string(snapshot.inputBackend);\n        Settings::SteeringDeadZone.set_from_string(snapshot.steeringDeadZone);\n        Settings::BypassGameSensitivity.set_from_string(snapshot.bypassSensitivity);''',
    '''        Settings::InputBackend.set_from_string(snapshot.inputBackend);\n        Settings::SteeringDeadZone.set_from_string(snapshot.steeringDeadZone);\n        Settings::BypassGameSensitivity.set_from_string(snapshot.bypassSensitivity);\n        Settings::WheelFFBDeviceName.set_from_string(snapshot.ffbDeviceName);\n        Settings::WheelFFBDeviceGuid.set_from_string(snapshot.ffbDeviceGuid);''')

replace_once(
    "src/wheel_profile_store.hpp",
    '''        file << "BypassGameSensitivity = " << Settings::BypassGameSensitivity.to_string() << "\\n";\n        if (!file)''',
    '''        file << "BypassGameSensitivity = " << Settings::BypassGameSensitivity.to_string() << "\\n";\n        file << "FFBDeviceName = " << Settings::WheelFFBDeviceName.to_string() << "\\n";\n        file << "FFBDeviceGuid = " << Settings::WheelFFBDeviceGuid.to_string() << "\\n";\n        file.flush();\n        if (!file)''')

replace_once(
    "src/wheel_profile_store.hpp",
    '''            !apply("SteeringDeadZone", Settings::SteeringDeadZone) ||\n            !apply("BypassGameSensitivity", Settings::BypassGameSensitivity))''',
    '''            !apply("SteeringDeadZone", Settings::SteeringDeadZone) ||\n            !apply("BypassGameSensitivity", Settings::BypassGameSensitivity) ||\n            !apply("FFBDeviceName", Settings::WheelFFBDeviceName) ||\n            !apply("FFBDeviceGuid", Settings::WheelFFBDeviceGuid))''')

# Flush before reporting success for FFB profiles too.
replace_once(
    "src/wheel_profile_store.hpp",
    '''        for (const Settings::SettingBase* setting : ffb_settings())\n            file << setting->key() << " = " << setting->to_string() << "\\n";\n        if (!file)''',
    '''        for (const Settings::SettingBase* setting : ffb_settings())\n            file << setting->key() << " = " << setting->to_string() << "\\n";\n        file.flush();\n        if (!file)''')

# 3) profile_exists() used to touch the filesystem every UI frame. The lists are
# already cached and refreshed explicitly, so use the cache for overwrite labels.
replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\tconst std::string* selected_wheel_profile() const\n\t{\n\t\treturn selectedWheelProfile >= 0 && selectedWheelProfile < int(wheelProfiles.size())\n\t\t\t? &wheelProfiles[selectedWheelProfile] : nullptr;\n\t}\n\n\tvoid draw_profiles()''',
    '''\tconst std::string* selected_wheel_profile() const\n\t{\n\t\treturn selectedWheelProfile >= 0 && selectedWheelProfile < int(wheelProfiles.size())\n\t\t\t? &wheelProfiles[selectedWheelProfile] : nullptr;\n\t}\n\n\tbool wheel_profile_exists_cached(const std::string& name) const\n\t{\n\t\tconst std::string wanted = WheelProfileStore::lower_ascii(name);\n\t\treturn std::any_of(wheelProfiles.begin(), wheelProfiles.end(), [&](const std::string& profile)\n\t\t{\n\t\t\treturn WheelProfileStore::lower_ascii(profile) == wanted;\n\t\t});\n\t}\n\n\tvoid draw_profiles()''')

replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\t\tconst bool profileAlreadyExists =\n\t\t\t!requestedName.empty() && WheelProfileStore::profile_exists(WheelProfileStore::Kind::Input, requestedName);''',
    '''\t\tconst bool profileAlreadyExists =\n\t\t\t!requestedName.empty() && wheel_profile_exists_cached(requestedName);''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''        const std::string* selected_ffb_profile() const\n        {\n            return selectedFfbProfile_ >= 0 && selectedFfbProfile_ < int(ffbProfiles_.size())\n                ? &ffbProfiles_[selectedFfbProfile_] : nullptr;\n        }\n\n        void draw_ffb_profiles()''',
    '''        const std::string* selected_ffb_profile() const\n        {\n            return selectedFfbProfile_ >= 0 && selectedFfbProfile_ < int(ffbProfiles_.size())\n                ? &ffbProfiles_[selectedFfbProfile_] : nullptr;\n        }\n\n        bool ffb_profile_exists_cached(const std::string& name) const\n        {\n            const std::string wanted = WheelProfileStore::lower_ascii(name);\n            return std::any_of(ffbProfiles_.begin(), ffbProfiles_.end(), [&](const std::string& profile)\n            {\n                return WheelProfileStore::lower_ascii(profile) == wanted;\n            });\n        }\n\n        void draw_ffb_profiles()''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            const bool exists = !requested.empty() &&\n                WheelProfileStore::profile_exists(WheelProfileStore::Kind::ForceFeedback, requested);''',
    '''            const bool exists = !requested.empty() && ffb_profile_exists_cached(requested);''')

# 4) Existing binding writer did not test buffered write/close errors. Profiles
# reuse it, so do not report success when the filesystem rejected the data.
replace_once(
    "src/input_manager.hpp",
    '''\t\tfile << "\\n[Keyboard]\\n";\n\t\twriteBindingSection(file, true);\n\n\t\tfile.close();\n\t\tspdlog::info(__FUNCTION__": saved to INI file: {}", iniPath.string());\n\n\t\treturn true;''',
    '''\t\tfile << "\\n[Keyboard]\\n";\n\t\twriteBindingSection(file, true);\n\n\t\tfile.flush();\n\t\tif (!file)\n\t\t{\n\t\t\tspdlog::error(__FUNCTION__ ": failed while writing INI file: {}", iniPath.string());\n\t\t\tfile.close();\n\t\t\treturn false;\n\t\t}\n\t\tfile.close();\n\t\tif (file.fail())\n\t\t{\n\t\t\tspdlog::error(__FUNCTION__ ": failed while closing INI file: {}", iniPath.string());\n\t\t\treturn false;\n\t\t}\n\t\tspdlog::info(__FUNCTION__": saved to INI file: {}", iniPath.string());\n\n\t\treturn true;''')

# Documentation: wheel profiles follow both input/calibration and the exact FFB
# output identity. Feel profiles remain device-independent.
replace_once(
    "WHEEL_FFB.md",
    '''steering deadzone, sensitivity bypass and input backend travel with that wheel profile. Loading a profile also updates the normal `OutRun2006Tweaks.input.ini`, so the selected setup survives the next restart.''',
    '''steering deadzone, sensitivity bypass, input backend and the exact selected DirectInput FFB output identity travel with that wheel profile. Loading a profile also updates the normal `OutRun2006Tweaks.input.ini` and user settings, so the selected setup survives the next restart. The separately named FFB feel profiles remain device-independent.''')

# Strengthen source-only verifier against the issue found during post-review.
verify = read("tools/verify_wheel_ffb_current.py")
replace_marker = "req(profiles, 'BypassGameSensitivity = ', 'wheel profile stores sensitivity bypass')\n"
if replace_marker not in verify:
    raise SystemExit("profile verifier marker missing")
verify = verify.replace(
    replace_marker,
    replace_marker +
    "req(profiles, 'FFBDeviceName = ', 'wheel profile stores FFB output name')\n"
    "req(profiles, 'FFBDeviceGuid = ', 'wheel profile stores exact FFB output GUID')\n",
    1)
verify = verify.replace(
    "for rel, text in [\n",
    "for rel, text in [\n",
    1)
# Add the profile store to brace/NUL integrity checks without disturbing the
# existing ordered checks.
verify = verify.replace(
    "    ('src/overlay/wheel_setup_ui.cpp', wheel_ui),\n]:\n    if text.count('{') != text.count('}'):",
    "    ('src/overlay/wheel_setup_ui.cpp', wheel_ui),\n    ('src/wheel_profile_store.hpp', profiles),\n]:\n    if '\\x00' in text:\n        raise SystemExit(f'CURRENT VERIFY FAILED [NUL byte in source]: {rel}')\n    if text.count('{') != text.count('}'):",
    1)
verify = verify.replace(
    "req(bind_ui, 'manager.saveBindingIni(Module::BindingsIniPath)', 'loaded wheel profile is durable in canonical binding file')\n",
    "req(bind_ui, 'manager.saveBindingIni(Module::BindingsIniPath)', 'loaded wheel profile is durable in canonical binding file')\n"
    "req(bind_ui, 'wheel_profile_exists_cached', 'input profile overwrite check uses cached list')\n"
    "req(wheel_ui, 'ffb_profile_exists_cached', 'FFB profile overwrite check uses cached list')\n"
    "req(input_hpp, 'file.flush();', 'binding/profile writer checks buffered write errors')\n",
    1)
write("tools/verify_wheel_ffb_current.py", verify)

subprocess.run(["python", "tools/verify_wheel_ffb_current.py"], cwd=ROOT, check=True)
subprocess.run([
    "git", "add", "src/wheel_profile_store.hpp", "src/overlay/input_bindings_ui.cpp",
    "src/overlay/wheel_setup_ui.cpp", "src/input_manager.hpp", "tools/verify_wheel_ffb_current.py",
    "WHEEL_FFB.md"
], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "fix: harden wheel profile identity and persistence [skip ci]"], cwd=ROOT, check=True)
