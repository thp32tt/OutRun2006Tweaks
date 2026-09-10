from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def require(path: str, needle: str, label: str) -> None:
    data = read(path)
    if needle not in data:
        raise SystemExit(f'ROUND12 VERIFY FAILED [{label}]: {needle!r} missing from {path}')
    print(f'ROUND12 VERIFY OK [{label}]')


def forbid(path: str, needle: str, label: str) -> None:
    data = read(path)
    if needle in data:
        raise SystemExit(f'ROUND12 VERIFY FAILED [{label}]: stale {needle!r} remains in {path}')
    print(f'ROUND12 VERIFY OK [{label}]')


# SAT must consume the SDL multi-device steering state directly when UseNewInput
# is active, while retaining the legacy game-function route as fallback.
require('src/hooks_wheel_ffb.cpp', 'extern float InputManager_SteeringValue();', 'direct SDL steering export declared')
require('src/hooks_wheel_ffb.cpp', 'if (Settings::UseNewInput)\n            {\n                const float steering = InputManager_SteeringValue();', 'new input SAT uses direct steering')
require('src/hooks_wheel_ffb.cpp', 'auto getVolume = Module::fn_ptr<GetVolumeFn>(0x53720);', 'legacy steering fallback retained')
require('src/hooks_wheel_ffb.cpp', 'sat={:.3f} steerSrc={}', 'diagnostic logs SAT and source')
require('src/hooks_wheel_ffb.cpp', 'Settings::UseNewInput ? "SDL" : "legacy"', 'diagnostic source selector')

# The Controls dialog should no longer expose a second FFB tuning page.
forbid('src/overlay/input_bindings_ui.cpp', 'ImGui::BeginTabItem("Force Feedback")', 'duplicate Controls FFB tab removed')

# In the normal SDL3 path, the main shell page is unambiguously FFB-only and
# legacy input mapping/options are gated away. Compatibility mode keeps them.
require('src/overlay/wheel_setup_ui.cpp', 'return Settings::UseNewInput ? "Force Feedback" : "Legacy Wheel Setup";', 'main tab has clear role')
require('src/overlay/wheel_setup_ui.cpp', '"Force feedback only. Configure steering, pedals, buttons and calibration in the game Controls / Controller Setup screen.', 'SDL navigation guidance')
require('src/overlay/wheel_setup_ui.cpp', 'if (!Settings::UseNewInput)\n            {\n            const int regularSlots', 'legacy mapper gated')
require('src/overlay/wheel_setup_ui.cpp', 'if (!Settings::UseNewInput)\n            {\n            ImGui::SeparatorText("Wheel options")', 'legacy wheel options gated')
require('src/overlay/wheel_setup_ui.cpp', 'Settings::write(Module::UserIniPath);', 'FFB device selection persists')
require('src/overlay/wheel_setup_ui.cpp', 'Settings::WheelFFBEnable = true;', 'SAT preset recovers disabled FFB')
require('src/overlay/wheel_setup_ui.cpp', '"Input setup: game Controls / Controller Setup. FFB setup: this page only.', 'single navigation summary')

# Round11 SAT still must be present and strong after the routing/UI repair.
require('src/hooks_wheel_ffb.cpp', 'const float selfAligningTorque =', 'SAT model retained')
require('src/hooks_wheel_ffb.cpp', 'structural = (softwareSpring + selfAligningTorque) * loadMod + damper;', 'SAT output retained')
require('src/overlay/wheel_setup_ui.cpp', 'Load MOZA R3 SAT test', 'SAT test preset retained')
require('src/overlay/wheel_setup_ui.cpp', 'Settings::WheelFFBSteeringWeight = 1.10f;', 'strong SAT setting retained')

for path in ['src/hooks_wheel_ffb.cpp', 'src/overlay/input_bindings_ui.cpp', 'src/overlay/wheel_setup_ui.cpp']:
    data = read(path)
    if data.count('{') != data.count('}'):
        raise SystemExit(f'ROUND12 VERIFY FAILED [brace balance]: {path}')
    print(f'ROUND12 VERIFY OK [brace balance {path}]')

print('Round-12 SAT steering-source and UI consolidation verification passed')
