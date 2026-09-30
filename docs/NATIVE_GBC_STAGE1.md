# Native GBC Stage 1 — Canonical Registry Seed

Status: **verified on all seven supplied Crystal ROMs**

Stage 0 created a common 4 MiB ROM / 64 KiB SRAM MBC30-compatible envelope.
Stage 1 uses the first new ROM bank, `$80`, to create a stable canonical data
boundary before runtime IDs themselves are widened.

## Registry bank

Physical ROM offset: `0x200000`

CPU bank/address layout:

| Registry | Count | Entry bytes | CPU address | Bytes |
| --- | ---: | ---: | ---: | ---: |
| Species BaseData | 251 | 32 | `$4100` | 8,032 |
| Moves | 251 | 7 | `$6060` | 1,757 |
| ItemAttributes | 256 | 7 | `$673D` | 1,792 |

Header and directory occupy the beginning of bank `$80`.
The complete Stage 1 seed uses 11,837 of 16,384 bytes, leaving 4,547 bytes.

The directory declares a 16-bit canonical ID width even though Stage 1 intentionally
keeps the retail u8 callers intact. This makes the new bank the stable registry
boundary for Stage 2.

## Table evidence

The seven verified ROMs place these tables at different physical offsets, but their
table payloads are byte-identical.

- BaseData SHA-256:
  `b5756adff731ac1a200056cf0b067eb7784319c4d74bdea022c7e66b519974f7`
- Moves SHA-256:
  `e84da1c005921f4352d9bbd83bd5a5885a12b0bbdcfd9ddc14c8ceb50c42670e`
- ItemAttributes SHA-256:
  `98c293815c3353a166a8a31cdbced6523dae70e3451de6e7839b6543d382301b`

The old tables are not deleted. They remain compatibility/evidence material inside
the original 2 MiB domain.

## Redirect coverage

`tools/seed_native_registries.py` scans the binary for proven table references and
patches both address and bank operands.

Every release has:

- 5 BaseData pointer reads and 5 matching bank loads;
- 2 ItemAttributes pointer reads and 2 matching bank loads.

Moves have language/revision-specific address collisions, so the scanner is
instruction-aware rather than treating every matching 16-bit constant as a pointer.

- Japanese: 25 proven move pointers / 18 bank loads; two non-table address collisions excluded.
- EN Rev0, EN RevA, FR, IT, ES: 23 / 16.
- DE: 23 / 16; one non-table collision excluded.

The exact hook counts and collision offsets are part of the machine-readable
`config/native_gbc_stage1.json` contract. If a future source or ROM differs, the
transform fails rather than patching an ambiguous address.

## Integrity

After redirecting table reads, the tool regenerates Crystal's Stadium metadata for
the original 2 MiB domain and recalculates the Game Boy global checksum.

The output SHA-1/SHA-256 for all seven releases is fixed in the Stage 1 config and
was produced from the raw supplied ROMs. ROM binaries themselves are not committed.

## Stage 2 boundary

Stage 1 deliberately does **not** pretend the runtime is already 16-bit.

Retail state still contains byte-sized Species, Item and Move IDs. Stage 2 widens the
runtime boundary while keeping all legacy low bytes compatible:

```text
legacy low byte
      +
canonical high byte
      |
      v
canonical u16 ID -> CRYSREG
```

The high-byte runtime/save state must be backed by measured WRAM/SRAM capacity and
must not overwrite existing Crystal structures.
