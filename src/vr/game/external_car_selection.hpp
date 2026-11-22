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
// Exactly 16 distinct selectable Ferrari models: stock IDs 0..14 plus
// the tuned-only F430 Spider (28). Retail variants 15..27 and 29 alias
// their matching base model, not additional external asset identities.
constexpr bool IsFerrari16CanonicalCarId(unsigned char carId) noexcept {
    return carId<=14u || carId==28u;
}
// Backwards compatibility for older private 288 GTO/F40 packages. Prefer a
// canonical car_id_XX.ovc when present; only use these fixed legacy names if
// the canonical file is missing. Never derive a path from untrusted input.
constexpr const wchar_t* LegacyFerrariCarSuffix(
    unsigned char observedId) noexcept
{
    switch(CanonicalFerrariExternalCarId(observedId)) {
    case 7u: return L"ExternalCars\\288gto.ovc";
    case 11u: return L"ExternalCars\\f40.ovc";
    default: return nullptr;
    }
}
static_assert(IsFerrari16CanonicalCarId(0u) &&
              IsFerrari16CanonicalCarId(14u) &&
              IsFerrari16CanonicalCarId(28u) &&
              !IsFerrari16CanonicalCarId(15u) &&
              !IsFerrari16CanonicalCarId(29u) &&
              !IsFerrari16CanonicalCarId(30u),
              "16 canonical car model IDs");
static_assert(LegacyFerrariCarSuffix(7u)!=nullptr &&
              LegacyFerrariCarSuffix(22u)!=nullptr &&
              LegacyFerrariCarSuffix(11u)!=nullptr &&
              LegacyFerrariCarSuffix(26u)!=nullptr &&
              LegacyFerrariCarSuffix(5u)==nullptr,
              "legacy GTO/F40 aliases only");
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
