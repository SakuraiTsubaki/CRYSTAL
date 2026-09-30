#!/usr/bin/env python3
"""Apply CRYSTAL native GBC Stage 2 box/party sidecar lifecycle patch.

Run after apply_native_source_stage0.py and apply_native_id_stage1.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED = "e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message: str) -> None:
    raise SystemExit(f"native ID Stage 2 box patch failed: {message}")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        fail(f"{path}: expected exactly one target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    root = args.source.resolve()

    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != PINNED:
        fail(f"source HEAD {head} != pinned {PINNED}")

    abi = root / "engine/pokemon/extended_ids.asm"
    if not abi.exists():
        fail("Stage 1 ABI missing; apply native ID Stage 1 first")

    abi_text = abi.read_text(encoding="utf-8")
    if "CrystalGetCurrentPartyMoveID::" not in abi_text:
        fail("Stage 1 party bridge missing")
    if "CrystalGetBoxSidecarEntry::" in abi_text:
        fail("Stage 2 box bridge already applied")

    abi_text += r"""

; ---------------------------------------------------------------------------
; Stage 2: current-box / party sidecar lifecycle.
; ---------------------------------------------------------------------------

CrystalGetBoxSidecarEntry::
; b = box index 0..13
; a = mon index 0..29
; returns de = persistent sidecar entry
	push af
	ld hl, sCrystalExtMonEntries
	ld bc, CRYSTAL_EXT_MAX_MONS_PER_BOX * CRYSTAL_EXT_MON_ENTRY_SIZE
	ld a, b
	call AddNTimes
	pop af
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	ret

CrystalCopyPartySidecarToCurrentBox::
; Called while the active-box SRAM bank is open.
; Source = wCurPartyMon, destination = newly appended current-box mon.
	ld a, [wCurPartyMon]
	call CrystalGetPartySidecarEntry
	push de

	ld a, [sBoxCount]
	dec a
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	call CrystalGetBoxSidecarEntry
	pop hl

	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	ld a, BANK(sBoxCount)
	call OpenSRAM
	ret

CrystalCopyCurrentBoxSidecarToParty::
; Called while the active-box SRAM bank is open.
; Source = wCurPartyMon in current box, destination = newly appended party mon.
	ld a, [wCurPartyMon]
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	call CrystalGetBoxSidecarEntry
	push de

	ld a, [wPartyCount]
	dec a
	call CrystalGetPartySidecarEntry
	pop hl

	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	ld a, BANK(sBoxCount)
	call OpenSRAM
	ret

CrystalShiftPartySidecarAfterRemove::
; Remove wCurPartyMon from party sidecar after wPartyCount was decremented.
; Opens/closes SRAM because the legacy party path has no box SRAM bank open.
	ld a, [wCurPartyMon]
	push af
	call CrystalGetPartySidecarEntry
	pop af
	ld c, a
	ld a, [wPartyCount]
	sub c
	push af

	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld h, d
	ld l, e
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	add hl, bc
	pop af
.shift
	and a
	jr z, .clear_tail
	push af
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	pop af
	dec a
	jr .shift

.clear_tail
	xor a
	ld b, CRYSTAL_EXT_MON_ENTRY_SIZE
.clear
	ld [de], a
	inc de
	dec b
	jr nz, .clear
	jp CloseSRAM

CrystalShiftCurrentBoxSidecarAfterRemove::
; Called while active-box SRAM bank is open, after sBoxCount was decremented.
; Restores the active-box bank before returning.
	ld a, [sBoxCount]
	push af
	ld a, [wCurPartyMon]
	push af
	ld a, [wCurBox]
	and $f
	ld b, a
	pop af
	push af
	call CrystalGetBoxSidecarEntry
	pop af
	ld c, a
	pop af
	sub c
	push af

	ld a, BANK(sCrystalExtSaveCore)
	call OpenSRAM
	ld h, d
	ld l, e
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	add hl, bc
	pop af
.shift
	and a
	jr z, .clear_tail
	push af
	ld bc, CRYSTAL_EXT_MON_ENTRY_SIZE
	call CopyBytes
	pop af
	dec a
	jr .shift

.clear_tail
	xor a
	ld b, CRYSTAL_EXT_MON_ENTRY_SIZE
.clear
	ld [de], a
	inc de
	dec b
	jr nz, .clear
	ld a, BANK(sBoxCount)
	call OpenSRAM
	ret
"""
    abi.write_text(abi_text, encoding="utf-8")

    move_mon = root / "engine/pokemon/move_mon.asm"

    replace_once(
        move_mon,
        """	ld bc, MON_NAME_LENGTH
	call CopyBytes
	pop hl

	ld a, [wPokemonWithdrawDepositParameter]
	cp PC_DEPOSIT
""",
        """	ld bc, MON_NAME_LENGTH
	call CopyBytes
	pop hl

; Preserve the canonical high-ID sidecar before the legacy source is removed.
	ld a, [wPokemonWithdrawDepositParameter]
	and a
	jr z, .crystal_box_to_party
	cp PC_DEPOSIT
	jr nz, .crystal_sidecar_transfer_done
	farcall CrystalCopyPartySidecarToCurrentBox
	jr .crystal_sidecar_transfer_done
.crystal_box_to_party
	farcall CrystalCopyCurrentBoxSidecarToParty
.crystal_sidecar_transfer_done

	ld a, [wPokemonWithdrawDepositParameter]
	cp PC_DEPOSIT
""",
    )

    replace_once(
        move_mon,
        """.finish
	ld a, [wPokemonWithdrawDepositParameter]
	and a
	jp nz, CloseSRAM
""",
        """.finish
; Mirror the legacy array compaction in the persistent canonical-ID sidecar.
	ld a, [wPokemonWithdrawDepositParameter]
	and a
	jr z, .crystal_shift_party_sidecar
	farcall CrystalShiftCurrentBoxSidecarAfterRemove
	jr .crystal_sidecar_shift_done
.crystal_shift_party_sidecar
	farcall CrystalShiftPartySidecarAfterRemove
.crystal_sidecar_shift_done
	ld a, [wPokemonWithdrawDepositParameter]
	and a
	jp nz, CloseSRAM
""",
    )

    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("CRYSTAL native ID Stage 2 box lifecycle patch: applied cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
