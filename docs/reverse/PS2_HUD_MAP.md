# PS2 HUD / Sprite Animation Knowledge Map

This map is based on the supplied Japanese PS2 OutRun 2 SP executable plus `JSPRITE.PS2` and `JSPRANI.PS2`.

## Key result for the VR HUD work

The PS2 executable contains explicit logical resource tables for sprite textures and sprite animation. Both use matching IDs for the main UI range `0x20..0x4A`.

High-value IDs:

- `0x23..0x2A`, `0x30..0x31` — individual Ferrari meter/gauge resources.
- `0x2B GAME_CVT` — primary in-race HUD candidate.
- `0x2C ETC_CVT` — miscellaneous in-race/UI candidate.
- `0x34 ROUTE_CVT` — route/map UI candidate.
- `0x3D RANKING_CVT` — ranking UI candidate.
- `0x3E..0x41 FLAG/CLAR/JENN/HOLL_RANK` — rank-marker/character-rank resources. These are direct candidates for the PC VR rank-marker investigation, but screen-space vs world-attached ownership still requires runtime/XREF confirmation.

## JSPRANI / JSPRITE shared IDs

| ID | JSPRANI | JSPRITE |
| ---: | --- | --- |
| 0x20 | ani_SPRANI_LOGO.sz | spr_sprani_logo_xst.sz |
| 0x21 | ani_SPRANI_LOGO_E.sz | spr_sprani_logo_e_xst.sz |
| 0x22 | ani_SPRANI_TITLE_CVT.sz | spr_sprani_title_cvt_xst.sz |
| 0x23 | ani_SPRANI_METER_246GTS.sz | spr_sprani_meter_246gts_xst.sz |
| 0x24 | ani_SPRANI_METER_288GTS.sz | spr_sprani_meter_288gts_xst.sz |
| 0x25 | ani_SPRANI_METER_360.sz | spr_sprani_meter_360_xst.sz |
| 0x26 | ani_SPRANI_METER_365GTS.sz | spr_sprani_meter_365gts_xst.sz |
| 0x27 | ani_SPRANI_METER_F40.sz | spr_sprani_meter_f40_xst.sz |
| 0x28 | ani_SPRANI_METER_F50.sz | spr_sprani_meter_f50_xst.sz |
| 0x29 | ani_SPRANI_METER_FX.sz | spr_sprani_meter_fx_xst.sz |
| 0x2A | ani_SPRANI_METER_TESTA.sz | spr_sprani_meter_testa_xst.sz |
| 0x2B | ani_SPRANI_GAME_CVT.sz | spr_sprani_game_cvt_xst.sz |
| 0x2C | ani_SPRANI_ETC_CVT.sz | spr_sprani_etc_cvt_xst.sz |
| 0x2D | ani_SPRANI_FIGHT.sz | spr_sprani_fight_xst.sz |
| 0x2E | ani_SPRANI_SELECTOR_CVT.sz | spr_sprani_selector_cvt_xst.sz |
| 0x2F | ani_SPRANI_LOADING_CVT.sz | spr_sprani_loading_cvt_xst.sz |
| 0x30 | ani_SPRANI_METER_512BB.sz | spr_sprani_meter_512bb_xst.sz |
| 0x31 | ani_SPRANI_METER_250GTO.sz | spr_sprani_meter_250gto_xst.sz |
| 0x32 | ani_SPRANI_ADV_CVT.sz | spr_sprani_adv_cvt_xst.sz |
| 0x33 | ani_SPRANI_COMMON_CVT.sz | spr_sprani_common_cvt_xst.sz |
| 0x34 | ani_SPRANI_ROUTE_CVT.sz | spr_sprani_route_cvt_xst.sz |
| 0x35 | ani_SPRANI_ENDING_CVT.sz | spr_sprani_ending_cvt_xst.sz |
| 0x36 | ani_SPRANI_NAME_CMN_CVT.sz | spr_sprani_name_cmn_cvt_xst.sz |
| 0x37 | ani_SPRANI_NAME5A_CVT.sz | spr_sprani_name5a_cvt_xst.sz |
| 0x38 | ani_SPRANI_NAME5B_CVT.sz | spr_sprani_name5b_cvt_xst.sz |
| 0x39 | ani_SPRANI_NAME5C_CVT.sz | spr_sprani_name5c_cvt_xst.sz |
| 0x3A | ani_SPRANI_NAME5D_CVT.sz | spr_sprani_name5d_cvt_xst.sz |
| 0x3B | ani_SPRANI_NAME5E_CVT.sz | spr_sprani_name5e_cvt_xst.sz |
| 0x3C | ani_SPRANI_EFCT_FLOR.sz | spr_sprani_efct_flor_xst.sz |
| 0x3D | ani_SPRANI_RANKING_CVT.sz | spr_sprani_ranking_cvt_xst.sz |
| 0x3E | ani_SPRANI_FLAG_RANK.sz | spr_sprani_FLAG_RANK_xst.sz |
| 0x3F | ani_SPRANI_CLAR_RANK.sz | spr_sprani_CLAR_RANK_xst.sz |
| 0x40 | ani_SPRANI_JENN_RANK.sz | spr_sprani_JENN_RANK_xst.sz |
| 0x41 | ani_SPRANI_HOLL_RANK.sz | spr_sprani_HOLL_RANK_xst.sz |
| 0x42 | ani_SPRANI_CONGRATS_CVT.sz | spr_sprani_congrats_cvt_xst.sz |
| 0x43 | ani_SPRANI_STAFFROLL_CVT.sz | spr_sprani_staffroll_cvt_xst.sz |
| 0x44 | ani_SPRANI_SUMO_FE_CVT.sz | spr_sprani_sumo_fe_cvt_xst.sz |
| 0x45 | ani_SPRANI_DEMOSPLASH_CVT.sz | spr_sprani_demosplash_cvt_xst.sz |
| 0x46 | ani_SPRANI_FRUITY_CVT.sz | spr_sprani_fruity_cvt_xst.sz |
| 0x47 | ani_SPRANI_SPLASH_CVT.sz | spr_sprani_splash_cvt_xst.sz |
| 0x48 | ani_SPRANI_SUMO_LOADING.sz | spr_sprani_sumo_loading_xst.sz |
| 0x49 | ani_SPRANI_SUMO_VSLOAD.sz | spr_sprani_sumo_vsload_xst.sz |
| 0x4A | ani_SPRANI_TAEXTRA_CVT.sz | spr_sprani_taextra_cvt_xst.sz |

JSPRITE-only early IDs are `0x00 spr_font_xst`, `0x03 spr_etc_xst`, `0x12 spr_select_xst`, `0x13 spr_warning_xst`, `0x14 spr_name_entry_xst`, `0x15 spr_ranking_xst`, and `0x17 spr_sumo_fe_xst`.

## Resource tables and code anchors

- JSPRANI path table: `0x0032AA58`; ID = table index + `0x20`.
- JSPRITE path table: `0x0035C96C`; entries are directly indexed by logical resource ID.
- `0x00116C50` — JSPRANI resource request/load. Subtracts `0x20` and indexes the JSPRANI path table.
- `0x00116DD0` — load-queue pump; iterates IDs `0x20..0x4A`.
- `0x00116EA8` — resource release path.
- `0x0030DBA0` — ELF section is explicitly named `Sprani_Update`; updates animation/color/rectangle geometry.
- `0x0030D220..0x0030DB9F` — ELF `.renderCode` region used by the PS2 sprite/render packet path.

## Game-state map

The current game-state index is stored at `0x00434110`. Function `0x001BBAB0` reads it and returns a name from the table at `0x0035CAA8`.

| ID | State | ID | State |
| ---: | --- | ---: | --- |
| 0x00 | SYSTEM | 0x13 | GOAL |
| 0x01 | WARNING | 0x14 | TIMEUP |
| 0x02 | INFO | 0x15 | LINK_TIMEUP |
| 0x03 | ADVERTISE | 0x16 | RESULT |
| 0x04 | TITLE | 0x17 | CONTINUE |
| 0x05 | RATING | 0x18 | ENDING |
| 0x06 | ENTRY | 0x19 | ROUTEMAP |
| 0x07 | ADVEXIT | 0x1A | T_RANKING |
| 0x08 | ERROR | 0x1B | GAMEOVER |
| 0x09 | MENU | 0x1C | GAMEEXIT |
| 0x0A | SELECTOR | 0x1D | GAMERESET |
| 0x0B | SELEXIT | 0x1E | SUMOGAMERESET |
| 0x0C | SELRESET | 0x1F | G_NAMEENTRY |
| 0x0D | START | 0x20 | SUMO_FE |
| 0x0E | WARP | 0x21 | LIVEUPDATE |
| 0x0F | RESTART | 0x22 | OUTRUNMILES |
| 0x10 | GAME | 0x23 | TRYAGAIN |
| 0x11 | GIVEUP | 0x24 | SUMOREWARD |
| 0x12 | SMPAUSEMENU |  |  |

## How to use this for PC VR

For screen-HUD ownership, combine three kinds of evidence instead of graphics-state heuristics:

1. **Resource provenance** — GAME_CVT / ROUTE_CVT / RANKING_CVT / meter / rank resource.
2. **Game state** — especially GAME, GOAL, RESULT, ROUTEMAP and T_RANKING.
3. **Producer call path** — SpriteNode/render queue producer and, for rank markers, the PC world-to-screen / Calc3D2D path.

The `FLAG/CLAR/JENN/HOLL_RANK` resources should be investigated first against the PC rank-marker producer. Their names alone do not prove that they are world-space billboards.
