// Quest 3 cockpit V2 — independently reconstructed compact B0/F0 affine
// correction. Research-only; not linked to PCVR or game. See research report.
// Input matrices are row-major arrays of 16 floats, with translation in
// indices 12,13,14, and indices 3,7,11,15 = 0,0,0,1 respectively.
// Mathematical candidate validated against separate 240-statement ARM64-FMA
// transcription; it is NOT asserted to be the original authored formula.
#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace quest_cockpit_research {

using AffineMatrix = std::array<float,16>;
constexpr std::array<float,9> kMirrorD = {{
     1.0f,0.0f,0.0f,
     0.0f,-1.0f,0.0f,
     0.0f,0.0f,1.0f
}};

inline bool IsFiniteAffine(const AffineMatrix& m, float eps=1.0e-5f) noexcept {
    for (float f : m) if (!std::isfinite(f)) return false;
    return std::fabs(m[3]) <= eps && std::fabs(m[7]) <= eps &&
           std::fabs(m[11]) <= eps && std::fabs(m[15]-1.0f) <= eps;
}

inline bool ComputeQuestBodyCorrectionAffine(
    const AffineMatrix& matrixB0,
    const AffineMatrix& matrixF0,
    AffineMatrix& destination) noexcept {
    if (!IsFiniteAffine(matrixB0) || !IsFiniteAffine(matrixF0))
        return false;

    // A=3x3(B0), B=3x3(F0), d=diag(+1,-1,+1).
    // C_R = - A^T B^T A
    // C_t = (I + A^T B D A)*tB0 - A^T B*tF0
    // Rows of D3DMATRIX-style input are indexed by r*4+c.
    // Compute in double to keep verification rounding stable across toolchains.
    double A[3][3], B[3][3], M[3][3]{}, U[3][3]{}, C[3][3]{};
    constexpr double d[3]{1.0,-1.0,1.0};
    for (int r=0;r<3;++r)
        for (int c=0;c<3;++c) {
            A[r][c]=matrixB0[4*r+c];
            B[r][c]=matrixF0[4*r+c];
        }

    // M = A^T B ; U = I + (A^T B) D A
    // C = - A^T B^T A (not simply -M, and det can be negative).
    for (int i=0;i<3;++i)
      for (int j=0;j<3;++j)
        for (int k=0;k<3;++k)
          M[i][j]+=A[k][i]*B[k][j];

    for (int i=0;i<3;++i)
      for (int j=0;j<3;++j) {
        U[i][j]=(i==j?1.0:0.0);
        for (int k=0;k<3;++k)
          U[i][j]+=M[i][k]*d[k]*A[k][j];
        for (int k=0;k<3;++k)
          for (int p=0;p<3;++p)
            C[i][j]-=A[k][i]*B[p][k]*A[p][j];
      }

    AffineMatrix tmp{};
    for (int i=0;i<3;++i) {
      for (int j=0;j<3;++j) {
        tmp[4*i+j]=static_cast<float>(C[i][j]);
      }
      double translation=0.0;
      for (int k=0;k<3;++k) {
        translation+=U[i][k]*static_cast<double>(matrixB0[12+k]);
        translation-=M[i][k]*static_cast<double>(matrixF0[12+k]);
      }
      tmp[12+i]=static_cast<float>(translation);
    }
    tmp[15]=1.0f;
    for (float x : tmp) if (!std::isfinite(x)) return false;
    destination=tmp; // leave destination unmodified on reject
    return true;
}
} // namespace quest_cockpit_research