# OutRun HD user manual ImageGen submission — candidate-only QA (2026-11-10 KST)

## Proven input and persistence
- User-uploaded `Downloads (15).zip`: **17,966,810 bytes**, SHA-256 `290e1280f5151ba3bc182c7877fed4348e6b78e472fd6766cb6dad38ec603909`.
- Unpacked **38 RGBA PNGs, 33 unique SHA-256, five exact duplicate groups**; this count is distinct from the 6 exact source ROI HOLDs and does not imply 33 releasable assets.
- Output of deterministic existing-art-only trim and fit: `OUTRUN_HD_MANUAL_SUBMISSION_QA_TEST_ONLY_20261110.zip` **381,232 bytes** SHA-256 `67522bd1ef6195362355b9e2c489a6418a823d1efe116a6f010f653e80001102`; saved to authenticated user's personal Library `/아웃런 한글화 신규/OUTRUN_HD_MANUAL_SUBMISSION_QA_TEST_ONLY_20261110.zip` (library file `libfile_d43ecf826fac8191a8a4caa381c0d560`).
- ZIP contains SHA manifest for all 38 inputs, 6 target ROI QA rows (5 distinct PNG bytes), native-HD target dimensions, semi-transparent fringe trimming, no font generation, source-aware two-line candidate repacking of `PAUSE MENU`, source-shadow band gating, and a full/50%-size preview. **Test candidates are not automatically imported or admitted to production.**

## Exact source-bound ROIs and candidate SHA

| ROI | English | Korean | Candidate SHA256 | Candidate geometry | Native lines | Decision |
|---|---|---|---|---|---|---|
| `Q193_53d6085638ec9c80` | OUTRUN SHOWROOM | 아웃런 쇼룸 | `e6df419c9300829cca7b10d4c1bf19686bed2ab958f437c968ef9ab5d8fbb8d3` | 405×137, 2 lines | 2 | C1 pending |
| `Q205_bf0d812a762a295e` | SORRY! You need more miles! | 죄송합니다! 마일이 더 필요합니다! | `9a7d7f71bccde056898167b340a9d4c19807e098d9d62181b127a4031b74ebac` | 677×187, 2 lines | 2 | C1 pending |
| `Q205_0e672581cf837a7d` | SORRY! You need more miles! | same Korean | same SHA (source-matched Switch/Xbox) | 677×187, 2 lines | 2 | separate C1/source-DDS validation |
| `Q226_17d32be0f1ec1624` | STAGE | 스테이지 | `c837654b9639842edfeaee749c4ae3586ca500d4d3fa1fd3e061f6d70da5ac07` | 435×201, bottom 1 text line | 3 full alpha bands | **HOLD_SOURCE_3_LABELS_NEEDS_CHILD_ROI_AND_CLEAN_MASK**; original crop also includes GOALS and OUTRUN2; cannot clear entire rectangle |
| `Q046_1c32c8310a619ea2` | PAUSE MENU | 일시정지 / 메뉴 | `4a0d17f50377cd336b9afaca3e6cae2a7cd7f9268cf62a62b1fe83cf1589fb26` | 265×147, 2 lines | 2 | Existing generated glyph pixels reorganized to `일시정지\n메뉴`; independent text-equivalence and C1 pending |
| `Q101_ce6fc95e42c9cdff` | Steering Wheel : | 스티어링 휠: | `40e219c656bbb984b8785e93aa84a76fdd1c157b1b69ffb3da74f9ef2b389992` | 487×145, 1 logical line | source 3 AA/shadow bands representing 1 logical line | C1 pending; exact-source AI-independent source-effect gate CI `42740015091` SUCCESS |

## Source-alpha problem and actual correction
- `tools/localization/hd_strict_qa.py` now uses `source_effect_band_lines` to join **only** short horizontally-contained AA/shadow slivers vertically adjacent to a >=4x taller central source text band, preserving unrelated headings and full-height lines. Source-only reconstruction, not a visual/QA acceptance.
- `tools/localization/test_hd_strict_qa.py` checks a native `Steering Wheel :`-shaped 3-band case and explicitly rejects merging independent text labels. GitHub Actions `42740015091` **SUCCESS** on exact SHA `48328cca21e137e5f822a41f24aac8e0dd54116f`. Recheck all full DDS output on its own SHA.
- `Q226` is still HOLD because the source crop has 3 separate English UI words/lines. No automatic rectangular English deletion or partial label overwrite is approved.

## Next verification (never fictional)
- Only 5 of 6 ROI test candidates have logical line-count conformity. C1 independent visual QA + original English CLEAN, other ROI/pixel protections, native DDS rewrite, BC3 whole mip chain and real-game QA remain open.
- Do not overwrite prior high-quality A/B PNGs without independent source/translation/quality and non-regression evidence.
- 654 prior HOLD, 300 TEST_ONLY paints and 58 DDS remain the last known completed run metrics; uploaded artwork does **not** automatically imply a HOLD count reduction or release.
- `release_approved=false`, `runtime_validation=UNTESTED`.

