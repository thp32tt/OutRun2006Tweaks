# Q051 F1 — TIME → 시간 (static, TEST_ONLY, 2026-10-16)

- **Source**: exact N100 native HD `FF2462BB` 4096×2048 DDS RGBA32 (one mip), source SHA-256 `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`.
- **F0 CLEAN**: source-preserving single-word test DDS SHA-256 `7c1a81b1570ffc910d71ea25d05819d93c8ed0a80be7d2c0437fce6b43fbdd43`.
- **Korean input**: existing user-supplied five-word generated image `54.png`, `시간` word cropped locally; transferred to N100 as palette-Q32 PNG SHA-256 `91ba2ec11302f468d1bf2a900fd35c6803d9852c9db1ba87c044c9916a67e474`. This was **not a new ImageGen call**, and 32-color conversion is an explicit quality/speed compromise.
- **Placement**: original readable Q051 TIME ROI `[1595,608,1845,727]`; safe glyph/effect region `[1629,636,1834,707]`; output `시간` 169×71 at readable coordinates (1647,636), aspect ratio preserved. Transformed back to DDS raw vertical orientation.
- **F1 candidate**: N100 `work/c_salvage_text_roi/F0_Q051_NATIVE_DDS_20261016/Q051_TIME_KO_F1_TEST_ONLY.dds` 33,554,560 bytes; SHA-256 **`4f07654689e93bfb65cdd0ca710490e7ecbc0e40f31f3109f7adceb442f2a956`**.
- **Static QA**: DDS header exact, size/mip exact, all RGBA protected pixels outside the TIME source ROI unchanged; persisted DDS decoded RGBA verifies exact alpha and visible RGB compared to constructed Korean layer. The transparent RGB of CLEAN is intentionally retained from source. `F1_STATIC=PASS_CANDIDATE`.
- **Crop caution**: `Q051-TIME_HUD_2` historical duplicate crop is explicitly excluded. `Q051-YOU` historical crop included a sliver of adjacent `TIME`; actual YOU label/icon were outside our removal mask. Independent QA still outstanding.
- **Runtime**: user explicitly waived physical-device/real-game testing for current forward test on 2026-10-16. This is a **waiver**, not `RUNTIME_VALIDATION=PASS`. Record `WAIVED_BY_USER_FOR_THIS_TEST_UNTESTED_NOT_PASS`. C1/C3 `NOT_RUN`; no automatic gate promotion, no game patch release, no container restart, no DDS deployment.
- **GitHub artifacts**: source script, report, Korean reference glyph (quantized), Korean layer, and actual side-by-side review PNG. The full 32 MiB candidate DDS is stored on N100 only; do not point to non-existent GitHub DDS.

Next step: independent screenshot review and separate F2 trial for the remaining four labels on the same atlas. Historical A/B/986 tile queues stay PAUSED.
