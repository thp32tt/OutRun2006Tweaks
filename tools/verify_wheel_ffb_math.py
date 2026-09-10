from pathlib import Path
import math

src = Path("src/hooks_wheel_ffb.cpp").read_text(encoding="utf-8")
natural = "const float satAngleInput =" in src

# Keep this numeric audit tied to the actual formulas compiled by the wheel
# branch. If the C++ formula changes, this verifier must be intentionally
# updated rather than silently testing an obsolete model.
common_fragments = [
    "dampingSpeed =",
    "0.10f + 0.90f * std::pow(speedNorm, 1.30f)",
    "0.25f + 0.75f * gripFactor",
    "std::clamp((roughness - 0.30f) / 0.55f, 0.0f, 1.0f)",
    "std::tanh(total)",
]
for fragment in common_fragments:
    if fragment not in src:
        raise SystemExit(f"MATH VERIFY FAILED: C++ formula fragment missing: {fragment}")


def smoothstep(v: float) -> float:
    v = max(0.0, min(1.0, v))
    return v * v * (3.0 - 2.0 * v)


def damper(speed: float, grip: float, strength: float = 0.35) -> float:
    damping_speed = 0.10 + 0.90 * speed ** 1.30
    damping_grip = 0.25 + 0.75 * grip
    return max(0.0, min(1.0, strength * damping_speed * damping_grip))


def texture(roughness: float) -> float:
    return max(0.0, min(1.0, (roughness - 0.30) / 0.55))


if natural:
    required = [
        "const float springFadeT =",
        "const float springSpeed = 1.0f - 0.88f * springFade;",
        "std::sin(satAngleInput * HalfPi)",
        "const float satMotionGate =",
        "const float satReturnRelief = 1.0f - 0.45f * returnRateSmooth;",
    ]
    for fragment in required:
        if fragment not in src:
            raise SystemExit(f"MATH VERIFY FAILED: natural C++ fragment missing: {fragment}")

    def spring(speed: float, grip: float = 1.0, strength: float = 0.65) -> float:
        fade = smoothstep((speed - 0.05) / 0.35)
        spring_speed = 1.0 - 0.88 * fade
        spring_grip = 0.80 + 0.20 * grip
        return max(0.0, min(1.0, strength * spring_speed * spring_grip))

    def sat(steer: float, speed: float, corner: float, drift: float,
            steer_rate: float = 0.0, strength: float = 1.75,
            grip_loss: float = 0.65) -> float:
        steer_abs = max(0.0, min(1.0, abs(steer)))
        angle_input = max(0.0, min(1.0, (steer_abs - 0.025) / 0.975))
        steer_curve = math.sin(angle_input * math.pi / 2.0)
        motion = smoothstep((speed - 0.015) / 0.085)
        speed_curve = motion * (0.20 + 0.80 * math.sqrt(max(speed, 0.0)))
        load_curve = 0.72 + 0.38 * smoothstep(max(0.0, min(1.0, corner)))
        slip = smoothstep((drift - 0.60) / 0.35)
        grip = 1.0 - 0.65 * grip_loss * slip
        returning = steer * steer_rate < 0.0
        return_t = min(abs(steer_rate) / 0.08, 1.0) if returning else 0.0
        relief = 1.0 - 0.45 * smoothstep(return_t)
        return steer_curve * speed_curve * load_curve * grip * relief * strength

    speeds = [i / 100.0 for i in range(101)]
    springs = [spring(s) for s in speeds]
    if not springs[0] > springs[20] > springs[50] > 0.0:
        raise SystemExit("MATH VERIFY FAILED: natural spring must fade with speed")
    if not springs[50] < springs[0] * 0.15:
        raise SystemExit("MATH VERIFY FAILED: high-speed spring still stacks too strongly with SAT")

    tiny = sat(0.05, 0.50, 0.30, 0.0)
    small = sat(0.10, 0.50, 0.30, 0.0)
    mid = sat(0.30, 0.50, 0.50, 0.0)
    high = sat(0.50, 0.75, 0.70, 0.0)
    deep = sat(0.50, 0.75, 0.70, 1.0)
    returning = sat(0.30, 0.50, 0.50, 0.0, -0.08)
    if not (0.0 < tiny < small < mid < high):
        raise SystemExit("MATH VERIFY FAILED: natural SAT is not progressive with steering/load")
    if not tiny < mid * 0.10:
        raise SystemExit("MATH VERIFY FAILED: tiny steering still produces an SAT snap")
    if not 0.50 < deep / high < 0.80:
        raise SystemExit("MATH VERIFY FAILED: deep slide SAT unload is implausible")
    if not returning < mid * 0.65:
        raise SystemExit("MATH VERIFY FAILED: fast self-centering return is not sufficiently relieved")

    print("Wheel FFB natural SAT numeric invariants passed")
    print(f"spring: park={springs[0]:.4f}, 20%={springs[20]:.4f}, 50%={springs[50]:.4f}")
    print(f"SAT raw: tiny={tiny:.4f}, small={small:.4f}, mid={mid:.4f}, high={high:.4f}, deep={deep:.4f}, fast-return={returning:.4f}")
else:
    required_fragments = [
        "std::pow(speedNorm, 1.60f)",
        "cornerLoad * static_cast<float>(Settings::WheelFFBSpringLoadBoost)",
    ]
    for fragment in required_fragments:
        if fragment not in src:
            raise SystemExit(f"MATH VERIFY FAILED: legacy C++ formula fragment missing: {fragment}")

    def speed_curve(speed: float, low_speed: float = 0.08) -> float:
        return max(0.0, min(1.0, low_speed + (1.0 - low_speed) * speed ** 1.60))

    def spring(speed: float, lat: float, grip: float,
               strength: float = 0.45, low_speed: float = 0.08,
               load_boost_setting: float = 0.35) -> float:
        curve = speed_curve(speed, low_speed)
        corner_load = max(0.0, min(1.0, abs(lat)))
        boost = 1.0 + corner_load * load_boost_setting
        return max(0.0, min(1.0, strength * curve * boost * grip))

    speeds = [i / 100.0 for i in range(101)]
    curves = [speed_curve(s) for s in speeds]
    if any(b + 1e-9 < a for a, b in zip(curves, curves[1:])):
        raise SystemExit("MATH VERIFY FAILED: aligning speed curve is not monotonic")
    springs = [spring(s, lat=0.5, grip=1.0) for s in speeds]
    if any(b + 1e-9 < a for a, b in zip(springs, springs[1:])):
        raise SystemExit("MATH VERIFY FAILED: spring output decreases with speed at fixed grip")

# Dynamic damper still grows with speed and relaxes with grip loss.
if not (damper(1.0, 1.0) > damper(0.0, 1.0) > 0.0):
    raise SystemExit("MATH VERIFY FAILED: damper speed scaling is invalid")
if not (damper(1.0, 0.35) < damper(1.0, 1.0)):
    raise SystemExit("MATH VERIFY FAILED: drift does not relax damper")

# Normal asphalt baseline (~0.25) must not create constant road buzz.
for r in (0.0, 0.10, 0.25, 0.30):
    if texture(r) != 0.0:
        raise SystemExit(f"MATH VERIFY FAILED: asphalt roughness {r} produces vibration")
if not (0.0 < texture(0.50) < texture(0.85) <= 1.0):
    raise SystemExit("MATH VERIFY FAILED: rough-surface texture ramp is invalid")

# 270-degree R3 sanity: 20% would be +/-27 degrees; the branch default is 0%.
rotation = 270.0
half_rotation = rotation / 2.0
angle_by_percent = {p: half_rotation * p / 100.0 for p in (0, 1, 2, 5, 20)}
if abs(angle_by_percent[20] - 27.0) > 1e-9:
    raise SystemExit("MATH VERIFY FAILED: 270-degree deadzone sanity check")

print(f"damper: stopped={damper(0.0, 1.0):.4f}, high-speed={damper(1.0, 1.0):.4f}, drift={damper(1.0, 0.35):.4f}")
print("270deg center deadzone half-angle:", ", ".join(f"{p}%={a:.2f}deg" for p, a in angle_by_percent.items()))
