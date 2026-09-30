#!/usr/bin/env python3
"""Validate CRYSTAL native GBC physical-expansion Stage 0 contract."""

from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config"/"native_gbc_stage0.json"

def fail(msg: str) -> None:
    raise SystemExit(f"native Stage 0 validation failed: {msg}")

def main() -> int:
    data=json.loads(CFG.read_text(encoding="utf-8"))
    if data.get("stage")!="native-gbc-physical-expansion-0":
        fail("unexpected stage id")

    target=data["target"]
    expected={
        "platform":"Game Boy Color",
        "mapper_profile":"MBC30-compatible",
        "cartridge_type":"0x10",
        "rom_bytes":4194304,
        "rom_banks_16k":256,
        "rom_size_code":"0x07",
        "sram_bytes":65536,
        "sram_banks_8k":8,
        "ram_size_code":"0x05",
    }
    for key,value in expected.items():
        if target.get(key)!=value:
            fail(f"target {key} changed: {target.get(key)!r}")
    if not target.get("rtc_preserved") or not target.get("stadium_metadata_regenerated"):
        fail("RTC/Stadium integrity policies must stay enabled")

    sig=data["signatures"]
    if sig.get("bankswitch_offset")!="0x0010" or sig.get("bankswitch_bytes")!="E0 9D EA 00 20 C9":
        fail("Bankswitch evidence changed")
    if sig.get("international_open_sram_guard_patch")!="04 -> 08":
        fail("international OpenSRAM 4->8 patch missing")
    if sig.get("empty_all_sram_offset")!="0x4CF1F":
        fail("EmptyAllSRAMBanks offset changed")

    save=data["save_policy"]
    if save.get("expanded_sram_output_bytes")!=65536:
        fail("expanded SRAM output must remain 64 KiB")
    if save.get("container_transform_enabled"):
        fail("44-byte container transform must remain disabled until raw bytes are verified")

    releases=data["releases"]
    expected_ids={"japan_rev0","en_rev0","en_rev_a","fr_rev0","de_rev0","it_rev0","es_rev0"}
    if set(releases)!=expected_ids:
        fail("release set changed")
    if releases["japan_rev0"]["input_ram_size_code"]!="0x05":
        fail("Japanese input must remain 64 KiB SRAM profile")
    for rid,profile in releases.items():
        if rid!="japan_rev0" and profile["input_ram_size_code"]!="0x03":
            fail(f"{rid}: international input SRAM code must remain 0x03")
        if len(profile.get("output_sha256",""))!=64:
            fail(f"{rid}: deterministic output SHA-256 missing")

    print("CRYSTAL native GBC Stage 0 contract: OK")
    print("7 releases / 4 MiB ROM / 64 KiB SRAM / MBC30-compatible")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
