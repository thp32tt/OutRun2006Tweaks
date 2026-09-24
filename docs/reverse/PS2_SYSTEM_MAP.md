# OutRun 2 SP (Japan) SYSTEM.PS2 map

Source `SYSTEM.PS2` SHA-256:

`a056e2b587530cea1a916a1a04e6ab3f2f7997d8c336e4c16719872e85f7ebc2`

The same executable pack hash at `SLPM_666.28:0x001749F0` maps all 11 SYSTEM entries.

| hash | logical name | bytes | SHA-256 |
| --- | --- | ---: | --- |
| `0x08D1DAD2` | `\IRX\MCSERV.IRX` | 7,713 | `cc85019b02b2a5b1a87e743085c8140cb8bc8a155576745139a521dc503f1699` |
| `0x0D969222` | `\DEL.ICO` | 64,302 | `657dcc53ce748e14d5da585607d4ccd7ef5e7c25d99d3958d5ce2d61a2bba07b` |
| `0x13A80D01` | `\IRX\PADMAN.IRX` | 45,925 | `1e3f3673818a5ddbf58de404cf4dda3de41a634687717bc9117331df71d2bcee` |
| `0x2037C482` | `\IRX\LIBSD.IRX` | 30,085 | `7f22ebd0a7f36458ba1f82b1d26f36266e63372173f8cd72bfc32e5b8a465dd8` |
| `0x2BC3970E` | `\IRX\LGDEV.IRX` | 64,005 | `205e94539293bffe8579b83e09c9e7fb3062fde8216adb7904a4bfac906435e8` |
| `0x3F93C2A8` | `\IRX\SOUNDCD.IRX` | 37,804 | `964359b7e2ae1701405bc63f7edd4fb5875c88924442ee897791baadf0e276ea` |
| `0x51D655AB` | `\IRX\SIO2MAN.IRX` | 5,217 | `7c5116436fd09cbdb3c64ca4b044b86f1cb4c8864fd3e25ce75fa7e8bf89d842` |
| `0x5C70405A` | `\IRX\USBD.IRX` | 35,009 | `564d684d2e9ac10af7d66bb4ec0cb835816e6b5d3fe2f6c38566ff47dc86bb72` |
| `0x841711E4` | `\IRX\MCMAN.IRX` | 103,677 | `52b189205f25e914ef5ea913429af14815c773b24d27ee733a4e708c00306e46` |
| `0xB524E958` | `\VIEW.ICO` | 64,302 | `657dcc53ce748e14d5da585607d4ccd7ef5e7c25d99d3958d5ce2d61a2bba07b` |
| `0xD9BB3420` | `\COPY.ICO` | 64,302 | `657dcc53ce748e14d5da585607d4ccd7ef5e7c25d99d3958d5ce2d61a2bba07b` |

## LGDEV.IRX

The `LGDEV.IRX` entry is the previously missing IOP-side Logitech service.

Verified properties:

- ELF32 little-endian MIPS / R3000
- extracted module name: `LgDev_tb_rb_Driver`
- library/export name: `lgdev`
- imports `usbd`
- version string: `Version 1.12.003 ( Wheel Joystick ), built on Jul  5 2006 at 11:40:35`
- text size about `0xB4B0`
- rodata about `0xB10`
- data about `0x410`
- bss about `0x5E0`
- diagnostic: `fixed memory allocations for %d devices and %d effects`

An IRX export descriptor with magic `0x41C00000` and name `lgdev` and an import descriptor with magic `0x41E00000` and name `usbd` are present.

This closes the earlier missing-binary gap. The next FFB reverse-engineering target is now the **IOP RPC command/ordinal to force-effect payload mapping**, followed by exact field units/scales.

## USBD.IRX

The `USBD.IRX` entry is also present:

- SHA-256 `564d684d2e9ac10af7d66bb4ec0cb835816e6b5d3fe2f6c38566ff47dc86bb72`
- module strings: `USB_driver`, `usbd`, `PsIIusbd 3100`

For game-behavior reconstruction, `LGDEV.IRX` is higher priority than the generic USB transport driver.
