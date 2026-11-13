#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <shellapi.h>
#include <filesystem>
#include <cwchar>

#include "hook_mgr.hpp"
#include "resource.h"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/ipc/shadow_lifetime_bridge.hpp"

void InitExceptionHandler(); // hooks_exceptions.cpp

namespace Module
{
	constexpr std::string_view TargetFilename = "OR2006C2C.exe";

	constexpr std::string_view IniFileName = "OutRun2006Tweaks.ini";
	constexpr std::string_view UserIniFileName = "OutRun2006Tweaks.user.ini";
	constexpr std::string_view LodIniFileName = "OutRun2006Tweaks.lods.ini";
	constexpr std::string_view OverlayIniFileName = "OutRun2006Tweaks.overlay.ini";
	constexpr std::string_view BindingsIniFileName = "OutRun2006Tweaks.input.ini";
	constexpr std::string_view LogFileName = "OutRun2006Tweaks.log";

	void init()
	{
		if (!DllHandle)
			return;

		ExeHandle = GetModuleHandle(nullptr);

		// Fetch paths of the DLL & EXE
		DllPath = Util::GetModuleFilePath(DllHandle);
		ExePath = Util::GetModuleFilePath(ExeHandle);

		// Setup Log & INI paths, always located next to the DLL instead of the EXE
		auto dllParent = DllPath.parent_path();
		LogPath = dllParent / LogFileName;
		IniPath = dllParent / IniFileName;
		UserIniPath = dllParent / UserIniFileName;
		LodIniPath = dllParent / LodIniFileName;
		OverlayIniPath = dllParent / OverlayIniFileName;
		BindingsIniPath = dllParent / BindingsIniFileName;

		Game::init();
	}

	static bool ParseIniBool(const wchar_t* text, bool fallback) noexcept
	{
		if (!text || !*text)
			return fallback;
		if (!_wcsicmp(text, L"true") || !_wcsicmp(text, L"yes") || !wcscmp(text, L"1"))
			return true;
		if (!_wcsicmp(text, L"false") || !_wcsicmp(text, L"no") || !wcscmp(text, L"0"))
			return false;
		return fallback;
	}

	static bool ReadIniBool(const std::filesystem::path& path,
		const wchar_t* section, const wchar_t* key, bool fallback) noexcept
	{
		const wchar_t* fallbackText = fallback ? L"true" : L"false";
		wchar_t value[16]{};
		GetPrivateProfileStringW(section, key, fallbackText, value,
			static_cast<DWORD>(std::size(value)), path.c_str());
		return ParseIniBool(value, fallback);
	}

	bool FileLoggingEnabled() noexcept
	{
		bool enabled = ReadIniBool(IniPath, L"VR", L"FileLogging", true);
		// A missing/inaccessible user INI must not throw from this noexcept
		// startup policy function (otherwise std::terminate is invoked).
		std::error_code userIniError;
		if (std::filesystem::exists(UserIniPath, userIniError) && !userIniError)
			enabled = ReadIniBool(UserIniPath, L"VR", L"FileLogging", enabled);

		wchar_t env[16]{};
		const DWORD envLen = GetEnvironmentVariableW(
			L"OUTRUN_VR_FILE_LOG", env, static_cast<DWORD>(std::size(env)));
		if (envLen > 0 && envLen < std::size(env))
			enabled = ParseIniBool(env, enabled);
		return enabled;
	}

	// Release packages are deliberately dual-entrypoint:
	//   OR2006C2C.exe           -> normal 2D
	//   Start-OutRun-VR.cmd     -> explicit VR opt-in
	// Development/test payloads do not contain VR_RELEASE_VERSION.txt and keep
	// their historical INI-driven behaviour.
	bool ReleasePackageVrLaunchRequested() noexcept
	{
		const auto marker = DllPath.parent_path() / "VR_RELEASE_VERSION.txt";
		if (GetFileAttributesW(marker.c_str()) == INVALID_FILE_ATTRIBUTES)
			return true;

		wchar_t env[16]{};
		const DWORD envLen = GetEnvironmentVariableW(
			L"OUTRUN_VR_LAUNCH", env, static_cast<DWORD>(std::size(env)));
		return envLen > 0 && envLen < std::size(env) &&
			ParseIniBool(env, false);
	}

	void to_log()
	{
		// Print some info about the users setup to log, can come in useful for debugging issues
		spdlog::info("EXE module (base address: {:p}):", fmt::ptr(ExeHandle));
		spdlog::info("  File path: {}", ExePath.string());
		spdlog::info("  Header timestamp: {}", Util::GetModuleTimestamp(ExeHandle));
		spdlog::info("DLL module (base address: {:p}):", fmt::ptr(DllHandle));
		spdlog::info("  File path: {}", DllPath.string());
	}
};

void Plugin_Init()
{
	// Establish paths and the crash handler BEFORE settings/FFB/VR hooks.
	// A malformed or inaccessible configuration can fail during startup too.
	Module::init();
	InitExceptionHandler();

	// spdlog setup
	{
		std::vector<spdlog::sink_ptr> sinks;
		sinks.push_back(std::make_shared<spdlog::sinks::msvc_sink_mt>(true)); // Print logs to debug output
		if (Module::FileLoggingEnabled())
		{
			try
			{
				sinks.push_back(std::make_shared<spdlog::sinks::basic_file_sink_mt>(Module::LogPath.string(), true));
			}
			catch (const std::exception&)
			{
				// spdlog failed to open log file for writing (happens in some WinStore apps)
				// let's just try to continue instead of crashing
			}
		}

		auto combined_logger = std::make_shared<spdlog::logger>("", begin(sinks), end(sinks));
		const bool diagnosticsEnabled = Module::FileLoggingEnabled();
#ifdef _DEBUG
		combined_logger->set_level(diagnosticsEnabled
			? spdlog::level::debug : spdlog::level::off);
#else
		combined_logger->set_level(diagnosticsEnabled
			? spdlog::level::debug : spdlog::level::off);
#endif
		spdlog::set_default_logger(combined_logger);
		if (diagnosticsEnabled)
			spdlog::flush_on(spdlog::level::debug);

	}

	spdlog::info("OutRun2006Tweaks v" MODULE_VERSION_STR " - github.com/emoose/OutRun2006Tweaks");
	Module::to_log();

	if (!Settings::read(Module::IniPath))
		spdlog::error("Settings::read - Launching game with default OR2006Tweaks INI settings!");

	// Anything past this point counts as an override, and is what gets written
	// back out to the user INI.
	Settings::mark_base_values();

	std::error_code userSettingsError;
	if (std::filesystem::exists(Module::UserIniPath, userSettingsError) &&
		!userSettingsError)
		Settings::read(Module::UserIniPath);
	else if (userSettingsError)
		spdlog::warn("User INI access failed during startup; continuing with base settings.");

	int argc;
	LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
	if (argv)
	{
		bool changed = Settings::read_cmd_line(argc, argv);
		LocalFree(argv);
		if (changed)
		{
			// F11 changes must persist; Settings::write excludes every launch-only
			// command-line override rather than disabling the entire user INI.
			spdlog::info("Command-line overrides active: unrelated F11 settings remain writable; overridden keys excluded.");
		} 
	}

	// A release package must never enter VR simply because the shipped INI or a
	// stale OutRun2006Tweaks.user.ini still says Enabled=true. Only the release
	// launcher sets OUTRUN_VR_LAUNCH=1; direct EXE launch is therefore forced to
	// the original 2D path before any hook decides whether VR is active.
	if (!Module::ReleasePackageVrLaunchRequested())
	{
		Settings::VREnabled = false;
		spdlog::info(
			"VR release entrypoint policy: direct OR2006C2C.exe launch uses 2D; "
			"use Start-OutRun-VR.cmd for VR.");
	}

	if (Settings::UseNewInput)
	{
		spdlog::info("Wheel input: multi-device SDL raw input enabled; legacy DirectInput helpers remain inactive fallback");
	}
	else if (Settings::WheelInputCompatibility)
	{
		spdlog::info("Wheel input: legacy DirectInput compatibility fallback enabled");
	}

	Settings::to_log();

	Game::StartupTime = std::chrono::system_clock::now();

	// Create save folder if it doesn't exist, otherwise game will have issues writing savegame...
	auto saveFolder = Module::ExePath.parent_path() / "SaveGame";
	std::error_code saveFolderError;
	if (!std::filesystem::exists(saveFolder, saveFolderError))
	{
		spdlog::warn("Plugin_Init: SaveGame folder doesn't exist, trying to create it...");
		try
		{
			std::filesystem::create_directory(saveFolder);
			spdlog::info("Plugin_Init: SaveGame folder created");
		}
		catch (const std::exception&)
		{
			spdlog::error("Plugin_Init: Failed to create SaveGame folder (may require permissions?) - game might have issues writing savegame!");
		}
	}

	HookManager::ApplyHooks();

	// Hooks declare which settings they read as they apply, so the snapshot and
	// the no-consumer check both have to wait until they've all run.
	Settings::mark_startup_values();
}

#include "Proxy.hpp"

BOOL APIENTRY DllMain(HMODULE hModule, int ul_reason_for_call, LPVOID lpReserved)
{
	DisableThreadLibraryCalls(hModule);

	if (ul_reason_for_call == DLL_PROCESS_ATTACH)
	{
		Module::DllHandle = hModule;
		proxy::on_attach(Module::DllHandle);

		static std::once_flag flag;
		std::call_once(flag, Plugin_Init);
	}
	else if (ul_reason_for_call == DLL_PROCESS_DETACH)
	{
		OutRunVR::IpcV3::RequestRegisteredShadowBridgeStop();
		proxy::on_detach();
	}

	return TRUE;
}