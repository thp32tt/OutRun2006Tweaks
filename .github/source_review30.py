from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools/verify_wheel_ffb_current.py"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected exactly one match, got {count}: {old[:160]!r}")
    write(rel, text.replace(old, new, 1))


def regex_once(rel, pattern, replacement):
    text = read(rel)
    new, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{rel}: regex expected exactly one match: {pattern!r}")
    write(rel, new)


def verify():
    subprocess.run(["python3", str(VERIFY)], cwd=ROOT, check=True)


def commit(message, *paths):
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        raise SystemExit(f"no changes staged for {message}")
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)


bind_ui = "src/overlay/input_bindings_ui.cpp"
wheel_ui = "src/overlay/wheel_setup_ui.cpp"
input_cpp = "src/input_manager.cpp"
settings_ui = "src/overlay/settings_ui.cpp"
overlay_cpp = "src/overlay/overlay.cpp"
hooks_input = "src/hooks_input.cpp"
compat_v2 = "src/hooks_wheel_input_compat_v2.hpp"
r3_dpad = "src/hooks_wheel_r3_menu_dpad.hpp"
r3_ab = "src/hooks_wheel_r3_menu_ab.hpp"
verifier = "tools/verify_wheel_ffb_current.py"
release_notes = "RELEASE_NOTES_v0.1.md"
discord_share = "DISCORD_SHARE_v0.1.md"

# Review findings 1-4: Quick Setup should replace only the same physical raw
# device, and loading/saving bindings must not silently destroy or fail to
# persist a user's in-session edits.
replace_once(
    bind_ui,
    '''\tbool unsavedChanges = false;\n\tbool confirmingReset = false;\n\tbool calibrationOpen = false;''',
    '''\tbool unsavedChanges = false;\n\tbool confirmingReset = false;\n\tbool confirmingLoad = false;\n\tstd::string persistenceStatus;\n\tbool calibrationOpen = false;''')

replace_once(
    bind_ui,
    '''\t// Quick Setup replaces only the same broad input source it just captured.\n\t// A wheel/raw-device pass must not erase the default gamepad bindings: the\n\t// whole point of this branch is that a wheel, pedals and a pad can coexist.\n\tstatic bool same_source_family(const InputBinding& existing, const InputBinding& candidate)\n\t{\n\t\tif (candidate.isRawDevice()) return existing.isRawDevice();\n\t\tif (candidate.isGamepad()) return existing.isGamepad();\n\t\tif (candidate.isKeyboard()) return existing.isKeyboard();\n\t\treturn false;\n\t}''',
    '''\t// Quick Setup replaces only the source it just captured. For raw SDL\n\t// devices, source family alone is too broad: a wheel, pedal set, shifter,\n\t// button box and mapped gamepad may all be Joy* bindings at the same time.\n\t// Resolve both bindings to their current physical SDL instance and replace\n\t// only bindings from that same device. Disconnected/unresolved bindings are\n\t// deliberately preserved rather than guessed away.\n\tstatic bool same_source_family(const InputBinding& existing, const InputBinding& candidate)\n\t{\n\t\tif (candidate.isRawDevice())\n\t\t{\n\t\t\tif (!existing.isRawDevice())\n\t\t\t\treturn false;\n\t\t\tconst auto* existingDevice = InputManager::instance.deviceForBinding(existing);\n\t\t\tconst auto* candidateDevice = InputManager::instance.deviceForBinding(candidate);\n\t\t\treturn existingDevice && candidateDevice &&\n\t\t\t\texistingDevice->instanceId == candidateDevice->instanceId;\n\t\t}\n\t\tif (candidate.isGamepad()) return existing.isGamepad();\n\t\tif (candidate.isKeyboard()) return existing.isKeyboard();\n\t\treturn false;\n\t}''')

replace_once(
    bind_ui,
    '''\tvoid start_quick_setup()\n\t{\n\t\tquickSetupBackup.clear();\n\t\tquickSetupPreviousUnsaved = unsavedChanges;''',
    '''\tvoid start_quick_setup()\n\t{\n\t\tquickSetupBackup.clear();\n\t\tconfirmingLoad = false;\n\t\tpersistenceStatus.clear();\n\t\tquickSetupPreviousUnsaved = unsavedChanges;''')

replace_once(
    bind_ui,
    '''\t\tif (ImGui::Button("Save & Drive"))\n\t\t{\n\t\t\tif (InputManager::instance.saveBindingIni(Module::BindingsIniPath))\n\t\t\t{\n\t\t\t\tquickSetupBackup.clear();\n\t\t\t\tquickSetupComplete = false;\n\t\t\t\tunsavedChanges = false;\n\t\t\t\tdialogOpen = false;\n\t\t\t\tImGui::CloseCurrentPopup();\n\t\t\t}\n\t\t}''',
    '''\t\tif (ImGui::Button("Save & Drive"))\n\t\t{\n\t\t\tif (InputManager::instance.saveBindingIni(Module::BindingsIniPath))\n\t\t\t{\n\t\t\t\tquickSetupBackup.clear();\n\t\t\t\tquickSetupComplete = false;\n\t\t\t\tunsavedChanges = false;\n\t\t\t\tconfirmingLoad = false;\n\t\t\t\tpersistenceStatus = "Bindings saved.";\n\t\t\t\tdialogOpen = false;\n\t\t\t\tImGui::CloseCurrentPopup();\n\t\t\t}\n\t\t\telse\n\t\t\t\tpersistenceStatus = "Could not save bindings. Check folder permissions and OutRun2006Tweaks.log.";\n\t\t}''')

replace_once(
    bind_ui,
    '''\t\tif (ImGui::Button("Cancel"))\n\t\t{\n\t\t\trestore_quick_setup_backup();\n\t\t\tImGui::CloseCurrentPopup();\n\t\t}\n\t\tImGui::EndPopup();''',
    '''\t\tif (ImGui::Button("Cancel"))\n\t\t{\n\t\t\trestore_quick_setup_backup();\n\t\t\tImGui::CloseCurrentPopup();\n\t\t}\n\t\tif (!persistenceStatus.empty())\n\t\t\tImGui::TextWrapped("%s", persistenceStatus.c_str());\n\t\tImGui::EndPopup();''')

replace_once(
    bind_ui,
    '''\t\t\tif (ImGui::Button(unsavedChanges ? "Save bindings*##save" : "Save bindings##save"))\n\t\t\t\tif (manager.saveBindingIni(Module::BindingsIniPath))\n\t\t\t\t\tunsavedChanges = false;\n\n\t\t\tImGui::SameLine();\n\n\t\t\tif (ImGui::Button("Load bindings"))\n\t\t\t\tif (manager.readBindingIni(Module::BindingsIniPath))\n\t\t\t\t\tunsavedChanges = false;\n\n\t\t\t// Two lines are reserved below: the unsaved note and the button row.\n\t\t\tconst float footerHeight = ImGui::GetFrameHeightWithSpacing() + ImGui::GetTextLineHeightWithSpacing();''',
    '''\t\t\tif (ImGui::Button(unsavedChanges ? "Save bindings*##save" : "Save bindings##save"))\n\t\t\t{\n\t\t\t\tif (manager.saveBindingIni(Module::BindingsIniPath))\n\t\t\t\t{\n\t\t\t\t\tunsavedChanges = false;\n\t\t\t\t\tconfirmingLoad = false;\n\t\t\t\t\tpersistenceStatus = "Bindings saved.";\n\t\t\t\t}\n\t\t\t\telse\n\t\t\t\t\tpersistenceStatus = "Could not save bindings. Check folder permissions and OutRun2006Tweaks.log.";\n\t\t\t}\n\n\t\t\tImGui::SameLine();\n\n\t\t\tconst char* loadLabel = unsavedChanges && confirmingLoad\n\t\t\t\t? "Discard edits & load?##load" : "Load bindings##load";\n\t\t\tif (ImGui::Button(loadLabel))\n\t\t\t{\n\t\t\t\tif (unsavedChanges && !confirmingLoad)\n\t\t\t\t{\n\t\t\t\t\tconfirmingLoad = true;\n\t\t\t\t\tpersistenceStatus = "Click again to discard unsaved edits and reload the saved binding file.";\n\t\t\t\t}\n\t\t\t\telse\n\t\t\t\t{\n\t\t\t\t\tif (manager.readBindingIni(Module::BindingsIniPath))\n\t\t\t\t\t{\n\t\t\t\t\t\tunsavedChanges = false;\n\t\t\t\t\t\tpersistenceStatus = "Saved bindings loaded.";\n\t\t\t\t\t}\n\t\t\t\t\telse\n\t\t\t\t\t\tpersistenceStatus = "Could not load bindings; the current bindings were kept.";\n\t\t\t\t\tconfirmingLoad = false;\n\t\t\t\t}\n\t\t\t}\n\n\t\t\t// Three lines are reserved below: unsaved state, persistence status\n\t\t\t// and the exit/reset button row.\n\t\t\tconst float footerHeight = ImGui::GetFrameHeightWithSpacing() +\n\t\t\t\t(ImGui::GetTextLineHeightWithSpacing() * 2.0f);''')

replace_once(
    bind_ui,
    '''\t\t\tImGui::TextDisabled("%s", unsavedChanges\n\t\t\t\t? "Note: unsaved bindings are active now but will be lost after restart."\n\t\t\t\t: "");\n\n\t\t\tif (unsavedChanges)''',
    '''\t\t\tImGui::TextDisabled("%s", unsavedChanges\n\t\t\t\t? "Note: unsaved bindings are active now but will be lost after restart."\n\t\t\t\t: "");\n\t\t\tImGui::TextDisabled("%s", persistenceStatus.c_str());\n\n\t\t\tif (unsavedChanges)''')

replace_once(
    bind_ui,
    '''\t\t\t\tif (ImGui::Button("Save & Return to game"))\n\t\t\t\t{\n\t\t\t\t\tif (manager.saveBindingIni(Module::BindingsIniPath))\n\t\t\t\t\t{\n\t\t\t\t\t\tunsavedChanges = false;\n\t\t\t\t\t\tdialogOpen = false;\n\t\t\t\t\t}\n\t\t\t\t}''',
    '''\t\t\t\tif (ImGui::Button("Save & Return to game"))\n\t\t\t\t{\n\t\t\t\t\tif (manager.saveBindingIni(Module::BindingsIniPath))\n\t\t\t\t\t{\n\t\t\t\t\t\tunsavedChanges = false;\n\t\t\t\t\t\tconfirmingLoad = false;\n\t\t\t\t\t\tpersistenceStatus = "Bindings saved.";\n\t\t\t\t\t\tdialogOpen = false;\n\t\t\t\t\t}\n\t\t\t\t\telse\n\t\t\t\t\t\tpersistenceStatus = "Could not save bindings. Check folder permissions and OutRun2006Tweaks.log.";\n\t\t\t\t}''')

verify()
commit("ux: protect multi-device bindings and persistence [skip ci]", bind_ui)

# Review findings 5-9: generic Settings should not compete with the dedicated
# Legacy Wheel Setup, and legacy-only helpers should stay out of the default
# new-input Controls list. WheelInputCompatibility itself really does require a
# restart because its hook stack is installed only at startup.
replace_once(
    input_cpp,
    '''\tSetting<bool> WheelInputCompatibility{ "Controls", "WheelInputCompatibility", false,\n\t\t"Use the original-game DirectInput wheel path as a compatibility fallback. Disable UseNewInput when enabling this." };''',
    '''\tSetting<bool> WheelInputCompatibility{ "Controls", "WheelInputCompatibility", false,\n\t\t"Advanced fallback for the original-game DirectInput wheel path. It only activates when UseNewInput is false at launch; both mode changes require a restart." };''')

replace_once(
    input_cpp,
    '''\t\tSettings::UseNewInput.needs_restart();\n\t\tSettings::UseNewInput.hidden(Settings::UseNewInput); // Unhide if UseNewInput is disabled for some reason, hide if it's enabled\n\t\tSettings::InputBackend.needs_restart();''',
    '''\t\tSettings::UseNewInput.needs_restart();\n\t\t// Keep this hidden while the modern path is active: changing it live\n\t\t// would stop SDL updates before the legacy hooks exist. It becomes visible\n\t\t// after a user explicitly boots with UseNewInput=false.\n\t\tSettings::UseNewInput.hidden(Settings::UseNewInput);\n\t\tSettings::WheelInputCompatibility.needs_restart();\n\t\tSettings::InputBackend.needs_restart();''')

replace_once(
    wheel_ui,
    '''        std::string_view description() override { return "Universal DirectInput Wheel Setup"; }\n        // Install with the legacy stack; active() gates live F11 ownership.\n        bool validate() override { return Settings::WheelInputCompatibility && !Settings::UseNewInput; }\n        bool apply() override''',
    '''        std::string_view description() override { return "Universal DirectInput Wheel Setup"; }\n        // The dedicated Legacy Wheel Setup page owns every WheelUniversal*\n        // setting. Keeping the raw axis/button numbers in generic Controls\n        // created a second, competing setup UI. Pedal invert is also exposed on\n        // the dedicated axis rows, so hide those duplicate controls as well.\n        void declare_settings() override\n        {\n            constexpr std::string_view prefix = "WheelUniversal";\n            for (auto* setting : Settings::SettingBase::registry())\n            {\n                if (!setting || setting->section() != "Controls")\n                    continue;\n                const std::string_view key = setting->key();\n                if (key.size() >= prefix.size() && key.substr(0, prefix.size()) == prefix)\n                    setting->hidden(true);\n            }\n            Settings::WheelAccelerationInvert.hidden(true);\n            Settings::WheelBrakeInvert.hidden(true);\n        }\n\n        // Install with the legacy stack; active() gates live F11 ownership.\n        bool validate() override { return Settings::WheelInputCompatibility && !Settings::UseNewInput; }\n        bool apply() override''')

replace_once(
    hooks_input,
    '''        Settings::WheelMenuDirectionFilter.needs_restart();''',
    '''        Settings::WheelMenuDirectionFilter.needs_restart();\n        Settings::WheelMenuDirectionFilter.hidden(Settings::UseNewInput);''')

replace_once(
    compat_v2,
    '''            Settings::WheelPedalSplitFix.needs_restart();\n            Settings::WheelMenuBackAlias.needs_restart();''',
    '''            Settings::WheelPedalSplitFix.needs_restart();\n            Settings::WheelMenuBackAlias.needs_restart();\n            Settings::WheelPedalSplitFix.hidden(Settings::UseNewInput);\n            Settings::WheelPedalSplitThreshold.hidden(Settings::UseNewInput);\n            Settings::WheelMenuBackAlias.hidden(Settings::UseNewInput);''')

replace_once(
    r3_dpad,
    '''            Settings::WheelMenuR3LeftButton.needs_restart();''',
    '''            Settings::WheelMenuR3LeftButton.needs_restart();\n\n            Settings::WheelMenuR3DirectDPad.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3DeviceName.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3UpButton.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3RightButton.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3DownButton.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3LeftButton.hidden(Settings::UseNewInput);''')

replace_once(
    r3_ab,
    '''            Settings::WheelMenuR3BButton.needs_restart();''',
    '''            Settings::WheelMenuR3BButton.needs_restart();\n            Settings::WheelMenuR3DirectAB.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3AButton.hidden(Settings::UseNewInput);\n            Settings::WheelMenuR3BButton.hidden(Settings::UseNewInput);''')

verify()
commit(
    "ux: separate modern and legacy setup surfaces [skip ci]",
    input_cpp, wheel_ui, hooks_input, compat_v2, r3_dpad, r3_ab)

# Review findings 10-12: make Input Bindings discoverable even while searching
# Settings, and tell a first-run wheel user which of the two setup surfaces owns
# input vs force feedback.
replace_once(
    settings_ui,
    '''\t\tif (matches_search(section, search))\n\t\t\treturn true;\n\n\t\tfor (const Settings::SettingBase* setting : Settings::SettingBase::registry())''',
    '''\t\tif (matches_search(section, search))\n\t\t\treturn true;\n\n\t\tif (section == "Controls" &&\n\t\t\t(matches_search("Input Bindings", search) ||\n\t\t\t matches_search("Configure Input Bindings", search)))\n\t\t\treturn true;\n\n\t\tfor (const Settings::SettingBase* setting : Settings::SettingBase::registry())''')

replace_once(
    settings_ui,
    '''\t\t\tif (section == "Controls" && search.empty())\n\t\t\t\tif (ImGui::Button("Configure Input Bindings"))\n\t\t\t\t\tOverlay::IsBindingDialogActive = true;''',
    '''\t\t\tconst bool inputSetupSearch = search.empty() ||\n\t\t\t\tmatches_search("Input Bindings", search) ||\n\t\t\t\tmatches_search("Configure Input Bindings", search);\n\t\t\tif (section == "Controls" && inputSetupSearch)\n\t\t\t\tif (ImGui::Button("Configure Input Bindings"))\n\t\t\t\t\tOverlay::IsBindingDialogActive = true;''')

replace_once(
    overlay_cpp,
    '''\tImGui::Bullet();\n\tImGui::TextUnformatted("Controller vibration is supported, but disabled by default as some Bluetooth controllers can have framerate issues. (configure it in Controls settings)");\n\n\tImGui::Bullet();\n\tImGui::TextUnformatted("Online play and leaderboards are back! Create an account from the game's menus to "''',
    '''\tImGui::Bullet();\n\tImGui::TextUnformatted("Controller vibration is supported, but disabled by default as some Bluetooth controllers can have framerate issues. (configure it in Controls settings)");\n\n\tImGui::Bullet();\n\tImGui::TextWrapped("Wheel users: configure steering, pedals, buttons and menu controls in Input Bindings (Controller Configuration or Settings > Controls). Force feedback is selected and tuned separately in the Force Feedback tab.");\n\n\tImGui::Bullet();\n\tImGui::TextUnformatted("Online play and leaderboards are back! Create an account from the game's menus to "''')

verify()
commit("ux: improve first-run wheel setup discovery [skip ci]", settings_ui, overlay_cpp)

# Review findings 13-17: FFB changes are live but were easy to leave unsaved,
# and several auto-save paths claimed success without checking Settings::write.
# Track only persistence state here; do not alter any force-model constants.
replace_once(
    wheel_ui,
    '''        bool baselineValid_ = false;\n        std::string status_;\n\n        void save()''',
    '''        bool baselineValid_ = false;\n        std::string status_;\n        bool ffbDirty_ = false;\n\n        void save()''')

replace_once(
    wheel_ui,
    '''        void save()\n        {\n            UniversalWheelProfile::apply_now();\n            Settings::write(Module::UserIniPath);\n            status_ = "Saved to OutRun2006Tweaks.user.ini";\n        }''',
    '''        void save()\n        {\n            UniversalWheelProfile::apply_now();\n            if (Settings::write(Module::UserIniPath))\n            {\n                ffbDirty_ = false;\n                status_ = "Saved to OutRun2006Tweaks.user.ini";\n            }\n            else\n                status_ = "Could not save OutRun2006Tweaks.user.ini.";\n        }''')

replace_once(
    wheel_ui,
    '''                Settings::WheelFFBDeviceName = info.name;\n                Settings::WheelFFBDeviceGuid = info.guidKey;\n                Settings::write(Module::UserIniPath);\n                status_ = "Selected FFB output and saved its exact DirectInput GUID. The FFB engine will reinitialize automatically on the next gameplay update.";\n                return;''',
    '''                Settings::WheelFFBDeviceName = info.name;\n                Settings::WheelFFBDeviceGuid = info.guidKey;\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = "Selected FFB output and saved its exact DirectInput GUID. The FFB engine will reinitialize automatically on the next gameplay update.";\n                }\n                else\n                {\n                    ffbDirty_ = true;\n                    status_ = "Selected FFB output for this session, but could not save user.ini.";\n                }\n                return;''')

replace_once(
    wheel_ui,
    '''            Settings::WheelUniversalDeviceName = info.name;\n            Settings::WheelUniversalDeviceGuid = info.guidKey;\n            gReader.select_by_identity(info.guidKey, info.name);\n            Settings::write(Module::UserIniPath);\n            status_ = UniversalWheelProfile::regular_device_count() > 1\n                ? "Selected legacy input device. Confirm the OutRun legacy input slot below when multiple controllers are present."\n                : "Selected legacy input device. FFB output is configured separately below.";''',
    '''            Settings::WheelUniversalDeviceName = info.name;\n            Settings::WheelUniversalDeviceGuid = info.guidKey;\n            gReader.select_by_identity(info.guidKey, info.name);\n            const bool saved = Settings::write(Module::UserIniPath);\n            status_ = !saved\n                ? "Selected legacy input device for this session, but could not save user.ini."\n                : (UniversalWheelProfile::regular_device_count() > 1\n                    ? "Selected legacy input device. Confirm the OutRun legacy input slot below when multiple controllers are present."\n                    : "Selected legacy input device. FFB output is configured separately below.");''')

replace_once(
    wheel_ui,
    '''        void render(bool) override\n        {\n            listen_for_binding();''',
    '''        void render(bool) override\n        {\n            listen_for_binding();\n            const auto track_ffb_change = [this](bool changed)\n            {\n                if (changed)\n                    ffbDirty_ = true;\n                return changed;\n            };''')

# Track all user-editable FFB controls. Tooltips still see the wrapped ImGui item
# as the last item, so wrapping does not change hover behaviour.
for old, new in [
    ('ImGui::Checkbox("Enable Force Feedback", Settings::WheelFFBEnable.ptr());',
     'track_ffb_change(ImGui::Checkbox("Enable Force Feedback", Settings::WheelFFBEnable.ptr()));'),
    ('ImGui::SliderFloat("Overall Strength", Settings::WheelFFBGlobalStrength.ptr(), 0.0f, 1.5f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Overall Strength", Settings::WheelFFBGlobalStrength.ptr(), 0.0f, 1.5f, "%.2f"));'),
    ('ImGui::SliderFloat("Centering Spring (low speed)", Settings::WheelFFBSpringStrength.ptr(), 0.0f, 1.0f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Centering Spring (low speed)", Settings::WheelFFBSpringStrength.ptr(), 0.0f, 1.0f, "%.2f"));'),
    ('ImGui::SliderFloat("Dynamic Damping", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 0.80f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Dynamic Damping", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 0.80f, "%.2f"));'),
    ('ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f"));'),
    ('ImGui::Checkbox("Physics SAT (body slip + yaw)", Settings::WheelFFBPhysicsSat.ptr())',
     'track_ffb_change(ImGui::Checkbox("Physics SAT (body slip + yaw)", Settings::WheelFFBPhysicsSat.ptr()))'),
    ('ImGui::SliderFloat("Grip-loss Response", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Grip-loss Response", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f"));'),
    ('ImGui::SliderFloat("Road Detail", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Road Detail", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, "%.2f"));'),
    ('ImGui::SliderFloat("Tire Slip", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Tire Slip", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, "%.2f"));'),
    ('ImGui::SliderFloat("Collision", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Collision", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, "%.2f"));'),
    ('ImGui::Checkbox("Hardware GUID_Spring", Settings::WheelFFBUseHardwareSpring.ptr());',
     'track_ffb_change(ImGui::Checkbox("Hardware GUID_Spring", Settings::WheelFFBUseHardwareSpring.ptr()));'),
    ('ImGui::Checkbox("Hardware GUID_Damper", Settings::WheelFFBUseHardwareDamper.ptr());',
     'track_ffb_change(ImGui::Checkbox("Hardware GUID_Damper", Settings::WheelFFBUseHardwareDamper.ptr()));'),
    ('ImGui::Checkbox("Hardware road/slip sine effects", Settings::WheelFFBUsePeriodicEffects.ptr());',
     'track_ffb_change(ImGui::Checkbox("Hardware road/slip sine effects", Settings::WheelFFBUsePeriodicEffects.ptr()));'),
    ('ImGui::SliderFloat("Spring Saturation", Settings::WheelFFBSpringSaturation.ptr(), 0.10f, 1.0f, "%.3f");',
     'track_ffb_change(ImGui::SliderFloat("Spring Saturation", Settings::WheelFFBSpringSaturation.ptr(), 0.10f, 1.0f, "%.3f"));'),
    ('ImGui::SliderFloat("Weight Transfer", Settings::WheelFFBWeightTransfer.ptr(), 0.0f, 1.5f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Weight Transfer", Settings::WheelFFBWeightTransfer.ptr(), 0.0f, 1.5f, "%.2f"));'),
    ('ImGui::SliderFloat("Lateral Signal Deadzone", Settings::WheelFFBLateralDeadzone.ptr(), 0.0f, 8.0f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Lateral Signal Deadzone", Settings::WheelFFBLateralDeadzone.ptr(), 0.0f, 8.0f, "%.2f"));'),
    ('ImGui::SliderFloat("Gear Shift", Settings::WheelFFBGearShift.ptr(), 0.0f, 1.0f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Gear Shift", Settings::WheelFFBGearShift.ptr(), 0.0f, 1.0f, "%.2f"));'),
    ('ImGui::SliderFloat("Engine Idle", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.50f, "%.2f");',
     'track_ffb_change(ImGui::SliderFloat("Engine Idle", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.50f, "%.2f"));'),
    ('ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f");',
     'track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));'),
    ('ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());',
     'track_ffb_change(ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr()));'),
    ('ImGui::Checkbox("Record driving telemetry (10 Hz)", Settings::WheelFFBTelemetry.ptr());',
     'track_ffb_change(ImGui::Checkbox("Record driving telemetry (10 Hz)", Settings::WheelFFBTelemetry.ptr()));'),
    ('ImGui::Checkbox("Reverse SAT / ConstantForce", Settings::WheelFFBInvertForce.ptr());',
     'track_ffb_change(ImGui::Checkbox("Reverse SAT / ConstantForce", Settings::WheelFFBInvertForce.ptr()));'),
    ('ImGui::Checkbox("Reverse Spring", Settings::WheelFFBInvertSpring.ptr());',
     'track_ffb_change(ImGui::Checkbox("Reverse Spring", Settings::WheelFFBInvertSpring.ptr()));'),
]:
    replace_once(wheel_ui, old, new)

replace_once(
    wheel_ui,
    '''            if (ImGui::Button("Save Force Feedback"))\n                status_ = Settings::write(Module::UserIniPath)\n                    ? "Force feedback settings saved." : "Could not save force feedback settings.";''',
    '''            if (ffbDirty_)\n                ImGui::TextDisabled("Unsaved FFB changes are active now but will be lost after restart.");\n            if (ImGui::Button(ffbDirty_ ? "Save Force Feedback*" : "Save Force Feedback"))\n            {\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = "Force feedback settings saved.";\n                }\n                else\n                    status_ = "Could not save force feedback settings.";\n            }''')

replace_once(
    wheel_ui,
    '''                Settings::VibrationMode = 0;\n                Settings::write(Module::UserIniPath);\n                status_ = "Loaded MOZA R3 Physics SAT: lateral load, body slide and front scrub are separated; diagnostic logging enabled. Saved to user.ini.";''',
    '''                Settings::VibrationMode = 0;\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = "Loaded MOZA R3 Physics SAT: lateral load, body slide and front scrub are separated; diagnostic logging enabled. Saved to user.ini.";\n                }\n                else\n                {\n                    ffbDirty_ = true;\n                    status_ = "Loaded MOZA R3 Physics SAT for this session, but could not save user.ini.";\n                }''')

replace_once(
    wheel_ui,
    '''                Settings::VibrationMode = 0;\n                Settings::write(Module::UserIniPath);\n                status_ = "Loaded MOZA R3 Natural SAT: smooth progressive SAT, low-speed-only spring assist and single DirectInput COM wheel FFB. Saved to user.ini.";''',
    '''                Settings::VibrationMode = 0;\n                if (Settings::write(Module::UserIniPath))\n                {\n                    ffbDirty_ = false;\n                    status_ = "Loaded MOZA R3 Natural SAT: smooth progressive SAT, low-speed-only spring assist and single DirectInput COM wheel FFB. Saved to user.ini.";\n                }\n                else\n                {\n                    ffbDirty_ = true;\n                    status_ = "Loaded MOZA R3 Natural SAT for this session, but could not save user.ini.";\n                }''')

verify()
commit("ux: make FFB persistence state explicit [skip ci]", wheel_ui)

# Review findings 18-20: release-facing text still described a deleted preset and
# old tuning values. Keep it aligned with the current UI and current setup flow.
write(release_notes, r'''# OutRun2006Tweaks Wheel FFB v0.1

## 한국어

이 빌드는 **OutRun 2006: Coast 2 Coast를 현대 레이싱 휠로 플레이하기 위한 실험적 wheel-ffb 포크**입니다. 현재 제가 직접 실기 확인한 장비는 **MOZA R3**이며, 다른 DirectInput 휠은 구조상 동작할 수 있지만 미검증입니다.

### 주요 기능

- SDL3 raw joystick 기반 멀티 디바이스 입력: 휠 / 별도 페달 / 쉬프터 / 버튼박스 / 게임패드 동시 바인딩
- 게임 내 **Input Bindings Quick Setup**과 Steering / Accelerator / Brake Min-Rest-Max 보정
- Quick Setup의 Start / Confirm / Back / Menu Up-Right-Down-Left 설정, 필요 없는 단계 Skip, 완료 후 `Keep & Fine-tune`
- Windows DirectInput COM 네이티브 FFB
- Physics SAT + Natural SAT fallback, 저속 센터링 Spring, Dynamic Damping, 그립 손실 언로드, 노면/타이어/기어/충돌 효과
- 정확한 FFB GUID 선택, 포커스 상실/장치 손실/watchdog 안전 처리
- 게임 플레이 중에만 동작하는 고정 20% 좌/우 방향 테스트

### MOZA R3 권장 시작점

F11 **Force Feedback**에는 두 프리셋이 있습니다.

| Setting | Physics SAT | Natural SAT |
| --- | ---: | ---: |
| Overall Strength | 0.70 | 0.70 |
| Centering Spring | 0.65 | 0.65 |
| Spring Saturation | 0.95 | 0.95 |
| Dynamic Damping | 0.28 | 0.30 |
| Self-aligning Torque | 1.45 | 1.75 |
| Grip-loss Response | 0.65 | 0.65 |
| Weight Transfer | 0.15 | 0.20 |
| Force Slew Rate | 0.040 | 0.045 |
| Road Detail | 0.30 | 0.30 |
| Tire Slip | 0.20 | 0.20 |
| Collision | 0.38 | 0.38 |
| Hardware Spring / Damper / sine | ON | ON |
| Reverse SAT / ConstantForce | ON | ON |
| Reverse Spring | OFF | OFF |

`Load MOZA R3 Physics SAT`는 차량 이동/방향으로 front slip을 추정하고, 유효한 Physics 샘플이 없을 때는 Natural SAT로 폴백합니다. `Load MOZA R3 Natural SAT`는 조향각 기반의 보다 단순한 비교 경로입니다. 방향은 드라이버/장치에 따라 달라질 수 있으므로 20% 방향 테스트 결과를 우선하세요.

### 초기 설정

1. 휠/페달을 연결하고 게임을 실행합니다.
2. 게임의 Controller Configuration 또는 **F11 → Force Feedback → Open Input Bindings**를 엽니다.
3. Quick Setup으로 Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left를 설정합니다. 없는 기능은 `Skip this step`을 사용합니다.
4. 완료 화면에서 조향/페달 값을 확인합니다. 범위가 맞지 않으면 `Keep & Fine-tune` 후 해당 JoyAxis의 **Calibrate**에서 Min / Rest / Max를 잡습니다.
5. `Save bindings` 또는 `Save & Return to game`으로 입력을 저장합니다.
6. Force Feedback에서 실제 FFB 출력 장치를 선택하고 Physics SAT 또는 Natural SAT 프리셋을 시작점으로 사용합니다.
7. FFB 수동 변경은 즉시 적용되며 `Save Force Feedback`으로 저장합니다. 별표(*)가 있으면 아직 저장되지 않은 변경이 있다는 뜻입니다.

> Direct Drive 휠은 큰 토크를 낼 수 있습니다. 처음에는 휠 베이스의 최대 토크를 보수적으로 설정하고 안전 방향 테스트부터 확인하세요.

### 테스트 범위

- 직접 테스트: MOZA R3
- 개인 테스트 조향 범위: 270°
- 입력: SDL3 raw joystick multi-device
- FFB: Windows DirectInput COM
- Windows Win32 x86

문제 제보 시 `OutRun2006Tweaks.log`, 휠/페달/쉬프터 모델과 드라이버/펌웨어 정보를 함께 남겨 주세요.

---

## English

This is an experimental **wheel-ffb fork for modern driving hardware in OutRun 2006: Coast 2 Coast**. My personally hardware-tested setup is a **MOZA R3**; other DirectInput wheels may work but remain unverified by me.

### Highlights

- SDL3 raw-joystick multi-device input for wheel / separate pedals / shifter / button box / gamepad
- In-game **Input Bindings Quick Setup** plus Steering / Accelerator / Brake Min-Rest-Max calibration
- Start / Confirm / Back / Menu Up-Right-Down-Left steps, optional-step Skip, and `Keep & Fine-tune`
- Native Windows DirectInput COM force feedback
- Physics SAT with full Natural SAT fallback, low-speed centering spring, Dynamic Damping, grip-loss unloading, road/tyre/gear/collision effects
- Exact FFB GUID selection plus focus-loss, device-loss and watchdog safety
- Fixed 20% left/right direction tests gated to active gameplay

### Recommended MOZA R3 starting points

The F11 **Force Feedback** page provides two presets:

| Setting | Physics SAT | Natural SAT |
| --- | ---: | ---: |
| Overall Strength | 0.70 | 0.70 |
| Centering Spring | 0.65 | 0.65 |
| Spring Saturation | 0.95 | 0.95 |
| Dynamic Damping | 0.28 | 0.30 |
| Self-aligning Torque | 1.45 | 1.75 |
| Grip-loss Response | 0.65 | 0.65 |
| Weight Transfer | 0.15 | 0.20 |
| Force Slew Rate | 0.040 | 0.045 |
| Road Detail | 0.30 | 0.30 |
| Tire Slip | 0.20 | 0.20 |
| Collision | 0.38 | 0.38 |
| Hardware Spring / Damper / sine | ON | ON |
| Reverse SAT / ConstantForce | ON | ON |
| Reverse Spring | OFF | OFF |

`Load MOZA R3 Physics SAT` estimates front slip from current vehicle motion/heading and falls back to Natural SAT whenever a valid physics sample is unavailable. `Load MOZA R3 Natural SAT` is the simpler steering-angle-based comparison path. Driver direction can vary, so the safe 20% direction test takes precedence over preset assumptions.

### Initial setup

1. Connect/power the wheel and pedals, then launch the game.
2. Open the game's Controller Configuration or **F11 → Force Feedback → Open Input Bindings**.
3. Run Quick Setup: Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left. Use `Skip this step` for controls the wheel does not have.
4. Verify the live steering/pedal bars. If a range is wrong, choose `Keep & Fine-tune` and use **Calibrate** on the JoyAxis to set Min / Rest / Max.
5. Persist input with `Save bindings` or `Save & Return to game`.
6. Under Force Feedback, select the actual FFB output and start from the Physics SAT or Natural SAT preset.
7. Manual FFB changes apply live; use `Save Force Feedback` to persist them. An asterisk (*) means changes are still unsaved.

> Direct-drive wheels can generate substantial torque. Start with a conservative wheel-base torque limit and verify the safe direction tests first.

### Tested scope

- Personally tested: MOZA R3
- Steering range used in my setup: 270°
- Input: SDL3 raw-joystick multi-device
- FFB: Windows DirectInput COM
- Windows Win32 x86

For compatibility reports, include `OutRun2006Tweaks.log`, wheel/pedal/shifter models, and driver/firmware versions.

### Credits / license

This work builds on public source, design and testing from **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB**, and community hardware reports. The upstream MIT license and notices are retained; see `LICENSE.md` and `THIRD_PARTY_NOTICES.md`.
''')

write(discord_share, r'''# Discord share text — v0.1

## English

I made an experimental **OutRun2006Tweaks Wheel FFB v0.1** build mainly around my **MOZA R3** setup. The only wheel I have personally hardware-tested is the R3, so other DirectInput wheels are still unverified on my side.

It adds SDL3 multi-device input, an in-game Quick Setup/calibration flow, and native DirectInput COM FFB without vJoy or an external mapper. Current F11 FFB presets are **MOZA R3 Physics SAT** and **MOZA R3 Natural SAT**. The Physics starting point uses Overall 0.70, Spring 0.65, Dynamic Damping 0.28 and SAT 1.45; Natural SAT uses Damping 0.30 and SAT 1.75. Both keep Collision at 0.38.

Quick Setup now covers steering, pedals, paddles, Start/Confirm/Back and all four menu directions, with Skip and fine-tune/calibration paths. FFB changes apply live and the UI marks unsaved tuning until `Save Force Feedback` is used.

Credits/thanks to **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB**, and everyone who shared wheel-testing information. The upstream license/notices are retained in the fork.

Release / install details:
https://github.com/thp32tt/OutRun2006Tweaks/releases/tag/v0.1

If anyone tries another wheel, compatibility feedback plus `OutRun2006Tweaks.log` would be very useful.

## 한국어

개인적으로 **MOZA R3로 OutRun 2006을 하려고 만든 OutRun2006Tweaks Wheel FFB v0.1**을 공유합니다. 제가 직접 실기 테스트한 휠은 R3 하나뿐이라 다른 DirectInput 휠은 아직 미검증입니다.

SDL3 멀티 디바이스 입력, 게임 내 Quick Setup/축 보정, 별도 vJoy 없이 DirectInput COM 방식의 네이티브 FFB를 넣었습니다. 현재 F11 프리셋은 **MOZA R3 Physics SAT**와 **MOZA R3 Natural SAT** 두 가지입니다. Physics 시작값은 Overall 0.70, Spring 0.65, Dynamic Damping 0.28, SAT 1.45이고 Natural SAT는 Damping 0.30, SAT 1.75를 사용합니다. Collision은 둘 다 0.38입니다.

Quick Setup은 조향/페달/패들/Start/Confirm/Back/메뉴 4방향을 설정하며 Skip과 세부 보정 경로가 있습니다. FFB 변경은 즉시 적용되고 `Save Force Feedback` 전에는 UI에 미저장 상태가 표시됩니다.

원본 **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB** 및 테스트 정보를 공유해 주신 커뮤니티 분들께 감사합니다. 원본 라이선스/고지는 포크에 유지했습니다.

릴리스/설치 방법:
https://github.com/thp32tt/OutRun2006Tweaks/releases/tag/v0.1

다른 휠에서 테스트해 보신 분이 있다면 `OutRun2006Tweaks.log`와 함께 결과를 알려주시면 도움이 됩니다.
''')

verify()
commit("docs: align release setup guidance with current source [skip ci]", release_notes, discord_share)

# Review findings 21-30: lock the justified changes into the consolidated
# source verifier so future refactors cannot silently restore the same UX gaps.
replace_once(
    verifier,
    "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')",
    '''req(bind_ui, 'existingDevice->instanceId == candidateDevice->instanceId', 'Quick Setup replaces raw bindings only on the captured physical device')\nforbid(bind_ui, 'if (candidate.isRawDevice()) return existing.isRawDevice();', 'Quick Setup never erases every raw-device binding family')\nreq(bind_ui, 'Discard edits & load?##load', 'loading cannot silently discard unsaved binding edits')\nreq(bind_ui, 'Could not save bindings. Check folder permissions', 'binding save failures are visible in the UI')\nreq(wheel_ui, 'bool ffbDirty_ = false;', 'FFB page tracks unsaved live tuning')\nreq(wheel_ui, 'Save Force Feedback*', 'FFB save button marks unsaved tuning')\nreq(wheel_ui, 'Unsaved FFB changes are active now but will be lost after restart.', 'FFB page explains live versus persisted tuning')\nreq(wheel_ui, 'Loaded MOZA R3 Physics SAT for this session, but could not save user.ini.', 'Physics preset never falsely reports a failed save')\nreq(wheel_ui, 'Loaded MOZA R3 Natural SAT for this session, but could not save user.ini.', 'Natural preset never falsely reports a failed save')\nreq(read('src/input_manager.cpp'), 'Settings::WheelInputCompatibility.needs_restart();', 'legacy compatibility mode is explicitly restart-bound')\nreq(wheel_ui, 'constexpr std::string_view prefix = "WheelUniversal";', 'raw WheelUniversal settings are owned only by dedicated legacy setup')\nreq(read('src/hooks_input.cpp'), 'Settings::WheelMenuDirectionFilter.hidden(Settings::UseNewInput);', 'legacy menu filter is hidden from default modern controls')\nreq(read('src/hooks_wheel_input_compat_v2.hpp'), 'Settings::WheelPedalSplitFix.hidden(Settings::UseNewInput);', 'legacy pedal workaround is hidden from default modern controls')\nreq(read('src/hooks_wheel_r3_menu_dpad.hpp'), 'Settings::WheelMenuR3DirectDPad.hidden(Settings::UseNewInput);', 'R3 legacy D-pad helper is hidden from default modern controls')\nreq(read('src/hooks_wheel_r3_menu_ab.hpp'), 'Settings::WheelMenuR3DirectAB.hidden(Settings::UseNewInput);', 'R3 legacy A/B helper is hidden from default modern controls')\nreq(read('src/overlay/settings_ui.cpp'), 'matches_search("Input Bindings", search)', 'settings search can still surface Input Bindings')\nreq(read('src/overlay/overlay.cpp'), 'Wheel users: configure steering, pedals, buttons and menu controls in Input Bindings', 'first-run overlay explains wheel input ownership')\nrelease_notes = read('RELEASE_NOTES_v0.1.md')\ndiscord_share = read('DISCORD_SHARE_v0.1.md')\nreq(release_notes, 'Load MOZA R3 Physics SAT', 'release notes name the current Physics preset')\nreq(release_notes, 'Save Force Feedback', 'release notes explain FFB persistence')\nforbid(release_notes, 'MOZA R3 v0.1 (default)', 'release notes have no deleted preset button')\nforbid(release_notes, 'Dynamic Damping** | **0.42', 'release notes have no obsolete damping table')\nreq(discord_share, 'Dynamic Damping 0.28', 'Discord share uses the current Physics damping')\nforbid(discord_share, 'Damping 0.42', 'Discord share has no obsolete damping value')\nprint('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')''')

verify()
commit("test: guard 30-pass setup and persistence review [skip ci]", verifier)

print("30-pass source review fixes applied and structurally verified")
