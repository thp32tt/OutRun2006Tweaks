# OutRun 2006 Korean ROI overlap auto-trim v2 — 2026-11-02

## Purpose
Resolve the 384 `OVERLAPPING_ROI` cases in the existing 104-source
OCR-free bulk **TEST_ONLY** DDS pack, without touching originals,
installed game files, A/B ImageGen queue or C1 QA.

## Algorithm
1. Preserve the existing SHA-verified native HD PNG, DDS target path,
   reviewed English→Korean mapping and deterministic smaller-ROI-first order.
2. Run the existing direct ROI writer unchanged. Collect original
   `OVERLAPPING_ROI` holds (previously 384).
3. For each held row, subtract all accepted ROI rectangles from its approved
   rectangle, producing non-overlapping free strips.
4. Choose the largest free rectangle that covers at least 12% of the approved
   ROI and is at least 16 pixels on each side. Re-render the **whole Hangul
   translation** within that one rectangle; never cut a Korean glyph.
   Clear only the unoccupied pieces of the approved ROI, keeping earlier
   accepted lettering unchanged. This is a quality-reduced fallback.
5. If the free area is empty, too narrow, or the whole phrase cannot fit,
   retain an explicit `OVERLAP_FULLY_COVERED` or
   `OVERLAP_NO_READABLE_FREE_RECT` HOLD. Never mark it as success.
6. Verify all changes stay within approved ROI union and DDS encode/decode
   roundtrip matches the PNG. Export `trimmed_count`, `held_count`,
   `placement_bbox`, and deterministic `overlap_mode=trim` receipts.

## Actual N100 isolated validation
- Unit regressions: 9/9 PASS, including no overwrite of the first Korean ROI,
  full glyph relocation, entirely covered hold and rectangle partition.
- `bash -n entrypoint.sh`: PASS; YAML Compose parsed correctly.
- Q051 native 4096×2048 HD source, **smoke-only** separate output directory:
  old 18 painted / 46 held → new **47 painted / 17 held**,
  including **29 fully re-rendered Korean labels in free space**.
- Q051 `outside_roi_changed_pixels=0`,
  `dds_roundtrip_exact=true`, source unchanged,
  `RUNTIME_VALIDATION=UNTESTED`.

## Automated GitOps integration
Portainer-managed single stack only:
- GitHub: `thp32tt/OutRun2006Tweaks`,
  `localization-controller-recovery-20260928`
- Compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`
- Enable `OUTRUN_OFFLINE_FALLBACK_OVERLAP_MODE=trim`.
- Use `OUTRUN_OFFLINE_FALLBACK_OUTPUT_ROOT=/data/imagegen/text_roi_batches/offline_overlap_v2_test_only`.
- Existing bounded worker runs one SHA-pinned source per minute at `nice -n 15`,
  timeout 900 seconds, retries next cycle if an exception occurs.
- `last_run.json` contains per-cycle total painted/trimmed/held.
- Completed files are deduplicated by existing per-source report and source SHA.
- Old `offline_bulk_test_only` ZIP, source PNG, installed DDS and A/B/C1
  manifests are never modified. v2 results remain `TEST_ONLY_NOT_RUNTIME_APPROVED`.
- The automatically generated v2 ZIP will contain only tested DDS candidates,
  receipts, and safety manifest; installation is not automatic.

**The user will perform the only Portainer Pull latest + Rebuild + Redeploy.
No Docker stack restart/redeploy is performed by ChatGPT.**

## Remaining safety limits
- Overlap trim may shift labels inside the approved ROI, shrink fonts or remove
  protected artwork **within** a box. A visually intact frame/icon is not guaranteed.
- DDS RGBA32 single mip can increase VRAM; DXT5 compatibility/game performance
  remain untested. Canonical DDS may be unavailable for many sources.
- User-visible game screenshots, C1/C3 image QA and real game runtime signoff
  are mandatory before replacing any installed DDS.