from pathlib import Path

p = Path('tools/apply_dx9ex_compat_review.py')
text = p.read_text(encoding='utf-8')
old = "replace(p, '                ++R32DirectFenceSuccess;\\n                return true;', '                if (Settings::VRTelemetry) ++R32DirectFenceSuccess;\\n                return true;', 2)"
new = "replace(p, '                ++R32DirectFenceSuccess;\\n                return true;', '                if (Settings::VRTelemetry) ++R32DirectFenceSuccess;\\n                return true;')\nreplace(p, '                    ++R32DirectFenceSuccess;\\n                    return true;', '                    if (Settings::VRTelemetry) ++R32DirectFenceSuccess;\\n                    return true;')"
if old not in text:
    raise SystemExit('R32 DirectFenceSuccess matcher line not found')
p.write_text(text.replace(old, new, 1), encoding='utf-8')
print('DX9Ex patch matcher fixed')
