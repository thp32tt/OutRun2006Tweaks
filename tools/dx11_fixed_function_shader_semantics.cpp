#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>

#include "vr/d3d11/pipeline_translation.hpp"
#include "vr/d3d11/state_translation.hpp"

namespace
{
    using outrun::vr::dx11::FixedFunctionAlphaTestState;
    using outrun::vr::dx11::FixedFunctionPixelShaderCompileProbe;
    using outrun::vr::dx11::FixedFunctionPixelShaderPrototype;
    using outrun::vr::dx11::FixedFunctionLightingState;
    using outrun::vr::dx11::FixedFunctionVertexShaderCompileProbe;
    using outrun::vr::dx11::FixedFunctionShaderPrototypeUnsupportedAlphaTestState;
    using outrun::vr::dx11::FixedFunctionShaderPrototypeUnsupportedNotReady;
    using outrun::vr::dx11::FixedFunctionShaderPrototypeUnsupportedResourceType;
    using outrun::vr::dx11::FixedFunctionStageState;
    using outrun::vr::dx11::FixedFunctionUnsupportedArgument;
    using outrun::vr::dx11::FixedFunctionUnsupportedSamplerAddress;
    using outrun::vr::dx11::FixedFunctionUnsupportedSamplerFilter;
    using outrun::vr::dx11::FixedFunctionUnsupportedSamplerLod;
    using outrun::vr::dx11::FixedFunctionUnsupportedSamplerSrgb;
    using outrun::vr::dx11::FixedFunctionUnsupportedResultArg;
    using outrun::vr::dx11::FixedFunctionUnsupportedStageChain;
    using outrun::vr::dx11::FixedFunctionUnsupportedTextureTransform;
    using outrun::vr::dx11::PipelineUnsupportedBlend;
    using outrun::vr::dx11::PipelineUnsupportedDualSourceBlend;
    using outrun::vr::dx11::PipelineUnsupportedLighting;
    using outrun::vr::dx11::PipelineUnsupportedSpecular;
    using outrun::vr::dx11::PipelineUnsupportedSeparateAlphaBlend;
    using outrun::vr::dx11::PipelineUnsupportedStencil;
    using outrun::vr::dx11::compile_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::compile_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::translate_pipeline;
    using outrun::vr::dx11::translate_primitive;
    using outrun::vr::dx11::translate_triangle_fan_expansion;
    using outrun::vr::dx11::triangle_fan_source_element;
    using outrun::vr::dx11::materialize_triangle_fan_vertex_indices;
    using outrun::vr::dx11::materialize_indexed_triangle_fan_indices;
    using outrun::vr::dx11::generate_fixed_function_pixel_shader_prototype;
    using outrun::vr::dx11::generate_fixed_function_vertex_shader_prototype;
    using outrun::vr::dx11::translate_fixed_function_readiness;
    using outrun::vr::dx11::translate_fixed_function_sampler;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R87 semantic smoke failure: " << message << '\n';
            std::exit(1);
        }
    }

    FixedFunctionStageState active_stage(
        DWORD colorOp,
        DWORD colorArg1,
        DWORD colorArg2,
        DWORD alphaOp,
        DWORD alphaArg1,
        DWORD alphaArg2,
        DWORD texCoordIndex)
    {
        FixedFunctionStageState stage{};
        stage.colorOp = colorOp;
        stage.colorArg1 = colorArg1;
        stage.colorArg2 = colorArg2;
        stage.alphaOp = alphaOp;
        stage.alphaArg1 = alphaArg1;
        stage.alphaArg2 = alphaArg2;
        stage.texCoordIndex = texCoordIndex;
        stage.textureTransformFlags = D3DTTFF_DISABLE;
        stage.minFilter = D3DTEXF_POINT;
        stage.magFilter = D3DTEXF_POINT;
        stage.mipFilter = D3DTEXF_NONE;
        stage.addressU = D3DTADDRESS_WRAP;
        stage.addressV = D3DTADDRESS_WRAP;
        return stage;
    }

    void require_compiles(
        const FixedFunctionPixelShaderPrototype& prototype,
        const char* label)
    {
        require(prototype.generated(), label);
        const FixedFunctionPixelShaderCompileProbe probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(probe.attempted, "compile probe was not attempted");
        require(probe.succeeded, "generated HLSL did not compile");
        require(probe.result == S_OK, "D3DCompile did not return S_OK");
        require(probe.bytecodeBytes > 0, "compiled bytecode is empty");
        require(probe.bytecodeHash != 0, "compiled bytecode hash is empty");
    }
}

int main()
{
    {
        const auto vertexPrototype =
            generate_fixed_function_vertex_shader_prototype(
                D3DFVF_XYZ | D3DFVF_DIFFUSE | D3DFVF_TEX1,
                24u,
                FixedFunctionLightingState{true, FALSE});
        require(vertexPrototype.generated(),
                "R223 generated vertex prototype missing");
        const FixedFunctionVertexShaderCompileProbe vertexProbe =
            compile_fixed_function_vertex_shader_prototype(vertexPrototype);
        require(vertexProbe.attempted,
                "R223 vertex compile probe was not attempted");
        require(vertexProbe.succeeded,
                "R223 generated vertex HLSL did not compile");
        require(vertexProbe.result == S_OK,
                "R223 vertex D3DCompile did not return S_OK");
        require(vertexProbe.bytecodeBytes > 0,
                "R223 compiled vertex bytecode is empty");
        require(vertexProbe.bytecodeHash != 0,
                "R223 compiled vertex bytecode hash is empty");

        auto rejectedVertexPrototype = vertexPrototype;
        rejectedVertexPrototype.unsupported =
            outrun::vr::dx11::
                FixedFunctionVertexShaderPrototypeUnsupportedInputLayout;
        const FixedFunctionVertexShaderCompileProbe rejectedVertexProbe =
            compile_fixed_function_vertex_shader_prototype(
                rejectedVertexPrototype);
        require(!rejectedVertexProbe.attempted,
                "R223 unsupported vertex compile probe must not be attempted");
        require(!rejectedVertexProbe.succeeded,
                "R223 unsupported vertex compile probe must fail closed");
        require(rejectedVertexProbe.result == E_FAIL,
                "R223 unsupported vertex compile result must remain E_FAIL");
        require(rejectedVertexProbe.bytecodeBytes == 0 &&
                    rejectedVertexProbe.bytecodeHash == 0,
                "R223 unsupported vertex compile must not retain bytecode");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;

        const auto baseline = translate_pipeline(state);
        require(
            (baseline.unsupported &
             (PipelineUnsupportedLighting | PipelineUnsupportedSpecular)) == 0,
            "default disabled specular state must remain exact");

        state.specularEnable = TRUE;
        const auto specular = translate_pipeline(state);
        require(
            (specular.unsupported & PipelineUnsupportedSpecular) != 0 &&
            (specular.unsupported & PipelineUnsupportedLighting) == 0 &&
            !specular.exact(),
            "R204 enabled D3DRS_SPECULARENABLE must use dedicated fail-closed blocker");

        state.lighting = TRUE;
        const auto lightingAndSpecular = translate_pipeline(state);
        require(
            (lightingAndSpecular.unsupported & PipelineUnsupportedLighting) != 0 &&
            (lightingAndSpecular.unsupported & PipelineUnsupportedSpecular) != 0,
            "R204 lighting and specular blockers must remain independently observable");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_BOTHSRCALPHA;
        state.destBlend = D3DBLEND_ZERO;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) == 0,
            "BOTHSRCALPHA source shortcut did not translate exactly");
        require(
            rt.SrcBlend == D3D11_BLEND_SRC_ALPHA &&
            rt.DestBlend == D3D11_BLEND_INV_SRC_ALPHA,
            "BOTHSRCALPHA did not override destination blend");
        require(
            rt.SrcBlendAlpha == D3D11_BLEND_SRC_ALPHA &&
            rt.DestBlendAlpha == D3D11_BLEND_INV_SRC_ALPHA,
            "BOTHSRCALPHA alpha factors drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_BOTHINVSRCALPHA;
        state.destBlend = D3DBLEND_ONE;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) == 0,
            "BOTHINVSRCALPHA source shortcut did not translate exactly");
        require(
            rt.SrcBlend == D3D11_BLEND_INV_SRC_ALPHA &&
            rt.DestBlend == D3D11_BLEND_SRC_ALPHA,
            "BOTHINVSRCALPHA did not override destination blend");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_SRCALPHA;
        state.destBlend = D3DBLEND_BOTHSRCALPHA;

        const auto translated = translate_pipeline(state);
        require(
            (translated.unsupported & PipelineUnsupportedBlend) != 0,
            "destination BOTHSRCALPHA must remain fail-closed");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_SRCCOLOR2;
        state.destBlend = D3DBLEND_ONE;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) != 0,
            "SRCCOLOR2 source blend must remain fail-closed without SV_Target1");
        require(
            (translated.unsupported & PipelineUnsupportedDualSourceBlend) != 0,
            "SRCCOLOR2 source blend must report dedicated dual-source blocker");
        require(
            rt.SrcBlend == D3D11_BLEND_SRC1_COLOR,
            "SRCCOLOR2 source blend mapping drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_INVSRCCOLOR2;
        state.destBlend = D3DBLEND_ONE;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) != 0,
            "INVSRCCOLOR2 source blend must remain fail-closed without SV_Target1");
        require(
            (translated.unsupported & PipelineUnsupportedDualSourceBlend) != 0,
            "INVSRCCOLOR2 source blend must report dedicated dual-source blocker");
        require(
            rt.SrcBlend == D3D11_BLEND_INV_SRC1_COLOR,
            "INVSRCCOLOR2 source blend mapping drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_ONE;
        state.destBlend = D3DBLEND_SRCCOLOR2;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) != 0,
            "SRCCOLOR2 destination blend must remain fail-closed without SV_Target1");
        require(
            (translated.unsupported & PipelineUnsupportedDualSourceBlend) != 0,
            "SRCCOLOR2 destination blend must report dedicated dual-source blocker");
        require(
            rt.DestBlend == D3D11_BLEND_SRC1_COLOR,
            "SRCCOLOR2 destination blend mapping drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_ONE;
        state.destBlend = D3DBLEND_INVSRCCOLOR2;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedBlend) != 0,
            "INVSRCCOLOR2 destination blend must remain fail-closed without SV_Target1");
        require(
            (translated.unsupported & PipelineUnsupportedDualSourceBlend) != 0,
            "INVSRCCOLOR2 destination blend must report dedicated dual-source blocker");
        require(
            rt.DestBlend == D3D11_BLEND_INV_SRC1_COLOR,
            "INVSRCCOLOR2 destination blend mapping drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = FALSE;
        state.srcBlend = D3DBLEND_SRCCOLOR2;
        state.destBlend = D3DBLEND_INVSRCCOLOR2;

        const auto translated = translate_pipeline(state);
        require(
            (translated.unsupported & PipelineUnsupportedDualSourceBlend) == 0 &&
            (translated.unsupported & PipelineUnsupportedBlend) == 0,
            "disabled alpha blending must ignore dormant dual-source factors");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_SRCALPHA;
        state.destBlend = D3DBLEND_INVSRCALPHA;
        state.separateAlphaBlendEnable = TRUE;
        state.srcBlendAlpha = D3DBLEND_SRCCOLOR;
        state.destBlendAlpha = D3DBLEND_INVDESTCOLOR;
        state.blendOpAlpha = D3DBLENDOP_REVSUBTRACT;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedSeparateAlphaBlend) == 0,
            "separate alpha blend did not translate exactly");
        require(
            rt.SrcBlendAlpha == D3D11_BLEND_SRC_ALPHA &&
            rt.DestBlendAlpha == D3D11_BLEND_INV_DEST_ALPHA &&
            rt.BlendOpAlpha == D3D11_BLEND_OP_REV_SUBTRACT,
            "separate alpha blend factors or operation drifted");
        require(
            rt.SrcBlend == D3D11_BLEND_SRC_ALPHA &&
            rt.DestBlend == D3D11_BLEND_INV_SRC_ALPHA,
            "separate alpha translation changed RGB blend factors");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = TRUE;
        state.separateAlphaBlendEnable = TRUE;
        state.srcBlendAlpha = D3DBLEND_BOTHSRCALPHA;

        const auto translated = translate_pipeline(state);
        require(
            (translated.unsupported & PipelineUnsupportedSeparateAlphaBlend) != 0,
            "legacy BOTH shortcut must fail closed in separate alpha state");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.alphaBlendEnable = FALSE;
        state.separateAlphaBlendEnable = TRUE;
        state.srcBlend = D3DBLEND_ONE;
        state.destBlend = D3DBLEND_ZERO;
        state.srcBlendAlpha = D3DBLEND_SRCCOLOR2;
        state.destBlendAlpha = D3DBLEND_INVSRCCOLOR2;

        const auto translated = translate_pipeline(state);
        const auto& rt = translated.blend.RenderTarget[0];
        require(
            (translated.unsupported & PipelineUnsupportedSeparateAlphaBlend) == 0,
            "disabled alpha blending must ignore separate alpha state");
        require(
            rt.SrcBlendAlpha == rt.SrcBlend &&
            rt.DestBlendAlpha == rt.DestBlend &&
            rt.BlendOpAlpha == rt.BlendOp,
            "disabled separate alpha state did not retain valid mirrored descriptor");
    }

    {
        const auto direct = translate_primitive(D3DPT_TRIANGLEFAN);
        require(
            !direct.exact &&
            direct.value == D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED,
            "triangle fan direct topology must remain fail-closed");

        const auto expansion = translate_triangle_fan_expansion(3u);
        require(expansion.exact, "triangle fan expansion was not exact");
        require(
            expansion.topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST,
            "triangle fan expansion did not target triangle list");
        require(
            expansion.sourceElementCount == 5u &&
            expansion.expandedIndexCount == 9u,
            "triangle fan expansion counts drifted");

        constexpr std::array<UINT, 9> expected{
            0u, 1u, 2u,
            0u, 2u, 3u,
            0u, 3u, 4u,
        };
        for (UINT expandedIndex = 0;
             expandedIndex < static_cast<UINT>(expected.size());
             ++expandedIndex)
        {
            UINT sourceElement = (std::numeric_limits<UINT>::max)();
            require(
                triangle_fan_source_element(
                    3u, expandedIndex, sourceElement),
                "triangle fan expansion source mapping rejected valid index");
            require(
                sourceElement == expected[expandedIndex],
                "triangle fan expansion source mapping drifted");
        }

        UINT sourceElement = 0u;
        require(
            !triangle_fan_source_element(3u, 9u, sourceElement),
            "triangle fan expansion accepted out-of-range index");

        std::array<UINT, 9> materialized{};
        require(
            materialize_triangle_fan_vertex_indices(
                3u, 7u, materialized.data(),
                static_cast<UINT>(materialized.size())),
            "triangle fan index stream materialization failed");
        constexpr std::array<UINT, 9> expectedMaterialized{
            7u, 8u, 9u,
            7u, 9u, 10u,
            7u, 10u, 11u,
        };
        require(
            materialized == expectedMaterialized,
            "triangle fan materialized index stream drifted");

        std::array<UINT, 9> untouched{};
        untouched.fill(0xA5A5A5A5u);
        const auto untouchedBefore = untouched;
        require(
            !materialize_triangle_fan_vertex_indices(
                3u, 7u, untouched.data(), 8u) &&
            untouched == untouchedBefore,
            "triangle fan short destination did not fail before writes");
        require(
            !materialize_triangle_fan_vertex_indices(
                3u, (std::numeric_limits<UINT>::max)() - 3u,
                untouched.data(), static_cast<UINT>(untouched.size())) &&
            untouched == untouchedBefore,
            "triangle fan base-vertex overflow did not fail before writes");
        require(
            materialize_triangle_fan_vertex_indices(
                0u, (std::numeric_limits<UINT>::max)(), nullptr, 0u),
            "zero-primitive triangle fan materialization must be empty-exact");

        constexpr std::array<WORD, 6> source16{
            0xFFFFu, 4u, 8u, 15u, 16u, 23u,
        };
        constexpr std::array<UINT, 9> expected16{
            4u, 8u, 15u,
            4u, 15u, 16u,
            4u, 16u, 23u,
        };
        std::array<UINT, 9> expanded16{};
        require(
            materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_INDEX16, 1u,
                source16.data(), static_cast<UINT>(source16.size()),
                expanded16.data(), static_cast<UINT>(expanded16.size())) &&
            expanded16 == expected16,
            "INDEX16 triangle fan did not preserve source indices");

        constexpr std::array<DWORD, 6> source32{
            0xDEADBEEFu, 70000u, 71000u, 72000u, 73000u, 74000u,
        };
        constexpr std::array<UINT, 9> expected32{
            70000u, 71000u, 72000u,
            70000u, 72000u, 73000u,
            70000u, 73000u, 74000u,
        };
        std::array<UINT, 9> expanded32{};
        require(
            materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_INDEX32, 1u,
                source32.data(), static_cast<UINT>(source32.size()),
                expanded32.data(), static_cast<UINT>(expanded32.size())) &&
            expanded32 == expected32,
            "INDEX32 triangle fan did not preserve 32-bit source indices");

        std::array<UINT, 9> indexedUntouched{};
        indexedUntouched.fill(0xCDCDCDCDu);
        const auto indexedUntouchedBefore = indexedUntouched;
        require(
            !materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_INDEX16, 2u,
                source16.data(), 6u,
                indexedUntouched.data(),
                static_cast<UINT>(indexedUntouched.size())) &&
            indexedUntouched == indexedUntouchedBefore,
            "indexed triangle fan short source did not fail before writes");
        require(
            !materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_INDEX16, 7u,
                source16.data(), static_cast<UINT>(source16.size()),
                indexedUntouched.data(),
                static_cast<UINT>(indexedUntouched.size())) &&
            indexedUntouched == indexedUntouchedBefore,
            "indexed triangle fan StartIndex overflow did not fail before writes");
        require(
            !materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_INDEX16, 1u,
                source16.data(), static_cast<UINT>(source16.size()),
                indexedUntouched.data(), 8u) &&
            indexedUntouched == indexedUntouchedBefore,
            "indexed triangle fan short destination did not fail before writes");
        require(
            !materialize_indexed_triangle_fan_indices(
                3u, D3DFMT_UNKNOWN, 1u,
                source16.data(), static_cast<UINT>(source16.size()),
                indexedUntouched.data(),
                static_cast<UINT>(indexedUntouched.size())) &&
            indexedUntouched == indexedUntouchedBefore,
            "indexed triangle fan accepted unsupported index format");
        require(
            materialize_indexed_triangle_fan_indices(
                0u, D3DFMT_INDEX16, (std::numeric_limits<UINT>::max)(),
                nullptr, 0u, nullptr, 0u),
            "zero-primitive indexed triangle fan must be empty-exact");

        require(
            !translate_triangle_fan_expansion(
                (std::numeric_limits<UINT>::max)()).exact,
            "triangle fan expansion overflow did not fail closed");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.stencilEnable = TRUE;
        state.stencilReadMask = 0x3Cu;
        state.stencilWriteMask = 0xA5u;
        state.stencilRef = 0x123u;
        state.stencilFail = D3DSTENCILOP_ZERO;
        state.stencilZFail = D3DSTENCILOP_INCRSAT;
        state.stencilPass = D3DSTENCILOP_REPLACE;
        state.stencilFunc = D3DCMP_GREATEREQUAL;

        const auto translated = translate_pipeline(state);
        const auto& ds = translated.depth_stencil;
        require(
            (translated.unsupported & PipelineUnsupportedStencil) == 0,
            "one-sided stencil did not translate exactly");
        require(
            ds.StencilReadMask == 0x3Cu &&
            ds.StencilWriteMask == 0xA5u &&
            translated.stencil_ref == 0x23u,
            "one-sided stencil masks/reference drifted");
        require(
            ds.FrontFace.StencilFailOp == D3D11_STENCIL_OP_ZERO &&
            ds.FrontFace.StencilDepthFailOp == D3D11_STENCIL_OP_INCR_SAT &&
            ds.FrontFace.StencilPassOp == D3D11_STENCIL_OP_REPLACE &&
            ds.FrontFace.StencilFunc == D3D11_COMPARISON_GREATER_EQUAL,
            "one-sided front-face stencil mapping drifted");
        require(
            ds.BackFace.StencilFailOp == ds.FrontFace.StencilFailOp &&
            ds.BackFace.StencilDepthFailOp == ds.FrontFace.StencilDepthFailOp &&
            ds.BackFace.StencilPassOp == ds.FrontFace.StencilPassOp &&
            ds.BackFace.StencilFunc == ds.FrontFace.StencilFunc,
            "one-sided stencil did not mirror front state to back face");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.cullMode = D3DCULL_NONE;
        state.stencilEnable = TRUE;
        state.twoSidedStencilMode = TRUE;
        state.stencilFail = D3DSTENCILOP_KEEP;
        state.stencilZFail = D3DSTENCILOP_INCR;
        state.stencilPass = D3DSTENCILOP_DECRSAT;
        state.stencilFunc = D3DCMP_LESS;
        state.ccwStencilFail = D3DSTENCILOP_REPLACE;
        state.ccwStencilZFail = D3DSTENCILOP_INVERT;
        state.ccwStencilPass = D3DSTENCILOP_DECR;
        state.ccwStencilFunc = D3DCMP_NOTEQUAL;

        const auto translated = translate_pipeline(state);
        const auto& ds = translated.depth_stencil;
        require(
            (translated.unsupported & PipelineUnsupportedStencil) == 0,
            "two-sided stencil did not translate exactly");
        require(
            ds.FrontFace.StencilDepthFailOp == D3D11_STENCIL_OP_INCR &&
            ds.FrontFace.StencilPassOp == D3D11_STENCIL_OP_DECR_SAT &&
            ds.FrontFace.StencilFunc == D3D11_COMPARISON_LESS,
            "clockwise/front stencil mapping drifted");
        require(
            ds.BackFace.StencilFailOp == D3D11_STENCIL_OP_REPLACE &&
            ds.BackFace.StencilDepthFailOp == D3D11_STENCIL_OP_INVERT &&
            ds.BackFace.StencilPassOp == D3D11_STENCIL_OP_DECR &&
            ds.BackFace.StencilFunc == D3D11_COMPARISON_NOT_EQUAL,
            "counterclockwise/back stencil mapping drifted");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.stencilEnable = TRUE;
        state.stencilFail = 0xFFFFFFFFu;

        const auto translated = translate_pipeline(state);
        require(
            (translated.unsupported & PipelineUnsupportedStencil) != 0,
            "invalid stencil op must fail closed");
    }

    {
        OutRunVR::DrawState::RenderStateSnapshot state{};
        state.complete = true;
        state.cullMode = D3DCULL_CCW;
        state.stencilEnable = TRUE;
        state.twoSidedStencilMode = TRUE;

        const auto translated = translate_pipeline(state);
        require(
            (translated.unsupported & PipelineUnsupportedStencil) != 0,
            "two-sided stencil with culling must fail closed");
    }

    std::array<D3DRESOURCETYPE, 8> textureTypes{};
    textureTypes.fill(D3DRTYPE_TEXTURE);

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes,
                FixedFunctionAlphaTestState{
                    true, TRUE, 128u, D3DCMP_GREATEREQUAL
                });
        require(
            prototype.generated(),
            "enabled alpha-test prototype was not generated");
        require(
            prototype.source.find(
                "const float alphaRef = (128.0f / 255.0f);") !=
                std::string::npos,
            "alpha-test reference normalization drifted");
        require(
            prototype.source.find(
                "if (!(current.a >= alphaRef)) discard;") !=
                std::string::npos,
            "alpha-test GREATEREQUAL semantic drift");
        require_compiles(prototype, "alpha-test GREATEREQUAL compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes,
                FixedFunctionAlphaTestState{
                    false, TRUE, 0u, D3DCMP_ALWAYS
                });
        require(
            !prototype.generated(),
            "incomplete alpha-test observation did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedAlphaTestState) != 0,
            "incomplete alpha-test observation missed blocker");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes,
                FixedFunctionAlphaTestState{
                    true, TRUE, 0u, 0xFFFFFFFFu
                });
        require(
            !prototype.generated(),
            "invalid alpha-test function did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedAlphaTestState) != 0,
            "invalid alpha-test function missed blocker");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes,
                FixedFunctionAlphaTestState{
                    true, FALSE, 255u, 0xFFFFFFFFu
                });
        require(
            prototype.generated(),
            "disabled alpha test incorrectly rejected irrelevant function");
        require(
            prototype.source.find("alphaRef") == std::string::npos &&
            prototype.source.find("discard;") == std::string::npos,
            "disabled alpha test injected pixel-kill semantics");
        require_compiles(prototype, "disabled alpha-test passthrough compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x00, 0x00);
        require(readiness.exact(), "zero-stage readiness was not exact");
        require(readiness.activeStages == 0, "zero-stage active count drift");

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(prototype.generated(), "zero-stage passthrough was not generated");
        require(prototype.activeStages == 0, "zero-stage prototype count drift");
        require(
            prototype.source.find("Texture2D texture") == std::string::npos,
            "zero-stage shader emitted a texture declaration");
        require(
            prototype.source.find("return current;") != std::string::npos,
            "zero-stage shader did not return diffuse current");
        require_compiles(prototype, "zero-stage passthrough compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(prototype.generated(), "diffuse passthrough was not generated");
        require(
            prototype.source.find(
                "float3 nextColor = input.diffuse.rgb;") != std::string::npos,
            "diffuse color semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = input.diffuse.a;") != std::string::npos,
            "diffuse alpha semantic drift");
        require(
            prototype.source.find("Texture2D texture") == std::string::npos,
            "texture declaration emitted for texture-free stage");
        require_compiles(prototype, "diffuse passthrough compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(prototype.generated(), "single texture modulate was not generated");
        require(
            prototype.source.find(
                "float4 sampled0 = texture0.Sample(sampler0, input.tex0.xy);") !=
                std::string::npos,
            "stage0 texture sample semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = sampled0.rgb * input.diffuse.rgb;") !=
                std::string::npos,
            "stage0 modulate semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = sampled0.a;") != std::string::npos,
            "stage0 texture alpha semantic drift");
        require_compiles(prototype, "single texture modulate compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[1] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG1,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            1);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x03, 0x03, textureTypes);
        require(prototype.generated(), "two-stage chain was not generated");
        require(
            prototype.source.find(
                "float4 sampled1 = texture1.Sample(sampler1, input.tex1.xy);") !=
                std::string::npos,
            "stage1 texture sample semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = current.rgb * sampled1.rgb;") !=
                std::string::npos,
            "stage1 CURRENT chaining semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = current.a;") != std::string::npos,
            "stage1 CURRENT alpha semantic drift");
        require_compiles(prototype, "two-stage chain compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_TEXTURE,
            D3DTA_DIFFUSE,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[1] = active_stage(
            D3DTOP_MODULATE,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG1,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            1);
        stages[2] = active_stage(
            D3DTOP_SELECTARG2,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            D3DTOP_SELECTARG2,
            D3DTA_CURRENT,
            D3DTA_TEXTURE,
            5);
        stages[2].minFilter = D3DTEXF_LINEAR;
        stages[2].magFilter = D3DTEXF_LINEAR;
        stages[2].mipFilter = D3DTEXF_LINEAR;
        stages[2].addressU = D3DTADDRESS_CLAMP;
        stages[2].addressV = D3DTADDRESS_CLAMP;

        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x07, 0x07);
        require(readiness.exact(), "stage2 SELECTARG2 readiness was not exact");
        require(readiness.activeStages == 3, "stage2 active count drift");

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x07, 0x07, textureTypes);
        require(prototype.generated(), "stage2 SELECTARG2 chain was not generated");
        require(
            prototype.source.find(
                "Texture2D texture2 : register(t2);") != std::string::npos,
            "stage2 texture register semantic drift");
        require(
            prototype.source.find(
                "float4 sampled2 = texture2.Sample(sampler2, input.tex5.xy);") !=
                std::string::npos,
            "stage2 nonmatching texcoord semantic drift");
        require(
            prototype.source.find(
                "float3 nextColor = sampled2.rgb;") != std::string::npos,
            "stage2 SELECTARG2 color semantic drift");
        require(
            prototype.source.find(
                "float nextAlpha = sampled2.a;") != std::string::npos,
            "stage2 SELECTARG2 alpha semantic drift");
        require_compiles(prototype, "stage2 SELECTARG2 chain compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].addressU = D3DTADDRESS_MIRROR;
        stages[0].addressV = D3DTADDRESS_MIRRORONCE;

        const auto mirrorReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        const auto mirrorSampler =
            translate_fixed_function_sampler(stages[0]);
        require(
            mirrorReadiness.exact(),
            "R159 mirror sampler addressing readiness was not exact");
        require(
            mirrorSampler.exact &&
            mirrorSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_MIRROR &&
            mirrorSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_MIRROR_ONCE,
            "R159 mirror sampler address translation drift");

        stages[0].addressU = D3DTADDRESS_BORDER;
        stages[0].borderColor = 0x80402010u;
        const auto borderReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        const auto borderSampler =
            translate_fixed_function_sampler(stages[0]);
        require(
            borderReadiness.exact(),
            "R160 border sampler addressing readiness was not exact");
        require(
            borderSampler.exact &&
            borderSampler.desc.AddressU == D3D11_TEXTURE_ADDRESS_BORDER &&
            borderSampler.desc.AddressV == D3D11_TEXTURE_ADDRESS_MIRROR_ONCE &&
            borderSampler.desc.BorderColor[0] == 64.0f / 255.0f &&
            borderSampler.desc.BorderColor[1] == 32.0f / 255.0f &&
            borderSampler.desc.BorderColor[2] == 16.0f / 255.0f &&
            borderSampler.desc.BorderColor[3] == 128.0f / 255.0f,
            "R160 border sampler ARGB to RGBA translation drift");

        stages[0].srgbTexture = TRUE;
        const auto srgbReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        const auto srgbSampler =
            translate_fixed_function_sampler(stages[0]);
        require(
            !srgbReadiness.exact(),
            "sampler sRGB decode did not fail closed");
        require(
            (srgbReadiness.unsupported &
             FixedFunctionUnsupportedSamplerSrgb) != 0,
            "sampler sRGB decode did not set blocker");
        require(
            !srgbSampler.exact,
            "sampler sRGB decode unexpectedly translated without sRGB SRV");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);
        const auto currentResult =
            translate_fixed_function_readiness(stages, true, 0x00, 0x00);
        require(currentResult.exact(),
                "RESULTARG-001 default CURRENT result routing must remain exact");

        stages[0].resultArg = D3DTA_TEMP;
        stages[1] = active_stage(
            D3DTOP_ADD,
            D3DTA_TEMP,
            D3DTA_CURRENT,
            D3DTOP_ADD,
            D3DTA_TEMP,
            D3DTA_CURRENT,
            1);
        const auto tempResult =
            translate_fixed_function_readiness(stages, true, 0x00, 0x00);
        require(tempResult.exact(),
                "RESULTARG-001 initialized TEMP routing must remain exact");
        const auto tempPrototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(
            tempPrototype.generated() &&
            tempPrototype.source.find(
                "temp = float4(nextColor, nextAlpha);") != std::string::npos &&
            tempPrototype.source.find(
                "float3 nextColor = temp.rgb + current.rgb;") != std::string::npos,
            "RESULTARG-001 initialized TEMP routing shader dataflow drift");

        auto uninitializedTemp = stages;
        uninitializedTemp[0].resultArg = D3DTA_CURRENT;
        uninitializedTemp[0].colorArg1 = D3DTA_TEMP;
        uninitializedTemp[0].alphaArg1 = D3DTA_TEMP;
        uninitializedTemp[1].colorOp = D3DTOP_DISABLE;
        uninitializedTemp[1].alphaOp = D3DTOP_DISABLE;
        const auto uninitializedResult =
            translate_fixed_function_readiness(
                uninitializedTemp, true, 0x00, 0x00);
        require(
            uninitializedResult.exact() &&
            (uninitializedResult.unsupported &
             FixedFunctionUnsupportedResultArg) == 0,
            "RESULTARG-001 default-zero TEMP read must remain exact");
        const auto uninitializedPrototype =
            generate_fixed_function_pixel_shader_prototype(
                uninitializedTemp, true, 0x00, 0x00, textureTypes);
        require(
            uninitializedPrototype.generated() &&
            uninitializedPrototype.source.find("float4 temp = 0.0f;") !=
                std::string::npos &&
            uninitializedPrototype.source.find(
                "float3 nextColor = temp.rgb;") != std::string::npos &&
            uninitializedPrototype.source.find(
                "float nextAlpha = temp.a;") != std::string::npos,
            "RESULTARG-001 default-zero TEMP shader semantics drift");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[1] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            1);
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x00, 0x00);
        require(!readiness.exact(), "stage-chain hole did not fail closed");
        require(
            (readiness.unsupported & FixedFunctionUnsupportedStageChain) != 0,
            "stage-chain hole did not set stage-chain blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x00, 0x00, textureTypes);
        require(!prototype.generated(), "stage-chain hole generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE | D3DTA_COMPLEMENT,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_DIFFUSE,
            D3DTA_CURRENT,
            0);
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(
            readiness.exact(),
            "R178 complement argument modifier must remain exact");
        require(
            (readiness.unsupported & FixedFunctionUnsupportedArgument) == 0,
            "R178 complement argument modifier retained argument blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(
            prototype.generated() &&
            prototype.source.find("(1.0 - sampled0.rgb)") !=
                std::string::npos,
            "R178 complement argument modifier shader semantics drift");
        require_compiles(
            prototype,
            "R178 complement argument modifier HLSL did not compile");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].textureTransformFlags = D3DTTFF_COUNT2;
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(!readiness.exact(), "texture transform did not fail closed");
        require(
            (readiness.unsupported &
             FixedFunctionUnsupportedTextureTransform) != 0,
            "texture transform did not set transform blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(!prototype.generated(), "texture transform generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].mipFilter = D3DTEXF_LINEAR;
        stages[0].mipLodBiasBits = 0x3F000000u;
        stages[0].maxMipLevel = 1u;
        const auto translatedReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(
            translatedReadiness.exact(),
            "sampler LOD bias/MAXMIPLEVEL did not translate exactly");
        require(
            (translatedReadiness.unsupported &
             FixedFunctionUnsupportedSamplerLod) == 0,
            "translated sampler LOD state retained blocker");

        stages[0].mipLodBiasBits = 0x41800000u;
        const auto outOfRangeBiasReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(
            !outOfRangeBiasReadiness.exact(),
            "out-of-range sampler LOD bias did not fail closed");
        require(
            (outOfRangeBiasReadiness.unsupported &
             FixedFunctionUnsupportedSamplerLod) != 0,
            "out-of-range sampler LOD bias did not set blocker");

        stages[0].mipLodBiasBits = 0;
        stages[0].maxMipLevel = D3D11_REQ_MIP_LEVELS;
        const auto outOfRangeMaxMipReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(
            !outOfRangeMaxMipReadiness.exact(),
            "out-of-range sampler MAXMIPLEVEL did not fail closed");

        stages[0].mipFilter = D3DTEXF_NONE;
        stages[0].maxMipLevel = 1u;
        const auto noMipNonDefaultReadiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(
            !noMipNonDefaultReadiness.exact(),
            "no-mip non-default sampler LOD state did not fail closed");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        stages[0].minFilter = D3DTEXF_ANISOTROPIC;
        const auto readiness =
            translate_fixed_function_readiness(
                stages, true, 0x01, 0x01);
        require(!readiness.exact(), "anisotropic sampler did not fail closed");
        require(
            (readiness.unsupported &
             FixedFunctionUnsupportedSamplerFilter) != 0,
            "anisotropic sampler did not set sampler-filter blocker");
        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, textureTypes);
        require(!prototype.generated(), "anisotropic sampler generated HLSL");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x00, textureTypes);
        require(!prototype.generated(), "missing exact resource did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedNotReady) != 0,
            "missing exact resource did not set not-ready blocker");
        const auto probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(!probe.attempted, "compile probe ran for fail-closed prototype");
    }

    {
        std::array<FixedFunctionStageState, 8> stages{};
        stages[0] = active_stage(
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            D3DTOP_SELECTARG1,
            D3DTA_TEXTURE,
            D3DTA_CURRENT,
            0);
        auto cubeTypes = textureTypes;
        cubeTypes[0] = D3DRTYPE_CUBETEXTURE;

        const auto prototype =
            generate_fixed_function_pixel_shader_prototype(
                stages, true, 0x01, 0x01, cubeTypes);
        require(!prototype.generated(), "cube texture did not fail closed");
        require(
            (prototype.unsupported &
             FixedFunctionShaderPrototypeUnsupportedResourceType) != 0,
            "cube texture did not set resource-type blocker");
        const auto probe =
            compile_fixed_function_pixel_shader_prototype(prototype);
        require(!probe.attempted, "compile probe ran for unsupported resource type");
    }

    std::cout << "DX11 fixed-function shader semantics smoke R87: PASS\n";
    return 0;
}
