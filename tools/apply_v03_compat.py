from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} not found')
    return text.replace(old, new, 1)


profiles = Path('src/wheel_profile_store.hpp')
p = profiles.read_text(encoding='utf-8')
start = p.index('        std::filesystem::rename(staged, finalPath, ec);')
end = p.index('\n    inline bool delete_profile', start)
new_tail = '''        bool installedByCopyFallback = false;
        std::filesystem::rename(staged, finalPath, ec);
        if (ec)
        {
            const std::string renameError = ec.message();
            std::error_code copyEc;
            std::filesystem::copy_file(
                staged, finalPath, std::filesystem::copy_options::overwrite_existing, copyEc);
            if (copyEc)
            {
                if (finalExists)
                {
                    std::error_code restoreEc;
                    std::filesystem::rename(backup, finalPath, restoreEc);
                    if (restoreEc)
                    {
                        if (error) *error = "Could not install the new profile (rename: " + renameError +
                            "; copy fallback: " + copyEc.message() + ") and could not restore the backup (" +
                            restoreEc.message() + "). Destination: " + finalPath.string();
                        return false;
                    }
                }
                if (error) *error = "Could not install the completed profile (rename: " + renameError +
                    "; copy fallback: " + copyEc.message() + "). Destination: " + finalPath.string();
                return false;
            }
            installedByCopyFallback = true;
        }

        std::error_code verifyEc;
        const bool installed = std::filesystem::is_regular_file(finalPath, verifyEc) && !verifyEc;
        if (!installed)
        {
            std::error_code ignored;
            std::filesystem::remove(finalPath, ignored);
            if (finalExists)
            {
                std::error_code restoreEc;
                std::filesystem::rename(backup, finalPath, restoreEc);
                if (restoreEc)
                {
                    if (error) *error = "Profile installation could not be verified and the previous profile could not be restored: " +
                        restoreEc.message() + ". Destination: " + finalPath.string();
                    return false;
                }
            }
            if (error) *error = "Profile installation could not be verified. Destination: " + finalPath.string();
            return false;
        }

        if (installedByCopyFallback)
        {
            std::error_code ignored;
            std::filesystem::remove(staged, ignored);
        }
        if (finalExists)
        {
            std::error_code ignored;
            std::filesystem::remove(backup, ignored);
        }
        return true;
    }
'''
p = p[:start] + new_tail + p[end:]
profiles.write_text(p, encoding='utf-8')

ui = Path('src/overlay/wheel_setup_ui.cpp')
u = ui.read_text(encoding='utf-8')
ready_start = u.index('                const auto readiness = [](const char* label, bool ok)')
ready_end = u.index('                ImGui::SeparatorText("FFB Runtime Status");', ready_start)
ready_block = '''                const auto readiness = [](const char* label, bool ok)
                {
                    ImGui::TextColored(ok ? ImVec4(0.35f, 0.90f, 0.45f, 1.0f) : ImVec4(1.0f, 0.45f, 0.25f, 1.0f),
                        "%s %s", ok ? "[OK]" : "[!]", label);
                };
                const auto pending = [](const char* label)
                {
                    ImGui::TextColored(ImVec4(0.85f, 0.78f, 0.35f, 1.0f), "[..] %s", label);
                };
                readiness("Steering", steeringReady);
                ImGui::SameLine(); readiness("Pedals", accelReady && brakeReady);
                ImGui::SameLine(); readiness("Shifters", driveButtonsReady);
                readiness("Menu controls", menuReady);
                const bool gameplayFfbWindow = Game::is_in_game();
                ImGui::SameLine();
                if (!Settings::WheelFFBEnable)
                    readiness("FFB disabled", true);
                else if (ffbStatus.initialized)
                    readiness("FFB device", true);
                else if (!gameplayFfbWindow)
                    pending("FFB device (starts in gameplay)");
                else
                    readiness("FFB device", false);
                ImGui::SameLine();
                if (!Settings::WheelFFBEnable || ffbStatus.directionTested)
                    readiness("Direction test", true);
                else
                    pending("Direction test (not run)");

'''
u = u[:ready_start] + ready_block + u[ready_end:]
engine_start = u.index('                ImGui::Text("Engine: %s   Device: %s   Output owner: %s",')
effects_start = u.index('                ImGui::Text("Effects: Constant %s | Spring %s | Damper %s | Periodic %s",', engine_start)
engine_block = '''                ImGui::Text("Engine: %s   Device: %s   Output owner: %s",
                    ffbStatus.initialized ? "ready" : "waiting",
                    ffbStatus.acquired ? "acquired" : "released",
                    ffbStatus.outputOwner ? "active" : "inactive");
                if (Settings::WheelFFBEnable && !ffbStatus.initialized && !gameplayFfbWindow)
                    ImGui::TextDisabled("Waiting / released / inactive is normal outside gameplay. The saved FFB GUID is acquired when driving starts.");
                if (Settings::WheelFFBEnable && !ffbStatus.directionTested)
                    ImGui::TextDisabled("Direction test is a setup confirmation, not a hardware error. Run Test Left/Right after the FFB engine is ready.");
'''
u = u[:engine_start] + engine_block + u[effects_start:]
u = replace_once(u,
'''                        status_ = currentSaved
                            ? "FFB profile saved: " + requested
                            : "FFB profile saved, but current user.ini settings could not be persisted.";
''',
'''                        std::string pathError;
                        const auto savedPath = WheelProfileStore::profile_path(
                            WheelProfileStore::Kind::ForceFeedback, requested, &pathError);
                        const std::string savedWhere = savedPath ? savedPath->string() : requested;
                        status_ = currentSaved
                            ? "FFB profile saved: " + savedWhere
                            : "FFB profile saved to " + savedWhere + ", but current user.ini settings could not be persisted.";
''', 'profile success status')
u = replace_once(u,
'''                    else
                        status_ = error;
''',
'''                    else
                    {
                        status_ = "FFB profile save failed: " + error + " Folder: " +
                            WheelProfileStore::directory(WheelProfileStore::Kind::ForceFeedback).string();
                        spdlog::error("{}", status_);
                    }
''', 'profile failure status')
u = replace_once(u,
'            ImGui::TextDisabled("Profile folder: OutRun2006Tweaks.profiles\\\\FFB");\n',
'''            const std::string ffbProfileFolder =
                WheelProfileStore::directory(WheelProfileStore::Kind::ForceFeedback).string();
            ImGui::TextDisabled("Profile folder: %s", ffbProfileFolder.c_str());
''', 'profile folder label')
ui.write_text(u, encoding='utf-8')

verifier = Path('tools/verify_wheel_ffb_current.py')
v = verifier.read_text(encoding='utf-8')
v = replace_once(v,
"req(wheel_ui, 'const bool ffbReady = !Settings::WheelFFBEnable || ffbStatus.initialized;', 'Ready checklist does not treat a disconnected saved GUID as ready')",
"req(wheel_ui, 'pending(\\\"FFB device (starts in gameplay)\\\");', 'Ready checklist treats menu-time FFB runtime as pending, not failed')",
'readiness verifier')
v = replace_once(v,
"req(wheel_ui, 'OutRun2006Tweaks.profiles\\\\\\\\FFB', 'FFB profile folder path escapes backslash')",
"req(wheel_ui, 'WheelProfileStore::directory(WheelProfileStore::Kind::ForceFeedback).string()', 'FFB page shows the actual runtime profile folder')",
'profile path verifier')
extra = '''
# v0.3 hardware compatibility regression guards
req(profiles, 'std::filesystem::copy_file(', 'named profile save has rename-to-copy fallback for Windows driver/filter edge cases')
req(profiles, 'Profile installation could not be verified.', 'named profile save verifies the final file exists')
req(wheel_ui, 'Direction test (not run)', 'direction-test checklist distinguishes pending from failure')
req(wheel_ui, 'Waiting / released / inactive is normal outside gameplay.', 'runtime status explains menu-time idle state')
req(wheel_ui, 'FFB profile save failed:', 'profile persistence failures are explicit')
req(wheel_ui, 'spdlog::error("{}", status_);', 'profile persistence failure is logged for remote testers')
'''
if '# v0.3 hardware compatibility regression guards' not in v:
    v += extra
verifier.write_text(v, encoding='utf-8')
