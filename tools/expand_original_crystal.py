#!/usr/bin/env python3
"""Expand verified original Pokémon Crystal GBC ROMs to the native MBC30-class Stage 0 target."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "native_gbc_stage0.json"

ROM_INPUT_BYTES = 0x200000
ROM_TARGET_BYTES = 0x400000
RAW_SRAM_32K = 0x8000
RAW_SRAM_64K = 0x10000
OBSERVED_CONTAINER_EXTRA = 0x2C

BANKSWITCH_OFFSET = 0x0010
BANKSWITCH_SIGNATURE = bytes.fromhex("E0 9D EA 00 20 C9")
OPEN_SRAM_BODY = bytes.fromhex("F5 3E 01 EA 00 60 3E 0A EA 00 00 F1 EA 00 40 C9")
OPEN_SRAM_GUARD_4 = bytes.fromhex("FE 04 38 02 18 10")
OPEN_SRAM_GUARD_8 = bytes.fromhex("FE 08 38 02 18 10")

CART_MBC3_RTC_RAM_BATTERY = 0x10
ROM_SIZE_2M = 0x06
ROM_SIZE_4M = 0x07
RAM_SIZE_32K = 0x03
RAM_SIZE_64K = 0x05

STADIUM_BASE_ROM_BYTES = 0x200000
STADIUM_BANK_BYTES = 0x4000
STADIUM_NUM_BANKS = 128
STADIUM_N64_HEADER = b"N64PS3"
STADIUM_N64_HEADER_BYTES = 8
STADIUM_N64_DATA_BYTES = STADIUM_NUM_BANKS * 2 * 2
STADIUM_N64_TOTAL_BYTES = STADIUM_N64_HEADER_BYTES + STADIUM_N64_DATA_BYTES
STADIUM_N64_OFFSET = STADIUM_BASE_ROM_BYTES - STADIUM_N64_TOTAL_BYTES
STADIUM_BASE_TOTAL_BYTES = 24
STADIUM_BASE_OFFSET = STADIUM_N64_OFFSET - STADIUM_BASE_TOTAL_BYTES
STADIUM_CRC_POLY = 0xC387
STADIUM_CRC_INIT = 0xFEFE
STADIUM_BASE_CRC_INIT = 0xACDE


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def header_checksum(data: bytes) -> int:
    value = 0
    for byte in data[0x134:0x14D]:
        value = (value - byte - 1) & 0xFF
    return value


def global_checksum(data: bytes) -> int:
    return (sum(data[:0x14E]) + sum(data[0x150:])) & 0xFFFF


def validate_checksums(data: bytes) -> None:
    if header_checksum(data) != data[0x14D]:
        raise ValueError("bad Game Boy header checksum")
    stored = int.from_bytes(data[0x14E:0x150], "big")
    if global_checksum(data) != stored:
        raise ValueError("bad Game Boy global checksum")


def fix_checksums(buf: bytearray) -> None:
    buf[0x14D] = header_checksum(buf)
    buf[0x14E:0x150] = global_checksum(buf).to_bytes(2, "big")


def _stadium_crc_table() -> list[int]:
    table = []
    for i in range(256):
        rem = 0
        c = i
        for _ in range(8):
            rem = (rem >> 1) ^ (STADIUM_CRC_POLY if ((rem ^ c) & 1) else 0)
            c >>= 1
        table.append(rem & 0xFFFF)
    return table


STADIUM_CRC_TABLE = _stadium_crc_table()


def stadium_crc(init: int, data: bytes | bytearray) -> int:
    crc = init
    for byte in data:
        crc = (crc >> 8) ^ STADIUM_CRC_TABLE[(crc & 0xFF) ^ byte]
    return crc & 0xFFFF


def stadium_sum(init: int, data: bytes | bytearray) -> int:
    return (init + sum(data)) & 0xFFFF


def set_u16be(buf: bytearray, offset: int, value: int) -> None:
    buf[offset:offset + 2] = value.to_bytes(2, "big")


def regenerate_stadium_metadata(buf: bytearray) -> None:
    """Regenerate the 2 MiB Stadium checksum area after header/code mutations.

    International builds keep a conservative base block: its version header is
    preserved, all 128 "matches base ROM" flags are cleared, and its CRC is
    recalculated. Japanese Crystal has no base block at this location, so its
    zero-filled 24-byte area remains zero.
    """
    if len(buf) < STADIUM_BASE_ROM_BYTES:
        raise ValueError("ROM too small for Crystal Stadium metadata")

    if bytes(buf[STADIUM_N64_OFFSET:STADIUM_N64_OFFSET + 6]) != STADIUM_N64_HEADER:
        raise ValueError("missing N64PS3 signature at the expected Crystal offset")

    buf[0x14E:0x150] = b"\x00\x00"

    old_base = bytes(buf[STADIUM_BASE_OFFSET:STADIUM_BASE_OFFSET + STADIUM_BASE_TOTAL_BYTES])
    base_prefix = old_base[:6]
    if base_prefix[:4] == b"base":
        # Only bank 0 changes inside the original 128-bank Stadium domain
        # (header + OpenSRAM guard). Preserve the retail match bitmap for
        # banks 1..127 and clear bank 0's match bit.
        old_flags = bytearray(old_base[8:])
        if len(old_flags) != 16:
            raise AssertionError("unexpected Crystal base-match bitmap length")
        old_flags[0] &= 0xFE

        buf[STADIUM_BASE_OFFSET:STADIUM_BASE_OFFSET + STADIUM_BASE_TOTAL_BYTES] = bytes(STADIUM_BASE_TOTAL_BYTES)
        buf[STADIUM_BASE_OFFSET:STADIUM_BASE_OFFSET + 6] = base_prefix
        buf[STADIUM_BASE_OFFSET + 8:STADIUM_BASE_OFFSET + 24] = old_flags
        base_crc = stadium_crc(
            STADIUM_BASE_CRC_INIT,
            buf[STADIUM_BASE_OFFSET:STADIUM_BASE_OFFSET + STADIUM_BASE_TOTAL_BYTES],
        )
        set_u16be(buf, STADIUM_BASE_OFFSET + 6, base_crc)
    elif any(old_base):
        raise ValueError("unexpected nonzero/non-base data before N64PS3 metadata")

    buf[STADIUM_N64_OFFSET:STADIUM_N64_OFFSET + STADIUM_N64_TOTAL_BYTES] = bytes(STADIUM_N64_TOTAL_BYTES)
    buf[STADIUM_N64_OFFSET:STADIUM_N64_OFFSET + 6] = STADIUM_N64_HEADER

    half_bank = STADIUM_BANK_BYTES // 2
    for i in range(STADIUM_NUM_BANKS * 2):
        source = i * half_bank
        checksum = stadium_sum(STADIUM_CRC_INIT, buf[source:source + half_bank])
        set_u16be(buf, STADIUM_N64_OFFSET + STADIUM_N64_HEADER_BYTES + i * 2, checksum)

    data_start = STADIUM_N64_OFFSET + STADIUM_N64_HEADER_BYTES
    n64_crc = stadium_crc(
        STADIUM_CRC_INIT,
        buf[data_start:STADIUM_N64_OFFSET + STADIUM_N64_TOTAL_BYTES],
    )
    set_u16be(buf, STADIUM_N64_OFFSET + 6, n64_crc)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def identify_release(data: bytes, config: dict) -> tuple[str, dict]:
    digest = sha256(data)
    matches = [
        (release_id, profile)
        for release_id, profile in config["releases"].items()
        if profile["input_sha256"] == digest
    ]
    if len(matches) != 1:
        raise ValueError(f"unsupported Crystal ROM SHA-256: {digest}")
    return matches[0]


def _expand_rom_with_profile(data: bytes, release_id: str, profile: dict) -> tuple[bytes, dict]:
    if len(data) != ROM_INPUT_BYTES:
        raise ValueError(f"{release_id}: expected 2 MiB input ROM")
    validate_checksums(data)

    if data[0x147] != CART_MBC3_RTC_RAM_BATTERY:
        raise ValueError(f"{release_id}: expected cartridge type 0x10")
    if data[0x148] != ROM_SIZE_2M:
        raise ValueError(f"{release_id}: expected 2 MiB ROM header code 0x06")
    expected_ram = int(profile["input_ram_size_code"], 16)
    if data[0x149] != expected_ram:
        raise ValueError(
            f"{release_id}: RAM-size header mismatch "
            f"(expected {expected_ram:#04x}, found {data[0x149]:#04x})"
        )
    if data[BANKSWITCH_OFFSET:BANKSWITCH_OFFSET + len(BANKSWITCH_SIGNATURE)] != BANKSWITCH_SIGNATURE:
        raise ValueError(f"{release_id}: unexpected Bankswitch bytes at 0x0010")

    open_sram = int(profile["open_sram_entry"], 16)
    if data[open_sram:open_sram + len(OPEN_SRAM_BODY)] != OPEN_SRAM_BODY:
        raise ValueError(f"{release_id}: OpenSRAM body precondition failed at {open_sram:#x}")

    out = bytearray(data)
    patches = []

    guard_offset_text = profile.get("open_sram_guard_patch_offset")
    if guard_offset_text is None:
        if expected_ram != RAM_SIZE_64K:
            raise ValueError(f"{release_id}: unguarded OpenSRAM is only accepted for 64 KiB baseline")
    else:
        guard_immediate = int(guard_offset_text, 16)
        guard_start = guard_immediate - 1
        if out[guard_start:guard_start + len(OPEN_SRAM_GUARD_4)] != OPEN_SRAM_GUARD_4:
            raise ValueError(f"{release_id}: expected CP $04 OpenSRAM guard at {guard_start:#x}")
        out[guard_immediate] = 0x08
        if out[guard_start:guard_start + len(OPEN_SRAM_GUARD_8)] != OPEN_SRAM_GUARD_8:
            raise AssertionError("OpenSRAM guard patch did not produce CP $08")
        patches.append({
            "offset": guard_immediate,
            "before": "0x04",
            "after": "0x08",
            "reason": "allow MBC30 SRAM banks 0..7",
        })

    out.extend(b"\xFF" * (ROM_TARGET_BYTES - len(out)))
    out[0x147] = CART_MBC3_RTC_RAM_BATTERY
    out[0x148] = ROM_SIZE_4M
    out[0x149] = RAM_SIZE_64K
    out[0x14D] = header_checksum(out)
    regenerate_stadium_metadata(out)
    out[0x14E:0x150] = global_checksum(out).to_bytes(2, "big")
    validate_checksums(out)

    report = {
        "release": release_id,
        "input_sha1": sha1(data),
        "input_sha256": sha256(data),
        "output_sha1": sha1(out),
        "output_sha256": sha256(out),
        "input_bytes": len(data),
        "output_bytes": len(out),
        "rom_banks_16k": len(out) // 0x4000,
        "sram_banks_8k": 8,
        "stadium_metadata_regenerated": True,
        "header": {
            "cartridge_type": f"0x{out[0x147]:02X}",
            "rom_size_code": f"0x{out[0x148]:02X}",
            "ram_size_code": f"0x{out[0x149]:02X}",
            "header_checksum": f"0x{out[0x14D]:02X}",
            "global_checksum": f"0x{int.from_bytes(out[0x14E:0x150], 'big'):04X}",
        },
        "patches": patches,
    }

    expected_sha1 = profile.get("output_sha1")
    expected_sha256 = profile.get("output_sha256")
    if expected_sha1 and report["output_sha1"] != expected_sha1:
        raise AssertionError(f"{release_id}: deterministic output SHA-1 mismatch")
    if expected_sha256 and report["output_sha256"] != expected_sha256:
        raise AssertionError(f"{release_id}: deterministic output SHA-256 mismatch")

    return bytes(out), report


def expand_rom(data: bytes, config: dict) -> tuple[bytes, dict]:
    release_id, profile = identify_release(data, config)
    return _expand_rom_with_profile(data, release_id, profile)


def inspect_save(data: bytes) -> dict:
    size = len(data)
    if size == RAW_SRAM_32K:
        kind = "raw-international-sram"
    elif size == RAW_SRAM_64K:
        kind = "raw-japanese-or-expanded-sram"
    elif size == RAW_SRAM_32K + OBSERVED_CONTAINER_EXTRA:
        kind = "observed-32k-plus-44-container"
    elif size == RAW_SRAM_64K + OBSERVED_CONTAINER_EXTRA:
        kind = "observed-64k-plus-44-container"
    else:
        kind = "unknown"
    return {
        "bytes": size,
        "classification": kind,
        "sha1": sha1(data),
        "sha256": sha256(data),
        "container_transform_safe": size in (RAW_SRAM_32K, RAW_SRAM_64K),
    }


def expand_raw_save(data: bytes, profile: str) -> tuple[bytes, dict]:
    if len(data) in (RAW_SRAM_32K + OBSERVED_CONTAINER_EXTRA, RAW_SRAM_64K + OBSERVED_CONTAINER_EXTRA):
        raise ValueError(
            "save contains the observed extra 44 bytes; container transform is disabled "
            "until those bytes are re-verified byte-for-byte"
        )

    if profile == "international":
        if len(data) != RAW_SRAM_32K:
            raise ValueError("international raw save must be exactly 32 KiB")
        out = data + bytes(RAW_SRAM_64K - RAW_SRAM_32K)
        added = RAW_SRAM_64K - RAW_SRAM_32K
    elif profile == "japan":
        if len(data) != RAW_SRAM_64K:
            raise ValueError("Japanese raw save must be exactly 64 KiB")
        out = bytes(data)
        added = 0
    else:
        raise ValueError("profile must be 'japan' or 'international'")

    return out, {
        "profile": profile,
        "input_bytes": len(data),
        "output_bytes": len(out),
        "legacy_bytes_preserved": len(data),
        "extension_bytes_added": added,
        "new_sram_banks_fill": "0x00",
        "input_sha1": sha1(data),
        "output_sha1": sha1(out),
        "output_sha256": sha256(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)

    rom = sub.add_parser("rom")
    rom.add_argument("input", type=Path)
    rom.add_argument("output", type=Path)

    inspect = sub.add_parser("inspect-save")
    inspect.add_argument("input", type=Path)

    save = sub.add_parser("save-raw")
    save.add_argument("profile", choices=("japan", "international"))
    save.add_argument("input", type=Path)
    save.add_argument("output", type=Path)

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "rom":
        output, report = expand_rom(args.input.read_bytes(), config)
        args.output.write_bytes(output)
    elif args.command == "inspect-save":
        report = inspect_save(args.input.read_bytes())
    else:
        output, report = expand_raw_save(args.input.read_bytes(), args.profile)
        args.output.write_bytes(output)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
