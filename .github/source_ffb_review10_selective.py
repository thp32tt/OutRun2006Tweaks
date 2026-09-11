from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERIFY = "tools/verify_wheel_ffb_current.py"


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


def add_before_verify_print(snippet):
    marker = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')"
    replace_once(VERIFY, marker, snippet.rstrip() + "\n" + marker)


def verify_and_commit(message, paths):
    subprocess.run(["python3", VERIFY], cwd=ROOT, check=True)
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--cached", "--check"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", message + " [skip ci]"], cwd=ROOT, check=True)


# Review 1-3: preserve the proven vehicle basis across UI/focus transitions, but
# do not retain the previous segment's warp-detection scale. This was the only
# estimator-state defect found; SAT constants themselves are intentionally left
# unchanged pending real R3 telemetry.
replace_once(
    "src/hooks_wheel_vehicle_dynamics.hpp",
    """        // Preserve the proven matrix basis while dropping every time-domain\n        // sample. Menu/focus/F11 transitions must not force another straight-\n        // line calibration before Physics SAT can return.\n        positionValid_ = false;\n        headingValid_ = false;\n        prevPosition_ = D3DVECTOR{};\n        positionStep_ = 0.0f;\n        spdLen_ = 0.0f;\n        spdCorrelation_ = 0.0f;\n        clear_dynamic_state();\n""",
    """        // Preserve the proven matrix basis while dropping every time-domain\n        // sample, including the warp-detection motion scale. Menu/focus/F11\n        // transitions must not compare a new segment against the old segment's\n        // movement scale before Physics SAT resumes.\n        positionValid_ = false;\n        headingValid_ = false;\n        prevPosition_ = D3DVECTOR{};\n        positionStep_ = 0.0f;\n        motionScaleEma_ = 0.0f;\n        motionScaleSamples_ = 0;\n        spdLen_ = 0.0f;\n        spdCorrelation_ = 0.0f;\n        clear_dynamic_state();\n""",
)
replace_once(
    "tools/test_wheel_ffb_current.cpp",
    """ require(std::abs(gap.yawRate())<.01f,\"short-gap derivative baseline\");\n WheelVehicleDynamics d; EVWORK_CAR c;d.reset();for(int i=0;i<80;++i)step(d,c);\n""",
    """ require(std::abs(gap.yawRate())<.01f,\"short-gap derivative baseline\");\n WheelVehicleDynamics resume; EVWORK_CAR resumeCar;resume.reset();for(int i=0;i<80;++i)step(resume,resumeCar);\n require(resume.calibrated()&&resume.motionScale()>0,\"resume baseline ready\");\n resume.reset_dynamic();\n require(resume.calibrated()&&resume.motionScale()==0&&!resume.sampleValid(),\"dynamic reset preserves basis but clears motion scale\");\n WheelVehicleDynamics d; EVWORK_CAR c;d.reset();for(int i=0;i<80;++i)step(d,c);\n""",
)
add_before_verify_print(
    """dynamic_reset_start = dyn.find('void reset_dynamic()')\ndynamic_reset_end = dyn.find('void update(', dynamic_reset_start)\nif not (0 <= dynamic_reset_start < dynamic_reset_end):\n    raise SystemExit('CURRENT VERIFY FAILED [dynamic reset section]')\ndynamic_reset = dyn[dynamic_reset_start:dynamic_reset_end]\nreq(dynamic_reset, 'motionScaleEma_ = 0.0f;', 'dynamic reset clears old motion-scale EMA')\nreq(dynamic_reset, 'motionScaleSamples_ = 0;', 'dynamic reset clears old motion-scale sample count')\n"""
)
verify_and_commit(
    "ffb review: clear stale motion scale across gameplay segments",
    ["src/hooks_wheel_vehicle_dynamics.hpp", "tools/test_wheel_ffb_current.cpp", VERIFY],
)


# Review 4: a null player-car sample must never leave the last DD torque alive
# until the lease/watchdog expires. Zero immediately, but keep normal disable
# teardown ahead of the null-car guard.
replace_once(
    "src/hooks_wheel_ffb.cpp",
    """        void update(EVWORK_CAR* car)\n        {\n            if (!car || panicStopped_)\n                return;\n\n            if (disable_live_if_needed())\n                return;\n            enabledLastTick_ = true;\n\n            // Safety first for a DD base: WM_ACTIVATEAPP releases exclusive\n""",
    """        void update(EVWORK_CAR* car)\n        {\n            if (panicStopped_)\n                return;\n\n            if (disable_live_if_needed())\n                return;\n            enabledLastTick_ = true;\n\n            if (!car)\n            {\n                if (initialized_)\n                {\n                    zero_all_forces();\n                    reset_signal_state();\n                }\n                lastCar_ = nullptr;\n                return;\n            }\n\n            // Safety first for a DD base: WM_ACTIVATEAPP releases exclusive\n""",
)
add_before_verify_print(
    """req(ffb, 'if (!car)\\n            {\\n                if (initialized_)\\n                {\\n                    zero_all_forces();', 'null car immediately clears active DD torque')\n"""
)
verify_and_commit(
    "ffb review: zero torque immediately on missing player car",
    ["src/hooks_wheel_ffb.cpp", VERIFY],
)


# Review 5-7: a requested torque sign reversal is partly an unload of stale
# torque. Release the old sign at the existing 2x unload rate, reach zero, then
# let the new sign build at the normal DD-safe slew. Do not raise base strength
# or base slew.
replace_once(
    "src/hooks_wheel_ffb.cpp",
    """            const bool sameTorqueDirection =\n                structuralLevel == 0 || prevStructuralLevel_ == 0 ||\n                (structuralLevel > 0) == (prevStructuralLevel_ > 0);\n            const bool unloadingStructural = sameTorqueDirection &&\n                std::abs(structuralLevel) < std::abs(prevStructuralLevel_);\n            const LONG appliedMaxSlew = unloadingStructural\n                ? std::min(static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2)\n                : maxSlew;\n            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;\n\n            if (std::abs(structuralDelta) > appliedMaxSlew)\n            {\n                structuralLevel = prevStructuralLevel_ +\n                    (structuralDelta > 0 ? appliedMaxSlew : -appliedMaxSlew);\n            }\n            prevStructuralLevel_ = structuralLevel;\n""",
    """            const LONG releaseMaxSlew = std::min(\n                static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2);\n            const bool oppositeTorqueDirection =\n                structuralLevel != 0 && prevStructuralLevel_ != 0 &&\n                (structuralLevel > 0) != (prevStructuralLevel_ > 0);\n\n            if (oppositeTorqueDirection)\n            {\n                // A sign change first unloads stale torque to zero at the\n                // already-approved faster release rate. Do not build the new\n                // direction in the same tick.\n                if (std::abs(prevStructuralLevel_) <= releaseMaxSlew)\n                    structuralLevel = 0;\n                else\n                    structuralLevel = prevStructuralLevel_ +\n                        (prevStructuralLevel_ > 0 ? -releaseMaxSlew : releaseMaxSlew);\n            }\n            else\n            {\n                const bool unloadingStructural =\n                    std::abs(structuralLevel) < std::abs(prevStructuralLevel_);\n                const LONG appliedMaxSlew =\n                    unloadingStructural ? releaseMaxSlew : maxSlew;\n                const LONG structuralDelta =\n                    structuralLevel - prevStructuralLevel_;\n                if (std::abs(structuralDelta) > appliedMaxSlew)\n                {\n                    structuralLevel = prevStructuralLevel_ +\n                        (structuralDelta > 0 ? appliedMaxSlew : -appliedMaxSlew);\n                }\n            }\n            prevStructuralLevel_ = structuralLevel;\n""",
)
replace_once(
    VERIFY,
    """req(ffb, 'const bool unloadingStructural = sameTorqueDirection &&', 'force unload detected separately from force build')\nreq(ffb, 'maxSlew * 2', 'stale torque can decay twice as fast')\nreq(ffb, 'std::abs(structuralDelta) > appliedMaxSlew', 'asymmetric slew applied to structural force')\n""",
    """req(ffb, 'const LONG releaseMaxSlew = std::min(', 'stale torque has a dedicated faster release rate')\nreq(ffb, 'const bool oppositeTorqueDirection =', 'torque sign reversal is detected explicitly')\nreq(ffb, 'if (std::abs(prevStructuralLevel_) <= releaseMaxSlew)\\n                    structuralLevel = 0;', 'sign reversal unloads old torque to zero before rebuilding')\nreq(ffb, 'unloadingStructural ? releaseMaxSlew : maxSlew', 'same-sign force unload remains faster than force build')\n""",
)
verify_and_commit(
    "ffb review: unload stale torque before direction reversal",
    ["src/hooks_wheel_ffb.cpp", VERIFY],
)


# Review 8-10: no force-model retune was justified. Correct only stale UI and
# diagnostics that now disagree with live reinitialization/full Natural fallback.
replace_once(
    "src/hooks_wheel_ffb.cpp",
    """            // During basis calibration retain only a small Natural SAT safety\n            // net, then crossfade over valid dynamics ticks. Invalid telemetry\n            // decays/clears dynamics state instead of leaking stale slide values.\n""",
    """            // Keep full Natural SAT while calibration/current motion is unavailable,\n            // then crossfade over valid dynamics ticks. Invalid telemetry falls\n            // back immediately instead of leaking stale Physics SAT values.\n""",
)
replace_once(
    "src/hooks_wheel_ffb.cpp",
    """            // Keep the Natural safety net alive throughout the activation ramp.\n            // Dropping it on the calibration tick created a short SAT hole while\n            // physicsMix was still near zero.\n""",
    """            // Natural SAT remains the fallback throughout the activation ramp.\n            // Dropping it on the calibration tick created a short SAT hole while\n            // physicsMix was still near zero.\n""",
)
replace_once(
    "src/hooks_wheel_ffb.cpp",
    """            // Hardware periodics are preferred. If unavailable, inject a capped\n            // low-frequency sine after the tanh compressor. Road/slip signals\n""",
    """            // Hardware periodics are preferred. If unavailable, inject a capped\n            // low-frequency sine after the structural soft-knee limiter. Road/slip signals\n""",
)
replace_once(
    "src/hooks_wheel_ffb.cpp",
    '? (vehicleDynamics_.sampleValid() ? "ACTIVE" : "HOLD")',
    '? (vehicleDynamics_.sampleValid() ? "ACTIVE" : "FALLBACK")',
)
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    """            ImGui::TextDisabled(\n                Settings::UseNewInput\n                    ? \"Input setup: Input Bindings only. FFB setup: this Force Feedback page only. Restart after switching to a different physical wheel.\"\n                    : \"Legacy input and DirectInput FFB output are selected separately on this page. Restart after switching physical devices.\");\n""",
    """            ImGui::TextDisabled(\n                Settings::UseNewInput\n                    ? \"Input setup: Input Bindings only. FFB selection and tuning apply live; Save Force Feedback persists them.\"\n                    : \"Legacy input and DirectInput FFB output are selected separately on this page. FFB selection and tuning apply live.\");\n""",
)
add_before_verify_print(
    """req(ffb, '? (vehicleDynamics_.sampleValid() ? \"ACTIVE\" : \"FALLBACK\")', 'diagnostics report Natural fallback instead of stale Physics hold')\nforbid(ffb, '? (vehicleDynamics_.sampleValid() ? \"ACTIVE\" : \"HOLD\")', 'diagnostics never claim invalid Physics SAT is held')\nreq(wheel_ui, 'FFB selection and tuning apply live', 'F11 footer matches live FFB reinitialization')\nforbid(wheel_ui, 'Restart after switching to a different physical wheel', 'new-input FFB page has no stale restart requirement')\nforbid(wheel_ui, 'Restart after switching physical devices', 'legacy FFB page has no stale restart requirement')\n"""
)
verify_and_commit(
    "ffb review: align UI and telemetry with live fallback behavior",
    ["src/hooks_wheel_ffb.cpp", "src/overlay/wheel_setup_ui.cpp", VERIFY],
)

print("SELECTIVE TEN-PASS SOURCE REVIEW COMPLETE: 4 justified change groups; no compiler invoked")
