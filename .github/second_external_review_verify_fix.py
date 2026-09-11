from pathlib import Path

p = Path('tools/verify_wheel_ffb_current.py')
text = p.read_text(encoding='utf-8')
replacements = {
    "req(ffb, 'WheelFFBMath::pneumatic_sat_shape(frontSlip)', 'production pneumatic SAT curve shared with compiled tests')":
        "req(ffb, 'WheelFFBMath::pneumatic_sat_shape(frontSlip, trailResponseSlip)', 'production pneumatic SAT curve separates force and trail transients')",
    "req(ffb, 'WheelFFBMath::combined_sat_shape(frontSlip, mechanicalTrailMix)', 'Physics SAT combines pneumatic and mechanical trail')":
        "req(ffb, 'WheelFFBMath::combined_sat_shape(\\n                frontSlip, trailResponseSlip, mechanicalTrailMix)', 'Physics SAT combines pneumatic and mechanical total trail')",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f'expected one verifier match, found {text.count(old)}: {old}')
    text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8', newline='\n')
print('aligned legacy SAT verifier strings with split force/trail inputs')
