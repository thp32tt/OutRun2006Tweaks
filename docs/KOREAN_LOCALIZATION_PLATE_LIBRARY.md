# Shared PSD/CLEAN production inputs — 2026-10-11

The authoritative branch is `korean-localization-recovery-20260928`. This is an input
library, not another asset queue or a replacement for the ten-stage QA pipeline.
A keeps odd assets, B even; C1/C2 independently review their respective parity and
C3 separately reviews exact final bytes. The six-launch schedule is unchanged.

## Reuse before reconstruction

At the beginning of A/B work, inspect `localization/graphics/plate_library/entries`.
Use `tools/localization/plate_library.py inspect` with the exact canonical DDS SHA,
queue index, semantic region ID and orientation. Do not rebuild an existing plate
because lettering, font or effects failed. Missing independent review means C must
inspect the stored plate, not that A/B should remake it. Preserve independent work.

`objects/<sha256>.png` holds immutable original bytes; Git deduplicates identical
blobs. `entries/<manifest-sha256>.json` binds the source, region, transform, masks,
plate, producer and provenance. Concurrent A/B additions use different files.
Changed plate/mask/coordinates require a new manifest, never an overwrite. Multiple
matching versions fail closed until an explicit version is selected in the recipe.
Old role evidence folders stay intact. Do not remove live referenced objects.

Before production reuse, C1/C2 writes `reviews/<manifest-sha256>.json` with
`manifest_sha256`, `reviewer` (`C1` odd / `C2` even), `status: PLATE_PASS`, actual
per-region `observations`, and `evidence: [{path, sha256}]` referencing independent
lossless SOURCE/CLEAN observations. Revoke this review (`REVOKED`/HOLD/FAIL) if new
evidence reveals a plate defect. A/B cannot write their own C approval. A supplied
review record is not cryptographic authentication: Git provenance and C independence
remain mandatory. Reused plate approval never approves new lettering or a DDS.

```sh
python tools/localization/plate_library.py audit
python tools/localization/plate_library.py inspect --index 60 --source-sha 6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc --region BEST_TIME --orientation readable_flip_y
python tools/localization/plate_library.py prepare --index 60 --source-sha 6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc --region BEST_TIME --orientation readable_flip_y --source-dds /inputs/A064FDFC.dds --output /output/CLEAN.png
```

`prepare` rechecks source bytes, full native dimensions, every RGBA pixel outside
removal and transparent alpha residue, then checks the independent review and writes
an exact byte copy. Colored backgrounds require independent seam/residue observation;
alpha-zero is not an appropriate test there. Preserve source-authored protected masks
and run the existing `production_pixel_guard.py` for final source/previous-candidate
protection, source typography/slant, native glyphs and persisted DDS QA.

q060 seed is the exact B348 readable PNG (`a03687d4…`) and original removal mask
(`25a89817…`, 89,391 pixels). Its previous producer P1 evidence is preserved. This
registration deliberately supplies **no new independent PLATE_PASS or final approval**.
C2 should reuse prior exact-source CLEAN observations where valid, inspect any missing
proof once and bind the decision to this manifest. q060/IGR044 stays REWORK/OPEN.

## PSD and renderer decisions

Reuse an approved library plate first. Otherwise inspect SHA-pinned external PSD/SVG.
`extract_psd_plate.py` extracts an explicit layer-index path onto a full native canvas;
its result is EXTRACTED_UNVERIFIED, never automatically a CLEAN plate. Verify layer
meaning, transform, source DDS equality/protected pixels and source-removal scope.
Do not substitute an upstream PSD for the canonical DDS without those comparisons.
If useful layers are absent, reconstruct from canonical English pixels.

Keep reconstruction separate from transparent Korean lettering. q121/q049 use source
layer/outline reconstruction; q060 uses distinct face/highlight/extrusion vector work;
q154 uses a native-size font renderer; q212 uses CLEAN plus selected title contours.
These are **pilot routes, not validated recipes**. Store renderer code/font/license,
exact hashes, parameters and plate manifest ID in the existing asset recipe.json.
Do not feed metallic headers into the generic proof-only render_artwork.py.
Only expand a recipe after its representative saved DDS has independent C acceptance;
C3 and user gameplay remain separate. Two same-cause rejects require method change.

## Execution and recovery

Local compute is preferred. Optional `docker/localization-production/Dockerfile` runs
the same CLI in a reproducible CPU environment; do not render repeatedly on N100.
The controller's versioned prompts under `tools/localization/controller_prompts` route
all four workers to this Git contract. No additional scheduler or PSD worker is added.
The deployment script layers only these prompts over the existing controller image,
preserves browser/state/log volumes and original timing, and never modifies the VR
container. Controller health does not establish artwork or gameplay success.

Performance: track first independent C acceptance, repeated defect causes and actual
user-game closures. Library registrations, CI counts and repeated hashes are not DDS
production. `RUNTIME_VALIDATION=UNTESTED` until an actual user game test.
