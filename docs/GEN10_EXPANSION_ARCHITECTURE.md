# Generation 10-ready expansion architecture

Status: **ACTIVE — Phase 0**

This document defines CRYSTAL's expansion contract before source/content import.

## 1. Goal

Generation 10 readiness means **capacity and architecture readiness**, not guessing
unreleased content.

CRYSTAL must accept verified future records without renumbering older data or replacing
the save/resource architecture again.

The Japanese Crystal release is the origin baseline. Localized releases and revisions
are imported as separately verified compatibility profiles.

## 2. Master ID rule

Every registry that can grow across generations uses a 16-bit master ID.

| Registry | Runtime width | Reserved zero |
| --- | ---: | --- |
| Species | 16-bit | NONE |
| Variety / battle profile | 16-bit | NONE |
| Form / appearance | 16-bit | NONE |
| Move | 16-bit | NONE |
| Item | 16-bit | NONE |
| Ability | 16-bit | NONE |
| Type | 16-bit | NONE |
| Evolution method | 16-bit | NONE |
| Resource | 16-bit | NONE |
| Feature / mechanic | 16-bit | NONE |

Valid normal ID space is `1..65535`.

The width is an engine contract, not a promise that every ID will be populated.

## 3. Append-only namespace

Registries are append-only.

- Existing IDs never move when later-generation data is imported.
- Deletions become tombstones/aliases when compatibility requires them.
- Generation boundaries are metadata, not numeric hard partitions.
- No guessed "Generation 10 starts at X" constant is created before verified data exists.
- Official National Pokédex numbers are preserved for Species whenever applicable.
- EGG and other legacy sentinels are state, not Species IDs.

## 4. Species, variety, and form are separate

CRYSTAL uses three layers:

```text
Species
  -> Variety / battle profile
       -> Form / appearance
```

**Species** is the stable creature identity.

**Variety** carries battle-relevant variation such as base stats, types, abilities,
regional profiles, or other persistent battle data.

**Form** describes selectable or derived appearance/state records and may reference a
variety, graphics, palette, cry/resource overrides, and transition rules.

This prevents later form mechanics from consuming or renumbering Species IDs.

## 5. Moves, items, abilities, and types

Crystal's original byte-sized namespaces are legacy encodings, not the new master
representation.

All APIs that cross subsystem boundaries exchange 16-bit master IDs. A subsystem may
use a compact local dictionary internally, but must decode to the canonical master ID
before gameplay logic consumes it.

This avoids widening Species now only to require another save/runtime rewrite when
Move, Item, Ability, Type, or future mechanics exceed legacy limits.

## 6. Save architecture

Runtime width and serialized storage width are separate concerns.

CRYSTAL Save V2 uses:

- a versioned header;
- feature flags;
- extension blocks;
- per-block lengths and checksums;
- compact dictionaries/side tables where useful;
- explicit importers for each verified legacy save profile;
- canonical in-memory records exposing 16-bit master IDs.

Crystal requires more than one legacy profile. The Japanese ROM header declares 64 KiB
SRAM while the currently verified international ROM headers declare 32 KiB. Physical
offsets and block maps are therefore measured per release/revision before import/export
code is finalized.

RTC handling is a separate subsystem and may use a versioned extension/transport block;
RTC state must never be overloaded into identity fields.

See `SAVE_FORMAT_V2.md`.

## 7. Resource and ROM-bank abstraction

Gameplay logic must not hard-code the physical ROM bank of content.

Use:

```text
ResourceId (u16)
  -> ResourceDirectory
       -> mapper-specific bank/address
```

The directory uses a 16-bit bank field even when the initial Game Boy Color mapper
backend needs fewer bits. Mapper/ROM expansion can then replace the backend without
rewriting every content consumer.

## 8. Feature registry for future mechanics

Unknown future mechanics are represented through a feature registry and data-driven
descriptors.

Potential consumers include:

- battle transformations;
- form transitions;
- field actions;
- encounter rules;
- evolution methods;
- held-item effects;
- move behavior flags;
- save extension blocks.

Do not reserve guessed Generation 10 mechanic names, counts, or IDs.

## 9. Compatibility layers

CRYSTAL distinguishes:

1. **Legacy source format** — original Crystal structures and byte-sized fields.
2. **Canonical runtime format** — 16-bit IDs and extensible records.
3. **Serialized Save V2 format** — compact, versioned representation.

Importers perform legacy -> canonical conversion.
Serializers perform canonical <-> Save V2 conversion.

Gameplay code must not depend on the original byte layout.

## 10. Phase order

Phase 0 is complete when the capacity contract, ID include, save contract, validator,
and mapper-independent resource contract exist.

Next:

1. verify/import the Japanese Crystal baseline;
2. verify localized/revision compatibility profiles;
3. establish canonical registry manifests;
4. convert Species/Move/Item accessors to 16-bit-safe APIs;
5. introduce generic Variety/Form access;
6. implement Save V2 and legacy/RTC import paths;
7. route graphics/text/audio through the resource directory;
8. append verified later-generation datasets through Generation 10 and beyond.

The key rule is: **expand the architecture first; populate it second.**
