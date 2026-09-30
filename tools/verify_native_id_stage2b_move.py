#!/usr/bin/env python3
"""Verify native Stage 2b MOVE PKMN W/O MAIL sidecar bridge."""

from __future__ import annotations
import argparse,re
from pathlib import Path

SYMBOL_RE=re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)$")
CODE=(
 "CrystalCopyPartySidecarToTemp",
 "CrystalCopyCurrentBoxSidecarToTemp",
 "CrystalInsertTempSidecarIntoParty",
 "CrystalInsertTempSidecarIntoCurrentBox",
)

def read_symbols(path:Path):
    out={}
    for line in path.read_text(encoding="utf-8").splitlines():
        m=SYMBOL_RE.match(line.strip())
        if m:
            b,a,n=m.groups();out[n]=(int(b,16),int(a,16))
    return out

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("rom",type=Path)
    ap.add_argument("sym",type=Path)
    args=ap.parse_args()
    sym=read_symbols(args.sym)
    for name in CODE:
        bank,addr=sym.get(name,(-1,-1))
        if bank!=0x80 or not (0x4000<=addr<0x8000):
            raise SystemExit(f"{name}: not in native ABI bank 0x80: {bank:#x}:{addr:#x}")

    start=sym.get("wCrystalExtTempMonEntry")
    end=sym.get("wCrystalExtTempMonEntryEnd")
    if start is None or end is None or start[0]!=end[0] or end[1]-start[1]!=9:
        raise SystemExit(f"temporary sidecar must be exactly 9 WRAM bytes: {start}..{end}")

    data=args.rom.read_bytes()
    if len(data)!=0x400000:
        raise SystemExit("ROM size changed")
    print(f"{args.rom.name}: Stage 2b MOVE PKMN W/O MAIL bridge OK; temp={start[0]:02x}:{start[1]:04x}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
