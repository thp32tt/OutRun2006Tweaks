from pathlib import Path
import math


def read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def require(path: str, needle: str, label: str) -> None:
    data = read(path)
    if needle not in data:
        raise SystemExit(f'ROUND11 VERIFY FAILED [{label}]: {needle!r} missing from {path}')
    print(f'ROUND11 VERIFY OK [{label}]')


def forbid(path: str, needle: str, label: str) -> None:
    data = read(path)
    if needle in data:
        raise SystemExit(f'ROUND11 VERIFY FAILED [{label}]: stale {needle!r} remains in {path}')
    print(f'ROUND11 VERIFY OK [{label}]')


require('src/hooks_wheel_ffb.cpp', '"WheelFFB", "SteeringWeight", 1.10f,', 'strong SAT default')
require('src/hooks_wheel_ffb.cpp', '"WheelFFB", "SpringStrength", 0.32f,', 'lighter generic spring')
require('src/hooks_wheel_ffb.cpp', '"WheelFFB", "DamperStrength", 0.34f,', 'damper is stabilizer')
require('src/hooks_wheel_ffb.cpp', '"WheelFFB", "SpringLoadBoost", 0.18f,', 'spring load boost reduced')
require('src/hooks_wheel_ffb.cpp', 'const float selfAligningTorque =', 'explicit SAT torque')
require('src/hooks_wheel_ffb.cpp', '(steer >= 0.0f ? -1.0f : 1.0f)', 'SAT always returns toward centre')
require('src/hooks_wheel_ffb.cpp', 'const float satSpeed = std::pow(speedNorm, 0.62f);', 'SAT speed response')
require('src/hooks_wheel_ffb.cpp', 'const float satLoadBoost = 1.0f + 0.80f * cornerLoad;', 'SAT lateral-load response')
require('src/hooks_wheel_ffb.cpp', 'const float satSlip = std::clamp((driftAmt - 0.35f) / 0.65f, 0.0f, 1.0f);', 'deep-drift onset')
require('src/hooks_wheel_ffb.cpp', 'structural = (softwareSpring + selfAligningTorque) * loadMod + damper;', 'SAT is primary structural torque')
forbid('src/hooks_wheel_ffb.cpp', 'latNorm * speedNorm *\n                static_cast<float>(Settings::WheelFFBSteeringWeight)', 'old signed lateral torque removed')
require('src/overlay/input_bindings_ui.cpp', 'MOZA R3 SAT test', 'bindings SAT preset')
require('src/overlay/input_bindings_ui.cpp', 'Self-aligning torque (SAT)', 'bindings SAT slider')
require('src/overlay/wheel_setup_ui.cpp', 'Self-aligning Torque (SAT)', 'setup SAT slider')
require('src/overlay/wheel_setup_ui.cpp', 'Settings::WheelFFBSteeringWeight = 1.10f;', 'setup SAT profile strength')

# Mirror the SAT math numerically. Strong normal-corner torque should grow with
# speed and steering angle, while a deep drift must clearly unload it.
def sat(steer: float, speed: float, corner: float, drift: float) -> float:
    steer_abs = min(abs(steer), 1.0)
    steer_for_sat = ((steer_abs - 0.012) / 0.988) ** 0.78 if steer_abs > 0.012 else 0.0
    sat_speed = speed ** 0.62
    sat_load = 1.0 + 0.80 * corner
    sat_slip = min(max((drift - 0.35) / 0.65, 0.0), 1.0)
    sat_grip = 1.0 - 0.65 * (sat_slip ** 1.35)
    return steer_for_sat * sat_speed * sat_load * sat_grip * 1.10

low_speed = sat(0.50, 0.25, 0.50, 0.10)
mid_speed = sat(0.50, 0.50, 0.50, 0.10)
high_speed = sat(0.50, 0.75, 0.50, 0.10)
small_angle = sat(0.20, 0.75, 0.50, 0.10)
large_angle = sat(0.60, 0.75, 0.50, 0.10)
deep_drift = sat(0.50, 0.75, 0.50, 1.00)

if not (0.0 < low_speed < mid_speed < high_speed):
    raise SystemExit('ROUND11 VERIFY FAILED [SAT must grow with speed]')
if not (0.0 < small_angle < large_angle):
    raise SystemExit('ROUND11 VERIFY FAILED [SAT must grow with steering angle]')
if not (deep_drift < high_speed * 0.50):
    raise SystemExit('ROUND11 VERIFY FAILED [deep drift must unload SAT strongly]')
if not (high_speed > 0.70):
    raise SystemExit('ROUND11 VERIFY FAILED [normal high-speed SAT is too weak]')

# Approximate final normalized structural output at a representative loaded
# 75%-speed / 50%-steer corner. The tanh/overall path should still deliver a
# clearly strong DD-wheel command without reaching the hard limit.
speed = 0.75
steer = 0.50
corner = 0.50
drift = 0.10
low_spring = 0.08
spring_curve = low_spring + (1.0 - low_spring) * (speed ** 1.60)
spring_strength = 0.32 * spring_curve * (1.0 + corner * 0.18) * (1.0 - 0.65 * drift)
structural = high_speed + steer * spring_strength
output = math.tanh(structural * 0.70)
if not (0.50 < output < 0.80):
    raise SystemExit(f'ROUND11 VERIFY FAILED [representative output] got {output:.4f}')
print(f'ROUND11 numeric SAT: low={low_speed:.4f} mid={mid_speed:.4f} high={high_speed:.4f} deep-drift={deep_drift:.4f} output={output:.4f}')

for path in ['src/hooks_wheel_ffb.cpp', 'src/overlay/input_bindings_ui.cpp', 'src/overlay/wheel_setup_ui.cpp']:
    data = read(path)
    if data.count('{') != data.count('}'):
        raise SystemExit(f'ROUND11 VERIFY FAILED [brace balance]: {path}')
    print(f'ROUND11 VERIFY OK [brace balance {path}]')

print('Round-11 strong pseudo-SAT verification passed')
