#!/usr/bin/env python3
"""Validate the first native GBC 16-bit identity sidecar slice."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

SYMBOL_RE = re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)$")


def symbols(path: Path) -> dict[str, tuple[int, int]]:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = SYMBOL_RE.match(raw.strip())
        if match:
            bank, addr, name = match.groups()
            out[name] = (int(bank, 16), int(addr, 16))
    return out


def require(sym: dict[str, tuple[int, int]], name: str, expected: tuple[int, int]) -> None:
    actual = sym.get(name)
    if actual != expected:
        raise SystemExit(f"{name}: expected {expected}, got {actual}")


def verify(rom: Path, sym_path: Path) -> None:
    data = rom.read_bytes()
    if len(data) != 0x400000:
        raise SystemExit(f"{rom}: expected 4 MiB")
    if (data[0x147], data[0x148], data[0x149]) != (0x10, 0x07, 0x05):
        raise SystemExit(f"{rom}: expanded cartridge header mismatch")
    if data[0x1FFDF8:0x1FFDFE] != b"N64PS3":
        raise SystemExit(f"{rom}: N64PS3 metadata missing")

    sym = symbols(sym_path)
    require(sym, "sCrystalExtSaveCore", (0x04, 0xB001))
    require(sym, "sCrystalExtMonEntries", (0x04, 0xB021))
    require(sym, "sCrystalExtSaveCoreEnd", (0x04, 0xBF1B))
    require(sym, "CrystalGetSpeciesID", (0x80, 0x4000))

    for name in (
        "CrystalSetSpeciesID",
        "CrystalGetHeldItemID",
        "CrystalSetHeldItemID",
        "CrystalGetMoveID",
        "CrystalSetMoveID",
        "CrystalGetVariantProfileID",
        "CrystalSetVariantProfileID",
        "CrystalGetAbilityState",
        "CrystalSetAbilityState",
        "CrystalInitExtendedSaveCore",
        "CrystalValidateExtendedSaveCore",
        "CrystalEnsureExtendedSaveCore",
        "CrystalGetPartySidecarEntry",
        "CrystalGetCurrentPartySpeciesID",
        "CrystalSetCurrentPartySpeciesID",
        "CrystalGetCurrentPartyHeldItemID",
        "CrystalSetCurrentPartyHeldItemID",
        "CrystalGetCurrentPartyMoveID",
        "CrystalSetCurrentPartyMoveID",
    ):
        bank, address = sym.get(name, (-1, -1))
        if bank != 0x80 or not (0x4000 <= address < 0x8000):
            raise SystemExit(f"{name}: expected callable code in ROM bank 0x80, got {bank:#x}:{address:#x}")

    bank80 = data[0x200000:0x204000]
    if bank80 == bytes(0x4000) or bank80 == b"\xFF" * 0x4000:
        raise SystemExit(f"{rom}: bank 0x80 does not contain the Stage 1 ABI")

    print(f"{rom.name}: Stage 1 sidecar/ABI OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("sym", type=Path)
    args = parser.parse_args()
    verify(args.rom, args.sym)
    return 0


if __name__ == "__main__":
    main()
