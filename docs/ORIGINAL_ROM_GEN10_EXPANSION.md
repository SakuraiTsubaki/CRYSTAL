# Original Crystal ROM — Generation 10+ native GBC expansion

Status: **Stage 0 implemented**

This work expands the **original Game Boy Color Crystal engine**. It is not the GBA remake workstream.

## Measured retail baseline

All seven verified Crystal ROMs are 2 MiB and cartridge type `0x10` (MBC3-family RTC + RAM + battery).
The Japanese release already declares 64 KiB SRAM and uses the MBC30-compatible path.
The six international/revision ROMs declare 32 KiB SRAM.

## ROM bank-switch result

All seven ROMs have this exact bank switch entry at file offset `0x0010`:

```text
E0 9D       LDH [hROMBank], A
EA 00 20    LD [$2000], A
C9          RET
```

There is no `AND $7F` in this entry. The full 8-bit bank number reaches the mapper register,
so the core bank switch path can address MBC30 banks `$80..$FF`.

## SRAM bank-switch result

The Japanese release already has an unguarded MBC30-compatible OpenSRAM path.

The six international/revision releases have:

```text
FE 04       CP $04
38 02       JR C, valid
18 10       JR invalid
```

followed by the SRAM/RTC enable and `LD [$4000], A` bank selection.

For the MBC30-class 64 KiB target, Stage 0 changes the immediate bound only:

```text
CP $04 -> CP $08
```

Release-specific byte offsets are stored in `config/native_gbc_stage0.json` and are checked
before mutation. A mismatching ROM is refused.

## Physical ROM transform

`tools/expand_original_crystal.py rom INPUT OUTPUT`:

1. identifies one of the seven verified releases by SHA-256;
2. validates Game Boy header/global checksums;
3. validates the exact bank-switch and OpenSRAM machine-code signatures;
4. applies the international `CP $04 -> CP $08` patch when required;
5. pads the ROM from 2 MiB to 4 MiB with `0xFF`;
6. sets ROM-size code `0x07` and RAM-size code `0x05`;
7. retains cartridge type `0x10` and RTC semantics;
8. recalculates both checksums;
9. verifies deterministic output hashes measured from the supplied ROM set.

No ROM output is committed to GitHub.

## Save transform boundary

The observed Crystal save containers are:

- international: `0x802C`;
- Japanese: `0x1002C`.

Both are nominal SRAM plus 44 bytes. The current evidence set does not include a fresh
byte-for-byte re-read of those save files, so Stage 0 does **not** assume where or how those
44 bytes encode emulator/RTC/container state.

The tool therefore supports only raw cartridge SRAM:

- international raw `0x8000` -> expanded `0x10000`;
- Japanese raw `0x10000` -> preserved `0x10000`.

For international raw SRAM, the original 32 KiB is preserved exactly and new SRAM banks 4..7
are initialized to zero.

`0x802C` and `0x1002C` containers are inspectable but intentionally refused for mutation until
their extra bytes are verified.

## What Stage 0 solves

Stage 0 creates native physical headroom:

- 128 -> 256 ROM banks;
- 2 MiB -> 4 MiB ROM;
- international 4 -> 8 SRAM banks;
- international 32 KiB -> 64 KiB SRAM;
- RTC retained.

This does **not** make the original byte-sized Species/Move/Item namespace modern by itself.

## Stage 1

Next, the original code paths are split at the identity boundary:

```text
legacy u8 ID
    <-> compatibility/import map
    <-> canonical u16 ID
    <-> expanded tables/resources
```

Species, Move, Item, Form/Variety, Ability, Type, and evolution methods remain separate
registries. Party/box/battle/link/script/table consumers are migrated one subsystem at a time,
with the retail seven-ROM family retained as compatibility evidence.
