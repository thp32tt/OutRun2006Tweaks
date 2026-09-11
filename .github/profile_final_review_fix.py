from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected one match, found {count}: {old[:120]!r}")
    write(rel, text.replace(old, new, 1))


# Keep cached existence checks for rendering, but re-check the filesystem only
# when Save is actually clicked. This preserves a cheap UI loop while ensuring
# an externally-created same-name profile can never be overwritten without the
# existing two-click confirmation.
replace_once(
    "src/overlay/input_bindings_ui.cpp",
    '''\t\tif (ImGui::Button(saveLabel))\n\t\t{\n\t\t\tstd::string error;\n\t\t\tif (profileAlreadyExists && !confirmingProfileOverwrite)''',
    '''\t\tif (ImGui::Button(saveLabel))\n\t\t{\n\t\t\tstd::string error;\n\t\t\tconst bool existsOnDisk = !requestedName.empty() &&\n\t\t\t\tWheelProfileStore::profile_exists(WheelProfileStore::Kind::Input, requestedName);\n\t\t\tif (existsOnDisk && !confirmingProfileOverwrite)''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            if (ImGui::Button(saveLabel))\n            {\n                if (exists && !confirmingFfbOverwrite_)''',
    '''            if (ImGui::Button(saveLabel))\n            {\n                const bool existsOnDisk = !requested.empty() &&\n                    WheelProfileStore::profile_exists(WheelProfileStore::Kind::ForceFeedback, requested);\n                if (existsOnDisk && !confirmingFfbOverwrite_)''')

verify = read("tools/verify_wheel_ffb_current.py")
marker = "req(bind_ui, 'wheel_profile_exists_cached', 'input profile overwrite check uses cached list')\n"
if marker not in verify:
    raise SystemExit("input profile verifier marker missing")
verify = verify.replace(
    marker,
    marker + "req(bind_ui, 'WheelProfileStore::profile_exists(WheelProfileStore::Kind::Input, requestedName)', 'input profile rechecks overwrite on save click')\n",
    1)
marker = "req(wheel_ui, 'ffb_profile_exists_cached', 'FFB profile overwrite check uses cached list')\n"
if marker not in verify:
    raise SystemExit("FFB profile verifier marker missing")
verify = verify.replace(
    marker,
    marker + "req(wheel_ui, 'WheelProfileStore::profile_exists(WheelProfileStore::Kind::ForceFeedback, requested)', 'FFB profile rechecks overwrite on save click')\n",
    1)
write("tools/verify_wheel_ffb_current.py", verify)

subprocess.run(["python", "tools/verify_wheel_ffb_current.py"], cwd=ROOT, check=True)
subprocess.run(["git", "add", "src/overlay/input_bindings_ui.cpp", "src/overlay/wheel_setup_ui.cpp", "tools/verify_wheel_ffb_current.py"], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "fix: confirm profile overwrite against live filesystem [skip ci]"], cwd=ROOT, check=True)
