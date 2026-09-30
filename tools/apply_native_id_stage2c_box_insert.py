#!/usr/bin/env python3
"""Apply native GBC Stage 2c for legacy-only direct box insertions."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED="e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message:str)->None:
    raise SystemExit(f"native ID Stage 2c patch failed: {message}")


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
    if "CrystalInsertTempSidecarIntoCurrentBox::" not in abi_text:
        fail("Stage 2b move bridge missing")
    if "CrystalClearTempSidecar::" in abi_text:
        fail("Stage 2c already applied")

    abi_text += r"""

; ---------------------------------------------------------------------------
; Stage 2c: legacy-only direct box insertion.
; Legacy callers can only supply u8 Species/Item/Move IDs, so their canonical
; high bytes are explicitly zero. The low bytes remain untouched in BoxMon.
; ---------------------------------------------------------------------------

CrystalClearTempSidecar::
	ld hl, wCrystalExtTempMonEntry
	xor a
	ld b, CRYSTAL_EXT_MON_ENTRY_SIZE
.loop
	ld [hli], a
	dec b
	jr nz, .loop
	ret

CrystalInsertLegacyZeroSidecarIntoCurrentBox::
; wCurPartyMon = insertion index already used by legacy InsertPokemonIntoBox.
	call CrystalClearTempSidecar
	jp CrystalInsertTempSidecarIntoCurrentBox

CrystalInsertLegacyZeroSidecarAtBoxFront::
; SendMonIntoBox always inserts at index 0 via ShiftBoxMon.
; Preserve wCurPartyMon because callers may still depend on it.
	ld a, [wCurPartyMon]
	push af
	xor a
	ld [wCurPartyMon], a
	call CrystalClearTempSidecar
	call CrystalInsertTempSidecarIntoCurrentBox
	pop af
	ld [wCurPartyMon], a
	ret
"""
    abi.write_text(abi_text,encoding="utf-8")

    move_mon=root/"engine/pokemon/move_mon.asm"
    replace_once(
        move_mon,
        """	ld b, 0
	call RestorePPOfDepositedPokemon

	call CloseSRAM
	scf
	ret
""",
        """	ld b, 0
	call RestorePPOfDepositedPokemon

; This path creates the new BoxMon from legacy u8 state only. Mirror the
; front insertion in the canonical sidecar and explicitly zero its high IDs.
	farcall CrystalInsertLegacyZeroSidecarAtBoxFront
	call CloseSRAM
	scf
	ret
""",
    )

    caught=root/"engine/pokemon/caught_data.asm"
    replace_once(
        caught,
        """	ld hl, wPlayerName
	ld de, wBufferMonOT
	ld bc, NAME_LENGTH
	call CopyBytes
	callfar InsertPokemonIntoBox
	ld a, [wCurPartySpecies]
""",
        """	ld hl, wPlayerName
	ld de, wBufferMonOT
	ld bc, NAME_LENGTH
	call CopyBytes
	callfar InsertPokemonIntoBox
; Bug Contest buffer data is still legacy-u8-only. Mirror the insertion in
; the sidecar and use zero high bytes.
	farcall CrystalInsertLegacyZeroSidecarIntoCurrentBox
	ld a, [wCurPartySpecies]
""",
    )

    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("CRYSTAL native ID Stage 2c legacy box insertion patch: applied cleanly")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
