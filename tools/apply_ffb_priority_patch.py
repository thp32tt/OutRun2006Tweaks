from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def replace_once(rel: str, old: str, new: str) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"PATCH FAILED [{rel}]: expected one match, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_after_once(rel: str, needle: str, addition: str) -> None:
    replace_once(rel, needle, needle + addition)


ffb = "src/hooks_wheel_ffb.cpp"
verify = "tools/verify_wheel_ffb_current.py"
workflow = ".github/workflows/build.yml"

# 1) Runtime recovery constants and robust DirectInput physical identity helpers.
replace_once(
    ffb,
    "    constexpr DWORD FFB_DEVICE_FAILED_BACKOFF_MS = 10000;\n",
    "    constexpr DWORD FFB_DEVICE_FAILED_BACKOFF_MS = 10000;\n"
    "    constexpr unsigned FFB_CONSTANT_LIVE_FAILURE_LIMIT = 3;\n",
)

replace_once(
    ffb,
    "        return lower_copy(b);\n"
    "    }\n\n"
    "    bool is_virtual_device_name(const std::string& lowered)\n",
    "        return lower_copy(b);\n"
    "    }\n\n"
    "    bool directinput_guid_equal(const GUID& a, const GUID& b)\n"
    "    {\n"
    "        return std::memcmp(&a, &b, sizeof(GUID)) == 0;\n"
    "    }\n\n"
    "    bool directinput_guid_is_zero(const GUID& guid)\n"
    "    {\n"
    "        const GUID zero{};\n"
    "        return directinput_guid_equal(guid, zero);\n"
    "    }\n\n"
    "    bool is_virtual_device_name(const std::string& lowered)\n",
)

# Reset all learned sibling hints when the configured physical wheel changes.
replace_once(
    ffb,
    "                    preferredVidPid_ = 0;\n"
    "                    failedInterfaces_.clear();\n",
    "                    preferredVidPid_ = 0;\n"
    "                    preferredProductGuid_ = {};\n"
    "                    preferredFFDriverGuid_ = {};\n"
    "                    preferredVendorId_ = 0;\n"
    "                    failedInterfaces_.clear();\n",
)

# 2) Probe one candidate per game update tick. This keeps exhaustive fallback but
# avoids recreating/enumerating the whole DirectInput root multiple times in one frame.
replace_once(
    ffb,
    "                bool ready = false;\n"
    "                size_t failedBefore = active_failed_interface_count();\n"
    "                while (!ready)\n"
    "                {\n"
    "                    ready = initialize();\n"
    "                    if (ready)\n"
    "                        break;\n\n"
    "                    const size_t failedAfter = active_failed_interface_count();\n"
    "                    if (failedAfter <= failedBefore)\n"
    "                        break;\n\n"
    "                    // Every compatibility failure adds one previously unseen GUID\n"
    "                    // to failedInterfaces_. That monotonic progress makes this\n"
    "                    // exhaustive without an arbitrary device-count limit, while\n"
    "                    // transient failures that do not quarantine a GUID break out.\n"
    "                    failedBefore = failedAfter;\n"
    "                    spdlog::info(\n"
    "                        \"WheelFFB: FFB interface failed validation; probing the next compatible interface immediately ({} rejected this cycle)\",\n"
    "                        failedAfter);\n"
    "                }\n\n"
    "                if (!ready)\n"
    "                {\n"
    "                    // initialize() can request the short retry interval for\n"
    "                    // transient startup/focus conditions. Do not overwrite that\n"
    "                    // with the rejected-interface backoff.\n"
    "                    const DWORD retryNow = GetTickCount();\n"
    "                    if (!tick_before(retryNow, retryAfter_))\n"
    "                        retryAfter_ = retryNow + FFB_DEVICE_FAILED_BACKOFF_MS;\n"
    "                    return;\n"
    "                }\n",
    "                const size_t failedBefore = active_failed_interface_count();\n"
    "                const bool ready = initialize();\n"
    "                if (!ready)\n"
    "                {\n"
    "                    const size_t failedAfter = active_failed_interface_count();\n"
    "                    if (failedAfter > failedBefore)\n"
    "                    {\n"
    "                        // Compatibility rejection is progress, not a reason to\n"
    "                        // block the game thread while every sibling is reopened.\n"
    "                        // Probe the next candidate on the next update tick.\n"
    "                        retryAfter_ = 0;\n"
    "                        spdlog::info(\n"
    "                            \"WheelFFB: FFB interface failed validation; next compatible interface will be probed on the next update tick ({} rejected this cycle)\",\n"
    "                            failedAfter);\n"
    "                        return;\n"
    "                    }\n\n"
    "                    // initialize() can request the short retry interval for\n"
    "                    // transient startup/focus conditions. Do not overwrite that\n"
    "                    // with the rejected-interface backoff.\n"
    "                    const DWORD retryNow = GetTickCount();\n"
    "                    if (!tick_before(retryNow, retryAfter_))\n"
    "                        retryAfter_ = retryNow + FFB_DEVICE_FAILED_BACKOFF_MS;\n"
    "                    return;\n"
    "                }\n",
)

# 1) Extend sibling selection with DirectInput product GUID and FFB-driver/vendor identity.
replace_once(
    ffb,
    "        struct EnumContext\n"
    "        {\n"
    "            WheelFFBEngine* self = nullptr;\n"
    "            GUID selectedGuid{};\n"
    "            std::string selectedName;\n"
    "            DWORD selectedVidPid = 0;\n"
    "            DWORD preferredVidPid = 0;\n"
    "            bool found = false;\n"
    "            bool matchGuidOnly = false;\n"
    "            bool requirePreferredVidPid = false;\n"
    "        };\n",
    "        struct EnumContext\n"
    "        {\n"
    "            WheelFFBEngine* self = nullptr;\n"
    "            GUID selectedGuid{};\n"
    "            GUID selectedProductGuid{};\n"
    "            GUID selectedFFDriverGuid{};\n"
    "            std::string selectedName;\n"
    "            DWORD selectedVidPid = 0;\n"
    "            GUID preferredProductGuid{};\n"
    "            GUID preferredFFDriverGuid{};\n"
    "            DWORD preferredVidPid = 0;\n"
    "            WORD preferredVendorId = 0;\n"
    "            bool found = false;\n"
    "            bool matchGuidOnly = false;\n"
    "            bool requirePreferredProductGuid = false;\n"
    "            bool requirePreferredVidPid = false;\n"
    "            bool requirePreferredDriverVendor = false;\n"
    "        };\n",
)

replace_once(
    ffb,
    "            if (ctx->matchGuidOnly &&\n"
    "                (wantedGuid.empty() || directinput_guid_key(instance->guidInstance) != wantedGuid))\n"
    "                return DIENUM_CONTINUE;\n\n"
    "            DWORD candidateVidPid = 0;\n"
    "            if (ctx->self && ctx->requirePreferredVidPid)\n"
    "            {\n"
    "                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n"
    "                if (candidateVidPid == 0 || candidateVidPid != ctx->preferredVidPid)\n"
    "                    return DIENUM_CONTINUE;\n"
    "            }\n\n"
    "            if (!ctx->matchGuidOnly && !ctx->requirePreferredVidPid && !wanted.empty() &&\n"
    "                instanceName.find(wanted) == std::string::npos &&\n"
    "                productName.find(wanted) == std::string::npos)\n"
    "            {\n"
    "                return DIENUM_CONTINUE;\n"
    "            }\n\n"
    "            if (candidateVidPid == 0 && ctx->self)\n"
    "                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n\n"
    "            ctx->selectedGuid = instance->guidInstance;\n"
    "            ctx->selectedName = instance->tszProductName;\n"
    "            ctx->selectedVidPid = candidateVidPid;\n",
    "            if (ctx->matchGuidOnly &&\n"
    "                (wantedGuid.empty() || directinput_guid_key(instance->guidInstance) != wantedGuid))\n"
    "                return DIENUM_CONTINUE;\n\n"
    "            if (ctx->requirePreferredProductGuid &&\n"
    "                !directinput_guid_equal(instance->guidProduct, ctx->preferredProductGuid))\n"
    "            {\n"
    "                return DIENUM_CONTINUE;\n"
    "            }\n\n"
    "            DWORD candidateVidPid = 0;\n"
    "            if (ctx->self &&\n"
    "                (ctx->requirePreferredVidPid || ctx->requirePreferredDriverVendor))\n"
    "            {\n"
    "                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n"
    "            }\n\n"
    "            if (ctx->requirePreferredVidPid &&\n"
    "                (candidateVidPid == 0 || candidateVidPid != ctx->preferredVidPid))\n"
    "            {\n"
    "                return DIENUM_CONTINUE;\n"
    "            }\n\n"
    "            if (ctx->requirePreferredDriverVendor)\n"
    "            {\n"
    "                if (candidateVidPid == 0 || LOWORD(candidateVidPid) != ctx->preferredVendorId ||\n"
    "                    directinput_guid_is_zero(ctx->preferredFFDriverGuid) ||\n"
    "                    !directinput_guid_equal(instance->guidFFDriver, ctx->preferredFFDriverGuid))\n"
    "                {\n"
    "                    return DIENUM_CONTINUE;\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx->matchGuidOnly &&\n"
    "                !ctx->requirePreferredProductGuid &&\n"
    "                !ctx->requirePreferredVidPid &&\n"
    "                !ctx->requirePreferredDriverVendor &&\n"
    "                !wanted.empty() &&\n"
    "                instanceName.find(wanted) == std::string::npos &&\n"
    "                productName.find(wanted) == std::string::npos)\n"
    "            {\n"
    "                return DIENUM_CONTINUE;\n"
    "            }\n\n"
    "            if (candidateVidPid == 0 && ctx->self)\n"
    "                candidateVidPid = ctx->self->query_device_vidpid(instance->guidInstance);\n\n"
    "            ctx->selectedGuid = instance->guidInstance;\n"
    "            ctx->selectedProductGuid = instance->guidProduct;\n"
    "            ctx->selectedFFDriverGuid = instance->guidFFDriver;\n"
    "            ctx->selectedName = instance->tszProductName;\n"
    "            ctx->selectedVidPid = candidateVidPid;\n",
)

# Disabling FFB is also a hard boundary for learned physical-device hints.
replace_once(
    ffb,
    "            failedInterfaces_.clear();\n"
    "            preferredVidPid_ = 0;\n\n"
    "            enabledLastTick_ = false;\n",
    "            failedInterfaces_.clear();\n"
    "            preferredVidPid_ = 0;\n"
    "            preferredProductGuid_ = {};\n"
    "            preferredFFDriverGuid_ = {};\n"
    "            preferredVendorId_ = 0;\n\n"
    "            enabledLastTick_ = false;\n",
)

# 3) Consecutive-failure hysteresis: a single vendor-driver SetParameters glitch no
# longer immediately blacklists an otherwise working interface.
replace_once(
    ffb,
    "        void clear_device_failure()\n"
    "        {\n"
    "            deviceFailureSince_ = 0;\n"
    "        }\n",
    "        void clear_constant_live_failure()\n"
    "        {\n"
    "            constantLiveFailureCount_ = 0;\n"
    "        }\n\n"
    "        bool record_constant_live_failure()\n"
    "        {\n"
    "            if (constantLiveFailureCount_ < FFB_CONSTANT_LIVE_FAILURE_LIMIT)\n"
    "                ++constantLiveFailureCount_;\n"
    "            return constantLiveFailureCount_ >= FFB_CONSTANT_LIVE_FAILURE_LIMIT;\n"
    "        }\n\n"
    "        void clear_device_failure()\n"
    "        {\n"
    "            deviceFailureSince_ = 0;\n"
    "        }\n",
)

replace_once(
    ffb,
    "            periodicStrategy_ = 1;\n"
    "        }\n\n"
    "        void teardown_for_reinitialize",
    "            periodicStrategy_ = 1;\n"
    "            clear_constant_live_failure();\n"
    "        }\n\n"
    "        void teardown_for_reinitialize",
)

# Replace the selection pipeline: exact saved GUID -> same product GUID -> exact
# VID/PID -> same FFB driver + USB vendor -> configured name.
replace_once(
    ffb,
    "            if (!configuredGuid.empty())\n"
    "            {\n"
    "                ctx.matchGuidOnly = true;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    // A physical wheel can expose more than one DirectInput\n"
    "                    // interface. Prefer the saved interface, but allow a sibling\n"
    "                    // with the same configured device name after validation fails.\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: saved FFB GUID unavailable or rejected; probing compatible sibling interfaces\");\n"
    "                    ctx.matchGuidOnly = false;\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found && preferredVidPid_ != 0)\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredVidPid = true;\n"
    "                ctx.preferredVidPid = preferredVidPid_;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: no remaining FFB interface shared preferred VID/PID 0x{:08X}; falling back to the configured device name\",\n"
    "                        (unsigned)preferredVidPid_);\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found)\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredVidPid = false;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "            }\n",
    "            if (!configuredGuid.empty())\n"
    "            {\n"
    "                ctx.matchGuidOnly = true;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: saved FFB GUID unavailable or rejected; probing compatible sibling interfaces\");\n"
    "                    ctx.matchGuidOnly = false;\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found && !directinput_guid_is_zero(preferredProductGuid_))\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredProductGuid = true;\n"
    "                ctx.preferredProductGuid = preferredProductGuid_;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                ctx.requirePreferredProductGuid = false;\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: no remaining FFB interface shared the preferred DirectInput product GUID\");\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found && preferredVidPid_ != 0)\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredVidPid = true;\n"
    "                ctx.preferredVidPid = preferredVidPid_;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                ctx.requirePreferredVidPid = false;\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: no remaining FFB interface shared preferred VID/PID 0x{:08X}\",\n"
    "                        (unsigned)preferredVidPid_);\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found && !directinput_guid_is_zero(preferredFFDriverGuid_) &&\n"
    "                preferredVendorId_ != 0)\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredDriverVendor = true;\n"
    "                ctx.preferredFFDriverGuid = preferredFFDriverGuid_;\n"
    "                ctx.preferredVendorId = preferredVendorId_;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "                ctx.requirePreferredDriverVendor = false;\n"
    "                if (FAILED(hr))\n"
    "                {\n"
    "                    release_directinput();\n"
    "                    return false;\n"
    "                }\n"
    "                if (!ctx.found)\n"
    "                {\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: no remaining FFB interface shared preferred FFB driver/vendor; falling back to the configured device name\");\n"
    "                }\n"
    "            }\n\n"
    "            if (!ctx.found)\n"
    "            {\n"
    "                ctx.matchGuidOnly = false;\n"
    "                ctx.requirePreferredProductGuid = false;\n"
    "                ctx.requirePreferredVidPid = false;\n"
    "                ctx.requirePreferredDriverVendor = false;\n"
    "                hr = directInput_->EnumDevices(\n"
    "                    DI8DEVCLASS_GAMECTRL, enum_devices_callback, &ctx,\n"
    "                    DIEDFL_ATTACHEDONLY | DIEDFL_FORCEFEEDBACK);\n"
    "            }\n",
)

replace_once(
    ffb,
    "            selectedGuid_ = ctx.selectedGuid;\n"
    "            selectedName_ = ctx.selectedName;\n"
    "            const bool selectedConfiguredInterface =\n"
    "                !configuredGuid.empty() && directinput_guid_key(selectedGuid_) == configuredGuid;\n"
    "            if (ctx.selectedVidPid != 0 &&\n"
    "                (preferredVidPid_ == 0 || selectedConfiguredInterface))\n"
    "            {\n"
    "                preferredVidPid_ = ctx.selectedVidPid;\n"
    "            }\n"
    "            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());\n"
    "            selectedConfiguredName_ = lower_copy(Settings::WheelFFBDeviceName.get().c_str());\n"
    "            spdlog::info(\"WheelFFB: selected DirectInput identity '{}' / '{}'\",\n"
    "                selectedName_, directinput_guid_key(selectedGuid_));\n",
    "            selectedGuid_ = ctx.selectedGuid;\n"
    "            selectedName_ = ctx.selectedName;\n"
    "            const bool selectedConfiguredInterface =\n"
    "                !configuredGuid.empty() && directinput_guid_key(selectedGuid_) == configuredGuid;\n"
    "            if (!directinput_guid_is_zero(ctx.selectedProductGuid) &&\n"
    "                (directinput_guid_is_zero(preferredProductGuid_) || selectedConfiguredInterface))\n"
    "            {\n"
    "                preferredProductGuid_ = ctx.selectedProductGuid;\n"
    "            }\n"
    "            if (!directinput_guid_is_zero(ctx.selectedFFDriverGuid) &&\n"
    "                (directinput_guid_is_zero(preferredFFDriverGuid_) || selectedConfiguredInterface))\n"
    "            {\n"
    "                preferredFFDriverGuid_ = ctx.selectedFFDriverGuid;\n"
    "            }\n"
    "            if (ctx.selectedVidPid != 0)\n"
    "            {\n"
    "                if (preferredVidPid_ == 0 || selectedConfiguredInterface)\n"
    "                    preferredVidPid_ = ctx.selectedVidPid;\n"
    "                if (preferredVendorId_ == 0 || selectedConfiguredInterface)\n"
    "                    preferredVendorId_ = LOWORD(ctx.selectedVidPid);\n"
    "            }\n"
    "            selectedConfiguredGuid_ = lower_copy(Settings::WheelFFBDeviceGuid.get().c_str());\n"
    "            selectedConfiguredName_ = lower_copy(Settings::WheelFFBDeviceName.get().c_str());\n"
    "            spdlog::info(\n"
    "                \"WheelFFB: selected DirectInput identity '{}' / '{}' product={} ffDriver={} vidpid=0x{:08X}\",\n"
    "                selectedName_, directinput_guid_key(selectedGuid_),\n"
    "                directinput_guid_key(ctx.selectedProductGuid),\n"
    "                directinput_guid_key(ctx.selectedFFDriverGuid),\n"
    "                (unsigned)ctx.selectedVidPid);\n",
)

# Preserve the existing descriptor-reset verifier anchor and clear hysteresis after it.
replace_once(
    ffb,
    "                constantEffectPolar_ = polar;\n"
    "                prevConstantLevel_ = 0;\n"
    "                lastConstantWriteTick_ = 0;\n"
    "                spdlog::info(\n",
    "                constantEffectPolar_ = polar;\n"
    "                prevConstantLevel_ = 0;\n"
    "                lastConstantWriteTick_ = 0;\n"
    "                clear_constant_live_failure();\n"
    "                spdlog::info(\n",
)

replace_once(
    ffb,
    "                recreateRampFrames_ = RecreateRampFrames;\n"
    "                prevConstantLevel_ = 0;\n"
    "                prevStructuralLevel_ = 0;\n"
    "                spdlog::info(\"WheelFFB: recreated ConstantForce after handle loss; ramping in\");\n",
    "                recreateRampFrames_ = RecreateRampFrames;\n"
    "                prevConstantLevel_ = 0;\n"
    "                prevStructuralLevel_ = 0;\n"
    "                clear_constant_live_failure();\n"
    "                spdlog::info(\"WheelFFB: recreated ConstantForce after handle loss; ramping in\");\n",
)

replace_once(
    ffb,
    "            if (FAILED(hr))\n"
    "            {\n"
    "                mark_selected_interface_failed(\"ConstantForce live SetParameters\", hr);\n"
    "                request_device_reinitialize(\"ConstantForce output failed\", hr);\n"
    "                spdlog::warn(\n"
    "                    \"WheelFFB: constant force update failed (0x{:08X}); current interface will be skipped on reinitialization\",\n"
    "                    (unsigned)hr);\n"
    "                return;\n"
    "            }\n\n"
    "            clear_device_failure();\n"
    "            prevConstantLevel_ = requestedLevel;\n",
    "            if (FAILED(hr))\n"
    "            {\n"
    "                if (!record_constant_live_failure())\n"
    "                {\n"
    "                    note_device_failure(\"ConstantForce live SetParameters\", hr);\n"
    "                    spdlog::warn(\n"
    "                        \"WheelFFB: transient ConstantForce update failure {}/{} (0x{:08X}); retaining the current interface\",\n"
    "                        constantLiveFailureCount_, FFB_CONSTANT_LIVE_FAILURE_LIMIT, (unsigned)hr);\n"
    "                    return;\n"
    "                }\n\n"
    "                mark_selected_interface_failed(\"ConstantForce live SetParameters\", hr);\n"
    "                request_device_reinitialize(\"ConstantForce output failed repeatedly\", hr);\n"
    "                spdlog::warn(\n"
    "                    \"WheelFFB: ConstantForce update failed {} consecutive times (0x{:08X}); current interface will be skipped on reinitialization\",\n"
    "                    constantLiveFailureCount_, (unsigned)hr);\n"
    "                return;\n"
    "            }\n\n"
    "            clear_constant_live_failure();\n"
    "            clear_device_failure();\n"
    "            prevConstantLevel_ = requestedLevel;\n",
)

# Runtime member state for learned physical identity and failure hysteresis.
replace_once(
    ffb,
    "        std::vector<FailedInterfaceState> failedInterfaces_;\n"
    "        DWORD preferredVidPid_ = 0;\n"
    "        DWORD constantRecreateHoldoffUntil_ = 0;\n",
    "        std::vector<FailedInterfaceState> failedInterfaces_;\n"
    "        DWORD preferredVidPid_ = 0;\n"
    "        GUID preferredProductGuid_{};\n"
    "        GUID preferredFFDriverGuid_{};\n"
    "        WORD preferredVendorId_ = 0;\n"
    "        DWORD constantRecreateHoldoffUntil_ = 0;\n",
)

replace_once(
    ffb,
    "        DWORD deviceFailureSince_ = 0;\n"
    "        DWORD deviceReinitAfter_ = 0;\n"
    "        bool deviceReinitPending_ = false;\n",
    "        DWORD deviceFailureSince_ = 0;\n"
    "        unsigned constantLiveFailureCount_ = 0;\n"
    "        DWORD deviceReinitAfter_ = 0;\n"
    "        bool deviceReinitPending_ = false;\n",
)

# 4) Verifier guards for the new recovery invariants.
replace_once(
    verify,
    "req(ffb, 'active_failed_interface_count()', 'FFB backend walks all rejected candidates instead of only one sibling')\n"
    "req(ffb, 'while (!ready)', 'FFB candidate probing is exhaustive without a fixed interface-count cap')\n"
    "forbid(ffb, 'MaxInterfaceProbes', 'FFB candidate probing has no arbitrary interface-count ceiling')\n"
    "req(ffb, 'DIPROP_VIDPID', 'FFB sibling selection can prefer matching physical VID/PID')\n"
    "req(ffb, 'requirePreferredVidPid', 'FFB sibling selection has a same-VID/PID pass before name fallback')\n",
    "req(ffb, 'active_failed_interface_count()', 'FFB backend walks all rejected candidates instead of only one sibling')\n"
    "req(ffb, 'const bool ready = initialize();', 'FFB candidate probing performs one potentially expensive interface open per update tick')\n"
    "req(ffb, 'next compatible interface will be probed on the next update tick', 'rejected sibling probing yields back to the game thread')\n"
    "forbid(ffb, 'while (!ready)', 'FFB candidate probing never loops over multiple device opens in one frame')\n"
    "forbid(ffb, 'MaxInterfaceProbes', 'FFB candidate probing has no arbitrary interface-count ceiling')\n"
    "req(ffb, 'DIPROP_VIDPID', 'FFB sibling selection can prefer matching physical VID/PID')\n"
    "req(ffb, 'requirePreferredProductGuid', 'FFB sibling selection prefers the DirectInput product GUID for one physical device')\n"
    "req(ffb, 'instance->guidFFDriver', 'FFB sibling selection can use the force-feedback driver identity')\n"
    "req(ffb, 'requirePreferredDriverVendor', 'FFB sibling selection can fall back to same FFB driver plus USB vendor')\n"
    "req(ffb, 'requirePreferredVidPid', 'FFB sibling selection has a same-VID/PID pass before name fallback')\n",
)

insert_after_once(
    verify,
    "req(ffb, 'mark_selected_interface_failed(\"ConstantForce live SetParameters\", hr)', 'runtime ConstantForce failure quarantines the bad interface before reinit')\n",
    "req(ffb, 'FFB_CONSTANT_LIVE_FAILURE_LIMIT = 3', 'runtime ConstantForce quarantine requires repeated live-output failure')\n"
    "req(ffb, 'if (!record_constant_live_failure())', 'single ConstantForce live-output failure is retained as transient')\n"
    "req(ffb, 'transient ConstantForce update failure', 'transient ConstantForce failures are logged without immediate interface blacklist')\n",
)

# Source snapshot should contain every verifier dependency, so the artifact can be
# rechecked independently instead of being only a curated partial tree.
replace_once(
    workflow,
    "            tools/verify_wheel_ffb_current.py\n",
    "            tools/verify_wheel_ffb_current.py\n"
    "            src/wheel_profile_store.hpp\n"
    "            src/hooks_input.cpp\n"
    "            src/overlay/settings_ui.cpp\n"
    "            src/overlay/overlay.cpp\n"
    "            CMakeLists.txt\n"
    "            cmake.toml\n"
    "            README.md\n"
    "            WHEEL_FFB.md\n"
    "            RELEASE_NOTES_v0.1.md\n"
    "            .github/workflows/build.yml\n"
    "          include-hidden-files: true\n",
)

# Guard the source-artifact dependency set in the verifier itself.
insert_after_once(
    verify,
    "ini = read('OutRun2006Tweaks.ini')\n",
    "workflow = read('.github/workflows/build.yml')\n",
)

insert_after_once(
    verify,
    "req(ini, 'UseNewInput = true', 'shipped SDL multi-device input default')\n",
    "for rel in (\n"
    "    'src/wheel_profile_store.hpp', 'src/hooks_input.cpp',\n"
    "    'src/overlay/settings_ui.cpp', 'src/overlay/overlay.cpp',\n"
    "    'CMakeLists.txt', 'cmake.toml', 'README.md', 'WHEEL_FFB.md',\n"
    "    'RELEASE_NOTES_v0.1.md', '.github/workflows/build.yml',\n"
    "):\n"
    "    req(workflow, rel, f'source snapshot includes verifier dependency {rel}')\n",
)

print("Priority FFB hardening patch applied")
