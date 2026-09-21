#!/usr/bin/env python3
"""Validate CRYSTAL's evidence-driven Generation 10 capacity contract."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "engine_capacity.json"
STORAGE = ROOT / "config" / "storage_profiles.json"
ROM_MANIFEST = ROOT / "research" / "evidence" / "rom_baselines.csv"
SAVE_MANIFEST = ROOT / "research" / "evidence" / "save_baselines.csv"

REQUIRED_REGISTRIES = {
    "species", "variety", "form", "move", "item", "ability", "type",
    "evolution_method", "resource", "feature",
}
REQUIRED_LEGACY_PROFILES = {
    "CRYSTAL_JP_64K_SRAM",
    "CRYSTAL_INTL_32K_SRAM",
}


def fail(message: str) -> None:
    raise SystemExit(f"capacity validation failed: {message}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    storage = json.loads(STORAGE.read_text(encoding="utf-8"))
    roms = read_csv(ROM_MANIFEST)
    saves = read_csv(SAVE_MANIFEST)

    if data.get("project") != "CRYSTAL":
        fail("project must be CRYSTAL")
    if data.get("target_generation", 0) < 10:
        fail("target_generation must be at least 10")

    policy = data.get("policy", {})
    for key in (
        "append_only_ids",
        "japanese_release_is_origin_baseline",
        "evidence_before_offsets",
        "region_revision_specific_legacy_profiles",
        "zero_filled_rom_is_not_free_by_default",
    ):
        if not policy.get(key):
            fail(f"policy {key} must remain enabled")
    if policy.get("guess_unreleased_content"):
        fail("unreleased content must not be guessed")

    master = data.get("master_id", {})
    if master.get("bits") != 16:
        fail("master IDs must be 16-bit")
    if master.get("min_normal") != 1 or master.get("max_normal") != 65535:
        fail("normal master ID range must remain 1..65535")

    registries = data.get("registries", {})
    missing = REQUIRED_REGISTRIES - set(registries)
    if missing:
        fail(f"missing registries: {', '.join(sorted(missing))}")
    for name in sorted(REQUIRED_REGISTRIES):
        if registries[name].get("bits") != 16 or not registries[name].get("append_only"):
            fail(f"{name} must be 16-bit and append-only")

    resource = data.get("resource_directory", {})
    if resource.get("resource_id_bits") != 16:
        fail("resource IDs must be 16-bit")
    if resource.get("logical_bank_id_bits", 0) < 16:
        fail("logical resource bank IDs must be at least 16-bit")
    if not resource.get("mapper_agnostic") or not resource.get("physical_mapper_is_backend"):
        fail("resource placement must remain mapper-backend based")

    save = data.get("save", {})
    if save.get("format") != "CRYSTAL_SAVE_V2":
        fail("save format must be CRYSTAL_SAVE_V2")
    if not save.get("versioned_blocks") or not save.get("legacy_import_required"):
        fail("Save V2 must be versioned and retain legacy import")
    if set(save.get("legacy_profiles", [])) < REQUIRED_LEGACY_PROFILES:
        fail("both Japanese and international legacy save profiles are required")
    if save.get("observed_common_extra_container_bytes") != 44:
        fail("observed save-container extra-byte count must remain 44 until re-measured")

    if len(roms) != 7:
        fail(f"expected 7 verified Crystal ROM baselines, found {len(roms)}")
    if any(r["size_bytes"] != "2097152" for r in roms):
        fail("all current verified Crystal ROM baselines must be 2 MiB")
    if any(r["header_checksum_ok"].lower() != "true" or r["global_checksum_ok"].lower() != "true" for r in roms):
        fail("every ROM baseline must pass both checksums")

    jp = [r for r in roms if r["game_code"] == "BXTJ"]
    intl = [r for r in roms if r["game_code"] != "BXTJ"]
    if len(jp) != 1 or jp[0]["ram_size_code"] != "0x05":
        fail("Japanese baseline must be unique and declare 64 KiB SRAM code 0x05")
    if len(intl) != 6 or any(r["ram_size_code"] != "0x03" for r in intl):
        fail("six international baselines must declare 32 KiB SRAM code 0x03")

    if len(saves) != 7:
        fail(f"expected metadata for 7 Crystal saves, found {len(saves)}")
    jp_saves = [r for r in saves if r["region"] == "Japan"]
    intl_saves = [r for r in saves if r["region"] != "Japan"]
    if len(jp_saves) != 1 or jp_saves[0]["observed_file_size_bytes"] != "65580":
        fail("Japanese save metadata must record 65,580 bytes")
    if len(intl_saves) != 6 or any(r["observed_file_size_bytes"] != "32812" for r in intl_saves):
        fail("six international save metadata rows must record 32,812 bytes")
    if any(r["observed_extra_bytes"] != "44" for r in saves):
        fail("all observed save containers currently have 44 extra bytes")

    expanded = storage.get("expanded_runtime", {})
    if expanded.get("logical_rom_bank_id_bits", 0) < 16:
        fail("expanded logical ROM bank IDs must be at least 16-bit")
    if expanded.get("physical_expanded_mapper") != "TBD_AFTER_DATA_AND_ASSET_CENSUS":
        fail("physical expanded mapper must remain evidence-gated until capacity census")

    print("CRYSTAL evidence-driven capacity contract: OK")
    print("ROM baselines: 7 verified / checksums OK")
    print("Save metadata: 7 observed / raw-byte offsets still unlocked")
    print("Runtime IDs: 16-bit / logical bank IDs: 16-bit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
