# Generation 10-ready expansion architecture

Status: **ACTIVE — evidence-driven Phase 0**

CRYSTAL does not expand from a generic Pokémon-engine template. The capacity contract is
derived from the verified Crystal ROM set and the observed Crystal save set first.

See `docs/EVIDENCE_DRIVEN_EXPANSION.md` and `research/evidence/`.

## 1. Verified starting point

Seven retail ROMs were read byte-for-byte:

- Japanese `BXTJ` Rev 0
- English `BYTE` Rev 0
- English `BYTE` Rev A
- French `BYTF`
- German `BYTD`
- Italian `BYTI`
- Spanish `BYTS`

All seven are 2 MiB, cartridge type `0x10`, CGB-only, and pass both header and global
checksum validation.

The Japanese ROM declares 64 KiB SRAM (`0x05`) while all verified international ROMs
declare 32 KiB (`0x03`). This is a structural compatibility boundary, not a cosmetic
region difference.

## 2. Physical mapper evidence

The international retail profile is MBC3:

- 2 MiB documented ROM ceiling;
- 32 KiB SRAM;
- RTC.

Japanese Crystal uses the MBC30-compatible profile identified by its 64 KiB SRAM
configuration:

- current verified ROM is still 2 MiB;
- MBC30 can address up to 4 MiB ROM;
- 64 KiB SRAM;
- RTC.

Therefore the full later-generation engine cannot encode physical MBC3 bank numbers as
content identity. A logical resource/bank layer is mandatory.

## 3. ROM-space evidence

Zero-filled ROM banks are not treated as automatically free.

Observed complete zero-filled 16 KiB banks:

- Japan: `0x60..0x7C` (29 banks).
- English Rev 0 / Rev A: `0x75 0x76 0x79 0x7A`.
- French/German/Italian/Spanish: only `0x7A`.

The region builds therefore do not share one safe fixed set of spare banks. Expansion
must be relocatable and mapper-backed, not hard-coded into "unused banks".

## 4. Master ID rule

Every registry that can grow across generations uses a 16-bit canonical master ID.

| Registry | Runtime width |
| --- | ---: |
| Species | 16-bit |
| Variety / battle profile | 16-bit |
| Form / appearance | 16-bit |
| Move | 16-bit |
| Item | 16-bit |
| Ability | 16-bit |
| Type | 16-bit |
| Evolution method | 16-bit |
| Resource | 16-bit |
| Feature / mechanic | 16-bit |

Normal IDs are `1..65535`; `0` is NONE.

This is a runtime identity contract. Serialized save or ROM tables may use a smaller
local dictionary when that encoding is lossless.

## 5. Why the original Pokémon record cannot simply be widened in place

The original Crystal BoxMon is 32 bytes.

Relevant legacy fields:

- Species: 1 byte.
- Item: 1 byte.
- Moves: four 1-byte IDs.
- International PC storage: 14 × 20 = 280 boxed Pokémon.
- The source separately defines `MONS_PER_BOX_JP = 30`.

Widening only Species + Item + four Move IDs from 8 to 16 bits adds six bytes to every
BoxMon. Across the 280 international box slots alone this costs 1,680 bytes before
adding Form, Variety, Ability, modern origin metadata, ribbons/marks, additional boxes,
or future mechanics.

Therefore legacy BoxMon is an import/export format, not the new canonical record.

## 6. Species, Variety, and Form are separate

```text
Species
  -> Variety / battle profile
       -> Form / appearance/state
```

Species remains the stable creature identity. Battle-relevant variants and appearance
or transformation state do not consume Species IDs.

## 7. Save evidence and Save V2

Observed save-file lengths from the seven uploaded Crystal saves were:

- Japanese: `0x1002C` = 65,580 bytes.
- International: `0x802C` = 32,812 bytes.

Each is exactly the ROM-header SRAM capacity plus `0x2C` (44) bytes.

The current runtime does not expose those raw save bytes, so the placement and meaning
of the 44 bytes remain opaque. Save V2 must preserve unknown container data and must not
lock offsets or RTC-container semantics from size alone.

Canonical runtime IDs are 16-bit. Save V2 may use save-local dictionaries and versioned
extension blocks. Legacy Japanese and international saves have separate importers.

## 8. Resource and mapper architecture

```text
ResourceId (u16)
  -> ResourceDirectory
       -> logical bank/address
            -> mapper backend
```

The resource directory uses a 16-bit logical bank ID. Retail MBC3 and MBC30 are backend
profiles, not engine-wide identity limits.

The final expanded physical mapper/storage backend is selected only after the complete
data + graphics + audio + text census establishes the required capacity.

## 9. Revision handling

English Rev 0 and Rev A differ by 584 bytes across 79 ranges in eight banks. Bank
`0x5C` contains 546 changed bytes.

A revision is therefore an explicit compatibility baseline. Save and ROM evidence are
never merged solely because titles/languages match.

## 10. Phase order

1. preserve the seven verified ROM baselines and their hashes;
2. re-read/hash all seven raw save files and map their layouts separately;
3. import a source baseline while retaining ROM-byte verification;
4. replace byte-sized cross-subsystem Species/Move/Item APIs with canonical ID accessors;
5. introduce Variety/Form/Ability-aware canonical Pokémon records;
6. implement legacy save importers and Save V2 serializer;
7. implement mapper-independent resource placement;
8. census later-generation data/assets and select the expanded physical mapper backend;
9. append verified generations through Generation 10 without renumbering prior IDs.

**Measure first, expand second, populate third.**
