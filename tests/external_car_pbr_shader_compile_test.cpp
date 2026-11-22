// Compile the actual runtime HLSL strings, not a hand-written copy.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "../src/vr/game/dino_external_pbr_shader.hpp"
#include <d3dcompiler.h>
#include <cstdio>
#include <cstring>

int main() {
    using OutRunVR::DinoSidecar::PbrShaders;
    struct Shader {
        const char* name;
        const char* source;
        const char* entry;
        const char* target;
    };
    const Shader shaders[]{
        {"PBR_VERTEX",PbrShaders::VertexHlsl(),"mainVS","vs_3_0"},
        {"PBR_PIXEL",PbrShaders::PixelHlsl(),"mainPS","ps_3_0"}
    };
    for(const auto& shader:shaders) {
        ID3DBlob* bytes=nullptr;
        ID3DBlob* errors=nullptr;
        const HRESULT result=D3DCompile(shader.source,
            std::strlen(shader.source),shader.name,nullptr,nullptr,
            shader.entry,shader.target,
            D3DCOMPILE_PACK_MATRIX_ROW_MAJOR|D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,&bytes,&errors);
        if(FAILED(result) || !bytes) {
            std::fprintf(stderr,"%s D3DCompile failed 0x%08X\n",
                shader.name,static_cast<unsigned>(result));
            if(errors)
                std::fprintf(stderr,"%.*s\n",
                    static_cast<int>(errors->GetBufferSize()),
                    static_cast<const char*>(errors->GetBufferPointer()));
            if(errors)errors->Release();
            if(bytes)bytes->Release();
            return 1;
        }
        std::printf("%s compiled %zu bytes\n",
            shader.name,static_cast<size_t>(bytes->GetBufferSize()));
        if(errors)errors->Release();
        bytes->Release();
    }
    return 0;
}
