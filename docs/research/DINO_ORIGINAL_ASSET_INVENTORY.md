# Dino 246 native PMT inventory

The read-only audit decoded all 17 objects and 41 texture slots in the local PC player Dino asset. Object 0 contains 34 material groups, 5,635 exported vertices and 6,185 triangles. Material group IDs are PMT identifiers, not runtime Draw fingerprints.

| Texture observed in native DDS | Object 0 group | Evidence |
| --- | --- | --- |
| Analog instruments | group 1 / material group 22 / slot 15 | Gauge artwork and 10 native triangles |
| Radio and sliders | group 1 / material group 27 / slot 17 | Control-panel artwork and 6 native vertices |
| Pleated seat upholstery | group 1 / material group 19 / slot 19 | Upholstery artwork and 186 native vertices |

Dash shell, wheel, shaft and stalk groups require visual isolation and a native Draw trace. Their presence or absence as independently replaceable native parts is unresolved. v1–v4 build authored cockpit topology against the original coordinate basis.

Run `python tools/inventory_dino_original_pmt.py <path-to-pmt>` for all decoded group counts, local bounds, texture slots and the source checksum. Keep raw assets and generated models local.
