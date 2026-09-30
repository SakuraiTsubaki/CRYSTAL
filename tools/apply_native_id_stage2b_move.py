#!/usr/bin/env python3
"""Apply CRYSTAL native GBC Stage 2b sidecar bridge for MOVE PKMN W/O MAIL."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED="e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message:str)->None:
    raise SystemExit(f"native ID Stage 2b patch failed: {message}")


def replace_once(path:Path,old:str,new:str)->None:
    text=path.read_text(encoding="utf-8")
    count=text.count(old)
    if count!=1:
        fail(f"{path}: expected exactly one target, found {count}")
    path.write_text(text.replace(old,new,1),encoding="utf-8")


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    args=ap.parse_args()
    root=args.source.resolve()

    head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if head!=PINNED:
        fail(f"source HEAD {head} != pinned {PINNED}")

    abi=root/"engine/pokemon/extended_ids.asm"
    if not abi.exists() or "CrystalGetBoxSidecarEntry::" not in abi.read_text(encoding="utf-8"):
        fail("Stage 2 box bridge missing")
    if "CrystalCopyPartySidecarToTemp::" in abi.read_text(encoding="utf-8"):
        fail("Stage 2b already applied")

    wram=root/"ram/wram.asm"
    replace_once(
        wram,
        """wBillsPCData::
wBillsPCPokemonList:: ds BOXLIST_SIZE * MONS_PER_BOX_JP
	ds 720
""",
        """wBillsPCData::
wBillsPCPokemonList:: ds BOXLIST_SIZE * MONS_PER_BOX_JP
; CRYSTAL native 16-bit ID bridge reuses the existing Bills PC scratch reservation.
wCrystalExtTempMonEntry:: ds CRYSTAL_EXT_MON_ENTRY_SIZE
wCrystalExtTempMonEntryEnd::
	ds 720 - CRYSTAL_EXT_MON_ENTRY_SIZE
""",
    )

    abi_text=abi.read_text(encoding="utf-8")
    abi_text += r"""

; ---------------------------------------------------------------------------
; Stage 2b: MOVE PKMN W/O MAIL temporary sidecar transport.
; ---------------------------------------------------------------------------

CrystalCopyPartySidecarToTemp::
	ld a, [wCurPartyMon]
	call CrystalGetPartySidecarEntry
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld h, d
	ld l, e
	ld de, wCrystalExtTempMonEntry
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	jp CloseSRAM

CrystalCopyCurrentBoxSidecarToTemp::
	ld a, [wCurPartyMon]
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	call CrystalGetBoxSidecarEntry
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld h, d
	ld l, e
	ld de, wCrystalExtTempMonEntry
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	jp CloseSRAM

CrystalInsertTempSidecarIntoParty::
; Legacy InsertPokemonIntoParty has already increased wPartyCount and shifted
; entries right at wCurPartyMon. Mirror that insertion in the sidecar.
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld a, [wPartyCount]
	cp 2
	jr c, .copy_temp
	sub 2 ; last source entry before insertion
	ld c, a
	ld a, [wCurPartyMon]
	cp c
	jr c, .begin_shift
	jr z, .begin_shift
	jr .copy_temp

.begin_shift
	ld a, c
.shift
; A = source entry index. Copy source -> source+1, highest to lowest.
	push af
	call CrystalGetPartySidecarEntry
	pop af
	push de
	push af
	inc a
	call CrystalGetPartySidecarEntry
	pop af
	pop hl
	push af
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	pop af
	ld c, a
	ld a, [wCurPartyMon]
	cp c
	jr z, .copy_temp
	ld a, c
	dec a
	jr .shift

.copy_temp
	ld a, [wCurPartyMon]
	call CrystalGetPartySidecarEntry
	ld hl, wCrystalExtTempMonEntry
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	jp CloseSRAM

CrystalInsertTempSidecarIntoCurrentBox::
; Legacy InsertPokemonIntoBox has already increased sBoxCount and shifted
; entries right at wCurPartyMon.
	ld a, BANK(sBoxCount)
	call OpenSRAM
	ld a, [sBoxCount]
	push af
	call CloseSRAM

	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	pop af
	cp 2
	jr c, .copy_temp
	sub 2 ; last source entry before insertion
	ld c, a
	ld a, [wCurPartyMon]
	cp c
	jr c, .begin_shift
	jr z, .begin_shift
	jr .copy_temp

.begin_shift
	ld a, c
.shift
; A = source box entry index.
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	push af
	call CrystalGetBoxSidecarEntry
	pop af
	push de
	push af
	inc a
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	call CrystalGetBoxSidecarEntry
	pop af
	pop hl
	push af
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	pop af
	ld c, a
	ld a, [wCurPartyMon]
	cp c
	jr z, .copy_temp
	ld a, c
	dec a
	jr .shift

.copy_temp
	ld a, [wCurPartyMon]
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	call CrystalGetBoxSidecarEntry
	ld hl, wCrystalExtTempMonEntry
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	jp CloseSRAM
"""
    abi.write_text(abi_text,encoding="utf-8")

    bills=root/"engine/pokemon/bills_pc.asm"

    replace_once(
        bills,
        """.CopyFromBox:
	ld a, [wBillsPC_BackupLoadedBox]
	dec a
	ld e, a
	farcall MoveMonWOMail_SaveGame
	ld a, [wBillsPC_BackupCursorPosition]
	ld hl, wBillsPC_BackupScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	ld a, BANK(sBox)
""",
        """.CopyFromBox:
	ld a, [wBillsPC_BackupLoadedBox]
	dec a
	ld e, a
	farcall MoveMonWOMail_SaveGame
	ld a, [wBillsPC_BackupCursorPosition]
	ld hl, wBillsPC_BackupScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall CrystalCopyCurrentBoxSidecarToTemp
	ld a, BANK(sBox)
""",
    )

    replace_once(
        bills,
        """.CopyFromParty:
	ld a, [wBillsPC_BackupCursorPosition]
	ld hl, wBillsPC_BackupScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	ld hl, wPartySpecies
""",
        """.CopyFromParty:
	ld a, [wBillsPC_BackupCursorPosition]
	ld hl, wBillsPC_BackupScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall CrystalCopyPartySidecarToTemp
	ld hl, wPartySpecies
""",
    )

    replace_once(
        bills,
        """.CopyToBox:
	ld a, [wBillsPC_LoadedBox]
	dec a
	ld e, a
	farcall MoveMonWOMail_SaveGame
	ld a, [wBillsPC_CursorPosition]
	ld hl, wBillsPC_ScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall InsertPokemonIntoBox
	ret
""",
        """.CopyToBox:
	ld a, [wBillsPC_LoadedBox]
	dec a
	ld e, a
	farcall MoveMonWOMail_SaveGame
	ld a, [wBillsPC_CursorPosition]
	ld hl, wBillsPC_ScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall InsertPokemonIntoBox
	farcall CrystalInsertTempSidecarIntoCurrentBox
	ret
""",
    )

    replace_once(
        bills,
        """.CopyToParty:
	ld a, [wBillsPC_CursorPosition]
	ld hl, wBillsPC_ScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall InsertPokemonIntoParty
	ret
""",
        """.CopyToParty:
	ld a, [wBillsPC_CursorPosition]
	ld hl, wBillsPC_ScrollPosition
	add [hl]
	ld [wCurPartyMon], a
	farcall InsertPokemonIntoParty
	farcall CrystalInsertTempSidecarIntoParty
	ret
""",
    )

    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("CRYSTAL native ID Stage 2b MOVE PKMN W/O MAIL patch: applied cleanly")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
