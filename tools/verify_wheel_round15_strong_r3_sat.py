from pathlib import Path
import math

ffb = Path('src/hooks_wheel_ffb.cpp').read_text(encoding='utf-8')
ui = Path('src/overlay/wheel_setup_ui.cpp').read_text(encoding='utf-8')


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f'ROUND15 VERIFY FAILED [{label}]: {needle!r}')
    print(f'ROUND15 VERIFY OK [{label}]')


require(ffb, '"WheelFFB", "SpringStrength", 0.65f,', 'strong spring default')
require(ffb, '"WheelFFB", "LowSpeedSpring", 0.20f,', 'low-speed centering default')
require(ffb, '"WheelFFB", "SpringLoadBoost", 0.30f,', 'spring load boost')
require(ffb, '"WheelFFB", "SteeringWeight", 1.45f,', 'strong SAT default')
require(ffb, 'Range<float>{ 0.0f, 2.0f }', 'SAT setting headroom')
require(ffb, '"WheelFFB", "InvertForce", true,', 'R3 ConstantForce direction corrected')
require(ffb, 'std::pow((steerAbs - 0.012f) / 0.988f, 0.58f)', 'moderate steering SAT response')
require(ffb, 'const float satSpeed = std::pow(speedNorm, 0.50f);', 'normal-speed SAT response')
require(ffb, 'const float satLoadBoost = 1.0f + 1.10f * cornerLoad;', 'strong corner-load SAT')
require(ffb, 'const float satSlip = std::clamp((driftAmt - 0.45f) / 0.55f, 0.0f, 1.0f);', 'later grip-loss unload')
require(ui, 'Reverse SAT / ConstantForce', 'clear SAT direction UI')
require(ui, 'Load MOZA R3 Strong SAT', 'strong R3 preset visible')
require(ui, 'Settings::WheelFFBInvertForce = true;', 'preset fixes SAT direction')
require(ui, 'Settings::WheelFFBInvertSpring = false;', 'preset keeps known-good R3 spring sign')
require(ui, 'Settings::write(Module::UserIniPath);', 'preset persists over stale user.ini')

# Numeric sanity: ordinary corners must now generate clearly visible SAT while
# a deep drift must still unload it. These are pre-tanh structural samples with
# the shipped 0.70 master gain applied for the output comparison.
def sat(steer: float, speed: float, corner: float, drift: float) -> tuple[float, float]:
    steer_abs = max(0.0, min(1.0, abs(steer)))
    steer_for_sat = ((steer_abs - 0.012) / 0.988) ** 0.58 if steer_abs > 0.012 else 0.0
    sat_speed = speed ** 0.50
    sat_load = 1.0 + 1.10 * corner
    sat_slip = max(0.0, min(1.0, (drift - 0.45) / 0.55))
    sat_grip = 1.0 - 0.65 * (sat_slip ** 1.35)
    raw = steer_for_sat * sat_speed * sat_load * sat_grip * 1.45
    return raw, math.tanh(raw * 0.70)

low_raw, low_out = sat(0.20, 0.25, 0.30, 0.0)
mid_raw, mid_out = sat(0.30, 0.50, 0.50, 0.0)
high_raw, high_out = sat(0.50, 0.75, 0.70, 0.0)
_, drift_out = sat(0.50, 0.75, 0.70, 1.0)
if not (low_out > 0.20 and mid_out > 0.45 and high_out > 0.70):
    raise SystemExit(f'ROUND15 VERIFY FAILED [SAT strength]: low={low_out:.3f} mid={mid_out:.3f} high={high_out:.3f}')
if not drift_out < high_out * 0.55:
    raise SystemExit(f'ROUND15 VERIFY FAILED [deep-drift unload]: high={high_out:.3f} drift={drift_out:.3f}')
print(f'ROUND15 VERIFY OK [SAT numeric]: low={low_out:.3f} mid={mid_out:.3f} high={high_out:.3f} drift={drift_out:.3f}')

# Hardware spring coefficient after master gain: it should no longer be near
# zero at normal speeds, but should remain below full saturation.
def spring_coeff(speed: float, corner: float = 0.5) -> float:
    speed_curve = 0.20 + 0.80 * (speed ** 1.60)
    return 0.65 * speed_curve * (1.0 + 0.30 * corner) * 0.70

stopped = spring_coeff(0.0)
mid = spring_coeff(0.5)
high = spring_coeff(0.75)
if not (stopped > 0.09 and mid > 0.22 and high > 0.34):
    raise SystemExit(f'ROUND15 VERIFY FAILED [spring strength]: stop={stopped:.3f} mid={mid:.3f} high={high:.3f}')
print(f'ROUND15 VERIFY OK [spring numeric]: stop={stopped:.3f} mid={mid:.3f} high={high:.3f}')

for path in ['src/hooks_wheel_ffb.cpp', 'src/overlay/wheel_setup_ui.cpp']:
    data = Path(path).read_text(encoding='utf-8')
    if data.count('{') != data.count('}'):
        raise SystemExit(f'ROUND15 VERIFY FAILED [brace balance]: {path}')
    print(f'ROUND15 VERIFY OK [brace balance {path}]')

print('Round-15 strong MOZA R3 SAT/centering verification passed')
