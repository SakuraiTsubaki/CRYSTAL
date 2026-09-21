#!/usr/bin/env python3
"""Analyze Pokémon Crystal ROM/save inputs without committing copyrighted binaries.

Outputs only metadata, hashes, header fields, conservative padding candidates, and
save-container size facts. Zero-filled ROM regions are candidates, not asserted free
space. Save bytes beyond nominal SRAM are kept opaque unless separately decoded.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

RAM_BYTES = {
    0x00: 0,
    0x01: 2 * 1024,
    0x02: 8 * 1024,
    0x03: 32 * 1024,
    0x04: 128 * 1024,
    0x05: 64 * 1024,
}
ROM_BYTES = {
    0x00: 32 * 1024,
    0x01: 64 * 1024,
    0x02: 128 * 1024,
    0x03: 256 * 1024,
    0x04: 512 * 1024,
    0x05: 1024 * 1024,
    0x06: 2 * 1024 * 1024,
    0x07: 4 * 1024 * 1024,
    0x08: 8 * 1024 * 1024,
}


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checksum_status(data: bytes) -> tuple[bool, bool]:
    header = 0
    for i in range(0x134, 0x14D):
        header = (header - data[i] - 1) & 0xFF

    global_sum = (sum(data[:0x14E]) + sum(data[0x150:])) & 0xFFFF
    stored_global = (data[0x14E] << 8) | data[0x14F]
    return header == data[0x14D], global_sum == stored_global


def longest_zero_run(data: bytes) -> tuple[int, int, int]:
    best = (0, 0, 0)
    i = 0
    while i < len(data):
        if data[i] != 0:
            i += 1
            continue
        j = i + 1
        while j < len(data) and data[j] == 0:
            j += 1
        if j - i > best[2]:
            best = (i, j, j - i)
        i = j
    return best


def analyze_rom(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 0x150:
        raise ValueError(f"{path}: too small to be a GB/GBC ROM")

    header_ok, global_ok = checksum_status(data)
    zero_banks: list[str] = []
    for bank in range(len(data) // 0x4000):
        block = data[bank * 0x4000 : (bank + 1) * 0x4000]
        if block == b"\0" * len(block):
            zero_banks.append(f"{bank:02X}")

    z0, z1, zlen = longest_zero_run(data)
    ram_code = data[0x149]
    cart_type = data[0x147]
    mapper = (
        "MBC30-compatible"
        if cart_type == 0x10 and ram_code == 0x05
        else "MBC3"
        if cart_type == 0x10
        else "other"
    )

    return {
        "kind": "rom",
        "filename": path.name,
        "size_bytes": len(data),
        "sha1": digest(path, "sha1"),
        "sha256": digest(path, "sha256"),
        "title": data[0x134:0x13F].split(b"\0", 1)[0].decode("ascii", "replace"),
        "game_code": data[0x13F:0x143].decode("ascii", "replace"),
        "cgb_flag": f"0x{data[0x143]:02X}",
        "cart_type": f"0x{cart_type:02X}",
        "rom_size_code": f"0x{data[0x148]:02X}",
        "header_rom_bytes": ROM_BYTES.get(data[0x148]),
        "ram_size_code": f"0x{ram_code:02X}",
        "header_sram_bytes": RAM_BYTES.get(ram_code),
        "destination_code": f"0x{data[0x14A]:02X}",
        "revision": data[0x14C],
        "mapper_profile": mapper,
        "header_checksum_ok": header_ok,
        "global_checksum_ok": global_ok,
        "all_zero_16k_banks": " ".join(zero_banks),
        "largest_zero_run_start": f"0x{z0:X}",
        "largest_zero_run_end_exclusive": f"0x{z1:X}",
        "largest_zero_run_bytes": zlen,
        "zero_run_policy": "candidate_only_not_proven_free_space",
    }


def analyze_save(path: Path) -> dict[str, object]:
    size = path.stat().st_size
    candidates: list[tuple[int, int]] = []
    for payload in (32 * 1024, 64 * 1024, 128 * 1024):
        if size >= payload and size - payload <= 4096:
            candidates.append((payload, size - payload))

    payload, extra = candidates[0] if len(candidates) == 1 else (None, None)
    return {
        "kind": "save",
        "filename": path.name,
        "size_bytes": size,
        "sha1": digest(path, "sha1"),
        "sha256": digest(path, "sha256"),
        "candidate_sram_payload_bytes": payload,
        "extra_container_bytes": extra,
        "extra_bytes_semantics": "opaque_unverified",
        "layout_status": "raw_bytes_available_not_decoded",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for raw in args.paths:
        path = Path(raw)
        if path.suffix.lower() in {".gb", ".gbc"}:
            rows.append(analyze_rom(path))
        else:
            rows.append(analyze_save(path))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    fields = sorted({key for row in rows for key in row})
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
