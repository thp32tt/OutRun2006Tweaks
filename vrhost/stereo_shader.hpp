#pragma once

inline constexpr const char* OutRunStereoBlitShader = R"HLSL(
Texture2D SourceTexture : register(t0);
SamplerState SourceSampler : register(s0);

cbuffer BlitParams : register(b0)
{
    float2 UvScale;
    float2 UvOffset;
    float SdrWhiteScale;
    float SourceIsScRgb;
    float2 Padding;
};

struct VSOut
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
};

VSOut VSMain(uint id : SV_VertexID)
{
    VSOut o;
    float2 uv = float2((id << 1) & 2, id & 2);
    o.position = float4(uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
    o.uv = uv * UvScale + UvOffset;
    return o;
}

float3 SrgbToLinear(float3 c)
{
    return float3(
        c.r <= 0.04045 ? c.r / 12.92 : pow((c.r + 0.055) / 1.055, 2.4),
        c.g <= 0.04045 ? c.g / 12.92 : pow((c.g + 0.055) / 1.055, 2.4),
        c.b <= 0.04045 ? c.b / 12.92 : pow((c.b + 0.055) / 1.055, 2.4));
}

float4 PSMain(VSOut input) : SV_Target
{
    float4 src = SourceTexture.Sample(SourceSampler, input.uv);
    float3 linear;
    if (SourceIsScRgb > 0.5)
        linear = max(src.rgb, 0.0) / max(SdrWhiteScale, 0.001);
    else
        linear = SrgbToLinear(saturate(src.rgb));
    return float4(saturate(linear), 1.0);
}
)HLSL";
