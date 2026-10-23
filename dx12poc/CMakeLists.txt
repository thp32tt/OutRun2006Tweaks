cmake_minimum_required(VERSION 3.21)

project(outrun_d3d9on12_probe LANGUAGES CXX)

add_executable(outrun-d3d9on12-probe
    src/main.cpp
)

target_compile_features(outrun-d3d9on12-probe PRIVATE cxx_std_17)

target_compile_definitions(outrun-d3d9on12-probe PRIVATE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
    _WIN32_WINNT=0x0A00
)

target_include_directories(outrun-d3d9on12-probe PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(outrun-d3d9on12-probe PRIVATE
    d3d12
    dxgi
    dxguid
    user32
)

if(MSVC)
    target_compile_options(outrun-d3d9on12-probe PRIVATE
        /W4
        /permissive-
        /EHsc
        /utf-8
    )
endif()
