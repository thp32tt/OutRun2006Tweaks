from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {count}')
    return text.replace(old, new, 1)

def insert_before(text, marker, block, label):
    return replace_once(text, marker, block + marker, label)

# ---------------------------------------------------------------------------
# Runtime snapshots shared by FFB engine, F11 UI and Input Bindings status.
# ---------------------------------------------------------------------------
runtime = '''#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

struct WheelFFBHeadroomSnapshot
{
    std::uint64_t samples = 0;
    float currentDemand = 0.0f;
    float peakDemand = 0.0f;
    float p95Demand = 0.0f;
    float p99Demand = 0.0f;
    float softKneePercent = 0.0f;
    float hardClipPercent = 0.0f;
    float suggestedOverall = 0.0f;
};

struct WheelFFBStatusSnapshot
{
    bool enabled = false;
    bool initialized = false;
    bool acquired = false;
    bool panicStopped = false;
    bool ffbStateValid = false;
    std::uint32_t ffbState = 0;
    bool constantHardware = false;
    bool springHardware = false;
    bool damperHardware = false;
    bool periodicHardware = false;
    bool constantCapabilityKnown = false;
    bool springCapabilityKnown = false;
    bool damperCapabilityKnown = false;
    bool periodicCapabilityKnown = false;
    bool constantDynamic = true;
    bool springDynamic = true;
    bool damperDynamic = true;
    bool periodicDynamic = true;
    bool constantRestartUpdates = false;
    bool directionLeftTested = false;
    bool directionRightTested = false;
    int physicsMode = 0; // 0=off, 1=calibrating, 2=active, 3=fallback
    std::string deviceName;
};

inline constexpr std::size_t WheelFFBGraphSamples = 180;
struct WheelFFBGraphSnapshot
{
    std::array<float, WheelFFBGraphSamples> rawStructural{};
    std::array<float, WheelFFBGraphSamples> postLimiter{};
    std::array<float, WheelFFBGraphSamples> postSlew{};
    std::array<float, WheelFFBGraphSamples> finalOutput{};
    std::size_t count = 0;
    std::size_t offset = 0;
};

void WheelFFB_RequestDirectionTest(int direction);
void WheelFFB_RequestSettingsTransition();
WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot();
WheelFFBStatusSnapshot WheelFFB_GetStatusSnapshot();
WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot();
void WheelFFB_ResetHeadroomStats();
'''
write('src/wheel_ffb_runtime.hpp', runtime)

# ---------------------------------------------------------------------------
# FFB engine: capability-aware hardware effects, status snapshot and graph.
# ---------------------------------------------------------------------------
path = 'src/hooks_wheel_ffb.cpp'
ffb = read(path)

# Capability helper before ConstantForce creation.
marker = '        bool create_constant_effect()\n        {\n'
cap_block = '''        struct DynamicEffectCapability
        {
            bool known = false;
            bool typeSpecific = true;
            bool direction = true;
        };

        DynamicEffectCapability query_dynamic_capability(REFGUID guid, const char* label)
        {
            DynamicEffectCapability capability{};
            if (!device_)
                return capability;

            DIEFFECTINFOA info{};
            info.dwSize = sizeof(info);
            const HRESULT hr = device_->GetEffectInfo(&info, guid);
            if (FAILED(hr))
            {
                spdlog::warn("WheelFFB: GetEffectInfo({}) failed (0x{:08X}); keeping compatibility path", label, (unsigned)hr);
                return capability;
            }

            capability.known = true;
            capability.typeSpecific = (info.dwDynamicParams & DIEP_TYPESPECIFICPARAMS) != 0;
            capability.direction = (info.dwDynamicParams & DIEP_DIRECTION) != 0;
            spdlog::info(
                "WheelFFB: {} dynamic params type={} direction={} mask=0x{:08X}",
                label, capability.typeSpecific, capability.direction,
                static_cast<unsigned>(info.dwDynamicParams));
            return capability;
        }

'''
ffb = insert_before(ffb, marker, cap_block, 'insert effect capability helper')

# Constant capability and polar fallback.
old = '''        bool create_constant_effect()
        {
            if (!device_)
                return false;

            DWORD axes[2] = {'''
new = '''        bool create_constant_effect()
        {
            if (!device_)
                return false;

            const DynamicEffectCapability capability =
                query_dynamic_capability(GUID_ConstantForce, "GUID_ConstantForce");
            constantCapabilityKnown_ = capability.known;
            constantTypeDynamic_ = capability.typeSpecific;
            constantDirectionDynamic_ = capability.direction;
            constantRequiresRestart_ = capability.known && !capability.typeSpecific;

            DWORD axes[2] = {'''
ffb = replace_once(ffb, old, new, 'constant capability query')
ffb = replace_once(
    ffb,
    '            if (actuatorAxes_.size() > 1)\n            {\n',
    '            if (actuatorAxes_.size() > 1 && (!capability.known || capability.direction))\n            {\n',
    'polar requires dynamic direction')

# Optional hardware effects use software fallback when type params cannot change live.
old = '''        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring)
                return false;

            DWORD axes[1] = { primary_actuator_axis() };'''
new = '''        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring || springCapabilityRejected_)
                return false;

            const DynamicEffectCapability capability =
                query_dynamic_capability(GUID_Spring, "GUID_Spring");
            springCapabilityKnown_ = capability.known;
            springTypeDynamic_ = capability.typeSpecific;
            if (capability.known && !capability.typeSpecific)
            {
                springCapabilityRejected_ = true;
                spdlog::warn("WheelFFB: GUID_Spring cannot update condition parameters while playing; using software spring fallback");
                return false;
            }

            DWORD axes[1] = { primary_actuator_axis() };'''
ffb = replace_once(ffb, old, new, 'spring capability query')

old = '''        bool create_damper_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareDamper)
                return false;

            DWORD axes[1] = { primary_actuator_axis() };'''
new = '''        bool create_damper_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareDamper || damperCapabilityRejected_)
                return false;

            const DynamicEffectCapability capability =
                query_dynamic_capability(GUID_Damper, "GUID_Damper");
            damperCapabilityKnown_ = capability.known;
            damperTypeDynamic_ = capability.typeSpecific;
            if (capability.known && !capability.typeSpecific)
            {
                damperCapabilityRejected_ = true;
                spdlog::warn("WheelFFB: GUID_Damper cannot update condition parameters while playing; using software damper fallback");
                return false;
            }

            DWORD axes[1] = { primary_actuator_axis() };'''
ffb = replace_once(ffb, old, new, 'damper capability query')

old = '''        void create_periodic_effects()
        {
            if (!Settings::WheelFFBUsePeriodicEffects || !device_)
            {
                periodicsActive_ = false;
                return;
            }

            if (!roadTextureEffect_)'''
new = '''        void create_periodic_effects()
        {
            if (!Settings::WheelFFBUsePeriodicEffects || !device_ || periodicCapabilityRejected_)
            {
                periodicsActive_ = false;
                return;
            }

            const DynamicEffectCapability capability =
                query_dynamic_capability(GUID_Sine, "GUID_Sine");
            periodicCapabilityKnown_ = capability.known;
            periodicTypeDynamic_ = capability.typeSpecific;
            if (capability.known && !capability.typeSpecific)
            {
                periodicCapabilityRejected_ = true;
                periodicsActive_ = false;
                spdlog::warn("WheelFFB: GUID_Sine cannot update magnitude/period while playing; using ConstantForce vibration fallback");
                return;
            }

            if (!roadTextureEffect_)'''
ffb = replace_once(ffb, old, new, 'periodic capability query')

# Stop/start only for essential ConstantForce on drivers without dynamic type updates.
old = '''            HRESULT hr = E_FAIL;
            if (constantEffect_)
                hr = constantEffect_->SetParameters(&params, flags);
'''
new = '''            HRESULT hr = E_FAIL;
            if (constantEffect_)
            {
                if (constantRequiresRestart_)
                    constantEffect_->Stop();
                hr = constantEffect_->SetParameters(&params, flags);
            }
'''
ffb = replace_once(ffb, old, new, 'constant non-dynamic compatibility')

# Reset capability state on physical device release.
old = '''        void release_device()
        {
            if (!device_)
            {
                deviceAcquired_ = false;
                driverAutocenterDisabled_ = false;
                return;
            }
'''
new = '''        void release_device()
        {
            directionLeftTested_ = false;
            directionRightTested_ = false;
            constantCapabilityKnown_ = false;
            springCapabilityKnown_ = false;
            damperCapabilityKnown_ = false;
            periodicCapabilityKnown_ = false;
            constantTypeDynamic_ = true;
            constantDirectionDynamic_ = true;
            springTypeDynamic_ = true;
            damperTypeDynamic_ = true;
            periodicTypeDynamic_ = true;
            constantRequiresRestart_ = false;
            springCapabilityRejected_ = false;
            damperCapabilityRejected_ = false;
            periodicCapabilityRejected_ = false;
            if (!device_)
            {
                deviceAcquired_ = false;
                driverAutocenterDisabled_ = false;
                return;
            }
'''
ffb = replace_once(ffb, old, new, 'reset capability state')

# Track direction tests.
needle = '            manualTestDirection_ = direction < 0 ? -1 : 1;\n'
replacement = '''            manualTestDirection_ = direction < 0 ? -1 : 1;
            if (direction < 0) directionLeftTested_ = true;
            if (direction > 0) directionRightTested_ = true;
'''
ffb = replace_once(ffb, needle, replacement, 'direction test tracking')

# Record live graph immediately after final response mapping.
needle = '''            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;
            const LONG level = apply_response_correction(levelBeforeResponse);

            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||'''
replacement = '''            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;
            const LONG level = apply_response_correction(levelBeforeResponse);
            record_graph(
                total,
                compressed,
                static_cast<float>(structuralLevel) / static_cast<float>(DI_FFNOMINALMAX),
                static_cast<float>(level) / static_cast<float>(DI_FFNOMINALMAX));

            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||'''
ffb = replace_once(ffb, needle, replacement, 'record live graph')

# Status/graph methods before settings transition.
marker = '        void settings_transition()\n        {\n'
methods = '''        WheelFFBStatusSnapshot status_snapshot()
        {
            WheelFFBStatusSnapshot snapshot{};
            snapshot.enabled = bool(Settings::WheelFFBEnable);
            snapshot.initialized = initialized_;
            snapshot.acquired = deviceAcquired_;
            snapshot.panicStopped = panicStopped_;
            snapshot.constantHardware = constantEffect_ != nullptr;
            snapshot.springHardware = springEffect_ != nullptr;
            snapshot.damperHardware = damperEffect_ != nullptr;
            snapshot.periodicHardware = periodicsActive_;
            snapshot.constantCapabilityKnown = constantCapabilityKnown_;
            snapshot.springCapabilityKnown = springCapabilityKnown_;
            snapshot.damperCapabilityKnown = damperCapabilityKnown_;
            snapshot.periodicCapabilityKnown = periodicCapabilityKnown_;
            snapshot.constantDynamic = constantTypeDynamic_ && constantDirectionDynamic_;
            snapshot.springDynamic = springTypeDynamic_;
            snapshot.damperDynamic = damperTypeDynamic_;
            snapshot.periodicDynamic = periodicTypeDynamic_;
            snapshot.constantRestartUpdates = constantRequiresRestart_;
            snapshot.directionLeftTested = directionLeftTested_;
            snapshot.directionRightTested = directionRightTested_;
            snapshot.deviceName = selectedName_;

            if (!Settings::WheelFFBPhysicsSat)
                snapshot.physicsMode = 0;
            else if (!vehicleDynamics_.calibrated())
                snapshot.physicsMode = 1;
            else if (vehicleDynamics_.sampleValid())
                snapshot.physicsMode = 2;
            else
                snapshot.physicsMode = 3;

            if (device_ && deviceAcquired_)
            {
                DWORD state = 0;
                if (SUCCEEDED(device_->GetForceFeedbackState(&state)))
                {
                    snapshot.ffbStateValid = true;
                    snapshot.ffbState = state;
                }
            }
            return snapshot;
        }

        void record_graph(float rawStructural, float postLimiter, float postSlew, float finalOutput)
        {
            auto finite_or_zero = [](float value)
            {
                return std::isfinite(value) ? value : 0.0f;
            };
            graphRaw_[graphWriteIndex_] = finite_or_zero(rawStructural);
            graphLimited_[graphWriteIndex_] = finite_or_zero(postLimiter);
            graphSlew_[graphWriteIndex_] = finite_or_zero(postSlew);
            graphFinal_[graphWriteIndex_] = finite_or_zero(finalOutput);
            graphWriteIndex_ = (graphWriteIndex_ + 1) % WheelFFBGraphSamples;
            graphCount_ = std::min<std::size_t>(graphCount_ + 1, WheelFFBGraphSamples);
        }

        WheelFFBGraphSnapshot graph_snapshot() const
        {
            WheelFFBGraphSnapshot snapshot{};
            snapshot.rawStructural = graphRaw_;
            snapshot.postLimiter = graphLimited_;
            snapshot.postSlew = graphSlew_;
            snapshot.finalOutput = graphFinal_;
            snapshot.count = graphCount_;
            snapshot.offset = graphCount_ == WheelFFBGraphSamples ? graphWriteIndex_ : 0;
            return snapshot;
        }

'''
ffb = insert_before(ffb, marker, methods, 'status/graph methods')

# Capability and graph state members.
needle = '''        bool periodicsActive_ = false;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
        int springStrategy_ = -1;
        int damperStrategy_ = -1;
'''
replacement = '''        bool periodicsActive_ = false;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
        int springStrategy_ = -1;
        int damperStrategy_ = -1;
        bool constantCapabilityKnown_ = false;
        bool springCapabilityKnown_ = false;
        bool damperCapabilityKnown_ = false;
        bool periodicCapabilityKnown_ = false;
        bool constantTypeDynamic_ = true;
        bool constantDirectionDynamic_ = true;
        bool springTypeDynamic_ = true;
        bool damperTypeDynamic_ = true;
        bool periodicTypeDynamic_ = true;
        bool constantRequiresRestart_ = false;
        bool springCapabilityRejected_ = false;
        bool damperCapabilityRejected_ = false;
        bool periodicCapabilityRejected_ = false;
        bool directionLeftTested_ = false;
        bool directionRightTested_ = false;
'''
ffb = replace_once(ffb, needle, replacement, 'capability members')

needle = '''        std::array<std::uint64_t, HeadroomHistogramBins> headroomHistogram_{};
'''
replacement = '''        std::array<float, WheelFFBGraphSamples> graphRaw_{};
        std::array<float, WheelFFBGraphSamples> graphLimited_{};
        std::array<float, WheelFFBGraphSamples> graphSlew_{};
        std::array<float, WheelFFBGraphSamples> graphFinal_{};
        std::size_t graphWriteIndex_ = 0;
        std::size_t graphCount_ = 0;

        std::array<std::uint64_t, HeadroomHistogramBins> headroomHistogram_{};
'''
ffb = replace_once(ffb, needle, replacement, 'graph members')

# Runtime exported functions.
needle = '''WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()
{
    return gWheelFFB.headroom_snapshot();
}

void WheelFFB_ResetHeadroomStats()
'''
replacement = '''WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()
{
    return gWheelFFB.headroom_snapshot();
}

WheelFFBStatusSnapshot WheelFFB_GetStatusSnapshot()
{
    return gWheelFFB.status_snapshot();
}

WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot()
{
    return gWheelFFB.graph_snapshot();
}

void WheelFFB_ResetHeadroomStats()
'''
ffb = replace_once(ffb, needle, replacement, 'runtime exports')

write(path, ffb)

# ---------------------------------------------------------------------------
# F11 UI: VID/PID recommendations, runtime status, revert, graph, slew info.
# ---------------------------------------------------------------------------
path = 'src/overlay/wheel_setup_ui.cpp'
ui = read(path)
ui = replace_once(ui, '#include "hook_mgr.hpp"\n', '#include "hook_mgr.hpp"\n#include "input_manager.hpp"\n', 'include InputManager')

# Device VID/PID.
needle = '''        DWORD axes = 0;
        DWORD buttons = 0;
        DWORD povs = 0;
        bool ffb = false;
'''
replacement = '''        DWORD axes = 0;
        DWORD buttons = 0;
        DWORD povs = 0;
        Uint16 vendor = 0;
        Uint16 product = 0;
        bool ffb = false;
'''
ui = replace_once(ui, needle, replacement, 'DeviceInfo VID/PID')

needle = '''                if (SUCCEEDED(temp->GetCapabilities(&caps)))
                {
                    info.axes = caps.dwAxes;
                    info.buttons = caps.dwButtons;
                    info.povs = caps.dwPOVs;
                    info.ffb = (caps.dwFlags & DIDC_FORCEFEEDBACK) != 0;
                }
                temp->Release();
'''
replacement = '''                if (SUCCEEDED(temp->GetCapabilities(&caps)))
                {
                    info.axes = caps.dwAxes;
                    info.buttons = caps.dwButtons;
                    info.povs = caps.dwPOVs;
                    info.ffb = (caps.dwFlags & DIDC_FORCEFEEDBACK) != 0;
                }
                DIPROPDWORD vidpid{};
                vidpid.diph.dwSize = sizeof(vidpid);
                vidpid.diph.dwHeaderSize = sizeof(vidpid.diph);
                vidpid.diph.dwObj = 0;
                vidpid.diph.dwHow = DIPH_DEVICE;
                if (SUCCEEDED(temp->GetProperty(DIPROP_VIDPID, &vidpid.diph)))
                {
                    info.vendor = LOWORD(vidpid.dwData);
                    info.product = HIWORD(vidpid.dwData);
                }
                temp->Release();
'''
ui = replace_once(ui, needle, replacement, 'read DirectInput VID/PID')

# Insert wheel-FFB saved snapshot utility before public section of WheelSetupWindow.
marker = '    public:\n        Kind kind() const override { return Kind::Tab; }\n'
snapshot_block = '''        struct FfbSettingsSnapshot
        {
            bool valid = false;
            bool enable = false;
            float global = 0.0f;
            float spring = 0.0f;
            float springSaturation = 0.0f;
            float damper = 0.0f;
            float steeringWeight = 0.0f;
            float mechanicalTrail = 0.0f;
            float trailLead = 0.0f;
            bool physicsSat = false;
            float gripLoss = 0.0f;
            float lateralDeadzone = 0.0f;
            float weightTransfer = 0.0f;
            float gearShift = 0.0f;
            float engineIdle = 0.0f;
            float slewRate = 0.0f;
            float road = 0.0f;
            float tire = 0.0f;
            float wall = 0.0f;
            bool hardwareSpring = false;
            bool hardwareDamper = false;
            bool periodic = false;
            bool invertForce = false;
            bool invertSpring = false;
            bool debugLog = false;
            bool telemetry = false;
            bool responseCorrection = false;
            std::string responseLut;
            float maxTorqueNm = 0.0f;
            int vibrationMode = 0;
        };

        FfbSettingsSnapshot capture_ffb_settings() const
        {
            FfbSettingsSnapshot s{};
            s.valid = true;
            s.enable = Settings::WheelFFBEnable;
            s.global = Settings::WheelFFBGlobalStrength;
            s.spring = Settings::WheelFFBSpringStrength;
            s.springSaturation = Settings::WheelFFBSpringSaturation;
            s.damper = Settings::WheelFFBDamperStrength;
            s.steeringWeight = Settings::WheelFFBSteeringWeight;
            s.mechanicalTrail = Settings::WheelFFBMechanicalTrail;
            s.trailLead = Settings::WheelFFBTrailResponseLead;
            s.physicsSat = Settings::WheelFFBPhysicsSat;
            s.gripLoss = Settings::WheelFFBGripLoss;
            s.lateralDeadzone = Settings::WheelFFBLateralDeadzone;
            s.weightTransfer = Settings::WheelFFBWeightTransfer;
            s.gearShift = Settings::WheelFFBGearShift;
            s.engineIdle = Settings::WheelFFBEngineIdle;
            s.slewRate = Settings::WheelFFBSlewRate;
            s.road = Settings::WheelFFBRoadTexture;
            s.tire = Settings::WheelFFBTireSlip;
            s.wall = Settings::WheelFFBWallImpact;
            s.hardwareSpring = Settings::WheelFFBUseHardwareSpring;
            s.hardwareDamper = Settings::WheelFFBUseHardwareDamper;
            s.periodic = Settings::WheelFFBUsePeriodicEffects;
            s.invertForce = Settings::WheelFFBInvertForce;
            s.invertSpring = Settings::WheelFFBInvertSpring;
            s.debugLog = Settings::WheelFFBDebugLog;
            s.telemetry = Settings::WheelFFBTelemetry;
            s.responseCorrection = Settings::WheelFFBResponseCorrection;
            s.responseLut = Settings::WheelFFBResponseLUT.get();
            s.maxTorqueNm = Settings::WheelFFBMaxTorqueNm;
            s.vibrationMode = Settings::VibrationMode;
            return s;
        }

        void restore_ffb_settings(const FfbSettingsSnapshot& s)
        {
            if (!s.valid) return;
            Settings::WheelFFBEnable = s.enable;
            Settings::WheelFFBGlobalStrength = s.global;
            Settings::WheelFFBSpringStrength = s.spring;
            Settings::WheelFFBSpringSaturation = s.springSaturation;
            Settings::WheelFFBDamperStrength = s.damper;
            Settings::WheelFFBSteeringWeight = s.steeringWeight;
            Settings::WheelFFBMechanicalTrail = s.mechanicalTrail;
            Settings::WheelFFBTrailResponseLead = s.trailLead;
            Settings::WheelFFBPhysicsSat = s.physicsSat;
            Settings::WheelFFBGripLoss = s.gripLoss;
            Settings::WheelFFBLateralDeadzone = s.lateralDeadzone;
            Settings::WheelFFBWeightTransfer = s.weightTransfer;
            Settings::WheelFFBGearShift = s.gearShift;
            Settings::WheelFFBEngineIdle = s.engineIdle;
            Settings::WheelFFBSlewRate = s.slewRate;
            Settings::WheelFFBRoadTexture = s.road;
            Settings::WheelFFBTireSlip = s.tire;
            Settings::WheelFFBWallImpact = s.wall;
            Settings::WheelFFBUseHardwareSpring = s.hardwareSpring;
            Settings::WheelFFBUseHardwareDamper = s.hardwareDamper;
            Settings::WheelFFBUsePeriodicEffects = s.periodic;
            Settings::WheelFFBInvertForce = s.invertForce;
            Settings::WheelFFBInvertSpring = s.invertSpring;
            Settings::WheelFFBDebugLog = s.debugLog;
            Settings::WheelFFBTelemetry = s.telemetry;
            Settings::WheelFFBResponseCorrection = s.responseCorrection;
            Settings::WheelFFBResponseLUT = s.responseLut;
            Settings::WheelFFBMaxTorqueNm = s.maxTorqueNm;
            Settings::VibrationMode = s.vibrationMode;
        }

        std::pair<Uint16, Uint16> steering_vidpid() const
        {
            const auto& bindings = InputManager::instance.actionFor(
                InputManager::ActionKind::Volume, int(ADChannel::Steering)).bindings();
            for (const auto& binding : bindings)
                if (binding.isRawDevice() && binding.deviceVendor != 0 && binding.deviceProduct != 0)
                    return { binding.deviceVendor, binding.deviceProduct };
            return { 0, 0 };
        }

'''
ui = insert_before(ui, marker, snapshot_block, 'insert UI helpers')

# Need a baseline snapshot member near ffbDirty. Locate and extend.
needle = '        bool ffbDirty_ = false;\n'
if needle not in ui:
    # older layout uses tabs/spaces; regex fallback
    match = re.search(r'(\s+bool ffbDirty_ = false;\n)', ui)
    if not match:
        raise RuntimeError('ffbDirty_ member not found')
    ui = ui[:match.end()] + match.group(1).split('bool')[0] + 'FfbSettingsSnapshot ffbSavedSnapshot_{};\n' + ui[match.end():]
else:
    ui = replace_once(ui, needle, needle + '        FfbSettingsSnapshot ffbSavedSnapshot_{};\n', 'FFB saved snapshot member')

# Render captures clean baseline before any live edit.
needle = '''        void render(bool) override
        {
            listen_for_binding();
            const auto track_ffb_change = [this](bool changed)
'''
replacement = '''        void render(bool) override
        {
            listen_for_binding();
            if (!ffbDirty_)
                ffbSavedSnapshot_ = capture_ffb_settings();
            const auto track_ffb_change = [this](bool changed)
'''
ui = replace_once(ui, needle, replacement, 'capture clean FFB baseline')

# Device labels get VID/PID recommendation.
needle = '''                    for (const auto& dev : devices)
                    {
                        if (ffbOnly && !dev.ffb)
                            continue;
                        const bool selected = isSelectedDevice(dev);
                        const std::string item = dev.name + "##" + label + dev.guidKey;
                        if (ImGui::Selectable(item.c_str(), selected))
'''
replacement = '''                    const auto [steeringVendor, steeringProduct] = steering_vidpid();
                    for (const auto& dev : devices)
                    {
                        if (ffbOnly && !dev.ffb)
                            continue;
                        const bool selected = isSelectedDevice(dev);
                        const bool recommended = ffbOutput && steeringVendor != 0 && steeringProduct != 0 &&
                            dev.vendor == steeringVendor && dev.product == steeringProduct;
                        const std::string item = dev.name +
                            (recommended ? "  [Recommended for steering]" : "") +
                            "##" + label + dev.guidKey;
                        if (ImGui::Selectable(item.c_str(), selected))
'''
ui = replace_once(ui, needle, replacement, 'VIDPID recommended FFB device')

needle = '''                        ImGui::TextDisabled("%lu axes / %lu buttons / %lu POV / FFB %s / GUID %s",
                            dev.axes, dev.buttons, dev.povs, dev.ffb ? "yes" : "no", dev.guidKey.c_str());
'''
replacement = '''                        ImGui::TextDisabled("%lu axes / %lu buttons / %lu POV / FFB %s / VID:%04X PID:%04X / GUID %s",
                            dev.axes, dev.buttons, dev.povs, dev.ffb ? "yes" : "no",
                            unsigned(dev.vendor), unsigned(dev.product), dev.guidKey.c_str());
'''
ui = replace_once(ui, needle, replacement, 'show VIDPID')

# Add runtime status after FFB output chooser before profiles.
needle = '''            draw_ffb_profiles();
'''
status_block = '''            ImGui::SeparatorText("FFB Runtime Status");
            const WheelFFBStatusSnapshot runtimeStatus = WheelFFB_GetStatusSnapshot();
            const char* physicsLabel = runtimeStatus.physicsMode == 2 ? "ACTIVE" :
                runtimeStatus.physicsMode == 1 ? "CAL" :
                runtimeStatus.physicsMode == 3 ? "FALLBACK" : "OFF";
            ImGui::Text("Output: %s", runtimeStatus.deviceName.empty() ? "not initialized" : runtimeStatus.deviceName.c_str());
            ImGui::SameLine();
            ImGui::TextDisabled("| Physics SAT %s | %s",
                physicsLabel, runtimeStatus.acquired ? "acquired" : "not acquired");
            if (runtimeStatus.ffbStateValid)
            {
                if (runtimeStatus.ffbState & DIGFFS_DEVICELOST)
                    ImGui::TextColored(ImVec4(1.0f, 0.35f, 0.25f, 1.0f), "DirectInput reports DEVICE LOST; automatic recovery is active.");
                if (runtimeStatus.ffbState & DIGFFS_ACTUATORSOFF)
                    ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f), "Wheel actuators are OFF.");
                if (runtimeStatus.ffbState & DIGFFS_POWEROFF)
                    ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f), "Wheel reports force-feedback power OFF.");
                if (runtimeStatus.ffbState & DIGFFS_SAFETYSWITCHOFF)
                    ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f), "Wheel safety switch is OFF; the game will not force it back on.");
                if (runtimeStatus.ffbState & DIGFFS_USERFFSWITCHOFF)
                    ImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f), "Wheel user FFB switch is OFF; the game will not override it.");
            }
            ImGui::TextDisabled("Constant: %s%s | Spring: %s%s | Damper: %s%s | Road/Slip: %s%s",
                runtimeStatus.constantHardware ? "HW" : "unavailable",
                runtimeStatus.constantRestartUpdates ? " (stop/start updates)" : "",
                runtimeStatus.springHardware ? "HW" : "software",
                runtimeStatus.springCapabilityKnown && !runtimeStatus.springDynamic ? " (driver non-dynamic)" : "",
                runtimeStatus.damperHardware ? "HW" : "software",
                runtimeStatus.damperCapabilityKnown && !runtimeStatus.damperDynamic ? " (driver non-dynamic)" : "",
                runtimeStatus.periodicHardware ? "HW" : "software",
                runtimeStatus.periodicCapabilityKnown && !runtimeStatus.periodicDynamic ? " (driver non-dynamic)" : "");
            ImGui::TextDisabled("Direction test run: Left %s / Right %s",
                runtimeStatus.directionLeftTested ? "yes" : "no",
                runtimeStatus.directionRightTested ? "yes" : "no");

            draw_ffb_profiles();
'''
ui = replace_once(ui, needle, status_block, 'runtime status panel')

# Slew response explanation and R3 defaults to 0.060.
needle = '''                track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
'''
replacement = '''                track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
                const float slewValue = std::max(0.01f, float(Settings::WheelFFBSlewRate));
                ImGui::TextDisabled("Approx. 0->100%% structural response limit: %.0f ms at 60 Hz (same-direction unloading is up to 2x faster).",
                    1000.0f / (60.0f * slewValue));
'''
ui = replace_once(ui, needle, replacement, 'slew response timing')
ui = ui.replace('Settings::WheelFFBSlewRate = 0.040f;', 'Settings::WheelFFBSlewRate = 0.060f;', 1)
ui = ui.replace('Settings::WheelFFBSlewRate = 0.045f;', 'Settings::WheelFFBSlewRate = 0.060f;', 1)

# Revert unsaved button next to Save.
needle = '''            if (ImGui::Button(ffbDirty_ ? "Save Force Feedback*" : "Save Force Feedback"))
            {
                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    status_ = "Force feedback settings saved.";
                }
                else
                    status_ = "Could not save force feedback settings.";
            }

            ImGui::SeparatorText("FFB Headroom / Clipping");
'''
replacement = '''            if (ImGui::Button(ffbDirty_ ? "Save Force Feedback*" : "Save Force Feedback"))
            {
                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    ffbSavedSnapshot_ = capture_ffb_settings();
                    status_ = "Force feedback settings saved.";
                }
                else
                    status_ = "Could not save force feedback settings.";
            }
            if (ffbDirty_)
            {
                ImGui::SameLine();
                if (ImGui::Button("Revert unsaved FFB"))
                {
                    restore_ffb_settings(ffbSavedSnapshot_);
                    ffbDirty_ = false;
                    WheelFFB_RequestSettingsTransition();
                    status_ = "Reverted to the last saved/loaded FFB settings.";
                }
            }

            ImGui::SeparatorText("FFB Headroom / Clipping");
'''
ui = replace_once(ui, needle, replacement, 'revert unsaved FFB')

# Live graphs after headroom reset button.
needle = '''            if (ImGui::Button("Reset headroom analysis"))
                WheelFFB_ResetHeadroomStats();

            ImGui::SeparatorText("Safe direction test");
'''
graph_block = '''            if (ImGui::Button("Reset headroom analysis"))
                WheelFFB_ResetHeadroomStats();

            if (ImGui::CollapsingHeader("Live FFB signal graph"))
            {
                const WheelFFBGraphSnapshot graph = WheelFFB_GetGraphSnapshot();
                if (graph.count == 0)
                    ImGui::TextDisabled("Drive for a moment to collect FFB samples; opening F11 freezes the most recent history.");
                else
                {
                    const int count = static_cast<int>(graph.count);
                    const int offset = static_cast<int>(graph.offset);
                    ImGui::PlotLines("Raw structural", graph.rawStructural.data(), count, offset, nullptr, -1.5f, 1.5f, ImVec2(0, 46));
                    ImGui::PlotLines("Post limiter", graph.postLimiter.data(), count, offset, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
                    ImGui::PlotLines("Post slew", graph.postSlew.data(), count, offset, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
                    ImGui::PlotLines("Final DirectInput", graph.finalOutput.data(), count, offset, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
                    ImGui::TextDisabled("About 3 seconds at 60 Hz. Compare raw -> limiter -> slew -> final output to locate lost detail or clipping.");
                }
            }

            ImGui::SeparatorText("Safe direction test");
'''
ui = replace_once(ui, needle, graph_block, 'live FFB graphs')

write(path, ui)

# ---------------------------------------------------------------------------
# Input Bindings: integrated axis calibration, conflict warnings, setup status,
# and visible inverted/highlighted manual binding target.
# ---------------------------------------------------------------------------
path = 'src/overlay/input_bindings_ui.cpp'
inp = read(path)
inp = replace_once(inp, '#include "wheel_profile_store.hpp"\n', '#include "wheel_profile_store.hpp"\n#include "wheel_ffb_runtime.hpp"\n', 'input runtime include')

# State for wizard calibration.
needle = '    bool quickSetupTimedOut = false;\n'
replacement = '    bool quickSetupTimedOut = false;\n\tbool quickSetupResumeAfterCalibration = false;\n'
if needle in inp:
    inp = replace_once(inp, needle, replacement, 'quick calibration state')
else:
    inp = replace_once(inp, '\tbool quickSetupTimedOut = false;\n', '\tbool quickSetupTimedOut = false;\n\tbool quickSetupResumeAfterCalibration = false;\n', 'quick calibration state tabs')

# Helpers after same_source_family.
marker = '\tvoid begin_listening(const Selection& target, int index)\n'
helpers = '''\tstatic bool same_physical_control(const InputBinding& a, const InputBinding& b)
\t{
\t\tif (a.kind != b.kind)
\t\t\treturn false;
\t\tswitch (a.kind)
\t\t{
\t\tcase InputBinding::Kind::Key:
\t\t\treturn a.key == b.key;
\t\tcase InputBinding::Kind::PadButton:
\t\t\treturn a.button == b.button;
\t\tcase InputBinding::Kind::PadAxis:
\t\t\treturn a.axis == b.axis;
\t\tcase InputBinding::Kind::JoyButton:
\t\tcase InputBinding::Kind::JoyAxis:
\t\t\treturn a.deviceGuid == b.deviceGuid && a.deviceOccurrence == b.deviceOccurrence &&
\t\t\t\ta.controlIndex == b.controlIndex;
\t\tcase InputBinding::Kind::JoyHat:
\t\t\treturn a.deviceGuid == b.deviceGuid && a.deviceOccurrence == b.deviceOccurrence &&
\t\t\t\ta.controlIndex == b.controlIndex && a.hatMask == b.hatMask;
\t\tdefault:
\t\t\treturn false;
\t\t}
\t}

\tstatic std::string conflict_summary(const InputBinding& candidate, const Selection& target)
\t{
\t\tstd::string result;
\t\tfor (const ActionListEntry& entry : ActionList)
\t\t{
\t\t\tconst Selection action{ entry.kind, entry.index };
\t\t\tif (action == target)
\t\t\t\tcontinue;
\t\t\tfor (const InputBinding& existing : action_for(action).bindings())
\t\t\t{
\t\t\t\tif (!same_physical_control(existing, candidate))
\t\t\t\t\tcontinue;
\t\t\t\tif (!result.empty()) result += ", ";
\t\t\t\tresult += name_for(action);
\t\t\t\tbreak;
\t\t\t}
\t\t}
\t\treturn result;
\t}

\tvoid continue_quick_setup_after_calibration()
\t{
\t\tif (!quickSetupResumeAfterCalibration)
\t\t\treturn;
\t\tquickSetupResumeAfterCalibration = false;
\t\tif (quickSetupStep < int(std::size(QuickSetupSteps)))
\t\t\tbegin_listening(quick_setup_selection(quickSetupStep), -1);
\t\telse
\t\t{
\t\t\tquickSetupActive = false;
\t\t\tquickSetupComplete = true;
\t\t\tisListeningForInput = ListenState::False;
\t\t}
\t}

'''
inp = insert_before(inp, marker, helpers, 'input helper block')

# Make manual target visible by selecting action.
needle = '''\t\tbindTarget = target;
\t\tbindIndex = index;
'''
replacement = '''\t\tbindTarget = target;
\t\tbindIndex = index;
\t\tselected = target;
'''
inp = replace_once(inp, needle, replacement, 'select manual bind target')

# Manual commit conflict status.
needle = '''\t\tconst auto commit = [&](const InputBinding& binding)
\t\t{
\t\t\tif (quickSetupActive)
'''
replacement = '''\t\tconst auto commit = [&](const InputBinding& binding)
\t\t{
\t\t\tconst std::string conflicts = conflict_summary(binding, bindTarget);
\t\t\tif (!conflicts.empty())
\t\t\t\tpersistenceStatus = "Shared control: also bound to " + conflicts + ". Sharing is allowed if intentional.";
\t\t\tif (quickSetupActive)
'''
inp = replace_once(inp, needle, replacement, 'manual conflict status')

# Calibration save/cancel resumes Quick Setup.
needle = '''\t\t\t\tunsavedChanges = true;
\t\t\t\tcalibrationOpen = false;
\t\t\t\tImGui::CloseCurrentPopup();
\t\t\t}
'''
replacement = '''\t\t\t\tunsavedChanges = true;
\t\t\t\tcalibrationOpen = false;
\t\t\t\tImGui::CloseCurrentPopup();
\t\t\t\tcontinue_quick_setup_after_calibration();
\t\t\t}
'''
inp = replace_once(inp, needle, replacement, 'resume after saved calibration')

needle = '''\t\tif (ImGui::Button("Cancel"))
\t\t{
\t\t\tcalibrationOpen = false;
\t\t\tImGui::CloseCurrentPopup();
\t\t}
'''
replacement = '''\t\tif (ImGui::Button(quickSetupResumeAfterCalibration ? "Skip calibration" : "Cancel"))
\t\t{
\t\t\tcalibrationOpen = false;
\t\t\tImGui::CloseCurrentPopup();
\t\t\tcontinue_quick_setup_after_calibration();
\t\t}
'''
inp = replace_once(inp, needle, replacement, 'skip calibration in wizard')

# Highlight the exact manual rebind button/row using inverse colors.
needle = '''\t\t\t\tif (ImGui::Button(label.c_str(), ImVec2(-FLT_MIN, 0)))
\t\t\t\t\tbegin_listening(selected, i);
\t\t\t\tif (ImGui::IsItemHovered())
'''
replacement = '''\t\t\t\tconst bool listeningHere = isListeningForInput != ListenState::False && bindTarget == selected && bindIndex == i;
\t\t\t\tif (listeningHere)
\t\t\t\t{
\t\t\t\t\tImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\t\t\tImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\t\t\tImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
\t\t\t\t}
\t\t\t\tif (ImGui::Button(label.c_str(), ImVec2(-FLT_MIN, 0)))
\t\t\t\t\tbegin_listening(selected, i);
\t\t\t\tif (listeningHere)
\t\t\t\t\tImGui::PopStyleColor(3);
\t\t\t\tif (ImGui::IsItemHovered())
'''
inp = replace_once(inp, needle, replacement, 'manual binding inverse highlight')

# Highlight Add binding when that is the current listen target.
needle = '''\t\tif (ImGui::Button("+ Add binding"))
\t\t\tbegin_listening(selected, -1);
'''
replacement = '''\t\tconst bool listeningForAdd = isListeningForInput != ListenState::False && bindTarget == selected && bindIndex < 0 && !quickSetupActive;
\t\tif (listeningForAdd)
\t\t{
\t\t\tImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\tImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\tImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
\t\t}
\t\tif (ImGui::Button("+ Add binding"))
\t\t\tbegin_listening(selected, -1);
\t\tif (listeningForAdd)
\t\t\tImGui::PopStyleColor(3);
'''
inp = replace_once(inp, needle, replacement, 'highlight add binding')

# Quick candidate conflict warning and automatic calibration for raw axes.
needle = '''\t\t\t\tImGui::TextWrapped("Confirm this input before Quick Setup moves to the next control.");
\t\t\t\tif (ImGui::Button("Use this input"))
'''
replacement = '''\t\t\t\tImGui::TextWrapped("Confirm this input before Quick Setup moves to the next control.");
\t\t\t\tconst std::string conflicts = conflict_summary(*quickSetupCandidate, bindTarget);
\t\t\t\tif (!conflicts.empty())
\t\t\t\t\tImGui::TextColored(ImVec4(1.0f, 0.65f, 0.25f, 1.0f), "Already used by: %s (sharing is allowed if intentional)", conflicts.c_str());
\t\t\t\tif (ImGui::Button("Use this input"))
'''
inp = replace_once(inp, needle, replacement, 'quick conflict warning')

old = '''\t\t\t\t\tauto& bindings = action_for(bindTarget).bindings();
\t\t\t\t\tstd::erase_if(bindings, [&](const InputBinding& existing)
\t\t\t\t\t\t{ return same_source_family(existing, *quickSetupCandidate); });
\t\t\t\t\taction_for(bindTarget).add(*quickSetupCandidate);
\t\t\t\t\treleaseGuardBinding = *quickSetupCandidate;
\t\t\t\t\tquickSetupCandidate.reset();
\t\t\t\t\t++quickSetupStep;
\t\t\t\t\tunsavedChanges = true;
\t\t\t\t\tisListeningForInput = ListenState::WaitForBindButtonRelease;
\t\t\t\t\tImGui::CloseCurrentPopup();
'''
new = '''\t\t\t\t\tauto& bindings = action_for(bindTarget).bindings();
\t\t\t\t\tconst InputBinding accepted = *quickSetupCandidate;
\t\t\t\t\tstd::erase_if(bindings, [&](const InputBinding& existing)
\t\t\t\t\t\t{ return same_source_family(existing, accepted); });
\t\t\t\t\taction_for(bindTarget).add(accepted);
\t\t\t\t\treleaseGuardBinding = accepted;
\t\t\t\t\tquickSetupCandidate.reset();
\t\t\t\t\t++quickSetupStep;
\t\t\t\t\tunsavedChanges = true;
\t\t\t\t\tif (accepted.kind == InputBinding::Kind::JoyAxis && bindTarget.isVolume())
\t\t\t\t\t{
\t\t\t\t\t\tisListeningForInput = ListenState::False;
\t\t\t\t\t\tquickSetupResumeAfterCalibration = true;
\t\t\t\t\t\tbegin_calibration(bindTarget, int(bindings.size()) - 1);
\t\t\t\t\t}
\t\t\t\t\telse
\t\t\t\t\t\tisListeningForInput = ListenState::WaitForBindButtonRelease;
\t\t\t\t\tImGui::CloseCurrentPopup();
'''
inp = replace_once(inp, old, new, 'wizard axis calibration integration')

# Clear resume flag on restore/start.
inp = inp.replace('\t\tquickSetupTimedOut = false;\n\t\tunsavedChanges = quickSetupPreviousUnsaved;', '\t\tquickSetupTimedOut = false;\n\t\tquickSetupResumeAfterCalibration = false;\n\t\tunsavedChanges = quickSetupPreviousUnsaved;', 1)
inp = inp.replace('\t\tquickSetupActive = true;\n\t\tbegin_listening', '\t\tquickSetupActive = true;\n\t\tquickSetupResumeAfterCalibration = false;\n\t\tbegin_listening', 1)

# Listening popup explicitly names the action being configured.
needle = '''\t\t\telse
\t\t\t\tImGui::Text("Press any input to bind to %s", bindingName.c_str());
'''
replacement = '''\t\t\telse
\t\t\t{
\t\t\t\tImGui::TextColored(ImGui::GetStyle().Colors[ImGuiCol_CheckMark], "Listening for: %s", bindingName.c_str());
\t\t\t\tImGui::Text("Press the control you want to assign.");
\t\t\t}
'''
inp = replace_once(inp, needle, replacement, 'manual listening target text')

# Setup status tab helper before render.
marker = 'public:\n\tvoid render(bool overlayEnabled) override\n'
status_helper = '''\tbool has_binding(const Selection& selection) const
\t{
\t\treturn !action_for(selection).bindings().empty();
\t}

\tvoid draw_setup_status()
\t{
\t\tauto status_line = [](const char* label, bool ok, const char* detail = nullptr)
\t\t{
\t\t\tImGui::TextColored(ok ? ImVec4(0.35f, 0.9f, 0.45f, 1.0f) : ImVec4(1.0f, 0.65f, 0.25f, 1.0f),
\t\t\t\t"%s  %s", ok ? "[OK]" : "[ ]", label);
\t\t\tif (detail && detail[0])
\t\t\t{
\t\t\t\tImGui::SameLine();
\t\t\t\tImGui::TextDisabled("%s", detail);
\t\t\t}
\t\t};

\t\tconst bool steering = has_binding({ Vol, int(ADChannel::Steering) });
\t\tconst bool throttle = has_binding({ Vol, int(ADChannel::Acceleration) });
\t\tconst bool brake = has_binding({ Vol, int(ADChannel::Brake) });
\t\tconst bool shifts = has_binding({ Sw, int(SwitchId::GearUp) }) && has_binding({ Sw, int(SwitchId::GearDown) });
\t\tconst bool menuCore = has_binding({ Sw, int(SwitchId::Start) }) && has_binding({ Sw, int(SwitchId::A) }) && has_binding({ Sw, int(SwitchId::B) });
\t\tconst bool menuNav = has_binding({ Sw, int(SwitchId::SelectionUp) }) && has_binding({ Sw, int(SwitchId::SelectionDown) }) &&
\t\t\thas_binding({ Sw, int(SwitchId::SelectionLeft) }) && has_binding({ Sw, int(SwitchId::SelectionRight) });
\t\tconst WheelFFBStatusSnapshot ffb = WheelFFB_GetStatusSnapshot();
\t\tconst bool ffbReady = !ffb.enabled || (ffb.initialized && ffb.acquired && ffb.constantHardware);

\t\tImGui::SeparatorText("Ready to Drive");
\t\tstatus_line("Steering binding", steering);
\t\tstatus_line("Accelerator + brake", throttle && brake, "Quick Setup now calibrates raw wheel/pedal axes inline.");
\t\tstatus_line("Shift up/down", shifts);
\t\tstatus_line("Start / Confirm / Back", menuCore);
\t\tstatus_line("Menu directions", menuNav);
\t\tstatus_line("FFB output", ffbReady, ffb.deviceName.empty() ? "Open F11 > Force Feedback to choose an output." : ffb.deviceName.c_str());
\t\tstatus_line("FFB direction test run", !ffb.enabled || (ffb.directionLeftTested && ffb.directionRightTested),
\t\t\tffb.enabled ? "Run both 20% direction tests in Force Feedback and confirm the physical direction." : "FFB disabled");
\t\tstatus_line("Bindings saved", !unsavedChanges, unsavedChanges ? "Current edits are live but not durable yet." : nullptr);

\t\tconst bool ready = steering && throttle && brake && shifts && menuCore && menuNav && ffbReady &&
\t\t\t(!ffb.enabled || (ffb.directionLeftTested && ffb.directionRightTested)) && !unsavedChanges;
\t\tImGui::Spacing();
\t\tif (ready)
\t\t\tImGui::TextColored(ImVec4(0.35f, 0.9f, 0.45f, 1.0f), "Setup is ready for driving.");
\t\telse
\t\t\tImGui::TextWrapped("Complete the unchecked items above. Axis calibration can be repeated at any time from Bindings > Calibrate.");
\t\tif (ImGui::Button("Run Quick Setup"))
\t\t\tstart_quick_setup();
\t}

'''
inp = insert_before(inp, marker, status_helper, 'setup status helper')

# Add Setup tab before Bindings.
needle = '''\t\t\tif (ImGui::BeginTabBar("##sections"))
\t\t\t{
\t\t\t\tif (ImGui::BeginTabItem("Bindings"))
'''
replacement = '''\t\t\tif (ImGui::BeginTabBar("##sections"))
\t\t\t{
\t\t\t\tif (ImGui::BeginTabItem("Setup"))
\t\t\t\t{
\t\t\t\t\tdraw_setup_status();
\t\t\t\t\tImGui::EndTabItem();
\t\t\t\t}

\t\t\t\tif (ImGui::BeginTabItem("Bindings"))
'''
inp = replace_once(inp, needle, replacement, 'Setup tab')

write(path, inp)

# ---------------------------------------------------------------------------
# Documentation and verifier guardrails.
# ---------------------------------------------------------------------------
path = 'WHEEL_FFB.md'
doc = read(path)
doc += '''\n\n## Setup and device diagnostics (current)\n\n- Input Bindings now has a **Setup** status tab that summarizes required driving/menu bindings, persistence, FFB output state and whether both safe direction tests have been run.\n- Quick Setup calibrates raw steering/pedal axes inline after capture; **Skip calibration** remains available for unusual devices.\n- During manual rebinding, the exact binding button being configured is shown with inverted colours and the listening popup names the target action.\n- Duplicate physical controls are warned about but remain allowed for intentional shared bindings.\n- FFB Output devices expose HID VID/PID when DirectInput provides it and mark a matching steering-device interface as **Recommended for steering** without forcing selection.\n- The FFB engine queries DirectInput effect dynamic-parameter capabilities. Optional Spring/Damper/Sine effects fall back to software when a driver cannot update them safely while playing; ConstantForce keeps a stop/update/start compatibility path when required.\n- **FFB Runtime Status** reports acquisition, DirectInput state switches and the active HW/SW effect paths. User/safety switch OFF states are reported but never overridden.\n- **Live FFB signal graph** retains roughly three seconds of raw structural, post-limiter, post-slew and final DirectInput output so F11 can show where detail is being compressed.\n- Unsaved live FFB tuning can be restored with **Revert unsaved FFB**.\n- The R3 Physics/Natural starting presets use `SlewRate=0.060`; the UI also reports the approximate 0->100% full-scale response time implied by the 60 Hz structural limiter.\n'''
write(path, doc)

# Update README concise operator note.
path = 'README.md'
readme = read(path)
anchor = '## Wheel / multi-device input'
if anchor in readme and 'Ready to Drive' not in readme:
    idx = readme.index(anchor)
    end = readme.find('\n## ', idx + len(anchor))
    if end < 0: end = len(readme)
    addition = '''\n\nCurrent setup UX also includes a **Setup / Ready to Drive** checklist, inline steering/pedal calibration during Quick Setup, visible manual-binding target highlighting, duplicate-control warnings, DirectInput FFB runtime/capability status, an optional VID/PID-based FFB-output recommendation, live FFB signal graphs, and one-click revert of unsaved FFB tuning.\n'''
    readme = readme[:end] + addition + readme[end:]
write(path, readme)

# Verifier: add source invariants without removing existing protections.
path = 'tools/verify_wheel_ffb_current.py'
verify = read(path)
append = r'''

# Setup/FFB UX and DirectInput capability review guards.
req(ffb, 'GetEffectInfo(&info, guid)', 'DirectInput effect dynamic capability query')
req(ffb, 'GUID_Spring cannot update condition parameters while playing', 'non-dynamic spring uses software fallback')
req(ffb, 'GUID_Damper cannot update condition parameters while playing', 'non-dynamic damper uses software fallback')
req(ffb, 'GUID_Sine cannot update magnitude/period while playing', 'non-dynamic periodic effects use software fallback')
req(ffb, 'constantRequiresRestart_', 'essential ConstantForce has non-dynamic compatibility path')
req(ffb, 'GetForceFeedbackState(&state)', 'DirectInput runtime FFB state is observable')
req(ffb, 'record_graph(', 'live FFB signal history is recorded')
req(ui, 'FFB Runtime Status', 'F11 exposes FFB runtime status')
req(ui, 'Recommended for steering', 'VID/PID matching can recommend FFB output')
req(ui, 'Revert unsaved FFB', 'unsaved live FFB tuning can be reverted')
req(ui, 'Live FFB signal graph', 'F11 exposes live FFB signal graph')
req(ui, 'Approx. 0->100%% structural response limit', 'slew control explains its response-time implication')
req(bindings_ui, 'Ready to Drive', 'Input Bindings exposes setup readiness summary')
req(bindings_ui, 'quickSetupResumeAfterCalibration', 'Quick Setup integrates raw-axis calibration')
req(bindings_ui, 'Already used by:', 'Quick Setup warns about duplicate physical controls')
req(bindings_ui, 'Listening for:', 'manual binding popup names its target')
req(bindings_ui, 'ImGuiCol_WindowBg', 'manual binding target uses visible inverted button styling')
req(bindings_ui, 'Setup##', 'noop') if False else None
'''
if 'DirectInput effect dynamic capability query' not in verify:
    verify += append
write(path, verify)

# Build payload markers for future normal CI.
path = '.github/workflows/build.yml'
build = read(path)
needle = '            "Test Left (20%)"\n'
replacement = '''            "Test Left (20%)"
            "FFB Runtime Status"
            "Revert unsaved FFB"
            "Live FFB signal graph"
            "Ready to Drive"
            "Listening for:"
            "Recommended for steering"
'''
build = replace_once(build, needle, replacement, 'build marker expansion')
write(path, build)

print('complete FFB + setup UX upgrade patch applied')
