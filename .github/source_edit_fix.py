from pathlib import Path
import re

p = Path('.github/source_edit.py')
s = p.read_text(encoding='utf-8')
pattern = r'''replace_once\(\n    'src/overlay/wheel_setup_ui\.cpp',\n    '                \\"Settings > WheelFFB is hidden; changes on this page apply live\. SDL gamepad rumble is suppressed while wheel FFB is enabled\.\\"\);',\n    '                \\"Settings > WheelFFB is hidden; changes on this page apply live\. SDL gamepad rumble is suppressed only while DirectInput FFB owns an output device\.\\"\);'\)\n'''
out, count = re.subn(pattern, '', s, count=1)
if count != 1:
    # The wording-only replacement is optional; if formatting differs, just
    # remove the four-line replace_once block by locating its unique phrase.
    start = s.find("replace_once(\n    'src/overlay/wheel_setup_ui.cpp',\n    '                \\\"Settings > WheelFFB is hidden;")
    if start >= 0:
        end = s.find("\n\n# 3) Binding identity", start)
        if end < 0:
            raise SystemExit('could not locate end of optional UI wording replacement')
        out = s[:start] + s[end + 2:]
    else:
        out = s
p.write_text(out, encoding='utf-8')
