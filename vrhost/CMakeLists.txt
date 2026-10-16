cmake_minimum_required(VERSION 3.20)
project(outrun-vr-host LANGUAGES C CXX)

if(NOT WIN32)
    message(FATAL_ERROR "outrun-vr-host currently supports Windows only")
endif()

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "outrun-vr-host must be configured as x64 (-A x64)")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
set(BUILD_LOADER ON CACHE BOOL "" FORCE)
set(BUILD_API_LAYERS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_CONFORMANCE_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_SDK_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_ALL_EXTENSIONS OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
    openxr_sdk
    GIT_REPOSITORY https://github.com/KhronosGroup/OpenXR-SDK.git
    GIT_TAG release-1.1.63
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(openxr_sdk)

execute_process(
    COMMAND git rev-parse --short=12 HEAD
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/.."
    OUTPUT_VARIABLE OUTRUN_VR_GIT_SHA
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT OUTRUN_VR_GIT_SHA)
    set(OUTRUN_VR_GIT_SHA "unknown")
endif()

add_executable(outrun-vr-host
    src/main_r23.cpp
    src/ipc/v3_shadow_bridge.cpp
    src/diagnostics/runtime_watchdog.cpp
)
target_include_directories(outrun-vr-host PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-host PRIVATE
    WIN32_LEAN_AND_MEAN NOMINMAX
    OUTRUN_VR_BUILD_SHA="${OUTRUN_VR_GIT_SHA}"
)
if(MSVC)
    # R23 remains the verified source/pose owner. R24 remains the visible
    # fallback authority. R32 adds an A/B SafeEye fallback and a final verified
    # DirectGPU single-projection path with asynchronous producer ACK; every
    # uncertain case still falls through to R26/R24.
    target_compile_options(outrun-vr-host PRIVATE
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/openxr_api_compat.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/bounded_swapchain_wait.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/sbs_capture_override.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/d3d9ex_direct_passthrough.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/d3d9ex_direct_passthrough_r32.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/review_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r21_runtime_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r22_runtime_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r23_runtime_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r24_black_screen_guard.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r26_recenter_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r32_direct_submit.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/capture_wait_guard.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r21_crash_diagnostics.hpp"
        "$<$<CONFIG:Release>:/Zi>"
    )
    target_link_options(outrun-vr-host PRIVATE
        "$<$<CONFIG:Release>:/DEBUG:FULL>"
        "$<$<CONFIG:RelWithDebInfo>:/DEBUG:FULL>"
    )
endif()
target_link_libraries(outrun-vr-host PRIVATE openxr_loader d3d11 dxgi d3dcompiler user32 dbghelp)

add_executable(outrun-vr-diagnostic
    src/diagnostic_pattern.cpp
)
target_compile_definitions(outrun-vr-diagnostic PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(outrun-vr-diagnostic PRIVATE openxr_loader d3d11 dxgi user32)

add_executable(outrun-vr-shader-smoke tests/stereo_shader_smoke.cpp)
target_include_directories(outrun-vr-shader-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
target_compile_definitions(outrun-vr-shader-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(outrun-vr-shader-smoke PRIVATE d3dcompiler)

add_executable(outrun-vr-protocol-v3-smoke tests/protocol_v3_smoke.cpp)
target_include_directories(outrun-vr-protocol-v3-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-protocol-v3-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-core-math-smoke tests/core_math_smoke.cpp)
target_include_directories(outrun-vr-core-math-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-core-math-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-host-state-v3-channel-smoke tests/host_state_v3_channel_smoke.cpp)
target_include_directories(outrun-vr-host-state-v3-channel-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-host-state-v3-channel-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-v2-v3-shadow-conversion-smoke tests/v2_v3_shadow_conversion_smoke.cpp)
target_include_directories(outrun-vr-v2-v3-shadow-conversion-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-v2-v3-shadow-conversion-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-host-pose-v3-validation-smoke tests/host_pose_v3_validation_smoke.cpp)
target_include_directories(outrun-vr-host-pose-v3-validation-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-host-pose-v3-validation-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

# R23 behavior regressions. These are intentionally small enough to run in CI
# without a headset/game process and cover the fail-closed state machine plus
# host-owned verified-bundle identity/TTL semantics.
add_executable(outrun-vr-runtime-eligibility-smoke tests/runtime_eligibility_smoke.cpp)
target_include_directories(outrun-vr-runtime-eligibility-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
)
target_compile_definitions(outrun-vr-runtime-eligibility-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-r23-verified-bundle-smoke tests/r23_verified_bundle_smoke.cpp)
target_include_directories(outrun-vr-r23-verified-bundle-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-r23-verified-bundle-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(outrun-vr-r23-verified-bundle-smoke PRIVATE
    openxr_loader d3d11 dxgi d3dcompiler user32)

# R32 review regressions are pure policy tests: no headset, game or graphics
# device is needed to validate reset-relative safety and fail-closed decisions.
add_executable(outrun-vr-direct-hold-reuse-smoke tests/direct_hold_frame_reuse_smoke.cpp)
add_executable(outrun-vr-direct-ack-device-epoch-smoke tests/direct_ack_device_epoch_smoke.cpp)
target_include_directories(outrun-vr-direct-ack-device-epoch-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
add_executable(outrun-vr-direct-ring-latest-smoke tests/direct_ring_latest_smoke.cpp)
target_include_directories(outrun-vr-direct-ring-latest-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
# Exact R41 skipped-frame ACK time/run isolation (no HMD or driver required).
add_executable(outrun-vr-direct-ring-skip-ack-smoke tests/test_direct_ring_skip_ack.cpp)
add_executable(outrun-vr-projection-blit-upload-smoke tests/projection_blit_upload_smoke.cpp)
add_executable(outrun-vr-menu-projection-copy-smoke tests/menu_projection_slice_copy_smoke.cpp)
target_include_directories(outrun-vr-menu-projection-copy-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
add_executable(outrun-vr-menu-content-aspect-smoke tests/menu_content_aspect_smoke.cpp)
# Build the real game CalcBall3D2D correction without a Windows game or HMD.
add_executable(outrun-vr-stage-edge-cull-smoke tests/stage_edge_cull_smoke.cpp)
target_include_directories(outrun-vr-stage-edge-cull-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
)
# Host gate must compile this actual game-culling regression, not only declare it.
add_dependencies(outrun-vr-host outrun-vr-stage-edge-cull-smoke)
# The mandatory x64 host compilation also EXECUTES the game-side pure
# C++ viewport-mutation checks. This test does not require a headset.
add_custom_command(TARGET outrun-vr-stage-edge-cull-smoke POST_BUILD
    COMMAND "$<TARGET_FILE:outrun-vr-stage-edge-cull-smoke>"
    COMMENT "Run native stage edge-cull viewport and fallback regression"
    VERBATIM)
# The mandatory x64 host CI compiles and executes real C993 game-eye math.
add_executable(outrun-vr-lens-eye-pose-smoke tests/lens_centre_eye_pose_smoke.cpp)
target_include_directories(outrun-vr-lens-eye-pose-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src")
add_dependencies(outrun-vr-host outrun-vr-lens-eye-pose-smoke)
add_custom_command(TARGET outrun-vr-lens-eye-pose-smoke POST_BUILD
    COMMAND "$<TARGET_FILE:outrun-vr-lens-eye-pose-smoke>"
    COMMENT "Run native C993 canted-eye and fail-closed regression"
    VERBATIM)
# Real game-side cockpit basis is compiled and executed by the mandatory host gate.
add_executable(outrun-vr-driver-seat-camera-smoke tests/driver_seat_camera_smoke.cpp)
target_include_directories(outrun-vr-driver-seat-camera-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../src")
add_dependencies(outrun-vr-host outrun-vr-driver-seat-camera-smoke)
add_custom_command(TARGET outrun-vr-driver-seat-camera-smoke POST_BUILD
    COMMAND "$<TARGET_FILE:outrun-vr-driver-seat-camera-smoke>"
    COMMENT "Run Quest-derived cockpit camera and render eligibility regression"
    VERBATIM)

add_executable(outrun-vr-pause-eye-affine-smoke tests/pause_menu_eye_affine_smoke.cpp)
add_executable(outrun-vr-stage-extension-owner-smoke tests/stage_extension_direct_owner_smoke.cpp)
add_executable(outrun-vr-rank-marker-fraction-smoke tests/rank_marker_fraction_smoke.cpp)
add_executable(outrun-vr-r30-early-rhw-shadow-smoke tests/r30_early_rhw_shadow_smoke.cpp)
add_executable(outrun-vr-r30-indexed-up-bounds-smoke tests/r30_indexed_up_bounds_smoke.cpp)
add_executable(outrun-vr-r30-shadow-ranges-smoke tests/r30_shadow_ranges_smoke.cpp)
add_executable(outrun-vr-car-base-shadow-stereo-smoke tests/car_base_shadow_stereo_smoke.cpp)
target_include_directories(outrun-vr-car-base-shadow-stereo-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../src")
target_include_directories(outrun-vr-r30-early-rhw-shadow-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../src")
target_include_directories(outrun-vr-rank-marker-fraction-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../src")
add_executable(outrun-vr-goal-progress-owner-smoke tests/goal_progress_owner_smoke.cpp)
add_executable(outrun-vr-semantic-tag-hint-smoke tests/semantic_tag_hint_smoke.cpp)
add_executable(outrun-vr-hud-original-wvp-smoke tests/hud_original_wvp_smoke.cpp)
# This smoke test compiles the real shared Win32 UI spacing policy from
# ../src/vr/ui, unlike host-only menu aspect math under vrhost/src.
target_include_directories(outrun-vr-menu-content-aspect-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
add_executable(outrun-vr-capture-descriptor-smoke tests/desktop_capture_descriptor_cache_smoke.cpp)
target_include_directories(outrun-vr-capture-descriptor-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
target_include_directories(outrun-vr-direct-hold-reuse-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")
target_include_directories(outrun-vr-projection-blit-upload-smoke PRIVATE "${CMAKE_CURRENT_LIST_DIR}/src")

add_executable(outrun-vr-r32-policy-smoke tests/r32_policy_smoke.cpp)
target_include_directories(outrun-vr-r32-policy-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
)
target_compile_definitions(outrun-vr-r32-policy-smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(outrun-vr-frame-pacing-smoke tests/frame_pacing_diagnostics_smoke.cpp)
target_include_directories(outrun-vr-frame-pacing-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
)

add_executable(outrun-vr-cadence-presented-wait-smoke tests/cadence_presented_wait_smoke.cpp)

add_executable(outrun-vr-cadence-schedule-smoke tests/cadence_schedule_smoke.cpp)

add_executable(outrun-vr-eye-extent-smoke tests/xr_eye_extent_smoke.cpp)
target_include_directories(outrun-vr-eye-extent-smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)

foreach(target
    outrun-vr-host
    outrun-vr-diagnostic
    outrun-vr-shader-smoke
    outrun-vr-protocol-v3-smoke
    outrun-vr-core-math-smoke
    outrun-vr-host-state-v3-channel-smoke
    outrun-vr-v2-v3-shadow-conversion-smoke
    outrun-vr-host-pose-v3-validation-smoke
    outrun-vr-runtime-eligibility-smoke
    outrun-vr-r23-verified-bundle-smoke
    outrun-vr-direct-hold-reuse-smoke
    outrun-vr-direct-ack-device-epoch-smoke
    outrun-vr-direct-ring-latest-smoke
    outrun-vr-direct-ring-skip-ack-smoke
    outrun-vr-projection-blit-upload-smoke
    outrun-vr-menu-projection-copy-smoke
    outrun-vr-menu-content-aspect-smoke
    outrun-vr-stage-edge-cull-smoke
    outrun-vr-driver-seat-camera-smoke
    outrun-vr-pause-eye-affine-smoke
    outrun-vr-stage-extension-owner-smoke
    outrun-vr-rank-marker-fraction-smoke
    outrun-vr-r30-early-rhw-shadow-smoke
    outrun-vr-r30-indexed-up-bounds-smoke
    outrun-vr-r30-shadow-ranges-smoke
    outrun-vr-goal-progress-owner-smoke
    outrun-vr-semantic-tag-hint-smoke
    outrun-vr-hud-original-wvp-smoke
    outrun-vr-capture-descriptor-smoke
    outrun-vr-r32-policy-smoke
    outrun-vr-frame-pacing-smoke
    outrun-vr-cadence-presented-wait-smoke
    outrun-vr-cadence-schedule-smoke
    outrun-vr-eye-extent-smoke)
    set_target_properties(${target} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}/bin"
        PDB_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
        PDB_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}/bin"
    )
endforeach()