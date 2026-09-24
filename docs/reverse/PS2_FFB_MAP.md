# OutRun 2 SP (Japan) PS2 FFB map

Source binaries analyzed:

- `SLPM_666.28` SHA-256 `bc5dd6d836bf34546ef9f047ad2bcb99c5ef5a713767a161d0c342af33f38c34`
- `IOPRP310.IMG` SHA-256 `1cf5475f533f04d161bbb4b08179df156afeb7b400f207c88dcf1e39466679b6`
- `SYSTEM.PS2` SHA-256 `a056e2b587530cea1a916a1a04e6ab3f2f7997d8c336e4c16719872e85f7ebc2`
- ELF entry `0x00100008`
- GP `0x0043BC70`

The retail ELF is stripped. Names in `reverse/ps2/semantics.json` are semantic names derived from literal diagnostic strings plus direct MIPS call edges; they are not claimed to be original Sega symbols.

## Verified EE-side FFB path

| Address | Semantic | Low-level target |
| --- | --- | --- |
| `0x00132488` | wheel/module initialization | literal `LGDEV.IRX`; wrapper init `0x001333D8` |
| `0x001354B0` | download condition force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135640` | update condition force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x001357B8` | download constant force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135910` | update constant force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x00135AA8` | start force effect | `0x00167C08 lgDevAStartForceEffect` |
| `0x00135B60` | stop force effect | `0x00167CA0 lgDevAStopForceEffect` |
| `0x00135C18` | destroy force effect | `0x00167888 lgDevDestroyForceEffect` |
| `0x00135CD8` | set overall force gain | `0x00167670 lgDevSetDeviceProperty` |
| `0x00135D40` | download periodic force | `0x00167720 lgDevDownloadForceEffect` |
| `0x00135EB0` | update periodic force | `0x00167AB8 lgDevAUpdateForceEffect` |
| `0x001362A0` | Logitech enumerate/open | `lgDevEnumerate/Open/SetDeviceProperty/Close` |

The supplied executable contains `EZ Wheel Wrapper v4.01`, Logitech wheel diagnostics and the EE-side `liblgdev` RPC implementation. Condition, constant and periodic effects have separate wrapper paths but converge on the same low-level force-effect payload API. This makes the effect structure passed into `lgDevDownloadForceEffect` / `lgDevAUpdateForceEffect` the next high-value target when comparing PS2 behavior with the PC DirectInput FFB implementation.

Update/start/stop use asynchronous `lgDevA*` calls in this build. Function `0x00167910` is repeatedly called immediately before those requests and is treated only as an unnamed synchronization/RPC helper until stronger evidence exists.

Ramp-force diagnostic strings are present, but no direct code XREF is verified yet. Do not assign a ramp wrapper address from adjacency alone.

## IOPRP310

The ROMDIR image was parsed into the standard runtime modules: SYSMEM, LOADCORE, SIFCMD, SIFMAN, THREADMAN, IOMAN, MODLOAD, FILEIO, CDVDMAN, CDVDFSV, LOADFILE, TIMEMANI, ROMDRV, EESYNC, SYSCLIB and STDIO.

`LGDEV.IRX` is not inside IOPRP310 itself, but it has now been recovered from `SYSTEM.PS2` together with `USBD.IRX`. See `docs/reverse/PS2_SYSTEM_MAP.md`.

## SYSTEM.PS2 / IOP-side FFB

`SYSTEM.PS2` hash `0x2BC3970E` maps exactly to `\\IRX\\LGDEV.IRX` and hash `0x5C70405A` maps to `\\IRX\\USBD.IRX` using the recovered executable pack-hash function.

`LGDEV.IRX` SHA-256 is `205e94539293bffe8579b83e09c9e7fb3062fde8216adb7904a4bfac906435e8`. It is an ELF32 little-endian MIPS/R3000 IRX with module/library name `lgdev`, imports `usbd`, and contains the version string `Version 1.12.003 ( Wheel Joystick ), built on Jul  5 2006 at 11:40:35`. Its diagnostics include fixed memory allocations for devices and force effects.

This closes the missing IOP service gap. The next useful reverse pass is to map `lgdev` export/RPC ordinals to effect commands and reconstruct the exact force-effect payload fields/units before transferring any PS2 tuning constants to the PC DirectInput implementation.

## Map-generation result

The local full map generated during this analysis indexed:

- 561,460 EE instructions
- 38,738 direct JAL calls
- 49,884 code references
- 22,169 data references
- 10,101 strings
- 2,490 exact string XREFs
- 8,537 inferred function anchors
- SQLite `integrity_check = ok`

Production PC FFB changes should use this PS2 map as comparative evidence, not blindly copy numeric values until the force-structure fields and units are confirmed.
