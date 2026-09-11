from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected one match, found {count}: {old[:100]!r}")
    write(rel, text.replace(old, new, 1))


profile_header = r'''#pragma once

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "plugin.hpp"

// Named wheel/input and force-feedback profiles live beside the DLL instead of
// inside OutRun2006Tweaks.user.ini.  The active configuration is still copied
// to the normal INI files when a profile is loaded, so selecting a profile is
// durable across restarts without making startup depend on a profile file.
namespace WheelProfileStore
{
    enum class Kind
    {
        Input,
        ForceFeedback,
    };

    inline std::string lower_ascii(std::string value)
    {
        std::transform(value.begin(), value.end(), value.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return value;
    }

    inline std::string normalize_profile_name(std::string value)
    {
        value = Util::trim(value);
        if (value.size() >= 4 && lower_ascii(value.substr(value.size() - 4)) == ".ini")
            value.resize(value.size() - 4);
        return Util::trim(value);
    }

    inline bool valid_profile_name(std::string_view rawName, std::string* reason = nullptr)
    {
        const std::string name = normalize_profile_name(std::string(rawName));
        auto fail = [&](const char* why)
        {
            if (reason) *reason = why;
            return false;
        };

        if (name.empty())
            return fail("Enter a profile name.");
        if (name.size() > 64)
            return fail("Profile names are limited to 64 characters.");
        if (name == "." || name == "..")
            return fail("That profile name is reserved.");

        // Keep file names portable and block path traversal. ASCII is deliberate:
        // std::filesystem narrow-string conversion is code-page dependent on
        // Windows, so accepting arbitrary UTF-8 here would produce profiles that
        // work on some systems but not others.
        for (const unsigned char c : name)
        {
            if (!(std::isalnum(c) || c == ' ' || c == '-' || c == '_' || c == '.'))
                return fail("Use letters, numbers, spaces, '.', '_' or '-' in profile names.");
        }
        if (name.back() == '.' || name.back() == ' ')
            return fail("Profile names cannot end with a dot or space.");

        const std::string lower = lower_ascii(name.substr(0, name.find('.')));
        static constexpr const char* reserved[] = {
            "con", "prn", "aux", "nul",
            "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
            "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
        };
        for (const char* value : reserved)
            if (lower == value)
                return fail("That profile name is reserved by Windows.");
        return true;
    }

    inline std::filesystem::path directory(Kind kind)
    {
        return Module::DllPath.parent_path() / "OutRun2006Tweaks.profiles" /
            (kind == Kind::Input ? "Input" : "FFB");
    }

    inline bool ensure_directory(Kind kind, std::string* error = nullptr)
    {
        std::error_code ec;
        std::filesystem::create_directories(directory(kind), ec);
        if (ec)
        {
            if (error) *error = "Could not create profile directory: " + ec.message();
            return false;
        }
        return true;
    }

    inline std::optional<std::filesystem::path> profile_path(
        Kind kind, std::string_view rawName, std::string* error = nullptr)
    {
        std::string reason;
        if (!valid_profile_name(rawName, &reason))
        {
            if (error) *error = reason;
            return std::nullopt;
        }
        if (!ensure_directory(kind, error))
            return std::nullopt;
        const std::string name = normalize_profile_name(std::string(rawName));
        return directory(kind) / (name + ".ini");
    }

    inline std::vector<std::string> list_profiles(Kind kind)
    {
        std::vector<std::string> result;
        std::string ignored;
        if (!ensure_directory(kind, &ignored))
            return result;

        std::error_code ec;
        for (std::filesystem::directory_iterator it(directory(kind), ec), end; !ec && it != end; it.increment(ec))
        {
            if (!it->is_regular_file(ec) || ec)
                continue;
            if (lower_ascii(it->path().extension().string()) != ".ini")
                continue;
            result.push_back(it->path().stem().string());
        }
        std::sort(result.begin(), result.end(), [](const std::string& a, const std::string& b)
        {
            return lower_ascii(a) < lower_ascii(b);
        });
        return result;
    }

    inline bool profile_exists(Kind kind, std::string_view rawName)
    {
        std::string ignored;
        auto path = profile_path(kind, rawName, &ignored);
        if (!path)
            return false;
        std::error_code ec;
        return std::filesystem::is_regular_file(*path, ec) && !ec;
    }

    inline bool delete_profile(Kind kind, std::string_view rawName, std::string* error = nullptr)
    {
        auto path = profile_path(kind, rawName, error);
        if (!path)
            return false;
        std::error_code ec;
        const bool removed = std::filesystem::remove(*path, ec);
        if (ec || !removed)
        {
            if (error) *error = ec ? ("Could not delete profile: " + ec.message()) : "Profile file was not found.";
            return false;
        }
        return true;
    }

    inline bool parse_section(
        const std::filesystem::path& path,
        std::string_view wantedSection,
        std::unordered_map<std::string, std::string>& values,
        std::string* error = nullptr)
    {
        std::ifstream file(path);
        if (!file)
        {
            if (error) *error = "Could not open profile file.";
            return false;
        }

        const std::string wanted = lower_ascii(std::string(wantedSection));
        std::string section;
        std::string line;
        while (std::getline(file, line))
        {
            line = Util::trim(line);
            if (line.empty() || line.front() == '#' || line.front() == ';')
                continue;
            if (line.front() == '[' && line.back() == ']')
            {
                section = lower_ascii(Util::trim(line.substr(1, line.size() - 2)));
                continue;
            }
            if (section != wanted)
                continue;
            const size_t equals = line.find('=');
            if (equals == std::string::npos)
                continue;
            const std::string key = lower_ascii(Util::trim(line.substr(0, equals)));
            const std::string value = Util::trim(line.substr(equals + 1));
            values[key] = value;
        }
        return true;
    }

    struct InputOptionsSnapshot
    {
        std::string inputBackend;
        std::string steeringDeadZone;
        std::string bypassSensitivity;
    };

    inline InputOptionsSnapshot capture_input_options()
    {
        return {
            Settings::InputBackend.to_string(),
            Settings::SteeringDeadZone.to_string(),
            Settings::BypassGameSensitivity.to_string(),
        };
    }

    inline void restore_input_options(const InputOptionsSnapshot& snapshot)
    {
        Settings::InputBackend.set_from_string(snapshot.inputBackend);
        Settings::SteeringDeadZone.set_from_string(snapshot.steeringDeadZone);
        Settings::BypassGameSensitivity.set_from_string(snapshot.bypassSensitivity);
    }

    inline bool append_input_options(const std::filesystem::path& path, std::string* error = nullptr)
    {
        std::ofstream file(path, std::ios::out | std::ios::app);
        if (!file)
        {
            if (error) *error = "Could not append wheel-specific input options to the profile.";
            return false;
        }
        file << "\n[WheelInputProfile]\n";
        file << "Version = 1\n";
        file << "InputBackend = " << Settings::InputBackend.to_string() << "\n";
        file << "SteeringDeadZone = " << Settings::SteeringDeadZone.to_string() << "\n";
        file << "BypassGameSensitivity = " << Settings::BypassGameSensitivity.to_string() << "\n";
        if (!file)
        {
            if (error) *error = "Failed while writing wheel-specific input options.";
            return false;
        }
        return true;
    }

    inline bool load_input_options(const std::filesystem::path& path, std::string* error = nullptr)
    {
        std::unordered_map<std::string, std::string> values;
        if (!parse_section(path, "WheelInputProfile", values, error))
            return false;

        const InputOptionsSnapshot before = capture_input_options();
        std::vector<Settings::SettingBase*> changed;
        const auto apply = [&](const char* key, Settings::SettingBase& setting) -> bool
        {
            const auto it = values.find(lower_ascii(key));
            if (it == values.end())
                return true; // Older profiles remain valid.
            const std::string oldValue = setting.to_string();
            if (!setting.set_from_string(it->second))
                return false;
            if (setting.to_string() != oldValue)
                changed.push_back(&setting);
            return true;
        };

        if (!apply("InputBackend", Settings::InputBackend) ||
            !apply("SteeringDeadZone", Settings::SteeringDeadZone) ||
            !apply("BypassGameSensitivity", Settings::BypassGameSensitivity))
        {
            restore_input_options(before);
            if (error) *error = "Input profile contains an invalid wheel-specific option.";
            return false;
        }

        for (Settings::SettingBase* setting : changed)
            setting->notify();
        return true;
    }

    inline bool is_ffb_profile_setting(const Settings::SettingBase* setting)
    {
        if (!setting || setting->section() != "WheelFFB")
            return false;
        const std::string key = std::string(setting->key());
        // Device routing and diagnostics stay global. A feel profile must never
        // silently redirect torque to another wheel or turn verbose logging on.
        return key != "DeviceName" && key != "DeviceGuid" &&
            key != "Telemetry" && key != "DebugLog";
    }

    inline std::vector<Settings::SettingBase*> ffb_settings()
    {
        std::vector<Settings::SettingBase*> result;
        for (Settings::SettingBase* setting : Settings::SettingBase::registry())
            if (is_ffb_profile_setting(setting))
                result.push_back(setting);
        std::sort(result.begin(), result.end(), [](const Settings::SettingBase* a, const Settings::SettingBase* b)
        {
            return a->key() < b->key();
        });
        return result;
    }

    inline bool save_ffb_profile(std::string_view rawName, std::string* error = nullptr)
    {
        auto path = profile_path(Kind::ForceFeedback, rawName, error);
        if (!path)
            return false;

        std::ofstream file(*path, std::ios::out | std::ios::trunc);
        if (!file)
        {
            if (error) *error = "Could not open FFB profile for writing.";
            return false;
        }
        file << "# OutRun2006Tweaks named force-feedback feel profile.\n";
        file << "# DeviceName/DeviceGuid and diagnostic logging are intentionally not stored here.\n\n";
        file << "[Profile]\nType = ForceFeedback\nVersion = 1\n\n";
        file << "[WheelFFB]\n";
        for (const Settings::SettingBase* setting : ffb_settings())
            file << setting->key() << " = " << setting->to_string() << "\n";
        if (!file)
        {
            if (error) *error = "Failed while writing FFB profile.";
            return false;
        }
        return true;
    }

    inline bool load_ffb_profile(
        std::string_view rawName, int* appliedCount = nullptr, std::string* error = nullptr)
    {
        auto path = profile_path(Kind::ForceFeedback, rawName, error);
        if (!path)
            return false;

        std::unordered_map<std::string, std::string> values;
        if (!parse_section(*path, "WheelFFB", values, error))
            return false;

        auto settings = ffb_settings();
        std::vector<std::string> before;
        before.reserve(settings.size());
        for (Settings::SettingBase* setting : settings)
            before.push_back(setting->to_string());

        int applied = 0;
        std::vector<Settings::SettingBase*> changed;
        for (size_t i = 0; i < settings.size(); ++i)
        {
            Settings::SettingBase* setting = settings[i];
            const auto it = values.find(lower_ascii(std::string(setting->key())));
            if (it == values.end())
                continue; // Forward/backward-compatible partial profile.
            if (!setting->set_from_string(it->second))
            {
                for (size_t restore = 0; restore < settings.size(); ++restore)
                    settings[restore]->set_from_string(before[restore]);
                if (error) *error = "FFB profile contains an invalid value for " + std::string(setting->key()) + ".";
                return false;
            }
            if (setting->to_string() != before[i])
                changed.push_back(setting);
            ++applied;
        }

        if (applied == 0)
        {
            if (error) *error = "FFB profile contains no recognized force settings.";
            return false;
        }

        for (Settings::SettingBase* setting : changed)
            setting->notify();
        if (appliedCount) *appliedCount = applied;
        return true;
    }
}
'''
write("src/wheel_profile_store.hpp", profile_header)

# Input profiles: one named file can keep the complete multi-device binding set
# plus the few modern-input options that are meaningfully wheel-specific.
replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '#include "input_manager.hpp"\n',
    '#include "input_manager.hpp"\n#include "wheel_profile_store.hpp"\n')

replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\tbool confirmingLoad = false;\n\tstd::string persistenceStatus;\n\tbool calibrationOpen = false;''',
    '''\tbool confirmingLoad = false;\n\tstd::string persistenceStatus;\n\tstd::vector<std::string> wheelProfiles;\n\tint selectedWheelProfile = -1;\n\tchar wheelProfileName[65]{};\n\tbool wheelProfilesLoaded = false;\n\tbool confirmingProfileLoad = false;\n\tbool confirmingProfileDelete = false;\n\tbool confirmingProfileOverwrite = false;\n\tbool calibrationOpen = false;''')

input_profile_methods = r'''
	void refresh_wheel_profiles(const std::string& selectName = {})
	{
		wheelProfiles = WheelProfileStore::list_profiles(WheelProfileStore::Kind::Input);
		selectedWheelProfile = -1;
		const std::string wanted = WheelProfileStore::normalize_profile_name(selectName);
		if (!wanted.empty())
		{
			for (size_t i = 0; i < wheelProfiles.size(); ++i)
				if (WheelProfileStore::lower_ascii(wheelProfiles[i]) == WheelProfileStore::lower_ascii(wanted))
				{
					selectedWheelProfile = int(i);
					break;
				}
		}
		if (selectedWheelProfile >= 0)
			strncpy_s(wheelProfileName, wheelProfiles[selectedWheelProfile].c_str(), sizeof(wheelProfileName) - 1);
		wheelProfilesLoaded = true;
	}

	const std::string* selected_wheel_profile() const
	{
		return selectedWheelProfile >= 0 && selectedWheelProfile < int(wheelProfiles.size())
			? &wheelProfiles[selectedWheelProfile] : nullptr;
	}

	void draw_profiles()
	{
		auto& manager = InputManager::instance;
		if (!wheelProfilesLoaded)
			refresh_wheel_profiles();

		ImGui::TextWrapped(
			"Named wheel profiles store the complete multi-device binding set, so a wheel can stay paired with its pedals, shifter and button box. Steering deadzone, sensitivity bypass and input backend are stored with the profile too.");
		ImGui::TextDisabled("Loading a profile also updates OutRun2006Tweaks.input.ini, so it remains active after restart.");
		ImGui::Spacing();

		const std::string* selectedProfile = selected_wheel_profile();
		const char* preview = selectedProfile ? selectedProfile->c_str() : "Select a saved wheel profile";
		if (ImGui::BeginCombo("Saved wheel profile", preview))
		{
			for (size_t i = 0; i < wheelProfiles.size(); ++i)
			{
				const bool selectedNow = int(i) == selectedWheelProfile;
				if (ImGui::Selectable(wheelProfiles[i].c_str(), selectedNow))
				{
					selectedWheelProfile = int(i);
					strncpy_s(wheelProfileName, wheelProfiles[i].c_str(), sizeof(wheelProfileName) - 1);
					confirmingProfileLoad = false;
					confirmingProfileDelete = false;
					confirmingProfileOverwrite = false;
				}
				if (selectedNow)
					ImGui::SetItemDefaultFocus();
			}
			ImGui::EndCombo();
		}

		if (ImGui::InputText("Profile name", wheelProfileName, sizeof(wheelProfileName)))
			confirmingProfileOverwrite = false;
		if (ImGui::IsItemHovered())
			ImGui::SetTooltip("Letters, numbers, spaces, '.', '_' and '-' are supported. '.ini' is optional.");

		const std::string requestedName = WheelProfileStore::normalize_profile_name(wheelProfileName);
		const bool profileAlreadyExists =
			!requestedName.empty() && WheelProfileStore::profile_exists(WheelProfileStore::Kind::Input, requestedName);
		const char* saveLabel = confirmingProfileOverwrite
			? "Confirm overwrite##inputProfileSave"
			: (profileAlreadyExists ? "Overwrite profile##inputProfileSave" : "Save as profile##inputProfileSave");
		if (ImGui::Button(saveLabel))
		{
			std::string error;
			if (profileAlreadyExists && !confirmingProfileOverwrite)
			{
				confirmingProfileOverwrite = true;
				persistenceStatus = "Click Confirm overwrite to replace the existing wheel profile.";
			}
			else if (auto profilePath = WheelProfileStore::profile_path(
				WheelProfileStore::Kind::Input, requestedName, &error))
			{
				if (!manager.saveBindingIni(*profilePath))
				{
					persistenceStatus = "Could not save wheel profile bindings.";
				}
				else if (!WheelProfileStore::append_input_options(*profilePath, &error))
				{
					std::error_code ignored;
					std::filesystem::remove(*profilePath, ignored);
					persistenceStatus = error;
				}
				else
				{
					const bool currentSaved = manager.saveBindingIni(Module::BindingsIniPath);
					const bool optionsSaved = Settings::write(Module::UserIniPath);
					unsavedChanges = !currentSaved;
					persistenceStatus = currentSaved && optionsSaved
						? "Wheel profile saved and made current: " + requestedName
						: "Wheel profile saved, but part of the current configuration could not be persisted.";
					confirmingProfileOverwrite = false;
					refresh_wheel_profiles(requestedName);
				}
			}
			else
				persistenceStatus = error;
		}

		ImGui::SameLine();
		const bool canLoadProfile = selected_wheel_profile() != nullptr;
		if (!canLoadProfile) ImGui::BeginDisabled();
		const char* loadLabel = unsavedChanges && confirmingProfileLoad
			? "Discard edits & load profile?##inputProfileLoad" : "Load selected##inputProfileLoad";
		if (ImGui::Button(loadLabel))
		{
			if (unsavedChanges && !confirmingProfileLoad)
			{
				confirmingProfileLoad = true;
				persistenceStatus = "Click again to discard unsaved binding edits and load the selected wheel profile.";
			}
			else if (const std::string* selected = selected_wheel_profile())
			{
				std::string error;
				auto profilePath = WheelProfileStore::profile_path(WheelProfileStore::Kind::Input, *selected, &error);
				const auto optionBackup = WheelProfileStore::capture_input_options();
				if (!profilePath || !WheelProfileStore::load_input_options(*profilePath, &error))
				{
					persistenceStatus = error.empty() ? "Could not load wheel profile options." : error;
				}
				else if (!manager.readBindingIni(*profilePath))
				{
					WheelProfileStore::restore_input_options(optionBackup);
					persistenceStatus = "Could not load wheel profile bindings; current bindings were preserved.";
				}
				else
				{
					const bool currentSaved = manager.saveBindingIni(Module::BindingsIniPath);
					const bool optionsSaved = Settings::write(Module::UserIniPath);
					unsavedChanges = !currentSaved;
					persistenceStatus = currentSaved && optionsSaved
						? "Wheel profile loaded and made current: " + *selected
						: "Wheel profile is active now, but part of it could not be persisted for restart.";
					if (Settings::InputBackend.changed_since_startup())
						persistenceStatus += " Restart the game to apply its input backend.";
				}
				confirmingProfileLoad = false;
			}
		}
		if (!canLoadProfile) ImGui::EndDisabled();

		ImGui::SameLine();
		if (!canLoadProfile) ImGui::BeginDisabled();
		const char* deleteLabel = confirmingProfileDelete
			? "Confirm delete##inputProfileDelete" : "Delete selected##inputProfileDelete";
		if (ImGui::Button(deleteLabel))
		{
			if (!confirmingProfileDelete)
			{
				confirmingProfileDelete = true;
				persistenceStatus = "Click Confirm delete to remove the selected profile file. Current bindings will not change.";
			}
			else if (const std::string* selected = selected_wheel_profile())
			{
				std::string error;
				if (WheelProfileStore::delete_profile(WheelProfileStore::Kind::Input, *selected, &error))
				{
					persistenceStatus = "Deleted wheel profile: " + *selected;
					wheelProfileName[0] = '\0';
					refresh_wheel_profiles();
				}
				else
					persistenceStatus = error;
				confirmingProfileDelete = false;
			}
		}
		if (!canLoadProfile) ImGui::EndDisabled();

		ImGui::SameLine();
		if (ImGui::Button("Refresh profile list"))
			refresh_wheel_profiles(selected_wheel_profile() ? *selected_wheel_profile() : std::string{});

		ImGui::Spacing();
		ImGui::TextDisabled("Profile folder: OutRun2006Tweaks.profiles\\Input");
	}
'''

replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\tvoid draw_options()\n\t{''',
    input_profile_methods + '''\n\tvoid draw_options()\n\t{''')

replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\t\t\t\tif (ImGui::BeginTabItem("Controllers"))\n\t\t\t\t{\n\t\t\t\t\tdraw_controllers();\n\t\t\t\t\tImGui::EndTabItem();\n\t\t\t\t}\n\n\n\t\t\t\tif (ImGui::BeginTabItem("Options"))''',
    '''\t\t\t\tif (ImGui::BeginTabItem("Controllers"))\n\t\t\t\t{\n\t\t\t\t\tdraw_controllers();\n\t\t\t\t\tImGui::EndTabItem();\n\t\t\t\t}\n\n\t\t\t\tif (ImGui::BeginTabItem("Profiles"))\n\t\t\t\t{\n\t\t\t\t\tdraw_profiles();\n\t\t\t\t\tImGui::EndTabItem();\n\t\t\t\t}\n\n\t\t\t\tif (ImGui::BeginTabItem("Options"))''')

replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\t\t\tconfirmingReset = false;\n\t\t}\n\t}\n''',
    '''\t\t\tconfirmingReset = false;\n\t\t\tconfirmingProfileLoad = false;\n\t\t\tconfirmingProfileDelete = false;\n\t\t\tconfirmingProfileOverwrite = false;\n\t\t}\n\t}\n''')

# FFB profile switching: soft-reset the live force pipeline so changing a whole
# set of gains/directions can never produce a one-frame DD-wheel step.
replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''        void service_safety()\n        {''',
    '''        void settings_transition()\n        {\n            manualTestFrames_ = 0;\n            if (initialized_ && device_ && deviceAcquired_ && !panicStopped_)\n                zero_all_forces();\n            reset_signal_state();\n            // Re-enable any hardware effect selected by the new profile on the\n            // first active gameplay tick instead of waiting up to one second.\n            // The normal warm-up ramp is already reset by reset_signal_state().\n            updateCounter_ = 59;\n            spdlog::info("WheelFFB: settings/profile transition; forces zeroed and warm-up restarted");\n        }\n\n        void service_safety()\n        {''')

replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''void WheelFFB_RequestDirectionTest(int direction)\n{\n    gWheelFFB.request_direction_test(direction);\n}\n''',
    '''void WheelFFB_RequestDirectionTest(int direction)\n{\n    gWheelFFB.request_direction_test(direction);\n}\n\nvoid WheelFFB_RequestSettingsTransition()\n{\n    gWheelFFB.settings_transition();\n}\n''')

# FFB profile UI and full 0..1 damping access. Device identity remains separate.
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '#include "overlay.hpp"\n',
    '#include "overlay.hpp"\n#include "wheel_profile_store.hpp"\n')
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    'void WheelFFB_RequestDirectionTest(int direction);\n',
    'void WheelFFB_RequestDirectionTest(int direction);\nvoid WheelFFB_RequestSettingsTransition();\n')
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''        std::string status_;\n        bool ffbDirty_ = false;\n\n        void save()''',
    '''        std::string status_;\n        bool ffbDirty_ = false;\n        std::vector<std::string> ffbProfiles_;\n        int selectedFfbProfile_ = -1;\n        char ffbProfileName_[65]{};\n        bool ffbProfilesLoaded_ = false;\n        bool confirmingFfbOverwrite_ = false;\n        bool confirmingFfbDelete_ = false;\n\n        void refresh_ffb_profiles(const std::string& selectName = {})\n        {\n            ffbProfiles_ = WheelProfileStore::list_profiles(WheelProfileStore::Kind::ForceFeedback);\n            selectedFfbProfile_ = -1;\n            const std::string wanted = WheelProfileStore::normalize_profile_name(selectName);\n            if (!wanted.empty())\n            {\n                for (size_t i = 0; i < ffbProfiles_.size(); ++i)\n                    if (WheelProfileStore::lower_ascii(ffbProfiles_[i]) == WheelProfileStore::lower_ascii(wanted))\n                    {\n                        selectedFfbProfile_ = int(i);\n                        break;\n                    }\n            }\n            if (selectedFfbProfile_ >= 0)\n                strncpy_s(ffbProfileName_, ffbProfiles_[selectedFfbProfile_].c_str(), sizeof(ffbProfileName_) - 1);\n            ffbProfilesLoaded_ = true;\n        }\n\n        const std::string* selected_ffb_profile() const\n        {\n            return selectedFfbProfile_ >= 0 && selectedFfbProfile_ < int(ffbProfiles_.size())\n                ? &ffbProfiles_[selectedFfbProfile_] : nullptr;\n        }\n\n        void draw_ffb_profiles()\n        {\n            if (!ffbProfilesLoaded_)\n                refresh_ffb_profiles();\n\n            ImGui::SeparatorText("Force Feedback Profiles");\n            ImGui::TextWrapped("Save several force-feel setups and switch between them. Profiles store force behavior only; the selected FFB Output wheel and diagnostic logging stay global.");\n\n            const std::string* selected = selected_ffb_profile();\n            const char* preview = selected ? selected->c_str() : "Select a saved FFB profile";\n            if (ImGui::BeginCombo("Saved FFB profile", preview))\n            {\n                for (size_t i = 0; i < ffbProfiles_.size(); ++i)\n                {\n                    const bool selectedNow = int(i) == selectedFfbProfile_;\n                    if (ImGui::Selectable(ffbProfiles_[i].c_str(), selectedNow))\n                    {\n                        selectedFfbProfile_ = int(i);\n                        strncpy_s(ffbProfileName_, ffbProfiles_[i].c_str(), sizeof(ffbProfileName_) - 1);\n                        confirmingFfbOverwrite_ = false;\n                        confirmingFfbDelete_ = false;\n                    }\n                    if (selectedNow) ImGui::SetItemDefaultFocus();\n                }\n                ImGui::EndCombo();\n            }\n\n            if (ImGui::InputText("FFB profile name", ffbProfileName_, sizeof(ffbProfileName_)))\n                confirmingFfbOverwrite_ = false;\n            const std::string requested = WheelProfileStore::normalize_profile_name(ffbProfileName_);\n            const bool exists = !requested.empty() &&\n                WheelProfileStore::profile_exists(WheelProfileStore::Kind::ForceFeedback, requested);\n            const char* saveLabel = confirmingFfbOverwrite_\n                ? "Confirm overwrite##ffbProfileSave"\n                : (exists ? "Overwrite profile##ffbProfileSave" : "Save as profile##ffbProfileSave");\n            if (ImGui::Button(saveLabel))\n            {\n                if (exists && !confirmingFfbOverwrite_)\n                {\n                    confirmingFfbOverwrite_ = true;\n                    status_ = "Click Confirm overwrite to replace the existing FFB profile.";\n                }\n                else\n                {\n                    std::string error;\n                    if (WheelProfileStore::save_ffb_profile(requested, &error))\n                    {\n                        const bool currentSaved = Settings::write(Module::UserIniPath);\n                        ffbDirty_ = !currentSaved;\n                        status_ = currentSaved\n                            ? "FFB profile saved: " + requested\n                            : "FFB profile saved, but current user.ini settings could not be persisted.";\n                        confirmingFfbOverwrite_ = false;\n                        refresh_ffb_profiles(requested);\n                    }\n                    else\n                        status_ = error;\n                }\n            }\n\n            ImGui::SameLine();\n            const bool canUseProfile = selected_ffb_profile() != nullptr;\n            if (!canUseProfile) ImGui::BeginDisabled();\n            if (ImGui::Button("Load selected##ffbProfileLoad"))\n            {\n                if (const std::string* profile = selected_ffb_profile())\n                {\n                    int applied = 0;\n                    std::string error;\n                    if (WheelProfileStore::load_ffb_profile(*profile, &applied, &error))\n                    {\n                        WheelFFB_RequestSettingsTransition();\n                        const bool persisted = Settings::write(Module::UserIniPath);\n                        ffbDirty_ = !persisted;\n                        status_ = persisted\n                            ? "Loaded FFB profile '" + *profile + "' (" + std::to_string(applied) + " settings)."\n                            : "FFB profile is active now, but could not be persisted to user.ini.";\n                    }\n                    else\n                        status_ = error;\n                }\n            }\n            if (!canUseProfile) ImGui::EndDisabled();\n\n            ImGui::SameLine();\n            if (!canUseProfile) ImGui::BeginDisabled();\n            const char* deleteLabel = confirmingFfbDelete_\n                ? "Confirm delete##ffbProfileDelete" : "Delete selected##ffbProfileDelete";\n            if (ImGui::Button(deleteLabel))\n            {\n                if (!confirmingFfbDelete_)\n                {\n                    confirmingFfbDelete_ = true;\n                    status_ = "Click Confirm delete to remove the selected FFB profile. Current forces will not change.";\n                }\n                else if (const std::string* profile = selected_ffb_profile())\n                {\n                    std::string error;\n                    if (WheelProfileStore::delete_profile(WheelProfileStore::Kind::ForceFeedback, *profile, &error))\n                    {\n                        status_ = "Deleted FFB profile: " + *profile;\n                        ffbProfileName_[0] = '\\0';\n                        refresh_ffb_profiles();\n                    }\n                    else\n                        status_ = error;\n                    confirmingFfbDelete_ = false;\n                }\n            }\n            if (!canUseProfile) ImGui::EndDisabled();\n\n            ImGui::SameLine();\n            if (ImGui::Button("Refresh FFB profiles"))\n                refresh_ffb_profiles(selected_ffb_profile() ? *selected_ffb_profile() : std::string{});\n            ImGui::TextDisabled("Profile folder: OutRun2006Tweaks.profiles\\\\FFB");\n        }\n\n        void save()''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            if (!Settings::UseNewInput)\n            {\n            const int regularSlots = UniversalWheelProfile::regular_device_count();''',
    '''            draw_ffb_profiles();\n\n            if (!Settings::UseNewInput)\n            {\n            const int regularSlots = UniversalWheelProfile::regular_device_count();''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    'ImGui::SliderFloat("Dynamic Damping", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 0.80f, "%.2f")',
    'ImGui::SliderFloat("Dynamic Damping", Settings::WheelFFBDamperStrength.ptr(), 0.0f, 1.0f, "%.2f")')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                Settings::VibrationMode = 0;\n                if (Settings::write(Module::UserIniPath))''',
    '''                Settings::VibrationMode = 0;\n                WheelFFB_RequestSettingsTransition();\n                if (Settings::write(Module::UserIniPath))''')
# Same block exists for Natural SAT after the first replacement, so replace it once again.
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                Settings::VibrationMode = 0;\n                if (Settings::write(Module::UserIniPath))''',
    '''                Settings::VibrationMode = 0;\n                WheelFFB_RequestSettingsTransition();\n                if (Settings::write(Module::UserIniPath))''')

# Runtime profile files should never be accidentally committed from a local install.
gitignore = read(".gitignore")
if "OutRun2006Tweaks.profiles/" not in gitignore:
    if gitignore and not gitignore.endswith("\n"):
        gitignore += "\n"
    gitignore += "OutRun2006Tweaks.profiles/\n"
    write(".gitignore", gitignore)

# Documentation: fix the stale broad-family wording and explain the two profile types.
replace_once(
    "WHEEL_FFB.md",
    '''Quick Setup currently walks through Steering, Accelerator, Brake, Shift Up/Down, Start, Confirm, Back and Menu Up/Right/Down/Left. Each captured raw-device source replaces only the same broad source family, so configuring a wheel does not erase existing gamepad bindings. A step can be skipped when the wheel has no matching control. After the wizard, **Keep & Fine-tune** retains all captures and returns to the editor for per-axis Min / Rest / Max calibration.\n\nBindings are live immediately but are not durable until saved. Manual edits expose **Save & Return to game** so it is explicit whether the current mapping has been persisted.\n''',
    '''Quick Setup currently walks through Steering, Accelerator, Brake, Shift Up/Down, Start, Confirm, Back and Menu Up/Right/Down/Left. Each captured raw-device source replaces bindings only from the same currently resolved physical SDL device, so a wheel pass does not erase separate pedals, a shifter/button box or the default gamepad bindings. A step can be skipped when the wheel has no matching control. After the wizard, **Keep & Fine-tune** retains all captures and returns to the editor for per-axis Min / Rest / Max calibration.\n\nBindings are live immediately but are not durable until saved. Manual edits expose **Save & Return to game** so it is explicit whether the current mapping has been persisted. The **Profiles** tab can save the complete multi-device binding set as `OutRun2006Tweaks.profiles/Input/<name>.ini`; steering deadzone, sensitivity bypass and input backend travel with that wheel profile. Loading a profile also updates the normal `OutRun2006Tweaks.input.ini`, so the selected setup survives the next restart.\n''')

replace_once(
    "WHEEL_FFB.md",
    '''The dedicated Force Feedback page exposes common controls directly and keeps lower-level but still supported values under **Advanced FFB tuning** (Spring Saturation, Weight Transfer, Lateral Signal Deadzone, Gear Shift, Engine Idle and Force Slew Rate).\n''',
    '''The dedicated Force Feedback page exposes common controls directly and keeps lower-level but still supported values under **Advanced FFB tuning** (Spring Saturation, Weight Transfer, Lateral Signal Deadzone, Gear Shift, Engine Idle and Force Slew Rate). Named feel profiles are stored separately under `OutRun2006Tweaks.profiles/FFB/<name>.ini`. They intentionally exclude the DirectInput output-device GUID/name and diagnostic logging, so switching a force profile cannot silently redirect torque to another wheel. Loading a profile zeroes the current effects and restarts the normal DD-safe warm-up ramp before the new values take over.\n''')

# Static regression guards for the new profile design and the FFB transition path.
verify = read("tools/verify_wheel_ffb_current.py")
verify = verify.replace(
    "wheel_ui = read('src/overlay/wheel_setup_ui.cpp')\nini = read('OutRun2006Tweaks.ini')\n",
    "wheel_ui = read('src/overlay/wheel_setup_ui.cpp')\nprofiles = read('src/wheel_profile_store.hpp')\nini = read('OutRun2006Tweaks.ini')\n",
    1)
marker = "req(wheel_ui, 'Save Force Feedback', 'dedicated FFB save action')\n"
if marker not in verify:
    raise SystemExit("verify insertion marker not found")
extra = r'''req(profiles, 'OutRun2006Tweaks.profiles', 'named wheel/FFB profile root')
req(profiles, 'Kind::Input ? "Input" : "FFB"', 'separate input and FFB profile folders')
req(profiles, 'InputBackend = ', 'wheel profile stores backend choice')
req(profiles, 'SteeringDeadZone = ', 'wheel profile stores steering deadzone')
req(profiles, 'BypassGameSensitivity = ', 'wheel profile stores sensitivity bypass')
forbid(profiles, 'UseNewInput = ', 'wheel profile never switches the input architecture live')
req(profiles, 'key != "DeviceName" && key != "DeviceGuid"', 'FFB profiles never reroute the output device')
req(profiles, 'key != "Telemetry" && key != "DebugLog"', 'FFB profiles keep diagnostics global')
req(profiles, 'load_ffb_profile(', 'transactional named FFB profile loader')
req(bind_ui, 'ImGui::BeginTabItem("Profiles")', 'input binding UI exposes wheel profiles')
req(bind_ui, 'WheelProfileStore::append_input_options', 'wheel profile saves wheel-specific input options')
req(bind_ui, 'manager.saveBindingIni(Module::BindingsIniPath)', 'loaded wheel profile is durable in canonical binding file')
req(wheel_ui, 'Force Feedback Profiles', 'FFB UI exposes named profiles')
req(wheel_ui, 'WheelProfileStore::save_ffb_profile', 'FFB UI saves named profile')
req(wheel_ui, 'WheelProfileStore::load_ffb_profile', 'FFB UI loads named profile')
req(wheel_ui, 'WheelFFB_RequestSettingsTransition();', 'profile/preset switching requests safe FFB transition')
req(wheel_ui, 'WheelFFBDamperStrength.ptr(), 0.0f, 1.0f', 'Dynamic Damping UI exposes full supported range')
req(ffb, 'void settings_transition()', 'FFB engine has profile transition safety path')
req(ffb, 'updateCounter_ = 59;', 'profile transition recreates newly enabled hardware effects promptly')
req(ffb, 'settings/profile transition; forces zeroed and warm-up restarted', 'profile transition is observable in logs')
req(ffb, 'void WheelFFB_RequestSettingsTransition()', 'FFB settings transition exported to UI')
'''
verify = verify.replace(marker, marker + extra, 1)
write("tools/verify_wheel_ffb_current.py", verify)

# Source-only validation. Compiled numeric/build testing remains for the later
# hardware/build phase; this review intentionally does not compile a DLL.
subprocess.run(["python", "tools/verify_wheel_ffb_current.py"], cwd=ROOT, check=True)

subprocess.run(["git", "add", ".gitignore", "src/wheel_profile_store.hpp",
                "src/overlay/input_bindings_ui.cpp", "src/overlay/wheel_setup_ui.cpp",
                "src/hooks_wheel_ffb.cpp", "tools/verify_wheel_ffb_current.py", "WHEEL_FFB.md"], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "feat: add named wheel and FFB profiles [skip ci]"], cwd=ROOT, check=True)
