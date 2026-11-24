#pragma once

namespace OutRunVR::DinoSidecar {
// An unsuccessful Lock owns no mapping. A successful Lock must be
// balanced even if a broken device returns null data. Publication is
// allowed only after the copy AND its Unlock succeed.
template<class Lock, class Copy, class Unlock>
inline bool UploadExternalMeshBuffer(Lock&& lock, Copy&& copy,
                                    Unlock&& unlock) noexcept {
    void* data=nullptr;
    if(!lock(&data))return false;
    if(data)copy(data);
    const bool committed=unlock();
    return data!=nullptr && committed;
}
} // namespace OutRunVR::DinoSidecar
