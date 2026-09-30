#!/usr/bin/env python3
"""Apply native GBC Stage 2d persistent Day-Care identity sidecars."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED="e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message:str)->None:
    raise SystemExit(f"native ID Stage 2d patch failed: {message}")


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
    abi_text=abi.read_text(encoding="utf-8")
    if "CrystalInsertLegacyZeroSidecarAtBoxFront::" not in abi_text:
        fail("Stage 2c missing")
    if "CrystalGetDayCareSidecarEntry::" in abi_text:
        fail("Stage 2d already applied")

    constants=root/"constants/pokemon_data_constants.asm"
    replace_once(
        constants,
        """DEF CRYSTAL_EXT_ABILITY_STATE    EQU 8
""",
        """DEF CRYSTAL_EXT_ABILITY_STATE    EQU 8

DEF CRYSTAL_EXT_DAYCARE_SLOTS      EQU 2
DEF CRYSTAL_EXT_DAYCARE_FLAG_F     EQU 0
DEF CRYSTAL_EXT_DAYCARE_FLAG       EQU 1 << CRYSTAL_EXT_DAYCARE_FLAG_F
""",
    )

    sram=root/"ram/sram.asm"
    replace_once(
        sram,
        """sCrystalExtMonEntries::    ds CRYSTAL_EXT_MON_SLOTS * CRYSTAL_EXT_MON_ENTRY_SIZE
sCrystalExtSaveCoreEnd::

assert sCrystalExtMonEntries - sCrystalExtSaveCore == CRYSTAL_EXT_HEADER_SIZE
""",
        """sCrystalExtMonEntries::    ds CRYSTAL_EXT_MON_SLOTS * CRYSTAL_EXT_MON_ENTRY_SIZE
sCrystalExtSaveCoreEnd::

; Kept outside the original 426-slot core so existing box/party slot numbers
; never move when this extension is introduced.
sCrystalExtDayCareEntries::
sCrystalExtDayCare1:: ds CRYSTAL_EXT_MON_ENTRY_SIZE
sCrystalExtDayCare2:: ds CRYSTAL_EXT_MON_ENTRY_SIZE
sCrystalExtDayCareEntriesEnd::

assert sCrystalExtMonEntries - sCrystalExtSaveCore == CRYSTAL_EXT_HEADER_SIZE
""",
    )
    replace_once(
        sram,
        """assert sCrystalExtSaveCoreEnd - sCrystalExtSaveCore <= $fff
""",
        """assert sCrystalExtSaveCoreEnd - sCrystalExtSaveCore <= $fff
assert sCrystalExtDayCareEntries == sCrystalExtSaveCoreEnd
assert sCrystalExtDayCareEntriesEnd - sCrystalExtDayCareEntries == CRYSTAL_EXT_DAYCARE_SLOTS * CRYSTAL_EXT_MON_ENTRY_SIZE
assert sCrystalExtDayCareEntriesEnd <= $c000
""",
    )

    abi_text=abi.read_text(encoding="utf-8")
    abi_text=abi_text.replace(
        """	ld bc, sCrystalExtSaveCoreEnd - sCrystalExtSaveCore
""",
        """	ld bc, sCrystalExtDayCareEntriesEnd - sCrystalExtSaveCore
""",
        1,
    )
    old_init="""	ld a, HIGH(CRYSTAL_EXT_MON_SLOTS)
	ld [sCrystalExtSlotCount + 1], a
	call CloseSRAM
	ret
"""
    new_init="""	ld a, HIGH(CRYSTAL_EXT_MON_SLOTS)
	ld [sCrystalExtSlotCount + 1], a
	ld a, CRYSTAL_EXT_DAYCARE_FLAG
	ld [sCrystalExtFlags], a
	call CloseSRAM
	ret
"""
    if abi_text.count(old_init)!=1:
        fail("Stage 1 initializer shape changed")
    abi_text=abi_text.replace(old_init,new_init,1)

    old_ensure="""CrystalEnsureExtendedSaveCore::
; Retail/legacy saves have no CX10 header. Initializing an all-zero sidecar
; makes every canonical ID equal its existing legacy low byte.
	call CrystalValidateExtendedSaveCore
	ret c
	jp CrystalInitExtendedSaveCore
"""
    new_ensure="""CrystalEnsureExtendedSaveCore::
; Retail/legacy saves have no CX10 header. Initializing an all-zero sidecar
; makes every canonical ID equal its existing legacy low byte.
	call CrystalValidateExtendedSaveCore
	jr nc, .init_core
	jp CrystalEnsureDayCareSidecars
.init_core
	jp CrystalInitExtendedSaveCore

CrystalEnsureDayCareSidecars::
; Upgrade an already-valid Stage 1 core without clearing box/party high IDs.
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld hl, sCrystalExtFlags
	bit CRYSTAL_EXT_DAYCARE_FLAG_F, [hl]
	jr nz, .done
	ld hl, sCrystalExtDayCareEntries
	ld bc, sCrystalExtDayCareEntriesEnd - sCrystalExtDayCareEntries
	xor a
	call ByteFill
	ld hl, sCrystalExtFlags
	set CRYSTAL_EXT_DAYCARE_FLAG_F, [hl]
.done
	jp CloseSRAM
"""
    if abi_text.count(old_ensure)!=1:
        fail("Stage 1 ensure routine shape changed")
    abi_text=abi_text.replace(old_ensure,new_ensure,1)

    abi_text += r"""

; ---------------------------------------------------------------------------
; Stage 2d: persistent Day-Care sidecars.
; ---------------------------------------------------------------------------

CrystalGetDayCareSidecarEntry::
; a = 0 (man) or 1 (lady); returns de.
	and 1
	ld hl, sCrystalExtDayCareEntries
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	ret

CrystalCopyPartySidecarToDayCare::
; a = Day-Care entry index 0..1; source is wCurPartyMon.
	push af
	ld a, [wCurPartyMon]
	call CrystalGetPartySidecarEntry
	push de
	pop hl
	pop af
	call CrystalGetDayCareSidecarEntry
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	jp CloseSRAM

CrystalCopyPartySidecarToDayCare1::
	xor a
	jp CrystalCopyPartySidecarToDayCare

CrystalCopyPartySidecarToDayCare2::
	ld a, 1
	jp CrystalCopyPartySidecarToDayCare

CrystalMoveDayCareSidecarToLastParty::
; a = Day-Care entry index. Destination is the party mon just appended.
	push af
	ld a, [wPartyCount]
	dec a
	call CrystalGetPartySidecarEntry
	ld b, d
	ld c, e
	pop af
	push bc
	call CrystalGetDayCareSidecarEntry
	ld h, d
	ld l, e
	pop de
	push hl
	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	pop hl
	xor a
	ld b, CRYSTAL_EXT_MON_ENTRY_SIZE
.clear
	ld [hli], a
	dec b
	jr nz, .clear
	jp CloseSRAM

CrystalMoveDayCare1SidecarToLastParty::
	xor a
	jp CrystalMoveDayCareSidecarToLastParty

CrystalMoveDayCare2SidecarToLastParty::
	ld a, 1
	jp CrystalMoveDayCareSidecarToLastParty
"""
    abi.write_text(abi_text,encoding="utf-8")

    move=root/"engine/pokemon/move_mon.asm"
    replace_once(
        move,
        """DepositMonWithDayCareMan:
	ld de, wBreedMon1Nickname
	call DepositBreedmon
	xor a ; REMOVE_PARTY
""",
        """DepositMonWithDayCareMan:
	ld de, wBreedMon1Nickname
	call DepositBreedmon
	farcall CrystalCopyPartySidecarToDayCare1
	xor a ; REMOVE_PARTY
""",
    )
    replace_once(
        move,
        """DepositMonWithDayCareLady:
	ld de, wBreedMon2Nickname
	call DepositBreedmon
	xor a ; REMOVE_PARTY
""",
        """DepositMonWithDayCareLady:
	ld de, wBreedMon2Nickname
	call DepositBreedmon
	farcall CrystalCopyPartySidecarToDayCare2
	xor a ; REMOVE_PARTY
""",
    )

    replace_once(
        move,
        """	xor a
	ld [wPokemonWithdrawDepositParameter], a
	jp RetrieveBreedmon

RetrieveMonFromDayCareLady:
""",
        """	xor a
	ld [wPokemonWithdrawDepositParameter], a
	call RetrieveBreedmon
	ret c
	farcall CrystalMoveDayCare1SidecarToLastParty
	and a
	ret

RetrieveMonFromDayCareLady:
""",
    )
    replace_once(
        move,
        """	ld a, PC_DEPOSIT
	ld [wPokemonWithdrawDepositParameter], a
	jp RetrieveBreedmon ; pointless
""",
        """	ld a, PC_DEPOSIT
	ld [wPokemonWithdrawDepositParameter], a
	call RetrieveBreedmon
	ret c
	farcall CrystalMoveDayCare2SidecarToLastParty
	and a
	ret
""",
    )

    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("CRYSTAL native ID Stage 2d Day-Care patch: applied cleanly")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
