#include <cstdlib>
#include <cstring>
#include <iostream>

#include <d3dcompiler.h>
#include <d3d11.h>
#include <d3d11shader.h>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R95 constant-buffer probe failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    struct DevicePair
    {
        ID3D11Device* device = nullptr;
        ID3D11DeviceContext* context = nullptr;
    };

    DevicePair create_warp_device()
    {
        const D3D_FEATURE_LEVEL requestedLevels[] = {
            D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1,
            D3D_FEATURE_LEVEL_10_0,
        };

        DevicePair out{};
        D3D_FEATURE_LEVEL createdLevel = D3D_FEATURE_LEVEL_9_1;
        const HRESULT hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            0,
            requestedLevels,
            3,
            D3D11_SDK_VERSION,
            &out.device,
            &createdLevel,
            &out.context);

        require(
            SUCCEEDED(hr) && out.device != nullptr && out.context != nullptr,
            "D3D11 WARP device/context creation");
        require(
            createdLevel >= D3D_FEATURE_LEVEL_10_0,
            "D3D11 WARP feature level");
        return out;
    }

    ID3DBlob* compile_vertex_shader(const std::string& source)
    {
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT hr = D3DCompile(
            source.data(),
            source.size(),
            "OutRunR95FixedFunctionVertexShader",
            nullptr,
            nullptr,
            "main",
            "vs_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
            diagnostics->Release();

        require(
            SUCCEEDED(hr) && bytecode != nullptr,
            "D3DCompile R93 vertex prototype");
        return bytecode;
    }
}

int main()
{
    D3DMATRIX identity{};
    identity._11 = 1.0f;
    identity._22 = 1.0f;
    identity._33 = 1.0f;
    identity._44 = 1.0f;

    D3DMATRIX world = identity;
    world._41 = 2.0f;
    D3DMATRIX view = identity;
    view._11 = 3.0f;

    const auto transform =
        generate_fixed_function_transform_constants(
            world, view, identity, true);
    require(transform.exact(), "R94 transform prerequisite");

    constexpr UINT expectedConstantBytes = 16u * sizeof(float);
    static_assert(expectedConstantBytes == 64u);
    require(
        sizeof(transform.worldViewProjection) == expectedConstantBytes,
        "R94 WVP payload must remain 64 bytes");

    const auto vertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            D3DFVF_XYZ | D3DFVF_DIFFUSE | D3DFVF_TEX1,
            24);
    require(
        vertexPrototype.generated(),
        "R93 vertex prototype prerequisite");

    ID3DBlob* vertexBytecode =
        compile_vertex_shader(vertexPrototype.source);

    ID3D11ShaderReflection* reflection = nullptr;
    require(
        SUCCEEDED(D3DReflect(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            IID_ID3D11ShaderReflection,
            reinterpret_cast<void**>(&reflection))) &&
        reflection != nullptr,
        "D3DReflect R93 vertex shader");

    D3D11_SHADER_INPUT_BIND_DESC binding{};
    require(
        SUCCEEDED(reflection->GetResourceBindingDescByName(
            "FixedFunctionTransform",
            &binding)),
        "reflect FixedFunctionTransform binding");
    require(
        binding.Type == D3D_SIT_CBUFFER &&
        binding.BindPoint == 0 &&
        binding.BindCount == 1,
        "FixedFunctionTransform must bind at b0");

    ID3D11ShaderReflectionConstantBuffer* reflectedBuffer =
        reflection->GetConstantBufferByName("FixedFunctionTransform");
    require(
        reflectedBuffer != nullptr,
        "reflect FixedFunctionTransform constant buffer");

    D3D11_SHADER_BUFFER_DESC reflectedBufferDesc{};
    require(
        SUCCEEDED(reflectedBuffer->GetDesc(&reflectedBufferDesc)),
        "reflect FixedFunctionTransform descriptor");
    require(
        reflectedBufferDesc.Size == expectedConstantBytes,
        "FixedFunctionTransform must remain 64 bytes");

    DevicePair d3d = create_warp_device();

    ID3D11VertexShader* vertexShader = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateVertexShader(
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            nullptr,
            &vertexShader)) &&
        vertexShader != nullptr,
        "CreateVertexShader R93");
    d3d.context->VSSetShader(vertexShader, nullptr, 0);

    D3D11_BUFFER_DESC bufferDesc{};
    bufferDesc.ByteWidth = expectedConstantBytes;
    bufferDesc.Usage = D3D11_USAGE_DYNAMIC;
    bufferDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    bufferDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

    ID3D11Buffer* constantBuffer = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateBuffer(
            &bufferDesc, nullptr, &constantBuffer)) &&
        constantBuffer != nullptr,
        "CreateBuffer D3D11_BIND_CONSTANT_BUFFER");

    D3D11_BUFFER_DESC observedDesc{};
    constantBuffer->GetDesc(&observedDesc);
    require(
        observedDesc.ByteWidth == expectedConstantBytes &&
        observedDesc.Usage == D3D11_USAGE_DYNAMIC &&
        observedDesc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
        observedDesc.CPUAccessFlags == D3D11_CPU_ACCESS_WRITE,
        "constant-buffer descriptor contract");

    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(
        SUCCEEDED(d3d.context->Map(
            constantBuffer,
            0,
            D3D11_MAP_WRITE_DISCARD,
            0,
            &mapped)) &&
        mapped.pData != nullptr,
        "Map D3D11_MAP_WRITE_DISCARD");

    std::memcpy(
        mapped.pData,
        transform.worldViewProjection.data(),
        expectedConstantBytes);
    require(
        std::memcmp(
            mapped.pData,
            transform.worldViewProjection.data(),
            expectedConstantBytes) == 0,
        "uploaded R94 WVP payload mismatch");
    d3d.context->Unmap(constantBuffer, 0);

    d3d.context->VSSetConstantBuffers(0, 1, &constantBuffer);
    ID3D11Buffer* boundBuffer = nullptr;
    d3d.context->VSGetConstantBuffers(0, 1, &boundBuffer);
    require(
        boundBuffer != nullptr && boundBuffer == constantBuffer,
        "VS b0 constant-buffer binding");

    if (boundBuffer)
        boundBuffer->Release();

    ID3D11Buffer* nullBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullBuffer);
    d3d.context->VSSetShader(nullptr, nullptr, 0);

    constantBuffer->Release();
    vertexShader->Release();
    d3d.context->Release();
    d3d.device->Release();
    reflection->Release();
    vertexBytecode->Release();

    std::cout << "DX11 constant buffer probe R95: PASS\n";
    return 0;
}
