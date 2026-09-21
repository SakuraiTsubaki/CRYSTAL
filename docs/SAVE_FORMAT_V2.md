# CRYSTAL Save Format V2 contract

Status: **evidence-driven design; raw save byte mapping still open**

## 1. Evidence boundary

The save architecture is not inferred from ROM header size alone.

Observed uploaded save-file lengths:

- Japanese Crystal: 65,580 bytes (`0x1002C`).
- International Crystal: 32,812 bytes (`0x802C`).

The corresponding ROM headers declare:

- Japan: 65,536 bytes SRAM.
- International: 32,768 bytes SRAM.

Both observed save containers therefore contain 44 bytes beyond nominal SRAM capacity.
Those 44 bytes remain **opaque** until the raw `.sav` files are read again. This
document does not assume whether they are a prefix, suffix, RTC block, emulator metadata,
or another container structure.

## 2. Legacy save profiles

At minimum:

- `CRYSTAL_JP_64K_SRAM`
- `CRYSTAL_INTL_32K_SRAM`

ROM revisions remain separately identified under those profiles. EN Rev A is not
silently merged into EN Rev 0.

Japanese and international layouts must have separate parsers. The source reference
also defines `MONS_PER_BOX_JP = 30` while the international format uses 20 Pokémon per
box, further proving that one fixed parser is insufficient.

## 3. Original Pokémon record pressure

Legacy BoxMon is 32 bytes and stores:

```text
species        u8
item           u8
moves[4]       u8 each
ot_id          u16
exp            u24
stat_exp[5]    u16 each
dvs            u16
pp[4]          u8 each
happiness      u8
pokerus        u8
caught_data    u16
level          u8
```

Species + Item + Moves alone consume six one-byte identity fields.

Naively widening those six fields to u16 increases every BoxMon by six bytes. Across
280 international box slots that is +1,680 bytes before any modern fields are added.

Save V2 therefore does not replace each legacy byte field in place.

## 4. Canonical Pokémon identity

Decoded runtime records expose at least:

```text
species_id      u16
variety_id      u16
form_id         u16
held_item_id    u16
move_id[4]      u16 each
ability_id      u16
```

Additional verified generation-specific data is attached through versioned canonical
fields/blocks.

## 5. Serialized Save V2

Save V2 is a versioned logical format with a physical storage backend.

Minimum logical header:

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

Extension directory entries contain a block type/version, storage location, length,
checksum, and flags.

Unknown optional blocks are skipped by length. Unknown required blocks make the save
incompatible rather than silently dropping data.

## 6. Compact dictionary encoding

Save-local dictionaries may encode frequently repeated 16-bit master IDs with smaller
indices.

Rules:

1. dictionary entries always resolve to canonical u16 IDs;
2. local indices never become global IDs;
3. loading resolves all identities before gameplay logic uses them;
4. overflow upgrades the block encoding rather than renumbering canonical IDs;
5. the serializer chooses encoding from measured physical storage capacity.

## 7. Physical storage backends

Save V2 is not synonymous with 32 KiB or 64 KiB SRAM.

Backends currently include:

- retail international MBC3 SRAM compatibility;
- retail Japanese MBC30 SRAM compatibility;
- future expanded storage backend selected after the content/asset census.

The full Generation 10 target must not pretend the international 32 KiB retail SRAM is
an unlimited modern save store.

## 8. RTC

RTC is a separate subsystem from content identity.

Legacy RTC/container bytes are preserved until decoded. A future backend may expose RTC
or an equivalent time service, but Species/Item/Move/Form IDs never depend on RTC
storage layout.

## 9. Required next evidence

Before exact offsets are committed:

1. raw bytes and hashes of all seven Crystal `.sav` files;
2. comparison of each save against its exact ROM/revision;
3. identification of nominal SRAM payload versus the 44 extra bytes;
4. primary/backup save blocks and checksums;
5. Japanese 64 KiB/mobile-era regions;
6. RTC serialization behavior of the producing emulator/tool.

Until those are measured, offsets remain deliberately unlocked.
