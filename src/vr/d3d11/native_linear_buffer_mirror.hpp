#pragma once
// R183: dormant D3D9 DEFAULT VB/IB snapshot -> owned D3D11 IA resource.
// A successful snapshot never authorizes game-native Draw or future Lock updates.
#include "resource_translation.hpp"
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <new>
#include <utility>
#include <wrl/client.h>

namespace outrun::vr::dx11 {
class NativeLinearBufferMirror final {
    struct IndexExtrema { UINT minimum; UINT maximum; };
public:
    bool initialize(ID3D11Device* device, ResourceRole role,
                    D3DPOOL pool, DWORD usage, D3DFORMAT indexFormat,
                    const void* sourceBytes, UINT byteWidth, UINT vertexStride,
                    std::uint64_t deviceGeneration,
                    std::uint64_t sourceSnapshotVersion) noexcept {
        shutdown(); // A rejected replacement cannot retain an old draw-ready VB/IB.
        if (!device || !sourceBytes || !byteWidth || !deviceGeneration ||
            !sourceSnapshotVersion || pool != D3DPOOL_DEFAULT ||
            (role != ResourceRole::Vertex && role != ResourceRole::Index))
            return false;

        const auto behavior = translate_resource_behavior(role, pool, usage);
        // DYNAMIC Map/NOOVERWRITE and MANAGED reset paths require a distinct
        // mutation/shadow owner; never label an initial upload as live parity.
        if (!behavior.descriptorExact ||
            behavior.lifetime != ResourceMirrorLifetime::DeviceGeneration ||
            behavior.usage != D3D11_USAGE_DEFAULT ||
            behavior.cpuAccessFlags != 0 || behavior.requiresCpuShadow)
            return false;

        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        if (role == ResourceRole::Vertex) {
            if (indexFormat != D3DFMT_UNKNOWN || !vertexStride ||
                byteWidth % vertexStride != 0)
                return false;
        } else {
            const auto translated = translate_resource_format(
                indexFormat, ResourceRole::Index);
            if (!translated.exact || vertexStride != 0)
                return false;
            format = translated.format;
            const UINT indexBytes = format == DXGI_FORMAT_R16_UINT ? 2u : 4u;
            if (byteWidth % indexBytes != 0)
                return false;
        }

        // R184: seal complete DEFAULT index-snapshot extrema at upload time.
        // This is metadata, not a mutable D3D9 Lock shadow. Full-buffer bounds
        // deliberately reject some legal partial draws rather than claim unsafe
        // parity before a future per-slice ownership implementation exists.
        UINT sealedIndexCount = 0, sealedMin = 0, sealedMax = 0;
        std::size_t rangeLeaves = 0;
        std::unique_ptr<IndexExtrema[]> rangeTree;
        if (role == ResourceRole::Index) {
            const UINT width = format == DXGI_FORMAT_R16_UINT ? 2u : 4u;
            sealedIndexCount = byteWidth / width;
            sealedMin = (std::numeric_limits<UINT>::max)();
            const auto* bytes = static_cast<const std::uint8_t*>(sourceBytes);
            // R195: immutable per-index segment tree. Unused IB indices cannot
            // poison an otherwise valid DrawIndexed subset.
            rangeLeaves = 1;
            while (rangeLeaves < sealedIndexCount) {
                if (rangeLeaves > (std::numeric_limits<std::size_t>::max)() / 2)
                    return false;
                rangeLeaves *= 2;
            }
            if (rangeLeaves > (std::numeric_limits<std::size_t>::max)() /
                    (2 * sizeof(IndexExtrema)))
                return false;
            rangeTree.reset(new (std::nothrow) IndexExtrema[rangeLeaves * 2]);
            if (!rangeTree) return false;
            for (std::size_t i = 0; i < rangeLeaves; ++i) {
                IndexExtrema extrema{(std::numeric_limits<UINT>::max)(), 0};
                if (i < sealedIndexCount) {
                    UINT value = 0;
                    std::memcpy(&value,
                        bytes + i * static_cast<std::size_t>(width), width);
                    extrema = {value, value};
                    if (value < sealedMin) sealedMin = value;
                    if (value > sealedMax) sealedMax = value;
                }
                rangeTree[rangeLeaves + i] = extrema;
            }
            for (std::size_t i = rangeLeaves; i-- > 1;) {
                const auto& a = rangeTree[2 * i];
                const auto& b = rangeTree[2 * i + 1];
                rangeTree[i] = {
                    a.minimum < b.minimum ? a.minimum : b.minimum,
                    a.maximum > b.maximum ? a.maximum : b.maximum};
            }
        }

        const UINT requiredBind = role == ResourceRole::Vertex
            ? D3D11_BIND_VERTEX_BUFFER : D3D11_BIND_INDEX_BUFFER;
        if (behavior.bindFlags != requiredBind)
            return false;

        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = byteWidth;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = requiredBind;
        D3D11_SUBRESOURCE_DATA initial{};
        initial.pSysMem = sourceBytes;
        Microsoft::WRL::ComPtr<ID3D11Buffer> buffer;
        if (FAILED(device->CreateBuffer(
                &desc, &initial, buffer.GetAddressOf())) || !buffer)
            return false;
        device_ = device;
        buffer_ = std::move(buffer);
        role_ = role;
        format_ = format;
        byte_width_ = byteWidth;
        stride_ = vertexStride;
        generation_ = deviceGeneration;
        source_version_ = sourceSnapshotVersion;
        index_count_ = sealedIndexCount;
        index_min_ = sealedMin;
        index_max_ = sealedMax;
        index_range_tree_ = std::move(rangeTree);
        index_range_leaves_ = rangeLeaves;
        if (!descriptor_exact()) {
            shutdown();
            return false;
        }
        return true;
    }

    bool descriptor_exact() const noexcept {
        if (!buffer_ || !device_ || !generation_ || !source_version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owningDevice;
        buffer_->GetDevice(owningDevice.GetAddressOf());
        if (owningDevice.Get() != device_.Get())
            return false;
        D3D11_BUFFER_DESC desc{};
        buffer_->GetDesc(&desc);
        return desc.ByteWidth == byte_width_ &&
            desc.Usage == D3D11_USAGE_DEFAULT &&
            desc.BindFlags == (role_ == ResourceRole::Vertex
                ? D3D11_BIND_VERTEX_BUFFER : D3D11_BIND_INDEX_BUFFER) &&
            desc.CPUAccessFlags == 0 && desc.MiscFlags == 0 &&
            desc.StructureByteStride == 0 &&
            (role_ == ResourceRole::Vertex
                ? format_ == DXGI_FORMAT_UNKNOWN && stride_ != 0
                : (format_ == DXGI_FORMAT_R16_UINT ||
                   format_ == DXGI_FORMAT_R32_UINT) && stride_ == 0);
    }

    bool bind(ID3D11DeviceContext* context,
              std::uint64_t currentGeneration,
              std::uint64_t currentSnapshotVersion) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            currentGeneration != generation_ ||
            currentSnapshotVersion != source_version_)
            return false;
        if (role_ == ResourceRole::Vertex) {
            ID3D11Buffer* raw = buffer_.Get();
            const UINT offset = 0;
            context->IASetVertexBuffers(0, 1, &raw, &stride_, &offset);
        } else {
            context->IASetIndexBuffer(buffer_.Get(), format_, 0);
        }
        return binding_exact(context, currentGeneration, currentSnapshotVersion);
    }

    bool binding_exact(ID3D11DeviceContext* context,
                       std::uint64_t currentGeneration,
                       std::uint64_t currentSnapshotVersion) const noexcept {
        if (!same_immediate_device(context) || !descriptor_exact() ||
            currentGeneration != generation_ ||
            currentSnapshotVersion != source_version_)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Buffer> live;
        if (role_ == ResourceRole::Vertex) {
            UINT liveStride = 0, offset = 1;
            context->IAGetVertexBuffers(0, 1, live.GetAddressOf(),
                                         &liveStride, &offset);
            return live.Get() == buffer_.Get() &&
                liveStride == stride_ && offset == 0;
        }
        DXGI_FORMAT liveFormat = DXGI_FORMAT_UNKNOWN;
        UINT offset = 1;
        context->IAGetIndexBuffer(live.GetAddressOf(), &liveFormat, &offset);
        return live.Get() == buffer_.Get() &&
            liveFormat == format_ && offset == 0;
    }

    // R184: conservative dormant preflight before any indexed draw. It proves
    // actual same-device IA objects, both independent source versions, index
    // slice bounds, and entire sealed IB's possible vertex extent. Because
    // only full-buffer extrema are retained, false means NOT PROVEN (not that
    // an isolated sub-range is necessarily invalid). No draw is issued here.
    [[nodiscard]] bool indexed_draw_bounds_exact(
        const NativeLinearBufferMirror& index,
        ID3D11DeviceContext* context,
        UINT startIndex, UINT indexCount, INT baseVertexLocation,
        std::uint64_t currentGeneration,
        std::uint64_t currentVertexSnapshotVersion,
        std::uint64_t currentIndexSnapshotVersion) const noexcept {
        if (role_ != ResourceRole::Vertex ||
            index.role_ != ResourceRole::Index ||
            !indexCount || !stride_ || !index.index_count_ ||
            device_.Get() != index.device_.Get() ||
            !binding_exact(context, currentGeneration, currentVertexSnapshotVersion) ||
            !index.binding_exact(context, currentGeneration, currentIndexSnapshotVersion) ||
            startIndex >= index.index_count_ ||
            indexCount > index.index_count_ - startIndex)
            return false;
        UINT rangeMin = index.index_min_, rangeMax = index.index_max_;
        // Immutable O(log N) exact subset query. No per-frame D3D9 Lock/Map
        // shadow, and the original full-range R184 guard is preserved.
        if (startIndex != 0 || indexCount != index.index_count_) {
            if (!index.index_range_tree_ || !index.index_range_leaves_)
                return false;
            std::size_t left = index.index_range_leaves_ + startIndex;
            std::size_t right = left + indexCount;
            rangeMin = (std::numeric_limits<UINT>::max)();
            rangeMax = 0;
            while (left < right) {
                if (left & 1u) {
                    const auto& item = index.index_range_tree_[left++];
                    if (item.minimum < rangeMin) rangeMin = item.minimum;
                    if (item.maximum > rangeMax) rangeMax = item.maximum;
                }
                if (right & 1u) {
                    const auto& item = index.index_range_tree_[--right];
                    if (item.minimum < rangeMin) rangeMin = item.minimum;
                    if (item.maximum > rangeMax) rangeMax = item.maximum;
                }
                left >>= 1;
                right >>= 1;
            }
        }
        const std::int64_t low = static_cast<std::int64_t>(baseVertexLocation)
            + static_cast<std::int64_t>(rangeMin);
        const std::int64_t high = static_cast<std::int64_t>(baseVertexLocation)
            + static_cast<std::int64_t>(rangeMax);
        const std::int64_t vertices = static_cast<std::int64_t>(byte_width_ / stride_);
        return low >= 0 && high >= low && high < vertices;
    }

    void shutdown() noexcept {
        buffer_.Reset();
        device_.Reset();
        role_ = ResourceRole::Vertex;
        format_ = DXGI_FORMAT_UNKNOWN;
        byte_width_ = stride_ = 0;
        generation_ = source_version_ = 0;
        index_count_ = index_min_ = index_max_ = 0;
        index_range_tree_.reset();
        index_range_leaves_ = 0;
    }

    [[nodiscard]] ID3D11Buffer* buffer() const noexcept { return buffer_.Get(); }
private:
    bool same_immediate_device(ID3D11DeviceContext* context) const noexcept {
        if (!context || !device_ ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> owner;
        context->GetDevice(owner.GetAddressOf());
        return owner.Get() == device_.Get();
    }
    Microsoft::WRL::ComPtr<ID3D11Device> device_;
    Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_;
    ResourceRole role_ = ResourceRole::Vertex;
    DXGI_FORMAT format_ = DXGI_FORMAT_UNKNOWN;
    UINT byte_width_ = 0;
    UINT stride_ = 0;
    std::uint64_t generation_ = 0;
    std::uint64_t source_version_ = 0;
    UINT index_count_ = 0;
    UINT index_min_ = 0;
    UINT index_max_ = 0;
    std::unique_ptr<IndexExtrema[]> index_range_tree_;
    std::size_t index_range_leaves_ = 0;
};
} // namespace outrun::vr::dx11
