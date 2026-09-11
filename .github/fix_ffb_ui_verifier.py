from pathlib import Path

p = Path('tools/verify_wheel_ffb_current.py')
text = p.read_text(encoding='utf-8')
old = "req(ffb, 'if (std::abs(prevStructuralLevel_) <= releaseMaxSlew)\\n                    structuralLevel = 0;', 'sign reversal unloads old torque to zero before rebuilding')"
new = "req(ffb, 'if (std::abs(prevStructuralLevel_) <= reversalReleaseMaxSlew)\\n                    structuralLevel = 0;', 'sign reversal unloads old torque to zero before rebuilding')"
if old not in text:
    raise SystemExit('old sign-reversal verifier guard not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8', newline='\n')
print('updated verifier for dedicated reversal release rate')
