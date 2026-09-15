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

add_executable(outrun-vr-host
    src/main.cpp
    src/ipc/v3_shadow_bridge.cpp
    src/diagnostics/runtime_watchdog.cpp
)
target_include_directories(outrun-vr-host PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../src"
    "${CMAKE_CURRENT_LIST_DIR}/src"
)
target_compile_definitions(outrun-vr-host PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
if(MSVC)
    # Forced-include order is the runtime ownership stack. R22 is the final
    # xrEndFrame owner: R21 retains readonly/direct/shouldRender policy and R22
    # adds latest-Frame.v2 pose/FOV bundle validation while blocking QPC-only
    # gameplay fallback synthesis. R22 capture diagnostics replace only the
    # production ReleaseFrame instrumentation with a non-blocking game-UV
    # staging/query sampler. Crash diagnostics remain last and do not alter
    # OpenXR dispatch.
    target_compile_options(outrun-vr-host PRIVATE
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/openxr_api_compat.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/sbs_capture_override.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r22_capture_diagnostics.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/d3d9ex_direct_passthrough.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/review_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r21_runtime_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r22_runtime_hardening.hpp"
        "/FI${CMAKE_CURRENT_LIST_DIR}/src/runtime/r21_crash_diagnostics.hpp"
        "$<$<CONFIG:Release>:/Zi>"
    )
    target_link_options(outrun-vr-host PRIVATE
        "$<$<CONFIG:Release>:/DEBUG:FULL>"
        "$<$<CONFIG:RelWithDebInfo>:/DEBUG:FULL>"
    )
endif()
target_link_libraries(outrun-vr-host PRIVATE openxr_loader d3d11 dxgi d3dcompiler user32 dbghelp)

# Renderer-independent hardware diagnostic. This intentionally does not use the
# host forced-include runtime wrappers and does not depend on the game process.
# It submits deterministic color patterns directly through OpenXR/D3D11 so
# VDXR swapchain/layer behavior can be isolated from D3D9 capture/stereo logic.
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

foreach(target
    outrun-vr-host
    outrun-vr-diagnostic
    outrun-vr-shader-smoke
    outrun-vr-protocol-v3-smoke
    outrun-vr-core-math-smoke
    outrun-vr-host-state-v3-channel-smoke
    outrun-vr-v2-v3-shadow-conversion-smoke
    outrun-vr-host-pose-v3-validation-smoke)
    set_target_properties(${target} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}/bin"
        PDB_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
        PDB_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}/bin"
    )
endforeach()
