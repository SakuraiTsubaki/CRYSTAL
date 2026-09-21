# Evidence-driven expansion baseline

Status: **ACTIVE**

CRYSTAL expansion is derived from verified ROMs and observed save-file metadata first.
The architecture must not be frozen from generic assumptions.

## ROM evidence

Seven retail Crystal ROMs were read byte-for-byte locally and only hashes/metadata are
stored in GitHub. All seven are 2 MiB and all pass both Game Boy header and global
checksum validation.

The Japanese release differs materially from the international releases:

- Japan: game code `BXTJ`, cartridge type `0x10`, RAM-size code `0x05` (64 KiB).
- International: `BYTE/BYTF/BYTD/BYTI/BYTS`, cartridge type `0x10`, RAM-size code
  `0x03` (32 KiB).
- Japan therefore requires the MBC30-compatible path; international retail releases use
  the normal MBC3 capacity profile.
- All current ROMs are 2 MiB, but MBC3's documented ceiling is 2 MiB while MBC30 can
  address 4 MiB. The logical resource architecture must therefore not encode an 8-bit
  physical bank assumption.

See `research/evidence/rom_baselines.csv`.

### Zero-filled ROM regions

Zero-filled banks are recorded only as **padding candidates**, never automatically as
safe free space.

The Japanese ROM has complete zero-filled banks `0x60..0x7C` (29 banks). English
Rev 0/Rev A each have only four complete zero banks (`0x75 0x76 0x79 0x7A`), while
the French/German/Italian/Spanish ROMs have only bank `0x7A` fully zero.

Therefore CRYSTAL cannot use "the same free banks in every region" as the expansion
strategy.

## Revision evidence

English Rev 0 and Rev A differ by 584 bytes across 79 contiguous ranges and 8 banks:

`00, 10, 11, 3E, 47, 5C, 7E, 7F`.

Bank `0x5C` contains 546 of the 584 changed bytes. Revision handling must be an
explicit baseline profile rather than a filename alias.

See `research/evidence/revision_diffs.csv`.

## Save evidence

Previously uploaded save-file metadata showed:

- Japanese Crystal: 65,580 bytes (`0x1002C`).
- International Crystal saves: 32,812 bytes (`0x802C`).

These lengths equal the ROM-header SRAM capacities plus exactly 44 bytes:

- `0x10000 + 0x2C` for Japanese Crystal.
- `0x8000 + 0x2C` for international Crystal.

The current runtime does not have the raw `.sav` bytes mounted. Therefore the
placement and meaning of those 44 bytes are intentionally **opaque/unverified**. No
offset, checksum, or RTC-container claim is locked from file size alone.

See `research/evidence/save_baselines.csv`.

## Legacy structure evidence

The public Crystal disassembly is used only to interpret the verified binary evidence,
not as a substitute for the ROMs/saves.

Important constraints from the original structures:

- BoxMon is 32 bytes.
- Species is one byte.
- Held Item is one byte.
- Four Move IDs are one byte each.
- International storage is 14 boxes × 20 Pokémon = 280 slots.
- The source explicitly carries `MONS_PER_BOX_JP = 30`, reinforcing that Japanese and
  international save layouts must not be conflated.
- The international source defines four SRAM banks while also documenting Japanese
  mobile-era SRAM structures separately.

A naive widening of Species + Item + four Move IDs adds 6 bytes per BoxMon. Across 280
international box slots alone that is 1,680 additional bytes before forms, abilities,
modern origin metadata, additional boxes, or other mechanics are considered.

Therefore the expanded engine uses:

1. legacy byte layouts only for import/export compatibility;
2. 16-bit canonical runtime IDs;
3. versioned Save V2 blocks;
4. compact save-local dictionaries where useful;
5. a separate physical storage backend from the logical save schema.

## Mapper consequence

Retail international MBC3 capacity cannot be the final full-generation expansion
ceiling. Japanese MBC30 provides more headroom but is still a physical backend, not the
logical engine contract.

The expanded engine therefore uses 16-bit logical bank/resource IDs and a mapper backend.
A larger physical mapper/storage target is selected only after the complete content and
asset census proves the needed capacity.

## Rule

**Measure first, expand second, populate third.**

Do not claim a save offset, free ROM region, mapper capacity requirement, or future
Generation 10 content count without evidence.
