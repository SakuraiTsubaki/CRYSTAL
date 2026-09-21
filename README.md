# CRYSTAL

Evidence-driven modernization workspace for Pokémon Crystal.

## Current phase

**Phase 0 — measure the real Crystal ROM/save family, then expand for Generation 10+**

The expansion contract is not allowed to outrun the evidence.

### Verified ROM inputs

Seven retail ROMs have been read byte-for-byte and recorded by SHA-1/SHA-256:

- Japanese `BXTJ` Rev 0
- English `BYTE` Rev 0
- English `BYTE` Rev A
- French `BYTF`
- German `BYTD`
- Italian `BYTI`
- Spanish `BYTS`

All are 2 MiB and pass header/global checksums.

The Japanese ROM declares 64 KiB SRAM and follows the MBC30-compatible hardware path.
The six international ROMs declare 32 KiB SRAM and use the retail MBC3 capacity profile.

See `research/evidence/rom_baselines.csv`.

### Save inputs

Seven matching Crystal save files were previously observed:

- Japanese: 65,580 bytes (`0x1002C`)
- six international/revision saves: 32,812 bytes (`0x802C`)

Those sizes equal nominal SRAM plus 44 bytes in both families. The raw `.sav` bytes are
not mounted in the current runtime, so the 44 bytes remain opaque and exact save offsets
are deliberately not locked yet.

See `research/evidence/save_baselines.csv`.

## What the evidence changes

- JP and international Crystal require separate legacy save profiles.
- EN Rev 0 and Rev A remain separate baselines: 584 bytes differ across 8 ROM banks.
- Japan has many zero-filled ROM banks, while international builds do not; fixed
  "free-bank" expansion is therefore not portable across regions.
- Retail MBC3's 2 MiB ROM limit cannot be the logical Generation 10 engine limit.
- MBC30 gives the Japanese path more physical headroom, but mapper capacity remains a
  backend detail rather than an ID/resource identity limit.
- Original BoxMon is 32 bytes with byte-sized Species, Item, and Move IDs. Save V2 uses
  canonical 16-bit IDs plus compact/versioned serialization instead of blindly widening
  the legacy record in place.

## Expansion contract

- 16-bit append-only master IDs for Species, Variety, Form, Move, Item, Ability, Type,
  Evolution Method, Resource, and Feature.
- Species / Variety / Form are separate identity layers.
- 16-bit logical Resource and ROM-bank IDs.
- Physical mapper and save storage are backends.
- `CRYSTAL_SAVE_V2` is versioned and has explicit JP/international legacy importers.
- Zero-filled ROM data is only a padding candidate until proven safe from source/binary
  references.
- No Generation 10 names/counts/mechanics are invented before verified data exists.

## Evidence and implementation files

- `research/evidence/rom_baselines.csv`
- `research/evidence/save_baselines.csv`
- `research/evidence/revision_diffs.csv`
- `research/evidence/reference_sources.csv`
- `config/storage_profiles.json`
- `config/engine_capacity.json`
- `docs/EVIDENCE_DRIVEN_EXPANSION.md`
- `docs/GEN10_EXPANSION_ARCHITECTURE.md`
- `docs/SAVE_FORMAT_V2.md`
- `engine/include/extended_ids.inc`
- `engine/include/resource_directory.inc`
- `tools/analyze_crystal_inputs.py`
- `tools/validate_capacity.py`

GitHub Actions validates that the capacity contract still agrees with the recorded ROM
and save evidence.

## Next work

1. re-read and hash the seven raw Crystal saves;
2. map JP vs international SRAM/checksum/RTC/container layouts byte-for-byte;
3. import the Crystal source baseline into this repository with ROM-byte verification;
4. replace byte-sized cross-subsystem identity accessors with canonical 16-bit accessors;
5. implement Save V2 and mapper-independent placement;
6. census later-generation data/assets before selecting the final expanded physical
   mapper/storage backend.

Original ROM binaries are never committed.
