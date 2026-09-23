#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "expand_original_crystal.py"

spec = importlib.util.spec_from_file_location("expand_original_crystal", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def make_rom(*, ram_code: int, guarded: bool) -> tuple[bytes, dict]:
    data = bytearray(0x200000)
    data[0x134:0x13F] = b"PM_CRYSTAL\x00"
    data[0x13F:0x143] = b"TEST"
    data[0x143] = 0xC0
    data[0x147] = 0x10
    data[0x148] = 0x06
    data[0x149] = ram_code
    data[0x14A] = 1
    data[0x14B] = 0x33
    data[0x14C] = 0
    data[0x10:0x16] = mod.BANKSWITCH_SIGNATURE

    open_sram = 0x3000
    data[open_sram:open_sram + len(mod.OPEN_SRAM_BODY)] = mod.OPEN_SRAM_BODY
    guard_patch = None
    if guarded:
        guard_start = open_sram - len(mod.OPEN_SRAM_GUARD_4)
        data[guard_start:open_sram] = mod.OPEN_SRAM_GUARD_4
        guard_patch = guard_start + 1

    data[0x14D] = mod.header_checksum(data)
    data[0x14E:0x150] = mod.global_checksum(data).to_bytes(2, "big")

    profile = {
        "input_ram_size_code": f"0x{ram_code:02X}",
        "open_sram_entry": f"0x{open_sram:X}",
        "open_sram_guard_patch_offset": None if guard_patch is None else f"0x{guard_patch:X}",
    }
    return bytes(data), profile


def test_japan_rom() -> None:
    data, profile = make_rom(ram_code=0x05, guarded=False)
    out, report = mod._expand_rom_with_profile(data, "test_japan", profile)
    assert len(out) == 0x400000
    assert out[0x148] == 0x07
    assert out[0x149] == 0x05
    assert report["patches"] == []
    assert out[0x200000:] == b"\xFF" * 0x200000
    mod.validate_checksums(out)


def test_international_rom() -> None:
    data, profile = make_rom(ram_code=0x03, guarded=True)
    guard_immediate = int(profile["open_sram_guard_patch_offset"], 16)
    out, report = mod._expand_rom_with_profile(data, "test_intl", profile)
    assert out[guard_immediate] == 0x08
    assert len(report["patches"]) == 1
    assert out[0x149] == 0x05
    mod.validate_checksums(out)


def test_save_rules() -> None:
    raw32 = bytes([0x5A]) * 0x8000
    out, report = mod.expand_raw_save(raw32, "international")
    assert len(out) == 0x10000
    assert out[:0x8000] == raw32
    assert out[0x8000:] == bytes(0x8000)
    assert report["extension_bytes_added"] == 0x8000

    raw64 = bytes([0xA5]) * 0x10000
    out, report = mod.expand_raw_save(raw64, "japan")
    assert out == raw64
    assert report["extension_bytes_added"] == 0

    container = bytes(0x802C)
    try:
        mod.expand_raw_save(container, "international")
    except ValueError as exc:
        assert "extra 44 bytes" in str(exc)
    else:
        raise AssertionError("44-byte container must be refused until verified")


if __name__ == "__main__":
    test_japan_rom()
    test_international_rom()
    test_save_rules()
    print("CRYSTAL native GBC Stage 0 tests: OK")
