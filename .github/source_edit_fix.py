from pathlib import Path


def replace_if_present(path, old, new):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if old in s:
        p.write_text(s.replace(old, new, 1), encoding='utf-8')


# Normalize small guards that may already have landed so the main script can
# apply its complete final gate deterministically.
for path in ('src/hooks_wheel_input_compat_v2.hpp', 'src/hooks_wheel_r3_menu_ab.hpp'):
    replace_if_present(
        path,
        '            return Settings::WheelInputCompatibility && !Settings::UseNewInput;\n',
        '            return Settings::WheelInputCompatibility;\n')

# Wording-only UI text is not part of the functional refactor. Remove that
# replacement block from the one-shot main script regardless of source wording.
p = Path('.github/source_edit.py')
s = p.read_text(encoding='utf-8')
marker = 'SDL gamepad rumble is suppressed while wheel FFB is enabled.'
idx = s.find(marker)
if idx >= 0:
    start = s.rfind('replace_once(', 0, idx)
    end_marker = '\n\n# 3) Binding identity'
    end = s.find(end_marker, idx)
    if start < 0 or end < 0:
        raise SystemExit('could not isolate optional rumble wording replacement block')
    s = s[:start] + s[end + 2:]
p.write_text(s, encoding='utf-8')
