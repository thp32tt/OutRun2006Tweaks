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
        raise SystemExit(f"{rel}: expected exactly one match, got {count}: {old[:140]!r}")
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
verifier = "tools/verify_wheel_ffb_current.py"
readme = "README.md"
wheel_doc = "WHEEL_FFB.md"

# Review findings 1-5: make Quick Setup complete enough to operate menus from a
# wheel, keep multi-device bindings from unrelated source families, allow
# unsupported steps to be skipped, allow post-wizard calibration without
# rollback, and make the persistence choice explicit when leaving manual edits.
replace_once(
    bind_ui,
    '''\t\t{ "Start",       "Press the button you want to use for Start and Pause.",      Sw,  int(SwitchId::Start) },
\t\t{ "Confirm",     "Press the button you want to use to confirm menu choices.",  Sw,  int(SwitchId::A) },
\t\t{ "Back",        "Press the button you want to use to go back.",               Sw,  int(SwitchId::B) },
\t};''',
    '''\t\t{ "Start",       "Press the button you want to use for Start and Pause.",      Sw,  int(SwitchId::Start) },
\t\t{ "Confirm",     "Press the button you want to use to confirm menu choices.",  Sw,  int(SwitchId::A) },
\t\t{ "Back",        "Press the button you want to use to go back.",               Sw,  int(SwitchId::B) },
\t\t{ "Menu Up",     "Press Up on the wheel D-pad/POV, or another menu button.",    Sw,  int(SwitchId::SelectionUp) },
\t\t{ "Menu Right",  "Press Right on the wheel D-pad/POV, or another menu button.", Sw,  int(SwitchId::SelectionRight) },
\t\t{ "Menu Down",   "Press Down on the wheel D-pad/POV, or another menu button.",  Sw,  int(SwitchId::SelectionDown) },
\t\t{ "Menu Left",   "Press Left on the wheel D-pad/POV, or another menu button.",  Sw,  int(SwitchId::SelectionLeft) },
\t};''')

replace_once(
    bind_ui,
    '''\tstatic bool is_steering(const Selection& selection)
\t{
\t\treturn selection.isVolume() && selection.index == int(ADChannel::Steering);
\t}

\tvoid begin_listening''',
    '''\tstatic bool is_steering(const Selection& selection)
\t{
\t\treturn selection.isVolume() && selection.index == int(ADChannel::Steering);
\t}

\t// Quick Setup replaces only the same broad input source it just captured.
\t// A wheel/raw-device pass must not erase the default gamepad bindings: the
\t// whole point of this branch is that a wheel, pedals and a pad can coexist.
\tstatic bool same_source_family(const InputBinding& existing, const InputBinding& candidate)
\t{
\t\tif (candidate.isRawDevice()) return existing.isRawDevice();
\t\tif (candidate.isGamepad()) return existing.isGamepad();
\t\tif (candidate.isKeyboard()) return existing.isKeyboard();
\t\treturn false;
\t}

\tvoid begin_listening''')

replace_once(
    bind_ui,
    '''\t\tfor (const auto& device : InputManager::instance.devices)
\t\t{
\t\t\tauto& baseline = axisBaseline[device.instanceId];
\t\t\tconst int axisCount = SDL_GetNumJoystickAxes(device.joystick);
\t\t\tbaseline.reserve(axisCount);
\t\t\tfor (int axis = 0; axis < axisCount; ++axis)
\t\t\t\tbaseline.push_back(SDL_GetJoystickAxis(device.joystick, axis));
\t\t}
\t}

\tstatic Selection quick_setup_selection''',
    '''\t\tfor (const auto& device : InputManager::instance.devices)
\t\t{
\t\t\tauto& baseline = axisBaseline[device.instanceId];
\t\t\tconst int axisCount = SDL_GetNumJoystickAxes(device.joystick);
\t\t\tbaseline.reserve(axisCount);
\t\t\tfor (int axis = 0; axis < axisCount; ++axis)
\t\t\t\tbaseline.push_back(SDL_GetJoystickAxis(device.joystick, axis));
\t\t}
\t}

\tvoid skip_quick_setup_step()
\t{
\t\tif (!quickSetupActive || quickSetupStep >= int(std::size(QuickSetupSteps)))
\t\t\treturn;

\t\t++quickSetupStep;
\t\tquickSetupCandidate.reset();
\t\treleaseGuardBinding.reset();
\t\tquickSetupTimedOut = false;
\t\tImGui::CloseCurrentPopup();

\t\tif (quickSetupStep < int(std::size(QuickSetupSteps)))
\t\t\tbegin_listening(quick_setup_selection(quickSetupStep), -1);
\t\telse
\t\t{
\t\t\tquickSetupActive = false;
\t\t\tquickSetupComplete = true;
\t\t\tisListeningForInput = ListenState::False;
\t\t}
\t}

\tstatic Selection quick_setup_selection''')

replace_once(
    bind_ui,
    '''\t\t\t\t\tauto& bindings = action_for(bindTarget).bindings();
\t\t\t\t\tstd::erase_if(bindings, [](const InputBinding& existing) { return !existing.isKeyboard(); });
\t\t\t\t\taction_for(bindTarget).add(*quickSetupCandidate);''',
    '''\t\t\t\t\tauto& bindings = action_for(bindTarget).bindings();
\t\t\t\t\tstd::erase_if(bindings, [&](const InputBinding& existing)
\t\t\t\t\t\t{ return same_source_family(existing, *quickSetupCandidate); });
\t\t\t\t\taction_for(bindTarget).add(*quickSetupCandidate);''')

replace_once(
    bind_ui,
    '''\t\t\telse if (quickSetupActive && quickSetupTimedOut)
\t\t\t{
\t\t\t\tImGui::TextWrapped("No deliberate input was detected. This step was not skipped.");
\t\t\t\tif (ImGui::Button("Try this step again"))
\t\t\t\t{
\t\t\t\t\tbegin_listening(bindTarget, -1);
\t\t\t\t\tImGui::CloseCurrentPopup();
\t\t\t\t}
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tImGui::TextDisabled(quickSetupActive ? "Escape to cancel Quick Setup" : "Escape to cancel, Delete to clear");
\t\t\t\tif (HandleNewBinding())
\t\t\t\t\tunsavedChanges = true;
\t\t\t}''',
    '''\t\t\telse if (quickSetupActive && quickSetupTimedOut)
\t\t\t{
\t\t\t\tImGui::TextWrapped("No deliberate input was detected. Retry this control or skip it and keep its existing bindings.");
\t\t\t\tif (ImGui::Button("Try this step again"))
\t\t\t\t{
\t\t\t\t\tbegin_listening(bindTarget, -1);
\t\t\t\t\tImGui::CloseCurrentPopup();
\t\t\t\t}
\t\t\t\tImGui::SameLine();
\t\t\t\tif (ImGui::Button("Skip this step"))
\t\t\t\t\tskip_quick_setup_step();
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tImGui::TextDisabled(quickSetupActive ? "Escape to cancel Quick Setup" : "Escape to cancel, Delete to clear");
\t\t\t\tif (HandleNewBinding())
\t\t\t\t\tunsavedChanges = true;
\t\t\t\tif (quickSetupActive && !quickSetupCandidate)
\t\t\t\t{
\t\t\t\t\tImGui::SameLine();
\t\t\t\t\tif (ImGui::Button("Skip this step"))
\t\t\t\t\t\tskip_quick_setup_step();
\t\t\t\t}
\t\t\t}''')

replace_once(
    bind_ui,
    '''\t\tImGui::SameLine();
\t\tif (ImGui::Button("Start Over"))
\t\t{
\t\t\trestore_quick_setup_backup();
\t\t\tstart_quick_setup();
\t\t\tImGui::CloseCurrentPopup();
\t\t}
\t\tImGui::SameLine();
\t\tif (ImGui::Button("Cancel"))''',
    '''\t\tImGui::SameLine();
\t\tif (ImGui::Button("Keep & Fine-tune"))
\t\t{
\t\t\tquickSetupBackup.clear();
\t\t\tquickSetupComplete = false;
\t\t\tunsavedChanges = true;
\t\t\tImGui::CloseCurrentPopup();
\t\t}
\t\tImGui::SameLine();
\t\tif (ImGui::Button("Start Over"))
\t\t{
\t\t\trestore_quick_setup_backup();
\t\t\tstart_quick_setup();
\t\t\tImGui::CloseCurrentPopup();
\t\t}
\t\tImGui::SameLine();
\t\tif (ImGui::Button("Cancel"))''')

replace_once(
    bind_ui,
    '''\t\t\tImGui::TextDisabled("%s", unsavedChanges ? "Note: you have unsaved changes!" : "");

\t\t\tif (ImGui::Button("Return to game"))
\t\t\t\tdialogOpen = false;

\t\t\tImGui::SameLine();''',
    '''\t\t\tImGui::TextDisabled("%s", unsavedChanges
\t\t\t\t? "Note: unsaved bindings are active now but will be lost after restart."
\t\t\t\t: "");

\t\t\tif (unsavedChanges)
\t\t\t{
\t\t\t\tif (ImGui::Button("Save & Return to game"))
\t\t\t\t{
\t\t\t\t\tif (manager.saveBindingIni(Module::BindingsIniPath))
\t\t\t\t\t{
\t\t\t\t\t\tunsavedChanges = false;
\t\t\t\t\t\tdialogOpen = false;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tImGui::SameLine();
\t\t\t\tif (ImGui::Button("Return to game (not saved)"))
\t\t\t\t\tdialogOpen = false;
\t\t\t}
\t\t\telse if (ImGui::Button("Return to game"))
\t\t\t\tdialogOpen = false;

\t\t\tImGui::SameLine();''')

verify()
commit("ux: complete multi-device Quick Setup flow [skip ci]", bind_ui)

# Review findings 6-7: the FFB-only page should provide the direct path back to
# input setup and expose every meaningful FFB tuning setting that was hidden
# from the generic Settings page. This changes UI reachability only, not forces.
replace_once(
    wheel_ui,
    '''    extern Setting<float> WheelFFBGripLoss;
    extern Setting<float> WheelFFBWeightTransfer;
    extern Setting<float> WheelFFBSlewRate;
    extern Setting<int> VibrationMode;''',
    '''    extern Setting<float> WheelFFBGripLoss;
    extern Setting<float> WheelFFBLateralDeadzone;
    extern Setting<float> WheelFFBWeightTransfer;
    extern Setting<float> WheelFFBGearShift;
    extern Setting<float> WheelFFBEngineIdle;
    extern Setting<float> WheelFFBSlewRate;
    extern Setting<int> VibrationMode;''')

replace_once(
    wheel_ui,
    '''            if (Settings::UseNewInput)
            {
                ImGui::TextWrapped(
                    "Force feedback only. With UseNewInput enabled, steering, pedals, buttons, menu controls and calibration come only from Input Bindings. This page does not create input bindings; it only selects the DirectInput FFB wheel and tunes its forces.");
            }
            else''',
    '''            if (Settings::UseNewInput)
            {
                ImGui::TextWrapped(
                    "Force feedback only. With UseNewInput enabled, steering, pedals, buttons, menu controls and calibration come only from Input Bindings. This page does not create input bindings; it only selects the DirectInput FFB wheel and tunes its forces.");
                if (ImGui::Button("Open Input Bindings"))
                    Overlay::RequestBindingDialog = true;
                ImGui::SameLine();
                ImGui::TextDisabled("Configure steering, pedals, shifter and menu controls there first.");
            }
            else''')

replace_once(
    wheel_ui,
    '''            ImGui::Checkbox("Hardware road/slip sine effects", Settings::WheelFFBUsePeriodicEffects.ptr());
            ImGui::SameLine();
            ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());''',
    '''            ImGui::Checkbox("Hardware road/slip sine effects", Settings::WheelFFBUsePeriodicEffects.ptr());

            if (ImGui::CollapsingHeader("Advanced FFB tuning"))
            {
                ImGui::SliderFloat("Spring Saturation", Settings::WheelFFBSpringSaturation.ptr(), 0.10f, 1.0f, "%.3f");
                ImGui::SliderFloat("Weight Transfer", Settings::WheelFFBWeightTransfer.ptr(), 0.0f, 1.5f, "%.2f");
                ImGui::SliderFloat("Lateral Signal Deadzone", Settings::WheelFFBLateralDeadzone.ptr(), 0.0f, 8.0f, "%.2f");
                ImGui::SliderFloat("Gear Shift", Settings::WheelFFBGearShift.ptr(), 0.0f, 1.0f, "%.2f");
                ImGui::SliderFloat("Engine Idle", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.50f, "%.2f");
                ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f");
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
                ImGui::TextDisabled("Advanced values apply live like the main controls; use Save Force Feedback to persist them.");
            }

            ImGui::SameLine();
            ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());''')

verify()
commit("ux: connect input setup and expose advanced FFB tuning [skip ci]", wheel_ui)

# Review findings 8-9: the operator docs still described the old v0.1 UI and
# obsolete tuning labels. Update both languages and architecture notes to the
# controls users actually see now.
replace_once(readme,
    '- **F11 Quick Setup / 입력 보정**: 조향, 엑셀, 브레이크, 패들, 메뉴 버튼을 게임 안에서 설정하고 축의 Min / Rest / Max를 보정할 수 있습니다.',
    '- **Input Bindings Quick Setup / 입력 보정**: 조향, 엑셀, 브레이크, 패들, Start/Confirm/Back과 메뉴 4방향을 게임 안에서 설정하고 축의 Min / Rest / Max를 보정할 수 있습니다. 필요한 단계는 건너뛸 수 있고, 완료 후 설정을 유지한 채 세부 보정으로 이어갈 수 있습니다.')
replace_once(readme,
    '- **F11 Quick Setup and calibration**: configure steering, pedals, paddles and menu buttons in-game, including Min / Rest / Max axis calibration.',
    '- **Input Bindings Quick Setup and calibration**: configure steering, pedals, paddles, Start/Confirm/Back and the four menu directions in-game, including Min / Rest / Max axis calibration. Unsupported steps can be skipped and the captured setup can be kept for fine-tuning.')

regex_once(readme, r'### v0\.1 기본 프로파일 — MOZA R3\n.*?\n### 설치 방법', '''### MOZA R3 권장 프리셋

현재 F11 **Force Feedback** 화면에는 `Load MOZA R3 Physics SAT`와 `Load MOZA R3 Natural SAT` 두 프리셋이 있습니다. Physics SAT 프리셋은 실제 차량 이동/방향으로 추정한 front slip을 사용하고, 해당 샘플을 사용할 수 없을 때는 Natural SAT로 자동 폴백합니다.

| 항목 | Physics SAT 프리셋 |
| --- | ---: |
| Overall Strength | 0.70 |
| Centering Spring | 0.65 |
| Spring Saturation | 0.95 |
| Dynamic Damping | 0.28 |
| Self-aligning Torque (SAT) | 1.45 |
| Grip-loss Response | 0.65 |
| Weight Transfer | 0.15 |
| Force Slew Rate | 0.040 |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Collision | 0.38 |
| Hardware Spring / Damper / sine | ON |
| Reverse SAT / ConstantForce | ON |
| Reverse Spring | OFF |

Natural SAT 프리셋은 Physics SAT를 끄고 Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20, Slew 0.045를 사용합니다. 방향 반전값은 장치별로 달라질 수 있으므로 안전 방향 테스트 결과를 우선하세요.

### 설치 방법''')

regex_once(readme, r'5\. 게임에서 \*\*F11\*\* 또는 Controller 설정 화면을 열고 .*?\n8\. 방향이 반대로 느껴질 때만 .*?\n', '''5. 게임의 **Controller Configuration**을 열거나, **F11 → Force Feedback → Open Input Bindings**를 눌러 Input Bindings를 엽니다.
6. **Quick Setup**으로 Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left를 설정합니다. 휠에 없는 기능은 `Skip this step`으로 기존 바인딩을 유지할 수 있습니다.
7. 완료 화면에서 조향/페달 값을 확인합니다. 범위가 맞지 않으면 `Keep & Fine-tune`으로 설정을 유지한 채 해당 축의 **Calibrate**에서 Min / Rest / Max를 보정한 뒤 `Save bindings` 또는 `Save & Return to game`으로 저장합니다.
8. **Force Feedback**에서 실제 FFB 휠을 선택하고 `Load MOZA R3 Physics SAT` 또는 `Load MOZA R3 Natural SAT`를 기준으로 시작합니다. 방향이 반대로 느껴질 때만 `Reverse SAT / ConstantForce` 또는 `Reverse Spring`을 조정합니다.
''')

replace_once(readme,
    '- FFB가 없으면 Force Feedback 탭에서 휠을 다시 선택하고 **Refresh connected wheels**를 사용합니다.',
    '- FFB가 없으면 Force Feedback 탭에서 **Refresh Devices**를 누르고 실제 FFB 인터페이스를 다시 선택합니다.')
replace_once(readme,
    '- 페달 방향이 반대라면 해당 축의 Invert/보정을 다시 설정합니다.',
    '- 페달 방향/범위가 이상하면 Input Bindings에서 해당 축의 **Calibrate**를 다시 실행합니다. 페달 방향은 FromRest 보정에서 자동 판별됩니다.')

regex_once(readme, r'### v0\.1 default profile — MOZA R3\n.*?\n### Installation', '''### Recommended MOZA R3 presets

The current F11 **Force Feedback** page provides `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT`. Physics SAT estimates front slip from current vehicle motion and heading, and automatically falls back to Natural SAT when a valid physics sample is unavailable.

| Setting | Physics SAT preset |
| --- | ---: |
| Overall Strength | 0.70 |
| Centering Spring | 0.65 |
| Spring Saturation | 0.95 |
| Dynamic Damping | 0.28 |
| Self-aligning Torque (SAT) | 1.45 |
| Grip-loss Response | 0.65 |
| Weight Transfer | 0.15 |
| Force Slew Rate | 0.040 |
| Road Detail | 0.30 |
| Tire Slip | 0.20 |
| Collision | 0.38 |
| Hardware Spring / Damper / sine | ON |
| Reverse SAT / ConstantForce | ON |
| Reverse Spring | OFF |

The Natural SAT preset disables Physics SAT and uses Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20 and Slew 0.045. Device direction can vary, so the safe direction test takes precedence over preset assumptions.

### Installation''')

regex_once(readme, r'5\. Open \*\*F11\*\* or the Controller setup screen and run .*?\n8\. Only change .*?\n', '''5. Open the game's **Controller Configuration**, or use **F11 → Force Feedback → Open Input Bindings**.
6. Run **Quick Setup**: Steering → Accelerator → Brake → Shift Up/Down → Start → Confirm → Back → Menu Up/Right/Down/Left. Use `Skip this step` for controls your wheel does not have; existing bindings are kept.
7. Check the live steering/pedal bars. If a range is wrong, choose `Keep & Fine-tune`, open **Calibrate** for that axis, then save with `Save bindings` or `Save & Return to game`.
8. Under **Force Feedback**, select the real FFB interface and start with `Load MOZA R3 Physics SAT` or `Load MOZA R3 Natural SAT`. Only change `Reverse SAT / ConstantForce` or `Reverse Spring` when the safe direction test shows it is needed.
''')
replace_once(readme,
    '- If FFB is missing, reselect the wheel under **Force Feedback** and try **Refresh connected wheels**.',
    '- If FFB is missing, use **Refresh Devices** under Force Feedback and reselect the actual FFB interface.')
replace_once(readme,
    '- If a pedal works backwards, recalibrate/invert that axis.',
    '- If a pedal direction or range is wrong, recalibrate that axis in Input Bindings; FromRest pedal direction is detected automatically.')

regex_once(wheel_doc, r'## Input setup\n.*?\n## Force model', '''## Input setup

With the default `UseNewInput=true` path, **Input Bindings** is the single owner of steering, pedals, shifter/buttons and menu controls. Open it from the game's Controller Configuration screen, from **Settings → Controls → Configure Input Bindings**, or directly from **F11 → Force Feedback → Open Input Bindings**.

Quick Setup currently walks through Steering, Accelerator, Brake, Shift Up/Down, Start, Confirm, Back and Menu Up/Right/Down/Left. Each captured raw-device source replaces only the same broad source family, so configuring a wheel does not erase existing gamepad bindings. A step can be skipped when the wheel has no matching control. After the wizard, **Keep & Fine-tune** retains all captures and returns to the editor for per-axis Min / Rest / Max calibration.

Bindings are live immediately but are not durable until saved. Manual edits expose **Save & Return to game** so it is explicit whether the current mapping has been persisted.

The Controllers page provides live raw axis/button/hat diagnostics and hotplugged devices appear automatically. Binding identity prefers VID/PID plus serial when available; USB path is only a duplicate-device fallback rather than a hard requirement.

## Force model''')

regex_once(wheel_doc, r'## Force model\n.*?\n## MOZA R3 v0\.1 default profile', '''## Force model

The FFB owner is the custom DirectInput COM engine and remains separate from SDL input ownership. The main steering model now has two SAT paths:

1. **Physics SAT** — estimates front slip from steering angle, body slip and yaw, then shapes it with a pneumatic-trail-like curve. It requires a current valid motion sample.
2. **Natural SAT** — steering-angle based progressive restoring torque. It is also the full-strength fallback while Physics SAT is calibrating or temporarily lacks valid motion telemetry.
3. **Centering Spring** — low-speed stabilizer, preferably DirectInput `GUID_Spring` when supported.
4. **Dynamic Damping** — resists steering velocity and releases with real front scrub/body slide.
5. **Weight Transfer** — filtered longitudinal acceleration/braking modulation of steering load.
6. **Collision / Gear Shift** — short event impulses kept separate from sustained steering slew.
7. **Road Detail / Tire Slip** — hardware sine effects where available, with a ConstantForce fallback that only uses remaining steering headroom.

`field_264/268` are used as lateral-load magnitude only; grip/slip decisions come from the vehicle-dynamics estimator. GlobalStrength is software model gain, while DirectInput device/effect gain stays at `DI_FFNOMINALMAX`. Sustained force passes through the production soft-knee limiter and DD-safe slew path.

The dedicated Force Feedback page exposes common controls directly and keeps lower-level but still supported values under **Advanced FFB tuning** (Spring Saturation, Weight Transfer, Lateral Signal Deadzone, Gear Shift, Engine Idle and Force Slew Rate).

## MOZA R3 recommended profiles''')

regex_once(wheel_doc, r'## MOZA R3 recommended profiles\n.*?\n## Safety and lifecycle', '''## MOZA R3 recommended profiles

The current UI provides two saved starting points rather than the obsolete single `v0.1 default` button.

```text
Load MOZA R3 Physics SAT
Overall Strength       0.70
Centering Spring       0.65
Spring Saturation      0.95
Dynamic Damping        0.28
Self-aligning Torque   1.45
Grip-loss Response     0.65
Weight Transfer        0.15
Force Slew Rate        0.040
Road Detail            0.30
Tire Slip              0.20
Collision              0.38
Hardware Spring        ON
Hardware Damper        ON
Hardware sine effects  ON
Reverse SAT/CF         ON
Reverse Spring         OFF
```

`Load MOZA R3 Natural SAT` keeps the same overall/effect baseline but disables Physics SAT and uses Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20 and Slew 0.045. Treat both as starting points: verify ConstantForce and Spring direction with the 20% safe tests before increasing hardware torque.

## Safety and lifecycle''')

commit("docs: align wheel setup guide with current UI [skip ci]", readme, wheel_doc)

# Review finding 10: lock the new setup UX into the consolidated verifier so a
# later FFB refactor cannot silently regress the initial configuration path.
text = read(verifier)
anchor = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')\n"
if text.count(anchor) != 1:
    raise SystemExit("verifier final print anchor missing or duplicated")
guards = '''req(bind_ui, 'Press Up on the wheel D-pad/POV, or another menu button.', 'Quick Setup captures menu Up')
req(bind_ui, 'Press Right on the wheel D-pad/POV, or another menu button.', 'Quick Setup captures menu Right')
req(bind_ui, 'Press Down on the wheel D-pad/POV, or another menu button.', 'Quick Setup captures menu Down')
req(bind_ui, 'Press Left on the wheel D-pad/POV, or another menu button.', 'Quick Setup captures menu Left')
req(bind_ui, 'same_source_family', 'Quick Setup preserves unrelated input source families')
forbid(bind_ui, 'return !existing.isKeyboard();', 'Quick Setup never erases every non-keyboard binding')
req(bind_ui, 'Skip this step', 'Quick Setup supports optional controls')
req(bind_ui, 'Keep & Fine-tune', 'Quick Setup can continue into manual calibration')
req(bind_ui, 'Save & Return to game', 'manual binding edits have an explicit persistence exit')
req(wheel_ui, 'Open Input Bindings', 'Force Feedback page links directly to input setup')
req(wheel_ui, 'Overlay::RequestBindingDialog = true;', 'FFB input shortcut uses the modal request path')
req(wheel_ui, 'Advanced FFB tuning', 'dedicated FFB page exposes advanced supported tuning')
req(wheel_ui, 'Settings::WheelFFBSpringSaturation.ptr()', 'spring saturation is reachable from FFB UI')
req(wheel_ui, 'Settings::WheelFFBWeightTransfer.ptr()', 'weight transfer is reachable from FFB UI')
req(wheel_ui, 'Settings::WheelFFBSlewRate.ptr()', 'force slew is reachable from FFB UI')
readme = read('README.md')
wheel_doc = read('WHEEL_FFB.md')
req(readme, 'Load MOZA R3 Physics SAT', 'README names current Physics preset')
req(readme, 'Save & Return to game', 'README documents durable binding exit')
forbid(readme, 'MOZA R3 v0.1 (default)', 'README has no obsolete preset button')
forbid(readme, 'Refresh connected wheels', 'README has no obsolete refresh label')
req(wheel_doc, 'Advanced FFB tuning', 'architecture doc covers reachable advanced tuning')
forbid(wheel_doc, 'MOZA R3 v0.1 (default)', 'architecture doc has no obsolete preset button')
'''
write(verifier, text.replace(anchor, guards + anchor, 1))
verify()
commit("test: guard setup UX and current wheel documentation [skip ci]", verifier)

print("10-pass FFB/setup UX review fixes applied and structurally verified")
