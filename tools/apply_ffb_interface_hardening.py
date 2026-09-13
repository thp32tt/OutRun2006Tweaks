from pathlib import Path

src_path = Path('src/hooks_wheel_ffb.cpp')
ver_path = Path('tools/verify_wheel_ffb_current.py')
text = src_path.read_text(encoding='utf-8')


def repl(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, got {count}')
    text = text.replace(old, new, 1)

repl('''                if (guidNow != selectedConfiguredGuid_ || nameNow != selectedConfiguredName_)\n                {\n                    selectedConfiguredGuid_ = guidNow;\n                    selectedConfiguredName_ = nameNow;\n                    directionTested_ = false;\n                    request_device_reinitialize("configured wheel identity changed", S_OK);\n                    return;\n                }\n''', '''                if (guidNow != selectedConfiguredGuid_ || nameNow != selectedConfiguredName_)\n                {\n                    selectedConfiguredGuid_ = guidNow;\n                    selectedConfiguredName_ = nameNow;\n                    preferredVidPid_ = 0;\n                    failedInterfaces_.clear();\n                    directionTested_ = false;\n                    request_device_reinitialize("configured wheel identity changed", S_OK);\n                    return;\n                }\n''', 'identity reset')

repl('''                bool ready = initialize();\n                if (!ready)\n                {\n                    const DWORD fallbackNow = GetTickCount();\n                    const bool rejectedInterfacePending =\n                        !failedInterfaceGuid_.empty() &&\n                        tick_before(fallbackNow, failedInterfaceUntil_);\n                    if (rejectedInterfacePending)\n                    {\n                        spdlog::info(\n                            "WheelFFB: selected FFB interface failed validation; probing a sibling interface immediately");\n                        ready = initialize();\n                    }\n                }\n\n                if (!ready)\n''', '''                bool ready = false;\n                constexpr size_t MaxInterfaceProbes = 16;\n                for (size_t probe = 0; probe < MaxInterfaceProbes && !ready; ++probe)\n                {\n                    const size_t failedBefore = active_failed_interface_count();\n                    ready = initialize();\n                    if (ready)\n                        break;\n\n                    const size_t failedAfter = active_failed_interface_count();\n                    if (failedAfter <= failedBefore)\n                        break;\n\n                    spdlog::info(\n                        "WheelFFB: FFB interface failed validation; probing the next compatible interface immediately ({}/{})",\n                        failedAfter, MaxInterfaceProbes);\n                }\n\n                if (!ready)\n''', 'multi interface probe loop')

repl('''        struct EnumContext\n        {\n            WheelFFBEngine* self = nullptr;\n            GUID selectedGuid{};\n            std::string selectedName;\n            bool found = false;\n                        bool matchGuidOnly = false;\n        };\n''', '''        struct FailedInterfaceState\n        {\n            std::string guid;\n            DWORD until = 0;\n        };\n\n        struct EnumContext\n        {\n            WheelFFBEngine* self = nullptr;\n            GUID selectedGuid{};\n            std::string selectedName;\n            DWORD selectedVidPid = 0;\n            DWORD preferredVidPid = 0;\n            bool found = false;\n            bool matchGuidOnly = false;\n            bool requirePreferredVidPid = false;\n        };\n''', 'enum context')

repl('''            if (ctx->self && tick_before(GetTickCount(), ctx->self->failedInterfaceUntil_) &&\n                directinput_guid_key(instance->guidInstance) == ctx->self->failedInterfaceGuid_)\n            {\n                spdlog::warn(\n                    "WheelFFB: temporarily skipping rejected FFB interface '{}' [{}] until retry",\n                    instance->tszProductName, directinput_guid_key(instance->guidInstance));\n                return DIENUM_CONTINUE;\n            }\n''', '''            if (ctx->self && ctx->self->interface_temporarily_failed(instance->guidInstance))\n            {\n                spdlog::warn(\n                    "WheelFFB: temporarily skipping rejected FFB interface '{}' [{}] until retry",\n                    instance->tszProductName, directinput_guid_key(instance->guidInstance));\n                return DIENUM_CONTINUE;\n            }\n''', 'failed callback')

repl('''            if (!ctx->matchGuidOnly && !wanted.empty() &&\n                instanceName.find(wanted) == std::string::npos &&\n                productName.find(wanted) == std::string::npos)\n            {\n                return DIENUM_CONTINUE;\n            }\n\n            ctx->selectedGuid = instance->guidInstance;\n            ctx->selectedName = instance->tszProductName;\n            ctx->found = true;\n            return DIENUM_STOP;\n''', '''            DWORD candidateVidPid = 0;\n            if (ctx->self && ctx->requirePreferredVidPid)\n            {\n                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n                if (candidateVidPid == 0 || candidateVidPid != ctx->preferredVidPid)\n                    return DIENUM_CONTINUE;\n            }\n\n            if (!ctx->matchGuidOnly && !ctx->requirePreferredVidPid && !wanted.empty() &&\n                instanceName.find(wanted) == std::string::npos &&\n                productName.find(wanted) == std::string::npos)\n            {\n                return DIENUM_CONTINUE;\n            }\n\n            if (candidateVidPid == 0 && ctx->self)\n                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n\n            ctx->selectedGuid = instance->guidInstance;\n            ctx->selectedName = instance->tszProductName;\n            ctx->selectedVidPid = candidateVidPid;\n            ctx->found = true;\n            return DIENUM_STOP;\n''', 'vidpid callback')

repl('''                failedInterfaceGuid_.clear();\n                failedInterfaceUntil_ = 0;\n''', '''                failedInterfaces_.clear();\n                preferredVidPid_ = 0;\n''', 'disable clear')

repl('''        void mark_selected_interface_failed(const char* reason, HRESULT hr)\n        {\n            failedInterfaceGuid_ = directinput_guid_key(selectedGuid_);\n            failedInterfaceUntil_ = GetTickCount() + FFB_DEVICE_FAILED_BACKOFF_MS;\n            spdlog::warn(\n                "WheelFFB: interface '{}' [{}] rejected {}; temporarily excluding it from automatic selection (0x{:08X})",\n                selectedName_, failedInterfaceGuid_, reason, (unsigned)hr);\n        }\n\n        bool initialize()\n''', '''        void prune_failed_interfaces()\n        {\n            const DWORD now = GetTickCount();\n            failedInterfaces_.erase(\n                std::remove_if(\n                    failedInterfaces_.begin(), failedInterfaces_.end(),\n                    [&](const FailedInterfaceState& state)\n                    {\n                        return tick_reached(now, state.until);\n                    }),\n                failedInterfaces_.end());\n        }\n\n        bool interface_temporarily_failed(const GUID& guid)\n        {\n            prune_failed_interfaces();\n            const std::string key = directinput_guid_key(guid);\n            return std::any_of(\n                failedInterfaces_.begin(), failedInterfaces_.end(),\n                [&](const FailedInterfaceState& state) { return state.guid == key; });\n        }\n\n        size_t active_failed_interface_count()\n        {\n            prune_failed_interfaces();\n            return failedInterfaces_.size();\n        }\n\n        DWORD query_device_vidpid(const GUID& guid)\n        {\n            if (!directInput_)\n                return 0;\n\n            IDirectInputDevice8A* probe = nullptr;\n            if (FAILED(directInput_->CreateDevice(guid, &probe, nullptr)) || !probe)\n                return 0;\n\n            DIPROPDWORD vidpid{};\n            vidpid.diph.dwSize = sizeof(vidpid);\n            vidpid.diph.dwHeaderSize = sizeof(vidpid.diph);\n            vidpid.diph.dwObj = 0;\n            vidpid.diph.dwHow = DIPH_DEVICE;\n            const HRESULT hr = probe->GetProperty(DIPROP_VIDPID, &vidpid.diph);\n            probe->Release();\n            return SUCCEEDED(hr) ? vidpid.dwData : 0;\n        }\n\n        void mark_selected_interface_failed(const char* reason, HRESULT hr)\n        {\n            prune_failed_interfaces();\n            const std::string failedGuid = directinput_guid_key(selectedGuid_);\n            const DWORD until = GetTickCount() + FFB_DEVICE_FAILED_BACKOFF_MS;\n            auto existing = std::find_if(\n                failedInterfaces_.begin(), failedInterfaces_.end(),\n                [&](const FailedInterfaceState& state) { return state.guid == failedGuid; });\n            if (existing != failedInterfaces_.end())\n                existing->until = until;\n            else\n                failedInterfaces_.push_back({ failedGuid, until });\n\n            spdlog::warn(\n                "WheelFFB: interface '{}' [{}] rejected {}; temporarily excluding it from automatic selection (0x{:08X})",\n                selectedName_, failedGuid, reason, (unsigned)hr);\n        }\n\n        bool initialize()\n''', 'failure set and vidpid helper')

repl('''            // Prefer the already-loaded original Windows dinput8 module instead\n            // of routing the FFB backend back through this proxy DLL.\n            if (!createDirectInput)\n            {\n                spdlog::warn(\n                    "WheelFFB: original proxy module has no DirectInput8Create export; using linked fallback");\n                createDirectInput = &::DirectInput8Create;\n            }\n''', '''            // The plugin is itself named dinput8.dll. Falling back to the linked\n            // DirectInput8Create symbol can route back through our own proxy export,\n            // so fail closed unless the already-loaded System32 module has the export.\n            if (!createDirectInput)\n            {\n                spdlog::error(\n                    "WheelFFB: original System32 dinput8 module has no DirectInput8Create export");\n                return false;\n            }\n''', 'proxy fail closed')

repl('''            if (!ctx.found)\n            {\n                ctx.matchGuidOnly = false;\n                hr = directInput_->EnumDevices(\n                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n            }\n\n            if (FAILED(hr) || !ctx.found)\n''', '''            if (!ctx.found && preferredVidPid_ != 0)\n            {\n                ctx.matchGuidOnly = false;\n                ctx.requirePreferredVidPid = true;\n                ctx.preferredVidPid = preferredVidPid_;\n                hr = directInput_->EnumDevices(\n                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n                if (FAILED(hr))\n                {\n                    release_directinput();\n                    return false;\n                }\n                if (!ctx.found)\n                {\n                    spdlog::warn(\n                        "WheelFFB: no remaining FFB interface shared preferred VID/PID 0x{:08X}; falling back to the configured device name",\n                        (unsigned)preferredVidPid_);\n                }\n            }\n\n            if (!ctx.found)\n            {\n                ctx.matchGuidOnly = false;\n                ctx.requirePreferredVidPid = false;\n                hr = directInput_->EnumDevices(\n                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n            }\n\n            if (FAILED(hr) || !ctx.found)\n''', 'vidpid fallback pass')

repl('''            selectedGuid_ = ctx.selectedGuid;\n            selectedName_ = ctx.selectedName;\n            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());\n''', '''            selectedGuid_ = ctx.selectedGuid;\n            selectedName_ = ctx.selectedName;\n            const bool selectedConfiguredInterface =\n                !configuredGuid.empty() && directinput_guid_key(selectedGuid_) == configuredGuid;\n            if (ctx.selectedVidPid != 0 &&\n                (preferredVidPid_ == 0 || selectedConfiguredInterface))\n            {\n                preferredVidPid_ = ctx.selectedVidPid;\n            }\n            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());\n''', 'remember vidpid')

repl('''            {\n                const std::string actualGuid = directinput_guid_key(selectedGuid_);\n                if (lower_copy(Settings::WheelFFBDeviceGuid.get().c_str()) != actualGuid)\n                {\n                    Settings::WheelFFBDeviceGuid = actualGuid;\n                    selectedConfiguredGuid_ = actualGuid;\n                    spdlog::info(\n                        "WheelFFB: pinned working force interface GUID '{}' after capability validation",\n                        actualGuid);\n                }\n            }\n''', '''            {\n                const std::string actualGuid = directinput_guid_key(selectedGuid_);\n                if (ctx.selectedVidPid != 0)\n                    preferredVidPid_ = ctx.selectedVidPid;\n                const bool identityChanged =\n                    lower_copy(Settings::WheelFFBDeviceGuid.get().c_str()) != actualGuid ||\n                    Settings::WheelFFBDeviceName.get() != selectedName_;\n                if (identityChanged)\n                {\n                    Settings::WheelFFBDeviceGuid = actualGuid;\n                    Settings::WheelFFBDeviceName = selectedName_;\n                    selectedConfiguredGuid_ = actualGuid;\n                    selectedConfiguredName_ = lower_copy(selectedName_.c_str());\n                    const bool saved = Settings::write(Module::UserIniPath);\n                    spdlog::info(\n                        "WheelFFB: pinned working force interface '{}' [{}] after capability validation{}",\n                        selectedName_, actualGuid, saved ? " and saved it to user.ini" : " for this session only");\n                    if (!saved)\n                    {\n                        spdlog::warn(\n                            "WheelFFB: automatic FFB interface selection could not persist user.ini; the interface may be probed again next launch");\n                    }\n                }\n            }\n''', 'persist working identity')

repl('''            failedInterfaceGuid_.clear();\n            failedInterfaceUntil_ = 0;\n''', '''            prune_failed_interfaces();\n''', 'success keeps quarantine')

start = text.index('        bool create_constant_effect()\n')
end = text.index('        bool create_spring_effect()\n', start)
new_func = r'''        bool create_constant_effect()
        {
            if (!device_)
                return false;

            const bool liveMagnitude = query_dynamic_effect_capability(
                GUID_ConstantForce, "ConstantForce", DIEP_TYPESPECIFICPARAMS,
                constantCapsKnown_, constantDynamicParams_);
            if (constantCapsKnown_ && !liveMagnitude)
            {
                spdlog::warn(
                    "WheelFFB: ConstantForce metadata reports no live magnitude update support; probing the real zero-force update path anyway");
            }

            safe_release_effect(constantEffect_, "constant before create");
            constantEffectPolar_ = false;

            DWORD axes[2] = { DIJOFS_X, DIJOFS_Y };
            LONG directions[2] = { 9000L, 0L };
            constantParams_ = {};
            constantParams_.lMagnitude = 0;

            DIEFFECT effect{};
            effect.dwSize = sizeof(effect);
            effect.dwDuration = FFB_EFFECT_LEASE_US;
            effect.dwSamplePeriod = 0;
            effect.dwGain = DI_FFNOMINALMAX;
            effect.dwTriggerButton = DIEB_NOTRIGGER;
            effect.dwTriggerRepeatInterval = 0;
            effect.rgdwAxes = axes;
            effect.rglDirection = directions;
            effect.cbTypeSpecificParams = sizeof(constantParams_);
            effect.lpvTypeSpecificParams = &constantParams_;

            auto probe_live_update = [&](const char* descriptor, bool polar) -> HRESULT
            {
                if (!constantEffect_)
                    return E_POINTER;

                HRESULT hr = constantEffect_->Start(1, 0);
                if (FAILED(hr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} start probe failed (0x{:08X})",
                        descriptor, (unsigned)hr);
                    return hr;
                }

                DICONSTANTFORCE zeroForce{};
                LONG probeDirections[2] = { 9000L, 0L };
                DIEFFECT params{};
                params.dwSize = sizeof(params);
                params.cbTypeSpecificParams = sizeof(zeroForce);
                params.lpvTypeSpecificParams = &zeroForce;
                DWORD flags = DIEP_TYPESPECIFICPARAMS | DIEP_START;

                if (polar)
                {
                    params.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
                    params.cAxes = 2;
                    params.rglDirection = probeDirections;
                    flags |= DIEP_DIRECTION;

                    probeDirections[0] = 27000L;
                    hr = constantEffect_->SetParameters(&params, flags);
                    if (SUCCEEDED(hr))
                    {
                        probeDirections[0] = 9000L;
                        hr = constantEffect_->SetParameters(&params, flags);
                    }
                }
                else
                {
                    hr = constantEffect_->SetParameters(&params, flags);
                }

                if (FAILED(hr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} zero-force live SetParameters probe failed (0x{:08X})",
                        descriptor, (unsigned)hr);
                    constantEffect_->Stop();
                    return hr;
                }

                const HRESULT stopHr = constantEffect_->Stop();
                if (FAILED(stopHr))
                {
                    spdlog::warn(
                        "WheelFFB: ConstantForce {} zero-force probe Stop failed (0x{:08X})",
                        descriptor, (unsigned)stopHr);
                }
                return S_OK;
            };

            auto accept_candidate = [&](const char* descriptor, bool polar) -> HRESULT
            {
                const HRESULT probeHr = probe_live_update(descriptor, polar);
                if (FAILED(probeHr))
                    return probeHr;

                constantEffectPolar_ = polar;
                prevConstantLevel_ = 0;
                lastConstantWriteTick_ = 0;
                spdlog::info(
                    "WheelFFB: ConstantForce validated with {} including zero-force live SetParameters",
                    descriptor);
                return S_OK;
            };

            HRESULT hr = E_FAIL;

            // Fanatec-style multi-interface drivers can report one physical
            // actuator while still requiring the legacy X/Y POLAR descriptor.
            effect.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS;
            effect.cAxes = 2;
            hr = device_->CreateEffect(
                GUID_ConstantForce, &effect, &constantEffect_, nullptr);
            if (SUCCEEDED(hr) && constantEffect_)
            {
                const HRESULT probeHr = accept_candidate("canonical X/Y 2-axis POLAR descriptor", true);
                if (SUCCEEDED(probeHr))
                    return true;
                hr = probeHr;
            }

            safe_release_effect(constantEffect_, "failed POLAR constant probe");
            spdlog::warn(
                "WheelFFB: X/Y POLAR ConstantForce unavailable; trying canonical one-axis X CARTESIAN");

            effect.dwFlags = DIEFF_CARTESIAN | DIEFF_OBJECTOFFSETS;
            effect.cAxes = 1;
            axes[0] = DIJOFS_X;
            directions[0] = 1;
            hr = device_->CreateEffect(
                GUID_ConstantForce, &effect, &constantEffect_, nullptr);
            if (SUCCEEDED(hr) && constantEffect_)
            {
                const HRESULT probeHr = accept_candidate("canonical one-axis X CARTESIAN descriptor", false);
                if (SUCCEEDED(probeHr))
                    return true;
                hr = probeHr;
            }

            safe_release_effect(constantEffect_, "failed X CARTESIAN constant probe");

            const DWORD detectedAxis = primary_actuator_axis();
            if (detectedAxis != DIJOFS_X)
            {
                axes[0] = detectedAxis;
                hr = device_->CreateEffect(
                    GUID_ConstantForce, &effect, &constantEffect_, nullptr);
                if (SUCCEEDED(hr) && constantEffect_)
                {
                    const HRESULT probeHr = accept_candidate("detected actuator one-axis CARTESIAN descriptor", false);
                    if (SUCCEEDED(probeHr))
                    {
                        spdlog::info(
                            "WheelFFB: ConstantForce is using detected actuator offset {} instead of DIJOFS_X",
                            (unsigned)detectedAxis);
                        return true;
                    }
                    hr = probeHr;
                }
                safe_release_effect(constantEffect_, "failed detected-axis CARTESIAN constant probe");
            }

            const HRESULT failHr = FAILED(hr) ? hr : E_FAIL;
            mark_selected_interface_failed("ConstantForce create/start/live-update probe", failHr);
            spdlog::error(
                "WheelFFB: no usable ConstantForce descriptor on selected interface (0x{:08X})",
                (unsigned)failHr);
            return false;
        }

'''
text = text[:start] + new_func + text[end:]

repl('''            if (FAILED(hr))\n            {\n                request_device_reinitialize("ConstantForce output failed", hr);\n                spdlog::warn("WheelFFB: constant force update failed (0x{:08X})", (unsigned)hr);\n                return;\n            }\n''', '''            if (FAILED(hr))\n            {\n                mark_selected_interface_failed("ConstantForce live SetParameters", hr);\n                request_device_reinitialize("ConstantForce output failed", hr);\n                spdlog::warn(\n                    "WheelFFB: constant force update failed (0x{:08X}); current interface will be skipped on reinitialization",\n                    (unsigned)hr);\n                return;\n            }\n''', 'runtime failure blacklist')

repl('''        DWORD retryAfter_ = 0;\n        std::string failedInterfaceGuid_;\n        DWORD failedInterfaceUntil_ = 0;\n''', '''        DWORD retryAfter_ = 0;\n        std::vector<FailedInterfaceState> failedInterfaces_;\n        DWORD preferredVidPid_ = 0;\n''', 'member failure vector')

src_path.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))

ver = ver_path.read_text(encoding='utf-8')
old = '''req(ffb, 'GUID_ConstantForce', 'DirectInput ConstantForce effect')\nreq(ffb, '#include "Proxy.hpp"', 'FFB backend can access original proxy module')\nreq(ffb, 'GetProcAddress(proxy::origModule, "DirectInput8Create")', 'FFB backend uses original Windows DirectInput export')\nreq(ffb, 'DWORD axes[2] = { DIJOFS_X, DIJOFS_Y };', 'ConstantForce tries canonical X/Y polar descriptor independent of actuator count')\nreq(ffb, 'ConstantForce validated with canonical X/Y 2-axis POLAR descriptor', '2-axis ConstantForce create/start probe required')\nreq(ffb, 'saved FFB GUID unavailable or rejected; probing compatible sibling interfaces', 'saved FFB GUID can fall back to sibling interface')\nreq(ffb, 'selected FFB interface failed validation; probing a sibling interface immediately', 'failed interface gets immediate sibling probe')\nreq(ffb, 'FFB_DEVICE_FAILED_BACKOFF_MS = 10000', 'failed FFB interface retry is throttled')\nreq(ffb, 'device_->SendForceFeedbackCommand(DISFFC_RESET)', 'FFB interface reset before actuator enable')\n'''
new = '''req(ffb, 'GUID_ConstantForce', 'DirectInput ConstantForce effect')\nreq(ffb, '#include "Proxy.hpp"', 'FFB backend can access original proxy module')\nreq(ffb, 'GetProcAddress(proxy::origModule, "DirectInput8Create")', 'FFB backend uses original Windows DirectInput export')\nforbid(ffb, 'createDirectInput = &::DirectInput8Create;', 'FFB backend never falls back through its own dinput8 proxy export')\nreq(ffb, 'std::vector<FailedInterfaceState> failedInterfaces_;', 'FFB backend can quarantine multiple rejected interfaces')\nreq(ffb, 'active_failed_interface_count()', 'FFB backend walks all rejected candidates instead of only one sibling')\nreq(ffb, 'DIPROP_VIDPID', 'FFB sibling selection can prefer matching physical VID/PID')\nreq(ffb, 'requirePreferredVidPid', 'FFB sibling selection has a same-VID/PID pass before name fallback')\nreq(ffb, 'DWORD axes[2] = { DIJOFS_X, DIJOFS_Y };', 'ConstantForce tries canonical X/Y polar descriptor independent of actuator count')\nreq(ffb, 'detected actuator one-axis CARTESIAN descriptor', 'ConstantForce can fall back to the actual enumerated actuator axis')\nreq(ffb, 'zero-force live SetParameters probe', 'ConstantForce candidate must validate the live update path at zero torque')\nreq(ffb, 'mark_selected_interface_failed("ConstantForce live SetParameters", hr)', 'runtime ConstantForce failure quarantines the bad interface before reinit')\nreq(ffb, 'Settings::write(Module::UserIniPath)', 'auto-selected working FFB GUID is persisted for the next launch')\nreq(ffb, 'saved FFB GUID unavailable or rejected; probing compatible sibling interfaces', 'saved FFB GUID can fall back to sibling interface')\nreq(ffb, 'FFB_DEVICE_FAILED_BACKOFF_MS = 10000', 'failed FFB interface retry is throttled')\nreq(ffb, 'device_->SendForceFeedbackCommand(DISFFC_RESET)', 'FFB interface reset before actuator enable')\n'''
if ver.count(old) != 1:
    raise SystemExit(f'verifier compatibility block: expected 1 match, got {ver.count(old)}')
ver = ver.replace(old, new, 1)

old2 = '''req(ffb, 'constantEffectPolar_ = true;\\n                    prevConstantLevel_ = 0;\\n                    lastConstantWriteTick_ = 0;', 'new POLAR ConstantForce resets accepted-output cache')\nreq(ffb, 'constantEffectPolar_ = false;\\n                    prevConstantLevel_ = 0;\\n                    lastConstantWriteTick_ = 0;', 'new CARTESIAN ConstantForce resets accepted-output cache')\n'''
new2 = '''req(ffb, 'constantEffectPolar_ = polar;\\n                prevConstantLevel_ = 0;\\n                lastConstantWriteTick_ = 0;', 'validated ConstantForce descriptor resets accepted-output cache')\n'''
if ver.count(old2) != 1:
    raise SystemExit(f'verifier cache block: expected 1 match, got {ver.count(old2)}')
ver = ver.replace(old2, new2, 1)

ver_path.write_bytes(ver.replace('\n', '\r\n').encode('utf-8'))
print('Patched FFB interface negotiation/recovery and verifier')
