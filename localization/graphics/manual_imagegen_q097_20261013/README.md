# Q097 manual Korean button localization (2026-10-13)

TUNED → 튜닝, NORMAL → 일반, extracted from user-provided generated RGB image with the button exterior discarded. The actual original HD DDS icon body is preserved, so generated/redrawn buttons do not overwrite original artwork.

Official base: `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds`. Its filename is legacy; actual dimensions are **2048×2048** and byte-exact source SHA-256 `bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364`.

`rebuild.py` composites transparent Korean text sprites over flat source button interiors, restores original raw texture orientation, and **asserts exact DDS SHA-256** `bb306b9a38de88d49602f3c45ff293302d0132290368984af2af65ecf1a766ac`. It verifies no changed pixels outside known text ROIs, and original alpha unchanged.

Build in GitHub Actions on this isolated branch. Do not deploy or treat static QA as game/runtime approval. `RUNTIME_VALIDATION=UNTESTED`.
