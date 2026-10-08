#include "vr/d3d11/triangle_fan_index_buffer.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>
#include <wrl/client.h>

namespace {

using Microsoft::WRL::ComPtr;
using outrun::vr::dx11::NativeTriangleFanIndexBuffer;

[[noreturn]] void fail(const char* message) {
    std::cerr << "DX11 triangle-fan index-buffer probe failure: "
              << message << '\n';
    std::exit(1);
}

void require(bool condition, const char* message) {
    if (!condition)
        fail(message);
}

void create_warp_device(
    ComPtr<ID3D11Device>& device,
    ComPtr<ID3D11DeviceContext>& context) {
    D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_9_1;
    const HRESULT hr = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_WARP,
        nullptr,
        0,
        nullptr,
        0,
        D3D11_SDK_VERSION,
        device.GetAddressOf(),
        &featureLevel,
        context.GetAddressOf());
    require(SUCCEEDED(hr) && device && context, "WARP device creation failed");
}

std::vector<UINT> read_back_indices(
    ID3D11Device* device,
    ID3D11DeviceContext* context,
    ID3D11Buffer* source,
    UINT expectedCount) {
    require(device && context && source && expectedCount != 0,
            "invalid readback arguments");

    D3D11_BUFFER_DESC sourceDesc{};
    source->GetDesc(&sourceDesc);
    require(sourceDesc.ByteWidth == expectedCount * sizeof(UINT),
            "generated index byte width drifted");

    D3D11_BUFFER_DESC stagingDesc = sourceDesc;
    stagingDesc.Usage = D3D11_USAGE_STAGING;
    stagingDesc.BindFlags = 0;
    stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    stagingDesc.MiscFlags = 0;
    stagingDesc.StructureByteStride = 0;

    ComPtr<ID3D11Buffer> staging;
    require(
        SUCCEEDED(device->CreateBuffer(
            &stagingDesc, nullptr, staging.GetAddressOf())) &&
            staging,
        "staging index buffer creation failed");

    context->CopyResource(staging.Get(), source);

    D3D11_MAPPED_SUBRESOURCE mapped{};
    require(
        SUCCEEDED(context->Map(
            staging.Get(), 0, D3D11_MAP_READ, 0, &mapped)) &&
            mapped.pData,
        "generated index buffer map failed");

    const auto* begin = static_cast<const UINT*>(mapped.pData);
    std::vector<UINT> result(begin, begin + expectedCount);
    context->Unmap(staging.Get(), 0);
    return result;
}

template <std::size_t N>
void require_indices(
    const std::vector<UINT>& actual,
    const std::array<UINT, N>& expected,
    const char* message) {
    require(
        actual.size() == expected.size() &&
            std::equal(actual.begin(), actual.end(), expected.begin()),
        message);
}

} // namespace

int main() {
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> context;
    create_warp_device(device, context);

    NativeTriangleFanIndexBuffer owner;
    require(
        owner.initialize_nonindexed(device.Get(), 3u, 7u),
        "R126 non-indexed triangle fan upload failed");

    const auto nonIndexedReady = owner.readiness(device.Get());
    require(
        nonIndexedReady.resourcesOwned &&
            nonIndexedReady.deviceMatches &&
            nonIndexedReady.descriptorExact &&
            nonIndexedReady.sourceProvenanceExact &&
            !nonIndexedReady.indexedSource &&
            nonIndexedReady.ready &&
            nonIndexedReady.indexCount == 9u &&
            nonIndexedReady.primitiveCount == 3u &&
            nonIndexedReady.baseVertex == 7u &&
            nonIndexedReady.sourceIndexFormat == D3DFMT_UNKNOWN &&
            nonIndexedReady.sourceStartIndex == 0u &&
            nonIndexedReady.sourceIndexCount == 0u &&
            nonIndexedReady.sourceIndexSnapshotToken == 0 &&
            nonIndexedReady.generation != 0 &&
            nonIndexedReady.contentHash != 0 &&
            nonIndexedReady.snapshotToken != 0 &&
            owner.validate_readiness_snapshot(
                device.Get(), nonIndexedReady.snapshotToken),
        "R126 non-indexed readiness snapshot was not exact");

    require_indices(
        read_back_indices(device.Get(), context.Get(), owner.buffer(), 9u),
        std::array<UINT, 9>{7u, 8u, 9u, 7u, 9u, 10u, 7u, 10u, 11u},
        "R126 non-indexed fan upload bytes drifted");

    require(owner.bind(context.Get()), "R126 same-device bind failed");
    ComPtr<ID3D11Buffer> boundIndexBuffer;
    DXGI_FORMAT boundFormat = DXGI_FORMAT_UNKNOWN;
    UINT boundOffset = 99u;
    context->IAGetIndexBuffer(
        boundIndexBuffer.GetAddressOf(), &boundFormat, &boundOffset);
    D3D11_PRIMITIVE_TOPOLOGY topology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&topology);
    require(
        boundIndexBuffer.Get() == owner.buffer() &&
            boundFormat == DXGI_FORMAT_R32_UINT &&
            boundOffset == 0u &&
            topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST,
        "R126 IA binding did not seal R32_UINT triangle-list state");

    const auto liveFanBinding = owner.binding_readiness(context.Get());
    require(
        liveFanBinding.inputValid &&
            liveFanBinding.ownerReady &&
            liveFanBinding.contextMatches &&
            liveFanBinding.bufferBoundExact &&
            liveFanBinding.formatExact &&
            liveFanBinding.offsetExact &&
            liveFanBinding.topologyExact &&
            liveFanBinding.ready &&
            liveFanBinding.ownerSnapshotToken == nonIndexedReady.snapshotToken &&
            liveFanBinding.snapshotToken != 0 &&
            owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 live generated fan IA binding seals exact owner identity");

    // R150 negative live ownership: a same-device deferred context can
    // record the identical IA state but must never seal live readiness.
    ComPtr<ID3D11DeviceContext> deferredContext;
    require(
        SUCCEEDED(device->CreateDeferredContext(
            0, deferredContext.GetAddressOf())) &&
            deferredContext &&
            deferredContext->GetType() == D3D11_DEVICE_CONTEXT_DEFERRED,
        "R150 same-device deferred context creation");
    deferredContext->IASetIndexBuffer(
        owner.buffer(), DXGI_FORMAT_R32_UINT, 0);
    deferredContext->IASetPrimitiveTopology(
        D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    const auto deferredFanBinding =
        owner.binding_readiness(deferredContext.Get());
    require(
        !owner.bind(deferredContext.Get()) &&
            !deferredFanBinding.inputValid &&
            !deferredFanBinding.ready &&
            deferredFanBinding.snapshotToken == 0 &&
            !owner.validate_binding_snapshot(
                deferredContext.Get(), liveFanBinding.snapshotToken) &&
            owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R150 same-device deferred IA state must not be live-ready");

    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
    const auto driftedFanBinding = owner.binding_readiness(context.Get());
    require(
        driftedFanBinding.inputValid &&
            driftedFanBinding.ownerReady &&
            driftedFanBinding.contextMatches &&
            driftedFanBinding.bufferBoundExact &&
            driftedFanBinding.formatExact &&
            driftedFanBinding.offsetExact &&
            !driftedFanBinding.topologyExact &&
            !driftedFanBinding.ready &&
            driftedFanBinding.snapshotToken == 0 &&
            !owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 live generated fan IA binding fails closed after topology drift");
    require(
        owner.bind(context.Get()) &&
            owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 generated fan IA binding restores deterministic snapshot");

    context->IASetIndexBuffer(
        owner.buffer(), DXGI_FORMAT_R32_UINT, sizeof(UINT));
    const auto offsetDriftFanBinding =
        owner.binding_readiness(context.Get());
    require(
        offsetDriftFanBinding.inputValid &&
            offsetDriftFanBinding.ownerReady &&
            offsetDriftFanBinding.contextMatches &&
            offsetDriftFanBinding.bufferBoundExact &&
            offsetDriftFanBinding.formatExact &&
            !offsetDriftFanBinding.offsetExact &&
            offsetDriftFanBinding.topologyExact &&
            !offsetDriftFanBinding.ready &&
            offsetDriftFanBinding.snapshotToken == 0 &&
            !owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 live generated fan IA binding rejects index offset drift");

    require(
        owner.bind(context.Get()),
        "R141 restore generated fan IA after index offset drift");
    context->IASetIndexBuffer(
        owner.buffer(), DXGI_FORMAT_R16_UINT, 0u);
    const auto formatDriftFanBinding =
        owner.binding_readiness(context.Get());
    require(
        formatDriftFanBinding.inputValid &&
            formatDriftFanBinding.ownerReady &&
            formatDriftFanBinding.contextMatches &&
            formatDriftFanBinding.bufferBoundExact &&
            !formatDriftFanBinding.formatExact &&
            formatDriftFanBinding.offsetExact &&
            formatDriftFanBinding.topologyExact &&
            !formatDriftFanBinding.ready &&
            formatDriftFanBinding.snapshotToken == 0 &&
            !owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 live generated fan IA binding rejects index format drift");

    require(
        owner.bind(context.Get()) &&
            owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 generated fan IA format offset restore reproduces snapshot");

    const std::array<std::uint16_t, 7> source16{
        99u, 4u, 8u, 15u, 16u, 23u, 77u};
    const auto staleToken = nonIndexedReady.snapshotToken;
    require(
        owner.initialize_indexed(
            device.Get(),
            3u,
            D3DFMT_INDEX16,
            1u,
            source16.data(),
            static_cast<UINT>(source16.size()),
            0x126160001ull),
        "R126 INDEX16 triangle fan upload failed");

    const auto indexed16Ready = owner.readiness(device.Get());
    require(
        indexed16Ready.ready &&
            indexed16Ready.sourceProvenanceExact &&
            indexed16Ready.indexedSource &&
            indexed16Ready.indexCount == 9u &&
            indexed16Ready.primitiveCount == 3u &&
            indexed16Ready.baseVertex == 0u &&
            indexed16Ready.sourceIndexFormat == D3DFMT_INDEX16 &&
            indexed16Ready.sourceStartIndex == 1u &&
            indexed16Ready.sourceIndexCount == source16.size() &&
            indexed16Ready.sourceIndexSnapshotToken == 0x126160001ull &&
            indexed16Ready.generation > nonIndexedReady.generation &&
            indexed16Ready.snapshotToken != staleToken &&
            !owner.validate_readiness_snapshot(device.Get(), staleToken) &&
            !owner.validate_binding_snapshot(
                context.Get(), liveFanBinding.snapshotToken),
        "R141 reupload invalidates stale live generated fan binding identity");

    require_indices(
        read_back_indices(device.Get(), context.Get(), owner.buffer(), 9u),
        std::array<UINT, 9>{4u, 8u, 15u, 4u, 15u, 16u, 4u, 16u, 23u},
        "R126 INDEX16 StartIndex upload bytes drifted");

    const std::array<std::uint32_t, 5> source32{
        1u, 70000u, 80000u, 90000u, 2u};
    require(
        owner.initialize_indexed(
            device.Get(),
            1u,
            D3DFMT_INDEX32,
            1u,
            source32.data(),
            static_cast<UINT>(source32.size()),
            0x126320001ull),
        "R126 INDEX32 triangle fan upload failed");
    require_indices(
        read_back_indices(device.Get(), context.Get(), owner.buffer(), 3u),
        std::array<UINT, 3>{70000u, 80000u, 90000u},
        "R126 INDEX32 source values were narrowed");

    const auto indexed32Ready = owner.readiness(device.Get());
    require(
        indexed32Ready.ready &&
            indexed32Ready.indexedSource &&
            indexed32Ready.sourceProvenanceExact &&
            indexed32Ready.primitiveCount == 1u &&
            indexed32Ready.sourceIndexFormat == D3DFMT_INDEX32 &&
            indexed32Ready.sourceStartIndex == 1u &&
            indexed32Ready.sourceIndexCount == source32.size() &&
            indexed32Ready.sourceIndexSnapshotToken == 0x126320001ull,
        "R129 INDEX32 source snapshot provenance was not sealed");

    ComPtr<ID3D11Device> foreignDevice;
    ComPtr<ID3D11DeviceContext> foreignContext;
    create_warp_device(foreignDevice, foreignContext);
    const auto foreignReady = owner.readiness(foreignDevice.Get());
    require(
        !foreignReady.ready &&
            !foreignReady.deviceMatches &&
            !foreignReady.descriptorExact &&
            !owner.bind(foreignContext.Get()) &&
            !owner.binding_readiness(foreignContext.Get()).ready &&
            !owner.validate_binding_snapshot(
                foreignContext.Get(), liveFanBinding.snapshotToken),
        "R141 foreign-device live generated fan binding fails closed");

    const std::array<std::uint16_t, 3> invalidSource{1u, 2u, 3u};
    require(
        !owner.initialize_indexed(
            device.Get(),
            1u,
            D3DFMT_UNKNOWN,
            0u,
            invalidSource.data(),
            static_cast<UINT>(invalidSource.size()),
            0x126BAD001ull) &&
            !owner.ready() &&
            !owner.readiness(device.Get()).ready,
        "R126 rejected replacement retained stale generated IB");

    require(
        !owner.initialize_indexed(
            device.Get(),
            1u,
            D3DFMT_INDEX16,
            0u,
            invalidSource.data(),
            static_cast<UINT>(invalidSource.size()),
            0) &&
            !owner.ready() &&
            !owner.readiness(device.Get()).sourceProvenanceExact,
        "R129 indexed fan without source snapshot provenance did not fail closed");

    require(
        !owner.initialize_nonindexed(device.Get(), 0u, 0u) &&
            !owner.ready(),
        "R126 zero-primitive fan unexpectedly created an IB");

    std::cout << "DX11 triangle-fan generated index buffer R126: PASS\n";
    std::cout << "DX11 indexed triangle-fan source provenance R129: PASS\n";
    std::cout << "DX11 triangle-fan live IA binding R141: PASS\n";
    std::cout << "DX11 triangle-fan immediate-context ownership R150: PASS\n";
    return 0;
}
