#pragma once

namespace OutRunVR::DinoSidecar {
// A successful lock owns a mapping even if its resource generation retires
// inside the driver. Balance the lock but do not copy or publish stale data.
template<class Lock,class Copy,class Unlock,class Current>
inline bool UploadExternalMeshBuffer(Lock&& lock,Copy&& copy,
                                     Unlock&& unlock,Current&& current) noexcept {
    void* data=nullptr;
    if(!current()||!lock(&data))return false;
    const bool copied=data&&current();
    if(copied)copy(data);
    const bool committed=unlock();
    return copied&&committed&&current();
}
template<class Lock,class Copy,class Unlock>
inline bool UploadExternalMeshBuffer(Lock&& lock,Copy&& copy,
                                     Unlock&& unlock) noexcept {
    return UploadExternalMeshBuffer(lock,copy,unlock,[](){return true;});
}
// Driver output must be a local pointer, never a vector member that Reset
// can destroy. Only publish the local result after the owner check.
template<class Resource,class Current,class Publish>
inline bool PublishExternalGpuResource(Resource*& pending,Current&& current,
                                       Publish&& publish) noexcept {
    auto* resource=pending;
    pending=nullptr;
    if(!resource)return false;
    if(!current()){resource->Release();return false;}
    publish(resource); // owner-local store only, no driver calls
    return true;
}
} // namespace OutRunVR::DinoSidecar
