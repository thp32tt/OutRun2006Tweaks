# q212 external PSD → canonical SOURCE DDS proof (2026-10-10)

Test asset: **q212 / BA0147DA**, B even producer lane. This is a **source-method feasibility experiment**, **NOT an approved Korean DDS**, and it must not be counted as C/C3/game PASS.

- Source: Sonic-TV/OR2006Sprites `main`, `Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds`
- Layered PSD: `PSDs, XCFs, SVGs, and other Working Source Assets/Sumo UI/Various/BA0147DA_v02/BA0147DA_512x512.psd`
- Exact PSD SHA-256: `be5095d2598a831461e2e345c8fd2cead0cdd8de00ea7481256f0494c671d736`.
- Exact 2048×2048 canonical English DDS SHA-256: `f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61` (matches our existing q212 contract/source SHA).
- Parsed **110 Photoshop layer records**, including separately extractable `Flat Colors 1`, `Flat Colors 6`, `capsule.shape.yellow`, `OR - Rasterized`.
- Parsed native four-channel layer pixels and saved 4 isolated PNGs with exact per-image SHA in report.
- Correct PSD-readable → native-DDS transform: **FLIP-Y**. Pixels compared: **4,194,304**; differences: **0**.
- Rebuilt **uncompressed RGBA32 DDS header/payload** from the PSD merged image using the source DDS masks. **Byte-for-byte identical to canonical English DDS (0 byte differences)**, 16,777,344 bytes.
- Target title `PROFESSIONAL`/`OUTRUN` was **not found as a clearly named independent editable text layer**. This does not prove it is absent as raster art; precise text-specific clean plate must still be derived.
- Official Korean candidate untouched. No new localized DDS. Producer title CLEAN/lettering **HOLD**, independent C/C3 **not run**, user game test **UNTESTED**. Other atlas cells remain protected.
- Input PSD, original source DDS and reproduced DDS intentionally **not copied into this repository**; use the pinned upstream source and hashes.

## Reproduction
```bash
python tools/localization/q212_external_psd_roundtrip_probe.py \
  --psd /path/to/BA0147DA_512x512.psd \
  --dds /path/to/BA0147DA_512x512.dds \
  --out-dir /tmp/q212-psd-roundtrip
```
Requires Python with Pillow and NumPy. Script fails closed unless exact input SHA and byte-identical reconstructed DDS are verified. Run outside the official `hd_candidates` path.

## Result and next gate
Exact source equivalence is validated, but this external PSD cannot yet substitute for a **title-specific** validated SOURCE→CLEAN plate; first identify the title's actual layer/pixels and independently inspect two target cells, then generate native Hangul and run B self-QA → C2 → C3/user in-game gate.
