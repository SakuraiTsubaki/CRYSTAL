#!/usr/bin/env python3
"""Seed CRYSTAL's native Generation-10 registry bank and redirect proven legacy reads.

Input is one of the seven verified retail Crystal ROMs. Stage 0 is applied first by
tools/expand_original_crystal.py. Stage 1 then:

- writes CRYSREG v1 into new ROM bank $81;
- copies the verified legacy BaseData, Moves and ItemAttributes tables into it;
- redirects every proven BaseData/ItemAttributes/Moves read to bank $81;
- keeps legacy u8 ID semantics for this stage;
- regenerates Crystal Stadium metadata and the Game Boy global checksum.

The result creates a single canonical registry boundary before Stage 2 widens runtime
IDs. ROM binaries are outputs only and must not be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import expand_original_crystal as stage0

ROOT = Path(__file__).resolve().parents[1]
STAGE0_CONFIG = ROOT / "config" / "native_gbc_stage0.json"
STAGE1_CONFIG = ROOT / "config" / "native_gbc_stage1.json"

REGISTRY_BANK = 0x81
REGISTRY_PHYS = REGISTRY_BANK * 0x4000
REGISTRY_MAGIC = b"CRYSREG\0"
REGISTRY_DIRECTORY_OFFSET = 0x40
REGISTRY_ENTRY_BYTES = 16
REGISTRY_DATA_OFFSET = 0x100

REGISTRY_SPECIES = 1
REGISTRY_MOVES = 2
REGISTRY_ITEMS = 3

BASE_DATA_COUNT = 251
BASE_DATA_ENTRY_BYTES = 32
BASE_DATA_BYTES = BASE_DATA_COUNT * BASE_DATA_ENTRY_BYTES
MOVES_COUNT = 251
MOVES_ENTRY_BYTES = 7
MOVES_BYTES = MOVES_COUNT * MOVES_ENTRY_BYTES
ITEM_COUNT = 256
ITEM_ENTRY_BYTES = 7
ITEM_BYTES = ITEM_COUNT * ITEM_ENTRY_BYTES

REGISTRY_BASE_ADDR = 0x4000 + REGISTRY_DATA_OFFSET
REGISTRY_MOVES_ADDR = REGISTRY_BASE_ADDR + BASE_DATA_BYTES
REGISTRY_ITEMS_ADDR = REGISTRY_MOVES_ADDR + MOVES_BYTES

BASE_PREFIX = bytes.fromhex("01 2D 31 31 2D 41 41 16 03 2D 40 00 00")
MOVE_PREFIX = bytes((1, 0, 40, 0, 255, 35, 0, 2, 0, 50, 1, 255, 25, 0))

BASE_LOOKUP_PATTERN = (
    0xC5, 0xD5, 0xE5, 0xF0, None, 0xF5, 0x3E, None, 0xD7,
    0xFA, None, None, 0xFE, 0xFD, 0x28, None, 0x3D, 0x01, 0x20,
    0x00, 0x21, None, None, 0xCD, None, None, 0x11, None, None,
    0x01, 0x20, 0x00, 0xCD, None, None,
)
ITEM_LOOKUP_PATTERN = (
    0xE5, 0xC5, 0x21, None, None, 0x4F, 0x06, 0x00, 0x09, 0xAF,
    0xEA, None, None, 0xFA, None, None, 0x3D, 0x4F, 0x3E, 0x07,
    0xCD, None, None, 0x3E, 0x01, 0xCD, None, None, 0xC1, 0xE1,
    0xC9,
)
MOVE_ATTR_HELPER_PATTERN = (
    0xC5, 0x01, 0x07, 0x00, 0xCD, None, None, 0xCD, None, None,
    0xC1, 0xC9,
)

IMM16_OPS = {
    0x01, 0x08, 0x11, 0x21, 0x31,
    0xC2, 0xC3, 0xC4, 0xCA, 0xCC, 0xCD,
    0xD2, 0xD4, 0xDA, 0xDC, 0xEA, 0xFA,
}
IMM8_OPS = {
    0x06, 0x0E, 0x10, 0x16, 0x18, 0x1E, 0x20, 0x26, 0x28,
    0x2E, 0x30, 0x36, 0x38, 0x3E, 0xC6, 0xCE, 0xD6, 0xDE,
    0xE0, 0xE6, 0xE8, 0xEE, 0xF0, 0xF6, 0xF8, 0xFE,
}
BANK_USE_OPS = {0xCD, 0xC3, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF}


def sha1(data: bytes | bytearray) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_all(data: bytes, pattern: bytes) -> list[int]:
    result = []
    pos = 0
    while True:
        hit = data.find(pattern, pos)
        if hit < 0:
            return result
        result.append(hit)
        pos = hit + 1


def find_wild(data: bytes, pattern: tuple[int | None, ...]) -> list[int]:
    result = []
    for offset in range(len(data) - len(pattern) + 1):
        if all(value is None or data[offset + index] == value for index, value in enumerate(pattern)):
            result.append(offset)
    return result


def locate_item_attributes(data: bytes) -> int:
    candidates = []
    for pos in range(len(data) - 5 * ITEM_ENTRY_BYTES):
        if all(
            data[pos + index * ITEM_ENTRY_BYTES: pos + index * ITEM_ENTRY_BYTES + 2]
            == price.to_bytes(2, "little")
            for index, price in enumerate((0, 1200, 10, 600, 200))
        ):
            candidates.append(pos)
    if len(candidates) != 1:
        raise ValueError(f"expected one ItemAttributes table, found {len(candidates)}")
    return candidates[0]


def locate_tables(data: bytes, config: dict) -> tuple[dict, tuple[bytes, bytes, bytes]]:
    base_hits = find_all(data, BASE_PREFIX)
    move_hits = find_all(data, MOVE_PREFIX)
    item = locate_item_attributes(data)
    if len(base_hits) != 1:
        raise ValueError(f"expected one BaseData table, found {len(base_hits)}")
    if len(move_hits) != 1:
        raise ValueError(f"expected one Moves table, found {len(move_hits)}")

    base = base_hits[0]
    moves = move_hits[0]
    base_blob = data[base:base + BASE_DATA_BYTES]
    move_blob = data[moves:moves + MOVES_BYTES]
    item_blob = data[item:item + ITEM_BYTES]

    tables = config["registry"]["tables"]
    checks = (
        ("BaseData", base_blob, tables["species_base_data"]["sha256"]),
        ("Moves", move_blob, tables["moves"]["sha256"]),
        ("ItemAttributes", item_blob, tables["item_attributes"]["sha256"]),
    )
    for name, blob, expected in checks:
        actual = sha256(blob)
        if actual != expected:
            raise ValueError(f"{name} SHA-256 mismatch: {actual}")

    return {
        "base_data": base,
        "moves": moves,
        "item_attributes": item,
    }, (base_blob, move_blob, item_blob)


def build_registry(data: bytes, release_id: str, config: dict) -> tuple[bytes, dict]:
    offsets, blobs = locate_tables(data, config)
    profile_ids = {
        release: index + 1
        for index, release in enumerate(config["releases"])
    }

    bank = bytearray(b"\xFF" * 0x4000)
    struct.pack_into(
        "<8sHHHHHH",
        bank,
        0,
        REGISTRY_MAGIC,
        1,
        profile_ids[release_id],
        3,
        REGISTRY_DIRECTORY_OFFSET,
        REGISTRY_DATA_OFFSET,
        16,
    )

    cursor = REGISTRY_DATA_OFFSET
    entries = []
    for registry_type, entry_size, count, blob in (
        (REGISTRY_SPECIES, BASE_DATA_ENTRY_BYTES, BASE_DATA_COUNT, blobs[0]),
        (REGISTRY_MOVES, MOVES_ENTRY_BYTES, MOVES_COUNT, blobs[1]),
        (REGISTRY_ITEMS, ITEM_ENTRY_BYTES, ITEM_COUNT, blobs[2]),
    ):
        entries.append((
            registry_type,
            1,
            entry_size,
            16,
            cursor,
            count,
            len(blob),
            0,
        ))
        bank[cursor:cursor + len(blob)] = blob
        cursor += len(blob)

    for index, entry in enumerate(entries):
        struct.pack_into(
            "<HHHHHHHH",
            bank,
            REGISTRY_DIRECTORY_OFFSET + index * REGISTRY_ENTRY_BYTES,
            *entry,
        )

    if cursor != config["registry"]["used_bytes_from_bank_start"]:
        raise AssertionError("registry size differs from contract")
    return bytes(bank), offsets


def bank_addr(physical: int) -> tuple[int, int]:
    return physical // 0x4000, 0x4000 + (physical % 0x4000)


def cpu_addr_to_phys(current_bank: int, address: int) -> int:
    if address < 0x4000:
        return address
    return current_bank * 0x4000 + (address - 0x4000)


def ld_hl_refs(data: bytes, address: int, width: int) -> list[tuple[int, int]]:
    refs = []
    for field_offset in range(width):
        target = address + field_offset
        sig = bytes((0x21, target & 0xFF, target >> 8))
        pos = 0
        while True:
            hit = data.find(sig, pos)
            if hit < 0:
                break
            refs.append((hit, field_offset))
            pos = hit + 1
    return sorted(refs)


def opcode_length(op: int) -> int:
    if op == 0xCB:
        return 2
    if op in IMM16_OPS:
        return 3
    if op in IMM8_OPS:
        return 2
    return 1


def decode_linear(data: bytes, start: int, max_bytes: int) -> list[tuple[int, int, bytes]]:
    end = min(len(data), start + max_bytes)
    pos = start
    decoded = []
    while pos < end:
        op = data[pos]
        length = opcode_length(op)
        if pos + length > end:
            break
        decoded.append((pos, op, data[pos:pos + length]))
        pos += length
        if op in (0xC9, 0xD9):
            break
    return decoded


def bank_load_ops(data: bytes, start: int, bank: int, max_bytes: int) -> list[int]:
    result = []
    for pos, op, raw in decode_linear(data, start, max_bytes):
        if op != 0x3E or len(raw) != 2 or raw[1] != bank:
            continue
        if pos + 2 < len(data) and data[pos + 2] in BANK_USE_OPS:
            result.append(pos)
    return result


def patch_base_data(out: bytearray, original: bytes, table_phys: int) -> dict:
    table_bank, table_addr = bank_addr(table_phys)
    if table_bank != 0x14:
        raise ValueError(f"unexpected BaseData bank {table_bank:#x}")

    central_hits = find_wild(original, BASE_LOOKUP_PATTERN)
    if len(central_hits) != 1:
        raise ValueError(f"expected one GetBaseData signature, found {len(central_hits)}")
    central = central_hits[0]

    if original[central + 7] != table_bank:
        raise ValueError("GetBaseData bank precondition failed")
    if (original[central + 21] | (original[central + 22] << 8)) != table_addr:
        raise ValueError("GetBaseData address precondition failed")

    out[central + 7] = REGISTRY_BANK
    out[central + 21] = REGISTRY_BASE_ADDR & 0xFF
    out[central + 22] = REGISTRY_BASE_ADDR >> 8

    pointer_offsets = [central + 20]
    bank_offsets = [central + 7]

    for offset, field_offset in ld_hl_refs(original, table_addr, BASE_DATA_ENTRY_BYTES):
        if offset == central + 20:
            continue
        loads = bank_load_ops(original, offset, table_bank, 48)
        if not loads:
            continue

        target = REGISTRY_BASE_ADDR + field_offset
        out[offset + 1] = target & 0xFF
        out[offset + 2] = target >> 8
        for load in loads:
            out[load + 1] = REGISTRY_BANK
            bank_offsets.append(load + 1)
        pointer_offsets.append(offset)

    return {
        "pointer_offsets": sorted(set(pointer_offsets)),
        "bank_immediate_offsets": sorted(set(bank_offsets)),
    }


def patch_item_attributes(out: bytearray, original: bytes, table_phys: int) -> dict:
    table_bank, table_addr = bank_addr(table_phys)
    if table_bank != 0x01:
        raise ValueError(f"unexpected ItemAttributes bank {table_bank:#x}")

    central_hits = find_wild(original, ITEM_LOOKUP_PATTERN)
    if len(central_hits) != 1:
        raise ValueError(f"expected one GetItemAttr signature, found {len(central_hits)}")
    central = central_hits[0]

    if (original[central + 3] | (original[central + 4] << 8)) != table_addr:
        raise ValueError("GetItemAttr address precondition failed")
    if original[central + 24] != table_bank:
        raise ValueError("GetItemAttr bank precondition failed")

    out[central + 3] = REGISTRY_ITEMS_ADDR & 0xFF
    out[central + 4] = REGISTRY_ITEMS_ADDR >> 8
    out[central + 24] = REGISTRY_BANK

    pointer_offsets = [central + 2]
    bank_offsets = [central + 24]

    for offset, field_offset in ld_hl_refs(original, table_addr, ITEM_ENTRY_BYTES):
        if offset == central + 2:
            continue
        loads = bank_load_ops(original, offset, table_bank, 48)
        if not loads:
            continue

        target = REGISTRY_ITEMS_ADDR + field_offset
        out[offset + 1] = target & 0xFF
        out[offset + 2] = target >> 8
        for load in loads:
            out[load + 1] = REGISTRY_BANK
            bank_offsets.append(load + 1)
        pointer_offsets.append(offset)

    return {
        "pointer_offsets": sorted(set(pointer_offsets)),
        "bank_immediate_offsets": sorted(set(bank_offsets)),
    }


def patch_moves(out: bytearray, original: bytes, table_phys: int) -> dict:
    table_bank, table_addr = bank_addr(table_phys)
    if table_bank != 0x10:
        raise ValueError(f"unexpected Moves bank {table_bank:#x}")

    helper_hits = find_wild(original, MOVE_ATTR_HELPER_PATTERN)
    if len(helper_hits) != 1:
        raise ValueError(f"expected one GetMoveAttr helper, found {len(helper_hits)}")
    helper = helper_hits[0]
    helper_cpu = bank_addr(helper)[1]

    get_move_data = helper + 12
    if (original[get_move_data + 1] | (original[get_move_data + 2] << 8)) != table_addr:
        raise ValueError("GetMoveData pointer precondition failed")
    if original[helper + 22] != table_bank or original[helper + 27] != table_bank:
        raise ValueError("Moves central bank precondition failed")

    out[get_move_data + 1] = REGISTRY_MOVES_ADDR & 0xFF
    out[get_move_data + 2] = REGISTRY_MOVES_ADDR >> 8
    out[helper + 22] = REGISTRY_BANK
    out[helper + 27] = REGISTRY_BANK

    pointer_offsets = [get_move_data]
    bank_offsets = [helper + 22, helper + 27]
    excluded = []

    for offset, field_offset in ld_hl_refs(original, table_addr, MOVES_ENTRY_BYTES):
        if offset == get_move_data:
            continue

        if original[offset + 3] == 0xCD:
            call_addr = original[offset + 4] | (original[offset + 5] << 8)
            call_phys = cpu_addr_to_phys(offset // 0x4000, call_addr)
            if call_phys == helper:
                target = REGISTRY_MOVES_ADDR + field_offset
                out[offset + 1] = target & 0xFF
                out[offset + 2] = target >> 8
                pointer_offsets.append(offset)
                continue

        loads = bank_load_ops(original, offset, table_bank, 40)
        if loads:
            target = REGISTRY_MOVES_ADDR + field_offset
            out[offset + 1] = target & 0xFF
            out[offset + 2] = target >> 8
            for load in loads:
                out[load + 1] = REGISTRY_BANK
                bank_offsets.append(load + 1)
            pointer_offsets.append(offset)
            continue

        excluded.append(offset)

    return {
        "helper_offset": helper,
        "helper_cpu_address": helper_cpu,
        "pointer_offsets": sorted(set(pointer_offsets)),
        "bank_immediate_offsets": sorted(set(bank_offsets)),
        "excluded_address_collisions": sorted(set(excluded)),
    }


def verify_contract(release_id: str, hooks: dict, config: dict) -> None:
    release = config["releases"][release_id]
    expected = release["expected_hooks"]
    actual = {
        "base_pointers": len(hooks["base"]["pointer_offsets"]),
        "base_bank_immediates": len(hooks["base"]["bank_immediate_offsets"]),
        "item_pointers": len(hooks["items"]["pointer_offsets"]),
        "item_bank_immediates": len(hooks["items"]["bank_immediate_offsets"]),
        "move_pointers": len(hooks["moves"]["pointer_offsets"]),
        "move_bank_immediates": len(hooks["moves"]["bank_immediate_offsets"]),
    }
    if actual != expected:
        raise ValueError(f"{release_id}: hook census changed: {actual} != {expected}")

    expected_excluded = sorted(int(value, 16) for value in release["excluded_move_address_collisions"])
    actual_excluded = hooks["moves"]["excluded_address_collisions"]
    if actual_excluded != expected_excluded:
        raise ValueError(
            f"{release_id}: Moves collision census changed: "
            f"{actual_excluded} != {expected_excluded}"
        )


def verify_registry_parity(output: bytes, original: bytes, offsets: dict) -> None:
    checks = (
        (REGISTRY_DATA_OFFSET, offsets["base_data"], BASE_DATA_BYTES),
        (REGISTRY_MOVES_ADDR - 0x4000, offsets["moves"], MOVES_BYTES),
        (REGISTRY_ITEMS_ADDR - 0x4000, offsets["item_attributes"], ITEM_BYTES),
    )
    for registry_offset, source_offset, length in checks:
        left = output[REGISTRY_PHYS + registry_offset:REGISTRY_PHYS + registry_offset + length]
        right = original[source_offset:source_offset + length]
        if left != right:
            raise ValueError(f"registry parity failed at source {source_offset:#x}")


def expand_stage1(data: bytes, stage0_config: dict, stage1_config: dict) -> tuple[bytes, dict]:
    release_id, _ = stage0.identify_release(data, stage0_config)
    stage0_output, stage0_report = stage0.expand_rom(data, stage0_config)

    registry, source_offsets = build_registry(data, release_id, stage1_config)

    expected_source = stage1_config["releases"][release_id]["source_offsets"]
    for key, actual in source_offsets.items():
        if actual != int(expected_source[key], 16):
            raise ValueError(
                f"{release_id}: {key} moved: {actual:#x} != {expected_source[key]}"
            )

    out = bytearray(stage0_output)
    out[REGISTRY_PHYS:REGISTRY_PHYS + 0x4000] = registry

    hooks = {
        "base": patch_base_data(out, data, source_offsets["base_data"]),
        "items": patch_item_attributes(out, data, source_offsets["item_attributes"]),
        "moves": patch_moves(out, data, source_offsets["moves"]),
    }
    verify_contract(release_id, hooks, stage1_config)

    # Stage 1 changes pointers/bank immediates inside the original 2 MiB
    # Stadium checksum domain, so regenerate it after all redirects.
    stage0.regenerate_stadium_metadata(out)
    out[0x14E:0x150] = stage0.global_checksum(out).to_bytes(2, "big")
    stage0.validate_checksums(out)

    verify_registry_parity(bytes(out), data, source_offsets)

    report = {
        "stage": "native-gbc-registry-seed-1",
        "release": release_id,
        "input_sha256": sha256(data),
        "stage0_sha256": stage0_report["output_sha256"],
        "output_sha1": sha1(out),
        "output_sha256": sha256(out),
        "output_bytes": len(out),
        "registry": {
            "bank": REGISTRY_BANK,
            "physical_offset": REGISTRY_PHYS,
            "base_data_cpu_address": REGISTRY_BASE_ADDR,
            "moves_cpu_address": REGISTRY_MOVES_ADDR,
            "item_attributes_cpu_address": REGISTRY_ITEMS_ADDR,
            "source_offsets": source_offsets,
        },
        "hooks": hooks,
    }

    expected = stage1_config["releases"][release_id]
    if report["output_sha1"] != expected["output_sha1"]:
        raise AssertionError(f"{release_id}: deterministic Stage 1 SHA-1 mismatch")
    if report["output_sha256"] != expected["output_sha256"]:
        raise AssertionError(f"{release_id}: deterministic Stage 1 SHA-256 mismatch")

    return bytes(out), report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stage0-config", type=Path, default=STAGE0_CONFIG)
    parser.add_argument("--stage1-config", type=Path, default=STAGE1_CONFIG)
    args = parser.parse_args()

    data = args.input.read_bytes()
    stage0_config = stage0.load_config(args.stage0_config)
    stage1_config = load_json(args.stage1_config)

    output, report = expand_stage1(data, stage0_config, stage1_config)
    args.output.write_bytes(output)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
