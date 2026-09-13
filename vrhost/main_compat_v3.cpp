#include "shader_compile_patch.hpp"

// main_compat_v2.cpp owns the host implementation. Route its runtime shader
// compilation through a small compatibility shim that fixes the accidental
// use of HLSL's reserved identifier "linear" before D3DCompile sees it.
#define D3DCompile OutRunVrD3DCompile
#include "main_compat_v2.cpp"
#undef D3DCompile
