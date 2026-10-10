# DX9Ex 2026-10-11 Quest3 third crash and historical rank comparison

Source: B HUD / C FLARE session build b913ef69e14aa2472260350f676fccae1c06a772; exact user minidump OR2006C2C.EXE.20261011011117.zip, EXE SHA 68ceb386...; log state 19/20.

## Crash proof, not speculation
- Earlier 2026-10-10 dumps: EIP OR2006C2C.EXE+0x97C5F inside five-byte E9 rel32 detour at +0x97C5C, immediately after original sub_4B9200 E8 at +0x97C57.
- Latest dump 2026-10-11 01:11:17 KST: exception 0xC0000005 reading 0x0000001E, EIP EXE+0x97E75. MemoryList stream of the MINIDUMP contains `E9 B5 DD 12 01` at EXE+0x97E72; EIP is the FOURTH byte of that detour, immediately after original E8 +0x97E6D. It is another one of 19 original result text parents.
- Real runtime log: `VR P0 RESULT TEXT B9200 calls=64 state=20` immediately before crash in first B session; other session calls=4096 at GOAL, matching user-observed graph animation progressing farther before crash.
- Prior fix blacklisted only +0x97C57; installed 18 of the same unsafe +5 midhooks. That is why crash moved instead of disappearing.
- Repair: **install NONE** of the 19 pairs of unsafe result print source midhooks. Keep all original E8 and result graph unchanged; this removes the confirmed detour fault mechanism, not claims the graph's double stereo already fixed. ABI of shared B9200 needs independent proof before converting these calls to wrapper proxies.

## True known-good source comparison
- Historical R64 `10c73daa037b5cc521b42ce7fb3a7cc1820b1921` and HMD-success R62 `945e4471d6463f757f38b4b39d3eb8e492b2254f` have `src/vr/d3d9/stereo_renderer_r7.inc` *identical Git blob* `e024100135b9c8d9805c8a6b369b369973428abf`. Current R7 differs in gameplay state gating, but the sky fixed-function stereo `rotationOnly` body retains identical head/IPD removal. Thus guessing that the old sky formula must be rewritten is unsound.
- Historical rank R57/R62 `Calc3D2D_dest` tested original EXE direct E8 at 0xBAEE2, return site 0xBAEE7. This build logs `rankProducerObserved=True`, `projectedMarkerSemanticCount=0`, `rankExactCalcObserved=False` when gameplay ordinal appears; HMD sees detached 1st-5th. Fresh original-source wrapper intercepts exactly this E8 using original void __cdecl ABI and calls existing Calc3D2D pipeline with scoped `RankMarkerExactCalcEdge`. Keeps NaviPub and rival separate. If no exact call occurs, the new log reports no change; **RUNTIME_VALIDATION=UNTESTED**.
- Present sky split and +TIME duplications are still OPEN. No global sky/alpha or time changes were made without optical source proof.
- Test: OutRun result graph reaching top without EIP+0x97E75 or +0x97C5F, original result time/map still visible (graph may still be double); normal mission finish time unchanged; compare rank marker yaw; record +TIME and sky transition separately.
