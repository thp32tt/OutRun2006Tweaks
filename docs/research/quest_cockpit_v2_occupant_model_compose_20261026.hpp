// QuestCockpitV2 research-only occupant model transformation.
// Native evidence: Draw::disp_514c30 @ ELF 0xD61100..0xD61288.
// In an admitted player occupant draw: stackMatrix = guestWorkMatrix * TLSBodyCorrection.
// Read-only, no game hooks, no Quest hands/wheel inputs. Not runtime validated.
#pragma once
#include <array>
#include <cmath>
#include <cstddef>
namespace quest_cockpit_research {
using Matrix4 = std::array<float,16>;
inline bool ComposeOccupantModelRightCorrection(
    const Matrix4& guestWorkMatrix,
    const Matrix4& nativeBodyCorrection,
    Matrix4& out) noexcept {
  for(float v:guestWorkMatrix) if(!std::isfinite(v)) return false;
  for(float v:nativeBodyCorrection) if(!std::isfinite(v)) return false;
  Matrix4 candidate{};
  for(std::size_t row=0;row<4;++row)
    for(std::size_t col=0;col<4;++col) {
      // Quest ARM64 uses a different FMADD accumulation order; double only
      // gives a stable clean-room numerical comparator, not bit-identical FP.
      double sum=0.0;
      for(std::size_t k=0;k<4;++k)
        sum+=static_cast<double>(guestWorkMatrix[4*row+k]) *
             static_cast<double>(nativeBodyCorrection[4*k+col]);
      candidate[4*row+col]=static_cast<float>(sum);
    }
  for(float v:candidate) if(!std::isfinite(v)) return false;
  out=candidate; // caller's output remains unchanged on failure
  return true;
}
} // namespace quest_cockpit_research
