#pragma once

// FSR 1 EASU/RCAS adaptation for the OutRun D3D11 OpenXR host.
// Based on AMD FidelityFX Super Resolution 1 reference concepts and the
// NFSHeatVR adaptation. AMD FidelityFX FSR is MIT licensed.
//
// This POC deliberately applies FSR only to the DirectGPU eye transport.
// OpenXR projection swapchains remain at the runtime-recommended size.

inline constexpr const char* OutRunFsr1EasuShader = R"HLSL(
Texture2D SourceTexture : register(t0);
SamplerState SourceSampler : register(s0);

cbuffer FsrEasuParams : register(b0)
{
    float4 EasuCon0;
    float4 EasuCon1;
    float4 EasuCon2;
    float4 EasuCon3;
    float SdrWhiteScale;
    float SourceIsScRgb;
    float2 Padding;
};

void EasuTap(inout float3 colour, inout float weight,
             float2 offset, float2 direction, float2 length,
             float lobe, float clipping, float3 sampleColour)
{
    float2 rotated;
    rotated.x = offset.x * direction.x + offset.y * direction.y;
    rotated.y = offset.x * -direction.y + offset.y * direction.x;
    rotated *= length;
    const float distanceSquared = min(dot(rotated, rotated), clipping);
    float base = 0.4 * distanceSquared - 1.0;
    float window = lobe * distanceSquared - 1.0;
    base *= base;
    window *= window;
    base = 1.5625 * base - 0.5625;
    const float tapWeight = base * window;
    colour += sampleColour * tapWeight;
    weight += tapWeight;
}

void EasuSet(inout float2 direction, inout float edgeLength,
             float bilinearWeight,
             float lumaA, float lumaB, float lumaC,
             float lumaD, float lumaE)
{
    const float dc = lumaD - lumaC;
    const float cb = lumaC - lumaB;
    const float directionX = lumaD - lumaB;
    const float lengthX =
        saturate(abs(directionX) / max(max(abs(dc), abs(cb)), 1e-6));
    direction.x += directionX * bilinearWeight;
    edgeLength += lengthX * lengthX * bilinearWeight;

    const float ec = lumaE - lumaC;
    const float ca = lumaC - lumaA;
    const float directionY = lumaE - lumaA;
    const float lengthY =
        saturate(abs(directionY) / max(max(abs(ec), abs(ca)), 1e-6));
    direction.y += directionY * bilinearWeight;
    edgeLength += lengthY * lengthY * bilinearWeight;
}

float3 SrgbToLinear(float3 c)
{
    return float3(
        c.r <= 0.04045 ? c.r / 12.92 : pow((c.r + 0.055) / 1.055, 2.4),
        c.g <= 0.04045 ? c.g / 12.92 : pow((c.g + 0.055) / 1.055, 2.4),
        c.b <= 0.04045 ? c.b / 12.92 : pow((c.b + 0.055) / 1.055, 2.4));
}

float3 FinalizeSourceColour(float3 c)
{
    if (SourceIsScRgb > 0.5)
        return max(c, 0.0) / max(SdrWhiteScale, 0.001);
    return SrgbToLinear(saturate(c));
}

float3 FsrEasu(uint2 outputPixel)
{
    const float2 pixelPosition =
        float2(outputPixel) * EasuCon0.xy + EasuCon0.zw;
    const float2 integerPosition = floor(pixelPosition);
    const float2 fractionalPosition = pixelPosition - integerPosition;
    const float2 gatherPosition =
        integerPosition * EasuCon1.xy + EasuCon1.zw;

    const float2 gatherPosition1 = gatherPosition + EasuCon2.xy;
    const float2 gatherPosition2 = gatherPosition + EasuCon2.zw;
    const float2 gatherPosition3 = gatherPosition + EasuCon3.xy;

    const float4 bczzR = SourceTexture.GatherRed(SourceSampler, gatherPosition);
    const float4 bczzG = SourceTexture.GatherGreen(SourceSampler, gatherPosition);
    const float4 bczzB = SourceTexture.GatherBlue(SourceSampler, gatherPosition);
    const float4 ijfeR = SourceTexture.GatherRed(SourceSampler, gatherPosition1);
    const float4 ijfeG = SourceTexture.GatherGreen(SourceSampler, gatherPosition1);
    const float4 ijfeB = SourceTexture.GatherBlue(SourceSampler, gatherPosition1);
    const float4 klhgR = SourceTexture.GatherRed(SourceSampler, gatherPosition2);
    const float4 klhgG = SourceTexture.GatherGreen(SourceSampler, gatherPosition2);
    const float4 klhgB = SourceTexture.GatherBlue(SourceSampler, gatherPosition2);
    const float4 zzonR = SourceTexture.GatherRed(SourceSampler, gatherPosition3);
    const float4 zzonG = SourceTexture.GatherGreen(SourceSampler, gatherPosition3);
    const float4 zzonB = SourceTexture.GatherBlue(SourceSampler, gatherPosition3);

    const float4 bczzL = bczzB * 0.5 + (bczzR * 0.5 + bczzG);
    const float4 ijfeL = ijfeB * 0.5 + (ijfeR * 0.5 + ijfeG);
    const float4 klhgL = klhgB * 0.5 + (klhgR * 0.5 + klhgG);
    const float4 zzonL = zzonB * 0.5 + (zzonR * 0.5 + zzonG);

    const float bL = bczzL.x, cL = bczzL.y;
    const float iL = ijfeL.x, jL = ijfeL.y;
    const float fL = ijfeL.z, eL = ijfeL.w;
    const float kL = klhgL.x, lL = klhgL.y;
    const float hL = klhgL.z, gL = klhgL.w;
    const float oL = zzonL.z, nL = zzonL.w;

    float2 direction = float2(0.0, 0.0);
    float edgeLength = 0.0;
    EasuSet(direction, edgeLength,
        (1.0 - fractionalPosition.x) * (1.0 - fractionalPosition.y),
        bL, eL, fL, gL, jL);
    EasuSet(direction, edgeLength,
        fractionalPosition.x * (1.0 - fractionalPosition.y),
        cL, fL, gL, hL, kL);
    EasuSet(direction, edgeLength,
        (1.0 - fractionalPosition.x) * fractionalPosition.y,
        fL, iL, jL, kL, nL);
    EasuSet(direction, edgeLength,
        fractionalPosition.x * fractionalPosition.y,
        gL, jL, kL, lL, oL);

    const float directionLengthSquared = dot(direction, direction);
    if (directionLengthSquared < 1.0 / 32768.0)
        direction = float2(1.0, 0.0);
    else
        direction *= rsqrt(directionLengthSquared);

    edgeLength *= 0.5;
    edgeLength *= edgeLength;
    const float stretch =
        dot(direction, direction) /
        max(max(abs(direction.x), abs(direction.y)), 1e-6);
    const float2 anisotropicLength =
        float2(1.0 + (stretch - 1.0) * edgeLength,
               1.0 - 0.5 * edgeLength);
    const float lobe = 0.5 + (0.21 - 0.5) * edgeLength;
    const float clipping = 1.0 / lobe;

    const float3 min4 = min(
        min(float3(ijfeR.z, ijfeG.z, ijfeB.z),
            float3(klhgR.w, klhgG.w, klhgB.w)),
        min(float3(ijfeR.y, ijfeG.y, ijfeB.y),
            float3(klhgR.x, klhgG.x, klhgB.x)));
    const float3 max4 = max(
        max(float3(ijfeR.z, ijfeG.z, ijfeB.z),
            float3(klhgR.w, klhgG.w, klhgB.w)),
        max(float3(ijfeR.y, ijfeG.y, ijfeB.y),
            float3(klhgR.x, klhgG.x, klhgB.x)));

    float3 accumulatedColour = float3(0.0, 0.0, 0.0);
    float accumulatedWeight = 0.0;
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(0.0, -1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(bczzR.x, bczzG.x, bczzB.x));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(1.0, -1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(bczzR.y, bczzG.y, bczzB.y));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(-1.0, 1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(ijfeR.x, ijfeG.x, ijfeB.x));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(0.0, 1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(ijfeR.y, ijfeG.y, ijfeB.y));
    EasuTap(accumulatedColour, accumulatedWeight,
        -fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(ijfeR.z, ijfeG.z, ijfeB.z));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(-1.0, 0.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(ijfeR.w, ijfeG.w, ijfeB.w));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(1.0, 1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(klhgR.x, klhgG.x, klhgB.x));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(2.0, 1.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(klhgR.y, klhgG.y, klhgB.y));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(2.0, 0.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(klhgR.z, klhgG.z, klhgB.z));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(1.0, 0.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(klhgR.w, klhgG.w, klhgB.w));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(1.0, 2.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(zzonR.z, zzonG.z, zzonB.z));
    EasuTap(accumulatedColour, accumulatedWeight,
        float2(0.0, 2.0) - fractionalPosition,
        direction, anisotropicLength, lobe, clipping,
        float3(zzonR.w, zzonG.w, zzonB.w));

    const float3 perceptual = clamp(
        accumulatedColour / max(accumulatedWeight, 1e-6),
        min4, max4);
    return FinalizeSourceColour(perceptual);
}

float4 PSFsrEasu(float4 position : SV_Position) : SV_Target
{
    return float4(FsrEasu(uint2(position.xy)), 1.0);
}
)HLSL";

inline constexpr const char* OutRunFsr1RcasShader = R"HLSL(
Texture2D SourceTexture : register(t0);

cbuffer FsrRcasParams : register(b0)
{
    float Attenuation;
    float OutputWidth;
    float OutputHeight;
    float Padding;
};

float3 LoadSource(int2 position)
{
    const int2 size = int2(OutputWidth, OutputHeight);
    return SourceTexture.Load(int3(
        clamp(position, int2(0, 0), size - int2(1, 1)), 0)).rgb;
}

float3 FsrRcas(uint2 outputPixel)
{
    const int2 pixel = int2(outputPixel);
    const float3 b = LoadSource(pixel + int2( 0,-1));
    const float3 d = LoadSource(pixel + int2(-1, 0));
    const float3 e = LoadSource(pixel);
    const float3 f = LoadSource(pixel + int2( 1, 0));
    const float3 h = LoadSource(pixel + int2( 0, 1));

    const float lumaB = b.b * 0.5 + (b.r * 0.5 + b.g);
    const float lumaD = d.b * 0.5 + (d.r * 0.5 + d.g);
    const float lumaE = e.b * 0.5 + (e.r * 0.5 + e.g);
    const float lumaF = f.b * 0.5 + (f.r * 0.5 + f.g);
    const float lumaH = h.b * 0.5 + (h.r * 0.5 + h.g);

    const float lumaRange =
        max(max(max(lumaB, lumaD), max(lumaE, lumaF)), lumaH) -
        min(min(min(lumaB, lumaD), min(lumaE, lumaF)), lumaH);
    const float noise =
        1.0 - 0.5 * saturate(
            abs(0.25 * (lumaB + lumaD + lumaF + lumaH) - lumaE) /
            (lumaRange + 1e-6));

    const float3 min4 = min(min(b, d), min(f, h));
    const float3 max4 = max(max(b, d), max(f, h));
    const float3 hitMin = min(min4, e) / max(4.0 * max4, 1e-6);
    const float3 hitMax =
        (1.0 - max(max4, e)) /
        min(4.0 * min4 - 4.0, -1e-6);
    const float lobe =
        max(-0.1875,
            min(max(max(-hitMin, hitMax).r,
                    max(-hitMin, hitMax).g),
                max(-hitMin, hitMax).b)) *
            exp2(-Attenuation) * noise;

    return (lobe * (b + d + f + h) + e) /
        (4.0 * lobe + 1.0);
}

float4 PSFsrRcas(float4 position : SV_Position) : SV_Target
{
    return float4(saturate(FsrRcas(uint2(position.xy))), 1.0);
}
)HLSL";
