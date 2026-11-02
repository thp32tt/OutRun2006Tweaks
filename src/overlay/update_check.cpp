#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <json/json.h>
#include <string>
#include <string_view>
#include <charconv>
#include <cstdint>
#include <system_error>
#include <exception>
#include <iostream>
#include "plugin.hpp"
#include <spdlog/spdlog.h>
#include "notifications.hpp"
#include "overlay.hpp"
#include "input_manager.hpp"
#include "resource.h"

namespace
{
	constexpr char UpdateRepoOwner[] = "thp32tt";
	constexpr char UpdateRepoName[] = "OutRun2006Tweaks";
	constexpr char UpdateReleasesUrl[] = "https://github.com/thp32tt/OutRun2006Tweaks/releases";
}

// Release tags are untrusted network data. The VR fork publishes tags such
// as "vr-v0.01-beta", not just numeric "v0.2" tags. Never use throwing stoi
// on these strings: UpdateCheck_Thread is a detached std::thread and an
// escaping std::invalid_argument would terminate the entire game process.
static bool TryParseNumericReleaseVersion(
    std::string_view version, std::uint64_t& numeric) noexcept
{
    numeric = 0;
    if (version.starts_with('v'))
        version.remove_prefix(1);
    if (version.empty())
        return false;

    // Reject different release channels / prerelease labels rather than
    // comparing a VR beta to the current wheel/Tweaks version.
    for (unsigned componentIndex = 0; componentIndex < 4; ++componentIndex)
    {
        const auto dot = version.find('.');
        const auto part = version.substr(0, dot);
        if (part.empty())
            return false;
        unsigned component = 0;
        const auto* const first = part.data();
        const auto* const last = first + part.size();
        const auto parsed = std::from_chars(first, last, component, 10);
        if (parsed.ec != std::errc{} || parsed.ptr != last ||
            component > 0xffffu)
            return false;
        numeric |= static_cast<std::uint64_t>(component)
            << ((3 - componentIndex) * 16);
        if (dot == std::string_view::npos)
            return true;
        version.remove_prefix(dot + 1);
    }
    return false; // More than four version components.
}

std::string UpdateCheck_IsNewerAvailable(const std::string& currentVersion, const std::string& repoOwner, const std::string& repoName)
{
	std::wstring path = L"/repos/" + std::wstring(repoOwner.begin(), repoOwner.end()) +
		L"/" + std::wstring(repoName.begin(), repoName.end()) + L"/releases/latest";

	std::string jsonResponse = Util::HttpGetRequest("api.github.com", path, 443);
	if (jsonResponse.empty())
	{
		spdlog::error("UpdateCheck_IsNewerAvailable: Failed to fetch the latest release information");
		return "";
	}

	Json::CharReaderBuilder builder;
	Json::Value root;
	std::string errs;

	std::istringstream stream(jsonResponse);
	if (!Json::parseFromStream(builder, stream, &root, &errs))
	{
		spdlog::error("UpdateCheck_IsNewerAvailable: JSON parsing error: " + errs);
		return "";
	}

	std::string latestVersion = root["tag_name"].asString();
	if (latestVersion.empty())
	{
		spdlog::error("UpdateCheck_IsNewerAvailable: Invalid JSON: Missing 'tag_name'.");
		return "";
	}

    std::uint64_t latestNumeric = 0;
    std::uint64_t currentNumeric = 0;
    if (!TryParseNumericReleaseVersion(latestVersion, latestNumeric) ||
        !TryParseNumericReleaseVersion(currentVersion, currentNumeric))
    {
        spdlog::info(
            "UpdateCheck_IsNewerAvailable: unsupported or incompatible release tag '{}'; skip notification safely",
            latestVersion);
        return "";
    }

	if (latestNumeric > currentNumeric)
	{
		spdlog::info("UpdateCheck_IsNewerAvailable: newer version {} available, current version {}", latestVersion, currentVersion);
		return latestVersion;
	}
	else
	{
		spdlog::info("UpdateCheck_IsNewerAvailable: latest version {} matches current version {}", latestVersion, currentVersion);
		return "";
	}
}

// Never allow HTTP, JSON, allocation or notification exceptions to escape
// a detached std::thread. Escaping exceptions invoke std::terminate and have
// previously surfaced as 0xC0000409 FAST_FAIL_FATAL_APP_EXIT in the game.
void UpdateCheck_Thread(const std::string& currentVersion, const std::string& repoOwner, const std::string& repoName) noexcept
{
    try
    {
        std::string newerVersion = UpdateCheck_IsNewerAvailable(currentVersion, repoOwner, repoName);
        if (!newerVersion.empty())
        {
            Notifications::instance.add(
                std::format("A newer version of OutRun2006Tweaks is available ({})\\n---\\nPress {} and click here to visit this fork's release page.",
                    newerVersion, InputManager_ModActionDisplayName(ModAction::OverlayToggle)),
                20,
                []() {
                    ShellExecuteA(nullptr, "open", UpdateReleasesUrl, nullptr, nullptr, SW_SHOWNORMAL);
                });
        }
    }
    catch (const std::exception& e)
    {
        try { spdlog::warn("UpdateCheck_Thread: update check failed safely: {}", e.what()); }
        catch (...) {}
    }
    catch (...)
    {
        try { spdlog::warn("UpdateCheck_Thread: unexpected update-check failure; skipped safely"); }
        catch (...) {}
    }
}

std::thread updateCheckThread;

void UpdateCheck_Init()
{
	if (Overlay::NotifyUpdateCheck)
	{
		// This fork carries wheel/FFB and VR changes that are not represented by
		// upstream emoose releases, so update notifications must never direct a
		// user to an incompatible upstream payload.
		updateCheckThread = std::thread(&UpdateCheck_Thread,
			MODULE_VERSION_STR, UpdateRepoOwner, UpdateRepoName);
		updateCheckThread.detach();
	}
}
