from pathlib import Path

ffb_path = Path('src/hooks_wheel_ffb.cpp')
ui_path = Path('src/overlay/wheel_setup_ui.cpp')
ffb = ffb_path.read_text(encoding='utf-8')
ui = ui_path.read_text(encoding='utf-8')


def rep(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'round17 {label}: expected exactly one match, got {count}')
    print(f'ROUND17 patched: {label}')
    return text.replace(old, new, 1)

ffb = rep(ffb,
'''#include "game_addrs.hpp"\n''',
'''#include "game_addrs.hpp"\n#include "hooks_wheel_physics_sat.hpp"\n''',
'include physics SAT helper')

ffb = rep(ffb,
'''    Setting<float> WheelFFBSteeringWeight{\n        "WheelFFB", "SteeringWeight", 1.45f,\n        "Self-aligning torque strength. Uses steering angle, speed and OutRun lateral load; unloads only in deeper drift.", Range<float>{ 0.0f, 2.0f }\n    };\n\n''',
'''    Setting<float> WheelFFBSteeringWeight{\n        "WheelFFB", "SteeringWeight", 1.45f,\n        "Self-aligning torque strength. Physics SAT uses body slip, yaw rate and lateral load; Natural SAT remains available for comparison.", Range<float>{ 0.0f, 2.0f }\n    };\n\n    Setting<bool> WheelFFBPhysicsSat{\n        "WheelFFB", "PhysicsSAT", true,\n        "Experimental body-slip/yaw SAT instead of steering-centre direction alone."\n    };\n\n''',
'physics SAT setting')

ffb = rep(ffb,
'''            const float selfAligningTorque =\n                (steer >= 0.0f ? -1.0f : 1.0f) *\n                steerForSat * satSpeed * satLoadBoost * satGrip *\n                satReturnRelief * satStrength;\n''',
'''            const float naturalSatTorque =\n                (steer >= 0.0f ? -1.0f : 1.0f) *\n                steerForSat * satSpeed * satLoadBoost * satGrip *\n                satReturnRelief * satStrength;\n\n            // Round-17 Physics SAT: front-slip direction comes from OutRun car\n            // motion + body yaw, not merely from the sign of steering input.\n            const float physicsSatTorque = physicsSat_.update(\n                car, steer, speedNorm, cornerLoadSmooth, returnRateSmooth,\n                static_cast<float>(Settings::WheelFFBGripLoss),\n                satStrength, satSpeed);\n            const float selfAligningTorque = Settings::WheelFFBPhysicsSat\n                ? (physicsSat_.ready() ? physicsSatTorque : naturalSatTorque * 0.25f)\n                : naturalSatTorque;\n''',
'front-slip physics SAT selection')

ffb = rep(ffb,
'''            smoothedLateral_ = 0.0f;\n            prevSteer_ = 0.0f;\n            prevStructuralLevel_ = 0;\n''',
'''            smoothedLateral_ = 0.0f;\n            prevSteer_ = 0.0f;\n            physicsSat_.reset();\n            prevStructuralLevel_ = 0;\n''',
'reset physics SAT state')

ffb = rep(ffb,
'''                "WheelFFB DIAG: spd={:.2f} steer={:.3f} rate={:.4f} lat={:.2f} drift={:.2f} rough={:.2f} sat={:.3f} steerSrc={} out={} invCF={} spring={} invSpring={} coeff={} damper={} dcoeff={} periodic={}",\n''',
'''                "WheelFFB DIAG: spd={:.2f} steer={:.3f} rate={:.4f} lat={:.2f} drift={:.2f} rough={:.2f} sat={:.3f} phys={} basis=M70r{} beta={:.3f} yaw={:.3f} fslip={:.3f} vLat={:.5f} vLong={:.5f} spdCorr={:.2f} steerSrc={} out={} invCF={} spring={} invSpring={} coeff={} damper={} dcoeff={} periodic={}",\n''',
'physics diagnostic format')
ffb = rep(ffb,
'''                satTorque,\n                Settings::UseNewInput ? "SDL" : "legacy",\n''',
'''                satTorque,\n                Settings::WheelFFBPhysicsSat ? (physicsSat_.ready() ? "ACTIVE" : "CAL") : "OFF",\n                physicsSat_.forwardAxis(),\n                physicsSat_.bodySlip(),\n                physicsSat_.yawRate(),\n                physicsSat_.frontSlip(),\n                physicsSat_.vLat(),\n                physicsSat_.vLong(),\n                physicsSat_.spdCorrelation(),\n                Settings::UseNewInput ? "SDL" : "legacy",\n''',
'physics diagnostic values')

ffb = rep(ffb,
'''        float smoothedLateral_ = 0.0f;\n        float prevSteer_ = 0.0f;\n        float crashImpulseForce_ = 0.0f;\n''',
'''        float smoothedLateral_ = 0.0f;\n        float prevSteer_ = 0.0f;\n        WheelPhysicsSatV1 physicsSat_{};\n        float crashImpulseForce_ = 0.0f;\n''',
'physics SAT state member')

ui = rep(ui,
'''    extern Setting<float> WheelFFBSteeringWeight;\n    extern Setting<float> WheelFFBGripLoss;\n''',
'''    extern Setting<float> WheelFFBSteeringWeight;\n    extern Setting<bool> WheelFFBPhysicsSat;\n    extern Setting<float> WheelFFBGripLoss;\n''',
'F11 physics SAT setting')

ui = rep(ui,
'''            ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f");\n            ImGui::SliderFloat("Grip-loss Unload", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f");\n''',
'''            ImGui::SliderFloat("Self-aligning Torque (SAT)", Settings::WheelFFBSteeringWeight.ptr(), 0.0f, 2.00f, "%.2f");\n            ImGui::Checkbox("Physics SAT v1 (body slip + yaw)", Settings::WheelFFBPhysicsSat.ptr());\n            if (ImGui::IsItemHovered())\n                ImGui::SetTooltip("Uses OutRun car motion/body heading to estimate front slip. Disable for the Round-16 Natural SAT comparison.");\n            ImGui::SliderFloat("Grip-loss Unload", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f");\n''',
'F11 physics SAT toggle')

ui = rep(ui,
'''            if (ImGui::Button("Load MOZA R3 Natural SAT"))\n            {\n''',
'''            if (ImGui::Button("Load MOZA R3 Physics SAT v1"))\n            {\n                Settings::WheelFFBEnable = true;\n                Settings::WheelFFBPhysicsSat = true;\n                Settings::WheelFFBGlobalStrength = 0.70f;\n                Settings::WheelFFBSpringStrength = 0.65f;\n                Settings::WheelFFBSpringSaturation = 0.95f;\n                Settings::WheelFFBDamperStrength = 0.28f;\n                Settings::WheelFFBSteeringWeight = 1.45f;\n                Settings::WheelFFBGripLoss = 0.65f;\n                Settings::WheelFFBWeightTransfer = 0.15f;\n                Settings::WheelFFBSlewRate = 0.040f;\n                Settings::WheelFFBRoadTexture = 0.30f;\n                Settings::WheelFFBTireSlip = 0.20f;\n                Settings::WheelFFBWallImpact = 0.38f;\n                Settings::WheelFFBUseHardwareSpring = true;\n                Settings::WheelFFBUseHardwareDamper = true;\n                Settings::WheelFFBInvertForce = true;\n                Settings::WheelFFBInvertSpring = false;\n                Settings::WheelFFBDebugLog = true;\n                Settings::VibrationMode = 0;\n                Settings::write(Module::UserIniPath);\n                status_ = "Loaded MOZA R3 Physics SAT v1: body-slip/yaw SAT enabled with diagnostic logging. Saved to user.ini.";\n            }\n            ImGui::SameLine();\n\n            if (ImGui::Button("Load MOZA R3 Natural SAT"))\n            {\n                Settings::WheelFFBPhysicsSat = false;\n''',
'Physics SAT preset plus Natural A/B fallback')

ffb_path.write_text(ffb, encoding='utf-8')
ui_path.write_text(ui, encoding='utf-8')
print('Applied round-17 physics SAT v1: body-slip/yaw front-slip model with Natural SAT fallback')
