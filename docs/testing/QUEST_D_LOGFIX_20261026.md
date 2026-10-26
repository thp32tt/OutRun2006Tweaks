# Quest D: October 26 2026 real user log fixes

Source: two DEBUG ZIPs game DLL SHA 3ABEF2543E80B1C9945F60BCFB67533F9BAD9310E7A59524C2C488419D7962FF, source 7c7c5632.

- VR desktop mirror and game source flip between 1920x1080 and 3440x1440 while host sees 2496x2688 per-eye. Explicit logical 1920x1080 fixes desktop dependence; bounded first-device live XR HostState fetch attempts physical XR extent.
- PC mirror was aspect fitted 2560x1440 at x=440 on 3440x1440 desktop, exposing windows/taskbar. D tests full monitor borderless (possible widened PC mirror; HMD untouched).
- Rival 0xBB6F0 projection anchor valid but 0xBB796 queue registeredDelta=0 through 8192 probes. D tests stock original rival route; effect on Quest 3 NOT YET VERIFIED.
- GOAL source 0x2D200 called STATE_TIMEUP=0x14 (numeric 20), rejected with reason=not-goal-at-entry 256 times. D extends exact original result source admission to GOAL/TIMEUP/RESULT while retaining queue-epoch lease and native draw.
- Keep D separate from vr-d3d9ex-focus. Original game EXE unbundled. Run only GitHub Actions produced TEST/DEBUG full runnable ZIP; RUNTIME_VALIDATION=UNTESTED.
