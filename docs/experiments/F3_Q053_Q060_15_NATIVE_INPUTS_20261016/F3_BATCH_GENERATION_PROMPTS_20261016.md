# F3 grouped image-generation upload sheets

These are actual **lossless source contact sheets** prepared from exact native HD PNG crops, unlike the old review JPEGs or previous individual-crop ZIPs.

| Family | Upload image | Native pixels | Layout |
|---|---|---|---|
| Q053 mission yellow/navy | Q053_MISSION_YELLOW_NAVY_IMAGEGEN_BATCH_INPUT.png | 1751×909 | 2 columns × 4 rows = 8 Korean words |
| Q060 metallic | Q060_METALLIC_GRADIENT_IMAGEGEN_BATCH_INPUT.png | 1399×1576 | 1 column × 7 rows |

Source crops retained 1:1 without rescaling; original alpha may include scenery, unrelated labels or panels. It is a **reference input**, not approved CLEAN or DDS. Korean translation drafts need independent SSOT review. The generated output must contain Korean lettering/effects only, transparent canvas, separated slot layout, no English or foreground props.

## Q060 (7 phrases, top → bottom) generation prompt

Use the attached ONE source sheet of seven separated OutRun 2006 metallic HD UI words. Replace the English text in each of the seven slots with Korean, top to bottom exactly:
1. CONTINUE? → 계속?
2. RETRY → 재시도
3. PLEASE WAIT → 잠시 대기
4. TRY AGAIN? → 다시 시도?
5. STAGE CLEAR → 스테이지 클리어
6. PASS!! → 통과!
7. DUMPED! → 차였어!

Create **one 7-slot batch PNG** with transparent RGBA background, only Korean text+outline+shine+shadow, respecting each slot's original slant and color gradient. No English text, incidental numerals, icons, shapes, cards, screenshots, backgrounds, explanations or status posters. Keep all 7 positions separated and allow adequate glyph margins; preserve sheet layout so each slot can be recropped and resized into the original DDS. No invented Korean characters or cropped characters. If output resolution differs, preserve relative slot placement. This is not a DDS or a game-completion certificate.

## Q053 (8 phrases, left → right, top → bottom) generation prompt

Use the attached ONE source sheet of eight OutRun 2006 yellow/navy mission phrases, arranged 2 columns × 4 rows. Replace each phrase in this reading order:
1. HIT THE CARS! → 차량을 들이받아!
2. DODGE THE BOMBS! → 폭탄을 피해라!
3. AVOID ABDUCTION! → 납치를 피해라!
4. AVOID METEORS! → 운석을 피해라!
5. DRIBBLE BEACH BALL! → 비치볼을 드리블해!
6. PHOTOGRAPH THE SIGHTS! → 명소를 촬영해!
7. HIT THE DUCKS! → 오리를 맞혀라!
8. SEE THE SIGHTS! → 명소를 구경해!

Create **one 8-slot batch PNG** on fully transparent RGBA. Reproduce bright yellow fill, dark navy outlines, soft outer glow, chunky arcade lettering, with only the Korean text+effects in each original slot. Neighbor art, original interface fragments, partially visible neighboring letters (for example left edge of DRIBBLE or SEE source) must **not** be copied. Do not produce a screenshot or infographic, and do not include English, numbers, icons, source backing, frames, checkerboard painting or any fake Hangul. Match the 2-column/4-row slot layout, maintain generous gaps; it will be independently recropped and resized.

## Caveats

- Both groups have mixed source background and edge-touching content. English whole-crop alpha **MUST NOT** become a CLEAN mask.
- Q053 has some truncated English source reference and neighboring text fragments; replace by the precise Korean mapping above instead of visually copying corrupt source letters.
- These sheets do **not** establish F3 output, DDS integration, or pass. Existing F3 status remains HOLD.

Layout coordinate map: F3_BATCH_INPUT_LAYOUT.json.

Hashes: Q053 `489623928c4af44933bbdc9e82e9d95e2820ad5a9cc14c222edf8e83aba28a35`; Q060 `35236cb333faac89af255907ee30d96e6de34a9296651bcadf7920f1369f5437`.