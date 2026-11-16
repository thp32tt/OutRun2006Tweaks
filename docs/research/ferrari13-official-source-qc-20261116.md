# Ferrari 13 external model acquisition audit — 2026-11-16 KST

**Result: 0/13 newly downloaded, 0/13 converted to OVC, 0/13 Quest 3 runtime-tested.** F50/F40/288 GTO belong to a separate existing 3-car test package. Do not present this audit as a 13-car playable build.

Public Sketchfab Data API `GET /v3/search` and `GET /v3/models/{uid}` verified candidate names, downloadability, stated licenses and triangle counts. Official `GET /v3/models/{uid}/download` requires **user OAuth**, even for free CC models; no such token or integration was provided. Unofficial viewer scraping and authenticated-access bypass were not used.

| Target car | Candidate | Displayed license | Triangles | Current outcome |
|---|---|---|---:|---|
| Ferrari 365 GTS/4 Daytona | [Sketchfab](https://sketchfab.com/3d-models/b7510383e3fb4a63a26d45e424a9f292) | CC-BY | 88,059 | `OFFICIAL_OAUTH_REQUIRED` |
| Dino 246 GTS | [Sketchfab](https://sketchfab.com/3d-models/3fefdbf09db342de8279b352bd5f325d) | CC-BY-NC-SA | 286,494 | `RIGHTS_UNVERIFIED_CSR2_EXTRACT` |
| Ferrari 360 Spider | [Sketchfab](https://sketchfab.com/3d-models/216e8f0ad97e44588c7cd55690bacc0a) | CC-BY | 1,437,245 | `OFFICIAL_OAUTH_REQUIRED` |
| Ferrari F355 Spider | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari 575 Superamerica | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari Testarossa Spider | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari 328 GTS | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari 250 GTO | [Sketchfab](https://sketchfab.com/3d-models/b12954e759df43e882a0136c1403a800) | CC-BY | 46,015 | `OFFICIAL_OAUTH_REQUIRED` |
| Ferrari 512 BB | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari 550 Barchetta | [Sketchfab](https://sketchfab.com/3d-models/e5de7426fc8f4ae5a6b60c0b5d7c34f4) | CC-BY | 117,447 | `OFFICIAL_OAUTH_REQUIRED` |
| Ferrari F430 Coupe | [Sketchfab](https://sketchfab.com/3d-models/2790d9ffd8ef4ca681d350a27c0ec0cb) | CC-BY | 2,284,171 | `OAUTH_AND_RUNTIME_MEMORY_LIMIT` |
| Ferrari F430 Spider | Not found | — | — | `EXACT_MODEL_NOT_FOUND` |
| Ferrari Enzo | [Sketchfab](https://sketchfab.com/3d-models/8553d226088e4497ae05decc15df6609) | CC-BY | 30,661 | `OFFICIAL_OAUTH_REQUIRED` |

**Rights:** A CC label uploaded by a Sketchfab user does not prove the uploader owned the underlying mesh. The Dino 246 GTS candidate says "MODEL AND TEXTURES FROM CSR2" and is blocked pending original publisher permission. Every other candidate needs independent provenance, interior/UV and exact-variant checks.

**Fidelity:** Do not substitute Daytona SP3 for 365 GTS/4, F355 Berlinetta for Spider, 575M for 575 Superamerica, a Testarossa coupe for Spider, 308 for 328 GTS, 512 BB LM for road BB or F430 coupe for Spider. Do not use auto-LOD reduction to bypass the runtime budget. Candidate F430 at 2,284,171 triangles already exceeds the current 2,000,000-triangle offline converter limit. 360 Spider has 1,437,245 triangles.

**Required for a real playable 13-car build:** authorized exact car assets → GLB archive and author rights review → original triangle/material/normal-map and cockpit QA → native model alignment and wheel contact → game car ID mapping → preserve-polycount OVC3 budget review → Windows CI → Quest 3 runtime → independent rollbackable install package.

Official reference: https://sketchfab.com/developers/download-api/downloading-models
