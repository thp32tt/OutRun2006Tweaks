#pragma once

// R21: BlitParams is intentionally consumed by PSMain. The host RenderTo()
// path already binds b0 to the pixel shader, while R20 never bound it to VS.
// Keeping the fullscreen-triangle VS free of constant-buffer dependencies makes
// the core compositor deterministic and removes the all-black single-sample UV
// failure mode without relying on inherited VS bindings.
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

cbuffer MenuPlaneParams : register(b1)
{
    float4 MenuClip[4];
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
    o.uv = uv;
    return o;
}

VSOut VSMenu(uint id : SV_VertexID)
{
    VSOut o;
    const uint corner = min(id, 3u);
    o.position = MenuClip[corner];
    o.uv = float2((corner & 1u) ? 1.0 : 0.0,
                  (corner & 2u) ? 1.0 : 0.0);
    return o;
}

float3 SrgbToLinear(float3 c)
{
    return float3(
        c.r <= 0.04045 ? c.r / 12.92 : pow((c.r + 0.055) / 1.055, 2.4),
        c.g <= 0.04045 ? c.g / 12.92 : pow((c.g + 0.055) / 1.055, 2.4),
        c.b <= 0.04045 ? c.b / 12.92 : pow((c.b + 0.055) / 1.055, 2.4));
}

float3 LinearSourceAt(float2 uv)
{
    float4 src = SourceTexture.Sample(SourceSampler, uv);
    if (SourceIsScRgb > 0.5)
        return max(src.rgb, 0.0) / max(SdrWhiteScale, 0.001);
    return SrgbToLinear(saturate(src.rgb));
}

float4 PSMain(VSOut input) : SV_Target
{
    const float2 sampleUv = input.uv * UvScale + UvOffset;
    float3 linearColor = LinearSourceAt(sampleUv);

    // Reference-stack sharpening. The game image may be scaled independently
    // from the OpenXR projection target. A compact 5-tap local-contrast pass
    // restores edge definition without adding another intermediate texture.
    // Padding.x is the host sharpening strength; zero preserves the old path.
    const float sharpen = saturate(Padding.x);
    if (sharpen > 0.0001)
    {
        uint sourceWidth = 1, sourceHeight = 1;
        SourceTexture.GetDimensions(sourceWidth, sourceHeight);
        const float2 texel = 1.0 / float2(max(sourceWidth, 1u), max(sourceHeight, 1u));
        const float2 uvMin = UvOffset + texel * 0.5;
        const float2 uvMax = UvOffset + UvScale - texel * 0.5;

        const float3 n = LinearSourceAt(clamp(sampleUv + float2(0, -texel.y), uvMin, uvMax));
        const float3 s = LinearSourceAt(clamp(sampleUv + float2(0,  texel.y), uvMin, uvMax));
        const float3 e = LinearSourceAt(clamp(sampleUv + float2( texel.x, 0), uvMin, uvMax));
        const float3 w = LinearSourceAt(clamp(sampleUv + float2(-texel.x, 0), uvMin, uvMax));
        const float3 local = (n + s + e + w) * 0.25;
        const float3 detail = linearColor - local;

        // Reduce sharpening near strong local excursions to limit halos.
        const float peak = max(abs(detail.r), max(abs(detail.g), abs(detail.b)));
        const float adaptive = sharpen / (1.0 + peak * 6.0);
        linearColor += detail * adaptive;
    }
    return float4(saturate(linearColor), 1.0);
}
)HLSL";
