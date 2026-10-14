# OutRun 2006 HD PNG — A/B 5-image ImageGen production contract (2026-10-14)

## Effective on next **manual** Portainer deployment; do not deploy from this change

Repository: `thp32tt/OutRun2006Tweaks`, branch `localization-controller-recovery-20260928`.

Compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.
Only the localization controller `outrun-chat-controller-localization-recovery` is modified. Ports remain 6082 (VNC), 8788 (status), original browser profile and named Docker volumes preserved. Independent VR service untouched.

## Slots, input ordinals, execution

| Slot | Local Asia/Seoul minute schedule | Source tile ordinals | First batch |
|---|---|---|---|
| A | 00, 10, 20, 30, 40, 50 | original `ALL_TILE_MAPPING.csv` rows **1–500** | #1–5 |
| B | 05, 15, 25, 35, 45, 55 | original `ALL_TILE_MAPPING.csv` rows **501–986** | #501–505 |

- Two persistent Chrome *tab slots*. **Start an independent, brand-new ChatGPT chat** for each accepted new batch, never reuse earlier conversation context. On an unverified/pending previous batch, do not replace its chat or send a new batch until it is resolved.
- Five original source PNGs attached to **one ChatGPT Create image** request. Prompt strictly demands **five separate outputs**, one input-to-one output, never a collage. Final B batch may contain fewer than five.
- Source tile numbering uses the original 986-row CSV **before** filtering, so A and B ranges never shift or overlap.
- Original #130 `Q046_AA04D779_BASE_READABLE_FLIPY__r03c01__x0_y1340__683x708.png` has a corrupt/truncated IDAT and is explicitly quarantined for REWORK, without renumbering other tiles.
- Total eligible: A 499, B 486, total **985**, plus 1 source REWORK. A takes 100 batches maximum, B takes 98 maximum. Numbers denote **candidate input** capacity, not completed Korean results.
- Strict shared upload cap of at most 75 recorded source files per rolling three hours. The requested 12 runs/hour × 5 source files exceeds sustained ChatGPT upload limits. Scheduler still checks at each appointed minute but **skips** when the rolling quota is reached; it must never retry a possibly submitted batch automatically.

## Translation and orientation

Input folder: `/home/chatgpt-runner2/work/image-src/inputs/A/HD_EN_TILES_20261014/`, bind-mounted to `/data/imagegen/inputs/A/HD_EN_TILES_20261014/`.

For each file:
1. Match exact original ordinal in `ALL_TILE_MAPPING.csv`.
2. Validate PNG bytes, SHA256, CRC, canvas ≤1024×1024 and mapped original DDS SHA256 from `SOURCE_MANIFEST_108.csv`.
3. Load official `OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv` approved Korean translations; only replace text visibly present in tile; do not translate music titles, car models, brands, manufacturers or protected originals.
4. Normalize English source to human-readable **upright** orientation. The reviewed Q012 source needs an independent vertical flip; already-readable `FLIPY` tiles must not be re-flipped. Original source bytes are immutable; retain transform and inverse for later DDS recomposition.
5. Prompt demands original RGBA alpha, canvas, protected art, button/icon size, font colors, sheen, borders, direction, shadows and original effect bounding box; no new UI drawing, no letters overlapping or clipping.

## ChatGPT prompt: five independent output images

The generated prompt in `ab_batch_queue._prompt()` is the authoritative operational instruction. It repeats in Korean:
- **N inputs → exactly N separate output images**, no stitched composite, collage, multipanel, sprite sheet, one combined visual or mockup.
- Each output matched to a **single listed original** and translated only with the official per-file map.
- Preserve all original art and alpha, exact original size if the image tool supports it, upright Korean glyph direction.
- Save each generated image to the **existing project Library** of `아웃런 한글화 신규`; do not attempt a separate `outrun_kor` folder.
- The controller independently matches generated PNG SHA256 to actual PNG SHA256 bytes in this project folder.
- Ask filename suffix lowercase `_k` before `.png` (e.g. `Q012_..._k.png`).

A prompt cannot guarantee arbitrary folders, caller-defined filename or exact source dimensions. **Prompt text is not proof of save**. The project Library verifier must match each image by byte SHA256.

## Strict success gates and evidence

1. A/B target project and new chat composer verified; model Create image mode verified.
2. Exact source PNGs shown as completed attachments, with the full translated prompt and durable message ID, chat `/c/` URL, exactly N `User attachment` images confirmed under that specific user turn.
3. Exactly N *distinct* `Generated image` previews under the same conversation turn (not original attachment thumbnails); partial output, extra or single collage means HOLD/REWORK.
4. Download unapproved output candidates to `/data/imagegen/ab_batches/candidate_outputs/<slot>/<original_stem>_k.png`. Assignment is **output display order only, not pixel-verified correspondence**. Record original/generated dimensions and mode, mark `REWORK_DIMENSIONS` or `PENDING_PIXEL_QA`. Do not silently upscale/downscale and never replace source English PNGs.
5. **Mandatory:** verify the `아웃런 한글화 신규` **project Library** contains the same N PNGs generated by this batch. `project_library_gate.py` opens a separate temporary authenticated browser tab, selects the existing project folder, scrolls through paginated images and matches all generated PNG SHA256 digests to separate `libfile_` item IDs with identical content hashes. Any missing item, inaccessible PNG or hash mismatch returns HOLD, not PASS.
6. On successful verification, automatically save real UI evidence to `/data/imagegen/ab_batches/library_evidence/<TASK_ID>.json` with `verification_method="browser_content_sha256_match"`, unique real `library_item_ids`, matching `generated_image_sha256` and `library_content_sha256`, project folder label, and actual folder URL. Existing historical `outrun_kor` evidence is not valid for the new policy. No separate folder creation is attempted, and generated filenames like `image-gen-1(2).png` are allowed; local candidate files use `_k.png`.
7. Only after the above gates: increment this slot's completed count/next ordinal and permit next new chat. Separate independent QA of Korean glyphs, layout, alpha and final DDS/game runtime remains required.

## 2026-10-14 live ImageGen and project-Library correction

The B first batch `OUTRUN-AB-B-0001-20261014` (source ordinal 501–505)
**really generated five independent images**. ChatGPT's updated UI uses one
large `generated-image-preview` followed by **five**
`Show generated image N` carousel selectors with distinct full PNG blobs.
The former controller counted only the large preview and falsely reported
`IMAGEGEN_OUTPUT_COUNT_MISMATCH:1/5`. The new `ab_batch_queue.py` detects
the five distinct carousel items, verifies each Blob is fetchable with image
type and nonzero byte length, and exports images 1–5 in carousel order. The
new regression test `tests/test_ab_carousel.py` covers 5-output export,
incomplete batches, duplicate images, immutable candidates and Library gate.

The actual ChatGPT Library **project folder** `아웃런 한글화 신규`
contains images named `image-gen-1(2).png` through `image-gen-5(2).png`.
On 2026-10-14 the user clarified that a separate `outrun_kor` folder does
not work and approved using the existing project Library. The new verifier
independently matched all **five generated PNG SHA256 digests** to five
separate saved Library `libfile_` IDs. The match was confirmed on N100
in a **read-only test** without resending the batch, overwriting its state,
or modifying source PNGs. This is image-generation + project-save evidence,
not exact-size texture QA. The new verifier needs manual Portainer redeployment
before existing B state can advance using the corrected success gate.

Real generated PNGs were also exported without overwriting input files to
`/data/imagegen/ab_batches/candidate_outputs/B/`, with hashes and
provenance in `/data/imagegen/ab_batches/export_evidence/OUTRUN-AB-B-0001-20261014.json`.
All five are **REWORK_DIMENSIONS** (e.g. English source 683×256 vs
generated 2048×768). Output-to-source assignment uses display order only;
independent semantic matching and DDS/runtime QA remain UNTESTED.
GitHub-only controller selector fix needs a separate user Portainer redeploy;
the currently running N100 container retains the old first-preview selector
until redeployed. No forced resends, Library evidence fabrication, or
automatic DDS changes.

## Persistent state and backward compatibility

- `/data/imagegen/ab_batches/A_state.json` and `B_state.json` — disjoint original ordinal ranges and one in-flight batch per slot.
- `/data/imagegen/sent/A_OUTRUN-AB-A-*.json` and equivalent for B — durable user message receipt or ambiguity marker; never delete or resend uncertain work.
- `/data/imagegen/ab_batches/generated_visible/` — observed assistant count, **not Library proof**.
- `/data/imagegen/ab_batches/candidate_outputs/{A,B}/` — locally exported `_k.png` candidates, **not Library proof / QA pass**.
- `/data/imagegen/ab_batches/export_evidence/` — output hashes, dimensions, mapping warning.
- `/data/imagegen/ab_batches/library_evidence/` — positive Library verification records.

Legacy `/data/imagegen/a_tile_batches/` states, corrupted source evidence and Q217 pilot records are preserved but no longer active under `OUTRUN_AB_BATCH_QUEUE=true`, `OUTRUN_A_TILE_BATCH_QUEUE=false`.

## Manual deployment / acceptance criteria

1. In Portainer update the existing Git-backed localization stack to branch `localization-controller-recovery-20260928` and pull/redeploy *manually*. Do not replace or remove existing named `/data`, `/logs` volumes or VNC credentials. **Do not modify VR.**
2. Check status URL port **8788**: registry `A,B`, `AUTO_SEND=true`, `SCHEDULE_MINUTES=[0,5,10,15,20,25,30,35,40,45,50,55]`, fresh chat mode.
3. On VNC port **6082** verify both tabs are logged into ChatGPT, current project identity is `아웃런 한글화 신규`, and Create image is selectable.
4. At A :00 / B :05 verify each opens a **new chat**, and exactly five *separate* original attachments plus strengthened prompt are visible.
5. Confirm exactly five generated images, not one collage; ensure Library folder `outrun_kor` actually exists and each image is saved there. If the UI cannot create/move them, record `LIBRARY_OUTRUN_KOR_UNVERIFIED` and do not mark complete.
6. Check A first index=1, B first index=501; content and SHAs never overlap. Verify old A-only legacy state remains intact.

**Current change:** GitHub-only source update; user deploys through Portainer manually. The previous B batch's five generated images and five project Library bytes were matched by SHA256 on N100; no new controller deployment, DDS quality pass or game runtime test was performed for this change.