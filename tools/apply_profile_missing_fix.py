from pathlib import Path

p = Path('src/wheel_profile_store.hpp')
text = p.read_text(encoding='utf-8')

old = '''        auto backup = finalPath;
        backup += ".bak";
        std::error_code ec;

        bool finalExists = std::filesystem::is_regular_file(finalPath, ec);
        if (ec)
        {
            if (error) *error = "Could not inspect the existing profile: " + ec.message();
            return false;
        }

        // Recover a previous interrupted replacement before starting another.
        if (!finalExists && std::filesystem::is_regular_file(backup, ec) && !ec)
        {
            std::filesystem::rename(backup, finalPath, ec);
            if (ec)
            {
                if (error) *error = "Could not recover the previous profile backup: " + ec.message();
                return false;
            }
            finalExists = true;
        }
        else if (ec)
        {
            if (error) *error = "Could not inspect the profile backup: " + ec.message();
            return false;
        }
'''

new = '''        auto backup = finalPath;
        backup += ".bak";
        std::error_code ec;

        // MSVC's std::filesystem::is_regular_file(path, ec) can report
        // ERROR_FILE_NOT_FOUND through ec for a path that simply does not exist.
        // A missing destination/backup is the normal first-save case, not an error.
        const auto inspect_regular_file = [&](const std::filesystem::path& path,
                                              bool& exists,
                                              const char* label) -> bool
        {
            ec.clear();
            exists = std::filesystem::is_regular_file(path, ec);
            if (ec == std::errc::no_such_file_or_directory)
            {
                ec.clear();
                exists = false;
                return true;
            }
            if (ec)
            {
                if (error) *error = std::string("Could not inspect ") + label + ": " + ec.message();
                return false;
            }
            return true;
        };

        bool finalExists = false;
        if (!inspect_regular_file(finalPath, finalExists, "the existing profile"))
            return false;

        bool backupExists = false;
        if (!inspect_regular_file(backup, backupExists, "the profile backup"))
            return false;

        // Recover a previous interrupted replacement before starting another.
        if (!finalExists && backupExists)
        {
            std::filesystem::rename(backup, finalPath, ec);
            if (ec)
            {
                if (error) *error = "Could not recover the previous profile backup: " + ec.message();
                return false;
            }
            finalExists = true;
        }
'''

if old not in text:
    raise SystemExit('commit_staged_profile inspection block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

vpath = Path('tools/verify_wheel_ffb_current.py')
v = vpath.read_text(encoding='utf-8')
extra = '''\n# first-save profile regression guards\nreq(profiles, 'ec == std::errc::no_such_file_or_directory', 'missing profile is a normal first-save state')\nreq(profiles, 'inspect_regular_file(finalPath, finalExists, "the existing profile")', 'final profile existence check uses missing-safe helper')\nreq(profiles, 'inspect_regular_file(backup, backupExists, "the profile backup")', 'backup existence check uses missing-safe helper')\nforbid(profiles, 'if (!finalExists && std::filesystem::is_regular_file(backup, ec) && !ec)', 'backup probe no longer treats missing backup as filesystem failure')\n'''
if '# first-save profile regression guards' not in v:
    v += extra
vpath.write_text(v, encoding='utf-8')
