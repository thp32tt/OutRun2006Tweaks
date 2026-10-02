#pragma once
#include <d3d9.h>
namespace OutRunVRStereo {
bool StereoMatrixFinite(const D3DMATRIX&) noexcept;
D3DMATRIX StereoMatrixFromPose(const float[4],const float[3],float) noexcept;
D3DMATRIX StereoInverseRigid(const D3DMATRIX&) noexcept;
D3DMATRIX StereoMultiplyMatrix(const D3DMATRIX&,const D3DMATRIX&) noexcept;
D3DMATRIX StereoTransposeMatrix(const D3DMATRIX&) noexcept;
D3DMATRIX StereoProjectionFromFov(const D3DMATRIX&,float,float,float,float) noexcept;
bool StereoGetInverseProjection(const D3DMATRIX&,D3DMATRIX&) noexcept;
}
