# Q097 411827E Korean overlay QA — 2026-10-14

Status: HOLD; DDS NOT PRODUCED; RUNTIME_VALIDATION=UNTESTED.

- Generated Korean button image: RGB 1536x581; contains regenerated red/green button panels and white border.
- Canonical HD source READABLE PNG: Q097_411827E_BASE_READABLE_FLIPY.png, RGBA 2048x2048.
- Source sample ROI (790,825,1570,1120), 780x295.
- Local experimental extraction: bright Korean text fill only, 26905 nonzero-alpha pixels; black glyph shadows not safely separable from generated button background.
- Reject direct generated-button overlay: it would damage protected original artwork. English removal needs exact clean plate.
- DDS export HOLD: original DDS binary header, compression, mips, sprite orientation and English-clean background not verified.
- Required: source DDS binary inspection; source-faithful clean plate; Korean text/shadow extraction; exact ROI compositing; protected-pixel QA; same-format DDS export; runtime validation.
- No production deployment or DDS PASS claim.
