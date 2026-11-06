# Dino 246 native PMT inventory

The read-only audit decoded all 17 objects and 41 texture slots in the local PC player Dino asset. Object 0 contains 34 material groups, 5,635 exported vertices and 6,185 triangles. Material group IDs are PMT identifiers, not runtime Draw fingerprints.

| Texture observed in native DDS | Object 0 group | Evidence |
| --- | --- | --- |
| Analog instruments | group 1 / material group 22 / slot 15 | Gauge artwork and 10 native triangles |
| Radio and sliders | group 1 / material group 27 / slot 17 | Control-panel artwork and 6 native vertices |
| Pleated seat upholstery | group 1 / material group 19 / slot 19 | Upholstery artwork and 186 native vertices |

Dash shell, wheel, shaft and stalk groups require visual isolation and a native Draw trace. Their presence or absence as independently replaceable native parts is unresolved. v1–v4 build authored cockpit topology against the original coordinate basis.

Run `python tools/inventory_dino_original_pmt.py <path-to-pmt>` for all decoded group counts, local bounds, texture slots and the source checksum. Keep raw assets and generated models local.

## Separate cockpit experiment

Run the following against the local player Dino PMT. The output folder should be outside the game installation.

```text
python tools/export_dino_native_cockpit.py <path-to-obj_plcar_dino_pmt.sz> <output-dir>
```

The GLB and OVC contain the native seats, gauge face and radio/control face plus a new three-dimensional trim ring derived from the instrument perimeter. Native position, normal, UV and index payloads remain byte-identical to the original GLB export. The trim occupies a narrow band outside the original panel and extends toward the front of the vehicle in negative native Z. Textures use the original DDS and the exporter interpolation at the selected scale.

The experiment does not contain an isolated steering wheel, column, stalks or the entire dash shell. Use the existing cockpit-only model mode with the experimental file in an isolated test setup. The repository's FitV6 loader resolves a fixed sidecar name and its packaged launcher also validates a pinned hash. Do not use that launcher to install this experimental file. Verify that the existing mode leaves uncovered native parts visible and excludes overlapping native groups before relying on the model in a race.

Offline gates passed on the local PMT: 314 original triangles and 48 trim triangles, standalone GLB validation, production OVC parser acceptance and corrupt-payload rejection. In-game visibility, clipping and headset validation remain pending.
