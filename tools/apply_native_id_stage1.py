#!/usr/bin/env python3
"""Apply CRYSTAL native GBC Stage 1 identity sidecar/ABI patch after Stage 0."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message: str) -> None:
    raise SystemExit(f"native ID Stage 1 patch failed: {message}")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        fail(f"{path}: expected exactly one target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def check_source(root: Path) -> None:
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != PINNED:
        fail(f"source HEAD {head} != pinned {PINNED}")
    constants = (root / "constants/ram_constants.asm").read_text(encoding="utf-8")
    if "DEF NUM_SRAM_BANKS EQU 8" not in constants:
        fail("Stage 0 must be applied before Stage 1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    root = args.source.resolve()
    check_source(root)

    replace_once(
        root / "constants/pokemon_data_constants.asm",
        "DEF NUM_BOXES EQU 14\n",
        """DEF NUM_BOXES EQU 14

; CRYSTAL Generation 10+ native identity sidecar.
; Capacity intentionally combines the largest source-side box count and
; per-box count so one ABI can cover both legacy layout families without
; asserting that either retail release uses the combined maximum.
DEF CRYSTAL_EXT_MAX_BOXES        EQU NUM_BOXES
DEF CRYSTAL_EXT_MAX_MONS_PER_BOX EQU MONS_PER_BOX_JP
DEF CRYSTAL_EXT_MON_SLOTS        EQU CRYSTAL_EXT_MAX_BOXES * CRYSTAL_EXT_MAX_MONS_PER_BOX + PARTY_LENGTH

DEF CRYSTAL_EXT_SCHEMA_VERSION  EQU 1
DEF CRYSTAL_EXT_HEADER_SIZE      EQU 32
DEF CRYSTAL_EXT_MON_ENTRY_SIZE   EQU 9
DEF CRYSTAL_EXT_SPECIES_HI       EQU 0
DEF CRYSTAL_EXT_ITEM_HI          EQU 1
DEF CRYSTAL_EXT_MOVE1_HI         EQU 2
DEF CRYSTAL_EXT_MOVE2_HI         EQU 3
DEF CRYSTAL_EXT_MOVE3_HI         EQU 4
DEF CRYSTAL_EXT_MOVE4_HI         EQU 5
DEF CRYSTAL_EXT_VARIANT_PROFILE  EQU 6 ; little-endian u16
DEF CRYSTAL_EXT_ABILITY_STATE    EQU 8
""",
    )

    replace_once(
        root / "ram/sram.asm",
        """sMobileAdapterStatus:: db


SECTION "SRAM Mobile 2", SRAM
""",
        """sMobileAdapterStatus:: db


SECTION "CRYSTAL Extended Save Core", SRAM

sCrystalExtSaveCore::
sCrystalExtMagic::         ds 4 ; "CX10" once initialized
sCrystalExtSchemaVersion:: db
sCrystalExtEntrySize::     db
sCrystalExtSlotCount::     dw
sCrystalExtFlags::         dw
sCrystalExtChecksum::      dw
sCrystalExtReserved::      ds CRYSTAL_EXT_HEADER_SIZE - 12
sCrystalExtMonEntries::    ds CRYSTAL_EXT_MON_SLOTS * CRYSTAL_EXT_MON_ENTRY_SIZE
sCrystalExtSaveCoreEnd::

assert sCrystalExtMonEntries - sCrystalExtSaveCore == CRYSTAL_EXT_HEADER_SIZE
assert sCrystalExtSaveCoreEnd - sCrystalExtSaveCore == $f1a
assert sCrystalExtSaveCoreEnd - sCrystalExtSaveCore <= $fff


SECTION "SRAM Mobile 2", SRAM
""",
    )

    replace_once(
        root / "layout.link",
        """SRAM $04
\t"SRAM Mobile 1"
SRAM $05
""",
        """SRAM $04
\t"SRAM Mobile 1"
\torg $b001
\t"CRYSTAL Extended Save Core"
SRAM $05
""",
    )

    replace_once(
        root / "layout.link",
        """ROMX $7f
\torg $7de0
\t"Stadium 2 Checksums"
ROMX $ff
""",
        """ROMX $7f
\torg $7de0
\t"Stadium 2 Checksums"
ROMX $80
\torg $4000
\t"CRYSTAL Extended ID ABI"
ROMX $ff
""",
    )

    replace_once(
        root / "main.asm",
        """SECTION "CRYSTAL Expansion End", ROMX[$7fff], BANK[$ff]
\tdb $ff
""",
        """SECTION "CRYSTAL Extended ID ABI", ROMX[$4000], BANK[$80]

INCLUDE "engine/pokemon/extended_ids.asm"


SECTION "CRYSTAL Expansion End", ROMX[$7fff], BANK[$ff]
\tdb $ff
""",
    )

    replace_once(
        root / "engine/menus/intro_menu.asm",
        """NewGame:
\txor a
\tld [wDebugFlags], a
\tcall ResetWRAM
\tcall NewGame_ClearTilemapEtc
""",
        """NewGame:
\txor a
\tld [wDebugFlags], a
\tcall ResetWRAM
\tfarcall CrystalInitExtendedSaveCore
\tcall NewGame_ClearTilemapEtc
""",
    )

    replace_once(
        root / "engine/menus/intro_menu.asm",
        """Continue:
\tfarcall TryLoadSaveFile
\tjr c, .FailToLoad
\tfarcall _LoadData
\tcall LoadStandardMenuHeader
""",
        """Continue:
\tfarcall TryLoadSaveFile
\tjr c, .FailToLoad
\tfarcall _LoadData
\tfarcall CrystalEnsureExtendedSaveCore
\tcall LoadStandardMenuHeader
""",
    )

    abi = root / "engine/pokemon/extended_ids.asm"
    abi.write_text(
        """; CRYSTAL Generation 10+ native canonical-ID ABI.
; These routines intentionally operate on a legacy BoxMon/PartyMon pointer in HL
; and its matching sidecar entry in DE. They do not choose a persistent slot;
; box/party/link consumers are migrated to this ABI in later Stage 1 slices.

CrystalGetSpeciesID::
\tld a, [de]
\tld b, a
\tld a, [hl]
\tld c, a
\tret

CrystalSetSpeciesID::
\tld [hl], c
\tld a, b
\tld [de], a
\tret

CrystalGetHeldItemID::
\tinc hl
\tinc de
\tld a, [de]
\tld b, a
\tld a, [hl]
\tld c, a
\tret

CrystalSetHeldItemID::
\tinc hl
\tinc de
\tld [hl], c
\tld a, b
\tld [de], a
\tret

CrystalGetMoveID::
; a = move slot 0..3
; hl = legacy mon, de = extension entry
; returns bc = canonical move ID
\tand NUM_MOVES - 1
\tinc hl
\tinc hl
\tinc de
\tinc de
.loop
\tand a
\tjr z, .read
\tinc hl
\tinc de
\tdec a
\tjr .loop
.read
\tld a, [de]
\tld b, a
\tld a, [hl]
\tld c, a
\tret

CrystalSetMoveID::
; a = move slot 0..3, bc = canonical move ID
; hl = legacy mon, de = extension entry
\tand NUM_MOVES - 1
\tinc hl
\tinc hl
\tinc de
\tinc de
.loop
\tand a
\tjr z, .write
\tinc hl
\tinc de
\tdec a
\tjr .loop
.write
\tld [hl], c
\tld a, b
\tld [de], a
\tret

CrystalGetVariantProfileID::
; de = extension entry; returns bc = little-endian u16 profile ID
\tld hl, CRYSTAL_EXT_VARIANT_PROFILE
\tadd hl, de
\tld a, [hli]
\tld c, a
\tld a, [hl]
\tld b, a
\tret

CrystalSetVariantProfileID::
; de = extension entry, bc = little-endian u16 profile ID
\tld hl, CRYSTAL_EXT_VARIANT_PROFILE
\tadd hl, de
\tld [hl], c
\tinc hl
\tld [hl], b
\tret

CrystalGetAbilityState::
; de = extension entry; returns a
\tld hl, CRYSTAL_EXT_ABILITY_STATE
\tadd hl, de
\tld a, [hl]
\tret

CrystalSetAbilityState::
; de = extension entry, a = state
\tld hl, CRYSTAL_EXT_ABILITY_STATE
\tadd hl, de
\tld [hl], a
\tret

CrystalInitExtendedSaveCore::
; Initialize only the reserved CRYSTAL sidecar region. Existing Crystal/Mobile
; SRAM outside B001..BF1A is not touched.
\tld a, BANK(sCrystalExtSaveCore)
\tcall OpenSRAM
\tld hl, sCrystalExtSaveCore
\tld bc, sCrystalExtSaveCoreEnd - sCrystalExtSaveCore
\txor a
\tcall ByteFill
\tld hl, sCrystalExtMagic
\tld a, $43
\tld [hli], a
\tld a, $58
\tld [hli], a
\tld a, $31
\tld [hli], a
\tld a, $30
\tld [hli], a
\tld a, CRYSTAL_EXT_SCHEMA_VERSION
\tld [sCrystalExtSchemaVersion], a
\tld a, CRYSTAL_EXT_MON_ENTRY_SIZE
\tld [sCrystalExtEntrySize], a
\tld a, LOW(CRYSTAL_EXT_MON_SLOTS)
\tld [sCrystalExtSlotCount], a
\tld a, HIGH(CRYSTAL_EXT_MON_SLOTS)
\tld [sCrystalExtSlotCount + 1], a
\tcall CloseSRAM
\tret

CrystalValidateExtendedSaveCore::
; carry set = compatible sidecar header present
\tld a, BANK(sCrystalExtSaveCore)
\tcall OpenSRAM
\tld hl, sCrystalExtMagic
\tld a, [hli]
\tcp $43
\tjr nz, .bad
\tld a, [hli]
\tcp $58
\tjr nz, .bad
\tld a, [hli]
\tcp $31
\tjr nz, .bad
\tld a, [hli]
\tcp $30
\tjr nz, .bad
\tld a, [sCrystalExtSchemaVersion]
\tcp CRYSTAL_EXT_SCHEMA_VERSION
\tjr nz, .bad
\tld a, [sCrystalExtEntrySize]
\tcp CRYSTAL_EXT_MON_ENTRY_SIZE
\tjr nz, .bad
\tld a, [sCrystalExtSlotCount]
\tcp LOW(CRYSTAL_EXT_MON_SLOTS)
\tjr nz, .bad
\tld a, [sCrystalExtSlotCount + 1]
\tcp HIGH(CRYSTAL_EXT_MON_SLOTS)
\tjr nz, .bad
\tcall CloseSRAM
\tscf
\tret

.bad
\tcall CloseSRAM
\tand a
\tret

CrystalEnsureExtendedSaveCore::
; Retail/legacy saves have no CX10 header. Initializing an all-zero sidecar
; makes every canonical ID equal its existing legacy low byte.
\tcall CrystalValidateExtendedSaveCore
\tret c
\tjp CrystalInitExtendedSaveCore
""",
        encoding="utf-8",
    )

    # Stage 0 filled the entire expansion half because it contained no code.
    # Stage 1 now owns bank $80, so keep linker-emitted bytes intact.
    replace_once(
        root / "Makefile",
        "\tpython3 tools/crystal_expand_padding.py $@\n",
        "\tpython3 tools/crystal_stage1_image_check.py $@\n",
    )
    image_check = root / "tools/crystal_stage1_image_check.py"
    image_check.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: crystal_stage1_image_check.py ROM")
path = Path(sys.argv[1])
size = path.stat().st_size
if size != 0x400000:
    raise SystemExit(f"expected 4 MiB linked image, got {size:#x}")
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("CRYSTAL native ID Stage 1 patch: applied cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
