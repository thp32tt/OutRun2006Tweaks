cmake_minimum_required(VERSION 3.24)
project(outrun_vr_x86_openxr_probe LANGUAGES CXX)

include(FetchContent)
set(BUILD_API_LAYERS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_CONFORMANCE_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_LOADER ON CACHE BOOL "" FORCE)
FetchContent_Declare(
  openxr_sdk
  GIT_REPOSITORY https://github.com/KhronosGroup/OpenXR-SDK.git
  GIT_TAG release-1.1.60
)
FetchContent_MakeAvailable(openxr_sdk)

add_executable(outrun-vr-x86-openxr-probe src/main.cpp)
target_compile_features(outrun-vr-x86-openxr-probe PRIVATE cxx_std_20)
target_compile_definitions(outrun-vr-x86-openxr-probe PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(outrun-vr-x86-openxr-probe PRIVATE openxr_loader)
set_target_properties(outrun-vr-x86-openxr-probe PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)
