#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>

#include <d3dcompiler.h>
#include <d3d11.h>
#include <d3d11shader.h>

#include "vr/d3d11/native_backend.hpp"
#include "vr/d3d11/pipeline_translation.hpp"
#include "vr/d3d11/resource_translation.hpp"
#include "vr/d3d11/surface_mirror.hpp"
#include "vr/d3d11/triangle_fan_index_buffer.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::NativeFixedFunctionPipelineBundle;
    using outrun::vr::dx11::NativeFixedFunctionRenderStateBundle;
    using outrun::vr::dx11::NativeFixedFunctionOutputStateBinding;
    using outrun::vr::dx11::NativeFixedFunctionSamplerState;
    using outrun::vr::dx11::NativeFixedFunctionTextureView;
    using outrun::vr::dx11::NativeFixedFunctionTransformBuffer;
    using outrun::vr::dx11::NativeManagedBufferShadow;
    using outrun::vr::dx11::NativeManagedTextureRegistry;
    using outrun::vr::dx11::NativeManagedTextureShadow;
    using outrun::vr::dx11::NativeManagedTextureStageReadiness;
    using outrun::vr::dx11::NativeProgrammableShaderPairCache;
    using outrun::vr::dx11::ProgrammableShaderFunctionIdentity;
    using outrun::vr::dx11::ProgrammableShaderRegisterOperandRole;
    using outrun::vr::dx11::ProgrammableShaderConstantRegisterClass;
    using outrun::vr::dx11::capture_programmable_shader_function_source_evidence;
    using outrun::vr::dx11::decode_programmable_shader_instruction_stream;
    using outrun::vr::dx11::decode_programmable_shader_register_semantics;
    using outrun::vr::dx11::decode_programmable_shader_interface_semantics;
    using outrun::vr::dx11::derive_programmable_shader_interface_linkage_evidence;
    using outrun::vr::dx11::derive_programmable_shader_pair_source_semantic_evidence;
    using outrun::vr::dx11::derive_programmable_shader_register_mapping_plan;
    using outrun::vr::dx11::NativeSurfacePairReadiness;
    using outrun::vr::dx11::NativeTriangleFanIndexBuffer;
    using outrun::vr::dx11::NativeTriangleFanIndexBufferReadiness;
    using outrun::vr::dx11::PipelineUnsupportedBlend;
    using outrun::vr::dx11::compose_fixed_function_activation_readiness;
    using outrun::vr::dx11::compose_fixed_function_nonindexed_triangle_fan_geometry_readiness;
    using outrun::vr::dx11::validate_fixed_function_activation_snapshot;
    using outrun::vr::dx11::validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot;
    using outrun::vr::dx11::ResourceRole;
    using outrun::vr::dx11::BufferMutationUpdateKind;
    using outrun::vr::dx11::TextureMutationUpdateKind;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_transform_constants;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::seal_programmable_shader_pair_cache_identity;
    using outrun::vr::dx11::translate_fixed_function_sampler;
    using outrun::vr::dx11::translate_pipeline;
    using outrun::vr::dx11::translate_resource_format;
    using outrun::vr::dx11::translate_texture_mutation;
    using outrun::vr::dx11::translate_vertex_input_layout;
    using outrun::vr::dx11::bind_fixed_function_texture_stage_for_observation;

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

    FixedFunctionStageState active_stage()
    {
        FixedFunctionStageState stage{};
        stage.colorOp = D3DTOP_MODULATE;
        stage.colorArg1 = D3DTA_TEXTURE;
        stage.colorArg2 = D3DTA_DIFFUSE;
        stage.alphaOp = D3DTOP_SELECTARG1;
        stage.alphaArg1 = D3DTA_TEXTURE;
        stage.alphaArg2 = D3DTA_CURRENT;
        stage.texCoordIndex = 0;
        stage.textureTransformFlags = D3DTTFF_DISABLE;
        stage.minFilter = D3DTEXF_POINT;
        stage.magFilter = D3DTEXF_POINT;
        stage.mipFilter = D3DTEXF_NONE;
        stage.addressU = D3DTADDRESS_WRAP;
        stage.addressV = D3DTADDRESS_WRAP;
        return stage;
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

    ID3DBlob* compile_geometry_shader()
    {
        static const char source[] = R"(
struct GSIn { float4 position : SV_Position; };
struct GSOut { float4 position : SV_Position; };
[maxvertexcount(1)]
void main(point GSIn input[1], inout PointStream<GSOut> outputStream)
{
    GSOut output;
    output.position = input[0].position;
    outputStream.Append(output);
}
)";
        ID3DBlob* bytecode = nullptr;
        ID3DBlob* diagnostics = nullptr;
        const HRESULT hr = D3DCompile(
            source,
            sizeof(source) - 1,
            "OutRunR147IsolationGeometryShader",
            nullptr,
            nullptr,
            "main",
            "gs_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0,
            &bytecode,
            &diagnostics);

        if (diagnostics)
            diagnostics->Release();

        require(
            SUCCEEDED(hr) && bytecode != nullptr,
            "D3DCompile R147 isolation geometry shader");
        return bytecode;
    }
    ID3D11Buffer* create_constant_buffer(
        ID3D11Device* device, UINT byteWidth)
    {
        require(
            device != nullptr && byteWidth != 0 &&
            (byteWidth & 15u) == 0,
            "R244 constant-buffer descriptor prerequisite");
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = byteWidth;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        ID3D11Buffer* buffer = nullptr;
        require(
            SUCCEEDED(device->CreateBuffer(&desc, nullptr, &buffer)) &&
            buffer != nullptr,
            "R244 D3D11 constant-buffer creation");
        return buffer;
    }


    // R169 WARP-only positive fragment control. The production translated VB
    // contains arbitrary shadow bytes, so its R157 IA statistics cannot prove
    // raster coverage. Use a separate device/known clip-space triangle to
    // prove that BGRA staging distinguishes a real PS write from clear-only.
    // This is NOT a native game Draw or an HMD/stereo acceptance test.
    void verify_r169_warp_fragment_coverage()
    {
        DevicePair warp = create_warp_device();
        D3D11_TEXTURE2D_DESC colorDesc{};
        colorDesc.Width = 16u;
        colorDesc.Height = 16u;
        colorDesc.MipLevels = 1u;
        colorDesc.ArraySize = 1u;
        colorDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        colorDesc.SampleDesc.Count = 1u;
        colorDesc.Usage = D3D11_USAGE_DEFAULT;
        colorDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
        ID3D11Texture2D* color = nullptr;
        require(SUCCEEDED(warp.device->CreateTexture2D(
                    &colorDesc, nullptr, &color)) && color != nullptr,
                "R169 WARP 16x16 BGRA color target");
        ID3D11RenderTargetView* target = nullptr;
        require(SUCCEEDED(warp.device->CreateRenderTargetView(
                    color, nullptr, &target)) && target != nullptr,
                "R169 WARP RTV");
        D3D11_TEXTURE2D_DESC readDesc = colorDesc;
        readDesc.Usage = D3D11_USAGE_STAGING;
        readDesc.BindFlags = 0u;
        readDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        ID3D11Texture2D* readback = nullptr;
        require(SUCCEEDED(warp.device->CreateTexture2D(
                    &readDesc, nullptr, &readback)) && readback != nullptr,
                "R169 read-only staging texture");

        static const std::string vsSource = R"(
struct V { float2 xy : POSITION; };
float4 main(V input) : SV_Position {
    return float4(input.xy, 0.5, 1.0);
}
)";
        static const char psSource[] = R"(
float4 main() : SV_Target {
    return float4(1.0, 0.0, 0.0, 1.0);
}
)";
        ID3DBlob* vertexCode = compile_vertex_shader(vsSource);
        ID3DBlob* pixelCode = nullptr;
        ID3DBlob* errors = nullptr;
        const HRESULT psResult = D3DCompile(
            psSource, sizeof(psSource) - 1u, "R169PixelCoverage",
            nullptr, nullptr, "main", "ps_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0u, &pixelCode, &errors);
        if (errors)
            errors->Release();
        require(SUCCEEDED(psResult) && pixelCode != nullptr,
                "R169 solid-red PS compile");
        ID3D11VertexShader* vs = nullptr;
        ID3D11PixelShader* ps = nullptr;
        require(SUCCEEDED(warp.device->CreateVertexShader(
                    vertexCode->GetBufferPointer(), vertexCode->GetBufferSize(),
                    nullptr, &vs)) && vs != nullptr,
                "R169 VS creation");
        require(SUCCEEDED(warp.device->CreatePixelShader(
                    pixelCode->GetBufferPointer(), pixelCode->GetBufferSize(),
                    nullptr, &ps)) && ps != nullptr,
                "R169 PS creation");
        D3D11_INPUT_ELEMENT_DESC element{};
        element.SemanticName = "POSITION";
        element.Format = DXGI_FORMAT_R32G32_FLOAT;
        element.InputSlotClass = D3D11_INPUT_PER_VERTEX_DATA;
        ID3D11InputLayout* layout = nullptr;
        require(SUCCEEDED(warp.device->CreateInputLayout(
                    &element, 1u, vertexCode->GetBufferPointer(),
                    vertexCode->GetBufferSize(), &layout)) && layout != nullptr,
                "R169 known XY vertex layout");
        struct Vertex { float x, y; };
        const Vertex vertices[3] = {
            {-0.75f, -0.75f}, {0.75f, -0.75f}, {0.0f, 0.75f}};
        const unsigned short indices[3] = {0u, 1u, 2u};
        D3D11_BUFFER_DESC vbDesc{};
        vbDesc.ByteWidth = sizeof(vertices);
        vbDesc.Usage = D3D11_USAGE_IMMUTABLE;
        vbDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA vbData{};
        vbData.pSysMem = vertices;
        ID3D11Buffer* vb = nullptr;
        require(SUCCEEDED(warp.device->CreateBuffer(
                    &vbDesc, &vbData, &vb)) && vb != nullptr,
                "R169 deterministic clip-space triangle VB");
        D3D11_BUFFER_DESC ibDesc{};
        ibDesc.ByteWidth = sizeof(indices);
        ibDesc.Usage = D3D11_USAGE_IMMUTABLE;
        ibDesc.BindFlags = D3D11_BIND_INDEX_BUFFER;
        D3D11_SUBRESOURCE_DATA ibData{};
        ibData.pSysMem = indices;
        ID3D11Buffer* ib = nullptr;
        require(SUCCEEDED(warp.device->CreateBuffer(
                    &ibDesc, &ibData, &ib)) && ib != nullptr,
                "R169 deterministic triangle index buffer");

        D3D11_RASTERIZER_DESC rasterDesc{};
        rasterDesc.FillMode = D3D11_FILL_SOLID;
        rasterDesc.CullMode = D3D11_CULL_NONE;
        rasterDesc.DepthClipEnable = TRUE;
        ID3D11RasterizerState* raster = nullptr;
        require(SUCCEEDED(warp.device->CreateRasterizerState(
                    &rasterDesc, &raster)) && raster != nullptr,
                "R169 explicit non-culled rasterizer");
        warp.context->RSSetState(raster);
        D3D11_VIEWPORT viewport{};
        viewport.Width = 16.0f;
        viewport.Height = 16.0f;
        viewport.MaxDepth = 1.0f;
        warp.context->RSSetViewports(1u, &viewport);
        warp.context->OMSetRenderTargets(1u, &target, nullptr);
        warp.context->IASetInputLayout(layout);
        const UINT stride = sizeof(Vertex);
        const UINT offset = 0u;
        warp.context->IASetVertexBuffers(0u, 1u, &vb, &stride, &offset);
        warp.context->IASetIndexBuffer(ib, DXGI_FORMAT_R16_UINT, 0u);
        warp.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        warp.context->VSSetShader(vs, nullptr, 0u);
        warp.context->PSSetShader(ps, nullptr, 0u);
        warp.context->GSSetShader(nullptr, nullptr, 0u);
        const FLOAT clear[4] = {0.0f, 0.0f, 0.0f, 1.0f};
        warp.context->ClearRenderTargetView(target, clear);

        const auto verify = [&](bool expectRed) {
            warp.context->CopyResource(readback, color);
            D3D11_MAPPED_SUBRESOURCE mapped{};
            require(SUCCEEDED(warp.context->Map(
                        readback, 0u, D3D11_MAP_READ, 0u, &mapped)) &&
                        mapped.pData != nullptr && mapped.RowPitch >= 64u,
                    "R169 WARP BGRA staging map");
            const auto matches = [&](UINT x, UINT y, bool red) {
                const auto* pixel = static_cast<const unsigned char*>(
                    mapped.pData) + static_cast<std::size_t>(y) *
                    mapped.RowPitch + 4u * x;
                const unsigned char expected[4] =
                    {0u, 0u, static_cast<unsigned char>(red ? 255u : 0u), 255u};
                return std::memcmp(pixel, expected, sizeof(expected)) == 0;
            };
            const bool pass = matches(8u, 8u, expectRed) &&
                matches(0u, 0u, false) &&
                matches(15u, 0u, false) &&
                matches(0u, 15u, false) &&
                matches(15u, 15u, false);
            warp.context->Unmap(readback, 0u);
            require(pass, expectRed
                ? "R169 indexed fragment writes red interior; borders stay clear"
                : "R169 negative control: clear-only center/borders stay black");
        };
        verify(false); // Counterfactual: clearing alone cannot satisfy coverage.
        warp.context->DrawIndexed(3u, 0u, 0);
        verify(true); // Deterministic interior PS coverage on WARP.

        // R170: unlike R169's synthetic position shader/solid PS, this uses
        // the real D3D9 FVF descriptor translator and both generated fixed-
        // function HLSL prototypes. A translated b0 WVP deliberately moves
        // the same known triangle out of clip space (negative control);
        // restoring the exact identity WVP must shade its center white.
        // No real game Draw/DrawIndexed dispatch is enabled by this probe.
        constexpr DWORD r170Fvf = D3DFVF_XYZ;
        constexpr UINT r170Stride = 3u * sizeof(float);
        const auto r170Layout = translate_vertex_input_layout(
            nullptr, 0u, r170Fvf, r170Stride);
        const auto r170VsPrototype =
            generate_fixed_function_vertex_shader_prototype(
                r170Fvf, r170Stride);
        std::array<FixedFunctionStageState, 8> r170Stages{};
        // The D3D9 fixed-function stage requires valid min/mag sampler
        // defaults even when SELECTARG1 does not sample a texture.
        // Default-constructed NONE min/mag fails translate readiness.
        // Limit R170's pixel provenance to opaque D3DTA_TFACTOR (the
        // generator's exact 0xFFFFFFFF default). Prior exact-SHA WARP gates
        // 37876360563 and 37877062280 revealed D3DTA_DIFFUSE COLOR0
        // mismatch ([B,G,R,A]=[128,0,16,255] instead of opaque white).
        // Never mistake this controlled factor path for diffuse fidelity:
        // native gameplay Draw stays off until the color-linkage bug is fixed.
        r170Stages[0] = active_stage();
        r170Stages[0].colorOp = D3DTOP_SELECTARG1;
        r170Stages[0].colorArg1 = D3DTA_TFACTOR;
        r170Stages[0].alphaOp = D3DTOP_SELECTARG1;
        r170Stages[0].alphaArg1 = D3DTA_TFACTOR;
        std::array<D3DRESOURCETYPE, 8> r170TextureTypes{};
        r170TextureTypes.fill(D3DRTYPE_TEXTURE);
        const auto r170PsPrototype =
            generate_fixed_function_pixel_shader_prototype(
                r170Stages, true, 0u, 0u, r170TextureTypes);
        require(r170Layout.exact && r170Layout.fvfPath &&
                    r170Layout.elementCount == 1u,
                "R170 real D3D9 XYZ FVF descriptor translation");
        require(r170VsPrototype.generated(),
                "R170 generated fixed-function VS source");
        require(r170PsPrototype.generated(),
                "R170 generated fixed-function opaque TFACTOR PS source");
        ID3DBlob* r170VsCode =
            compile_vertex_shader(r170VsPrototype.source);
        ID3DBlob* r170PsCode = nullptr;
        ID3DBlob* r170Diagnostics = nullptr;
        const HRESULT r170Compile = D3DCompile(
            r170PsPrototype.source.data(), r170PsPrototype.source.size(),
            "R170TranslatedFixedFunctionPixel", nullptr, nullptr, "main",
            "ps_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0u, &r170PsCode, &r170Diagnostics);
        if (r170Diagnostics)
            r170Diagnostics->Release();
        require(SUCCEEDED(r170Compile) && r170PsCode != nullptr,
                "R170 generated fixed-function PS compiles");
        ID3D11VertexShader* r170Vs = nullptr;
        ID3D11PixelShader* r170Ps = nullptr;
        ID3D11InputLayout* r170Ia = nullptr;
        require(SUCCEEDED(warp.device->CreateVertexShader(
                    r170VsCode->GetBufferPointer(),
                    r170VsCode->GetBufferSize(), nullptr, &r170Vs)) &&
                    r170Vs != nullptr &&
                SUCCEEDED(warp.device->CreatePixelShader(
                    r170PsCode->GetBufferPointer(),
                    r170PsCode->GetBufferSize(), nullptr, &r170Ps)) &&
                    r170Ps != nullptr &&
                SUCCEEDED(warp.device->CreateInputLayout(
                    r170Layout.elements.data(), r170Layout.elementCount,
                    r170VsCode->GetBufferPointer(),
                    r170VsCode->GetBufferSize(), &r170Ia)) &&
                    r170Ia != nullptr,
                "R170 translated fixed-function IA/VS/PS objects");
        struct R170Vertex { float x, y, z; };
        const R170Vertex r170Vertices[3] = {
            {-0.75f, -0.75f, 0.5f},
            { 0.75f, -0.75f, 0.5f},
            { 0.00f,  0.75f, 0.5f}};
        D3D11_BUFFER_DESC r170VbDesc{};
        r170VbDesc.ByteWidth = sizeof(r170Vertices);
        r170VbDesc.Usage = D3D11_USAGE_IMMUTABLE;
        r170VbDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA r170VbData{};
        r170VbData.pSysMem = r170Vertices;
        ID3D11Buffer* r170Vb = nullptr;
        require(SUCCEEDED(warp.device->CreateBuffer(
                    &r170VbDesc, &r170VbData, &r170Vb)) && r170Vb != nullptr,
                "R170 exact XYZ source-stride vertex buffer");
        ID3D11Buffer* r170Wvp =
            create_constant_buffer(warp.device, 16u * sizeof(float));
        D3DMATRIX r170Identity{};
        r170Identity._11 = r170Identity._22 =
            r170Identity._33 = r170Identity._44 = 1.0f;
        D3DMATRIX r170Clipped = r170Identity;
        r170Clipped._41 = 4.0f;
        const auto r170Offscreen =
            generate_fixed_function_transform_constants(
                r170Clipped, r170Identity, r170Identity, true);
        const auto r170Onscreen =
            generate_fixed_function_transform_constants(
                r170Identity, r170Identity, r170Identity, true);
        require(r170Offscreen.exact() && r170Onscreen.exact() &&
                    r170Offscreen.payloadHash != r170Onscreen.payloadHash,
                "R170 WVP identity and offscreen fixture identities differ");
        warp.context->IASetInputLayout(r170Ia);
        warp.context->IASetVertexBuffers(
            0u, 1u, &r170Vb, &r170Stride, &offset);
        warp.context->VSSetShader(r170Vs, nullptr, 0u);
        warp.context->PSSetShader(r170Ps, nullptr, 0u);
        warp.context->VSSetConstantBuffers(0u, 1u, &r170Wvp);
        const auto r170Pixel = [&](bool expectedWhite) {
            warp.context->CopyResource(readback, color);
            D3D11_MAPPED_SUBRESOURCE mapped{};
            require(SUCCEEDED(warp.context->Map(
                        readback, 0u, D3D11_MAP_READ, 0u, &mapped)) &&
                        mapped.pData != nullptr && mapped.RowPitch >= 64u,
                    "R170 translated FVF readback map");
            const auto* pixel =
                static_cast<const unsigned char*>(mapped.pData) +
                static_cast<std::size_t>(8u) * mapped.RowPitch + 4u * 8u;
            const unsigned char wanted = expectedWhite ? 255u : 0u;
            const bool centerOk = pixel[0] == wanted &&
                pixel[1] == wanted && pixel[2] == wanted &&
                pixel[3] == 255u;
            const auto* border = static_cast<const unsigned char*>(
                mapped.pData);
            const bool borderOk = border[0] == 0u && border[1] == 0u &&
                border[2] == 0u && border[3] == 255u;
            // Preserve the observed bytes before Unmap. A failed white
            // control must show whether geometry missed the center or the
            // generated VS/PS produced the wrong channel/alpha value.
            const std::array<unsigned int, 4> centerBytes = {
                pixel[0], pixel[1], pixel[2], pixel[3]};
            const std::array<unsigned int, 4> borderBytes = {
                border[0], border[1], border[2], border[3]};
            warp.context->Unmap(readback, 0u);
            if (!centerOk || !borderOk)
            {
                std::cerr << "R170 WARP translated FVF readback "
                          << (expectedWhite ? "positive" : "offscreen")
                          << " center BGRA=["
                          << centerBytes[0] << "," << centerBytes[1] << ","
                          << centerBytes[2] << "," << centerBytes[3]
                          << "] border BGRA=[" << borderBytes[0] << ","
                          << borderBytes[1] << "," << borderBytes[2] << ","
                          << borderBytes[3] << "]\n";
            }
            require(centerOk && borderOk,
                    expectedWhite
                        ? "R170 translated FVF+WVP white interior / clear border"
                        : "R170 displaced WVP fails closed to clear center");
        };
        warp.context->ClearRenderTargetView(target, clear);
        warp.context->UpdateSubresource(
            r170Wvp, 0u, nullptr,
            r170Offscreen.worldViewProjection.data(), 0u, 0u);
        warp.context->DrawIndexed(3u, 0u, 0);
        r170Pixel(false);
        warp.context->ClearRenderTargetView(target, clear);
        warp.context->UpdateSubresource(
            r170Wvp, 0u, nullptr,
            r170Onscreen.worldViewProjection.data(), 0u, 0u);
        // R170 A/B discriminator: keep real translated FVF IA/VS/WVP
        // identical while binding the already-proven R169 constant-red PS.
        // Failure here implicates translation/geometry/OM, not the generated
        // fixed-function pixel shader; success localizes the color mismatch
        // to the generated VS->PS color/linkage or PS contract.
        warp.context->PSSetShader(ps, nullptr, 0u);
        warp.context->DrawIndexed(3u, 0u, 0);
        verify(true);
        warp.context->PSSetShader(r170Ps, nullptr, 0u);
        warp.context->ClearRenderTargetView(target, clear);
        warp.context->DrawIndexed(3u, 0u, 0);
        r170Pixel(true);
        // R173 isolated real COLOR0 transport: unlike R172, use a single
        // direct pass-through PS and compare direct VS versus generated VS.
        // The existing R170 identity b0 WVP and indexed WARP setup are reused.
        constexpr DWORD r173Fvf = D3DFVF_XYZ | D3DFVF_DIFFUSE;
        struct R173Vertex { float x, y, z; D3DCOLOR color; };
        constexpr D3DCOLOR r173Color = 0xFF2080E0u;
        const R173Vertex r173Verts[3] = {
            {-0.75f,-0.75f,0.5f,r173Color},
            { 0.75f,-0.75f,0.5f,r173Color},
            { 0.0f, 0.75f,0.5f,r173Color}};
        const UINT r173Stride = sizeof(R173Vertex);
        const auto r173Layout = translate_vertex_input_layout(
            nullptr, 0u, r173Fvf, r173Stride);
        const auto r173Prototype =
            generate_fixed_function_vertex_shader_prototype(
                r173Fvf, r173Stride);
        require(r173Layout.exact && r173Layout.elementCount == 2u &&
                    r173Layout.elements[1].AlignedByteOffset == 12u &&
                    r173Layout.elements[1].Format ==
                        DXGI_FORMAT_R8G8B8A8_UNORM &&
                    r173Prototype.generated(),
                "R173 source packed COLOR0 FVF and generated VS");
        // Probe actual WARP input-assembler support, not texture support.
        UINT r173BgraSupport = 0u;
        UINT r173RgbaSupport = 0u;
        const HRESULT r173BgraQuery = warp.device->CheckFormatSupport(
            DXGI_FORMAT_B8G8R8A8_UNORM, &r173BgraSupport);
        const HRESULT r173RgbaQuery = warp.device->CheckFormatSupport(
            DXGI_FORMAT_R8G8B8A8_UNORM, &r173RgbaSupport);
        require(SUCCEEDED(r173RgbaQuery) &&
                    (r173RgbaSupport &
                        D3D11_FORMAT_SUPPORT_IA_VERTEX_BUFFER) != 0u,
                "R173 vertex color input requires supported RGBA IA format");
        std::cout << "DX11 R173 WARP IA_FORMAT BGRA="
                  << (SUCCEEDED(r173BgraQuery) &&
                      (r173BgraSupport &
                          D3D11_FORMAT_SUPPORT_IA_VERTEX_BUFFER) != 0u)
                  << " RGBA=1\n";
        D3D11_BUFFER_DESC r173Desc{};
        r173Desc.ByteWidth = sizeof(r173Verts);
        r173Desc.Usage = D3D11_USAGE_IMMUTABLE;
        r173Desc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA r173Init{};
        r173Init.pSysMem = r173Verts;
        ID3D11Buffer* r173VB = nullptr;
        require(SUCCEEDED(warp.device->CreateBuffer(
                    &r173Desc, &r173Init, &r173VB)) && r173VB,
                "R173 immutable packed COLOR0 buffer");
        static const std::string directVS = R"(
struct I {float3 position : POSITION0; float4 color : COLOR0;};
struct O {float4 position : SV_Position; float4 color : COLOR0;};
O main(I i) {O o; o.position=float4(i.position,1.0f);
              o.color=i.color.bgra; return o;}
)";
        // R174 independent WARP constant VS: exact same IA and PS,
        // fixed output bypasses source D3DCOLOR decoding.
        static const std::string constantVS = R"(
struct I {float3 position : POSITION0; float4 color : COLOR0;};
struct O {float4 position : SV_Position; float4 color : COLOR0;};
O main(I i) {O o; o.position=float4(i.position,1.0f);
             o.color=float4(32.0f/255.0f,128.0f/255.0f,
                            224.0f/255.0f,1.0f); return o;}
)";
        // R175: separate TEXCOORD6 pair. This does not change the global
        // R92 COLOR0/TEXCOORD8 generator contract or native game Draw.
        static const std::string r175VS = R"(
struct I {float3 position : POSITION0; float4 color : COLOR0;};
struct O {float4 position : SV_Position; float4 payload : TEXCOORD6;};
O main(I i) {O o; o.position=float4(i.position,1.0f);
             o.payload=float4(32.0f/255.0f,128.0f/255.0f,
                              224.0f/255.0f,1.0f); return o;}
)";
        static const char r175PS[] = R"(
float4 main(float4 payload : TEXCOORD6) : SV_Target {return payload;}
)";
        static const char directPS[] = R"(
float4 main(float4 color : COLOR0) : SV_Target {return color;}
)";
        ID3DBlob* r173DirectCode = compile_vertex_shader(directVS);
        ID3DBlob* r173ConstantCode = compile_vertex_shader(constantVS);
        ID3DBlob* r175VertexCode = compile_vertex_shader(r175VS);
        ID3DBlob* r175PixelCode = nullptr;
        ID3DBlob* r175Errors = nullptr;
        const HRESULT r175Compile = D3DCompile(
            r175PS, sizeof(r175PS)-1u, "R175Texcoord6",
            nullptr,nullptr,"main","ps_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0u,&r175PixelCode,&r175Errors);
        if (r175Errors) r175Errors->Release();
        require(SUCCEEDED(r175Compile) && r175PixelCode,
                "R175 dedicated TEXCOORD6 PS compiled");
        ID3DBlob* r173GeneratedCode =
            compile_vertex_shader(r173Prototype.source);
        ID3DBlob* r173PixelCode = nullptr;
        ID3DBlob* r173Err = nullptr;
        const HRESULT r173Compile = D3DCompile(
            directPS, sizeof(directPS)-1u, "R173COLOR0",
            nullptr,nullptr,"main","ps_4_0",
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0u,&r173PixelCode,&r173Err);
        if (r173Err) r173Err->Release();
        require(SUCCEEDED(r173Compile) && r173PixelCode,
                "R173 passthrough COLOR0 PS compiled");
        ID3D11VertexShader* r173DirectVS = nullptr;
        ID3D11VertexShader* r173ConstantVS = nullptr;
        ID3D11VertexShader* r175LinkedVS = nullptr;
        ID3D11PixelShader* r175LinkedPS = nullptr;
        ID3D11VertexShader* r173GeneratedVS = nullptr;
        ID3D11PixelShader* r173PS = nullptr;
        ID3D11InputLayout* r173IA = nullptr;
        require(SUCCEEDED(warp.device->CreateVertexShader(
                    r173DirectCode->GetBufferPointer(),
                    r173DirectCode->GetBufferSize(),nullptr,&r173DirectVS)) &&
                    r173DirectVS &&
                SUCCEEDED(warp.device->CreateVertexShader(
                    r173ConstantCode->GetBufferPointer(),
                    r173ConstantCode->GetBufferSize(),nullptr,&r173ConstantVS)) &&
                    r173ConstantVS &&
                SUCCEEDED(warp.device->CreateVertexShader(
                    r175VertexCode->GetBufferPointer(),
                    r175VertexCode->GetBufferSize(),nullptr,&r175LinkedVS)) &&
                    r175LinkedVS &&
                SUCCEEDED(warp.device->CreatePixelShader(
                    r175PixelCode->GetBufferPointer(),
                    r175PixelCode->GetBufferSize(),nullptr,&r175LinkedPS)) &&
                    r175LinkedPS &&
                SUCCEEDED(warp.device->CreateVertexShader(
                    r173GeneratedCode->GetBufferPointer(),
                    r173GeneratedCode->GetBufferSize(),nullptr,&r173GeneratedVS)) &&
                    r173GeneratedVS &&
                SUCCEEDED(warp.device->CreatePixelShader(
                    r173PixelCode->GetBufferPointer(),
                    r173PixelCode->GetBufferSize(),nullptr,&r173PS)) && r173PS &&
                SUCCEEDED(warp.device->CreateInputLayout(
                    r173Layout.elements.data(),r173Layout.elementCount,
                    r173DirectCode->GetBufferPointer(),
                    r173DirectCode->GetBufferSize(),&r173IA)) && r173IA,
                "R173 exact WARP pipeline objects");
        warp.context->IASetInputLayout(r173IA);
        warp.context->IASetVertexBuffers(
            0u,1u,&r173VB,&r173Stride,&offset);
        warp.context->PSSetShader(r173PS,nullptr,0u);
        const auto r173Pixel = [&]() {
            warp.context->CopyResource(readback,color);
            D3D11_MAPPED_SUBRESOURCE map{};
            require(SUCCEEDED(warp.context->Map(
                readback,0u,D3D11_MAP_READ,0u,&map)) &&
                map.pData && map.RowPitch>=64u,
                "R173 native WARP staging map");
            const auto* bytes =
                static_cast<const unsigned char*>(map.pData);
            const auto* center = bytes + 8u*map.RowPitch + 8u*4u;
            std::array<unsigned int,4> result{
                center[0],center[1],center[2],center[3]};
            const bool borderBlack = bytes[0]==0u && bytes[1]==0u &&
                bytes[2]==0u && bytes[3]==255u;
            warp.context->Unmap(readback,0u);
            require(borderBlack,"R173 untouched corner stays clear");
            return result;
        };
        const std::array<unsigned int,4> expected{
            224u,128u,32u,255u};
        warp.context->VSSetShader(r173DirectVS,nullptr,0u);
        warp.context->ClearRenderTargetView(target,clear);
        const auto blank = r173Pixel();
        require(blank[0]==0u && blank[1]==0u &&
                    blank[2]==0u && blank[3]==255u,
                "R173 clear-only negative control");
        warp.context->DrawIndexed(3u,0u,0);
        const auto directColor = r173Pixel();
        // R173: finish both VS controls before fail-closed assertions, so
        // negative evidence always includes both WARP BGRA readbacks.
        const bool directMatches = directColor == expected;
        warp.context->VSSetShader(r173GeneratedVS,nullptr,0u);
        warp.context->ClearRenderTargetView(target,clear);
        warp.context->DrawIndexed(3u,0u,0);
        const auto generatedColor = r173Pixel();
        const bool generatedMatches = generatedColor==expected;
        // A constant-color VS isolates vertex COLOR0 from VS->PS and OM.
        // A solid-red PS using the original VS independently proves coverage.
        warp.context->VSSetShader(r173ConstantVS,nullptr,0u);
        warp.context->ClearRenderTargetView(target,clear);
        warp.context->DrawIndexed(3u,0u,0);
        const auto constantColor = r173Pixel();
        const bool constantMatches = constantColor==expected;
        warp.context->VSSetShader(r173DirectVS,nullptr,0u);
        warp.context->PSSetShader(ps,nullptr,0u);
        warp.context->ClearRenderTargetView(target,clear);
        warp.context->DrawIndexed(3u,0u,0);
        const auto solidPsColor = r173Pixel();
        const std::array<unsigned int,4> expectedRed{0u,0u,255u,255u};
        const bool solidPsMatches = solidPsColor==expectedRed;
        // Preserve the same RTV, viewport, IA, geometry and index topology;
        // change ONLY the VS/PS linkage semantic for the R175 control.
        warp.context->VSSetShader(r175LinkedVS,nullptr,0u);
        warp.context->PSSetShader(r175LinkedPS,nullptr,0u);
        warp.context->ClearRenderTargetView(target,clear);
        warp.context->DrawIndexed(3u,0u,0);
        const auto r175Color = r173Pixel();
        const bool r175Matches = r175Color==expected;
        warp.context->PSSetShader(r173PS,nullptr,0u);
        std::cout<<"DX11 R173 COLOR0 direct VS BGRA=["
            <<directColor[0]<<","<<directColor[1]<<","
            <<directColor[2]<<","<<directColor[3]
            <<"] generated VS BGRA=["
            <<generatedColor[0]<<","<<generatedColor[1]<<","
            <<generatedColor[2]<<","<<generatedColor[3]
            <<"] constant VS BGRA=["
            <<constantColor[0]<<","<<constantColor[1]<<","
            <<constantColor[2]<<","<<constantColor[3]
            <<"] solid PS BGRA=["
            <<solidPsColor[0]<<","<<solidPsColor[1]<<","
            <<solidPsColor[2]<<","<<solidPsColor[3]
            <<"] R175 TEXCOORD6 BGRA=["
            <<r175Color[0]<<","<<r175Color[1]<<","
            <<r175Color[2]<<","<<r175Color[3]
            <<"] expected BGRA=["
            <<expected[0]<<","<<expected[1]<<","
            <<expected[2]<<","<<expected[3]
            <<"] classification="
            <<(!solidPsMatches?"R174_GEOMETRY_OR_OM_MISMATCH"
                :(!r175Matches?"R175_GENERIC_VARYING_MISMATCH"
                :(!constantMatches?"R174_COLOR0_VARYING_MISMATCH"
                :(!directMatches?"R174_IA_VERTEX_COLOR_MISMATCH"
                :(!generatedMatches?"GENERATED_VS_COLOR0_MISMATCH"
                                   :"ALL_R175_CONTROLS_MATCH")))))<<std::endl;
        // An incorrect direct control invalidates generated-VS attribution.
        // Neither failure can be treated as native gameplay approval.
        require(solidPsMatches,
                "R174 known-geometry solid PS must cover interior");
        require(r175Matches,
                "R175 independent TEXCOORD6 VS/PS varying control");
        require(constantMatches,
                "R174 constant VS color must survive PS and OM");
        require(directMatches,
                "R173 direct VS COLOR0 packed-BGRA passthrough control");
        require(generatedMatches,
                "R173 generated VS COLOR0 packed-BGRA passthrough control");
        warp.context->IASetInputLayout(r170Ia);
        warp.context->IASetVertexBuffers(
            0u,1u,&r170Vb,&r170Stride,&offset);
        warp.context->VSSetShader(r170Vs,nullptr,0u);
        warp.context->PSSetShader(r170Ps,nullptr,0u);
        r173IA->Release();
        r173VB->Release();
        r173PS->Release();
        r173GeneratedVS->Release();
        r175LinkedPS->Release();
        r175LinkedVS->Release();
        r173ConstantVS->Release();
        r173DirectVS->Release();
        r173PixelCode->Release();
        r173GeneratedCode->Release();
        r175PixelCode->Release();
        r175VertexCode->Release();
        r173ConstantCode->Release();
        r173DirectCode->Release();
        std::cout<<"DX11 WARP COLOR0 source-linkage isolation R173: PASS\n";
        ID3D11Buffer* r170NullWvp = nullptr;
        warp.context->VSSetConstantBuffers(0u, 1u, &r170NullWvp);
        r170Wvp->Release();
        r170Vb->Release();
        r170Ia->Release();
        r170Ps->Release();
        r170Vs->Release();
        r170PsCode->Release();
        r170VsCode->Release();
        std::cout << "DX11 WARP translated FVF fragment provenance R170: PASS\n";

        warp.context->OMSetRenderTargets(0u, nullptr, nullptr);
        raster->Release();
        ib->Release();
        vb->Release();
        layout->Release();
        ps->Release();
        vs->Release();
        pixelCode->Release();
        vertexCode->Release();
        readback->Release();
        target->Release();
        color->Release();
        warp.context->ClearState();
        warp.context->Release();
        warp.device->Release();
    }

}

int main()
{
    const auto a2b10g10r10 = translate_resource_format(
        D3DFMT_A2B10G10R10, ResourceRole::Texture);
    require(
        a2b10g10r10.exact &&
        a2b10g10r10.format == DXGI_FORMAT_R10G10B10A2_UNORM,
        "A2B10G10R10 must map exactly to R10G10B10A2_UNORM");

    const auto a2r10g10b10 = translate_resource_format(
        D3DFMT_A2R10G10B10, ResourceRole::Texture);
    require(
        !a2r10g10b10.exact &&
        a2r10g10b10.format == DXGI_FORMAT_UNKNOWN,
        "A2R10G10B10 must remain fail-closed without a direct DXGI equivalent");

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

    constexpr DWORD fixedFunctionFvf =
        D3DFVF_XYZ | D3DFVF_DIFFUSE | D3DFVF_TEX1;
    const auto vertexPrototype =
        generate_fixed_function_vertex_shader_prototype(
            fixedFunctionFvf, 24);
    require(
        vertexPrototype.generated(),
        "R93 vertex prototype prerequisite");

    const auto inputLayout =
        translate_vertex_input_layout(
            nullptr, 0, fixedFunctionFvf, 24);
    require(
        inputLayout.exact && inputLayout.elementCount > 0,
        "R97 input-layout prerequisite");

    std::array<FixedFunctionStageState, 8> stages{};
    stages[0] = active_stage();
    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);
    const auto pixelPrototype =
        generate_fixed_function_pixel_shader_prototype(
            stages, true, 0x01, 0x01, textureTypes);
    require(
        pixelPrototype.generated(),
        "R97 pixel prototype prerequisite");

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

    const DWORD r264VsTokens[] = {
        D3DVS_VERSION(3, 0),
        0x0000FFFFu,
    };
    const DWORD r264PsTokens[] = {
        D3DPS_VERSION(3, 0),
        0x0000FFFFu,
    };
    const auto r264VsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r264VsTokens, sizeof(r264VsTokens), true);
    const auto r264PsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r264PsTokens, sizeof(r264PsTokens), false);
    const ProgrammableShaderFunctionIdentity r264VsIdentity{
        true,
        true,
        r264VsEvidence.byteSize,
        r264VsEvidence.versionToken,
        r264VsEvidence.bytecodeHash,
    };
    const ProgrammableShaderFunctionIdentity r264PsIdentity{
        true,
        true,
        r264PsEvidence.byteSize,
        r264PsEvidence.versionToken,
        r264PsEvidence.bytecodeHash,
    };
    require(
        r264VsEvidence.exact() &&
        r264PsEvidence.exact() &&
        r264VsEvidence.tokens.size() == 2u &&
        r264PsEvidence.tokens.size() == 2u &&
        outrun::vr::dx11::
            validate_programmable_shader_function_source_evidence(
                r264VsEvidence, r264VsIdentity, true) &&
        outrun::vr::dx11::
            validate_programmable_shader_function_source_evidence(
                r264PsEvidence, r264PsIdentity, false),
        "R264 captures exact programmable shader source bytecode evidence");

    auto r264DriftedVsIdentity = r264VsIdentity;
    r264DriftedVsIdentity.bytecodeHash ^= 1ull;
    const auto r264WrongStageEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r264VsTokens, sizeof(r264VsTokens), false);
    const auto r264MisalignedEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r264VsTokens,
                static_cast<UINT>(sizeof(r264VsTokens) - 1u),
                true);
    require(
        !outrun::vr::dx11::
            validate_programmable_shader_function_source_evidence(
                r264VsEvidence, r264DriftedVsIdentity, true) &&
        !r264WrongStageEvidence.exact() &&
        !r264MisalignedEvidence.exact(),
        "R264 rejects source identity drift, wrong-stage bytecode, and misaligned payloads");

    const DWORD r265VsTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_MOV) | (2u << 24u),
        0x800F0000u,
        0x80E40000u,
        static_cast<DWORD>(D3DSIO_COMMENT) | (1u << 16u),
        0x26500001u,
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r265VsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r265VsTokens, sizeof(r265VsTokens), true);
    const auto r265VsDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r265VsEvidence);
    require(
        r265VsDecode.exact() &&
        r265VsDecode.vertexStage &&
        r265VsDecode.instructionCount == 1u &&
        r265VsDecode.operandTokenCount == 2u &&
        r265VsDecode.commentDwordCount == 1u &&
        r265VsDecode.instructions.size() == 1u &&
        r265VsDecode.instructions[0].opcode ==
            static_cast<DWORD>(D3DSIO_MOV) &&
        r265VsDecode.instructions[0].operandCount == 2u &&
        r265VsDecode.instructions[0].operandTokens.size() == 2u &&
        r265VsDecode.sourceBytecodeHash == r265VsEvidence.bytecodeHash &&
        r265VsDecode.instructionStreamHash != 0 &&
        r265VsDecode.decoderRevisionHash != 0 &&
        r265VsDecode.semanticContractHash != 0,
        "R265 decodes exact SM3 instruction and raw operand provenance");

    const auto r265TruncatedEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r265VsTokens,
                static_cast<UINT>(sizeof(r265VsTokens) - sizeof(DWORD)),
                true);
    const DWORD r265UnknownOpcodeTokens[] = {
        D3DVS_VERSION(3, 0),
        0x00001234u | (1u << 24u),
        0x80000000u,
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r265UnknownOpcodeEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r265UnknownOpcodeTokens,
                sizeof(r265UnknownOpcodeTokens),
                true);
    const DWORD r265Sm1Tokens[] = {
        D3DVS_VERSION(1, 1),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r265Sm1Evidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r265Sm1Tokens, sizeof(r265Sm1Tokens), true);
    const auto r265TruncatedDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r265TruncatedEvidence);
    const auto r265UnknownOpcodeDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r265UnknownOpcodeEvidence);
    const auto r265Sm1Decode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r265Sm1Evidence);
    require(
        r265TruncatedEvidence.exact() &&
        !r265TruncatedDecode.exact() &&
        !r265TruncatedDecode.endSeen &&
        r265UnknownOpcodeEvidence.exact() &&
        !r265UnknownOpcodeDecode.exact() &&
        r265Sm1Evidence.exact() &&
        !r265Sm1Decode.versionSupported &&
        !r265Sm1Decode.exact(),
        "R265 fails closed on truncated, unknown-opcode, and SM1 streams");

    const auto r266ParameterToken =
        [](D3DSHADER_PARAM_REGISTER_TYPE type,
           UINT index,
           DWORD payload) noexcept -> DWORD
    {
        const DWORD rawType = static_cast<DWORD>(type);
        return 0x80000000u |
               (index & D3DSP_REGNUM_MASK) |
               ((rawType << D3DSP_REGTYPE_SHIFT) &
                D3DSP_REGTYPE_MASK) |
               ((rawType << D3DSP_REGTYPE_SHIFT2) &
                D3DSP_REGTYPE_MASK2) |
               payload;
    };

    const DWORD r266VsTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_MOV) | (3u << 24u),
        r266ParameterToken(
            D3DSPR_TEMP, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_CONST2,
            7u,
            D3DSP_NOSWIZZLE | D3DSHADER_ADDRMODE_RELATIVE),
        r266ParameterToken(
            D3DSPR_ADDR, 0u, D3DSP_REPLICATERED),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r266VsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r266VsTokens, sizeof(r266VsTokens), true);
    const auto r266VsDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r266VsEvidence);
    const auto r266VsSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r266VsDecode);
    require(
        r266VsSemantics.exact() &&
        r266VsSemantics.versionToken == r266VsDecode.versionToken &&
        r266VsSemantics.sourceBytecodeHash ==
            r266VsDecode.sourceBytecodeHash &&
        outrun::vr::dx11::
            validate_programmable_shader_register_semantics(
                r266VsSemantics, r266VsDecode) &&
        r266VsSemantics.vertexStage &&
        r266VsSemantics.semanticInstructionCount == 1u &&
        r266VsSemantics.destinationOperandCount == 1u &&
        r266VsSemantics.sourceOperandCount == 1u &&
        r266VsSemantics.relativeAddressOperandCount == 1u &&
        r266VsSemantics.floatConstantReferenceCount == 1u &&
        r266VsSemantics.samplerReferenceCount == 0u &&
        r266VsSemantics.operands.size() == 3u &&
        r266VsSemantics.operands[0].role ==
            ProgrammableShaderRegisterOperandRole::Destination &&
        r266VsSemantics.operands[1].role ==
            ProgrammableShaderRegisterOperandRole::Source &&
        r266VsSemantics.operands[1].registerType ==
            D3DSPR_CONST2 &&
        r266VsSemantics.operands[1].registerIndex == 7u &&
        r266VsSemantics.operands[1].constantReference &&
        r266VsSemantics.operands[1].normalizedConstantIndex ==
            2055u &&
        r266VsSemantics.operands[1].relativeAddressing &&
        r266VsSemantics.operands[2].role ==
            ProgrammableShaderRegisterOperandRole::RelativeAddress &&
        r266VsSemantics.operands[2].registerType ==
            D3DSPR_ADDR &&
        r266VsSemantics.registerSemanticsHash != 0 &&
        r266VsSemantics.decoderRevisionHash != 0 &&
        r266VsSemantics.semanticContractHash != 0,
        "R266 decodes destination/source register semantics, relative addressing, and normalized constant provenance");

    auto r270StaleVsSemantics = r266VsSemantics;
    r270StaleVsSemantics.sourceBytecodeHash =
        r266VsSemantics.sourceBytecodeHash == 1ull
            ? 2ull
            : (r266VsSemantics.sourceBytecodeHash ^ 1ull);
    require(
        r270StaleVsSemantics.exact() &&
        !outrun::vr::dx11::
            validate_programmable_shader_register_semantics(
                r270StaleVsSemantics, r266VsDecode),
        "R270 rejects detached R266 register semantics with stale R265 source provenance");

    const DWORD r266PsTokens[] = {
        D3DPS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_TEX) | (3u << 24u),
        r266ParameterToken(
            D3DSPR_TEMP, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_NOSWIZZLE),
        r266ParameterToken(
            D3DSPR_SAMPLER, 3u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r266PsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r266PsTokens, sizeof(r266PsTokens), false);
    const auto r266PsDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r266PsEvidence);
    const auto r266PsSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r266PsDecode);
    require(
        r266PsSemantics.exact() &&
        outrun::vr::dx11::
            validate_programmable_shader_register_semantics(
                r266PsSemantics, r266PsDecode) &&
        !r266PsSemantics.vertexStage &&
        r266PsSemantics.destinationOperandCount == 1u &&
        r266PsSemantics.sourceOperandCount == 2u &&
        r266PsSemantics.samplerReferenceCount == 1u &&
        r266PsSemantics.operands.size() == 3u &&
        r266PsSemantics.operands[2].samplerReference &&
        r266PsSemantics.operands[2].registerType ==
            D3DSPR_SAMPLER &&
        r266PsSemantics.operands[2].registerIndex == 3u,
        "R266 derives exact TEX sampler provenance");

    const DWORD r266UnsupportedTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_SGN) | (4u << 24u),
        r266ParameterToken(
            D3DSPR_TEMP, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_TEMP, 1u, D3DSP_NOSWIZZLE),
        r266ParameterToken(
            D3DSPR_CONST, 0u, D3DSP_NOSWIZZLE),
        r266ParameterToken(
            D3DSPR_CONST, 1u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r266UnsupportedEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r266UnsupportedTokens,
                sizeof(r266UnsupportedTokens),
                true);
    const auto r266UnsupportedDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r266UnsupportedEvidence);
    const auto r266UnsupportedSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r266UnsupportedDecode);
    require(
        r266UnsupportedDecode.exact() &&
        !r266UnsupportedSemantics.complete &&
        !r266UnsupportedSemantics.exact(),
        "R266 preserves R265 structure but fails closed on model-dependent register-role layouts");

    const auto r267DclSemanticToken =
        [](D3DDECLUSAGE usage, UINT usageIndex) noexcept -> DWORD
    {
        return 0x80000000u |
               (static_cast<DWORD>(usage) & D3DSP_DCL_USAGE_MASK) |
               ((usageIndex << D3DSP_DCL_USAGEINDEX_SHIFT) &
                D3DSP_DCL_USAGEINDEX_MASK);
    };

    const DWORD r267VsTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_POSITION, 0u),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_POSITION, 0u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 1u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 2u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        0x80000000u | static_cast<DWORD>(D3DSTT_2D),
        r266ParameterToken(
            D3DSPR_SAMPLER, 0u, 0u),
        static_cast<DWORD>(D3DSIO_MOV) | (2u << 24u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_MOV) | (2u << 24u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 2u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r267VsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r267VsTokens, sizeof(r267VsTokens), true);
    const auto r267VsDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r267VsEvidence);
    const auto r267VsRegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r267VsDecode);
    const auto r267VsInterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r267VsDecode, r267VsRegisterSemantics);
    require(
        r267VsDecode.exact() &&
        r267VsDecode.versionToken == D3DVS_VERSION(3, 0) &&
        r267VsRegisterSemantics.exact() &&
        r267VsInterfaceSemantics.exact() &&
        r267VsInterfaceSemantics.vertexStage &&
        r267VsInterfaceSemantics.versionToken ==
            r267VsEvidence.versionToken &&
        r267VsInterfaceSemantics.sourceBytecodeHash ==
            r267VsEvidence.bytecodeHash &&
        r267VsInterfaceSemantics.shaderModel3 &&
        r267VsInterfaceSemantics.declarationInstructionCount == 4u &&
        r267VsInterfaceSemantics.semanticDeclarationCount == 3u &&
        r267VsInterfaceSemantics.inputSemanticCount == 1u &&
        r267VsInterfaceSemantics.outputSemanticCount == 2u &&
        r267VsInterfaceSemantics.samplerDeclarationCount == 1u &&
        r267VsInterfaceSemantics.semantics.size() == 3u &&
        r267VsInterfaceSemantics.semantics[0].input &&
        !r267VsInterfaceSemantics.semantics[0].output &&
        r267VsInterfaceSemantics.semantics[0].usage ==
            D3DDECLUSAGE_POSITION &&
        r267VsInterfaceSemantics.semantics[0].usageIndex == 0u &&
        r267VsInterfaceSemantics.semantics[0].registerType ==
            D3DSPR_INPUT &&
        r267VsInterfaceSemantics.semantics[0].registerIndex == 0u &&
        r267VsInterfaceSemantics.semantics[0].writeMask ==
            D3DSP_WRITEMASK_ALL &&
        !r267VsInterfaceSemantics.semantics[1].input &&
        r267VsInterfaceSemantics.semantics[1].output &&
        r267VsInterfaceSemantics.semantics[1].usage ==
            D3DDECLUSAGE_POSITION &&
        r267VsInterfaceSemantics.semantics[1].usageIndex == 0u &&
        r267VsInterfaceSemantics.semantics[1].registerType ==
            D3DSPR_OUTPUT &&
        r267VsInterfaceSemantics.semantics[1].registerIndex == 0u &&
        r267VsInterfaceSemantics.semantics[1].writeMask ==
            D3DSP_WRITEMASK_ALL &&
        !r267VsInterfaceSemantics.semantics[2].input &&
        r267VsInterfaceSemantics.semantics[2].output &&
        r267VsInterfaceSemantics.semantics[2].usage ==
            D3DDECLUSAGE_TEXCOORD &&
        r267VsInterfaceSemantics.semantics[2].usageIndex == 1u &&
        r267VsInterfaceSemantics.semantics[2].registerType ==
            D3DSPR_OUTPUT &&
        r267VsInterfaceSemantics.semantics[2].registerIndex == 2u &&
        r267VsInterfaceSemantics.semantics[2].writeMask ==
            D3DSP_WRITEMASK_ALL &&
        r267VsInterfaceSemantics.interfaceSemanticsHash != 0 &&
        r267VsInterfaceSemantics.decoderRevisionHash != 0 &&
        r267VsInterfaceSemantics.semanticContractHash != 0,
        "R267 decodes exact SM3 DCL input/output interface semantics");

    const DWORD r267MissingMarkerTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        static_cast<DWORD>(D3DDECLUSAGE_POSITION),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r267MissingMarkerDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                outrun::vr::dx11::
                    capture_programmable_shader_function_source_evidence(
                        r267MissingMarkerTokens,
                        sizeof(r267MissingMarkerTokens),
                        true));
    const auto r267MissingMarkerRegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r267MissingMarkerDecode);
    const auto r267MissingMarkerInterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r267MissingMarkerDecode,
                r267MissingMarkerRegisterSemantics);
    require(
        r267MissingMarkerDecode.exact() &&
        r267MissingMarkerRegisterSemantics.exact() &&
        !r267MissingMarkerInterfaceSemantics.complete &&
        !r267MissingMarkerInterfaceSemantics.exact(),
        "R267 rejects DCL info tokens without parameter marker bit");

    const DWORD r267Sm2Tokens[] = {
        D3DVS_VERSION(2, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_POSITION, 0u),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r267Sm2Decode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                outrun::vr::dx11::
                    capture_programmable_shader_function_source_evidence(
                        r267Sm2Tokens, sizeof(r267Sm2Tokens), true));
    const auto r267Sm2RegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r267Sm2Decode);
    const auto r267Sm2InterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r267Sm2Decode, r267Sm2RegisterSemantics);
    require(
        r267Sm2Decode.exact() &&
        r267Sm2Decode.versionToken == D3DVS_VERSION(2, 0) &&
        r267Sm2RegisterSemantics.exact() &&
        !r267Sm2InterfaceSemantics.shaderModel3 &&
        !r267Sm2InterfaceSemantics.complete &&
        !r267Sm2InterfaceSemantics.exact(),
        "R267 rejects SM2 DCL interface semantics");

    const DWORD r267DuplicateTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 0u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 0u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 1u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r267DuplicateDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                outrun::vr::dx11::
                    capture_programmable_shader_function_source_evidence(
                        r267DuplicateTokens,
                        sizeof(r267DuplicateTokens),
                        true));
    const auto r267DuplicateRegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r267DuplicateDecode);
    const auto r267DuplicateInterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r267DuplicateDecode,
                r267DuplicateRegisterSemantics);
    require(
        r267DuplicateDecode.exact() &&
        r267DuplicateRegisterSemantics.exact() &&
        r267DuplicateInterfaceSemantics.shaderModel3 &&
        !r267DuplicateInterfaceSemantics.complete &&
        !r267DuplicateInterfaceSemantics.exact(),
        "R267 rejects duplicate SM3 interface semantic declarations");

    const DWORD r267OverlapTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 0u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 0u,
            D3DSP_WRITEMASK_0 | D3DSP_WRITEMASK_1),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_COLOR, 0u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 0u,
            D3DSP_WRITEMASK_1 | D3DSP_WRITEMASK_2),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r267OverlapDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                outrun::vr::dx11::
                    capture_programmable_shader_function_source_evidence(
                        r267OverlapTokens,
                        sizeof(r267OverlapTokens),
                        true));
    const auto r267OverlapRegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r267OverlapDecode);
    const auto r267OverlapInterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r267OverlapDecode,
                r267OverlapRegisterSemantics);
    require(
        r267OverlapDecode.exact() &&
        r267OverlapRegisterSemantics.exact() &&
        r267OverlapInterfaceSemantics.shaderModel3 &&
        !r267OverlapInterfaceSemantics.complete &&
        !r267OverlapInterfaceSemantics.exact(),
        "R267 rejects overlapping SM3 interface declaration masks");

    const DWORD r268PsTokens[] = {
        D3DPS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 1u),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_MOV) | (2u << 24u),
        r266ParameterToken(
            D3DSPR_COLOROUT, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r268PsEvidence =
        outrun::vr::dx11::
            capture_programmable_shader_function_source_evidence(
                r268PsTokens, sizeof(r268PsTokens), false);
    const auto r268PsDecode =
        outrun::vr::dx11::
            decode_programmable_shader_instruction_stream(
                r268PsEvidence);
    const auto r268PsRegisterSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_register_semantics(
                r268PsDecode);
    const auto r268PsInterfaceSemantics =
        outrun::vr::dx11::
            decode_programmable_shader_interface_semantics(
                r268PsDecode, r268PsRegisterSemantics);
    const auto r268Linkage =
        outrun::vr::dx11::
            derive_programmable_shader_interface_linkage_evidence(
                r267VsInterfaceSemantics,
                r268PsInterfaceSemantics);
    require(
        r268PsDecode.exact() &&
        r268PsRegisterSemantics.exact() &&
        r268PsInterfaceSemantics.exact() &&
        !r268PsInterfaceSemantics.vertexStage &&
        r268Linkage.exact() &&
        r268Linkage.vertexVersionToken == r267VsEvidence.versionToken &&
        r268Linkage.pixelVersionToken == r268PsDecode.versionToken &&
        r268Linkage.vertexSourceBytecodeHash ==
            r267VsEvidence.bytecodeHash &&
        r268Linkage.pixelSourceBytecodeHash ==
            r268PsDecode.sourceBytecodeHash &&
        r268Linkage.vertexOutputSemanticCount == 2u &&
        r268Linkage.pixelInputSemanticCount == 1u &&
        r268Linkage.matchedSemanticCount == 1u &&
        r268Linkage.interfaceLinkHash != 0 &&
        r268Linkage.linkerRevisionHash != 0 &&
        r268Linkage.semanticContractHash != 0,
        "R268 derives exact VS-output to PS-input stage linkage");

    auto r268SemanticMismatch = r268PsInterfaceSemantics;
    r268SemanticMismatch.semantics[0].usage = D3DDECLUSAGE_COLOR;
    const auto r268SemanticMismatchLinkage =
        outrun::vr::dx11::
            derive_programmable_shader_interface_linkage_evidence(
                r267VsInterfaceSemantics,
                r268SemanticMismatch);
    require(
        !r268SemanticMismatchLinkage.complete &&
        !r268SemanticMismatchLinkage.exact(),
        "R268 rejects unmatched pixel input semantics");

    auto r268NarrowVertex = r267VsInterfaceSemantics;
    r268NarrowVertex.semantics[2].writeMask =
        D3DSP_WRITEMASK_0 | D3DSP_WRITEMASK_1;
    auto r268WidePixel = r268PsInterfaceSemantics;
    r268WidePixel.semantics[0].writeMask = D3DSP_WRITEMASK_ALL;
    const auto r268MaskMismatchLinkage =
        outrun::vr::dx11::
            derive_programmable_shader_interface_linkage_evidence(
                r268NarrowVertex,
                r268WidePixel);
    require(
        !r268MaskMismatchLinkage.complete &&
        !r268MaskMismatchLinkage.exact(),
        "R268 rejects insufficient vertex output component coverage");

    const auto r268StageSwapLinkage =
        outrun::vr::dx11::
            derive_programmable_shader_interface_linkage_evidence(
                r268PsInterfaceSemantics,
                r267VsInterfaceSemantics);
    require(
        !r268StageSwapLinkage.vertexInterfaceExact &&
        !r268StageSwapLinkage.pixelInterfaceExact &&
        !r268StageSwapLinkage.exact(),
        "R268 rejects reversed VS and PS interface receipts");

    const ProgrammableShaderFunctionIdentity programmableVs{
        true,
        true,
        static_cast<UINT>(sizeof(r267VsTokens)),
        r267VsEvidence.versionToken,
        r267VsEvidence.bytecodeHash,
    };
    const ProgrammableShaderFunctionIdentity programmablePs{
        true,
        true,
        static_cast<UINT>(sizeof(r268PsTokens)),
        r268PsDecode.versionToken,
        r268PsDecode.sourceBytecodeHash,
    };
    const auto programmablePair =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, programmablePs);
    require(
        programmablePair.exact_identity() &&
        !programmablePair.translationImplemented,
        "R240 programmable pair identity prerequisite");

    const auto r271SourceSemanticPair =
        derive_programmable_shader_pair_source_semantic_evidence(
            programmablePair,
            r267VsRegisterSemantics,
            r268PsRegisterSemantics,
            r268Linkage);
    require(
        validate_programmable_shader_register_semantics(
            r267VsRegisterSemantics, r267VsDecode) &&
        validate_programmable_shader_register_semantics(
            r268PsRegisterSemantics, r268PsDecode) &&
        r271SourceSemanticPair.exact() &&
        r271SourceSemanticPair.sourceIdentityExact &&
        r271SourceSemanticPair.vertexRegisterSemanticsExact &&
        r271SourceSemanticPair.pixelRegisterSemanticsExact &&
        r271SourceSemanticPair.interfaceLinkageExact &&
        r271SourceSemanticPair.cacheKey == programmablePair.cacheKey &&
        r271SourceSemanticPair.vertexSourceBytecodeHash ==
            programmablePair.vertexShader.bytecodeHash &&
        r271SourceSemanticPair.pixelSourceBytecodeHash ==
            programmablePair.pixelShader.bytecodeHash &&
        r271SourceSemanticPair.vertexRegisterSemanticsHash ==
            r267VsRegisterSemantics.registerSemanticsHash &&
        r271SourceSemanticPair.pixelRegisterSemanticsHash ==
            r268PsRegisterSemantics.registerSemanticsHash &&
        r271SourceSemanticPair.interfaceLinkHash ==
            r268Linkage.interfaceLinkHash &&
        r271SourceSemanticPair.pairSemanticHash != 0 &&
        r271SourceSemanticPair.receiptRevisionHash != 0 &&
        r271SourceSemanticPair.semanticContractHash != 0,
        "R271 composes exact R239 R266 R268 pair source-semantic receipt");

    auto r271StalePixelSemantics = r268PsRegisterSemantics;
    r271StalePixelSemantics.sourceBytecodeHash =
        r268PsRegisterSemantics.sourceBytecodeHash == 1ull
            ? 2ull
            : (r268PsRegisterSemantics.sourceBytecodeHash ^ 1ull);
    const auto r271StalePair =
        derive_programmable_shader_pair_source_semantic_evidence(
            programmablePair,
            r267VsRegisterSemantics,
            r271StalePixelSemantics,
            r268Linkage);
    require(
        r271StalePixelSemantics.exact() &&
        !r271StalePair.pixelRegisterSemanticsExact &&
        !r271StalePair.complete &&
        !r271StalePair.exact(),
        "R271 rejects detached pixel register semantics from another source stream");

    const DWORD r272VsTokens[] = {
        D3DVS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_POSITION, 0u),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 1u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 2u, D3DSP_WRITEMASK_ALL),
        static_cast<DWORD>(D3DSIO_MOV) | (2u << 24u),
        r266ParameterToken(
            D3DSPR_OUTPUT, 2u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_CONST, 5u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const DWORD r272PsTokens[] = {
        D3DPS_VERSION(3, 0),
        static_cast<DWORD>(D3DSIO_DCL) | (2u << 24u),
        r267DclSemanticToken(D3DDECLUSAGE_TEXCOORD, 1u),
        r266ParameterToken(
            D3DSPR_INPUT, 0u,
            D3DSP_WRITEMASK_0 | D3DSP_WRITEMASK_1),
        static_cast<DWORD>(D3DSIO_TEX) | (3u << 24u),
        r266ParameterToken(
            D3DSPR_TEMP, 0u, D3DSP_WRITEMASK_ALL),
        r266ParameterToken(
            D3DSPR_INPUT, 0u, D3DSP_NOSWIZZLE),
        r266ParameterToken(
            D3DSPR_SAMPLER, 3u, D3DSP_NOSWIZZLE),
        static_cast<DWORD>(D3DSIO_END),
    };
    const auto r272VsEvidence =
        capture_programmable_shader_function_source_evidence(
            r272VsTokens, sizeof(r272VsTokens), true);
    const auto r272PsEvidence =
        capture_programmable_shader_function_source_evidence(
            r272PsTokens, sizeof(r272PsTokens), false);
    const auto r272VsDecode =
        decode_programmable_shader_instruction_stream(r272VsEvidence);
    const auto r272PsDecode =
        decode_programmable_shader_instruction_stream(r272PsEvidence);
    const auto r272VsRegisterSemantics =
        decode_programmable_shader_register_semantics(r272VsDecode);
    const auto r272PsRegisterSemantics =
        decode_programmable_shader_register_semantics(r272PsDecode);
    const auto r272VsInterfaceSemantics =
        decode_programmable_shader_interface_semantics(
            r272VsDecode, r272VsRegisterSemantics);
    const auto r272PsInterfaceSemantics =
        decode_programmable_shader_interface_semantics(
            r272PsDecode, r272PsRegisterSemantics);
    const auto r272Linkage =
        derive_programmable_shader_interface_linkage_evidence(
            r272VsInterfaceSemantics, r272PsInterfaceSemantics);
    const ProgrammableShaderFunctionIdentity r272VsIdentity{
        true, true, static_cast<UINT>(sizeof(r272VsTokens)),
        r272VsEvidence.versionToken, r272VsEvidence.bytecodeHash,
    };
    const ProgrammableShaderFunctionIdentity r272PsIdentity{
        true, true, static_cast<UINT>(sizeof(r272PsTokens)),
        r272PsEvidence.versionToken, r272PsEvidence.bytecodeHash,
    };
    const auto r272Pair =
        seal_programmable_shader_pair_cache_identity(
            true, false, r272VsIdentity, r272PsIdentity);
    const auto r272SourceReceipt =
        derive_programmable_shader_pair_source_semantic_evidence(
            r272Pair, r272VsRegisterSemantics,
            r272PsRegisterSemantics, r272Linkage);
    const auto r272MappingPlan =
        derive_programmable_shader_register_mapping_plan(
            r272SourceReceipt,
            r272VsRegisterSemantics,
            r272PsRegisterSemantics);
    require(
        r272SourceReceipt.exact() &&
        r272MappingPlan.exact() &&
        r272MappingPlan.sourceSemanticReceiptExact &&
        r272MappingPlan.vertexRegisterSemanticsExact &&
        r272MappingPlan.pixelRegisterSemanticsExact &&
        r272MappingPlan.constantRegisterMappingExact &&
        r272MappingPlan.samplerMappingExact &&
        r272MappingPlan.constantMappingCount == 1u &&
        r272MappingPlan.samplerMappingCount == 1u &&
        r272MappingPlan.constantMappings.size() == 1u &&
        r272MappingPlan.constantMappings[0].vertexStage &&
        r272MappingPlan.constantMappings[0].registerClass ==
            ProgrammableShaderConstantRegisterClass::Float &&
        r272MappingPlan.constantMappings[0].sourceRegisterType ==
            D3DSPR_CONST &&
        r272MappingPlan.constantMappings[0].sourceRegisterIndex == 5u &&
        r272MappingPlan.constantMappings[0].normalizedConstantIndex == 5u &&
        r272MappingPlan.constantMappings[0].logicalTargetIndex == 5u &&
        r272MappingPlan.samplerMappings.size() == 1u &&
        !r272MappingPlan.samplerMappings[0].vertexStage &&
        r272MappingPlan.samplerMappings[0].sourceRegisterIndex == 3u &&
        r272MappingPlan.samplerMappings[0].targetSamplerSlot == 3u &&
        r272MappingPlan.constantMappingHash != 0 &&
        r272MappingPlan.samplerMappingHash != 0 &&
        r272MappingPlan.planRevisionHash != 0 &&
        r272MappingPlan.semanticContractHash != 0,
        "R272 derives exact deterministic constant-register and sampler mapping plan");

    auto r272RelativeVs = r272VsRegisterSemantics;
    for (auto& operand : r272RelativeVs.operands)
    {
        if (operand.constantReference)
        {
            operand.relativeAddressing = true;
            break;
        }
    }
    const auto r272RelativePlan =
        derive_programmable_shader_register_mapping_plan(
            r272SourceReceipt, r272RelativeVs, r272PsRegisterSemantics);
    require(
        !r272RelativePlan.constantRegisterMappingExact &&
        !r272RelativePlan.samplerMappingExact &&
        !r272RelativePlan.complete &&
        !r272RelativePlan.exact(),
        "R272 rejects relative-address constant mapping plans fail closed");

    const auto r273SourceMappingHandoff =
        outrun::vr::dx11::
            compose_programmable_shader_source_mapping_handoff(
                r272Pair, r272SourceReceipt, r272MappingPlan);
    require(
        r273SourceMappingHandoff.inputValid &&
        r273SourceMappingHandoff.sourceIdentityExact &&
        r273SourceMappingHandoff.sourceSemanticReceiptExact &&
        r273SourceMappingHandoff.mappingPlanExact &&
        r273SourceMappingHandoff.sourceReceiptIdentityMatches &&
        r273SourceMappingHandoff.mappingPlanIdentityMatches &&
        r273SourceMappingHandoff.constantRegisterMappingExact &&
        r273SourceMappingHandoff.samplerMappingExact &&
        r273SourceMappingHandoff.diagnosticOnly &&
        r273SourceMappingHandoff.boundaryPreserved &&
        r273SourceMappingHandoff.reviewReady &&
        r273SourceMappingHandoff.cacheKey == r272Pair.cacheKey &&
        r273SourceMappingHandoff.pairSemanticHash ==
            r272SourceReceipt.pairSemanticHash &&
        r273SourceMappingHandoff.constantMappingHash ==
            r272MappingPlan.constantMappingHash &&
        r273SourceMappingHandoff.samplerMappingHash ==
            r272MappingPlan.samplerMappingHash &&
        r273SourceMappingHandoff.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_source_mapping_handoff_snapshot(
                r272Pair,
                r272SourceReceipt,
                r272MappingPlan,
                r273SourceMappingHandoff.reviewSnapshotToken),
        "R273 binds exact R272 mapping plan to R239 R271 source identity");

    auto r273StaleMappingPlan = r272MappingPlan;
    r273StaleMappingPlan.cacheKey =
        r272MappingPlan.cacheKey == 1ull
            ? 2ull
            : (r272MappingPlan.cacheKey ^ 1ull);
    const auto r273StaleMappingHandoff =
        outrun::vr::dx11::
            compose_programmable_shader_source_mapping_handoff(
                r272Pair, r272SourceReceipt, r273StaleMappingPlan);
    require(
        r273StaleMappingPlan.exact() &&
        r273StaleMappingHandoff.sourceReceiptIdentityMatches &&
        !r273StaleMappingHandoff.mappingPlanIdentityMatches &&
        !r273StaleMappingHandoff.constantRegisterMappingExact &&
        !r273StaleMappingHandoff.samplerMappingExact &&
        !r273StaleMappingHandoff.reviewReady &&
        r273StaleMappingHandoff.reviewSnapshotToken == 0,
        "R273 rejects detached R272 mapping-plan identity fail closed");

    NativeProgrammableShaderPairCache programmableCache;
    require(
        !programmableCache.ready() &&
        programmableCache.entry_count() == 0,
        "R240 programmable cache starts dormant");
    require(
        programmableCache.initialize(d3d.device) &&
        programmableCache.ready() &&
        programmableCache.device() == d3d.device &&
        programmableCache.entry_count() == 0,
        "R240 programmable cache initializes per device");
    const auto firstCacheGeneration =
        programmableCache.owner_generation();
    require(
        firstCacheGeneration != 0 &&
        programmableCache.cache_for_observation(programmablePair) &&
        programmableCache.entry_count() == 1,
        "R240 programmable pair enters dormant cache");
    const auto programmableReady =
        programmableCache.readiness(d3d.device, programmablePair);
    require(
        programmableReady.inputValid &&
        programmableReady.ownerReady &&
        programmableReady.deviceMatches &&
        programmableReady.identityExact &&
        programmableReady.collisionFree &&
        programmableReady.cached &&
        programmableReady.ready &&
        programmableReady.entryCount == 1 &&
        programmableReady.ownerGeneration == firstCacheGeneration &&
        programmableReady.cacheKey == programmablePair.cacheKey &&
        programmableReady.snapshotToken != 0 &&
        programmableCache.validate_snapshot(
            d3d.device, programmablePair,
            programmableReady.snapshotToken),
        "R240 programmable cache readiness seals exact device identity");

    const auto unreservedProgrammableSlot =
        programmableCache.translation_slot_ownership_readiness(
            d3d.device, programmablePair,
            programmableReady.snapshotToken);
    require(
        unreservedProgrammableSlot.inputValid &&
        unreservedProgrammableSlot.cacheReady &&
        unreservedProgrammableSlot.deviceMatches &&
        unreservedProgrammableSlot.cacheSnapshotMatches &&
        !unreservedProgrammableSlot.slotReserved &&
        !unreservedProgrammableSlot.translationObjectsPresent &&
        !unreservedProgrammableSlot.ownershipReady &&
        unreservedProgrammableSlot.slotGeneration == 0 &&
        unreservedProgrammableSlot.snapshotToken == 0,
        "R241 cached pair starts without a translation object slot");
    require(
        programmableCache.reserve_translation_slot_for_observation(
            d3d.device, programmablePair,
            programmableReady.snapshotToken),
        "R241 reserve translation slot from exact R240 cache snapshot");
    const auto programmableSlot =
        programmableCache.translation_slot_ownership_readiness(
            d3d.device, programmablePair,
            programmableReady.snapshotToken);
    require(
        programmableSlot.inputValid &&
        programmableSlot.cacheReady &&
        programmableSlot.deviceMatches &&
        programmableSlot.cacheSnapshotMatches &&
        programmableSlot.slotReserved &&
        !programmableSlot.translationObjectsPresent &&
        programmableSlot.ownershipReady &&
        programmableSlot.ownerGeneration == firstCacheGeneration &&
        programmableSlot.slotGeneration != 0 &&
        programmableSlot.cacheKey == programmablePair.cacheKey &&
        programmableSlot.cacheSnapshotToken ==
            programmableReady.snapshotToken &&
        programmableSlot.snapshotToken != 0 &&
        programmableCache.validate_translation_slot_snapshot(
            d3d.device, programmablePair,
            programmableReady.snapshotToken,
            programmableSlot.snapshotToken),
        "R241 translation slot ownership seals device and cache generation");
    const auto firstTranslationSlotGeneration =
        programmableSlot.slotGeneration;
    require(
        programmableCache.reserve_translation_slot_for_observation(
            d3d.device, programmablePair,
            programmableReady.snapshotToken) &&
        programmableCache.translation_slot_ownership_readiness(
            d3d.device, programmablePair,
            programmableReady.snapshotToken).snapshotToken ==
            programmableSlot.snapshotToken,
        "R241 duplicate slot reservation is idempotent");

    require(
        programmableCache.cache_for_observation(programmablePair) &&
        programmableCache.entry_count() == 1,
        "R240 duplicate programmable pair dedupes by exact identity");
    const auto duplicateReady =
        programmableCache.readiness(d3d.device, programmablePair);
    require(
        duplicateReady.ready &&
        duplicateReady.snapshotToken == programmableReady.snapshotToken,
        "R240 duplicate programmable pair preserves snapshot identity");

    auto changedPs = programmablePs;
    changedPs.bytecodeHash ^= 1ull;
    const auto changedPair =
        seal_programmable_shader_pair_cache_identity(
            true, false, programmableVs, changedPs);
    require(
        changedPair.exact_identity() &&
        changedPair.cacheKey != programmablePair.cacheKey &&
        programmableCache.cache_for_observation(changedPair) &&
        programmableCache.entry_count() == 2,
        "R240 distinct programmable pair receives a distinct cache entry");
    require(
        programmableCache.validate_snapshot(
            d3d.device, programmablePair,
            programmableReady.snapshotToken),
        "R240 unrelated cache insertion does not stale an exact pair snapshot");

    auto forgedCollision = changedPair;
    forgedCollision.cacheKey = programmablePair.cacheKey;
    require(
        forgedCollision.exact_identity() &&
        !programmableCache.cache_for_observation(forgedCollision),
        "R240 forged cache-key collision fails closed");
    require(
        !programmableCache.reserve_translation_slot_for_observation(
            d3d.device, forgedCollision,
            programmableReady.snapshotToken),
        "R241 forged cache-key collision cannot reserve translation slot");
    const auto collisionReady =
        programmableCache.readiness(d3d.device, forgedCollision);
    require(
        collisionReady.inputValid &&
        collisionReady.ownerReady &&
        collisionReady.deviceMatches &&
        collisionReady.identityExact &&
        !collisionReady.collisionFree &&
        !collisionReady.cached &&
        !collisionReady.ready &&
        collisionReady.snapshotToken == 0,
        "R240 collision readiness cannot authenticate mismatched metadata");

    const auto incompletePair =
        seal_programmable_shader_pair_cache_identity(
            false, false, programmableVs, programmablePs);
    require(
        !incompletePair.exact_identity() &&
        !programmableCache.cache_for_observation(incompletePair),
        "R240 incomplete programmable identity cannot enter cache");

    require(
        !programmableCache.reserve_translation_slot_for_observation(
            d3d.device, incompletePair,
            programmableReady.snapshotToken),
        "R241 incomplete identity cannot reserve translation slot");

    DevicePair secondDevice = create_warp_device();
    require(
        programmableCache.initialize(secondDevice.device) &&
        programmableCache.ready() &&
        programmableCache.device() == secondDevice.device &&
        programmableCache.entry_count() == 0 &&
        programmableCache.owner_generation() != firstCacheGeneration &&
        !programmableCache.validate_snapshot(
            secondDevice.device, programmablePair,
            programmableReady.snapshotToken),
        "R240 device reinitialize clears entries and invalidates prior snapshots");
    require(
        programmableCache.cache_for_observation(programmablePair) &&
        programmableCache.entry_count() == 1 &&
        programmableCache.readiness(
            secondDevice.device, programmablePair).ready,
        "R240 exact pair can be re-cached on the new device generation");
    const auto secondProgrammableReady =
        programmableCache.readiness(
            secondDevice.device, programmablePair);
    require(
        secondProgrammableReady.ready &&
        !programmableCache.validate_translation_slot_snapshot(
            secondDevice.device, programmablePair,
            secondProgrammableReady.snapshotToken,
            programmableSlot.snapshotToken),
        "R241 device generation change invalidates prior slot snapshot");
    const auto secondUnreservedSlot =
        programmableCache.translation_slot_ownership_readiness(
            secondDevice.device, programmablePair,
            secondProgrammableReady.snapshotToken);
    require(
        secondUnreservedSlot.cacheReady &&
        secondUnreservedSlot.cacheSnapshotMatches &&
        !secondUnreservedSlot.slotReserved &&
        !secondUnreservedSlot.ownershipReady,
        "R241 re-cached pair requires a fresh device-generation slot");
    require(
        !programmableCache.reserve_translation_slot_for_observation(
            secondDevice.device, programmablePair,
            programmableReady.snapshotToken) &&
        programmableCache.reserve_translation_slot_for_observation(
            secondDevice.device, programmablePair,
            secondProgrammableReady.snapshotToken),
        "R241 stale cache snapshot rejected before fresh slot reservation");
    const auto secondProgrammableSlot =
        programmableCache.translation_slot_ownership_readiness(
            secondDevice.device, programmablePair,
            secondProgrammableReady.snapshotToken);
    require(
        secondProgrammableSlot.ownershipReady &&
        !secondProgrammableSlot.translationObjectsPresent &&
        secondProgrammableSlot.slotGeneration != 0 &&
        secondProgrammableSlot.slotGeneration !=
            firstTranslationSlotGeneration &&
        secondProgrammableSlot.snapshotToken !=
            programmableSlot.snapshotToken &&
        programmableCache.validate_translation_slot_snapshot(
            secondDevice.device, programmablePair,
            secondProgrammableReady.snapshotToken,
            secondProgrammableSlot.snapshotToken),
        "R241 fresh device generation receives a distinct translation slot");
    secondDevice.context->Release();
    secondDevice.device->Release();

    const auto pointWrapSampler =
        translate_fixed_function_sampler(stages[0]);
    require(
        pointWrapSampler.exact &&
        pointWrapSampler.desc.Filter == D3D11_FILTER_MIN_MAG_MIP_POINT &&
        pointWrapSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_WRAP &&
        pointWrapSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_WRAP &&
        pointWrapSampler.desc.MaxLOD == 0.0f,
        "R98 point/wrap sampler translation");

    NativeFixedFunctionSamplerState samplerOwner;
    require(!samplerOwner.ready(),
            "R98 sampler owner must start dormant");
    require(
        samplerOwner.initialize(d3d.device, stages[0]),
        "R98 sampler owner initialize");
    require(
        samplerOwner.ready() &&
        samplerOwner.device() == d3d.device &&
        samplerOwner.sampler() != nullptr,
        "R98 sampler owner readiness");

    D3D11_SAMPLER_DESC observedSampler{};
    samplerOwner.sampler()->GetDesc(&observedSampler);
    require(
        observedSampler.Filter == D3D11_FILTER_MIN_MAG_MIP_POINT &&
        observedSampler.AddressU == D3D11_TEXTURE_ADDRESS_WRAP &&
        observedSampler.AddressV == D3D11_TEXTURE_ADDRESS_WRAP &&
        observedSampler.MaxLOD == 0.0f,
        "R98 created sampler descriptor");

    auto linearClampStage = stages[0];
    linearClampStage.minFilter = D3DTEXF_LINEAR;
    linearClampStage.magFilter = D3DTEXF_LINEAR;
    linearClampStage.mipFilter = D3DTEXF_LINEAR;
    linearClampStage.addressU = D3DTADDRESS_CLAMP;
    linearClampStage.addressV = D3DTADDRESS_CLAMP;
    const auto linearClampSampler =
        translate_fixed_function_sampler(linearClampStage);
    require(
        linearClampSampler.exact &&
        linearClampSampler.desc.Filter == D3D11_FILTER_MIN_MAG_MIP_LINEAR &&
        linearClampSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_CLAMP &&
        linearClampSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_CLAMP &&
        linearClampSampler.desc.MaxLOD == D3D11_FLOAT32_MAX,
        "R98 linear/clamp sampler translation");
    require(
        samplerOwner.initialize(d3d.device, linearClampStage),
        "R98 sampler owner reinitialize with linear clamp");

    auto borderStage = linearClampStage;
    borderStage.addressU = D3DTADDRESS_BORDER;
    borderStage.addressV = D3DTADDRESS_BORDER;
    borderStage.borderColor = 0x80402010u;
    const auto borderSampler = translate_fixed_function_sampler(borderStage);
    require(
        borderSampler.exact &&
        borderSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_BORDER &&
        borderSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_BORDER &&
        borderSampler.desc.BorderColor[0] == 64.0f / 255.0f &&
        borderSampler.desc.BorderColor[1] == 32.0f / 255.0f &&
        borderSampler.desc.BorderColor[2] == 16.0f / 255.0f &&
        borderSampler.desc.BorderColor[3] == 128.0f / 255.0f,
        "R160 BORDER sampler translation preserves D3D9 ARGB color");
    require(
        samplerOwner.initialize(d3d.device, borderStage),
        "R160 sampler owner accepts exact BORDER state");
    D3D11_SAMPLER_DESC observedBorderSampler{};
    samplerOwner.sampler()->GetDesc(&observedBorderSampler);
    require(
        observedBorderSampler.AddressU == D3D11_TEXTURE_ADDRESS_BORDER &&
        observedBorderSampler.AddressV == D3D11_TEXTURE_ADDRESS_BORDER &&
        observedBorderSampler.BorderColor[0] == 64.0f / 255.0f &&
        observedBorderSampler.BorderColor[1] == 32.0f / 255.0f &&
        observedBorderSampler.BorderColor[2] == 16.0f / 255.0f &&
        observedBorderSampler.BorderColor[3] == 128.0f / 255.0f,
        "R160 created BORDER sampler descriptor preserves ARGB color");

    auto srgbStage = linearClampStage;
    srgbStage.srgbTexture = TRUE;
    require(
        !translate_fixed_function_sampler(srgbStage).exact,
        "sampler sRGB decode must fail closed without sRGB SRV");
    require(
        !samplerOwner.initialize(d3d.device, srgbStage),
        "sampler owner rejects sRGB decode without sRGB SRV");
    require(
        !samplerOwner.ready(),
        "failed sRGB sampler initialize leaves owner dormant");
    require(
        samplerOwner.initialize(d3d.device, linearClampStage),
        "sampler owner recovers after sRGB fail-closed probe");

    auto translatedLodStage = linearClampStage;
    translatedLodStage.mipLodBiasBits = 0x3F000000u;
    translatedLodStage.maxMipLevel = 1u;
    const auto translatedLodSampler =
        translate_fixed_function_sampler(translatedLodStage);
    require(
        translatedLodSampler.exact &&
        translatedLodSampler.desc.MipLODBias == 0.5f &&
        translatedLodSampler.desc.MinLOD == 1.0f &&
        translatedLodSampler.desc.MaxLOD == D3D11_FLOAT32_MAX,
        "sampler LOD bias/MAXMIPLEVEL translation");
    require(
        samplerOwner.initialize(d3d.device, translatedLodStage),
        "sampler owner accepts translated LOD state");
    D3D11_SAMPLER_DESC observedLodSampler{};
    samplerOwner.sampler()->GetDesc(&observedLodSampler);
    require(
        observedLodSampler.MipLODBias == 0.5f &&
        observedLodSampler.MinLOD == 1.0f &&
        observedLodSampler.MaxLOD == D3D11_FLOAT32_MAX,
        "created sampler preserves translated LOD state");

    auto unsupportedLodBiasStage = linearClampStage;
    unsupportedLodBiasStage.mipLodBiasBits = 0x41800000u;
    require(
        !translate_fixed_function_sampler(unsupportedLodBiasStage).exact,
        "out-of-range sampler MIP LOD bias must fail closed");

    auto unsupportedMaxMipStage = linearClampStage;
    unsupportedMaxMipStage.maxMipLevel = D3D11_REQ_MIP_LEVELS;
    require(
        !translate_fixed_function_sampler(unsupportedMaxMipStage).exact,
        "out-of-range sampler MAXMIPLEVEL must fail closed");

    auto unsupportedNoMipLodStage = stages[0];
    unsupportedNoMipLodStage.maxMipLevel = 1u;
    require(
        !translate_fixed_function_sampler(unsupportedNoMipLodStage).exact,
        "no-mip non-default sampler LOD must fail closed");

    auto unsupportedSamplerStage = stages[0];
    unsupportedSamplerStage.minFilter = D3DTEXF_ANISOTROPIC;
    require(
        !translate_fixed_function_sampler(unsupportedSamplerStage).exact,
        "R98 anisotropic sampler translation must fail closed");
    require(
        !samplerOwner.initialize(d3d.device, unsupportedSamplerStage),
        "R98 unsupported sampler owner must fail closed");
    require(
        !samplerOwner.ready(),
        "R98 failed sampler reinitialize must leave owner dormant");
    require(
        samplerOwner.initialize(d3d.device, stages[0]),
        "R98 sampler owner recovery after fail-closed reset");

    D3D11_TEXTURE2D_DESC textureDesc{};
    textureDesc.Width = 4;
    textureDesc.Height = 4;
    textureDesc.MipLevels = 1;
    textureDesc.ArraySize = 1;
    textureDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    textureDesc.SampleDesc.Count = 1;
    textureDesc.Usage = D3D11_USAGE_DEFAULT;
    textureDesc.BindFlags = D3D11_BIND_SHADER_RESOURCE;

    ID3D11Texture2D* fixedFunctionTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &textureDesc, nullptr, &fixedFunctionTexture)) &&
        fixedFunctionTexture != nullptr,
        "R99 translated texture prerequisite");

    NativeFixedFunctionTextureView textureView;
    require(!textureView.ready(),
            "R99 texture view must start dormant");
    require(
        textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture view initialize");
    require(
        textureView.ready() &&
        textureView.device() == d3d.device &&
        textureView.texture() == fixedFunctionTexture &&
        textureView.srv() != nullptr,
        "R99 texture/SRV owner readiness");

    D3D11_SHADER_RESOURCE_VIEW_DESC observedTextureSrv{};
    textureView.srv()->GetDesc(&observedTextureSrv);
    require(
        observedTextureSrv.Format == DXGI_FORMAT_B8G8R8A8_UNORM &&
        observedTextureSrv.ViewDimension == D3D11_SRV_DIMENSION_TEXTURE2D &&
        observedTextureSrv.Texture2D.MostDetailedMip == 0 &&
        observedTextureSrv.Texture2D.MipLevels == 1,
        "R99 created Texture2D SRV descriptor");

    require(
        !textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8B8G8R8, D3DPOOL_DEFAULT, 0),
        "R99 mismatched translated format must fail closed");
    require(!textureView.ready(),
            "R99 format failure must leave owner dormant");

    require(
        !textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, 0),
        "R99 managed source without CPU shadow must fail closed");
    require(!textureView.ready(),
            "R99 managed-source failure must leave owner dormant");

    D3D11_TEXTURE2D_DESC noSrvDesc = textureDesc;
    noSrvDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* noSrvTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &noSrvDesc, nullptr, &noSrvTexture)) &&
        noSrvTexture != nullptr,
        "R99 no-SRV negative texture prerequisite");
    require(
        !textureView.initialize(
            d3d.device, noSrvTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture without shader-resource bind must fail closed");
    require(!textureView.ready(),
            "R99 bind failure must leave owner dormant");

    require(
        textureView.initialize(
            d3d.device, fixedFunctionTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "R99 texture view recovery after fail-closed reset");

    constexpr UINT textureStageSlot = 3;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, textureView),
        "DX11 dormant texture-stage same-device bind");

    ID3D11SamplerState* observedStageSampler = nullptr;
    ID3D11ShaderResourceView* observedStageSrv = nullptr;
    d3d.context->PSGetSamplers(
        textureStageSlot, 1, &observedStageSampler);
    d3d.context->PSGetShaderResources(
        textureStageSlot, 1, &observedStageSrv);
    require(
        observedStageSampler == samplerOwner.sampler() &&
        observedStageSrv == textureView.srv(),
        "DX11 dormant texture-stage binding preserves sampler/SRV identity");

    const auto textureStageBindingReady =
        outrun::vr::dx11::observe_fixed_function_texture_stage_binding(
            d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        textureStageBindingReady.inputValid &&
        textureStageBindingReady.slotValid &&
        textureStageBindingReady.ownersReady &&
        textureStageBindingReady.devicesMatch &&
        textureStageBindingReady.contextMatches &&
        textureStageBindingReady.boundExact &&
        textureStageBindingReady.ready &&
        textureStageBindingReady.slot == textureStageSlot &&
        textureStageBindingReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            d3d.context, textureStageSlot, samplerOwner, textureView,
            textureStageBindingReady.snapshotToken),
        "R132 texture-stage binding issues exact sampler/SRV snapshot");

    // R152: reject a same-device deferred context even when it contains
    // matching PS sampler/SRV recordings. Preserve the immediate receipt.
    ID3D11DeviceContext* r152DeferredContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(0, &r152DeferredContext)) &&
        r152DeferredContext != nullptr &&
        r152DeferredContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R152 WARP same-device deferred texture-stage prerequisite");
    require(
        !bind_fixed_function_texture_stage_for_observation(
            r152DeferredContext, textureStageSlot, samplerOwner, textureView),
        "R152 deferred texture-stage live bind fails closed");
    ID3D11SamplerState* r152RecordedSampler = samplerOwner.sampler();
    ID3D11ShaderResourceView* r152RecordedSrv = textureView.srv();
    r152DeferredContext->PSSetSamplers(
        textureStageSlot, 1, &r152RecordedSampler);
    r152DeferredContext->PSSetShaderResources(
        textureStageSlot, 1, &r152RecordedSrv);
    const auto r152DeferredReceipt =
        outrun::vr::dx11::observe_fixed_function_texture_stage_binding(
            r152DeferredContext, textureStageSlot, samplerOwner, textureView);
    require(
        !r152DeferredReceipt.inputValid &&
        !r152DeferredReceipt.ready &&
        r152DeferredReceipt.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            r152DeferredContext, textureStageSlot, samplerOwner, textureView,
            textureStageBindingReady.snapshotToken) &&
        outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            d3d.context, textureStageSlot, samplerOwner, textureView,
            textureStageBindingReady.snapshotToken),
        "R152 recorded deferred PS bindings cannot forge immediate live receipt");
    r152DeferredContext->Release();
    if (observedStageSampler)
        observedStageSampler->Release();
    if (observedStageSrv)
        observedStageSrv->Release();

    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT,
            samplerOwner, textureView),
        "DX11 dormant texture-stage sampler slot overflow fails closed");
    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT,
            samplerOwner, textureView),
        "DX11 dormant texture-stage SRV slot overflow fails closed");

    DevicePair textureStageOtherDevice = create_warp_device();
    require(
        !bind_fixed_function_texture_stage_for_observation(
            textureStageOtherDevice.context, 0, samplerOwner, textureView),
        "DX11 dormant texture-stage foreign context fails closed");

    NativeFixedFunctionSamplerState foreignStageSampler;
    require(
        foreignStageSampler.initialize(
            textureStageOtherDevice.device, stages[0]),
        "DX11 dormant texture-stage foreign sampler prerequisite");
    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, 0, foreignStageSampler, textureView),
        "DX11 dormant texture-stage cross-device owners fail closed");
    foreignStageSampler.shutdown();
    textureStageOtherDevice.context->Release();
    textureStageOtherDevice.device->Release();

    ID3D11SamplerState* nullSampler = nullptr;
    ID3D11ShaderResourceView* nullSrv = nullptr;
    d3d.context->PSSetSamplers(
        textureStageSlot, 1, &nullSampler);
    d3d.context->PSSetShaderResources(
        textureStageSlot, 1, &nullSrv);

    D3D11_TEXTURE2D_DESC hazardTextureDesc = textureDesc;
    hazardTextureDesc.BindFlags =
        D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* hazardTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &hazardTextureDesc, nullptr, &hazardTexture)) &&
        hazardTexture != nullptr,
        "DX11 dormant texture-stage output hazard texture prerequisite");

    NativeFixedFunctionTextureView hazardTextureView;
    require(
        hazardTextureView.initialize(
            d3d.device, hazardTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, 0),
        "DX11 dormant texture-stage output hazard view prerequisite");

    ID3D11RenderTargetView* hazardRtv = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateRenderTargetView(
            hazardTexture, nullptr, &hazardRtv)) &&
        hazardRtv != nullptr,
        "DX11 dormant texture-stage output hazard RTV prerequisite");
    d3d.context->OMSetRenderTargets(1, &hazardRtv, nullptr);

    require(
        !bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, hazardTextureView),
        "DX11 dormant texture-stage output hazard fails closed");

    ID3D11SamplerState* hazardBoundSampler = nullptr;
    ID3D11ShaderResourceView* hazardBoundSrv = nullptr;
    d3d.context->PSGetSamplers(
        textureStageSlot, 1, &hazardBoundSampler);
    d3d.context->PSGetShaderResources(
        textureStageSlot, 1, &hazardBoundSrv);
    require(
        hazardBoundSampler == nullptr && hazardBoundSrv == nullptr,
        "DX11 dormant texture-stage failed bind clears partial state");
    if (hazardBoundSampler)
        hazardBoundSampler->Release();
    if (hazardBoundSrv)
        hazardBoundSrv->Release();

    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    hazardRtv->Release();
    hazardTextureView.shutdown();
    hazardTexture->Release();

    const auto managedVertexWritePlan = translate_buffer_mutation(
        ResourceRole::Vertex, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY, 0);
    require(
        managedVertexWritePlan.planExact &&
        managedVertexWritePlan.kind ==
            BufferMutationUpdateKind::ManagedCpuShadowWrite &&
        managedVertexWritePlan.requiresCpuShadow,
        "R121 managed VB write is an exact CPU-shadow mutation plan");

    const auto managedIndexReadPlan = translate_buffer_mutation(
        ResourceRole::Index, D3DPOOL_MANAGED, 0, D3DLOCK_READONLY);
    require(
        managedIndexReadPlan.planExact &&
        managedIndexReadPlan.kind ==
            BufferMutationUpdateKind::ManagedCpuShadowRead &&
        managedIndexReadPlan.requiresCpuShadow,
        "R121 managed IB read is an exact CPU-shadow mutation plan");

    const auto managedDiscardPlan = translate_buffer_mutation(
        ResourceRole::Vertex, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY,
        D3DLOCK_DISCARD);
    require(
        !managedDiscardPlan.planExact &&
        managedDiscardPlan.kind == BufferMutationUpdateKind::Unsupported,
        "R121 managed DISCARD remains fail-closed");

    const auto managedNoOverwritePlan = translate_buffer_mutation(
        ResourceRole::Index, D3DPOOL_MANAGED, D3DUSAGE_WRITEONLY,
        D3DLOCK_NOOVERWRITE);
    require(
        !managedNoOverwritePlan.planExact &&
        managedNoOverwritePlan.kind == BufferMutationUpdateKind::Unsupported,
        "R121 managed NOOVERWRITE remains fail-closed");

    const auto dynamicDiscardTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_DISCARD, true);
    require(
        dynamicDiscardTexture.planExact &&
        dynamicDiscardTexture.kind ==
            TextureMutationUpdateKind::DynamicMapWriteDiscard &&
        dynamicDiscardTexture.mapType == D3D11_MAP_WRITE_DISCARD &&
        dynamicDiscardTexture.requiresFullSubresource &&
        !dynamicDiscardTexture.requiresCpuShadow,
        "R100 full dynamic texture discard maps exactly");

    const auto partialDiscardTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_DISCARD, false);
    require(
        !partialDiscardTexture.planExact &&
        partialDiscardTexture.kind == TextureMutationUpdateKind::Unsupported &&
        partialDiscardTexture.requiresFullSubresource,
        "R100 partial dynamic texture discard must fail closed");

    const auto plainDynamicTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, 0, true);
    require(
        !plainDynamicTexture.planExact &&
        plainDynamicTexture.kind == TextureMutationUpdateKind::Unsupported &&
        plainDynamicTexture.requiresFullSubresource,
        "R100 plain dynamic texture write must fail closed");

    const auto noOverwriteTexture = translate_texture_mutation(
        D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC, D3DLOCK_NOOVERWRITE, true);
    require(
        !noOverwriteTexture.planExact &&
        noOverwriteTexture.kind == TextureMutationUpdateKind::Unsupported,
        "R100 texture NOOVERWRITE must fail closed");

    const auto managedTextureWrite = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, 0, true);
    require(
        !managedTextureWrite.planExact &&
        managedTextureWrite.kind ==
            TextureMutationUpdateKind::ManagedCpuShadowWrite &&
        managedTextureWrite.requiresCpuShadow,
        "R100 managed texture write requires CPU shadow");

    const auto managedTextureRead = translate_texture_mutation(
        D3DPOOL_MANAGED, 0, D3DLOCK_READONLY, true);
    require(
        !managedTextureRead.planExact &&
        managedTextureRead.kind ==
            TextureMutationUpdateKind::ManagedCpuShadowRead &&
        managedTextureRead.requiresCpuShadow,
        "R100 managed texture read requires CPU shadow");

    D3D11_TEXTURE2D_DESC dynamicTextureDesc = textureDesc;
    dynamicTextureDesc.Usage = D3D11_USAGE_DYNAMIC;
    dynamicTextureDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

    ID3D11Texture2D* dynamicTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &dynamicTextureDesc, nullptr, &dynamicTexture)) &&
        dynamicTexture != nullptr,
        "R101 dynamic texture prerequisite");

    NativeFixedFunctionTextureView dynamicTextureView;
    require(
        dynamicTextureView.initialize(
            d3d.device, dynamicTexture,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_DYNAMIC),
        "R101 dynamic texture view initialize");
    require(
        dynamicTextureView.ready() &&
        !dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 0,
        "R101 dynamic texture content starts uninitialized");

    std::array<unsigned char, 80> dynamicSource{};
    constexpr UINT dynamicSourcePitch = 20;
    constexpr UINT dynamicRowBytes = 16;
    constexpr UINT dynamicRows = 4;
    for (UINT row = 0; row < dynamicRows; ++row) {
        for (UINT column = 0; column < dynamicRowBytes; ++column) {
            dynamicSource[static_cast<std::size_t>(row) * dynamicSourcePitch + column] =
                static_cast<unsigned char>(row * 32 + column + 1);
        }
    }

    require(
        !dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicRowBytes - 1, dynamicRows),
        "R101 short source row pitch must fail closed");
    require(
        !dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows - 1),
        "R101 partial source rows must fail closed");
    require(
        dynamicTextureView.upload_generation() == 0 &&
        !dynamicTextureView.content_ready(),
        "R101 rejected uploads must not advance content generation");

    DevicePair textureOtherDevice = create_warp_device();
    require(
        !dynamicTextureView.upload_full_discard(
            textureOtherDevice.context,
            dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 foreign device context must fail closed");
    require(
        dynamicTextureView.upload_generation() == 0,
        "R101 foreign-context rejection must preserve generation");

    // R153: a same-device deferred context may record DISCARD uploads, but
    // cannot prove that Map/Unmap made texture content live immediately.
    ID3D11DeviceContext* r153DeferredContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(0, &r153DeferredContext)) &&
        r153DeferredContext != nullptr &&
        r153DeferredContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R153 WARP same-device deferred texture upload prerequisite");
    require(
        !dynamicTextureView.upload_full_discard(
            r153DeferredContext, dynamicSource.data(),
            dynamicSourcePitch, dynamicRows) &&
        dynamicTextureView.upload_generation() == 0 &&
        !dynamicTextureView.content_ready(),
        "R153 deferred Map/Unmap cannot forge a live texture upload receipt");

    require(
        dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 full dynamic texture discard upload");
    require(
        dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 1,
        "R101 successful upload advances content generation");
    require(
        !dynamicTextureView.upload_full_discard(
            r153DeferredContext, dynamicSource.data(),
            dynamicSourcePitch, dynamicRows) &&
        dynamicTextureView.upload_generation() == 1 &&
        dynamicTextureView.content_ready(),
        "R153 deferred upload cannot advance or erase an immediate receipt");
    r153DeferredContext->Release();

    D3D11_TEXTURE2D_DESC stagingDesc = dynamicTextureDesc;
    stagingDesc.Usage = D3D11_USAGE_STAGING;
    stagingDesc.BindFlags = 0;
    stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;

    ID3D11Texture2D* stagingTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &stagingDesc, nullptr, &stagingTexture)) &&
        stagingTexture != nullptr,
        "R101 staging readback prerequisite");
    d3d.context->CopyResource(stagingTexture, dynamicTexture);

    D3D11_MAPPED_SUBRESOURCE stagingMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            stagingTexture, 0, D3D11_MAP_READ, 0, &stagingMap)) &&
        stagingMap.pData != nullptr &&
        stagingMap.RowPitch >= dynamicRowBytes,
        "R101 staging readback map");
    for (UINT row = 0; row < dynamicRows; ++row) {
        const auto* observed =
            static_cast<const unsigned char*>(stagingMap.pData) +
            static_cast<std::size_t>(row) * stagingMap.RowPitch;
        const auto* expected =
            dynamicSource.data() +
            static_cast<std::size_t>(row) * dynamicSourcePitch;
        require(
            std::memcmp(observed, expected, dynamicRowBytes) == 0,
            "R101 uploaded texture bytes must match source rows");
    }
    d3d.context->Unmap(stagingTexture, 0);

    dynamicSource[0] ^= 0x5a;
    require(
        dynamicTextureView.upload_full_discard(
            d3d.context, dynamicSource.data(), dynamicSourcePitch, dynamicRows),
        "R101 second full-discard upload");
    require(
        dynamicTextureView.upload_generation() == 2,
        "R101 upload generation must advance monotonically");

    NativeManagedBufferShadow managedVertexBuffer;
    require(
        managedVertexBuffer.initialize(
            ResourceRole::Vertex, 256, D3DUSAGE_WRITEONLY),
        "R113 managed vertex-buffer shadow initialize");
    require(
        managedVertexBuffer.ready() &&
        !managedVertexBuffer.shadow_valid() &&
        !managedVertexBuffer.mirror_ready(),
        "R113 managed vertex-buffer shadow starts content-invalid");

    std::array<unsigned char, 256> managedVertexBytes{};
    for (std::size_t index = 0; index < managedVertexBytes.size(); ++index)
        managedVertexBytes[index] =
            static_cast<unsigned char>(0x20u + index);

    require(
        !managedVertexBuffer.write_range(
            4, managedVertexBytes.data() + 4, 8),
        "R113 first managed buffer write must cover the full resource");
    require(
        managedVertexBuffer.write_range(
            0, managedVertexBytes.data(),
            static_cast<UINT>(managedVertexBytes.size())) &&
        managedVertexBuffer.shadow_valid() &&
        managedVertexBuffer.shadow_version() == 1,
        "R113 full managed vertex-buffer write establishes CPU shadow");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 managed vertex-buffer mirror upload");

    const auto managedVertexReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexReady.inputValid &&
        managedVertexReady.shadowValid &&
        managedVertexReady.resourcesOwned &&
        managedVertexReady.lifetimeCurrent &&
        managedVertexReady.deviceMatches &&
        managedVertexReady.descriptorExact &&
        managedVertexReady.mutationPlanExact &&
        managedVertexReady.ready &&
        managedVertexReady.role == ResourceRole::Vertex &&
        managedVertexReady.deviceGeneration == 1 &&
        managedVertexReady.shadowVersion == 1 &&
        managedVertexReady.mirrorGeneration == 1 &&
        managedVertexReady.mirrorShadowVersion == 1 &&
        managedVertexReady.mirrorInstanceGeneration == 1 &&
        managedVertexReady.snapshotToken != 0 &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexReady.snapshotToken),
        "R119 managed vertex-buffer mirror issues exact readiness snapshot");
    require(
        managedVertexReady.mutationPlanExact,
        "R127 managed-buffer readiness consumes exact mutation plan");
    const auto managedVertexInitialToken = managedVertexReady.snapshotToken;

    DevicePair managedBufferOtherDevice = create_warp_device();
    const auto managedVertexForeignReady =
        managedVertexBuffer.mirror_readiness(managedBufferOtherDevice.device);
    require(
        managedVertexForeignReady.inputValid &&
        managedVertexForeignReady.shadowValid &&
        managedVertexForeignReady.resourcesOwned &&
        managedVertexForeignReady.lifetimeCurrent &&
        !managedVertexForeignReady.deviceMatches &&
        !managedVertexForeignReady.descriptorExact &&
        !managedVertexForeignReady.ready &&
        managedVertexForeignReady.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            managedBufferOtherDevice.device, managedVertexInitialToken),
        "R119 foreign device cannot claim managed-buffer readiness");
    managedBufferOtherDevice.context->Release();
    managedBufferOtherDevice.device->Release();

    D3D11_BUFFER_DESC managedVertexDesc{};
    managedVertexBuffer.mirror_buffer()->GetDesc(&managedVertexDesc);
    require(
        managedVertexDesc.ByteWidth == managedVertexBytes.size() &&
        managedVertexDesc.Usage == D3D11_USAGE_DEFAULT &&
        managedVertexDesc.BindFlags == D3D11_BIND_VERTEX_BUFFER &&
        managedVertexDesc.CPUAccessFlags == 0,
        "R113 managed vertex-buffer descriptor contract");

    D3D11_BUFFER_DESC managedVertexStagingDesc = managedVertexDesc;
    managedVertexStagingDesc.Usage = D3D11_USAGE_STAGING;
    managedVertexStagingDesc.BindFlags = 0;
    managedVertexStagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Buffer* managedVertexStaging = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateBuffer(
            &managedVertexStagingDesc, nullptr, &managedVertexStaging)) &&
        managedVertexStaging != nullptr,
        "R113 managed vertex-buffer staging prerequisite");
    d3d.context->CopyResource(
        managedVertexStaging, managedVertexBuffer.mirror_buffer());
    D3D11_MAPPED_SUBRESOURCE managedVertexMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            managedVertexStaging, 0, D3D11_MAP_READ, 0, &managedVertexMap)) &&
        managedVertexMap.pData != nullptr &&
        std::memcmp(
            managedVertexMap.pData,
            managedVertexBytes.data(),
            managedVertexBytes.size()) == 0,
        "R113 managed vertex-buffer mirror bytes");
    d3d.context->Unmap(managedVertexStaging, 0);
    managedVertexStaging->Release();

    const unsigned char managedVertexPatch[] = {0xe1, 0xe2, 0xe3, 0xe4};
    require(
        managedVertexBuffer.write_range(
            8, managedVertexPatch,
            static_cast<UINT>(sizeof(managedVertexPatch))) &&
        managedVertexBuffer.shadow_version() == 2 &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 partial managed buffer update invalidates stale mirror");
    const auto managedVertexAfterWrite =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterWrite.inputValid &&
        managedVertexAfterWrite.shadowValid &&
        !managedVertexAfterWrite.resourcesOwned &&
        !managedVertexAfterWrite.lifetimeCurrent &&
        !managedVertexAfterWrite.ready &&
        managedVertexAfterWrite.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexInitialToken),
        "R119 shadow mutation invalidates managed-buffer snapshot");
    require(
        !managedVertexBuffer.write_range(
            static_cast<UINT>(managedVertexBytes.size() - 1u),
            managedVertexPatch,
            static_cast<UINT>(sizeof(managedVertexPatch))),
        "R113 out-of-range managed buffer write must fail closed");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device),
        "R113 managed vertex-buffer mirror recreation");
    const auto managedVertexAfterWriteRecreate =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterWriteRecreate.ready &&
        managedVertexAfterWriteRecreate.shadowVersion == 2 &&
        managedVertexAfterWriteRecreate.mirrorShadowVersion == 2 &&
        managedVertexAfterWriteRecreate.mirrorInstanceGeneration == 2 &&
        managedVertexAfterWriteRecreate.snapshotToken != 0 &&
        managedVertexAfterWriteRecreate.snapshotToken != managedVertexInitialToken &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexAfterWriteRecreate.snapshotToken),
        "R119 managed-buffer recreation issues fresh snapshot");
    const auto managedVertexPreResetToken =
        managedVertexAfterWriteRecreate.snapshotToken;

    managedVertexBuffer.observe_device_reset();
    require(
        managedVertexBuffer.device_generation() == 2 &&
        managedVertexBuffer.shadow_valid() &&
        managedVertexBuffer.shadow_version() == 2 &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 Reset preserves managed buffer CPU shadow only");
    const auto managedVertexAfterReset =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexAfterReset.inputValid &&
        managedVertexAfterReset.shadowValid &&
        !managedVertexAfterReset.resourcesOwned &&
        !managedVertexAfterReset.lifetimeCurrent &&
        !managedVertexAfterReset.ready &&
        managedVertexAfterReset.snapshotToken == 0 &&
        !managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexPreResetToken),
        "R119 Reset invalidates managed-buffer readiness snapshot");
    require(
        managedVertexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedVertexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 post-Reset managed vertex-buffer mirror recreation");
    const auto managedVertexPostResetReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    require(
        managedVertexPostResetReady.ready &&
        managedVertexPostResetReady.deviceGeneration == 2 &&
        managedVertexPostResetReady.shadowVersion == 2 &&
        managedVertexPostResetReady.mirrorGeneration == 2 &&
        managedVertexPostResetReady.mirrorShadowVersion == 2 &&
        managedVertexPostResetReady.mirrorInstanceGeneration == 3 &&
        managedVertexPostResetReady.snapshotToken != 0 &&
        managedVertexPostResetReady.snapshotToken != managedVertexPreResetToken &&
        managedVertexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedVertexPostResetReady.snapshotToken),
        "R119 post-Reset managed-buffer mirror issues generation-current snapshot");

    NativeManagedBufferShadow managedIndexBuffer;
    std::array<unsigned short, 6> managedIndexBytes{0, 1, 2, 2, 3, 0};
    require(
        managedIndexBuffer.initialize(
            ResourceRole::Index,
            static_cast<UINT>(sizeof(managedIndexBytes)),
            0) &&
        managedIndexBuffer.write_range(
            0, managedIndexBytes.data(),
            static_cast<UINT>(sizeof(managedIndexBytes))) &&
        managedIndexBuffer.recreate_and_upload_mirror(d3d.device) &&
        managedIndexBuffer.mirror_descriptor_exact(d3d.device),
        "R113 managed index-buffer mirror upload");
    D3D11_BUFFER_DESC managedIndexDesc{};
    managedIndexBuffer.mirror_buffer()->GetDesc(&managedIndexDesc);
    require(
        managedIndexDesc.BindFlags == D3D11_BIND_INDEX_BUFFER,
        "R113 managed index-buffer bind contract");
    const auto managedIndexReady =
        managedIndexBuffer.mirror_readiness(d3d.device);
    require(
        managedIndexReady.ready &&
        managedIndexReady.role == ResourceRole::Index &&
        managedIndexReady.snapshotToken != 0 &&
        managedIndexReady.mirrorInstanceGeneration == 1 &&
        managedIndexBuffer.validate_mirror_readiness_snapshot(
            d3d.device, managedIndexReady.snapshotToken),
        "R119 managed index-buffer mirror issues exact readiness snapshot");

    const auto indexedGeometryReady =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, true, managedIndexReady,
            D3DPT_TRIANGLELIST);
    require(
        indexedGeometryReady.inputValid &&
        indexedGeometryReady.vertexBufferReady &&
        indexedGeometryReady.indexBufferRequired &&
        indexedGeometryReady.indexBufferReady &&
        indexedGeometryReady.topologyReady &&
        indexedGeometryReady.componentSnapshotsPresent &&
        indexedGeometryReady.ready &&
        indexedGeometryReady.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedGeometryReady.vertexBufferSnapshotToken ==
            managedVertexPostResetReady.snapshotToken &&
        indexedGeometryReady.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedGeometryReady.snapshotToken != 0 &&
        validate_fixed_function_geometry_snapshot(
            managedVertexPostResetReady, true, managedIndexReady,
            D3DPT_TRIANGLELIST, indexedGeometryReady.snapshotToken),
        "R122 indexed geometry seals VB IB and topology snapshots");

    const auto nonIndexedGeometryReady =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, false, managedIndexReady,
            D3DPT_TRIANGLESTRIP);
    require(
        nonIndexedGeometryReady.ready &&
        !nonIndexedGeometryReady.indexBufferRequired &&
        nonIndexedGeometryReady.indexBufferReady &&
        nonIndexedGeometryReady.indexBufferSnapshotToken == 0 &&
        nonIndexedGeometryReady.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP,
        "R122 non-indexed geometry ignores unrelated IB identity");

    constexpr UINT geometryVertexStride = 24u;
    constexpr UINT geometryVertexOffset = 0u;
    constexpr UINT geometryIndexOffset = 0u;
    require(
        outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                indexedGeometryReady) &&
        outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                nonIndexedGeometryReady),
        "R139 direct geometry readiness seals copied struct identity");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R139 direct indexed geometry binds exact IA state");
    const auto indexedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        indexedGeometryBinding.inputValid &&
        indexedGeometryBinding.geometryReady &&
        indexedGeometryBinding.contextMatches &&
        indexedGeometryBinding.vertexBufferCurrent &&
        indexedGeometryBinding.indexBufferCurrent &&
        indexedGeometryBinding.vertexBufferBoundExact &&
        indexedGeometryBinding.indexBufferBoundExact &&
        indexedGeometryBinding.topologyBoundExact &&
        indexedGeometryBinding.ready &&
        indexedGeometryBinding.indexed &&
        indexedGeometryBinding.geometrySnapshotToken ==
            indexedGeometryReady.snapshotToken &&
        indexedGeometryBinding.vertexBufferSnapshotToken ==
            managedVertexPostResetReady.snapshotToken &&
        indexedGeometryBinding.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedGeometryBinding.vertexStride == geometryVertexStride &&
        indexedGeometryBinding.indexFormat == DXGI_FORMAT_R16_UINT &&
        indexedGeometryBinding.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedGeometryBinding.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 live IA observer seals VB IB stride offsets and topology");

    d3d.context->IASetPrimitiveTopology(
        D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto driftedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        driftedGeometryBinding.inputValid &&
        driftedGeometryBinding.geometryReady &&
        driftedGeometryBinding.vertexBufferBoundExact &&
        driftedGeometryBinding.indexBufferBoundExact &&
        !driftedGeometryBinding.topologyBoundExact &&
        !driftedGeometryBinding.ready &&
        driftedGeometryBinding.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 live IA topology drift invalidates geometry binding snapshot");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            nullptr, DXGI_FORMAT_UNKNOWN, 0),
        "R139 non-indexed geometry clears unrelated IA index binding");
    const auto nonIndexedGeometryBinding =
        outrun::vr::dx11::observe_fixed_function_geometry_binding(
            d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            nullptr, DXGI_FORMAT_UNKNOWN, 0);
    require(
        nonIndexedGeometryBinding.ready &&
        !nonIndexedGeometryBinding.indexed &&
        nonIndexedGeometryBinding.indexBufferCurrent &&
        nonIndexedGeometryBinding.indexBufferBoundExact &&
        nonIndexedGeometryBinding.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP &&
        nonIndexedGeometryBinding.snapshotToken != 0,
        "R139 non-indexed live IA binding is exact and index-free");

    auto forgedDirectGeometry = indexedGeometryReady;
    forgedDirectGeometry.topology = D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP;
    require(
        !outrun::vr::dx11::
            validate_fixed_function_direct_geometry_readiness_integrity(
                forgedDirectGeometry) &&
        !outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, forgedDirectGeometry, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R139 copied geometry topology drift fails closed before IA mutation");
    require(
        !outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R8_UINT, geometryIndexOffset),
        "R139 unsupported IA index format fails closed");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R139 exact indexed IA binding restores deterministic snapshot");

    auto wrongVertexRole = managedVertexPostResetReady;
    wrongVertexRole.role = ResourceRole::Index;
    auto missingIndexReady = managedIndexReady;
    missingIndexReady.ready = false;
    missingIndexReady.snapshotToken = 0;
    const auto wrongRoleGeometry =
        compose_fixed_function_geometry_readiness(
            wrongVertexRole, true, managedIndexReady, D3DPT_TRIANGLELIST);
    const auto missingIndexGeometry =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, true, missingIndexReady,
            D3DPT_TRIANGLELIST);
    const auto fanGeometry =
        compose_fixed_function_geometry_readiness(
            managedVertexPostResetReady, false, managedIndexReady,
            D3DPT_TRIANGLEFAN);
    require(
        !wrongRoleGeometry.inputValid &&
        !wrongRoleGeometry.ready &&
        wrongRoleGeometry.snapshotToken == 0 &&
        !missingIndexGeometry.ready &&
        missingIndexGeometry.snapshotToken == 0 &&
        !fanGeometry.topologyReady &&
        !fanGeometry.ready &&
        fanGeometry.snapshotToken == 0,
        "R122 geometry fails closed on role IB or unowned fan expansion");

    NativeTriangleFanIndexBufferReadiness generatedFanReady{};
    generatedFanReady.resourcesOwned = true;
    generatedFanReady.deviceMatches = true;
    generatedFanReady.descriptorExact = true;
    generatedFanReady.sourceProvenanceExact = true;
    generatedFanReady.indexedSource = false;
    generatedFanReady.ready = true;
    generatedFanReady.indexCount = 9;
    generatedFanReady.primitiveCount = 3;
    generatedFanReady.baseVertex = 7;
    generatedFanReady.generation = 1;
    generatedFanReady.contentHash = 0xd8928727f6a47b73ull;
    generatedFanReady.snapshotToken = 0x1280F11ull;

    const auto expandedNonIndexedFan =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, generatedFanReady, 3u, 7u);
    require(
        expandedNonIndexedFan.inputValid &&
        expandedNonIndexedFan.vertexBufferReady &&
        !expandedNonIndexedFan.indexBufferRequired &&
        expandedNonIndexedFan.indexBufferReady &&
        expandedNonIndexedFan.generatedIndexBufferRequired &&
        expandedNonIndexedFan.generatedIndexBufferReady &&
        expandedNonIndexedFan.generatedIndexBufferMatchesDraw &&
        expandedNonIndexedFan.topologyReady &&
        expandedNonIndexedFan.componentSnapshotsPresent &&
        expandedNonIndexedFan.ready &&
        expandedNonIndexedFan.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        expandedNonIndexedFan.indexBufferSnapshotToken == 0 &&
        expandedNonIndexedFan.generatedIndexBufferSnapshotToken ==
            generatedFanReady.snapshotToken &&
        expandedNonIndexedFan.snapshotToken != 0 &&
        validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
            managedVertexPostResetReady, generatedFanReady, 3u, 7u,
            expandedNonIndexedFan.snapshotToken),
        "R128 generated IB makes exact non-indexed fan geometry ready");

    auto mismatchedGeneratedFan = generatedFanReady;
    mismatchedGeneratedFan.contentHash ^= 0x1u;
    const auto mismatchedFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, mismatchedGeneratedFan, 3u, 7u);
    auto staleGeneratedFan = generatedFanReady;
    staleGeneratedFan.snapshotToken ^= 0x100000001b3ull;
    const auto staleFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, staleGeneratedFan, 3u, 7u);
    require(
        mismatchedFanGeometry.generatedIndexBufferReady &&
        !mismatchedFanGeometry.generatedIndexBufferMatchesDraw &&
        !mismatchedFanGeometry.ready &&
        mismatchedFanGeometry.snapshotToken == 0 &&
        staleFanGeometry.ready &&
        staleFanGeometry.snapshotToken !=
            expandedNonIndexedFan.snapshotToken &&
        !validate_fixed_function_nonindexed_triangle_fan_geometry_snapshot(
            managedVertexPostResetReady, staleGeneratedFan, 3u, 7u,
            expandedNonIndexedFan.snapshotToken),
        "R128 fan geometry rejects mismatched or stale generated IB identity");

    auto wrongFanProvenance = generatedFanReady;
    wrongFanProvenance.baseVertex = 8u;
    const auto wrongProvenanceFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, wrongFanProvenance, 3u, 7u);
    require(
        wrongProvenanceFanGeometry.generatedIndexBufferReady &&
        !wrongProvenanceFanGeometry.generatedIndexBufferMatchesDraw &&
        !wrongProvenanceFanGeometry.ready &&
        wrongProvenanceFanGeometry.snapshotToken == 0,
        "R142 non-indexed fan geometry rejects owner provenance drift");

    auto overflowGeneratedFan = generatedFanReady;
    overflowGeneratedFan.indexCount = 3;
    const auto overflowFanGeometry =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            managedVertexPostResetReady, overflowGeneratedFan, 1u, ~0u);
    require(
        !overflowFanGeometry.inputValid &&
        overflowFanGeometry.vertexBufferReady &&
        overflowFanGeometry.generatedIndexBufferReady &&
        !overflowFanGeometry.generatedIndexBufferMatchesDraw &&
        overflowFanGeometry.topologyReady &&
        !overflowFanGeometry.ready &&
        overflowFanGeometry.snapshotToken == 0,
        "R129 non-indexed fan base-vertex overflow fails closed");

    auto indexedGeneratedFanReady = generatedFanReady;
    indexedGeneratedFanReady.sourceProvenanceExact = true;
    indexedGeneratedFanReady.indexedSource = true;
    indexedGeneratedFanReady.primitiveCount = 3u;
    indexedGeneratedFanReady.sourceIndexFormat = D3DFMT_INDEX16;
    indexedGeneratedFanReady.sourceStartIndex = 2u;
    indexedGeneratedFanReady.sourceIndexCount = 8u;
    indexedGeneratedFanReady.sourceIndexSnapshotToken =
        managedIndexReady.snapshotToken;
    indexedGeneratedFanReady.snapshotToken = 0x1430F11ull;

    const auto indexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        indexedFanGeometry.inputValid &&
        indexedFanGeometry.vertexBufferReady &&
        indexedFanGeometry.indexBufferRequired &&
        indexedFanGeometry.indexBufferReady &&
        indexedFanGeometry.generatedIndexBufferRequired &&
        indexedFanGeometry.generatedIndexBufferReady &&
        indexedFanGeometry.generatedIndexBufferMatchesDraw &&
        indexedFanGeometry.topologyReady &&
        indexedFanGeometry.componentSnapshotsPresent &&
        indexedFanGeometry.ready &&
        indexedFanGeometry.topology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        indexedFanGeometry.indexBufferSnapshotToken ==
            managedIndexReady.snapshotToken &&
        indexedFanGeometry.generatedIndexBufferSnapshotToken ==
            indexedGeneratedFanReady.snapshotToken &&
        indexedFanGeometry.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u,
                indexedFanGeometry.snapshotToken),
        "R143 indexed fan geometry seals current source-index mirror provenance");

    auto staleIndexedFan = indexedGeneratedFanReady;
    staleIndexedFan.sourceIndexSnapshotToken ^= 0x100000001b3ull;
    staleIndexedFan.snapshotToken ^= 0x100000001b3ull;
    const auto staleIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                staleIndexedFan, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        staleIndexedFanGeometry.generatedIndexBufferReady &&
        !staleIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !staleIndexedFanGeometry.ready &&
        staleIndexedFanGeometry.snapshotToken == 0,
        "R143 indexed fan geometry rejects stale source-index snapshot");

    const auto formatDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX32, 2u, 8u);
    const auto startDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 3u, 8u);
    const auto countDriftIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 7u);
    require(
        !formatDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !formatDriftIndexedFanGeometry.ready &&
        !startDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !startDriftIndexedFanGeometry.ready &&
        !countDriftIndexedFanGeometry.generatedIndexBufferMatchesDraw &&
        !countDriftIndexedFanGeometry.ready,
        "R143 indexed fan geometry rejects format start and count drift");

    auto wrongSourceIndexRole = managedIndexReady;
    wrongSourceIndexRole.role = ResourceRole::Vertex;
    const auto wrongSourceRoleIndexedFanGeometry =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                managedVertexPostResetReady, wrongSourceIndexRole,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 8u);
    require(
        !wrongSourceRoleIndexedFanGeometry.inputValid &&
        !wrongSourceRoleIndexedFanGeometry.ready &&
        wrongSourceRoleIndexedFanGeometry.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_geometry_snapshot(
                managedVertexPostResetReady, managedIndexReady,
                indexedGeneratedFanReady, 3u, D3DFMT_INDEX16, 2u, 7u,
                indexedFanGeometry.snapshotToken),
        "R143 indexed fan geometry rejects source role and sealed range drift");
    std::cout << "DX11 indexed triangle-fan geometry readiness R143: PASS\n";

    NativeManagedBufferShadow invalidManagedBuffer;
    require(
        !invalidManagedBuffer.initialize(
            ResourceRole::Texture, 32, 0),
        "R113 non-buffer managed shadow must fail closed");

    NativeManagedTextureShadow managedShadow;
    require(
        managedShadow.initialize(D3DFMT_A8R8G8B8, 4, 4),
        "R102 managed shadow initialize");
    require(
        managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow starts allocated but content-invalid");
    require(
        !managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 mirror upload requires valid CPU shadow");
    managedShadow.note_mirror_uploaded();
    require(
        !managedShadow.mirror_ready(),
        "R103 bare mirror acknowledgment must not fabricate readiness");

    std::array<unsigned char, 80> managedSource{};
    constexpr UINT managedSourcePitch = 20;
    constexpr UINT managedRowBytes = 16;
    constexpr UINT managedRows = 4;
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            managedSource[static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x40 + row * 16 + column);
        }
    }

    require(
        !managedShadow.write_full(
            managedSource.data(), managedRowBytes - 1, managedRows),
        "R102 managed shadow short source pitch must fail closed");
    require(
        !managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows - 1),
        "R102 managed shadow partial rows must fail closed");
    require(
        managedShadow.shadow_version() == 0 &&
        !managedShadow.shadow_valid(),
        "R102 rejected managed writes must preserve invalid version");

    require(
        managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows),
        "R102 managed shadow full write");
    require(
        managedShadow.shadow_valid() &&
        managedShadow.shadow_version() == 1 &&
        !managedShadow.mirror_ready(),
        "R102 managed write advances shadow version and invalidates mirror");

    std::array<unsigned char, 96> managedReadback{};
    constexpr UINT managedReadbackPitch = 24;
    require(
        managedShadow.read_full(
            managedReadback.data(), managedReadbackPitch, managedRows),
        "R102 managed shadow full read");
    for (UINT row = 0; row < managedRows; ++row) {
        require(
            std::memcmp(
                managedReadback.data() +
                    static_cast<std::size_t>(row) * managedReadbackPitch,
                managedSource.data() +
                    static_cast<std::size_t>(row) * managedSourcePitch,
                managedRowBytes) == 0,
            "R102 managed shadow readback must match source rows");
    }

    require(
        managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 managed shadow creates DEFAULT mirror");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == d3d.device &&
        managedShadow.mirror_texture() != nullptr &&
        managedShadow.mirror_srv() != nullptr &&
        managedShadow.lifetime_state().mirrorGeneration == 1 &&
        managedShadow.lifetime_state().mirrorShadowVersion == 1,
        "R103 managed mirror ownership matches shadow generation");

    D3D11_TEXTURE2D_DESC managedMirrorDesc{};
    managedShadow.mirror_texture()->GetDesc(&managedMirrorDesc);
    require(
        managedMirrorDesc.Width == 4 &&
        managedMirrorDesc.Height == 4 &&
        managedMirrorDesc.MipLevels == 1 &&
        managedMirrorDesc.ArraySize == 1 &&
        managedMirrorDesc.Format == DXGI_FORMAT_B8G8R8A8_UNORM &&
        managedMirrorDesc.Usage == D3D11_USAGE_DEFAULT &&
        managedMirrorDesc.CPUAccessFlags == 0 &&
        (managedMirrorDesc.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0,
        "R103 managed mirror DEFAULT descriptor contract");

    D3D11_TEXTURE2D_DESC managedStagingDesc = managedMirrorDesc;
    managedStagingDesc.Usage = D3D11_USAGE_STAGING;
    managedStagingDesc.BindFlags = 0;
    managedStagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* managedStagingTexture = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateTexture2D(
            &managedStagingDesc, nullptr, &managedStagingTexture)) &&
        managedStagingTexture != nullptr,
        "R103 managed mirror staging prerequisite");
    d3d.context->CopyResource(
        managedStagingTexture, managedShadow.mirror_texture());

    D3D11_MAPPED_SUBRESOURCE managedStagingMap{};
    require(
        SUCCEEDED(d3d.context->Map(
            managedStagingTexture, 0, D3D11_MAP_READ, 0, &managedStagingMap)) &&
        managedStagingMap.pData != nullptr &&
        managedStagingMap.RowPitch >= managedRowBytes,
        "R103 managed mirror staging readback map");
    for (UINT row = 0; row < managedRows; ++row) {
        const auto* observed =
            static_cast<const unsigned char*>(managedStagingMap.pData) +
            static_cast<std::size_t>(row) * managedStagingMap.RowPitch;
        const auto* expected =
            managedSource.data() +
            static_cast<std::size_t>(row) * managedSourcePitch;
        require(
            std::memcmp(observed, expected, managedRowBytes) == 0,
            "R103 managed mirror uploaded bytes must match shadow rows");
    }
    d3d.context->Unmap(managedStagingTexture, 0);
    managedStagingTexture->Release();

    managedShadow.observe_device_reset();
    require(
        managedShadow.device_generation() == 2 &&
        managedShadow.shadow_valid() &&
        managedShadow.shadow_version() == 1 &&
        !managedShadow.mirror_ready(),
        "R102 Reset preserves CPU shadow and invalidates GPU mirror");
    require(
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr,
        "R103 Reset preserves shadow and releases generation-bound mirror");

    managedReadback.fill(0);
    require(
        managedShadow.read_full(
            managedReadback.data(), managedReadbackPitch, managedRows),
        "R102 managed shadow remains readable after Reset");
    require(
        std::memcmp(
            managedReadback.data(),
            managedSource.data(),
            managedRowBytes) == 0,
        "R102 Reset-preserved first row must match");

    require(
        managedShadow.recreate_and_upload_mirror(d3d.device),
        "R103 post-Reset mirror recreation");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.lifetime_state().mirrorGeneration == 2,
        "R102 post-Reset mirror acknowledgment uses new device generation");
    require(
        managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == d3d.device &&
        managedShadow.mirror_texture() != nullptr &&
        managedShadow.mirror_srv() != nullptr &&
        managedShadow.lifetime_state().mirrorShadowVersion == 1,
        "R103 post-Reset mirror upload uses new device generation");
    require(
        managedShadow.mirror_descriptor_exact(d3d.device) &&
        !managedShadow.mirror_descriptor_exact(textureOtherDevice.device),
        "R111 managed mirror descriptor and SRV view identity are exact-device bound");

    managedSource[0] ^= 0x33;
    require(
        managedShadow.write_full(
            managedSource.data(), managedSourcePitch, managedRows),
        "R102 second managed shadow full write");
    require(
        managedShadow.shadow_version() == 2 &&
        !managedShadow.mirror_ready() &&
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr &&
        !managedShadow.mirror_descriptor_exact(d3d.device),
        "R103 shadow mutation invalidates and releases uploaded mirror");

    NativeManagedTextureShadow unsupportedManagedShadow;
    require(
        !unsupportedManagedShadow.initialize(D3DFMT_DXT1, 4, 4),
        "R102 compressed managed shadow must fail closed");
    require(
        !unsupportedManagedShadow.ready(),
        "R102 failed managed shadow initialize stays dormant");

    NativeManagedTextureShadow lockBridgeShadow;
    require(
        lockBridgeShadow.initialize(D3DFMT_A8R8G8B8, 4, 4),
        "R104 LockRect bridge shadow initialize");

    std::array<unsigned char, 80> lockBridgeSource{};
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            lockBridgeSource[
                static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x90 + row * 16 + column);
        }
    }

    D3DLOCKED_RECT sourceLock{};
    sourceLock.Pitch = static_cast<INT>(managedSourcePitch);
    sourceLock.pBits = lockBridgeSource.data();
    RECT partialRect{0, 0, 2, 2};

    require(
        !lockBridgeShadow.begin_source_lock(
            1, nullptr, 0, sourceLock),
        "R104 nonzero mip LockRect must fail closed");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, &partialRect, 0, sourceLock),
        "R104 partial LockRect must fail closed");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, D3DLOCK_READONLY, sourceLock),
        "R104 read-only LockRect must not arm write capture");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, D3DLOCK_DISCARD, sourceLock),
        "R104 MANAGED discard LockRect must fail closed");

    D3DLOCKED_RECT shortPitchLock = sourceLock;
    shortPitchLock.Pitch = static_cast<INT>(managedRowBytes - 1);
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, shortPitchLock),
        "R104 short-pitch LockRect must fail closed");

    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock) &&
        lockBridgeShadow.source_lock_active(),
        "R104 full MANAGED LockRect arms source capture");
    require(
        !lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock),
        "R104 nested LockRect must fail closed");
    require(
        !lockBridgeShadow.commit_source_unlock(1) &&
        lockBridgeShadow.source_lock_active(),
        "R104 mismatched UnlockRect level must preserve active capture");

    // Prove the bridge observes the final lock contents rather than the bytes
    // that happened to exist when LockRect first returned.
    lockBridgeSource[0] ^= 0x5c;
    require(
        lockBridgeShadow.commit_source_unlock(0) &&
        !lockBridgeShadow.source_lock_active(),
        "R104 matching UnlockRect commits final lock contents");
    require(
        lockBridgeShadow.shadow_valid() &&
        lockBridgeShadow.shadow_version() == 1,
        "R104 UnlockRect commit advances managed shadow version");

    std::array<unsigned char, 96> lockBridgeReadback{};
    require(
        lockBridgeShadow.read_full(
            lockBridgeReadback.data(), managedReadbackPitch, managedRows),
        "R104 committed LockRect shadow readback");
    for (UINT row = 0; row < managedRows; ++row) {
        require(
            std::memcmp(
                lockBridgeReadback.data() +
                    static_cast<std::size_t>(row) * managedReadbackPitch,
                lockBridgeSource.data() +
                    static_cast<std::size_t>(row) * managedSourcePitch,
                managedRowBytes) == 0,
            "R104 UnlockRect-captured bytes must match final source rows");
    }

    require(
        lockBridgeShadow.recreate_and_upload_mirror(d3d.device),
        "R104 bridge mirror prerequisite");
    require(
        lockBridgeShadow.mirror_ready(),
        "R104 bridge mirror starts generation-current");

    lockBridgeSource[0] ^= 0x27;
    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock) &&
        lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.mirror_ready() &&
        lockBridgeShadow.mirror_texture() == nullptr,
        "R104 writable LockRect invalidates stale GPU mirror immediately");
    require(
        !lockBridgeShadow.read_full(
            lockBridgeReadback.data(), managedReadbackPitch, managedRows) &&
        !lockBridgeShadow.recreate_and_upload_mirror(d3d.device),
        "R104 active source lock blocks stale shadow read/upload");

    lockBridgeShadow.observe_device_reset();
    require(
        !lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.commit_source_unlock(0) &&
        lockBridgeShadow.shadow_valid() &&
        lockBridgeShadow.shadow_version() == 1 &&
        lockBridgeShadow.device_generation() == 2,
        "R104 Reset clears stale LockRect pointer without committing it");

    require(
        lockBridgeShadow.begin_source_lock(
            0, nullptr, 0, sourceLock),
        "R104 post-Reset LockRect re-arms capture");
    lockBridgeShadow.cancel_source_lock();
    require(
        !lockBridgeShadow.source_lock_active() &&
        lockBridgeShadow.shadow_version() == 1,
        "R104 cancelled LockRect clears capture without shadow mutation");

    NativeManagedTextureRegistry managedRegistry;
    int registryTextureA = 0;
    int registryTextureB = 0;
    require(
        !managedRegistry.register_texture(
            nullptr, D3DFMT_A8R8G8B8, 4, 4, 1, 0, D3DPOOL_MANAGED),
        "R105 registry rejects null texture identity");
    require(
        !managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 2, 0,
            D3DPOOL_MANAGED),
        "R105 registry rejects multi-mip MANAGED texture");
    require(
        !managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_DEFAULT),
        "R105 registry rejects non-MANAGED texture");
    require(
        managedRegistry.register_texture(
            &registryTextureA, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.size() == 1 &&
        managedRegistry.contains(&registryTextureA),
        "R105 registry accepts exact single-mip MANAGED texture");

    std::array<unsigned char, 80> registrySource{};
    for (UINT row = 0; row < managedRows; ++row) {
        for (UINT column = 0; column < managedRowBytes; ++column) {
            registrySource[
                static_cast<std::size_t>(row) * managedSourcePitch + column] =
                static_cast<unsigned char>(0x30 + row * 16 + column);
        }
    }
    D3DLOCKED_RECT registryLock{};
    registryLock.Pitch = static_cast<INT>(managedSourcePitch);
    registryLock.pBits = registrySource.data();

    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.source_lock_active(&registryTextureA),
        "R105 registry begins exact managed LockRect transaction");
    registrySource[0] ^= 0x19;
    require(
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        !managedRegistry.source_lock_active(&registryTextureA) &&
        managedRegistry.source_unlock_staged(&registryTextureA),
        "R105 pre-Unlock staging clears raw source pointer");
    const unsigned char stagedFirstByte = registrySource[0];
    registrySource[0] ^= 0x7f;
    require(
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 1 &&
        !managedRegistry.source_unlock_staged(&registryTextureA),
        "R105 successful real Unlock commits staged bytes");

    std::array<unsigned char, 96> registryReadback{};
    require(
        managedRegistry.read_shadow(
            &registryTextureA,
            registryReadback.data(), managedReadbackPitch, managedRows) &&
        registryReadback[0] == stagedFirstByte &&
        registryReadback[0] != registrySource[0],
        "R105 commit uses pre-Unlock staged snapshot, not post-stage source");

    registrySource[0] ^= 0x23;
    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0),
        "R105 failed-Unlock transaction stages before COM call");
    require(
        !managedRegistry.finish_source_unlock(
            &registryTextureA, 0, E_FAIL) &&
        !managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 1,
        "R105 failed real Unlock invalidates shadow without commit");

    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) == 2,
        "R105 later successful Unlock recovers invalidated shadow");

    const auto registryVersionBeforeExternalMutation =
        managedRegistry.shadow_version(&registryTextureA);
    require(
        !managedRegistry.recreate_and_upload_mirror_for_observation(
            nullptr, d3d.device) &&
        !managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, nullptr),
        "R108 registry mirror preparation rejects incomplete ownership identity");
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 registry prepares exact identity-owned mirror for observation");
    const auto registryMirrorReady =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorReady.registered &&
        registryMirrorReady.shadowValid &&
        registryMirrorReady.resourcesOwned &&
        registryMirrorReady.lifetimeCurrent &&
        registryMirrorReady.deviceMatches &&
        registryMirrorReady.descriptorExact &&
        registryMirrorReady.ready &&
        registryMirrorReady.deviceGeneration ==
            managedRegistry.device_generation(&registryTextureA) &&
        registryMirrorReady.shadowVersion ==
            registryVersionBeforeExternalMutation &&
        registryMirrorReady.mirrorGeneration ==
            registryMirrorReady.deviceGeneration &&
        registryMirrorReady.mirrorShadowVersion ==
            registryMirrorReady.shadowVersion,
        "R108 registry mirror readiness seals texture identity generation and shadow version");
    const auto registryMirrorForeignDevice =
        managedRegistry.mirror_readiness(
            &registryTextureA, textureOtherDevice.device);
    require(
        registryMirrorForeignDevice.registered &&
        registryMirrorForeignDevice.shadowValid &&
        registryMirrorForeignDevice.resourcesOwned &&
        registryMirrorForeignDevice.lifetimeCurrent &&
        !registryMirrorForeignDevice.deviceMatches &&
        !registryMirrorForeignDevice.descriptorExact &&
        !registryMirrorForeignDevice.ready,
        "R108 foreign D3D11 device cannot claim registered mirror readiness");

    const std::array<const void*, 2> registryStageKeys{
        &registryTextureA, &registryTextureB};
    const auto registryStageNullKeys =
        managedRegistry.mirror_readiness_for_stages(
            nullptr, 1, 0x1u, d3d.device);
    require(
        !registryStageNullKeys.inputValid &&
        registryStageNullKeys.requiredMask == 0x1u &&
        registryStageNullKeys.pendingMask == 0x1u &&
        !registryStageNullKeys.allRequiredReady,
        "R109 stage aggregate rejects null key array fail-closed");
    const auto registryStageOutOfRange =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), 1, 0x2u, d3d.device);
    require(
        !registryStageOutOfRange.inputValid &&
        registryStageOutOfRange.pendingMask == 0x2u &&
        !registryStageOutOfRange.allRequiredReady,
        "R109 stage aggregate rejects required bits beyond observed stages");
    const auto registryStageNullDevice =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, nullptr);
    require(
        !registryStageNullDevice.inputValid &&
        registryStageNullDevice.pendingMask == 0x1u &&
        !registryStageNullDevice.allRequiredReady,
        "R109 stage aggregate rejects missing expected D3D11 device");
    const auto registryStageReady =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageReady.inputValid &&
        registryStageReady.requiredMask == 0x1u &&
        registryStageReady.registeredMask == 0x1u &&
        registryStageReady.shadowValidMask == 0x1u &&
        registryStageReady.resourcesOwnedMask == 0x1u &&
        registryStageReady.lifetimeCurrentMask == 0x1u &&
        registryStageReady.deviceMatchesMask == 0x1u &&
        registryStageReady.descriptorExactMask == 0x1u &&
        registryStageReady.readyMask == 0x1u &&
        registryStageReady.pendingMask == 0 &&
        registryStageReady.allRequiredReady,
        "R109 exact required stage aggregates all R108 readiness evidence");
    require(
        registryStageReady.snapshotToken != 0 &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageReady.snapshotToken),
        "R110 ready stage aggregate issues a valid nonzero snapshot token");
    require(
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, textureOtherDevice.device, registryStageReady.snapshotToken) &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x3u, d3d.device, registryStageReady.snapshotToken) &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, 0),
        "R110 snapshot token is bound to exact device mask and nonzero identity");
    const auto registryStageInitialToken = registryStageReady.snapshotToken;
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R110 same-shadow mirror recreation prerequisite");
    const auto registryStageAfterSameShadowRecreate =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterSameShadowRecreate.allRequiredReady &&
        registryStageAfterSameShadowRecreate.snapshotToken != 0 &&
        registryStageAfterSameShadowRecreate.snapshotToken !=
            registryStageInitialToken &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageInitialToken) &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterSameShadowRecreate.snapshotToken),
        "R110 mirror instance recreation invalidates stale readiness token");
    const auto registryStageBeforeMembershipChangeToken =
        registryStageAfterSameShadowRecreate.snapshotToken;
    require(
        managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED),
        "R110 registry membership generation change prerequisite");
    require(
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeMembershipChangeToken),
        "R110 registry membership change invalidates prior snapshot token");
    managedRegistry.forget_texture(&registryTextureB);
    const auto registryStageAfterMembershipRefresh =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterMembershipRefresh.allRequiredReady &&
        registryStageAfterMembershipRefresh.snapshotToken != 0 &&
        registryStageAfterMembershipRefresh.snapshotToken !=
            registryStageBeforeMembershipChangeToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterMembershipRefresh.snapshotToken),
        "R110 refreshed membership snapshot issues a fresh valid token");
    const auto registryStageBeforeExternalMutationToken =
        registryStageAfterMembershipRefresh.snapshotToken;
    const auto registryStageMissingRequired =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x3u, d3d.device);
    require(
        registryStageMissingRequired.inputValid &&
        registryStageMissingRequired.registeredMask == 0x1u &&
        registryStageMissingRequired.readyMask == 0x1u &&
        registryStageMissingRequired.pendingMask == 0x2u &&
        !registryStageMissingRequired.allRequiredReady,
        "R109 unregistered required stage remains activation-pending");
    const auto registryStageForeignDevice =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, textureOtherDevice.device);
    require(
        registryStageForeignDevice.inputValid &&
        registryStageForeignDevice.registeredMask == 0x1u &&
        registryStageForeignDevice.shadowValidMask == 0x1u &&
        registryStageForeignDevice.resourcesOwnedMask == 0x1u &&
        registryStageForeignDevice.lifetimeCurrentMask == 0x1u &&
        registryStageForeignDevice.deviceMatchesMask == 0 &&
        registryStageForeignDevice.descriptorExactMask == 0 &&
        registryStageForeignDevice.readyMask == 0 &&
        registryStageForeignDevice.pendingMask == 0x1u &&
        !registryStageForeignDevice.allRequiredReady,
        "R109 foreign device keeps required stage activation-pending");

    require(
        managedRegistry.invalidate_external_mutation(&registryTextureA) &&
        !managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeExternalMutation,
        "R107 external update invalidates current MANAGED texture shadow");
    const auto registryMirrorAfterExternalMutation =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterExternalMutation.registered &&
        !registryMirrorAfterExternalMutation.shadowValid &&
        !registryMirrorAfterExternalMutation.resourcesOwned &&
        !registryMirrorAfterExternalMutation.lifetimeCurrent &&
        !registryMirrorAfterExternalMutation.ready,
        "R108 external mutation clears registry mirror ownership readiness");
    const auto registryStageAfterExternalMutation =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterExternalMutation.inputValid &&
        registryStageAfterExternalMutation.registeredMask == 0x1u &&
        registryStageAfterExternalMutation.shadowValidMask == 0 &&
        registryStageAfterExternalMutation.resourcesOwnedMask == 0 &&
        registryStageAfterExternalMutation.lifetimeCurrentMask == 0 &&
        registryStageAfterExternalMutation.deviceMatchesMask == 0 &&
        registryStageAfterExternalMutation.descriptorExactMask == 0 &&
        registryStageAfterExternalMutation.readyMask == 0 &&
        registryStageAfterExternalMutation.pendingMask == 0x1u &&
        !registryStageAfterExternalMutation.allRequiredReady,
        "R109 external mutation makes required stage activation-pending");
    require(
        registryStageAfterExternalMutation.snapshotToken == 0 &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeExternalMutationToken),
        "R110 external mutation invalidates prior readiness snapshot token");
    require(
        !managedRegistry.invalidate_external_mutation(&registryTextureA) &&
        !managedRegistry.shadow_valid(&registryTextureA),
        "R107 repeated external update remains fail-closed while shadow is stale");

    registrySource[0] ^= 0x31;
    require(
        managedRegistry.begin_source_lock(
            &registryTextureA, 0, nullptr, 0, registryLock) &&
        managedRegistry.stage_source_unlock(&registryTextureA, 0) &&
        managedRegistry.finish_source_unlock(
            &registryTextureA, 0, S_OK) &&
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeExternalMutation + 1,
        "R107 LockRect recapture restores readiness after external update");

    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 recaptured shadow recreates registry mirror");
    const auto registryMirrorBeforeReset =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorBeforeReset.ready &&
        registryMirrorBeforeReset.mirrorGeneration ==
            registryMirrorBeforeReset.deviceGeneration &&
        registryMirrorBeforeReset.mirrorShadowVersion ==
            registryMirrorBeforeReset.shadowVersion,
        "R108 recaptured mirror is generation-current before Reset");
    const auto registryStageAfterRecapture =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterRecapture.inputValid &&
        registryStageAfterRecapture.readyMask == 0x1u &&
        registryStageAfterRecapture.pendingMask == 0 &&
        registryStageAfterRecapture.allRequiredReady,
        "R109 recaptured mirror restores required stage readiness");
    require(
        registryStageAfterRecapture.snapshotToken != 0 &&
        registryStageAfterRecapture.snapshotToken !=
            registryStageBeforeExternalMutationToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageAfterRecapture.snapshotToken),
        "R110 recapture and mirror recreation issue a fresh valid token");
    const auto registryStageBeforeResetToken =
        registryStageAfterRecapture.snapshotToken;

    const auto registryVersionBeforeReset =
        managedRegistry.shadow_version(&registryTextureA);
    const auto registryGenerationBeforeReset =
        managedRegistry.device_generation(&registryTextureA);
    managedRegistry.observe_device_reset();
    require(
        managedRegistry.shadow_valid(&registryTextureA) &&
        managedRegistry.shadow_version(&registryTextureA) ==
            registryVersionBeforeReset &&
        managedRegistry.device_generation(&registryTextureA) ==
            registryGenerationBeforeReset + 1,
        "R105 Reset preserves CPU shadow and advances registry generation");
    const auto registryMirrorAfterReset =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterReset.registered &&
        registryMirrorAfterReset.shadowValid &&
        !registryMirrorAfterReset.resourcesOwned &&
        !registryMirrorAfterReset.lifetimeCurrent &&
        !registryMirrorAfterReset.ready &&
        registryMirrorAfterReset.deviceGeneration ==
            registryGenerationBeforeReset + 1 &&
        registryMirrorAfterReset.shadowVersion == registryVersionBeforeReset,
        "R108 Reset invalidates generation-bound registry mirror readiness");
    const auto registryStageAfterReset =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterReset.inputValid &&
        registryStageAfterReset.registeredMask == 0x1u &&
        registryStageAfterReset.shadowValidMask == 0x1u &&
        registryStageAfterReset.resourcesOwnedMask == 0 &&
        registryStageAfterReset.lifetimeCurrentMask == 0 &&
        registryStageAfterReset.deviceMatchesMask == 0 &&
        registryStageAfterReset.descriptorExactMask == 0 &&
        registryStageAfterReset.readyMask == 0 &&
        registryStageAfterReset.pendingMask == 0x1u &&
        !registryStageAfterReset.allRequiredReady,
        "R109 Reset keeps required stage activation-pending");
    require(
        registryStageAfterReset.snapshotToken == 0 &&
        !managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device, registryStageBeforeResetToken),
        "R110 Reset invalidates pre-Reset readiness snapshot token");
    require(
        managedRegistry.recreate_and_upload_mirror_for_observation(
            &registryTextureA, d3d.device),
        "R108 post-Reset registry mirror recreation");
    const auto registryMirrorAfterResetRecreate =
        managedRegistry.mirror_readiness(&registryTextureA, d3d.device);
    require(
        registryMirrorAfterResetRecreate.ready &&
        registryMirrorAfterResetRecreate.deviceGeneration ==
            registryGenerationBeforeReset + 1 &&
        registryMirrorAfterResetRecreate.mirrorGeneration ==
            registryMirrorAfterResetRecreate.deviceGeneration &&
        registryMirrorAfterResetRecreate.mirrorShadowVersion ==
            registryVersionBeforeReset,
        "R108 post-Reset mirror readiness uses current device generation");
    const auto registryStageAfterResetRecreate =
        managedRegistry.mirror_readiness_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device);
    require(
        registryStageAfterResetRecreate.inputValid &&
        registryStageAfterResetRecreate.readyMask == 0x1u &&
        registryStageAfterResetRecreate.pendingMask == 0 &&
        registryStageAfterResetRecreate.allRequiredReady,
        "R109 post-Reset recreation restores required stage readiness");
    require(
        registryStageAfterResetRecreate.snapshotToken != 0 &&
        registryStageAfterResetRecreate.snapshotToken !=
            registryStageBeforeResetToken &&
        managedRegistry.validate_mirror_readiness_snapshot_for_stages(
            registryStageKeys.data(), registryStageKeys.size(),
            0x1u, d3d.device,
            registryStageAfterResetRecreate.snapshotToken),
        "R110 post-Reset recreation issues a generation-current fresh token");

    managedRegistry.forget_texture(&registryTextureA);
    require(
        !managedRegistry.contains(&registryTextureA) &&
        managedRegistry.size() == 0,
        "R105 Release cleanup forgets per-texture shadow");

    require(
        managedRegistry.register_texture(
            &registryTextureA, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.register_texture(
            &registryTextureB, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED) &&
        managedRegistry.size() == 2,
        "R105 registry clear prerequisite");
    managedRegistry.clear();
    require(
        managedRegistry.size() == 0,
        "R105 registry shutdown clears all texture ownership");

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

    ID3DBlob* isolationGeometryBytecode = compile_geometry_shader();
    ID3D11GeometryShader* isolationGeometryShader = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateGeometryShader(
            isolationGeometryBytecode->GetBufferPointer(),
            isolationGeometryBytecode->GetBufferSize(),
            nullptr,
            &isolationGeometryShader)) &&
        isolationGeometryShader != nullptr,
        "CreateGeometryShader R147 isolation probe");

    D3D11_BUFFER_DESC isolationStreamOutputDesc{};
    isolationStreamOutputDesc.ByteWidth = 64;
    isolationStreamOutputDesc.Usage = D3D11_USAGE_DEFAULT;
    isolationStreamOutputDesc.BindFlags = D3D11_BIND_STREAM_OUTPUT;
    ID3D11Buffer* isolationStreamOutputBuffer = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateBuffer(
            &isolationStreamOutputDesc, nullptr,
            &isolationStreamOutputBuffer)) &&
        isolationStreamOutputBuffer != nullptr,
        "CreateBuffer R148 stream-output isolation probe");
    D3D11_QUERY_DESC isolationPredicateDesc{};
    isolationPredicateDesc.Query = D3D11_QUERY_OCCLUSION_PREDICATE;
    ID3D11Predicate* isolationPredicate = nullptr;
    require(
        SUCCEEDED(d3d.device->CreatePredicate(
            &isolationPredicateDesc, &isolationPredicate)) &&
        isolationPredicate != nullptr,
        "CreatePredicate R148 draw-predication isolation probe");

    NativeFixedFunctionTransformBuffer owner;
    require(!owner.ready(), "R96 owner must start dormant");
    require(owner.upload_generation() == 0,
            "R96 owner generation must start at zero");
    require(owner.initialize(d3d.device),
            "R96 owner initialize");

    OutRunVR::DrawState::RenderStateSnapshot renderStateSource{};
    renderStateSource.complete = true;
    renderStateSource.stencilEnable = TRUE;
    renderStateSource.stencilRef = 0x5au;
    renderStateSource.stencilFunc = D3DCMP_ALWAYS;
    const auto renderStateTranslation =
        translate_pipeline(renderStateSource);
    require(
        renderStateTranslation.exact(),
        "R116 render-state translation prerequisite");

    NativeFixedFunctionRenderStateBundle renderStateBundle;
    require(
        !renderStateBundle.ready(),
        "R116 render-state bundle must start dormant");
    require(
        renderStateBundle.initialize(d3d.device, renderStateTranslation),
        "R116 render-state bundle initialize");
    require(
        renderStateBundle.ready() &&
        renderStateBundle.device() == d3d.device &&
        renderStateBundle.blend_state() != nullptr &&
        renderStateBundle.depth_stencil_state() != nullptr &&
        renderStateBundle.rasterizer_state() != nullptr &&
        renderStateBundle.stencil_ref() == 0x5au,
        "R116 render-state bundle owns exact translated state objects");

    const auto renderStateReady =
        renderStateBundle.translation_readiness(
            d3d.device, renderStateTranslation);
    require(
        renderStateReady.inputValid &&
        renderStateReady.bundleReady &&
        renderStateReady.deviceMatches &&
        renderStateReady.translationMatches &&
        renderStateReady.ready &&
        renderStateReady.bundleGeneration != 0 &&
        renderStateReady.translationIdentity != 0 &&
        renderStateReady.snapshotToken != 0 &&
        renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateReady.snapshotToken),
        "R116 exact render-state translation issues a valid snapshot");

    auto changedRenderStateTranslation = renderStateTranslation;
    changedRenderStateTranslation.stencil_ref ^= 0x1u;
    const auto changedRenderStateReady =
        renderStateBundle.translation_readiness(
            d3d.device, changedRenderStateTranslation);
    require(
        changedRenderStateReady.inputValid &&
        changedRenderStateReady.bundleReady &&
        changedRenderStateReady.deviceMatches &&
        !changedRenderStateReady.translationMatches &&
        !changedRenderStateReady.ready &&
        changedRenderStateReady.snapshotToken == 0 &&
        !renderStateBundle.validate_translation_snapshot(
            d3d.device, changedRenderStateTranslation,
            renderStateReady.snapshotToken),
        "R116 changed render-state identity fails closed");

    DevicePair renderStateOtherDevice = create_warp_device();
    const auto foreignRenderStateReady =
        renderStateBundle.translation_readiness(
            renderStateOtherDevice.device, renderStateTranslation);
    require(
        foreignRenderStateReady.inputValid &&
        foreignRenderStateReady.bundleReady &&
        !foreignRenderStateReady.deviceMatches &&
        !foreignRenderStateReady.ready &&
        foreignRenderStateReady.snapshotToken == 0,
        "R116 foreign device cannot claim render-state readiness");
    renderStateOtherDevice.context->Release();
    renderStateOtherDevice.device->Release();

    const auto renderStateInitialToken = renderStateReady.snapshotToken;
    const auto renderStateInitialGeneration =
        renderStateReady.bundleGeneration;
    auto inexactRenderStateTranslation = renderStateTranslation;
    inexactRenderStateTranslation.unsupported |= PipelineUnsupportedBlend;
    require(
        !renderStateBundle.initialize(
            d3d.device, inexactRenderStateTranslation) &&
        !renderStateBundle.ready(),
        "R116 inexact render-state translation must fail closed");
    require(
        renderStateBundle.initialize(d3d.device, renderStateTranslation),
        "R116 render-state bundle recreate");
    const auto renderStateRecreated =
        renderStateBundle.translation_readiness(
            d3d.device, renderStateTranslation);
    require(
        renderStateRecreated.ready &&
        renderStateRecreated.bundleGeneration >
            renderStateInitialGeneration &&
        renderStateRecreated.snapshotToken != 0 &&
        renderStateRecreated.snapshotToken != renderStateInitialToken &&
        !renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateInitialToken) &&
        renderStateBundle.validate_translation_snapshot(
            d3d.device, renderStateTranslation,
            renderStateRecreated.snapshotToken),
        "R116 render-state bundle recreation invalidates stale snapshot");

    NativeFixedFunctionPipelineBundle pipelineBundle;
    require(!pipelineBundle.ready(),
            "R97 bundle must start dormant");
    require(
        pipelineBundle.initialize(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype),
        "R97 bundle initialize");
    require(
        pipelineBundle.ready() &&
        pipelineBundle.device() == d3d.device &&
        pipelineBundle.vertex_shader() != nullptr &&
        pipelineBundle.pixel_shader() != nullptr &&
        pipelineBundle.input_layout() != nullptr &&
        pipelineBundle.transform_buffer().ready(),
        "R97 bundle owned-object readiness");

    const auto pipelineIdentityReady =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype);
    require(
        pipelineIdentityReady.inputValid &&
        pipelineIdentityReady.bundleReady &&
        pipelineIdentityReady.deviceMatches &&
        pipelineIdentityReady.inputLayoutMatches &&
        pipelineIdentityReady.vertexShaderMatches &&
        pipelineIdentityReady.pixelShaderMatches &&
        pipelineIdentityReady.ready &&
        pipelineIdentityReady.bundleGeneration != 0 &&
        pipelineIdentityReady.snapshotToken != 0 &&
        pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R112 exact fixed-function pipeline translation identity issues a valid snapshot");

    require(
        programmableCache.initialize(d3d.device) &&
        programmableCache.cache_for_observation(programmablePair),
        "R242 programmable object attachment cache prerequisite");
    const auto r242CacheReady =
        programmableCache.readiness(d3d.device, programmablePair);
    require(
        r242CacheReady.ready &&
        !programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken, 0,
            pipelineBundle.vertex_shader(),
            pipelineBundle.pixel_shader()),
        "R242 translation slot must exist before translated objects attach");
    require(
        programmableCache.reserve_translation_slot_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken),
        "R242 translation slot reservation prerequisite");
    const auto r242SlotReady =
        programmableCache.translation_slot_ownership_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken);
    require(
        r242SlotReady.ownershipReady &&
        r242SlotReady.snapshotToken != 0,
        "R242 exact R241 translation slot prerequisite");
    require(
        programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            pipelineBundle.vertex_shader(),
            pipelineBundle.pixel_shader()),
        "R242 attach translated object pair to exact slot");
    const auto r242ObjectReady =
        programmableCache.translation_object_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken);
    require(
        r242ObjectReady.inputValid &&
        r242ObjectReady.slotReady &&
        r242ObjectReady.deviceMatches &&
        r242ObjectReady.cacheSnapshotMatches &&
        r242ObjectReady.slotSnapshotMatches &&
        r242ObjectReady.objectsAttached &&
        r242ObjectReady.objectDevicesMatch &&
        r242ObjectReady.attachmentReady &&
        r242ObjectReady.ownerGeneration != 0 &&
        r242ObjectReady.slotGeneration != 0 &&
        r242ObjectReady.translationObjectReceiptGeneration != 0 &&
        r242ObjectReady.cacheKey == programmablePair.cacheKey &&
        r242ObjectReady.snapshotToken != 0 &&
        programmableCache.validate_translation_object_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken),
        "R242 translated object receipt seals device cache and slot ownership");
    const auto firstR242ReceiptGeneration =
        r242ObjectReady.translationObjectReceiptGeneration;
    const auto firstR242ObjectSnapshot =
        r242ObjectReady.snapshotToken;
    require(
        programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            pipelineBundle.vertex_shader(),
            pipelineBundle.pixel_shader()) &&
        programmableCache.translation_object_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken).snapshotToken ==
            firstR242ObjectSnapshot,
        "R242 same translated object pair attachment is idempotent");

    const auto r243UnattachedInputLayout =
        programmableCache.input_layout_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout);
    require(
        r243UnattachedInputLayout.inputValid &&
        r243UnattachedInputLayout.objectReceiptReady &&
        r243UnattachedInputLayout.deviceMatches &&
        r243UnattachedInputLayout.objectSnapshotMatches &&
        r243UnattachedInputLayout.layoutIdentityExact &&
        !r243UnattachedInputLayout.inputLayoutAttached &&
        !r243UnattachedInputLayout.inputLayoutDeviceMatches &&
        !r243UnattachedInputLayout.attachmentReady &&
        r243UnattachedInputLayout.inputLayoutReceiptGeneration == 0 &&
        r243UnattachedInputLayout.snapshotToken == 0 &&
        !programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            0,
            inputLayout,
            pipelineBundle.input_layout()),
        "R243 translated objects must exist before input layout attaches");
    require(
        programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            pipelineBundle.input_layout()),
        "R243 attach input layout to exact R242 object receipt");
    const auto r243InputLayoutReady =
        programmableCache.input_layout_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout);
    require(
        r243InputLayoutReady.inputValid &&
        r243InputLayoutReady.objectReceiptReady &&
        r243InputLayoutReady.deviceMatches &&
        r243InputLayoutReady.objectSnapshotMatches &&
        r243InputLayoutReady.layoutIdentityExact &&
        r243InputLayoutReady.inputLayoutAttached &&
        r243InputLayoutReady.inputLayoutDeviceMatches &&
        r243InputLayoutReady.attachmentReady &&
        r243InputLayoutReady.ownerGeneration != 0 &&
        r243InputLayoutReady.slotGeneration != 0 &&
        r243InputLayoutReady.translationObjectReceiptGeneration != 0 &&
        r243InputLayoutReady.inputLayoutReceiptGeneration != 0 &&
        r243InputLayoutReady.inputLayoutIdentity != 0 &&
        r243InputLayoutReady.snapshotToken != 0 &&
        programmableCache.validate_input_layout_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            r243InputLayoutReady.snapshotToken),
        "R243 input-layout receipt seals exact R242 object receipt and metadata");
    const auto firstR243ReceiptGeneration =
        r243InputLayoutReady.inputLayoutReceiptGeneration;
    const auto firstR243InputLayoutSnapshot =
        r243InputLayoutReady.snapshotToken;
    require(
        programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            pipelineBundle.input_layout()) &&
        programmableCache.input_layout_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout).snapshotToken ==
            firstR243InputLayoutSnapshot,
        "R243 same input layout attachment is idempotent");
    auto r243MismatchedLayoutMetadata = inputLayout;
    ++r243MismatchedLayoutMetadata.stream0Stride;
    require(
        !programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            r243MismatchedLayoutMetadata,
            pipelineBundle.input_layout()) &&
        !programmableCache.input_layout_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            r243MismatchedLayoutMetadata).attachmentReady,
        "R243 changed input layout metadata cannot reuse sealed receipt");

    ID3D11InputLayout* r243ReplacementInputLayout = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateInputLayout(
            inputLayout.elements.data(),
            inputLayout.elementCount,
            vertexBytecode->GetBufferPointer(),
            vertexBytecode->GetBufferSize(),
            &r243ReplacementInputLayout)) &&
        r243ReplacementInputLayout != nullptr &&
        r243ReplacementInputLayout != pipelineBundle.input_layout() &&
        !programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            r243ReplacementInputLayout),
        "R243 different input layout object cannot replace sealed receipt");
    r243ReplacementInputLayout->Release();

    constexpr UINT r244ConstantBytes = 64u;
    ID3D11Buffer* r244VertexConstants =
        create_constant_buffer(d3d.device, r244ConstantBytes);
    ID3D11Buffer* r244PixelConstants =
        create_constant_buffer(d3d.device, r244ConstantBytes);
    const auto r244UnattachedConstantState =
        programmableCache.constant_state_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            r243InputLayoutReady.snapshotToken);
    require(
        r244UnattachedConstantState.inputValid &&
        r244UnattachedConstantState.inputLayoutReceiptReady &&
        r244UnattachedConstantState.deviceMatches &&
        r244UnattachedConstantState.inputLayoutSnapshotMatches &&
        !r244UnattachedConstantState.constantBuffersAttached &&
        !r244UnattachedConstantState.attachmentReady &&
        r244UnattachedConstantState.constantStateReceiptGeneration == 0 &&
        r244UnattachedConstantState.snapshotToken == 0 &&
        !programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, 0,
            r244VertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes),
        "R244 input layout receipt must exist before constant state attaches");

    DevicePair r244ForeignDevice = create_warp_device();
    ID3D11Buffer* r244ForeignVertexConstants =
        create_constant_buffer(r244ForeignDevice.device, r244ConstantBytes);
    ID3D11Buffer* r244ForeignPixelConstants =
        create_constant_buffer(r244ForeignDevice.device, r244ConstantBytes);
    require(
        !programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ForeignVertexConstants, r244ConstantBytes,
            r244ForeignPixelConstants, r244ConstantBytes),
        "R244 foreign-device constant buffers fail closed");
    r244ForeignVertexConstants->Release();
    r244ForeignPixelConstants->Release();
    r244ForeignDevice.context->Release();
    r244ForeignDevice.device->Release();

    require(
        programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244VertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes),
        "R244 attach exact constant state to R243 input layout receipt");
    const auto r244ConstantStateReady =
        programmableCache.constant_state_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken);
    require(
        r244ConstantStateReady.inputValid &&
        r244ConstantStateReady.inputLayoutReceiptReady &&
        r244ConstantStateReady.deviceMatches &&
        r244ConstantStateReady.inputLayoutSnapshotMatches &&
        r244ConstantStateReady.constantBuffersAttached &&
        r244ConstantStateReady.constantBufferDevicesMatch &&
        r244ConstantStateReady.constantBufferDescriptorsExact &&
        r244ConstantStateReady.attachmentReady &&
        r244ConstantStateReady.constantStateReceiptGeneration != 0 &&
        r244ConstantStateReady.vertexConstantBytes == r244ConstantBytes &&
        r244ConstantStateReady.pixelConstantBytes == r244ConstantBytes &&
        r244ConstantStateReady.snapshotToken != 0 &&
        programmableCache.validate_constant_state_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken),
        "R244 constant-state receipt seals exact R243 ownership and descriptors");
    const auto firstR244ReceiptGeneration =
        r244ConstantStateReady.constantStateReceiptGeneration;
    const auto firstR244ConstantStateSnapshot =
        r244ConstantStateReady.snapshotToken;
    require(
        programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244VertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes) &&
        programmableCache.constant_state_readiness(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken).snapshotToken ==
            firstR244ConstantStateSnapshot,
        "R244 same constant-state attachment is idempotent");
    require(
        !programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244VertexConstants, r244ConstantBytes + 16u,
            r244PixelConstants, r244ConstantBytes),
        "R244 changed constant metadata cannot reuse sealed receipt");
    ID3D11Buffer* r244ReplacementVertexConstants =
        create_constant_buffer(d3d.device, r244ConstantBytes);
    require(
        !programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ReplacementVertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes),
        "R244 different constant buffer object cannot replace sealed receipt");
    r244ReplacementVertexConstants->Release();

    const std::array<std::uint32_t, 16> r245VertexPayload = {
        0x3f800000u, 0x40000000u, 0x40400000u, 0x40800000u,
        0x40a00000u, 0x40c00000u, 0x40e00000u, 0x41000000u,
        0x41100000u, 0x41200000u, 0x41300000u, 0x41400000u,
        0x41500000u, 0x41600000u, 0x41700000u, 0x41800000u,
    };
    const std::array<std::uint32_t, 16> r245PixelPayload = {
        0x3dcccccdU, 0x3e4ccccdU, 0x3e99999aU, 0x3ecccccdU,
        0x3f000000U, 0x3f19999aU, 0x3f333333U, 0x3f4ccccdU,
        0x3f666666U, 0x3f800000U, 0x3f8ccccdU, 0x3f99999aU,
        0x3fa66666U, 0x3fb33333U, 0x3fc00000U, 0x3fcccccdU,
    };
    static_assert(sizeof(r245VertexPayload) == r244ConstantBytes);
    static_assert(sizeof(r245PixelPayload) == r244ConstantBytes);
    const auto r245UnuploadedPayload =
        programmableCache.constant_payload_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken);
    require(
        r245UnuploadedPayload.inputValid &&
        r245UnuploadedPayload.constantStateReceiptReady &&
        r245UnuploadedPayload.deviceMatches &&
        r245UnuploadedPayload.contextDeviceMatches &&
        r245UnuploadedPayload.constantStateSnapshotMatches &&
        !r245UnuploadedPayload.payloadReceiptPresent &&
        !r245UnuploadedPayload.uploadReady &&
        r245UnuploadedPayload.constantPayloadReceiptGeneration == 0 &&
        r245UnuploadedPayload.snapshotToken == 0 &&
        !programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken, 0,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 constant-state receipt must exist before payload upload");

    ID3D11DeviceContext* r245DeferredBeforeUpload = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r245DeferredBeforeUpload)) &&
        r245DeferredBeforeUpload != nullptr &&
        !programmableCache.upload_constant_payload_for_observation(
            r245DeferredBeforeUpload, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 deferred context cannot establish upload receipt");
    r245DeferredBeforeUpload->Release();

    DevicePair r245ForeignDevice = create_warp_device();
    require(
        !programmableCache.upload_constant_payload_for_observation(
            r245ForeignDevice.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 foreign-device context fails closed");
    r245ForeignDevice.context->Release();
    r245ForeignDevice.device->Release();

    require(
        programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 exact constant payload upload to R244-owned buffers");
    const auto r245PayloadReady =
        programmableCache.constant_payload_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken);
    require(
        r245PayloadReady.inputValid &&
        r245PayloadReady.constantStateReceiptReady &&
        r245PayloadReady.deviceMatches &&
        r245PayloadReady.contextDeviceMatches &&
        r245PayloadReady.constantStateSnapshotMatches &&
        r245PayloadReady.payloadReceiptPresent &&
        r245PayloadReady.payloadBytesExact &&
        r245PayloadReady.uploadReady &&
        r245PayloadReady.constantPayloadReceiptGeneration != 0 &&
        r245PayloadReady.vertexPayloadHash != 0 &&
        r245PayloadReady.pixelPayloadHash != 0 &&
        r245PayloadReady.snapshotToken != 0 &&
        programmableCache.validate_constant_payload_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken),
        "R245 exact constant payload upload receipt");
    const auto firstR245ReceiptGeneration =
        r245PayloadReady.constantPayloadReceiptGeneration;
    const auto firstR245PayloadSnapshot = r245PayloadReady.snapshotToken;
    require(
        programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes) &&
        programmableCache.constant_payload_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken).snapshotToken ==
            firstR245PayloadSnapshot,
        "R245 same constant payload upload is idempotent");

    auto r245ChangedVertexPayload = r245VertexPayload;
    r245ChangedVertexPayload[0] ^= 0x00000001u;
    require(
        !programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245ChangedVertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 changed constant payload cannot reuse sealed receipt");

    ID3D11DeviceContext* r245ReplacementContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r245ReplacementContext)) &&
        r245ReplacementContext != nullptr &&
        r245ReplacementContext != d3d.context &&
        !programmableCache.upload_constant_payload_for_observation(
            r245ReplacementContext, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 different same-device context cannot replace sealed receipt");
    r245ReplacementContext->Release();

    const auto r246UnboundSlots =
        programmableCache.constant_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken);
    require(
        r246UnboundSlots.inputValid &&
        r246UnboundSlots.constantPayloadReceiptReady &&
        r246UnboundSlots.deviceMatches &&
        r246UnboundSlots.contextDeviceMatches &&
        r246UnboundSlots.constantPayloadSnapshotMatches &&
        !r246UnboundSlots.bindingReceiptPresent &&
        !r246UnboundSlots.bindingReady &&
        r246UnboundSlots.constantBindingReceiptGeneration == 0 &&
        r246UnboundSlots.snapshotToken == 0 &&
        !programmableCache.bind_constant_slots_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken, 0),
        "R246 constant-payload receipt must exist before slot binding");

    ID3D11DeviceContext* r246DeferredBeforeBinding = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r246DeferredBeforeBinding)) &&
        r246DeferredBeforeBinding != nullptr &&
        !programmableCache.bind_constant_slots_for_observation(
            r246DeferredBeforeBinding, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken),
        "R246 non-immediate context cannot establish slot binding");
    r246DeferredBeforeBinding->Release();

    require(
        programmableCache.bind_constant_slots_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken),
        "R246 exact VS/PS b0 constant-slot binding");
    const auto r246BindingReady =
        programmableCache.constant_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken);
    require(
        r246BindingReady.inputValid &&
        r246BindingReady.constantPayloadReceiptReady &&
        r246BindingReady.deviceMatches &&
        r246BindingReady.contextDeviceMatches &&
        r246BindingReady.constantPayloadSnapshotMatches &&
        r246BindingReady.bindingReceiptPresent &&
        r246BindingReady.vertexSlotMatches &&
        r246BindingReady.pixelSlotMatches &&
        r246BindingReady.bindingReady &&
        r246BindingReady.constantBindingReceiptGeneration != 0 &&
        r246BindingReady.snapshotToken != 0 &&
        programmableCache.validate_constant_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken),
        "R246 exact constant-slot binding receipt");
    const auto firstR246ReceiptGeneration =
        r246BindingReady.constantBindingReceiptGeneration;
    const auto firstR246BindingSnapshot =
        r246BindingReady.snapshotToken;
    require(
        programmableCache.bind_constant_slots_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken) &&
        programmableCache.constant_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken).snapshotToken ==
            firstR246BindingSnapshot,
        "R246 same constant-slot binding is idempotent");

    const auto r247UnboundPipeline =
        programmableCache.pipeline_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken);
    require(
        r247UnboundPipeline.inputValid &&
        r247UnboundPipeline.constantBindingReceiptReady &&
        r247UnboundPipeline.deviceMatches &&
        r247UnboundPipeline.contextDeviceMatches &&
        r247UnboundPipeline.constantBindingSnapshotMatches &&
        !r247UnboundPipeline.bindingReceiptPresent &&
        !r247UnboundPipeline.bindingReady &&
        r247UnboundPipeline.pipelineBindingReceiptGeneration == 0 &&
        r247UnboundPipeline.snapshotToken == 0 &&
        !programmableCache.bind_pipeline_objects_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken, 0),
        "R247 constant-binding receipt must exist before pipeline binding");

    ID3D11DeviceContext* r247DeferredBeforeBinding = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r247DeferredBeforeBinding)) &&
        r247DeferredBeforeBinding != nullptr &&
        !programmableCache.bind_pipeline_objects_for_observation(
            r247DeferredBeforeBinding, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken),
        "R247 non-immediate context cannot establish pipeline binding");
    r247DeferredBeforeBinding->Release();

    require(
        programmableCache.bind_pipeline_objects_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken),
        "R247 exact VS/PS/input-layout pipeline binding");
    const auto r247PipelineReady =
        programmableCache.pipeline_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken);
    require(
        r247PipelineReady.bindingReady &&
        r247PipelineReady.bindingReceiptPresent &&
        r247PipelineReady.vertexShaderMatches &&
        r247PipelineReady.pixelShaderMatches &&
        r247PipelineReady.inputLayoutMatches &&
        r247PipelineReady.pipelineBindingReceiptGeneration != 0 &&
        r247PipelineReady.snapshotToken != 0 &&
        programmableCache.validate_pipeline_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken),
        "R247 exact programmable pipeline binding receipt");
    const auto firstR247ReceiptGeneration =
        r247PipelineReady.pipelineBindingReceiptGeneration;
    const auto firstR247BindingSnapshot =
        r247PipelineReady.snapshotToken;
    require(
        programmableCache.bind_pipeline_objects_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken) &&
        programmableCache.pipeline_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken).snapshotToken ==
            firstR247BindingSnapshot,
        "R247 same programmable pipeline binding is idempotent");

    const auto r248UnboundTopology =
        programmableCache.primitive_topology_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST);
    require(
        r248UnboundTopology.inputValid &&
        r248UnboundTopology.pipelineBindingReceiptReady &&
        r248UnboundTopology.deviceMatches &&
        r248UnboundTopology.contextDeviceMatches &&
        r248UnboundTopology.pipelineBindingSnapshotMatches &&
        r248UnboundTopology.topologyExact &&
        !r248UnboundTopology.topologyReceiptPresent &&
        !r248UnboundTopology.bindingReady &&
        r248UnboundTopology.topologyBindingReceiptGeneration == 0 &&
        r248UnboundTopology.snapshotToken == 0 &&
        !programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            0, D3DPT_TRIANGLELIST),
        "R248 pipeline-binding receipt must exist before topology binding");

    require(
        !programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLEFAN),
        "R248 triangle fan direct topology remains fail closed");

    ID3D11DeviceContext* r248DeferredBeforeBinding = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r248DeferredBeforeBinding)) &&
        r248DeferredBeforeBinding != nullptr &&
        !programmableCache.bind_primitive_topology_for_observation(
            r248DeferredBeforeBinding, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST),
        "R248 non-immediate context cannot establish topology binding");
    r248DeferredBeforeBinding->Release();

    require(
        programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST),
        "R248 exact translated primitive topology binding");
    const auto r248TopologyReady =
        programmableCache.primitive_topology_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST);
    require(
        r248TopologyReady.bindingReady &&
        r248TopologyReady.topologyReceiptPresent &&
        r248TopologyReady.topologyMatches &&
        r248TopologyReady.topologyExact &&
        r248TopologyReady.translatedTopology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
        r248TopologyReady.topologyBindingReceiptGeneration != 0 &&
        r248TopologyReady.snapshotToken != 0 &&
        programmableCache.validate_primitive_topology_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken),
        "R248 exact primitive topology binding receipt");
    const auto firstR248ReceiptGeneration =
        r248TopologyReady.topologyBindingReceiptGeneration;
    const auto firstR248BindingSnapshot =
        r248TopologyReady.snapshotToken;
    require(
        programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST) &&
        programmableCache.primitive_topology_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST).snapshotToken ==
            firstR248BindingSnapshot,
        "R248 same primitive topology binding is idempotent");

    const auto r249UnboundGeometry =
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        r249UnboundGeometry.inputValid &&
        r249UnboundGeometry.topologyBindingReceiptReady &&
        r249UnboundGeometry.topologyBindingSnapshotMatches &&
        r249UnboundGeometry.vertexBufferCurrent &&
        r249UnboundGeometry.indexBufferCurrent &&
        !r249UnboundGeometry.geometryReceiptPresent &&
        !r249UnboundGeometry.bindingReady &&
        r249UnboundGeometry.indexedGeometryBindingReceiptGeneration == 0 &&
        r249UnboundGeometry.snapshotToken == 0 &&
        !programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST, 0,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 topology-binding receipt must exist before indexed geometry binding");

    require(
        !programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken ^ 1ull,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        !programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken ^ 1ull,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 stale managed mirror snapshots cannot bind indexed geometry");

    ID3D11DeviceContext* r249DeferredBeforeBinding = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r249DeferredBeforeBinding)) &&
        r249DeferredBeforeBinding != nullptr &&
        !programmableCache.bind_indexed_geometry_for_observation(
            r249DeferredBeforeBinding, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 non-immediate context cannot establish indexed geometry binding");
    r249DeferredBeforeBinding->Release();

    require(
        programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 exact programmable indexed IA geometry binding");
    const auto r249GeometryReady =
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        r249GeometryReady.bindingReady &&
        r249GeometryReady.geometryReceiptPresent &&
        r249GeometryReady.vertexBufferMatches &&
        r249GeometryReady.indexBufferMatches &&
        r249GeometryReady.indexedGeometryBindingReceiptGeneration != 0 &&
        r249GeometryReady.snapshotToken != 0 &&
        programmableCache.validate_indexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r249GeometryReady.snapshotToken),
        "R249 exact programmable indexed geometry binding receipt");
    const auto firstR249ReceiptGeneration =
        r249GeometryReady.indexedGeometryBindingReceiptGeneration;
    const auto firstR249BindingSnapshot = r249GeometryReady.snapshotToken;

    const auto r252DispatchReady =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u);
    require(
        r252DispatchReady.inputValid &&
        r252DispatchReady.geometryBindingReady &&
        r252DispatchReady.geometryBindingSnapshotMatches &&
        r252DispatchReady.primitiveExact &&
        r252DispatchReady.topologyMatchesGeometry &&
        r252DispatchReady.countExact &&
        r252DispatchReady.sourceVertexRangeExact &&
        r252DispatchReady.effectiveVertexRangeExact &&
        r252DispatchReady.indexBufferRangeExact &&
        r252DispatchReady.vertexBufferRangeExact &&
        r252DispatchReady.dispatchArgumentsExact &&
        r252DispatchReady.componentSnapshotsPresent &&
        r252DispatchReady.ready &&
        r252DispatchReady.indexCount == 3u &&
        r252DispatchReady.maxVertexIndex == 3u &&
        r252DispatchReady.vertexBufferByteWidth ==
            managedVertexBuffer.byte_width() &&
        r252DispatchReady.indexBufferByteWidth ==
            managedIndexBuffer.byte_width() &&
        r252DispatchReady.snapshotToken != 0 &&
        programmableCache.validate_indexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, r252DispatchReady.snapshotToken),
        "R252 exact programmable indexed dispatch and source range");
    const auto firstR252DispatchSnapshot = r252DispatchReady.snapshotToken;

    const auto r253SourceValuesReady =
        programmableCache.indexed_source_value_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot);
    require(
        r253SourceValuesReady.inputValid &&
        r253SourceValuesReady.directDispatchReady &&
        r253SourceValuesReady.directDispatchSnapshotMatches &&
        r253SourceValuesReady.indexMirrorReady &&
        r253SourceValuesReady.indexMirrorSnapshotMatches &&
        r253SourceValuesReady.indexFormatExact &&
        r253SourceValuesReady.sourceValuesReady &&
        r253SourceValuesReady.sourceValuesMatchDispatchWindow &&
        r253SourceValuesReady.sourceValuesMatchDispatchRange &&
        r253SourceValuesReady.componentSnapshotsPresent &&
        r253SourceValuesReady.ready &&
        r253SourceValuesReady.sourceIndexFormat == D3DFMT_INDEX16 &&
        r253SourceValuesReady.scanStartIndex == 0u &&
        r253SourceValuesReady.indexCount == 3u &&
        r253SourceValuesReady.minVertexIndex == 0u &&
        r253SourceValuesReady.maxVertexIndex == 3u &&
        r253SourceValuesReady.observedMinIndex == 0u &&
        r253SourceValuesReady.observedMaxIndex == 2u &&
        r253SourceValuesReady.sourceContentHash != 0 &&
        r253SourceValuesReady.snapshotToken != 0 &&
        programmableCache.validate_indexed_source_value_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot,
            r253SourceValuesReady.snapshotToken),
        "R253 programmable indexed source values seal exact managed IB contents");
    const auto firstR253SourceValueSnapshot =
        r253SourceValuesReady.snapshotToken;

    const auto r254LiveIndexReady =
        programmableCache.indexed_live_index_binding_readiness(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot);
    require(
        r254LiveIndexReady.inputValid &&
        r254LiveIndexReady.sourceValueReady &&
        r254LiveIndexReady.sourceValueSnapshotMatches &&
        r254LiveIndexReady.sourceValueFormatMatches &&
        r254LiveIndexReady.indexMirrorReady &&
        r254LiveIndexReady.indexMirrorSnapshotMatches &&
        r254LiveIndexReady.contextDeviceMatches &&
        r254LiveIndexReady.liveIndexBufferMatches &&
        r254LiveIndexReady.liveIndexFormatMatches &&
        r254LiveIndexReady.liveIndexOffsetMatches &&
        r254LiveIndexReady.componentSnapshotsPresent &&
        r254LiveIndexReady.ready &&
        r254LiveIndexReady.expectedIndexFormat == DXGI_FORMAT_R16_UINT &&
        r254LiveIndexReady.observedIndexFormat == DXGI_FORMAT_R16_UINT &&
        r254LiveIndexReady.expectedIndexOffset == geometryIndexOffset &&
        r254LiveIndexReady.observedIndexOffset == geometryIndexOffset &&
        r254LiveIndexReady.expectedIndexBufferIdentity != 0 &&
        r254LiveIndexReady.expectedIndexBufferIdentity ==
            r254LiveIndexReady.observedIndexBufferIdentity &&
        r254LiveIndexReady.snapshotToken != 0 &&
        programmableCache.validate_indexed_live_index_binding_snapshot(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot,
            r254LiveIndexReady.snapshotToken),
        "R254 seals fresh live IA index buffer format and offset after R253");
    const auto firstR254LiveIndexSnapshot = r254LiveIndexReady.snapshotToken;

    d3d.context->IASetIndexBuffer(
        nullptr, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    const auto r254MissingLiveIndex =
        programmableCache.indexed_live_index_binding_readiness(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot);
    require(
        r254MissingLiveIndex.sourceValueSnapshotMatches &&
        !r254MissingLiveIndex.liveIndexBufferMatches &&
        !r254MissingLiveIndex.ready &&
        r254MissingLiveIndex.snapshotToken == 0 &&
        !programmableCache.validate_indexed_live_index_binding_snapshot(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot),
        "R254 rejects live IA index-buffer identity drift");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(),
        DXGI_FORMAT_R32_UINT, geometryIndexOffset);
    const auto r254FormatDrift =
        programmableCache.indexed_live_index_binding_readiness(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot);
    require(
        r254FormatDrift.liveIndexBufferMatches &&
        !r254FormatDrift.liveIndexFormatMatches &&
        !r254FormatDrift.ready &&
        r254FormatDrift.snapshotToken == 0,
        "R254 rejects live IA index-format drift");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(),
        DXGI_FORMAT_R16_UINT, geometryIndexOffset + 2u);
    const auto r254OffsetDrift =
        programmableCache.indexed_live_index_binding_readiness(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot);
    require(
        r254OffsetDrift.liveIndexBufferMatches &&
        r254OffsetDrift.liveIndexFormatMatches &&
        !r254OffsetDrift.liveIndexOffsetMatches &&
        !r254OffsetDrift.ready &&
        r254OffsetDrift.snapshotToken == 0,
        "R254 rejects live IA index-offset drift");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(),
        DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        programmableCache.validate_indexed_live_index_binding_snapshot(
            d3d.context, d3d.device,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r253SourceValuesReady, firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot),
        "R254 fresh live IA receipt revalidates after exact binding restore");

    const auto r255PreDrawReadiness =
        [&](std::uint64_t directDispatchSnapshotToken,
            std::uint64_t sourceValueSnapshotToken,
            std::uint64_t liveIndexBindingSnapshotToken) {
            return programmableCache.indexed_pre_draw_readiness(
                d3d.context, d3d.device, programmablePair,
                r242CacheReady.snapshotToken,
                r242SlotReady.snapshotToken,
                r242ObjectReady.snapshotToken,
                inputLayout, r243InputLayoutReady.snapshotToken,
                r244ConstantStateReady.snapshotToken,
                r245PayloadReady.snapshotToken,
                r246BindingReady.snapshotToken,
                r247PipelineReady.snapshotToken,
                D3DPT_TRIANGLELIST,
                r248TopologyReady.snapshotToken,
                managedVertexBuffer,
                managedVertexPostResetReady.snapshotToken,
                geometryVertexStride, geometryVertexOffset,
                managedIndexBuffer, managedIndexReady.snapshotToken,
                DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                firstR249BindingSnapshot,
                1u, 0, 0u, 4u, 0u,
                directDispatchSnapshotToken,
                sourceValueSnapshotToken,
                liveIndexBindingSnapshotToken);
        };
    const auto validateR255PreDraw =
        [&](std::uint64_t directDispatchSnapshotToken,
            std::uint64_t sourceValueSnapshotToken,
            std::uint64_t liveIndexBindingSnapshotToken,
            std::uint64_t preDrawSnapshotToken) {
            return programmableCache.validate_indexed_pre_draw_snapshot(
                d3d.context, d3d.device, programmablePair,
                r242CacheReady.snapshotToken,
                r242SlotReady.snapshotToken,
                r242ObjectReady.snapshotToken,
                inputLayout, r243InputLayoutReady.snapshotToken,
                r244ConstantStateReady.snapshotToken,
                r245PayloadReady.snapshotToken,
                r246BindingReady.snapshotToken,
                r247PipelineReady.snapshotToken,
                D3DPT_TRIANGLELIST,
                r248TopologyReady.snapshotToken,
                managedVertexBuffer,
                managedVertexPostResetReady.snapshotToken,
                geometryVertexStride, geometryVertexOffset,
                managedIndexBuffer, managedIndexReady.snapshotToken,
                DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                firstR249BindingSnapshot,
                1u, 0, 0u, 4u, 0u,
                directDispatchSnapshotToken,
                sourceValueSnapshotToken,
                liveIndexBindingSnapshotToken,
                preDrawSnapshotToken);
        };

    const auto r255PreDrawReady = r255PreDrawReadiness(
        firstR252DispatchSnapshot,
        firstR253SourceValueSnapshot,
        firstR254LiveIndexSnapshot);
    require(
        r255PreDrawReady.inputValid &&
        r255PreDrawReady.directDispatchReady &&
        r255PreDrawReady.directDispatchSnapshotMatches &&
        r255PreDrawReady.sourceValueReady &&
        r255PreDrawReady.sourceValueSnapshotMatches &&
        r255PreDrawReady.liveIndexBindingReady &&
        r255PreDrawReady.liveIndexBindingSnapshotMatches &&
        r255PreDrawReady.dispatchSourceLineageMatches &&
        r255PreDrawReady.sourceLiveLineageMatches &&
        r255PreDrawReady.componentSnapshotsPresent &&
        r255PreDrawReady.ready &&
        r255PreDrawReady.indexCount == 3u &&
        r255PreDrawReady.startIndexLocation == 0u &&
        r255PreDrawReady.indexFormat == DXGI_FORMAT_R16_UINT &&
        r255PreDrawReady.indexOffset == geometryIndexOffset &&
        r255PreDrawReady.snapshotToken != 0 &&
        validateR255PreDraw(
            firstR252DispatchSnapshot,
            firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot,
            r255PreDrawReady.snapshotToken),
        "R255 joins current R252 R253 and R254 receipts into final indexed pre-Draw proof");
    const auto firstR255PreDrawSnapshot = r255PreDrawReady.snapshotToken;

    const auto staleR252DispatchSnapshot =
        firstR252DispatchSnapshot == 1ull ? 2ull : 1ull;
    const auto r255StaleDispatch = r255PreDrawReadiness(
        staleR252DispatchSnapshot,
        firstR253SourceValueSnapshot,
        firstR254LiveIndexSnapshot);
    require(
        !r255StaleDispatch.directDispatchSnapshotMatches &&
        !r255StaleDispatch.ready &&
        r255StaleDispatch.snapshotToken == 0,
        "R255 rejects stale R252 dispatch receipt");

    const auto staleR253SourceValueSnapshot =
        firstR253SourceValueSnapshot == 1ull ? 2ull : 1ull;
    const auto r255StaleSource = r255PreDrawReadiness(
        firstR252DispatchSnapshot,
        staleR253SourceValueSnapshot,
        firstR254LiveIndexSnapshot);
    require(
        r255StaleSource.directDispatchSnapshotMatches &&
        !r255StaleSource.sourceValueSnapshotMatches &&
        !r255StaleSource.ready &&
        r255StaleSource.snapshotToken == 0,
        "R255 rejects stale R253 source-value receipt");

    const auto staleR254LiveIndexSnapshot =
        firstR254LiveIndexSnapshot == 1ull ? 2ull : 1ull;
    const auto r255StaleLive = r255PreDrawReadiness(
        firstR252DispatchSnapshot,
        firstR253SourceValueSnapshot,
        staleR254LiveIndexSnapshot);
    require(
        r255StaleLive.directDispatchSnapshotMatches &&
        r255StaleLive.sourceValueSnapshotMatches &&
        r255StaleLive.liveIndexBindingReady &&
        !r255StaleLive.liveIndexBindingSnapshotMatches &&
        !r255StaleLive.ready &&
        r255StaleLive.snapshotToken == 0,
        "R255 rejects stale R254 live IA receipt");

    require(
        validateR255PreDraw(
            firstR252DispatchSnapshot,
            firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot,
            firstR255PreDrawSnapshot),
        "R255 final indexed pre-Draw receipt revalidates while all inputs remain current");

    const auto r256IndexedCandidate =
        outrun::vr::dx11::compose_programmable_draw_candidate_readiness(
            r255PreDrawReady, firstR255PreDrawSnapshot);
    require(
        r256IndexedCandidate.inputValid &&
        r256IndexedCandidate.selectedReceiptReady &&
        r256IndexedCandidate.selectedReceiptSnapshotMatches &&
        r256IndexedCandidate.componentSnapshotsPresent &&
        r256IndexedCandidate.ready &&
        r256IndexedCandidate.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::Indexed &&
        r256IndexedCandidate.indexed &&
        r256IndexedCandidate.elementCount == 3u &&
        r256IndexedCandidate.startLocation == 0u &&
        r256IndexedCandidate.baseVertexIndex == 0 &&
        r256IndexedCandidate.minVertexIndex == 0u &&
        r256IndexedCandidate.numVertices == 4u &&
        r256IndexedCandidate.indexFormat == DXGI_FORMAT_R16_UINT &&
        r256IndexedCandidate.indexOffset == geometryIndexOffset &&
        r256IndexedCandidate.sourceReceiptSnapshotToken ==
            firstR255PreDrawSnapshot &&
        r256IndexedCandidate.snapshotToken != 0 &&
        outrun::vr::dx11::validate_programmable_draw_candidate_snapshot(
            r255PreDrawReady, firstR255PreDrawSnapshot,
            r256IndexedCandidate.snapshotToken),
        "R256 indexed draw-candidate union accepts current R255 receipt");
    const auto staleR255CandidateSource =
        firstR255PreDrawSnapshot == 1ull ? 2ull : 1ull;
    const auto r256IndexedStale =
        outrun::vr::dx11::compose_programmable_draw_candidate_readiness(
            r255PreDrawReady, staleR255CandidateSource);
    require(
        r256IndexedStale.selectedReceiptReady &&
        !r256IndexedStale.selectedReceiptSnapshotMatches &&
        !r256IndexedStale.ready &&
        r256IndexedStale.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_programmable_draw_candidate_snapshot(
            r255PreDrawReady, staleR255CandidateSource,
            r256IndexedCandidate.snapshotToken),
        "R256 indexed draw-candidate union rejects stale R255 receipt");

    const auto r257IndexedPreActivation =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            r256IndexedCandidate, r256IndexedCandidate.snapshotToken);
    require(
        r257IndexedPreActivation.inputValid &&
        r257IndexedPreActivation.candidateReady &&
        r257IndexedPreActivation.candidateSnapshotMatches &&
        r257IndexedPreActivation.candidatePayloadSnapshotMatches &&
        r257IndexedPreActivation.candidateKindValid &&
        r257IndexedPreActivation.diagnosticOnly &&
        !r257IndexedPreActivation.activationProofPresent &&
        !r257IndexedPreActivation.nativeDrawPathActivationAllowed &&
        !r257IndexedPreActivation.drawDispatchAuthorized &&
        r257IndexedPreActivation.boundaryPreserved &&
        r257IndexedPreActivation.ready &&
        r257IndexedPreActivation.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::Indexed &&
        r257IndexedPreActivation.indexed &&
        r257IndexedPreActivation.candidateSnapshotToken ==
            r256IndexedCandidate.snapshotToken &&
        r257IndexedPreActivation.snapshotToken != 0 &&
        outrun::vr::dx11::validate_programmable_dormant_pre_activation_snapshot(
            r256IndexedCandidate, r256IndexedCandidate.snapshotToken,
            r257IndexedPreActivation.snapshotToken),
        "R257 indexed candidate seals dormant pre-activation review without draw authorization");

    const auto staleR256IndexedSnapshot =
        r256IndexedCandidate.snapshotToken == 1ull
            ? 2ull
            : (r256IndexedCandidate.snapshotToken ^ 1ull);
    const auto r257IndexedStale =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            r256IndexedCandidate, staleR256IndexedSnapshot);
    require(
        r257IndexedStale.candidateReady &&
        !r257IndexedStale.candidateSnapshotMatches &&
        !r257IndexedStale.ready &&
        r257IndexedStale.snapshotToken == 0,
        "R257 rejects stale R256 indexed candidate token");

    auto tamperedR256IndexedCandidate = r256IndexedCandidate;
    tamperedR256IndexedCandidate.baseVertexIndex += 1;
    const auto r257IndexedTampered =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            tamperedR256IndexedCandidate,
            tamperedR256IndexedCandidate.snapshotToken);
    require(
        r257IndexedTampered.candidateSnapshotMatches &&
        !r257IndexedTampered.candidatePayloadSnapshotMatches &&
        !r257IndexedTampered.ready &&
        r257IndexedTampered.snapshotToken == 0,
        "R257 rejects indexed source-range drift hidden behind an unchanged R256 snapshot token");

    const auto r258IndexedSourceRevalidation =
        programmableCache.indexed_dormant_source_revalidation_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u,
            firstR252DispatchSnapshot,
            firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot,
            r256IndexedCandidate.snapshotToken,
            r257IndexedPreActivation.snapshotToken);
    require(
        r258IndexedSourceRevalidation.inputValid &&
        r258IndexedSourceRevalidation.sourceReceiptReady &&
        r258IndexedSourceRevalidation.sourceReceiptSnapshotPresent &&
        r258IndexedSourceRevalidation.candidateReady &&
        r258IndexedSourceRevalidation.candidateSnapshotMatches &&
        r258IndexedSourceRevalidation.preActivationReady &&
        r258IndexedSourceRevalidation.preActivationSnapshotMatches &&
        r258IndexedSourceRevalidation.sourceLineageMatches &&
        r258IndexedSourceRevalidation.candidateLineageMatches &&
        r258IndexedSourceRevalidation.cacheKey == programmablePair.cacheKey &&
        r258IndexedSourceRevalidation.boundaryPreserved &&
        r258IndexedSourceRevalidation.ready &&
        r258IndexedSourceRevalidation.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::Indexed &&
        r258IndexedSourceRevalidation.indexed &&
        r258IndexedSourceRevalidation.baseVertexIndex == 0 &&
        r258IndexedSourceRevalidation.minVertexIndex == 0u &&
        r258IndexedSourceRevalidation.numVertices == 4u &&
        r258IndexedSourceRevalidation.currentSourceReceiptSnapshotToken ==
            firstR255PreDrawSnapshot &&
        r258IndexedSourceRevalidation.candidateSnapshotToken ==
            r256IndexedCandidate.snapshotToken &&
        r258IndexedSourceRevalidation.preActivationSnapshotToken ==
            r257IndexedPreActivation.snapshotToken &&
        r258IndexedSourceRevalidation.snapshotToken != 0,
        "R258 indexed final dormant handoff revalidates current R255 source state");

    NativeManagedTextureRegistry r261TextureRegistry;
    int r261TextureKey = 0;
    require(
        r261TextureRegistry.register_texture(
            &r261TextureKey, D3DFMT_A8R8G8B8, 4, 4, 1, 0,
            D3DPOOL_MANAGED),
        "R261 texture registry accepts exact managed stage resource");
    std::array<unsigned char, 64> r261TexturePixels{};
    for (std::size_t i = 0; i < r261TexturePixels.size(); ++i)
        r261TexturePixels[i] = static_cast<unsigned char>(0x40u + (i & 0x1fu));
    D3DLOCKED_RECT r261TextureLock{};
    r261TextureLock.Pitch = 16;
    r261TextureLock.pBits = r261TexturePixels.data();
    require(
        r261TextureRegistry.begin_source_lock(
            &r261TextureKey, 0, nullptr, 0, r261TextureLock) &&
        r261TextureRegistry.stage_source_unlock(&r261TextureKey, 0) &&
        r261TextureRegistry.finish_source_unlock(
            &r261TextureKey, 0, S_OK) &&
        r261TextureRegistry.recreate_and_upload_mirror_for_observation(
            &r261TextureKey, d3d.device),
        "R261 texture stage builds current managed shadow and mirror");
    const std::array<const void*, 1> r261TextureKeys{&r261TextureKey};
    const auto r261TextureStages =
        r261TextureRegistry.mirror_readiness_for_stages(
            r261TextureKeys.data(), r261TextureKeys.size(),
            0x1u, d3d.device);
    require(
        r261TextureStages.inputValid &&
        r261TextureStages.allRequiredReady &&
        r261TextureStages.registeredMask == 0x1u &&
        r261TextureStages.shadowValidMask == 0x1u &&
        r261TextureStages.resourcesOwnedMask == 0x1u &&
        r261TextureStages.lifetimeCurrentMask == 0x1u &&
        r261TextureStages.deviceMatchesMask == 0x1u &&
        r261TextureStages.descriptorExactMask == 0x1u &&
        r261TextureStages.readyMask == 0x1u &&
        r261TextureStages.pendingMask == 0 &&
        r261TextureStages.snapshotToken != 0 &&
        r261TextureRegistry.validate_mirror_readiness_snapshot_for_stages(
            r261TextureKeys.data(), r261TextureKeys.size(),
            0x1u, d3d.device, r261TextureStages.snapshotToken),
        "R261 texture stage prerequisite seals current managed texture behavior");

    outrun::vr::dx11::NativeSurfaceMirror r262OutputColorSurface;
    require(
        r262OutputColorSurface.initialize(
            d3d.device, ResourceRole::Color, 64u, 32u,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE, 0u),
        "R262 output color surface preserves exact render-target descriptor");
    outrun::vr::dx11::NativeSurfaceMirror r262OutputDepthSurface;
    require(
        r262OutputDepthSurface.initialize(
            d3d.device, ResourceRole::DepthStencil, 64u, 32u,
            D3DFMT_D24S8, D3DPOOL_DEFAULT, D3DUSAGE_DEPTHSTENCIL,
            D3DMULTISAMPLE_NONE, 0u),
        "R262 output depth surface preserves exact depth-stencil descriptor");
    const auto r262SurfacePair =
        outrun::vr::dx11::compose_surface_pair_readiness(
            d3d.device, r262OutputColorSurface, r262OutputDepthSurface);
    require(
        r262SurfacePair.ready &&
        r262SurfacePair.snapshotToken != 0 &&
        outrun::vr::dx11::validate_surface_pair_snapshot(
            d3d.device, r262OutputColorSurface, r262OutputDepthSurface,
            r262SurfacePair.snapshotToken),
        "R262 output surface pair seals exact descriptor and generation identity");
    outrun::vr::dx11::NativeSurfacePairBinding r262SurfaceBinding;
    require(
        r262SurfaceBinding.initialize(
            d3d.device, r262OutputColorSurface, r262OutputDepthSurface,
            r262SurfacePair) &&
        r262SurfaceBinding.apply(
            d3d.context, r262OutputColorSurface, r262OutputDepthSurface),
        "R262 output binding applies exact current RTV DSV pair");
    const auto r262SurfaceBindingReady =
        r262SurfaceBinding.binding_readiness(
            d3d.context, r262OutputColorSurface, r262OutputDepthSurface);
    require(
        r262SurfaceBindingReady.ready &&
        r262SurfaceBindingReady.surfacePairSnapshotToken ==
            r262SurfacePair.snapshotToken &&
        r262SurfaceBindingReady.unorderedAccessClear &&
        r262SurfaceBindingReady.snapshotToken != 0 &&
        r262SurfaceBinding.validate_binding_snapshot(
            d3d.context, r262OutputColorSurface, r262OutputDepthSurface,
            r262SurfaceBindingReady.snapshotToken),
        "R262 output binding seals live RTV DSV identity with UAVs clear");

    const auto r260IndexedResourceBehavior =
        outrun::vr::dx11::compose_programmable_resource_behavior_readiness(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            d3d.device,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            &managedIndexBuffer,
            managedIndexReady.snapshotToken);
    require(
        r260IndexedResourceBehavior.inputValid &&
        r260IndexedResourceBehavior.sourceRevalidationReady &&
        r260IndexedResourceBehavior.sourceRevalidationSnapshotMatches &&
        r260IndexedResourceBehavior.
            sourceRevalidationPayloadSnapshotMatches &&
        r260IndexedResourceBehavior.vertexMirrorReady &&
        r260IndexedResourceBehavior.vertexMirrorSnapshotMatches &&
        r260IndexedResourceBehavior.indexMirrorRequired &&
        r260IndexedResourceBehavior.indexMirrorReady &&
        r260IndexedResourceBehavior.indexMirrorSnapshotMatches &&
        r260IndexedResourceBehavior.geometryResourceBehaviorExact &&
        !r260IndexedResourceBehavior.textureResourceBehaviorProofPresent &&
        !r260IndexedResourceBehavior.outputResourceBehaviorProofPresent &&
        !r260IndexedResourceBehavior.fullResourceBehaviorProofPresent &&
        r260IndexedResourceBehavior.missingResourceScopeMask == 0x6u &&
        r260IndexedResourceBehavior.diagnosticOnly &&
        r260IndexedResourceBehavior.boundaryPreserved &&
        r260IndexedResourceBehavior.reviewReady &&
        r260IndexedResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_resource_behavior_readiness_snapshot(
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                d3d.device,
                managedVertexBuffer,
                managedVertexPostResetReady.snapshotToken,
                &managedIndexBuffer,
                managedIndexReady.snapshotToken,
                r260IndexedResourceBehavior.reviewSnapshotToken),
        "R260 indexed geometry resource behavior is exact while texture/output F18 scopes remain fail-closed");

    auto r300TamperedR258ForResourceBehavior =
        r258IndexedSourceRevalidation;
    r300TamperedR258ForResourceBehavior.startLocation += 1u;
    const auto r300TamperedResourceBehavior =
        outrun::vr::dx11::compose_programmable_resource_behavior_readiness(
            r300TamperedR258ForResourceBehavior,
            r300TamperedR258ForResourceBehavior.snapshotToken,
            d3d.device,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            &managedIndexBuffer,
            managedIndexReady.snapshotToken);
    require(
        r300TamperedResourceBehavior.sourceRevalidationReady &&
        r300TamperedResourceBehavior.sourceRevalidationSnapshotMatches &&
        !r300TamperedResourceBehavior.
            sourceRevalidationPayloadSnapshotMatches &&
        !r300TamperedResourceBehavior.geometryResourceBehaviorExact &&
        (r300TamperedResourceBehavior.missingResourceScopeMask & 0x1u) != 0 &&
        !r300TamperedResourceBehavior.boundaryPreserved &&
        !r300TamperedResourceBehavior.reviewReady &&
        r300TamperedResourceBehavior.reviewSnapshotToken == 0,
        "R300 rejects R258 payload drift before minting R260 geometry resource proof");

    const auto staleR260IndexedVertexToken =
        managedVertexPostResetReady.snapshotToken == 1ull
            ? 2ull
            : (managedVertexPostResetReady.snapshotToken ^ 1ull);
    const auto r260IndexedStaleVertex =
        outrun::vr::dx11::compose_programmable_resource_behavior_readiness(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            d3d.device,
            managedVertexBuffer,
            staleR260IndexedVertexToken,
            &managedIndexBuffer,
            managedIndexReady.snapshotToken);
    require(
        r260IndexedStaleVertex.vertexMirrorReady &&
        !r260IndexedStaleVertex.vertexMirrorSnapshotMatches &&
        !r260IndexedStaleVertex.geometryResourceBehaviorExact &&
        !r260IndexedStaleVertex.reviewReady &&
        r260IndexedStaleVertex.reviewSnapshotToken == 0,
        "R260 indexed resource behavior rejects stale vertex mirror identity");

    auto r301TamperedR260ForTextureBehavior =
        r260IndexedResourceBehavior;
    r301TamperedR260ForTextureBehavior.sourceRevalidationSnapshotToken += 1u;
    const auto r301TamperedTextureBehavior =
        outrun::vr::dx11::
            compose_programmable_texture_resource_behavior_readiness(
                r301TamperedR260ForTextureBehavior,
                r301TamperedR260ForTextureBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken);
    require(
        r301TamperedTextureBehavior.geometryReviewReady &&
        r301TamperedTextureBehavior.geometrySnapshotMatches &&
        !r301TamperedTextureBehavior.geometryPayloadSnapshotMatches &&
        !r301TamperedTextureBehavior.geometryResourceBehaviorExact &&
        (r301TamperedTextureBehavior.missingResourceScopeMask & 0x1u) != 0 &&
        !r301TamperedTextureBehavior.boundaryPreserved &&
        !r301TamperedTextureBehavior.reviewReady &&
        r301TamperedTextureBehavior.reviewSnapshotToken == 0,
        "R301 rejects R260 payload drift before minting R261 texture resource proof");

    const auto r261IndexedTextureResourceBehavior =
        outrun::vr::dx11::
            compose_programmable_texture_resource_behavior_readiness(
                r260IndexedResourceBehavior,
                r260IndexedResourceBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken);
    require(
        r261IndexedTextureResourceBehavior.inputValid &&
        r261IndexedTextureResourceBehavior.geometryReviewReady &&
        r261IndexedTextureResourceBehavior.geometrySnapshotMatches &&
        r261IndexedTextureResourceBehavior.
            geometryPayloadSnapshotMatches &&
        r261IndexedTextureResourceBehavior.requiredTextureScopePresent &&
        r261IndexedTextureResourceBehavior.textureStagesInputValid &&
        r261IndexedTextureResourceBehavior.textureStageSnapshotMatches &&
        r261IndexedTextureResourceBehavior.geometryResourceBehaviorExact &&
        r261IndexedTextureResourceBehavior.textureResourceBehaviorExact &&
        !r261IndexedTextureResourceBehavior.outputResourceBehaviorProofPresent &&
        !r261IndexedTextureResourceBehavior.fullResourceBehaviorProofPresent &&
        r261IndexedTextureResourceBehavior.requiredTextureMask == 0x1u &&
        r261IndexedTextureResourceBehavior.readyTextureMask == 0x1u &&
        r261IndexedTextureResourceBehavior.pendingTextureMask == 0 &&
        r261IndexedTextureResourceBehavior.missingResourceScopeMask == 0x4u &&
        r261IndexedTextureResourceBehavior.boundaryPreserved &&
        r261IndexedTextureResourceBehavior.reviewReady &&
        r261IndexedTextureResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_texture_resource_behavior_readiness_snapshot(
                r260IndexedResourceBehavior,
                r260IndexedResourceBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken,
                r261IndexedTextureResourceBehavior.reviewSnapshotToken),
        "R261 indexed texture resource behavior closes supplied texture scope while output F18 remains fail-closed");

    auto r302TamperedR261ForOutputBehavior =
        r261IndexedTextureResourceBehavior;
    r302TamperedR261ForOutputBehavior.requiredTextureMask ^= 0x2u;
    const auto r302TamperedOutputResourceBehavior =
        outrun::vr::dx11::
            compose_programmable_output_resource_behavior_readiness(
                r302TamperedR261ForOutputBehavior,
                r302TamperedR261ForOutputBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                r262SurfaceBindingReady.snapshotToken);
    require(
        r302TamperedOutputResourceBehavior.textureReviewReady &&
        r302TamperedOutputResourceBehavior.textureSnapshotMatches &&
        !r302TamperedOutputResourceBehavior.texturePayloadSnapshotMatches &&
        !r302TamperedOutputResourceBehavior.geometryResourceBehaviorExact &&
        !r302TamperedOutputResourceBehavior.textureResourceBehaviorExact &&
        r302TamperedOutputResourceBehavior.outputResourceBehaviorExact &&
        !r302TamperedOutputResourceBehavior.fullResourceBehaviorProofPresent &&
        (r302TamperedOutputResourceBehavior.missingResourceScopeMask & 0x3u) ==
            0x3u &&
        !r302TamperedOutputResourceBehavior.boundaryPreserved &&
        !r302TamperedOutputResourceBehavior.reviewReady &&
        r302TamperedOutputResourceBehavior.reviewSnapshotToken == 0,
        "R302 rejects R261 payload drift before minting R262 full resource proof");

    const auto r262IndexedOutputResourceBehavior =
        outrun::vr::dx11::
            compose_programmable_output_resource_behavior_readiness(
                r261IndexedTextureResourceBehavior,
                r261IndexedTextureResourceBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                r262SurfaceBindingReady.snapshotToken);
    require(
        r262IndexedOutputResourceBehavior.inputValid &&
        r262IndexedOutputResourceBehavior.textureReviewReady &&
        r262IndexedOutputResourceBehavior.textureSnapshotMatches &&
        r262IndexedOutputResourceBehavior.texturePayloadSnapshotMatches &&
        r262IndexedOutputResourceBehavior.surfacePairReady &&
        r262IndexedOutputResourceBehavior.surfacePairSnapshotMatches &&
        r262IndexedOutputResourceBehavior.surfaceBindingReady &&
        r262IndexedOutputResourceBehavior.surfaceBindingSnapshotMatches &&
        r262IndexedOutputResourceBehavior.geometryResourceBehaviorExact &&
        r262IndexedOutputResourceBehavior.textureResourceBehaviorExact &&
        r262IndexedOutputResourceBehavior.outputResourceBehaviorExact &&
        r262IndexedOutputResourceBehavior.fullResourceBehaviorProofPresent &&
        r262IndexedOutputResourceBehavior.missingResourceScopeMask == 0 &&
        r262IndexedOutputResourceBehavior.diagnosticOnly &&
        r262IndexedOutputResourceBehavior.boundaryPreserved &&
        r262IndexedOutputResourceBehavior.reviewReady &&
        r262IndexedOutputResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_output_resource_behavior_readiness_snapshot(
                r261IndexedTextureResourceBehavior,
                r261IndexedTextureResourceBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                r262SurfaceBindingReady.snapshotToken,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken),
        "R262 indexed output resource behavior closes full F18 without activation authority");

    const auto staleR262IndexedBindingToken =
        r262SurfaceBindingReady.snapshotToken == 1ull
            ? 2ull
            : (r262SurfaceBindingReady.snapshotToken ^ 1ull);
    const auto r262IndexedStaleOutputBinding =
        outrun::vr::dx11::
            compose_programmable_output_resource_behavior_readiness(
                r261IndexedTextureResourceBehavior,
                r261IndexedTextureResourceBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                staleR262IndexedBindingToken);
    require(
        r262IndexedStaleOutputBinding.surfaceBindingReady &&
        !r262IndexedStaleOutputBinding.surfaceBindingSnapshotMatches &&
        !r262IndexedStaleOutputBinding.outputResourceBehaviorExact &&
        !r262IndexedStaleOutputBinding.fullResourceBehaviorProofPresent &&
        !r262IndexedStaleOutputBinding.reviewReady &&
        r262IndexedStaleOutputBinding.reviewSnapshotToken == 0,
        "R262 rejects stale live output-binding identity");

    const auto staleR261TextureStageToken =
        r261TextureStages.snapshotToken == 1ull
            ? 2ull
            : (r261TextureStages.snapshotToken ^ 1ull);
    const auto r261IndexedStaleTexture =
        outrun::vr::dx11::
            compose_programmable_texture_resource_behavior_readiness(
                r260IndexedResourceBehavior,
                r260IndexedResourceBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                staleR261TextureStageToken);
    require(
        r261IndexedStaleTexture.geometrySnapshotMatches &&
        !r261IndexedStaleTexture.textureStageSnapshotMatches &&
        !r261IndexedStaleTexture.textureResourceBehaviorExact &&
        !r261IndexedStaleTexture.reviewReady &&
        r261IndexedStaleTexture.reviewSnapshotToken == 0,
        "R261 rejects stale managed texture-stage identity");

    const auto staleR260IndexedTextureGeometryToken =
        r260IndexedResourceBehavior.reviewSnapshotToken == 1ull
            ? 2ull
            : (r260IndexedResourceBehavior.reviewSnapshotToken ^ 1ull);
    const auto r261IndexedStaleGeometry =
        outrun::vr::dx11::
            compose_programmable_texture_resource_behavior_readiness(
                r260IndexedResourceBehavior,
                staleR260IndexedTextureGeometryToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken);
    require(
        r261IndexedStaleGeometry.geometryReviewReady &&
        !r261IndexedStaleGeometry.geometrySnapshotMatches &&
        !r261IndexedStaleGeometry.geometryResourceBehaviorExact &&
        !r261IndexedStaleGeometry.reviewReady &&
        r261IndexedStaleGeometry.reviewSnapshotToken == 0,
        "R261 rejects stale R260 geometry resource-behavior identity");

    const auto r274SourceMappingPlan =
        outrun::vr::dx11::derive_programmable_shader_register_mapping_plan(
            r271SourceSemanticPair,
            r267VsRegisterSemantics,
            r268PsRegisterSemantics);
    const auto r274SourceMappingHandoff =
        outrun::vr::dx11::compose_programmable_shader_source_mapping_handoff(
            programmablePair,
            r271SourceSemanticPair,
            r274SourceMappingPlan);
    require(
        r274SourceMappingPlan.exact() &&
        r274SourceMappingHandoff.reviewReady &&
        r274SourceMappingHandoff.sourceReceiptIdentityMatches &&
        r274SourceMappingHandoff.mappingPlanIdentityMatches &&
        r274SourceMappingHandoff.constantRegisterMappingExact &&
        r274SourceMappingHandoff.samplerMappingExact &&
        r274SourceMappingHandoff.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_source_mapping_handoff_snapshot(
                programmablePair,
                r271SourceSemanticPair,
                r274SourceMappingPlan,
                r274SourceMappingHandoff.reviewSnapshotToken),
        "R274 source-derived R273 mapping handoff prerequisite is exact");

    const auto r276TranslationPlan =
        outrun::vr::dx11::
            derive_programmable_shader_semantic_translation_plan(
                r271SourceSemanticPair,
                r268Linkage,
                r274SourceMappingHandoff,
                r274SourceMappingHandoff.reviewSnapshotToken);
    require(
        r276TranslationPlan.inputValid &&
        r276TranslationPlan.sourceSemanticReceiptExact &&
        r276TranslationPlan.interfaceLinkageExact &&
        r276TranslationPlan.sourceMappingHandoffReady &&
        r276TranslationPlan.sourceMappingHandoffSnapshotMatches &&
        r276TranslationPlan.provenanceMatches &&
        r276TranslationPlan.vertexSemanticExact &&
        r276TranslationPlan.pixelSemanticExact &&
        r276TranslationPlan.targetVertexSemanticHash != 0 &&
        r276TranslationPlan.targetPixelSemanticHash != 0 &&
        r276TranslationPlan.translatorRevisionHash != 0 &&
        r276TranslationPlan.semanticContractHash != 0 &&
        r276TranslationPlan.diagnosticOnly &&
        r276TranslationPlan.boundaryPreserved &&
        r276TranslationPlan.reviewReady &&
        r276TranslationPlan.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_semantic_translation_plan_snapshot(
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken),
        "R276 derives target semantic identities from R271 R268 R273 provenance");

    const auto staleR274MappingToken =
        r274SourceMappingHandoff.reviewSnapshotToken == 1ull
            ? 2ull
            : (r274SourceMappingHandoff.reviewSnapshotToken ^ 1ull);
    const auto r276StaleMappingPlan =
        outrun::vr::dx11::
            derive_programmable_shader_semantic_translation_plan(
                r271SourceSemanticPair,
                r268Linkage,
                r274SourceMappingHandoff,
                staleR274MappingToken);
    require(
        r276StaleMappingPlan.sourceMappingHandoffReady &&
        !r276StaleMappingPlan.sourceMappingHandoffSnapshotMatches &&
        !r276StaleMappingPlan.provenanceMatches &&
        !r276StaleMappingPlan.vertexSemanticExact &&
        !r276StaleMappingPlan.pixelSemanticExact &&
        !r276StaleMappingPlan.reviewReady &&
        r276StaleMappingPlan.reviewSnapshotToken == 0,
        "R276 rejects stale R273 mapping snapshot before target semantic derivation");

    const auto r279ObjectPrerequisite =
        outrun::vr::dx11::
            derive_programmable_shader_translation_object_prerequisite(
                programmablePair,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r279ObjectPrerequisite.inputValid &&
        r279ObjectPrerequisite.sourceIdentityExact &&
        r279ObjectPrerequisite.translationPlanReady &&
        r279ObjectPrerequisite.translationPlanSnapshotMatches &&
        r279ObjectPrerequisite.cacheIdentityMatches &&
        r279ObjectPrerequisite.cacheOwnerGenerationRequired &&
        r279ObjectPrerequisite.translationSlotGenerationRequired &&
        r279ObjectPrerequisite.translationObjectReceiptGenerationRequired &&
        r279ObjectPrerequisite.sameDeviceObjectPairRequired &&
        r279ObjectPrerequisite.cacheSnapshotRequired &&
        r279ObjectPrerequisite.slotSnapshotRequired &&
        r279ObjectPrerequisite.diagnosticOnly &&
        r279ObjectPrerequisite.boundaryPreserved &&
        r279ObjectPrerequisite.reviewReady &&
        r279ObjectPrerequisite.cacheKey == programmablePair.cacheKey &&
        r279ObjectPrerequisite.targetVertexSemanticHash ==
            r276TranslationPlan.targetVertexSemanticHash &&
        r279ObjectPrerequisite.targetPixelSemanticHash ==
            r276TranslationPlan.targetPixelSemanticHash &&
        r279ObjectPrerequisite.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_translation_object_prerequisite_snapshot(
                programmablePair,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r279ObjectPrerequisite.reviewSnapshotToken),
        "R279 translated object prerequisite seals R240 R241 R242 lifetime requirements");

    const auto staleR279PlanToken =
        r276TranslationPlan.reviewSnapshotToken == 1ull
            ? 2ull
            : (r276TranslationPlan.reviewSnapshotToken ^ 1ull);
    const auto r279StaleObjectPrerequisite =
        outrun::vr::dx11::
            derive_programmable_shader_translation_object_prerequisite(
                programmablePair,
                r276TranslationPlan,
                staleR279PlanToken);
    require(
        r279StaleObjectPrerequisite.translationPlanReady &&
        !r279StaleObjectPrerequisite.translationPlanSnapshotMatches &&
        !r279StaleObjectPrerequisite.cacheIdentityMatches &&
        !r279StaleObjectPrerequisite.reviewReady &&
        r279StaleObjectPrerequisite.reviewSnapshotToken == 0,
        "R279 translated object prerequisite rejects stale R276 plan identity");

    const auto r280ObjectCreationHandoff =
        outrun::vr::dx11::
            compose_programmable_shader_object_creation_handoff(
                programmablePair,
                r267VsEvidence,
                r268PsEvidence,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken);
    require(
        r280ObjectCreationHandoff.inputValid &&
        r280ObjectCreationHandoff.sourceIdentityExact &&
        r280ObjectCreationHandoff.vertexSourceExact &&
        r280ObjectCreationHandoff.pixelSourceExact &&
        r280ObjectCreationHandoff.sourcePairMatches &&
        r280ObjectCreationHandoff.translationPlanReady &&
        r280ObjectCreationHandoff.translationPlanSnapshotMatches &&
        r280ObjectCreationHandoff.objectPrerequisiteReady &&
        r280ObjectCreationHandoff.objectPrerequisiteSnapshotMatches &&
        r280ObjectCreationHandoff.cacheIdentityMatches &&
        !r280ObjectCreationHandoff.objectCreationAuthorized &&
        r280ObjectCreationHandoff.diagnosticOnly &&
        r280ObjectCreationHandoff.boundaryPreserved &&
        r280ObjectCreationHandoff.reviewReady &&
        r280ObjectCreationHandoff.cacheKey == programmablePair.cacheKey &&
        r280ObjectCreationHandoff.vertexBytecodeHash ==
            programmablePair.vertexShader.bytecodeHash &&
        r280ObjectCreationHandoff.pixelBytecodeHash ==
            programmablePair.pixelShader.bytecodeHash &&
        r280ObjectCreationHandoff.targetVertexSemanticHash ==
            r276TranslationPlan.targetVertexSemanticHash &&
        r280ObjectCreationHandoff.targetPixelSemanticHash ==
            r276TranslationPlan.targetPixelSemanticHash &&
        r280ObjectCreationHandoff.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_object_creation_handoff_snapshot(
                programmablePair,
                r267VsEvidence,
                r268PsEvidence,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff.reviewSnapshotToken),
        "R280 object creation handoff binds exact R264 source bytes to R276 R279 without creation authority");

    auto r280StaleVertexSource = r267VsEvidence;
    r280StaleVertexSource.bytecodeHash ^= 1ull;
    const auto r280StaleSourceHandoff =
        outrun::vr::dx11::
            compose_programmable_shader_object_creation_handoff(
                programmablePair,
                r280StaleVertexSource,
                r268PsEvidence,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken);
    require(
        r280StaleVertexSource.exact() &&
        !r280StaleSourceHandoff.vertexSourceExact &&
        !r280StaleSourceHandoff.sourcePairMatches &&
        !r280StaleSourceHandoff.cacheIdentityMatches &&
        !r280StaleSourceHandoff.reviewReady &&
        r280StaleSourceHandoff.reviewSnapshotToken == 0,
        "R280 object creation handoff rejects stale R264 source identity");

    const auto staleR280OwnershipToken =
        r279ObjectPrerequisite.reviewSnapshotToken == 1ull
            ? 2ull
            : (r279ObjectPrerequisite.reviewSnapshotToken ^ 1ull);
    const auto r280StaleOwnershipHandoff =
        outrun::vr::dx11::
            compose_programmable_shader_object_creation_handoff(
                programmablePair,
                r267VsEvidence,
                r268PsEvidence,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r279ObjectPrerequisite,
                staleR280OwnershipToken);
    require(
        r280StaleOwnershipHandoff.objectPrerequisiteReady &&
        !r280StaleOwnershipHandoff.objectPrerequisiteSnapshotMatches &&
        !r280StaleOwnershipHandoff.cacheIdentityMatches &&
        !r280StaleOwnershipHandoff.reviewReady &&
        r280StaleOwnershipHandoff.reviewSnapshotToken == 0,
        "R280 object creation handoff rejects stale R279 ownership prerequisite");

    const auto r281TranslatedArtifactReceipt =
        outrun::vr::dx11::
            derive_programmable_shader_translated_artifact_receipt(
                programmablePair,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r281TranslatedArtifactReceipt.inputValid &&
        r281TranslatedArtifactReceipt.sourceIdentityExact &&
        r281TranslatedArtifactReceipt.objectCreationHandoffReady &&
        r281TranslatedArtifactReceipt.objectCreationHandoffSnapshotMatches &&
        r281TranslatedArtifactReceipt.translationPlanReady &&
        r281TranslatedArtifactReceipt.translationPlanSnapshotMatches &&
        r281TranslatedArtifactReceipt.cacheIdentityMatches &&
        r281TranslatedArtifactReceipt.targetVertexIdentityDefined &&
        r281TranslatedArtifactReceipt.targetPixelIdentityDefined &&
        r281TranslatedArtifactReceipt.targetBytecodeReceiptRequired &&
        !r281TranslatedArtifactReceipt.targetBytecodeMaterialized &&
        !r281TranslatedArtifactReceipt.objectCreationAuthorized &&
        r281TranslatedArtifactReceipt.diagnosticOnly &&
        r281TranslatedArtifactReceipt.boundaryPreserved &&
        r281TranslatedArtifactReceipt.reviewReady &&
        r281TranslatedArtifactReceipt.targetVertexBytecodeReceiptIdentity != 0 &&
        r281TranslatedArtifactReceipt.targetPixelBytecodeReceiptIdentity != 0 &&
        r281TranslatedArtifactReceipt.targetVertexBytecodeReceiptIdentity !=
            r281TranslatedArtifactReceipt.targetPixelBytecodeReceiptIdentity &&
        r281TranslatedArtifactReceipt.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_translated_artifact_receipt_snapshot(
                programmablePair,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r281TranslatedArtifactReceipt.reviewSnapshotToken),
        "R281 translated artifact receipt defines target bytecode identity without materializing shaders");

    const auto staleR281HandoffToken =
        r280ObjectCreationHandoff.reviewSnapshotToken == 1ull
            ? 2ull
            : (r280ObjectCreationHandoff.reviewSnapshotToken ^ 1ull);
    const auto r281StaleHandoffReceipt =
        outrun::vr::dx11::
            derive_programmable_shader_translated_artifact_receipt(
                programmablePair,
                r280ObjectCreationHandoff,
                staleR281HandoffToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r281StaleHandoffReceipt.objectCreationHandoffReady &&
        !r281StaleHandoffReceipt.objectCreationHandoffSnapshotMatches &&
        !r281StaleHandoffReceipt.cacheIdentityMatches &&
        !r281StaleHandoffReceipt.targetBytecodeReceiptRequired &&
        !r281StaleHandoffReceipt.reviewReady &&
        r281StaleHandoffReceipt.reviewSnapshotToken == 0,
        "R281 translated artifact receipt rejects stale R280 handoff identity");

    const auto r282TargetMaterializationContract =
        outrun::vr::dx11::
            derive_programmable_shader_target_materialization_contract(
                programmablePair,
                r281TranslatedArtifactReceipt,
                r281TranslatedArtifactReceipt.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r282TargetMaterializationContract.inputValid &&
        r282TargetMaterializationContract.sourceIdentityExact &&
        r282TargetMaterializationContract.translatedArtifactReceiptReady &&
        r282TargetMaterializationContract.
            translatedArtifactReceiptSnapshotMatches &&
        r282TargetMaterializationContract.translationPlanReady &&
        r282TargetMaterializationContract.translationPlanSnapshotMatches &&
        r282TargetMaterializationContract.cacheIdentityMatches &&
        r282TargetMaterializationContract.targetArtifactIdentityMatches &&
        r282TargetMaterializationContract.entryPointExact &&
        r282TargetMaterializationContract.vertexTargetProfileExact &&
        r282TargetMaterializationContract.pixelTargetProfileExact &&
        r282TargetMaterializationContract.compileFlagsExact &&
        r282TargetMaterializationContract.targetBytecodeMaterializationRequired &&
        !r282TargetMaterializationContract.targetBytecodeMaterialized &&
        !r282TargetMaterializationContract.compilationAuthorized &&
        !r282TargetMaterializationContract.objectCreationAuthorized &&
        r282TargetMaterializationContract.diagnosticOnly &&
        r282TargetMaterializationContract.boundaryPreserved &&
        r282TargetMaterializationContract.reviewReady &&
        r282TargetMaterializationContract.vertexCompileContractIdentity != 0 &&
        r282TargetMaterializationContract.pixelCompileContractIdentity != 0 &&
        r282TargetMaterializationContract.vertexCompileContractIdentity !=
            r282TargetMaterializationContract.pixelCompileContractIdentity &&
        r282TargetMaterializationContract.compileFlags ==
            (D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3) &&
        r282TargetMaterializationContract.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_target_materialization_contract_snapshot(
                programmablePair,
                r281TranslatedArtifactReceipt,
                r281TranslatedArtifactReceipt.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r282TargetMaterializationContract.reviewSnapshotToken),
        "R282 target materialization contract seals main vs_4_0 ps_4_0 strict O3 without compiling");

    const auto staleR282ArtifactToken =
        r281TranslatedArtifactReceipt.reviewSnapshotToken == 1ull
            ? 2ull
            : (r281TranslatedArtifactReceipt.reviewSnapshotToken ^ 1ull);
    const auto r282StaleArtifactContract =
        outrun::vr::dx11::
            derive_programmable_shader_target_materialization_contract(
                programmablePair,
                r281TranslatedArtifactReceipt,
                staleR282ArtifactToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r282StaleArtifactContract.translatedArtifactReceiptReady &&
        !r282StaleArtifactContract.translatedArtifactReceiptSnapshotMatches &&
        !r282StaleArtifactContract.cacheIdentityMatches &&
        !r282StaleArtifactContract.targetArtifactIdentityMatches &&
        !r282StaleArtifactContract.targetBytecodeMaterializationRequired &&
        !r282StaleArtifactContract.reviewReady &&
        r282StaleArtifactContract.reviewSnapshotToken == 0,
        "R282 target materialization contract rejects stale R281 artifact receipt identity");

    const auto r283TargetBytecodeMaterialization =
        outrun::vr::dx11::
            materialize_programmable_shader_target_bytecode(
                programmablePair,
                r267VsEvidence,
                r268PsEvidence,
                r281TranslatedArtifactReceipt,
                r281TranslatedArtifactReceipt.reviewSnapshotToken,
                r282TargetMaterializationContract,
                r282TargetMaterializationContract.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r283TargetBytecodeMaterialization.inputValid &&
        r283TargetBytecodeMaterialization.sourceIdentityExact &&
        r283TargetBytecodeMaterialization.vertexSourceExact &&
        r283TargetBytecodeMaterialization.pixelSourceExact &&
        r283TargetBytecodeMaterialization.translatedArtifactReceiptReady &&
        r283TargetBytecodeMaterialization.
            translatedArtifactReceiptSnapshotMatches &&
        r283TargetBytecodeMaterialization.targetMaterializationContractReady &&
        r283TargetBytecodeMaterialization.
            targetMaterializationContractSnapshotMatches &&
        r283TargetBytecodeMaterialization.translationPlanReady &&
        r283TargetBytecodeMaterialization.translationPlanSnapshotMatches &&
        r283TargetBytecodeMaterialization.provenanceMatches &&
        r283TargetBytecodeMaterialization.vertexSubsetSupported &&
        r283TargetBytecodeMaterialization.pixelSubsetSupported &&
        r283TargetBytecodeMaterialization.vertexSourceMaterialized &&
        r283TargetBytecodeMaterialization.pixelSourceMaterialized &&
        r283TargetBytecodeMaterialization.vertexCompilationSucceeded &&
        r283TargetBytecodeMaterialization.pixelCompilationSucceeded &&
        r283TargetBytecodeMaterialization.targetBytecodeMaterialized &&
        !r283TargetBytecodeMaterialization.objectCreationAuthorized &&
        r283TargetBytecodeMaterialization.diagnosticOnly &&
        r283TargetBytecodeMaterialization.boundaryPreserved &&
        r283TargetBytecodeMaterialization.reviewReady &&
        r283TargetBytecodeMaterialization.vertexTranslatedSourceBytes != 0 &&
        r283TargetBytecodeMaterialization.pixelTranslatedSourceBytes != 0 &&
        r283TargetBytecodeMaterialization.vertexTranslatedSourceHash != 0 &&
        r283TargetBytecodeMaterialization.pixelTranslatedSourceHash != 0 &&
        r283TargetBytecodeMaterialization.vertexTargetBytecodeBytes >= 4u &&
        r283TargetBytecodeMaterialization.pixelTargetBytecodeBytes >= 4u &&
        r283TargetBytecodeMaterialization.vertexTargetBytecodeHash != 0 &&
        r283TargetBytecodeMaterialization.pixelTargetBytecodeHash != 0 &&
        r283TargetBytecodeMaterialization.vertexMaterializedArtifactIdentity != 0 &&
        r283TargetBytecodeMaterialization.pixelMaterializedArtifactIdentity != 0 &&
        r283TargetBytecodeMaterialization.vertexMaterializedArtifactIdentity !=
            r283TargetBytecodeMaterialization.pixelMaterializedArtifactIdentity &&
        r283TargetBytecodeMaterialization.vertexTargetBytecode.size() ==
            r283TargetBytecodeMaterialization.vertexTargetBytecodeBytes &&
        r283TargetBytecodeMaterialization.pixelTargetBytecode.size() ==
            r283TargetBytecodeMaterialization.pixelTargetBytecodeBytes &&
        r283TargetBytecodeMaterialization.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_target_bytecode_materialization_snapshot(
                programmablePair,
                r267VsEvidence,
                r268PsEvidence,
                r281TranslatedArtifactReceipt,
                r281TranslatedArtifactReceipt.reviewSnapshotToken,
                r282TargetMaterializationContract,
                r282TargetMaterializationContract.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken),
        "R283 materializes bounded SM3 DCL+MOV HLSL and DXBC while object creation stays disabled");

    auto r283StaleVertexSource = r267VsEvidence;
    r283StaleVertexSource.bytecodeHash =
        r267VsEvidence.bytecodeHash == 1ull
            ? 2ull
            : (r267VsEvidence.bytecodeHash ^ 1ull);
    const auto r283StaleSourceMaterialization =
        outrun::vr::dx11::
            materialize_programmable_shader_target_bytecode(
                programmablePair,
                r283StaleVertexSource,
                r268PsEvidence,
                r281TranslatedArtifactReceipt,
                r281TranslatedArtifactReceipt.reviewSnapshotToken,
                r282TargetMaterializationContract,
                r282TargetMaterializationContract.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r283StaleSourceMaterialization.sourceIdentityExact &&
        !r283StaleSourceMaterialization.vertexSourceExact &&
        !r283StaleSourceMaterialization.provenanceMatches &&
        !r283StaleSourceMaterialization.targetBytecodeMaterialized &&
        !r283StaleSourceMaterialization.objectCreationAuthorized &&
        !r283StaleSourceMaterialization.reviewReady &&
        r283StaleSourceMaterialization.reviewSnapshotToken == 0,
        "R283 rejects source bytes detached from the R281/R282 provenance");

    DevicePair r284Device = create_warp_device();
    NativeProgrammableShaderPairCache r284Cache;
    const auto r284ObjectMaterialization =
        outrun::vr::dx11::
            materialize_programmable_shader_translation_objects(
                r284Device.device,
                r284Cache,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken);
    require(
        r284ObjectMaterialization.inputValid &&
        r284ObjectMaterialization.sourceIdentityExact &&
        r284ObjectMaterialization.objectPrerequisiteReady &&
        r284ObjectMaterialization.objectPrerequisiteSnapshotMatches &&
        r284ObjectMaterialization.creationHandoffReady &&
        r284ObjectMaterialization.creationHandoffSnapshotMatches &&
        r284ObjectMaterialization.targetBytecodeMaterializationReady &&
        r284ObjectMaterialization.targetBytecodeMaterializationSnapshotMatches &&
        r284ObjectMaterialization.provenanceMatches &&
        r284ObjectMaterialization.cacheInitialized &&
        r284ObjectMaterialization.cacheEntryReady &&
        r284ObjectMaterialization.cacheSnapshotMatches &&
        r284ObjectMaterialization.translationSlotReserved &&
        r284ObjectMaterialization.translationSlotReady &&
        r284ObjectMaterialization.slotSnapshotMatches &&
        r284ObjectMaterialization.objectsAbsentBeforeMaterialization &&
        r284ObjectMaterialization.vertexObjectCreated &&
        r284ObjectMaterialization.pixelObjectCreated &&
        r284ObjectMaterialization.objectsAttached &&
        r284ObjectMaterialization.objectDevicesMatch &&
        r284ObjectMaterialization.translationObjectReceiptReady &&
        !r284ObjectMaterialization.objectBindingAuthorized &&
        r284ObjectMaterialization.diagnosticOnly &&
        r284ObjectMaterialization.boundaryPreserved &&
        r284ObjectMaterialization.reviewReady &&
        r284ObjectMaterialization.cacheKey == programmablePair.cacheKey &&
        r284ObjectMaterialization.targetVertexBytecodeHash ==
            r283TargetBytecodeMaterialization.vertexTargetBytecodeHash &&
        r284ObjectMaterialization.targetPixelBytecodeHash ==
            r283TargetBytecodeMaterialization.pixelTargetBytecodeHash &&
        r284ObjectMaterialization.vertexMaterializedArtifactIdentity ==
            r283TargetBytecodeMaterialization.vertexMaterializedArtifactIdentity &&
        r284ObjectMaterialization.pixelMaterializedArtifactIdentity ==
            r283TargetBytecodeMaterialization.pixelMaterializedArtifactIdentity &&
        r284ObjectMaterialization.ownerGeneration != 0 &&
        r284ObjectMaterialization.slotGeneration != 0 &&
        r284ObjectMaterialization.translationObjectReceiptGeneration != 0 &&
        r284ObjectMaterialization.objectMaterializerRevisionHash != 0 &&
        r284ObjectMaterialization.cacheSnapshotToken != 0 &&
        r284ObjectMaterialization.slotSnapshotToken != 0 &&
        r284ObjectMaterialization.translationObjectSnapshotToken != 0 &&
        r284ObjectMaterialization.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_object_materialization_snapshot(
                r284Device.device,
                r284Cache,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken,
                r284ObjectMaterialization,
                r284ObjectMaterialization.reviewSnapshotToken),
        "R284 materializes exact R283 DXBC into same-device R242 object ownership");

    ID3D11VertexShader* r284BoundVertex = nullptr;
    ID3D11PixelShader* r284BoundPixel = nullptr;
    r284Device.context->VSGetShader(&r284BoundVertex, nullptr, nullptr);
    r284Device.context->PSGetShader(&r284BoundPixel, nullptr, nullptr);
    require(
        r284BoundVertex == nullptr &&
        r284BoundPixel == nullptr,
        "R284 object materialization must not bind VS or PS to the immediate context");
    if (r284BoundVertex)
        r284BoundVertex->Release();
    if (r284BoundPixel)
        r284BoundPixel->Release();

    DevicePair r284ForeignDevice = create_warp_device();
    require(
        !outrun::vr::dx11::
            validate_programmable_shader_object_materialization_snapshot(
                r284ForeignDevice.device,
                r284Cache,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken,
                r284ObjectMaterialization,
                r284ObjectMaterialization.reviewSnapshotToken),
        "R284 ownership receipt rejects a foreign D3D11 device");
    r284ForeignDevice.context->Release();
    r284ForeignDevice.device->Release();

    auto r284StaleBytecodeMaterialization =
        r283TargetBytecodeMaterialization;
    r284StaleBytecodeMaterialization.vertexTargetBytecodeHash ^=
        0x1ull;
    NativeProgrammableShaderPairCache r284StaleCache;
    const auto r284StaleObjectMaterialization =
        outrun::vr::dx11::
            materialize_programmable_shader_translation_objects(
                r284Device.device,
                r284StaleCache,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r284StaleBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken);
    require(
        r284StaleObjectMaterialization.targetBytecodeMaterializationReady &&
        !r284StaleObjectMaterialization.
            targetBytecodeMaterializationSnapshotMatches &&
        !r284StaleObjectMaterialization.provenanceMatches &&
        !r284StaleObjectMaterialization.cacheInitialized &&
        !r284StaleObjectMaterialization.vertexObjectCreated &&
        !r284StaleObjectMaterialization.pixelObjectCreated &&
        !r284StaleObjectMaterialization.translationObjectReceiptReady &&
        !r284StaleObjectMaterialization.reviewReady &&
        r284StaleObjectMaterialization.reviewSnapshotToken == 0,
        "R284 rejects stale/tampered R283 bytecode provenance before object creation");

    outrun::vr::dx11::NativeProgrammableShaderBackendOwnership
        r285BackendOwnership;
    require(
        !r285BackendOwnership.ready() &&
        r285BackendOwnership.initialize(r284Device.device) &&
        r285BackendOwnership.ready() &&
        r285BackendOwnership.device() == r284Device.device &&
        r285BackendOwnership.cache().entry_count() == 0 &&
        r285BackendOwnership.owner_generation() != 0,
        "R285 native-device programmable owner initializes with persistent empty cache");
    const auto r285FirstOwnerGeneration =
        r285BackendOwnership.owner_generation();

    const auto r285FirstHandoff =
        r285BackendOwnership.materialize_semantic_handoff_for_observation(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken);
    require(
        r285FirstHandoff.inputValid &&
        r285FirstHandoff.ownerReady &&
        r285FirstHandoff.deviceMatches &&
        r285FirstHandoff.materializationReady &&
        r285FirstHandoff.materializationSnapshotMatches &&
        !r285FirstHandoff.materializationReused &&
        r285FirstHandoff.translationObjectReady &&
        r285FirstHandoff.translationObjectSnapshotMatches &&
        r285FirstHandoff.translatedSemanticReceiptReady &&
        r285FirstHandoff.translatedSemanticReceiptSnapshotMatches &&
        !r285FirstHandoff.objectBindingAuthorized &&
        !r285FirstHandoff.nativeDrawPathActivationAllowed &&
        !r285FirstHandoff.drawDispatchAuthorized &&
        r285FirstHandoff.diagnosticOnly &&
        r285FirstHandoff.boundaryPreserved &&
        r285FirstHandoff.reviewReady &&
        r285FirstHandoff.cacheKey == programmablePair.cacheKey &&
        r285FirstHandoff.backendOwnerGeneration ==
            r285FirstOwnerGeneration &&
        r285FirstHandoff.cacheOwnerGeneration != 0 &&
        r285FirstHandoff.objectMaterializationSnapshotToken != 0 &&
        r285FirstHandoff.cacheSnapshotToken != 0 &&
        r285FirstHandoff.slotSnapshotToken != 0 &&
        r285FirstHandoff.translationObjectSnapshotToken != 0 &&
        r285FirstHandoff.translatedSemanticReceiptSnapshotToken != 0 &&
        r285FirstHandoff.translatedSemanticReceipt.reviewReady &&
        r285FirstHandoff.translatedSemanticReceipt.
            translationObjectSnapshotToken ==
            r285FirstHandoff.translationObjectSnapshotToken &&
        r285FirstHandoff.reviewSnapshotToken != 0 &&
        r285BackendOwnership.cache().entry_count() == 1 &&
        r285BackendOwnership.validate_semantic_handoff_snapshot(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken,
            r285FirstHandoff,
            r285FirstHandoff.reviewSnapshotToken),
        "R285 native owner feeds exact persistent R242 ownership into R275 without binding");

    const auto r285RepeatedHandoff =
        r285BackendOwnership.materialize_semantic_handoff_for_observation(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken);
    require(
        r285RepeatedHandoff.reviewReady &&
        r285RepeatedHandoff.materializationReused &&
        r285RepeatedHandoff.backendOwnerGeneration ==
            r285FirstHandoff.backendOwnerGeneration &&
        r285RepeatedHandoff.cacheOwnerGeneration ==
            r285FirstHandoff.cacheOwnerGeneration &&
        r285RepeatedHandoff.objectMaterializationSnapshotToken ==
            r285FirstHandoff.objectMaterializationSnapshotToken &&
        r285RepeatedHandoff.translationObjectSnapshotToken ==
            r285FirstHandoff.translationObjectSnapshotToken &&
        r285RepeatedHandoff.translatedSemanticReceiptSnapshotToken ==
            r285FirstHandoff.translatedSemanticReceiptSnapshotToken &&
        r285RepeatedHandoff.reviewSnapshotToken ==
            r285FirstHandoff.reviewSnapshotToken &&
        r285BackendOwnership.cache().entry_count() == 1 &&
        r285BackendOwnership.validate_semantic_handoff_snapshot(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken,
            r285RepeatedHandoff,
            r285RepeatedHandoff.reviewSnapshotToken),
        "R285 repeated pair reuses exact R284/R242 receipt instead of recreating shaders");


    const auto r286ProductionObservation =
        outrun::vr::dx11::
            observe_programmable_shader_production_source_evidence_chain(
                r285BackendOwnership,
                r284Device.device,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken,
                r274SourceMappingHandoff,
                r274SourceMappingHandoff.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r286ProductionObservation.inputValid &&
        r286ProductionObservation.ownerReady &&
        r286ProductionObservation.deviceMatches &&
        r286ProductionObservation.objectPrerequisiteReady &&
        r286ProductionObservation.creationHandoffReady &&
        r286ProductionObservation.targetBytecodeMaterializationReady &&
        r286ProductionObservation.sourceMappingHandoffReady &&
        r286ProductionObservation.translationPlanReady &&
        r286ProductionObservation.semanticHandoffReady &&
        r286ProductionObservation.semanticHandoffSnapshotMatches &&
        r286ProductionObservation.semanticHandoff.materializationReused &&
        !r286ProductionObservation.objectBindingAuthorized &&
        !r286ProductionObservation.nativeDrawPathActivationAllowed &&
        !r286ProductionObservation.drawDispatchAuthorized &&
        r286ProductionObservation.diagnosticOnly &&
        r286ProductionObservation.boundaryPreserved &&
        r286ProductionObservation.reviewReady &&
        r286ProductionObservation.cacheKey == programmablePair.cacheKey &&
        r286ProductionObservation.backendOwnerGeneration ==
            r285BackendOwnership.owner_generation() &&
        r286ProductionObservation.semanticHandoffSnapshotToken ==
            r286ProductionObservation.semanticHandoff.reviewSnapshotToken &&
        r286ProductionObservation.reviewSnapshotToken != 0 &&
        r285BackendOwnership.cache().entry_count() == 1,
        "R286 production source-evidence bridge reaches R285 ownership without binding or draw");

    const auto r288TranslationAdmission =
        outrun::vr::dx11::seal_programmable_shader_translation_admission(
            programmablePair,
            r286ProductionObservation,
            r286ProductionObservation.reviewSnapshotToken);
    require(
        r288TranslationAdmission.inputValid &&
        r288TranslationAdmission.sourceIdentityExact &&
        r288TranslationAdmission.productionObservationReady &&
        r288TranslationAdmission.productionObservationSnapshotMatches &&
        r288TranslationAdmission.translatedSemanticReceiptReady &&
        r288TranslationAdmission.translatedSemanticReceiptSnapshotMatches &&
        r288TranslationAdmission.cacheIdentityMatches &&
        r288TranslationAdmission.translationObjectReady &&
        !r288TranslationAdmission.objectBindingAuthorized &&
        !r288TranslationAdmission.nativeDrawPathActivationAllowed &&
        !r288TranslationAdmission.drawDispatchAuthorized &&
        r288TranslationAdmission.diagnosticOnly &&
        r288TranslationAdmission.boundaryPreserved &&
        r288TranslationAdmission.reviewReady &&
        r288TranslationAdmission.cacheKey == programmablePair.cacheKey &&
        r288TranslationAdmission.backendOwnerGeneration ==
            r286ProductionObservation.backendOwnerGeneration &&
        r288TranslationAdmission.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_translation_admission_snapshot(
                programmablePair,
                r286ProductionObservation,
                r286ProductionObservation.reviewSnapshotToken,
                r288TranslationAdmission,
                r288TranslationAdmission.reviewSnapshotToken),
        "R288 translation admission seals exact R286/R275 readiness without authorizing binding or draw");

    const auto r288TamperedObservationToken =
        r286ProductionObservation.reviewSnapshotToken ^ 0x1ull;
    const auto r288TamperedTranslationAdmission =
        outrun::vr::dx11::seal_programmable_shader_translation_admission(
            programmablePair,
            r286ProductionObservation,
            r288TamperedObservationToken);
    require(
        r288TamperedTranslationAdmission.inputValid &&
        r288TamperedTranslationAdmission.productionObservationReady &&
        !r288TamperedTranslationAdmission.productionObservationSnapshotMatches &&
        !r288TamperedTranslationAdmission.boundaryPreserved &&
        !r288TamperedTranslationAdmission.reviewReady &&
        r288TamperedTranslationAdmission.reviewSnapshotToken == 0,
        "R288 translation admission rejects tampered R286 snapshot");

    const auto r289ProductionSemanticReview =
        r285BackendOwnership.
            materialize_semantic_translation_review_for_observation(
                programmablePair,
                r286ProductionObservation,
                r286ProductionObservation.reviewSnapshotToken,
                r288TranslationAdmission,
                r288TranslationAdmission.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                inputLayout,
                r268Linkage);
    require(
        r289ProductionSemanticReview.inputValid &&
        r289ProductionSemanticReview.ownerReady &&
        r289ProductionSemanticReview.admissionReady &&
        r289ProductionSemanticReview.admissionSnapshotMatches &&
        r289ProductionSemanticReview.targetVertexBytecodeReady &&
        r289ProductionSemanticReview.inputLayoutDescriptorExact &&
        r289ProductionSemanticReview.inputLayoutObjectReady &&
        !r289ProductionSemanticReview.inputLayoutReused &&
        r289ProductionSemanticReview.translationObjectReady &&
        r289ProductionSemanticReview.translationObjectSnapshotMatches &&
        r289ProductionSemanticReview.inputLayoutReceiptReady &&
        r289ProductionSemanticReview.inputLayoutSnapshotMatches &&
        r289ProductionSemanticReview.semanticTranslationReady &&
        r289ProductionSemanticReview.semanticTranslationSnapshotMatches &&
        r289ProductionSemanticReview.semanticTranslation.semanticProofPresent &&
        !r289ProductionSemanticReview.objectBindingAuthorized &&
        !r289ProductionSemanticReview.nativeDrawPathActivationAllowed &&
        !r289ProductionSemanticReview.drawDispatchAuthorized &&
        r289ProductionSemanticReview.diagnosticOnly &&
        r289ProductionSemanticReview.boundaryPreserved &&
        r289ProductionSemanticReview.reviewReady &&
        r289ProductionSemanticReview.reviewSnapshotToken != 0 &&
        r285BackendOwnership.validate_semantic_translation_review_snapshot(
            programmablePair,
            r286ProductionObservation,
            r286ProductionObservation.reviewSnapshotToken,
            r288TranslationAdmission,
            r288TranslationAdmission.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            inputLayout,
            r268Linkage,
            r289ProductionSemanticReview,
            r289ProductionSemanticReview.reviewSnapshotToken),
        "R289 production semantic review materializes R243 and validates R263 without binding or draw");

    const auto r289RepeatedSemanticReview =
        r285BackendOwnership.
            materialize_semantic_translation_review_for_observation(
                programmablePair,
                r286ProductionObservation,
                r286ProductionObservation.reviewSnapshotToken,
                r288TranslationAdmission,
                r288TranslationAdmission.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                inputLayout,
                r268Linkage);
    require(
        r289RepeatedSemanticReview.reviewReady &&
        r289RepeatedSemanticReview.inputLayoutReused &&
        r289RepeatedSemanticReview.inputLayoutSnapshotToken ==
            r289ProductionSemanticReview.inputLayoutSnapshotToken &&
        r289RepeatedSemanticReview.semanticTranslationSnapshotToken ==
            r289ProductionSemanticReview.semanticTranslationSnapshotToken &&
        r285BackendOwnership.validate_semantic_translation_review_snapshot(
            programmablePair,
            r286ProductionObservation,
            r286ProductionObservation.reviewSnapshotToken,
            r288TranslationAdmission,
            r288TranslationAdmission.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            inputLayout,
            r268Linkage,
            r289RepeatedSemanticReview,
            r289RepeatedSemanticReview.reviewSnapshotToken),
        "R289 repeated review reuses the persistent R243 input-layout receipt");

    const auto r289StaleAdmissionToken =
        r288TranslationAdmission.reviewSnapshotToken ^ 0x1ull;
    const auto r289StaleAdmissionReview =
        r285BackendOwnership.
            materialize_semantic_translation_review_for_observation(
                programmablePair,
                r286ProductionObservation,
                r286ProductionObservation.reviewSnapshotToken,
                r288TranslationAdmission,
                r289StaleAdmissionToken,
                r283TargetBytecodeMaterialization,
                inputLayout,
                r268Linkage);
    require(
        r289StaleAdmissionReview.inputValid &&
        r289StaleAdmissionReview.ownerReady &&
        r289StaleAdmissionReview.admissionReady &&
        !r289StaleAdmissionReview.admissionSnapshotMatches &&
        !r289StaleAdmissionReview.semanticTranslationReady &&
        !r289StaleAdmissionReview.boundaryPreserved &&
        !r289StaleAdmissionReview.reviewReady &&
        r289StaleAdmissionReview.reviewSnapshotToken == 0,
        "R289 production semantic review rejects stale R288 admission before layout mutation");

    ID3D11InputLayout* r289BoundInputLayout = nullptr;
    ID3D11VertexShader* r289BoundVertex = nullptr;
    ID3D11PixelShader* r289BoundPixel = nullptr;
    r284Device.context->IAGetInputLayout(&r289BoundInputLayout);
    r284Device.context->VSGetShader(&r289BoundVertex, nullptr, nullptr);
    r284Device.context->PSGetShader(&r289BoundPixel, nullptr, nullptr);
    require(
        r289BoundInputLayout == nullptr &&
        r289BoundVertex == nullptr &&
        r289BoundPixel == nullptr,
        "R289 production semantic review must not bind IA/VS/PS state");
    if (r289BoundInputLayout)
        r289BoundInputLayout->Release();
    if (r289BoundVertex)
        r289BoundVertex->Release();
    if (r289BoundPixel)
        r289BoundPixel->Release();

    const auto r286StaleMappingObservation =
        outrun::vr::dx11::
            observe_programmable_shader_production_source_evidence_chain(
                r285BackendOwnership,
                r284Device.device,
                programmablePair,
                r279ObjectPrerequisite,
                r279ObjectPrerequisite.reviewSnapshotToken,
                r280ObjectCreationHandoff,
                r280ObjectCreationHandoff.reviewSnapshotToken,
                r283TargetBytecodeMaterialization,
                r283TargetBytecodeMaterialization.reviewSnapshotToken,
                r274SourceMappingHandoff,
                staleR274MappingToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r286StaleMappingObservation.inputValid &&
        r286StaleMappingObservation.ownerReady &&
        r286StaleMappingObservation.deviceMatches &&
        !r286StaleMappingObservation.sourceMappingHandoffReady &&
        !r286StaleMappingObservation.semanticHandoffReady &&
        !r286StaleMappingObservation.boundaryPreserved &&
        !r286StaleMappingObservation.reviewReady &&
        r286StaleMappingObservation.reviewSnapshotToken == 0 &&
        r285BackendOwnership.cache().entry_count() == 1,
        "R286 production bridge rejects stale R274 evidence before R285 handoff");

    outrun::vr::dx11::NativeBackend r286UninitializedBackend;
    const auto r286UninitializedObservation =
        r286UninitializedBackend.observe_programmable_shader_source_evidence_chain(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken);
    require(
        !r286UninitializedObservation.inputValid &&
        !r286UninitializedObservation.reviewReady &&
        r286UninitializedObservation.reviewSnapshotToken == 0,
        "R286 NativeBackend entrypoint fails closed before native-device initialization");

    ID3D11VertexShader* r285BoundVertex = nullptr;
    ID3D11PixelShader* r285BoundPixel = nullptr;
    r284Device.context->VSGetShader(&r285BoundVertex, nullptr, nullptr);
    r284Device.context->PSGetShader(&r285BoundPixel, nullptr, nullptr);
    require(
        r285BoundVertex == nullptr &&
        r285BoundPixel == nullptr,
        "R285 persistent ownership handoff must not bind VS or PS to the immediate context");
    if (r285BoundVertex)
        r285BoundVertex->Release();
    if (r285BoundPixel)
        r285BoundPixel->Release();

    const auto r285StaleMappingHandoff =
        r285BackendOwnership.materialize_semantic_handoff_for_observation(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            staleR274MappingToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken);
    require(
        r285StaleMappingHandoff.materializationReady &&
        r285StaleMappingHandoff.materializationReused &&
        r285StaleMappingHandoff.translationObjectReady &&
        !r285StaleMappingHandoff.translatedSemanticReceiptReady &&
        !r285StaleMappingHandoff.translatedSemanticReceiptSnapshotMatches &&
        !r285StaleMappingHandoff.reviewReady &&
        r285StaleMappingHandoff.reviewSnapshotToken == 0 &&
        r285BackendOwnership.cache().entry_count() == 1,
        "R285 rejects stale R274 mapping identity after safe R284 receipt reuse");

    DevicePair r285NextDevice = create_warp_device();
    require(
        r285BackendOwnership.initialize(r285NextDevice.device) &&
        r285BackendOwnership.ready() &&
        r285BackendOwnership.device() == r285NextDevice.device &&
        r285BackendOwnership.owner_generation() !=
            r285FirstOwnerGeneration &&
        r285BackendOwnership.cache().entry_count() == 0 &&
        !r285BackendOwnership.validate_semantic_handoff_snapshot(
            programmablePair,
            r279ObjectPrerequisite,
            r279ObjectPrerequisite.reviewSnapshotToken,
            r280ObjectCreationHandoff,
            r280ObjectCreationHandoff.reviewSnapshotToken,
            r283TargetBytecodeMaterialization,
            r283TargetBytecodeMaterialization.reviewSnapshotToken,
            r274SourceMappingHandoff,
            r274SourceMappingHandoff.reviewSnapshotToken,
            r276TranslationPlan,
            r276TranslationPlan.reviewSnapshotToken,
            r285FirstHandoff,
            r285FirstHandoff.reviewSnapshotToken),
        "R285 native-device generation change invalidates prior persistent ownership handoff");
    r285BackendOwnership.shutdown();
    r285NextDevice.context->Release();
    r285NextDevice.device->Release();

    r284Device.context->Release();
    r284Device.device->Release();

    const auto r275SemanticReceipt =
        outrun::vr::dx11::
            compose_programmable_shader_translated_semantic_receipt(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r274SourceMappingHandoff,
                r274SourceMappingHandoff.reviewSnapshotToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r275SemanticReceipt.inputValid &&
        r275SemanticReceipt.sourceIdentityExact &&
        r275SemanticReceipt.translationObjectReady &&
        r275SemanticReceipt.translationObjectSnapshotMatches &&
        r275SemanticReceipt.sourceMappingHandoffReady &&
        r275SemanticReceipt.sourceMappingHandoffSnapshotMatches &&
        r275SemanticReceipt.translationPlanReady &&
        r275SemanticReceipt.translationPlanSnapshotMatches &&
        r275SemanticReceipt.cacheIdentityMatches &&
        r275SemanticReceipt.vertexSemanticExact &&
        r275SemanticReceipt.pixelSemanticExact &&
        r275SemanticReceipt.translatedVertexSemanticHash ==
            r276TranslationPlan.targetVertexSemanticHash &&
        r275SemanticReceipt.translatedPixelSemanticHash ==
            r276TranslationPlan.targetPixelSemanticHash &&
        r275SemanticReceipt.translatorRevisionHash ==
            r276TranslationPlan.translatorRevisionHash &&
        r275SemanticReceipt.semanticContractHash ==
            r276TranslationPlan.semanticContractHash &&
        r275SemanticReceipt.constantRegisterMappingExact &&
        r275SemanticReceipt.samplerMappingExact &&
        r275SemanticReceipt.diagnosticOnly &&
        r275SemanticReceipt.boundaryPreserved &&
        r275SemanticReceipt.reviewReady &&
        r275SemanticReceipt.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_translated_semantic_receipt_snapshot(
                r275SemanticReceipt,
                r275SemanticReceipt.reviewSnapshotToken),
        "R275 seals R276 source-derived semantic translation plan");

    const auto r275StaleMappingReceipt =
        outrun::vr::dx11::
            compose_programmable_shader_translated_semantic_receipt(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r274SourceMappingHandoff,
                staleR274MappingToken,
                r276TranslationPlan,
                r276TranslationPlan.reviewSnapshotToken);
    require(
        r275StaleMappingReceipt.sourceMappingHandoffReady &&
        !r275StaleMappingReceipt.sourceMappingHandoffSnapshotMatches &&
        !r275StaleMappingReceipt.cacheIdentityMatches &&
        !r275StaleMappingReceipt.reviewReady &&
        r275StaleMappingReceipt.reviewSnapshotToken == 0,
        "R275 rejects stale R273 mapping handoff before semantic receipt sealing");

    const auto staleR276PlanToken =
        r276TranslationPlan.reviewSnapshotToken == 1ull
            ? 2ull
            : (r276TranslationPlan.reviewSnapshotToken ^ 1ull);
    const auto r275StaleTranslationPlanReceipt =
        outrun::vr::dx11::
            compose_programmable_shader_translated_semantic_receipt(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r274SourceMappingHandoff,
                r274SourceMappingHandoff.reviewSnapshotToken,
                r276TranslationPlan,
                staleR276PlanToken);
    require(
        r275StaleTranslationPlanReceipt.translationPlanReady &&
        !r275StaleTranslationPlanReceipt.translationPlanSnapshotMatches &&
        !r275StaleTranslationPlanReceipt.cacheIdentityMatches &&
        !r275StaleTranslationPlanReceipt.reviewReady &&
        r275StaleTranslationPlanReceipt.reviewSnapshotToken == 0,
        "R275 rejects stale R276 semantic translation plan snapshot");

    const auto r263SemanticTranslation =
        outrun::vr::dx11::
            compose_programmable_shader_semantic_translation_readiness(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275SemanticReceipt,
                r275SemanticReceipt.reviewSnapshotToken,
                r268Linkage);
    require(
        r263SemanticTranslation.inputValid &&
        r263SemanticTranslation.sourceIdentityExact &&
        r263SemanticTranslation.translationObjectReady &&
        r263SemanticTranslation.translationObjectSnapshotMatches &&
        r263SemanticTranslation.inputLayoutReady &&
        r263SemanticTranslation.inputLayoutSnapshotMatches &&
        r263SemanticTranslation.cacheIdentityMatches &&
        r263SemanticTranslation.translatedSemanticReceiptReady &&
        r263SemanticTranslation.translatedSemanticReceiptSnapshotMatches &&
        r263SemanticTranslation.translatedSemanticIdentityMatches &&
        r263SemanticTranslation.sourceMappingHandoffReady &&
        r263SemanticTranslation.sourceMappingHandoffSnapshotMatches &&
        r263SemanticTranslation.sourceMappingIdentityMatches &&
        r263SemanticTranslation.vertexSemanticExact &&
        r263SemanticTranslation.pixelSemanticExact &&
        r263SemanticTranslation.constantRegisterMappingExact &&
        r263SemanticTranslation.samplerMappingExact &&
        r263SemanticTranslation.translatedSemanticReceiptSnapshotToken ==
            r275SemanticReceipt.reviewSnapshotToken &&
        r263SemanticTranslation.sourcePairSemanticHash ==
            r275SemanticReceipt.sourcePairSemanticHash &&
        r263SemanticTranslation.sourceConstantMappingHash ==
            r275SemanticReceipt.sourceConstantMappingHash &&
        r263SemanticTranslation.sourceSamplerMappingHash ==
            r275SemanticReceipt.sourceSamplerMappingHash &&
        r263SemanticTranslation.interfaceLinkExact &&
        r263SemanticTranslation.translatorRevisionHash ==
            r276TranslationPlan.translatorRevisionHash &&
        r263SemanticTranslation.semanticContractHash ==
            r276TranslationPlan.semanticContractHash &&
        r263SemanticTranslation.semanticProofPresent &&
        r263SemanticTranslation.diagnosticOnly &&
        r263SemanticTranslation.boundaryPreserved &&
        r263SemanticTranslation.reviewReady &&
        r263SemanticTranslation.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_semantic_translation_readiness_snapshot(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275SemanticReceipt,
                r275SemanticReceipt.reviewSnapshotToken,
                r268Linkage,
                r263SemanticTranslation.reviewSnapshotToken),
        "R275 R263 consumes snapshot-sealed translated semantic receipt");

    auto r269StaleInterfaceLinkage = r268Linkage;
    r269StaleInterfaceLinkage.vertexSourceBytecodeHash ^= 1ull;
    const auto r263MissingInterfaceProof =
        outrun::vr::dx11::
            compose_programmable_shader_semantic_translation_readiness(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275SemanticReceipt,
                r275SemanticReceipt.reviewSnapshotToken,
                r269StaleInterfaceLinkage);
    require(
        r263MissingInterfaceProof.inputValid &&
        r263MissingInterfaceProof.sourceIdentityExact &&
        r263MissingInterfaceProof.translatedSemanticIdentityMatches &&
        !r263MissingInterfaceProof.interfaceSourceIdentityMatches &&
        !r263MissingInterfaceProof.interfaceLinkExact &&
        !r263MissingInterfaceProof.semanticProofPresent &&
        !r263MissingInterfaceProof.reviewReady &&
        r263MissingInterfaceProof.reviewSnapshotToken == 0,
        "R269 rejects R268 linkage provenance that does not match R263 source pair identity");

    const auto staleR275ReceiptToken =
        r275SemanticReceipt.reviewSnapshotToken == 1ull
            ? 2ull
            : (r275SemanticReceipt.reviewSnapshotToken ^ 1ull);
    const auto r263StaleSemanticReceipt =
        outrun::vr::dx11::
            compose_programmable_shader_semantic_translation_readiness(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275SemanticReceipt,
                staleR275ReceiptToken,
                r268Linkage);
    require(
        !r263StaleSemanticReceipt.translatedSemanticReceiptReady &&
        !r263StaleSemanticReceipt.translatedSemanticReceiptSnapshotMatches &&
        !r263StaleSemanticReceipt.translatedSemanticIdentityMatches &&
        !r263StaleSemanticReceipt.semanticProofPresent &&
        !r263StaleSemanticReceipt.reviewReady &&
        r263StaleSemanticReceipt.reviewSnapshotToken == 0,
        "R263 rejects stale R275 translated semantic receipt");

    auto r275MissingConstantReceipt = r275SemanticReceipt;
    r275MissingConstantReceipt.constantRegisterMappingExact = false;
    const auto r263MissingConstantMapping =
        outrun::vr::dx11::
            compose_programmable_shader_semantic_translation_readiness(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275MissingConstantReceipt,
                r275SemanticReceipt.reviewSnapshotToken,
                r268Linkage);
    require(
        !r263MissingConstantMapping.translatedSemanticReceiptReady &&
        !r263MissingConstantMapping.constantRegisterMappingExact &&
        !r263MissingConstantMapping.semanticProofPresent &&
        !r263MissingConstantMapping.reviewReady &&
        r263MissingConstantMapping.reviewSnapshotToken == 0,
        "R263 rejects incomplete programmable constant-register semantic proof");

    auto r275MissingSamplerReceipt = r275SemanticReceipt;
    r275MissingSamplerReceipt.samplerMappingExact = false;
    const auto r263MissingSamplerMapping =
        outrun::vr::dx11::
            compose_programmable_shader_semantic_translation_readiness(
                programmablePair,
                r242ObjectReady, r242ObjectReady.snapshotToken,
                r243InputLayoutReady, r243InputLayoutReady.snapshotToken,
                r275MissingSamplerReceipt,
                r275SemanticReceipt.reviewSnapshotToken,
                r268Linkage);
    require(
        !r263MissingSamplerMapping.translatedSemanticReceiptReady &&
        !r263MissingSamplerMapping.samplerMappingExact &&
        !r263MissingSamplerMapping.semanticProofPresent &&
        !r263MissingSamplerMapping.reviewReady &&
        r263MissingSamplerMapping.reviewSnapshotToken == 0,
        "R263 rejects incomplete programmable sampler semantic proof");

    auto r304TamperedR262ForDirectPrerequisite =
        r262IndexedOutputResourceBehavior;
    r304TamperedR262ForDirectPrerequisite.surfacePairSnapshotToken += 1ull;
    const auto r304TamperedDirectPrerequisite =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r304TamperedR262ForDirectPrerequisite,
            r304TamperedR262ForDirectPrerequisite.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r304TamperedDirectPrerequisite.resourceBehaviorReviewReady &&
        r304TamperedDirectPrerequisite.resourceBehaviorSnapshotMatches &&
        !r304TamperedDirectPrerequisite.
            resourceBehaviorPayloadSnapshotMatches &&
        !r304TamperedDirectPrerequisite.resourceBehaviorGeometryProofPresent &&
        !r304TamperedDirectPrerequisite.resourceBehaviorTextureProofPresent &&
        !r304TamperedDirectPrerequisite.resourceBehaviorOutputProofPresent &&
        !r304TamperedDirectPrerequisite.resourceBehaviorCoverageComplete &&
        !r304TamperedDirectPrerequisite.resourceBehaviorProofPresent &&
        (r304TamperedDirectPrerequisite.missingPrerequisiteMask & 0x1u) != 0 &&
        !r304TamperedDirectPrerequisite.activationPrerequisitesSatisfied &&
        !r304TamperedDirectPrerequisite.boundaryPreserved &&
        !r304TamperedDirectPrerequisite.reviewReady &&
        r304TamperedDirectPrerequisite.reviewSnapshotToken == 0 &&
        r304TamperedDirectPrerequisite.activationSnapshotToken == 0,
        "R304 rejects R262 payload drift at shared R259 prerequisite gate");

    const auto r259IndexedPrerequisiteHandoff =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r259IndexedPrerequisiteHandoff.inputValid &&
        r259IndexedPrerequisiteHandoff.sourceRevalidationReady &&
        r259IndexedPrerequisiteHandoff.sourceRevalidationSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.
            sourceRevalidationPayloadSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.sourceIdentityMatches &&
        r259IndexedPrerequisiteHandoff.cacheKey == programmablePair.cacheKey &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorReviewReady &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.
            resourceBehaviorPayloadSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorGeometryProofPresent &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorTextureProofPresent &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorOutputProofPresent &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorCoverageComplete &&
        r259IndexedPrerequisiteHandoff.inputLayoutOwnershipReady &&
        r259IndexedPrerequisiteHandoff.inputLayoutSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.shaderTranslationReviewReady &&
        r259IndexedPrerequisiteHandoff.shaderTranslationSnapshotMatches &&
        r259IndexedPrerequisiteHandoff.resourceBehaviorProofPresent &&
        r259IndexedPrerequisiteHandoff.inputLayoutProofPresent &&
        r259IndexedPrerequisiteHandoff.shaderTranslationProofPresent &&
        r259IndexedPrerequisiteHandoff.sourceIdentityProofPresent &&
        r259IndexedPrerequisiteHandoff.activationPrerequisitesSatisfied &&
        r259IndexedPrerequisiteHandoff.diagnosticOnly &&
        !r259IndexedPrerequisiteHandoff.nativeDrawPathActivationAllowed &&
        !r259IndexedPrerequisiteHandoff.drawDispatchAuthorized &&
        r259IndexedPrerequisiteHandoff.boundaryPreserved &&
        r259IndexedPrerequisiteHandoff.reviewReady &&
        r259IndexedPrerequisiteHandoff.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::Indexed &&
        r259IndexedPrerequisiteHandoff.indexed &&
        r259IndexedPrerequisiteHandoff.missingPrerequisiteMask == 0 &&
        r259IndexedPrerequisiteHandoff.reviewSnapshotToken != 0 &&
        r259IndexedPrerequisiteHandoff.activationSnapshotToken == 0 &&
        outrun::vr::dx11::
            validate_programmable_activation_prerequisite_handoff_snapshot(
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken,
                r243InputLayoutReady,
                r243InputLayoutReady.snapshotToken,
                r263SemanticTranslation,
                r263SemanticTranslation.reviewSnapshotToken,
                r259IndexedPrerequisiteHandoff.reviewSnapshotToken),
        "R259 indexed review handoff consumes exact F18+F21 while activation remains fail-closed");

    auto r303TamperedR262ForProductionPrerequisites =
        r262IndexedOutputResourceBehavior;
    r303TamperedR262ForProductionPrerequisites.surfaceBindingSnapshotToken +=
        1ull;
    const auto r303TamperedProductionActivationPrerequisites =
        outrun::vr::dx11::
            observe_programmable_shader_production_activation_prerequisites(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r303TamperedR262ForProductionPrerequisites,
                r303TamperedR262ForProductionPrerequisites.reviewSnapshotToken);
    require(
        r303TamperedProductionActivationPrerequisites.resourceBehaviorReady &&
        r303TamperedProductionActivationPrerequisites.
            resourceBehaviorSnapshotMatches &&
        !r303TamperedProductionActivationPrerequisites.
            resourceBehaviorPayloadSnapshotMatches &&
        !r303TamperedProductionActivationPrerequisites.
            prerequisiteHandoffReady &&
        !r303TamperedProductionActivationPrerequisites.
            prerequisiteHandoffSnapshotMatches &&
        !r303TamperedProductionActivationPrerequisites.
            staticPrerequisitesSatisfied &&
        !r303TamperedProductionActivationPrerequisites.boundaryPreserved &&
        !r303TamperedProductionActivationPrerequisites.reviewReady &&
        r303TamperedProductionActivationPrerequisites.reviewSnapshotToken == 0,
        "R303 rejects R262 payload drift before production prerequisite handoff");

    const auto r292ProductionActivationPrerequisites =
        outrun::vr::dx11::
            observe_programmable_shader_production_activation_prerequisites(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken);
    require(
        r292ProductionActivationPrerequisites.inputValid &&
        r292ProductionActivationPrerequisites.productionSemanticReviewReady &&
        r292ProductionActivationPrerequisites.
            productionSemanticReviewSnapshotMatches &&
        r292ProductionActivationPrerequisites.sourceRevalidationReady &&
        r292ProductionActivationPrerequisites.
            sourceRevalidationSnapshotMatches &&
        r292ProductionActivationPrerequisites.resourceBehaviorReady &&
        r292ProductionActivationPrerequisites.
            resourceBehaviorSnapshotMatches &&
        r292ProductionActivationPrerequisites.
            resourceBehaviorPayloadSnapshotMatches &&
        r292ProductionActivationPrerequisites.prerequisiteHandoffReady &&
        r292ProductionActivationPrerequisites.
            prerequisiteHandoffSnapshotMatches &&
        r292ProductionActivationPrerequisites.staticPrerequisitesSatisfied &&
        r292ProductionActivationPrerequisites.missingPrerequisiteMask == 0 &&
        !r292ProductionActivationPrerequisites.objectBindingAuthorized &&
        !r292ProductionActivationPrerequisites.
            nativeDrawPathActivationAllowed &&
        !r292ProductionActivationPrerequisites.drawDispatchAuthorized &&
        r292ProductionActivationPrerequisites.diagnosticOnly &&
        r292ProductionActivationPrerequisites.boundaryPreserved &&
        r292ProductionActivationPrerequisites.reviewReady &&
        r292ProductionActivationPrerequisites.reviewSnapshotToken != 0 &&
        r292ProductionActivationPrerequisites.prerequisites.
            activationSnapshotToken == 0 &&
        outrun::vr::dx11::
            validate_programmable_shader_production_activation_prerequisite_snapshot(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken,
                r292ProductionActivationPrerequisites,
                r292ProductionActivationPrerequisites.reviewSnapshotToken),
        "R292 production activation-prerequisite observation combines exact R289+R258+R262 through R259 without activation");

    auto r305TamperedProductionActivationPayload =
        r292ProductionActivationPrerequisites;
    r305TamperedProductionActivationPayload.sourceRevalidationReady = false;
    require(
        !outrun::vr::dx11::
            validate_programmable_shader_production_activation_prerequisite_snapshot(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken,
                r305TamperedProductionActivationPayload,
                r292ProductionActivationPrerequisites.reviewSnapshotToken),
        "R305 rejects copied R292 observation payload drift before production census trust");

    auto r305TamperedNestedPrerequisitePayload =
        r292ProductionActivationPrerequisites;
    r305TamperedNestedPrerequisitePayload.prerequisites.
        resourceBehaviorGeometryProofPresent = false;
    require(
        !outrun::vr::dx11::
            validate_programmable_shader_production_activation_prerequisite_snapshot(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken,
                r305TamperedNestedPrerequisitePayload,
                r292ProductionActivationPrerequisites.reviewSnapshotToken),
        "R305 rejects copied R259 prerequisite payload drift nested under R292");

    const auto r292StaleSemanticReview =
        outrun::vr::dx11::
            observe_programmable_shader_production_activation_prerequisites(
                r289ProductionSemanticReview,
                r289ProductionSemanticReview.reviewSnapshotToken ^ 0x1ull,
                r258IndexedSourceRevalidation,
                r258IndexedSourceRevalidation.snapshotToken,
                r262IndexedOutputResourceBehavior,
                r262IndexedOutputResourceBehavior.reviewSnapshotToken);
    require(
        r292StaleSemanticReview.productionSemanticReviewReady &&
        !r292StaleSemanticReview.productionSemanticReviewSnapshotMatches &&
        !r292StaleSemanticReview.staticPrerequisitesSatisfied &&
        !r292StaleSemanticReview.boundaryPreserved &&
        !r292StaleSemanticReview.reviewReady &&
        r292StaleSemanticReview.reviewSnapshotToken == 0,
        "R292 rejects stale R289 production semantic review before R259 composition");

    auto r290ForeignPairInputLayout = r243InputLayoutReady;
    r290ForeignPairInputLayout.cacheKey ^= 0x1ull;
    if (r290ForeignPairInputLayout.cacheKey == 0)
        r290ForeignPairInputLayout.cacheKey = 1;
    auto r290ForeignPairSemanticTranslation = r263SemanticTranslation;
    r290ForeignPairSemanticTranslation.cacheKey =
        r290ForeignPairInputLayout.cacheKey;
    const auto r290CrossPairPrerequisiteHandoff =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r290ForeignPairInputLayout,
            r243InputLayoutReady.snapshotToken,
            r290ForeignPairSemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r290CrossPairPrerequisiteHandoff.inputValid &&
        r290CrossPairPrerequisiteHandoff.sourceRevalidationReady &&
        r290CrossPairPrerequisiteHandoff.sourceRevalidationSnapshotMatches &&
        !r290CrossPairPrerequisiteHandoff.sourceIdentityMatches &&
        r290CrossPairPrerequisiteHandoff.resourceBehaviorProofPresent &&
        r290CrossPairPrerequisiteHandoff.inputLayoutProofPresent &&
        r290CrossPairPrerequisiteHandoff.shaderTranslationProofPresent &&
        !r290CrossPairPrerequisiteHandoff.sourceIdentityProofPresent &&
        (r290CrossPairPrerequisiteHandoff.missingPrerequisiteMask & 0x8u) != 0 &&
        !r290CrossPairPrerequisiteHandoff.activationPrerequisitesSatisfied &&
        !r290CrossPairPrerequisiteHandoff.boundaryPreserved &&
        !r290CrossPairPrerequisiteHandoff.reviewReady &&
        r290CrossPairPrerequisiteHandoff.reviewSnapshotToken == 0 &&
        r290CrossPairPrerequisiteHandoff.activationSnapshotToken == 0,
        "R290 rejects cross-pair R258 versus R243/R263 prerequisite evidence");

    const auto staleR263ReviewToken =
        r263SemanticTranslation.reviewSnapshotToken == 1ull
            ? 2ull
            : (r263SemanticTranslation.reviewSnapshotToken ^ 1ull);
    const auto r259IndexedStaleShaderTranslation =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            staleR263ReviewToken);
    require(
        r259IndexedStaleShaderTranslation.shaderTranslationReviewReady &&
        !r259IndexedStaleShaderTranslation.shaderTranslationSnapshotMatches &&
        !r259IndexedStaleShaderTranslation.shaderTranslationProofPresent &&
        (r259IndexedStaleShaderTranslation.missingPrerequisiteMask & 0x4u) != 0 &&
        !r259IndexedStaleShaderTranslation.activationPrerequisitesSatisfied &&
        !r259IndexedStaleShaderTranslation.reviewReady &&
        r259IndexedStaleShaderTranslation.reviewSnapshotToken == 0 &&
        r259IndexedStaleShaderTranslation.activationSnapshotToken == 0,
        "R259 rejects stale R263 shader semantic-translation identity");

    const auto staleR258IndexedReviewToken =
        r258IndexedSourceRevalidation.snapshotToken == 1ull
            ? 2ull
            : (r258IndexedSourceRevalidation.snapshotToken ^ 1ull);
    const auto r259IndexedStaleSource =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            staleR258IndexedReviewToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r259IndexedStaleSource.sourceRevalidationReady &&
        !r259IndexedStaleSource.sourceRevalidationSnapshotMatches &&
        !r259IndexedStaleSource.reviewReady &&
        r259IndexedStaleSource.reviewSnapshotToken == 0 &&
        r259IndexedStaleSource.activationSnapshotToken == 0,
        "R259 rejects stale R258 source-revalidation identity");

    auto r299TamperedR258 = r258IndexedSourceRevalidation;
    r299TamperedR258.startLocation += 1u;
    const auto r299TamperedSource =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r299TamperedR258,
            r299TamperedR258.snapshotToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r299TamperedSource.sourceRevalidationReady &&
        r299TamperedSource.sourceRevalidationSnapshotMatches &&
        !r299TamperedSource.sourceRevalidationPayloadSnapshotMatches &&
        !r299TamperedSource.sourceIdentityMatches &&
        !r299TamperedSource.sourceIdentityProofPresent &&
        (r299TamperedSource.missingPrerequisiteMask & 0x8u) != 0 &&
        !r299TamperedSource.activationPrerequisitesSatisfied &&
        !r299TamperedSource.boundaryPreserved &&
        !r299TamperedSource.reviewReady &&
        r299TamperedSource.reviewSnapshotToken == 0 &&
        r299TamperedSource.activationSnapshotToken == 0,
        "R299 rejects R258 payload drift hidden behind an unchanged source-revalidation snapshot token");

    const auto staleR261IndexedReviewToken =
        r262IndexedOutputResourceBehavior.reviewSnapshotToken == 1ull
            ? 2ull
            : (r262IndexedOutputResourceBehavior.reviewSnapshotToken ^ 1ull);
    const auto r259IndexedStaleResourceBehavior =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r262IndexedOutputResourceBehavior,
            staleR261IndexedReviewToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r259IndexedStaleResourceBehavior.resourceBehaviorReviewReady &&
        !r259IndexedStaleResourceBehavior.resourceBehaviorSnapshotMatches &&
        !r259IndexedStaleResourceBehavior.resourceBehaviorGeometryProofPresent &&
        !r259IndexedStaleResourceBehavior.resourceBehaviorOutputProofPresent &&
        !r259IndexedStaleResourceBehavior.reviewReady &&
        r259IndexedStaleResourceBehavior.reviewSnapshotToken == 0 &&
        r259IndexedStaleResourceBehavior.activationSnapshotToken == 0,
        "R259 rejects stale R262 resource-behavior identity");

    const auto staleR243ReviewToken =
        r243InputLayoutReady.snapshotToken == 1ull
            ? 2ull
            : (r243InputLayoutReady.snapshotToken ^ 1ull);
    const auto r259IndexedStaleInputLayout =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258IndexedSourceRevalidation,
            r258IndexedSourceRevalidation.snapshotToken,
            r262IndexedOutputResourceBehavior,
            r262IndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            staleR243ReviewToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r259IndexedStaleInputLayout.inputLayoutOwnershipReady &&
        !r259IndexedStaleInputLayout.inputLayoutSnapshotMatches &&
        !r259IndexedStaleInputLayout.inputLayoutProofPresent &&
        (r259IndexedStaleInputLayout.missingPrerequisiteMask & 0x2u) != 0 &&
        !r259IndexedStaleInputLayout.reviewReady &&
        r259IndexedStaleInputLayout.reviewSnapshotToken == 0 &&
        r259IndexedStaleInputLayout.activationSnapshotToken == 0,
        "R259 rejects stale R243 input-layout identity");

    const auto r258IndexedSourceDrift =
        programmableCache.indexed_dormant_source_revalidation_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 1u,
            firstR252DispatchSnapshot,
            firstR253SourceValueSnapshot,
            firstR254LiveIndexSnapshot,
            r256IndexedCandidate.snapshotToken,
            r257IndexedPreActivation.snapshotToken);
    require(
        !r258IndexedSourceDrift.sourceReceiptReady &&
        !r258IndexedSourceDrift.candidateReady &&
        !r258IndexedSourceDrift.ready &&
        r258IndexedSourceDrift.snapshotToken == 0,
        "R258 indexed final dormant handoff rejects current source-state drift");

    const auto r252DeclaredRangeExcludesZero =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 1u, 3u, 0u);
    require(
        r252DeclaredRangeExcludesZero.ready &&
        r252DeclaredRangeExcludesZero.snapshotToken != 0,
        "R253 setup keeps R252 numeric range valid while excluding source index zero");
    const auto r253DeclaredRangeViolation =
        programmableCache.indexed_source_value_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 1u, 3u, 0u,
            r252DeclaredRangeExcludesZero.snapshotToken);
    require(
        r253DeclaredRangeViolation.directDispatchReady &&
        r253DeclaredRangeViolation.directDispatchSnapshotMatches &&
        r253DeclaredRangeViolation.indexMirrorSnapshotMatches &&
        !r253DeclaredRangeViolation.sourceValuesReady &&
        !r253DeclaredRangeViolation.ready &&
        r253DeclaredRangeViolation.snapshotToken == 0,
        "R253 rejects managed source index outside declared D3D9 vertex range");

    const auto r253StaleR252 =
        programmableCache.indexed_source_value_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot ^ 1ull);
    require(
        r253StaleR252.directDispatchReady &&
        !r253StaleR252.directDispatchSnapshotMatches &&
        !r253StaleR252.sourceValuesReady &&
        !r253StaleR252.ready &&
        r253StaleR252.snapshotToken == 0,
        "R253 stale R252 dispatch receipt cannot seal source values");

    const auto r252StaleGeometry =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot ^ 1ull,
            1u, 0, 0u, 4u, 0u);
    require(
        r252StaleGeometry.geometryBindingReady &&
        !r252StaleGeometry.geometryBindingSnapshotMatches &&
        !r252StaleGeometry.ready &&
        r252StaleGeometry.snapshotToken == 0,
        "R252 stale R249 geometry receipt cannot seal indexed dispatch");

    const auto r252IndexRangeOverflow =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 4u);
    require(
        r252IndexRangeOverflow.countExact &&
        r252IndexRangeOverflow.sourceVertexRangeExact &&
        !r252IndexRangeOverflow.indexBufferRangeExact &&
        !r252IndexRangeOverflow.dispatchArgumentsExact &&
        !r252IndexRangeOverflow.ready,
        "R252 out-of-range index window fails closed");

    const auto r252VertexRangeOverflow =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 8u, 4u, 0u);
    require(
        r252VertexRangeOverflow.sourceVertexRangeExact &&
        r252VertexRangeOverflow.effectiveVertexRangeExact &&
        !r252VertexRangeOverflow.vertexBufferRangeExact &&
        !r252VertexRangeOverflow.ready,
        "R252 out-of-range declared vertex window fails closed");

    const auto r252EffectiveUnderflow =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, -1, 0u, 4u, 0u);
    require(
        r252EffectiveUnderflow.sourceVertexRangeExact &&
        !r252EffectiveUnderflow.effectiveVertexRangeExact &&
        !r252EffectiveUnderflow.vertexBufferRangeExact &&
        !r252EffectiveUnderflow.ready,
        "R252 negative effective vertex range fails closed");

    const auto r252CountOverflow =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            (std::numeric_limits<UINT>::max)() / 3u + 1u,
            0, 0u, 4u, 0u);
    require(
        !r252CountOverflow.countExact &&
        !r252CountOverflow.indexBufferRangeExact &&
        !r252CountOverflow.dispatchArgumentsExact &&
        !r252CountOverflow.ready,
        "R252 indexed primitive-count overflow fails closed");

    const auto r252SameDispatch =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u);
    require(
        r252SameDispatch.ready &&
        r252SameDispatch.snapshotToken == firstR252DispatchSnapshot,
        "R252 same indexed dispatch arguments are idempotent");

    require(
        programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset).snapshotToken ==
            firstR249BindingSnapshot,
        "R249 same indexed geometry binding is idempotent");

    ID3D11Buffer* r249Vertex = managedVertexBuffer.mirror_buffer();
    const UINT r249DriftedStride = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &r249Vertex, &r249DriftedStride, &geometryVertexOffset);
    const auto r249VertexDrift =
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        r249VertexDrift.geometryReceiptPresent &&
        !r249VertexDrift.vertexBufferMatches &&
        r249VertexDrift.indexBufferMatches &&
        !r249VertexDrift.bindingReady &&
        !programmableCache.validate_indexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot),
        "R249 external vertex stride drift invalidates indexed geometry receipt");
    d3d.context->IASetVertexBuffers(
        0, 1, &r249Vertex, &geometryVertexStride, &geometryVertexOffset);

    d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0);
    const auto r249IndexDrift =
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        r249IndexDrift.geometryReceiptPresent &&
        r249IndexDrift.vertexBufferMatches &&
        !r249IndexDrift.indexBufferMatches &&
        !r249IndexDrift.bindingReady,
        "R249 external index binding drift invalidates indexed geometry receipt");
    const auto r252LiveGeometryDrift =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u);
    require(
        !r252LiveGeometryDrift.geometryBindingReady &&
        !r252LiveGeometryDrift.geometryBindingSnapshotMatches &&
        !r252LiveGeometryDrift.ready &&
        !programmableCache.validate_indexed_source_value_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot,
            firstR253SourceValueSnapshot) &&
        !programmableCache.validate_indexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot),
        "R252 live IA drift invalidates indexed dispatch receipt");
    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(),
        DXGI_FORMAT_R16_UINT, geometryIndexOffset);

    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto r248DriftedTopology =
        programmableCache.primitive_topology_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST);
    require(
        r248DriftedTopology.topologyReceiptPresent &&
        !r248DriftedTopology.topologyMatches &&
        !r248DriftedTopology.bindingReady &&
        !programmableCache.validate_primitive_topology_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot),
        "R248 external topology drift invalidates topology binding receipt");
    require(
        !programmableCache.validate_indexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot),
        "R249 upstream topology drift invalidates indexed geometry receipt");
    d3d.context->IASetPrimitiveTopology(
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);

    const auto r250UnboundGeometry =
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset);
    require(
        r250UnboundGeometry.inputValid &&
        r250UnboundGeometry.topologyBindingReceiptReady &&
        r250UnboundGeometry.topologyBindingSnapshotMatches &&
        r250UnboundGeometry.vertexBufferCurrent &&
        !r250UnboundGeometry.geometryReceiptPresent &&
        !r250UnboundGeometry.bindingReady &&
        r250UnboundGeometry.nonIndexedGeometryBindingReceiptGeneration == 0 &&
        r250UnboundGeometry.snapshotToken == 0 &&
        !programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST, 0,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset),
        "R250 topology-binding receipt must exist before non-indexed geometry binding");

    require(
        !programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken ^ 1ull,
            geometryVertexStride, geometryVertexOffset),
        "R250 stale managed vertex mirror snapshot cannot bind non-indexed geometry");

    ID3D11DeviceContext* r250DeferredBeforeBinding = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(
            0, &r250DeferredBeforeBinding)) &&
        r250DeferredBeforeBinding != nullptr &&
        !programmableCache.bind_nonindexed_geometry_for_observation(
            r250DeferredBeforeBinding, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset),
        "R250 non-immediate context cannot establish non-indexed geometry binding");
    r250DeferredBeforeBinding->Release();

    require(
        programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset),
        "R250 exact programmable non-indexed IA geometry binding");
    const auto r250GeometryReady =
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset);
    require(
        r250GeometryReady.bindingReady &&
        r250GeometryReady.geometryReceiptPresent &&
        r250GeometryReady.vertexBufferMatches &&
        r250GeometryReady.indexBufferClear &&
        r250GeometryReady.nonIndexedGeometryBindingReceiptGeneration != 0 &&
        r250GeometryReady.snapshotToken != 0 &&
        programmableCache.validate_nonindexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            r250GeometryReady.snapshotToken),
        "R250 exact programmable non-indexed geometry binding receipt");
    const auto firstR250ReceiptGeneration =
        r250GeometryReady.nonIndexedGeometryBindingReceiptGeneration;
    const auto firstR250BindingSnapshot = r250GeometryReady.snapshotToken;

    const auto r251DispatchReady =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u);
    require(
        r251DispatchReady.inputValid &&
        r251DispatchReady.geometryBindingReady &&
        r251DispatchReady.geometryBindingSnapshotMatches &&
        r251DispatchReady.primitiveExact &&
        r251DispatchReady.topologyMatchesGeometry &&
        r251DispatchReady.countExact &&
        r251DispatchReady.vertexRangeExact &&
        r251DispatchReady.dispatchArgumentsExact &&
        r251DispatchReady.componentSnapshotsPresent &&
        r251DispatchReady.ready &&
        r251DispatchReady.vertexCount == 3u &&
        r251DispatchReady.vertexBufferByteWidth ==
            managedVertexBuffer.byte_width() &&
        r251DispatchReady.snapshotToken != 0 &&
        programmableCache.validate_nonindexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u, r251DispatchReady.snapshotToken),
        "R251 exact programmable non-indexed direct dispatch arguments");
    const auto firstR251DispatchSnapshot = r251DispatchReady.snapshotToken;

    const auto r256NonIndexedCandidate =
        outrun::vr::dx11::compose_programmable_draw_candidate_readiness(
            r251DispatchReady, firstR251DispatchSnapshot);
    require(
        r256NonIndexedCandidate.inputValid &&
        r256NonIndexedCandidate.selectedReceiptReady &&
        r256NonIndexedCandidate.selectedReceiptSnapshotMatches &&
        r256NonIndexedCandidate.componentSnapshotsPresent &&
        r256NonIndexedCandidate.ready &&
        r256NonIndexedCandidate.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
        !r256NonIndexedCandidate.indexed &&
        r256NonIndexedCandidate.elementCount == 3u &&
        r256NonIndexedCandidate.startLocation == 0u &&
        r256NonIndexedCandidate.indexFormat == DXGI_FORMAT_UNKNOWN &&
        r256NonIndexedCandidate.indexOffset == 0u &&
        r256NonIndexedCandidate.sourceReceiptSnapshotToken ==
            firstR251DispatchSnapshot &&
        r256NonIndexedCandidate.snapshotToken != 0 &&
        r256NonIndexedCandidate.snapshotToken !=
            r256IndexedCandidate.snapshotToken &&
        outrun::vr::dx11::validate_programmable_draw_candidate_snapshot(
            r251DispatchReady, firstR251DispatchSnapshot,
            r256NonIndexedCandidate.snapshotToken),
        "R256 non-indexed draw-candidate union accepts current R251 receipt");
    const auto staleR251CandidateSource =
        firstR251DispatchSnapshot == 1ull ? 2ull : 1ull;
    const auto r256NonIndexedStale =
        outrun::vr::dx11::compose_programmable_draw_candidate_readiness(
            r251DispatchReady, staleR251CandidateSource);
    require(
        r256NonIndexedStale.selectedReceiptReady &&
        !r256NonIndexedStale.selectedReceiptSnapshotMatches &&
        !r256NonIndexedStale.ready &&
        r256NonIndexedStale.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_programmable_draw_candidate_snapshot(
            r251DispatchReady, staleR251CandidateSource,
            r256NonIndexedCandidate.snapshotToken),
        "R256 non-indexed draw-candidate union rejects stale R251 receipt");

    const auto r257NonIndexedPreActivation =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            r256NonIndexedCandidate, r256NonIndexedCandidate.snapshotToken);
    require(
        r257NonIndexedPreActivation.inputValid &&
        r257NonIndexedPreActivation.candidateReady &&
        r257NonIndexedPreActivation.candidateSnapshotMatches &&
        r257NonIndexedPreActivation.candidatePayloadSnapshotMatches &&
        r257NonIndexedPreActivation.candidateKindValid &&
        r257NonIndexedPreActivation.diagnosticOnly &&
        !r257NonIndexedPreActivation.activationProofPresent &&
        !r257NonIndexedPreActivation.nativeDrawPathActivationAllowed &&
        !r257NonIndexedPreActivation.drawDispatchAuthorized &&
        r257NonIndexedPreActivation.boundaryPreserved &&
        r257NonIndexedPreActivation.ready &&
        r257NonIndexedPreActivation.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
        !r257NonIndexedPreActivation.indexed &&
        r257NonIndexedPreActivation.candidateSnapshotToken ==
            r256NonIndexedCandidate.snapshotToken &&
        r257NonIndexedPreActivation.snapshotToken != 0 &&
        outrun::vr::dx11::validate_programmable_dormant_pre_activation_snapshot(
            r256NonIndexedCandidate, r256NonIndexedCandidate.snapshotToken,
            r257NonIndexedPreActivation.snapshotToken),
        "R257 non-indexed candidate seals dormant pre-activation review without draw authorization");

    auto tamperedR256NonIndexedCandidate = r256NonIndexedCandidate;
    tamperedR256NonIndexedCandidate.startLocation += 1u;
    const auto r257NonIndexedTampered =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            tamperedR256NonIndexedCandidate,
            tamperedR256NonIndexedCandidate.snapshotToken);
    require(
        r257NonIndexedTampered.candidateSnapshotMatches &&
        !r257NonIndexedTampered.candidatePayloadSnapshotMatches &&
        r257NonIndexedTampered.candidateKindValid &&
        !r257NonIndexedTampered.ready &&
        r257NonIndexedTampered.snapshotToken == 0,
        "R298 rejects non-indexed source-start drift hidden behind an unchanged R256 snapshot token");

    auto malformedR256NonIndexedCandidate = r256NonIndexedCandidate;
    malformedR256NonIndexedCandidate.indexed = true;
    const auto r257NonIndexedMalformed =
        outrun::vr::dx11::compose_programmable_dormant_pre_activation_readiness(
            malformedR256NonIndexedCandidate,
            malformedR256NonIndexedCandidate.snapshotToken);
    require(
        r257NonIndexedMalformed.candidateSnapshotMatches &&
        r257NonIndexedMalformed.candidatePayloadSnapshotMatches &&
        !r257NonIndexedMalformed.candidateKindValid &&
        !r257NonIndexedMalformed.ready &&
        r257NonIndexedMalformed.snapshotToken == 0,
        "R257 rejects non-indexed R256 branch-tag mismatch");

    const auto r258NonIndexedSourceRevalidation =
        programmableCache.nonindexed_dormant_source_revalidation_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u,
            r256NonIndexedCandidate.snapshotToken,
            r257NonIndexedPreActivation.snapshotToken);
    require(
        r258NonIndexedSourceRevalidation.inputValid &&
        r258NonIndexedSourceRevalidation.sourceReceiptReady &&
        r258NonIndexedSourceRevalidation.sourceReceiptSnapshotPresent &&
        r258NonIndexedSourceRevalidation.candidateReady &&
        r258NonIndexedSourceRevalidation.candidateSnapshotMatches &&
        r258NonIndexedSourceRevalidation.preActivationReady &&
        r258NonIndexedSourceRevalidation.preActivationSnapshotMatches &&
        r258NonIndexedSourceRevalidation.sourceLineageMatches &&
        r258NonIndexedSourceRevalidation.candidateLineageMatches &&
        r258NonIndexedSourceRevalidation.boundaryPreserved &&
        r258NonIndexedSourceRevalidation.ready &&
        r258NonIndexedSourceRevalidation.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
        !r258NonIndexedSourceRevalidation.indexed &&
        r258NonIndexedSourceRevalidation.currentSourceReceiptSnapshotToken ==
            firstR251DispatchSnapshot &&
        r258NonIndexedSourceRevalidation.candidateSnapshotToken ==
            r256NonIndexedCandidate.snapshotToken &&
        r258NonIndexedSourceRevalidation.preActivationSnapshotToken ==
            r257NonIndexedPreActivation.snapshotToken &&
        r258NonIndexedSourceRevalidation.snapshotToken != 0,
        "R258 non-indexed final dormant handoff revalidates current R251 source state");

    const auto r260NonIndexedResourceBehavior =
        outrun::vr::dx11::compose_programmable_resource_behavior_readiness(
            r258NonIndexedSourceRevalidation,
            r258NonIndexedSourceRevalidation.snapshotToken,
            d3d.device,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            nullptr,
            0);
    require(
        r260NonIndexedResourceBehavior.sourceRevalidationReady &&
        r260NonIndexedResourceBehavior.sourceRevalidationSnapshotMatches &&
        r260NonIndexedResourceBehavior.
            sourceRevalidationPayloadSnapshotMatches &&
        r260NonIndexedResourceBehavior.vertexMirrorReady &&
        r260NonIndexedResourceBehavior.vertexMirrorSnapshotMatches &&
        !r260NonIndexedResourceBehavior.indexMirrorRequired &&
        r260NonIndexedResourceBehavior.indexMirrorReady &&
        r260NonIndexedResourceBehavior.indexMirrorSnapshotMatches &&
        r260NonIndexedResourceBehavior.geometryResourceBehaviorExact &&
        !r260NonIndexedResourceBehavior.fullResourceBehaviorProofPresent &&
        r260NonIndexedResourceBehavior.missingResourceScopeMask == 0x6u &&
        r260NonIndexedResourceBehavior.reviewReady &&
        r260NonIndexedResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_resource_behavior_readiness_snapshot(
                r258NonIndexedSourceRevalidation,
                r258NonIndexedSourceRevalidation.snapshotToken,
                d3d.device,
                managedVertexBuffer,
                managedVertexPostResetReady.snapshotToken,
                nullptr,
                0,
                r260NonIndexedResourceBehavior.reviewSnapshotToken),
        "R260 non-indexed geometry resource behavior is exact without inventing index coverage");

    const auto r261NonIndexedTextureResourceBehavior =
        outrun::vr::dx11::
            compose_programmable_texture_resource_behavior_readiness(
                r260NonIndexedResourceBehavior,
                r260NonIndexedResourceBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken);
    require(
        r261NonIndexedTextureResourceBehavior.geometryReviewReady &&
        r261NonIndexedTextureResourceBehavior.geometrySnapshotMatches &&
        r261NonIndexedTextureResourceBehavior.
            geometryPayloadSnapshotMatches &&
        r261NonIndexedTextureResourceBehavior.textureStageSnapshotMatches &&
        r261NonIndexedTextureResourceBehavior.geometryResourceBehaviorExact &&
        r261NonIndexedTextureResourceBehavior.textureResourceBehaviorExact &&
        !r261NonIndexedTextureResourceBehavior.outputResourceBehaviorProofPresent &&
        !r261NonIndexedTextureResourceBehavior.fullResourceBehaviorProofPresent &&
        r261NonIndexedTextureResourceBehavior.missingResourceScopeMask == 0x4u &&
        r261NonIndexedTextureResourceBehavior.reviewReady &&
        r261NonIndexedTextureResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_texture_resource_behavior_readiness_snapshot(
                r260NonIndexedResourceBehavior,
                r260NonIndexedResourceBehavior.reviewSnapshotToken,
                r261TextureRegistry,
                r261TextureKeys.data(), r261TextureKeys.size(),
                d3d.device,
                r261TextureStages,
                r261TextureStages.snapshotToken,
                r261NonIndexedTextureResourceBehavior.reviewSnapshotToken),
        "R261 non-indexed texture resource behavior reuses exact current texture stage without widening F18");

    const auto r262NonIndexedOutputResourceBehavior =
        outrun::vr::dx11::
            compose_programmable_output_resource_behavior_readiness(
                r261NonIndexedTextureResourceBehavior,
                r261NonIndexedTextureResourceBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                r262SurfaceBindingReady.snapshotToken);
    require(
        r262NonIndexedOutputResourceBehavior.textureReviewReady &&
        r262NonIndexedOutputResourceBehavior.textureSnapshotMatches &&
        r262NonIndexedOutputResourceBehavior.surfacePairSnapshotMatches &&
        r262NonIndexedOutputResourceBehavior.surfaceBindingSnapshotMatches &&
        r262NonIndexedOutputResourceBehavior.geometryResourceBehaviorExact &&
        r262NonIndexedOutputResourceBehavior.textureResourceBehaviorExact &&
        r262NonIndexedOutputResourceBehavior.outputResourceBehaviorExact &&
        r262NonIndexedOutputResourceBehavior.fullResourceBehaviorProofPresent &&
        r262NonIndexedOutputResourceBehavior.missingResourceScopeMask == 0 &&
        r262NonIndexedOutputResourceBehavior.reviewReady &&
        r262NonIndexedOutputResourceBehavior.reviewSnapshotToken != 0 &&
        outrun::vr::dx11::
            validate_programmable_output_resource_behavior_readiness_snapshot(
                r261NonIndexedTextureResourceBehavior,
                r261NonIndexedTextureResourceBehavior.reviewSnapshotToken,
                d3d.context, d3d.device,
                r262SurfacePair, r262SurfacePair.snapshotToken,
                r262SurfaceBinding,
                r262OutputColorSurface, r262OutputDepthSurface,
                r262SurfaceBindingReady.snapshotToken,
                r262NonIndexedOutputResourceBehavior.reviewSnapshotToken),
        "R262 non-indexed output resource behavior closes full F18 on the same current output pair");

    const auto r259NonIndexedPrerequisiteHandoff =
        outrun::vr::dx11::compose_programmable_activation_prerequisite_handoff(
            r258NonIndexedSourceRevalidation,
            r258NonIndexedSourceRevalidation.snapshotToken,
            r262NonIndexedOutputResourceBehavior,
            r262NonIndexedOutputResourceBehavior.reviewSnapshotToken,
            r243InputLayoutReady,
            r243InputLayoutReady.snapshotToken,
            r263SemanticTranslation,
            r263SemanticTranslation.reviewSnapshotToken);
    require(
        r259NonIndexedPrerequisiteHandoff.sourceRevalidationReady &&
        r259NonIndexedPrerequisiteHandoff.sourceRevalidationSnapshotMatches &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorReviewReady &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorSnapshotMatches &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorGeometryProofPresent &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorTextureProofPresent &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorOutputProofPresent &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorCoverageComplete &&
        r259NonIndexedPrerequisiteHandoff.inputLayoutProofPresent &&
        r259NonIndexedPrerequisiteHandoff.resourceBehaviorProofPresent &&
        r259NonIndexedPrerequisiteHandoff.shaderTranslationReviewReady &&
        r259NonIndexedPrerequisiteHandoff.shaderTranslationSnapshotMatches &&
        r259NonIndexedPrerequisiteHandoff.shaderTranslationProofPresent &&
        r259NonIndexedPrerequisiteHandoff.activationPrerequisitesSatisfied &&
        r259NonIndexedPrerequisiteHandoff.boundaryPreserved &&
        r259NonIndexedPrerequisiteHandoff.reviewReady &&
        r259NonIndexedPrerequisiteHandoff.kind ==
            outrun::vr::dx11::NativeProgrammableShaderDrawCandidateKind::NonIndexed &&
        !r259NonIndexedPrerequisiteHandoff.indexed &&
        r259NonIndexedPrerequisiteHandoff.missingPrerequisiteMask == 0 &&
        r259NonIndexedPrerequisiteHandoff.reviewSnapshotToken != 0 &&
        r259NonIndexedPrerequisiteHandoff.activationSnapshotToken == 0 &&
        outrun::vr::dx11::
            validate_programmable_activation_prerequisite_handoff_snapshot(
                r258NonIndexedSourceRevalidation,
                r258NonIndexedSourceRevalidation.snapshotToken,
                r262NonIndexedOutputResourceBehavior,
                r262NonIndexedOutputResourceBehavior.reviewSnapshotToken,
                r243InputLayoutReady,
                r243InputLayoutReady.snapshotToken,
                r263SemanticTranslation,
                r263SemanticTranslation.reviewSnapshotToken,
                r259NonIndexedPrerequisiteHandoff.reviewSnapshotToken),
        "R259 non-indexed review handoff consumes exact F18+F21 while activation remains fail-closed");

    const auto r258NonIndexedSourceDrift =
        programmableCache.nonindexed_dormant_source_revalidation_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            0u, 0u,
            r256NonIndexedCandidate.snapshotToken,
            r257NonIndexedPreActivation.snapshotToken);
    require(
        r258NonIndexedSourceDrift.sourceReceiptReady &&
        r258NonIndexedSourceDrift.candidateReady &&
        !r258NonIndexedSourceDrift.candidateSnapshotMatches &&
        !r258NonIndexedSourceDrift.preActivationSnapshotMatches &&
        !r258NonIndexedSourceDrift.ready &&
        r258NonIndexedSourceDrift.snapshotToken == 0,
        "R258 non-indexed final dormant handoff rejects fresh source identity drift");

    const auto r251StaleGeometry =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot ^ 1ull,
            1u, 0u);
    require(
        r251StaleGeometry.geometryBindingReady &&
        !r251StaleGeometry.geometryBindingSnapshotMatches &&
        !r251StaleGeometry.ready &&
        r251StaleGeometry.snapshotToken == 0,
        "R251 stale R250 geometry receipt cannot seal dispatch arguments");

    const auto r251RangeOverflow =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 9u);
    require(
        r251RangeOverflow.countExact &&
        !r251RangeOverflow.vertexRangeExact &&
        !r251RangeOverflow.dispatchArgumentsExact &&
        !r251RangeOverflow.ready,
        "R251 out-of-range non-indexed vertex window fails closed");

    const auto r251CountOverflow =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            (std::numeric_limits<UINT>::max)() / 3u + 1u, 0u);
    require(
        !r251CountOverflow.countExact &&
        !r251CountOverflow.dispatchArgumentsExact &&
        !r251CountOverflow.ready,
        "R251 primitive-count overflow fails closed");

    const auto r251SameDispatch =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u);
    require(
        r251SameDispatch.ready &&
        r251SameDispatch.snapshotToken == firstR251DispatchSnapshot,
        "R251 same non-indexed direct dispatch arguments are idempotent");

    require(
        programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset) &&
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset).snapshotToken ==
            firstR250BindingSnapshot,
        "R250 same non-indexed geometry binding is idempotent");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(),
        DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    const auto r250IndexDrift =
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset);
    require(
        r250IndexDrift.geometryReceiptPresent &&
        r250IndexDrift.vertexBufferMatches &&
        !r250IndexDrift.indexBufferClear &&
        !r250IndexDrift.bindingReady &&
        !programmableCache.validate_nonindexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot),
        "R250 external index binding invalidates explicit IB-clear receipt");
    d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0);

    ID3D11Buffer* r250Vertex = managedVertexBuffer.mirror_buffer();
    const UINT r250DriftedStride = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &r250Vertex, &r250DriftedStride, &geometryVertexOffset);
    const auto r250VertexDrift =
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset);
    require(
        r250VertexDrift.geometryReceiptPresent &&
        !r250VertexDrift.vertexBufferMatches &&
        r250VertexDrift.indexBufferClear &&
        !r250VertexDrift.bindingReady,
        "R250 external vertex binding drift invalidates non-indexed geometry receipt");
    const auto r251LiveGeometryDrift =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u);
    require(
        !r251LiveGeometryDrift.geometryBindingReady &&
        !r251LiveGeometryDrift.geometryBindingSnapshotMatches &&
        !r251LiveGeometryDrift.ready &&
        !programmableCache.validate_nonindexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            r247PipelineReady.snapshotToken,
            D3DPT_TRIANGLELIST,
            r248TopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u, firstR251DispatchSnapshot),
        "R251 live IA drift invalidates non-indexed dispatch receipt");
    d3d.context->IASetVertexBuffers(
        0, 1, &r250Vertex, &geometryVertexStride, &geometryVertexOffset);

    d3d.context->PSSetShader(nullptr, nullptr, 0);
    const auto r247DriftedPipeline =
        programmableCache.pipeline_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken);
    require(
        r247DriftedPipeline.bindingReceiptPresent &&
        r247DriftedPipeline.vertexShaderMatches &&
        !r247DriftedPipeline.pixelShaderMatches &&
        r247DriftedPipeline.inputLayoutMatches &&
        !r247DriftedPipeline.bindingReady &&
        !programmableCache.validate_pipeline_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            r246BindingReady.snapshotToken,
            firstR247BindingSnapshot),
        "R247 external shader drift invalidates pipeline binding receipt");

    ID3D11Buffer* r246NullPixelSlot = nullptr;
    d3d.context->PSSetConstantBuffers(0, 1, &r246NullPixelSlot);
    const auto r246DriftedBinding =
        programmableCache.constant_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken);
    require(
        r246DriftedBinding.bindingReceiptPresent &&
        r246DriftedBinding.vertexSlotMatches &&
        !r246DriftedBinding.pixelSlotMatches &&
        !r246DriftedBinding.bindingReady &&
        !programmableCache.validate_constant_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout, r243InputLayoutReady.snapshotToken,
            r244ConstantStateReady.snapshotToken,
            r245PayloadReady.snapshotToken,
            firstR246BindingSnapshot),
        "R246 external b0 slot drift invalidates binding receipt");

    const std::string r242AlternateVertexSource = R"(
struct VSInput { float4 position : POSITION0; };
struct VSOutput { float4 position : SV_Position; };
VSOutput main(VSInput input)
{
    VSOutput output;
    output.position = input.position;
    return output;
}
)";
    ID3DBlob* r242AlternateVertexBytecode =
        compile_vertex_shader(r242AlternateVertexSource);
    ID3D11VertexShader* r242AlternateVertexShader = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateVertexShader(
            r242AlternateVertexBytecode->GetBufferPointer(),
            r242AlternateVertexBytecode->GetBufferSize(),
            nullptr,
            &r242AlternateVertexShader)) &&
        r242AlternateVertexShader != nullptr &&
        r242AlternateVertexShader != pipelineBundle.vertex_shader(),
        "R242 distinct translated vertex object prerequisite");
    require(
        !programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242AlternateVertexShader,
            pipelineBundle.pixel_shader()),
        "R242 different translated object pair cannot replace sealed receipt");
    r242AlternateVertexShader->Release();
    r242AlternateVertexBytecode->Release();

    DevicePair r242ForeignDevice = create_warp_device();
    NativeFixedFunctionPipelineBundle r242ForeignPipeline;
    require(
        r242ForeignPipeline.initialize(
            r242ForeignDevice.device,
            inputLayout, vertexPrototype, pixelPrototype) &&
        !programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ForeignPipeline.vertex_shader(),
            r242ForeignPipeline.pixel_shader()),
        "R242 foreign-device translated object pair fails closed");
    require(
        !programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            r242ObjectReady.snapshotToken,
            inputLayout,
            r242ForeignPipeline.input_layout()),
        "R243 foreign-device input layout fails closed");
    r242ForeignPipeline.shutdown();
    r242ForeignDevice.context->Release();
    r242ForeignDevice.device->Release();

    require(
        programmableCache.initialize(d3d.device) &&
        !programmableCache.validate_translation_object_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot),
        "R242 device reinitialize invalidates translated object receipt");
    require(
        !programmableCache.validate_input_layout_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot),
        "R243 device reinitialize invalidates input layout receipt");
    require(
        !programmableCache.validate_constant_state_snapshot(
            d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot),
        "R244 device reinitialize invalidates constant-state receipt");
    require(
        !programmableCache.validate_constant_payload_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot),
        "R245 device reinitialize invalidates constant-payload receipt");
    require(
        !programmableCache.validate_constant_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot),
        "R246 device reinitialize invalidates constant-binding receipt");
    require(
        !programmableCache.validate_pipeline_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot),
        "R247 device reinitialize invalidates pipeline-binding receipt");
    require(
        !programmableCache.validate_primitive_topology_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot),
        "R248 device reinitialize invalidates topology-binding receipt");
    require(
        !programmableCache.validate_indexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot),
        "R249 device reinitialize invalidates indexed geometry receipt");
    require(
        !programmableCache.validate_indexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            firstR249BindingSnapshot,
            1u, 0, 0u, 4u, 0u, firstR252DispatchSnapshot),
        "R252 device reinitialize invalidates indexed dispatch receipt");
    require(
        !programmableCache.validate_nonindexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot),
        "R250 device reinitialize invalidates non-indexed geometry receipt");
    require(
        !programmableCache.validate_nonindexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242CacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            firstR243InputLayoutSnapshot,
            firstR244ConstantStateSnapshot,
            firstR245PayloadSnapshot,
            firstR246BindingSnapshot,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLELIST,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            firstR250BindingSnapshot,
            1u, 0u, firstR251DispatchSnapshot),
        "R251 device reinitialize invalidates non-indexed dispatch receipt");
    require(
        programmableCache.cache_for_observation(programmablePair),
        "R242 fresh cache generation prerequisite");
    const auto r242FreshCacheReady =
        programmableCache.readiness(d3d.device, programmablePair);
    require(
        r242FreshCacheReady.ready &&
        programmableCache.reserve_translation_slot_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken),
        "R242 fresh slot generation prerequisite");
    const auto r242FreshSlotReady =
        programmableCache.translation_slot_ownership_readiness(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken);
    require(
        r242FreshSlotReady.ownershipReady &&
        !programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242SlotReady.snapshotToken,
            pipelineBundle.vertex_shader(),
            pipelineBundle.pixel_shader()),
        "R242 stale slot snapshot cannot attach translated objects");
    require(
        programmableCache.attach_translation_objects_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            pipelineBundle.vertex_shader(),
            pipelineBundle.pixel_shader()),
        "R242 fresh slot accepts translated object pair");
    const auto r242FreshObjectReady =
        programmableCache.translation_object_readiness(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken);
    require(
        r242FreshObjectReady.attachmentReady &&
        r242FreshObjectReady.translationObjectReceiptGeneration !=
            firstR242ReceiptGeneration &&
        r242FreshObjectReady.snapshotToken !=
            firstR242ObjectSnapshot,
        "R242 fresh device generation receives a distinct object receipt");
    require(
        !programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            firstR242ObjectSnapshot,
            inputLayout,
            pipelineBundle.input_layout()),
        "R243 stale object receipt cannot attach input layout");
    require(
        programmableCache.attach_input_layout_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout,
            pipelineBundle.input_layout()),
        "R243 fresh object receipt accepts input layout");
    const auto r243FreshInputLayoutReady =
        programmableCache.input_layout_readiness(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout);
    require(
        r243FreshInputLayoutReady.attachmentReady &&
        r243FreshInputLayoutReady.inputLayoutDeviceMatches &&
        r243FreshInputLayoutReady.inputLayoutReceiptGeneration !=
            firstR243ReceiptGeneration &&
        r243FreshInputLayoutReady.snapshotToken !=
            firstR243InputLayoutSnapshot &&
        programmableCache.validate_input_layout_snapshot(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout,
            r243FreshInputLayoutReady.snapshotToken),
        "R243 fresh device generation receives distinct input layout receipt");
    require(
        !programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, firstR243InputLayoutSnapshot,
            r244VertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes),
        "R244 stale input-layout receipt cannot attach constant state");
    require(
        programmableCache.attach_constant_state_for_observation(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244VertexConstants, r244ConstantBytes,
            r244PixelConstants, r244ConstantBytes),
        "R244 fresh R243 receipt accepts constant state");
    const auto r244FreshConstantStateReady =
        programmableCache.constant_state_readiness(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken);
    require(
        r244FreshConstantStateReady.attachmentReady &&
        r244FreshConstantStateReady.constantBufferDevicesMatch &&
        r244FreshConstantStateReady.constantBufferDescriptorsExact &&
        r244FreshConstantStateReady.constantStateReceiptGeneration !=
            firstR244ReceiptGeneration &&
        r244FreshConstantStateReady.snapshotToken !=
            firstR244ConstantStateSnapshot &&
        programmableCache.validate_constant_state_snapshot(
            d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken),
        "R244 fresh device generation receives distinct constant-state receipt");
    require(
        !programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            firstR244ConstantStateSnapshot,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 stale constant-state receipt cannot upload payload");
    require(
        programmableCache.upload_constant_payload_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245VertexPayload.data(), r244ConstantBytes,
            r245PixelPayload.data(), r244ConstantBytes),
        "R245 fresh R244 receipt accepts exact constant payload");
    const auto r245FreshPayloadReady =
        programmableCache.constant_payload_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken);
    require(
        r245FreshPayloadReady.uploadReady &&
        r245FreshPayloadReady.payloadReceiptPresent &&
        r245FreshPayloadReady.payloadBytesExact &&
        r245FreshPayloadReady.constantPayloadReceiptGeneration !=
            firstR245ReceiptGeneration &&
        r245FreshPayloadReady.snapshotToken != firstR245PayloadSnapshot &&
        programmableCache.validate_constant_payload_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken),
        "R245 fresh device generation receives distinct constant-payload receipt");
    require(
        !programmableCache.bind_constant_slots_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            firstR245PayloadSnapshot),
        "R246 stale constant-payload receipt cannot bind slots");
    require(
        programmableCache.bind_constant_slots_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken),
        "R246 fresh R245 receipt binds exact VS/PS b0 slots");
    const auto r246FreshBindingReady =
        programmableCache.constant_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken);
    require(
        r246FreshBindingReady.bindingReady &&
        r246FreshBindingReady.bindingReceiptPresent &&
        r246FreshBindingReady.vertexSlotMatches &&
        r246FreshBindingReady.pixelSlotMatches &&
        r246FreshBindingReady.constantBindingReceiptGeneration !=
            firstR246ReceiptGeneration &&
        r246FreshBindingReady.snapshotToken != firstR246BindingSnapshot &&
        programmableCache.validate_constant_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken),
        "R246 fresh device generation receives distinct constant-binding receipt");
    require(
        !programmableCache.bind_pipeline_objects_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            firstR246BindingSnapshot),
        "R247 stale constant-binding receipt cannot bind pipeline objects");
    require(
        programmableCache.bind_pipeline_objects_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken),
        "R247 fresh R246 receipt binds exact programmable pipeline objects");
    const auto r247FreshPipelineReady =
        programmableCache.pipeline_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken);
    require(
        r247FreshPipelineReady.bindingReady &&
        r247FreshPipelineReady.bindingReceiptPresent &&
        r247FreshPipelineReady.vertexShaderMatches &&
        r247FreshPipelineReady.pixelShaderMatches &&
        r247FreshPipelineReady.inputLayoutMatches &&
        r247FreshPipelineReady.pipelineBindingReceiptGeneration !=
            firstR247ReceiptGeneration &&
        r247FreshPipelineReady.snapshotToken != firstR247BindingSnapshot &&
        programmableCache.validate_pipeline_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken),
        "R247 fresh device generation receives distinct pipeline-binding receipt");
    require(
        !programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            firstR247BindingSnapshot,
            D3DPT_TRIANGLESTRIP),
        "R248 stale pipeline-binding receipt cannot bind topology");
    require(
        programmableCache.bind_primitive_topology_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP),
        "R248 fresh R247 receipt binds exact translated topology");
    const auto r248FreshTopologyReady =
        programmableCache.primitive_topology_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP);
    require(
        r248FreshTopologyReady.bindingReady &&
        r248FreshTopologyReady.topologyReceiptPresent &&
        r248FreshTopologyReady.topologyMatches &&
        r248FreshTopologyReady.translatedTopology ==
            D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP &&
        r248FreshTopologyReady.topologyBindingReceiptGeneration !=
            firstR248ReceiptGeneration &&
        r248FreshTopologyReady.snapshotToken != firstR248BindingSnapshot &&
        programmableCache.validate_primitive_topology_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken),
        "R248 fresh device generation receives distinct topology-binding receipt");
    require(
        !programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 stale topology receipt cannot bind indexed geometry");
    require(
        programmableCache.bind_indexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R249 fresh R248 receipt binds exact indexed geometry");
    const auto r249FreshGeometryReady =
        programmableCache.indexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        r249FreshGeometryReady.bindingReady &&
        r249FreshGeometryReady.geometryReceiptPresent &&
        r249FreshGeometryReady.vertexBufferMatches &&
        r249FreshGeometryReady.indexBufferMatches &&
        r249FreshGeometryReady.indexedGeometryBindingReceiptGeneration !=
            firstR249ReceiptGeneration &&
        r249FreshGeometryReady.snapshotToken != firstR249BindingSnapshot &&
        programmableCache.validate_indexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r249FreshGeometryReady.snapshotToken),
        "R249 fresh device generation receives distinct indexed geometry receipt");
    const auto r252FreshDispatchReady =
        programmableCache.indexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r249FreshGeometryReady.snapshotToken,
            1u, 0, 0u, 4u, 0u);
    require(
        r252FreshDispatchReady.ready &&
        r252FreshDispatchReady.indexCount == 3u &&
        r252FreshDispatchReady.snapshotToken != firstR252DispatchSnapshot &&
        programmableCache.validate_indexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            managedIndexBuffer, managedIndexReady.snapshotToken,
            DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            r249FreshGeometryReady.snapshotToken,
            1u, 0, 0u, 4u, 0u, r252FreshDispatchReady.snapshotToken),
        "R252 fresh device generation receives distinct indexed dispatch receipt");
    require(
        !programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            firstR248BindingSnapshot,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset),
        "R250 stale topology receipt cannot bind non-indexed geometry");
    require(
        programmableCache.bind_nonindexed_geometry_for_observation(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset),
        "R250 fresh R248 receipt binds exact non-indexed geometry");
    const auto r250FreshGeometryReady =
        programmableCache.nonindexed_geometry_binding_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset);
    require(
        r250FreshGeometryReady.bindingReady &&
        r250FreshGeometryReady.geometryReceiptPresent &&
        r250FreshGeometryReady.vertexBufferMatches &&
        r250FreshGeometryReady.indexBufferClear &&
        r250FreshGeometryReady.nonIndexedGeometryBindingReceiptGeneration !=
            firstR250ReceiptGeneration &&
        r250FreshGeometryReady.snapshotToken != firstR250BindingSnapshot &&
        programmableCache.validate_nonindexed_geometry_binding_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            r250FreshGeometryReady.snapshotToken),
        "R250 fresh device generation receives distinct non-indexed geometry receipt");
    const auto r251FreshDispatchReady =
        programmableCache.nonindexed_direct_dispatch_readiness(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            r250FreshGeometryReady.snapshotToken,
            1u, 1u);
    require(
        r251FreshDispatchReady.ready &&
        r251FreshDispatchReady.vertexCount == 3u &&
        r251FreshDispatchReady.snapshotToken != firstR251DispatchSnapshot &&
        programmableCache.validate_nonindexed_direct_dispatch_snapshot(
            d3d.context, d3d.device, programmablePair,
            r242FreshCacheReady.snapshotToken,
            r242FreshSlotReady.snapshotToken,
            r242FreshObjectReady.snapshotToken,
            inputLayout, r243FreshInputLayoutReady.snapshotToken,
            r244FreshConstantStateReady.snapshotToken,
            r245FreshPayloadReady.snapshotToken,
            r246FreshBindingReady.snapshotToken,
            r247FreshPipelineReady.snapshotToken,
            D3DPT_TRIANGLESTRIP,
            r248FreshTopologyReady.snapshotToken,
            managedVertexBuffer,
            managedVertexPostResetReady.snapshotToken,
            geometryVertexStride, geometryVertexOffset,
            r250FreshGeometryReady.snapshotToken,
            1u, 1u, r251FreshDispatchReady.snapshotToken),
        "R251 fresh device generation receives distinct non-indexed dispatch receipt");
    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        outrun::vr::dx11::validate_fixed_function_geometry_binding_snapshot(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            indexedGeometryBinding.snapshotToken),
        "R248 restores prior fixed-function IA geometry after topology probe; R249 restores prior fixed-function IA geometry after indexed geometry probe; R250 restores prior fixed-function IA geometry after non-indexed geometry probe");
    r244VertexConstants->Release();
    r244PixelConstants->Release();

    require(
        pipelineBundle.upload_transform_for_observation(d3d.context, transform),
        "final VS b0 transform upload prerequisite");
    const auto pipelineTransformBindingReady =
        pipelineBundle.transform_buffer().binding_readiness(
            d3d.context, transform);
    require(
        pipelineTransformBindingReady.inputValid &&
        pipelineTransformBindingReady.ownerReady &&
        pipelineTransformBindingReady.contextMatches &&
        pipelineTransformBindingReady.payloadMatches &&
        pipelineTransformBindingReady.boundExact &&
        pipelineTransformBindingReady.uploadPresent &&
        pipelineTransformBindingReady.ready &&
        pipelineTransformBindingReady.payloadHash == transform.payloadHash &&
        pipelineTransformBindingReady.snapshotToken != 0 &&
        pipelineBundle.transform_buffer().validate_binding_snapshot(
            d3d.context, transform, pipelineTransformBindingReady.snapshotToken),
        "final VS b0 transform binding seals exact WVP payload");

    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "dormant pipeline binding accepts exact same-device R97 snapshot");

    // R154 WARP: same-device command recording must not acquire an
    // immediate-context IA/VS/PS receipt or alter the live pipeline.
    ID3D11DeviceContext* r154DeferredContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(0, &r154DeferredContext)) &&
        r154DeferredContext != nullptr &&
        r154DeferredContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R154 same-device deferred pipeline prerequisite");
    require(
        !pipelineBundle.bind_for_observation(
            r154DeferredContext, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R154 deferred context rejected by pipeline binding");
    const auto r154DeferredPipeline = pipelineBundle.binding_readiness(
        r154DeferredContext, inputLayout, vertexPrototype, pixelPrototype,
        pipelineIdentityReady.snapshotToken);
    require(
        !r154DeferredPipeline.inputValid && !r154DeferredPipeline.ready &&
        r154DeferredPipeline.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            r154DeferredContext, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken, 1),
        "R154 deferred pipeline never yields a live receipt");
    const auto r154ImmediatePipeline = pipelineBundle.binding_readiness(
        d3d.context, inputLayout, vertexPrototype, pixelPrototype,
        pipelineIdentityReady.snapshotToken);
    require(
        r154ImmediatePipeline.ready &&
        r154ImmediatePipeline.snapshotToken != 0 &&
        pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            r154ImmediatePipeline.snapshotToken),
        "R154 immediate pipeline remains bound and valid");
    r154DeferredContext->Release();

    ID3D11InputLayout* boundPipelineLayout = nullptr;
    ID3D11VertexShader* boundPipelineVertexShader = nullptr;
    ID3D11PixelShader* boundPipelinePixelShader = nullptr;
    d3d.context->IAGetInputLayout(&boundPipelineLayout);
    d3d.context->VSGetShader(
        &boundPipelineVertexShader, nullptr, nullptr);
    d3d.context->PSGetShader(
        &boundPipelinePixelShader, nullptr, nullptr);
    require(
        boundPipelineLayout == pipelineBundle.input_layout() &&
        boundPipelineVertexShader == pipelineBundle.vertex_shader() &&
        boundPipelinePixelShader == pipelineBundle.pixel_shader(),
        "dormant pipeline binding preserves exact IA VS PS identity");
    if (boundPipelineLayout)
        boundPipelineLayout->Release();
    if (boundPipelineVertexShader)
        boundPipelineVertexShader->Release();
    if (boundPipelinePixelShader)
        boundPipelinePixelShader->Release();

    require(
        !pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype, 0),
        "dormant pipeline binding rejects missing R97 snapshot");
    require(
        !pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken ^ 0x100000001b3ull),
        "dormant pipeline binding rejects stale R97 snapshot");

    DevicePair pipelineBindingForeignDevice = create_warp_device();
    require(
        !pipelineBundle.bind_for_observation(
            pipelineBindingForeignDevice.context,
            inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "dormant pipeline binding rejects foreign D3D11 context");
    pipelineBindingForeignDevice.context->Release();
    pipelineBindingForeignDevice.device->Release();

    d3d.context->IASetInputLayout(nullptr);
    d3d.context->VSSetShader(vertexShader, nullptr, 0);
    d3d.context->PSSetShader(nullptr, nullptr, 0);

    NativeManagedTextureStageReadiness untexturedStageReady{};
    untexturedStageReady.inputValid = true;
    untexturedStageReady.allRequiredReady = true;
    const auto untexturedActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, untexturedStageReady);
    require(
        untexturedActivation.inputValid &&
        untexturedActivation.pipelineReady &&
        untexturedActivation.textureStagesReady &&
        untexturedActivation.componentSnapshotsPresent &&
        untexturedActivation.ready &&
        untexturedActivation.requiredTextureMask == 0 &&
        untexturedActivation.pipelineSnapshotToken ==
            pipelineIdentityReady.snapshotToken &&
        untexturedActivation.textureSnapshotToken == 0 &&
        untexturedActivation.snapshotToken != 0 &&
        validate_fixed_function_activation_snapshot(
            pipelineIdentityReady, untexturedStageReady,
            untexturedActivation.snapshotToken),
        "R115 composite activation readiness accepts exact untextured evidence");

    NativeManagedTextureStageReadiness texturedStageReady{};
    texturedStageReady.inputValid = true;
    texturedStageReady.allRequiredReady = true;
    texturedStageReady.requiredMask = 0x1u;
    texturedStageReady.readyMask = 0x1u;
    texturedStageReady.snapshotToken = 0x115001ull;
    const auto texturedActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, texturedStageReady);
    require(
        texturedActivation.inputValid &&
        texturedActivation.pipelineReady &&
        texturedActivation.textureStagesReady &&
        texturedActivation.componentSnapshotsPresent &&
        texturedActivation.ready &&
        texturedActivation.requiredTextureMask == 0x1u &&
        texturedActivation.textureSnapshotToken ==
            texturedStageReady.snapshotToken &&
        texturedActivation.snapshotToken != 0 &&
        validate_fixed_function_activation_snapshot(
            pipelineIdentityReady, texturedStageReady,
            texturedActivation.snapshotToken),
        "R115 composite activation readiness requires both exact component snapshots");

    auto missingTextureSnapshot = texturedStageReady;
    missingTextureSnapshot.snapshotToken = 0;
    const auto missingTextureActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, missingTextureSnapshot);
    auto pendingTextureStage = texturedStageReady;
    pendingTextureStage.allRequiredReady = false;
    pendingTextureStage.readyMask = 0;
    pendingTextureStage.pendingMask = 0x1u;
    pendingTextureStage.snapshotToken = 0;
    const auto pendingTextureActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, pendingTextureStage);
    auto pipelineNotReady = pipelineIdentityReady;
    pipelineNotReady.ready = false;
    const auto pipelinePendingActivation =
        compose_fixed_function_activation_readiness(
            pipelineNotReady, texturedStageReady);
    require(
        !missingTextureActivation.ready &&
        missingTextureActivation.snapshotToken == 0 &&
        !pendingTextureActivation.ready &&
        pendingTextureActivation.snapshotToken == 0 &&
        !pipelinePendingActivation.ready &&
        pipelinePendingActivation.snapshotToken == 0,
        "R115 composite activation readiness fails closed on missing component evidence");

    auto changedPipelineIdentity = pipelineIdentityReady;
    changedPipelineIdentity.snapshotToken ^= 0x100000001b3ull;
    const auto changedActivation =
        compose_fixed_function_activation_readiness(
            changedPipelineIdentity, texturedStageReady);
    require(
        changedActivation.ready &&
        changedActivation.snapshotToken != 0 &&
        changedActivation.snapshotToken != texturedActivation.snapshotToken &&
        !validate_fixed_function_activation_snapshot(
            changedPipelineIdentity, texturedStageReady,
            texturedActivation.snapshotToken) &&
        validate_fixed_function_activation_snapshot(
            changedPipelineIdentity, texturedStageReady,
            changedActivation.snapshotToken),
        "R115 composite activation snapshot changes with component identity");

    outrun::vr::dx11::NativeSurfaceMirror outputColorSurface;
    require(
        outputColorSurface.initialize(
            d3d.device, ResourceRole::Color, 64u, 32u,
            D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_RENDERTARGET,
            D3DMULTISAMPLE_NONE, 0u),
        "R145 live OM color mirror prerequisite");
    outrun::vr::dx11::NativeSurfaceMirror outputDepthSurface;
    require(
        outputDepthSurface.initialize(
            d3d.device, ResourceRole::DepthStencil, 64u, 32u,
            D3DFMT_D24S8, D3DPOOL_DEFAULT, D3DUSAGE_DEPTHSTENCIL,
            D3DMULTISAMPLE_NONE, 0u),
        "R145 live OM depth mirror prerequisite");
    const auto surfacePairReady =
        outrun::vr::dx11::compose_surface_pair_readiness(
            d3d.device, outputColorSurface, outputDepthSurface);
    require(
        surfacePairReady.ready &&
        surfacePairReady.snapshotToken != 0,
        "R145 live OM surface pair prerequisite");

    outrun::vr::dx11::NativeSurfacePairBinding surfaceTargetBinding;
    require(
        surfaceTargetBinding.initialize(
            d3d.device, outputColorSurface, outputDepthSurface,
            surfacePairReady) &&
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface),
        "R145 live OM target owner prerequisite");
    const auto surfaceTargetBindingReady =
        surfaceTargetBinding.binding_readiness(
            d3d.context, outputColorSurface, outputDepthSurface);
    require(
        surfaceTargetBindingReady.ready &&
        surfaceTargetBindingReady.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        surfaceTargetBindingReady.snapshotToken != 0 &&
        surfaceTargetBinding.validate_binding_snapshot(
            d3d.context, outputColorSurface, outputDepthSurface,
            surfaceTargetBindingReady.snapshotToken),
        "R145 live OM target prerequisite seals current RTV DSV");

    auto outputStateSource = renderStateSource;
    outputStateSource.outputStateComplete = true;
    outputStateSource.scissorTestEnable = TRUE;
    outputStateSource.blendFactor = 0xFF804020u;
    outputStateSource.multiSampleMask = 0x0F0FF0F0u;
    outputStateSource.viewport.X = 4;
    outputStateSource.viewport.Y = 2;
    outputStateSource.viewport.Width = 56;
    outputStateSource.viewport.Height = 28;
    outputStateSource.viewport.MinZ = 0.125f;
    outputStateSource.viewport.MaxZ = 0.875f;
    outputStateSource.scissorRect = RECT{5, 3, 58, 29};

    const auto outputStateReady =
        compose_fixed_function_output_state_readiness(
            outputStateSource, surfacePairReady);
    require(
        outputStateReady.inputValid &&
        outputStateReady.viewportExact &&
        outputStateReady.scissorExact &&
        outputStateReady.omDynamicExact &&
        outputStateReady.ready &&
        outputStateReady.viewport.TopLeftX == 4.0f &&
        outputStateReady.viewport.TopLeftY == 2.0f &&
        outputStateReady.viewport.Width == 56.0f &&
        outputStateReady.viewport.Height == 28.0f &&
        outputStateReady.viewport.MinDepth == 0.125f &&
        outputStateReady.viewport.MaxDepth == 0.875f &&
        outputStateReady.scissorRect.left == 5 &&
        outputStateReady.scissorRect.top == 3 &&
        outputStateReady.scissorRect.right == 58 &&
        outputStateReady.scissorRect.bottom == 29 &&
        outputStateReady.blendFactor[0] == 128.0f / 255.0f &&
        outputStateReady.blendFactor[1] == 64.0f / 255.0f &&
        outputStateReady.blendFactor[2] == 32.0f / 255.0f &&
        outputStateReady.blendFactor[3] == 1.0f &&
        outputStateReady.sampleMask == 0x0F0FF0F0u &&
        outputStateReady.snapshotToken != 0 &&
        validate_fixed_function_output_state_snapshot(
            outputStateSource, surfacePairReady,
            outputStateReady.snapshotToken),
        "R124 exact dynamic output state issues a valid snapshot");

    const auto outputBindingTranslation =
        translate_pipeline(outputStateSource);
    require(
        outputBindingTranslation.exact() &&
        outputBindingTranslation.rasterizer.ScissorEnable,
        "R126 output-state binding translation prerequisite");

    NativeFixedFunctionRenderStateBundle outputBindingRenderStateBundle;
    require(
        outputBindingRenderStateBundle.initialize(
            d3d.device, outputBindingTranslation),
        "R126 output-state binding render bundle initialize");
    const auto outputBindingRenderReady =
        outputBindingRenderStateBundle.translation_readiness(
            d3d.device, outputBindingTranslation);
    require(
        outputBindingRenderReady.ready &&
        outputBindingRenderReady.snapshotToken != 0,
        "R126 output-state binding render snapshot prerequisite");

    NativeFixedFunctionOutputStateBinding outputStateBinding;
    require(
        outputStateBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        outputStateBinding.ready() &&
        outputStateBinding.render_state_snapshot_token() ==
            outputBindingRenderReady.snapshotToken &&
        outputStateBinding.surface_pair_snapshot_token() ==
            surfacePairReady.snapshotToken &&
        outputStateBinding.output_state_snapshot_token() ==
            outputStateReady.snapshotToken &&
        outputStateBinding.snapshot_token() != 0,
        "R126 exact render/output snapshots initialize dormant binding owner");
    require(
        outputStateBinding.apply(d3d.context),
        "R126 output binding applies exact RS/OM state");

    ID3D11RasterizerState* boundRasterizer = nullptr;
    ID3D11BlendState* boundBlend = nullptr;
    ID3D11DepthStencilState* boundDepthStencil = nullptr;
    UINT boundStencilRef = 0;
    FLOAT boundBlendFactor[4] = {};
    UINT boundSampleMask = 0;
    UINT boundViewportCount = 1;
    UINT boundScissorCount = 1;
    D3D11_VIEWPORT boundViewport{};
    D3D11_RECT boundScissor{};
    d3d.context->RSGetState(&boundRasterizer);
    d3d.context->RSGetViewports(&boundViewportCount, &boundViewport);
    d3d.context->RSGetScissorRects(&boundScissorCount, &boundScissor);
    d3d.context->OMGetBlendState(
        &boundBlend, boundBlendFactor, &boundSampleMask);
    d3d.context->OMGetDepthStencilState(
        &boundDepthStencil, &boundStencilRef);
    require(
        boundRasterizer == outputBindingRenderStateBundle.rasterizer_state() &&
        boundBlend == outputBindingRenderStateBundle.blend_state() &&
        boundDepthStencil ==
            outputBindingRenderStateBundle.depth_stencil_state() &&
        boundStencilRef == outputBindingRenderStateBundle.stencil_ref() &&
        boundViewportCount == 1 &&
        boundViewport.TopLeftX == outputStateReady.viewport.TopLeftX &&
        boundViewport.TopLeftY == outputStateReady.viewport.TopLeftY &&
        boundViewport.Width == outputStateReady.viewport.Width &&
        boundViewport.Height == outputStateReady.viewport.Height &&
        boundViewport.MinDepth == outputStateReady.viewport.MinDepth &&
        boundViewport.MaxDepth == outputStateReady.viewport.MaxDepth &&
        boundScissorCount == 1 &&
        boundScissor.left == outputStateReady.scissorRect.left &&
        boundScissor.top == outputStateReady.scissorRect.top &&
        boundScissor.right == outputStateReady.scissorRect.right &&
        boundScissor.bottom == outputStateReady.scissorRect.bottom &&
        boundBlendFactor[0] == outputStateReady.blendFactor[0] &&
        boundBlendFactor[1] == outputStateReady.blendFactor[1] &&
        boundBlendFactor[2] == outputStateReady.blendFactor[2] &&
        boundBlendFactor[3] == outputStateReady.blendFactor[3] &&
        boundSampleMask == outputStateReady.sampleMask,
        "R126 WARP context exposes the exact sealed RS/OM binding");
    if (boundRasterizer)
        boundRasterizer->Release();
    if (boundBlend)
        boundBlend->Release();
    if (boundDepthStencil)
        boundDepthStencil->Release();

    const auto liveOutputBindingReady =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        liveOutputBindingReady.inputValid &&
        liveOutputBindingReady.ownerReady &&
        liveOutputBindingReady.contextMatches &&
        liveOutputBindingReady.rasterizerMatches &&
        liveOutputBindingReady.viewportMatches &&
        liveOutputBindingReady.scissorMatches &&
        liveOutputBindingReady.blendStateMatches &&
        liveOutputBindingReady.blendFactorMatches &&
        liveOutputBindingReady.sampleMaskMatches &&
        liveOutputBindingReady.depthStencilMatches &&
        liveOutputBindingReady.stencilRefMatches &&
        liveOutputBindingReady.ready &&
        liveOutputBindingReady.outputBindingSnapshotToken ==
            outputStateBinding.snapshot_token() &&
        liveOutputBindingReady.snapshotToken != 0 &&
        outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 live output binding issues exact RS OM snapshot");

    // R155 WARP: same-device deferred RS/OM recording cannot impersonate
    // the live immediate output-state binding, even with identical values.
    ID3D11DeviceContext* r155DeferredOutputContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(0, &r155DeferredOutputContext)) &&
        r155DeferredOutputContext != nullptr &&
        r155DeferredOutputContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R155 same-device deferred output-state prerequisite");
    require(
        !outputStateBinding.apply(r155DeferredOutputContext),
        "R155 deferred output-state apply must fail closed");
    r155DeferredOutputContext->RSSetState(
        outputBindingRenderStateBundle.rasterizer_state());
    r155DeferredOutputContext->RSSetViewports(1, &outputStateReady.viewport);
    r155DeferredOutputContext->RSSetScissorRects(1, &outputStateReady.scissorRect);
    r155DeferredOutputContext->OMSetBlendState(
        outputBindingRenderStateBundle.blend_state(),
        outputStateReady.blendFactor.data(), outputStateReady.sampleMask);
    r155DeferredOutputContext->OMSetDepthStencilState(
        outputBindingRenderStateBundle.depth_stencil_state(),
        outputBindingRenderStateBundle.stencil_ref());
    const auto r155DeferredOutputReceipt =
        outputStateBinding.binding_readiness(r155DeferredOutputContext);
    require(
        !r155DeferredOutputReceipt.inputValid &&
        r155DeferredOutputReceipt.ownerReady &&
        !r155DeferredOutputReceipt.ready &&
        r155DeferredOutputReceipt.snapshotToken == 0 &&
        !outputStateBinding.validate_binding_snapshot(
            r155DeferredOutputContext, liveOutputBindingReady.snapshotToken),
        "R155 recorded deferred RS/OM state cannot forge live binding receipt");
    require(
        outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R155 live immediate RS/OM receipt survives deferred recording");
    r155DeferredOutputContext->Release();

    d3d.context->RSSetState(nullptr);
    const auto driftedOutputBinding =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        driftedOutputBinding.inputValid &&
        driftedOutputBinding.ownerReady &&
        driftedOutputBinding.contextMatches &&
        !driftedOutputBinding.rasterizerMatches &&
        !driftedOutputBinding.ready &&
        driftedOutputBinding.snapshotToken == 0 &&
        !outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 live output binding fails closed after RS drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R137 live output binding restores sealed RS OM state");
    const auto restoredOutputBinding =
        outputStateBinding.binding_readiness(d3d.context);
    require(
        restoredOutputBinding.ready &&
        restoredOutputBinding.snapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        outputStateBinding.validate_binding_snapshot(
            d3d.context, liveOutputBindingReady.snapshotToken),
        "R137 restored output binding reproduces exact snapshot");

    DevicePair outputBindingOtherDevice = create_warp_device();
    require(
        !outputStateBinding.apply(outputBindingOtherDevice.context),
        "R126 foreign D3D11 context cannot consume binding owner");
    outputBindingOtherDevice.context->Release();
    outputBindingOtherDevice.device->Release();

    NativeFixedFunctionOutputStateBinding rejectedOutputBinding;
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            outputStateSource,
            surfacePairReady,
            0) &&
        !rejectedOutputBinding.ready(),
        "R126 missing R124 snapshot token fails closed");
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            0,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 missing R116 snapshot token fails closed");

    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            renderStateBundle,
            renderStateTranslation,
            renderStateRecreated.snapshotToken,
            outputStateSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 mismatched sealed scissor state fails closed");

    auto staleOutputBindingSource = outputStateSource;
    staleOutputBindingSource.blendFactor ^= 0x00010000u;
    require(
        !rejectedOutputBinding.initialize(
            d3d.device,
            outputBindingRenderStateBundle,
            outputBindingTranslation,
            outputBindingRenderReady.snapshotToken,
            staleOutputBindingSource,
            surfacePairReady,
            outputStateReady.snapshotToken) &&
        !rejectedOutputBinding.ready(),
        "R126 stale R124 source/token pair fails closed");

    auto incompleteOutputState = outputStateSource;
    incompleteOutputState.outputStateComplete = false;
    const auto incompleteOutputReady =
        compose_fixed_function_output_state_readiness(
            incompleteOutputState, surfacePairReady);
    require(
        !incompleteOutputReady.inputValid &&
        !incompleteOutputReady.ready &&
        incompleteOutputReady.snapshotToken == 0,
        "R124 incomplete output-state observation fails closed");

    auto invalidViewportState = outputStateSource;
    invalidViewportState.viewport.Width = 61;
    const auto invalidViewportReady =
        compose_fixed_function_output_state_readiness(
            invalidViewportState, surfacePairReady);
    require(
        invalidViewportReady.inputValid &&
        !invalidViewportReady.viewportExact &&
        !invalidViewportReady.ready &&
        invalidViewportReady.snapshotToken == 0,
        "R124 out-of-bounds viewport fails closed");

    auto invalidScissorState = outputStateSource;
    invalidScissorState.scissorRect.right = 65;
    const auto invalidScissorReady =
        compose_fixed_function_output_state_readiness(
            invalidScissorState, surfacePairReady);
    require(
        invalidScissorReady.inputValid &&
        invalidScissorReady.viewportExact &&
        !invalidScissorReady.scissorExact &&
        !invalidScissorReady.ready &&
        invalidScissorReady.snapshotToken == 0,
        "R124 enabled out-of-bounds scissor fails closed");

    auto changedOutputStateSource = outputStateSource;
    changedOutputStateSource.blendFactor ^= 0x00010000u;
    changedOutputStateSource.multiSampleMask ^= 0x00000001u;
    const auto changedOutputStateReady =
        compose_fixed_function_output_state_readiness(
            changedOutputStateSource, surfacePairReady);
    require(
        changedOutputStateReady.ready &&
        changedOutputStateReady.snapshotToken != 0 &&
        changedOutputStateReady.snapshotToken !=
            outputStateReady.snapshotToken &&
        !validate_fixed_function_output_state_snapshot(
            changedOutputStateSource, surfacePairReady,
            outputStateReady.snapshotToken) &&
        validate_fixed_function_output_state_snapshot(
            changedOutputStateSource, surfacePairReady,
            changedOutputStateReady.snapshotToken),
        "R124 OM dynamic state changes invalidate output snapshot");

    constexpr UINT drawTextureStageSlot = 0;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView),
        "R132 textured draw texture-stage rebind prerequisite");
    const auto drawTextureStageReady =
        outrun::vr::dx11::observe_fixed_function_texture_stage_binding(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        drawTextureStageReady.ready &&
        drawTextureStageReady.snapshotToken != 0,
        "R132 textured draw texture-stage snapshot prerequisite");

    const auto drawReady =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        drawReady.inputValid &&
        drawReady.activationReady &&
        drawReady.renderStateReady &&
        drawReady.surfacePairReady &&
        drawReady.outputStateReady &&
        drawReady.outputBindingReady &&
        drawReady.geometryReady &&
        drawReady.componentSnapshotsPresent &&
        drawReady.ready &&
        drawReady.requiredTextureMask == 0x1u &&
        drawReady.activationSnapshotToken ==
            texturedActivation.snapshotToken &&
        drawReady.pipelineSnapshotToken ==
            texturedActivation.pipelineSnapshotToken &&
        drawReady.renderStateSnapshotToken ==
            outputBindingRenderReady.snapshotToken &&
        drawReady.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        drawReady.outputStateSnapshotToken ==
            outputStateReady.snapshotToken &&
        drawReady.outputBindingSnapshotToken ==
            outputStateBinding.snapshot_token() &&
        drawReady.geometrySnapshotToken ==
            indexedGeometryReady.snapshotToken &&
        drawReady.snapshotToken != 0 &&
        validate_fixed_function_draw_readiness_integrity(drawReady) &&
        validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw readiness composes sealed output binding identity");

    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R134 bound draw pipeline rebind prerequisite");
    const auto drawPipelineBindingReady =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        drawPipelineBindingReady.inputValid &&
        drawPipelineBindingReady.bundleReady &&
        drawPipelineBindingReady.contextMatches &&
        drawPipelineBindingReady.translationSnapshotValid &&
        drawPipelineBindingReady.geometryShaderClear &&
        drawPipelineBindingReady.hullShaderClear &&
        drawPipelineBindingReady.domainShaderClear &&
        drawPipelineBindingReady.graphicsStageIsolationReady &&
        drawPipelineBindingReady.streamOutputTargetsClear &&
        drawPipelineBindingReady.predicationClear &&
        drawPipelineBindingReady.drawSideEffectIsolationReady &&
        drawPipelineBindingReady.boundExact &&
        drawPipelineBindingReady.ready &&
        drawPipelineBindingReady.pipelineSnapshotToken ==
            pipelineIdentityReady.snapshotToken &&
        drawPipelineBindingReady.snapshotToken != 0 &&
        pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R134 exact IA VS PS binding issues a live snapshot");

    d3d.context->GSSetShader(isolationGeometryShader, nullptr, 0);
    const auto graphicsStageIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        graphicsStageIsolationDrift.inputValid &&
        graphicsStageIsolationDrift.bundleReady &&
        graphicsStageIsolationDrift.contextMatches &&
        graphicsStageIsolationDrift.translationSnapshotValid &&
        !graphicsStageIsolationDrift.geometryShaderClear &&
        graphicsStageIsolationDrift.hullShaderClear &&
        graphicsStageIsolationDrift.domainShaderClear &&
        !graphicsStageIsolationDrift.graphicsStageIsolationReady &&
        !graphicsStageIsolationDrift.boundExact &&
        !graphicsStageIsolationDrift.ready &&
        graphicsStageIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R147 live GS drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R147 restore fixed-function graphics stage isolation");
    const auto graphicsStageIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        graphicsStageIsolationRestored.ready &&
        graphicsStageIsolationRestored.graphicsStageIsolationReady &&
        graphicsStageIsolationRestored.streamOutputTargetsClear &&
        graphicsStageIsolationRestored.predicationClear &&
        graphicsStageIsolationRestored.drawSideEffectIsolationReady &&
        graphicsStageIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R147 restored graphics stage isolation reproduces pipeline snapshot");

    UINT isolationStreamOutputOffset = 0;
    d3d.context->SOSetTargets(
        1, &isolationStreamOutputBuffer, &isolationStreamOutputOffset);
    const auto streamOutputIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        streamOutputIsolationDrift.inputValid &&
        streamOutputIsolationDrift.graphicsStageIsolationReady &&
        !streamOutputIsolationDrift.streamOutputTargetsClear &&
        streamOutputIsolationDrift.predicationClear &&
        !streamOutputIsolationDrift.drawSideEffectIsolationReady &&
        !streamOutputIsolationDrift.boundExact &&
        !streamOutputIsolationDrift.ready &&
        streamOutputIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R148 live SO target drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R148 restore fixed-function stream-output isolation");
    const auto streamOutputIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        streamOutputIsolationRestored.ready &&
        streamOutputIsolationRestored.streamOutputTargetsClear &&
        streamOutputIsolationRestored.predicationClear &&
        streamOutputIsolationRestored.drawSideEffectIsolationReady &&
        streamOutputIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R148 restored SO isolation reproduces pipeline snapshot");

    d3d.context->SetPredication(isolationPredicate, TRUE);
    const auto predicationIsolationDrift =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        predicationIsolationDrift.inputValid &&
        predicationIsolationDrift.graphicsStageIsolationReady &&
        predicationIsolationDrift.streamOutputTargetsClear &&
        !predicationIsolationDrift.predicationClear &&
        !predicationIsolationDrift.drawSideEffectIsolationReady &&
        !predicationIsolationDrift.boundExact &&
        !predicationIsolationDrift.ready &&
        predicationIsolationDrift.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R148 live predication drift invalidates fixed-function pipeline binding");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R148 restore fixed-function draw-predication isolation");
    const auto predicationIsolationRestored =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        predicationIsolationRestored.ready &&
        predicationIsolationRestored.streamOutputTargetsClear &&
        predicationIsolationRestored.predicationClear &&
        predicationIsolationRestored.drawSideEffectIsolationReady &&
        predicationIsolationRestored.snapshotToken ==
            drawPipelineBindingReady.snapshotToken,
        "R148 restored predication isolation reproduces pipeline snapshot");

    const auto texturedDrawReady =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        texturedDrawReady.inputValid &&
        texturedDrawReady.drawReady &&
        texturedDrawReady.textureStageReady &&
        texturedDrawReady.textureMaskMatches &&
        texturedDrawReady.componentSnapshotsPresent &&
        texturedDrawReady.ready &&
        texturedDrawReady.requiredTextureMask == 0x1u &&
        texturedDrawReady.observedTextureMask == 0x1u &&
        texturedDrawReady.drawSnapshotToken == drawReady.snapshotToken &&
        texturedDrawReady.textureStageSnapshotToken ==
            drawTextureStageReady.snapshotToken &&
        texturedDrawReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_textured_draw_snapshot(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            texturedDrawReady.snapshotToken),
        "R133 textured draw readiness composes the exact required PS stage");

    auto multiStageTextureReady = texturedStageReady;
    multiStageTextureReady.requiredMask = 0x3u;
    multiStageTextureReady.readyMask = 0x3u;
    multiStageTextureReady.pendingMask = 0;
    multiStageTextureReady.snapshotToken = 0x136003ull;
    const auto multiStageActivation =
        compose_fixed_function_activation_readiness(
            pipelineIdentityReady, multiStageTextureReady);
    require(
        multiStageActivation.ready &&
        multiStageActivation.requiredTextureMask == 0x3u &&
        multiStageActivation.snapshotToken != 0,
        "R136 two-stage activation prerequisite");

    const auto multiStageDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        multiStageDrawReady.ready &&
        multiStageDrawReady.requiredTextureMask == 0x3u &&
        validate_fixed_function_draw_readiness_integrity(
            multiStageDrawReady),
        "R136 two-stage sealed draw prerequisite");

    constexpr UINT secondDrawTextureStageSlot = 1;
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView),
        "R136 second texture-stage live binding prerequisite");

    std::array<
        const outrun::vr::dx11::NativeFixedFunctionSamplerState*, 8>
        multiStageSamplers{};
    std::array<
        const outrun::vr::dx11::NativeFixedFunctionTextureView*, 8>
        multiStageTextures{};
    multiStageSamplers[0] = &samplerOwner;
    multiStageSamplers[1] = &samplerOwner;
    multiStageTextures[0] = &textureView;
    multiStageTextures[1] = &textureView;

    const auto multiStageBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures);
    require(
        multiStageBindingSet.inputValid &&
        multiStageBindingSet.requiredMaskValid &&
        multiStageBindingSet.allRequiredBoundExact &&
        multiStageBindingSet.ready &&
        multiStageBindingSet.requiredTextureMask == 0x3u &&
        multiStageBindingSet.observedTextureMask == 0x3u &&
        multiStageBindingSet.stageSnapshotTokens[0] != 0 &&
        multiStageBindingSet.stageSnapshotTokens[1] != 0 &&
        multiStageBindingSet.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                multiStageBindingSet) &&
        outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate two-stage PS binding captures exact live identity");

    const auto multiStageTexturedDraw =
        outrun::vr::dx11::
            compose_fixed_function_multistage_textured_draw_readiness(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures);
    require(
        multiStageTexturedDraw.inputValid &&
        multiStageTexturedDraw.drawReady &&
        multiStageTexturedDraw.textureStageReady &&
        multiStageTexturedDraw.textureMaskMatches &&
        multiStageTexturedDraw.componentSnapshotsPresent &&
        multiStageTexturedDraw.ready &&
        multiStageTexturedDraw.requiredTextureMask == 0x3u &&
        multiStageTexturedDraw.observedTextureMask == 0x3u &&
        multiStageTexturedDraw.drawSnapshotToken ==
            multiStageDrawReady.snapshotToken &&
        multiStageTexturedDraw.textureStageSnapshotToken ==
            multiStageBindingSet.snapshotToken &&
        multiStageTexturedDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_multistage_textured_draw_snapshot(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures,
                multiStageTexturedDraw.snapshotToken),
        "R136 aggregate two-stage PS binding composes exact draw readiness");

    const auto multiStageBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            multiStageDrawReady, multiStageTexturedDraw,
            drawPipelineBindingReady, d3d.context, outputStateBinding);
    require(
        multiStageBoundDraw.ready &&
        multiStageBoundDraw.pipelineBindingMatchesDraw &&
        multiStageBoundDraw.snapshotToken != 0,
        "R136 aggregate textured draw remains compatible with R134 pipeline identity");

    auto forgedMultiStageBindingSet = multiStageBindingSet;
    forgedMultiStageBindingSet.stageSnapshotTokens[1] ^=
        0x9e3779b97f4a7c15ull;
    require(
        !outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                forgedMultiStageBindingSet),
        "R136 aggregate binding snapshot rejects copied stage-token drift");

    auto injectedUnusedStageBindingSet = multiStageBindingSet;
    injectedUnusedStageBindingSet.stageSnapshotTokens[2] =
        multiStageBindingSet.stageSnapshotTokens[0];
    require(
        !outrun::vr::dx11::
            validate_fixed_function_texture_binding_set_readiness_integrity(
                injectedUnusedStageBindingSet),
        "R136 aggregate binding snapshot rejects unrequired stage-token injection");

    ID3D11SamplerState* clearSecondStageSampler = nullptr;
    ID3D11ShaderResourceView* clearSecondStageSrv = nullptr;
    d3d.context->PSSetSamplers(
        secondDrawTextureStageSlot, 1, &clearSecondStageSampler);
    d3d.context->PSSetShaderResources(
        secondDrawTextureStageSlot, 1, &clearSecondStageSrv);
    const auto missingSecondStageBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures);
    require(
        missingSecondStageBindingSet.inputValid &&
        missingSecondStageBindingSet.requiredMaskValid &&
        !missingSecondStageBindingSet.allRequiredBoundExact &&
        !missingSecondStageBindingSet.ready &&
        missingSecondStageBindingSet.observedTextureMask == 0x1u &&
        missingSecondStageBindingSet.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate binding fails closed after one required PS stage drifts");

    const auto staleLiveMultiStageDraw =
        outrun::vr::dx11::
            compose_fixed_function_multistage_textured_draw_readiness(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures);
    require(
        !staleLiveMultiStageDraw.textureStageReady &&
        !staleLiveMultiStageDraw.ready &&
        staleLiveMultiStageDraw.observedTextureMask == 0x1u &&
        staleLiveMultiStageDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_multistage_textured_draw_snapshot(
                multiStageDrawReady, d3d.context,
                multiStageSamplers, multiStageTextures,
                multiStageTexturedDraw.snapshotToken),
        "R136 multistage draw reobserves live PS binding drift");

    const auto unsupportedStageMaskBindingSet =
        outrun::vr::dx11::observe_fixed_function_texture_binding_set(
            d3d.context, 0x101u, multiStageSamplers, multiStageTextures);
    require(
        !unsupportedStageMaskBindingSet.requiredMaskValid &&
        !unsupportedStageMaskBindingSet.inputValid &&
        !unsupportedStageMaskBindingSet.ready &&
        unsupportedStageMaskBindingSet.snapshotToken == 0,
        "R136 aggregate binding rejects stages outside fixed-function 0-7");

    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView) &&
        outrun::vr::dx11::validate_fixed_function_texture_binding_set_snapshot(
            d3d.context, multiStageDrawReady.requiredTextureMask,
            multiStageSamplers, multiStageTextures,
            multiStageBindingSet.snapshotToken),
        "R136 aggregate live binding restores deterministic snapshot identity");

    const auto boundDrawReady =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        boundDrawReady.inputValid &&
        boundDrawReady.texturedDrawReady &&
        boundDrawReady.pipelineBindingReady &&
        boundDrawReady.pipelineBindingMatchesDraw &&
        boundDrawReady.outputBindingReady &&
        boundDrawReady.outputBindingMatchesDraw &&
        boundDrawReady.componentSnapshotsPresent &&
        boundDrawReady.ready &&
        boundDrawReady.texturedDrawSnapshotToken ==
            texturedDrawReady.snapshotToken &&
        boundDrawReady.pipelineBindingSnapshotToken ==
            drawPipelineBindingReady.snapshotToken &&
        boundDrawReady.outputBindingSnapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        boundDrawReady.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R138 bound draw reobserves exact live RS OM binding");

    d3d.context->RSSetState(nullptr);
    const auto staleOutputBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        staleOutputBoundDraw.pipelineBindingReady &&
        staleOutputBoundDraw.pipelineBindingMatchesDraw &&
        !staleOutputBoundDraw.outputBindingReady &&
        staleOutputBoundDraw.outputBindingMatchesDraw &&
        !staleOutputBoundDraw.componentSnapshotsPresent &&
        !staleOutputBoundDraw.ready &&
        staleOutputBoundDraw.outputBindingSnapshotToken == 0 &&
        staleOutputBoundDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R138 bound draw fails closed after live RS drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R138 restore output binding after final draw drift probe");
    const auto restoredOutputBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        restoredOutputBoundDraw.ready &&
        restoredOutputBoundDraw.outputBindingReady &&
        restoredOutputBoundDraw.outputBindingMatchesDraw &&
        restoredOutputBoundDraw.outputBindingSnapshotToken ==
            liveOutputBindingReady.snapshotToken &&
        restoredOutputBoundDraw.snapshotToken ==
            boundDrawReady.snapshotToken,
        "R138 restored output binding reproduces final bound draw snapshot");


    const auto sameContextBoundDraw =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextBoundDraw.inputValid &&
        sameContextBoundDraw.texturedDrawReady &&
        sameContextBoundDraw.pipelineBindingReady &&
        sameContextBoundDraw.pipelineBindingMatchesDraw &&
        sameContextBoundDraw.outputBindingReady &&
        sameContextBoundDraw.outputBindingMatchesDraw &&
        sameContextBoundDraw.componentSnapshotsPresent &&
        sameContextBoundDraw.ready &&
        sameContextBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_same_context_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            sameContextBoundDraw.snapshotToken),
        "R139 same-context final bound draw reobserves every live binding");

    d3d.context->PSSetShader(nullptr, nullptr, 0);
    const auto sameContextPipelineDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextPipelineDrift.texturedDrawReady &&
        !sameContextPipelineDrift.pipelineBindingReady &&
        sameContextPipelineDrift.outputBindingReady &&
        !sameContextPipelineDrift.ready &&
        sameContextPipelineDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_same_context_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            sameContextBoundDraw.snapshotToken),
        "R139 same-context final bound draw rejects live PS pipeline drift");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R139 restore pipeline after same-context drift probe");

    ID3D11SamplerState* clearSameContextSampler = nullptr;
    ID3D11ShaderResourceView* clearSameContextSrv = nullptr;
    d3d.context->PSSetSamplers(
        secondDrawTextureStageSlot, 1, &clearSameContextSampler);
    d3d.context->PSSetShaderResources(
        secondDrawTextureStageSlot, 1, &clearSameContextSrv);
    const auto sameContextTextureDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        !sameContextTextureDrift.texturedDrawReady &&
        sameContextTextureDrift.pipelineBindingReady &&
        sameContextTextureDrift.outputBindingReady &&
        !sameContextTextureDrift.ready &&
        sameContextTextureDrift.snapshotToken == 0,
        "R139 same-context final bound draw rejects live aggregate PS drift");
    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, secondDrawTextureStageSlot, samplerOwner, textureView),
        "R139 restore aggregate PS stage after same-context drift probe");

    d3d.context->RSSetState(nullptr);
    const auto sameContextOutputDrift =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextOutputDrift.texturedDrawReady &&
        sameContextOutputDrift.pipelineBindingReady &&
        !sameContextOutputDrift.outputBindingReady &&
        !sameContextOutputDrift.ready &&
        sameContextOutputDrift.snapshotToken == 0,
        "R139 same-context final bound draw rejects live RS OM drift");
    require(
        outputStateBinding.apply(d3d.context),
        "R139 restore RS OM after same-context drift probe");

    const auto sameContextRestored =
        outrun::vr::dx11::compose_fixed_function_same_context_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures);
    require(
        sameContextRestored.ready &&
        sameContextRestored.snapshotToken == sameContextBoundDraw.snapshotToken,
        "R139 same-context final bound draw restores deterministic snapshot");

    const auto completeBoundDraw =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeBoundDraw.inputValid &&
        completeBoundDraw.sameContextBoundDrawReady &&
        completeBoundDraw.geometryBindingReady &&
        completeBoundDraw.geometryBindingMatchesDraw &&
        completeBoundDraw.componentSnapshotsPresent &&
        completeBoundDraw.ready &&
        completeBoundDraw.sameContextBoundDrawSnapshotToken ==
            sameContextBoundDraw.snapshotToken &&
        completeBoundDraw.geometryBindingSnapshotToken ==
            indexedGeometryBinding.snapshotToken &&
        completeBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw includes exact live IA geometry");

    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto completeGeometryDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeGeometryDrift.sameContextBoundDrawReady &&
        !completeGeometryDrift.geometryBindingReady &&
        completeGeometryDrift.geometryBindingMatchesDraw &&
        !completeGeometryDrift.componentSnapshotsPresent &&
        !completeGeometryDrift.ready &&
        completeGeometryDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 final gate fails closed after live IA topology drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R140 restore IA geometry after final gate drift probe");
    const auto completeBoundDrawRestored =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures,
            indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeBoundDrawRestored.ready &&
        completeBoundDrawRestored.geometryBindingReady &&
        completeBoundDrawRestored.geometryBindingMatchesDraw &&
        completeBoundDrawRestored.snapshotToken == completeBoundDraw.snapshotToken,
        "R140 restored IA geometry reproduces complete bound draw snapshot");

    ID3D11Buffer* strideDriftVertex =
        managedVertexBuffer.mirror_buffer();
    const UINT strideDriftValue = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &strideDriftVertex, &strideDriftValue, &geometryVertexOffset);
    const auto completeStrideDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeStrideDrift.sameContextBoundDrawReady &&
        !completeStrideDrift.geometryBindingReady &&
        completeStrideDrift.geometryBindingMatchesDraw &&
        !completeStrideDrift.componentSnapshotsPresent &&
        !completeStrideDrift.ready &&
        completeStrideDrift.geometryBindingSnapshotToken == 0 &&
        completeStrideDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw rejects live IA vertex stride drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R140 restore IA after vertex stride drift");

    d3d.context->IASetIndexBuffer(
        managedIndexBuffer.mirror_buffer(), DXGI_FORMAT_R16_UINT,
        geometryIndexOffset + 2u);
    const auto completeIndexOffsetDrift =
        outrun::vr::dx11::compose_fixed_function_complete_bound_draw_readiness(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset);
    require(
        completeIndexOffsetDrift.sameContextBoundDrawReady &&
        !completeIndexOffsetDrift.geometryBindingReady &&
        completeIndexOffsetDrift.geometryBindingMatchesDraw &&
        !completeIndexOffsetDrift.componentSnapshotsPresent &&
        !completeIndexOffsetDrift.ready &&
        completeIndexOffsetDrift.geometryBindingSnapshotToken == 0 &&
        completeIndexOffsetDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw rejects live IA index offset drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
        outrun::vr::dx11::validate_fixed_function_complete_bound_draw_snapshot(
            multiStageDrawReady, d3d.context, outputStateBinding,
            pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
            multiStageSamplers, multiStageTextures, indexedGeometryReady,
            managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
            completeBoundDraw.snapshotToken),
        "R140 complete bound draw restores exact IA binding parameters");


    {
        const auto fullyBoundDraw =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            fullyBoundDraw.inputValid &&
            fullyBoundDraw.completeBoundDrawReady &&
            fullyBoundDraw.transformBindingReady &&
            fullyBoundDraw.componentSnapshotsPresent &&
            fullyBoundDraw.ready &&
            fullyBoundDraw.transformBindingSnapshotToken ==
                pipelineTransformBindingReady.snapshotToken &&
            fullyBoundDraw.transformPayloadHash == transform.payloadHash &&
            fullyBoundDraw.snapshotToken != 0 &&
            outrun::vr::dx11::validate_fixed_function_fully_bound_draw_snapshot(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform, fullyBoundDraw.snapshotToken),
            "final fully bound draw includes exact live VS b0 transform");

        ID3D11Buffer* nullFinalTransformBuffer = nullptr;
        d3d.context->VSSetConstantBuffers(0, 1, &nullFinalTransformBuffer);
        const auto missingTransformBinding =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            missingTransformBinding.completeBoundDrawReady &&
            !missingTransformBinding.transformBindingReady &&
            !missingTransformBinding.ready &&
            missingTransformBinding.snapshotToken == 0 &&
            !outrun::vr::dx11::validate_fixed_function_fully_bound_draw_snapshot(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform, fullyBoundDraw.snapshotToken),
            "final fully bound draw fails closed after VS b0 drift");

        ID3D11Buffer* restoredFinalTransformBuffer =
            pipelineBundle.transform_buffer().buffer();
        d3d.context->VSSetConstantBuffers(0, 1, &restoredFinalTransformBuffer);
        const auto fullyBoundDrawRestored =
            outrun::vr::dx11::compose_fixed_function_fully_bound_draw_readiness(
                multiStageDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset,
                transform);
        require(
            fullyBoundDrawRestored.ready &&
            fullyBoundDrawRestored.snapshotToken == fullyBoundDraw.snapshotToken,
            "final VS b0 restore reproduces fully bound draw snapshot");

        auto transformPayloadDrift = transform;
        transformPayloadDrift.worldViewProjection[0] += 1.0f;
        const auto copiedPayloadDrift =
            pipelineBundle.transform_buffer().binding_readiness(
                d3d.context, transformPayloadDrift);
        require(
            !copiedPayloadDrift.inputValid &&
            !copiedPayloadDrift.payloadMatches &&
            !copiedPayloadDrift.ready &&
            copiedPayloadDrift.snapshotToken == 0,
            "final VS b0 copied WVP payload drift fails closed");

        const auto renderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            renderTargetBoundDraw.inputValid &&
            renderTargetBoundDraw.fullyBoundDrawReady &&
            renderTargetBoundDraw.surfaceTargetBindingReady &&
            renderTargetBoundDraw.surfacePairMatchesDraw &&
            renderTargetBoundDraw.geometryRangeMetadataExact &&
            renderTargetBoundDraw.vertexStrideMatchesInputLayout &&
            renderTargetBoundDraw.vertexStride == geometryVertexStride &&
            renderTargetBoundDraw.inputLayoutStream0Stride ==
                inputLayout.stream0Stride &&
            renderTargetBoundDraw.vertexOffset == geometryVertexOffset &&
            renderTargetBoundDraw.vertexBufferByteWidth == managedVertexBytes.size() &&
            renderTargetBoundDraw.indexFormat == DXGI_FORMAT_R16_UINT &&
            renderTargetBoundDraw.indexOffset == geometryIndexOffset &&
            renderTargetBoundDraw.indexBufferByteWidth == sizeof(managedIndexBytes) &&
            renderTargetBoundDraw.componentSnapshotsPresent &&
            renderTargetBoundDraw.ready &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_readiness_integrity(
                    renderTargetBoundDraw) &&
            renderTargetBoundDraw.surfaceTargetBindingSnapshotToken ==
                surfaceTargetBindingReady.snapshotToken &&
            renderTargetBoundDraw.surfacePairSnapshotToken ==
                surfacePairReady.snapshotToken &&
            renderTargetBoundDraw.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 final draw seals exact live OM RTV DSV identity");

        constexpr UINT mismatchedLayoutStride = 16u;
        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                mismatchedLayoutStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
            "R158 mismatched IA stride binding prerequisite");
        const auto layoutStrideMismatch =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    mismatchedLayoutStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            layoutStrideMismatch.inputValid &&
            layoutStrideMismatch.fullyBoundDrawReady &&
            layoutStrideMismatch.surfaceTargetBindingReady &&
            layoutStrideMismatch.geometryRangeMetadataExact &&
            !layoutStrideMismatch.vertexStrideMatchesInputLayout &&
            layoutStrideMismatch.vertexStride == mismatchedLayoutStride &&
            layoutStrideMismatch.inputLayoutStream0Stride ==
                inputLayout.stream0Stride &&
            !layoutStrideMismatch.ready &&
            layoutStrideMismatch.snapshotToken == 0,
            "R158 final draw rejects live IA stride drift from translated layout");
        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset) &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R158 exact IA stride restore keeps final draw snapshot deterministic");

        d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
        const auto missingRenderTargets =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface);
        require(
            missingRenderTargets.fullyBoundDrawReady &&
            !missingRenderTargets.surfaceTargetBindingReady &&
            missingRenderTargets.surfacePairMatchesDraw &&
            !missingRenderTargets.ready &&
            missingRenderTargets.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 final draw fails closed after live OM target unbind");

        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            outrun::vr::dx11::
                validate_fixed_function_render_target_bound_draw_snapshot(
                    multiStageDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    indexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    &managedIndexBuffer, DXGI_FORMAT_R16_UINT,
                    geometryIndexOffset, transform, surfaceTargetBinding,
                    outputColorSurface, outputDepthSurface,
                    renderTargetBoundDraw.snapshotToken),
            "R145 live OM target restore reproduces final draw snapshot");

        const auto indexedDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 0u, 0);
        require(
            indexedDirectDispatch.inputValid &&
            indexedDirectDispatch.renderTargetBoundDrawReady &&
            indexedDirectDispatch.geometryReady &&
            indexedDirectDispatch.geometryMatchesDraw &&
            indexedDirectDispatch.surfacePairMatchesDraw &&
            indexedDirectDispatch.topologyMatchesGeometry &&
            indexedDirectDispatch.bufferRangeExact &&
            indexedDirectDispatch.dispatchArgumentsExact &&
            indexedDirectDispatch.componentSnapshotsPresent &&
            indexedDirectDispatch.ready &&
            indexedDirectDispatch.indexed &&
            indexedDirectDispatch.elementCount == 6u &&
            indexedDirectDispatch.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 0u, 0, indexedDirectDispatch.snapshotToken),
            "R147 direct indexed dispatch seals DrawIndexed arguments");

        const auto indexedSourceRange =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 0u);
        require(
            indexedSourceRange.inputValid &&
            indexedSourceRange.primitiveExact &&
            indexedSourceRange.vertexRangeExact &&
            indexedSourceRange.indexRangeExact &&
            indexedSourceRange.ready &&
            indexedSourceRange.topology ==
                D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST &&
            indexedSourceRange.primitiveCount == 2u &&
            indexedSourceRange.elementCount == 6u &&
            indexedSourceRange.baseVertexIndex == 0 &&
            indexedSourceRange.minVertexIndex == 0u &&
            indexedSourceRange.numVertices == 4u &&
            indexedSourceRange.maxVertexIndex == 3u &&
            indexedSourceRange.startIndex == 0u &&
            indexedSourceRange.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_range_snapshot(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 0u,
                    indexedSourceRange.snapshotToken),
            "R149 indexed source range seals D3D9 DrawIndexedPrimitive arguments");

        const auto indexedSourceRangeMissingVertices =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 0u, 0u);
        require(
            indexedSourceRangeMissingVertices.inputValid &&
            indexedSourceRangeMissingVertices.primitiveExact &&
            !indexedSourceRangeMissingVertices.vertexRangeExact &&
            indexedSourceRangeMissingVertices.indexRangeExact &&
            !indexedSourceRangeMissingVertices.ready &&
            indexedSourceRangeMissingVertices.snapshotToken == 0,
            "R149 indexed source range rejects empty vertex range for live primitives");

        const auto indexedSourceRangeVertexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, 0,
                    (std::numeric_limits<UINT>::max)(), 2u, 0u);
        require(
            indexedSourceRangeVertexOverflow.inputValid &&
            !indexedSourceRangeVertexOverflow.vertexRangeExact &&
            indexedSourceRangeVertexOverflow.indexRangeExact &&
            !indexedSourceRangeVertexOverflow.ready &&
            indexedSourceRangeVertexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects MinVertexIndex NumVertices overflow");

        const auto indexedSourceRangeNegativeEffectiveVertex =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, -2, 1u, 3u, 0u);
        require(
            indexedSourceRangeNegativeEffectiveVertex.inputValid &&
            !indexedSourceRangeNegativeEffectiveVertex.vertexRangeExact &&
            indexedSourceRangeNegativeEffectiveVertex.indexRangeExact &&
            !indexedSourceRangeNegativeEffectiveVertex.ready &&
            indexedSourceRangeNegativeEffectiveVertex.snapshotToken == 0,
            "R149 indexed source range rejects negative effective BaseVertexIndex range");

        const auto indexedSourceRangeEffectiveVertexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, 1,
                    (std::numeric_limits<UINT>::max)(), 1u, 0u);
        require(
            indexedSourceRangeEffectiveVertexOverflow.inputValid &&
            !indexedSourceRangeEffectiveVertexOverflow.vertexRangeExact &&
            indexedSourceRangeEffectiveVertexOverflow.indexRangeExact &&
            !indexedSourceRangeEffectiveVertexOverflow.ready &&
            indexedSourceRangeEffectiveVertexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects effective BaseVertexIndex maximum overflow");

        const auto indexedSourceRangeNegativeBaseValid =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 1u, -2, 2u, 3u, 0u);
        require(
            indexedSourceRangeNegativeBaseValid.vertexRangeExact &&
            indexedSourceRangeNegativeBaseValid.ready &&
            indexedSourceRangeNegativeBaseValid.snapshotToken != 0,
            "R149 indexed source range accepts bounded negative BaseVertexIndex");

        const auto indexedSourceRangeIndexOverflow =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u,
                    (std::numeric_limits<UINT>::max)() - 5u);
        require(
            indexedSourceRangeIndexOverflow.inputValid &&
            indexedSourceRangeIndexOverflow.vertexRangeExact &&
            !indexedSourceRangeIndexOverflow.indexRangeExact &&
            !indexedSourceRangeIndexOverflow.ready &&
            indexedSourceRangeIndexOverflow.snapshotToken == 0,
            "R149 indexed source range rejects StartIndex element-count overflow");

        const auto indexedSourceRangeFan =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLEFAN, 2u, 0, 0u, 4u, 0u);
        require(
            !indexedSourceRangeFan.inputValid &&
            !indexedSourceRangeFan.primitiveExact &&
            !indexedSourceRangeFan.ready &&
            indexedSourceRangeFan.snapshotToken == 0,
            "R149 indexed source range keeps triangle fan on generated-index path");

        const auto indexedSourceRangePointList =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_POINTLIST, 1u, 0, 0u, 1u, 0u);
        require(
            !indexedSourceRangePointList.inputValid &&
            !indexedSourceRangePointList.primitiveExact &&
            indexedSourceRangePointList.vertexRangeExact &&
            indexedSourceRangePointList.indexRangeExact &&
            !indexedSourceRangePointList.ready &&
            indexedSourceRangePointList.snapshotToken == 0,
            "R149 indexed source range rejects D3D9 DIP point list");

        require(
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_range_snapshot(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 3u, 0u,
                    indexedSourceRange.snapshotToken),
            "R149 indexed source range snapshot rejects NumVertices drift");

        const auto indexedDirectLineage =
            outrun::vr::dx11::
                compose_fixed_function_indexed_direct_dispatch_readiness(
                    indexedDirectDispatch, indexedSourceRange,
                    renderTargetBoundDraw);
        require(
            indexedDirectLineage.inputValid &&
            indexedDirectLineage.directDispatchReady &&
            indexedDirectLineage.sourceRangeReady &&
            indexedDirectLineage.boundDrawReady &&
            indexedDirectLineage.dispatchMatchesSourceRange &&
            indexedDirectLineage.boundDrawMatchesDispatch &&
            indexedDirectLineage.vertexBufferRangeExact &&
            indexedDirectLineage.componentSnapshotsPresent &&
            indexedDirectLineage.ready &&
            indexedDirectLineage.directDispatchSnapshotToken ==
                indexedDirectDispatch.snapshotToken &&
            indexedDirectLineage.sourceRangeSnapshotToken ==
                indexedSourceRange.snapshotToken &&
            indexedDirectLineage.boundDrawSnapshotToken ==
                renderTargetBoundDraw.snapshotToken &&
            indexedDirectLineage.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_direct_dispatch_snapshot(
                    indexedDirectDispatch, indexedSourceRange,
                    renderTargetBoundDraw, indexedDirectLineage.snapshotToken),
            "R150 indexed direct dispatch binds R147 tuple to R149 source range");

        const auto indexedSourceRangeStartDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_range_readiness(
                    D3DPT_TRIANGLELIST, 2u, 0, 0u, 4u, 1u);
        const auto indexedDirectLineageDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_direct_dispatch_readiness(
                    indexedDirectDispatch, indexedSourceRangeStartDrift,
                    renderTargetBoundDraw);
        require(
            indexedSourceRangeStartDrift.ready &&
            indexedDirectLineageDrift.inputValid &&
            indexedDirectLineageDrift.directDispatchReady &&
            indexedDirectLineageDrift.sourceRangeReady &&
            !indexedDirectLineageDrift.dispatchMatchesSourceRange &&
            !indexedDirectLineageDrift.ready &&
            indexedDirectLineageDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_direct_dispatch_snapshot(
                    indexedDirectDispatch, indexedSourceRangeStartDrift,
                    renderTargetBoundDraw, indexedDirectLineage.snapshotToken),
            "R150 indexed direct dispatch rejects R149 StartIndex lineage drift");

        const auto indexedSourceRangeBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_indexed_source_range_readiness(
                D3DPT_TRIANGLELIST, 2u, 0, 14u, 3u, 0u);
        const auto indexedVertexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_indexed_direct_dispatch_readiness(
                indexedDirectDispatch, indexedSourceRangeBufferOverrun,
                renderTargetBoundDraw);
        require(
            indexedSourceRangeBufferOverrun.ready &&
            indexedVertexBufferOverrun.inputValid &&
            indexedVertexBufferOverrun.dispatchMatchesSourceRange &&
            indexedVertexBufferOverrun.boundDrawMatchesDispatch &&
            !indexedVertexBufferOverrun.vertexBufferRangeExact &&
            !indexedVertexBufferOverrun.ready &&
            indexedVertexBufferOverrun.snapshotToken == 0,
            "R151 indexed direct lineage rejects declared vertex buffer overrun");

        const auto indexedIndexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                renderTargetBoundDraw, multiStageDrawReady,
                indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                0u, 1u, 0);
        require(
            indexedIndexBufferOverrun.inputValid &&
            !indexedIndexBufferOverrun.bufferRangeExact &&
            !indexedIndexBufferOverrun.dispatchArgumentsExact &&
            !indexedIndexBufferOverrun.ready &&
            indexedIndexBufferOverrun.snapshotToken == 0,
            "R151 direct indexed dispatch rejects index buffer overrun");

        const auto indexedSourceValues =
            managedIndexBuffer.index_range_readiness(
                managedIndexReady, D3DFMT_INDEX16,
                indexedSourceRange.startIndex,
                indexedSourceRange.elementCount,
                indexedSourceRange.minVertexIndex,
                indexedSourceRange.maxVertexIndex);
        require(
            indexedSourceValues.inputValid &&
            indexedSourceValues.shadowValid &&
            indexedSourceValues.indexFormatExact &&
            indexedSourceValues.mirrorSnapshotExact &&
            indexedSourceValues.byteRangeExact &&
            indexedSourceValues.valuesWithinDeclaredRange &&
            indexedSourceValues.ready &&
            indexedSourceValues.startIndex == 0u &&
            indexedSourceValues.indexCount == 6u &&
            indexedSourceValues.observedMinIndex == 0u &&
            indexedSourceValues.observedMaxIndex == 3u &&
            indexedSourceValues.mirrorSnapshotToken ==
                managedIndexReady.snapshotToken &&
            indexedSourceValues.contentHash != 0 &&
            indexedSourceValues.snapshotToken != 0 &&
            managedIndexBuffer.validate_index_range_readiness_snapshot(
                managedIndexReady, D3DFMT_INDEX16, 0u, 6u, 0u, 3u,
                indexedSourceValues.snapshotToken),
            "R152 indexed source values scan exact managed IB range");

        const auto indexedSourceValueLineage =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues);
        require(
            indexedSourceValueLineage.inputValid &&
            indexedSourceValueLineage.directDispatchReady &&
            indexedSourceValueLineage.indexedLineageReady &&
            indexedSourceValueLineage.sourceRangeReady &&
            indexedSourceValueLineage.geometryReady &&
            indexedSourceValueLineage.sourceValuesReady &&
            indexedSourceValueLineage.dispatchMatchesLineage &&
            indexedSourceValueLineage.geometryMatchesSourceValues &&
            indexedSourceValueLineage.sourceValuesMatchRange &&
            indexedSourceValueLineage.componentSnapshotsPresent &&
            indexedSourceValueLineage.ready &&
            indexedSourceValueLineage.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_value_snapshot(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues,
                    indexedSourceValueLineage.snapshotToken),
            "R152 indexed source values bind exact IB contents to R150 lineage");

        const auto indexedSourceBinding =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    renderTargetBoundDraw);
        require(
            indexedSourceBinding.inputValid &&
            indexedSourceBinding.sourceValueLineageReady &&
            indexedSourceBinding.boundDrawReady &&
            indexedSourceBinding.boundDrawMatchesLineage &&
            indexedSourceBinding.indexFormatMatchesSourceValues &&
            indexedSourceBinding.indexOffsetExact &&
            indexedSourceBinding.componentSnapshotsPresent &&
            indexedSourceBinding.ready &&
            indexedSourceBinding.sourceIndexFormat == D3DFMT_INDEX16 &&
            indexedSourceBinding.boundIndexFormat == DXGI_FORMAT_R16_UINT &&
            indexedSourceBinding.boundIndexOffset == 0u &&
            indexedSourceBinding.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_binding_snapshot(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    renderTargetBoundDraw, indexedSourceBinding.snapshotToken),
            "R153 indexed source binding seals live IA format and offset");

        auto indexedSourceValuesFormatDrift = indexedSourceValues;
        indexedSourceValuesFormatDrift.sourceIndexFormat = D3DFMT_INDEX32;
        const auto indexedSourceValueLineageFormatDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValuesFormatDrift);
        const auto indexedSourceBindingFormatDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineageFormatDrift,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValuesFormatDrift, renderTargetBoundDraw);
        require(
            indexedSourceValueLineageFormatDrift.ready &&
            indexedSourceBindingFormatDrift.inputValid &&
            indexedSourceBindingFormatDrift.sourceValueLineageReady &&
            indexedSourceBindingFormatDrift.boundDrawReady &&
            !indexedSourceBindingFormatDrift.indexFormatMatchesSourceValues &&
            indexedSourceBindingFormatDrift.indexOffsetExact &&
            !indexedSourceBindingFormatDrift.ready &&
            indexedSourceBindingFormatDrift.snapshotToken == 0,
            "R153 indexed source binding rejects source format drift");

        auto indexedBoundDrawOffsetDrift = renderTargetBoundDraw;
        indexedBoundDrawOffsetDrift.indexOffset = 2u;
        const auto indexedSourceBindingOffsetDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_binding_readiness(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    indexedBoundDrawOffsetDrift);
        require(
            indexedSourceBindingOffsetDrift.inputValid &&
            indexedSourceBindingOffsetDrift.sourceValueLineageReady &&
            !indexedSourceBindingOffsetDrift.boundDrawReady &&
            indexedSourceBindingOffsetDrift.boundDrawMatchesLineage &&
            indexedSourceBindingOffsetDrift.indexFormatMatchesSourceValues &&
            !indexedSourceBindingOffsetDrift.indexOffsetExact &&
            !indexedSourceBindingOffsetDrift.ready &&
            indexedSourceBindingOffsetDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_binding_snapshot(
                    indexedSourceValueLineage, indexedDirectDispatch,
                    indexedDirectLineage, indexedSourceRange,
                    indexedGeometryReady, indexedSourceValues,
                    indexedBoundDrawOffsetDrift,
                    indexedSourceBinding.snapshotToken),
            "R153 indexed source binding rejects live IA index offset drift");


        const auto indexedSourceLiveBinding =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBinding.inputValid &&
            indexedSourceLiveBinding.sourceBindingReady &&
            indexedSourceLiveBinding.contextMatchesMirror &&
            indexedSourceLiveBinding.indexMirrorCurrent &&
            indexedSourceLiveBinding.liveIndexBufferExact &&
            indexedSourceLiveBinding.liveIndexFormatExact &&
            indexedSourceLiveBinding.liveIndexOffsetExact &&
            indexedSourceLiveBinding.componentSnapshotsPresent &&
            indexedSourceLiveBinding.ready &&
            indexedSourceLiveBinding.observedIndexFormat ==
                DXGI_FORMAT_R16_UINT &&
            indexedSourceLiveBinding.observedIndexOffset == 0u &&
            indexedSourceLiveBinding.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_indexed_source_live_binding_snapshot(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer,
                    indexedSourceLiveBinding.snapshotToken),
            "R153 live source binding reobserves current IA index mirror");

        d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
        const auto indexedSourceLiveBindingDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBindingDrift.inputValid &&
            indexedSourceLiveBindingDrift.sourceBindingReady &&
            indexedSourceLiveBindingDrift.contextMatchesMirror &&
            indexedSourceLiveBindingDrift.indexMirrorCurrent &&
            !indexedSourceLiveBindingDrift.liveIndexBufferExact &&
            !indexedSourceLiveBindingDrift.ready &&
            indexedSourceLiveBindingDrift.snapshotToken == 0 &&
            !outrun::vr::dx11::
                validate_fixed_function_indexed_source_live_binding_snapshot(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer,
                    indexedSourceLiveBinding.snapshotToken),
            "R153 live source binding rejects post-snapshot IA index drift");

        d3d.context->IASetIndexBuffer(
            managedIndexBuffer.mirror_buffer(), DXGI_FORMAT_R16_UINT, 0u);
        const auto indexedSourceLiveBindingRestored =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_live_binding_readiness(
                    indexedSourceBinding, indexedSourceValueLineage,
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, indexedGeometryReady,
                    indexedSourceValues, renderTargetBoundDraw,
                    d3d.context, managedIndexBuffer);
        require(
            indexedSourceLiveBindingRestored.ready &&
            indexedSourceLiveBindingRestored.liveIndexBufferExact &&
            indexedSourceLiveBindingRestored.liveIndexFormatExact &&
            indexedSourceLiveBindingRestored.liveIndexOffsetExact &&
            indexedSourceLiveBindingRestored.snapshotToken ==
                indexedSourceLiveBinding.snapshotToken,
            "R153 live source binding restores deterministic IA identity");


        // R157 offscreen WARP indexed submission: revalidate CPU source-index
        // values and the immediate live IA/OM/VS/PS binding before DrawIndexed.
        auto r157Probe = [&](ID3D11DeviceContext* context,
                             ID3D11RenderTargetView* target,
                             const outrun::vr::dx11::NativeFixedFunctionDirectDrawDispatchReadiness& packet) {
            return outrun::vr::dx11::
                prepare_fixed_function_indexed_direct_draw_probe(
                    context, target, outputDepthSurface.depth_stencil_view(),
                    pipelineBundle.input_layout(), pipelineBundle.vertex_shader(),
                    pipelineBundle.pixel_shader(),
                    outputStateBinding, renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, packet,
                    indexedDirectLineage, indexedSourceRange,
                    indexedSourceValues, indexedSourceValueLineage,
                    indexedSourceBinding, managedVertexBuffer,
                    managedIndexBuffer, D3DPT_TRIANGLELIST, 2u, 0u, 0);
        };
        require(
            !r157Probe(d3d.context, nullptr, indexedDirectDispatch),
            "R157 rejects missing offscreen target");
        ID3D11DeviceContext* r157Deferred = nullptr;
        require(
            SUCCEEDED(d3d.device->CreateDeferredContext(0, &r157Deferred)) &&
            r157Deferred != nullptr,
            "R157 deferred context negative prerequisite");
        require(
            !r157Probe(r157Deferred, outputColorSurface.render_target_view(),
                       indexedDirectDispatch),
            "R157 rejects deferred DrawIndexed recording");
        r157Deferred->Release();
        auto r157Forged = indexedDirectDispatch;
        r157Forged.elementCount += 1u;
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       r157Forged),
            "R157 rejects copied packet with forged index count");
        r157Forged = indexedDirectDispatch;
        r157Forged.startIndexLocation += 1u;
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       r157Forged),
            "R157 rejects stale StartIndexLocation");
        d3d.context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       indexedDirectDispatch),
            "R157 rejects removed IA index owner");
        d3d.context->IASetIndexBuffer(
            managedIndexBuffer.mirror_buffer(), DXGI_FORMAT_R16_UINT, 0u);
        require(
            r157Probe(d3d.context, outputColorSurface.render_target_view(),
                      indexedDirectDispatch),
            "R157 revalidates exact WARP indexed IA/OM/VS/PS and shadow");
        // R161: a valid R157 snapshot cannot survive late IA/VS/PS rebinds.
        d3d.context->IASetInputLayout(nullptr);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                        indexedDirectDispatch),
            "R161 rejects live indexed IA input-layout detach");
        d3d.context->IASetInputLayout(pipelineBundle.input_layout());
        require(vertexShader != pipelineBundle.vertex_shader(),
                "R161 distinct foreign vertex shader fixture");
        d3d.context->VSSetShader(vertexShader, nullptr, 0);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                        indexedDirectDispatch),
            "R161 rejects substituted indexed VS");
        d3d.context->VSSetShader(pipelineBundle.vertex_shader(), nullptr, 0);
        d3d.context->PSSetShader(nullptr, nullptr, 0);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                        indexedDirectDispatch),
            "R161 rejects detached indexed PS");
        d3d.context->PSSetShader(pipelineBundle.pixel_shader(), nullptr, 0);
        require(
            r157Probe(d3d.context, outputColorSurface.render_target_view(),
                      indexedDirectDispatch),
            "R161 exact IA/VS/PS restore permits indexed DrawIndexed probe");
        // R162 negative controls: the sealed packet survives, but live
        // output-state identity must fail closed until restored.
        D3D11_VIEWPORT r162Viewport{};
        UINT r162ViewportCount = 1u;
        d3d.context->RSGetViewports(&r162ViewportCount, &r162Viewport);
        require(r162ViewportCount == 1u,
                "R162 exactly one viewport before indexed GPU probe");
        d3d.context->RSSetViewports(0u, nullptr);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       indexedDirectDispatch),
            "R162 rejects late missing indexed viewport");
        d3d.context->RSSetViewports(1u, &r162Viewport);
        D3D11_RECT r162Scissor{};
        UINT r162ScissorCount = 1u;
        d3d.context->RSGetScissorRects(&r162ScissorCount, &r162Scissor);
        require(r162ScissorCount == 1u &&
                    r162Scissor.right > r162Scissor.left + 1,
                "R162 valid scissor before indexed GPU probe");
        D3D11_RECT r162DriftScissor = r162Scissor;
        --r162DriftScissor.right;
        d3d.context->RSSetScissorRects(1u, &r162DriftScissor);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       indexedDirectDispatch),
            "R162 rejects post-snapshot indexed scissor drift");
        d3d.context->RSSetScissorRects(1u, &r162Scissor);
        require(
            r157Probe(d3d.context, outputColorSurface.render_target_view(),
                      indexedDirectDispatch),
            "R162 restores exact viewport/scissor RS/OM ownership");
        // R163: a foreign GS can change the topology/output despite an
        // unchanged indexed dispatch packet and exact IA/VS/PS/RS/OM owners.
        // Keep the proof restricted to this isolated WARP executable.
        require(isolationGeometryShader != nullptr,
                "R163 distinct geometry shader negative fixture");
        d3d.context->GSSetShader(isolationGeometryShader, nullptr, 0u);
        require(
            !r157Probe(d3d.context, outputColorSurface.render_target_view(),
                       indexedDirectDispatch),
            "R163 rejects late geometry shader injection");
        d3d.context->GSSetShader(nullptr, nullptr, 0u);
        require(
            r157Probe(d3d.context, outputColorSurface.render_target_view(),
                      indexedDirectDispatch),
            "R163 restores fixed-function indexed stage isolation");
        // R164: the same sealed indexed packet must fail closed if the
        // offscreen depth-stencil attachment is detached after R145/R163.
        // Rebind the exact R145 surface pair before allowing the WARP draw.
        ID3D11RenderTargetView* r164Color =
            outputColorSurface.render_target_view();
        require(r164Color != nullptr &&
                    outputDepthSurface.depth_stencil_view() != nullptr,
                "R164 offscreen RTV/DSV pair fixture prerequisite");
        d3d.context->OMSetRenderTargets(1u, &r164Color, nullptr);
        require(
            !r157Probe(d3d.context, r164Color, indexedDirectDispatch),
            "R164 rejects late OM depth-stencil detach");
        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            r157Probe(d3d.context, r164Color, indexedDirectDispatch),
            "R164 exact RTV/DSV restoration permits indexed WARP draw");
        // R165 WARP-only readback: clear a deterministic color outside the
        // translated viewport/scissor, then execute the already-sealed draw.
        // The border pixel proves that the exact offscreen color mirror is
        // copyable and readable after DrawIndexed; the R157 query separately
        // proves two primitives reached IA (not full pixel-shader coverage).
        const FLOAT r165ClearColor[4] = {0.125f, 0.25f, 0.375f, 1.0f};
        d3d.context->ClearRenderTargetView(r164Color, r165ClearColor);
        d3d.context->ClearDepthStencilView(
            outputDepthSurface.depth_stencil_view(),
            D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL, 1.0f, 0);
        ID3D11Query* r157Stats = nullptr;
        D3D11_QUERY_DESC r157StatsDesc{};
        r157StatsDesc.Query = D3D11_QUERY_PIPELINE_STATISTICS;
        require(
            SUCCEEDED(d3d.device->CreateQuery(&r157StatsDesc, &r157Stats)) &&
            r157Stats != nullptr,
            "R157 pipeline statistics query prerequisite");
        d3d.context->Begin(r157Stats);
        // Production game path remains dormant. Only the isolated WARP test
        // is allowed to issue this native DrawIndexed.
        d3d.context->DrawIndexed(
            indexedDirectDispatch.elementCount,
            indexedDirectDispatch.startIndexLocation,
            indexedDirectDispatch.baseVertexLocation);
        d3d.context->End(r157Stats);
        d3d.context->Flush();
        D3D11_QUERY_DATA_PIPELINE_STATISTICS r157Counters{};
        HRESULT r157Result = S_FALSE;
        for (unsigned spin = 0; spin < 2048u; ++spin) {
            r157Result = d3d.context->GetData(
                r157Stats, &r157Counters, sizeof(r157Counters), 0u);
            if (r157Result != S_FALSE)
                break;
        }
        require(
            r157Result == S_OK && r157Counters.IAPrimitives == 2u &&
            r157Counters.IAVertices == 6u,
            "R157 WARP executes two actual indexed triangles (six IA indices)");
        r157Stats->Release();

        ID3D11Texture2D* r165Rejected = nullptr;
        require(
            !outputDepthSurface.copy_color_to_staging(
                d3d.context, &r165Rejected) && r165Rejected == nullptr,
            "R165 rejects depth mirror readback through color-only owner");
        DevicePair r165ForeignDevice = create_warp_device();
        require(
            !outputColorSurface.copy_color_to_staging(
                r165ForeignDevice.context, &r165Rejected) &&
            r165Rejected == nullptr,
            "R165 rejects foreign D3D11 context readback");
        r165ForeignDevice.context->Release();
        r165ForeignDevice.device->Release();
        ID3D11DeviceContext* r165DeferredContext = nullptr;
        require(
            SUCCEEDED(d3d.device->CreateDeferredContext(
                0u, &r165DeferredContext)) && r165DeferredContext != nullptr,
            "R165 deferred readback negative fixture");
        require(
            !outputColorSurface.copy_color_to_staging(
                r165DeferredContext, &r165Rejected) &&
            r165Rejected == nullptr,
            "R165 rejects deferred context staging copy");
        r165DeferredContext->Release();

        // R166 WARP-only provenance regression: BGRA staging must not
        // accept a former color surface after live OM detach or substitution.
        // Restore the R145 target pair without activating gameplay Draw.
        ID3D11Texture2D* r166Rejected = nullptr;
        d3d.context->OMSetRenderTargets(0u, nullptr, nullptr);
        require(
            !outputColorSurface.copy_color_to_staging(
                d3d.context, &r166Rejected) && r166Rejected == nullptr,
            "R166 rejects post-indexed OM color target detach");
        outrun::vr::dx11::NativeSurfaceMirror r166SubstituteColor;
        require(
            r166SubstituteColor.initialize(
                d3d.device, ResourceRole::Color, 64u, 32u,
                D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, D3DUSAGE_RENDERTARGET,
                D3DMULTISAMPLE_NONE, 0u),
            "R166 same-device matching-descriptor substitute prerequisite");
        ID3D11RenderTargetView* r166SubstituteRtv =
            r166SubstituteColor.render_target_view();
        d3d.context->OMSetRenderTargets(
            1u, &r166SubstituteRtv,
            outputDepthSurface.depth_stencil_view());
        require(
            !outputColorSurface.copy_color_to_staging(
                d3d.context, &r166Rejected) && r166Rejected == nullptr,
            "R166 rejects same-device foreign RTV despite identical descriptor");
        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            r157Probe(d3d.context, r164Color, indexedDirectDispatch),
            "R166 restores exact OM RTV/DSV for valid post-draw readback");
        require(
            !r166SubstituteColor.copy_color_to_staging(
                d3d.context, &r166Rejected) && r166Rejected == nullptr,
            "R166 rejects unbound substitute mirror readback");

        // R167 color/depth provenance: preserve the exact R145 pair before
        // staging. A detached or foreign (same-format) depth view is not the
        // actual offscreen indexed draw's depth attachment.
        ID3D11Texture2D* r167Rejected = nullptr;
        d3d.context->OMSetRenderTargets(1u, &r164Color, nullptr);
        require(
            !outputColorSurface.copy_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, &r167Rejected) &&
            r167Rejected == nullptr,
            "R167 rejects detached live OM DSV after indexed WARP draw");
        outrun::vr::dx11::NativeSurfaceMirror r167SubstituteDepth;
        require(
            r167SubstituteDepth.initialize(
                d3d.device, ResourceRole::DepthStencil, 64u, 32u,
                D3DFMT_D24S8, D3DPOOL_DEFAULT, D3DUSAGE_DEPTHSTENCIL,
                D3DMULTISAMPLE_NONE, 0u),
            "R167 same-device identical-descriptor DSV fixture");
        d3d.context->OMSetRenderTargets(
            1u, &r164Color, r167SubstituteDepth.depth_stencil_view());
        require(
            !outputColorSurface.copy_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, &r167Rejected) &&
            r167Rejected == nullptr,
            "R167 rejects substituted DSV despite matching descriptor");
        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            r157Probe(d3d.context, r164Color, indexedDirectDispatch),
            "R167 restores exact live depth attachment without native game Draw");
        require(
            !outputColorSurface.copy_color_depth_pair_to_staging(
                d3d.context, r166SubstituteColor, &r167Rejected) &&
            r167Rejected == nullptr,
            "R167 rejects color-role object as depth mirror");

        // R168: a live slot-0 RTV/DSV is not sufficient if the producer's
        // complete R145 OM binding receipt is missing, forged or polluted.
        ID3D11Texture2D* r168Rejected = nullptr;
        require(
            !outputColorSurface.copy_bound_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, surfaceTargetBinding,
                0u, &r168Rejected) && r168Rejected == nullptr,
            "R168 rejects absent R145 binding snapshot");
        require(
            !outputColorSurface.copy_bound_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, surfaceTargetBinding,
                surfaceTargetBindingReady.snapshotToken ^ 1ull,
                &r168Rejected) && r168Rejected == nullptr,
            "R168 rejects forged R145 binding snapshot");
        outrun::vr::dx11::NativeSurfacePairBinding r168UnsealedOwner;
        require(
            !outputColorSurface.copy_bound_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, r168UnsealedOwner,
                surfaceTargetBindingReady.snapshotToken, &r168Rejected) &&
            r168Rejected == nullptr,
            "R168 rejects unsealed owner even with copied R145 token");
        ID3D11RenderTargetView* r168ExtraRtvs[2] = {
            r164Color, r166SubstituteColor.render_target_view()};
        require(r168ExtraRtvs[1] != nullptr,
                "R168 additional offscreen RTV fixture");
        d3d.context->OMSetRenderTargets(
            2u, r168ExtraRtvs, outputDepthSurface.depth_stencil_view());
        require(
            !outputColorSurface.copy_bound_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, surfaceTargetBinding,
                surfaceTargetBindingReady.snapshotToken, &r168Rejected) &&
            r168Rejected == nullptr,
            "R168 rejects polluted OM slot 1 despite exact slot-0 RTV/DSV");
        require(
            surfaceTargetBinding.apply(
                d3d.context, outputColorSurface, outputDepthSurface) &&
            r157Probe(d3d.context, r164Color, indexedDirectDispatch),
            "R168 restores exact R145 OM owner after second-RTV pollution");

        ID3D11Texture2D* r165Readback = nullptr;
        require(
            outputColorSurface.copy_bound_color_depth_pair_to_staging(
                d3d.context, outputDepthSurface, surfaceTargetBinding,
                surfaceTargetBindingReady.snapshotToken, &r165Readback) &&
            r165Readback != nullptr,
            "R168 exact R145 binding lineage stages indexed WARP color/depth");
        D3D11_TEXTURE2D_DESC r165Desc{};
        r165Readback->GetDesc(&r165Desc);
        require(
            r165Desc.Width == 64u && r165Desc.Height == 32u &&
            r165Desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM &&
            r165Desc.Usage == D3D11_USAGE_STAGING &&
            r165Desc.BindFlags == 0u &&
            r165Desc.CPUAccessFlags == D3D11_CPU_ACCESS_READ &&
            r165Desc.SampleDesc.Count == 1u,
            "R165 staging resource has exact 64x32 BGRA8 read-only descriptor");
        D3D11_MAPPED_SUBRESOURCE r165Mapped{};
        require(
            SUCCEEDED(d3d.context->Map(
                r165Readback, 0u, D3D11_MAP_READ, 0u, &r165Mapped)) &&
            r165Mapped.pData != nullptr && r165Mapped.RowPitch >= 64u * 4u,
            "R165 readback map waits for offscreen WARP copy");
        constexpr unsigned char r165ExpectedBgra[4] = {96u, 64u, 32u, 255u};
        for (const UINT row : {0u, 31u}) {
            for (const UINT column : {0u, 63u}) {
                const auto* pixel =
                    static_cast<const unsigned char*>(r165Mapped.pData) +
                    static_cast<std::size_t>(row) * r165Mapped.RowPitch +
                    static_cast<std::size_t>(column) * 4u;
                bool matches = true;
                for (UINT channel = 0; channel < 4u; ++channel) {
                    const int delta = static_cast<int>(pixel[channel]) -
                        static_cast<int>(r165ExpectedBgra[channel]);
                    if (delta < -1 || delta > 1)
                        matches = false;
                }
                require(matches,
                    "R165 off-viewport border retains exact BGRA clear color");
            }
        }
        d3d.context->Unmap(r165Readback, 0u);
        r165Readback->Release();
        verify_r169_warp_fragment_coverage();

        const auto indexedSourceValuesOutOfRange =
            managedIndexBuffer.index_range_readiness(
                managedIndexReady, D3DFMT_INDEX16, 0u, 6u, 1u, 3u);
        require(
            indexedSourceValuesOutOfRange.inputValid &&
            indexedSourceValuesOutOfRange.byteRangeExact &&
            !indexedSourceValuesOutOfRange.valuesWithinDeclaredRange &&
            !indexedSourceValuesOutOfRange.ready &&
            indexedSourceValuesOutOfRange.snapshotToken == 0,
            "R152 indexed source values reject index outside declared vertex range");

        auto forgedManagedIndexReady = managedIndexReady;
        forgedManagedIndexReady.snapshotToken ^= 1u;
        const auto indexedSourceValuesForgedMirror =
            managedIndexBuffer.index_range_readiness(
                forgedManagedIndexReady, D3DFMT_INDEX16, 0u, 6u, 0u, 3u);
        require(
            indexedSourceValuesForgedMirror.inputValid &&
            !indexedSourceValuesForgedMirror.mirrorSnapshotExact &&
            !indexedSourceValuesForgedMirror.ready &&
            indexedSourceValuesForgedMirror.snapshotToken == 0,
            "R152 indexed source values reject forged managed IB snapshot");

        auto forgedIndexedGeometry = indexedGeometryReady;
        forgedIndexedGeometry.indexBufferSnapshotToken ^= 1u;
        const auto indexedSourceValueGeometryDrift =
            outrun::vr::dx11::
                compose_fixed_function_indexed_source_value_readiness(
                    indexedDirectDispatch, indexedDirectLineage,
                    indexedSourceRange, forgedIndexedGeometry,
                    indexedSourceValues);
        require(
            indexedSourceValueGeometryDrift.inputValid &&
            !indexedSourceValueGeometryDrift.geometryMatchesSourceValues &&
            !indexedSourceValueGeometryDrift.ready &&
            indexedSourceValueGeometryDrift.snapshotToken == 0,
            "R152 indexed source values reject geometry IB identity drift");

        require(
            !outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST, 2u, true,
                    0u, 1u, 0, indexedDirectDispatch.snapshotToken),
            "R147 direct indexed dispatch snapshot rejects StartIndexLocation drift");

        const auto directFanDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLEFAN, 2u, true,
                    0u, 0u, 0);
        require(
            !directFanDispatch.topologyMatchesGeometry &&
            !directFanDispatch.dispatchArgumentsExact &&
            !directFanDispatch.ready &&
            directFanDispatch.snapshotToken == 0,
            "R147 direct dispatch keeps triangle fan fail closed");

        const auto overflowDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    renderTargetBoundDraw, multiStageDrawReady,
                    indexedGeometryReady, D3DPT_TRIANGLELIST,
                    (std::numeric_limits<UINT>::max)(), true, 0u, 0u, 0);
        require(
            !overflowDirectDispatch.dispatchArgumentsExact &&
            !overflowDirectDispatch.ready &&
            overflowDirectDispatch.snapshotToken == 0,
            "R147 direct dispatch rejects element-count overflow");

        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, nonIndexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                nullptr, DXGI_FORMAT_UNKNOWN, 0),
            "R147 nonindexed direct IA prerequisite");
        const auto nonIndexedDirectDrawReady =
            compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, nonIndexedGeometryReady);
        require(
            nonIndexedDirectDrawReady.ready,
            "R147 nonindexed direct sealed draw prerequisite");
        const auto nonIndexedRenderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    nonIndexedDirectDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    nonIndexedGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                    surfaceTargetBinding, outputColorSurface, outputDepthSurface);
        require(
            nonIndexedRenderTargetBoundDraw.ready,
            "R147 nonindexed final bound-state prerequisite");

        const auto nonIndexedDirectDispatch =
            outrun::vr::dx11::
                compose_fixed_function_direct_draw_dispatch_readiness(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    1u, 0u, 0);
        require(
            nonIndexedDirectDispatch.ready &&
            !nonIndexedDirectDispatch.indexed &&
            nonIndexedDirectDispatch.bufferRangeExact &&
            nonIndexedDirectDispatch.elementCount == 4u &&
            nonIndexedDirectDispatch.startVertexLocation == 1u &&
            nonIndexedDirectDispatch.startIndexLocation == 0u &&
            nonIndexedDirectDispatch.baseVertexLocation == 0 &&
            nonIndexedDirectDispatch.snapshotToken != 0 &&
            outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    1u, 0u, 0, nonIndexedDirectDispatch.snapshotToken),
            "R147 direct nonindexed dispatch seals Draw start vertex");

        // R156 issues real native Draw on WARP using the already sealed IA/VS/PS
        // and OM target, without enabling the game's native draw selector.
        ID3D11Query* r156Stats = nullptr;
        D3D11_QUERY_DESC r156StatsDesc{};
        r156StatsDesc.Query = D3D11_QUERY_PIPELINE_STATISTICS;
        require(
            SUCCEEDED(d3d.device->CreateQuery(&r156StatsDesc, &r156Stats)) &&
            r156Stats != nullptr,
            "R156 offscreen WARP pipeline statistics query prerequisite");
        auto r156Probe = [&](ID3D11DeviceContext* context,
                             ID3D11RenderTargetView* target,
                             const outrun::vr::dx11::NativeFixedFunctionDirectDrawDispatchReadiness& packet) {
            return outrun::vr::dx11::
                prepare_fixed_function_nonindexed_direct_draw_probe(
                    context, target, pipelineBundle.input_layout(),
                    pipelineBundle.vertex_shader(), pipelineBundle.pixel_shader(),
                    nonIndexedRenderTargetBoundDraw,
                    nonIndexedDirectDrawReady, nonIndexedGeometryReady,
                    packet, D3DPT_TRIANGLESTRIP, 2u, 1u);
        };
        require(
            !r156Probe(d3d.context, nullptr, nonIndexedDirectDispatch),
            "R156 refuses missing offscreen target");
        ID3D11DeviceContext* r156Deferred = nullptr;
        require(
            SUCCEEDED(d3d.device->CreateDeferredContext(0, &r156Deferred)) &&
            r156Deferred != nullptr,
            "R156 deferred context negative prerequisite");
        require(
            !r156Probe(r156Deferred, outputColorSurface.render_target_view(),
                       nonIndexedDirectDispatch),
            "R156 deferred recording never issues native probe Draw");
        r156Deferred->Release();
        auto r156Forged = nonIndexedDirectDispatch;
        r156Forged.startVertexLocation ^= 1u;
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       r156Forged),
            "R156 refuses stale nonindexed Draw argument tuple");
        auto r156WrongElementCount = nonIndexedDirectDispatch;
        r156WrongElementCount.elementCount += 1u;
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       r156WrongElementCount),
            "R156 copied Draw packet cannot forge an extra vertex count");
        auto r156WrongLineage = nonIndexedDirectDispatch;
        r156WrongLineage.geometrySnapshotToken ^= 1u;
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       r156WrongLineage),
            "R156 copied Draw packet cannot borrow a foreign geometry token");
        // R171: same-device IA/VS/PS mutations must fail closed even when
        // the prior dispatch token and vertex/topology provenance are intact.
        d3d.context->IASetInputLayout(nullptr);
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       nonIndexedDirectDispatch),
            "R171 rejects detached nonindexed IA layout");
        d3d.context->IASetInputLayout(pipelineBundle.input_layout());
        require(vertexShader != pipelineBundle.vertex_shader(),
                "R171 distinct same-device VS substitution prerequisite");
        d3d.context->VSSetShader(vertexShader, nullptr, 0u);
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       nonIndexedDirectDispatch),
            "R171 rejects substituted nonindexed live VS");
        d3d.context->VSSetShader(pipelineBundle.vertex_shader(), nullptr, 0u);
        d3d.context->PSSetShader(nullptr, nullptr, 0u);
        require(
            !r156Probe(d3d.context, outputColorSurface.render_target_view(),
                       nonIndexedDirectDispatch),
            "R171 rejects detached nonindexed PS");
        d3d.context->PSSetShader(pipelineBundle.pixel_shader(), nullptr, 0u);
        d3d.context->Begin(r156Stats);
        require(
            r156Probe(d3d.context, outputColorSurface.render_target_view(),
                      nonIndexedDirectDispatch),
            "R171 exact IA/VS/PS restore permits native nonindexed Draw");
        // The protected native backend never calls Draw*: issue this only
        // inside the isolated WARP regression probe after live preflight.
        d3d.context->Draw(
            nonIndexedDirectDispatch.elementCount,
            nonIndexedDirectDispatch.startVertexLocation);
        d3d.context->End(r156Stats);
        d3d.context->Flush();
        D3D11_QUERY_DATA_PIPELINE_STATISTICS r156Counters{};
        HRESULT r156QueryResult = S_FALSE;
        for (unsigned spin = 0; spin < 2048u; ++spin) {
            r156QueryResult = d3d.context->GetData(
                r156Stats, &r156Counters, sizeof(r156Counters), 0u);
            if (r156QueryResult != S_FALSE)
                break;
        }
        require(
            r156QueryResult == S_OK && r156Counters.IAPrimitives == 2u,
            "R156 WARP confirms two actual native triangle-strip primitives");
        r156Stats->Release();

        require(
            !outrun::vr::dx11::
                validate_fixed_function_direct_draw_dispatch_snapshot(
                    nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                    nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                    2u, 0u, 0, nonIndexedDirectDispatch.snapshotToken),
            "R147 direct nonindexed dispatch snapshot rejects StartVertexLocation drift");

        const auto nonIndexedVertexBufferOverrun =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                nonIndexedRenderTargetBoundDraw, nonIndexedDirectDrawReady,
                nonIndexedGeometryReady, D3DPT_TRIANGLESTRIP, 2u, false,
                14u, 0u, 0);
        require(
            nonIndexedVertexBufferOverrun.inputValid &&
            !nonIndexedVertexBufferOverrun.bufferRangeExact &&
            !nonIndexedVertexBufferOverrun.dispatchArgumentsExact &&
            !nonIndexedVertexBufferOverrun.ready &&
            nonIndexedVertexBufferOverrun.snapshotToken == 0,
            "R151 direct nonindexed dispatch rejects vertex buffer overrun");

        const auto pointListGeometryReady =
            outrun::vr::dx11::compose_fixed_function_geometry_readiness(
                managedVertexPostResetReady, false, managedIndexReady,
                D3DPT_POINTLIST);
        require(
            pointListGeometryReady.ready &&
            pointListGeometryReady.topology ==
                D3D11_PRIMITIVE_TOPOLOGY_POINTLIST &&
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, pointListGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                nullptr, DXGI_FORMAT_UNKNOWN, 0u),
            "R155 point-list fixture reaches exact dormant IA topology");

        const auto pointListDrawReady =
            compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, pointListGeometryReady);
        const auto pointListRenderTargetBoundDraw =
            outrun::vr::dx11::
                compose_fixed_function_render_target_bound_draw_readiness(
                    pointListDrawReady, d3d.context, outputStateBinding,
                    pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                    multiStageSamplers, multiStageTextures,
                    pointListGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                    surfaceTargetBinding, outputColorSurface, outputDepthSurface);
        const auto pointListDirectDispatch =
            outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                pointListRenderTargetBoundDraw, pointListDrawReady,
                pointListGeometryReady, D3DPT_POINTLIST, 1u, false,
                0u, 0u, 0);
        require(
            pointListRenderTargetBoundDraw.ready &&
            pointListDirectDispatch.inputValid &&
            pointListDirectDispatch.renderTargetBoundDrawReady &&
            pointListDirectDispatch.geometryReady &&
            pointListDirectDispatch.geometryMatchesDraw &&
            pointListDirectDispatch.topologyMatchesGeometry &&
            pointListDirectDispatch.bufferRangeExact &&
            pointListDirectDispatch.dispatchArgumentsExact &&
            !pointListDirectDispatch.pointRasterSemanticsExact &&
            !pointListDirectDispatch.ready &&
            pointListDirectDispatch.snapshotToken == 0,
            "R155 direct point-list raster semantics remain fail closed");

        const std::array<D3DPRIMITIVETYPE, 2> directLinePrimitives{
            D3DPT_LINELIST, D3DPT_LINESTRIP};
        for (const auto linePrimitive : directLinePrimitives) {
            const auto lineGeometryReady =
                outrun::vr::dx11::compose_fixed_function_geometry_readiness(
                    managedVertexPostResetReady, false, managedIndexReady,
                    linePrimitive);
            require(
                lineGeometryReady.ready &&
                outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                    d3d.context, lineGeometryReady, managedVertexBuffer,
                    geometryVertexStride, geometryVertexOffset,
                    nullptr, DXGI_FORMAT_UNKNOWN, 0u),
                "R157 line fixture reaches exact dormant IA topology");

            const auto lineDrawReady = compose_fixed_function_draw_readiness(
                multiStageActivation, outputBindingRenderReady, surfacePairReady,
                outputStateReady, outputStateBinding, lineGeometryReady);
            const auto lineRenderTargetBoundDraw =
                outrun::vr::dx11::
                    compose_fixed_function_render_target_bound_draw_readiness(
                        lineDrawReady, d3d.context, outputStateBinding,
                        pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                        multiStageSamplers, multiStageTextures,
                        lineGeometryReady, managedVertexBuffer,
                        geometryVertexStride, geometryVertexOffset,
                        nullptr, DXGI_FORMAT_UNKNOWN, 0u, transform,
                        surfaceTargetBinding, outputColorSurface, outputDepthSurface);
            const auto lineDirectDispatch =
                outrun::vr::dx11::compose_fixed_function_direct_draw_dispatch_readiness(
                    lineRenderTargetBoundDraw, lineDrawReady, lineGeometryReady,
                    linePrimitive, 1u, false, 0u, 0u, 0);
            require(
                lineRenderTargetBoundDraw.ready &&
                lineDirectDispatch.inputValid &&
                lineDirectDispatch.renderTargetBoundDrawReady &&
                lineDirectDispatch.geometryReady &&
                lineDirectDispatch.geometryMatchesDraw &&
                lineDirectDispatch.topologyMatchesGeometry &&
                lineDirectDispatch.pointRasterSemanticsExact &&
                !lineDirectDispatch.lineRasterSemanticsExact &&
                lineDirectDispatch.bufferRangeExact &&
                lineDirectDispatch.dispatchArgumentsExact &&
                !lineDirectDispatch.ready &&
                lineDirectDispatch.snapshotToken == 0,
                "R157 direct line raster semantics remain fail closed");
        }

        require(
            outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
                d3d.context, indexedGeometryReady, managedVertexBuffer,
                geometryVertexStride, geometryVertexOffset,
                &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
            "R147 restore indexed direct IA after dispatch proof");
    }

    constexpr UINT liveFanBaseVertex = 5u;
    NativeTriangleFanIndexBuffer liveFanOwner;
    require(
        liveFanOwner.initialize_nonindexed(
            d3d.device, 3u, liveFanBaseVertex),
        "R142 generated fan owner prerequisite");
    const auto liveFanOwnerReady = liveFanOwner.readiness(d3d.device);
    require(
        (static_cast<std::uint64_t>(liveFanBaseVertex) + 5ull) *
                geometryVertexStride <= managedVertexBuffer.byte_width(),
        "R154 positive fan fixture fits managed vertex-buffer capacity");
    const auto liveFanVertexReady =
        managedVertexBuffer.mirror_readiness(d3d.device);
    const auto liveFanGeometryReady =
        compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(
            liveFanVertexReady, liveFanOwnerReady, 3u, liveFanBaseVertex);
    require(
        liveFanGeometryReady.ready &&
        liveFanGeometryReady.generatedIndexBufferMatchesDraw &&
        liveFanGeometryReady.generatedIndexBufferSnapshotToken ==
            liveFanOwnerReady.snapshotToken,
        "R142 generated fan geometry prerequisite");

    const auto liveFanDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, liveFanGeometryReady);
    require(
        liveFanDrawReady.ready &&
        liveFanDrawReady.geometrySnapshotToken ==
            liveFanGeometryReady.snapshotToken,
        "R142 generated fan sealed draw prerequisite");

    ID3D11Buffer* liveFanVertexBuffer =
        managedVertexBuffer.mirror_buffer();
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        liveFanOwner.bind(d3d.context),
        "R142 bind generated fan IA prerequisite");

    const auto completeFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex);
    require(
        completeFanBoundDraw.inputValid &&
        completeFanBoundDraw.sameContextBoundDrawReady &&
        completeFanBoundDraw.geometryReady &&
        completeFanBoundDraw.geometryMatchesDraw &&
        completeFanBoundDraw.vertexBufferBoundExact &&
        completeFanBoundDraw.generatedIndexBindingReady &&
        completeFanBoundDraw.generatedIndexMatchesGeometry &&
        completeFanBoundDraw.componentSnapshotsPresent &&
        completeFanBoundDraw.ready &&
        completeFanBoundDraw.geometrySnapshotToken ==
            liveFanGeometryReady.snapshotToken &&
        completeFanBoundDraw.vertexBufferSnapshotToken ==
            liveFanVertexReady.snapshotToken &&
        completeFanBoundDraw.generatedIndexBindingSnapshotToken != 0 &&
        completeFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw seals live VB and generated IB");

    const auto finalFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        finalFanBoundDraw.inputValid &&
        finalFanBoundDraw.completeFanBoundDrawReady &&
        finalFanBoundDraw.transformBindingReady &&
        finalFanBoundDraw.surfaceTargetBindingReady &&
        finalFanBoundDraw.surfacePairMatchesDraw &&
        finalFanBoundDraw.componentSnapshotsPresent &&
        finalFanBoundDraw.ready &&
        finalFanBoundDraw.transformPayloadHash == transform.payloadHash &&
        finalFanBoundDraw.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        finalFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw seals live VS b0 and OM target");

    ID3D11Buffer* nullFanTransformBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullFanTransformBuffer);
    const auto fanMissingTransform =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanMissingTransform.completeFanBoundDrawReady &&
        !fanMissingTransform.transformBindingReady &&
        fanMissingTransform.surfaceTargetBindingReady &&
        !fanMissingTransform.ready &&
        fanMissingTransform.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw fails closed after VS b0 drift");

    ID3D11Buffer* restoredFanTransformBuffer =
        pipelineBundle.transform_buffer().buffer();
    d3d.context->VSSetConstantBuffers(0, 1, &restoredFanTransformBuffer);
    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    const auto fanMissingTargets =
        outrun::vr::dx11::
            compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanMissingTargets.completeFanBoundDrawReady &&
        fanMissingTargets.transformBindingReady &&
        !fanMissingTargets.surfaceTargetBindingReady &&
        fanMissingTargets.surfacePairMatchesDraw &&
        !fanMissingTargets.ready &&
        fanMissingTargets.snapshotToken == 0,
        "R146 nonindexed fan final draw fails closed after OM target drift");
    require(
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface) &&
        outrun::vr::dx11::
            validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalFanBoundDraw.snapshotToken),
        "R146 nonindexed fan final draw restores transform and OM target snapshot");


    const auto fanDispatch =
        outrun::vr::dx11::
            compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        fanDispatch.inputValid &&
        fanDispatch.finalFanBoundDrawReady &&
        fanDispatch.generatedIndexReady &&
        fanDispatch.generatedIndexMatchesDispatch &&
        fanDispatch.vertexBufferRangeExact &&
        fanDispatch.dispatchArgumentsExact &&
        fanDispatch.componentSnapshotsPresent &&
        fanDispatch.ready &&
        !fanDispatch.indexedSource &&
        fanDispatch.primitiveCount == 3u &&
        fanDispatch.indexCount == 9u &&
        fanDispatch.startIndexLocation == 0u &&
        fanDispatch.baseVertexLocation == 0 &&
        fanDispatch.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R148 generated fan dispatch seals nonindexed DrawIndexed tuple");
    require(
        !outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex + 1u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R148 generated fan dispatch rejects nonindexed base-vertex drift");

    const UINT fanCapacityOverrunStride =
        managedVertexBuffer.byte_width();
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &fanCapacityOverrunStride, &geometryVertexOffset);
    const auto fanCapacityOverrun =
        outrun::vr::dx11::
            compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, fanCapacityOverrunStride,
                geometryVertexOffset, liveFanOwner, 3u, liveFanBaseVertex, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface);
    require(
        fanCapacityOverrun.inputValid &&
        fanCapacityOverrun.finalFanBoundDrawReady &&
        fanCapacityOverrun.generatedIndexReady &&
        fanCapacityOverrun.generatedIndexMatchesDispatch &&
        !fanCapacityOverrun.vertexBufferRangeExact &&
        !fanCapacityOverrun.dispatchArgumentsExact &&
        !fanCapacityOverrun.ready &&
        fanCapacityOverrun.snapshotToken == 0,
        "R154 nonindexed fan dispatch rejects vertex buffer overrun");
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        outrun::vr::dx11::
            validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                fanDispatch.snapshotToken),
        "R154 nonindexed fan dispatch restores bounded vertex span");

    d3d.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto fanTopologyDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex);
    require(
        fanTopologyDrift.sameContextBoundDrawReady &&
        fanTopologyDrift.geometryReady &&
        fanTopologyDrift.geometryMatchesDraw &&
        fanTopologyDrift.vertexBufferBoundExact &&
        !fanTopologyDrift.generatedIndexBindingReady &&
        !fanTopologyDrift.ready &&
        fanTopologyDrift.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw rejects generated IB topology drift");
    require(
        liveFanOwner.bind(d3d.context),
        "R142 restore generated fan topology after drift");

    const UINT liveFanStrideDrift = geometryVertexStride + 4u;
    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &liveFanStrideDrift, &geometryVertexOffset);
    const auto fanVertexDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex);
    require(
        fanVertexDrift.sameContextBoundDrawReady &&
        fanVertexDrift.geometryReady &&
        fanVertexDrift.geometryMatchesDraw &&
        !fanVertexDrift.vertexBufferBoundExact &&
        fanVertexDrift.generatedIndexBindingReady &&
        fanVertexDrift.generatedIndexMatchesGeometry &&
        !fanVertexDrift.ready &&
        fanVertexDrift.snapshotToken == 0,
        "R142 complete fan bound draw rejects live VB stride drift");

    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        outrun::vr::dx11::
            validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(
                liveFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveFanOwner, 3u, liveFanBaseVertex, completeFanBoundDraw.snapshotToken),
        "R142 complete fan bound draw restores deterministic live IA snapshot");

    // R156 capacity fixture is intentionally bounded by the 256-byte managed
    // VB at stride 24. The positive BaseVertexLocation (-3) must fit while the
    // negative probe (+1) must cross the same byte-capacity boundary.
    const std::array<std::uint16_t, 5> liveIndexedFanSource{
        99u, 4u, 6u, 8u, 9u};
    NativeManagedBufferShadow liveIndexedFanSourceBuffer;
    require(
        liveIndexedFanSourceBuffer.initialize(
            ResourceRole::Index,
            static_cast<UINT>(sizeof(liveIndexedFanSource)),
            0) &&
        liveIndexedFanSourceBuffer.write_range(
            0, liveIndexedFanSource.data(),
            static_cast<UINT>(sizeof(liveIndexedFanSource))) &&
        liveIndexedFanSourceBuffer.recreate_and_upload_mirror(d3d.device),
        "R155 indexed fan managed source prerequisite");
    const auto liveIndexedSourceReady =
        liveIndexedFanSourceBuffer.mirror_readiness(d3d.device);
    NativeTriangleFanIndexBuffer liveIndexedFanOwner;
    require(
        liveIndexedSourceReady.ready &&
        liveIndexedSourceReady.role == ResourceRole::Index &&
        liveIndexedFanOwner.initialize_indexed(
            d3d.device, 2u, D3DFMT_INDEX16, 1u,
            liveIndexedFanSource.data(),
            static_cast<UINT>(liveIndexedFanSource.size()),
            liveIndexedSourceReady.snapshotToken),
        "R144 indexed generated fan owner prerequisite");
    const auto liveIndexedFanOwnerReady =
        liveIndexedFanOwner.readiness(d3d.device);
    const auto liveIndexedFanSourceContent =
        outrun::vr::dx11::compose_fixed_function_indexed_fan_source_content_readiness(
            liveIndexedFanSourceBuffer, liveIndexedFanOwner, d3d.device);
    require(
        liveIndexedFanSourceContent.inputValid &&
        liveIndexedFanSourceContent.generatedIndexReady &&
        liveIndexedFanSourceContent.sourceIndexReady &&
        liveIndexedFanSourceContent.sourceProvenanceMatches &&
        liveIndexedFanSourceContent.expandedContentExact &&
        liveIndexedFanSourceContent.componentSnapshotsPresent &&
        liveIndexedFanSourceContent.ready &&
        liveIndexedFanSourceContent.expectedExpandedContentHash ==
            liveIndexedFanOwnerReady.contentHash &&
        liveIndexedFanSourceContent.snapshotToken != 0 &&
        outrun::vr::dx11::validate_fixed_function_indexed_fan_source_content_snapshot(
            liveIndexedFanSourceBuffer, liveIndexedFanOwner, d3d.device,
            liveIndexedFanSourceContent.snapshotToken),
        "R155 indexed fan source content matches exact managed IB shadow");

    const std::array<std::uint16_t, 5> forgedIndexedFanSource{
        99u, 4u, 6u, 8u, 10u};
    NativeTriangleFanIndexBuffer forgedIndexedFanOwner;
    require(
        forgedIndexedFanOwner.initialize_indexed(
            d3d.device, 2u, D3DFMT_INDEX16, 1u,
            forgedIndexedFanSource.data(),
            static_cast<UINT>(forgedIndexedFanSource.size()),
            liveIndexedSourceReady.snapshotToken),
        "R155 forged indexed fan owner prerequisite");
    const auto forgedIndexedFanSourceContent =
        outrun::vr::dx11::compose_fixed_function_indexed_fan_source_content_readiness(
            liveIndexedFanSourceBuffer, forgedIndexedFanOwner, d3d.device);
    require(
        forgedIndexedFanSourceContent.inputValid &&
        forgedIndexedFanSourceContent.generatedIndexReady &&
        forgedIndexedFanSourceContent.sourceIndexReady &&
        forgedIndexedFanSourceContent.sourceProvenanceMatches &&
        !forgedIndexedFanSourceContent.expandedContentExact &&
        !forgedIndexedFanSourceContent.ready &&
        forgedIndexedFanSourceContent.snapshotToken == 0,
        "R155 indexed fan source content rejects borrowed token with foreign bytes");
    const auto liveIndexedFanGeometryReady =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_geometry_readiness(
                liveFanVertexReady, liveIndexedSourceReady,
                liveIndexedFanOwnerReady, 2u, D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()));
    require(
        liveIndexedFanGeometryReady.ready &&
        liveIndexedFanGeometryReady.indexBufferSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        liveIndexedFanGeometryReady.generatedIndexBufferSnapshotToken ==
            liveIndexedFanOwnerReady.snapshotToken,
        "R144 indexed fan geometry prerequisite");

    const auto liveIndexedFanDrawReady =
        compose_fixed_function_draw_readiness(
            multiStageActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding,
            liveIndexedFanGeometryReady);
    require(
        liveIndexedFanDrawReady.ready &&
        liveIndexedFanDrawReady.geometrySnapshotToken ==
            liveIndexedFanGeometryReady.snapshotToken,
        "R144 indexed fan sealed draw prerequisite");

    d3d.context->IASetVertexBuffers(
        0, 1, &liveFanVertexBuffer,
        &geometryVertexStride, &geometryVertexOffset);
    require(
        liveIndexedFanOwner.bind(d3d.context),
        "R144 bind indexed generated fan IA prerequisite");

    constexpr INT indexedFanBaseVertexLocation = -3;
    constexpr UINT indexedFanObservedMaxIndex = 9u;
    const std::int64_t indexedFanPositiveEffectiveMax =
        static_cast<std::int64_t>(indexedFanBaseVertexLocation) +
        static_cast<std::int64_t>(indexedFanObservedMaxIndex);
    const std::int64_t indexedFanOverrunEffectiveMax =
        1ll + static_cast<std::int64_t>(indexedFanObservedMaxIndex);
    require(
        indexedFanPositiveEffectiveMax >= 0 &&
        (static_cast<std::uint64_t>(indexedFanPositiveEffectiveMax) + 1ull) *
                static_cast<std::uint64_t>(geometryVertexStride) <=
            static_cast<std::uint64_t>(managedVertexBuffer.byte_width()) &&
        indexedFanOverrunEffectiveMax >= 0 &&
        (static_cast<std::uint64_t>(indexedFanOverrunEffectiveMax) + 1ull) *
                static_cast<std::uint64_t>(geometryVertexStride) >
            static_cast<std::uint64_t>(managedVertexBuffer.byte_width()),
        "R156 indexed fan capacity fixture straddles managed VB boundary");
    const auto completeIndexedFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation);
    require(
        completeIndexedFanBoundDraw.inputValid &&
        completeIndexedFanBoundDraw.sameContextBoundDrawReady &&
        completeIndexedFanBoundDraw.geometryReady &&
        completeIndexedFanBoundDraw.geometryMatchesDraw &&
        completeIndexedFanBoundDraw.sourceIndexBufferCurrent &&
        completeIndexedFanBoundDraw.vertexBufferBoundExact &&
        completeIndexedFanBoundDraw.generatedIndexBindingReady &&
        completeIndexedFanBoundDraw.generatedIndexMatchesGeometry &&
        completeIndexedFanBoundDraw.componentSnapshotsPresent &&
        completeIndexedFanBoundDraw.ready &&
        completeIndexedFanBoundDraw.geometrySnapshotToken ==
            liveIndexedFanGeometryReady.snapshotToken &&
        completeIndexedFanBoundDraw.sourceIndexBufferSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        completeIndexedFanBoundDraw.generatedIndexBindingSnapshotToken != 0 &&
        completeIndexedFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation,
                completeIndexedFanBoundDraw.snapshotToken),
        "R144 indexed fan final bound draw seals source provenance and live generated IA");

    const auto finalIndexedFanBoundDraw =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        finalIndexedFanBoundDraw.inputValid &&
        finalIndexedFanBoundDraw.completeFanBoundDrawReady &&
        finalIndexedFanBoundDraw.transformBindingReady &&
        finalIndexedFanBoundDraw.surfaceTargetBindingReady &&
        finalIndexedFanBoundDraw.surfacePairMatchesDraw &&
        finalIndexedFanBoundDraw.componentSnapshotsPresent &&
        finalIndexedFanBoundDraw.ready &&
        finalIndexedFanBoundDraw.transformPayloadHash == transform.payloadHash &&
        finalIndexedFanBoundDraw.surfacePairSnapshotToken ==
            surfacePairReady.snapshotToken &&
        finalIndexedFanBoundDraw.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw seals live VS b0 and OM target");

    ID3D11Buffer* nullIndexedFanTransformBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullIndexedFanTransformBuffer);
    const auto indexedFanMissingTransform =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanMissingTransform.completeFanBoundDrawReady &&
        !indexedFanMissingTransform.transformBindingReady &&
        indexedFanMissingTransform.surfaceTargetBindingReady &&
        indexedFanMissingTransform.surfacePairMatchesDraw &&
        !indexedFanMissingTransform.ready &&
        indexedFanMissingTransform.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw fails closed after VS b0 drift");

    ID3D11Buffer* restoredIndexedFanTransformBuffer =
        pipelineBundle.transform_buffer().buffer();
    d3d.context->VSSetConstantBuffers(
        0, 1, &restoredIndexedFanTransformBuffer);

    d3d.context->OMSetRenderTargets(0, nullptr, nullptr);
    const auto indexedFanMissingTargets =
        outrun::vr::dx11::
            compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanMissingTargets.completeFanBoundDrawReady &&
        indexedFanMissingTargets.transformBindingReady &&
        !indexedFanMissingTargets.surfaceTargetBindingReady &&
        indexedFanMissingTargets.surfacePairMatchesDraw &&
        !indexedFanMissingTargets.ready &&
        indexedFanMissingTargets.snapshotToken == 0 &&
        !outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw fails closed after OM target drift");

    require(
        surfaceTargetBinding.apply(
            d3d.context, outputColorSurface, outputDepthSurface) &&
        outrun::vr::dx11::
            validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                finalIndexedFanBoundDraw.snapshotToken),
        "R146 indexed fan final draw restores transform and OM target snapshot");

    require(
        !outrun::vr::dx11::
            validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation + 1,
                completeIndexedFanBoundDraw.snapshotToken),
        "R144 indexed fan final snapshot rejects BaseVertexLocation drift");

    const auto indexedFanFormatDrift =
        outrun::vr::dx11::
            compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX32, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation);
    require(
        indexedFanFormatDrift.sameContextBoundDrawReady &&
        !indexedFanFormatDrift.geometryReady &&
        !indexedFanFormatDrift.geometryMatchesDraw &&
        indexedFanFormatDrift.generatedIndexBindingReady &&
        !indexedFanFormatDrift.ready &&
        indexedFanFormatDrift.snapshotToken == 0,
        "R144 indexed fan final bound draw rejects source format drift");


    const auto indexedFanDispatch =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, 4u, 6u, transform,
                surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanDispatch.inputValid &&
        indexedFanDispatch.finalFanBoundDrawReady &&
        indexedFanDispatch.generatedIndexReady &&
        indexedFanDispatch.generatedIndexMatchesDispatch &&
        indexedFanDispatch.sourceDeclaredVertexRangeExact &&
        indexedFanDispatch.sourceValuesWithinDeclaredRange &&
        indexedFanDispatch.sourceDeclaredVertexBufferRangeExact &&
        indexedFanDispatch.sourceMinVertexIndex == 4u &&
        indexedFanDispatch.sourceNumVertices == 6u &&
        indexedFanDispatch.sourceMaxVertexIndex == indexedFanObservedMaxIndex &&
        indexedFanDispatch.vertexBufferRangeExact &&
        indexedFanDispatch.dispatchArgumentsExact &&
        indexedFanDispatch.componentSnapshotsPresent &&
        indexedFanDispatch.ready &&
        indexedFanDispatch.indexedSource &&
        indexedFanDispatch.primitiveCount == 2u &&
        indexedFanDispatch.indexCount == 6u &&
        indexedFanDispatch.startIndexLocation == 0u &&
        indexedFanDispatch.baseVertexLocation ==
            indexedFanBaseVertexLocation &&
        indexedFanDispatch.sourceIndexSnapshotToken ==
            liveIndexedSourceReady.snapshotToken &&
        indexedFanDispatch.sourceContentSnapshotToken ==
            liveIndexedFanSourceContent.snapshotToken &&
        indexedFanDispatch.sourceObservedMinIndex == 4u &&
        indexedFanDispatch.sourceObservedMaxIndex == indexedFanObservedMaxIndex &&
        indexedFanDispatch.sourceValueSnapshotToken != 0 &&
        indexedFanDispatch.snapshotToken != 0 &&
        outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, 4u, 6u, transform,
                surfaceTargetBinding,
                outputColorSurface, outputDepthSurface,
                indexedFanDispatch.snapshotToken),
        "R148 generated fan dispatch seals indexed DrawIndexed tuple");

    const auto indexedFanVertexOverrun =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                1, 4u, 6u, transform, surfaceTargetBinding,
                outputColorSurface, outputDepthSurface);
    require(
        indexedFanVertexOverrun.inputValid &&
        indexedFanVertexOverrun.finalFanBoundDrawReady &&
        indexedFanVertexOverrun.generatedIndexReady &&
        indexedFanVertexOverrun.generatedIndexMatchesDispatch &&
        indexedFanVertexOverrun.sourceObservedMinIndex == 4u &&
        indexedFanVertexOverrun.sourceObservedMaxIndex == indexedFanObservedMaxIndex &&
        indexedFanVertexOverrun.sourceValueSnapshotToken != 0 &&
        indexedFanVertexOverrun.sourceDeclaredVertexRangeExact &&
        indexedFanVertexOverrun.sourceValuesWithinDeclaredRange &&
        !indexedFanVertexOverrun.vertexBufferRangeExact &&
        !indexedFanVertexOverrun.sourceDeclaredVertexBufferRangeExact &&
        !indexedFanVertexOverrun.dispatchArgumentsExact &&
        !indexedFanVertexOverrun.ready &&
        indexedFanVertexOverrun.snapshotToken == 0,
        "R156 indexed fan dispatch rejects effective vertex buffer overrun");

    const auto indexedFanDeclaredRangeMismatch =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, 4u, 5u, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface);
    require(
        indexedFanDeclaredRangeMismatch.inputValid &&
        indexedFanDeclaredRangeMismatch.finalFanBoundDrawReady &&
        indexedFanDeclaredRangeMismatch.generatedIndexReady &&
        indexedFanDeclaredRangeMismatch.generatedIndexMatchesDispatch &&
        indexedFanDeclaredRangeMismatch.sourceDeclaredVertexRangeExact &&
        !indexedFanDeclaredRangeMismatch.sourceValuesWithinDeclaredRange &&
        indexedFanDeclaredRangeMismatch.sourceObservedMinIndex == 4u &&
        indexedFanDeclaredRangeMismatch.sourceObservedMaxIndex ==
            indexedFanObservedMaxIndex &&
        indexedFanDeclaredRangeMismatch.sourceValueSnapshotToken == 0 &&
        !indexedFanDeclaredRangeMismatch.vertexBufferRangeExact &&
        !indexedFanDeclaredRangeMismatch.sourceDeclaredVertexBufferRangeExact &&
        !indexedFanDeclaredRangeMismatch.dispatchArgumentsExact &&
        !indexedFanDeclaredRangeMismatch.ready &&
        indexedFanDeclaredRangeMismatch.snapshotToken == 0,
        "indexed fan dispatch rejects source index outside D3D9 declared vertex range");

    const auto indexedFanDeclaredCapacityOverrun =
        outrun::vr::dx11::
            compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation, 4u, 13u, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface);
    require(
        indexedFanDeclaredCapacityOverrun.inputValid &&
        indexedFanDeclaredCapacityOverrun.finalFanBoundDrawReady &&
        indexedFanDeclaredCapacityOverrun.generatedIndexReady &&
        indexedFanDeclaredCapacityOverrun.generatedIndexMatchesDispatch &&
        indexedFanDeclaredCapacityOverrun.sourceDeclaredVertexRangeExact &&
        indexedFanDeclaredCapacityOverrun.sourceValuesWithinDeclaredRange &&
        indexedFanDeclaredCapacityOverrun.vertexBufferRangeExact &&
        !indexedFanDeclaredCapacityOverrun.sourceDeclaredVertexBufferRangeExact &&
        !indexedFanDeclaredCapacityOverrun.dispatchArgumentsExact &&
        !indexedFanDeclaredCapacityOverrun.ready &&
        indexedFanDeclaredCapacityOverrun.snapshotToken == 0,
        "R160 indexed fan rejects declared vertex window beyond managed VB");

    require(
        !outrun::vr::dx11::
            validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(
                liveIndexedFanDrawReady, d3d.context, outputStateBinding,
                pipelineBundle, inputLayout, vertexPrototype, pixelPrototype,
                multiStageSamplers, multiStageTextures,
                managedVertexBuffer, geometryVertexStride, geometryVertexOffset,
                liveIndexedFanSourceBuffer, liveIndexedFanOwner, 2u,
                D3DFMT_INDEX16, 1u,
                static_cast<UINT>(liveIndexedFanSource.size()),
                indexedFanBaseVertexLocation + 1, 4u, 6u, transform,
                surfaceTargetBinding, outputColorSurface, outputDepthSurface,
                indexedFanDispatch.snapshotToken),
        "R148 generated fan dispatch rejects indexed BaseVertexLocation drift");

    require(
        outrun::vr::dx11::bind_fixed_function_geometry_for_observation(
            d3d.context, indexedGeometryReady, managedVertexBuffer,
            geometryVertexStride, geometryVertexOffset,
            &managedIndexBuffer, DXGI_FORMAT_R16_UINT, geometryIndexOffset),
        "R142 restore direct IA geometry after generated fan proof");

    auto mismatchedPipelineBinding = drawPipelineBindingReady;
    mismatchedPipelineBinding.pipelineSnapshotToken ^= 0x100000001b3ull;
    const auto mismatchedPipelineBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, texturedDrawReady, mismatchedPipelineBinding,
            d3d.context, outputStateBinding);
    require(
        mismatchedPipelineBoundDraw.pipelineBindingReady &&
        !mismatchedPipelineBoundDraw.pipelineBindingMatchesDraw &&
        !mismatchedPipelineBoundDraw.ready &&
        mismatchedPipelineBoundDraw.snapshotToken == 0,
        "R134 bound draw rejects mismatched R112 pipeline identity");

    auto mismatchedTexturedDraw = texturedDrawReady;
    mismatchedTexturedDraw.drawSnapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto mismatchedTexturedBoundDraw =
        outrun::vr::dx11::compose_fixed_function_bound_draw_readiness(
            drawReady, mismatchedTexturedDraw, drawPipelineBindingReady,
            d3d.context, outputStateBinding);
    require(
        !mismatchedTexturedBoundDraw.texturedDrawReady &&
        mismatchedTexturedBoundDraw.pipelineBindingReady &&
        mismatchedTexturedBoundDraw.pipelineBindingMatchesDraw &&
        !mismatchedTexturedBoundDraw.ready &&
        mismatchedTexturedBoundDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_bound_draw_snapshot(
            drawReady, mismatchedTexturedDraw, drawPipelineBindingReady,
            d3d.context, outputStateBinding, boundDrawReady.snapshotToken),
        "R134 bound draw rejects textured R133-to-R131 identity drift");

    d3d.context->PSSetShader(nullptr, nullptr, 0);
    const auto staleLivePipelineBinding =
        pipelineBundle.binding_readiness(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken);
    require(
        !staleLivePipelineBinding.boundExact &&
        !staleLivePipelineBinding.ready &&
        staleLivePipelineBinding.snapshotToken == 0 &&
        !pipelineBundle.validate_binding_snapshot(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken,
            drawPipelineBindingReady.snapshotToken),
        "R134 live PS binding drift invalidates pipeline binding snapshot");
    require(
        pipelineBundle.bind_for_observation(
            d3d.context, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityReady.snapshotToken),
        "R134 restore pipeline binding after drift probe");

    ID3D11SamplerState* clearDrawSampler = nullptr;
    ID3D11ShaderResourceView* clearDrawSrv = nullptr;
    d3d.context->PSSetSamplers(
        drawTextureStageSlot, 1, &clearDrawSampler);
    d3d.context->PSSetShaderResources(
        drawTextureStageSlot, 1, &clearDrawSrv);
    const auto missingTextureStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView);
    require(
        !missingTextureStageDraw.textureStageReady &&
        !missingTextureStageDraw.ready &&
        missingTextureStageDraw.snapshotToken == 0 &&
        !outrun::vr::dx11::validate_fixed_function_texture_stage_binding_snapshot(
            d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            drawTextureStageReady.snapshotToken) &&
        !outrun::vr::dx11::validate_fixed_function_textured_draw_snapshot(
            drawReady, d3d.context, drawTextureStageSlot, samplerOwner, textureView,
            texturedDrawReady.snapshotToken),
        "R132 textured draw readiness fails closed after PS binding drift");

    require(
        bind_fixed_function_texture_stage_for_observation(
            d3d.context, textureStageSlot, samplerOwner, textureView),
        "R133 wrong-stage binding prerequisite");
    const auto wrongTextureStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            drawReady, d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        wrongTextureStageDraw.textureStageReady &&
        !wrongTextureStageDraw.textureMaskMatches &&
        !wrongTextureStageDraw.inputValid &&
        !wrongTextureStageDraw.ready &&
        wrongTextureStageDraw.requiredTextureMask == 0x1u &&
        wrongTextureStageDraw.observedTextureMask ==
            (1u << textureStageSlot) &&
        wrongTextureStageDraw.snapshotToken == 0,
        "R133 textured draw rejects texture stage outside activation mask");

    auto forgedTextureMaskDraw = drawReady;
    forgedTextureMaskDraw.requiredTextureMask =
        (1u << textureStageSlot);
    const auto forgedTextureMaskTexturedDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            forgedTextureMaskDraw, d3d.context, textureStageSlot,
            samplerOwner, textureView);
    require(
        forgedTextureMaskTexturedDraw.textureStageReady &&
        forgedTextureMaskTexturedDraw.textureMaskMatches &&
        !outrun::vr::dx11::validate_fixed_function_draw_readiness_integrity(
            forgedTextureMaskDraw) &&
        !forgedTextureMaskTexturedDraw.drawReady &&
        !forgedTextureMaskTexturedDraw.ready &&
        forgedTextureMaskTexturedDraw.snapshotToken == 0,
        "R135 textured readiness rejects unsealed required-stage mask drift");

    auto multiStageDraw = drawReady;
    multiStageDraw.requiredTextureMask = 0x3u;
    const auto partialMultiStageDraw =
        outrun::vr::dx11::compose_fixed_function_textured_draw_readiness(
            multiStageDraw, d3d.context, textureStageSlot, samplerOwner, textureView);
    require(
        partialMultiStageDraw.textureStageReady &&
        !partialMultiStageDraw.textureMaskMatches &&
        !partialMultiStageDraw.drawReady &&
        !partialMultiStageDraw.ready &&
        partialMultiStageDraw.snapshotToken == 0,
        "R133 single-stage observer rejects multi-stage activation mask");

    auto activationMissingSnapshot = texturedActivation;
    activationMissingSnapshot.snapshotToken = 0;
    auto renderStateMissingSnapshot = outputBindingRenderReady;
    renderStateMissingSnapshot.snapshotToken = 0;
    auto renderStateNotReady = outputBindingRenderReady;
    renderStateNotReady.ready = false;
    auto surfacePairMissingSnapshot = surfacePairReady;
    surfacePairMissingSnapshot.snapshotToken = 0;
    auto surfacePairNotReady = surfacePairReady;
    surfacePairNotReady.ready = false;
    auto outputStateNotReady = outputStateReady;
    outputStateNotReady.ready = false;
    outputStateNotReady.snapshotToken = 0;
    NativeFixedFunctionOutputStateBinding missingDrawOutputBinding;

    const auto missingActivationDraw =
        compose_fixed_function_draw_readiness(
            activationMissingSnapshot, outputBindingRenderReady,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto missingRenderStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, renderStateMissingSnapshot,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingRenderStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, renderStateNotReady,
            surfacePairReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto missingSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            surfacePairMissingSnapshot, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            surfacePairNotReady, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    const auto pendingOutputStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateNotReady, outputStateBinding, indexedGeometryReady);
    const auto missingOutputBindingDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, missingDrawOutputBinding, indexedGeometryReady);
    auto geometryNotReady = indexedGeometryReady;
    geometryNotReady.ready = false;
    geometryNotReady.snapshotToken = 0;
    const auto pendingGeometryDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, geometryNotReady);
    require(
        !missingActivationDraw.ready &&
        missingActivationDraw.snapshotToken == 0 &&
        !missingRenderStateDraw.ready &&
        missingRenderStateDraw.snapshotToken == 0 &&
        !pendingRenderStateDraw.ready &&
        pendingRenderStateDraw.snapshotToken == 0 &&
        !missingSurfacePairDraw.ready &&
        missingSurfacePairDraw.snapshotToken == 0 &&
        !pendingSurfacePairDraw.ready &&
        pendingSurfacePairDraw.snapshotToken == 0 &&
        !pendingOutputStateDraw.ready &&
        pendingOutputStateDraw.snapshotToken == 0 &&
        !missingOutputBindingDraw.outputBindingReady &&
        !missingOutputBindingDraw.ready &&
        missingOutputBindingDraw.snapshotToken == 0 &&
        !pendingGeometryDraw.ready &&
        pendingGeometryDraw.snapshotToken == 0,
        "R131 draw readiness fails closed on missing binding evidence");

    auto changedRenderStateIdentity = outputBindingRenderReady;
    changedRenderStateIdentity.snapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto changedDrawReady =
        compose_fixed_function_draw_readiness(
            texturedActivation, changedRenderStateIdentity, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        !changedDrawReady.outputBindingReady &&
        !changedDrawReady.ready &&
        changedDrawReady.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, changedRenderStateIdentity, surfacePairReady,
            outputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw binding rejects render-state identity drift");

    auto changedSurfacePairIdentity = surfacePairReady;
    changedSurfacePairIdentity.snapshotToken ^= 0x100000001b3ull;
    const auto changedSurfacePairDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady,
            changedSurfacePairIdentity, outputStateReady, outputStateBinding,
            indexedGeometryReady);
    require(
        !changedSurfacePairDraw.outputBindingReady &&
        !changedSurfacePairDraw.ready &&
        changedSurfacePairDraw.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady,
            changedSurfacePairIdentity, outputStateReady, outputStateBinding,
            indexedGeometryReady, drawReady.snapshotToken),
        "R131 draw binding rejects surface-pair identity drift");

    const auto changedOutputStateDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            changedOutputStateReady, outputStateBinding, indexedGeometryReady);
    require(
        !changedOutputStateDraw.outputBindingReady &&
        !changedOutputStateDraw.ready &&
        changedOutputStateDraw.snapshotToken == 0 &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            changedOutputStateReady, outputStateBinding, indexedGeometryReady,
            drawReady.snapshotToken),
        "R131 draw binding rejects output-state identity drift");

    auto changedGeometryIdentity = indexedGeometryReady;
    changedGeometryIdentity.snapshotToken ^= 0x9e3779b97f4a7c15ull;
    const auto changedGeometryDraw =
        compose_fixed_function_draw_readiness(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity);
    require(
        changedGeometryDraw.outputBindingReady &&
        changedGeometryDraw.ready &&
        changedGeometryDraw.snapshotToken != 0 &&
        changedGeometryDraw.snapshotToken != drawReady.snapshotToken &&
        !validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity,
            drawReady.snapshotToken) &&
        validate_fixed_function_draw_snapshot(
            texturedActivation, outputBindingRenderReady, surfacePairReady,
            outputStateReady, outputStateBinding, changedGeometryIdentity,
            changedGeometryDraw.snapshotToken),
        "R122 draw snapshot changes with geometry identity; R131 draw snapshot still changes with independent geometry identity");

    DevicePair pipelineOtherDevice = create_warp_device();
    auto changedLayout = inputLayout;
    changedLayout.elements[0].SemanticIndex ^= 1u;
    auto changedStrideLayout = inputLayout;
    changedStrideLayout.stream0Stride -= 4u;
    auto changedVertexPrototype = vertexPrototype;
    changedVertexPrototype.sourceHash ^= 0x100000001b3ull;
    auto changedPixelPrototype = pixelPrototype;
    changedPixelPrototype.sourceHash ^= 0x9e3779b97f4a7c15ull;
    const auto pipelineForeignDevice =
        pipelineBundle.translation_readiness(
            pipelineOtherDevice.device, inputLayout,
            vertexPrototype, pixelPrototype);
    const auto pipelineChangedLayout =
        pipelineBundle.translation_readiness(
            d3d.device, changedLayout, vertexPrototype, pixelPrototype);
    const auto pipelineChangedStride =
        pipelineBundle.translation_readiness(
            d3d.device, changedStrideLayout, vertexPrototype, pixelPrototype);
    const auto pipelineChangedVertex =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, changedVertexPrototype, pixelPrototype);
    const auto pipelineChangedPixel =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, changedPixelPrototype);
    require(
        pipelineForeignDevice.inputValid &&
        pipelineForeignDevice.bundleReady &&
        !pipelineForeignDevice.deviceMatches &&
        !pipelineForeignDevice.ready &&
        pipelineForeignDevice.snapshotToken == 0 &&
        pipelineChangedLayout.inputValid &&
        !pipelineChangedLayout.inputLayoutMatches &&
        !pipelineChangedLayout.ready &&
        pipelineChangedLayout.snapshotToken == 0 &&
        pipelineChangedStride.inputValid &&
        !pipelineChangedStride.inputLayoutMatches &&
        !pipelineChangedStride.ready &&
        pipelineChangedStride.snapshotToken == 0 &&
        pipelineChangedVertex.inputValid &&
        !pipelineChangedVertex.vertexShaderMatches &&
        !pipelineChangedVertex.ready &&
        pipelineChangedVertex.snapshotToken == 0 &&
        pipelineChangedPixel.inputValid &&
        !pipelineChangedPixel.pixelShaderMatches &&
        !pipelineChangedPixel.ready &&
        pipelineChangedPixel.snapshotToken == 0,
        "R112 pipeline identity fails closed on device layout and shader provenance drift");
    pipelineOtherDevice.context->Release();
    pipelineOtherDevice.device->Release();

    const auto pipelineInitialToken = pipelineIdentityReady.snapshotToken;
    const auto pipelineInitialGeneration =
        pipelineIdentityReady.bundleGeneration;

    auto inexactLayout = inputLayout;
    inexactLayout.exact = false;
    require(
        !pipelineBundle.initialize(
            d3d.device, inexactLayout, vertexPrototype, pixelPrototype),
        "R97 inexact input layout must fail closed");
    require(
        !pipelineBundle.ready(),
        "R97 failed reinitialize must leave bundle dormant");
    require(
        pipelineBundle.initialize(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype),
        "R97 bundle reinitialize after fail-closed reset");
    require(
        pipelineBundle.ready(),
        "R97 bundle must recover after exact reinitialize");
    const auto pipelineIdentityRecreated =
        pipelineBundle.translation_readiness(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype);
    require(
        pipelineIdentityRecreated.ready &&
        pipelineIdentityRecreated.bundleGeneration >
            pipelineInitialGeneration &&
        pipelineIdentityRecreated.snapshotToken != 0 &&
        pipelineIdentityRecreated.snapshotToken != pipelineInitialToken &&
        !pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineInitialToken) &&
        pipelineBundle.validate_translation_snapshot(
            d3d.device, inputLayout, vertexPrototype, pixelPrototype,
            pipelineIdentityRecreated.snapshotToken),
        "R112 bundle recreation invalidates stale pipeline translation snapshot");

    D3D11_BUFFER_DESC observedDesc{};
    owner.buffer()->GetDesc(&observedDesc);
    require(
        observedDesc.ByteWidth == expectedConstantBytes &&
        observedDesc.Usage == D3D11_USAGE_DYNAMIC &&
        observedDesc.BindFlags == D3D11_BIND_CONSTANT_BUFFER &&
        observedDesc.CPUAccessFlags == D3D11_CPU_ACCESS_WRITE,
        "constant-buffer descriptor contract");

    // R151 negative control: a same-device deferred context can record VS b0,
    // but must never be accepted as the live immediate-context owner.
    ID3D11DeviceContext* r151DeferredContext = nullptr;
    require(
        SUCCEEDED(d3d.device->CreateDeferredContext(0, &r151DeferredContext)) &&
        r151DeferredContext != nullptr &&
        r151DeferredContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R151 WARP same-device deferred context prerequisite");
    require(
        !owner.upload_and_bind(r151DeferredContext, transform) &&
        owner.upload_generation() == 0,
        "R151 deferred WVP upload must fail closed without advancing generation");

    DevicePair otherDevice = create_warp_device();
    require(
        !owner.upload_and_bind(otherDevice.context, transform),
        "R96 foreign device context must fail closed");
    require(owner.upload_generation() == 0,
            "R96 failed upload must not advance generation");

    const auto incompleteTransform =
        generate_fixed_function_transform_constants(
            identity, identity, identity, false);
    require(
        !owner.upload_and_bind(d3d.context, incompleteTransform),
        "R96 inexact transform must fail closed");
    require(owner.upload_generation() == 0,
            "R96 inexact upload must not advance generation");

    require(
        owner.upload_and_bind(d3d.context, transform),
        "R96 owner upload and b0 bind");
    require(owner.upload_generation() == 1,
            "R96 successful upload generation");

    const auto r151ImmediateReceipt =
        owner.binding_readiness(d3d.context, transform);
    require(
        r151ImmediateReceipt.ready && r151ImmediateReceipt.snapshotToken != 0 &&
        owner.validate_binding_snapshot(
            d3d.context, transform, r151ImmediateReceipt.snapshotToken),
        "R151 WARP immediate WVP b0 receipt positive control");
    ID3D11Buffer* r151RecordedBuffer = owner.buffer();
    r151DeferredContext->VSSetConstantBuffers(0, 1, &r151RecordedBuffer);
    const auto r151DeferredReceipt =
        owner.binding_readiness(r151DeferredContext, transform);
    require(
        !r151DeferredReceipt.inputValid && !r151DeferredReceipt.ready &&
        r151DeferredReceipt.snapshotToken == 0 &&
        !owner.validate_binding_snapshot(
            r151DeferredContext, transform, r151ImmediateReceipt.snapshotToken) &&
        owner.validate_binding_snapshot(
            d3d.context, transform, r151ImmediateReceipt.snapshotToken),
        "R151 recorded same-device deferred VS b0 must not forge live WVP receipt");
    r151DeferredContext->Release();

    ID3D11Buffer* boundBuffer = nullptr;
    d3d.context->VSGetConstantBuffers(0, 1, &boundBuffer);
    require(
        boundBuffer != nullptr && boundBuffer == owner.buffer(),
        "VS b0 constant-buffer binding");
    if (boundBuffer)
        boundBuffer->Release();

    D3DMATRIX translatedWorld = world;
    translatedWorld._42 = 4.0f;
    const auto transform2 =
        generate_fixed_function_transform_constants(
            translatedWorld, view, identity, true);
    require(transform2.exact(), "R96 second transform prerequisite");
    require(
        owner.upload_and_bind(d3d.context, transform2),
        "R96 second owner upload");
    require(owner.upload_generation() == 2,
            "R96 upload generation must advance monotonically");

    ID3D11Buffer* nullBuffer = nullptr;
    d3d.context->VSSetConstantBuffers(0, 1, &nullBuffer);
    d3d.context->VSSetShader(nullptr, nullptr, 0);

    lockBridgeShadow.shutdown();
    require(
        !lockBridgeShadow.ready() &&
        !lockBridgeShadow.source_lock_active() &&
        !lockBridgeShadow.shadow_valid() &&
        !lockBridgeShadow.mirror_ready(),
        "R104 LockRect bridge shutdown clears capture and ownership");

    managedIndexBuffer.shutdown();
    managedVertexBuffer.shutdown();
    require(
        !managedIndexBuffer.ready() &&
        !managedIndexBuffer.shadow_valid() &&
        !managedIndexBuffer.mirror_ready() &&
        managedIndexBuffer.mirror_buffer() == nullptr &&
        !managedVertexBuffer.ready() &&
        !managedVertexBuffer.shadow_valid() &&
        !managedVertexBuffer.mirror_ready() &&
        managedVertexBuffer.mirror_buffer() == nullptr,
        "R113 managed buffer shutdown releases CPU/GPU ownership");

    managedShadow.shutdown();
    require(
        !managedShadow.ready() &&
        !managedShadow.shadow_valid() &&
        !managedShadow.mirror_ready() &&
        managedShadow.shadow_version() == 0 &&
        managedShadow.device_generation() == 1,
        "R102 managed shadow shutdown resets storage and lifetime");
    require(
        managedShadow.mirror_device() == nullptr &&
        managedShadow.mirror_texture() == nullptr &&
        managedShadow.mirror_srv() == nullptr,
        "R103 managed shadow shutdown resets CPU and GPU ownership");

    dynamicTextureView.shutdown();
    require(
        !dynamicTextureView.ready() &&
        !dynamicTextureView.content_ready() &&
        dynamicTextureView.upload_generation() == 0,
        "R101 dynamic texture shutdown resets ownership and content generation");

    textureView.shutdown();
    require(!textureView.ready(),
            "R99 texture view shutdown must release owner resources");
    require(
        textureView.device() == nullptr &&
        textureView.texture() == nullptr &&
        textureView.srv() == nullptr,
        "R99 texture view shutdown must clear owned objects");

    samplerOwner.shutdown();
    require(!samplerOwner.ready(),
            "R98 sampler shutdown must release owner resources");
    require(
        samplerOwner.device() == nullptr &&
        samplerOwner.sampler() == nullptr,
        "R98 sampler shutdown must clear owned objects");

    pipelineBundle.shutdown();
    require(!pipelineBundle.ready(),
            "R97 shutdown must release bundle resources");
    require(
        pipelineBundle.device() == nullptr &&
        pipelineBundle.vertex_shader() == nullptr &&
        pipelineBundle.pixel_shader() == nullptr &&
        pipelineBundle.input_layout() == nullptr &&
        !pipelineBundle.transform_buffer().ready(),
        "R97 shutdown must clear owned objects");

    owner.shutdown();
    require(!owner.ready(), "R96 shutdown must release owner resources");
    require(owner.buffer() == nullptr,
            "R96 shutdown must clear constant buffer");
    require(owner.upload_generation() == 0,
            "R96 shutdown must reset generation");

    require(owner.initialize(d3d.device),
            "R96 owner reinitialize after shutdown");
    require(owner.ready(), "R96 owner must be ready after reinitialize");
    owner.shutdown();

    stagingTexture->Release();
    dynamicTexture->Release();
    textureOtherDevice.context->Release();
    textureOtherDevice.device->Release();
    noSrvTexture->Release();
    fixedFunctionTexture->Release();
    otherDevice.context->Release();
    otherDevice.device->Release();
    isolationPredicate->Release();
    isolationStreamOutputBuffer->Release();
    isolationGeometryShader->Release();
    isolationGeometryBytecode->Release();
    vertexShader->Release();
    d3d.context->Release();
    d3d.device->Release();
    reflection->Release();
    vertexBytecode->Release();

    std::cout << "DX11 constant buffer probe R95: PASS\n";
    std::cout << "DX11 constant buffer lifetime R96: PASS\n";
    std::cout << "DX11 fixed-function pipeline bundle R97: PASS\n";
    std::cout << "DX11 dormant fixed-function pipeline object binding: PASS\n";
    std::cout << "DX11 fixed-function GS/HS/DS isolation R147: PASS\n";
    std::cout << "DX11 fixed-function SO/predication isolation R148: PASS\n";
    std::cout << "DX11 direct bound-buffer capacity R151: PASS\n";
    std::cout << "DX11 indexed source binding R153: PASS\n";
    std::cout << "DX11 indexed fan source content R155: PASS\n";
    std::cout << "DX11 indexed fan vertex capacity R156: PASS\n";
    std::cout << "DX11 indexed fan declared vertex range: PASS\n";
    std::cout << "DX11 indexed fan declared VB capacity R160: PASS\n";
    std::cout << "DX11 resource A2B10G10R10 exact mapping: PASS\n";
    std::cout << "DX11 direct line raster semantics R157: PASS\n";
    std::cout << "DX11 WARP fragment coverage R169: PASS\n";
    std::cout << "DX11 fixed-function sampler ownership R98: PASS\n";
    std::cout << "DX11 fixed-function texture view ownership R99: PASS\n";
    std::cout << "DX11 texture mutation readiness R100: PASS\n";
    std::cout << "DX11 fixed-function texture upload R101: PASS\n";
    std::cout << "DX11 managed texture shadow lifetime R102: PASS\n";
    std::cout << "DX11 managed texture mirror reupload R103: PASS\n";
    std::cout << "DX11 managed Texture2D LockRect bridge R104: PASS\n";
    std::cout << "DX11 managed Texture2D lifetime registry R105: PASS\n";
    std::cout << "DX11 managed Texture2D mutation-source completeness R107: PASS\n";
    std::cout << "DX11 managed Texture2D registry mirror readiness R108: PASS\n";
    std::cout << "DX11 managed Texture2D stage mirror readiness R109: PASS\n";
    std::cout << "DX11 managed Texture2D readiness snapshot token R110: PASS\n";
    std::cout << "DX11 managed Texture2D mirror descriptor exactness R111: PASS\n";
    std::cout << "DX11 fixed-function pipeline translation identity R112: PASS\n";
    std::cout << "DX11 managed vertex/index buffer mirror R113: PASS\n";
    std::cout << "DX11 managed buffer mirror readiness snapshot R119: PASS\n";
    std::cout << "DX11 fixed-function activation evidence composition R115: PASS\n";
    std::cout << "DX11 fixed-function render-state bundle R116: PASS\n";
    std::cout << "DX11 fixed-function draw readiness composition R120: PASS\n";
    std::cout << "DX11 draw output-binding readiness R131: PASS\n";
    std::cout << "DX11 final dormant bound-draw readiness R134: PASS\n";
    std::cout << "DX11 draw texture-mask snapshot integrity R135: PASS\n";
    std::cout << "DX11 aggregate texture binding readiness R136: PASS\n";
    std::cout << "DX11 geometry-gated draw readiness R122: PASS\n";
    std::cout << "DX11 dynamic output-state readiness R124: PASS\n";
    return 0;
}