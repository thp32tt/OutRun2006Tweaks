# DX9Ex R26+HUD official focus integration, October 27 2026

User requested one normal branch, no A/B/C/D/E build switching.

- Primary VR development/test source: `vr-d3d9ex-focus`.
- Integrated Quest E source (original flare family all unhidden, exact rival
  source ownership, XR live eye startup 8s, aspect-preserving PC mirror).
- Inherits A/B/C/D +TIME and GOAL source admission changes, subject to
  unresolved visual HMD validation. RUNTIME_VALIDATION=UNTESTED.
- Tested Windows build packaging requires START_HERE.cmd, Run-FocusOfficialTest.ps1,
  OutRun2006Tweaks.ini, x86 dinput8.dll and x64 outrun-vr-host.exe.
- Existing automated review and cockpit reverse-engineering docs on focus
  were retained. Prior detached experimental branches are historical only.
- PC mirror aspect fitting can expose sidebars on 3440x1440; not solved
  by stretching a 4:3 menu. +TIME/GOAL final graph and rival stereo
  are NOT confirmed optically correct.
- Use only GitHub Actions on exact focus SHA, TEST and DEBUG separate ZIPs.
