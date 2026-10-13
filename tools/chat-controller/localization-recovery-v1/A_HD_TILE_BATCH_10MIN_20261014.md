# OutRun HD 986 tiles — A 5-source / 10-minute ImageGen queue

## Purpose and boundaries

- Source: `/home/chatgpt-runner2/work/image-src/inputs/A/HD_EN_TILES_20261014/` (986 English PNG tiles, 108 source DDS).
- In-container: `/data/imagegen/inputs/A/HD_EN_TILES_20261014/`.
- Exactly **5 distinct source tiles per batch** (last batch has 1), starting at 00, 10, 20, 30, 40, 50 KST.
- `CHAT_SLOTS=1`, `OUTRUN_A_TILE_BATCH_QUEUE=true`, `AUTO_SEND=true`. B/C1/C2 inactive; VR unchanged.
- Existing `pending_A.json` and Q217 test results are preserved; queue mode ignores that single-asset pilot.

## Upright baseline normalization (2026-10-14)

Visual review of original English PNG shows:
- Q012 `...BASE_READABLE_NORMAL__r01c01...`: text `Continue?` is upside down. Make a **separate vertically-flipped upright reference**, preserving RGBA pixels and dimensions.
- Q032 `...BASE_READABLE_FLIPY...`: `Total Rank` is already upright. Do **not** flip it again.
- Source CSV contains 1 `NORMAL` tile and 985 `FLIP_Y_PREVIEW_PER_SPRITE_VERIFY` tiles. Review cannot infer direction from `FLIPY` label alone; the incoming readable PNG is authoritative. Any new/unknown orientation fails closed.

Original English PNGs and source hash mapping stay immutable. The verified Q012 derivative is stored under `/data/imagegen/a_tile_batches/upright_sources/`, with a separate `.orientation.json` containing original and derived SHA256 and reversible transform.

**ImageGen always receives the readable-upright English reference**, and must output Korean in the same upright direction. Do not feed upside-down text to ImageGen or ask it to draw upside-down Korean. On reassembly, first apply the recorded `upright_to_source` inverse (`FLIP_Y` for Q012, identity for already-upright readable FLIPY PNGs), then perform DDS-specific orientation/texture QA before changing game assets. Do not silently flip whole DDS atlases.

## Input and official translation mapping

The controller builds prompts from:
- `ALL_TILE_MAPPING.csv`: tile filename, DDS parent, x/y, dimensions and SHA256.
- `SOURCE_MANIFEST_108.csv`: original DDS path and SHA256.
- `OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv`: reviewed English→Korean pairs and protected originals.

For each of the five images, the batch queue rechecks PNG SHA256, CRC, original dimensions (each ≤1024×1024) and native source mapping before uploading. It never translates music titles, car names, brands or protected UI art. Prompts ask for **five separate Korean image outputs**, not a composite. Since an image generator may change dimensions, these are *candidate images only*, not directly approved DDS.

## Queue state, duplicate prevention and rolling upload cap

- `/data/imagegen/a_tile_batches/state.json`: offset, batch task, in-flight batch.
- `/data/imagegen/sent/A_OUTRUN-A-HD5-XXXX-20261014.json`: exact user message receipt or do-not-retry ambiguity.
- `/data/imagegen/a_tile_batches/visible_results/<task>.json`: UI-observed count of five loaded assistant images (not QA).
- Each interval checks current batch before loading a new one. The queue does **not** advance on upload preview or on a text-only answer.
- Missing target, missing image-tool pill, file upload failure, no persisted message with five attached images or ambiguous send => halt/hold. Never fabricate completion.
- Even after a verified user request, hold the batch until *five separate assistant images* appear after that specific request. If fewer appear, leave it pending and do not send subsequent tiles.
- 80 uploads / 3h is the published ChatGPT upload quota (can be lower). Enforce **75 tile uploads in the last 3h**; every 10-minute tick still runs but will skip batches when needed. Other manually uploaded files may use quota too.
- PNG QA, file naming, original exact dimensions, per-tile output download, Library persistence and DDS runtime are **not independently proven by a five-image DOM count**.

## ChatGPT Images and Library

ChatGPT automatically saves images it actually generates in the **Images** tab; uploaded and created files may appear in Library too, subject to account settings. This is platform behavior, not a custom file-export service. The queue cannot certify exact `_KOR.png` files have been exported into a user-created Library folder, or that they retain source dimensions. If the user needs reassembled DDS/ZIP files, a separate output download, postprocess and independent QA lane is required. Do not mark files PASSED without byte-level verification.

References:
- https://help.openai.com/ko-kr/articles/11084440-chatgpt-image-library
- https://help.openai.com/en/articles/20001052-using-library-to-manage-files-in-chatgpt

## Deployment and verification

Branch `localization-controller-recovery-20260928`; Compose:
`tools/chat-controller/localization-recovery-v1/docker-compose.yml`

Rebuild **only** `outrun-chat-controller-localization-recovery`; preserve original `outrun_chat_localization_recovery_data` and `outrun_chat_localization_recovery_logs` and VNC profile. Rebuild `pull_policy: build` when using Portainer Git stacks.

Check:
1. Status page on `8788`: one A slot, `AUTO_SEND=true`, minute list `[0,10,20,30,40,50]`.
2. Queue state offset 0, first five SHA-valid source filenames, unique batch task ID.
3. A project tab has composer and explicit **Create image** pill.
4. Five *named*, fully uploaded attachments and full translation prompt visible before send.
5. A persisted `/c/` URL, exact task ID in user turn and five attached images. Only then mark sent.
6. On a later tick, five *assistant-generated* images visible (not thumbnails of the user uploads). Only then advance queue.
7. Check ChatGPT Images and Library personally; pixel QA/alpha/orientation/English-original comparisons remain separate.

Never delete or auto-retry a `SUBMISSION_UNVERIFIED_DO_NOT_AUTO_RETRY` record without checking the existing ChatGPT conversation. One batch per tick at most. The A-only Compose disables run-count chat recycling (`CHAT_RECYCLE_RUNS=0`) so the next scheduled result probe remains in the same chat.


## Source integrity exception (N100 audit, 2026-10-14)

Of 986 hashed transfers, **985 parse fully as PNG with valid chunk lengths and CRC**. One source tile, `Q046_AA04D779_BASE_READABLE_FLIPY__r03c01__x0_y1340__683x708.png`, is truncated in its IDAT chunk (file length 65,577 bytes; claimed IDAT length 65,536 exceeds file end). Pillow verification also reports a broken PNG. Do not use it for ImageGen, do not falsely mark it translated, and do not change the provided source in place. The current production queue deterministically excludes exactly that tile (985 candidates); its evidence is retained in `/data/imagegen/a_tile_batches/input_integrity_report.json` for separate source repair/rework. If a corrected original arrives, introduce it through a separately audited repair queue, without shifting the active 985-tile queue offsets.