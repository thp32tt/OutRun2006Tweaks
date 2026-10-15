# Q095 Entry has been closed. — direct full-source text ROI (TEST_ONLY)

- TASK_ID: `OUTRUN-C-ROI-SOURCE-Q095-ENTRY-CLOSED-20261015-2103`; project: `아웃런 한글화 신규`. New, independent one-phrase ROI, separate from previously completed Q095 `Please stand by.`.
- English exact source: `Entry has been closed.`; reviewed Korean mapping: `참가 접수가 종료되었습니다.` from `localization/graphics/transcriptions.jsonl`, index 95.
- Original PC DDS: `localization/validation/binary_compare/pairs/37759842/original/37759842_1024x1024.dds`; source DDS SHA256: `ec69c95e638f6ba1ef2c23db173462adb26ad0d10caed28f1c83b7d1d15658f0`.
- Independent preexisting canonical full PNG: `localization/graphics/reference_packs/full_dds_test/37759842_FULL_ENGLISH_ORIGINAL_FLIPY_1024x1024.png`, SHA256 `8b78a092b5ca82276076cc5d99b05afd0831651ae2d4afbbcf7486f4693fa7c9`, 1024x1024 RGBA. Verified **pixel-for-pixel identical** to direct original DDS vertical flip. Full source was **not reassembled from the previous 986 tiles**.
- Full-source native ROI xyxy `[403,183,842,239]`; native 439x56; text/effect alpha bbox `[411,188,828,233]`; alpha transparent margins left/top/right/bottom `[8,5,14,6]`; 2px no-edge-contact on every side. Visually reviewed complete phrase, without adjacent labels.
- `english_text_roi_native.png` SHA256 `f8c3cdcbc862b36403b8af802c4b940c3af60e751c49a1284393f1aa816dac2e`; `imagegen_input_upscaled.png` 1756x224 at 4x SHA256 `86d657659b1f678049d198a818a49de5fa9dba005a88a74b277099dc88bc126c`.
- `roi_spec.json`, `roi_manifest.json`, `SOURCE_ROI_QA_TEST_ONLY.json` supply exact provenance and machine-verifiable source/crop hashes. Created using `tools/localization/text_roi_source_pack.py` schema `outrun-hd-text-roi-v1`, no ImageGen API.
- `source_integrity=PASS_TEST_ONLY` **only**. Neither Korean rendered layer nor CLEAN plate, re-composed DDS, C1/C3 approval nor in-game validation exists. Future Korean output should be fitted into original **UI cell/UV safe region** with preserved aspect ratio and reviewed CLEAN; source width mismatch alone is not a rejection.
- A/B legacy tile batches, queues, browser tabs, states and production deployment **untouched**. ROI activation would require independent verified input index, separate state/queue and user manual Portainer deployment. Do not resurrect the 986 tile `ab_batch_queue.py` flow.
- `RUNTIME_VALIDATION=UNTESTED`.
