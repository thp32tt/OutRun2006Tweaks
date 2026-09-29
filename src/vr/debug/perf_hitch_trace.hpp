#pragma once

#include <atomic>
#include <cstdint>

namespace OutRunVR::PerfHitch
{
    struct ResourceSnapshot
    {
        std::uint64_t managedTextureCreates = 0;
        std::uint64_t managedTextureCreateBytes = 0;
        std::uint64_t textureLocks = 0;
        std::uint64_t textureUploads = 0;
        std::uint64_t textureUploadBytes = 0;
        std::uint64_t textureUploadUs = 0;
        std::uint64_t fileLoadCalls = 0;
        std::uint64_t fileLoadBusyCalls = 0;
        std::uint64_t fileLoadUs = 0;
        std::uint64_t fileLoadMaxUs = 0;
        std::uint64_t vertexBufferCreates = 0;
        std::uint64_t vertexBufferCreateBytes = 0;
        std::uint64_t indexBufferCreates = 0;
        std::uint64_t indexBufferCreateBytes = 0;
        std::uint64_t bufferLocks = 0;
        std::uint64_t bufferLockBytes = 0;
        std::uint64_t bufferDiscardLocks = 0;
        std::uint64_t bufferNoOverwriteLocks = 0;
    };

    inline std::atomic<std::uint64_t> ManagedTextureCreates{ 0 };
    inline std::atomic<std::uint64_t> ManagedTextureCreateBytes{ 0 };
    inline std::atomic<std::uint64_t> TextureLocks{ 0 };
    inline std::atomic<std::uint64_t> TextureUploads{ 0 };
    inline std::atomic<std::uint64_t> TextureUploadBytes{ 0 };
    inline std::atomic<std::uint64_t> TextureUploadUs{ 0 };
    inline std::atomic<std::uint64_t> FileLoadCalls{ 0 };
    inline std::atomic<std::uint64_t> FileLoadBusyCalls{ 0 };
    inline std::atomic<std::uint64_t> FileLoadUs{ 0 };
    inline std::atomic<std::uint64_t> FileLoadMaxUs{ 0 };
    inline std::atomic<std::uint64_t> VertexBufferCreates{ 0 };
    inline std::atomic<std::uint64_t> VertexBufferCreateBytes{ 0 };
    inline std::atomic<std::uint64_t> IndexBufferCreates{ 0 };
    inline std::atomic<std::uint64_t> IndexBufferCreateBytes{ 0 };
    inline std::atomic<std::uint64_t> BufferLocks{ 0 };
    inline std::atomic<std::uint64_t> BufferLockBytes{ 0 };
    inline std::atomic<std::uint64_t> BufferDiscardLocks{ 0 };
    inline std::atomic<std::uint64_t> BufferNoOverwriteLocks{ 0 };

    inline void NoteManagedTextureCreate(std::uint64_t bytes) noexcept
    {
        ManagedTextureCreates.fetch_add(1, std::memory_order_relaxed);
        ManagedTextureCreateBytes.fetch_add(bytes, std::memory_order_relaxed);
    }

    inline void NoteTextureLock() noexcept
    {
        TextureLocks.fetch_add(1, std::memory_order_relaxed);
    }

    inline void NoteTextureUpload(
        std::uint64_t bytes, std::uint64_t elapsedUs) noexcept
    {
        TextureUploads.fetch_add(1, std::memory_order_relaxed);
        TextureUploadBytes.fetch_add(bytes, std::memory_order_relaxed);
        TextureUploadUs.fetch_add(elapsedUs, std::memory_order_relaxed);
    }

    inline void NoteFileLoad(
        std::uint64_t elapsedUs, bool busy) noexcept
    {
        FileLoadCalls.fetch_add(1, std::memory_order_relaxed);
        if (busy)
            FileLoadBusyCalls.fetch_add(1, std::memory_order_relaxed);
        FileLoadUs.fetch_add(elapsedUs, std::memory_order_relaxed);
        auto current = FileLoadMaxUs.load(std::memory_order_relaxed);
        while (elapsedUs > current &&
            !FileLoadMaxUs.compare_exchange_weak(
                current, elapsedUs,
                std::memory_order_relaxed,
                std::memory_order_relaxed))
        {
        }
    }

    inline void NoteVertexBufferCreate(std::uint64_t bytes) noexcept
    {
        VertexBufferCreates.fetch_add(1, std::memory_order_relaxed);
        VertexBufferCreateBytes.fetch_add(bytes, std::memory_order_relaxed);
    }

    inline void NoteIndexBufferCreate(std::uint64_t bytes) noexcept
    {
        IndexBufferCreates.fetch_add(1, std::memory_order_relaxed);
        IndexBufferCreateBytes.fetch_add(bytes, std::memory_order_relaxed);
    }

    inline void NoteBufferLock(
        std::uint64_t bytes, std::uint32_t flags) noexcept
    {
        BufferLocks.fetch_add(1, std::memory_order_relaxed);
        BufferLockBytes.fetch_add(bytes, std::memory_order_relaxed);
        if ((flags & 0x00002000u) != 0) // D3DLOCK_DISCARD
            BufferDiscardLocks.fetch_add(1, std::memory_order_relaxed);
        if ((flags & 0x00001000u) != 0) // D3DLOCK_NOOVERWRITE
            BufferNoOverwriteLocks.fetch_add(1, std::memory_order_relaxed);
    }

    inline ResourceSnapshot Consume() noexcept
    {
        ResourceSnapshot out{};
        out.managedTextureCreates =
            ManagedTextureCreates.exchange(0, std::memory_order_acq_rel);
        out.managedTextureCreateBytes =
            ManagedTextureCreateBytes.exchange(0, std::memory_order_acq_rel);
        out.textureLocks =
            TextureLocks.exchange(0, std::memory_order_acq_rel);
        out.textureUploads =
            TextureUploads.exchange(0, std::memory_order_acq_rel);
        out.textureUploadBytes =
            TextureUploadBytes.exchange(0, std::memory_order_acq_rel);
        out.textureUploadUs =
            TextureUploadUs.exchange(0, std::memory_order_acq_rel);
        out.fileLoadCalls =
            FileLoadCalls.exchange(0, std::memory_order_acq_rel);
        out.fileLoadBusyCalls =
            FileLoadBusyCalls.exchange(0, std::memory_order_acq_rel);
        out.fileLoadUs =
            FileLoadUs.exchange(0, std::memory_order_acq_rel);
        out.fileLoadMaxUs =
            FileLoadMaxUs.exchange(0, std::memory_order_acq_rel);
        out.vertexBufferCreates =
            VertexBufferCreates.exchange(0, std::memory_order_acq_rel);
        out.vertexBufferCreateBytes =
            VertexBufferCreateBytes.exchange(0, std::memory_order_acq_rel);
        out.indexBufferCreates =
            IndexBufferCreates.exchange(0, std::memory_order_acq_rel);
        out.indexBufferCreateBytes =
            IndexBufferCreateBytes.exchange(0, std::memory_order_acq_rel);
        out.bufferLocks =
            BufferLocks.exchange(0, std::memory_order_acq_rel);
        out.bufferLockBytes =
            BufferLockBytes.exchange(0, std::memory_order_acq_rel);
        out.bufferDiscardLocks =
            BufferDiscardLocks.exchange(0, std::memory_order_acq_rel);
        out.bufferNoOverwriteLocks =
            BufferNoOverwriteLocks.exchange(0, std::memory_order_acq_rel);
        return out;
    }
}
