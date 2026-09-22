# CRYSTAL Project

## Canonical direction

ポケットモンスター クリスタル의 **원본 Game Boy Color 엔진을 직접 확장**하여
Generation 10 이후까지 수용할 수 있는 구조를 만든다.

GBA 리메이크는 별도 작업이며 이 저장소의 native runtime 기준이 아니다.

## Source baselines

- Japanese `BXTJ` Rev 0 is the origin/master reference.
- English `BYTE` Rev 0 and Rev A are separate revision baselines.
- French `BYTF`, German `BYTD`, Italian `BYTI`, Spanish `BYTS` are independent localized baselines.
- ROM and save evidence must remain revision-specific.

## Runtime baseline

- Host: Game Boy Color
- CPU: Sharp SM83
- Native engine family: Pokémon Crystal / Generation II
- Retail compatibility backends:
  - Japan: MBC30-compatible / 64 KiB SRAM / RTC
  - International: MBC3 / 32 KiB SRAM / RTC
- Expanded mapper/storage backend: selected only after complete code/data/graphics/audio/text capacity census.

## Generation 10-ready rules

- Cross-subsystem IDs use append-only 16-bit canonical identities.
- Legacy 8-bit ROM/save fields are import/export encodings, not the new runtime identity contract.
- Mapper-independent resource lookup separates logical content IDs from physical bank placement.
- Save V2 is versioned and keeps Japanese/international legacy import paths separate.
- Existing ROM behavior remains evidence for compatibility; unverified future content is never guessed.

## Separation from GBA work

Johto GBA remake work, pokeemerald-expansion integration, Hoenn/FRLG donor assets,
and GBA save geometry belong to the separate GBA remake workstream and are not part of
this repository's native GBC expansion implementation.
