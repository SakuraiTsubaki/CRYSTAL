# Native Expansion Policy

## Preserve from Crystal

- Japanese original behavior as the origin baseline.
- Every verified international revision as a separate compatibility baseline.
- Region/story/event/NPC/version-specific behavior unless intentionally modernized.
- ROM and save evidence, checksums, RTC behavior, mapper behavior, and revision differences.

## Expand for Generation 10+

- Canonical Species, Move, Item, Ability, Type, Form, Variety, Evolution Method,
  Resource, and Feature identities use 16-bit append-only IDs.
- Original one-byte identity fields remain legacy serialization formats.
- New runtime structures must not silently truncate canonical IDs.
- Physical mapper/SRAM limits are backend constraints and are selected from measured capacity needs.
- Save V2 uses versioned blocks and explicit migration/import logic.

## Engine boundary

The implementation target is the original **Game Boy Color Crystal engine**.
GBA remake integration is explicitly out of scope here and is handled separately.

## Future-content rule

Only verified official data is added. Generation 10 capacity is reserved structurally;
unreleased species, moves, items, abilities, mechanics, names, or counts are not invented.
