#!/usr/bin/env python3
"""Audit the pinned pokeemerald-expansion storage limits used by CRYSTAL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

EXPECTED_REF = "75b806a3ab57a81ff1eb6179288981f0b3cc3050"

def fail(message: str) -> None:
    raise SystemExit(f"GBA capacity audit failed: {message}")

def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")

def require_int(pattern: str, text: str, label: str) -> int:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        fail(f"cannot locate {label}")
    return int(match.group(1), 0)

def git_head(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.upstream.resolve()

    head = git_head(root)
    if head is not None and head != EXPECTED_REF:
        fail(f"upstream HEAD {head} != pinned {EXPECTED_REF}")

    pokemon_h = read(root, "include/pokemon.h")
    storage_h = read(root, "include/pokemon_storage_system.h")
    save_h = read(root, "include/save.h")
    species_h = read(root, "include/constants/species.h")
    items_h = read(root, "include/constants/items.h")
    moves_h = read(root, "include/constants/moves.h")

    species_bits = require_int(r"enum Species species:(\d+)", pokemon_h, "BoxPokemon species bit width")
    item_bits = require_int(r"enum Item heldItem:(\d+)", pokemon_h, "BoxPokemon held-item bit width")
    move_bits = [
        require_int(rf"enum Move move{i}:(\d+)", pokemon_h, f"BoxPokemon move{i} bit width")
        for i in range(1, 5)
    ]
    boxes = require_int(r"#define\s+TOTAL_BOXES_COUNT\s+(\d+)", storage_h, "TOTAL_BOXES_COUNT")
    rows = require_int(r"#define\s+IN_BOX_ROWS\s+(\d+)", storage_h, "IN_BOX_ROWS")
    cols = require_int(r"#define\s+IN_BOX_COLUMNS\s+(\d+)", storage_h, "IN_BOX_COLUMNS")
    sector_data = require_int(r"#define\s+SECTOR_DATA_SIZE\s+(\d+)", save_h, "SECTOR_DATA_SIZE")
    sectors_per_slot = require_int(r"#define\s+NUM_SECTORS_PER_SLOT\s+(\d+)", save_h, "NUM_SECTORS_PER_SLOT")
    storage_start = require_int(r"#define\s+SECTOR_ID_PKMN_STORAGE_START\s+(\d+)", save_h, "storage start sector")
    storage_end = require_int(r"#define\s+SECTOR_ID_PKMN_STORAGE_END\s+(\d+)", save_h, "storage end sector")

    species_max = max(map(int, re.findall(r"SPECIES_[A-Z0-9_]+\s*=\s*(\d+)", species_h)))
    item_max = max(map(int, re.findall(r"ITEM_[A-Z0-9_]+\s*=\s*(\d+)", items_h)))
    move_max_explicit = max(map(int, re.findall(r"MOVE_[A-Z0-9_]+\s*=\s*(\d+)", moves_h)))

    if species_bits != 11:
        fail(f"expected pinned species low width 11, found {species_bits}")
    if item_bits != 10:
        fail(f"expected pinned item low width 10, found {item_bits}")
    if move_bits != [11, 11, 11, 11]:
        fail(f"expected four 11-bit moves, found {move_bits}")
    if boxes != 14 or rows * cols != 30:
        fail(f"expected 14x30 PC storage, found {boxes}x{rows * cols}")
    if sector_data != 3968 or sectors_per_slot != 14:
        fail(f"unexpected save geometry: data={sector_data}, sectors/slot={sectors_per_slot}")
    if storage_end - storage_start + 1 != 9:
        fail("expected pinned PokemonStorage to occupy 9 sectors")

    report = {
        "upstream": EXPECTED_REF,
        "boxPokemonLowBits": {
            "species": species_bits,
            "item": item_bits,
            "moves": move_bits,
        },
        "pc": {
            "boxes": boxes,
            "monsPerBox": rows * cols,
            "storedMons": boxes * rows * cols,
            "extensionGrowthBytes": boxes * rows * cols * 4,
        },
        "save": {
            "sectorDataBytes": sector_data,
            "sectorsPerSlot": sectors_per_slot,
            "pokemonStorageSectors": storage_end - storage_start + 1,
            "pokemonStorageCapacityBytes": (storage_end - storage_start + 1) * sector_data,
            "candidateTenSectorCapacityBytes": 10 * sector_data,
        },
        "currentExplicitMax": {
            "species": species_max,
            "item": item_max,
            "move": move_max_explicit,
        },
        "target": {
            "speciesBits": 16,
            "itemBits": 16,
            "moveBits": 16,
            "maxId": 65535,
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("CRYSTAL GBA capacity audit: OK")
        print(f"Pinned upstream: {EXPECTED_REF}")
        print(f"Serialized low widths: species={species_bits}, item={item_bits}, moves={move_bits}")
        print(f"PC storage: {boxes * rows * cols} mons; +4 bytes/mon = +{report['pc']['extensionGrowthBytes']} bytes")
        print(f"PokemonStorage: 9 sectors={report['save']['pokemonStorageCapacityBytes']} bytes; 10 sectors={report['save']['candidateTenSectorCapacityBytes']} bytes")
        print(f"Explicit upstream maxima seen: species={species_max}, item={item_max}, move={move_max_explicit}")
        print("Target canonical ID width: 16 bits")
    return 0

if __name__ == "__main__":
    sys.exit(main())
