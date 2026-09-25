# Graphics Orientation & Preserve Policy

Updated: 2026-09-25 22:50 KST
Branch: `korean-localization-clean`

This policy is mandatory for all Korean graphics localization work.

## Source-of-truth rule

1. **Always inspect the original game DDS from the original analysis archive before editing.**
2. Do **not** infer orientation from a previously generated Korean FULL-DRAFT DDS or from a generated preview.
3. The original raw DDS may intentionally contain per-sprite mirroring, rotation, upside-down text, or mixed orientations because the runtime sprite/UV path corrects it in game.
4. Orientation is therefore determined **per element / per sprite**, not per whole texture.

## Translation exclusion rule

The following embedded text is preserved exactly as original artwork and is excluded from Korean translation unless later explicitly approved:

- vehicle model names,
- vehicle variant names,
- manufacturer/brand marks,
- logos,
- song titles / music credits,
- legal/licensing marks,
- product/model codes where they identify the vehicle.

When a selector tile contains a vehicle picture plus vehicle/model name, preserve the original picture **and** original vehicle/model-name artwork, including its raw DDS orientation.

## Orientation rule

For every localizable text/image segment:

1. Inspect the corresponding segment in the **original raw DDS**.
2. Record its original orientation: normal / mirror-X / mirror-Y / rotate-180 / other atlas-specific transform.
3. If the original text is mirrored, rotated, or upside down in the raw DDS, the Korean replacement must be rendered with the **same raw-texture transform**.
4. If artwork and text use different transforms in the same DDS, preserve those transforms independently.
5. Never normalize the entire DDS to make it visually upright in an image viewer.
6. Never assume that a vehicle/icon and adjacent text share the same transform.
7. Game-view screenshots are validation evidence; raw DDS orientation is the construction reference.

## Confirmed examples

### `spr_sprani_selector_cvt_Exst/841E796B_512x128.dds`
- The top/bottom blue selector tiles are vehicle/model-name artwork.
- Vehicle/model names and their vehicle pictograms are **preserve-original** and are not translated.
- Preserve the raw texture orientation exactly.

### `spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds`
- Branch-road text and loading labels are intentionally stored with non-upright transforms in the original raw DDS.
- Korean replacements must reproduce each original element's raw transform rather than being made upright in the DDS.
- Existing non-text artwork should remain source-faithful unless localization requires replacing embedded text.

## QA gate before marking an asset ready

An asset cannot move to final candidate status until all are checked:

- original DDS inspected,
- preserve-vs-translate classification confirmed,
- per-element transform confirmed,
- Korean text rendered with matching raw transform,
- non-text original artwork preserved where possible,
- dimensions/alpha/DDS format/mip behavior preserved,
- in-game screenshot validation completed.

## Resume rule

On any future request such as **"이어서 작업해줘"**, read and apply this policy before producing or revising localization artwork.
