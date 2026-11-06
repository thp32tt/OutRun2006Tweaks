// Windows CI: compile the exact runtime HLSL with the Windows D3DCompiler.
#include "src/vr/game/dino_external_pbr_shader.hpp"
#include <cstdio>
#include <cstring>
using namespace OutRunVR::DinoSidecar;
int main(){
    HMODULE compiler=LoadLibraryW(L"d3dcompiler_47.dll");
    if(!compiler){std::fputs("D3DCompiler_47 unavailable\n",stderr);return 2;}
    using Compile=HRESULT (WINAPI *)(LPCVOID,SIZE_T,LPCSTR,
        const D3D_SHADER_MACRO*,ID3DInclude*,LPCSTR,LPCSTR,
        UINT,UINT,ID3DBlob**,ID3DBlob**);
    const auto fn=reinterpret_cast<Compile>(GetProcAddress(compiler,"D3DCompile"));
    if(!fn){FreeLibrary(compiler);return 3;}
    const char* sources[]{PbrShaders::VertexHlsl(),PbrShaders::PixelHlsl()};
    const char* entries[]{"mainVS","mainPS"};
    const char* targets[]{"vs_3_0","ps_3_0"};
    bool ok=true;
    for(unsigned i=0;i<2;++i) {
        ID3DBlob *code=nullptr,*errors=nullptr;
        HRESULT hr=fn(sources[i],std::strlen(sources[i]),"DinoRuntimePBR",
                      nullptr,nullptr,entries[i],targets[i],
                      D3DCOMPILE_PACK_MATRIX_ROW_MAJOR|D3DCOMPILE_OPTIMIZATION_LEVEL3,
                      0,&code,&errors);
        if(FAILED(hr) || !code) {
            std::fprintf(stderr,"%s compile failed HRESULT=%08lx: %.*s\n",
                    targets[i],static_cast<unsigned long>(hr),
                    errors?static_cast<int>(errors->GetBufferSize()):0,
                    errors?static_cast<const char*>(errors->GetBufferPointer()):"");
            ok=false;
        }
        if(code)code->Release();
        if(errors)errors->Release();
    }
    FreeLibrary(compiler);
    if(ok)std::puts("DINO_OVC3_REAL_D3DCOMPILE_VS3_PS3_PASS");
    return ok?0:4;
}
