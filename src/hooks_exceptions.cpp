#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <filesystem>
#include <limits>
#include <system_error>
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
    wchar_t     crash_signature_filename[MAX_PATH];
    wchar_t     re4t_log_filename[MAX_PATH];
    wchar_t     save_filename[MAX_PATH];
    wchar_t     zip_filename[MAX_PATH];
    wchar_t     timestamp[128];
    wchar_t*    modulenameptr{};
    bool        bDumpSuccess = false;
    bool        crashLogWriteSuccess = false;
    bool        re4tLogSnapshotReady = false;
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

        if (!CloseHandle(hFile))
            bDumpSuccess = false;
    }

    // Logs exception into buffer and writes to file
    swprintf_s(crash_log_filename, L"%s\\%s\\%s.%s.log", modulename, L"CrashDumps", modulenameptr, timestamp);
    hFile = CreateFileW(crash_log_filename, GENERIC_WRITE, FILE_SHARE_WRITE, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);

    if (hFile != INVALID_HANDLE_VALUE)
    {
        auto Log = [ExceptionInfo, hFile](char* buffer, size_t size, bool reg, bool stack, bool trace) noexcept
        {
            try
            {
                if (!LogException(buffer, size, (LPEXCEPTION_POINTERS)ExceptionInfo, reg, stack, trace))
                    return false;

                const size_t requested = strlen(buffer);
                if (requested == 0 ||
                    requested > static_cast<size_t>((std::numeric_limits<DWORD>::max)()))
                    return false;

                DWORD NumberOfBytesWritten = 0;
                return WriteFile(hFile, buffer, static_cast<DWORD>(requested),
                    &NumberOfBytesWritten, NULL) != FALSE &&
                    NumberOfBytesWritten == requested;
            }
            catch (...)
            {
                return false;
            }
        };

        bool logContentWritten = false;

        // Try to make a very descriptive exception, for that we need to malloc a huge buffer...
        if (auto buffer = (char*)malloc(max_logsize_ever))
        {
            logContentWritten =
                Log(buffer, max_logsize_ever, true, true, true);
            free(buffer);
        }
        else
        {
            // Use a static buffer, no need for any allocation
            static const auto size = max_logsize_basic + max_logsize_regs + max_logsize_stackdump;
            static char static_buf[size];
            static_assert(size <= max_static_buffer, "Static buffer is too big");

            logContentWritten =
                Log(static_buf, sizeof(static_buf), true, true, false);
        }

        const bool crashLogClosed = CloseHandle(hFile) != FALSE;
        crashLogWriteSuccess =
            logContentWritten && crashLogClosed;
    }

    // Write a compact machine-readable crash signature. The absolute address
    // alone is unstable across ASLR, so preserve the OR2006C2C.exe-relative
    // RVA when the fault belongs to the main executable. Offline analysis can
    // then join this directly to docs/VR_BINARY_CONTRACT.json.
    swprintf_s(crash_signature_filename, L"%s\\%s\\%s.%s.signature.json",
        modulename, L"CrashDumps", modulenameptr, timestamp);
    {
        HANDLE signatureFile = CreateFileW(crash_signature_filename,
            GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL, NULL);
        if (signatureFile != INVALID_HANDLE_VALUE)
        {
            const uintptr_t moduleBase =
                reinterpret_cast<uintptr_t>(GetModuleHandleW(NULL));
            const uintptr_t faultAddress = reinterpret_cast<uintptr_t>(
                ExceptionInfo->ExceptionRecord->ExceptionAddress);
            const bool inMainExe = faultAddress >= moduleBase;
            const uintptr_t exeRva = inMainExe ?
                (faultAddress - moduleBase) : 0;

            char signatureJson[768]{};
            sprintf_s(signatureJson,
                "{\n"
                "  \"schemaVersion\": 1,\n"
                "  \"exceptionCode\": \"0x%08X\",\n"
                "  \"absoluteAddress\": \"0x%p\",\n"
                "  \"moduleBase\": \"0x%p\",\n"
                "  \"module\": \"OR2006C2C.EXE\",\n"
                "  \"faultInMainExe\": %s,\n"
                "  \"exeRva\": \"0x%08llX\",\n"
                "  \"threadId\": %lu\n"
                "}\n",
                static_cast<unsigned>(
                    ExceptionInfo->ExceptionRecord->ExceptionCode),
                ExceptionInfo->ExceptionRecord->ExceptionAddress,
                reinterpret_cast<void*>(moduleBase),
                inMainExe ? "true" : "false",
                static_cast<unsigned long long>(exeRva),
                static_cast<unsigned long>(GetCurrentThreadId()));

            DWORD written = 0;
            WriteFile(signatureFile, signatureJson,
                static_cast<DWORD>(strlen(signatureJson)), &written, NULL);
            FlushFileBuffers(signatureFile);
            CloseHandle(signatureFile);
        }
    }

    // Snapshot the tweaks log without allowing filesystem/path-construction
    // failures to escape from the unhandled-exception filter. Use a per-crash
    // destination so evidence retained after an earlier failed ZIP is preserved.
    try
    {
        std::error_code source_ec;
        if (std::filesystem::is_regular_file(Module::LogPath, source_ec) &&
            !source_ec)
        {
            for (unsigned suffix = 0; suffix < 100; ++suffix)
            {
                if (suffix == 0)
                    swprintf_s(re4t_log_filename,
                        L"%s\\%s\\OutRun2006Tweaks.%s.log",
                        modulename, L"CrashDumps", timestamp);
                else
                    swprintf_s(re4t_log_filename,
                        L"%s\\%s\\OutRun2006Tweaks.%s.%u.log",
                        modulename, L"CrashDumps", timestamp, suffix);

                const std::filesystem::path snapshotPath(re4t_log_filename);

                std::error_code exists_ec;
                if (std::filesystem::exists(snapshotPath, exists_ec))
                {
                    if (exists_ec)
                        break;
                    continue;
                }
                if (exists_ec)
                    break;

                std::error_code copy_ec;
                re4tLogSnapshotReady = std::filesystem::copy_file(
                    Module::LogPath,
                    snapshotPath,
                    std::filesystem::copy_options::none,
                    copy_ec);
                if (re4tLogSnapshotReady)
                    break;

                // Retry only if another writer won the destination-name race.
                std::error_code collision_ec;
                if (!std::filesystem::exists(snapshotPath, collision_ec) ||
                    collision_ec)
                    break;
            }
        }
    }
    catch (...)
    {
        re4tLogSnapshotReady = false;
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
          bool required_entries_ok =
            bDumpSuccess && crashLogWriteSuccess && re4tLogSnapshotReady;

          if (bDumpSuccess &&
              !mz_zip_writer_add_file(&zip_archive, "dump.dmp", dump_filename, nullptr, 0, 3))
            required_entries_ok = false;
          if (crashLogWriteSuccess &&
              !mz_zip_writer_add_file(&zip_archive, "crash.log", crash_log_filename, nullptr, 0, 3))
            required_entries_ok = false;
          if (re4tLogSnapshotReady &&
              !mz_zip_writer_add_file(&zip_archive, "OutRun2006Tweaks.log", re4t_log_filename, nullptr, 0, 3))
            required_entries_ok = false;

          // VR diagnostics are optional. Keep every path construction,
          // metadata lookup and directory traversal behind a no-throw boundary
          // so optional evidence can never abort the primary crash archive.
          try
          {
            auto add_optional_vr_file = [&zip_archive](const char* archive_name,
                const std::filesystem::path& source) noexcept
            {
              try
              {
                std::error_code metadata_ec;
                if (!std::filesystem::is_regular_file(source, metadata_ec) ||
                    metadata_ec)
                  return;
                const std::wstring wide = source.wstring();
                mz_zip_writer_add_file(&zip_archive, archive_name, wide.c_str(),
                  nullptr, 0, 3);
              }
              catch (...) {}
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
            add_optional_vr_file("crash_signature.json",
              crash_signature_filename);

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
        DeleteFileW(crash_signature_filename);
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