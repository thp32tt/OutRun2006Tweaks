#pragma once
// Ferrari retail ID -> canonical optional OVC slot, pure and portable.
// Testing slot -1 permits all installed cars; a specific slot is fail closed.
namespace OutRunVR::DinoSidecar {
constexpr unsigned char CanonicalFerrariExternalCarId(unsigned char carId) noexcept {
    if (carId >= 15u && carId <= 27u)
        return static_cast<unsigned char>(carId - 15u);
    if (carId == 29u) return 14u;
    return carId;
}
constexpr bool MatchesFerrariSelection(unsigned char observedId,
                                        int requestedId) noexcept {
    if (observedId >= 30u) return false;
    if (requestedId == -1) return true;
    if (requestedId < 0 || requestedId >= 30) return false;
    return CanonicalFerrariExternalCarId(observedId) ==
        CanonicalFerrariExternalCarId(
            static_cast<unsigned char>(requestedId));
}
static_assert(CanonicalFerrariExternalCarId(5u) == 5u &&
              CanonicalFerrariExternalCarId(20u) == 5u &&
              CanonicalFerrariExternalCarId(8u) == 8u &&
              CanonicalFerrariExternalCarId(23u) == 8u &&
              CanonicalFerrariExternalCarId(28u) == 28u &&
              CanonicalFerrariExternalCarId(29u) == 14u,
              "Ferrari 30-car alias contract");
static_assert(MatchesFerrariSelection(5u,5) &&
              MatchesFerrariSelection(20u,5) &&
              !MatchesFerrariSelection(2u,5) &&
              !MatchesFerrariSelection(28u,5) &&
              !MatchesFerrariSelection(30u,-1),
              "Ferrari per-car isolation contract");
} // namespace OutRunVR::DinoSidecar
