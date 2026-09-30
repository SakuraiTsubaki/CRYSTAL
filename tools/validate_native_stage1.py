#!/usr/bin/env python3
"""Validate CRYSTAL native GBC canonical-registry Stage 1 contract."""

from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config"/"native_gbc_stage1.json"
RESULTS=ROOT/"research"/"evidence"/"native_gbc_stage1_results.csv"

def fail(msg: str) -> None:
    raise SystemExit(f"native Stage 1 validation failed: {msg}")

def main() -> int:
    data=json.loads(CFG.read_text(encoding="utf-8"))
    if data.get("stage")!="native-gbc-registry-seed-1":
        fail("unexpected stage id")

    reg=data["registry"]
    if reg.get("bank")!="0x80" or reg.get("physical_offset")!="0x200000":
        fail("canonical registry must remain in bank 0x80")
    if reg.get("canonical_id_bits")!=16:
        fail("canonical registry IDs must be 16-bit")
    if reg.get("used_bytes_from_bank_start")!=11837 or reg.get("remaining_bytes")!=4547:
        fail("registry bank size accounting changed")

    tables=reg["tables"]
    expected={
        "species_base_data":(251,32,"0x4100","b5756adff731ac1a200056cf0b067eb7784319c4d74bdea022c7e66b519974f7"),
        "moves":(251,7,"0x6060","e84da1c005921f4352d9bbd83bd5a5885a12b0bbdcfd9ddc14c8ceb50c42670e"),
        "item_attributes":(256,7,"0x673D","98c293815c3353a166a8a31cdbced6523dae70e3451de6e7839b6543d382301b"),
    }
    for name,(count,size,address,digest) in expected.items():
        table=tables[name]
        if (table["legacy_count"],table["entry_bytes"],table["target_cpu_address"],table["sha256"])!=(count,size,address,digest):
            fail(f"{name}: table contract changed")

    releases=data["releases"]
    if len(releases)!=7:
        fail("expected seven release profiles")

    with RESULTS.open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=7:
        fail("expected seven raw-ROM result rows")
    by_release={row["release"]:row for row in rows}

    for release,profile in releases.items():
        if release not in by_release:
            fail(f"{release}: result missing")
        row=by_release[release]
        if row["output_sha1"]!=profile["output_sha1"] or row["output_sha256"]!=profile["output_sha256"]:
            fail(f"{release}: deterministic result hash mismatch")
        if row["status"]!="verified_on_raw_rom":
            fail(f"{release}: raw-ROM verification marker missing")
        hooks=profile["expected_hooks"]
        if int(row["base_pointer_hooks"])!=hooks["base_pointers"]:
            fail(f"{release}: BaseData hook count mismatch")
        if int(row["item_pointer_hooks"])!=hooks["item_pointers"]:
            fail(f"{release}: item hook count mismatch")
        if int(row["move_pointer_hooks"])!=hooks["move_pointers"]:
            fail(f"{release}: move hook count mismatch")
        if int(row["move_bank_hooks"])!=hooks["move_bank_immediates"]:
            fail(f"{release}: move bank-hook count mismatch")
        if int(row["excluded_move_collisions"])!=len(profile["excluded_move_address_collisions"]):
            fail(f"{release}: collision count mismatch")

    if not data["patch_policy"].get("preserve_legacy_u8_semantics_in_stage1"):
        fail("Stage 1 must not claim runtime widening")
    if not data["patch_policy"].get("widen_ids_in_later_stage"):
        fail("Stage 2 widening boundary disappeared")

    print("CRYSTAL native GBC Stage 1 contract: OK")
    print("CRYSREG bank 0x80 / BaseData + Moves + ItemAttributes / 7 raw-ROM outputs")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
