from pathlib import Path

p = Path('tools/verify_wheel_ffb_current.py')
s = p.read_text(encoding='utf-8')
repls = {
    "req(readme, 'Load MOZA R3 Physics SAT', 'README names current Physics preset')":
        "req(readme, 'Load Universal Physics SAT', 'README names current universal Physics preset')",
    "req(release_notes, 'Load MOZA R3 Physics SAT', 'release notes name the current Physics preset')":
        "req(release_notes, 'Load Universal Physics SAT', 'release notes name the current universal Physics preset')",
}
for old, new in repls.items():
    if s.count(old) != 1:
        raise SystemExit(f'expected exactly one verifier guard: {old}')
    s = s.replace(old, new, 1)

# The shipped docs should explicitly explain the new opt-in engine haptic behavior.
anchor = "req(release_notes, 'Save Force Feedback', 'release notes explain FFB persistence')"
if anchor not in s:
    raise SystemExit('release notes persistence guard missing')
extra = "\n".join([
    anchor,
    "req(readme, 'Engine Vibration', 'README documents optional engine vibration')",
    "req(readme, 'OFF by default', 'README documents engine vibration default off')",
    "req(release_notes, 'Engine Vibration', 'release notes document optional engine vibration')",
    "req(release_notes, '기본 OFF', 'Korean release notes document engine vibration default off')",
])
s = s.replace(anchor, extra, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('verifier documentation guards updated')
