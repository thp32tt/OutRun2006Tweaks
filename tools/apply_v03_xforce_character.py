from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Core: selectable steering character + guarded native X-Force candidate.
# ---------------------------------------------------------------------------
replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''    Setting<bool> WheelFFBPhysicsSat{\n        "WheelFFB", "PhysicsSAT", true,\n        "Experimental body-slip/yaw SAT instead of steering-centre direction alone."\n    };\n\n    Setting<float> WheelFFBGripLoss{''',
    '''    Setting<bool> WheelFFBPhysicsSat{\n        "WheelFFB", "PhysicsSAT", true,\n        "Experimental body-slip/yaw SAT instead of steering-centre direction alone."\n    };\n\n    // v0.3 steering-character experiment. Modern preserves the v0.2 model exactly;\n    // Arcade/Hybrid can consume the game's actionforce_DBC field only after\n    // conservative plausibility checks. Until that field is proven to be Howard\n    // Castro's X-Force, it is deliberately treated as a candidate signal.\n    Setting<int> WheelFFBFeedbackCharacter{\n        "WheelFFB", "FeedbackCharacter", 0,\n        "Steering-force character: 0=Modern DD, 1=Arcade X-Force candidate, 2=Hybrid.",\n        Range<int>{ 0, 2 }\n    };\n\n    Setting<float> WheelFFBXForceMix{\n        "WheelFFB", "XForceMix", 0.50f,\n        "Hybrid share of the guarded native X-Force candidate. 0=Modern SAT, 1=native candidate.",\n        Range<float>{ 0.0f, 1.0f }\n    };\n\n    Setting<bool> WheelFFBXForceInvert{\n        "WheelFFB", "XForceInvert", false,\n        "Reverse only the native X-Force candidate before it is mixed with Modern SAT."\n    };\n\n    Setting<float> WheelFFBGripLoss{'''
)

replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''            const float physicsFallback = naturalSatTorque;\n            const float selfAligningTorque = Settings::WheelFFBPhysicsSat\n                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix\n                : naturalSatTorque;\n\n            float loadMod = 1.0f;''',
    '''            const float physicsFallback = naturalSatTorque;\n            const float modernSelfAligningTorque = Settings::WheelFFBPhysicsSat\n                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix\n                : naturalSatTorque;\n\n            // v0.3 native steering-force experiment. Howard Castro described an\n            // internal OutRun steering-force value with a nominal low-speed span\n            // around +/-62. actionforce_DBC is a promising existing EVWORK_CAR\n            // field, but it is not yet proven to be that exact value. Therefore:\n            //   * Modern DD never consumes it.\n            //   * Arcade/Hybrid accept it only inside a conservative finite/range\n            //     envelope and require a non-trivial response while steering.\n            //   * any suspicious or apparently dead signal falls back to the\n            //     already-proven Modern SAT for that tick.\n            //   * all modes still pass through the common DD slew, soft limiter,\n            //     focus watchdog and DirectInput safety path below.\n            constexpr float XForceNominalFullScale = 62.0f;\n            constexpr float XForceAbsoluteSafetyLimit = 128.0f;\n            constexpr float XForceNoiseFloor = 0.20f;\n            const float xForceRaw = car->actionforce_DBC;\n            const bool xForceFinite = std::isfinite(xForceRaw);\n            const bool xForceRangeValid =\n                xForceFinite && std::abs(xForceRaw) <= XForceAbsoluteSafetyLimit;\n            const bool xForceResponsive =\n                std::abs(xForceRaw) >= 0.05f || steerAbs < 0.05f || speedNorm < 0.04f;\n            const bool xForceValid = xForceRangeValid && xForceResponsive;\n\n            float xForceNormalized = 0.0f;\n            if (xForceValid)\n            {\n                const float magnitude = std::max(0.0f, std::abs(xForceRaw) - XForceNoiseFloor);\n                const float normalizedMagnitude = std::clamp(\n                    magnitude / (XForceNominalFullScale - XForceNoiseFloor),\n                    0.0f, 1.0f);\n                xForceNormalized = std::copysign(normalizedMagnitude, xForceRaw);\n                if (Settings::WheelFFBXForceInvert)\n                    xForceNormalized = -xForceNormalized;\n            }\n\n            // Keep the original low-speed character but protect a modern DD base\n            // from the candidate signal's historically large parking-speed force.\n            // Above the launch/parking region the native magnitude is left intact.\n            const float xForceLowSpeedT = std::clamp(\n                (speedNorm - 0.015f) / 0.12f, 0.0f, 1.0f);\n            const float xForceLowSpeedSmooth =\n                xForceLowSpeedT * xForceLowSpeedT * (3.0f - 2.0f * xForceLowSpeedT);\n            const float xForceLowSpeedGuard = 0.30f + 0.70f * xForceLowSpeedSmooth;\n            const float nativeXForceTorque =\n                xForceNormalized * xForceLowSpeedGuard * satStrength;\n\n            const int feedbackCharacter = std::clamp(\n                static_cast<int>(Settings::WheelFFBFeedbackCharacter), 0, 2);\n            const float configuredXForceMix =\n                static_cast<float>(Settings::WheelFFBXForceMix);\n            const float xForceMix = std::isfinite(configuredXForceMix)\n                ? std::clamp(configuredXForceMix, 0.0f, 1.0f)\n                : 0.50f;\n\n            float selfAligningTorque = modernSelfAligningTorque;\n            if (xForceValid && feedbackCharacter == 1)\n                selfAligningTorque = nativeXForceTorque;\n            else if (xForceValid && feedbackCharacter == 2)\n                selfAligningTorque = modernSelfAligningTorque +\n                    (nativeXForceTorque - modernSelfAligningTorque) * xForceMix;\n\n            float loadMod = 1.0f;'''
)

replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''                spdlog::info(\n                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} trailResponseSlip={} trailResponseLead={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",''',
    '''                spdlog::info(\n                    "WheelFFB XFORCE t={} character={} raw={} finite={} valid={} normalized={} nativeTorque={} modernTorque={} finalSat={} mix={} candidateInvert={}",\n                    telemetryNow, feedbackCharacter, xForceRaw, xForceFinite, xForceValid,\n                    xForceNormalized, nativeXForceTorque, modernSelfAligningTorque,\n                    selfAligningTorque, xForceMix, bool(Settings::WheelFFBXForceInvert));\n                spdlog::info(\n                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} trailResponseSlip={} trailResponseLead={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",'''
)

# ---------------------------------------------------------------------------
# UI: character picker, Hybrid mix, candidate sign control, save/revert state.
# ---------------------------------------------------------------------------
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''    extern Setting<bool> WheelFFBPhysicsSat;\n    extern Setting<float> WheelFFBGripLoss;''',
    '''    extern Setting<bool> WheelFFBPhysicsSat;\n    extern Setting<int> WheelFFBFeedbackCharacter;\n    extern Setting<float> WheelFFBXForceMix;\n    extern Setting<bool> WheelFFBXForceInvert;\n    extern Setting<float> WheelFFBGripLoss;'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            bool physicsSat = true;\n            bool hwSpring = true;''',
    '''            bool physicsSat = true;\n            int feedbackCharacter = 0;\n            float xForceMix = 0.50f;\n            bool xForceInvert = false;\n            bool hwSpring = true;'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            savedFfb_.physicsSat = Settings::WheelFFBPhysicsSat;\n            savedFfb_.hwSpring = Settings::WheelFFBUseHardwareSpring;''',
    '''            savedFfb_.physicsSat = Settings::WheelFFBPhysicsSat;\n            savedFfb_.feedbackCharacter = Settings::WheelFFBFeedbackCharacter;\n            savedFfb_.xForceMix = Settings::WheelFFBXForceMix;\n            savedFfb_.xForceInvert = Settings::WheelFFBXForceInvert;\n            savedFfb_.hwSpring = Settings::WheelFFBUseHardwareSpring;'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            Settings::WheelFFBPhysicsSat = savedFfb_.physicsSat;\n            Settings::WheelFFBUseHardwareSpring = savedFfb_.hwSpring;''',
    '''            Settings::WheelFFBPhysicsSat = savedFfb_.physicsSat;\n            Settings::WheelFFBFeedbackCharacter = savedFfb_.feedbackCharacter;\n            Settings::WheelFFBXForceMix = savedFfb_.xForceMix;\n            Settings::WheelFFBXForceInvert = savedFfb_.xForceInvert;\n            Settings::WheelFFBUseHardwareSpring = savedFfb_.hwSpring;'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            ImGui::TextWrapped(\n                "Single-owner wheel FFB: DirectInput COM only. field_264/268 are lateral load only; front slip drives a pneumatic + mechanical/caster SAT model, while body/front slip release damping. Centering Spring remains a low-speed stabilizer.");''',
    '''            ImGui::TextWrapped(\n                "Single-owner wheel FFB: DirectInput COM only. v0.3 can keep the Modern DD front-slip SAT, test the game's actionforce_DBC as an X-Force candidate, or blend both. Centering Spring remains a low-speed stabilizer and every character shares the same DD safety/output path.");'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            track_ffb_change(ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f"));\n            track_ffb_change(ImGui::Checkbox("Physics SAT (body slip + yaw)", Settings::WheelFFBPhysicsSat.ptr()));\n            if (ImGui::IsItemHovered())\n                ImGui::SetTooltip("Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Natural SAT comparison.");\n            if (Settings::WheelFFBPhysicsSat)''',
    '''            track_ffb_change(ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f"));\n\n            static constexpr const char* FeedbackCharacters[] = {\n                "Modern DD", "Arcade / X-Force candidate", "Hybrid"\n            };\n            int feedbackCharacter = std::clamp(int(Settings::WheelFFBFeedbackCharacter), 0, 2);\n            if (ImGui::BeginCombo("Feedback Character", FeedbackCharacters[feedbackCharacter]))\n            {\n                for (int character = 0; character < 3; ++character)\n                {\n                    const bool selected = character == feedbackCharacter;\n                    if (ImGui::Selectable(FeedbackCharacters[character], selected))\n                    {\n                        Settings::WheelFFBFeedbackCharacter = character;\n                        feedbackCharacter = character;\n                        track_ffb_change(true);\n                        WheelFFB_RequestSettingsTransition();\n                    }\n                    if (selected)\n                        ImGui::SetItemDefaultFocus();\n                }\n                ImGui::EndCombo();\n            }\n\n            if (feedbackCharacter == 0)\n                ImGui::TextDisabled("Modern DD: v0.2 front-slip / pneumatic + mechanical-trail SAT behavior.");\n            else if (feedbackCharacter == 1)\n                ImGui::TextDisabled("Arcade: guarded actionforce_DBC candidate drives SAT; invalid/dead samples fall back to Modern SAT.");\n            else\n            {\n                ImGui::TextDisabled("Hybrid: blends the guarded actionforce_DBC candidate with Modern SAT.");\n                track_ffb_change(ImGui::SliderFloat("X-Force Mix", Settings::WheelFFBXForceMix.ptr(), 0.0f, 1.0f, "%.2f"));\n            }\n            if (feedbackCharacter != 0)\n                ImGui::TextColored(ImVec4(1.0f, 0.75f, 0.25f, 1.0f),\n                    "Experimental: actionforce_DBC is a strong X-Force candidate, not yet proven. Enable telemetry before judging the native signal.");\n\n            const char* physicsSatLabel = feedbackCharacter == 0\n                ? "Physics SAT (body slip + yaw)"\n                : "Modern fallback uses Physics SAT";\n            track_ffb_change(ImGui::Checkbox(physicsSatLabel, Settings::WheelFFBPhysicsSat.ptr()));\n            if (ImGui::IsItemHovered())\n                ImGui::SetTooltip("Uses post-physics OutRun car motion/body heading to estimate front slip. In Arcade/Hybrid this is also the safe fallback when the X-Force candidate is invalid.");\n            if (Settings::WheelFFBPhysicsSat)'''
)

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                if (Settings::WheelFFBPhysicsSat)\n                {\n                    ImGui::SeparatorText("Physics SAT transient");''',
    '''                const int advancedFeedbackCharacter = std::clamp(int(Settings::WheelFFBFeedbackCharacter), 0, 2);\n                if (advancedFeedbackCharacter != 0)\n                {\n                    ImGui::SeparatorText("Native X-Force candidate");\n                    track_ffb_change(ImGui::Checkbox("Reverse X-Force candidate only", Settings::WheelFFBXForceInvert.ptr()));\n                    if (ImGui::IsItemHovered())\n                        ImGui::SetTooltip("Use this only if Arcade/Hybrid steering force is reversed relative to Modern DD. Global Reverse SAT / ConstantForce still applies after the mix.");\n                    if (advancedFeedbackCharacter != 2)\n                        track_ffb_change(ImGui::SliderFloat("X-Force Mix (used by Hybrid)", Settings::WheelFFBXForceMix.ptr(), 0.0f, 1.0f, "%.2f"));\n                }\n                if (Settings::WheelFFBPhysicsSat)\n                {\n                    ImGui::SeparatorText("Physics SAT transient");'''
)

# Presets explicitly return to the known v0.2 Modern character.
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                Settings::WheelFFBPhysicsSat = true;\n                Settings::WheelFFBGlobalStrength = 0.70f;''',
    '''                Settings::WheelFFBPhysicsSat = true;\n                Settings::WheelFFBFeedbackCharacter = 0;\n                Settings::WheelFFBXForceMix = 0.50f;\n                Settings::WheelFFBXForceInvert = false;\n                Settings::WheelFFBGlobalStrength = 0.70f;'''
)
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                Settings::WheelFFBPhysicsSat = false;\n                Settings::WheelFFBEnable = true;''',
    '''                Settings::WheelFFBPhysicsSat = false;\n                Settings::WheelFFBFeedbackCharacter = 0;\n                Settings::WheelFFBXForceMix = 0.50f;\n                Settings::WheelFFBXForceInvert = false;\n                Settings::WheelFFBEnable = true;'''
)

# ---------------------------------------------------------------------------
# Shipped configuration: Modern DD remains the default; opt-in experiment only.
# ---------------------------------------------------------------------------
replace_once(
    "OutRun2006Tweaks.ini",
    '''[WheelFFB]\n; Physics SAT uses front lateral force times total pseudo-trail:''',
    '''[WheelFFB]\n; v0.3 steering-force character. Modern DD preserves the v0.2 behavior.\n; 0 = Modern DD, 1 = Arcade / guarded X-Force candidate, 2 = Hybrid.\n; actionforce_DBC is still under validation, so Arcade/Hybrid fall back to the\n; Modern SAT whenever the candidate is non-finite, implausible, or unresponsive.\nFeedbackCharacter = 0\nXForceMix = 0.50\nXForceInvert = false\n\n; Physics SAT uses front lateral force times total pseudo-trail:'''
)

# ---------------------------------------------------------------------------
# Verification: lock in safety/fallback properties and the user-facing selector.
# ---------------------------------------------------------------------------
replace_once(
    "tools/verify_wheel_ffb_current.py",
    '''req(ffb, 'const float steering = InputManager_SteeringValue();', 'SAT reads active InputManager steering')''',
    '''req(ffb, 'const float steering = InputManager_SteeringValue();', 'SAT reads active InputManager steering')\nreq(ffb, 'Setting<int> WheelFFBFeedbackCharacter', 'v0.3 selectable feedback character setting')\nreq(ffb, 'constexpr float XForceNominalFullScale = 62.0f;', 'X-Force candidate uses documented nominal scale')\nreq(ffb, 'constexpr float XForceAbsoluteSafetyLimit = 128.0f;', 'X-Force candidate has a hard plausibility envelope')\nreq(ffb, 'const bool xForceValid = xForceRangeValid && xForceResponsive;', 'X-Force candidate requires finite plausible responsive data')\nreq(ffb, 'float selfAligningTorque = modernSelfAligningTorque;', 'Modern SAT is the fail-safe baseline')\nreq(ffb, 'if (xForceValid && feedbackCharacter == 1)', 'Arcade character only uses validated X-Force candidate')\nreq(ffb, 'else if (xForceValid && feedbackCharacter == 2)', 'Hybrid character only mixes validated X-Force candidate')\nreq(ffb, 'WheelFFB XFORCE t={}', 'X-Force candidate is observable in opt-in telemetry')\nreq(wheel_ui, 'Feedback Character', 'FFB UI exposes feedback character selector')\nreq(wheel_ui, 'X-Force Mix', 'FFB UI exposes Hybrid native mix')\nreq(wheel_ui, 'Reverse X-Force candidate only', 'FFB UI exposes candidate-only direction correction')'''
)

print("v0.3 X-Force character patch applied")
