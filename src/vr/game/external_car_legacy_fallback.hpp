#pragma once
// Win32 GetFileAttributesW: only a genuinely absent canonical file may
// select the old 288gto.ovc/f40.ovc identity. Permission, sharing, device
// errors and an existing DIRECTORY are not "file missing" and must fail closed.
// Pure contract stays portable for the 16-car runtime regression.
namespace OutRunVR::DinoSidecar {
constexpr unsigned kWin32FileNotFound=2u; // ERROR_FILE_NOT_FOUND
constexpr unsigned kWin32PathNotFound=3u; // ERROR_PATH_NOT_FOUND
constexpr bool LegacyFallbackForMissingCanonical(
    bool querySucceeded,unsigned errorCode) noexcept
{
    return !querySucceeded &&
        (errorCode==kWin32FileNotFound ||
         errorCode==kWin32PathNotFound);
}
static_assert(LegacyFallbackForMissingCanonical(false,kWin32FileNotFound));
static_assert(LegacyFallbackForMissingCanonical(false,kWin32PathNotFound));
static_assert(!LegacyFallbackForMissingCanonical(true,kWin32FileNotFound));
static_assert(!LegacyFallbackForMissingCanonical(false,5u)); // access denied
} // namespace OutRunVR::DinoSidecar
