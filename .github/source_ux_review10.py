from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools/verify_wheel_ffb_current.py"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected exactly one match, got {count}: {old[:140]!r}")
    write(rel, text.replace(old, new, 1))


def verify():
    subprocess.run(["python3", str(VERIFY)], cwd=ROOT, check=True)


def commit(message, *paths):
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        raise SystemExit(f"no changes staged for {message}")
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)


bind_ui = "src/overlay/input_bindings_ui.cpp"
wheel_ui = "src/overlay/wheel_setup_ui.cpp"
verifier = "tools/verify_wheel_ffb_current.py"

# Back/B must not bypass the explicit save-vs-discard controls introduced for
# unsaved mappings.
replace_once(
    bind_ui,
    '''\t\t\tif (isListeningForInput == ListenState::False)
\t\t\t{
\t\t\t\tif ((manager.switch_overlay & (1 << int(SwitchId::Back) | 1 << int(SwitchId::B))) != 0)
\t\t\t\t\tdialogOpen = false;
\t\t\t}''',
    '''\t\t\tif (isListeningForInput == ListenState::False && !unsavedChanges)
\t\t\t{
\t\t\t\tif ((manager.switch_overlay & (1 << int(SwitchId::Back) | 1 << int(SwitchId::B))) != 0)
\t\t\t\t\tdialogOpen = false;
\t\t\t}''')

# Diagnostics belong on their own row after the collapsing advanced section
# rather than being attached to its header.
replace_once(
    wheel_ui,
    '''            }

            ImGui::SameLine();
            ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());''',
    '''            }

            ImGui::Checkbox("Diagnostic logging", Settings::WheelFFBDebugLog.ptr());''')

text = read(verifier)
anchor = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')\n"
if text.count(anchor) != 1:
    raise SystemExit("verifier final print anchor missing or duplicated")
guards = '''req(bind_ui, 'if (isListeningForInput == ListenState::False && !unsavedChanges)', 'Back/B cannot bypass unsaved binding persistence choice')
forbid(wheel_ui, '}\\n\\n            ImGui::SameLine();\\n            ImGui::Checkbox("Diagnostic logging"', 'advanced FFB header does not share a line with diagnostics')
'''
write(verifier, text.replace(anchor, guards + anchor, 1))

verify()
commit("ux: close setup persistence and layout gaps [skip ci]", bind_ui, wheel_ui, verifier)
print("setup UX post-review corrections verified")
