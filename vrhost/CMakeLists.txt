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

# v2 keeps the OpenXR 1.0 compatibility wrapper but adds a real GPU color
# conversion path for SDR BGRA8 and HDR FP16/scRGB desktop frames, plus pose
# telemetry and automatic session exit when OutRun closes.
add_executable(outrun-vr-host main_compat_v2.cpp)
target_include_directories(outrun-vr-host PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../src")
target_compile_definitions(outrun-vr-host PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(outrun-vr-host PRIVATE openxr_loader d3d11 dxgi d3dcompiler)

set_target_properties(outrun-vr-host PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}/bin"
)
