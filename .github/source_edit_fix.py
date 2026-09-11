from pathlib import Path
import re


def replace_if_present(path, old, new):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if old in s:
        p.write_text(s.replace(old, new, 1), encoding='utf-8')


# Two small guards may already have been applied manually before the source-only
# workflow runs. Put them back into the script's expected pre-image so the main
# transformation remains deterministic and applies the stronger final gates.
replace_if_present(
    'src/hooks_wheel_input_compat_v2.hpp',
    '            return Settings::WheelInputCompatibility && !Settings::UseNewInput;\n',
    '            return Settings::WheelInputCompatibility;\n')
replace_if_present(
    'src/hooks_wheel_r3_menu_ab.hpp',
    '            return Settings::WheelInputCompatibility && !Settings::UseNewInput;\n',
    '            return Settings::WheelInputCompatibility;\n')

# This wording-only replacement is optional and varied across revisions. Remove
# it from the main script rather than allowing harmless text drift to abort the
# source transformation.
p = Path('.github/source_edit.py')
s = p.read_text(encoding='utf-8')
pattern = r'''replace_once\(\n    'src/overlay/wheel_setup_ui\.cpp',\n    '                \\"Settings > WheelFFB is hidden; changes on this page apply live\. SDL gamepad rumble is suppressed while wheel FFB is enabled\.\\"\);',\n    '                \\"Settings > WheelFFB is hidden; changes on this page apply live\. SDL gamepad rumble is suppressed only while DirectInput FFB owns an output device\.\\"\);'\)\n'''
out, count = re.subn(pattern, '', s, count=1)
if count != 1:
    start = s.find("replace_once(\n    'src/overlay/wheel_setup_ui.cpp',\n    '                \\\"Settings > WheelFFB is hidden;")
    if start >= 0:
        end = s.find("\n\n# 3) Binding identity", start)
        if end < 0:
            raise SystemExit('could not locate end of optional UI wording replacement')
        out = s[:start] + s[end + 2:]
    else:
        out = s
p.write_text(out, encoding='utf-8')
