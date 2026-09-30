#!/usr/bin/env python3
"""Verify native Stage 2d Day-Care persistent sidecars."""

from __future__ import annotations
import argparse,re
from pathlib import Path

SYM=re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)$")
CODE=(
 "CrystalEnsureDayCareSidecars",
 "CrystalGetDayCareSidecarEntry",
 "CrystalCopyPartySidecarToDayCare1",
 "CrystalCopyPartySidecarToDayCare2",
 "CrystalMoveDayCare1SidecarToLastParty",
 "CrystalMoveDayCare2SidecarToLastParty",
)

def syms(path:Path):
    out={}
    for line in path.read_text(encoding="utf-8").splitlines():
        m=SYM.match(line.strip())
        if m:
            b,a,n=m.groups();out[n]=(int(b,16),int(a,16))
    return out

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("rom",type=Path)
    ap.add_argument("sym",type=Path)
    args=ap.parse_args()
    s=syms(args.sym)

    for name in CODE:
        b,a=s.get(name,(-1,-1))
        if b!=0x80 or not (0x4000<=a<0x8000):
            raise SystemExit(f"{name}: expected bank80 code, got {b:#x}:{a:#x}")

    start=s.get("sCrystalExtDayCareEntries")
    one=s.get("sCrystalExtDayCare1")
    two=s.get("sCrystalExtDayCare2")
    end=s.get("sCrystalExtDayCareEntriesEnd")
    if start!=(0x04,0xBF1B) or one!=start or two!=(0x04,0xBF24) or end!=(0x04,0xBF2D):
        raise SystemExit(f"Day-Care sidecar layout mismatch: {start} {one} {two} {end}")

    if len(args.rom.read_bytes())!=0x400000:
        raise SystemExit("ROM size changed")
    print(f"{args.rom.name}: Stage 2d Day-Care sidecars OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
