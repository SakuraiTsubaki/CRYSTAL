#!/usr/bin/env python3
"""Verify CRYSTAL native GBC Stage 2 box-sidecar symbols and storage geometry."""

from __future__ import annotations
import argparse
from pathlib import Path
import re

SYMBOL_RE=re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)$")
REQUIRED=(
 "CrystalGetBoxSidecarEntry",
 "CrystalCopyPartySidecarToCurrentBox",
 "CrystalCopyCurrentBoxSidecarToParty",
 "CrystalShiftPartySidecarAfterRemove",
 "CrystalShiftCurrentBoxSidecarAfterRemove",
)

def symbols(path:Path):
    out={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        m=SYMBOL_RE.match(raw.strip())
        if m:
            bank,addr,name=m.groups()
            out[name]=(int(bank,16),int(addr,16))
    return out

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("rom",type=Path)
    ap.add_argument("sym",type=Path)
    args=ap.parse_args()
    data=args.rom.read_bytes()
    if len(data)!=0x400000:
        raise SystemExit("Stage 2 ROM must remain 4 MiB")
    if (data[0x147],data[0x148],data[0x149])!=(0x10,0x07,0x05):
        raise SystemExit("Stage 2 cartridge header mismatch")

    sym=symbols(args.sym)
    for name in REQUIRED:
        bank,addr=sym.get(name,(-1,-1))
        if bank!=0x80 or not (0x4000<=addr<0x8000):
            raise SystemExit(f"{name}: expected bank 0x80 callable code, got {bank:#x}:{addr:#x}")

    start=sym.get("sCrystalExtMonEntries")
    end=sym.get("sCrystalExtSaveCoreEnd")
    if start!=(0x04,0xB021) or end!=(0x04,0xBF1B):
        raise SystemExit(f"sidecar layout moved: {start}..{end}")

    # 14*30 reserved box entries followed by six party entries.
    if 14*30+6!=426:
        raise SystemExit("slot-capacity arithmetic changed")

    print(f"{args.rom.name}: Stage 2 box/party sidecar lifecycle OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
