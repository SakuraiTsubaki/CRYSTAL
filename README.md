# CRYSTAL

Future-ready modernization workspace for Pokémon Crystal.

## Current phase

**Phase 0 — Generation 10-ready expansion architecture**

CRYSTAL expands the engine contracts **before** importing or rebuilding game content.
The goal is to avoid repeated rewrites as later-generation Pokémon, forms, moves,
items, abilities, mechanics, resources, and save metadata are added.

This repository does **not** invent unreleased Generation 10 species, moves, items,
forms, mechanics, counts, or names. It prepares stable capacity and compatibility rules
so verified official data can be appended later.

## Origin baseline

The Japanese Crystal release is the origin/reference baseline.

Localized releases and revisions remain separate compatibility profiles rather than
being treated as interchangeable ROM/save layouts.

Current verified ROM-header distinction that affects the save plan:

- Japanese Crystal: 64 KiB SRAM profile.
- Current international Crystal set: 32 KiB SRAM profile.
- MBC3 RTC handling is a separate subsystem from content identity and Save V2 IDs.

Exact save offsets, mirrored blocks, checksums, and revision-specific layouts are not
guessed; they are measured when each legacy baseline is imported.

## Architecture baseline

- 16-bit master IDs for Species, Variety, Form, Move, Item, Ability, Type, evolution
  methods, resources, and feature/mechanic registries.
- Append-only IDs: later generations never renumber older canonical identities.
- Species, battle-relevant Variety, and appearance/state Form are separate layers.
- Runtime master IDs are independent from compact ROM/save encoding.
- `CRYSTAL_SAVE_V2` uses versioned extension blocks and explicit legacy import profiles.
- Japanese 64 KiB and international 32 KiB legacy SRAM profiles are tracked separately.
- Resource lookup is mapper-agnostic: gameplay refers to Resource IDs instead of
  hard-coded ROM banks.
- Unknown future mechanics are attached through feature/registry descriptors rather
  than guessed Generation 10 constants.

See [Generation 10 Expansion Architecture](docs/GEN10_EXPANSION_ARCHITECTURE.md).

## Phase 0 implementation files

- `config/engine_capacity.json` — machine-readable 10+ generation capacity contract.
- `engine/include/extended_ids.inc` — RGBDS 16-bit master-ID constants/macros.
- `engine/include/resource_directory.inc` — mapper-independent resource-entry ABI.
- `docs/GEN10_EXPANSION_ARCHITECTURE.md` — architecture and migration rules.
- `docs/SAVE_FORMAT_V2.md` — extended versioned-save contract.
- `tools/validate_capacity.py` — guardrail validator.
- `.github/workflows/capacity-contract.yml` — CI validation for the contract.

## Next phase

After the expansion contract is stable:

1. verify/import the Japanese Crystal baseline;
2. register EN Rev 0 / Rev A and FR / DE / IT / ES compatibility profiles;
3. establish canonical Species/Move/Item/Variety/Form manifests;
4. convert legacy byte-sized accessors to 16-bit-safe APIs;
5. implement Save V2 plus legacy/RTC import paths;
6. route graphics, text, audio, and data through Resource IDs;
7. append verified later-generation datasets through Generation 10 and beyond.

Original ROM binaries are never committed.
