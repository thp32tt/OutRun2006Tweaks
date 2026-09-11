# Third-party notices and acknowledgements

This file documents the main upstream/reference projects used by the `wheel-ffb` branch and how binary-release notices are handled.

## Upstream base

### emoose / OutRun2006Tweaks

Repository: https://github.com/emoose/OutRun2006Tweaks

Role: upstream/base project. The wrapper, game hooks, overlay/configuration system and much of the codebase originate from this project.

License: MIT. The original `Copyright (c) 2023 emoose` notice is preserved in this repository's `LICENSE.md`.

## Wheel/input references

### hyp36rmax / multi-device-input

Repository/branch: https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input

Role: important public reference/adaptation source for SDL3 raw multi-device input, separate USB-device handling and modern wheel compatibility behavior.

The branch retains the upstream MIT license notice.

### d-b-c-e / OutRun2006Tweaks-FFB

Repository: https://github.com/d-b-c-e/OutRun2006Tweaks-FFB

Role: important public reference for DirectInput wheel-FFB architecture and force-model/signal-conditioning ideas.

The repository retains the upstream MIT license notice. This fork does not redistribute the separate `WheelFfb.dll` toolkit from that project; the v0.1 FFB backend is implemented directly with Windows DirectInput COM.

## Build dependencies

The produced DLL also incorporates open-source dependencies from the upstream build, including projects fetched or linked through CMake/submodules such as SDL, SafetyHook/Zydis, spdlog, Dear ImGui, xxHash, IXWebSocket, zlib, jsoncpp, Ogg/FLAC, miniz and related support libraries.

Rather than manually maintaining a second copy of every dependency license in the release workflow, CI scans the exact checked-out/fetched dependency source trees used for the build and concatenates unique `LICENSE*`, `COPYING*` and `COPYRIGHT*` files into the release package as `LICENSES.txt`.

This keeps the public ZIP small while retaining the notices supplied by the actual dependency revisions that were compiled.

## Replacement game executable

The release package includes `OR2006C2C.exe` downloaded from the public upstream OutRun2006Tweaks v0.1 release asset. The upstream release describes it as a replacement executable for Steam/DVD installations so DLL wrappers can work with the game.

Source release: https://github.com/emoose/OutRun2006Tweaks/releases/tag/v0.1

Game code/assets and related trademarks remain the property of their respective rights holders; inclusion here does not change those rights.

## Community testing

Community discussions and user hardware logs were used as practical testing/design input for wheel behavior, device-interface quirks, force direction, reconnect handling and R3 tactile tuning.

## License summary

The forked source remains under the repository's MIT license while preserving the upstream notice. Binary-release dependency notices are generated from the actual source/dependency trees and shipped as `LICENSES.txt`.

This file is a project attribution/packaging record, not legal advice.
