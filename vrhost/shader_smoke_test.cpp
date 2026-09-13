#include "shader_compile_patch.hpp"

#define D3DCompile OutRunVrD3DCompile
#define main OutRunVrHostMain_NotExecutedByShaderTest
#include "main_compat_v2.cpp"
#undef main
#undef D3DCompile

#include <iostream>

int main()
{
    try
    {
        ID3DBlob* vs = CompileShader(MirrorShader, "VSMain", "vs_5_0");
        ID3DBlob* ps = CompileShader(MirrorShader, "PSMain", "ps_5_0");
        ReleaseCom(vs);
        ReleaseCom(ps);
        std::cout << "OutRun VR mirror HLSL smoke test passed (vs_5_0 + ps_5_0).\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << "OutRun VR mirror HLSL smoke test FAILED: " << e.what() << "\n";
        return 1;
    }
}
