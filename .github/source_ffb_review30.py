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
        raise SystemExit(f"{rel}: expected exactly one match, got {count}: {old[:120]!r}")
    write(rel, text.replace(old, new, 1))


def replace_n(rel, old, new, expected):
    text = read(rel)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{rel}: expected {expected} matches, got {count}: {old[:120]!r}")
    write(rel, text.replace(old, new))


def verify():
    subprocess.run(["python3", str(VERIFY)], cwd=ROOT, check=True)


def commit(message, *paths):
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        raise SystemExit(f"no changes staged for {message}")
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)


ffb = "src/hooks_wheel_ffb.cpp"
verifier = "tools/verify_wheel_ffb_current.py"

# Review finding 1: foreground recovery must not depend on WM_ACTIVATEAPP being
# delivered after we have already detected focus loss ourselves.
replace_once(
    ffb,
    """            // Safety first for a DD base: WM_ACTIVATEAPP releases exclusive\n"
    "            // ownership when the game loses focus. Do not let the 60 Hz update\n"
    "            // loop immediately reacquire it while another application is active.\n"
    "            if (!appActive_)\n"
    "            {\n"
    "                // initialize() can set appActive_=false before the window\n"
    "                // subclass exists. Recover from that startup/background case\n"
    "                // only after the real game window is foreground again.\n"
    "                if (!initialized_ && gameHwnd_ && GetForegroundWindow() == gameHwnd_)\n"
    "                {\n"
    "                    appActive_ = true;\n"
    "                    warmupFrames_ = 0;\n"
    "                }\n"
    "                else\n"
    "                {\n"
    "                    if (initialized_)\n"
    "                    {\n"
    "                        zero_all_forces();\n"
    "                        reset_signal_state();\n"
    "                    }\n"
    "                    return;\n"
    "                }\n"
    "            }\n""",
    """            // Safety first for a DD base: WM_ACTIVATEAPP releases exclusive\n"
    "            // ownership when the game loses focus. The foreground window is also\n"
    "            // authoritative on recovery so a missed activation message cannot\n"
    "            // leave FFB permanently dormant after Alt-Tab.\n"
    "            if (!appActive_)\n"
    "            {\n"
    "                if (gameHwnd_ && GetForegroundWindow() == gameHwnd_)\n"
    "                {\n"
    "                    appActive_ = true;\n"
    "                    warmupFrames_ = 0;\n"
    "                }\n"
    "                else\n"
    "                {\n"
    "                    if (initialized_)\n"
    "                    {\n"
    "                        zero_all_forces();\n"
    "                        reset_signal_state();\n"
    "                    }\n"
    "                    return;\n"
    "                }\n"
    "            }\n""",
)
verify()
commit("fix: recover wheel FFB after missed focus activation [skip ci]", ffb)

# Review finding 2: update_spring/update_damper may release their own effect on
# failure. The live-disable caller must re-check the pointer before Stop().
replace_once(
    ffb,
    """            if (!Settings::WheelFFBUseHardwareSpring && springEffect_)\n"
    "            {\n"
    "                update_spring(0.0f);\n"
    "                springEffect_->Stop();\n"
    "                safe_release_effect(springEffect_, \"hardware spring disabled\");\n""",
    """            if (!Settings::WheelFFBUseHardwareSpring && springEffect_)\n"
    "            {\n"
    "                update_spring(0.0f);\n"
    "                if (springEffect_)\n"
    "                    springEffect_->Stop();\n"
    "                safe_release_effect(springEffect_, \"hardware spring disabled\");\n""",
)
replace_once(
    ffb,
    """            if (!Settings::WheelFFBUseHardwareDamper && damperEffect_)\n"
    "            {\n"
    "                update_damper(0.0f);\n"
    "                damperEffect_->Stop();\n"
    "                safe_release_effect(damperEffect_, \"hardware damper disabled\");\n""",
    """            if (!Settings::WheelFFBUseHardwareDamper && damperEffect_)\n"
    "            {\n"
    "                update_damper(0.0f);\n"
    "                if (damperEffect_)\n"
    "                    damperEffect_->Stop();\n"
    "                safe_release_effect(damperEffect_, \"hardware damper disabled\");\n""",
)
verify()
commit("fix: make live condition-effect disable null-safe [skip ci]", ffb)

# Review finding 3: optional road/tire sine failures must never delay recovery of
# the critical steering ConstantForce effect. Give the two recovery paths
# independent holdoff deadlines.
text = read(ffb)
if text.count("recreateHoldoffUntil_") != 7:
    raise SystemExit(f"unexpected shared recreate holdoff occurrence count: {text.count('recreateHoldoffUntil_')}")
replace_once(
    ffb,
    "        DWORD recreateHoldoffUntil_ = 0;\n",
    "        DWORD constantRecreateHoldoffUntil_ = 0;\n"
    "        DWORD periodicRecreateHoldoffUntil_ = 0;\n",
)
replace_once(
    ffb,
    "            recreateHoldoffUntil_ = 0;\n            springRecreateHoldoffUntil_ = 0;\n",
    "            constantRecreateHoldoffUntil_ = 0;\n"
    "            periodicRecreateHoldoffUntil_ = 0;\n"
    "            springRecreateHoldoffUntil_ = 0;\n",
)
replace_once(
    ffb,
    "                tick_reached(GetTickCount(), recreateHoldoffUntil_))\n",
    "                tick_reached(GetTickCount(), periodicRecreateHoldoffUntil_))\n",
)
replace_n(
    ffb,
    "                recreateHoldoffUntil_ = GetTickCount() + 500;\n",
    "                periodicRecreateHoldoffUntil_ = GetTickCount() + 500;\n",
    2,
)
replace_once(
    ffb,
    "                if (tick_before(now, recreateHoldoffUntil_))\n",
    "                if (tick_before(now, constantRecreateHoldoffUntil_))\n",
)
replace_once(
    ffb,
    "                    recreateHoldoffUntil_ = now + 500;\n",
    "                    constantRecreateHoldoffUntil_ = now + 500;\n",
)
if "recreateHoldoffUntil_" in read(ffb):
    raise SystemExit("shared recreate holdoff name still present")
verify()
commit("fix: isolate steering and periodic effect recovery [skip ci]", ffb)

# Review finding 4: every newly created ConstantForce starts at magnitude zero,
# so the software cache must also start at zero. Otherwise a full device reinit
# can inherit a stale accepted level and defer the first write to the new effect.
replace_once(
    ffb,
    """                    constantEffectPolar_ = true;\n"
    "                    spdlog::info(\"WheelFFB: ConstantForce created with 2-axis POLAR actuator encoding\");\n""",
    """                    constantEffectPolar_ = true;\n"
    "                    prevConstantLevel_ = 0;\n"
    "                    lastConstantWriteTick_ = 0;\n"
    "                    spdlog::info(\"WheelFFB: ConstantForce created with 2-axis POLAR actuator encoding\");\n""",
)
replace_once(
    ffb,
    """            constantEffectPolar_ = false;\n"
    "            spdlog::info(\"WheelFFB: ConstantForce created with 1-axis CARTESIAN fallback\");\n""",
    """            constantEffectPolar_ = false;\n"
    "            prevConstantLevel_ = 0;\n"
    "            lastConstantWriteTick_ = 0;\n"
    "            spdlog::info(\"WheelFFB: ConstantForce created with 1-axis CARTESIAN fallback\");\n""",
)
verify()
commit("fix: reset ConstantForce cache on effect creation [skip ci]", ffb)

# Review finding 5: strengthen source verification so it proves the FFB engine
# actually consumes the active InputManager steering bridge, and lock in the
# lifecycle/recovery invariants found in this 30-pass review.
replace_once(
    verifier,
    "req(input_cpp, 'InputManager_SteeringValue()', 'SAT reads active InputManager steering')\n",
    "req(input_cpp, 'float InputManager_SteeringValue()', 'InputManager steering bridge exported')\n"
    "req(ffb, 'const float steering = InputManager_SteeringValue();', 'SAT reads active InputManager steering')\n",
)
text = read(verifier)
anchor = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')\n"
if text.count(anchor) != 1:
    raise SystemExit("verifier final print anchor missing or duplicated")
guards = """forbid(ffb, 'if (!initialized_ && gameHwnd_ && GetForegroundWindow() == gameHwnd_)', 'foreground recovery is not gated on initialization state')
req(ffb, 'if (gameHwnd_ && GetForegroundWindow() == gameHwnd_)', 'foreground state can recover a missed activation message')
req(ffb, 'update_spring(0.0f);\\n                if (springEffect_)\\n                    springEffect_->Stop();', 'live spring disable rechecks effect after zero update')
req(ffb, 'update_damper(0.0f);\\n                if (damperEffect_)\\n                    damperEffect_->Stop();', 'live damper disable rechecks effect after zero update')
forbid(ffb, 'DWORD recreateHoldoffUntil_', 'critical ConstantForce recovery has no shared periodic holdoff')
req(ffb, 'DWORD constantRecreateHoldoffUntil_ = 0;', 'ConstantForce recreation has an independent holdoff')
req(ffb, 'DWORD periodicRecreateHoldoffUntil_ = 0;', 'periodic recreation has an independent holdoff')
req(ffb, 'tick_before(now, constantRecreateHoldoffUntil_)', 'ConstantForce retries use the steering-specific holdoff')
req(ffb, 'tick_reached(GetTickCount(), periodicRecreateHoldoffUntil_)', 'periodic retries use the periodic-specific holdoff')
req(ffb, 'constantEffectPolar_ = true;\\n                    prevConstantLevel_ = 0;\\n                    lastConstantWriteTick_ = 0;', 'new POLAR ConstantForce resets accepted-output cache')
req(ffb, 'constantEffectPolar_ = false;\\n            prevConstantLevel_ = 0;\\n            lastConstantWriteTick_ = 0;', 'new CARTESIAN ConstantForce resets accepted-output cache')
"""
write(verifier, text.replace(anchor, guards + anchor, 1))
verify()
commit("test: guard 30-pass FFB recovery invariants [skip ci]", verifier)

print("30-pass selective FFB source review fixes applied and structurally verified")
