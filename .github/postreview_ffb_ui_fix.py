from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8',newline='\n')
def rep(p,old,new,count=1):
    s=read(p); n=s.count(old)
    if n!=count: raise SystemExit(f'{p}: expected {count}, found {n}: {old[:90]!r}')
    write(p,s.replace(old,new,count))

# Explicit OFF-state bits are safer for UI warnings than assuming every driver
# reports the corresponding ON bit.
rep('src/wheel_ffb_runtime.hpp', '''    bool actuatorsOn = false;
    bool powerOn = false;
    bool safetySwitchOn = false;
    bool userSwitchOn = false;
''', '''    bool actuatorsOn = false;
    bool powerOn = false;
    bool powerOff = false;
    bool safetySwitchOn = false;
    bool safetySwitchOff = false;
    bool userSwitchOn = false;
    bool userSwitchOff = false;
''')

# Capability metadata on old drivers is advisory for the irreplaceable
# ConstantForce path. Keep CARTESIAN fallback, but do not reject the interface.
rep('src/hooks_wheel_ffb.cpp', '''            if (constantCapsKnown_ && !liveMagnitude)
            {
                spdlog::error(
                    "WheelFFB: ConstantForce reports no live magnitude update support; rejecting this FFB interface");
                return false;
            }
''', '''            if (constantCapsKnown_ && !liveMagnitude)
            {
                spdlog::warn(
                    "WheelFFB: ConstantForce metadata reports no live magnitude update support; keeping the compatibility path because no equivalent software actuator exists");
            }
''')

rep('src/hooks_wheel_ffb.cpp', '''                    result.powerOn = (state & DIGFFS_POWERON) != 0;
                    result.safetySwitchOn = (state & DIGFFS_SAFETYSWITCHON) != 0;
                    result.userSwitchOn = (state & DIGFFS_USERFFSWITCHON) != 0;
''', '''                    result.powerOn = (state & DIGFFS_POWERON) != 0;
                    result.powerOff = (state & DIGFFS_POWEROFF) != 0;
                    result.safetySwitchOn = (state & DIGFFS_SAFETYSWITCHON) != 0;
                    result.safetySwitchOff = (state & DIGFFS_SAFETYSWITCHOFF) != 0;
                    result.userSwitchOn = (state & DIGFFS_USERFFSWITCHON) != 0;
                    result.userSwitchOff = (state & DIGFFS_USERFFSWITCHOFF) != 0;
''')

# Mark direction verification only when the test can actually be queued.
rep('src/hooks_wheel_ffb.cpp', '''        void request_direction_test(int direction)
        {
            if (direction != 0)
                directionTested_ = true;
            if (direction == 0)
''', '''        void request_direction_test(int direction)
        {
            if (direction == 0)
''')
rep('src/hooks_wheel_ffb.cpp', '''            manualTestDirection_ = direction < 0 ? -1 : 1;
            manualTestFrames_ = 18;
''', '''            directionTested_ = true;
            manualTestDirection_ = direction < 0 ? -1 : 1;
            manualTestFrames_ = 18;
''')

# Explicit include for std::uint16_t used by DirectInput device metadata.
rep('src/overlay/wheel_setup_ui.cpp', '''#include <cstdio>
#include <cstring>
''', '''#include <cstdio>
#include <cstdint>
#include <cstring>
''')

# Warn only for explicit OFF/lost state; not all drivers advertise ON bits.
rep('src/overlay/wheel_setup_ui.cpp', '''                    if (!ffbStatus.powerOn || !ffbStatus.safetySwitchOn || !ffbStatus.userSwitchOn || ffbStatus.deviceLost)
                        ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.25f, 1.0f),
                            "Wheel/driver reports FFB disabled or unavailable. This page will not override a hardware safety/user switch.");
''', '''                    if (ffbStatus.powerOff || ffbStatus.safetySwitchOff || ffbStatus.userSwitchOff || ffbStatus.deviceLost)
                        ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.25f, 1.0f),
                            "Wheel/driver explicitly reports FFB disabled or unavailable. This page will not override a hardware safety/user switch.");
''')

# Revert baseline follows every operation that successfully persisted the now
# active FFB values.
rep('src/overlay/wheel_setup_ui.cpp', '''                        ffbDirty_ = !persisted;
                        status_ = persisted
                            ? "Loaded FFB profile '" + *profile + "' (" + std::to_string(applied) + " settings)."
''', '''                        ffbDirty_ = !persisted;
                        if (persisted)
                            capture_saved_ffb();
                        status_ = persisted
                            ? "Loaded FFB profile '" + *profile + "' (" + std::to_string(applied) + " settings)."
''')
# Both R3 preset save-success blocks have the same ffbDirty/status structure but
# distinct status strings. Add capture after ffbDirty false for both.
s=read('src/overlay/wheel_setup_ui.cpp')
old='''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    status_ = "Loaded MOZA R3 Physics SAT: speed-adaptive front slip plus pneumatic/mechanical trail SAT; diagnostic logging enabled. Saved to user.ini.";
'''
new='''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    capture_saved_ffb();
                    status_ = "Loaded MOZA R3 Physics SAT: speed-adaptive front slip plus pneumatic/mechanical trail SAT; diagnostic logging enabled. Saved to user.ini.";
'''
if old not in s: raise SystemExit('Physics preset save block not found')
s=s.replace(old,new,1)
old='''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    status_ = "Loaded MOZA R3 Natural SAT: smooth progressive SAT, low-speed-only spring assist and single DirectInput COM wheel FFB. Saved to user.ini.";
'''
new='''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    capture_saved_ffb();
                    status_ = "Loaded MOZA R3 Natural SAT: smooth progressive SAT, low-speed-only spring assist and single DirectInput COM wheel FFB. Saved to user.ini.";
'''
if old not in s: raise SystemExit('Natural preset save block not found')
s=s.replace(old,new,1)
write('src/overlay/wheel_setup_ui.cpp',s)

# Also highlight legacy Bind buttons for consistency when compatibility mode is
# used; modern Input Bindings already highlights the exact listening row.
rep('src/overlay/wheel_setup_ui.cpp', '''            ImGui::SameLine(290.0f);
            if (ImGui::Button("Bind", ImVec2(70, 0)))
                begin_bind(target);
''', '''            ImGui::SameLine(290.0f);
            const bool listeningHere = target_ == target;
            if (listeningHere)
            {
                ImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
                ImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
            }
            if (ImGui::Button(listeningHere ? "LISTENING..." : "Bind", ImVec2(90, 0)))
                begin_bind(target);
            if (listeningHere)
                ImGui::PopStyleColor(2);
''')
rep('src/overlay/wheel_setup_ui.cpp', '''            ImGui::SameLine(330.0f);
            if (ImGui::Button("Bind", ImVec2(70, 0)))
                begin_bind(target);
''', '''            ImGui::SameLine(330.0f);
            const bool listeningHere = target_ == target;
            if (listeningHere)
            {
                ImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
                ImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
            }
            if (ImGui::Button(listeningHere ? "LISTENING..." : "Bind", ImVec2(90, 0)))
                begin_bind(target);
            if (listeningHere)
                ImGui::PopStyleColor(2);
''')

# Extend verifier to cover post-review safeguards.
p=Path('tools/verify_wheel_ffb_current.py')
v=p.read_text(encoding='utf-8')
extra='''\nreq(ffb, 'result.powerOff = (state & DIGFFS_POWEROFF) != 0;', 'FFB status distinguishes explicit power-off state')\nreq(wheel_ui, 'ffbStatus.powerOff || ffbStatus.safetySwitchOff || ffbStatus.userSwitchOff', 'FFB UI warns only on explicit driver OFF states')\nforbid(ffb, 'rejecting this FFB interface', 'ConstantForce capability metadata cannot falsely reject the only actuator path')\nreq(wheel_ui, 'if (persisted)\\n                            capture_saved_ffb();', 'loaded FFB profile updates revert baseline after persistence')\nreq(wheel_ui, 'listeningHere ? "LISTENING..." : "Bind"', 'legacy manual binding also highlights current target')\n'''
if 'FFB status distinguishes explicit power-off state' not in v:
    v += extra
p.write_text(v,encoding='utf-8',newline='\n')
print('post-review FFB/UI safeguards applied')
