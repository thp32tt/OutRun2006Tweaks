from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8', newline='\n')


def rep(path, old, new, count=1):
    text = read(path)
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f'{path}: expected {count} matches, found {actual}: {old[:100]!r}')
    write(path, text.replace(old, new, count))

# ---------------------------------------------------------------------------
# Runtime API: status + 3-second force graph.
# ---------------------------------------------------------------------------
write('src/wheel_ffb_runtime.hpp', r'''#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

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
    bool initialized = false;
    bool acquired = false;
    bool outputOwner = false;
    bool ffbStateValid = false;
    bool actuatorsOn = false;
    bool powerOn = false;
    bool safetySwitchOn = false;
    bool userSwitchOn = false;
    bool paused = false;
    bool deviceLost = false;
    bool constantEffect = false;
    bool springEffect = false;
    bool damperEffect = false;
    bool periodicEffects = false;
    bool constantCapsKnown = false;
    bool constantDynamic = false;
    bool polarDirectionDynamic = false;
    bool springCapsKnown = false;
    bool springDynamic = false;
    bool damperCapsKnown = false;
    bool damperDynamic = false;
    bool periodicCapsKnown = false;
    bool periodicDynamic = false;
    bool directionTested = false;
};

inline constexpr std::size_t WheelFFBGraphCapacity = 180;
struct WheelFFBGraphSnapshot
{
    std::size_t count = 0;
    std::array<float, WheelFFBGraphCapacity> rawStructural{};
    std::array<float, WheelFFBGraphCapacity> softLimited{};
    std::array<float, WheelFFBGraphCapacity> postSlew{};
    std::array<float, WheelFFBGraphCapacity> finalOutput{};
};

void WheelFFB_RequestDirectionTest(int direction);
void WheelFFB_RequestSettingsTransition();
WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot();
WheelFFBStatusSnapshot WheelFFB_GetStatusSnapshot();
WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot();
void WheelFFB_ResetHeadroomStats();
''')

# ---------------------------------------------------------------------------
# FFB engine: capability probing, status/graph, faster stale-torque release.
# ---------------------------------------------------------------------------
rep('src/hooks_wheel_ffb.cpp', '''    Setting<float> WheelFFBSlewRate{
        "WheelFFB", "SlewRate", 0.06f,
        "Maximum structural-force change per 60 Hz tick, normalized 0..1.", Range<float>{ 0.01f, 1.0f }
    };
''', '''    Setting<float> WheelFFBSlewRate{
        "WheelFFB", "SlewRate", 0.06f,
        "Maximum normal structural-force build change per 60 Hz tick, normalized 0..1.", Range<float>{ 0.01f, 1.0f }
    };

    Setting<float> WheelFFBReversalReleaseRate{
        "WheelFFB", "ReversalReleaseRate", 0.12f,
        "Dedicated stale-torque release rate when SAT changes direction. Higher values reduce counter-steer latency without accelerating normal force build.",
        Range<float>{ 0.02f, 1.0f }
    };
''')

# Insert live capability helper before ConstantForce creation.
rep('src/hooks_wheel_ffb.cpp', '''        bool create_constant_effect()
        {
            if (!device_)
                return false;
''', '''        bool query_dynamic_effect_capability(
            REFGUID effectGuid, const char* label, DWORD required,
            bool& known, DWORD& dynamicParams)
        {
            known = false;
            dynamicParams = 0;
            if (!device_)
                return false;

            DIEFFECTINFOA info{};
            info.dwSize = sizeof(info);
            const HRESULT hr = device_->GetEffectInfo(&info, effectGuid);
            if (FAILED(hr))
            {
                // Some older drivers do not expose useful effect metadata even
                // though SetParameters works. Preserve the proven legacy path
                // when capability discovery itself is unavailable.
                spdlog::warn(
                    "WheelFFB: GetEffectInfo({}) failed (0x{:08X}); keeping compatibility behavior",
                    label, (unsigned)hr);
                return true;
            }

            known = true;
            dynamicParams = info.dwDynamicParams;
            const bool supported = (dynamicParams & required) == required;
            spdlog::info(
                "WheelFFB: {} dynamic params=0x{:08X}, required=0x{:08X}, live={}",
                label, (unsigned)dynamicParams, (unsigned)required, supported);
            return supported;
        }

        bool create_constant_effect()
        {
            if (!device_)
                return false;

            const bool liveMagnitude = query_dynamic_effect_capability(
                GUID_ConstantForce, "ConstantForce", DIEP_TYPESPECIFICPARAMS,
                constantCapsKnown_, constantDynamicParams_);
            if (constantCapsKnown_ && !liveMagnitude)
            {
                spdlog::error(
                    "WheelFFB: ConstantForce reports no live magnitude update support; rejecting this FFB interface");
                return false;
            }
''')

# Only use 2-axis POLAR when direction can be changed while playing.
rep('src/hooks_wheel_ffb.cpp', '''            HRESULT hr = E_FAIL;
            if (actuatorAxes_.size() > 1)
            {
''', '''            HRESULT hr = E_FAIL;
            const bool polarDirectionDynamic =
                !constantCapsKnown_ || (constantDynamicParams_ & DIEP_DIRECTION) != 0;
            if (actuatorAxes_.size() > 1 && polarDirectionDynamic)
            {
''')

# Spring/damper/periodic prefer software fallback if metadata explicitly says
# live type-specific updates are unsupported.
rep('src/hooks_wheel_ffb.cpp', '''        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring)
                return false;
''', '''        bool create_spring_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareSpring)
                return false;
            if (!query_dynamic_effect_capability(
                    GUID_Spring, "GUID_Spring", DIEP_TYPESPECIFICPARAMS,
                    springCapsKnown_, springDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Spring is not safely live-updatable; using software centering");
                return false;
            }
''')
rep('src/hooks_wheel_ffb.cpp', '''        bool create_damper_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareDamper)
                return false;
''', '''        bool create_damper_effect()
        {
            if (!device_ || !Settings::WheelFFBUseHardwareDamper)
                return false;
            if (!query_dynamic_effect_capability(
                    GUID_Damper, "GUID_Damper", DIEP_TYPESPECIFICPARAMS,
                    damperCapsKnown_, damperDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Damper is not safely live-updatable; using software damping");
                return false;
            }
''')
rep('src/hooks_wheel_ffb.cpp', '''        IDirectInputEffect* create_periodic_effect(const char* label, float initialHz)
        {
            if (!device_)
                return nullptr;
''', '''        IDirectInputEffect* create_periodic_effect(const char* label, float initialHz)
        {
            if (!device_)
                return nullptr;
            if (!query_dynamic_effect_capability(
                    GUID_Sine, "GUID_Sine", DIEP_TYPESPECIFICPARAMS,
                    periodicCapsKnown_, periodicDynamicParams_))
            {
                spdlog::warn("WheelFFB: GUID_Sine is not safely live-updatable; using ConstantForce vibration fallback");
                return nullptr;
            }
''')

# Add graph recorder before headroom recorder.
rep('src/hooks_wheel_ffb.cpp', '''        void record_headroom(float demand, bool eligible)
        {
''', '''        void record_graph_sample(float rawStructural, float softLimited, float postSlew, float finalOutput)
        {
            const size_t slot = graphWriteIndex_ % WheelFFBGraphCapacity;
            graphRawStructural_[slot] = std::isfinite(rawStructural) ? rawStructural : 0.0f;
            graphSoftLimited_[slot] = std::isfinite(softLimited) ? softLimited : 0.0f;
            graphPostSlew_[slot] = std::isfinite(postSlew) ? postSlew : 0.0f;
            graphFinalOutput_[slot] = std::isfinite(finalOutput) ? finalOutput : 0.0f;
            ++graphWriteIndex_;
            graphCount_ = std::min<std::size_t>(graphCount_ + 1, WheelFFBGraphCapacity);
        }

        void record_headroom(float demand, bool eligible)
        {
''')

# Record final pipeline each driving tick.
rep('src/hooks_wheel_ffb.cpp', '''            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;
            const LONG level = apply_response_correction(levelBeforeResponse);

            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||
''', '''            const LONG levelBeforeResponse = baseSteeringLevel + vibrationLevel;
            const LONG level = apply_response_correction(levelBeforeResponse);
            record_graph_sample(
                total,
                compressed,
                static_cast<float>(structuralLevel) / static_cast<float>(DI_FFNOMINALMAX),
                static_cast<float>(level) / static_cast<float>(DI_FFNOMINALMAX));

            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||
''')

# Dedicated fast stale-torque release on sign reversal.
rep('src/hooks_wheel_ffb.cpp', '''            const LONG releaseMaxSlew = std::min(
                static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2);
            const bool oppositeTorqueDirection =
''', '''            const LONG releaseMaxSlew = std::min(
                static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2);
            const float configuredReversalRelease =
                static_cast<float>(Settings::WheelFFBReversalReleaseRate);
            const float safeReversalRelease = std::isfinite(configuredReversalRelease)
                ? std::clamp(configuredReversalRelease, 0.02f, 1.0f)
                : 0.12f;
            const LONG reversalReleaseMaxSlew = std::max(
                releaseMaxSlew,
                static_cast<LONG>(safeReversalRelease * static_cast<float>(DI_FFNOMINALMAX)));
            const bool oppositeTorqueDirection =
''')
rep('src/hooks_wheel_ffb.cpp', '''                if (std::abs(prevStructuralLevel_) <= releaseMaxSlew)
                    structuralLevel = 0;
                else
                    structuralLevel = prevStructuralLevel_ +
                        (prevStructuralLevel_ > 0 ? -releaseMaxSlew : releaseMaxSlew);
''', '''                if (std::abs(prevStructuralLevel_) <= reversalReleaseMaxSlew)
                    structuralLevel = 0;
                else
                    structuralLevel = prevStructuralLevel_ +
                        (prevStructuralLevel_ > 0 ? -reversalReleaseMaxSlew : reversalReleaseMaxSlew);
''')

# Public snapshots after headroom snapshot.
rep('src/hooks_wheel_ffb.cpp', '''            return result;
        }

        void reset_headroom_stats()
''', '''            return result;
        }

        WheelFFBStatusSnapshot status_snapshot() const
        {
            WheelFFBStatusSnapshot result{};
            result.initialized = initialized_;
            result.acquired = deviceAcquired_;
            result.outputOwner = output_owner_active();
            result.constantEffect = constantEffect_ != nullptr;
            result.springEffect = springEffect_ != nullptr;
            result.damperEffect = damperEffect_ != nullptr;
            result.periodicEffects = periodicsActive_;
            result.constantCapsKnown = constantCapsKnown_;
            result.constantDynamic = !constantCapsKnown_ ||
                (constantDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.polarDirectionDynamic = !constantCapsKnown_ ||
                (constantDynamicParams_ & DIEP_DIRECTION) != 0;
            result.springCapsKnown = springCapsKnown_;
            result.springDynamic = !springCapsKnown_ ||
                (springDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.damperCapsKnown = damperCapsKnown_;
            result.damperDynamic = !damperCapsKnown_ ||
                (damperDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.periodicCapsKnown = periodicCapsKnown_;
            result.periodicDynamic = !periodicCapsKnown_ ||
                (periodicDynamicParams_ & DIEP_TYPESPECIFICPARAMS) != 0;
            result.directionTested = directionTested_;

            if (device_)
            {
                DWORD state = 0;
                if (SUCCEEDED(device_->GetForceFeedbackState(&state)))
                {
                    result.ffbStateValid = true;
                    result.actuatorsOn = (state & DIGFFS_ACTUATORSON) != 0;
                    result.powerOn = (state & DIGFFS_POWERON) != 0;
                    result.safetySwitchOn = (state & DIGFFS_SAFETYSWITCHON) != 0;
                    result.userSwitchOn = (state & DIGFFS_USERFFSWITCHON) != 0;
                    result.paused = (state & DIGFFS_PAUSED) != 0;
                    result.deviceLost = (state & DIGFFS_DEVICELOST) != 0;
                }
            }
            return result;
        }

        WheelFFBGraphSnapshot graph_snapshot() const
        {
            WheelFFBGraphSnapshot result{};
            result.count = graphCount_;
            const size_t start = graphCount_ < WheelFFBGraphCapacity
                ? 0
                : graphWriteIndex_ % WheelFFBGraphCapacity;
            for (size_t i = 0; i < graphCount_; ++i)
            {
                const size_t src = (start + i) % WheelFFBGraphCapacity;
                result.rawStructural[i] = graphRawStructural_[src];
                result.softLimited[i] = graphSoftLimited_[src];
                result.postSlew[i] = graphPostSlew_[src];
                result.finalOutput[i] = graphFinalOutput_[src];
            }
            return result;
        }

        void reset_headroom_stats()
''')

# Direction test completion marker.
rep('src/hooks_wheel_ffb.cpp', '''        void request_direction_test(int direction)
        {
            if (direction == 0)
''', '''        void request_direction_test(int direction)
        {
            if (direction != 0)
                directionTested_ = true;
            if (direction == 0)
''')

# Private state fields.
rep('src/hooks_wheel_ffb.cpp', '''        bool periodicsActive_ = false;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
''', '''        bool periodicsActive_ = false;
        bool directionTested_ = false;
        bool constantCapsKnown_ = false;
        bool springCapsKnown_ = false;
        bool damperCapsKnown_ = false;
        bool periodicCapsKnown_ = false;
        DWORD constantDynamicParams_ = 0;
        DWORD springDynamicParams_ = 0;
        DWORD damperDynamicParams_ = 0;
        DWORD periodicDynamicParams_ = 0;
        int periodicStrategy_ = 1; // Explicitly restart sine effects on every update.
''')
rep('src/hooks_wheel_ffb.cpp', '''        float headroomCurrentDemand_ = 0.0f;
        float headroomPeakDemand_ = 0.0f;

        WheelFFBMath::ResponseLUT responseLut_ = WheelFFBMath::linear_response_lut();
''', '''        float headroomCurrentDemand_ = 0.0f;
        float headroomPeakDemand_ = 0.0f;

        std::array<float, WheelFFBGraphCapacity> graphRawStructural_{};
        std::array<float, WheelFFBGraphCapacity> graphSoftLimited_{};
        std::array<float, WheelFFBGraphCapacity> graphPostSlew_{};
        std::array<float, WheelFFBGraphCapacity> graphFinalOutput_{};
        std::size_t graphWriteIndex_ = 0;
        std::size_t graphCount_ = 0;

        WheelFFBMath::ResponseLUT responseLut_ = WheelFFBMath::linear_response_lut();
''')

# Export runtime snapshots.
rep('src/hooks_wheel_ffb.cpp', '''WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()
{
    return gWheelFFB.headroom_snapshot();
}

void WheelFFB_ResetHeadroomStats()
''', '''WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot()
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
''')

# ---------------------------------------------------------------------------
# Input binding UX: conflict hints, active-listening inversion, calibration in
# Quick Setup completion.
# ---------------------------------------------------------------------------
# Conflict helpers after source-family helper.
rep('src/overlay/input_bindings_ui.cpp', '''\tstatic bool same_source_family(const InputBinding& existing, const InputBinding& candidate)
\t{
''', '''\tstatic bool same_control(const InputBinding& a, const InputBinding& b)
\t{
\t\tif (a.kind != b.kind)
\t\t\treturn false;
\t\tswitch (a.kind)
\t\t{
\t\tcase InputBinding::Kind::Key: return a.key == b.key;
\t\tcase InputBinding::Kind::PadButton: return a.button == b.button;
\t\tcase InputBinding::Kind::PadAxis: return a.axis == b.axis && a.negate == b.negate;
\t\tcase InputBinding::Kind::JoyButton:
\t\tcase InputBinding::Kind::JoyAxis:
\t\tcase InputBinding::Kind::JoyHat:
\t\t{
\t\t\tconst auto* da = InputManager::instance.deviceForBinding(a);
\t\t\tconst auto* db = InputManager::instance.deviceForBinding(b);
\t\t\tconst bool sameDevice = da && db
\t\t\t\t? da->instanceId == db->instanceId
\t\t\t\t: a.deviceGuid == b.deviceGuid && a.deviceOccurrence == b.deviceOccurrence;
\t\t\treturn sameDevice && a.controlIndex == b.controlIndex &&
\t\t\t\t(a.kind != InputBinding::Kind::JoyHat || a.hatMask == b.hatMask);
\t\t}
\t\tdefault: return false;
\t\t}
\t}

\tstatic std::string binding_conflicts(const InputBinding& candidate, const Selection& target)
\t{
\t\tstd::string result;
\t\tfor (const ActionListEntry& entry : ActionList)
\t\t{
\t\t\tconst Selection other{ entry.kind, entry.index };
\t\t\tif (other == target)
\t\t\t\tcontinue;
\t\t\tconst auto& bindings = action_for(other).bindings();
\t\t\tif (std::any_of(bindings.begin(), bindings.end(), [&](const InputBinding& b)
\t\t\t\t{ return same_control(b, candidate); }))
\t\t\t{
\t\t\t\tif (!result.empty()) result += ", ";
\t\t\t\tresult += name_for(other);
\t\t\t}
\t\t}
\t\treturn result;
\t}

\tstatic bool same_source_family(const InputBinding& existing, const InputBinding& candidate)
\t{
''')

# Manual commit conflict notice.
rep('src/overlay/input_bindings_ui.cpp', '''\t\tconst auto commit = [&](const InputBinding& binding)
\t\t{
\t\t\tif (quickSetupActive)
''', '''\t\tconst auto commit = [&](const InputBinding& binding)
\t\t{
\t\t\tconst std::string conflicts = binding_conflicts(binding, bindTarget);
\t\t\tif (!conflicts.empty())
\t\t\t\tpersistenceStatus = "Note: this control is also bound to " + conflicts + ".";
\t\t\tif (quickSetupActive)
''')

# Highlight the exact manual binding button being listened for.
rep('src/overlay/input_bindings_ui.cpp', '''\t\t\t\tif (ImGui::Button(label.c_str(), ImVec2(-FLT_MIN, 0)))
\t\t\t\t\tbegin_listening(selected, i);
\t\t\t\tif (ImGui::IsItemHovered())
''', '''\t\t\t\tconst bool listeningHere = isListeningForInput != ListenState::False &&
\t\t\t\t\t!quickSetupActive && bindTarget == selected && bindIndex == i;
\t\t\t\tif (listeningHere)
\t\t\t\t{
\t\t\t\t\tImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\t\t\tImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
\t\t\t\t}
\t\t\t\tif (ImGui::Button(label.c_str(), ImVec2(-FLT_MIN, 0)))
\t\t\t\t\tbegin_listening(selected, i);
\t\t\t\tif (listeningHere)
\t\t\t\t\tImGui::PopStyleColor(2);
\t\t\t\tif (ImGui::IsItemHovered())
''')
rep('src/overlay/input_bindings_ui.cpp', '''\t\tif (ImGui::Button("+ Add binding"))
\t\t\tbegin_listening(selected, -1);
''', '''\t\tconst bool listeningForNew = isListeningForInput != ListenState::False &&
\t\t\t!quickSetupActive && bindTarget == selected && bindIndex == -1;
\t\tif (listeningForNew)
\t\t{
\t\t\tImGui::PushStyleColor(ImGuiCol_Button, ImGui::GetStyle().Colors[ImGuiCol_Text]);
\t\t\tImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyle().Colors[ImGuiCol_WindowBg]);
\t\t}
\t\tif (ImGui::Button(listeningForNew ? "LISTENING...##addBinding" : "+ Add binding"))
\t\t\tbegin_listening(selected, -1);
\t\tif (listeningForNew)
\t\t\tImGui::PopStyleColor(2);
''')

# Quick Setup conflict warning before accepting candidate.
rep('src/overlay/input_bindings_ui.cpp', '''\t\t\t\tif (const auto* device = manager.deviceForBinding(*quickSetupCandidate))
\t\t\t\t\tImGui::TextDisabled("Device: %s", SDL_GetJoystickName(device->joystick));
\t\t\t\tImGui::TextWrapped("Confirm this input before Quick Setup moves to the next control.");
''', '''\t\t\t\tif (const auto* device = manager.deviceForBinding(*quickSetupCandidate))
\t\t\t\t\tImGui::TextDisabled("Device: %s", SDL_GetJoystickName(device->joystick));
\t\t\t\tconst std::string conflicts = binding_conflicts(*quickSetupCandidate, bindTarget);
\t\t\t\tif (!conflicts.empty())
\t\t\t\t\tImGui::TextColored(ImVec4(1.0f, 0.70f, 0.20f, 1.0f),
\t\t\t\t\t\t"Also bound to: %s", conflicts.c_str());
\t\t\t\tImGui::TextWrapped("Confirm this input before Quick Setup moves to the next control.");
''')

# Calibration helpers before completion dialog.
rep('src/overlay/input_bindings_ui.cpp', '''\tvoid draw_quick_setup_complete(bool& dialogOpen)
\t{
''', '''\tint first_raw_axis_binding(const Selection& selection) const
\t{
\t\tconst auto& bindings = action_for(selection).bindings();
\t\tfor (int i = 0; i < int(bindings.size()); ++i)
\t\t\tif (bindings[i].kind == InputBinding::Kind::JoyAxis)
\t\t\t\treturn i;
\t\treturn -1;
\t}

\tbool axis_calibrated(const Selection& selection) const
\t{
\t\tconst int index = first_raw_axis_binding(selection);
\t\tif (index < 0)
\t\t\treturn true; // SDL gamepad axes already use normalized platform ranges.
\t\tconst auto& binding = action_for(selection).bindings()[index];
\t\tconst int negative = binding.axisRest - binding.axisMinimum;
\t\tconst int positive = binding.axisMaximum - binding.axisRest;
\t\treturn binding.axisMode == InputBinding::AxisMode::Signed
\t\t\t? negative > 4096 && positive > 4096
\t\t\t: (std::max)(negative, positive) > 4096;
\t}

\tvoid quick_calibration_row(const char* label, const Selection& selection)
\t{
\t\tconst int index = first_raw_axis_binding(selection);
\t\tif (index < 0)
\t\t{
\t\t\tImGui::TextDisabled("%s: platform/gamepad calibration", label);
\t\t\treturn;
\t\t}
\t\tconst bool ready = axis_calibrated(selection);
\t\tImGui::TextColored(ready ? ImVec4(0.35f, 0.90f, 0.45f, 1.0f) : ImVec4(1.0f, 0.70f, 0.20f, 1.0f),
\t\t\t"%s: %s", label, ready ? "calibrated" : "needs calibration");
\t\tImGui::SameLine();
\t\tImGui::PushID(label);
\t\tif (ImGui::SmallButton(ready ? "Recalibrate" : "Calibrate now"))
\t\t\tbegin_calibration(selection, index);
\t\tImGui::PopID();
\t}

\tvoid draw_quick_setup_complete(bool& dialogOpen)
\t{
''')
rep('src/overlay/input_bindings_ui.cpp', '''\t\tImGui::Text("Brake");
\t\tImGui::SameLine();
\t\tImGui::ProgressBar(std::clamp(brake, 0.0f, 1.0f), ImVec2(280.0f, 0),
\t\t\tstd::format("{:.2f}", brake).c_str());

\t\tImGui::Spacing();
''', '''\t\tImGui::Text("Brake");
\t\tImGui::SameLine();
\t\tImGui::ProgressBar(std::clamp(brake, 0.0f, 1.0f), ImVec2(280.0f, 0),
\t\t\tstd::format("{:.2f}", brake).c_str());

\t\tImGui::SeparatorText("Guided axis calibration");
\t\tImGui::TextWrapped("Finish wheel center/end-stops and pedal rest/full-travel here before saving. This keeps calibration inside Quick Setup instead of hiding it in the manual editor.");
\t\tquick_calibration_row("Steering", { Vol, int(ADChannel::Steering) });
\t\tquick_calibration_row("Accelerator", { Vol, int(ADChannel::Acceleration) });
\t\tquick_calibration_row("Brake", { Vol, int(ADChannel::Brake) });
\t\tconst bool guidedCalibrationReady =
\t\t\taxis_calibrated({ Vol, int(ADChannel::Steering) }) &&
\t\t\taxis_calibrated({ Vol, int(ADChannel::Acceleration) }) &&
\t\t\taxis_calibrated({ Vol, int(ADChannel::Brake) });
\t\tif (!guidedCalibrationReady)
\t\t\tImGui::TextColored(ImVec4(1.0f, 0.70f, 0.20f, 1.0f),
\t\t\t\t"Raw wheel/pedal axes still need calibration; Save & Drive remains available if you intentionally want the current ranges.");

\t\tImGui::Spacing();
''')
# Draw calibration popup once globally instead of only inside the Bindings tab.
rep('src/overlay/input_bindings_ui.cpp', '''\t\tdraw_calibration_popup();
\t}

\tvoid draw_controllers()
''', '''\t}

\tvoid draw_controllers()
''')
rep('src/overlay/input_bindings_ui.cpp', '''\t\t\tdraw_listening_popup();
\t\t\tdraw_quick_setup_complete(dialogOpen);

\t\t\tImGui::EndPopup();
''', '''\t\t\tdraw_listening_popup();
\t\t\tdraw_quick_setup_complete(dialogOpen);
\t\t\tdraw_calibration_popup();

\t\t\tImGui::EndPopup();
''')

# ---------------------------------------------------------------------------
# Wheel/FFB UI: VID/PID recommendation, status/readiness, graph, revert, release
# rate control and understandable timing.
# ---------------------------------------------------------------------------
rep('src/overlay/wheel_setup_ui.cpp', '''#include "overlay.hpp"
#include "wheel_ffb_math.hpp"
''', '''#include "overlay.hpp"
#include "input_manager.hpp"
#include "wheel_ffb_math.hpp"
''')
rep('src/overlay/wheel_setup_ui.cpp', '''    extern Setting<float> WheelFFBSlewRate;
''', '''    extern Setting<float> WheelFFBSlewRate;
    extern Setting<float> WheelFFBReversalReleaseRate;
''')

# VID/PID fields.
rep('src/overlay/wheel_setup_ui.cpp', '''        DWORD povs = 0;
        bool ffb = false;
''', '''        DWORD povs = 0;
        bool ffb = false;
        std::uint16_t vendor = 0;
        std::uint16_t product = 0;
''')
rep('src/overlay/wheel_setup_ui.cpp', '''                if (SUCCEEDED(temp->GetCapabilities(&caps)))
                {
                    info.axes = caps.dwAxes;
                    info.buttons = caps.dwButtons;
                    info.povs = caps.dwPOVs;
                    info.ffb = (caps.dwFlags & DIDC_FORCEFEEDBACK) != 0;
                }
                temp->Release();
''', '''                if (SUCCEEDED(temp->GetCapabilities(&caps)))
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
''')

# FFB saved snapshot struct/methods.
rep('src/overlay/wheel_setup_ui.cpp', '''        bool confirmingFfbOverwrite_ = false;
        bool confirmingFfbDelete_ = false;

        void refresh_ffb_profiles''', '''        bool confirmingFfbOverwrite_ = false;
        bool confirmingFfbDelete_ = false;

        struct FfbSavedSnapshot
        {
            bool valid = false;
            bool enable = true;
            bool physicsSat = true;
            bool hwSpring = true;
            bool hwDamper = true;
            bool periodic = true;
            bool invertForce = true;
            bool invertSpring = false;
            bool responseCorrection = false;
            float global = 0.70f;
            float spring = 0.65f;
            float springSaturation = 0.95f;
            float damper = 0.30f;
            float steering = 1.45f;
            float mechanical = 0.25f;
            float trailLead = 0.25f;
            float gripLoss = 0.65f;
            float lateralDeadzone = 1.5f;
            float weightTransfer = 0.15f;
            float gearShift = 0.18f;
            float engineIdle = 0.04f;
            float slew = 0.06f;
            float reversalRelease = 0.12f;
            float road = 0.30f;
            float tire = 0.20f;
            float collision = 0.38f;
            float maxTorque = 0.0f;
            std::string responseLut;
        } savedFfb_;

        void capture_saved_ffb()
        {
            savedFfb_.valid = true;
            savedFfb_.enable = Settings::WheelFFBEnable;
            savedFfb_.physicsSat = Settings::WheelFFBPhysicsSat;
            savedFfb_.hwSpring = Settings::WheelFFBUseHardwareSpring;
            savedFfb_.hwDamper = Settings::WheelFFBUseHardwareDamper;
            savedFfb_.periodic = Settings::WheelFFBUsePeriodicEffects;
            savedFfb_.invertForce = Settings::WheelFFBInvertForce;
            savedFfb_.invertSpring = Settings::WheelFFBInvertSpring;
            savedFfb_.responseCorrection = Settings::WheelFFBResponseCorrection;
            savedFfb_.global = Settings::WheelFFBGlobalStrength;
            savedFfb_.spring = Settings::WheelFFBSpringStrength;
            savedFfb_.springSaturation = Settings::WheelFFBSpringSaturation;
            savedFfb_.damper = Settings::WheelFFBDamperStrength;
            savedFfb_.steering = Settings::WheelFFBSteeringWeight;
            savedFfb_.mechanical = Settings::WheelFFBMechanicalTrail;
            savedFfb_.trailLead = Settings::WheelFFBTrailResponseLead;
            savedFfb_.gripLoss = Settings::WheelFFBGripLoss;
            savedFfb_.lateralDeadzone = Settings::WheelFFBLateralDeadzone;
            savedFfb_.weightTransfer = Settings::WheelFFBWeightTransfer;
            savedFfb_.gearShift = Settings::WheelFFBGearShift;
            savedFfb_.engineIdle = Settings::WheelFFBEngineIdle;
            savedFfb_.slew = Settings::WheelFFBSlewRate;
            savedFfb_.reversalRelease = Settings::WheelFFBReversalReleaseRate;
            savedFfb_.road = Settings::WheelFFBRoadTexture;
            savedFfb_.tire = Settings::WheelFFBTireSlip;
            savedFfb_.collision = Settings::WheelFFBWallImpact;
            savedFfb_.maxTorque = Settings::WheelFFBMaxTorqueNm;
            savedFfb_.responseLut = Settings::WheelFFBResponseLUT.get();
        }

        void restore_saved_ffb()
        {
            if (!savedFfb_.valid) return;
            Settings::WheelFFBEnable = savedFfb_.enable;
            Settings::WheelFFBPhysicsSat = savedFfb_.physicsSat;
            Settings::WheelFFBUseHardwareSpring = savedFfb_.hwSpring;
            Settings::WheelFFBUseHardwareDamper = savedFfb_.hwDamper;
            Settings::WheelFFBUsePeriodicEffects = savedFfb_.periodic;
            Settings::WheelFFBInvertForce = savedFfb_.invertForce;
            Settings::WheelFFBInvertSpring = savedFfb_.invertSpring;
            Settings::WheelFFBResponseCorrection = savedFfb_.responseCorrection;
            Settings::WheelFFBGlobalStrength = savedFfb_.global;
            Settings::WheelFFBSpringStrength = savedFfb_.spring;
            Settings::WheelFFBSpringSaturation = savedFfb_.springSaturation;
            Settings::WheelFFBDamperStrength = savedFfb_.damper;
            Settings::WheelFFBSteeringWeight = savedFfb_.steering;
            Settings::WheelFFBMechanicalTrail = savedFfb_.mechanical;
            Settings::WheelFFBTrailResponseLead = savedFfb_.trailLead;
            Settings::WheelFFBGripLoss = savedFfb_.gripLoss;
            Settings::WheelFFBLateralDeadzone = savedFfb_.lateralDeadzone;
            Settings::WheelFFBWeightTransfer = savedFfb_.weightTransfer;
            Settings::WheelFFBGearShift = savedFfb_.gearShift;
            Settings::WheelFFBEngineIdle = savedFfb_.engineIdle;
            Settings::WheelFFBSlewRate = savedFfb_.slew;
            Settings::WheelFFBReversalReleaseRate = savedFfb_.reversalRelease;
            Settings::WheelFFBRoadTexture = savedFfb_.road;
            Settings::WheelFFBTireSlip = savedFfb_.tire;
            Settings::WheelFFBWallImpact = savedFfb_.collision;
            Settings::WheelFFBMaxTorqueNm = savedFfb_.maxTorque;
            Settings::WheelFFBResponseLUT = savedFfb_.responseLut;
        }

        void refresh_ffb_profiles''')

# Capture snapshot at first render.
rep('src/overlay/wheel_setup_ui.cpp', '''        void render(bool) override
        {
            listen_for_binding();
''', '''        void render(bool) override
        {
            listen_for_binding();
            if (!savedFfb_.valid)
                capture_saved_ffb();
''')

# Steering VID/PID helper and recommendation state before combo lambda.
rep('src/overlay/wheel_setup_ui.cpp', '''            auto first_device_name = [&](bool ffbOnly) -> std::string
            {
''', '''            std::uint16_t steeringVendor = 0;
            std::uint16_t steeringProduct = 0;
            if (Settings::UseNewInput)
            {
                const auto& steeringBindings = InputManager::instance.actionFor(
                    InputManager::ActionKind::Volume, int(ADChannel::Steering)).bindings();
                for (const auto& binding : steeringBindings)
                {
                    if (binding.isRawDevice() && binding.deviceVendor != 0)
                    {
                        steeringVendor = binding.deviceVendor;
                        steeringProduct = binding.deviceProduct;
                        break;
                    }
                }
            }

            auto first_device_name = [&](bool ffbOnly) -> std::string
            {
''')
rep('src/overlay/wheel_setup_ui.cpp', '''                        const bool selected = isSelectedDevice(dev);
                        const std::string item = dev.name + "##" + label + dev.guidKey;
                        if (ImGui::Selectable(item.c_str(), selected))
''', '''                        const bool selected = isSelectedDevice(dev);
                        const bool steeringMatch = ffbOutput && steeringVendor != 0 &&
                            dev.vendor == steeringVendor &&
                            (steeringProduct == 0 || dev.product == steeringProduct);
                        const std::string item = dev.name +
                            (steeringMatch ? "  [recommended: steering device]" : "") +
                            "##" + label + dev.guidKey;
                        if (ImGui::Selectable(item.c_str(), selected))
''')
rep('src/overlay/wheel_setup_ui.cpp', '''                        ImGui::TextDisabled("%lu axes / %lu buttons / %lu POV / FFB %s / GUID %s",
                            dev.axes, dev.buttons, dev.povs, dev.ffb ? "yes" : "no", dev.guidKey.c_str());
''', '''                    {
                        ImGui::TextDisabled("%lu axes / %lu buttons / %lu POV / FFB %s / VID:%04X PID:%04X / GUID %s",
                            dev.axes, dev.buttons, dev.povs, dev.ffb ? "yes" : "no",
                            unsigned(dev.vendor), unsigned(dev.product), dev.guidKey.c_str());
                        if (ffbOutput && steeringVendor != 0 && dev.vendor == steeringVendor &&
                            (steeringProduct == 0 || dev.product == steeringProduct))
                            ImGui::TextColored(ImVec4(0.35f, 0.90f, 0.45f, 1.0f),
                                "Matches the steering device VID/PID (recommendation only). ");
                    }
''')

# Status + ready checklist after FFB output selection before profiles.
rep('src/overlay/wheel_setup_ui.cpp', '''            draw_ffb_profiles();

            if (!Settings::UseNewInput)
''', '''            if (Settings::UseNewInput)
            {
                const WheelFFBStatusSnapshot ffbStatus = WheelFFB_GetStatusSnapshot();
                ImGui::SeparatorText("Ready to Drive");
                const auto bound = [](InputManager::ActionKind kind, int index)
                {
                    return !InputManager::instance.actionFor(kind, index).bindings().empty();
                };
                const bool steeringReady = bound(InputManager::ActionKind::Volume, int(ADChannel::Steering));
                const bool accelReady = bound(InputManager::ActionKind::Volume, int(ADChannel::Acceleration));
                const bool brakeReady = bound(InputManager::ActionKind::Volume, int(ADChannel::Brake));
                const bool driveButtonsReady =
                    bound(InputManager::ActionKind::Switch, int(SwitchId::GearUp)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::GearDown));
                const bool menuReady =
                    bound(InputManager::ActionKind::Switch, int(SwitchId::A)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::B)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::SelectionUp)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::SelectionDown)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::SelectionLeft)) &&
                    bound(InputManager::ActionKind::Switch, int(SwitchId::SelectionRight));
                const auto readiness = [](const char* label, bool ok)
                {
                    ImGui::TextColored(ok ? ImVec4(0.35f, 0.90f, 0.45f, 1.0f) : ImVec4(1.0f, 0.70f, 0.20f, 1.0f),
                        "%s %s", ok ? "[OK]" : "[!]", label);
                };
                readiness("Steering", steeringReady);
                ImGui::SameLine(); readiness("Pedals", accelReady && brakeReady);
                ImGui::SameLine(); readiness("Shifters", driveButtonsReady);
                readiness("Menu controls", menuReady);
                ImGui::SameLine(); readiness("FFB device", ffbStatus.initialized || !Settings::WheelFFBDeviceGuid.get().empty());
                ImGui::SameLine(); readiness("Direction test", ffbStatus.directionTested);

                ImGui::SeparatorText("FFB Runtime Status");
                ImGui::Text("Engine: %s   Device: %s   Output owner: %s",
                    ffbStatus.initialized ? "ready" : "waiting",
                    ffbStatus.acquired ? "acquired" : "released",
                    ffbStatus.outputOwner ? "active" : "inactive");
                ImGui::Text("Effects: Constant %s | Spring %s | Damper %s | Periodic %s",
                    ffbStatus.constantEffect ? "HW" : "-",
                    ffbStatus.springEffect ? "HW" : "SW",
                    ffbStatus.damperEffect ? "HW" : "SW",
                    ffbStatus.periodicEffects ? "HW" : "SW");
                if (ffbStatus.ffbStateValid)
                {
                    ImGui::Text("Driver state: actuators %s | power %s | safety %s | user switch %s%s%s",
                        ffbStatus.actuatorsOn ? "ON" : "OFF",
                        ffbStatus.powerOn ? "ON" : "OFF",
                        ffbStatus.safetySwitchOn ? "ON" : "OFF",
                        ffbStatus.userSwitchOn ? "ON" : "OFF",
                        ffbStatus.paused ? " | PAUSED" : "",
                        ffbStatus.deviceLost ? " | DEVICE LOST" : "");
                    if (!ffbStatus.powerOn || !ffbStatus.safetySwitchOn || !ffbStatus.userSwitchOn || ffbStatus.deviceLost)
                        ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.25f, 1.0f),
                            "Wheel/driver reports FFB disabled or unavailable. This page will not override a hardware safety/user switch.");
                }
                ImGui::TextDisabled("Dynamic effect capability: Constant %s, POLAR direction %s, Spring %s, Damper %s, Sine %s",
                    ffbStatus.constantDynamic ? "yes" : "no",
                    ffbStatus.polarDirectionDynamic ? "yes" : "no",
                    ffbStatus.springDynamic ? "yes" : "no",
                    ffbStatus.damperDynamic ? "yes" : "no",
                    ffbStatus.periodicDynamic ? "yes" : "no");
            }

            draw_ffb_profiles();

            if (!Settings::UseNewInput)
''')

# Advanced slew UI + time explanation.
rep('src/overlay/wheel_setup_ui.cpp', '''                track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
''', '''                track_ffb_change(ImGui::SliderFloat("Force Build Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum normal structural-force build change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
                track_ffb_change(ImGui::SliderFloat("Countersteer Release Rate", Settings::WheelFFBReversalReleaseRate.ptr(), 0.02f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("When SAT reverses direction, stale torque unloads at least this fast before the new direction builds. This reduces counter-steer latency without speeding up normal force buildup.");
                const float buildRate = std::max(0.01f, float(Settings::WheelFFBSlewRate));
                const float reversalRate = std::max(0.02f, float(Settings::WheelFFBReversalReleaseRate));
                ImGui::TextDisabled("Approx full-scale ramp: build %.0f ms | stale reversal release %.0f ms at 60 Hz.",
                    (1.0f / buildRate) * (1000.0f / 60.0f),
                    (1.0f / reversalRate) * (1000.0f / 60.0f));
''')

# Save/revert controls and snapshot refresh on save.
rep('src/overlay/wheel_setup_ui.cpp', '''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    status_ = "Force feedback settings saved.";
                }
''', '''                if (Settings::write(Module::UserIniPath))
                {
                    ffbDirty_ = false;
                    capture_saved_ffb();
                    status_ = "Force feedback settings saved.";
                }
''')
rep('src/overlay/wheel_setup_ui.cpp', '''            if (ImGui::Button(ffbDirty_ ? "Save Force Feedback*" : "Save Force Feedback"))
            {
''', '''            if (ImGui::Button(ffbDirty_ ? "Save Force Feedback*" : "Save Force Feedback"))
            {
''')
# Insert revert just after save block by anchoring next separator.
rep('src/overlay/wheel_setup_ui.cpp', '''                else
                    status_ = "Could not save force feedback settings.";
            }

            ImGui::SeparatorText("FFB Headroom / Clipping");
''', '''                else
                    status_ = "Could not save force feedback settings.";
            }
            ImGui::SameLine();
            if (!ffbDirty_ || !savedFfb_.valid) ImGui::BeginDisabled();
            if (ImGui::Button("Revert unsaved FFB"))
            {
                restore_saved_ffb();
                ffbDirty_ = false;
                WheelFFB_RequestSettingsTransition();
                status_ = "Reverted live FFB tuning to the last saved state.";
            }
            if (!ffbDirty_ || !savedFfb_.valid) ImGui::EndDisabled();

            ImGui::SeparatorText("FFB Headroom / Clipping");
''')

# Live graph after headroom reset.
rep('src/overlay/wheel_setup_ui.cpp', '''            if (ImGui::Button("Reset headroom analysis"))
                WheelFFB_ResetHeadroomStats();

            ImGui::SeparatorText("Safe direction test");
''', '''            if (ImGui::Button("Reset headroom analysis"))
                WheelFFB_ResetHeadroomStats();

            ImGui::SeparatorText("Recent FFB Pipeline (last 3 seconds of driving)");
            const WheelFFBGraphSnapshot graph = WheelFFB_GetGraphSnapshot();
            if (graph.count > 1)
            {
                ImGui::PlotLines("Raw structural", graph.rawStructural.data(), int(graph.count), 0, nullptr, -1.5f, 1.5f, ImVec2(0, 46));
                ImGui::PlotLines("Soft limited", graph.softLimited.data(), int(graph.count), 0, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
                ImGui::PlotLines("Post slew", graph.postSlew.data(), int(graph.count), 0, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
                ImGui::PlotLines("Final DirectInput", graph.finalOutput.data(), int(graph.count), 0, nullptr, -1.1f, 1.1f, ImVec2(0, 46));
            }
            else
                ImGui::TextDisabled("Drive for a moment, then open F11 to inspect the captured force pipeline.");

            ImGui::SeparatorText("Safe direction test");
''')

# Presets explicitly set reversal release; keep existing build slew numbers.
rep('src/overlay/wheel_setup_ui.cpp', '''                Settings::WheelFFBSlewRate = 0.040f;
                Settings::WheelFFBRoadTexture = 0.30f;
''', '''                Settings::WheelFFBSlewRate = 0.040f;
                Settings::WheelFFBReversalReleaseRate = 0.12f;
                Settings::WheelFFBRoadTexture = 0.30f;
''')
rep('src/overlay/wheel_setup_ui.cpp', '''                Settings::WheelFFBSlewRate = 0.045f;
                Settings::WheelFFBRoadTexture = 0.30f;
''', '''                Settings::WheelFFBSlewRate = 0.045f;
                Settings::WheelFFBReversalReleaseRate = 0.12f;
                Settings::WheelFFBRoadTexture = 0.30f;
''')

# ---------------------------------------------------------------------------
# Verifier/docs: hard guards for the new behavior.
# ---------------------------------------------------------------------------
verifier = read('tools/verify_wheel_ffb_current.py')
append = r'''

# Setup/FFB UX and compatibility review guards.
req(ffb, 'WheelFFBReversalReleaseRate', 'dedicated counter-steer stale-torque release rate')
req(ffb, 'GetEffectInfo(&info, effectGuid)', 'DirectInput effect dynamic capability query')
req(ffb, 'DIEP_TYPESPECIFICPARAMS', 'dynamic type-specific capability gate')
req(ffb, 'WheelFFBStatusSnapshot status_snapshot() const', 'runtime FFB status snapshot')
req(ffb, 'WheelFFBGraphSnapshot graph_snapshot() const', 'runtime rolling force graph')
req(ffb, 'record_graph_sample(', 'force pipeline graph recorder')
req(runtime, 'WheelFFB_GetStatusSnapshot', 'status API exported to UI')
req(runtime, 'WheelFFB_GetGraphSnapshot', 'graph API exported to UI')
req(ui, 'Ready to Drive', 'setup readiness summary')
req(ui, 'FFB Runtime Status', 'driver/effect status panel')
req(ui, 'recommended: steering device', 'VID/PID steering-to-FFB recommendation')
req(ui, 'Revert unsaved FFB', 'live FFB revert action')
req(ui, 'Recent FFB Pipeline', 'FFB rolling pipeline graph')
req(ui, 'Countersteer Release Rate', 'counter-steer release UI')
req(bindings_ui, 'LISTENING...##addBinding', 'manual add-binding target highlight')
req(bindings_ui, 'const bool listeningHere', 'manual rebind button target highlight')
req(bindings_ui, 'binding_conflicts', 'duplicate-control conflict warning')
req(bindings_ui, 'Guided axis calibration', 'Quick Setup integrated axis calibration')
'''
if 'Setup/FFB UX and compatibility review guards.' not in verifier:
    verifier += append
    write('tools/verify_wheel_ffb_current.py', verifier)

# Architecture note, concise and operator-focused.
doc = read('WHEEL_FFB.md')
section = r'''

## Setup and DirectInput capability diagnostics

The F11 Force Feedback page now reports the live DirectInput FFB state, hardware effect/fallback ownership, and whether each effect advertises dynamic parameter updates. If a driver explicitly reports that Spring, Damper, or Sine type-specific parameters cannot be changed while playing, the engine prefers the software fallback instead of repeatedly stop/restarting that hardware effect. Failed capability discovery preserves the prior compatibility path rather than rejecting older drivers blindly.

The page also shows a Ready to Drive checklist, steering-device VID/PID recommendation for the FFB output, a rolling three-second Raw -> Soft Limit -> Post Slew -> Final DirectInput graph, and a Revert unsaved FFB action. Input Bindings highlights the exact manual binding button currently listening, warns when the same physical control is already used by another action, and exposes wheel/pedal calibration directly in the Quick Setup completion flow.

`ReversalReleaseRate` is separate from the normal `SlewRate`: normal SAT buildup keeps its existing profile tuning, while stale torque can unload faster when SAT changes direction. This targets counter-steer latency without globally making impacts or ordinary force buildup harsher.
'''
if '## Setup and DirectInput capability diagnostics' not in doc:
    doc += section
    write('WHEEL_FFB.md', doc)

print('FFB/UI compatibility and setup UX patch applied')
