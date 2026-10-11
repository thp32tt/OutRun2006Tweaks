# Upstream PSD workbases (source only, not game replacement)

Source: [Sonic-TV/OR2006Sprites](https://github.com/Sonic-TV/OR2006Sprites) at
`3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`.

This folder contains **actual binary PSD working sources** copied from the source
repository with their original Git blob hashes verified. Each basename begins with
the exact 8-character Git blob prefix, preserving revisions without overwriting.

- Current mirrored priority batch: **10 PSDs, 132,176,274 bytes**, 10 queue indexes.
- Full survey: **184 upstream PSDs**, of which **81 versions match 65 graphics queue
  entries**. The rest are cataloged, not copied.
- Authoritative upstream path, queue index, source Git SHA and size:
  `localization/graphics/plate_library/PSD_IMPORT_CATALOG.json`.
- Check if your asset has an **actually available** PSD before reconstructing:
  `python tools/localization/psd_source_lookup.py --index 60`.
- Inventory and separate local PSD layers:
  `python tools/localization/psd_layer_workbase.py inventory --psd PATH --output DIR`
  or `separate`. Then use `export --english-layers INDEX,...` for a
  full-canvas CLEAN **candidate** and isolated English lettering/effects.
- Preserve source PSDs and extracted English original. Never overwrite them
  with Korean artwork or mistake external PSD previews for the canonical DDS.
- Compare extracted source/CLEAN to the exact original game DDS in both readable
  and RAW orientations, respecting all protected pixels; independent C2 plate
  approval is mandatory, followed by DDS/C3/real-game QA.

**Provenance/rights:** The upstream repository did not include a repository-wide
LICENSE at the pinned commit. This mirror records authorship but does not
claim any new redistribution license. Review rights before repackaging into
a public standalone asset release; distinguish game-derived art from original work.
