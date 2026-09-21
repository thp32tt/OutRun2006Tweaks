#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <filesystem>
#include <ini.h>
#include <exception.hpp>
#include <miniz.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"

// miniz unfortunately doesn't include wchar versions of its functions, but fortunately does allow passing FILE* to it
mz_bool mz_zip_writer_add_file(mz_zip_archive* pZip, const char* pArchive_name, const wchar_t* pSrc_filename, const void* pComment, mz_uint16 comment_size, mz_uint level_and_flags)
{
  MZ_FILE* pSrc_file = NULL;
  mz_uint64 uncomp_size = 0;
  MZ_TIME_T file_modified_time;
  MZ_TIME_T* pFile_time = NULL;
  mz_bool status;

  memset(&file_modified_time, 0, sizeof(file_modified_time));

  _wfopen_s(&pSrc_file, pSrc_filename, L"rb");
  if (!pSrc_file)
    return false;

  _fseeki64(pSrc_file, 0, SEEK_END);
  uncomp_size = _ftelli64(pSrc_file);
  _fseeki64(pSrc_file, 0, SEEK_SET);

  status = mz_zip_writer_add_cfile(pZip, pArchive_name, pSrc_file, uncomp_size, pFile_time, pComment, comment_size, level_and_flags, NULL, 0, NULL, 0);

  fclose(pSrc_file);

  return status;
}

LONG WINAPI CustomUnhandledExceptionFilter(LPEXCEPTION_POINTERS ExceptionInfo)
{
    wchar_t     modulename[MAX_PATH];
    wchar_t     dump_filename[MAX_PATH];
    wchar_t     crash_log_filename[MAX_PATH];
    wchar_t     re4t_log_filename[MAX_PATH];
    wchar_t     save_filename[MAX_PATH];
    wchar_t     zip_filename[MAX_PATH];
    wchar_t     timestamp[128];
    wchar_t*    modulenameptr{};
    bool        bDumpSuccess = false;
    __time64_t  time;
    struct tm   ltime;
    HWND        hWnd;
    HANDLE      hFile;

    // Write minidump
    if (GetModuleFileNameW(GetModuleHandle(NULL), modulename, _countof(modulename)) != 0)
    {
        modulenameptr = wcsrchr(modulename, '\\');
        *modulenameptr = L'\0';
        modulenameptr += 1;
    }
    else
    {
        modulenameptr = (wchar_t*)L"err.err";
    }

    _time64(&time);
    _localtime64_s(&ltime, &time);
    wcsftime(timestamp, _countof(timestamp), L"%Y%m%d%H%M%S", &ltime);
    swprintf_s(dump_filename, L"%s\\%s\\%s.%s.dmp", modulename, L"CrashDumps", modulenameptr, timestamp);

    hFile = CreateFileW(dump_filename, GENERIC_WRITE, FILE_SHARE_WRITE, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);

    if (hFile != INVALID_HANDLE_VALUE)
    {
        MINIDUMP_EXCEPTION_INFORMATION ex;
        memset(&ex, 0, sizeof(ex));
        ex.ThreadId = GetCurrentThreadId();
        ex.ExceptionPointers = ExceptionInfo;
        ex.ClientPointers = TRUE;

        bDumpSuccess =
            MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), hFile,
                MiniDumpWithDataSegs, &ex, NULL, NULL) != FALSE;

        CloseHandle(hFile);
    }

    // Logs exception into buffer and writes to file
    swprintf_s(crash_log_filename, L"%s\\%s\\%s.%s.log", modulename, L"CrashDumps", modulenameptr, timestamp);
    hFile = CreateFileW(crash_log_filename, GENERIC_WRITE, FILE_SHARE_WRITE, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);

    if (hFile != INVALID_HANDLE_VALUE)
    {
        auto Log = [ExceptionInfo, hFile](char* buffer, size_t size, bool reg, bool stack, bool trace)
        {
            if (LogException(buffer, size, (LPEXCEPTION_POINTERS)ExceptionInfo, reg, stack, trace))
            {
                // Write log file
                DWORD NumberOfBytesWritten = 0;
                WriteFile(hFile, buffer, strlen(buffer), &NumberOfBytesWritten, NULL);
            }
        };

        // Try to make a very descriptive exception, for that we need to malloc a huge buffer...
        if (auto buffer = (char*)malloc(max_logsize_ever))
        {
            Log(buffer, max_logsize_ever, true, true, true);
            free(buffer);
        }
        else
        {
            // Use a static buffer, no need for any allocation
            static const auto size = max_logsize_basic + max_logsize_regs + max_logsize_stackdump;
            static char static_buf[size];
            static_assert(size <= max_static_buffer, "Static buffer is too big");

            Log(buffer = static_buf, sizeof(static_buf), true, true, false);
        }
        CloseHandle(hFile);
    }

    // Copy re4_tweaks log file to CrashDumps
    {
        swprintf_s(re4t_log_filename, L"%s\\%s\\OutRun2006Tweaks.log", modulename, L"CrashDumps");

        if (std::filesystem::exists(Module::LogPath))
            std::filesystem::copy_file(Module::LogPath, re4t_log_filename);
    }

    bool zip_created = false;

    // ZIP up the dump/log/save
    {
      swprintf_s(zip_filename, L"%s\\%s\\%s.%s.zip", modulename, L"CrashDumps", modulenameptr, timestamp);

      FILE* zip_file = nullptr;
      if (_wfopen_s(&zip_file, zip_filename, L"wb") == 0 && zip_file)
      {
        mz_zip_archive zip_archive;
        mz_zip_zero_struct(&zip_archive);
        if (mz_zip_writer_init_cfile(&zip_archive, zip_file, 3))
        {
          // Required crash evidence must all be present, but success is not
          // published until archive finalization, writer teardown, and the
          // underlying FILE flush/close have also succeeded.
          bool required_entries_ok = bDumpSuccess;

          // A created file is not proof that MiniDumpWriteDump completed.
          // Never publish a crash ZIP as valid when the required minidump
          // failed and left an empty or partial file behind.
          if (bDumpSuccess &&
              !mz_zip_writer_add_file(&zip_archive, "dump.dmp", dump_filename, nullptr, 0, 3))
            required_entries_ok = false;
          if (!mz_zip_writer_add_file(&zip_archive, "crash.log", crash_log_filename, nullptr, 0, 3))
            required_entries_ok = false;
          if (!mz_zip_writer_add_file(&zip_archive, "OutRun2006Tweaks.log", re4t_log_filename, nullptr, 0, 3))
            required_entries_ok = false;

          // VR diagnostics are optional. A crash can happen while one of these
          // files is still open, so an optional add failure must never suppress
          // the primary dump/log archive.
          auto add_optional_vr_file = [&zip_archive](const char* archive_name,
              const std::filesystem::path& source)
          {
            if (!std::filesystem::exists(source) ||
                !std::filesystem::is_regular_file(source))
              return;
            const std::wstring wide = source.wstring();
            mz_zip_writer_add_file(&zip_archive, archive_name, wide.c_str(),
              nullptr, 0, 3);
          };

          const std::filesystem::path game_dir = Module::ExePath.parent_path();
          add_optional_vr_file("vr/OutRun2006Tweaks-hudtrace.csv",
            game_dir / "OutRun2006Tweaks-hudtrace.csv");
          add_optional_vr_file("vr/OutRun2006Tweaks-xstmap.csv",
            game_dir / "OutRun2006Tweaks-xstmap.csv");
          add_optional_vr_file("vr/CURRENT_VR_SESSION.json",
            game_dir / "CURRENT_VR_SESSION.json");
          add_optional_vr_file("vr/ACTIVE_VR_BACKEND.txt",
            game_dir / "ACTIVE_VR_BACKEND.txt");
          add_optional_vr_file("vr/BUILD_INPUTS.json",
            game_dir / "BUILD_INPUTS.json");

          try
          {
            for (const auto& entry :
                std::filesystem::directory_iterator(game_dir))
            {
              if (!entry.is_regular_file())
                continue;
              const std::string name = entry.path().filename().string();
              if (name.starts_with("outrun-vr-host") &&
                  entry.path().extension() == ".log")
                add_optional_vr_file(("vr/" + name).c_str(), entry.path());
              else if (name.starts_with("outrun-vr-watchdog") &&
                       entry.path().extension() == ".log")
                add_optional_vr_file(("vr/" + name).c_str(), entry.path());
            }
          }
          catch (...) {}

          const bool finalized =
            mz_zip_writer_finalize_archive(&zip_archive) != 0;
          const bool ended = mz_zip_writer_end(&zip_archive) != 0;
          const bool closed = fclose(zip_file) == 0;
          zip_file = nullptr;
          zip_created =
            required_entries_ok && finalized && ended && closed;
        }
        if (zip_file)
          fclose(zip_file);
      }

      if (zip_created)
      {
        DeleteFileW(dump_filename);
        DeleteFileW(crash_log_filename);
        DeleteFileW(re4t_log_filename);
      }
    }

    // Exit the application
    wchar_t	error[1024];
    if (zip_created)
      swprintf_s(error, L"Fatal error (0x%08X) at 0x%08X.\n\nA crash log has been saved to \"%s\".", (int)ExceptionInfo->ExceptionRecord->ExceptionCode, (int)ExceptionInfo->ExceptionRecord->ExceptionAddress, zip_filename);
    else
      swprintf_s(error, L"Fatal error (0x%08X) at 0x%08X.\n\nThe crash ZIP could not be finalized. Loose dump/log files were kept in the CrashDumps folder.", (int)ExceptionInfo->ExceptionRecord->ExceptionCode, (int)ExceptionInfo->ExceptionRecord->ExceptionAddress);
    MessageBoxW(NULL, error, L"OutRun2006Tweaks", MB_ICONERROR | MB_OK);

    ShowCursor(TRUE);
    hWnd = FindWindowW(0, L"");
    SetForegroundWindow(hWnd);

    return EXCEPTION_CONTINUE_SEARCH;
}

void InitExceptionHandler()
{
    std::filesystem::path dumpPath = Module::ExePath.parent_path() / L"CrashDumps";

    if (!std::filesystem::exists(dumpPath))
        std::filesystem::create_directories(dumpPath);

    SetUnhandledExceptionFilter(CustomUnhandledExceptionFilter);

    // Now stub out SetUnhandledExceptionFilter so NO ONE ELSE can set it!
    Memory::VP::Patch(&SetUnhandledExceptionFilter, { 0xC2, 0x04, 0x00 });
}