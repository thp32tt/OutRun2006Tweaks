# Shared PSD/CLEAN production inputs — 2026-10-11

The authoritative branch is `korean-localization-recovery-20260928`. This is an input
library, not another asset queue or a replacement for the ten-stage QA pipeline.
A keeps odd assets, B even; C1/C2 independently review their respective parity and
C3 separately reviews exact final bytes. The six-launch schedule is unchanged.

## 2026-10-11 expanded upstream PSD mirror

The entire pinned upstream git tree has **184 PSDs**, of which **81 distinct PSD files
match 65 current queue texture hashes** (original and alternate revisions both included).
The complete source mapping, original upstream Git blob SHA/byte count, and target local
paths are in `localization/graphics/plate_library/PSD_IMPORT_CATALOG.json`.
The full matching set is about 1.84 GB; do not blindly import unrelated media,
multiple revisions or copyright-unverified content as runtime assets.

**Local-first input rule:** before fetching remote or rebuilding CLEAN, check
`localization/graphics/source_psd_upstream/<texture-hash>/` for matching PSDs
whose Git blob SHA is listed in the catalog. These are source *inputs*, not game
overrides. They remain unchanged; use `psd_layer_workbase.py separate` to
create the full English PSD reference and all layers, then explicitly select
English glyph/effect layers to derive CLEAN candidates. Source-vs-canonical DDS
pixel fidelity and independent C2 approval still gate their use.

The `Localization PSD Source Mirror` workflow imports a selected priority
batch into **this exact branch**, verifies Git SHA and size, then checks the
remote committed blob. Its first selected set is q060, q121, q049, q205,
q227, q212, q135, q230, q188, q176. Only claim each imported source
after the GitHub remote blob is confirmed. Additional catalog entries do not
constitute copied PSDs and still require a deliberate import batch.

The community upstream does not advertise a repository-level license, so
preserve exact upstream origins, credits and distinguish the source mirror
from any external distribution or publicly endorsed license grant.

## 2026-10-11 PSD-first source workbase — latest user request

Before manually erasing English from an HD DDS, look up a **matching native texture hash** in
`localization/graphics/plate_library/PSD_UPSTREAM_SOURCES.json`. The initial pinned working
source is `Sonic-TV/OR2006Sprites` at commit
`3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`.
Fetch **only the needed PSD** at this commit (do not consume unpinned upstream HEAD),
verify the original Git blob SHA and actual PSD SHA256, then run
`tools/localization/psd_layer_workbase.py inventory` followed by `separate`.

PSD-first processing order:
1. Inventory all original PSD groups/layers and create **an independent full-canvas PNG per layer**.
2. Preserve the source `english_original_full.png` and source English typography/effects
   references; review layers to identify exactly which contain source English glyphs,
   outline, and shadow. Layer names/kinds may be misleading or English may be baked.
3. Use `export --english-layers INDEX,INDEX` to produce both
   `clean_plate_candidate.png` (all other layers) and
   `english_letter_layers.png` (isolated selected English/effects), never editing
   the originals. Check hidden/clipped/adjustment effects manually when needed.
4. Compare source PSD full composite and extracted CLEAN to the **exact pinned canonical
   English game DDS**, at native 100/75/50, RAW/readable orientation, ROI, protected art,
   effects and 1-pixel boundaries. A community PSD remake is **not** assumed pixel-
   equivalent to the canonical DDS and cannot silently replace it.
5. If the PSD faithfully supplies a reusable CLEAN and English reference, publish it
   with precise origin/SHA/layer paths in the existing `plate_library`; C2 independently
   reviews SOURCE vs CLEAN and writes `PLATE_PASS` before A/B/C1 lettering. A/B/C1 may
   not self-approve. C3/actual user in-game QA remain separate.
6. Reconstruct CLEAN from English DDS pixels **only when** there is no matching useful
   PSD layer or the PSD candidate fails canonical checks; record the reason.
   Do not destroy older independently approved source-aligned CLEAN objects.

The pinned catalog includes initial matches for queue indexes 49, 51, 46, 135, 188,
212, and 230. Their hashes are **matches by texture identifier only**, not promises
that all seven contain separate English or true CLEAN. q060/q102 currently have no
verified exact PSD entry; do not pretend they do.

`PSD Layer Source Pilot` GitHub Actions performs an actual q135 source/layer
separation and q49 layer inventory. This pilot produces **EXTRACTED_UNCLASSIFIED**
materials for inspection, never C2 approval or a game-ready DDS. Existing
`extract_psd_plate.py` is kept for explicitly selected single-layer extraction.

The upstream repository did not advertise a repository-level license at inspection.
Maintain upstream authorship and source links; review reuse/redistribution rights.
The current connected GitHub action set has no dedicated remote `fork` mutation,
so pinned upstream checkout and derivative working outputs are **not presented as an
actual GitHub platform fork**.

**C2 ownership correction (2026-10-11):** C2 alone independently reviews all
A/B/C1 CLEAN plates and final DDS, odd/even/special; the older C1-odd/C2-even
wording below is superseded. Do not treat legacy C1 PLATE_PASS as fresh C2 approval.

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
