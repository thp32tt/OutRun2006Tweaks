# OutRun2 VR PC self-hosted fast test path

Purpose: use the Windows development PC only during an interactive test/fix/retest session. Normal A/N100/B/C/D review and automation must not consume this PC.

## One-time PC setup

1. Prefer changing the repository to Private before registering a self-hosted runner.
2. Install Visual Studio 2022 or Build Tools 2022 with Desktop development with C++, MSVC v143 x86/x64 tools, Windows 10/11 SDK, CMake, and Git for Windows.
3. In GitHub open Settings -> Actions -> Runners -> New self-hosted runner -> Windows -> x64.
4. Use C:\actions-runner and run the exact download and extract commands GitHub shows.
5. Configure runner name outrun-pc and custom label outrun-pc.
6. Do not install it as a Windows service. The runner is deliberately opt-in.

Example shape only; use the temporary token displayed by GitHub:

    cd C:\actions-runner
    .\config.cmd --url https://github.com/thp32tt/OutRun2006Tweaks --token <TEMP_TOKEN> --name outrun-pc --labels outrun-pc

## Start only when interactive testing begins

    cd C:\actions-runner
    .\run.cmd

Leave this window open. The expected state is Listening for Jobs.

Stop with Ctrl+C when the test session ends. While stopped, the PC does not accept GitHub jobs.

For convenience create a desktop file named OutRun Runner Start.cmd:

    @echo off
    cd /d C:\actions-runner
    call run.cmd

## Automatic fast-build trigger

The workflow .github/workflows/vr-pc-fast-build.yml uses the labels:

    self-hosted, Windows, X64, outrun-pc

Normal pushes do nothing. A push to vr-d3d9ex-focus only enters this PC path when the commit message contains:

    [pc-build]

The marker is reserved for an explicitly requested interactive PC test session. Scheduled jobs and normal review/integration commits must never add it.

## Speed behavior

The fast path intentionally differs from final CI.

- Persistent build caches: out/pc-fast/game and out/pc-fast/host.
- Checkout uses clean=false, so object and dependency caches survive between test builds.
- Parallel CMake builds use all logical processors exposed to the runner.
- Only the active Win32 game DLL and x64 OpenXR host are built.
- Expensive policy, smoke, and final validation are not rerun on every interactive iteration.
- GitHub artifact upload is skipped by default.
- The ready-to-run package is copied directly to Desktop\OutRunTestBuilds\LATEST.
- The ZIP is kept in Desktop\OutRunTestBuilds.
- Only the newest eight PC-fast ZIPs are retained.

The first PC build is a warm-up build and can still take time because dependencies and build trees must be created. Later source-only changes use incremental compilation.

## Validation boundary

A PC fast build is tagged PC_FAST_INCREMENTAL_NOT_FINAL_CI.

It is suitable for Quest 3 / VDXR test-fix-retest iteration. It does not replace the repository normal exact-SHA policy, smoke, regression, integration, or final package validation.

After the runtime symptom is fixed, run the normal canonical validation path before treating the result as a final candidate.
