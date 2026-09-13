from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src/hooks_wheel_ffb.cpp"
VERIFIER = ROOT / "tools/verify_wheel_ffb_current.py"

old_loop = '''                bool ready = false;
                constexpr size_t MaxInterfaceProbes = 16;
                for (size_t probe = 0; probe < MaxInterfaceProbes && !ready; ++probe)
                {
                    const size_t failedBefore = active_failed_interface_count();
                    ready = initialize();
                    if (ready)
                        break;

                    const size_t failedAfter = active_failed_interface_count();
                    if (failedAfter <= failedBefore)
                        break;

                    spdlog::info(
                        "WheelFFB: FFB interface failed validation; probing the next compatible interface immediately ({}/{})",
                        failedAfter, MaxInterfaceProbes);
                }
'''

new_loop = '''                bool ready = false;
                size_t failedBefore = active_failed_interface_count();
                while (!ready)
                {
                    ready = initialize();
                    if (ready)
                        break;

                    const size_t failedAfter = active_failed_interface_count();
                    if (failedAfter <= failedBefore)
                        break;

                    // Every compatibility failure adds one previously unseen GUID
                    // to failedInterfaces_. That monotonic progress makes this
                    // exhaustive without an arbitrary device-count limit, while
                    // transient failures that do not quarantine a GUID break out.
                    failedBefore = failedAfter;
                    spdlog::info(
                        "WheelFFB: FFB interface failed validation; probing the next compatible interface immediately ({} rejected this cycle)",
                        failedAfter);
                }
'''

source = SOURCE.read_text(encoding="utf-8")
if source.count(old_loop) != 1:
    raise SystemExit(f"source loop match count was {source.count(old_loop)}, expected 1")
source = source.replace(old_loop, new_loop, 1)
if "MaxInterfaceProbes" in source:
    raise SystemExit("MaxInterfaceProbes remained after patch")
if source.count("{") != source.count("}"):
    raise SystemExit("source brace balance failed")
SOURCE.write_text(source, encoding="utf-8", newline="\n")

anchor = "req(ffb, 'active_failed_interface_count()', 'FFB backend walks all rejected candidates instead of only one sibling')\n"
guards = (
    anchor
    + "req(ffb, 'while (!ready)', 'FFB candidate probing is exhaustive without a fixed interface-count cap')\n"
    + "forbid(ffb, 'MaxInterfaceProbes', 'FFB candidate probing has no arbitrary interface-count ceiling')\n"
)
verifier = VERIFIER.read_text(encoding="utf-8")
if guards in verifier:
    pass
elif verifier.count(anchor) == 1:
    verifier = verifier.replace(anchor, guards, 1)
else:
    raise SystemExit(f"verifier anchor match count was {verifier.count(anchor)}, expected 1")
VERIFIER.write_text(verifier, encoding="utf-8", newline="\n")

print("Applied exhaustive FFB interface probing patch")
