# OutRun 2006 — all-HD-original text ROI production, 2026-10-15

## Implementation (staged, user deployment pending)

**Never feed the former 986 fixed rectangular tiles to ChatGPT ImageGen.**
The formerly generated image files and A/B state are kept untouched for audit.
This implementation preserves the existing 3 ChatGPT browser tabs and A/B times,
as well as the C text-only :03/:33 runs. No paid image API or quota bypass.

Live controller target is the existing user-managed Portainer Git Stack:
- Git ref `localization-controller-recovery-20260928`
- Compose `tools/chat-controller/localization-recovery-v1/docker-compose.yml`
- Host mount `/home/chatgpt-runner2/work/image-src` -> `/data/imagegen`
- New independent source/index: `/data/imagegen/text_roi_batches/production_manifest.json`
- New independent PNG directory: `/data/imagegen/text_roi_batches/inputs/`
- New independent state, receipts, evidence and outputs: `/data/imagegen/text_roi_batches/{A,B}_state.json` and its ancillary directories. Legacy `ab_batches` remains unchanged; shared sent receipts and project Library verification are used to prevent duplicate submissions.

The Compose sets `OUTRUN_AB_BATCH_QUEUE=false` and `OUTRUN_AB_TEXT_ROI_QUEUE=true`.
The new opt-in queue reads **only** entries with
`status=ROI_APPROVED_FOR_IMAGEGEN`, `source_provenance=DIRECT_FULL_HD_PNG`
or `DDS_PIXEL_VERIFIED_FULL_SOURCE`, exact SHA256s, independently checked
text alpha margins, original ROI coordinates and verbatim approved Korean.
Unreviewed alpha proposals, atlas-only reassemblies, missing source DDS proofs,
unknown translations and old sliced tiles are **not eligible**.
A and B each get separately persisted state and independent 1–5 input jobs.
The old 986-tile branch `next_binding` is explicitly disabled.

## Input inventory already staged on N100

- `work/image-src/inputs/A/HD_EN_TILES_20261014/SOURCE_MANIFEST_108.csv`: 108 native HD originals.
- `work/image-src/inputs/A/HD_EN_TILES_20261014/OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv`: 759 English→Korean rows.
- `work/text_roi_bulk_20261015/atlases/<source-group>/source_reassembled_readable.png`: 107 complete, SHA-pinned full-size English PNG pixel reassemblies. This is **not yet native DDS-equivalence proof**. The Q046 source group is HOLD due corrupt English source tile.
- `work/image-src/text_roi_batches/full_source_inventory.json`: 108 group index with 88 translation path matches, 20 platform-specific no-exact-path associations held; includes exact source paths, translated phrases, SHA and candidate locations.
- `work/image-src/text_roi_batches/proposals/`: 12 single-phrase machine ROI proposals from full-size source, **QA_PENDING** (not ready for ImageGen).
- `work/image-src/text_roi_batches/inputs/Q104_OutRunMode_FullHD_TextROI_2x.png`: 1952×336 Q104 actual input, SHA256 `69b94a31fed5533acb2e08b678befe03996587d25c1ad9d0fd764c598d788555`. Its source was an independently distributed full English original HD PNG from the pinned 2026-10-12 GitHub manual pack, not a stitched tile; source SHA256 `09c6604f41083ed6c8bf020b1600c6aef5190a42918f9cdf358473aecb1bd929`, source coordinate [386,42,1362,210], English `OutRun Mode`, approved Korean `아웃런 모드`. **The sole approved ImageGen-ready manifest entry so far.**

Asset branch source inventory and production manifest are mirrored at
`localization/graphics/role_C_salvage/20261015-text-roi-pilot/`.
Actual large full-size recovered PNGs live on N100 in a separate isolated
workspace, **not** as files committed into GitHub or as current ChatGPT
Project Library images.

## Manual Portainer deployment (user-owned)

1. Verify Stack Git repository/ref, existing Compose path and host mount. Confirm
   `/home/chatgpt-runner2/work/image-src/text_roi_batches/production_manifest.json`
   and `inputs/Q104_OutRunMode_FullHD_TextROI_2x.png` exist with correct hashes.
2. Keep browser named volumes and current A/B/C tab session data unchanged.
   User clicks **Pull and redeploy** on existing Stack. **Do not create another Stack**.
3. Check port 8788 controller status: 3 tabs, source mode ROI, A/B schedule and C :03/:33.
   Q104 should be the only initial producible task; B has no approved candidate and must HOLD.
4. Check A actually attaches the verified PNG in ChatGPT project
   `아웃런 한글화 신규`, and ImageGen tool is selected. One input→one separate
   transparent Korean output. The source uploaded must be bound to the queue
   task ID. Do not infer generation merely from submission or Library filename.
5. Library success requires real generated PNG counts, actual browser
   `libfile_` item IDs and SHA256 content equality; then the next unique
   approved ROI may advance. Guard outstanding unsent/unverified batches;
   do not retry a previously submitted batch or consume historic A/B state.
6. If image generation remains rate-limited, wait for the normal reset; no
   extra tab/account/API workaround.

## Remaining tasks, kept explicitly OPEN

The other 758 translation-table rows are **not** automatically eligible:
per-phrase coordinates, platform orientation, clean background/alpha,
crop boundary, approved text correspondence and C1/C3 review need evidence.
A staged proposed ROI never implies it is an approved source. The controller
blocks such entries, rather than sending a wrong phrase or clipped Hangul.

**Verified:** 7 unit tests for source-bound queue, simulated single-source
submission/duplicate guard, Python AST of actual patched A/B/C controller.
**Not verified:** live Portainer rebuild, project attachment, native ImageGen
execution, real generated output and saved SHA, final native DDS and user game.
`RUNTIME_VALIDATION=UNTESTED`.
