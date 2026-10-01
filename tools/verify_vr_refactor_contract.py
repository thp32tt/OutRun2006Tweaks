#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        errors.append(f"missing required file: {rel}")
        return ""
    return path.read_text(encoding="utf-8")

tracker = read("src/vr/state/state_block_tracker.hpp")
r22 = read("src/vr/d3d9/stereo_renderer_r22.cpp")
r29 = read("src/vr/d3d9/stereo_renderer_r29.cpp")
r30 = read("src/vr/d3d9/stereo_renderer_r30.cpp")
r31 = read("src/vr/d3d9/stereo_renderer_r31.cpp")
r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
r33 = read("src/vr/d3d9/stereo_renderer_r33.cpp")
r34 = read("src/vr/d3d9/stereo_renderer_r34.cpp")

for marker in (
    "class StateBlockTracker final",
    "SetR22Reliable",
    "SetR31Reliable",
    "R22Reliable",
    "R31Reliable",
    "Reliable",
    "MarkCoverageLost",
    "ResetCoverageLoss",
    "CoverageLost",
    "RequireResync",
    "ConsumeResync",
    "BeginRecording",
    "EndRecording",
    "IsRecording",
    "NoteApply",
    "RecordingCount",
    "ApplyCount",
):
    if marker not in tracker:
        errors.append(f"StateBlockTracker API missing marker: {marker}")

for rel, source in (
    ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
    ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
    ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
):
    if "state_block_tracker.hpp" not in source:
        errors.append(f"{rel}: StateBlockTracker include missing")

for legacy in (
    "R22StateBlockTrackingReliable",
    "R31StateBlockTrackingReliable",
    "R31StateBlockCoverageLost",
    "R31StateBlockResyncPending",
    "R31StateBlockRecordings",
    "R31StateBlockApplies",
    "R31StateBlockRecording",
):
    for rel, source in (
        ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
        ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
        ("src/vr/d3d9/stereo_renderer_r32.cpp", r32),
        ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
    ):
        if legacy in source:
            errors.append(f"{rel}: legacy StateBlock authority reintroduced: {legacy}")

if "StateBlockTracker::Reliable()" not in r33:
    errors.append("R33: neutral aggregate StateBlock reliability query missing")

for required in (
    "src/vr/render/screen_space_kind.hpp",
    "src/vr/render/screen_space_api.hpp",
    "src/vr/render/stereo_base_policy.hpp",
    "src/vr/render/fast_path_support.hpp",
    "src/vr/render/lower_draw_api.hpp",
    "src/vr/render/xyzrhw_api.hpp",
    "src/vr/state/right_depth_stencil_sync.hpp",
    "src/vr/state/depth_target_state.hpp",
    "src/vr/lifecycle/frame_accounting.hpp",
):
    read(required)

for legacy in (
    "R9",
    "R13",
    "R20",
    "R21",
    "R22",
    "R23",
    "R26",
    "R29",
    "R30",
    "R31",
):
    import re
    if re.search(rf"\\b{legacy}[A-Za-z0-9_]+", r32):
        errors.append(f"R32 regained lower-layer implementation dependency: {legacy}*")

for legacy in (
    "R9",
    "R13",
    "R20",
    "R21",
    "R22",
    "R23",
    "R26",
    "R29",
    "R30",
):
    import re
    if re.search(rf"\\b{legacy}[A-Za-z0-9_]+", r31):
        errors.append(f"R31 regained lower-layer implementation dependency: {legacy}*")

if r29.count("R29StereoInstallState.store(") != 1:
    errors.append("R29 install-state storage must have one write boundary")
if r29.count("R29StereoInstallState.load(") != 1:
    errors.append("R29 install-state storage must have one read boundary")
read_state_begin = r29.find("ReadStereoBaseInstallState() noexcept")
effect_state_begin = r29.find("struct R29EffectState", read_state_begin)
if read_state_begin < 0 or effect_state_begin <= read_state_begin:
    errors.append("R29 install-state read boundary missing")
else:
    read_state = r29[read_state_begin:effect_state_begin]
    if "R29StereoInstallState.load(std::memory_order_acquire)" not in read_state:
        errors.append("R29 install-state read boundary no longer owns atomic load")
    if "return ReadStereoBaseInstallState();" in read_state:
        errors.append("R29 install-state read boundary became recursive")
public_state_begin = r29.rfind("StereoBaseInstallState() noexcept")
if public_state_begin < 0 or "return ReadStereoBaseInstallState();" not in r29[public_state_begin:]:
    errors.append("R29 public install-state facade bypassed read boundary")

r29_transaction_begin = r29.find("bool R29InstallHookTransaction() noexcept")
r29_transaction_end = r29.find("void R29PublishInstallResult(", r29_transaction_begin)
if r29_transaction_begin < 0 or r29_transaction_end <= r29_transaction_begin:
    errors.append("R29 disabled-first hook transaction boundary missing")
else:
    transaction = r29[r29_transaction_begin:r29_transaction_end]
    markers = [
        "R29DrawPrimitiveR27Hook = safetyhook::create_inline(",
        "R29DrawIndexedPrimitiveR27Hook = safetyhook::create_inline(",
        "R29DrawPrimitiveUPR27Hook = safetyhook::create_inline(",
        "R29DrawIndexedPrimitiveUPR27Hook = safetyhook::create_inline(",
        "R29SetRenderStateR22Hook = safetyhook::create_inline(",
    ]
    positions = [transaction.find(marker) for marker in markers]
    if min(positions) < 0 or positions != sorted(positions):
        errors.append("R29 hook transaction changed disabled-first creation order")
    enable_pos = transaction.find("if (R29EnableStereoHooks())")
    rollback_pos = transaction.find("R29RollbackStereoHooks()", enable_pos)
    if enable_pos < 0 or rollback_pos <= enable_pos:
        errors.append("R29 hook transaction lost enable-then-rollback behavior")
r29_install = r29[r29.find("DWORD WINAPI R29StereoInstallThread("):]
if "if (!R29InstallHookTransaction())" not in r29_install:
    errors.append("R29 install thread bypassed hook transaction boundary")
for marker in (
    "R29DrawPrimitiveR27Hook = safetyhook::create_inline(",
    "R29DrawIndexedPrimitiveR27Hook = safetyhook::create_inline(",
    "R29DrawPrimitiveUPR27Hook = safetyhook::create_inline(",
    "R29DrawIndexedPrimitiveUPR27Hook = safetyhook::create_inline(",
    "R29SetRenderStateR22Hook = safetyhook::create_inline(",
):
    if marker in r29_install:
        errors.append(f"R29 install thread regained hook creation ownership: {marker}")

if r29.count('HookManager::ReportAsyncResult("OpenXRVRStereoR29", success)') != 1:
    errors.append("R29 async install-result reporting is no longer centralized")
r29_install_begin = r29.find("DWORD WINAPI R29StereoInstallThread(")
r29_startup_boundary = r29.find("bool R29StartInstallThread()", r29_install_begin)
if r29_install_begin < 0 or r29_startup_boundary <= r29_install_begin:
    errors.append("R29 install thread boundary missing")
else:
    install = r29[r29_install_begin:r29_startup_boundary]
    if install.count("R29PublishInstallResult(") != 3:
        errors.append("R29 install thread must publish exactly three failure result routes")
    if install.count("R29CompleteSuccessfulInstall();") != 1:
        errors.append("R29 install thread must delegate exactly one successful terminal route")
    if 'HookManager::ReportAsyncResult("OpenXRVRStereoR29"' in install:
        errors.append("R29 install thread regained direct async publication")

r29_success_begin = r29.find("void R29CompleteSuccessfulInstall() noexcept")
r29_success_end = r29.find("enum class R29PrerequisiteDecision", r29_success_begin)
if r29_success_begin < 0 or r29_success_end <= r29_success_begin:
    errors.append("R29 successful-install publication boundary missing")
else:
    successful = r29[r29_success_begin:r29_success_end]
    order = [
        successful.find("R29ArmMonoSafety(2)"),
        successful.find("InvalidateRawWvpGeneration()"),
        successful.find("R29PublishInstallResult("),
    ]
    if min(order) < 0 or order != sorted(order):
        errors.append(
            "R29 successful install changed mono-safety/WVP/Ready publication order")
    if "InstallState::Ready, true" not in successful:
        errors.append("R29 successful install must publish Ready=true")
    if "R29ArmMonoSafety(2);" in install or \
            "InvalidateRawWvpGeneration();" in install:
        errors.append("R29 install thread regained successful cleanup ownership")

for marker in (
    "enum class R29PrerequisiteDecision",
    "R29PrerequisiteWaitAttempts = 4800",
    "R29PrerequisiteWaitMs = 25",
    "R29ClassifyPrerequisite(",
    "R29PrerequisiteDecision::Wait",
    "R29PrerequisiteDecision::Fail",
    "R29PrerequisiteDecision::Install",
):
    if marker not in r29:
        errors.append(f"R29 prerequisite wait-policy boundary missing marker: {marker}")
if "attempt < 4800" in r29 or "Sleep(25)" in r29:
    errors.append("R29 prerequisite timing literal escaped wait-policy boundary")
if "attempt < R29PrerequisiteWaitAttempts" not in r29 or \
        "Sleep(R29PrerequisiteWaitMs)" not in r29:
    errors.append("R29 install thread bypassed prerequisite timing policy")
if "R29ClassifyPrerequisite(r26, rendererR29)" not in r29:
    errors.append("R29 install thread bypassed prerequisite classification boundary")

r29_startup_begin = r29.find("bool R29StartInstallThread() noexcept")
r29_hook_begin = r29.find("class VRStereoR29Hook", r29_startup_begin)
if r29_startup_begin < 0 or r29_hook_begin <= r29_startup_begin:
    errors.append("R29 startup thread publication boundary missing")
else:
    startup = r29[r29_startup_begin:r29_hook_begin]
    order = [
        startup.find("SetStereoBaseInstallState(State::Pending)"),
        startup.find("CreateThread(nullptr, 0,"),
        startup.find("if (!thread)"),
        startup.find("SetStereoBaseInstallState(State::Failed)"),
        startup.find("CloseHandle(thread)"),
    ]
    if min(order) < 0 or order != sorted(order):
        errors.append("R29 startup boundary changed Pending/CreateThread/Failed/CloseHandle order")
r29_apply_begin = r29.find("bool apply() override", r29_hook_begin)
r29_apply_end = r29.find("static VRStereoR29Hook instance", r29_apply_begin)
if r29_apply_begin < 0 or r29_apply_end <= r29_apply_begin:
    errors.append("R29 hook apply boundary missing")
else:
    apply_body = r29[r29_apply_begin:r29_apply_end]
    if "return R29StartInstallThread();" not in apply_body:
        errors.append("R29 apply no longer delegates startup ownership")
    for escaped in ("CreateThread(", "CloseHandle(", "SetStereoBaseInstallState("):
        if escaped in apply_body:
            errors.append(f"R29 apply regained startup ownership: {escaped}")

for legacy in (
    "R26InstallState",
    "R29RendererState",
    "R29InvalidateRawWvpGeneration",
    "R29InvalidateRendererStateAfterExternalRestore",
):
    if legacy in r29:
        errors.append(f"R29 regained lower-layer prerequisite/recovery dependency: {legacy}")

for required in (
    "src/vr/lifecycle/correction_overlay_state.hpp",
    "src/vr/game/renderer_recovery.hpp",
):
    read(required)

for legacy in (
    "R9",
    "R13",
    "R20",
    "R21",
    "R22",
    "R23",
    "R26",
    "R29",
):
    import re
    if re.search(rf"\\b{legacy}[A-Za-z0-9_]+", r30):
        errors.append(f"R30 regained lower-layer implementation dependency: {legacy}*")

for marker in (
    "R30InstallStateStorage",
    "R30SetInstallState",
    "R30GetInstallState",
    "R30PublishInstallResult",
):
    if marker not in r30:
        errors.append(f"R30 install lifecycle boundary missing marker: {marker}")

if r30.count("R30InstallStateStorage.store(") != 1:
    errors.append("R30 install-state storage must have one write boundary")
if r30.count("R30InstallStateStorage.load(") != 1:
    errors.append("R30 install-state storage must have one read boundary")
if r30.count('HookManager::ReportAsyncResult(\n                "OpenXRVRStereoR30HUD", success)') != 1:
    errors.append("R30 async install-result reporting is no longer centralized")
if "R30InstallState.store(" in r30 or "R30InstallState.load(" in r30:
    errors.append("R30 legacy direct install-state access reintroduced")

for marker in (
    "enum class R30PrerequisiteDecision",
    "R30PrerequisiteWaitAttempts = 4800",
    "R30PrerequisiteWaitMs = 25",
    "R30ClassifyPrerequisite(",
    "R30PrerequisiteDecision::Wait",
    "R30PrerequisiteDecision::Fail",
    "R30PrerequisiteDecision::Install",
):
    if marker not in r30:
        errors.append(f"R30 prerequisite wait-policy boundary missing marker: {marker}")

if "attempt < 4800" in r30 or "Sleep(25)" in r30:
    errors.append("R30 prerequisite timing literal escaped the wait-policy boundary")
if "attempt < R30PrerequisiteWaitAttempts" not in r30 or \
        "Sleep(R30PrerequisiteWaitMs)" not in r30:
    errors.append("R30 install thread no longer consumes the prerequisite wait policy")
for marker in (
    "enum class R32PrerequisiteDecision",
    "R32PrerequisiteWaitAttempts = 4800",
    "R32PrerequisiteWaitMs = 25",
    "R32ClassifyPrerequisite(",
    "R32PrerequisiteDecision::Wait",
    "R32PrerequisiteDecision::Fail",
    "R32PrerequisiteDecision::Install",
):
    if marker not in r32:
        errors.append(f"R32 prerequisite wait-policy boundary missing marker: {marker}")
if "attempt < 4800" in r32 or "Sleep(25)" in r32:
    errors.append("R32 prerequisite timing literal escaped the wait-policy boundary")
if "attempt < R32PrerequisiteWaitAttempts" not in r32 or \
        "Sleep(R32PrerequisiteWaitMs)" not in r32:
    errors.append("R32 install thread no longer consumes prerequisite wait policy")
for marker in (
    "R34PrerequisiteWaitAttempts = 4800",
    "R34PrerequisiteWaitMs = 25",
    "attempt < R34PrerequisiteWaitAttempts",
    "Sleep(R34PrerequisiteWaitMs)",
):
    if marker not in r34:
        errors.append(f"R34 prerequisite wait-policy boundary missing: {marker}")
if "attempt < 4800" in r34 or "Sleep(25)" in r34:
    errors.append("R34 prerequisite timing literal escaped wait-policy boundary")

for marker in (
    "R33PrerequisiteWaitAttempts = 4800",
    "R33PrerequisiteWaitMs = 25",
    "attempt < R33PrerequisiteWaitAttempts",
    "Sleep(R33PrerequisiteWaitMs)",
):
    if marker not in r33:
        errors.append(f"R33 prerequisite wait-policy boundary missing: {marker}")
if "attempt < 4800" in r33 or "Sleep(25)" in r33:
    errors.append("R33 prerequisite timing literal escaped wait-policy boundary")

if "void R32PublishInstallState(" not in r32:
    errors.append("R32 install-state publication boundary missing")
if r32.count("R32InstallState.store(") != 1:
    errors.append("R32 install-state store escaped publication boundary")
for marker in (
    "R32PublishInstallState(State::Pending)",
    "R32PublishInstallState(State::Failed)",
    "R32PublishInstallState(State::Ready)",
):
    if marker not in r32:
        errors.append(f"R32 install-state publication path missing: {marker}")

if "R32ClassifyPrerequisite(" not in r32:
    errors.append("R32 install thread bypassed prerequisite classifier")

if "R30ClassifyPrerequisite(StereoBaseInstallState())" not in r30:
    errors.append("R30 install thread bypassed prerequisite classification boundary")

if "void R30FailInstall() noexcept" not in r30:
    errors.append("R30 install failure boundary missing")
else:
    fail_begin = r30.find("void R30FailInstall() noexcept")
    fail_end = r30.find("enum class R30PrerequisiteDecision", fail_begin)
    fail_body = r30[fail_begin:fail_end]
    rollback_pos = fail_body.find("R30RollbackBufferShadowHooks()")
    publish_pos = fail_body.find("R30PublishInstallResult(")
    if rollback_pos < 0 or publish_pos <= rollback_pos:
        errors.append("R30 failure boundary changed buffer-rollback-before-publication order")

success_begin = r30.find("void R30CompleteSuccessfulInstall() noexcept")
success_end = r30.find("enum class R30PrerequisiteDecision", success_begin)
if success_begin < 0 or success_end <= success_begin:
    errors.append("R30 successful-install publication boundary missing")
else:
    success_body = r30[success_begin:success_end]
    if success_body.count("R30PublishInstallResult(") != 1 or \
            "R30InstallStateValue::Ready, true" not in success_body:
        errors.append("R30 successful-install boundary must publish Ready=true exactly once")

transaction_begin = r30.find("bool R30InstallHookTransaction() noexcept")
transaction_end = r30.find("void R30PublishInstallResult(", transaction_begin)
install_begin = r30.find("DWORD WINAPI R30InstallThread(")
if transaction_begin < 0 or transaction_end <= transaction_begin:
    errors.append("R30 disabled-first hook transaction ownership boundary missing")
else:
    transaction = r30[transaction_begin:transaction_end]
    create_markers = [
        "R30PresentR29Hook = safetyhook::create_inline(",
        "R30ResetR29Hook = safetyhook::create_inline(",
        "R30DrawPrimitiveR29Hook = safetyhook::create_inline(",
        "R30DrawIndexedPrimitiveR29Hook = safetyhook::create_inline(",
        "R30DrawPrimitiveUPR29Hook = safetyhook::create_inline(",
        "R30DrawIndexedPrimitiveUPR29Hook = safetyhook::create_inline(",
    ]
    create_positions = [transaction.find(marker) for marker in create_markers]
    if min(create_positions) < 0 or create_positions != sorted(create_positions):
        errors.append("R30 hook transaction changed disabled-first creation order")
    enable_pos = transaction.find("if (R30EnableHooks())")
    rollback_pos = transaction.find("R30RollbackHooks()", enable_pos)
    if enable_pos < 0 or rollback_pos <= enable_pos:
        errors.append("R30 hook transaction lost enable-then-rollback behavior")

if install_begin < 0:
    errors.append("R30 install thread missing")
else:
    install_thread = r30[install_begin:]
    if install_thread.count("R30FailInstall();") != 3:
        errors.append("R30 install thread must route all three failure exits through one boundary")
    if "R30RollbackBufferShadowHooks();" in install_thread or \
            "R30PublishInstallResult(State::Failed, false);" in install_thread:
        errors.append("R30 install thread regained inline failure cleanup/publication ownership")
    if "if (!R30InstallHookTransaction())" not in install_thread:
        errors.append("R30 install thread bypassed hook transaction boundary")
    if install_thread.count("R30CompleteSuccessfulInstall();") != 1:
        errors.append("R30 install thread must delegate exactly one successful terminal route")
    if "R30PublishInstallResult(State::Ready, true);" in install_thread:
        errors.append("R30 install thread regained inline successful publication ownership")
    for marker in (
        "R30PresentR29Hook = safetyhook::create_inline(",
        "R30ResetR29Hook = safetyhook::create_inline(",
        "R30DrawPrimitiveR29Hook = safetyhook::create_inline(",
        "R30DrawIndexedPrimitiveR29Hook = safetyhook::create_inline(",
        "R30DrawPrimitiveUPR29Hook = safetyhook::create_inline(",
        "R30DrawIndexedPrimitiveUPR29Hook = safetyhook::create_inline(",
    ):
        if marker in install_thread:
            errors.append(f"R30 install thread regained hook creation ownership: {marker}")

skyglow_gate_begin = r30.find("bool R30ShouldApplySkyGlow() noexcept")
present_begin = r30.find("HRESULT __stdcall PresentDestR30(")
if skyglow_gate_begin < 0 or present_begin <= skyglow_gate_begin:
    errors.append("R30 SkyGlow eligibility boundary missing")
else:
    gate = r30[skyglow_gate_begin:present_begin]
    for marker in (
        "Settings::SkyGlowFactor > 0",
        "StereoWanted()",
        "FrameHadWorldStereo",
        "FrameHadDuplicatedDraw",
        "!FrameRightDrawFailed",
        "!FrameStereoIncomplete",
    ):
        if marker not in gate:
            errors.append(f"R30 SkyGlow eligibility lost protected condition: {marker}")
    present_end = r30.find("void R30PrepareSkyGlowForReset()", present_begin)
    present = r30[present_begin:present_end]
    if "if (R30ShouldApplySkyGlow())" not in present:
        errors.append("R30 Present bypassed SkyGlow eligibility boundary")
    for escaped in (
        "Settings::SkyGlowFactor > 0",
        "FrameHadWorldStereo",
        "FrameHadDuplicatedDraw",
        "FrameRightDrawFailed",
        "FrameStereoIncomplete",
    ):
        if escaped in present:
            errors.append(f"R30 Present regained inline SkyGlow eligibility: {escaped}")

if "R30TelemetryIntervalMs = 5000" not in r30:
    errors.append("R30 telemetry cadence policy missing")
if "now - R30LastTelemetryMs < R30TelemetryIntervalMs" not in r30:
    errors.append("R30 telemetry logger bypassed cadence policy")
if "now - R30LastTelemetryMs < 5000" in r30:
    errors.append("R30 telemetry cadence literal escaped policy boundary")

reset_prep_begin = r30.find("void R30PrepareSkyGlowForReset() noexcept")
reset_dest_begin = r30.find("HRESULT __stdcall ResetDestR30(")
hud_scale_begin = r30.find("float R30HudScaleValue()", reset_dest_begin)
if reset_prep_begin < 0 or reset_dest_begin <= reset_prep_begin:
    errors.append("R30 SkyGlow reset preparation boundary missing")
else:
    reset_prep = r30[reset_prep_begin:reset_dest_begin]
    release_pos = reset_prep.find("R30ReleaseSkyGlowResources()")
    epoch_pos = reset_prep.find("R30SkyGlowSceneCaptureEpoch = 0")
    if release_pos < 0 or epoch_pos <= release_pos:
        errors.append("R30 SkyGlow reset preparation changed release-before-epoch order")
if reset_dest_begin < 0 or hud_scale_begin <= reset_dest_begin:
    errors.append("R30 Reset callback boundary missing")
else:
    reset_dest = r30[reset_dest_begin:hud_scale_begin]
    prep_pos = reset_dest.find("R30PrepareSkyGlowForReset()")
    lower_pos = reset_dest.find("R30ResetR29Hook.stdcall<HRESULT>")
    if prep_pos < 0 or lower_pos <= prep_pos:
        errors.append("R30 Reset callback changed SkyGlow-prep-before-lower-Reset order")
    if "R30ReleaseSkyGlowResources()" in reset_dest or \
            "R30SkyGlowSceneCaptureEpoch = 0" in reset_dest:
        errors.append("R30 Reset callback regained inline SkyGlow reset ownership")

startup_begin = r30.find("bool R30StartInstallThread() noexcept")
startup_end = r30.find("class VRStereoR30HudHook", startup_begin)
if startup_begin < 0 or startup_end <= startup_begin:
    errors.append("R30 startup thread publication boundary missing")
else:
    startup = r30[startup_begin:startup_end]
    startup_order = [
        startup.find("R30SetInstallState(State::Pending)"),
        startup.find("CreateThread(nullptr, 0,"),
        startup.find("if (!thread)"),
        startup.find("R30SetInstallState(State::Failed)"),
        startup.find("CloseHandle(thread)"),
    ]
    if min(startup_order) < 0 or startup_order != sorted(startup_order):
        errors.append("R30 startup boundary changed Pending/CreateThread/Failed/CloseHandle order")

apply_begin = r30.find("bool apply() override")
apply_end = r30.find("static VRStereoR30HudHook instance", apply_begin)
if apply_begin < 0 or apply_end <= apply_begin:
    errors.append("R30 hook apply boundary missing")
else:
    apply_body = r30[apply_begin:apply_end]
    if "return R30StartInstallThread();" not in apply_body:
        errors.append("R30 apply no longer delegates startup ownership")
    for escaped in ("CreateThread(", "CloseHandle(", "R30SetInstallState("):
        if escaped in apply_body:
            errors.append(f"R30 apply regained startup ownership: {escaped}")

for marker in (
    "enum class R31PrerequisiteDecision",
    "R31PrerequisiteWaitAttempts = 4800",
    "R31PrerequisiteWaitMs = 25",
    "R31ClassifyPrerequisite(",
):
    if marker not in r31:
        errors.append(f"R31 prerequisite policy boundary missing marker: {marker}")
if "attempt < 4800" in r31 or "Sleep(25)" in r31:
    errors.append("R31 prerequisite timing literal escaped policy boundary")
if "attempt < R31PrerequisiteWaitAttempts" not in r31 or "Sleep(R31PrerequisiteWaitMs)" not in r31:
    errors.append("R31 install thread no longer consumes prerequisite timing policy")
if "R31ClassifyPrerequisite(r30, renderer)" not in r31:
    errors.append("R31 install thread bypassed prerequisite classifier")

r33_read_begin = r33.find("ReadFinalDispatchInstallState() noexcept")
r33_public_read_begin = r33.find("FinalDispatchInstallState() noexcept", r33_read_begin + 1)
if r33_read_begin < 0 or r33_public_read_begin <= r33_read_begin:
    errors.append("R33 final-dispatch install-state read boundary missing")
else:
    r33_read_body = r33[r33_read_begin:r33_public_read_begin]
    if "return R33InstallState.load(std::memory_order_acquire);" not in r33_read_body:
        errors.append("R33 install-state read boundary lost sole acquire-load")
    if "return ReadFinalDispatchInstallState();" in r33_read_body:
        errors.append("R33 install-state read boundary became recursively self-referential")
    r33_public_read = r33[r33_public_read_begin:]
    if "return ReadFinalDispatchInstallState();" not in r33_public_read:
        errors.append("R33 public install-state facade bypassed read boundary")
    if "R33InstallState.load(" in r33_public_read:
        errors.append("R33 public install-state facade regained direct atomic load")

for legacy in (
    "R29StableStereoBase",
    "R29FragileEffectCached",
    "R29ArmMonoSafety",
    "R29StableTwoEyeDraws",
    "R30ScreenSpaceKind",
    "R30ClassifyScreenSpacePass",
    "R30BuildScreenSpaceEyeConstants",
    "R30ScreenSpaceFovDraws",
    "R30DrawPrimitiveR29Hook",
    "R30DrawIndexedPrimitiveR29Hook",
    "R30DrawPrimitiveUPR29Hook",
    "R30DrawIndexedPrimitiveUPR29Hook",
    "R31BuildFastWorldConstants",
    "R31DiscardUnreliableDrawCaches",
    "R31LiveShaderMatches",
    "R31ObserveDraw",
    "R31Frame",
    "R31FastWorldDraws",
    "R31HudDraws",
    "R31FlushPendingStateBlockResync",
    "R32EffectIsFragileLive",
    "R32GetSavedViewport",
    "R32SetWvpBatch",
    "R32RestoreRightPassState",
    "R32LowerFailClosed",
    "R32InstallState",
    "R9MainDepthIdentity",
    "R9MainDepthKnown",
    "R9MainDepthDesc",
    "R9MainDepthGeneration",
    "R9MainDepthContentSerial",
    "R9DrawCalls",
    "R9MonoBackupGap",
    "R9Poison",
):
    if legacy in r33:
        errors.append(f"R33 regained lower-layer implementation dependency: {legacy}")

for legacy in (
    "R22ReplayScope",
    "R30TryXyzrhwPrimitiveVB",
    "R30TryXyzrhwIndexedPrimitiveVB",
    "R30TryXyzrhwPrimitiveUP",
    "R30TryXyzrhwIndexedPrimitiveUP",
):
    if legacy in r34:
        errors.append(f"R34 regained lower-layer implementation dependency: {legacy}")

reset_begin = r34.find("HRESULT __stdcall ResetDestR34")
rollback_begin = r34.find("void R34RollbackHooks")
if reset_begin >= 0 and rollback_begin > reset_begin:
    callback_region = r34[reset_begin:rollback_begin]
    for legacy in ("R34ResetR33Hook.stdcall", "R34PresentR33Hook.stdcall"):
        if legacy in callback_region:
            errors.append(f"R34 callback bypassed lifecycle facade: {legacy}")

if errors:
    print("R84 refactor contract FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("R84 refactor contract OK")
