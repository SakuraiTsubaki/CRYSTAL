#!/usr/bin/env python3
"""Verify patched source outputs against CRYSTAL's binary Stage 0 transformer."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

EXPECTED = {
    "pokecrystal.gbc": "7b5f7f48825696fc9cbca09eceff9afc74881d53",
    "pokecrystal11.gbc": "c206ea7770ac566783ac22b33240f260643c96b6",
}


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def verify(path: Path) -> None:
    data = path.read_bytes()
    if len(data) != 0x400000:
        raise SystemExit(f"{path}: expected 4 MiB, got {len(data):#x}")
    if data[0x147] != 0x10 or data[0x148] != 0x07 or data[0x149] != 0x05:
        raise SystemExit(
            f"{path}: bad expanded header "
            f"{data[0x147]:#x}/{data[0x148]:#x}/{data[0x149]:#x}"
        )
    if data[0x10:0x16] != bytes.fromhex("E0 9D EA 00 20 C9"):
        raise SystemExit(f"{path}: bank switch signature changed")
    if data[0x2FCB:0x2FD1] != bytes.fromhex("FE 08 38 02 18 10"):
        raise SystemExit(f"{path}: OpenSRAM is not widened to eight banks")
    if data[0x1FFDF8:0x1FFDFE] != b"N64PS3":
        raise SystemExit(f"{path}: missing regenerated N64PS3 metadata")
    if data[0x200000:] != b"\xFF" * 0x200000:
        raise SystemExit(f"{path}: expansion half is not all 0xFF")
    expected = EXPECTED[path.name]
    actual = sha1(path)
    if actual != expected:
        raise SystemExit(f"{path}: SHA-1 {actual} != expected {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roms", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.roms:
        verify(path)
        print(f"{path.name}: OK {sha1(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
