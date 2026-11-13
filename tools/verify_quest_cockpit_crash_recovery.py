#!/usr/bin/env python3
"""Regression guard for QuestCockpitV2 startup and crash evidence recovery."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
startup = (root / "src/dllmain.cpp").read_text(encoding="utf-8")
crash = (root / "src/hooks_exceptions.cpp").read_text(encoding="utf-8")

assert "std::filesystem::exists(UserIniPath, userIniError)" in startup
assert "std::filesystem::exists(saveFolder, saveFolderError)" in startup
assert startup.index("InitExceptionHandler();") < startup.index("Settings::read(Module::IniPath)")
assert startup.count("\n\tInitExceptionHandler();") == 1
assert "std::filesystem::create_directories(dumpPath, directoryError)" in crash
assert "std::filesystem::copy_file(Module::LogPath, re4t_log_filename," in crash
assert "std::filesystem::copy_options::overwrite_existing, copyError)" in crash
assert "std::filesystem::exists(re4t_log_filename, logError)" in crash
assert 'required_entries_ok = false' in crash  # dump/crash.log stay required
assert "faultRegion.AllocationBase ==" in crash and "faultRegion.Type == MEM_IMAGE" in crash
assert "const bool inMainExe = faultAddress >= moduleBase" not in crash
assert "if (wchar_t* separator = wcsrchr(modulename" in crash
print("QuestCockpitV2 startup/crash-evidence guards PASS")
