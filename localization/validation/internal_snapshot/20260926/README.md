# Internal localization validation snapshot — 2026-09-26

Source Library folder: `/아웃런2 한글화`

This snapshot is for verification only and must not be merged into VR/FFB source branches.

## Uploaded directly

- 23 fallback / work-in-progress text files are preserved under `library_fallback/`.
- GitHub placeholder reports `BATCH45_37759842_EXACT_DIFF_ISOLATION_REPORT.json` and `BATCH53_377_GLYPH_MASK_PLAN_REPORT.json` were restored from the non-empty Library originals.

## FULL_DRAFT raw-byte archive

`OutRun2_Korean_GFX_FULL_DRAFT_Test.zip` is preserved as 25 consecutive 1,000,000-character base64 chunks (last chunk shorter).

Reconstruct:

```bash
cat full_draft_b64_1m/part-*.b64 | base64 -d > OutRun2_Korean_GFX_FULL_DRAFT_Test.zip
```

Verified result:

- Size: `18,700,347` bytes
- SHA256: `5512dad798a4ddb4872e4aa3e69438537f75f488f439317d7b95c0eb372b6c78`
- `unzip -t`: PASS, no compressed-data errors

## Complete inventory

See `LIBRARY_MANIFEST.json` for all 122 files, including filename, Library path, byte size, MIME type, file id, modification time, and GitHub transfer status.

Some generated binary artifacts are visible in Library but the current GitHub connector accepts text/base64 content rather than a Library file reference. Those rows are marked `RAW_TRANSFER_BLOCKED_BY_CURRENT_GITHUB_CONNECTOR`; they are intentionally listed rather than silently omitted.
