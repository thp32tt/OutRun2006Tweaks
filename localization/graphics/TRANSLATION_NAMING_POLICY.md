# Korean Graphics Naming Policy

Updated: 2026-10-04 KST
Branch: `korean-localization-recovery-20260928`

This policy is mandatory for graphics production, text catalogs, self-QA, cross-lane QA, and rework.

## Stage names: phonetic transliteration only

Stage names are proper names. Translate them by **Korean phonetic transliteration (음차)**, not by semantic meaning. Mixing semantic translation and transliteration across stage names is forbidden. Descriptive qualifiers outside the proper stage name (for example a reverse-route suffix) may be translated, but the stage-name portion must stay transliterated.

Canonical spellings:

| English stage name | Korean |
|---|---|
| Alpine | 알파인 |
| Ancient Ruins | 에인션트 루인스 |
| Bay Area | 베이 에어리어 |
| Big Forest | 빅 포레스트 |
| Canyon | 캐니언 |
| Cape Way | 케이프 웨이 |
| Casino Town | 카지노 타운 |
| Castle Wall | 캐슬 월 |
| Cloudy Highland | 클라우디 하이랜드 |
| Coniferous Forest | 코니퍼러스 포레스트 |
| Deep Lake | 딥 레이크 |
| Desert | 데저트 |
| Floral Village | 플로럴 빌리지 |
| Ghost Forest | 고스트 포레스트 |
| Giant Statues | 자이언트 스태추스 |
| Ice Scape | 아이스스케이프 |
| Imperial Avenue | 임페리얼 애비뉴 |
| Industrial Complex | 인더스트리얼 컴플렉스 |
| Jungle | 정글 |
| Legend | 레전드 |
| Lost City | 로스트 시티 |
| Metropolis | 메트로폴리스 |
| Milky Way | 밀키 웨이 |
| National Park | 내셔널 파크 |
| Palm Beach | 팜 비치 |
| Skyscrapers | 스카이스크레이퍼스 |
| Snow Mountain | 스노 마운틴 |
| Sunny Beach | 서니 비치 |
| Tulip Garden | 튤립 가든 |
| Water Falls / Waterfalls | 워터폴스 |

If another stage name appears, add its agreed transliteration here before producing final artwork.

## Song titles and music credits: preserve original English artwork

Song titles and music credits are **never translated or redrawn into Korean** unless the user explicitly overrides this policy for a specific title. Preserve their original pixels, casing, punctuation, spacing, and artwork. They are protected regions during clean-plate construction and final QA.

Known title examples include `Rush A Difficulty`, `Shake The Street`, `Who Are You?`, `Passing Breeze`, `Risky Ride`, `Shiny World`, `Splash Wave`, `Night Bird`, `Radiation`, `Magical Sound Shower`, `Last Wave`, and `Keep Your Heart -1989-`. This list is illustrative, not exhaustive.

## Rendering size ceiling

For each localized text element, measure the exact source glyph/effect bounding box including fill, outline, shadow/glow and antialias fringe. The localized glyph/effect bbox must satisfy **both**:

- it is fully contained inside the exact source bbox; and
- `localized_width <= source_width` and `localized_height <= source_height`.

A localized result that is even **1 pixel wider or 1 pixel taller** than the corresponding source text is `REWORK_REQUIRED`, even when no plate/border is visible and even when it still fits inside a larger sprite cell. Equal size is allowed; slightly smaller is preferred when visual clipping risk exists. A sprite-cell or plate rectangle may never be substituted for the source text size ceiling.

For multi-line text, apply the size ceiling to the whole block and, where source lines can be isolated reliably, to each corresponding line.

## Source-style fidelity

Korean lettering must be generated as close to the source typography as the available Hangul glyphs allow. Measure and reproduce source fill/gradient, font weight, outline count and thickness, shadow/glow, slant/italic angle, baseline, alignment, line spacing, proportions and relative scale before rendering.

For multi-line labels, measure each source line. If the source lines share one style, all Korean lines must share that style and must not differ arbitrarily in weight, fill, outline, shadow, slant or scale. If source lines intentionally use different styles, preserve the corresponding per-line differences. A visually convenient but source-unjustified style change is `REWORK_REQUIRED`.
