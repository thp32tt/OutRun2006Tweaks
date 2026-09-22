from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "src/hooks_exceptions.cpp").read_text(encoding="utf-8")

required = (
    "bool        bDumpSuccess = false;",
    "bDumpSuccess = MiniDumpWriteDump(",
    "bool required_entries_ok = bDumpSuccess;",
)
for marker in required:
    if marker not in src:
        raise SystemExit(f"CRASH-MINIDUMP-WRITE-VALIDITY-001 missing invariant: {marker}")

if "if (!(MiniDumpWriteDump(" in src:
    raise SystemExit("CRASH-MINIDUMP-WRITE-VALIDITY-001 legacy unchecked MiniDumpWriteDump path remains")

print("CRASH-MINIDUMP-WRITE-VALIDITY-001: PASS")
