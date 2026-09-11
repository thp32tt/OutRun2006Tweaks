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
        raise SystemExit(f'{path}: expected one match, got {count}')
    write(path, s.replace(old, new, 1))


path = 'src/overlay/wheel_setup_ui.cpp'
replace_once(
    path,
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
''',
    '''                const std::string configuredGuid = lower_identity(configuredGuidValue);
                const std::string configuredName = lower_identity(configuredNameValue);
                std::string autoMatchedFfbGuid;
                if (ffbOutput && configuredGuid.empty() && !configuredName.empty())
                {
                    // Match the FFB engine's DeviceName behavior: before F11 has
                    // saved an exact GUID, values such as the shipped "MOZA"
                    // default are case-insensitive product-name substrings.
                    for (const auto& dev : devices)
                    {
                        if (dev.ffb && lower_identity(dev.name).find(configuredName) != std::string::npos)
                        {
                            autoMatchedFfbGuid = dev.guidKey;
                            break;
                        }
                    }
                }
                auto isSelectedDevice = [&](const DeviceInfo& dev)
                {
                    if (ffbOnly && !dev.ffb)
                        return false;
                    if (!configuredGuid.empty())
                        return dev.guidKey == configuredGuid;
                    if (ffbOutput && !autoMatchedFfbGuid.empty())
                        return dev.guidKey == autoMatchedFfbGuid;
                    return dev.name == configuredNameValue;
                };

                std::string preview;
''')

verify_path = 'tools/verify_wheel_ffb_current.py'
v = read(verify_path)
anchor = "req(wheel_ui, 'draw_device_combo(\"FFB Output\", true', 'FFB selector filters to FFB-capable interfaces')\n"
if anchor not in v:
    raise SystemExit('verifier FFB selector anchor missing')
v = v.replace(
    anchor,
    anchor + "req(wheel_ui, 'autoMatchedFfbGuid', 'FFB selector mirrors DeviceName substring auto-match before GUID save')\n",
    1)
write(verify_path, v)

subprocess.run(['python3', 'tools/verify_wheel_ffb_current.py'], check=True)
print('FFB SELECTOR AUTO-MATCH REVIEW VERIFIED WITHOUT COMPILATION')
