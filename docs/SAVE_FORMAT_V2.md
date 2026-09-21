# CRYSTAL Save Format V2 contract

Status: design contract for implementation.

## Goals

- Decode every extensible identity to a 16-bit master ID.
- Keep future additions appendable.
- Avoid making Crystal's original Pokémon/save byte layouts the permanent modern schema.
- Permit compact SRAM encoding without leaking compact IDs into gameplay logic.
- Preserve explicit import paths for Japanese and localized Crystal saves.
- Keep RTC state separate from Pokémon/content identity.
- Detect incompatible or corrupted extension blocks.

## Header

A Save V2 implementation must carry at least:

```text
magic
format_version
schema_version
feature_flags
legacy_profile
directory_offset
directory_count
payload_checksum
```

Exact byte offsets are assigned only after each verified Crystal save layout has been
measured.

## Extension directory

Each extension block is described by:

```text
block_type      u16
block_version   u16
offset          u16/u24 build-dependent
length          u16/u24 build-dependent
checksum        u16
flags           u16
```

Unknown optional blocks are skipped by length.
Unknown required blocks make the save incompatible rather than being silently ignored.

## Pokémon identity

The canonical record exposes:

```text
species_id      u16
variety_id      u16
form_id         u16
held_item_id    u16
move_id[4]      u16 each
ability_id      u16
```

Later verified mechanics and metadata are added as canonical fields or versioned blocks
without reusing legacy sentinel values.

## Compact SRAM encoding

Serialized records may replace repeated 16-bit IDs with local dictionary indices.

Rules:

1. dictionary entries map to 16-bit master IDs;
2. index 0 is NONE unless a block explicitly defines otherwise;
3. dictionaries are save-local and never become global engine IDs;
4. loading always resolves to canonical master IDs;
5. dictionary overflow upgrades to a wider block version rather than renumbering IDs.

## Legacy Crystal profiles

Legacy import is profile-driven, not one-layout-fits-all.

Initial verified ROM-header profiles:

- `CRYSTAL_JP_64K_SRAM`
- `CRYSTAL_INTL_32K_SRAM`

The exact Japanese/international save block maps, checksums, mirrored regions, and RTC
interaction are measured from verified binaries/saves before implementation offsets are
locked.

Legacy byte-sized Species/Move/Item values are translated through explicit compatibility
tables. EGG and other sentinels become state flags, not fake master IDs.

## RTC

MBC3 RTC behavior is modeled as a separate subsystem.

A Save V2 implementation may serialize RTC-related transport/continuity metadata in a
versioned extension block when required by the target environment, but gameplay content
IDs never depend on RTC storage layout.

## Compatibility

Save V2 may differ physically from original Crystal SRAM. Compatibility is provided by
explicit import/export code, not by freezing the modern engine to the original field
widths.
