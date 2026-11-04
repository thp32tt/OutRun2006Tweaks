# OutRun 2006 Dino V15 R3 — PC PMT native loader graph crosscheck

Analyzed 2026-11-04 against user-supplied crash and r4dius/outrun2-decomp commit e1e1c592b802a6f3f7020a676abd3ba1be479e62.

## Runtime observation
The second game dump from 2026-11-04 23:11:25 KST shows access violation 0xC0000005 at OR2006C2C.EXE+0x3C030 (0x0043C030), trying to write 0x17638000. First dump reported the SAME faulting instruction. Thus reducing R1 mesh from 51,712 to R2 38,992 triangles did not fix the crash. Native DEFLATE buffer allocation contract remains unverified. The prior 2 MiB ceiling was a hypothesis, not a proved game limit.

## Confirmed PMT bug #1: missing shader-record matrix expansion
Decompiled src/platform/pc_pmt_loader.cpp pmt_objects_step_42e4f0 iterates each format and each material. Shader record is at object+0x0C + 24*(material_count * format + material). The R2 patch appended one format and 70 materials but did not resize object0 q[3]. User-owned original Dino PMT has exactly 2 formats, 34 materials, 68*24=1,632 bytes of shader table at offset 9256, ending at the next table offset 10888. A patched 3*104 matrix requires 7,488 bytes. R3 preserves 68 original descriptors, zero-initializes 244 added cells, moves q[3] to an append-only table, and sets the shader pointer.

## Confirmed PMT bug #2: unreferenced cockpit primitive
Decompiled src/platform/pc_pmt_records.hpp PmtNode -> PmtMesh -> PmtPrimitive and src/platform/pc_scene_select_car.cpp 46A560. Original Dino object0 has one root node, one mesh, two primitives; root node mesh[0]=0 and mesh0 has first=0,count=2. R2 appended primitive index 2 but did not change mesh0 count. The new cockpit cannot be drawn. R3 safely changes mesh0 count from 2 to 3 after verifying all reference fields, without replacing original geometry. Camera-mode scoping not yet implemented; this is only a rendering proof.

## Other constraints
The src/pc_pmt.cpp 128 MiB limit and retail_asset_store.cpp zlib 128 MiB limit are added safety limits of the community reimplementation. They DO NOT prove native OR2006C2C.EXE buffer size. New XPR template descriptor6 reports size_word=10936, which is a coherent BC1 128x128 eight-mip pixel size; +128 DDS header gives 11064 bytes. The texture file stores 72 more bytes of padding; it is not currently the primary supported cause of the 0x43C030 crash.

## QA and installation
Source-only changes on isolated branch test/dino-cockpit-v15-pmt-r3-20261104. User must first restore the exact original PMT from the backup. Keep .dino-v12-original.bak. No modified original assets committed to GitHub. HMD_RUNTIME_VALIDATION=UNTESTED. The structural changes may prevent downstream renderer faults, but the observed DEFLATE write fault remains UNRESOLVED until the native loader's allocation is measured. Do not advertise R3 as a crash fix without real PC game testing.
