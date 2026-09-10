# Third-party notices and acknowledgements

This file records the source projects most directly referenced while developing the `wheel-ffb` branch.

## 1. emoose / OutRun2006Tweaks

Repository: https://github.com/emoose/OutRun2006Tweaks

Role in this project: **upstream/base project**. The wrapper, game hooks, overlay/config system and the majority of the codebase originate from OutRun2006Tweaks.

License reviewed: **MIT License**. The repository license notice is:

```text
MIT License
Copyright (c) 2023 emoose
```

The complete MIT text and required copyright/permission notice are preserved in this repository's `LICENSE.md`.

**Thank you to emoose and all upstream contributors for OutRun2006Tweaks.**

## 2. hyp36rmax / multi-device-input

Repository/branch: https://github.com/hyp36rmax/multi-device-input/tree/multi-device-input

Role in this project: important reference/adaptation source for **SDL3 raw multi-device input**, separate USB device handling, guided Quick Setup, physical-device identity and hardware compatibility behavior.

License reviewed: the `multi-device-input` branch retains the same **MIT License** file and upstream copyright notice (`Copyright (c) 2023 emoose`). The required MIT notice is already preserved by `LICENSE.md` in this repository.

**Special thanks to hyp36rmax for the multi-device work, hardware testing and the practical compatibility lessons shared with the OutRun community.**

## 3. d-b-c-e / OutRun2006Tweaks-FFB

Repository: https://github.com/d-b-c-e/OutRun2006Tweaks-FFB

Role in this project: important reference for **DirectInput steering-wheel FFB architecture**, hardware periodic effects, centre/spring + damper + cornering-load model design, grip-loss unloading and force signal-conditioning order.

License reviewed: the repository root publishes the fork under the same **MIT License** and upstream copyright notice (`Copyright (c) 2023 emoose`). The required MIT notice is preserved by this repository's `LICENSE.md`.

The d-b-c-e fork documents a separately vendored wheel toolkit in its own tree. **This project does not copy or redistribute that toolkit's `WheelFfb.dll`, native binary, or vendored toolkit source.** The v0.1 backend here is implemented directly with Windows DirectInput COM; only architectural/behavioral lessons from the public FFB fork were used as references.

**Thank you to d-b-c-e for publishing the FFB experiments, measurements and implementation lessons.**

## 4. Community testing / discussion

OutRun2006Tweaks Discord/community discussions were also used as practical references for wheel behavior, device-interface quirks, safe force-test levels and reconnect/focus handling. These are acknowledged as testing/design input rather than copied source code.

Thank you to everyone who shared logs, hardware behavior and troubleshooting results.

## License summary

The three directly referenced OutRun2006Tweaks code repositories above expose an MIT `LICENSE.md`, and this repository preserves that upstream MIT notice unchanged. The `wheel-ffb` additions are distributed under the same repository license.

This notice is an attribution/engineering record, not legal advice. Third-party libraries/submodules used by the upstream build retain their own licenses and notices.
