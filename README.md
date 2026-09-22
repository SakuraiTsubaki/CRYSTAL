# CRYSTAL

Evidence-driven modernization workspace for Pokémon Crystal.

## Current phase

**Phase 0 — measure the real Crystal ROM/save family, then expand the original GBC engine for Generation 10+**

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

Seven matching Crystal save containers were previously observed:

- Japanese: 65,580 bytes (`0x1002C`)
- six international/revision saves: 32,812 bytes (`0x802C`)

Those sizes equal nominal SRAM plus 44 bytes in both families. Exact save offsets remain
unlocked until the raw save payload/container layout is re-verified.

## Native expansion contract

- The runtime target is the **original Game Boy Color Crystal engine**, not a GBA port.
- GBA remakes are a separate project/workstream.
- 16-bit append-only master IDs for Species, Variety, Form, Move, Item, Ability, Type,
  Evolution Method, Resource, and Feature.
- Species / Variety / Form are separate identity layers.
- 16-bit logical Resource and ROM-bank IDs.
- Retail MBC3/MBC30 limits are compatibility backends, not logical ID limits.
- `CRYSTAL_SAVE_V2` is versioned and has separate JP/international legacy importers.
- Zero-filled ROM data is only a padding candidate until proven safe.
- No Generation 10 names/counts/mechanics are invented before verified data exists.

## Evidence and implementation files

- `research/evidence/rom_baselines.csv`
- `research/evidence/save_baselines.csv`
- `research/evidence/revision_diffs.csv`
- `config/storage_profiles.json`
- `config/engine_capacity.json`
- `docs/EVIDENCE_DRIVEN_EXPANSION.md`
- `docs/GEN10_EXPANSION_ARCHITECTURE.md`
- `docs/SAVE_FORMAT_V2.md`
- `engine/include/extended_ids.inc`
- `engine/include/resource_directory.inc`
- `tools/validate_capacity.py`

GitHub Actions validates that the capacity contract still agrees with the recorded ROM
and save evidence.

ROM binaries are never committed.
