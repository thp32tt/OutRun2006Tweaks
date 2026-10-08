#include "triangle_fan_index_buffer.hpp"

#include "state_translation.hpp"

#include <limits>
#include <utility>
#include <vector>

namespace outrun::vr::dx11 {
namespace {

std::uint64_t mix_index_token(
    std::uint64_t token,
    std::uint64_t value) noexcept {
    token ^= value + 0x9e3779b97f4a7c15ull + (token << 6) + (token >> 2);
    return token;
}

std::uint64_t hash_indices(const UINT* indices, UINT count) noexcept {
    if (!indices || count == 0)
        return 0;

    std::uint64_t hash = 0xcbf29ce484222325ull;
    for (UINT i = 0; i < count; ++i)
        hash = mix_index_token(hash, indices[i]);
    return hash == 0 ? 1 : hash;
}

} // namespace

bool NativeTriangleFanIndexBuffer::initialize_nonindexed(
    ID3D11Device* device,
    UINT primitiveCount,
    UINT baseVertex) noexcept {
    // R126 fail-closed reinitialization: a rejected replacement must not leave
    // a previously generated fan stream eligible for a later bind.
    shutdown();

    const auto plan = translate_triangle_fan_expansion(primitiveCount);
    if (!device || !plan.exact || plan.expandedIndexCount == 0)
        return false;

    std::vector<UINT> indices(plan.expandedIndexCount);
    if (!materialize_triangle_fan_vertex_indices(
            primitiveCount,
            baseVertex,
            indices.data(),
            static_cast<UINT>(indices.size())))
        return false;

    if (!initialize_materialized(
            device,
            indices.data(),
            static_cast<UINT>(indices.size())))
        return false;

    source_provenance_exact_ = true;
    indexed_source_ = false;
    primitive_count_ = primitiveCount;
    base_vertex_ = baseVertex;
    return true;
}

bool NativeTriangleFanIndexBuffer::initialize_indexed(
    ID3D11Device* device,
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    const void* sourceIndices,
    UINT sourceIndexCount,
    std::uint64_t sourceIndexSnapshotToken) noexcept {
    // Preserve the same fail-closed replacement rule for indexed fans.
    shutdown();

    const auto plan = translate_triangle_fan_expansion(primitiveCount);
    if (!device || !plan.exact || plan.expandedIndexCount == 0 ||
        sourceIndexSnapshotToken == 0)
        return false;

    std::vector<UINT> indices(plan.expandedIndexCount);
    if (!materialize_indexed_triangle_fan_indices(
            primitiveCount,
            sourceIndexFormat,
            startIndex,
            sourceIndices,
            sourceIndexCount,
            indices.data(),
            static_cast<UINT>(indices.size())))
        return false;

    if (!initialize_materialized(
            device,
            indices.data(),
            static_cast<UINT>(indices.size())))
        return false;

    source_provenance_exact_ = true;
    indexed_source_ = true;
    primitive_count_ = primitiveCount;
    source_index_format_ = sourceIndexFormat;
    source_start_index_ = startIndex;
    source_index_count_ = sourceIndexCount;
    source_index_snapshot_token_ = sourceIndexSnapshotToken;
    return true;
}

bool NativeTriangleFanIndexBuffer::initialize_materialized(
    ID3D11Device* device,
    const UINT* indices,
    UINT indexCount) noexcept {
    shutdown();

    if (!device || !indices || indexCount == 0 ||
        indexCount >
            (std::numeric_limits<UINT>::max)() /
                static_cast<UINT>(sizeof(UINT)) ||
        generation_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;

    const std::uint64_t contentHash = hash_indices(indices, indexCount);
    if (contentHash == 0)
        return false;

    D3D11_BUFFER_DESC desc{};
    desc.ByteWidth = indexCount * static_cast<UINT>(sizeof(UINT));
    desc.Usage = D3D11_USAGE_IMMUTABLE;
    desc.BindFlags = D3D11_BIND_INDEX_BUFFER;

    D3D11_SUBRESOURCE_DATA initialData{};
    initialData.pSysMem = indices;

    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
    if (FAILED(device->CreateBuffer(&desc, &initialData, buffer.GetAddressOf())) ||
        !buffer)
        return false;

    device_ = device;
    buffer_ = std::move(buffer);
    index_count_ = indexCount;
    content_hash_ = contentHash;
    ++generation_;
    return true;
}

bool NativeTriangleFanIndexBuffer::descriptor_exact(
    ID3D11Device* expectedDevice) const noexcept {
    if (!ready() || !expectedDevice || expectedDevice != device_.Get())
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> bufferDevice;
    buffer_->GetDevice(bufferDevice.GetAddressOf());
    if (bufferDevice.Get() != expectedDevice)
        return false;

    if (index_count_ >
        (std::numeric_limits<UINT>::max)() /
            static_cast<UINT>(sizeof(UINT)))
        return false;

    D3D11_BUFFER_DESC desc{};
    buffer_->GetDesc(&desc);
    return
        desc.ByteWidth ==
            index_count_ * static_cast<UINT>(sizeof(UINT)) &&
        desc.Usage == D3D11_USAGE_IMMUTABLE &&
        desc.BindFlags == D3D11_BIND_INDEX_BUFFER &&
        desc.CPUAccessFlags == 0 &&
        desc.MiscFlags == 0 &&
        desc.StructureByteStride == 0;
}

NativeTriangleFanIndexBufferReadiness
NativeTriangleFanIndexBuffer::readiness(
    ID3D11Device* expectedDevice) const noexcept {
    NativeTriangleFanIndexBufferReadiness out{};
    out.resourcesOwned = device_ && buffer_;
    out.deviceMatches =
        expectedDevice != nullptr &&
        device_.Get() == expectedDevice;
    out.descriptorExact = descriptor_exact(expectedDevice);
    out.sourceProvenanceExact = source_provenance_exact_;
    out.indexedSource = indexed_source_;
    out.indexCount = index_count_;
    out.primitiveCount = primitive_count_;
    out.baseVertex = base_vertex_;
    out.sourceIndexFormat = source_index_format_;
    out.sourceStartIndex = source_start_index_;
    out.sourceIndexCount = source_index_count_;
    out.sourceIndexSnapshotToken = source_index_snapshot_token_;
    out.generation = generation_;
    out.contentHash = content_hash_;
    out.ready =
        out.resourcesOwned &&
        out.deviceMatches &&
        out.descriptorExact &&
        out.sourceProvenanceExact &&
        out.indexCount != 0 &&
        out.primitiveCount != 0 &&
        (!out.indexedSource ||
            (out.sourceIndexSnapshotToken != 0 &&
             (out.sourceIndexFormat == D3DFMT_INDEX16 ||
              out.sourceIndexFormat == D3DFMT_INDEX32))) &&
        out.generation != 0 &&
        out.contentHash != 0;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_index_token(token, out.generation);
        token = mix_index_token(token, out.indexCount);
        token = mix_index_token(token, out.primitiveCount);
        token = mix_index_token(token, out.baseVertex);
        token = mix_index_token(token, out.indexedSource ? 1u : 0u);
        token = mix_index_token(
            token, static_cast<std::uint32_t>(out.sourceIndexFormat));
        token = mix_index_token(token, out.sourceStartIndex);
        token = mix_index_token(token, out.sourceIndexCount);
        token = mix_index_token(token, out.sourceIndexSnapshotToken);
        token = mix_index_token(token, out.contentHash);
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeTriangleFanIndexBuffer::validate_readiness_snapshot(
    ID3D11Device* expectedDevice,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = readiness(expectedDevice);
    return current.ready && current.snapshotToken == snapshotToken;
}

NativeTriangleFanIndexBufferBindingReadiness
NativeTriangleFanIndexBuffer::binding_readiness(
    ID3D11DeviceContext* context) const noexcept {
    NativeTriangleFanIndexBufferBindingReadiness out{};
    // R150: a deferred context only records IA commands; it cannot prove the
    // immediate producer's live index-buffer/topology state. Fail closed.
    out.inputValid =
        context != nullptr &&
        context->GetType() == D3D11_DEVICE_CONTEXT_IMMEDIATE;
    if (!out.inputValid)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.GetAddressOf());
    out.contextMatches =
        contextDevice && contextDevice.Get() == device_.Get();

    const auto owner = readiness(contextDevice.Get());
    out.ownerReady = owner.ready && owner.snapshotToken != 0;
    out.ownerSnapshotToken = owner.snapshotToken;
    if (!out.contextMatches || !out.ownerReady)
        return out;

    Microsoft::WRL::ComPtr<ID3D11Buffer> observedBuffer;
    DXGI_FORMAT observedFormat = DXGI_FORMAT_UNKNOWN;
    UINT observedOffset = 0;
    context->IAGetIndexBuffer(
        observedBuffer.GetAddressOf(), &observedFormat, &observedOffset);
    D3D11_PRIMITIVE_TOPOLOGY observedTopology =
        D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&observedTopology);

    out.bufferBoundExact = observedBuffer.Get() == buffer_.Get();
    out.formatExact = observedFormat == DXGI_FORMAT_R32_UINT;
    out.offsetExact = observedOffset == 0;
    out.topologyExact =
        observedTopology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
    out.ready =
        out.bufferBoundExact &&
        out.formatExact &&
        out.offsetExact &&
        out.topologyExact;

    if (out.ready) {
        std::uint64_t token = 0xcbf29ce484222325ull;
        token = mix_index_token(token, out.ownerSnapshotToken);
        token = mix_index_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(context)));
        token = mix_index_token(
            token, static_cast<std::uint64_t>(
                reinterpret_cast<std::uintptr_t>(observedBuffer.Get())));
        token = mix_index_token(
            token, static_cast<std::uint32_t>(observedFormat));
        token = mix_index_token(token, observedOffset);
        token = mix_index_token(
            token, static_cast<std::uint32_t>(observedTopology));
        out.snapshotToken = token == 0 ? 1 : token;
    }
    return out;
}

bool NativeTriangleFanIndexBuffer::validate_binding_snapshot(
    ID3D11DeviceContext* context,
    std::uint64_t snapshotToken) const noexcept {
    if (snapshotToken == 0)
        return false;
    const auto current = binding_readiness(context);
    return current.ready && current.snapshotToken == snapshotToken;
}

bool NativeTriangleFanIndexBuffer::bind(
    ID3D11DeviceContext* context) const noexcept {
    // Same-device deferred contexts must not qualify as live IA binding.
    if (!ready() || !context ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
        return false;

    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice;
    context->GetDevice(contextDevice.GetAddressOf());
    if (contextDevice.Get() != device_.Get())
        return false;

    context->IASetIndexBuffer(buffer_.Get(), DXGI_FORMAT_R32_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    return binding_readiness(context).ready;
}

void NativeTriangleFanIndexBuffer::shutdown() noexcept {
    buffer_.Reset();
    device_.Reset();
    index_count_ = 0;
    source_provenance_exact_ = false;
    indexed_source_ = false;
    primitive_count_ = 0;
    base_vertex_ = 0;
    source_index_format_ = D3DFMT_UNKNOWN;
    source_start_index_ = 0;
    source_index_count_ = 0;
    source_index_snapshot_token_ = 0;
    content_hash_ = 0;
}

} // namespace outrun::vr::dx11
